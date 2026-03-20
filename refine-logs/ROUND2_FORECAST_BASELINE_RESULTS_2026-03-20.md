# Round 2 结果：Stronger Forecast Baseline（2026-03-20）

## 1. 本轮为什么做这个实验

这轮实验直接回应用户提出的一个核心质疑：

> 当前高层路由的结论，会不会只是建立在一个过弱的 `GRU` backbone 上？

因此，这轮没有继续调 router，也没有同时引入真实 LLM router，而是优先做一个更强的 low-level forecasting baseline 检查。

## 2. 设计前 review 结论

对应的 reviewed note 是：

- `refine-logs/auto-review/2026-03-20-round2-forecast-baseline-review.md`

review 决策是：

1. 先补一个实现成本低但比 `GRU` 更现代的时序 baseline
2. 本轮选择 `TSMixer`
3. 依次比较：
   - forecasting 指标
   - 下游 `learned + QP` 控制指标
   - 最小高层稳定性检查（`fixed` vs `text_v4`）

## 3. 本轮做了什么

### 3.1 新增实现

- `models/tsmixer_forecaster.py`
- `models/factory.py`
- `scripts/train_forecaster.py`
- `configs/forecast_tsmixer.yaml`
- `tests/test_forecaster_factory.py`

并把以下入口改成支持按 config 选择 backbone：

- `eval/run_controller.py`
- `eval/run_preference_shift.py`

### 3.2 验证顺序

- 本地测试：通过
- `GPU 3`：`TSMixer` 短程训练 sanity，通过
- `GPU 2`：完整训练与后续评估

## 4. 实验结果

## 4.1 Forecasting 结果：`GRU` vs `TSMixer`

使用同一份 `artifacts/forecast_data.npz`，当前关键 test 指标如下：

| Backbone | overall_mse | overall_mae |
|---|---:|---:|
| GRU | 0.9323 | 0.3580 |
| TSMixer | 0.9422 | 0.3850 |

结论：

- `TSMixer` 在当前设置下**没有整体优于** `GRU`
- 至少从当前这一轮看，不能说“GRU 过于弱，以至于当前所有结果都不可信”
- 但也不能反过来说“GRU 已经足够代表最强 forecasting backbone”

更准确的判断是：

> 当前补进来的第一个 stronger baseline（`TSMixer`）没有优于 `GRU`，因此“当前结论完全只是因为 GRU 太弱”这一说法暂时没有被支持；但 stronger baseline 检查仍然不充分，还不能替代 `PatchTST` / foundation model 级比较。

## 4.2 下游控制结果：`GRU + QP` vs `TSMixer + QP`

在相同 `learned + QP` 闭环下：

| Run | cost | carbon | peak | ramping |
|---|---:|---:|---:|---:|
| GRU + QP | 32.0099 | 488.5686 | 15.8135 | 853.9113 |
| TSMixer + QP | 32.6081 | 496.0019 | 15.9166 | 909.8013 |

结论：

- 在当前配置下，`TSMixer + QP` **整体劣于** `GRU + QP`
- 这说明当前 backbone 的改变确实会显著影响下游控制结果
- 也说明：

> 当前高层路由结论不是“对任意 low-level backbone 都自动成立”，它仍然依赖 low-level backbone 的质量。

## 4.3 最小高层稳定性检查：`TSMixer` 下的 fixed vs `text_v4`

为了看高层结论是否会因为 backbone 改变而翻转，本轮在 `TSMixer` 下重新跑了：

- `tsmixer_fixed_balanced`
- `tsmixer_fixed_cost`
- `tsmixer_fixed_carbon`
- `tsmixer_fixed_peak`
- `tsmixer_fixed_reserve`
- `tsmixer_text_v4`

汇总结果：

| Run | avg_preference_score | avg_regret_to_best_fixed | avg_regret_to_best_single_fixed |
|---|---:|---:|---:|
| tsmixer_fixed_peak | 0.873682 | 0.000101 | 0.000000 |
| tsmixer_fixed_balanced | 0.875000 | 0.001419 | 0.001318 |
| tsmixer_text_v4 | 0.875277 | 0.001695 | 0.001595 |
| tsmixer_fixed_carbon | 0.875708 | 0.002126 | 0.002026 |
| tsmixer_fixed_cost | 0.878206 | 0.004625 | 0.004524 |
| tsmixer_fixed_reserve | 0.882195 | 0.008614 | 0.008513 |

结论：

- 在 `TSMixer` backbone 下，`text_v4` **不再优于** 最佳单一固定控制器
- 当前 best single fixed 变成了 `tsmixer_fixed_peak`
- 这说明高层路由当前的优势并不是“独立于低层 backbone 的强结论”

这轮最关键的发现不是 “`text_v4` 被推翻”，而是：

> 当前高层路由主结果对 low-level backbone 仍然敏感，因此不能再把“固定低层后只研究高层”写成理所当然，而应该明确承认：低层 backbone 的选择本身就是当前结果可信度的一部分。

## 5. 本轮结果意味着什么

### 5.1 哪些说法被削弱了

本轮之后，以下说法都必须收紧：

1. “低层 backbone 已经足够，不再重要”
2. “当前高层路由结果已经与 low-level 选择无关”
3. “现在可以放心把高层结果直接写成投稿版主结果”

### 5.2 哪些说法仍然可以保留

1. 当前 `GRU` 主线不是显然的假象
   - 因为补进来的 `TSMixer` 没有更强
2. 当前 stronger-baseline 检查已经开始做，而且确实影响结论
3. 当前工程进入“需要更强 baseline 才能继续推进”的阶段，而不是继续微调 router 的阶段

### 5.3 最关键的新结论

本轮最关键的新结论可以写成：

> 当前项目的主要瓶颈已经从“router 还有没有局部可调空间”，转移到了“low-level backbone 与评测协议是否足够强，足以支撑高层路由结论”。

## 6. 下一步建议

按收益和必要性排序，下一步最合理的是：

1. **再补一个 stronger forecasting baseline**
   - 优先 `PatchTST` 或 `TSMixer` 之外的一个更强经典模型
2. **升级 preference-shift 协议**
   - 从人工四段切换升级到 event-driven / multi-episode protocol
3. **暂缓继续微调 router**
   - 在 low-level 和 protocol 还没站稳前，再调 `text_v8` 价值不高
4. **真实 LLM router 作为单独一轮**
   - 不要和 stronger low-level baseline 混在同一轮里做

## 7. 一句话总结

> 这轮 stronger forecast baseline 实验没有支持“GRU 太弱导致当前结论失真”这个最简单的反对意见，但它确实证明：高层路由的结论仍然依赖 low-level backbone 的质量，因此当前论文要想站稳，必须继续补 stronger baseline 和更强协议，而不是继续只调高层 router。
