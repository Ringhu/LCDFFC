# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|--------|-----------|---------|------------------|-------|---------|----------|--------|-------|
| P201 | M0 | frozen evidence | package R201/R202 preflight conclusion | test | oracle alignment / top-decile MAE ratio | MUST | DONE | Formal conclusion available: R201 PASS, R202 FAIL, raw-CSFT falsified in current setting |
| P202 | M1 | prior extraction | extract controller-dual prior `G(h,c)` from fixed `qp_carbon` | train | prior heatmap / heuristic similarity | MUST | BLOCKED | Current analytic/dual extraction returned no usable solved diagnostics on sampled train windows; prior collapsed to all zeros |
| P203 | M2 | main pivot method | GRU + controller-dual prior + `qp_carbon` | train/val/test | high-prior-cell MAE / overall MAE / cost / carbon / peak | MUST | BLOCKED | Not launched because P202 did not produce a usable non-zero controller-dual prior |
| P204 | M3 | strongest simple alternative | GRU + strongest heuristic baseline + `qp_carbon` | train/val/test | high-prior-cell MAE / overall MAE / cost / carbon / peak | MUST | TODO | Compare only one strongest heuristic family |
| P205 | M4 | mechanism package | decile/high-prior-cell curves + prior heatmap + heuristic similarity | test | figures/tables | MUST | TODO | Needed whether pivot is positive or negative |
| P206 | M5 | optional strengthening | controller-dual prior multi-seed or controller-specificity check | train/val/test | same primary KPIs | NICE | TODO | Only if P203 is clearly positive |
| H201 | history | frozen falsification | R201 oracle alignment | test | max_abs_error | CONTEXT | DONE | PASS: all channels 0.0 |
| H202 | history | frozen falsification | R202 raw-label utility | test | top-decile MAE ratio | CONTEXT | DONE | FAIL: 1.0546 > 1.05 |
| H203 | history | existing baseline | GRU + uniform + `qp_carbon` | val/test | MAE / MSE / control KPIs | CONTEXT | DONE | Existing references: R103 + R112 |
| H204 | history | failed route | GRU + raw-CSFT + `qp_carbon` | val/test | MAE / MSE / control KPIs | CONTEXT | DONE | Existing references: R105 + R113 |
| H205 | history | blocked run | stabilized-CSFT R203 | train/val/test | — | CONTEXT | BLOCKED | Not launched because raw-CSFT preflight failed |
