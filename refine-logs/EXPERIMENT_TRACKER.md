# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|--------|-----------|---------|------------------|-------|---------|----------|--------|-------|
| R201 | M0 | preflight | oracle alignment check (`oracle slices` vs `env future`) | test | max_abs_error on `price/load/solar` | MUST | TODO | PASS iff each channel `<= 1e-6` over first 20 matched steps |
| R202 | M0 | preflight | raw-label utility check (`uniform` vs `raw-CSFT`) | test | top-decile MAE ratio | MUST | TODO | PASS iff raw-CSFT top-decile MAE is not worse than uniform by >5% |
| R203 | M1 | main method | GRU + stabilized-CSFT (`clip@q95 -> log1p -> normalize`, `alpha=0.85`, Huber=1.0) + `qp_carbon` | train/val/test | top-decile MAE / overall MAE / cost / carbon / peak | MUST | TODO | Launch only if R201 and R202 both PASS |
| R204 | M2 | strongest simple baseline | GRU + strongest simple heuristic weighting + `qp_carbon` | train/val/test | top-decile MAE / overall MAE / cost / carbon / peak | MUST | TODO | Launch only if R203 passes acceptance rule |
| R205 | M3 | mechanism package | decile curve + raw vs stabilized weight distribution + acceptance dashboard | test | figures/tables | MUST | TODO | Needed whether R203 is positive or negative |
| R206 | M4 | controller specificity | stabilized-CSFT with mismatched controller labels | train/val/test | top-decile MAE / cost / carbon / peak | NICE | TODO | Only if R203 is clearly positive |
| H101 | history | existing baseline | GRU + uniform loss + `qp_carbon` | val/test | MAE / MSE / control KPIs | CONTEXT | DONE | Existing references: R103 + R112 |
| H102 | history | existing pilot | GRU + raw-CSFT + `qp_carbon` | val/test | MAE / MSE / control KPIs | CONTEXT | DONE | Existing references: R105 + R113 |
| H103 | history | existing upper bound | oracle forecast + `qp_carbon` | test | cost / carbon / peak / ramping | CONTEXT | DONE | Existing reference: R104 |
