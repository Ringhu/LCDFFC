# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|--------|-----------|---------|------------------|-------|---------|----------|--------|-------|
| Q201 | M0 | frozen evidence | package R201/R202 + offline-dual failure summary | test/train-sample | preflight PASS/FAIL + solved-diagnostics rate | MUST | DONE | Summary packaged: oracle PASS, raw-CSFT FAIL, offline dual extraction unusable |
| Q202 | M1 | replay prior extraction | build replay-calibrated controller prior `G(h,c)` from successful replay states | replay/train metadata | prior heatmap / heuristic similarity / solved-state coverage | MUST | DONE | PASS: solved_fraction=1.0, nonzero_prior_fraction=1.0, manual_horizon_corr=0.379, cosine=0.388 |
| Q203 | M2 | main pivot method | GRU + replay-calibrated prior + `qp_carbon` | train/val/test | high-prior-cell MAE / overall MAE / cost / carbon / peak | MUST | DONE | Forecast: overall_mae=0.2823, overall_mse=0.8884; Control: cost=31.7324, carbon=483.4166, peak=15.8958, ramping=846.3832 |
| Q204 | M3 | strongest simple alternative | GRU + strongest heuristic baseline + `qp_carbon` | train/val/test | high-prior-cell MAE / overall MAE / cost / carbon / peak | MUST | TODO | Only one heuristic family kept |
| Q205 | M4 | mechanism package | error concentration curves + replay prior heatmap + heuristic similarity | test | figures/tables | MUST | TODO | Needed whether replay-prior is positive or negative |
| Q206 | M5 | optional strengthening | replay-prior multi-seed or alternative replay-derived prior | train/val/test | same primary KPIs | NICE | TODO | Only if Q203 is clearly positive |
| H201 | history | frozen falsification | R201 oracle alignment | test | max_abs_error | CONTEXT | DONE | PASS: all channels 0.0 |
| H202 | history | frozen falsification | R202 raw-label utility | test | top-decile MAE ratio | CONTEXT | DONE | FAIL: 1.0546 > 1.05 |
| H203 | history | failed extraction | P202 offline controller-dual prior extraction | train windows | prior mass / solved diagnostics | CONTEXT | DONE | Failed: sampled train windows produced 0 solved diagnostics and zero prior |
| H204 | history | existing baseline | GRU + uniform + `qp_carbon` | val/test | MAE / MSE / control KPIs | CONTEXT | DONE | Existing references: R103 + R112 |
| H205 | history | failed route | GRU + raw-CSFT + `qp_carbon` | val/test | MAE / MSE / control KPIs | CONTEXT | DONE | Existing references: R105 + R113 |
| H206 | history | blocked run | previous P203 controller-dual prior rerun | train/val/test | — | CONTEXT | BLOCKED | Not launched because P202 prior was unusable |
