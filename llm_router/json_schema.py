"""JSON schema definition and validation for LLM router output."""

import json

ROUTER_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["weights"],
    "properties": {
        "weights": {
            "type": "object",
            "required": ["cost", "carbon", "peak", "smooth"],
            "properties": {
                "cost": {"type": "number", "minimum": 0, "maximum": 1},
                "carbon": {"type": "number", "minimum": 0, "maximum": 1},
                "peak": {"type": "number", "minimum": 0, "maximum": 1},
                "smooth": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        "constraints": {
            "type": "object",
            "properties": {
                "reserve_soc": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                "max_charge_rate": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
            },
        },
    },
}

DEFAULT_OUTPUT = {
    "weights": {"cost": 0.4, "carbon": 0.2, "peak": 0.3, "smooth": 0.1},
    "constraints": {"reserve_soc": None, "max_charge_rate": None},
}


def validate_router_output(output: dict) -> dict:
    """Validate and sanitize LLM router output.

    Falls back to defaults for missing or invalid fields.

    Args:
        output: Parsed JSON dict from LLM.

    Returns:
        Validated output dict.
    """
    result = {"weights": {}, "constraints": {}}

    weights = output.get("weights", {})
    for key in ("cost", "carbon", "peak", "smooth"):
        val = weights.get(key, DEFAULT_OUTPUT["weights"][key])
        if isinstance(val, (int, float)) and 0 <= val <= 1:
            result["weights"][key] = float(val)
        else:
            result["weights"][key] = DEFAULT_OUTPUT["weights"][key]

    constraints = output.get("constraints", {})
    for key in ("reserve_soc", "max_charge_rate"):
        val = constraints.get(key, None)
        if val is None or (isinstance(val, (int, float)) and 0 <= val <= 1):
            result["constraints"][key] = float(val) if val is not None else None
        else:
            result["constraints"][key] = None

    return result


def parse_llm_json(text: str) -> dict:
    """Extract and parse JSON from LLM text output.

    Handles cases where JSON is wrapped in markdown code blocks.

    Args:
        text: Raw LLM output string.

    Returns:
        Parsed and validated dict.
    """
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    parsed = json.loads(text)
    return validate_router_output(parsed)
