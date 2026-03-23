# 最终方案提案

**日期**：2026-03-19  
**结论**：`需要继续收敛，但在聚焦后已经足够强且可行`

## 问题锚点

这个项目最应该围绕下面这个问题来组织：

> 在外生时间序列驱动的顺序控制问题中，成本、碳排、削峰和韧性之间的期望权衡会随时间变化，但大多数学习型或优化型控制器都只针对一个固定目标进行调参与训练，无法在不重训的前提下自然适配新的高层偏好。

这才是当前最值得解决的问题。  
它比“在 CityLearn 上做 forecasting + control”更尖锐，也更像一篇方法论文的问题定义。

## 为什么当前 broad idea 还不够成熟

当前的 broad idea 同时揉进了太多层内容：

- `forecast + QP`
- uncertainty-aware fallback
- decision-focused training
- LLM preference routing
- 可选的 Grid2Op 迁移验证

作为研究路线图，这没有问题。  
但作为第一篇顶会论文，这样的范围太宽了。

当前仓库其实已经证明了一件很重要的事：

> `forecast + QP` 这条低层闭环本身是可行的，而且在当前本地验证设置下已经优于 `RBC`。

这意味着低层闭环应该被当成**论文平台和基础设施**，而不是论文的主 novelty。

## 最终方法主张

**基于语言条件化的高层目标路由，用于偏好变化场景下的 forecast-then-control。**

更具体地说：

1. 保持当前已经验证通过的 `forecast + QP` 低层控制器不变
2. 将当前控制上下文压缩成结构化摘要
3. 读取人类可解释的高层偏好 / 指令
4. 输出结构化的 `QP` 目标权重与约束
5. 在**不重训低层控制器**的前提下，实现在线适配

## 主贡献

最应该保留的主贡献是：

> 一种面向外生时序控制的、语言条件化的高层目标路由机制，它能够在线修改低层优化器的目标与约束，而不需要重新训练底层预测与控制系统。

这个说法明显强于“我们在能源控制里用了 LLM”。  
同时，它也让 LLM 的角色和当前仓库已有工程现实保持一致。

## 支撑性贡献

最多保留一个支撑性贡献：

> 一个确定性的结构化 fallback，用来在语言层输出不稳定、低置信或不合法时，保证路由结果始终可用且安全。

这类贡献可以增强可部署性与鲁棒性，但不会把论文拖成“两篇论文缝在一起”。

## 明确拒绝的复杂度

为了让论文保持锋利，下面这些内容不应该与主贡献并列：

- 新的 forecasting backbone
- 完整的 decision-focused training 论文叙事
- uncertainty ensemble 作为并列主贡献
- 在 CityLearn 主线尚未讲清之前，就把 Grid2Op 做成必须的第二 benchmark
- LLM 直接输出底层连续动作

## 为什么这个主张是可行的

这条 refined route 是可行的，因为当前 repo 已经有足够稳定的基础层：

- `data/prepare_citylearn.py`
- `data/dataset.py`
- `scripts/train_gru.py`
- `controllers/qp_controller.py`
- `eval/run_rbc.py`
- `eval/run_controller.py`
- `llm_router/prompt_templates.py`
- `llm_router/json_schema.py`

当前缺的不是再造一整套新系统，而是：

1. 一个明确收缩后的高层路由机制
2. 一套能够证明其价值的评测协议

## 当前工程成熟度判断

当前工程成熟度已经不低：

- 低层主闭环已经实现
- 本地复现实验已经存在
- 当前 `learned forecast + QP` 在验证设置中优于 `RBC`
- `learned / oracle / myopic` 三种诊断模式也已经具备

这意味着：

- 项目已经**足够成熟，可以支撑一篇真正的方法论文迭代**
- 但还**不够成熟，不能直接宣称自己已经具备完整顶会故事**

## Novelty 判断

### 什么内容本身还不够 novel

下面这些内容单独拿出来，还不足以形成强 CCF-A novelty：

- 在 CityLearn 上做 GRU forecasting
- 在 CityLearn 上做 QP control
- 用一个调得更好的 forecast-control loop 超过 RBC
- “LLM 输出 objective weights”，但没有更锋利的主张

这些都算是扎实工程结果，但还不够构成顶会级别的方法贡献。

### 什么方向可能足够 novel

当且仅当论文能证明下面几件事时，这个方向才开始变得真正有希望：

1. 控制器能够在**不重训**的情况下适配变化中的高层偏好
2. 语言是一个真正有意义的接口，而不只是装饰
3. 低层控制效果在偏好变化时仍然保持竞争力甚至更优
4. 更简单的替代方法不能完全解释掉这部分收益

也就是说：

当前 novelty 不是已经站稳了，而是**在聚焦之后有潜力站稳**。

## 与附近工作的关系

这个 refined idea 处在三类相关工作的交叉点：

### 1. CityLearn / 层次化 / 优化控制

现有 CityLearn 工作已经说明：

- 优化式控制是合理路径
- 层次化控制是合理路径

所以论文不能再把 novelty 写成“forecast + control 这个组合存在”。

### 2. Decision-focused learning

这类工作说明：

- 预测的价值应该通过下游决策质量来衡量

但这并不意味着你必须在第一篇论文里就把 DFL 作为主贡献。

### 3. LLM for control / optimization / energy systems

现有工作越来越说明：

- 当 LLM 充当高层 planner、interface、optimizer assistant 时，最容易被接受
- 当 LLM 直接做低层数值控制时，最容易被质疑

这恰好支持了当前 refined route 中 LLM 的放置方式。

用于这次判断的代表性参考包括：

- CityLearn benchmark / 环境：https://pypi.org/project/citylearn/
- CityLearn challenge 获胜优化式控制器：https://jinming.tech/papers/2023-aaai-citylearn-winning-solution.html
- 集群能量管理中的层次化 RL-MPC：https://doi.org/10.1016/j.enbuild.2025.116879
- 基于 LLM 的可解释建筑控制：https://dblp.org/rec/journals/corr/abs-2402-09584
- 面向能量管理的 decision-focused / robust optimization：https://doi.org/10.1016/j.apenergy.2025.127343

## 什么样的版本会更像一篇 CCF-A 论文

一旦论文能够明确说出下面这句话，它就会比现在成熟很多：

> 我们不是在提出一个新的低层能源控制器。我们提出的是一种新的高层语言接口，使既有的 forecast-control 系统能够在偏好变化时在线适配其控制目标。

这个 thesis 明显比当前“路线图式大合集”更清楚、更锋利，也更像可发表论文。

## 最终建议

### 成熟度

- **当前工程成熟度**：已经足够支撑论文迭代
- **当前论文成熟度**：还不够，需要继续收缩

### 可行性

- **基础系统可行性**：高
- **收缩后论文的可行性**：高

### Novelty

- **当前已实现部分的 novelty**：不足以支撑强 CCF-A 论文
- **收缩后方案的 novelty**：有潜力，但必须通过和更简单替代方案的对照来防守

## 最优下一步

现在不应该继续扩系统。

最应该做的是：

1. 冻结当前低层 `forecast + QP` 主循环
2. 实现一个最小高层路由器
3. 构造 `preference-shift` 评测协议
4. 让语言条件路由与更简单的结构化路由正面对比

如果这几步结果为正，这个想法就会比现在更接近真正的 paper-ready 状态。
