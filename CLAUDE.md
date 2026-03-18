# LCDFFC — Language-Conditioned Decision-Focused Forecast-Control

## Project Overview

This project implements a **forecast-then-control** system for the CityLearn Challenge 2023, enhanced with:
- **Decision-focused learning** (SPO+ surrogate) so forecasts serve downstream control
- **LLM preference router** (Qwen2.5-7B-Instruct) for high-level constraint/weight selection
- **QP-based MPC** (cvxpy) with receding horizon (24-step plan, execute first action)

Target venue: CCF-A conference (NeurIPS / ICML / AAAI).

## Architecture

```
LLM Router (Qwen2.5-7B) ──► weights / constraints
                                    │
Raw observations ──► GRU Forecaster ──► QP Controller ──► CityLearn env
                         ▲                    │
                         └── SPO+ loss ◄──────┘
```

Five modules, each independently owned by a sub-agent:

| Module | Path | Responsibility |
|--------|------|---------------|
| Data | `data/` | CityLearn data extraction, dataset/dataloader |
| Forecast | `models/` | Time-series forecasters (GRU → TSMixer/PatchTST) |
| Controller | `controllers/` | QP/MPC via cvxpy, safe fallback |
| Eval | `eval/` | Baselines (RBC, RL), metrics, KPI reporting |
| LLM Router | `llm_router/` | Prompt templates, JSON schema, router logic |

## Tech Stack

- **Python 3.10+**
- **CityLearn 2.1+** with `central_agent=True`
- **PyTorch** for forecaster training
- **cvxpy** for QP solving (OSQP backend)
- **vLLM or transformers** for local LLM inference
- **Hydra / OmegaConf** style configs in `configs/*.yaml`

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
# Forecaster interface (models/base_forecaster.py)
class BaseForecaster:
    def predict(self, history: Tensor, horizon: int) -> Tensor: ...
    def train_step(self, batch, loss_fn) -> dict: ...

# Controller interface (controllers/qp_controller.py)
class QPController:
    def act(self, state: dict, forecast: np.ndarray,
            weights: dict, constraints: dict) -> np.ndarray: ...

# LLM Router interface (llm_router/router.py)
class LLMRouter:
    def route(self, context: dict) -> dict:
        """Returns {"weights": {...}, "constraints": {...}}"""
```

### Config
- All hyperparameters live in `configs/*.yaml`, not in source code.
- Use `yaml.safe_load()` for config loading.

### Testing
- Smoke tests in `tests/test_smoke.py` — must pass before any PR.
- Each module should have its own test file as it matures.

### Git
- Commit messages: `<module>: <imperative verb> <description>`
  - Example: `forecast: add GRU training loop with teacher forcing`
- One logical change per commit.

## Sprint Plan (see INSTRUCTION.md for details)

1. **Sprint 0**: Project scaffolding (this step)
2. **Sprint 1**: Data pipeline + GRU forecaster + standard MSE training
3. **Sprint 2**: QP controller + RBC baseline + end-to-end eval
4. **Sprint 3**: SPO+ decision-focused loss integration
5. **Sprint 4**: LLM router (prompt-only) + synthetic instruction data
6. **Sprint 5**: Ablation, paper writing

## Important Notes

- CityLearn uses `central_agent=True` mode — all buildings share one agent.
- QP solver numerical stability matters for SPO+ perturbation — use OSQP with warm-starting.
- The LLM is prompt-only in v1; LoRA fine-tuning is a stretch goal.
- Reports go to `reports/`, trained model checkpoints to `artifacts/`.
