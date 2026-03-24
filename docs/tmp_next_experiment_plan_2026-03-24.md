# Next experiment plan（temporary, 2026-03-24）

当前下一步不该再堆 router 版本。下一步应该先把 corrected low-level stack 固定下来，再用最强 backbone 跑最小 routing 矩阵，最后补统计证据。

## 1. Review 结论

当前工程里最真实的问题不是 QP family 本身弱，而是主实验链路里的 controller 输入还不一致。

直接证据有三处：

- `eval/run_foundation_control.py:79` 到 `eval/run_foundation_control.py:85` 调 `ctrl.act(...)` 时没有传 `carbon_intensity`。
- `eval/run_preference_shift.py:337` 到 `eval/run_preference_shift.py:343` 现在也是只传 `forecast / weights / constraints`，没有传未来 carbon 预测。
- `eval/run_foundation_controller_compare.py:96` 到 `eval/run_foundation_controller_compare.py:120` 已经把 `qp_current` 和 `qp_carbon` 区分清楚了，这个脚本是当前最接近正确 low-level 对照的实现。

Round 7 结果已经说明结论：

- `qp_carbon` 比 `qp_current` 稳定更好，但增益不大。
- 非 QP controller 没打过 QP。
- foundation forecast 强，不会自动按 forecasting 排名兑现到控制 KPI。

所以接下来的实验顺序应该是：

1. 固定 corrected QP 参考栈。
2. 在最强 backbone 上重跑最小 routing 矩阵。
3. 给主结论补多 episode / 置信区间。
4. OOD / transfer 以后再做，不要插到这轮前面。

## 2. 本轮要回答的核心问题

当前最值得回答的是三个问题。

### Q1. corrected QP 作为统一 low-level 参考后，backbone 排名怎么变？

这决定后面 routing 实验到底该绑定哪条低层栈。

### Q2. 在 corrected QP 上，event-driven routing 结论还能不能成立？

这决定 paper 还能不能继续讲高层 preference routing，而不是退回纯 backbone/controller 比较。

### Q3. 当前主结果是不是只是一条单 episode 现象？

这决定结果能不能拿去写 reviewer-facing 主表。

## 3. 推荐实验顺序

## Stage A — 固定 low-level reference stack

先做这一段。没做完不要急着再跑更多 router。

### A1. 用 corrected path 复核 foundation backbone 排名

目标很直接：确认 `qp_carbon` 作为 reference 时，最值得保留的 backbone 是哪些。

最小矩阵：

- forecast source:
  - `granite_patchtst`
  - `moirai2`
  - `timesfm2.5`
- controller:
  - `qp_current`
  - `qp_carbon`

要看的指标：

- `cost`
- `carbon`
- `peak`
- `ramping`
- 相对 `zero_action` 的归一化平均分

通过条件：

- `qp_carbon` 在 `moirai2 / timesfm2.5` 上继续稳定优于 `qp_current`。
- `granite` 仍保持 peak 优势，或者至少继续构成明确 trade-off。
- 结果能支持一句稳定说法：
  - `granite + corrected QP` 更偏 peak
  - `moirai2/timesfm + corrected QP` 更偏 cost/carbon/ramping

停下条件：

- 如果 corrected path 改完后 ranking 完全翻盘，而且波动大到没法解释，就先别跑 routing，先查 objective / forecast interface。

### A2. 把 preference runner 的 carbon path 补齐后，做一个 sanity round

目标不是大跑量。目标只是确认 preference-shift runner 不再沿用旧的 low-level 输入缺口。

最小 sanity：

- backbone 先只选 1 条：优先 `granite` 或当前 cost/carbon 更强的 foundation backbone。
- router 只跑：
  - `fixed_balanced`
  - `heuristic`
- schedule 固定：
  - `event_driven`

通过条件：

- runner 能稳定产出 `routes.json / segments.json / kpis.json`
- 指标量级与旧结果同一数量级，不出现明显退化到接近 zero-action 的异常

停下条件：

- 如果 corrected carbon path 一接入就导致 routing runner 行为异常，先修 runner，不扩实验矩阵。

## Stage B — 重跑最小 high-level matrix

只有 Stage A 稳定后才做这一段。

### B1. backbone × router 的最小主表

建议只保留最有信息量的组合，不要再堆 `text_v2~v7`。

backbone：

- `granite_patchtst`
- `moirai2` 或 `timesfm2.5` 二选一；如果算力允许就两个都留

router：

- `fixed_balanced`
- `fixed_cost`
- `fixed_peak`
- `fixed_reserve`
- `heuristic`
- `llm_prompt_v1` 或当前最强文本 router（如果现有 prompt-only 版本就是要评估的对象）

protocol：

- `schedule_type=event_driven`
- 不再把旧 default schedule 当主证据

forecast mode：

- learned backbone 用 learned
- foundation backbone 走对应 foundation runner 路径，不混写成同一个结论

这一步要回答的不是“文本 router 有没有到处都最强”。

这一步要回答的是：

- 在 corrected low-level stack 上，高层 routing 能不能稳定优于单一 fixed policy。
- 这种结论会不会随 backbone 改变而消失。

通过条件：

- 至少在 1 条强 backbone 上，router 明确优于 best single fixed baseline。
- 在另一条 backbone 上，哪怕优势变弱，也要方向一致，或者能解释为什么不一致。

停下条件：

- 如果 router 只在单一 backbone 上成立，其他 backbone 上完全不成立，那 paper 主线就别再写“稳定 routing 增益”，改写成 backbone-sensitive 结论。

### B2. 保留 1 组 corruption / fallback 结果

这一步只保留 reviewer 最关心的一组，不要再横向扩张。

推荐只留：

- corruption: `transition_wrong_expert` 或 `carbon_misroute`
- fallback:
  - `none`
  - `heuristic` 或 `schema`

目的很简单：

- 证明 fallback 在真实 misroute 场景下有保护作用。
- 不再把 fallback 写成大而全模块。

通过条件：

- fallback 至少能稳定降低最坏段的 carbon / reserve 类损失。

## Stage C — 给结果补 reviewer 能接受的统计层

这一段很重要。没有它，当前结果更像一轮 run，不像主表证据。

### C1. 多 episode / 多 seed

优先方案：

- 如果 CityLearn episode 可控，就对同一配置跑多 episode。
- 如果 episode 不可控，就对 schedule slicing / sampled windows 做重复评估。
- 如果以上都不方便，至少做：
  - 多段 event-driven segments 的 paired aggregation
  - bootstrap confidence interval

最低要求：

- 给主比较项补 mean ± interval
- 给关键 pair 补 paired difference

关键比较项：

- `qp_current` vs `qp_carbon`
- best fixed vs heuristic
- best fixed vs text router
- `granite + corrected QP` vs `moirai2/timesfm + corrected QP`

通过条件：

- 关键差异不是只靠单 episode 偶然值站住。

停下条件：

- 如果 interval 很宽，所有差异都压不实，就先缩 paper 结论，不再补更多花样实验。

## 4. 当前最合理的 paper 说法

当前更合理的说法不是“大一统 LLM agent 改善 forecast-then-control”。

当前更合理的说法是两层：

### 低层说法

不同 backbone + corrected QP 会落在不同 KPI trade-off 点。

最可能稳定成立的是：

- `granite` 更强 peak
- `moirai2 / timesfm2.5` 更强 cost/carbon/ramping

### 高层说法

event-driven preference routing 只有在固定 low-level reference 后才有资格讨论。

如果它成立，最合理的主张也应该写成：

- 高层语言/规则路由可以在固定 low-level stack 上优于单一固定策略
- 但增益受 backbone 和 regime 影响，不该写成无条件通用优势

## 5. 不建议现在做的事

下面这些现在做了，信息增量低：

- 继续堆更多 router prompt 版本
- 再加更多弱 controller baseline
- 现在就补第二环境
- 现在就讲 broad agent story
- 在 corrected low-level 还没固定前就开始最终 paper 定稿

## 6. 执行清单

按这个顺序做：

1. 固定 `qp_current` vs `qp_carbon` backbone comparison 主表
2. 给 preference-shift runner 接上 corrected carbon path
3. 跑 1 组 event-driven sanity
4. 跑 backbone × router 最小主表
5. 跑 1 组 corruption/fallback 保护实验
6. 给关键结果补 interval / paired difference
7. 再决定 paper 是写 focused routing，还是改写成 trade-off + routing sensitivity

## 7. Stop / Go 决策

### Go

满足下面三条，就可以继续写 focused paper 主结果：

- corrected QP 结论稳定
- 至少一条强 backbone 上 router 优于 best fixed
- 关键差异有最小统计支撑

### Stop and rewrite claim

出现下面任一条，就不要硬讲 routing 主胜：

- corrected path 后 router 结论消失
- router 只在单一 backbone 上偶然成立
- interval 太宽，关键 pair 不稳定

这时把 paper 主线改成：

- backbone/controller trade-off 是主结果
- routing 只作为 sensitivity / exploratory result

## 8. 当前最短结论

下一步实验计划已经很明确：先固定 corrected QP 参考栈，再在 `event_driven` 协议上只跑最小 backbone × router 矩阵，最后补统计层。现在继续堆 router 小版本，信息增量太低。
