# Final Proposal

## 结论

第一篇主论文不该继续押在 language-conditioned routing 上。当前最强、最稳、最像方法论文的主线是：

> **Uniform forecast accuracy is the wrong training target for fixed forecast-then-control. Forecast training should prioritize the future errors that the frozen controller actually cares about.**

这条线和当前仓库最匹配。因为仓库已经有稳定的 `forecast -> QP -> CityLearn` 主闭环，也已经出现了 controller-family 和 backbone diagnosis 的实证信号。现在最该做的不是继续扩高层 router，而是把 fixed controller 的 sensitivity 变成 forecast-side supervision。

## 问题锚点

### Bottom-line problem
在外生时间序列驱动控制里，更好的 forecast 不应该只体现在平均误差更低，还要稳定转化成更好的下游控制 KPI。

### Must-solve bottleneck
固定 controller 只对少数 future windows / channels 真正敏感，但标准 forecast training 对所有预测误差基本一视同仁。这个错配会让更强的 forecaster 也拿不到稳定的控制收益。

### Non-goals
- 不做新的 time-series foundation model
- 不做新的 low-level controller
- 不把 LLM / router 作为第一篇主贡献
- 不做 full differentiable decision-focused training through the whole control loop
- 不把 Grid2Op transfer 塞进第一篇主论文

### Constraints
- 从当前 CityLearn 主路径出发
- 固定 low-level QP stack
- 用 modest compute 完成第一版
- 只保留一条清楚机制和一套最小验证包

### Success condition
在相同 controller 下，新的 forecast training 方法相对 uniform loss 带来更稳定的 `cost / carbon / peak` 改善；这些改善能被追溯到 controller-critical future cells 上的 forecast error 更低。

## 为什么当前 router 主线不适合当第一篇论文

结论很直接。当前 router 方向还不够强。

原因有三点：
1. `text / numeric / heuristic` router 的结果还没把 language necessity 立住。
2. 当前最强的 `text_router_v4` 也更像 constrained expert routing，不像必须由 LLM 才能完成的科学问题。
3. reviewer 最容易问的一句就是：**为什么不用 numeric preference vector 或 rule router？** 当前证据还防不住这句。

所以 router 更适合作为：
- 未来单独一篇小论文
- appendix motivation
- 或第二阶段扩展

但不适合作为第一篇 CCF-A / NeurIPS 风格主线。

## 最终方法主张

### 方法名
**Controller-Sensitive Forecast Training (CSFT)**

### 一句话 thesis
固定 forecast-then-control 里，forecast loss 应该按 frozen controller 的局部敏感度重加权，而不是按 uniform error 学习。

## 方法设计

### 固定不动的部分
- CityLearn environment
- 当前数据准备与窗口数据集
- 一个主 forecasting backbone
- 主 controller：`qp_carbon`
- 推理路径：`forecast -> qp_carbon -> CityLearn`

### 新增的部分
只新增两样：
1. **离线 sensitivity label generation**
2. **mixed weighted forecast loss**

不新增新的 planner，不新增新的 trainable controller，也不引入第二个主模型。

## 核心机制

### 1. 对每个 training sample 生成 controller sensitivity map
对每个 sample 的 oracle future `y_t`，对每个 forecast cell `(h, c)` 做有限差分扰动：

- `y+ = y_t + δ_c e_(h,c)`
- `y- = y_t - δ_c e_(h,c)`

然后把 `y+` 和 `y-` 都送入固定 `qp_carbon` controller，计算对应 first-step action 下的一步 stage objective 变化。

定义 sensitivity：

` s_(t,h,c) = |ℓ_t(a+) - ℓ_t(a-)| / (2 δ_c) `

这里的 `ℓ_t` 用 controller 的一步目标，而不是长 rollout regret。这样更轻，也更贴当前 repo 的 fixed-QP 主路径。

### 2. 对 sensitivity 做稳定化
直接用原始 sensitivity 会太噪。

所以先做两步：
- 训练集 95 分位截断
- 样本内归一化

得到 `ŝ_(t,h,c)` 作为最终 loss weight。

### 3. 用 mixed weighted loss 微调 forecaster
主 loss 用混合形式：

` L_t = α * Σ ell(yhat, y) + (1-α) * Σ ŝ_(t,h,c) * ell(yhat_(t,h,c), y_(t,h,c)) `

推荐：
- `ell = Huber` 或 `MAE`
- `α = 0.5` 起步

原因很直接。纯 weighted loss 容易过度盯住少数 spikes，把整体 forecast 搞坏。mixed loss 更稳。

## 为什么这条机制更像论文而不是工程 patch

结论是：它讲的是一个真正的方法问题。

这条方法不是“再加个模块”。它回答的是：

> 在 fixed forecast-then-control 里，哪些 forecast errors 值得模型优先学习？

这比继续堆 backbone、继续换 controller、继续做 router prompt engineering 都更像可以独立成立的方法论文。

## 最小实验包

### 主设置
- **1 个主 backbone**：选当前最稳的可训练模型
- **1 个主 controller**：`qp_carbon`
- **1 个主环境**：CityLearn
- **chronological split**：train 70% / val 10% / test 20%

### 主 baselines
1. uniform-loss forecaster
2. manual horizon weighting
3. event-window weighting
4. proposed CSFT
5. oracle-forecast upper bound

### 必做 ablations
1. **matched vs mismatched controller labels**
   - 用 `qp_carbon` sensitivity 训练
   - 用 `qp_current` sensitivity 训练
   - 都在 `qp_carbon` 下评估
2. **mixed vs pure weighted loss**
3. **event-only vs finite-difference weighting**

### test views
1. standard test
2. carbon / price stress subset
3. peak-load stress subset

### 核心指标
#### Forecast side
- overall RMSE / MAE
- top-sensitivity-decile RMSE / MAE

#### Control side
- total cost
- total carbon
- peak load
- 可选 aggregate score 作为辅指标

## 最关键的防守图

最重要的图不是 giant benchmark table。

最重要的图是：

> **Forecast error reduction vs controller-sensitivity decile**

如果 CSFT 真的在高敏感度 decile 上明显降低误差，而 overall RMSE 变化不大，同时下游 `cost / carbon` 更好，这个机制就立住了。

第二关键图是：
- `qp_carbon` 下的平均 sensitivity heatmap

## 什么结果能把论文从“能讲”推到“接近能投”

如果出现下面这个模式，这篇论文就明显站住了：

1. CSFT 相对 uniform loss 在 `cost / carbon` 上持续改善
2. 没有明显 peak 退化
3. heuristic weighting 明显输给 CSFT
4. matched-controller labels 明显优于 mismatched labels
5. CSFT 对 oracle gap 有非平凡收缩
6. 高敏感度桶上的 forecast error 下降明显，大于低敏感度桶

## routing 应该怎么处理

### 结论
**不进主结果。**

它最多做两件事里的一个：
1. appendix 里的 motivation experiment
2. future work

不要再让 routing 主线稀释第一篇论文。

## 风险

### 风险 1：finite-difference sensitivity 太噪
应对：
- clipping
- per-sample normalization
- 先做 label pilot
- 必要时只把 hybrid 作为工程 fallback，不升格为主方法

### 风险 2：只提升 forecast，不提升 control
应对：
- 用 stress subsets
- 强制对照 heuristic weighting
- 做 top-decile error vs KPI 的机制分析

### 风险 3：提升太小
应对：
- 先只保留一个 backbone + 一个 controller
- 先把 matched/mismatched 和 decile analysis 做强
- 不要过早摊到多 backbone、多环境

## 最终建议

1. 冻结 low-level `forecast + qp_carbon` 主闭环。
2. 不再把 language routing 当第一篇主线。
3. 先实现 A1：finite-difference controller sensitivity weighting。
4. 先跑最小 claim-driven experiment package。
5. 等 CSFT 主结果站稳后，再决定 routing 是 appendix 还是第二篇。
