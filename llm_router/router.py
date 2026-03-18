"""LLM-based preference router for dynamic weight/constraint selection."""

from typing import Any

from llm_router.json_schema import validate_router_output
from llm_router.prompt_templates import build_prompt


class LLMRouter:
    """Routes context to controller weights and constraints via LLM.

    In v1 (prompt-only), calls a local LLM (e.g., Qwen2.5-7B via vLLM)
    to generate weight/constraint JSON given the current scenario context.

    Args:
        model_name: HuggingFace model name or vLLM endpoint.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens for LLM response.
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-7B-Instruct",
        temperature: float = 0.1,
        max_tokens: int = 256,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._model = None

    def route(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate controller weights and constraints from context.

        Args:
            context: Scenario context dict (time_of_day, weather, grid_status, etc.)

        Returns:
            {"weights": {"cost": float, ...}, "constraints": {...}}
        """
        # TODO: Implement LLM call and JSON parsing
        raise NotImplementedError("LLM router not yet implemented")

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM and return raw text response."""
        # TODO: Implement vLLM or transformers inference
        raise NotImplementedError("LLM inference not yet implemented")
