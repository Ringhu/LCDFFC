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
