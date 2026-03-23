# LCDFFC — Claude Code Project Guide

## 1. Role of this file

This `CLAUDE.md` is the **main project document for Claude Code in this repository**.

Use it for stable, high-signal project guidance:
- what the repository currently does
- which paths are core vs experimental
- which commands and files matter most
- how documentation and code changes should be kept aligned

Do **not** turn this file into a dated experiment log or paper-facing narrative. Time-sensitive results, round summaries, and historical judgments should stay in `refine-logs/`, dated review docs, or dedicated docs under `docs/`.

If this file grows too large, split detailed guidance into imported files or `.claude/rules/` instead of expanding it indefinitely.

---

## 2. Source of truth

When project state is ambiguous, use this order:

1. **Code + tests** — implementation truth
2. **`CLAUDE.md`** — primary Claude Code project guide
3. **`README.md`** — external overview and runnable entrypoints
4. **`INSTRUCTION.md`** — staged plans, sprint flow, next-step sequencing
5. **dated reviews / `refine-logs/` / older specs** — historical research context only

If `CLAUDE.md` conflicts with code or tests, update `CLAUDE.md`.

---

## 3. Project snapshot

This repository is a research codebase for **CityLearn 2023 forecast-then-control**.

Current main executable path:

```text
CityLearn observation
  -> centralized history/features
  -> forecasting backbone or diagnostic forecast mode
  -> controller
  -> CityLearn env
```

The repository is **not** accurately described as:
- a GRU-only prototype
- a completed decision-focused training stack
- a production-grade LLM agent system

The most accurate stage label is:

> post-prototype, pre-consolidation research platform

---

## 4. Capability tiers

### 4.1 Core supported path

These are the most stable, repo-level supported capabilities:

- `data/prepare_citylearn.py` — CityLearn extraction and prepared forecast data generation
- `data/dataset.py` — sliding-window dataset and normalization stats
- `scripts/train_forecaster.py` — shared forecasting training entrypoint
- `models/factory.py` — unified forecaster construction
- `controllers/qp_controller.py` — main low-level QP battery controller
- `controllers/safe_fallback.py` — current conservative zero-action fallback
- `eval/run_controller.py` — main forecast + control evaluation runner
- `eval/run_controller.py --forecast_mode {learned,oracle,myopic}` — supported diagnostic modes

### 4.2 Supported experimental path

These exist in code and are supported enough to describe as experiments, not stable core:

- multi-backbone forecasting via `build_forecaster(...)`
- `llm_router/router.py` minimal prompt-only `LLMRouter.route()`
- `llm_router/preference_routers.py` heuristic/text preference routers
- `eval/run_preference_shift.py` preference-shift and event-driven experiments
- `eval/run_foundation_control.py` foundation forecast + controller evaluation
- `eval/run_foundation_controller_compare.py` controller-family comparison
- `controllers/baseline_controllers.py` non-QP controller baselines

### 4.3 Planned / partial path

Do not document these as completed:

- full `SPO+` / decision-focused end-to-end training
- uncertainty-aware ensemble / gating full path
- deterministic-fallback-complete LLM routing
- RL baseline
- full OOD evaluation loop

Notes:
- `QPController.solve_with_cost_vector(...)` is only a partial interface clue for decision-focused work.
- `LLMRouter.route()` is implemented, but only as a minimal prompt-only router.

---

## 5. Architecture and interfaces

### Forecasting

`models/factory.py` is the canonical forecaster entrypoint.

Currently supported model types in code:
- `gru`
- `tsmixer`
- `patchtst`
- `transformer`
- `granite_patchtst`

`tests/test_forecaster_factory.py` confirms factory instantiation and forward-shape support. It does **not** by itself prove equal end-to-end maturity for all backbones.

### Controller

`controllers/qp_controller.py` is the main controller contract.

Key interface shape:

```python
QPController.act(state, forecast, weights, constraints=None, carbon_intensity=None)
```

Working assumptions:
- forecast columns are centered on `[price, load, solar]`
- optimization weights use `cost / carbon / peak / smooth`
- constraints may include `reserve_soc` and `max_charge_rate`
- solver failure falls back through `SafeFallback`

### Router

`llm_router/router.py` provides a minimal high-level preference router.

Key interface shape:

```python
LLMRouter.route(context) -> {"weights": ..., "constraints": ..., "mode": ...?}
```

Interpretation rules:
- router outputs high-level preferences/constraints, not continuous actions
- bad JSON falls back to a default normalized profile
- current implementation is experimental and not production-grade

### Baseline clarification

`eval/run_rbc.py` should currently be described as a **zero-action / default-building-behavior baseline runner**, not as a fully implemented repository-owned RBC policy.

---

## 6. Important commands

Common commands Claude should prefer when checking repo behavior:

```bash
python tests/test_smoke.py
python tests/test_forecaster_factory.py
python tests/test_run_controller_modes.py
python tests/test_controller_baselines.py
python tests/test_preference_shift.py
```

Main runners:

```bash
python scripts/train_forecaster.py --config configs/forecast.yaml --data_path artifacts/forecast_data.npz --device cpu
python eval/run_rbc.py --schema citylearn_challenge_2023_phase_1 --output_dir reports/
python eval/run_controller.py --schema citylearn_challenge_2023_phase_1 --forecast_config configs/forecast.yaml --controller_config configs/controller.yaml --output_dir reports/ --tag forecast_qp
```

Use GPU 2 for training/inference when GPU execution is needed.

---

## 7. Module map

- `data/` — extraction, features, datasets, normalization
- `models/` — forecasting backbones and factory
- `controllers/` — QP control, fallback, controller baselines
- `eval/` — core evaluation, diagnostics, comparison runners
- `llm_router/` — prompt/schema/router and preference routing experiments
- `scripts/` — training and helper entrypoints
- `tests/` — behavior boundaries and regression checks
- `configs/` — YAML configuration
- `artifacts/` — prepared data, checkpoints, norm stats
- `reports/` — KPI tables, outputs, evaluation reports

---

## 8. Documentation rules

When updating docs:
- keep `CLAUDE.md` focused on stable Claude Code project guidance
- keep `README.md` focused on overview and runnable entrypoints
- keep `INSTRUCTION.md` focused on stage plans and execution order
- keep dated findings in `docs/` or `refine-logs/`, not here

When writing new claims:
- separate **implemented**, **experimental**, and **planned**
- do not promote experiment scripts into core capabilities without evidence
- do not state "passed RBC" as a permanent repo fact unless backed by stable, reproducible acceptance artifacts
- do not describe the router as agentic or production-ready

---

## 9. Coding and change conventions

- Follow PEP 8.
- Use type hints on public functions.
- Keep docstrings concise.
- Prefer updating existing files over creating new ones.
- Keep hyperparameters in `configs/*.yaml` rather than hard-coding them.
- Add or update focused tests when changing supported interfaces.
- Treat documentation drift as a real bug: update `CLAUDE.md` when stable repo behavior changes.

---

## 10. Validation contract

Minimum validation expectations:
- `tests/test_smoke.py` for baseline smoke coverage
- `tests/test_qp.py` for controller-path validation when `cvxpy` is available
- focused tests for any changed runner, factory, router, or controller behavior

Important rule:

> implementation exists != acceptance is complete

A shape test, a unit test, or a single experiment script is not enough to claim full maturity.
