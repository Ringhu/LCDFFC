# 实验跟踪表

| Run ID | 里程碑 | 目的 | 系统 / 变体 | 数据划分 | 指标 | 优先级 | 状态 | 备注 |
|---|---|---|---|---|---|---|---|---|
| R001 | M0 | 定义 regime 协议 | preference schedule generator | val | protocol sanity | MUST | DONE | 已实现 4 段默认 regime：cost / carbon / peak / reserve |
| R002 | M0 | 评分规则检查 | preference-matched KPI scorer | val | regret / match score | MUST | DONE | 已实现 `eval/summarize_preference_shift.py`，以 `fixed_balanced` 为 reference，计算对最佳固定策略 regret |
| R003 | M1 | baseline | 固定权重 learned forecast + QP | test | cost/carbon/peak | MUST | DONE | 当前已验证 base loop 存在 |
| R004 | M1 | baseline | 面向不同目标的固定权重变体 | test | cost/carbon/peak | MUST | DONE | 已完成 `fixed_balanced / cost / carbon / peak / reserve` 五组 GPU2 全量评测 |
| R005 | M2 | 雏形 | heuristic rule router | test | regime regret | MUST | DONE | GPU2 全量评测完成；平均 regret 低于 text / numeric，但仍未超过最佳固定权重 |
| R006 | M2 | 雏形 | language-conditioned router v1 | test | regime regret | MUST | DONE | 先用 text-template router 代替真实 LLM；GPU3 短程 sanity + GPU2 全量完成 |
| R007 | M3 | ablation | 结构化数值路由器 | test | regime regret | MUST | DONE | GPU2 全量评测完成；当前结果劣于 heuristic，且未优于最佳固定权重 |
| R008 | M3 | ablation | 无 router（固定权重） | test | regime regret | MUST | DONE | 由 `fixed_balanced` 和其他固定权重变体共同覆盖 |
| R009 | M4 | 鲁棒性 | text router + deterministic fallback | shifted | validity / KPI | MUST | TODO | 尚未注入低置信 / 错误输出场景 |
| R010 | M5 | 扩展 | 最佳 router 在 OOD weather/price 下 | shifted | degradation | NICE | TODO | 仅在主结果成立后运行 |
