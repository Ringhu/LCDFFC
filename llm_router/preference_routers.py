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
    raise ValueError(f"Unsupported router_type: {router_type}")
