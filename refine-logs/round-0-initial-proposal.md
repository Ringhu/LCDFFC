# Research Proposal: LCDFFC Current Broad Idea (Round 0)

## Problem Anchor
- Bottom-line problem:
  Build a publishable method for exogenous time-series-driven energy control where future price, carbon, and load variation matter for decision quality.
- Must-solve bottleneck:
  Fixed controllers and reward-specific policies do not adapt gracefully when operator preferences or external conditions shift, and pure forecast accuracy does not guarantee better downstream control.
- Non-goals:
  Not trying to build a general-purpose building foundation model, a full RL stack, or an LLM that directly outputs low-level continuous actions.
- Constraints:
  Current codebase is centered on CityLearn 2023 with a working `forecast + QP` loop. Compute appears modest. The first paper must be implementable on top of the current repo rather than requiring a full reset.
- Success condition:
  A method that is clearly more paper-worthy than a tuned baseline, shows why time-series prediction matters for control, and provides a clean novelty story that can survive top-venue scrutiny.

## Technical Gap

The current repository and planning docs implicitly bundle several ideas:

1. fixed-weight forecast + QP control
2. uncertainty-aware fallback
3. decision-focused training
4. LLM preference routing
5. optional Grid2Op transfer

That stack is directionally sensible, but it is too wide for one paper. As written, it does not yet isolate one dominant contribution. The codebase today mainly demonstrates:

- a GRU forecaster
- a QP controller
- a CityLearn evaluation path
- prompt/schema scaffolding for a future LLM router

This means the current broad idea risks becoming "forecast + optimizer + uncertainty + DFL + LLM" without a single crisp mechanism claim.

## Method Thesis

The current broad thesis can be paraphrased as:

"Use time-series forecasting to improve low-level battery control, then extend the controller with uncertainty handling, decision-focused learning, and language-conditioned preference routing so the same system can adapt to changing high-level objectives."

This is directionally attractive but methodologically unstable as a paper thesis because it contains multiple plausible papers.

## Contribution Focus
- Dominant contribution:
  Not yet singular. The proposal currently mixes at least three candidate dominant contributions:
  - decision-focused forecast-control
  - uncertainty-aware robust control
  - language-conditioned dynamic preference routing
- Optional supporting contribution:
  Cross-environment transfer to Grid2Op.
- Explicit non-contributions:
  General building automation, end-to-end RL, and full LLM control are not intended.

## Proposed Method (Current Broad Version)

### Complexity Budget
- Frozen / reused backbone:
  CityLearn environment, 9-D forecast feature extraction, GRU forecaster, QP low-level controller.
- New trainable components:
  Possibly uncertainty ensemble, possibly decision-focused objective, possibly LLM router.
- Tempting additions intentionally not used:
  LLM direct action output and large-scale RL are already excluded in docs.

### System Overview

```text
CityLearn observations
  -> feature extraction
  -> GRU forecasting
  -> QP control
  -> optional uncertainty gate
  -> optional LLM preference router
  -> battery action
  -> CityLearn rollout
```

### Core Mechanism

At present, the code does not yet implement a complete mechanism beyond fixed-weight forecast + QP. The current broad idea imagines:

- forecast the future
- use optimization for low-level control
- let language specify dynamic high-level control intent
- optionally train the predictor in a decision-focused way

### Modern Primitive Usage

The intended LLM role is high-level and structured:

- input: compact scenario summary
- output: `weights / constraints / mode`
- not allowed: direct continuous control

This is a healthier placement than LLM direct action, but it remains only partially specified and unimplemented.

### Training Plan

The current broad plan implies multiple stages:

1. train GRU with MSE
2. possibly add decision-focused loss
3. possibly add uncertainty estimation
4. possibly add LLM routing

### Failure Modes and Diagnostics
- Contribution drift:
  The paper story becomes "many ingredients added together" instead of one mechanism.
- Novelty dilution:
  The fixed-weight `forecast + QP` system alone is not novel enough for a top venue.
- Validation ambiguity:
  If performance improves, it may be unclear whether the gain comes from forecasting, optimization tuning, uncertainty handling, or language routing.

### Novelty and Elegance Argument

In its current broad form, the idea is promising but not elegant enough. It is better viewed as a research program than as a single paper.

## Claim-Driven Validation Sketch

### Claim 1
Language-conditioned high-level adaptation improves multi-objective sequential control without retraining the low-level controller.

- Minimal experiment:
  Compare fixed weights vs language-routed weights under preference shifts.
- Baselines / ablations:
  fixed weights, heuristic rule router, structured numeric preference router.
- Metric:
  KPI regret under changing preference regimes.
- Expected evidence:
  Better adaptation to preference shifts.

### Claim 2
Decision-focused or uncertainty-aware training improves robustness of forecast-control.

- Minimal experiment:
  Compare MSE-only vs decision-focused or uncertainty-gated variants.
- Baselines / ablations:
  MSE forecast + QP, uncertainty gate off, DFL off.
- Metric:
  cost/carbon/peak under OOD or preference-shift settings.
- Expected evidence:
  More stable downstream control.

## Experiment Handoff Inputs
- Must-prove claims:
  adaptation without retraining, genuine downstream value of the added module, and top-venue-worthy novelty.
- Must-run ablations:
  no LLM, heuristic router, numeric router, fixed weights, possibly no uncertainty or no DFL.
- Critical datasets / metrics:
  CityLearn 2023 with cost/carbon/peak, preference-shift episodes, OOD variants.
- Highest-risk assumptions:
  That the LLM routing layer is necessary and not replaceable by a much simpler structured module.

## Compute & Timeline Estimate
- Estimated GPU-hours:
  modest for GRU, modest-to-moderate for ablations, unknown for any local LLM fine-tuning.
- Data / annotation cost:
  potentially low if language preferences are templated synthetically.
- Timeline:
  feasible for a staged prototype, but too broad for one clean first paper.
