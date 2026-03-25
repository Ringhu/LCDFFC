# Initial Experiment Results

**Date**: 2026-03-25
**Plan**: `refine-logs/EXPERIMENT_PLAN.md`
**Topic**: CSFT pilot failure diagnosis

## Raw Data Table

### Forecast-side comparison

| System | Val loss | Test loss* | Overall MSE | Overall MAE | Price MSE | Load MSE | Solar MSE |
|---|---:|---:|---:|---:|---:|---:|---:|
| GRU + uniform | 0.134295 | 0.203695 | 1.132944 | 0.363535 | 0.814345 | 2.552710 | 0.031776 |
| GRU + CSFT (`alpha=0.5`) | 0.121692 | 0.181953 | 1.190106 | 0.393872 | 0.911787 | 2.601809 | 0.056723 |

\* `test_loss` is not the cleanest cross-mode metric because CSFT uses weighted mixed loss while uniform uses the uniform version of the same loss function. The more reliable cross-mode metrics are `overall_mse` / `overall_mae` and per-target MSE/MAE.

### Control-side comparison (`qp_carbon` replay)

| System | Cost | Carbon | Peak | Ramping | Avg Net Load |
|---|---:|---:|---:|---:|---:|
| Oracle forecast + `qp_carbon` | 33.833866 | 511.593814 | 16.227163 | 1020.678528 | 1.284337 |
| Uniform forecast + `qp_carbon` | 31.669215 | 480.774130 | 15.729058 | 850.380737 | 1.280156 |
| CSFT forecast + `qp_carbon` | 32.462909 | 489.856484 | 16.375679 | 861.327881 | 1.263511 |

### Label distribution snapshot

| Split | Samples | Raw mean | Raw max | Normalized mean | Normalized max |
|---|---:|---:|---:|---:|---:|
| Train | 456 | 0.046178 | 2.138771 | 0.765338 | 37.492641 |
| Val | 62 | 0.050428 | 2.113926 | 0.838696 | 36.289032 |
| Test | 61 | 0.039599 | 2.308118 | 0.672095 | 71.900040 |

## Key Findings

1. **CSFT does not beat the uniform baseline on forecast metrics.**
   - Observation: `overall_mse` worsens from `1.132944` to `1.190106` (`+5.0%`), and `overall_mae` worsens from `0.363535` to `0.393872` (`+8.3%`). Price/load/solar MSE all worsen, with solar MSE degrading the most (`0.031776 -> 0.056723`, about `+78.5%`).
   - Interpretation: the current weighting scheme is not reallocating capacity in a useful way; it is simply hurting forecast quality.
   - Implication: the current CSFT implementation does **not** support the claim that controller-sensitive weighting helps the forecasting model.
   - Next step: compute top-sensitivity-decile error for uniform vs CSFT. If CSFT does not improve even the most sensitive cells, the label/weighting design is likely wrong rather than merely too strong.

2. **CSFT also loses on the final control KPIs.**
   - Observation: compared with uniform, CSFT is worse on `cost` (`31.6692 -> 32.4629`, `+2.5%`), `carbon` (`480.7741 -> 489.8565`, `+1.9%`), `peak` (`15.7291 -> 16.3757`, `+4.1%`), and `ramping` (`850.3807 -> 861.3279`, `+1.3%`).
   - Interpretation: even after plugging forecasts into the real `qp_carbon` loop, CSFT does not recover a control-side gain.
   - Implication: the current main thesis is **not supported** in this pilot.
   - Next step: do not scale to more seeds/backbones yet. Enter route-A failure diagnosis first.

3. **The label distribution is extremely spiky, especially on test.**
   - Observation: normalized max weight is about `37.5` on train and `71.9` on test while normalized means stay below `1`.
   - Interpretation: the finite-difference sensitivity map is concentrating too much mass on a very small number of cells. This can make optimization brittle and degrade overall learning.
   - Implication: the current weighting may be too sharp for `alpha=0.5`.
   - Next step: test stronger clipping / softer transforms (`sqrt`, `log1p`, temperature) and a weaker mix such as `alpha=0.8` or `0.9` before changing the whole idea.

4. **The current oracle result is suspiciously worse than the learned uniform baseline.**
   - Observation: oracle + `qp_carbon` is worse than learned-uniform on `cost`, `carbon`, `peak`, and especially `ramping`. For example, oracle `cost=33.8339` vs uniform `31.6692`, oracle `ramping=1020.68` vs uniform `850.38`.
   - Interpretation: something is off in the current “oracle” notion. Either the oracle series is not perfectly aligned with the environment timeline, or the raw future signals are less controller-friendly than the smoothed learned forecast, or the controller/eval interface still has a mismatch.
   - Implication: oracle gap is currently **not trustworthy** as a paper argument. This is a high-priority diagnosis item before using oracle as an upper bound.
   - Next step: log the first 20 steps of env-true future `price/load/solar` and compare them to `build_oracle_forecast(...)` slices exactly. If they are not identical, fix alignment before any further interpretation.

5. **Val loss improves while test MSE/MAE worsen, which suggests the optimization target itself may be mis-specified.**
   - Observation: CSFT has better validation loss (`0.121692` vs `0.134295`) but worse held-out forecast metrics and worse downstream control.
   - Interpretation: the weighted validation objective may be rewarding the wrong regions, or the model is overfitting to unstable sensitivity labels.
   - Implication: “better weighted loss” is not evidence of a better method here.
   - Next step: add per-horizon / per-target and top-decile metrics instead of relying on the weighted validation loss alone.

## Route-A Failure Diagnosis

### Likely problem 1: the labels are too sharp / too noisy
- Why this is plausible:
  - label maxima are very high relative to the mean
  - CSFT hurts all three target metrics rather than making a clean tradeoff
- Most informative diagnostic:
  - bucket future cells by sensitivity decile and compare uniform vs CSFT error **within those buckets**
- What would confirm it:
  - if CSFT does not improve the highest-sensitivity bucket, then the label is not useful signal
- Minimal test:
  - reuse existing checkpoints and labels; compute decile-wise MSE/MAE on test

### Likely problem 2: the stage objective is too myopic
- Why this is plausible:
  - labels are built from first-step stage objective sensitivity, but the controller optimizes over a 24-step horizon
  - this may overweight immediate responses that do not improve the full episode KPI
- Most informative diagnostic:
  - compare current labels against a short-horizon cumulative objective (e.g. first 4 or 6 steps) on a small subset
- What would confirm it:
  - if the label map changes substantially and aligns better with simpler heuristics, the current label target is too narrow
- Minimal test:
  - compute alternative labels on 20-50 samples only; no need to retrain first

### Likely problem 3: the weighting strength is too aggressive for this dataset size
- Why this is plausible:
  - `alpha=0.5` means the weighted term has a large influence
  - train set is only 456 windows; sharp weights can easily destabilize fitting
- Most informative diagnostic:
  - rerun CSFT with the same labels but `alpha=0.8` and/or stronger clipping
- What would confirm it:
  - if softer weighting recovers uniform-level MSE while improving control-critical slices, then the idea is not dead; the current weighting is just too strong
- Minimal test:
  - one rerun each for `alpha=0.8` and `clip_quantile=0.8` or a `sqrt(weight)` transform

### Likely problem 4: the current oracle path may not be a valid upper bound
- Why this matters:
  - if oracle is worse than learned-uniform, then one of the main diagnostic anchors is unstable
- Most informative diagnostic:
  - step-by-step alignment check between environment future and `oracle_data_path`
- Minimal test:
  - dump the first 20 steps of oracle-sliced `price/load/solar` and compare against env-derived future values from the same episode

## Suggested Next Experiments

### Highest priority (cheap, diagnostic-first)
1. **D1: Top-decile error analysis**
   - Input: existing `uniform` and `CSFT` checkpoints + existing test labels
   - Output: decile-wise MSE/MAE table and plot
   - Goal: check whether CSFT helps the cells it claims to care about

2. **D2: Oracle alignment sanity check**
   - Input: existing oracle pipeline
   - Output: first-20-step comparison between env future and oracle slices
   - Goal: verify whether oracle is a trustworthy upper bound

3. **D3: Softened-CSFT rerun**
   - Variant A: `alpha=0.8`
   - Variant B: stronger clipping or `sqrt(weight)` transform
   - Goal: test whether the current failure is caused by over-aggressive weighting rather than a fundamentally wrong direction

### Only after D1-D3
4. **D4: manual_horizon / event_window baselines**
   - Reason: if softened CSFT still loses, you need to know whether simple heuristics outperform it

5. **D5: alternative label objective on small subset**
   - Reason: only worth doing if D1 says the current labels are not helping the sensitive cells at all

## Concise Finding Statement

Current pilot evidence does **not** support the CSFT thesis. In this setting, CSFT underperforms the uniform baseline on both held-out forecasting metrics and final `qp_carbon` control KPIs, while the current oracle result is also suspiciously worse than learned-uniform, indicating that label sharpness and oracle alignment should be diagnosed before scaling the study.
