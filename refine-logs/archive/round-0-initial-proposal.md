# Research Proposal: Controller-Calibrated Forecast Training After Preflight Failure

## Problem Anchor
- Bottom-line problem:
  Build a publishable method for exogenous time-series-driven control where forecast training improves downstream control KPIs rather than only average forecast error.
- Must-solve bottleneck:
  In forecast-then-control pipelines, the controller only cares about a small subset of future windows and channels, but the current raw per-sample slot-wise CSFT labels are too sparse and unstable to serve as useful supervision. The latest numerical preflight shows that raw-CSFT still loses even on the top-sensitivity cells it claims to prioritize.
- Non-goals:
  Not scaling the raw slot-wise CSFT route, not introducing a new controller, not moving to end-to-end RL, not adding language/routing components, and not keeping a paper thesis that the current evidence has already falsified.
- Constraints:
  Start from the current CityLearn + GRU + fixed `qp_carbon` stack; use modest compute; use GPU 2 only for training/inference; prefer one new trainable route with low engineering overhead; reuse existing artifacts and diagnostics.
- Success condition:
  The next route should produce a lower-entropy, controller-derived weighting signal that is stable enough to beat raw-CSFT, match or beat the strongest simple heuristic baseline, and show at least early improvement on control-critical error and control KPIs.

## Technical Gap
The recent preflight changes the conclusion sharply.

- **R201 passes**: oracle alignment is exact, so oracle path mismatch is not the main explanation.
- **R202 fails**: raw-CSFT top-decile MAE is worse than uniform by 5.46%, which exceeds the allowed 5% threshold.

This means the raw slot-wise finite-difference sensitivity signal is not just noisy in aggregate; it is already failing on the cells where it should help most. The dominant problem is therefore not “how to soften raw weights a bit more,” but “how to compress controller relevance into a lower-variance supervision target.”

Naive fixes are insufficient:
- More seeds on raw-CSFT would only make a falsified route more expensive.
- A single softened operator after a failed utility gate is hard to defend as a paper path.
- Broader backbone/controller sweeps would not solve the supervision entropy problem.

The smallest adequate pivot is to stop using per-sample raw slot weights, and instead distill controller relevance into a **global controller-calibrated weight prior** over horizon × channel. This preserves the fixed-controller thesis while removing the sample-wise sparsity that appears to break raw-CSFT.

## Method Thesis
- One-sentence thesis:
  When per-sample controller sensitivities are too sparse to supervise forecasting directly, aggregate them across the training set into a stable controller-calibrated horizon×channel prior, and train against that low-entropy prior instead of raw sample-wise weights.
- Why this is the smallest adequate intervention:
  It keeps the same fixed controller, same forecasting backbone, same inference path, and same offline sensitivity machinery; only the supervision target changes from high-variance per-sample weights to one fixed controller-derived prior.
- Why this route is timely in the foundation-model era:
  The bottleneck is supervision stability, not representation size. A compact controller-derived prior is a cleaner answer than a bigger model or more complicated optimization stack.

## Contribution Focus
- Dominant contribution:
  A controller-calibrated forecast training recipe that compresses raw finite-difference sensitivities into a stable global horizon×channel weight prior.
- Optional supporting contribution:
  A formal preflight-based falsification criterion for raw slot-wise controller-sensitive supervision.
- Explicit non-contributions:
  No new controller, no full decision-focused training, no LLM/RL components, no multi-environment transfer, and no large family of weighting variants.

## Proposed Method
### Complexity Budget
- Frozen / reused backbone:
  Current GRU forecaster, CityLearn dataset path, chronological split, fixed `qp_carbon` controller, existing raw sensitivity generation code, and existing baseline checkpoints.
- New trainable components:
  None.
- Tempting additions intentionally not used:
  Per-sample stabilized-CSFT, bucket search, routing/fallback stacks, multi-backbone sweeps, end-to-end differentiable control.

### System Overview
```text
raw finite-difference sensitivities on train split
  -> aggregate across samples into stable horizon×channel prior G[h,c]
  -> normalize / quantize once
  -> broadcast prior to all training samples
  -> mixed weighted forecast loss
  -> forecast -> qp_carbon -> CityLearn
```

### Core Mechanism
- Input / output:
  Same forecasting inputs and outputs as the current GRU setup.
- Representation design:
  Replace sample-specific weights `w_(t,h,c)` with a global controller-calibrated prior `G_(h,c)` learned once from train-split raw sensitivities.
- Prior construction:
  1. Compute raw train sensitivities `s_(t,h,c)` as before.
  2. Clip each value at train-set q95.
  3. Apply `log1p` compression.
  4. Aggregate across samples:
     `G_(h,c) = mean_t log1p(min(s_(t,h,c), q95) / (m_train + eps))`
  5. Normalize `G` so its mean over `(h,c)` is 1.
- Training signal / loss:
  Broadcast `G` to every sample and use the same mixed Huber objective:
  `L_t = alpha * sum Huber(yhat, y) + (1-alpha) * sum G_(h,c) * Huber(yhat_(t,h,c), y_(t,h,c))`
- Why this is the main novelty:
  The method directly answers the preflight failure: raw controller relevance is too high-entropy to train on directly, but its low-rank/global structure may still be usable.

### Optional Supporting Component
- Only include if truly necessary:
  A binarized version of the global prior, where only the top-K horizon×channel cells in `G` receive boosted weight.
- Why it does not create contribution sprawl:
  This is a single ablation of the same compressed prior, not a separate method family.

### Modern Primitive Usage
- None.

### Integration into Base Generator / Downstream Pipeline
1. Reuse raw train sensitivities.
2. Compress them into one global prior `G(h,c)`.
3. Train one GRU rerun with broadcasted `G`.
4. Evaluate with unchanged `forecast -> qp_carbon -> CityLearn`.

### Training Plan
1. Treat raw slot-wise CSFT as formally falsified in the current setting.
2. Build one global controller-calibrated prior from train raw sensitivities.
3. Run one GRU rerun with mixed loss using this fixed prior.
4. Compare against uniform, raw-CSFT, and one strongest heuristic baseline.
5. Only if this route is positive, consider seeds or controller-specificity strengthening.

### Failure Modes and Diagnostics
- Failure mode: the global prior collapses to a nearly heuristic front-loaded mask.
  - How to detect:
    compare `G(h,c)` visually to manual horizon weighting.
  - Fallback or mitigation:
    then the claim should weaken to controller-calibrated justification for a simple heuristic.
- Failure mode: the global prior improves stability but not control.
  - How to detect:
    top-decile / high-prior-cell MAE improves but `cost/carbon/peak` do not.
  - Fallback or mitigation:
    conclude that even compressed controller-aware weighting is insufficient in this stack.
- Failure mode: the strongest heuristic ties or wins.
  - How to detect:
    direct comparison on the same single-run budget.
  - Fallback or mitigation:
    pivot to heuristic/event-window paper or stop controller-aware weighting as main thesis.

### Novelty and Elegance Argument
The strongest clean conclusion from the preflight failure is not “try more smoothing.” It is:

> Controller-aware forecast supervision must be compressed before it becomes useful.

That is a tighter and more paper-worthy pivot than continuing to defend raw sample-wise weighting after it already failed its own utility gate.

## Claim-Driven Validation Sketch
### Claim 1: Raw slot-wise CSFT is formally falsified in the current setting
- Minimal experiment:
  use R201/R202 results as frozen evidence.
- Baselines / ablations:
  oracle alignment and top-decile utility gate.
- Metric:
  preflight PASS/FAIL.
- Expected evidence:
  oracle passes, utility fails, so raw-CSFT is not a viable main route.

### Claim 2: A compressed controller-calibrated prior is a better supervision target than raw per-sample weights
- Minimal experiment:
  one GRU rerun with the global prior.
- Baselines / ablations:
  uniform, raw-CSFT, strongest simple heuristic, global-prior method.
- Metric:
  top-prior-cell MAE, overall MAE, `cost`, `carbon`, `peak`.
- Expected evidence:
  global prior should beat raw-CSFT and at least match heuristic on primary KPIs.

## Experiment Handoff Inputs
- Must-prove claims:
  raw slot-wise controller-sensitive supervision is invalid here; a lower-entropy controller-calibrated prior is the best remaining fixed-controller route.
- Must-run ablations:
  uniform, raw-CSFT, strongest heuristic, global-prior method.
- Critical datasets / metrics:
  current split, raw train sensitivity maps, MAE, `cost`, `carbon`, `peak`.
- Highest-risk assumptions:
  that there exists a stable global controller-relevance structure at all; if not, the whole controller-aware weighting line should be deprioritized.

## Compute & Timeline Estimate
- Estimated GPU-hours:
  Low. One new rerun after reusing existing raw sensitivities.
- Data / annotation cost:
  None.
- Timeline:
  One analysis step to build the prior, one rerun, one stop/go decision.
