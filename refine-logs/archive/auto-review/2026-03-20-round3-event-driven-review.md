# Auto Review Note: Event-Driven Preference Protocol（2026-03-20）

## 当前问题

现有 `cost / carbon / peak / reserve` 四段等长协议，优点是简单，但缺点也很明显：

- 不像真实运营侧偏好切换
- regime 持续时间固定，过于理想化
- 很容易把 router 问题简化成“识别当前段标签”

用户关于“什么样的偏好切换是好的、如何切换、如何作为 baseline”的质疑，必须靠新的协议来回答。

## 候选做法

### 方案 A：随机切换

优点：
- 容易实现

缺点：
- 不可解释
- 很难说这是“好的偏好切换”

### 方案 B：基于外部事件的 event-driven 切换

候选触发：
- 价格异常高 -> `cost`
- 碳强度异常高 -> `carbon`
- 未来负荷峰值高 / 电网压力高 -> `peak`
- 未来风险高但当前仍有准备窗口 -> `reserve`

优点：
- 可解释
- 与真实运营语义更接近
- 可以自然地产生不等长 segment

缺点：
- 需要定义阈值和最短持续时间

## Review 决策

选择 **方案 B**。

## 协议设计

1. 用 oracle 序列预先扫描整个 episode。
2. 对未来短窗统计量做 quantile-based event detection：
   - price score
   - carbon score
   - load/peak score
   - future-risk score
3. 每个 step 只分配一个 dominant regime。
4. 引入两个稳定机制：
   - `min_segment_len`
   - `cooldown / persistence`
5. `reserve` 不再依赖当前真实 SOC，而依赖“未来风险高、当前尚未进入直接冲击段”的准备语境。

## 为什么这样设计合理

- 它回答的是“运营者为什么此刻会发出某种高层指令”，而不是“我们想把 episode 均匀切成四块”。
- `reserve` 作为一种准备策略，本来就更应该由未来风险触发，而不是由等长切段硬塞出来。
- 定量阈值和最短持续时间能减少 label jitter，让 router 的难度更接近真实高层决策。

## baseline 设计

在新协议下，至少比较：

- `fixed_balanced`
- `fixed_cost`
- `fixed_carbon`
- `fixed_peak`
- `fixed_reserve`
- `heuristic`
- `text_best`

这样可以回答：

- 单一固定偏好够不够
- 简单规则路由够不够
- 当前最佳文本 surrogate 是否仍然有增益

## 成功标准

如果 event-driven 协议下：

- fixed expert 排名明显改变
- `text_best` 的优势消失或翻转

则说明旧协议过弱，后续论文必须改用新协议或至少同时报告两者。

如果 relative ordering 基本稳定：
- 则说明旧协议虽然理想化，但没有完全误导结论
