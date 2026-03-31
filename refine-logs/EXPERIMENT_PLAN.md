# Experiment Plan

**Problem**: Forecast-control misalignment in building energy management
**Method Thesis**: CAVS selects better forecasting models than MSE/MAE
**Date**: 2026-03-31 (revised — expanded E01 model pool)

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|-------|----------------|----------------------------|---------------|
| C1: Misalignment is systematic | Core thesis — if MSE rankings match KPI rankings, there's no problem | Rank reversals (Spearman < 0.7) across 5 scenarios, 7 models | B2, B3 |
| C2: CAVS > MSE selection | Main method contribution — CAVS must actually help | CAVS-selected model beats MSE-selected on 2+ KPIs in majority of scenarios | B4, B5 |

## Paper Storyline

- Main paper must prove: misalignment exists across model families (trained + FM); CAVS fixes model selection
- Appendix can support: per-scenario breakdowns, event-critical error tables, oracle semantics
- Experiments intentionally cut: RL baseline, full SPO+ end-to-end training, LLM routing

## Model Pool (7 models)

| Model | Family | Type | Training | Notes |
|-------|--------|------|----------|-------|
| GRU | Trained | Seq2Seq | MSE on CityLearn | Existing in factory |
| PatchTST | Trained | Patch-Transformer | MSE on CityLearn | Existing in factory |
| TSMixer | Trained | MLP-Mixer | MSE on CityLearn | Existing in factory |
| DLinear | Trained | Linear decomposition | MSE on CityLearn | **Needs implementation** |
| Chronos-2 | Foundation | Probabilistic | Zero-shot | Adapter exists (`amazon/chronos-2`) |
| Moirai2 | Foundation | Universal | Zero-shot | Adapter exists (`Salesforce/moirai-2.0-R-small`) |
| TimesFM 2.5 | Foundation | Decoder-only | Zero-shot | Adapter exists (`google/timesfm-2.5-200m-transformers`) |

Plus two diagnostic baselines (not in the 7-model pool):
- **myopic**: repeat current observation across horizon
- **oracle**: ground-truth future (upper bound reference)

## Experiment Blocks

### Block 1: Lock corrected stack + full baseline sweep (E01)
- Claim tested: Baseline reproducibility; initial misalignment signal
- Priority: MUST-RUN
- Why this block exists: Before any claims, we need all 7 models + 2 diagnostic baselines running on the corrected stack with consistent KPI computation
- Scenario: citylearn_challenge_2023_phase_1
- Compared systems:
  - Diagnostic: myopic, oracle
  - Trained (need training first): GRU, PatchTST, TSMixer, DLinear
  - Foundation (zero-shot): Chronos-2, Moirai2, TimesFM 2.5
- Metrics: MSE, MAE per channel; control KPIs (cost, carbon, peak, ramping)
- Setup details:
  - Trained models: train on phase_1 train split, seed=42, ~100 epochs, early stop on val MSE
  - Foundation models: zero-shot inference, horizon=24, context_length=168
  - Controller: qp_carbon with default weights
  - Device: cuda:2
- Success criterion: All 9 systems produce valid KPIs; at least one rank reversal visible (MSE rank ≠ KPI rank)
- Failure interpretation: If no rank reversal on phase_1, thesis may still hold on other scenarios but E01 doesn't give early signal
- Table / figure target: Table 1 draft (sanity), not final paper table
- Sub-tasks:
  1. Implement DLinear forecaster + add to factory
  2. Train GRU, PatchTST, TSMixer, DLinear on phase_1 (seed=42)
  3. Run all 4 trained models through run_controller.py
  4. Run Chronos-2, Moirai2, TimesFM 2.5 through run_foundation_control.py
  5. Run myopic and oracle through run_controller.py
  6. Collect all KPIs into single comparison table
- GPU-hours: 10 (4 training + 6 inference/control)
- Risk: Low-Medium (DLinear implementation is straightforward; main risk is FM dependency issues)

### Block 2: Multi-scenario misalignment — trained models (E02)
- Claim tested: C1
- Priority: MUST-RUN
- Models: GRU, PatchTST, TSMixer, DLinear; 5 scenarios; 3 seeds each
- Scenarios: phase_1, phase_2_local, phase_3_1, phase_3_2, phase_3_3
- Output: 4 models × 5 scenarios × 3 seeds = 60 checkpoints + forecast/KPI tables
- GPU-hours: 60 (increased from 40 due to 4 trained models instead of 2)
- Risk: Medium (training may not converge on all scenarios for all backbones)

### Block 3: Multi-scenario misalignment — foundation models (E03)
- Claim tested: C1
- Priority: MUST-RUN
- Models: Chronos-2, Moirai2, TimesFM 2.5; 5 scenarios (zero-shot)
- Output: 3 FM × 5 scenarios = 15 forecast/control result sets
- GPU-hours: 15 (increased from 10 due to adding Chronos-2)
- Risk: Low (zero-shot, no training)

### Block 4: Leaderboard + rank correlation (E04, E05)
- Claim tested: C1
- Priority: MUST-RUN
- Input: All results from E02 + E03 (7 models × 5 scenarios)
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
- Models: All 7 from E04; 5 scenarios
- Analysis: Compute forecast error specifically during high-price, high-carbon, and peak-load events
- Output: Event-error table showing which models fail on controller-critical windows
- GPU-hours: 1 (analysis only)
- Risk: Low

### Block 7: CAVS validation (E09)
- Claim tested: C2
- Priority: MUST-RUN
- Input: All 7 models from E04 + sensitivity map from E07
- Method: Compute CAVS for each model; select model by CAVS vs by MSE vs by MAE; compare selected model's KPIs
- Output: Model-selection comparison table + KPI improvement chart
- GPU-hours: 4
- Risk: High (core claim — if CAVS doesn't beat MSE selection, paper weakens significantly)
- Decision gate: CAVS-selected model must beat MSE-selected on 2+ KPIs in 3+ scenarios

### Block 8: External transfer (E10)
- Claim tested: Generalization
- Priority: NICE-TO-HAVE
- Models: All 7; CityLearn 2022 scenarios (phase_1, phase_2, phase_3)
- Output: Transfer table showing whether misalignment and CAVS advantage hold on different building stock
- GPU-hours: 25 (increased due to more trained models)
- Risk: Medium

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|-----------|------|------|---------------|------|------|
| M0 | Sanity + full baseline | E01 | All 9 systems produce valid KPIs; initial rank reversal visible | 10h | Low-Med |
| M1 | Misalignment evidence | E02-E05 | Rank reversals exist (Spearman < 0.7) across scenarios | 76h | Medium |
| M2 | Mechanism | E06-E08 | Sensitivity structure found; event errors explain misalignment | 13h | Medium |
| M3 | CAVS validation | E09 | CAVS beats MSE selection on 2+ KPIs | 4h | High |
| M4 | Transfer | E10 | Results hold on 2022 family | 25h | Medium |

## Compute and Data Budget

- Total: ~128 GPU-hours (minimum viable without E10: ~103h)
- GPU: single GPU (cuda:2)
- Data: CityLearn 2023 (5 scenarios) + CityLearn 2022 (3 scenarios, optional)
- Environment: CityLearn v2.1b12 (2023 challenge version)
- Seeds: 3 per trained model configuration (E02); seed=42 only for E01

## Pre-requisites Before E01

1. **Implement DLinear forecaster**: Create `models/dlinear_forecaster.py`, add `dlinear` to `models/factory.py`
2. **Verify Chronos-2 adapter**: Confirm `eval/foundation_model_adapters.py` Chronos2Adapter works on cuda:2
3. **Update configs/cavs.yaml**: Add all 7 models to sweep config

## Risks and Mitigations

- DLinear implementation: Simple architecture (two linear layers with decomposition), low risk. Fallback: drop DLinear and use 6 models.
- Chronos-2 dependency: HuggingFace model download may fail on cluster. Mitigation: pre-download to local cache.
- Training budget increase: 60h for E02 (was 40h). Mitigation: can reduce to 2 seeds if budget tight.
- FM inference time: Chronos-2 is slower than Moirai2/TimesFM. Mitigation: batch inference, reduce context if needed.

## Final Checklist

- [ ] Main paper tables are covered (7-model leaderboard + rank correlation)
- [ ] Novelty is isolated (CAVS vs MSE/MAE selection comparison)
- [ ] Simplicity is defended (CAVS is post-hoc scoring, no retraining needed)
- [ ] Frontier contribution is justified (FM zero-shot results support misalignment claim)
- [ ] Nice-to-have runs are separated from must-run runs (E10 is NICE-TO-HAVE)
- [ ] DLinear implementation is a pre-requisite for E01
