# Initial Experiment Results

**Date**: 2026-03-26
**Plan**: `refine-logs/EXPERIMENT_PLAN.md`
**Topic**: replay-calibrated controller prior after raw-CSFT failure

## Results by Milestone

### M0: Frozen falsification evidence — PASSED
- `R201` oracle alignment passes exactly:
  - `price=0.0`, `load=0.0`, `solar=0.0`
- `R202` raw-label utility fails:
  - uniform top-decile MAE = `0.25036`
  - raw-CSFT top-decile MAE = `0.26402`
  - ratio = `1.05457 > 1.05`
- Conclusion:
  - raw slot-wise CSFT is not a viable route in the current setting

### M1: Prior extraction
- Offline train-window dual extraction failed earlier:
  - sampled train windows returned no usable solved diagnostics
  - prior collapsed to all zeros
- Replay-calibrated prior extraction succeeds:
  - solved replay steps = `719 / 719`
  - nonzero prior fraction = `1.0`
  - similarity to manual horizon weighting:
    - correlation = `0.3791`
    - cosine = `0.3882`
- Interpretation:
  - replay-derived prior is nontrivial and not obviously identical to a simple front-loaded horizon mask

### M2: Main method — Q203 replay prior

#### Forecast-side
| System | Overall MSE | Overall MAE | Price MAE | Load MAE | Solar MAE |
|---|---:|---:|---:|---:|---:|
| Uniform (R103) | 1.13294 | 0.36354 | 0.42431 | 0.53409 | 0.13221 |
| Raw-CSFT (R105) | 1.19011 | 0.39387 | 0.44492 | 0.55036 | 0.18633 |
| Replay-prior (Q203) | 0.88843 | 0.28232 | 0.21557 | 0.52243 | 0.10895 |

#### Control-side (`qp_carbon` replay)
| System | Cost | Carbon | Peak | Ramping |
|---|---:|---:|---:|---:|
| Uniform (R112) | 31.6692 | 480.7741 | 15.7291 | 850.3807 |
| Raw-CSFT (R113) | 32.4629 | 489.8565 | 16.3757 | 861.3279 |
| Replay-prior (Q203) | 31.7324 | 483.4166 | 15.8958 | 846.3832 |

## Summary
- `[3/4]` current must-run blocks are now meaningfully advanced:
  - frozen falsification evidence: DONE
  - replay prior extraction: DONE
  - main replay-prior method: DONE
  - strongest heuristic comparison: TODO
- Main result:
  - replay-prior is **clearly better than raw-CSFT** on both forecast and control metrics
  - replay-prior is **much better than uniform on forecast metrics**
  - but replay-prior is **still slightly worse than uniform on primary control KPIs** (`cost`, `carbon`, `peak`), while slightly better on `ramping`
- Current verdict:
  - **positive pivot signal, but not yet a paper-claim win**
  - the route remains alive because it rescues raw-CSFT and gives a nontrivial prior, but it still must beat the strongest simple heuristic and ideally close the remaining uniform-control gap

## Next Step
1. Run `Q204`: strongest simple heuristic baseline under the same budget.
2. Compute high-prior-cell MAE directly for replay-prior vs uniform vs raw-CSFT.
3. Then decide whether to continue to strengthening or rewrite the claim more narrowly.
