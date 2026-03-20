"""Schedule builders for preference-shift experiments."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from llm_router.preference_routers import PRESET_PROFILES, PreferenceRegime, _make_instruction


def _normalize_series(values: np.ndarray, quantile: float = 0.75) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    if len(values) == 0:
        return values
    center = float(np.quantile(values, 0.5))
    high = float(np.quantile(values, max(float(quantile), 0.51)))
    scale = max(high - center, 1e-6)
    return np.clip((values - center) / scale, 0.0, 2.0)


def _window_mean(signal: np.ndarray, start: int, end: int) -> float:
    start = max(int(start), 0)
    end = min(int(end), len(signal))
    if end <= start:
        return float(signal[min(start, len(signal) - 1)])
    return float(np.mean(signal[start:end]))


def _window_max(signal: np.ndarray, start: int, end: int) -> float:
    start = max(int(start), 0)
    end = min(int(end), len(signal))
    if end <= start:
        return float(signal[min(start, len(signal) - 1)])
    return float(np.max(signal[start:end]))


def _preference_vector(name: str) -> dict[str, float]:
    if name == "balanced":
        return {"cost": 1.0 / 3.0, "carbon": 1.0 / 3.0, "peak": 1.0 / 3.0, "reserve": 0.0}
    vector = {key: 0.0 for key in ("cost", "carbon", "peak", "reserve")}
    vector[name] = 1.0
    return vector


def _build_segment(name: str, start: int, end: int, reason: str) -> PreferenceRegime:
    instruction = _make_instruction(name)
    if reason:
        instruction = f"{instruction} Trigger: {reason}."
    return PreferenceRegime(
        name=name,
        start_step=int(start),
        end_step=int(end),
        instruction=instruction,
        preference_vector=_preference_vector(name),
        target_profile=PRESET_PROFILES[name],
    )


def _compress_segments(labels: list[str], reasons: list[str], min_segment_len: int) -> tuple[list[str], list[str]]:
    if not labels:
        return labels, reasons
    min_segment_len = max(int(min_segment_len), 1)
    changed = True
    while changed:
        changed = False
        segments = []
        start = 0
        for i in range(1, len(labels) + 1):
            if i == len(labels) or labels[i] != labels[start]:
                segments.append((start, i, labels[start]))
                start = i
        for idx, (start, end, name) in enumerate(segments):
            if end - start >= min_segment_len:
                continue
            changed = True
            if idx == 0 and len(segments) > 1:
                replacement = segments[idx + 1][2]
            else:
                replacement = segments[idx - 1][2]
            for pos in range(start, end):
                labels[pos] = replacement
                reasons[pos] = reasons[max(start - 1, 0)] if replacement != name else reasons[pos]
            break
    return labels, reasons


def load_signal_table(npz_path: str | Path, total_steps: int | None = None) -> dict[str, np.ndarray]:
    loaded = np.load(npz_path, allow_pickle=True)
    data = loaded["data"].astype(np.float32)
    columns = [str(col) for col in loaded["columns"]]
    if total_steps is not None:
        data = data[: int(total_steps)]
    table = {name: data[:, idx] for idx, name in enumerate(columns)}
    table["_num_steps"] = np.array([len(data)], dtype=np.int32)
    return table


def build_event_driven_preference_schedule(
    signal_table: dict[str, np.ndarray],
    total_steps: int,
    short_window: int = 6,
    reserve_window: int = 12,
    quantile: float = 0.75,
    reserve_quantile: float = 0.8,
    min_segment_len: int = 12,
) -> list[PreferenceRegime]:
    total_steps = min(int(total_steps), int(signal_table["_num_steps"][0]))
    if total_steps <= 0:
        return [_build_segment("balanced", 0, 1, "empty episode fallback")]

    price = signal_table["electricity_pricing"][:total_steps]
    carbon = signal_table["carbon_intensity"][:total_steps]
    net_load = signal_table.get("net_electricity_consumption_avg", signal_table["non_shiftable_load_avg"])[:total_steps]

    price_short = np.array([_window_mean(price, t, t + short_window) for t in range(total_steps)], dtype=np.float32)
    carbon_short = np.array([_window_mean(carbon, t, t + short_window) for t in range(total_steps)], dtype=np.float32)
    peak_short = np.array([_window_max(net_load, t, t + short_window) for t in range(total_steps)], dtype=np.float32)

    price_norm = _normalize_series(price_short, quantile)
    carbon_norm = _normalize_series(carbon_short, quantile)
    peak_norm = _normalize_series(peak_short, quantile)

    future_risk = np.zeros(total_steps, dtype=np.float32)
    for t in range(total_steps):
        future_start = min(t + short_window, total_steps - 1)
        future_end = min(t + reserve_window, total_steps)
        future_risk[t] = max(
            _window_mean(price_norm, future_start, future_end),
            _window_mean(carbon_norm, future_start, future_end),
            _window_max(peak_norm, future_start, future_end),
        )
    reserve_threshold = float(np.quantile(future_risk, max(float(reserve_quantile), 0.55)))

    labels: list[str] = []
    reasons: list[str] = []
    active = "balanced"
    last_change = 0
    persistence_margin = 0.15

    for t in range(total_steps):
        event_scores = {
            "cost": float(price_norm[t]),
            "carbon": float(carbon_norm[t]),
            "peak": float(peak_norm[t]),
        }
        dominant_name, dominant_score = max(event_scores.items(), key=lambda item: item[1])
        reserve_ready = future_risk[t] >= reserve_threshold and dominant_score < 0.8

        if reserve_ready:
            candidate = "reserve"
            reason = f"future_risk={future_risk[t]:.2f}, immediate={dominant_name}:{dominant_score:.2f}"
        elif dominant_score >= 1.0:
            candidate = dominant_name
            reason = f"{dominant_name}_score={dominant_score:.2f}"
        else:
            candidate = "balanced"
            reason = f"no dominant event, top={dominant_name}:{dominant_score:.2f}"

        if t == 0:
            active = candidate
            last_change = 0
        elif candidate != active:
            since_change = t - last_change
            active_score = event_scores.get(active, 0.75 if active == "balanced" else 0.6)
            candidate_score = event_scores.get(candidate, future_risk[t] if candidate == "reserve" else 0.7)
            if since_change >= min_segment_len and candidate_score >= active_score + persistence_margin:
                active = candidate
                last_change = t
                reason = f"switch_from={labels[-1]} | {reason}"
            else:
                candidate = active
                reason = reasons[-1]

        labels.append(candidate)
        reasons.append(reason)

    labels, reasons = _compress_segments(labels, reasons, min_segment_len)

    schedule: list[PreferenceRegime] = []
    start = 0
    for step in range(1, total_steps + 1):
        if step == total_steps or labels[step] != labels[start]:
            reason = reasons[start]
            schedule.append(_build_segment(labels[start], start, step, reason))
            start = step

    return schedule
