# Research Proposal: Forecast-Control Misalignment and Control-Aware Model Selection

## Problem Anchor

- Bottom-line problem: Average forecast metrics (MSE/MAE) are unreliable proxies for downstream control quality in forecast-then-control systems
- Must-solve bottleneck: Model selection by forecast accuracy can pick the wrong model for control
- Non-goals: Not proposing a new forecasting architecture; not claiming LLM routing is the main contribution
- Constraints: CityLearn 2023, single GPU, ~100 GPU-hours budget
- Success condition: CAVS selects models that produce better control KPIs than MSE/MAE selection

## Technical Gap

Forecast-then-control is the dominant paradigm in building energy management: train a forecaster, freeze it, feed predictions to a downstream controller. Model selection universally uses average forecast accuracy (MSE or MAE on held-out windows).

Evidence from our existing experiments shows this is unreliable:

1. GRU wins forecast MSE but loses to zero-shot foundation models (Moirai2, TimesFM2.5) on control KPIs (cost, carbon)
2. Replay-prior CSFT improves forecast MAE (0.282 vs 0.364) but slightly worsens control KPIs vs uniform training
3. Input-oracle (perfect future knowledge) does not yield the best control outcome either
4. Foundation models achieve ~8% cost improvement and ~7% carbon improvement over best trained model, despite higher forecast error on some channels

The root cause: the controller is a QP that weights channels and horizons non-uniformly. Errors on price-sensitive hours matter more than errors on flat periods. Average metrics treat all errors equally.

The predict-then-optimize literature (NeurIPS 2024 Directional Gradients, AAAI 2025 DFF) recognizes this gap but focuses on end-to-end training. We address the simpler, more practical question: can we at least *select* the right model without retraining?

## Method Thesis

- One-sentence thesis: Controller-aware validation score (CAVS) is a better model selection criterion than forecast accuracy for downstream control
- Why smallest adequate intervention: CAVS is just a scoring function applied post-hoc to existing model outputs — no new model architecture, no retraining, no end-to-end gradient
- Why timely: predict-then-optimize is an active frontier; model selection is the lowest-cost entry point that practitioners can adopt immediately

## Contribution Focus

- Dominant contribution: CAVS metric + systematic diagnosis of forecast-control misalignment across multiple scenarios, seeds, and model families
- Supporting contribution: Decision-focused fine-tuning (CSFT variant) for trainable backbones, using CAVS-derived sensitivity as training signal
- Explicit non-contributions: LLM routing (optional extension only, not part of main claims)

## Proposed Method

### CAVS Definition

CAVS scores a forecaster by weighting its errors according to controller sensitivity:

```
CAVS(f) = mean_i mean_{h,c} [ s(h,c) * |ŷ_f(i,h,c) - y(i,h,c)| ]
```

where `s(h,c)` is the controller sensitivity at horizon `h` and channel `c`.

**Version 1 — CAVS-global (fast):** Reuse a pre-computed sensitivity map `G(h,c)` from perturbation analysis on oracle forecasts:

```
CAVS-global(f) = mean_i mean_{h,c} [ G(h,c) * |ŷ_f(i,h,c) - y(i,h,c)| ]
```

`G(h,c)` is computed once by perturbing each (channel, horizon) cell of the oracle forecast and measuring KPI change through the QP.

**Version 2 — CAVS-local (stronger):** Per-window perturbation sensitivity:

```
s_i(h,c) = |J(F_i + δe_{hc}) - J(F_i - δe_{hc})| / (2δ)
```

where `J` is the QP objective value and `e_{hc}` is the unit perturbation at position (h,c).

### Integration with Existing Pipeline

CAVS plugs into the existing stack without modification:
1. Run each candidate model through `eval/run_controller.py` to get KPIs
2. Compute CAVS from forecast errors + sensitivity map
3. Select the model with lowest CAVS (or best CAVS-derived KPI prediction)
4. Compare against MSE/MAE selection

### Relation to CSFT

The sensitivity map `G(h,c)` that CAVS uses for evaluation can also serve as a training signal. This salvages the CSFT line: sensitivity is more reliable for evaluation/model-selection than for direct weighted training, but the weights themselves are reusable.

## Claim-Driven Validation Sketch

### Claim 1: Forecast-control misalignment is systematic

- Evidence needed: rank reversals between forecast metrics and control KPIs across 5 CityLearn 2023 scenarios, multiple model families (GRU, TSMixer, Moirai2, TimesFM2.5), 3 seeds
- Quantification: Spearman/Kendall rank correlation between MSE ranking and KPI ranking
- Threshold: correlation < 0.7 in majority of scenarios

### Claim 2: CAVS selects better models than MSE/MAE

- Evidence needed: CAVS-selected model produces better control KPIs than MSE-selected model
- Quantification: KPI improvement (cost, carbon, peak) of CAVS-selected vs MSE-selected model
- Threshold: improvement on at least 2 of 3 primary KPIs in majority of scenarios

## Experiment Handoff Inputs

- Must-prove claims: H1 (misalignment is systematic), H2 (CAVS > MSE selection)
- Must-run ablations: perturbation sensitivity analysis, multi-scenario replication, seed variance
- Critical datasets: CityLearn 2023 phase_1 through phase_3 (5 scenarios)
- External validation: CityLearn 2022 family (3 scenarios)
- Highest-risk assumptions: misalignment may shrink after oracle cleanup; CAVS advantage may be small if all models have similar error patterns

## Compute & Timeline Estimate

| Component | GPU-hours |
|-----------|-----------|
| E01: Lock stack / baselines | 6 |
| E02: Train specialists (GRU, TSMixer; 5 scenarios; 3 seeds) | 40 |
| E03: FM sweep (Moirai2, TimesFM2.5; 5 scenarios) | 10 |
| E04-E05: Leaderboard + rank correlation | 1 |
| E06: Oracle semantics | 4 |
| E07: Perturbation sensitivity | 8 |
| E08: Event-critical error analysis | 1 |
| E09: CAVS validation | 4 |
| E10: External transfer (2022) | 20 |
| **Total** | **~94** |
| **Minimum viable (without E10)** | **~63** |
