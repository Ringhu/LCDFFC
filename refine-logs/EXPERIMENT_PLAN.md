# Experiment Plan

**Problem**: Forecast-control misalignment in building energy management
**Method Thesis**: CAVS selects better forecasting models than MSE/MAE
**Date**: 2026-03-30

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|-------|----------------|----------------------------|---------------|
| C1: Misalignment is systematic | Core thesis — if MSE rankings match KPI rankings, there's no problem | Rank reversals (Spearman < 0.7) across 5 scenarios, 4+ models | B2, B3 |
| C2: CAVS > MSE selection | Main method contribution — CAVS must actually help | CAVS-selected model beats MSE-selected on 2+ KPIs in majority of scenarios | B4, B5 |

## Experiment Blocks

### Block 1: Lock corrected stack (E01)
- Claim tested: Baseline reproducibility
- Priority: MUST-RUN
- Models: myopic, oracle, GRU (MSE-trained), Moirai2, TimesFM2.5
- Scenario: citylearn_challenge_2023_phase_1
- What to check: KPIs reproduce on corrected stack; oracle gives reasonable upper bound; RBC baseline is properly labeled
- Output: Sanity table in reports/cavs/E01/
- GPU-hours: 6
- Risk: Low

### Block 2: Multi-backbone misalignment — trained models (E02)
- Claim tested: C1
- Priority: MUST-RUN
- Models: GRU, TSMixer; 5 scenarios; 3 seeds each
- Scenarios: phase_1, phase_2_local, phase_3_1, phase_3_2, phase_3_3
- Output: Checkpoints + forecast tables + KPI tables
- GPU-hours: 40
- Risk: Medium (training may not converge on all scenarios)

### Block 3: Multi-backbone misalignment — foundation models (E03)
- Claim tested: C1
- Priority: MUST-RUN
- Models: Moirai2, TimesFM2.5; 5 scenarios (zero-shot)
- Output: FM forecast/control tables
- GPU-hours: 10
- Risk: Low (zero-shot, no training)

### Block 4: Leaderboard + rank correlation (E04, E05)
- Claim tested: C1
- Priority: MUST-RUN
- Input: All results from E02 + E03
- E04: Build multi-scenario leaderboard (forecast metrics + control KPIs)
- E05: Compute Spearman/Kendall rank correlation between MSE ranking and KPI ranking
- Output: Main paper table + scatter plots + rank-correlation heatmap
- GPU-hours: 1 (analysis only)
- Risk: Medium (if correlations are high, C1 fails)
- Decision gate: If rank correlation > 0.85 across all scenarios, thesis is weak

### Block 5: Oracle semantics + perturbation sensitivity (E06, E07)
- Claim tested: C1 mechanism
- Priority: MUST-RUN
- E06: Compare oracle variants (myopic, input-oracle, stronger oracle) on 3 scenarios
- E07: Channel-horizon perturbation analysis — perturb oracle at each (channel, horizon) cell, measure KPI change
- Output: Oracle comparison table + sensitivity heatmap (24 horizons × 3 channels)
- GPU-hours: 12 (4 + 8)
- Risk: Medium

### Block 6: Event-critical error analysis (E08)
- Claim tested: C1 mechanism
- Priority: MUST-RUN
- Models: All from E04; 5 scenarios
- Analysis: Compute forecast error specifically during high-price, high-carbon, and peak-load events
- Output: Event-error table showing which models fail on controller-critical windows
- GPU-hours: 1 (analysis only)
- Risk: Low

### Block 7: CAVS validation (E09)
- Claim tested: C2
- Priority: MUST-RUN
- Input: All models from E04 + sensitivity map from E07
- Method: Compute CAVS for each model; select model by CAVS vs by MSE vs by MAE; compare selected model's KPIs
- Output: Model-selection comparison table + KPI improvement chart
- GPU-hours: 4
- Risk: High (core claim — if CAVS doesn't beat MSE selection, paper weakens significantly)
- Decision gate: CAVS-selected model must beat MSE-selected on 2+ KPIs in 3+ scenarios

### Block 8: External transfer (E10)
- Claim tested: Generalization
- Priority: NICE-TO-HAVE
- Models: All from E02+E03; CityLearn 2022 scenarios (phase_1, phase_2, phase_3)
- Output: Transfer table showing whether misalignment and CAVS advantage hold on different building stock
- GPU-hours: 20
- Risk: Medium

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|-----------|------|------|---------------|------|------|
| M0 | Sanity | E01 | Baselines reproduce on corrected stack | 6h | Low |
| M1 | Misalignment evidence | E02-E05 | Rank reversals exist (Spearman < 0.7) | 51h | Medium |
| M2 | Mechanism | E06-E08 | Sensitivity structure found; event errors explain misalignment | 13h | Medium |
| M3 | CAVS validation | E09 | CAVS beats MSE selection on 2+ KPIs | 4h | High |
| M4 | Transfer | E10 | Results hold on 2022 family | 20h | Medium |

## Compute and Data Budget

- Total: ~94 GPU-hours (minimum viable without E10: ~63h)
- GPU: single GPU (GPU 2)
- Data: CityLearn 2023 (5 scenarios) + CityLearn 2022 (3 scenarios, optional)
- Environment: CityLearn v2.1b12 (2023 challenge version)
- Seeds: 3 per trained model configuration
