# Round 1 Refinement

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

## Anchor Check
- Original bottleneck:
  原始 bottleneck 仍然是 forecast loss 没有学到 controller 真正在意的 future cells。
- Why the revised method still addresses it:
  新 pivot 不是放弃 controller-aware supervision，而是把它从 raw noisy slot weights 提升成更稳、更明确的 controller-derived prior。
- Reviewer suggestions rejected as drift:
  不转向 heuristic weighting paper，不转向 RL，不回到 broad method bundle。

## Simplicity Check
- Dominant contribution after revision:
  一个从固定 QP controller 直接导出的 **controller-dual prior**。
- Components removed or merged:
  去掉 global mean finite-difference prior；不保留 top-K prior；不保留多种 prior 家族。
- Reviewer suggestions rejected as unnecessary complexity:
  不加第二个模型，不做复杂 meta-learning，不做可学习 prior 网络。
- Why the remaining mechanism is still the smallest adequate route:
  prior 仍然是一个固定的 horizon×channel weight matrix，只是来源从 noisy finite differences 平均升级为 QP 解析敏感度统计。

## Changes Made

### 1. Replace heuristic-looking global mean prior with controller-dual prior
- Reviewer said:
  global prior 可能塌成 front-loaded heuristic，论文强度不够。
- Action:
  把方法主张改成从 QP objective / constraints 中提取解析梯度或 dual-derived sensitivity，再聚合成 `G(h,c)`。
- Reasoning:
  这样 prior 仍然低熵、低成本，但 controller-specificity 更强，不容易被说成 post-hoc smoothing。
- Impact on core method:
  pivot 变成一个更 principled 的 fixed-controller supervision route。

### 2. Freeze channel-scale handling
- Reviewer said:
  当前 prior 仍有 scale leakage 风险。
- Action:
  用 baseline per-channel MAE 或 train-set target std 做 channel-wise normalization，再构造 prior。
- Reasoning:
  这样 `price/load/solar` 的不同数值尺度不会直接污染 prior。
- Impact on core method:
  prior 更可比较，也更像真正的 controller relevance map。

## Revised Proposal

# Research Proposal: Controller-Dual Forecast Prior After Raw-CSFT Failure

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
  The next route should produce a lower-variance, controller-specific weighting signal that beats raw-CSFT, is measurably different from a generic front-loaded heuristic, and shows at least early improvement on control-critical forecast error and control KPIs.

## Technical Gap
The preflight failure says something precise: raw slot-wise finite-difference sensitivities are too sparse to supervise forecasting directly. But that does not yet falsify the broader thesis that controller-derived relevance matters. It only falsifies one estimator.

So the key question becomes:

> Can a fixed QP controller yield a lower-variance, controller-specific relevance prior that is more principled than raw finite differences and more specific than a horizon heuristic?

The smallest adequate answer is not another smoothing recipe. It is to extract a **controller-dual prior** from the QP itself.

## Method Thesis
- One-sentence thesis:
  When raw slot-wise finite-difference sensitivities fail, replace them with a controller-dual prior: a fixed horizon×channel relevance map derived from the QP objective/constraint sensitivities and used as a low-entropy forecast weighting prior.
- Why this is the smallest adequate intervention:
  Same controller, same backbone, same data, same inference path; only the supervision source changes from noisy sample-wise perturbations to an analytic controller-derived prior.
- Why this route is timely in the foundation-model era:
  The bottleneck is not model capacity but whether forecast supervision reflects the downstream controller. A dual-derived prior is a more principled decision-aware signal than heuristic weighting.

## Contribution Focus
- Dominant contribution:
  A controller-dual forecast prior that converts fixed-QP sensitivities into a stable horizon×channel weighting map for forecast training.
- Optional supporting contribution:
  A formal falsification result showing that raw per-sample slot-wise CSFT is invalid in the current setting.
- Explicit non-contributions:
  No new controller, no end-to-end decision-focused training, no new backbone, no RL/LLM components, no large hyperparameter family.

## Proposed Method
### Complexity Budget
- Frozen / reused backbone:
  Current GRU forecaster, CityLearn data path, chronological split, fixed `qp_carbon` controller, existing baseline checkpoints.
- New trainable components:
  None.
- Tempting additions intentionally not used:
  raw slot-wise stabilized CSFT, top-K priors, controller retraining, meta-learning over priors.

### System Overview
```text
fixed qp_carbon controller
  -> analytic sensitivity / dual-derived relevance over horizon×channel
  -> channel-normalized controller-dual prior G[h,c]
  -> broadcast prior to all samples
  -> mixed weighted forecast loss
  -> forecast -> qp_carbon -> CityLearn
```

### Core Mechanism
- Input / output:
  Same forecasting input/output as the current GRU setup.
- Representation design:
  Build one fixed prior `G(h,c)` over horizon × channel.
- Prior construction:
  1. For the fixed QP controller, compute per-step objective sensitivity to forecasted `price/load/solar` using analytic objective coefficients and, where needed, dual variables from active constraints.
  2. Normalize each channel by a training-scale quantity (either train-set target std or uniform-baseline per-channel MAE).
  3. Aggregate over train windows to form expected absolute controller relevance:
     `G(h,c) = E_t |dJ_t / d y_(t,h,c)|`
  4. Normalize `G` to mean 1 over `(h,c)`.
- Training signal / loss:
  Broadcast `G` to all samples and use a fixed mixed Huber objective:
  `L_t = alpha * sum Huber(yhat, y) + (1-alpha) * sum G(h,c) * Huber(yhat_(t,h,c), y_(t,h,c))`
  with fixed `alpha`.
- Why this is the main novelty:
  It yields a controller-specific low-entropy prior that is derived from the optimization structure itself, rather than from noisy brute-force perturbations or manual masks.

### Optional Supporting Component
- None.

### Modern Primitive Usage
- None.

### Integration into Base Generator / Downstream Pipeline
1. Keep the same GRU + fixed `qp_carbon` pipeline.
2. Extract one controller-dual prior from the fixed controller and train split.
3. Train one rerun with that prior.
4. Evaluate against uniform, raw-CSFT, and strongest simple heuristic.

### Training Plan
1. Freeze raw-CSFT as falsified in the current setting.
2. Implement controller-dual prior extraction.
3. Train one GRU rerun with fixed prior weighting.
4. Compare against uniform, raw-CSFT, and strongest heuristic baseline.
5. Only if this route is positive consider multi-seed strengthening.

### Failure Modes and Diagnostics
- Failure mode: controller-dual prior is too correlated with a simple front-loaded horizon mask.
  - How to detect:
    compare `G(h,c)` with manual horizon weighting using correlation / relative entropy.
  - Fallback or mitigation:
    if nearly identical, weaken the claim to controller-justified heuristic weighting.
- Failure mode: dual prior improves error concentration but not control KPIs.
  - How to detect:
    high-prior-cell MAE improves but `cost/carbon/peak` do not.
  - Fallback or mitigation:
    conclude that controller-aware weighting is still insufficient in this stack.
- Failure mode: strongest heuristic beats controller-dual prior.
  - How to detect:
    direct comparison under same budget.
  - Fallback or mitigation:
    stop treating controller-aware weighting as a paper-level method contribution.

### Novelty and Elegance Argument
The cleanest post-failure pivot is:

> Raw controller-aware supervision failed because it was too noisy, not because controller relevance is unimportant.

The smallest principled repair is therefore to replace noisy sample-wise weights with a controller-dual prior that is:
- fixed,
- controller-specific,
- lower-variance,
- and still compatible with the existing pipeline.

## Claim-Driven Validation Sketch
### Claim 1: Raw slot-wise CSFT is falsified in the current setting
- Minimal experiment:
  reuse R201/R202 as frozen evidence.
- Baselines / ablations:
  oracle alignment and top-decile utility gate.
- Metric:
  PASS/FAIL.
- Expected evidence:
  oracle passes, raw-label utility fails.

### Claim 2: Controller-dual prior is a stronger and more defensible supervision target than raw-CSFT and simple heuristic weighting
- Minimal experiment:
  one GRU rerun with controller-dual prior.
- Baselines / ablations:
  uniform, raw-CSFT, strongest heuristic, controller-dual prior.
- Metric:
  high-prior-cell MAE, overall MAE, `cost`, `carbon`, `peak`, plus similarity-to-heuristic characterization.
- Expected evidence:
  controller-dual prior beats raw-CSFT and is either better than or clearly different from the strongest heuristic baseline.

## Experiment Handoff Inputs
- Must-prove claims:
  raw slot-wise CSFT is invalid here; a controller-specific low-entropy prior remains the strongest minimal pivot.
- Must-run ablations:
  uniform, raw-CSFT, strongest heuristic, controller-dual prior.
- Critical datasets / metrics:
  current split, controller-derived prior, MAE, `cost`, `carbon`, `peak`, heuristic-similarity characterization.
- Highest-risk assumptions:
  that QP-derived prior is genuinely controller-specific and not just a relabeled horizon heuristic.

## Compute & Timeline Estimate
- Estimated GPU-hours:
  Low.
- Data / annotation cost:
  None.
- Timeline:
  one prior extraction step, one rerun, one stop/go decision.
