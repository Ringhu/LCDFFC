# Research Proposal: Decision-Critical Forecast Refinement for Exogenous Time-Series Control

## Problem Anchor
- Bottom-line problem:
  Build a publishable method for exogenous time-series-driven control where better forecasting translates into reliable downstream control gains rather than only lower forecast error.
- Must-solve bottleneck:
  In forecast-then-control pipelines, the controller only cares about a small subset of future windows and channels, but standard training treats all forecast errors roughly equally. This mismatch is why stronger forecasters often fail to produce stable KPI gains.
- Non-goals:
  Not trying to build a new time-series foundation model, not using LLMs to output low-level actions, not making RL the main method, and not forcing a multi-environment paper in the first version.
- Constraints:
  Start from CityLearn battery control, keep the current low-level QP stack fixed, use modest compute, and keep the main method small enough to implement and validate quickly in the current repository.
- Success condition:
  With the same controller, the proposed training method should produce more consistent cost / carbon / peak improvements than plain MSE training across at least one classic backbone and one strong foundation backbone, and the gain should be traceable to better accuracy on controller-critical future windows.

## Technical Gap
Current predict-then-optimize pipelines usually break at the same place. The forecaster is optimized for average error, while the controller reacts to a few decision-critical future events such as price spikes, carbon spikes, outage-sensitive reserve periods, and peak-load windows. A backbone can improve average MSE and still miss the exact windows that move the control objective.

Naive fixes are not enough.
- A larger forecaster can still spend capacity on the wrong horizons.
- End-to-end RL changes the whole problem and loses the clean forecast-control decomposition.
- Full differentiable decision-focused training through long-horizon control is heavier and less stable than this repo needs for a first paper.

The missing mechanism is a small way to tell the forecaster which future errors the controller actually cares about.

## Method Thesis
- One-sentence thesis:
  Fine-tune any forecaster with controller-derived criticality weights so that forecast error is reduced most on the future slots that matter most to the fixed downstream controller.
- Why this is the smallest adequate intervention:
  The controller stays fixed. The backbone stays almost unchanged. The only main change is how training weight is assigned across future horizons and channels.
- Why this route is timely in the foundation-model era:
  Strong time-series backbones already exist, but they are still trained mostly for generic forecast metrics. A backbone-agnostic control-aware refinement method is a cleaner and more current contribution than building yet another forecasting model.

## Contribution Focus
- Dominant contribution:
  A controller-critical forecast refinement recipe that estimates which future forecast slots matter to control, then uses those signals to fine-tune the forecaster.
- Optional supporting contribution:
  Show that the same refinement objective improves both a classic backbone and a strong foundation backbone, which turns the paper from "one tuned model" into a backbone-agnostic method.
- Explicit non-contributions:
  No new optimizer, no new low-level controller, no language router in the first paper, no uncertainty stack as a second main contribution.

## Proposed Method
### Complexity Budget
- Frozen / reused backbone:
  CityLearn environment, current data path, current action space, fixed QP controller, and existing forecaster families.
- New trainable components:
  No mandatory new trainable module. The main novelty is the control-aware refinement objective. If needed for stability, add one lightweight event auxiliary head, but this is optional rather than core.
- Tempting additions intentionally not used:
  End-to-end RL, LLM objective routing, uncertainty ensemble as a co-equal contribution, and a required Grid2Op transfer benchmark.

### System Overview
```text
history + known future exogenous signals
  -> forecasting backbone
  -> future net-demand / PV trajectories
  -> fixed QP controller
  -> battery action
  -> CityLearn rollout

training-only side path:
  training windows + fixed QP + oracle futures
    -> controller criticality estimator
    -> per-horizon / per-channel importance weights
    -> weighted refinement loss for the forecaster
```

### Core Mechanism
- Input / output:
  Input is the same forecast training window used by the current repo: historical building-side time series plus known or provided future exogenous signals. Output is the same forecast target already consumed by the controller.
- Architecture or policy:
  The forecasting backbone stays unchanged. The controller stays unchanged. The new mechanism is an offline criticality estimator that scores each future target slot by how much downstream control quality changes when that slot is perturbed.
- Training signal / loss:
  For each training example and future slot `(h, c)`, estimate a criticality score

  `s_(h,c) = |J(pi(y + delta e_(h,c)), y) - J(pi(y), y)| / |delta|`

  where `y` is the oracle future target, `pi` is the fixed controller driven by that target, `J` is the rollout or local control objective surrogate, and `e_(h,c)` perturbs one horizon/channel.

  Then fine-tune the forecaster with

  `L = L_base + lambda * sum_(h,c) normalize(s_(h,c)) * ell(yhat_(h,c), y_(h,c))`

  where `L_base` is the normal forecast loss and `ell` is the per-slot prediction loss.
- Why this is the main novelty:
  This is not generic reweighting and not full end-to-end DFL. It extracts controller sensitivity into explicit supervision over forecast slots, which is simpler to implement, easier to diagnose, and portable across backbones.

### Optional Supporting Component
- Only include if truly necessary:
  A small event auxiliary head that predicts whether each future window is in a high-risk regime such as peak, carbon spike, or reserve-stress period.
- Input / output:
  Backbone hidden state to event logits.
- Training signal / loss:
  Binary or multi-label cross-entropy on event windows derived from the oracle target and known exogenous drivers.
- Why it does not create contribution sprawl:
  It exists only to stabilize the weighting signal if the raw finite-difference score is noisy. The paper still stands if this head is removed.

### Modern Primitive Usage
- Which LLM / VLM / Diffusion / RL-era primitive is used:
  A time-series foundation backbone can be used as one of the backbones tested by the method, but it is frozen or lightly adapted rather than introduced as the main contribution.
- Exact role in the pipeline:
  Numeric representation backbone only.
- Why it is more natural than an old-school alternative:
  The point is not to invent another backbone. The point is to make an existing strong backbone decision-aware with a minimal training-side intervention.

### Integration into Base Generator / Downstream Pipeline
The method attaches at the training objective, not at inference-time control.

1. Pretrain or reuse the forecasting backbone with the usual forecast loss.
2. Build controller-criticality labels offline from the fixed QP controller using oracle futures on the training split.
3. Fine-tune the same forecaster with the weighted loss.
4. At inference time, run the normal forecast -> QP pipeline with no additional planner, router, or policy network.

This keeps inference simple and makes the method easy to retrofit into the current repository.

### Training Plan
1. Use CityLearn training windows with building-side targets such as future net demand and optional PV.
2. Train or reuse a baseline forecaster with the current standard objective.
3. For each sampled training window, compute controller-criticality labels by perturbing target slots and measuring downstream objective change under the fixed QP controller.
4. Smooth and clip the raw scores so training does not collapse to a few nearest horizons.
5. Fine-tune the forecaster with the weighted objective.
6. Optionally repeat the same recipe on one classic backbone and one foundation backbone.
7. Keep the controller fixed throughout the main experiments.

### Failure Modes and Diagnostics
- Criticality collapses to only the nearest few steps:
  Detect by plotting weight mass over horizons.
  Fallback is temperature scaling, percentile clipping, and comparison to a naive horizon-decay baseline.
- Sensitivity labels are too noisy:
  Detect by low rank-correlation across nearby windows or seeds.
  Fallback is local smoothing, event-window aggregation, or the optional auxiliary head.
- Gains only appear on one backbone:
  Detect by running the same recipe on one classic and one foundation backbone.
  Fallback is to narrow the claim from backbone-agnostic to backbone-compatible.
- Gains improve MSE but not control:
  Detect by KPI delta versus the MSE baseline.
  Fallback is to inspect whether the criticality score is aligned with the actual controller bottlenecks and revise the score definition.

### Novelty and Elegance Argument
The paper is focused because it makes one claim.

Forecast quality should be measured and trained according to controller sensitivity, not uniform average error.

That is sharper than bundling forecasting, uncertainty, routing, and RL into one stack. It also fits current time-series practice better: strong pretrained or standard backbones already exist, but they still need a clean way to become decision-aware.

## Claim-Driven Validation Sketch
### Claim 1: Controller-critical refinement improves downstream control more reliably than plain forecast training
- Minimal experiment:
  Train the same backbone with MSE only versus the proposed refinement objective, then evaluate both with the same fixed QP controller on CityLearn.
- Baselines / ablations:
  myopic or no-forecast controller, MSE training, naive horizon-decay weighting, event-only weighting.
- Metric:
  cost, carbon, peak, ramping, and KPI regret relative to an oracle-forecast controller.
- Expected evidence:
  The proposed refinement gives a more consistent KPI gain than MSE-only training and naive weighting.

### Claim 2: The gain comes from protecting controller-critical windows rather than blanket accuracy improvement
- Minimal experiment:
  Partition future slots into high-criticality and low-criticality bins, then compare forecast error and perturbation robustness for each bin.
- Baselines / ablations:
  MSE model versus proposed model.
- Metric:
  weighted error on critical slots, action deviation under perturbation, and local objective degradation around price/carbon/peak events.
- Expected evidence:
  The proposed model reduces error mostly where the controller is sensitive, and this change explains the KPI improvement.

### Claim 3: The method is backbone-compatible rather than tied to one model family
- Minimal experiment:
  Apply the same refinement recipe to one classic backbone and one strong foundation backbone.
- Baselines / ablations:
  MSE version of each backbone.
- Metric:
  downstream KPI delta over each backbone's own MSE baseline across ID and outage-seed-shifted evaluation.
- Expected evidence:
  The refinement direction is consistent across backbones even if absolute gains differ.

## Experiment Handoff Inputs
- Must-prove claims:
  controller-aware forecast training matters, the effect is caused by critical-window protection, and the method is not tied to one backbone.
- Must-run ablations:
  MSE only, naive horizon weighting, event-only weighting, proposed criticality weighting, and at least one backbone swap.
- Critical datasets / metrics:
  CityLearn 2023 with cost / carbon / peak / ramping and outage-seed shift evaluation.
- Highest-risk assumptions:
  the fixed-controller sensitivity signal must be stable enough to supervise forecasting, and the resulting gains must survive when moving from a classic model to a stronger backbone.

## Compute & Timeline Estimate
- Estimated GPU-hours:
  Low for GRU-scale runs, moderate for one foundation-backbone replication. Sensitivity label generation is mostly offline controller evaluation rather than large-model training.
- Data / annotation cost:
  No manual labeling cost. Criticality labels come from the simulator and fixed controller.
- Timeline:
  Stage 1: stabilize the reference backbone and controller. Stage 2: build criticality labels and weighted refinement. Stage 3: run backbone and shift validation.
