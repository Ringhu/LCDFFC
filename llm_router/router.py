"""LLM-based preference router for dynamic weight/constraint selection."""

from __future__ import annotations

import time
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from llm_router.json_schema import DEFAULT_OUTPUT, parse_llm_json, validate_router_output
from llm_router.prompt_templates import build_prompt


class LLMRouter:
    """Prompt-only LLM router for high-level controller preferences."""

    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-0.5B-Instruct",
        backend: str = "transformers",
        temperature: float = 0.0,
        max_tokens: int = 192,
        device: str = "cpu",
        cache_by_instruction: bool = True,
    ):
        self.model_name = model_name
        self.backend = backend
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.device = device
        self.cache_by_instruction = cache_by_instruction
        self._model = None
        self._tokenizer = None
        self._cached_instruction: str | None = None
        self._cached_output: dict[str, Any] | None = None
        self._stats = {
            "num_calls": 0,
            "num_parse_failures": 0,
            "num_fallbacks": 0,
            "total_latency_sec": 0.0,
        }

    def _prepare_prompt_context(self, context: dict[str, Any]) -> dict[str, Any]:
        hour = int(context.get("hour", 0))
        if 0 <= hour < 6:
            time_of_day = "overnight"
        elif hour < 12:
            time_of_day = "morning"
        elif hour < 18:
            time_of_day = "afternoon"
        else:
            time_of_day = "evening"
        return {
            "instruction": str(context.get("instruction", "Maintain a balanced tradeoff.")),
            "time_of_day": time_of_day,
            "hour": hour,
            "day_type": int(context.get("day_type", 0)),
            "price": float(context.get("price", 0.0)),
            "price_trend": str(context.get("price_trend", "stable")),
            "carbon_intensity": float(context.get("carbon_intensity", 0.0)),
            "temperature": float(context.get("temperature", 0.0)),
            "soc": float(context.get("soc_avg", 0.5)),
            "grid_stress": str(context.get("grid_stress", "low")),
            "load_peak_forecast": float(context.get("load_peak_forecast", 0.0)),
        }

    def _lazy_load(self):
        if self._model is not None and self._tokenizer is not None:
            return
        if self.backend != "transformers":
            raise ValueError(f"Unsupported LLM backend: {self.backend}")
        dtype = torch.float16 if self.device.startswith("cuda") else torch.float32
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForCausalLM.from_pretrained(self.model_name, dtype=dtype)
        self._model.to(self.device)
        self._model.eval()

    def _normalize_strategy(self, strategy: dict[str, Any]) -> dict[str, Any]:
        strategy = validate_router_output(strategy)
        weights = dict(strategy["weights"])
        smooth = min(max(float(weights.get("smooth", DEFAULT_OUTPUT["weights"]["smooth"])), 0.05), 0.3)
        primary_total = max(weights["cost"] + weights["carbon"] + weights["peak"], 1e-8)
        scale = max(1.0 - smooth, 1e-8)
        weights["cost"] = scale * weights["cost"] / primary_total
        weights["carbon"] = scale * weights["carbon"] / primary_total
        weights["peak"] = scale * weights["peak"] / primary_total
        weights["smooth"] = smooth
        reserve_soc = strategy["constraints"].get("reserve_soc")
        if reserve_soc is not None:
            reserve_soc = min(max(float(reserve_soc), 0.0), 0.5)
        strategy["weights"] = weights
        strategy["constraints"]["reserve_soc"] = reserve_soc
        return strategy

    def route(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt_context = self._prepare_prompt_context(context)
        instruction = prompt_context["instruction"]
        if self.cache_by_instruction and instruction == self._cached_instruction and self._cached_output is not None:
            return self._cached_output

        messages = build_prompt(prompt_context)
        start = time.perf_counter()
        try:
            raw_text = self._call_llm(messages)
            parsed = parse_llm_json(raw_text)
            strategy = self._normalize_strategy(parsed)
        except Exception:
            self._stats["num_parse_failures"] += 1
            self._stats["num_fallbacks"] += 1
            strategy = self._normalize_strategy(DEFAULT_OUTPUT)
        self._stats["num_calls"] += 1
        self._stats["total_latency_sec"] += time.perf_counter() - start
        if self.cache_by_instruction:
            self._cached_instruction = instruction
            self._cached_output = strategy
        return strategy

    def _call_llm(self, messages: list[dict[str, str]]) -> str:
        self._lazy_load()
        prompt = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self._tokenizer(prompt, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        generate_kwargs = {
            "max_new_tokens": self.max_tokens,
            "do_sample": self.temperature > 0,
        }
        if self.temperature > 0:
            generate_kwargs["temperature"] = self.temperature
        with torch.no_grad():
            generated = self._model.generate(
                **inputs,
                **generate_kwargs,
            )
        new_tokens = generated[:, inputs["input_ids"].shape[1]:]
        return self._tokenizer.decode(new_tokens[0], skip_special_tokens=True)

    def get_stats(self) -> dict[str, Any]:
        return dict(self._stats)
