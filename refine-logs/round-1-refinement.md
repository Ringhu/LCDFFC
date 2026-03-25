# Round 1 Refinement

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
  不是所有 future forecast error 都同等重要，但当前 raw CSFT label 可能把“重要性”估错了或放大过头了。
- Why the revised method still addresses it:
  这版 refinement 没有换问题，只是把“controller-sensitive weighting”从一个脆弱的 raw-label 假设，收紧成“经过 validity preflight 和固定稳定化算子之后的 controller-sensitive supervision”。
- Reviewer suggestions rejected as drift:
  不引入更多 backbone、不切到 end-to-end DFL、不把 heuristic baseline 变成主方法，也不重新回到 routing 主线。

## Simplicity Check
- Dominant contribution after revision:
  一个固定的 stabilized-weight operator，加上一个预注册的 acceptance criterion。
- Components removed or merged:
  把 D1/D2 合并成一个统一的 `label validity preflight`；把 bucketed-weight fallback 从主方法中删除，只留作 contingency note。
- Reviewer suggestions rejected as unnecessary complexity:
  不保留 transform 搜索空间，不保留 smoothing 搜索空间，不把多个 `alpha` 写成主方法的一部分。
- Why the remaining mechanism is still the smallest adequate route:
  只做三件事：验证 label、固定变换、跑一个 softened rerun。除此之外不改模型、不改 controller、不改 inference。

## Changes Made

### 1. Freeze one operator instead of a tuning menu
- Reviewer said:
  当前 proposal 还像“诊断 + 可选变换”的流程，不像一个固定算法。
- Action:
  把主方法冻结为唯一算子：`preflight -> clip@q95 -> log1p transform -> per-sample normalize -> alpha=0.85 mixed loss`。
- Reasoning:
  只有冻结 operator，reviewer 才不会把这条线看成 weight tuning。
- Impact on core method:
  主贡献从“stabilize somehow”变成“一个明确可实现、可失败、可复用的 stabilized CSFT operator”。

### 2. Collapse D1 and D2 into one label-validity gate
- Reviewer said:
  proposal 读起来像 troubleshooting checklist。
- Action:
  将 decile check 和 oracle alignment check 合并为统一的 `label validity preflight`。
- Reasoning:
  这样方法结构更像：先验证 supervision 是否可信，再训练；而不是两条并行 debug 分支。
- Impact on core method:
  方法叙事更像单一训练配方，而不是研究日志。

### 3. Pre-register pass/fail acceptance criteria
- Reviewer said:
  需要清楚的 success criterion，否则不像方法贡献。
- Action:
  明确规定 softened-CSFT 要满足的最小通过条件。
- Reasoning:
  这既能防止事后解释，也能把负结果转化成可发表的 falsification logic。
- Impact on core method:
  论文不再依赖模糊的“看起来更好”，而是依赖预先定义的机制验证标准。

## Revised Proposal

# Research Proposal: Preflight-Validated CSFT for Forecast-Then-Control

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
The negative pilot changes the nature of the problem. The missing piece is no longer merely “use controller sensitivity.” The missing piece is **how to decide whether a controller-derived supervision signal is valid enough to train on**.

Current evidence suggests two concrete failure channels:
1. the raw slot-wise finite-difference labels may be too spiky/noisy to act as stable loss weights;
2. the oracle path may be misaligned, which would poison both upper-bound interpretation and label quality.

So the smallest adequate intervention is not a broader method. It is a **preflight-validated, fixed stabilization operator** for controller-sensitive supervision.

## Method Thesis
- One-sentence thesis:
  Controller-sensitive forecast training should not use raw finite-difference labels directly; it should first pass a label-validity preflight and then apply a single fixed stabilization operator before mixed weighted training.
- Why this is the smallest adequate intervention:
  The backbone, controller, environment, and inference path remain unchanged. Only the training weights are repaired.
- Why this route is timely in the foundation-model era:
  The failure is not due to insufficient model size. It is due to bad supervision. Repairing supervision is the most direct scientific next step.

## Contribution Focus
- Dominant contribution:
  A fixed, diagnosis-driven stabilized CSFT operator for converting raw controller sensitivities into trainable forecast weights.
- Optional supporting contribution:
  A label-validity preflight that determines whether controller-derived labels are trustworthy enough to supervise training.
- Explicit non-contributions:
  No new controller, no new backbone, no RL, no routing, no multi-domain transfer, no search over many weighting recipes.

## Proposed Method
### Complexity Budget
- Frozen / reused backbone:
  Current GRU forecaster, current CityLearn data path, chronological split, fixed `qp_carbon` controller, and existing uniform/CSFT checkpoints.
- New trainable components:
  None.
- Tempting additions intentionally not used:
  Multiple transforms, smoothing variants, fallback modules, bucketed-weight method as main route, backbone expansion, controller expansion.

### System Overview
```text
existing pipeline:
history + known future exogenous signals
  -> GRU forecaster
  -> forecast trajectory
  -> fixed qp_carbon controller
  -> battery action
  -> CityLearn rollout

training-side method:
raw finite-difference sensitivity labels
  -> label-validity preflight
  -> fixed stabilization operator
  -> mixed weighted loss (alpha=0.85)
  -> softened CSFT rerun
```

### Core Mechanism
- Input / output:
  Same forecasting inputs and outputs as the existing GRU setup.

- Step 1: Label-validity preflight
  Before any retraining, run one unified preflight:
  1. **Oracle alignment check**: compare `build_oracle_forecast(...)` slices to environment-derived future `price/load/solar` values on matched episodes.
  2. **Critical-cell utility check**: compare existing uniform and raw-CSFT checkpoints on sensitivity-decile test error.

  Preflight passes only if:
  - oracle slices are exactly aligned or numerically identical up to a tiny tolerance;
  - the raw label ranking is at least not completely useless, meaning the top-decile error comparison does not show raw-CSFT catastrophically losing precisely where the labels say it should win.

- Step 2: Fixed stabilization operator
  For clipped raw sensitivities `s_(t,h,c)`, define:
  1. clip at train-set 95th percentile:
     `s_clip = min(s, q95_train)`
  2. transform with a fixed monotone compression:
     `u = log1p(s_clip / (median_positive_train + eps))`
  3. per-sample normalize:
     `w_(t,h,c) = u_(t,h,c) / (eps + mean_{h,c}(u_(t,h,c)))`

  This is the only main operator. No alternative transforms are part of the method claim.

- Step 3: Fixed mixed objective
  Train with:

  `L_t = 0.85 * sum ell(yhat, y) + 0.15 * sum w_(t,h,c) * ell(yhat_(t,h,c), y_(t,h,c))`

  where `ell` is Huber loss.

- Why this is the main novelty:
  The method is not “tune some weights.” It is a specific claim: **controller-derived supervision becomes useful only after a validity gate and a fixed stabilization operator**.

### Optional Supporting Component
- Only include if truly necessary:
  None in the main proposal.
- Why it does not create contribution sprawl:
  Removing all auxiliary branches makes the paper cleaner and easier to falsify.

### Modern Primitive Usage
- Which LLM / VLM / Diffusion / RL-era primitive is used:
  None.
- Exact role in the pipeline:
  Not applicable.
- Why this is more natural than an old-school alternative:
  The bottleneck is supervision validity, not representation power.

### Integration into Base Generator / Downstream Pipeline
The method changes only the training-side weighting:
1. reuse existing artifacts to run preflight;
2. if preflight passes, compute stabilized weights with the fixed operator;
3. run one softened-CSFT training run;
4. evaluate with the unchanged `forecast -> qp_carbon -> CityLearn` pipeline.

### Training Plan
1. Run one `label validity preflight` script.
2. If preflight fails, do not proceed to full softened-CSFT; instead downgrade the thesis and pivot.
3. If preflight passes, generate stabilized weights with the fixed operator.
4. Run one softened-CSFT rerun on GPU 2.
5. Evaluate against uniform and raw-CSFT on forecast metrics, top-decile metrics, and control KPIs.
6. Only after a positive signal decide whether heuristic baselines or matched/mismatched label runs are worth the compute.

### Failure Modes and Diagnostics
- Failure mode: oracle alignment fails.
  - How to detect:
    preflight exact comparison between oracle slices and env truth.
  - Fallback or mitigation:
    fix alignment first; do not interpret any CSFT result before that.
- Failure mode: top-decile utility check fails.
  - How to detect:
    raw-CSFT clearly loses on the highest-sensitivity decile.
  - Fallback or mitigation:
    abandon raw slot-wise sensitivity as supervision; do not scale this line.
- Failure mode: stabilized operator improves top-decile cells but degrades aggregate forecast too much.
  - How to detect:
    top-decile MAE decreases but overall MAE degrades beyond tolerance.
  - Fallback or mitigation:
    conclude the direction is too costly in aggregate accuracy for the current setting.
- Failure mode: stabilized operator improves forecast-side critical cells but not control KPIs.
  - How to detect:
    no meaningful `cost/carbon/peak` gain vs uniform.
  - Fallback or mitigation:
    narrow claim to forecast-side alignment only, or stop this paper direction.

### Novelty and Elegance Argument
The clean scientific question is:

> Under what conditions can controller-derived sensitivity act as valid supervision for forecasting?

The answer proposed here is deliberately narrow and falsifiable:

> Only after passing a label-validity preflight and a fixed stabilization operator.

This is more paper-like than an open-ended repair loop because it defines one operator, one gate, and one pass/fail rule.

## Claim-Driven Validation Sketch
### Claim 1: A controller-sensitive supervision signal should only be trusted if it survives a preflight validity check
- Minimal experiment:
  Run the unified preflight on existing checkpoints and artifacts.
- Baselines / ablations:
  raw oracle slices vs env truth; uniform vs raw-CSFT on decile-wise test error.
- Metric:
  oracle alignment error; decile-wise MSE/MAE.
- Expected evidence:
  If preflight fails, the raw route is invalid and should not be scaled.

### Claim 2: The fixed stabilization operator should recover better control-critical fitting than raw CSFT without materially breaking aggregate forecasting
- Minimal experiment:
  One rerun with the frozen stabilized operator.
- Baselines / ablations:
  uniform, raw-CSFT, stabilized-CSFT.
- Metric:
  top-decile MAE, overall MAE, `cost`, `carbon`, `peak`.
- Expected evidence:
  stabilized-CSFT should beat raw-CSFT on top-decile MAE and avoid significant overall MAE collapse.

### Claim 3: The method survives only if it clears a pre-registered acceptance criterion
- Minimal experiment:
  Evaluate the single softened rerun against the acceptance rule.
- Baselines / ablations:
  stabilized-CSFT vs uniform.
- Metric:
  the acceptance rule itself.
- Expected evidence:
  The method is considered viable only if all three conditions hold:
  1. top-decile MAE is lower than uniform,
  2. overall MAE is not worse than uniform by more than 1%,
  3. at least one primary KPI (`cost` or `carbon`) improves, and `peak` does not worsen by more than 1%.

## Experiment Handoff Inputs
- Must-prove claims:
  raw controller sensitivity is not automatically valid supervision; a fixed preflight + stabilization operator can make it usable in this setting.
- Must-run ablations:
  uniform vs raw-CSFT decile analysis; oracle alignment preflight; one stabilized-CSFT rerun.
- Critical datasets / metrics:
  current CityLearn split, existing checkpoints, existing label files, overall MAE/MSE, decile-wise MAE/MSE, `cost/carbon/peak/ramping`.
- Highest-risk assumptions:
  that preflight does not immediately kill the route, and that a single fixed operator is enough to recover useful weighting signal.

## Compute & Timeline Estimate
- Estimated GPU-hours:
  Very low for preflight, low for one rerun.
- Data / annotation cost:
  None.
- Timeline:
  Preflight first, one rerun second, then stop/go decision.
