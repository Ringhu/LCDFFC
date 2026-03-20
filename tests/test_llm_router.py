"""Tests for the prompt-only LLM router wrapper."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llm_router.router import LLMRouter


class DummyLLMRouter(LLMRouter):
    def __init__(self, responses):
        super().__init__(model_name='dummy', backend='transformers', device='cpu')
        self._responses = list(responses)

    def _lazy_load(self):
        return

    def _call_llm(self, messages):
        return self._responses.pop(0)


def test_llm_router_normalizes_weights_and_clamps_constraints():
    router = DummyLLMRouter([
        '{"weights": {"cost": 0.4, "carbon": 0.4, "peak": 0.4, "smooth": 0.2}, "constraints": {"reserve_soc": 0.9, "max_charge_rate": null}}'
    ])
    result = router.route({"instruction": 'carbon first', "hour": 12})
    assert abs(sum(result['weights'].values()) - 1.0) < 1e-6
    assert result['constraints']['reserve_soc'] == 0.5


def test_llm_router_caches_by_instruction():
    router = DummyLLMRouter([
        '{"weights": {"cost": 0.5, "carbon": 0.2, "peak": 0.2, "smooth": 0.1}, "constraints": {"reserve_soc": null, "max_charge_rate": null}}'
    ])
    ctx = {"instruction": 'peak first', "hour": 18}
    first = router.route(ctx)
    second = router.route(dict(ctx, price=0.05))
    assert first == second
    assert router.get_stats()['num_calls'] == 1


def test_llm_router_falls_back_on_bad_json():
    router = DummyLLMRouter(['not json'])
    result = router.route({"instruction": 'balanced', "hour": 9})
    assert abs(sum(result['weights'].values()) - 1.0) < 1e-6
    assert router.get_stats()['num_fallbacks'] == 1
