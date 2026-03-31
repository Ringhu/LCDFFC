# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|--------|-----------|---------|------------------|-------|---------|----------|--------|-------|
| E01 | M0 | Lock stack | myopic,oracle,GRU,Moirai2,TimesFM2.5 | phase_1 | KPIs | MUST | TODO | |
| E02 | M1 | Train specialists | GRU,TSMixer; 5 scenarios; 3 seeds | all | MSE,MAE,KPIs | MUST | TODO | |
| E03 | M1 | FM sweep | Moirai2,TimesFM2.5; 5 scenarios | all | MAE,KPIs | MUST | TODO | |
| E04 | M1 | Leaderboard | all from E02+E03 | all | combined | MUST | TODO | |
| E05 | M1 | Rank correlation | all from E04 | all | Spearman/Kendall | MUST | TODO | |
| E06 | M2 | Oracle semantics | oracle variants; 3 scenarios | test | KPIs | MUST | TODO | |
| E07 | M2 | Perturbation | oracle; 3 scenarios | test | sensitivity heatmap | MUST | TODO | |
| E08 | M2 | Event errors | all models; 5 scenarios | test | event MAE | MUST | TODO | |
| E09 | M3 | CAVS validation | all from E04 | val | CAVS vs MSE selection | MUST | TODO | |
| E10 | M4 | Transfer | all; 2022 scenarios | test | KPIs | NICE | TODO | |
