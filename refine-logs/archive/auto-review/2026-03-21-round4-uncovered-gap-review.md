# Auto Review Note: Round 4 未覆盖缺口盘点（2026-03-21）

## 1. 目标

这份 review 不直接发起代码实现，而是回答：

> 在用户的 critical review 里，当前还有哪些点没有真正覆盖到？

## 2. 当前已覆盖

已覆盖的 critical review 点：

1. 低层不是只有 `GRU`
2. protocol 不再只有四段等长切换
3. 真实 `LLMRouter.route()` 已实现最小 prompt-only 版本

## 3. 当前仍未覆盖完

### 3.1 `QP` vs 更强控制 baseline

当前仍未做：

- 新的 controller family
- `QP` vs 更强 optimization / heuristic / MPC baseline 的系统比较

当前只能说：

- `QP` 是 working backbone
- 不是已证明最优 controller

### 3.2 更强统计证据

当前主协议已经从 default 升级到 event-driven，但仍然主要是单个场景、单个 episode。

还缺：

- 多 episode
- 统计区间
- 更稳定的 margin 估计

### 3.3 OOD / transfer

当前仍未进入。

## 4. 本轮怎么处理这些缺口

本轮不强行同时实现它们，而是做下面两件事：

1. 在结果文档中明确写出这些缺口仍然存在。
2. 用 backbone 扩展来先回答“high-level 结论到底有多依赖 low-level”。

## 5. 为什么本轮不直接做 controller baseline

因为当前最强的不确定性仍然在 backbone 层。

如果现在同时引入新 controller family，那么：

- forecasting backbone 变了
- high-level protocol 变了
- controller family 也变了

结果仍然很难解释。

所以更合理的顺序是：

1. 先把 backbone 试够
2. 再单开一轮 controller baseline review + experiment

## 6. Round 4 之后的计划入口

如果 Round 4 证明 backbone 扩展后排序仍不稳定，则下一轮优先继续 low-level / protocol 收敛。

如果 Round 4 证明 event-driven 下排序开始稳定，则下一轮优先补：

- controller baseline
- 多 episode / 统计证据
