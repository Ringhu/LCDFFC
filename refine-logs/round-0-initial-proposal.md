# Research Proposal: Stabilized Controller-Sensitive Forecast Training After Pilot Failure

## Problem Anchor
- Bottom-line problem:
  Build a publishable method for exogenous time-series-driven control where forecast training improves downstream control KPIs, not just average forecast error.
- Must-solve bottleneck:
  In forecast-then-control pipelines, the controller only cares about a small subset of future windows and channels, but the current raw cell-wise CSFT labels appear too sharp, too noisy, or misaligned to provide useful supervision. The current pilot suggests that naive controller-sensitive weighting can hurt both forecasting and control.
- Non-goals:
  Not scaling to more seeds/backbones yet, not introducing a new controller, not switching to end-to-end RL, not making language routing part of the main story, and not claiming a final paper-ready method before pilot failure is explained.
- Constraints:
  Start from the current CityLearn + GRU + fixed `qp_carbon` stack, use the existing chronological split and artifacts, keep compute modest, use GPU 2 only for training/inference, and prefer diagnostics that reuse existing checkpoints before new full reruns.
- Success condition:
  After a small diagnostic-and-refinement loop, either (a) a softened controller-sensitive training objective shows better error on controller-critical cells and at least early positive KPI signal over uniform training, or (b) we can confidently falsify the current raw-label route and pivot without wasting more compute.

## Technical Gap
Current evidence says the original A1-style CSFT formulation is not yet a paper; it is a failed pilot that still needs diagnosis. The actual numbers are not ambiguous: compared with uniform training, current CSFT worsens overall forecast MSE/MAE and also worsens `cost`, `carbon`, `peak`, and `ramping` under the same fixed `qp_carbon` controller. The label distribution is extremely spiky, and the current oracle path is suspiciously worse than learned uniform.

That means the missing mechanism is no longer just “controller-aware weighting.” The missing mechanism is a **stable and validated controller-sensitive supervision signal**. Without that, raw finite-difference labels are just noisy weights.

Naive next steps are insufficient:
- More seeds on a broken pilot will only make the negative result more expensive.
- More backbones will not fix label mis-specification.
- Full decision-focused training is too large a pivot before the fixed-controller supervision signal is validated.
- Heuristic event windows alone are useful baselines, but not a satisfying main method unless they clearly outperform the sensitivity route.

The smallest adequate next route is therefore:
1. verify whether the current labels help on the cells they claim to prioritize,
2. verify oracle alignment,
3. test a softened/stabilized weighting variant before scaling anything else.

## Method Thesis
- One-sentence thesis:
  The right next method is not raw CSFT, but **stabilized controller-sensitive forecast training**: keep fixed-controller supervision, but replace brittle cell-wise spike weights with validated, softened importance targets that are required to improve controller-critical forecast cells before being trusted as a training signal.
- Why this is the smallest adequate intervention:
  The environment, controller, dataset, and backbone all stay fixed. Only the label processing, weighting transform, and acceptance criteria change.
- Why this route is timely in the foundation-model era:
  Strong backbones already exist; the bottleneck here is not capacity but misaligned supervision. A small but principled repair to the supervision signal is more valuable than another large model or control stack.

## Contribution Focus
- Dominant contribution:
  A diagnosis-driven stabilized CSFT recipe that turns raw controller sensitivities into a tractable supervision signal through validation, clipping, smoothing, and softened weighting.
- Optional supporting contribution:
  A falsification protocol for controller-aware forecasting: top-decile error analysis, oracle alignment check, and matched-versus-broken weighting diagnostics.
- Explicit non-contributions:
  No new controller, no new backbone family as a main claim, no RL policy learning, no LLM-based objective routing, no multi-environment transfer in this phase.

## Proposed Method
### Complexity Budget
- Frozen / reused backbone:
  Current GRU forecaster, current CityLearn data path, chronological split, fixed `qp_carbon` controller, and existing CSFT/uniform checkpoints.
- New trainable components:
  None required.
- Tempting additions intentionally not used:
  Backbone zoo, full differentiable decision-focused training, long-horizon regret optimization, routing/fallback machinery, and broad benchmark expansion.

### System Overview
```text
existing pipeline:
history + known future exogenous signals
  -> GRU forecaster
  -> forecast trajectory
  -> fixed qp_carbon controller
  -> battery action
  -> CityLearn rollout

new diagnosis-and-refinement loop:
existing checkpoints + test labels
  -> top-decile error analysis
  -> verify whether CSFT helps controller-critical cells

env future + oracle slices
  -> exact alignment check
  -> verify oracle is trustworthy

raw sensitivity labels
  -> clipping / transform / coarse smoothing
  -> softened mixed weighted loss
  -> one small rerun
```

### Core Mechanism
- Input / output:
  Same forecasting input and output as the existing GRU setup. The method changes only the training-side importance map.
- Label validation first:
  Before trusting any weighted objective, require the current CSFT checkpoint to beat or at least match the uniform checkpoint on the highest-sensitivity forecast cells. If it cannot, the raw label route is not yet a valid supervision target.
- Stabilized weight construction:
  Start from existing finite-difference sensitivities `s_(t,h,c)` but do not use them directly. Construct stabilized weights via:
  1. oracle alignment sanity check,
  2. clipping at a train-set quantile,
  3. monotone soft transform such as `sqrt(s)` or `log1p(s / tau)`,
  4. optional horizon-channel smoothing or rank-binning,
  5. per-sample normalization.
- Training signal / loss:
  Keep the mixed objective form,

  `L_t = alpha * sum ell(yhat, y) + (1-alpha) * sum w_(t,h,c) * ell(yhat_(t,h,c), y_(t,h,c))`

  but move to softer regimes such as `alpha in {0.8, 0.9}` before considering stronger weighting again.
- Why this is the main novelty:
  The paper-worthy claim is no longer “any controller sensitivity helps.” It becomes: **controller-sensitive supervision must be stabilized and validated at the cell level before it can improve forecast-then-control.** This is sharper, more honest to the negative result, and still mechanism-centered.

### Optional Supporting Component
- Only include if truly necessary:
  Replace raw cell-wise weights with coarse horizon-channel buckets if diagnostics show that exact cell weights are too noisy but rank information is still useful.
- Input / output:
  Raw `H x C` sensitivity map in, coarse bucketed importance map out.
- Training signal / loss:
  Same mixed loss, but weights are bucket-level rather than raw-cell level.
- Why it does not create contribution sprawl:
  This is a single fallback simplification of the weighting signal, not a second model.

### Modern Primitive Usage
- Which LLM / VLM / Diffusion / RL-era primitive is used:
  None in the core method.
- Exact role in the pipeline:
  Not applicable.
- Why this is more natural than an old-school alternative:
  The current bottleneck is label quality, not expressivity of the learner. Staying simple is the right choice.

### Integration into Base Generator / Downstream Pipeline
The method attaches only at the training objective and diagnosis stage:
1. reuse existing uniform and CSFT checkpoints for decile analysis;
2. verify oracle alignment against environment truth;
3. regenerate or reprocess weights if needed;
4. rerun one softened CSFT variant;
5. evaluate again with the unchanged `forecast -> qp_carbon -> CityLearn` pipeline.

### Training Plan
1. **D1: Top-decile error analysis** on existing checkpoints and test labels.
2. **D2: Oracle alignment sanity check** by comparing `build_oracle_forecast(...)` slices against environment-derived future values step-by-step.
3. If D1 says the labels contain some useful ranking signal and D2 passes, build one softened label transform.
4. Run **D3: one softened-CSFT rerun** with `alpha=0.8` and one monotone transform such as `sqrt(weight)`.
5. Compare against uniform on overall metrics, top-decile metrics, and control KPIs.
6. Only if this rerun shows signal, continue to heuristic baselines or matched/mismatched label ablations.

### Failure Modes and Diagnostics
- Failure mode: CSFT still loses on top-decile error.
  - How to detect:
    Decile-wise MSE/MAE table using existing checkpoints.
  - Fallback or mitigation:
    Abandon raw finite-difference slot-wise weighting as the main route; pivot to coarser event/horizon supervision or drop the controller-aware weighting thesis.
- Failure mode: oracle path is misaligned.
  - How to detect:
    exact first-20-step comparison between environment future and oracle slices.
  - Fallback or mitigation:
    fix alignment before interpreting any KPI gap or sensitivity labels.
- Failure mode: label ranking exists, but weighting is too aggressive.
  - How to detect:
    top-decile improves weakly while overall metrics and KPIs degrade.
  - Fallback or mitigation:
    increase `alpha`, apply monotone soft transforms, and prefer bucketed weights over raw spikes.
- Failure mode: even softened labels do not beat heuristic weighting.
  - How to detect:
    compare against manual horizon and event-window baselines after the softened rerun.
  - Fallback or mitigation:
    narrow the thesis to “simple control-aware heuristics suffice” and stop investing in CSFT as the main paper.

### Novelty and Elegance Argument
The elegant version of this story is not “we added another weighting trick.” The real question is:

> When controller sensitivity is used as supervision for forecasting, what makes that supervision valid rather than harmful?

The current negative result gives this paper a sharper scientific angle than the earlier optimistic proposal. The contribution becomes a small, falsifiable mechanism study: raw controller sensitivities are not automatically useful; they must be validated and stabilized before they can support forecast-then-control gains.

## Claim-Driven Validation Sketch
### Claim 1: Useful controller-aware supervision should improve the forecast cells it claims to care about
- Minimal experiment:
  Reuse existing uniform and CSFT checkpoints and evaluate decile-wise test MSE/MAE under the current test sensitivity labels.
- Baselines / ablations:
  Uniform vs current raw-CSFT.
- Metric:
  top-decile and per-decile MSE/MAE.
- Expected evidence:
  If CSFT does not help the highest-sensitivity decile, the raw label route is invalid.

### Claim 2: Oracle alignment must be correct before any controller-sensitive interpretation is trusted
- Minimal experiment:
  Compare oracle forecast slices and environment-derived future values on the same episode/time steps.
- Baselines / ablations:
  raw oracle slices vs env truth.
- Metric:
  exact equality or negligible numerical deviation for `price/load/solar` over the first several steps.
- Expected evidence:
  A trustworthy oracle path either matches exactly or reveals a fixable interface bug.

### Claim 3: If the label ranking is useful, a softened weighting regime should recover better control-critical fitting than raw CSFT
- Minimal experiment:
  One rerun with softened weighting such as `alpha=0.8` plus `sqrt(weight)`.
- Baselines / ablations:
  uniform, raw CSFT, softened CSFT.
- Metric:
  overall MSE/MAE, top-decile MSE/MAE, and `cost/carbon/peak`.
- Expected evidence:
  softened CSFT should at least recover uniform-level aggregate forecasting while improving controller-critical slices; otherwise the direction is too weak.

## Experiment Handoff Inputs
- Must-prove claims:
  raw controller sensitivity is not enough; validated and softened controller-sensitive supervision is the only viable next step for this direction.
- Must-run ablations:
  existing uniform vs raw CSFT decile analysis; oracle alignment check; one softened rerun.
- Critical datasets / metrics:
  current CityLearn chronological split, existing CSFT label files, existing GRU checkpoints, overall MSE/MAE, decile-wise MSE/MAE, and `cost/carbon/peak/ramping`.
- Highest-risk assumptions:
  that the current labels contain a useful ranking signal at all, and that the oracle path is not broken.

## Compute & Timeline Estimate
- Estimated GPU-hours:
  Very low for D1/D2; low for one softened rerun; still much cheaper than expanding to multi-seed or multi-backbone studies.
- Data / annotation cost:
  None. Reuses existing checkpoints, labels, and artifacts.
- Timeline:
  Stage 1: cheap falsification diagnostics (D1/D2). Stage 2: one softened rerun (D3). Stage 3: only then decide whether to scale, pivot, or stop.
