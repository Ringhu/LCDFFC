# Auto Review Note: Round 7 Controller Diagnosis（2026-03-21）

## 1. 本轮问题定义

用户的核心质疑是：

> foundation model 的 zero-shot forecasting 已经很强，但接到当前 `QP` 控制器后，下游收益没有按预期完全兑现。这是不是 `QP` 本身的问题？

这个质疑是成立的，而且需要通过新的 controller round 来回答，而不是继续扩 forecasting backbone。

## 2. 当前必须先澄清的事实

### 2.1 当前主控制链路里，`carbon` 目标实际上没有真正进入 QP

代码审查后发现：

- `controllers/qp_controller.py` 支持 `carbon_intensity`
- 但 `eval/run_controller.py` 和 `eval/run_foundation_control.py` 在调用 `ctrl.act(...)` 时都没有传这一路输入

这意味着当前很多实验虽然写了：

- `w_carbon > 0`

但控制器真实优化的其实是：

- `cost + peak + smooth`

而不是文档里描述的完整 `cost + carbon + peak + smooth`。

因此，本轮不能只比较不同 controller family，还必须加入一个 **修正信号输入后的 QP 诊断版本**。

### 2.2 zero-shot forecasting 强，不等于 downstream control 一定同步变强

这在当前项目里至少有三类可能原因：

1. forecast metric 与 control objective 不完全一致
2. controller family 本身限制了 forecast 信息的兑现方式
3. controller 目标里有缺失信号或结构失配

所以本轮的目标不是简单证明“QP 好/坏”，而是拆开回答：

- 是 `QP family` 本身有问题
- 还是当前 `QP` 的目标与输入存在结构问题
- 还是 forecasting 改善本来就不会一比一转化成 KPI 改善

## 3. 本轮 review 决策

### 3.1 固定哪些变量

为了把问题收紧，本轮固定：

- backbone：只选当前最强的两个 foundation backbone
  - `moirai2`
  - `timesfm2.5`
- 场景：`citylearn_challenge_2023_phase_1`
- forecast horizon：`24`
- context length：`512`
- 统一控制权重：
  - `cost 0.15`
  - `carbon 0.10`
  - `peak 0.65`
  - `smooth 0.10`
- 统一 `reserve_soc = 0.2`

不再同时混入 router 或 event-driven 偏好切换，避免变量重新缠绕。

### 3.2 需要比较的 controller family

本轮比较 5 类控制策略：

1. `zero_action`
   - 作用：电池完全不控制，作为 battery-only 最低基线

2. `qp_current`
   - 作用：复现当前 round6 的实际 `QP` 路径
   - 特点：不传未来 carbon forecast，只优化当前实际生效的目标

3. `qp_carbon`
   - 作用：在相同 QP family 下修正目标输入
   - 特点：额外预测未来 `carbon_intensity`，并真正传入 QP
   - 目的：回答“问题是不是 QP family 本身，而不是当前 QP 输入少了一路信号”

4. `forecast_heuristic`
   - 作用：不用优化器，直接用 horizon 统计量做充放电
   - 特点：真正不同于 `QP`
   - 目的：回答“如果只靠 forecast-aware rule，会不会更好”

5. `action_grid`
   - 作用：对离散候选动作做一步前瞻评分
   - 特点：不是凸优化，但也不是纯规则
   - 目的：提供一个介于 heuristic 和 QP 之间的 controller baseline

## 4. 需要验证的假设

### H1. 如果 `qp_carbon` 明显优于 `qp_current`

则说明当前问题至少部分来自：

- `QP` 的目标信号缺失

而不能直接下结论说：

- `QP family` 不行

### H2. 如果 `forecast_heuristic` 或 `action_grid` 持续优于 `qp_carbon`

则说明：

- `QP family` 可能确实限制了 foundation forecast 的兑现

### H3. 如果 `qp_carbon` 仍然整体最强或最稳

则更合理的结论是：

- foundation forecast 强但下游不完全兑现，不是因为 `QP` 失效
- 而是 forecast metric 和最终 control KPI 的映射本来就不是单调关系

## 5. 指标与结论判据

主指标：

- `cost`
- `carbon`
- `peak`
- `ramping`

辅助汇总：

- 相对 `zero_action` 的归一化平均比分
- 各 controller 在 4 个 KPI 上的胜负关系

结论判据：

- 如果 `qp_current` 被 `qp_carbon` 明显超过，则先修正 QP 输入，再谈 controller family
- 如果 `qp_carbon` 被 `heuristic / action_grid` 明显超过，则当前 QP 主张必须收紧
- 如果 `qp_carbon` 仍然最强或最稳，则当前问题主要不是“QP 用错了”，而是 objective trade-off 与 forecast-control mismatch

## 6. 实验执行顺序

1. 先实现 controller baseline
2. 在 `GPU 3` 做短程 sanity
3. 在 `GPU 2` 跑完整 episode
4. 汇总结果并单独回答用户的问题：
   - zero-shot 强但加 QP 不完全兑现，究竟是不是 QP 的问题

## 7. 本轮成功标准

本轮成功不要求“某个新 controller 一定超过 QP”，而要求：

- 能把问题定位得更清楚
- 能区分 `QP family` 问题与 `QP 输入/目标定义` 问题
- 给出下一步应不应该继续做 controller baseline round 的明确结论
