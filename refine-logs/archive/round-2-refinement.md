# Round 2 Refinement

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

## Anchor Check
- Original bottleneck:
  当前真正的问题不是模型太弱，而是 controller-derived supervision 是否有效、是否稳定。
- Why the revised method still addresses it:
  这轮 refinement 继续只修 supervision，不改 backbone、不改 controller、不改推理路径。
- Reviewer suggestions rejected as drift:
  不新增额外实验家族，不回到 broader CSFT family，也不把 heuristic baselines 抬成主方法。

## Simplicity Check
- Dominant contribution after revision:
  一个完全数值化的 preflight gate + 一个固定 stabilized operator。
- Components removed or merged:
  删除多余指标歧义；主接受标准只围绕 MAE 和主 KPI；preflight 输出压缩为单一 PASS/FAIL。
- Reviewer suggestions rejected as unnecessary complexity:
  不再保留 narrative-style check，不保留多阈值搜索，不加第二套 stabilization path。
- Why the remaining mechanism is still the smallest adequate route:
  它现在是一个可执行算法：给定 checkpoint 和 label，就能直接给出 PASS/FAIL 和后续唯一训练配方。

## Changes Made

### 1. Numeric preflight thresholds are now fully specified
- Reviewer said:
  preflight 还带有“not catastrophically losing”这类定性说法，不够算法化。
- Action:
  把 oracle alignment、top-decile fail threshold、Huber delta、epsilon、median_positive_train 计算方式全部数值化。
- Reasoning:
  这样 reviewer 看到的是一个可执行 gate，不是 debug 经验。
- Impact on core method:
  proposal 更像一个 fixed algorithm，而不是研究过程记录。

### 2. Acceptance rule is narrowed to MAE + primary KPIs
- Reviewer said:
  双 forecast 指标会造成歧义。
- Action:
  主 claim 中只保留 MAE 和 primary KPIs (`cost`, `carbon`, `peak`)。
- Reasoning:
  MAE 更贴近当前 pilot 诊断，也能减少 metric shopping 的感觉。
- Impact on core method:
  pass/fail rule 更紧，叙事更清楚。

## Revised Proposal

# Research Proposal: Algorithmic Preflight-Validated CSFT

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
The pilot failure implies that raw controller sensitivity is not yet a valid training signal. The actual method question is therefore:

> Can controller-derived sensitivity be converted into a stable, trainable supervision signal by a fixed validation-and-stabilization algorithm?

The answer must be algorithmic, not narrative. So the proposal is reduced to one gate and one operator.

## Method Thesis
- One-sentence thesis:
  Raw finite-difference controller sensitivities should only be used for forecast training after passing a numerical preflight validity gate and a fixed stabilization operator.
- Why this is the smallest adequate intervention:
  Nothing in inference changes; only the training-side supervision is repaired.
- Why this route is timely in the foundation-model era:
  The current failure is supervision-limited, not capacity-limited.

## Contribution Focus
- Dominant contribution:
  A fully specified algorithm that decides whether raw controller-sensitive labels are valid enough to use, and if so, transforms them into stabilized mixed-loss weights.
- Optional supporting contribution:
  None in the main claim.
- Explicit non-contributions:
  No controller redesign, no new backbone, no RL, no routing, no search over multiple stabilization recipes.

## Proposed Method
### Complexity Budget
- Frozen / reused backbone:
  Current GRU forecaster, current CityLearn data path, chronological split, fixed `qp_carbon` controller, and existing uniform/raw-CSFT checkpoints.
- New trainable components:
  None.
- Tempting additions intentionally not used:
  alternative transforms, smoothing variants, bucketed fallback, backbone/controller scaling.

### System Overview
```text
raw finite-difference sensitivity labels
  -> numerical preflight gate (PASS/FAIL)
  -> fixed stabilization operator
  -> mixed weighted Huber loss
  -> one stabilized-CSFT rerun
```

### Core Mechanism
- Input / output:
  Same forecasting input/output as the current GRU setup.

- Step 1: Numerical preflight gate
  Given existing uniform/raw-CSFT checkpoints and current artifacts, compute two checks:

  **(A) Oracle alignment test**
  - Compare oracle slices and environment-derived future `price/load/solar` on the first 20 matched steps.
  - Pass criterion:
    `max_abs_error <= 1e-6` for each of the three channels.

  **(B) Raw-label utility test**
  - Use current test labels to rank all forecast cells by sensitivity.
  - Compute top-decile MAE for uniform and raw-CSFT.
  - Pass criterion:
    raw-CSFT top-decile MAE is **not worse than uniform by more than 5%**.

  Preflight returns a single boolean:
  - PASS only if both (A) and (B) pass.
  - Otherwise FAIL and stop this method route.

- Step 2: Fixed stabilization operator
  If preflight passes, compute weights as follows.

  Let `q95_train` be the 95th percentile over all positive raw train sensitivities.
  Let `m_train` be the median over all positive clipped raw train sensitivities.
  Let `eps = 1e-8`.

  For each raw sensitivity `s_(t,h,c)`:
  1. `s_clip = min(max(s_(t,h,c), 0), q95_train)`
  2. `u_(t,h,c) = log1p(s_clip / (m_train + eps))`
  3. `w_(t,h,c) = u_(t,h,c) / (eps + mean_{h,c}(u_(t,h,c)))`

  This is the only stabilization operator used in the paper.

- Step 3: Fixed mixed objective
  Train the stabilized model with Huber loss where:
  - Huber delta = `1.0`
  - `alpha = 0.85`

  Objective:

  `L_t = 0.85 * sum Huber(yhat, y) + 0.15 * sum w_(t,h,c) * Huber(yhat_(t,h,c), y_(t,h,c))`

- Why this is the main novelty:
  The contribution is now a reproducible algorithmic claim: controller-sensitive supervision becomes usable only after a numerical validity gate and a fixed stabilization operator.

### Optional Supporting Component
- None.

### Modern Primitive Usage
- None.

### Integration into Base Generator / Downstream Pipeline
1. Run numerical preflight on existing artifacts.
2. If FAIL: stop and falsify raw-CSFT in this setting.
3. If PASS: compute stabilized weights with the fixed operator.
4. Train one stabilized-CSFT rerun on GPU 2.
5. Evaluate with unchanged `forecast -> qp_carbon -> CityLearn` pipeline.

### Training Plan
1. Run one preflight script.
2. If PASS, launch one stabilized-CSFT rerun.
3. Evaluate against uniform and raw-CSFT.
4. Stop/go decision immediately after this single rerun.

### Failure Modes and Diagnostics
- Failure mode: oracle alignment fails.
  - Detection: preflight alignment test.
  - Mitigation: stop and fix oracle path before any further interpretation.
- Failure mode: raw labels fail the utility test.
  - Detection: preflight top-decile MAE threshold.
  - Mitigation: falsify raw slot-wise CSFT for this setting.
- Failure mode: stabilized rerun improves top-decile MAE but hurts aggregate MAE too much.
  - Detection: acceptance rule below.
  - Mitigation: reject method as too costly in aggregate forecast quality.
- Failure mode: stabilized rerun improves forecast-side critical cells but not primary KPIs.
  - Detection: acceptance rule below.
  - Mitigation: reject method as not decision-useful enough.

### Novelty and Elegance Argument
The paper asks one narrow question:

> When can controller-derived sensitivity be trusted as supervision for forecasting?

The proposed answer is fully algorithmic:

> Only when it clears a numerical preflight gate, and only after a fixed stabilization operator.

That is sharper than a general “debug and tune CSFT” story.

## Claim-Driven Validation Sketch
### Claim 1: Raw controller-sensitive labels are only usable if they pass a numerical validity gate
- Minimal experiment:
  Run the preflight.
- Baselines / ablations:
  oracle slices vs env truth; uniform vs raw-CSFT top-decile MAE.
- Metric:
  `max_abs_error`, top-decile MAE ratio.
- Expected evidence:
  FAIL means the method route should not be scaled.

### Claim 2: The fixed stabilization operator should improve controller-critical fitting without unacceptable aggregate degradation
- Minimal experiment:
  One stabilized-CSFT rerun.
- Baselines / ablations:
  uniform, raw-CSFT, stabilized-CSFT.
- Metric:
  top-decile MAE and overall MAE.
- Expected evidence:
  stabilized-CSFT beats raw-CSFT on top-decile MAE and stays close to uniform on overall MAE.

### Claim 3: The method is viable only if it passes a pre-registered acceptance rule
- Minimal experiment:
  Evaluate stabilized-CSFT vs uniform.
- Acceptance rule:
  1. top-decile MAE lower than uniform,
  2. overall MAE no worse than uniform by more than 1%,
  3. at least one of `cost` or `carbon` improves,
  4. `peak` no worse than uniform by more than 1%.

  All four must hold.

## Experiment Handoff Inputs
- Must-prove claims:
  the preflight gate is meaningful, and the fixed stabilization operator can convert valid raw sensitivities into useful supervision.
- Must-run ablations:
  uniform vs raw-CSFT top-decile analysis; oracle alignment test; one stabilized rerun.
- Critical datasets / metrics:
  current split, existing checkpoints, label files, top-decile MAE, overall MAE, `cost`, `carbon`, `peak`.
- Highest-risk assumptions:
  preflight may immediately fail; if so, this route should be stopped rather than expanded.

## Compute & Timeline Estimate
- Estimated GPU-hours:
  Very low for preflight, low for one rerun.
- Data / annotation cost:
  None.
- Timeline:
  one preflight, one rerun, one stop/go decision.
