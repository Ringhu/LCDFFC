# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|--------|-----------|---------|------------------|-------|---------|----------|--------|-------|
| E01-pre | M0 | Implement DLinear | DLinear forecaster | — | — | MUST | TODO | Add to factory.py |
| E01a | M0 | Train baselines (phase_1) | GRU,PatchTST,TSMixer,DLinear; seed=42 | phase_1 | MSE,MAE | MUST | TODO | ~4h training |
| E01b | M0 | FM inference (phase_1) | Chronos-2,Moirai2,TimesFM2.5 | phase_1 | MAE | MUST | TODO | Zero-shot |
| E01c | M0 | Diagnostic baselines | myopic,oracle | phase_1 | KPIs | MUST | TODO | |
| E01d | M0 | Control eval all | All 9 systems | phase_1 | cost,carbon,peak,ramping | MUST | TODO | Sanity table |
| E02 | M1 | Train specialists | GRU,PatchTST,TSMixer,DLinear; 5 scenarios; 3 seeds | all | MSE,MAE,KPIs | MUST | TODO | 60 checkpoints |
| E03 | M1 | FM sweep | Chronos-2,Moirai2,TimesFM2.5; 5 scenarios | all | MAE,KPIs | MUST | TODO | 15 result sets |
| E04 | M1 | Leaderboard | all 7 models from E02+E03 | all | combined | MUST | TODO | |
| E05 | M1 | Rank correlation | all from E04 | all | Spearman/Kendall | MUST | TODO | Decision gate: ρ < 0.7 |
| E06 | M2 | Oracle semantics | oracle variants; 3 scenarios | test | KPIs | MUST | TODO | |
| E07 | M2 | Perturbation | oracle; 3 scenarios | test | sensitivity heatmap | MUST | TODO | |
| E08 | M2 | Event errors | all 7 models; 5 scenarios | test | event MAE | MUST | TODO | |
| E09 | M3 | CAVS validation | all 7 from E04 | val | CAVS vs MSE selection | MUST | TODO | Decision gate |
| E10 | M4 | Transfer | all 7; 2022 scenarios | test | KPIs | NICE | TODO | |
