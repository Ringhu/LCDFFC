"""Tests for preference-shift routing and metrics."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from eval.run_preference_shift import build_corrupted_strategy
from eval.analyze_preference_shift_gap import summarize_routes
from eval.preference_shift_metrics import compute_episode_kpis, compute_preference_score, compute_segment_metrics
from llm_router.preference_routers import build_default_preference_schedule, make_router, resolve_regime


def test_default_schedule_covers_all_steps():
    schedule = build_default_preference_schedule(100)
    assert len(schedule) == 4
    assert schedule[0].start_step == 0
    assert schedule[-1].end_step == 100
    assert resolve_regime(schedule, 99).name == "reserve"


def test_text_router_outputs_valid_profile():
    router = make_router("text")
    result = router.route(
        {
            "instruction": "Peak shaving is the main priority and keep reserve SOC for resilience.",
            "price": 0.03,
            "carbon_intensity": 0.45,
            "grid_stress": "high",
            "soc_avg": 0.4,
        }
    )
    assert set(result["weights"].keys()) == {"cost", "carbon", "peak", "smooth"}
    assert abs(sum(result["weights"].values()) - 1.0) < 1e-6
    assert result["constraints"]["reserve_soc"] is not None


def test_text_v2_router_handles_carbon_instruction_without_cost_bias():
    router = make_router("text_v2")
    result = router.route(
        {
            "instruction": "Carbon reduction is the main priority, even if cost is not minimal.",
            "price": 0.03,
            "carbon_intensity": 0.52,
            "grid_stress": "medium",
            "load_peak_forecast": 0.8,
            "soc_avg": 0.4,
        }
    )
    assert result["weights"]["carbon"] > result["weights"]["cost"]
    assert abs(sum(result["weights"].values()) - 1.0) < 1e-6


def test_text_v3_router_keeps_instruction_dominant():
    router = make_router("text_v3")
    result = router.route(
        {
            "instruction": "Electricity price is the main priority. Reduce operating cost first, but keep the controller stable.",
            "price": 0.028,
            "carbon_intensity": 0.42,
            "grid_stress": "medium",
            "load_peak_forecast": 0.75,
            "soc_avg": 0.3,
            "price_trend": "stable",
        }
    )
    assert result["weights"]["cost"] >= 0.55
    assert abs(sum(result["weights"].values()) - 1.0) < 1e-6


def test_text_v4_routes_to_reviewed_experts():
    router = make_router("text_v4")
    result = router.route(
        {
            "instruction": "Resilience is the main priority. Keep meaningful battery reserve for future risk and avoid aggressive depletion.",
            "price": 0.03,
            "carbon_intensity": 0.40,
            "grid_stress": "high",
            "load_peak_forecast": 1.1,
            "soc_avg": 0.22,
            "price_trend": "stable",
        }
    )
    assert result["constraints"]["reserve_soc"] is not None
    assert result["weights"]["peak"] >= 0.45
    assert abs(sum(result["weights"].values()) - 1.0) < 1e-6


def test_text_best_alias_points_to_current_verified_best():
    context = {
        "instruction": "Resilience is the main priority. Keep meaningful battery reserve for future risk and avoid aggressive depletion.",
        "price": 0.03,
        "carbon_intensity": 0.40,
        "grid_stress": "high",
        "load_peak_forecast": 1.1,
        "soc_avg": 0.22,
        "price_trend": "stable",
    }
    best_router = make_router("text_best")
    v4_router = make_router("text_v4")
    assert best_router.route(context) == v4_router.route(context)


def test_text_v5_keeps_reserve_guard_after_leaving_reserve():
    router = make_router("text_v5")
    reserve_context = {
        "regime_name": "reserve",
        "instruction": "Resilience is the main priority. Keep meaningful battery reserve for future risk and avoid aggressive depletion.",
        "price": 0.03,
        "carbon_intensity": 0.40,
        "grid_stress": "medium",
        "load_peak_forecast": 0.9,
        "soc_avg": 0.34,
        "price_trend": "stable",
    }
    cost_context = {
        "regime_name": "cost",
        "instruction": "Electricity price is the main priority. Reduce operating cost first, but keep the controller stable.",
        "price": 0.045,
        "carbon_intensity": 0.41,
        "grid_stress": "medium",
        "load_peak_forecast": 0.8,
        "soc_avg": 0.32,
        "price_trend": "rising",
    }
    router.route(reserve_context)
    guarded = router.route(cost_context)
    assert guarded["constraints"]["reserve_soc"] is not None
    assert guarded["constraints"]["reserve_soc"] >= 0.25


def test_text_v6_only_keeps_narrow_release_guard_when_soc_is_low():
    router = make_router("text_v6")
    reserve_context = {
        "regime_name": "reserve",
        "instruction": "Resilience is the main priority. Keep meaningful battery reserve for future risk and avoid aggressive depletion.",
        "price": 0.03,
        "carbon_intensity": 0.40,
        "grid_stress": "medium",
        "load_peak_forecast": 0.9,
        "soc_avg": 0.34,
        "price_trend": "stable",
    }
    low_soc_cost_context = {
        "regime_name": "cost",
        "instruction": "Electricity price is the main priority. Reduce operating cost first, but keep the controller stable.",
        "price": 0.045,
        "carbon_intensity": 0.41,
        "grid_stress": "medium",
        "load_peak_forecast": 0.8,
        "soc_avg": 0.32,
        "price_trend": "rising",
    }
    high_soc_cost_context = dict(low_soc_cost_context)
    high_soc_cost_context["soc_avg"] = 0.45
    router.route(reserve_context)
    guarded = router.route(low_soc_cost_context)
    released = router.route(high_soc_cost_context)
    assert guarded["constraints"]["reserve_soc"] is not None
    assert guarded["constraints"]["reserve_soc"] >= 0.2
    assert released["constraints"]["reserve_soc"] in (None, 0.0)


def test_wrong_expert_corruption_drops_reserve_guard_in_reserve_regime():
    strategy = build_corrupted_strategy(
        {
            "regime_name": "reserve",
            "instruction": "Keep reserve for resilience.",
        },
        corruption_mode="wrong_expert",
    )
    assert strategy["constraints"]["reserve_soc"] is None
    assert strategy["weights"]["cost"] >= 0.65


def test_transition_wrong_expert_corruption_misroutes_carbon_regime():
    strategy = build_corrupted_strategy(
        {
            "regime_name": "carbon",
            "instruction": "Carbon reduction is the main priority.",
        },
        corruption_mode="transition_wrong_expert",
    )
    assert strategy["weights"]["cost"] >= 0.65
    assert strategy["weights"]["carbon"] <= 0.1


def test_reserve_drop_guard_corruption_only_removes_reserve_constraint():
    strategy = build_corrupted_strategy(
        {
            "regime_name": "reserve",
            "instruction": "Resilience is the main priority.",
        },
        corruption_mode="reserve_drop_guard",
    )
    assert strategy["constraints"]["reserve_soc"] is None
    assert strategy["weights"]["cost"] == 0.65


def test_carbon_misroute_corruption_forces_cost_heavy_profile():
    strategy = build_corrupted_strategy(
        {
            "regime_name": "carbon",
            "instruction": "Carbon reduction is the main priority.",
        },
        corruption_mode="carbon_misroute",
    )
    assert strategy["weights"]["cost"] == 0.65
    assert strategy["weights"]["carbon"] == 0.1


def test_summarize_routes_counts_corruption_and_fallback():
    summary = summarize_routes(
        [
            {
                "regime": "cost",
                "weights": {"cost": 0.4, "carbon": 0.2, "peak": 0.3, "smooth": 0.1},
                "constraints": {"reserve_soc": None},
                "corrupted": False,
                "fallback_used": False,
            },
            {
                "regime": "cost",
                "weights": {"cost": 0.6, "carbon": 0.1, "peak": 0.2, "smooth": 0.1},
                "constraints": {"reserve_soc": 0.2},
                "corrupted": True,
                "fallback_used": True,
            },
        ]
    )
    assert summary["cost"]["num_steps"] == 2
    assert summary["cost"]["num_corrupted"] == 1
    assert summary["cost"]["num_fallback_used"] == 1
    assert summary["cost"]["avg_reserve_soc"] == 0.2


def test_preference_score_prefers_lower_segment_metrics():
    load = np.array([1.0, 1.2, 0.8, 1.1], dtype=np.float32)
    prices = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32)
    carbon = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32)
    soc = np.array([0.4, 0.4, 0.4, 0.4], dtype=np.float32)
    regime = {
        "name": "cost",
        "instruction": "Cost first",
        "preference_vector": {"cost": 1.0, "carbon": 0.0, "peak": 0.0, "reserve": 0.0},
        "target_profile": {
            "weights": {"cost": 0.65, "carbon": 0.1, "peak": 0.15, "smooth": 0.1},
            "constraints": {"reserve_soc": None, "max_charge_rate": None},
        },
    }
    seg = compute_segment_metrics(load, prices, carbon, soc, 0, 4, regime)
    ref = compute_episode_kpis(load, prices, carbon)
    score = compute_preference_score(seg, ref)
    assert score > 0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
        except Exception as exc:
            print(f"FAIL: {test.__name__}: {exc}")
