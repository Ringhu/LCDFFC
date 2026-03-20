"""Simple high-level preference routers for experiment bridging.

These routers are intentionally lightweight. They sit above the existing
forecast + QP loop and output structured controller weights/constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from llm_router.json_schema import validate_router_output

SMOOTH_FLOOR = 0.1

PRESET_PROFILES = {
    "balanced": {
        "weights": {"cost": 0.4, "carbon": 0.2, "peak": 0.3, "smooth": 0.1},
        "constraints": {"reserve_soc": None, "max_charge_rate": None},
    },
    "cost": {
        "weights": {"cost": 0.65, "carbon": 0.1, "peak": 0.15, "smooth": 0.1},
        "constraints": {"reserve_soc": None, "max_charge_rate": None},
    },
    "carbon": {
        "weights": {"cost": 0.1, "carbon": 0.65, "peak": 0.15, "smooth": 0.1},
        "constraints": {"reserve_soc": None, "max_charge_rate": None},
    },
    "peak": {
        "weights": {"cost": 0.15, "carbon": 0.1, "peak": 0.65, "smooth": 0.1},
        "constraints": {"reserve_soc": 0.2, "max_charge_rate": None},
    },
    "reserve": {
        "weights": {"cost": 0.15, "carbon": 0.1, "peak": 0.55, "smooth": 0.2},
        "constraints": {"reserve_soc": 0.35, "max_charge_rate": None},
    },
}

DEFAULT_REGIME_ORDER = ["cost", "carbon", "peak", "reserve"]
REVIEWED_EXPERT_BY_INTENT = {
    "cost": "balanced",
    "carbon": "balanced",
    "peak": "carbon",
    "reserve": "reserve",
    "balanced": "balanced",
}

CANDIDATE_COMPATIBILITY = {
    "cost": {"cost": 1.0, "balanced": 0.75, "peak": 0.45, "reserve": 0.35, "carbon": 0.25},
    "carbon": {"carbon": 1.0, "balanced": 0.75, "peak": 0.4, "reserve": 0.35, "cost": 0.2},
    "peak": {"peak": 1.0, "reserve": 0.8, "balanced": 0.65, "carbon": 0.35, "cost": 0.25},
    "reserve": {"reserve": 1.0, "peak": 0.8, "balanced": 0.6, "carbon": 0.3, "cost": 0.2},
    "balanced": {"balanced": 1.0, "cost": 0.6, "carbon": 0.6, "peak": 0.6, "reserve": 0.5},
}


@dataclass
class PreferenceRegime:
    """One interval in a preference-shift schedule."""

    name: str
    start_step: int
    end_step: int
    instruction: str
    preference_vector: dict[str, float]
    target_profile: dict[str, Any]


def _make_instruction(name: str) -> str:
    """Return a natural-language instruction for one regime."""
    mapping = {
        "cost": "Electricity price is the main priority. Reduce operating cost first, but keep the controller stable.",
        "carbon": "Carbon reduction is the main priority. Prefer lower-emission operation even if cost is not minimal.",
        "peak": "Grid stress is high. Peak shaving is the main priority, and the controller should protect the grid.",
        "reserve": "Resilience is the main priority. Keep meaningful battery reserve for future risk and avoid aggressive depletion.",
        "balanced": "Maintain a balanced tradeoff across cost, carbon, and peak reduction.",
    }
    return mapping[name]


def build_default_preference_schedule(total_steps: int) -> list[PreferenceRegime]:
    """Split one episode into four preference-shift segments."""
    total_steps = max(int(total_steps), 1)
    segment_length = max(total_steps // len(DEFAULT_REGIME_ORDER), 1)
    schedule: list[PreferenceRegime] = []

    for i, name in enumerate(DEFAULT_REGIME_ORDER):
        start = i * segment_length
        end = total_steps if i == len(DEFAULT_REGIME_ORDER) - 1 else min((i + 1) * segment_length, total_steps)
        vector = {key: 0.0 for key in ("cost", "carbon", "peak", "reserve")}
        vector[name] = 1.0
        schedule.append(
            PreferenceRegime(
                name=name,
                start_step=start,
                end_step=end,
                instruction=_make_instruction(name),
                preference_vector=vector,
                target_profile=PRESET_PROFILES[name],
            )
        )

    return schedule


def resolve_regime(schedule: list[PreferenceRegime], step: int) -> PreferenceRegime:
    """Return the active regime for the current step."""
    for regime in schedule:
        if regime.start_step <= step < regime.end_step:
            return regime
    return schedule[-1]


def _normalize_primary(cost: float, carbon: float, peak: float) -> dict[str, float]:
    total = max(cost + carbon + peak, 1e-8)
    scale = 1.0 - SMOOTH_FLOOR
    return {
        "cost": scale * cost / total,
        "carbon": scale * carbon / total,
        "peak": scale * peak / total,
        "smooth": SMOOTH_FLOOR,
    }


def _with_context_adjustment(output: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Slightly adjust routing outputs using current numeric context."""
    result = {
        "weights": dict(output["weights"]),
        "constraints": dict(output["constraints"]),
    }

    price = float(context.get("price", 0.0))
    carbon = float(context.get("carbon_intensity", 0.0))
    grid_stress = str(context.get("grid_stress", "low"))
    soc = float(context.get("soc_avg", 0.5))

    if price > 0.04:
        result["weights"]["cost"] = min(result["weights"]["cost"] + 0.05, 0.8)
    if carbon > 0.48:
        result["weights"]["carbon"] = min(result["weights"]["carbon"] + 0.05, 0.8)
    if grid_stress in {"high", "critical"}:
        result["weights"]["peak"] = min(result["weights"]["peak"] + 0.08, 0.85)
        result["constraints"]["reserve_soc"] = max(result["constraints"].get("reserve_soc") or 0.0, 0.25)
    if soc < 0.18:
        result["constraints"]["reserve_soc"] = max(result["constraints"].get("reserve_soc") or 0.0, 0.2)

    primary = _normalize_primary(
        result["weights"]["cost"],
        result["weights"]["carbon"],
        result["weights"]["peak"],
    )
    result["weights"].update(primary)
    return validate_router_output(result)


class FixedPreferenceRouter:
    """Always return one preset profile for the full episode."""

    def __init__(self, regime_name: str = "balanced"):
        if regime_name not in PRESET_PROFILES:
            raise ValueError(f"Unknown fixed regime: {regime_name}")
        self.regime_name = regime_name

    def route(self, context: dict[str, Any]) -> dict[str, Any]:
        return validate_router_output(PRESET_PROFILES[self.regime_name])


class HeuristicPreferenceRouter:
    """Rule-based router that uses structured regime identity and context."""

    def route(self, context: dict[str, Any]) -> dict[str, Any]:
        regime_name = str(context.get("regime_name", "balanced"))
        base = PRESET_PROFILES.get(regime_name, PRESET_PROFILES["balanced"])
        return _with_context_adjustment(base, context)


class NumericPreferenceRouter:
    """Structured router that reads a numeric preference vector."""

    def route(self, context: dict[str, Any]) -> dict[str, Any]:
        vector = context.get("preference_vector", {}) or {}
        cost = float(vector.get("cost", 0.0))
        carbon = float(vector.get("carbon", 0.0))
        peak = float(vector.get("peak", 0.0))
        reserve = float(vector.get("reserve", 0.0))
        weights = _normalize_primary(cost, carbon, peak)
        constraints = {
            "reserve_soc": None if reserve <= 1e-8 else min(0.15 + 0.2 * reserve, 0.5),
            "max_charge_rate": None,
        }
        return _with_context_adjustment({"weights": weights, "constraints": constraints}, context)


class TextTemplatePreferenceRouter:
    """Keyword-based text router for the first experiment-bridge iteration."""

    COST_PAT = re.compile(r"(cost|price|bill|tariff|成本|电价)", re.I)
    CARBON_PAT = re.compile(r"(carbon|emission|low[- ]?carbon|碳)", re.I)
    PEAK_PAT = re.compile(r"(peak|grid stress|demand|shav|削峰|峰)", re.I)
    RESERVE_PAT = re.compile(r"(reserve|resilien|outage|backup|保底|韧性|soc)", re.I)

    def route(self, context: dict[str, Any]) -> dict[str, Any]:
        text = str(context.get("instruction", ""))
        vector = {
            "cost": 1.0 if self.COST_PAT.search(text) else 0.0,
            "carbon": 1.0 if self.CARBON_PAT.search(text) else 0.0,
            "peak": 1.0 if self.PEAK_PAT.search(text) else 0.0,
            "reserve": 1.0 if self.RESERVE_PAT.search(text) else 0.0,
        }

        if sum(vector.values()) == 0:
            vector["cost"] = vector["carbon"] = vector["peak"] = 1.0 / 3.0

        weights = _normalize_primary(vector["cost"], vector["carbon"], vector["peak"])
        constraints = {
            "reserve_soc": 0.35 if vector["reserve"] > 0 else None,
            "max_charge_rate": None,
        }
        return _with_context_adjustment({"weights": weights, "constraints": constraints}, context)


class TextAdaptivePreferenceRouterV2:
    """Context-aware text router that selects and blends candidate profiles."""

    COST_PAT = re.compile(r"(cost first|price first|reduce operating cost|成本优先|电价优先)", re.I)
    CARBON_PAT = re.compile(r"(carbon reduction|carbon first|low-emission|低碳优先|碳排优先)", re.I)
    PEAK_PAT = re.compile(r"(peak shaving|grid stress|protect the grid|削峰优先|电网压力)", re.I)
    RESERVE_PAT = re.compile(r"(reserve|resilience|backup|保留.*soc|韧性优先|保底)", re.I)
    NEGATE_COST_PAT = re.compile(r"(even if cost is not minimal|cost is not the main priority|即使成本不是最低|成本不是首要)", re.I)

    def _dominant_intent(self, text: str) -> str:
        text = text.strip()
        if self.RESERVE_PAT.search(text):
            return "reserve"
        if self.PEAK_PAT.search(text):
            return "peak"
        if self.CARBON_PAT.search(text):
            return "carbon"
        if self.COST_PAT.search(text):
            return "cost"
        return "balanced"

    def _base_priority(self, text: str) -> dict[str, float]:
        dominant = self._dominant_intent(text)
        vector = {k: 0.0 for k in ("cost", "carbon", "peak", "reserve")}
        vector[dominant] = 1.0

        if dominant == "carbon" and self.NEGATE_COST_PAT.search(text):
            vector["cost"] = 0.0
        elif dominant == "carbon":
            vector["cost"] = 0.15
        elif dominant == "peak":
            vector["reserve"] = 0.2
        elif dominant == "reserve":
            vector["peak"] = 0.2

        return vector

    def _context_score(self, candidate_name: str, context: dict[str, Any]) -> float:
        price = float(context.get("price", 0.0))
        carbon = float(context.get("carbon_intensity", 0.0))
        load_peak_forecast = float(context.get("load_peak_forecast", 0.0))
        grid_stress = str(context.get("grid_stress", "low"))
        soc = float(context.get("soc_avg", 0.5))

        score = 0.0
        if candidate_name == "cost":
            score += 3.0 * price
        elif candidate_name == "carbon":
            score += 3.0 * carbon
        elif candidate_name == "peak":
            score += 0.7 * load_peak_forecast
            score += 0.2 if grid_stress in {"high", "critical"} else 0.0
        elif candidate_name == "reserve":
            score += 0.25 if grid_stress in {"high", "critical"} else 0.0
            score += max(0.35 - soc, 0.0)
        elif candidate_name == "balanced":
            score += 0.05

        return score

    def route(self, context: dict[str, Any]) -> dict[str, Any]:
        text = str(context.get("instruction", ""))
        dominant = self._dominant_intent(text)
        base_priority = self._base_priority(text)

        candidates = ["balanced", "cost", "carbon", "peak", "reserve"]
        scored = []
        for candidate in candidates:
            compatibility = CANDIDATE_COMPATIBILITY[dominant][candidate]
            score = compatibility + self._context_score(candidate, context)
            scored.append((candidate, score))
        best_candidate = max(scored, key=lambda item: item[1])[0]

        candidate_profile = PRESET_PROFILES[best_candidate]
        balanced_profile = PRESET_PROFILES["balanced"]
        if dominant in {"peak", "reserve"}:
            alpha = 0.8
        elif dominant == "balanced":
            alpha = 0.5
        else:
            alpha = 0.7

        blended = {
            "weights": {
                key: alpha * candidate_profile["weights"][key] + (1 - alpha) * balanced_profile["weights"][key]
                for key in candidate_profile["weights"]
            },
            "constraints": dict(candidate_profile["constraints"]),
        }

        if base_priority["reserve"] > 0 or best_candidate == "reserve":
            blended["constraints"]["reserve_soc"] = max(blended["constraints"].get("reserve_soc") or 0.0, 0.3)

        if dominant == "carbon" and self.NEGATE_COST_PAT.search(text):
            blended["weights"]["cost"] *= 0.3
            blended["weights"]["carbon"] += 0.1

        return _with_context_adjustment(blended, context)


class TextAdaptivePreferenceRouterV3:
    """Instruction-anchored router with bounded context adaptation.

    V2 improved over the first keyword router but still let context sometimes
    overpower the explicit textual intent. V3 keeps the instruction as the
    dominant source of weights and uses context only for bounded local tweaks.
    """

    COST_PAT = TextAdaptivePreferenceRouterV2.COST_PAT
    CARBON_PAT = TextAdaptivePreferenceRouterV2.CARBON_PAT
    PEAK_PAT = TextAdaptivePreferenceRouterV2.PEAK_PAT
    RESERVE_PAT = TextAdaptivePreferenceRouterV2.RESERVE_PAT
    NEGATE_COST_PAT = TextAdaptivePreferenceRouterV2.NEGATE_COST_PAT

    def _dominant_intent(self, text: str) -> str:
        text = text.strip()
        if self.RESERVE_PAT.search(text):
            return "reserve"
        if self.PEAK_PAT.search(text):
            return "peak"
        if self.CARBON_PAT.search(text):
            return "carbon"
        if self.COST_PAT.search(text):
            return "cost"
        return "balanced"

    def route(self, context: dict[str, Any]) -> dict[str, Any]:
        text = str(context.get("instruction", ""))
        dominant = self._dominant_intent(text)
        result = {
            "weights": dict(PRESET_PROFILES[dominant]["weights"]),
            "constraints": dict(PRESET_PROFILES[dominant]["constraints"]),
        }

        price = float(context.get("price", 0.0))
        carbon = float(context.get("carbon_intensity", 0.0))
        grid_stress = str(context.get("grid_stress", "low"))
        soc = float(context.get("soc_avg", 0.5))
        load_peak_forecast = float(context.get("load_peak_forecast", 0.0))
        price_trend = str(context.get("price_trend", "stable"))

        if dominant == "cost":
            if price > 0.04 or price_trend == "rising":
                result["weights"]["cost"] += 0.08
            if grid_stress in {"high", "critical"}:
                result["weights"]["peak"] += 0.05
            result["weights"]["carbon"] = min(result["weights"]["carbon"], 0.12)

        elif dominant == "carbon":
            result["weights"]["carbon"] += 0.05
            if carbon > 0.48:
                result["weights"]["carbon"] += 0.04
            if self.NEGATE_COST_PAT.search(text):
                result["weights"]["cost"] *= 0.25
            if grid_stress == "critical":
                result["weights"]["peak"] += 0.06
            result["weights"]["peak"] = min(result["weights"]["peak"], 0.22)

        elif dominant == "peak":
            if load_peak_forecast > 1.0 or grid_stress in {"high", "critical"}:
                result["weights"]["peak"] += 0.08
            result["constraints"]["reserve_soc"] = max(result["constraints"].get("reserve_soc") or 0.0, 0.25)

        elif dominant == "reserve":
            result["constraints"]["reserve_soc"] = max(result["constraints"].get("reserve_soc") or 0.0, 0.35)
            if soc < 0.25:
                result["weights"]["peak"] += 0.03
            if grid_stress in {"high", "critical"}:
                result["weights"]["peak"] += 0.05
            result["weights"]["cost"] = min(result["weights"]["cost"], 0.18)

        else:
            if price > 0.04:
                result["weights"]["cost"] += 0.03
            if carbon > 0.48:
                result["weights"]["carbon"] += 0.03
            if grid_stress in {"high", "critical"}:
                result["weights"]["peak"] += 0.04

        if soc < 0.18:
            result["constraints"]["reserve_soc"] = max(result["constraints"].get("reserve_soc") or 0.0, 0.2)

        weights = result["weights"]
        primary = _normalize_primary(weights["cost"], weights["carbon"], weights["peak"])
        result["weights"].update(primary)

        # Keep explicit textual intent dominant after normalization.
        dominant_floor = {
            "cost": ("cost", 0.55),
            "carbon": ("carbon", 0.55),
            "peak": ("peak", 0.55),
            "reserve": ("peak", 0.45),
            "balanced": ("cost", None),
        }
        key, minimum = dominant_floor[dominant]
        if minimum is not None and result["weights"][key] < minimum:
            deficit = minimum - result["weights"][key]
            take_from = [k for k in ("cost", "carbon", "peak") if k != key]
            available = sum(result["weights"][k] for k in take_from)
            if available > 1e-8:
                for other in take_from:
                    result["weights"][other] -= deficit * (result["weights"][other] / available)
                result["weights"][key] = minimum

        return validate_router_output(result)


class TextExpertSelectorRouterV4:
    """Review-informed text router that selects among strong fixed experts.

    This version is chosen after reviewing v1-v3 results. The fixed policies
    are currently the strongest building blocks, so language should first route
    across validated experts before trying to synthesize completely free-form
    weights.
    """

    COST_PAT = TextAdaptivePreferenceRouterV2.COST_PAT
    CARBON_PAT = TextAdaptivePreferenceRouterV2.CARBON_PAT
    PEAK_PAT = TextAdaptivePreferenceRouterV2.PEAK_PAT
    RESERVE_PAT = TextAdaptivePreferenceRouterV2.RESERVE_PAT
    NEGATE_COST_PAT = TextAdaptivePreferenceRouterV2.NEGATE_COST_PAT

    def _dominant_intent(self, text: str) -> str:
        if self.RESERVE_PAT.search(text):
            return "reserve"
        if self.PEAK_PAT.search(text):
            return "peak"
        if self.CARBON_PAT.search(text):
            return "carbon"
        if self.COST_PAT.search(text):
            return "cost"
        return "balanced"

    def route(self, context: dict[str, Any]) -> dict[str, Any]:
        text = str(context.get("instruction", ""))
        dominant = self._dominant_intent(text)
        primary_name = REVIEWED_EXPERT_BY_INTENT[dominant]
        primary = PRESET_PROFILES[primary_name]
        balanced = PRESET_PROFILES["balanced"]

        grid_stress = str(context.get("grid_stress", "low"))
        soc = float(context.get("soc_avg", 0.5))
        carbon = float(context.get("carbon_intensity", 0.0))
        price = float(context.get("price", 0.0))
        price_trend = str(context.get("price_trend", "stable"))

        if dominant == "reserve":
            alpha = 0.9
        elif dominant == "peak":
            alpha = 0.8
        elif dominant == "carbon":
            alpha = 0.75 if carbon > 0.45 else 0.65
        elif dominant == "cost":
            alpha = 0.65 if price > 0.035 or price_trend == "rising" else 0.55
        else:
            alpha = 0.5

        result = {
            "weights": {
                key: alpha * primary["weights"][key] + (1 - alpha) * balanced["weights"][key]
                for key in primary["weights"]
            },
            "constraints": dict(primary["constraints"]),
        }

        if dominant == "peak":
            result["constraints"]["reserve_soc"] = max(result["constraints"].get("reserve_soc") or 0.0, 0.2)
        if dominant == "reserve":
            result["constraints"]["reserve_soc"] = max(result["constraints"].get("reserve_soc") or 0.0, 0.35)
        if dominant == "cost" and grid_stress in {"high", "critical"}:
            result["weights"]["peak"] += 0.05
            result["weights"]["cost"] -= 0.05
        if dominant == "carbon" and self.NEGATE_COST_PAT.search(text):
            result["weights"]["cost"] *= 0.4
            result["weights"]["carbon"] += 0.06
        if soc < 0.2:
            result["constraints"]["reserve_soc"] = max(result["constraints"].get("reserve_soc") or 0.0, 0.2)

        weights = result["weights"]
        normalized = _normalize_primary(weights["cost"], weights["carbon"], weights["peak"])
        result["weights"].update(normalized)
        return validate_router_output(result)


def make_router(router_type: str, fixed_regime: str = "balanced"):
    """Factory for experiment routers."""
    router_type = router_type.lower()
    if router_type == "fixed":
        return FixedPreferenceRouter(fixed_regime)
    if router_type == "heuristic":
        return HeuristicPreferenceRouter()
    if router_type == "numeric":
        return NumericPreferenceRouter()
    if router_type == "text":
        return TextTemplatePreferenceRouter()
    if router_type == "text_v2":
        return TextAdaptivePreferenceRouterV2()
    if router_type == "text_v3":
        return TextAdaptivePreferenceRouterV3()
    if router_type == "text_v4":
        return TextExpertSelectorRouterV4()
    raise ValueError(f"Unsupported router_type: {router_type}")
