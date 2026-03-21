# 实验跟踪表

| Run ID | 里程碑 | 目的 | 系统 / 变体 | 数据划分 | 指标 | 优先级 | 状态 | 备注 |
|---|---|---|---|---|---|---|---|---|
| R001 | M0 | 定义 regime 协议 | preference schedule generator | val | protocol sanity | MUST | DONE | 已实现 4 段默认 regime：cost / carbon / peak / reserve |
| R002 | M0 | 评分规则检查 | preference-matched KPI scorer | val | regret / match score | MUST | DONE | 已实现 `eval/summarize_preference_shift.py`，以 `fixed_balanced` 为 reference，计算对最佳固定策略 regret |
| R003 | M1 | baseline | 固定权重 learned forecast + QP | test | cost/carbon/peak | MUST | DONE | 当前已验证 base loop 存在 |
| R004 | M1 | baseline | 面向不同目标的固定权重变体 | test | cost/carbon/peak | MUST | DONE | 已完成 `fixed_balanced / cost / carbon / peak / reserve` 五组 GPU2 全量评测 |
| R005 | M2 | 雏形 | heuristic rule router | test | regime regret | MUST | DONE | GPU2 全量评测完成；相对最佳单一固定策略仍略差，但优于 text_v1 / numeric |
| R006 | M2 | 雏形 | language-conditioned router（v1 → v2） | test | regime regret | MUST | DONE | v1 使用 text-template，结果明显弱于最佳固定；v2 在 GPU3/GPU2 复跑后，`avg_preference_score=0.876864`，已略优于最佳单一固定策略 `fixed_reserve=0.876931` |
| R007 | M3 | ablation | 结构化数值路由器 | test | regime regret | MUST | DONE | GPU2 全量评测完成；当前结果劣于 heuristic，且未优于最佳固定权重 |
| R008 | M3 | ablation | 无 router（固定权重） | test | regime regret | MUST | DONE | 由 `fixed_balanced` 和其他固定权重变体共同覆盖 |
| R009 | M4 | 鲁棒性 | text router + deterministic fallback | shifted | validity / KPI | MUST | DONE | 已从旧版 `extreme_peak` 周期注入升级到 `transition_wrong_expert` 协议；在 `text_best` 上完整验证后，fallback 能保护 `peak / ramping`，但会付出轻微 `cost / carbon` 代价 |
| R010 | M5 | 扩展 | 最佳 router 在 OOD weather/price 下 | shifted | degradation | NICE | TODO | 仅在主结果成立后运行 |
| R011 | M2+ | review-selected 改进 | text expert-selector router (`text_v4`) | test | regime regret | MUST | DONE | 基于 auto-review 选择的下一版；当前是已验证的最佳文本路由版本，并新增 `text_best` 别名固定这一状态 |
| R012 | M2+ | 误差归因 | `text_best` segment-level gap analysis | test | per-regime delta / route stats | MUST | DONE | 已新增 `eval/analyze_preference_shift_gap.py`；当前结论是 `text_best` 相对 `v2` 的主要优势来自 `cost / carbon / peak` 三段，而剩余短板主要落在 `reserve` 与部分 `carbon` 区段 |
| R013 | M4+ | targeted ablation | `reserve_drop_guard` vs `carbon_misroute` | shifted | KPI delta / reserve gap / fallback gain | MUST | DONE | 已完成 GPU3 sanity 与 GPU2 全量对照；当前证据显示 `reserve` 是更强的主敏感点，`carbon` 是次要但真实存在的误差来源 |
| R014 | M2+ | reviewed v5/v6 | reserve-aware release guard | test | regime regret | MUST | DONE | `v5` 改进方向正确但 guard 过宽，整体劣于 `v4`；`v6` 收窄后与 `v4` 完全打平，因此当前 `text_best` 仍保持为 `v4` |
| R015 | M2+ | reviewed v7 | regime-aware transition trigger | test | regime regret | MUST | DONE | `v7` 通过按下一段 regime 区分 release guard，但最终与 `v4 / v6` 仍完全打平；说明局部 reserve release guard 调优已进入饱和区，当前 best 仍是 `v4` |
| R016 | M1+ | stronger baseline | `GRU` vs `TSMixer` + downstream control check | test | forecast metrics / cost / carbon / peak | MUST | DONE | 已完成 reviewed stronger-forecast-baseline 实验；`TSMixer` 未优于 `GRU`，且在 `TSMixer` 下 `text_v4` 不再优于最佳单一固定控制器，说明当前高层结论对 low-level backbone 仍敏感 |

| R017 | M1+ | stronger baseline | `GRU` vs `TSMixer` vs `PatchTST` + downstream control check | test | forecast metrics / cost / carbon / peak | MUST | DONE | 已完成 reviewed `PatchTST` stronger baseline；`PatchTST` 的 forecasting 指标最差，但 `PatchTST + QP` 在 `cost / carbon` 上优于 `GRU + QP`，说明 forecasting 误差与控制表现并不严格同向 |
| R018 | M0+ | protocol upgrade | event-driven preference protocol | test | regime regret / protocol robustness | MUST | DONE | 已完成 reviewed event-driven 协议与完整对比；在新协议下 `fixed_peak` 成为最佳单一固定策略，`text_best / heuristic` 都不再占优，说明旧四段协议偏乐观 |
| R019 | M2++ | real LLM router | prompt-only `LLMRouter.route()` | test | validity / latency / regime regret | MUST | DONE | 已实现并跑通本地 Qwen prompt-only router；完整 event-driven 结果优于 `text_best / heuristic`，但仍略弱于 `fixed_peak`；`48` 次调用、`0` 次 parse failure、`0` 次 fallback |

| R020 | M1++ | backbone expansion | `TransformerEncoder` + downstream control check | test | forecast metrics / cost / carbon / peak | MUST | DONE | 已完成 reviewed former 类 backbone；forecast 指标未超过 `GRU`，但 `Transformer + QP` 把 `peak` 压到 `15.2551`，说明新的 former backbone 继续改变 control trade-off |
| R021 | M1++ | backbone expansion | `Granite PatchTST init` + downstream control check | test | forecast metrics / cost / carbon / peak | MUST | DONE | 已完成 reviewed foundation-like backbone；尽管 forecasting 指标弱于 `GRU`，但 `Granite + QP` 在 `cost / carbon / peak / ramping` 上给出当前最强闭环结果，改写了 low-level backbone 排名 |
| R022 | M2+++ | backbone-sensitive transfer | event-driven transfer on `Transformer / Granite` | test | avg_preference_score / KPI | MUST | DONE | 已完成最小 high-level transfer 检查；`Transformer` 下 `llm_prompt_v1` 略优于 `fixed_peak`，但 `Granite` 下 `fixed_peak` 重新占优，说明 high-level 结论在 backbone 之间仍不稳定 |

| R023 | M1+++ | foundation models | `Chronos-2 / Moirai2 / TimesFM 2.5 / MOMENT` zero-shot rolling forecast | test | raw-scale MSE / MAE / latency | MUST | DONE | 已完成 reviewed foundation-model round；四者都已按官方或最接近官方路径跑通，其中 `Moirai2` rolling forecast 最好，`TimesFM 2.5` 次之，`Chronos-2` 再次，`MOMENT` 最弱且官方 warning 指出 forecasting head 需 fine-tune |
| R024 | M1+++ | foundation models | `foundation forecast + QP` downstream control | test | cost / carbon / peak / ramping | MUST | DONE | 已完成四个 foundation family 的下游控制比较；`Moirai2 + QP` 最强，`TimesFM 2.5 + QP` 次之，二者都明显优于 `Chronos-2 / MOMENT`，并在 `cost / carbon / ramping` 上优于当前 `Granite + QP` |
