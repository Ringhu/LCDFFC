"""Generate synthetic instruction-tuning data for the LLM router.

Creates scenario-response pairs for LoRA fine-tuning.

Usage:
    python scripts/generate_instruction_data.py --num_samples 1000 --output artifacts/instruction_data.jsonl
"""

import argparse
import json
import random
from pathlib import Path


def generate_scenario() -> dict:
    """Generate a random building energy scenario."""
    hour = random.randint(0, 23)
    return {
        "time_of_day": "night" if hour < 6 or hour >= 22 else ("morning" if hour < 12 else ("afternoon" if hour < 18 else "evening")),
        "hour": hour,
        "day_type": random.choice(["weekday", "weekend"]),
        "price": round(random.uniform(0.05, 0.50), 3),
        "price_trend": random.choice(["rising", "falling", "stable", "peak_coming"]),
        "carbon_intensity": round(random.uniform(100, 800), 1),
        "temperature": round(random.uniform(-5, 40), 1),
        "soc": round(random.uniform(0.0, 1.0), 2),
        "grid_stress": random.choice(["low", "medium", "high", "critical"]),
    }


def generate_response(scenario: dict) -> dict:
    """Generate a reasonable control strategy for a given scenario."""
    weights = {"cost": 0.25, "carbon": 0.25, "peak": 0.25, "smooth": 0.25}
    constraints = {"reserve_soc": None, "max_charge_rate": None}

    if scenario["price"] > 0.30 or scenario["price_trend"] == "peak_coming":
        weights["cost"] = 0.5
        weights["carbon"] = 0.15
        weights["peak"] = 0.25
        weights["smooth"] = 0.1

    if scenario["carbon_intensity"] > 500:
        weights["carbon"] = max(weights["carbon"], 0.4)
        weights["cost"] = min(weights["cost"], 0.2)

    if scenario["grid_stress"] in ("high", "critical"):
        weights["peak"] = 0.5
        constraints["reserve_soc"] = 0.3
        weights["cost"] = 0.2
        weights["carbon"] = 0.15
        weights["smooth"] = 0.15

    return {"weights": weights, "constraints": constraints}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_samples", type=int, default=1000)
    parser.add_argument("--output", type=str, default="artifacts/instruction_data.jsonl")
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    with open(args.output, "w") as f:
        for _ in range(args.num_samples):
            scenario = generate_scenario()
            response = generate_response(scenario)
            record = {"input": scenario, "output": response}
            f.write(json.dumps(record) + "\n")

    print(f"Generated {args.num_samples} samples to {args.output}")


if __name__ == "__main__":
    main()
