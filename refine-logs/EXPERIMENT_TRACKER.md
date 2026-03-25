# Experiment Tracker

当前 tracker 只服务于 **CSFT 主线**。旧的 routing / foundation 结果保留为历史参考，不再作为当前主执行面。

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|--------|-----------|---------|------------------|-------|---------|----------|--------|-------|
| R101 | M0 | label sanity | `qp_carbon` sensitivity label generation on small train subset | train-mini | label stats / rank corr / top-mass | MUST | DONE | small sanity passed；`normalized_mean≈1.00` |
| R102 | M0 | metric sanity | stress subset masks + chronological split + oracle-gap evaluator | val | mask coverage / KPI script sanity | MUST | DONE | split / stress mask diagnostics 已生成 |
| R103 | M1 | baseline | GRU + uniform loss + `qp_carbon` full-budget | val/test | RMSE / MAE | MUST | DONE | best val loss=0.134295, overall MSE=1.13294, overall MAE=0.36354 |
| R104 | M1 | upper bound | oracle forecast + `qp_carbon` | test | cost / carbon / peak / ramping | MUST | DONE | cost=33.8339, carbon=511.5938, peak=16.2272 |
| R105 | M2 | pilot | GRU + CSFT (1 seed) + `qp_carbon` | val/test | RMSE / MAE | MUST | DONE | best val loss=0.121692, overall MSE=1.19011, overall MAE=0.39387 |
| R106 | M3 | heuristic baseline | GRU + manual horizon weighting + `qp_carbon` | test | forecast + control | MUST | TODO | 防守“简单窗口 weighting 已经够用” |
| R107 | M3 | heuristic baseline | GRU + event-window weighting + `qp_carbon` | test | forecast + control | MUST | TODO | 防守“手工事件 weighting 已经够用” |
| R108 | M3 | main result | GRU + CSFT (3 seeds) + `qp_carbon` | test | forecast + control / oracle gap | MUST | TODO | 主表结果 |
| R109 | M3 | controller specificity | GRU + CSFT with `qp_current` labels, eval on `qp_carbon` | test | forecast + control | MUST | TODO | matched vs mismatched labels |
| R110 | M4 | loss stability | GRU + pure weighted loss (`alpha=0`) | val/test | forecast + control | MUST | TODO | mixed loss 对照 |
| R111 | M4 | mechanism figure | decile-wise error reduction + average sensitivity heatmap | test | decile RMSE / MAE / heatmap | MUST | TODO | 主文关键图 |
| R112 | M4 | learned-control eval | replay `qp_carbon` with `gru_uniform_best_r103_uniform_seed42.pt` | test | cost / carbon / peak / ramping | MUST | TODO | fairness compare: uniform checkpoint |
| R113 | M4 | learned-control eval | replay `qp_carbon` with `gru_csft_best_r105_csft_seed42.pt` | test | cost / carbon / peak / ramping | MUST | TODO | fairness compare: CSFT checkpoint |
| R114 | M4 | result summary | summarize R103/R105/R112/R113 for bridge handoff | test | claim status | MUST | TODO | 生成 `refine-logs/EXPERIMENT_RESULTS.md` |
| R115 | M5 | optional replication | second backbone uniform vs CSFT | test | cost / carbon / peak | NICE | TODO | 只有主结果稳才做 |
