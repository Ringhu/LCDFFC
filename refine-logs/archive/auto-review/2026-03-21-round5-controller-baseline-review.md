# Auto Review Note: Round 5 Controller Baseline（2026-03-21）

## 1. 为什么下一步应进入 controller baseline round

Round 4 之后，当前 strongest low-level setting 已经变成：

- `Granite + QP`
- 主协议：event-driven

同时，critical review 里仍未覆盖完的最大缺口是：

> `QP` 只是 working backbone，还没有和其他 controller family 做系统比较。

因此，如果继续往下推进，最合理的下一轮不再是继续扩 forecasting backbone，而是：

- 固定 strongest forecasting backbone：`Granite`
- 固定主协议：event-driven
- 单独比较 controller family

## 2. 候选 controller baseline

### 方案 A：forecast-aware heuristic controller

特点：

- 不解优化问题
- 直接基于未来 price/load/carbon 统计量做 charge/discharge 决策
- 实现成本最低

### 方案 B：greedy one-step controller

特点：

- 每步只看即时收益和约束
- 比 heuristic 更数值化
- 但很可能只是 myopic 的另一种写法

### 方案 C：更一般的 MPC family

特点：

- 学术上更强
- 但与当前 QP controller 的边界太近
- 这一轮里不容易形成“真正不同的 controller family”

## 3. Review 决策

下一轮优先做 **方案 A：forecast-aware heuristic controller**。

理由：

1. 它和 `QP` 在方法形态上真正不同。
2. 它能最直接回答“如果不用优化器，只靠 forecast-aware rule，会怎样”。
3. 它不会把 controller baseline round 重新做成另一个“QP 小改版”。

## 4. 实验设计

固定：

- backbone：`Granite`
- protocol：event-driven

比较：

- `Granite + QP + fixed_peak`
- `Granite + QP + llm_prompt_v1`
- `Granite + forecast-aware heuristic controller`

指标：

- `cost`
- `carbon`
- `peak`
- `ramping`
- event-driven `avg_preference_score`

## 5. 成功标准

- 如果 heuristic controller 接近或超过 `QP`，则当前 `QP` 主张必须显著收紧。
- 如果 heuristic controller 明显更差，则可以更有把握地说：
  - `QP` 至少优于一类不解优化问题的 forecast-aware controller。
