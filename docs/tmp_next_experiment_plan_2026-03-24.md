# Next experiment plan（temporary, 2026-03-24）

这是一份临时实验计划，不是仓库长期事实源。它只用来说明这轮实验先做什么、为什么这么排、什么时候继续、什么时候停下来改论文说法。

## 最短结论

现在先别继续堆 `router` 版本。原因是主实验链路里未来 `carbon` 信号还没稳定传到控制器，先把 `corrected QP` 路径固定下来才值得比较高层策略。

## 先把几个词说清楚

`backbone` 在这里就是预测模型。它负责给控制器提供未来一段时间的预测值，比如 `price / load / solar`，有些脚本还会额外预测 `carbon`。

`router` 在这里就是高层偏好选择器。它只负责选一组 `weights` 和 `constraints`，不直接输出电池动作。

`corrected QP` 在这里就是把未来 `carbon` 信号正确传给 `QPController.act(..., carbon_intensity=...)` 之后的 QP 控制路径。这个词不是新算法，只是把该传的输入真的传进去。

## 现在到底发现了什么

当前真正的问题是 controller 输入前后不一致，不是 QP 这条路天然不行。因为 `controllers/qp_controller.py:87-125` 的 `QPController.act(...)` 已经支持 `carbon_intensity`，但两条主实验脚本还没有把这个输入稳定传进去。

- `eval/run_foundation_control.py:79-84` 现在没传 `carbon_intensity`。这里调用 `ctrl.act(...)` 时只传了 `state / forecast / weights / constraints`。
- `eval/run_preference_shift.py:337-342` 现在也没传未来 `carbon` 预测。也就是说，当前 `router` 实验还是跑在旧的 low-level 输入上。
- `eval/run_foundation_controller_compare.py:95-119` 已经把 `qp_current` 和 `qp_carbon` 分开了。这个脚本里 `qp_carbon` 会用未来 `carbon` 预测，`qp_current` 会显式传 `carbon_intensity=None`。

当前已经看到的方向没有变。现有记录说明 `qp_carbon` 比 `qp_current` 更稳，但增益不大；非 QP controller 没赢 QP；foundation forecast 很强，也不会自动变成最强控制 KPI。

## 为什么下一步不是继续堆 router 版本

现在继续堆 `router` 版本，信息增量很低。因为低层输入还没固定，新的 `router` 结果会和旧路径的问题混在一起。

现在更该先跑清楚的是 low-level 对照。因为 `eval/run_foundation_controller_compare.py` 已经能直接比较 `qp_current` 和 `qp_carbon`，这比继续加 `text_v2 ~ v7` 更接近真正的问题。

只有 low-level 参考路径固定后，高层 `router` 结果才有解释价值。否则很难判断差异到底来自高层策略，还是来自底层输入没传全。

## 下一步按什么顺序做

### 第一步：先固定 corrected QP 参考路径

第一步先重跑 backbone 和 QP 的最小对照。目的只有一个：确认把未来 `carbon` 正确传进去以后，低层结论有没有变。

建议先跑这个最小矩阵。`forecast source` 先看 `granite_patchtst`、`moirai2`、`timesfm2.5`，`controller` 只看 `qp_current` 和 `qp_carbon`。

这一步重点看 5 个指标。它们是 `cost`、`carbon`、`peak`、`ramping`，以及相对 `zero_action` 的归一化平均分。

这一步可以继续的条件很明确。`qp_carbon` 在 `moirai2 / timesfm2.5` 上还要继续稳定优于 `qp_current`，同时 `granite` 还要保住 `peak` 优势，或者至少继续形成清楚的取舍关系。

这一步该停下来查问题的条件也很明确。如果 corrected path 接上后 ranking 完全翻盘，而且波动大到说不清，就先别跑 `router`，先查 objective 和 forecast interface。

### 第二步：把 preference runner 的 carbon 路径补齐后，只跑一组 sanity check

第二步先别急着扩实验矩阵。目的只是确认 `eval/run_preference_shift.py` 不再沿用旧的 low-level 输入缺口。

这一步先用一条 backbone 就够了。优先选 `granite` 或当前 `cost / carbon` 更强的 foundation backbone。

这一步只跑最小组合就够了。`router` 先看 `fixed_balanced` 和 `heuristic`，`schedule` 固定为 `event_driven`。

这一步先看输出文件是不是正常。至少要稳定产出 `routes.json`、`segments.json`、`kpis.json`。

这一步还要看结果量级是不是正常。指标不能明显退化到接近 `zero_action`，不然说明 runner 接入 corrected path 后行为已经变形。

这一步该继续的条件是 runner 能正常跑完，而且结果量级还在旧结果附近。这样才值得进入下一轮主表。

这一步该停下来的条件是 corrected `carbon` 路径一接入就出现异常。遇到这种情况先修 runner，不要扩更多 `router × backbone` 组合。

### 第三步：再跑最小 backbone × router 主表

第三步才轮到高层 `router` 主表。前两步没跑稳，就不要急着讲高层策略。

这一步的 backbone 不要放太多。建议保留 `granite_patchtst`，再从 `moirai2` 和 `timesfm2.5` 里选一条；如果算力够，再把两个都留。

这一步的 router 也不要再堆版本。建议只保留 `fixed_balanced`、`fixed_cost`、`fixed_peak`、`fixed_reserve`、`heuristic`，以及 `llm_prompt_v1` 或当前最强的文本 router。

这一步的协议也要固定。`schedule_type` 用 `event_driven`，不要再把旧的 default schedule 当主证据。

这一步真正要回答的问题很简单。要看的是高层 routing 在 corrected low-level 路径上，能不能稳定优于单一固定策略，而不是看文本 router 能不能在所有地方都最强。

这一步可以继续的条件是至少一条强 backbone 上，router 明确优于最好的单一 fixed baseline。另一条 backbone 就算优势变弱，也要方向一致，或者至少能解释为什么不一致。

这一步该停下来改论文说法的条件是 router 只在单一 backbone 上偶然成立。遇到这种情况，就不要再写“稳定 routing 增益”，而要改写成“效果依赖 backbone”。

### 第四步：只保留一组 corruption / fallback 结果

第四步只做一组最有信息量的保护实验。目的不是扩张实验面，而是回答“错路由时有没有保护”。

这一步建议只留一类 corruption。优先留 `transition_wrong_expert` 或 `carbon_misroute`。

这一步建议只留两类 fallback。优先留 `none` 和 `heuristic`，或者 `none` 和 `schema`。

这一步重点看最坏时段有没有被拉回来。只要 fallback 能稳定降低最坏时段的 `carbon` 或 `reserve` 类损失，这组结果就够用了。

这一步没必要继续横向扩张。因为 reviewer 真正常问的是“错了以后会不会更糟”，不是“你一共写了多少种 fallback”。

### 第五步：最后补统计层

第五步必须补最基本的统计支撑。没有这一层，现在很多结果更像单次 run，不像主表证据。

这一步优先跑多 episode。要是 CityLearn episode 不好控，就对 `event_driven` 的分段结果做重复统计；再不方便，至少做 paired aggregation 和 bootstrap interval。

这一步最低要求很明确。主比较项要补 `mean ± interval`，关键 pair 要补 paired difference。

这一步重点比较 4 组。它们是 `qp_current vs qp_carbon`、`best fixed vs heuristic`、`best fixed vs text router`、`granite + corrected QP vs moirai2/timesfm + corrected QP`。

这一步可以继续的条件是关键差异不是只靠单次 episode 的偶然值站住。只要主要 pair 还能保持方向，就够支撑论文主表。

这一步该停下来改论文说法的条件是 interval 很宽，关键 pair 说不稳。遇到这种情况，就别再补更多花样实验，先缩小主张。

## 每一步到底要看什么

现在最需要先回答 3 个问题。它们决定这轮实验是继续做 routing，还是改回更保守的论文说法。

- 第一个问题是 corrected QP 固定后，backbone 排名会不会变。这个问题决定后面高层实验要绑哪条 low-level 路径。
- 第二个问题是 corrected QP 接上以后，`event_driven` routing 还成不成立。这个问题决定高层 routing 还能不能做主结果。
- 第三个问题是当前主结果是不是只是一条单次 episode 现象。这个问题决定结果能不能进 reviewer-facing 主表。

## 继续和停止条件

满足下面三条，就可以继续写 focused routing 的主结果。`corrected QP` 结论要稳定，至少一条强 backbone 上 router 要优于最好的固定策略，关键差异还要有最基本的统计支撑。

出现下面任一条，就该停下来改论文说法。只要 corrected path 接上后 router 结论消失，或者 router 只在单一 backbone 上偶然成立，或者 interval 太宽说不稳，都不要硬讲 routing 主胜。

## 当前最适合的论文说法

当前更适合的说法是“先讲 backbone + corrected QP 的取舍关系，再讲 routing 在固定 low-level 路径上的额外收益”。这比直接写成“大一统 LLM agent 全面改善 forecast-then-control”更接近现状。

低层结果现在最可能稳定成立。`granite + corrected QP` 更偏 `peak`，`moirai2 / timesfm2.5 + corrected QP` 更偏 `cost / carbon / ramping`。

高层结果只有在 fixed low-level reference 之后才值得讨论。如果 routing 成立，最稳妥的写法也应该是“它在固定 low-level 路径上能优于单一固定策略，但效果受 backbone 和场景影响”。

如果上面的条件站不住，论文说法就要改小。那时主结果应改成 `backbone/controller trade-off`，routing 只保留成补充结果或敏感性结果。

## 当前不建议做的事

现在不建议继续堆更多 `router prompt` 版本。因为 low-level 还没固定，继续加版本只会把问题越搅越杂。

现在不建议再加更多弱 controller baseline。因为现有记录已经说明非 QP controller 没打过 QP。

现在不建议立刻补第二环境。因为这轮最关键的问题还在第一环境里没理清。

现在不建议提前写“大而全的 agent 说法”。因为当前证据更适合支持 trade-off + routing sensitivity，而不是无条件通用优势。

## 执行清单

按下面顺序做最省时间。先固定 `qp_current vs qp_carbon` 的 backbone comparison 主表，再给 `preference-shift` runner 接上 corrected `carbon` path，再跑一组 `event_driven` sanity，之后再跑最小 `backbone × router` 主表、保留一组 corruption / fallback、最后补 interval 和 paired difference。
