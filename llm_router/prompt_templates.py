"""Prompt templates for the LLM preference router."""

SYSTEM_PROMPT = """You are an energy management advisor for a smart building district.
Given the current scenario context, you must decide the control strategy by outputting
a JSON object with objective weights and optional constraints.

Output format (JSON only, no explanation):
{
  "weights": {
    "cost": <float 0-1>,
    "carbon": <float 0-1>,
    "peak": <float 0-1>,
    "smooth": <float 0-1>
  },
  "constraints": {
    "reserve_soc": <float 0-1 or null>,
    "max_charge_rate": <float 0-1 or null>
  }
}

Guidelines:
- During peak pricing hours, increase "cost" weight
- During high carbon intensity, increase "carbon" weight
- When grid is stressed, increase "peak" weight and set reserve_soc > 0.2
- Weights should sum to approximately 1.0
- Set constraint values to null if no special constraint needed"""

USER_TEMPLATE = """Current scenario:
- Time: {time_of_day} (hour {hour})
- Day type: {day_type}
- Current electricity price: {price} $/kWh
- Price trend (next 6h): {price_trend}
- Carbon intensity: {carbon_intensity} gCO2/kWh
- Outdoor temperature: {temperature} °C
- Current SOC: {soc}
- Grid stress level: {grid_stress}

Output the JSON control strategy:"""


def build_prompt(context: dict) -> list[dict[str, str]]:
    """Build chat-format prompt from context dict.

    Args:
        context: Scenario context with keys matching USER_TEMPLATE placeholders.

    Returns:
        List of {"role": ..., "content": ...} messages.
    """
    user_msg = USER_TEMPLATE.format(**context)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]
