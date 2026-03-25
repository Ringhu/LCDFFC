# Experiment Tracker

当前 tracker 只服务于 **CSFT 主线**。旧的 routing / foundation 结果保留为历史参考，不再作为当前主执行面。

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|--------|-----------|---------|------------------|-------|---------|----------|--------|-------|
| R101 | M0 | label sanity | `qp_carbon` sensitivity label generation on small train subset | train-mini | label stats / rank corr / top-mass | MUST | TODO | 先检查 finite-difference label 是否可用 |
| R102 | M0 | metric sanity | stress subset masks + chronological split + oracle-gap evaluator | val | mask coverage / KPI script sanity | MUST | TODO | 先把 standard / carbon-price stress / peak stress 三种 view 固定下来 |
| R103 | M1 | baseline | GRU + uniform loss + `qp_carbon` | val/test | cost / carbon / peak / RMSE / MAE | MUST | TODO | 当前主 baseline |
| R104 | M1 | upper bound | oracle forecast + `qp_carbon` | test | cost / carbon / peak | MUST | TODO | 用来算 oracle gap closure |
| R105 | M2 | pilot | GRU + CSFT (1 seed) + `qp_carbon` | val/test | cost / carbon / peak / top-decile error | MUST | TODO | 先判断主 thesis 有没有正信号 |
| R106 | M3 | heuristic baseline | GRU + manual horizon weighting + `qp_carbon` | test | cost / carbon / peak / top-decile error | MUST | TODO | 防守“简单窗口 weighting 已经够用” |
| R107 | M3 | heuristic baseline | GRU + event-window weighting + `qp_carbon` | test | cost / carbon / peak / top-decile error | MUST | TODO | 防守“手工事件 weighting 已经够用” |
| R108 | M3 | main result | GRU + CSFT (3 seeds) + `qp_carbon` | test | cost / carbon / peak / oracle gap | MUST | TODO | 主表结果 |
| R109 | M3 | controller specificity | GRU + CSFT with `qp_current` labels, eval on `qp_carbon` | test | cost / carbon / peak / top-decile error | MUST | TODO | matched vs mismatched controller labels |
| R110 | M4 | loss stability | GRU + pure weighted loss (`alpha=0`) | val/test | KPI / loss stability / label-mass stats | MUST | TODO | 和 mixed loss 对照 |
| R111 | M4 | mechanism figure | decile-wise error reduction + average sensitivity heatmap | test | decile RMSE / MAE / heatmap | MUST | TODO | 主文关键图 |
| R112 | M5 | optional replication | second backbone uniform vs CSFT | test | cost / carbon / peak | NICE | TODO | 只有 R108 很稳才做 |
