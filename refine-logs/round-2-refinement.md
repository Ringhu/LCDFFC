# Round 2 Refinement

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
  With the same controller, the proposed training method should produce more consistent cost / carbon / peak improvements than plain uniform forecast training, and the gain should be traceable to better accuracy on controller-critical future windows.

## Anchor Check
- Original bottleneck:
  预测误差没有区分哪些 future slots 真正影响固定控制器的下游目标。
- Why the revised method still addresses it:
  这版方法只改 forecast loss，不改 controller，不改 inference path。它直接把 controller sensitivity 变成训练监督。
- Reviewer suggestions rejected as drift:
  把论文主线放到 language routing、fallback robustness、Grid2Op transfer，都会把第一篇论文从 forecast-control bottleneck 上带偏。

## Simplicity Check
- Dominant contribution after revision:
  Controller-Sensitive Forecast Training, CSFT。
- Components removed or merged:
  去掉 language-conditioned router 作为主贡献；去掉 uncertainty / fallback 作为主贡献；不再把 backbone zoo 当论文主体。
- Reviewer suggestions rejected as unnecessary complexity:
  不做 full differentiable decision-focused training；不做长 rollout regret 主损失；不做多环境大扩展。
- Why the remaining mechanism is still the smallest adequate route:
  它只新增离线 sensitivity label 生成和一个 weighted forecast loss，其他训练 / 推理路径都沿用当前稳定主栈。

## Changes Made

### 1. 论文锚点从 high-level routing 改回 forecast-side bottleneck
- Reviewer said:
  language routing 目前更像 wrapper，不像第一篇顶会主线。
- Action:
  主线改成 controller-sensitive forecast refinement。
- Reasoning:
  当前仓库最强信号来自固定 controller 下不同 forecast/controller choices 的 KPI 变化，不是 language superiority。
- Impact on core method:
  论文 claim 从“在线偏好路由”改成“uniform forecast loss 不适合 forecast-then-control”。

### 2. 主方法收缩到 A1
- Reviewer said:
  A1 finite-difference controller sensitivity 是最干净的最小方法；A2 适合作 baseline；A4 太重。
- Action:
  采用 A1 作为主方法，A2 作为 heuristic baseline，A3 只作为工程 fallback 预案，不写成主贡献。
- Reasoning:
  A1 最贴 thesis，也最容易用现有固定 QP controller 实现。
- Impact on core method:
  方法边界清楚，validation 也更容易闭合。

### 3. 主实验包大幅收缩
- Reviewer said:
  只保留一个主 controller、一个主 backbone、少量关键 ablations。
- Action:
  主实验固定 `qp_carbon`；主 backbone 只保留一个稳定可训练模型；主 ablations 只保留 3 组。
- Reasoning:
  先把机制讲清，再决定要不要补 foundation replication。
- Impact on core method:
  claim 和实验一一对应，不再是路线图式大合集。

## Revised Proposal

# Research Proposal: Controller-Sensitive Forecast Training for Fixed Forecast-Then-Control

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
  With the same controller, the proposed training method should produce more consistent cost / carbon / peak improvements than plain uniform forecast training, and the gain should be traceable to better accuracy on controller-critical future windows.

## Technical Gap
当前主路径已经说明，单纯把 forecasting 做出来不够。固定 controller 的目标函数只依赖一小部分未来窗口和通道，但常规 forecasting loss 对所有 horizon / channel 基本一视同仁。结果是模型可能在平均误差上更好，却没有把容量用在真正影响 `cost / carbon / peak` 的位置。

更大的 backbone 不是直接答案。因为 capacity 还是可能被浪费在对控制几乎不敏感的 future slots 上。完整 end-to-end decision-focused training 也不是第一篇该走的路。它更重、更难稳，而且会把当前已经跑通的 forecast + fixed-QP decomposition 一起搅乱。

缺的不是新的 controller。缺的是一个小而直接的机制：把固定 controller 对 future forecast cell 的敏感度，变成 forecast training 的监督。

## Method Thesis
- One-sentence thesis:
  Uniform forecast accuracy is the wrong training target for forecast-then-control; a frozen controller can provide per-slot sensitivity signals that reweight forecast training toward controller-critical future cells.
- Why this is the smallest adequate intervention:
  Environment、controller、inference path、forecast architecture 都不变，只新增离线 sensitivity label 和 weighted loss。
- Why this route is timely in the foundation-model era:
  当前真正缺的不是再做一个 backbone，而是让已有 backbone 在 forecast-then-control 场景里更接近真实决策目标。

## Contribution Focus
- Dominant contribution:
  A controller-sensitive forecast training recipe that uses frozen-QP finite-difference sensitivities as supervision for weighted forecast refinement.
- Optional supporting contribution:
  A controller-matched vs mismatched-label analysis showing the weighting signal is not generic importance, but controller-specific importance.
- Explicit non-contributions:
  No new controller, no new foundation model, no language router as a main claim, no full decision-focused differentiable training stack.

## Proposed Method
### Complexity Budget
- Frozen / reused backbone:
  CityLearn data path, existing dataset windows, one existing forecast backbone, and the current `qp_carbon` controller.
- New trainable components:
  No new trainable module is required. The method adds offline sensitivity-map generation and a mixed weighted forecast loss.
- Tempting additions intentionally not used:
  Free-form routing, uncertainty ensemble, fallback robustness as paper claim, Grid2Op transfer, end-to-end RL, backbone zoo.

### System Overview
```text
history + known future exogenous signals
  -> forecasting backbone
  -> future exogenous trajectory forecast
  -> fixed qp_carbon controller
  -> battery action
  -> CityLearn rollout

training-only side path:
training sample + oracle future + fixed qp_carbon
  -> per-slot finite-difference sensitivity map
  -> normalized controller-sensitive weights
  -> mixed weighted forecast loss
```

### Core Mechanism
- Input / output:
  输入和当前 forecaster 一样，输出仍然是 controller 消费的 future exogenous trajectory。
- Architecture or policy:
  Forecast backbone 不变。`qp_carbon` controller 不变。新机制是对每个训练样本生成 `H x C` 的 local sensitivity map。
- Offline label generation:
  对于每个 sample 的 oracle future `y_t` 和每个 forecast cell `(h, c)`，构造
  - `y+ = y_t + δ_c e_(h,c)`
  - `y- = y_t - δ_c e_(h,c)`
  然后分别送入固定 `qp_carbon` controller，得到对应 first-step action 下的一步 stage objective `ℓ_t(a+)` 与 `ℓ_t(a-)`。

  定义 sensitivity:

  `s_(t,h,c) = |ℓ_t(a+) - ℓ_t(a-)| / (2 δ_c)`

  其中 `δ_c` 按通道标准差缩放，初始设成 `0.1 * std(channel c)`。
- Weight normalization:
  对 `s_(t,h,c)` 先做训练集 95 分位截断，再在样本内归一化：

  `ŝ_(t,h,c) = s_(t,h,c) / (eps + mean_{h,c}(s_(t,h,c)))`

- Training signal / loss:
  用 mixed weighted loss，而不是纯 weighted loss：

  `L_t = α * Σ ell(yhat, y) + (1-α) * Σ ŝ_(t,h,c) * ell(yhat_(t,h,c), y_(t,h,c))`

  其中 `ell` 用 Huber 或 MAE，`α` 从 `0.5` 起步。
- Why this is the main novelty:
  这不是 hand-crafted event rule，也不是 full DFL。它把固定 controller 的局部敏感度直接抽出来，变成 forecast-side supervision。

### Optional Supporting Component
- Only include if truly necessary:
  无。第一版 proposal 不引入额外 trainable auxiliary head。
- Why it does not create contribution sprawl:
  把主线压到一条机制上，避免第二个 trainable module 稀释论文说法。

### Modern Primitive Usage
- Which foundation-model-era primitive is used:
  没有必须的 LLM / RL / Diffusion 组件。foundation TS model 最多只作为后续 replication backbone，不进主 claim。
- Exact role in the pipeline:
  如果后续补 foundation replication，它只是 numeric backbone。
- Why this is more natural than an old-school alternative:
  这篇论文的核心不是 modern primitive，而是 decision-relevant forecast supervision。这里保持保守，反而更稳。

### Integration into Base Generator / Downstream Pipeline
方法挂在训练阶段，不改推理路径。

1. 用当前标准 loss 训练或复用 baseline forecaster。
2. 在训练集上用固定 `qp_carbon` 生成 sensitivity map。
3. 用 mixed weighted loss 微调同一个 forecaster。
4. 推理时仍然走原来的 `forecast -> qp_carbon -> CityLearn`。

这保证主系统结构不变，工程风险也最低。

### Training Plan
1. 选一个稳定的主 forecasting backbone。
2. 用当前标准 loss 训练 uniform baseline。
3. 对训练样本生成 `qp_carbon` sensitivity labels。
4. 做截断、归一化和样本缓存。
5. 用 mixed weighted loss 微调得到 CSFT 模型。
6. 只在主 backbone 上完成完整实验。
7. 如果主结果为正，再决定是否补一个 foundation replication。

### Failure Modes and Diagnostics
- Sensitivity label 太噪：
  用 rank correlation、邻近窗口平滑和样本内分布看稳定性。必要时只做 top-k mask pilot，但不把它写成主方法。
- Weighted loss 只提升少数 spike，拖坏整体 forecast：
  比较 `α=0.5` 与 `α=0`，用 mixed loss 兜底。
- 下游 KPI 提升不明显：
  对照 `top-sensitivity decile` forecast error 是否真的下降。如果没有，就说明 sensitivity labels 本身没有提供有效监督。
- 结果被 reviewer 说成 heuristic reweighting：
  用 `event-only` baseline 和 `mismatched-controller labels` ablation 防守。

### Novelty and Elegance Argument
论文只讲一句话：

> 在固定 forecast-then-control 系统里，uniform forecast loss 学错了目标；forecast training 应该优先修正 controller 真正在意的 future errors。

这比 routing、fallback、uncertainty、multi-domain transfer 的大合集更集中，也更符合当前仓库已经有的稳定基础设施。

## Claim-Driven Validation Sketch
### Claim 1: Controller-sensitive forecast training improves downstream KPIs more reliably than uniform forecast training
- Minimal experiment:
  同一个 backbone、同一个 `qp_carbon` controller，对比 uniform loss vs CSFT。
- Baselines / ablations:
  uniform loss、manual horizon weighting、event-window weighting。
- Metric:
  total cost、total carbon、peak load，以及 relative gap-to-oracle。
- Expected evidence:
  CSFT 在标准测试和 stress subset 上都比 uniform loss 更稳，且优于 heuristic weighting。

### Claim 2: The gain comes from protecting controller-critical forecast cells, not blanket accuracy improvement
- Minimal experiment:
  把 forecast cells 按 sensitivity decile 分桶，比较 uniform vs CSFT 的 error reduction。
- Baselines / ablations:
  uniform loss vs CSFT。
- Metric:
  overall RMSE/MAE、top-sensitivity-decile RMSE/MAE、error reduction vs sensitivity decile plot。
- Expected evidence:
  overall forecast error变化不大，但高敏感度桶下降明显。

### Claim 3: The weighting signal is controller-specific rather than generic importance
- Minimal experiment:
  用 `qp_carbon` labels 训练 CSFT；再用 `qp_current` labels 训练同样的模型；都在 `qp_carbon` 下评估。
- Baselines / ablations:
  matched-controller labels vs mismatched-controller labels。
- Metric:
  downstream KPI delta、top-decile forecast error、gap-to-oracle closure。
- Expected evidence:
  matched labels 明显比 mismatched labels 更有效。

## Experiment Handoff Inputs
- Must-prove claims:
  uniform loss 不适合 fixed forecast-then-control；controller-sensitive labels 能带来 controller-specific 的 forecast refinement；这种 refinement 会转化成稳定下游 KPI 提升。
- Must-run ablations:
  uniform、manual horizon weighting、event-window weighting、CSFT、mismatched-controller labels、mixed vs pure weighted loss。
- Critical datasets / metrics:
  CityLearn 2023 单一主设定；chronological split；standard / carbon-price stress / peak-load stress 三种 test view；cost / carbon / peak + top-decile forecast error。
- Highest-risk assumptions:
  sensitivity labels 必须足够稳定；CSFT 不能只是“看起来有道理”，而要在 heuristic baselines 之上给出清楚增益。

## Compute & Timeline Estimate
- Estimated GPU-hours:
  训练本身不高。主要额外成本在离线 sensitivity label 生成，但这比 full end-to-end DFL 轻很多。
- Data / annotation cost:
  无人工标注。labels 全来自固定 QP controller 的 perturbation solves。
- Timeline:
  先做 label generation pilot 和 1 个 backbone 小规模训练；一旦 sensitivity plot 有信号，再扩到完整 test / ablations。
