# LCDFFC — Language-Conditioned Decision-Focused Forecast-Control

## Project Overview

This repository is currently centered on the first usable closed loop for CityLearn 2023:

- GRU forecaster trained from historical observations
- fixed-weight QP controller for battery-only control
- end-to-end evaluation against the `RBC` baseline

Later stages such as `SPO+`, uncertainty-aware control, and the LLM router remain part of the research roadmap, but they are not yet implemented as production-ready features in this codebase.

## Current Architecture

Current executable path:

```text
Raw observations -> GRU forecaster -> QP controller -> CityLearn env
```

Planned later-stage path:

```text
Raw observations -> GRU forecaster -> QP controller -> CityLearn env
                         ^                  ^
                         |                  |
                   SPO+ training      LLM preference routing
```

## Module Ownership

| Module | Path | Responsibility |
|--------|------|---------------|
| Data | `data/` | CityLearn data extraction, dataset/dataloader |
| Forecast | `models/` | Time-series forecasters and forecast training |
| Controller | `controllers/` | QP control and safe fallback |
| Eval | `eval/` | RBC baseline, end-to-end evaluation, metrics, KPI reporting |
| LLM Router | `llm_router/` | Prompt templates, JSON schema, router implementation skeleton |

## Tech Stack

- **Python 3.10+**
- **CityLearn 2.1+** with `central_agent=True`
- **PyTorch** for forecaster training
- **cvxpy** with **OSQP** for QP solving
- **YAML** configs in `configs/*.yaml`
- **vLLM / transformers** only when the LLM router stage is actually enabled

## Coding Conventions

### Style
- Follow PEP 8. Use type hints on all public functions.
- Docstrings: Google style, keep them concise.
- Max line length: 100 characters.

### Module Boundaries
- Each module exposes its API through `__init__.py`.
- Cross-module imports go through the public API only.
- Never import internal helpers from another module.

### Key Interfaces

```python
# Controller interface (controllers/qp_controller.py)
class QPController:
    def act(self, state: dict, forecast: np.ndarray,
            weights: dict, constraints: dict) -> np.ndarray: ...

# LLM Router interface (llm_router/router.py)
class LLMRouter:
    def route(self, context: dict) -> dict:
        """Returns {"weights": {...}, "constraints": {...}, "mode": "..."}"""
```

Notes:

- `QPController` is implemented and used by `eval/run_controller.py`.
- `LLMRouter.route()` is not implemented yet and must not be documented elsewhere as an available runtime feature.
- A deterministic fallback is required before the LLM router can be considered usable.

### Config

- Keep hyperparameters in `configs/*.yaml`, not hard-coded in source files.
- Use `yaml.safe_load()` for config loading.
- Configs should use real built-in dataset identifiers or valid local paths; do not keep stale placeholder paths.

### Testing

- `tests/test_smoke.py` is the minimum baseline check.
- `tests/test_qp.py` is the controller-path check and depends on `cvxpy`.
- Each module should gain its own focused tests as the implementation matures.

### Git
- Commit messages: `<module>: <imperative verb> <description>`
  - Example: `forecast: add GRU training loop with teacher forcing`
- One logical change per commit.

## Current Phase

1. **Sprint 0**: Project scaffolding — done
2. **Sprint 1**: Data pipeline + GRU forecaster — largely done
3. **Sprint 2**: QP controller + RBC baseline + end-to-end eval — code mostly done, acceptance not passed
4. **Sprint 3**: SPO+ decision-focused loss integration — not started
5. **Sprint 4**: LLM router — prompt/schema skeleton only
6. **Sprint 5**: Ablation and paper writing — not started

## Important Notes

- CityLearn uses `central_agent=True`; the current setup assumes a shared central controller.
- The immediate target is to beat or tie `RBC` with fixed weights before adding more research modules.
- QP solver numerical stability matters; prefer OSQP with warm-starting.
- Reports go to `reports/`, trained model checkpoints and prepared data go to `artifacts/`.
