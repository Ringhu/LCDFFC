# Research Review: First Research Line Re-evaluation

**Date**: 2026-03-27
**Reviewer**: GPT-5.4 (xhigh reasoning) via Codex MCP
**Thread ID**: `019d2e83-eac7-7bd2-b02d-0ac70ff8f5e1`
**Score**: 4/10 (current state), medium odds if pivoted to Direction A

---

## Executive Summary

The current LCDFFC project bundles three partially connected stories (CSFT, backbone benchmarking, LLM routing) without a clear central thesis. None of the three is individually strong enough for CCF-A in its current form. However, the strongest empirical signal — **forecast-control misalignment** — is a viable paper direction if properly scoped and expanded.

---

## Key Findings

### 1. LLM "Agent" Framing Is Overstated
- Most router variants are hand-built profile selectors, not LLMs
- The prompt-only LLM (Qwen 0.5B) is not consistently strong
- No systematic evaluation results saved
- At best a "conditioned hyperparameter selector," not an agent

### 2. CSFT Line Not Yet Validated
- Raw-CSFT: falsified (R202 ratio 1.0546 > 1.05)
- Controller-dual prior: failed (offline QP infeasible)
- Replay-prior: improves forecast MAE dramatically (0.282 vs 0.364) but slightly worsens control KPIs vs uniform
- Q204 (strongest heuristic comparison) still TODO

### 3. Experimental Scope Too Narrow
- 1 schema, 1 seed, 1 controller family
- Not enough for NeurIPS/ICML/KDD main track

### 4. Foundation Models Dominate
- Moirai2: cost=29.17, carbon=446.43 (zero-shot)
- Best trained (GRU uniform): cost=31.67, carbon=480.77
- ~8% cost improvement, ~7% carbon improvement from zero-shot FMs

### 5. Forecast-Control Misalignment Is the Strongest Signal
- GRU wins forecast MSE but loses to FMs on control
- Replay-prior improves forecast but worsens control
- Input-oracle doesn't give best control either
- This is the most interesting and publishable finding

---

## Recommended Paper Direction

### Direction A: Forecast-Control Misalignment (BEST)

**Core Thesis**: Average forecast error is a poor proxy for downstream control quality in forecast-then-control building energy systems, and a simple controller-aware validation score selects better forecasting models than MSE/MAE.

**Title Options**:
1. "Forecast Accuracy Is Not Enough: Diagnosing Forecast-Control Misalignment in Building Energy Management"
2. "When Better Forecasts Do Not Yield Better Control: Control-Aware Model Selection for CityLearn"
3. "Forecast-Control Misalignment in Building Energy Systems: A Multi-Scenario Study with Foundation Models"
4. "Control-Aware Validation Beats MSE for Forecast-Then-Control in Building Energy Management"

**Venue**: KDD safest CCF-A target; NeurIPS/ICML only with constructive method

### Direction Ranking (by CCF-A probability)
1. **A. Forecast-Control Misalignment** — medium odds
2. **D. Combined A+B** — medium-low to medium
3. **B. Foundation Model + Control** — medium-low
4. **C. Context-Adaptive Routing** — low

---

## Paper Outline

### 1. Introduction
- Claim: forecast model ranking by MAE/MSE can invert under downstream control
- Fig 1: pipeline overview + motivating rank-reversal example

### 2. Problem Setup
- Claim: the controller only values some channels, horizons, and events
- Fig 2: notation and setup diagram

### 3. Benchmark Design
- Claim: multi-scenario evaluation required because ranking is scenario-dependent
- Table 1: scenario pack, dataset names, evaluation protocol

### 4. Empirical Misalignment
- Claim: forecast metrics and control KPIs disagree systematically
- Table 2: main benchmark leaderboard
- Fig 3: scatter of forecast metric vs control KPI
- Fig 4: rank-correlation heatmap

### 5. Mechanism Analysis
- Claim: control is most sensitive to specific channel-horizon-event regions
- Fig 5: channel-horizon perturbation sensitivity heatmap
- Fig 6: event-critical error analysis

### 6. Constructive Method: Control-Aware Validation Score (CAVS)
- Claim: sensitivity-weighted validation predicts downstream performance better
- Eq 1: CAVS definition
- Table 3: model-selection comparison
- Fig 7: selected-model KPI improvement

### 7. Discussion
- Foundation models help because of controller-compatible error patterns

### 8. Limitations
- About evaluation and model selection, not full end-to-end optimal control

---

## CAVS Formula

```
CAVS(f) = mean_i mean_{h,c} [ s_i(h,c) * |ŷ_f(i,h,c) - y(i,h,c)| ]
```

**Version 1 (Global, fast)**: Reuse replay-calibrated sensitivity map G(h,c)
```
CAVS-global(f) = mean_i mean_{h,c} [ G(h,c) * abs_error_f(i,h,c) ]
```

**Version 2 (Local, stronger)**: Per-window perturbation sensitivity
```
s_i(h,c) = |J(F + δe_hc) - J(F - δe_hc)| / (2δ)
```

**Relation to CSFT**: This salvages the CSFT work — sensitivity is more reliable for evaluation/model-selection than for direct weighted training.

---

## 10-Experiment Schedule

| ID | What it tests | Models / Scenarios | Output | Depends | GPU-h |
|---|---|---|---|---|---:|
| E01 | Lock corrected stack, reproduce baselines | myopic, input-oracle, GRU, Moirai2, TimesFM2.5 on phase_1 | Sanity table | None | 6 |
| E02 | Train specialists across 2023 scenarios | GRU, TSMixer; 5 scenarios; 3 seeds | Checkpoints + forecast tables | E01 | 40 |
| E03 | Zero-shot FM sweep across 2023 scenarios | Moirai2, TimesFM2.5; 5 scenarios | FM forecast/control table | E01 | 10 |
| E04 | Build main multi-scenario leaderboard | All from E02+E03 | Main paper table | E02, E03 | 1 |
| E05 | Quantify forecast-metric vs KPI misalignment | All runs from E04 | Scatter + rank-correlation heatmap | E04 | 0 |
| E06 | Clarify oracle semantics | myopic, input-oracle, stronger oracle; 3 scenarios | Oracle comparison table | E01 | 4 |
| E07 | Channel-horizon perturbation sensitivity | input-oracle or best forecast; 3 scenarios | Sensitivity heatmap | E06 | 8 |
| E08 | Event-critical error analysis | GRU, TSMixer, Moirai2, TimesFM2.5; 5 scenarios | Error-on-events table | E04 | 1 |
| E09 | Evaluate CAVS | Candidate models from E04; validation-based selection | Model-selection table + KPI gains | E07, E08 | 4 |
| E10 | External transfer (2022 family) | GRU, TSMixer, Moirai2, TimesFM2.5 on 2022 scenarios | Transfer table | E02, E03, E09 | 20 |

**Minimum viable**: E01-E05 + E07 + E09 = ~63 GPU-h
**Full paper**: + E06 + E08 + E10 = ~94 GPU-h

---

## Results-to-Claims Matrix

| Outcome | Observation | Claim Allowed | Claim NOT Allowed |
|---|---|---|---|
| A. Strong positive | Rank reversals replicate; CAVS selects better models | "Average forecast error is unreliable proxy; controller-aware validation improves selection" | "We solved forecast-then-control" |
| B. Moderate positive | Misalignment exists; CAVS helps on some KPIs/scenarios | "Forecast metrics insufficient in important cases; CAVS useful for KPI-sensitive selection" | "CAVS is universally better" |
| C. Benchmark-only | FMs dominate; CAVS weak/unstable | "FMs yield more control-compatible forecasts; average metrics don't explain downstream value" | "We propose a strong new validation method" |
| D. Oracle-cleanup weakens anomaly | Rank reversals shrink after corrections | "Originally observed anomaly partly due to controller abstraction" | "Misalignment is general phenomenon" |
| E. Negative | MAE/MSE rankings mostly agree with control KPIs | No CCF-A paper on this thesis | Any broad ML claim |

---

## CityLearn Scenario Pack

**Minimum (2023 family)**:
- `citylearn_challenge_2023_phase_1`
- `citylearn_challenge_2023_phase_2_local_evaluation`
- `citylearn_challenge_2023_phase_3_1`
- `citylearn_challenge_2023_phase_3_2`
- `citylearn_challenge_2023_phase_3_3`

**External validation (2022 family)**:
- `citylearn_challenge_2022_phase_1`
- `citylearn_challenge_2022_phase_2`
- `citylearn_challenge_2022_phase_3`

**Optional stretch**: `citylearn_challenge_2020_climate_zone_1` to `_4`

Pin environment version: CityLearn v2.1b12 (2023 challenge version).

---

## Execution Order

1. Freeze corrected stack → E01
2. Launch GRU + TSMixer training → E02
3. Run FM sweep → E03
4. Build leaderboard → E04 + E05
5. If rank reversals replicate → E07 + E09
6. Then E06 + E10

---

## Mock Review (Current State)

**Score**: 4/10
**Confidence**: 4/5

**Strengths**:
- Technically broad codebase
- Targets important problem (forecast-control alignment)
- Interesting empirical finding (rank reversals)
- Documents negative results honestly

**Weaknesses**:
- Three contributions bundled without clear thesis
- LLM/agent claim weak (mostly hand-built routing)
- CSFT doesn't improve control over uniform
- Experimental scope too narrow (1 schema, 1 seed)
- Baselines weak or mislabeled (zero-action had been labeled as a rule-based-control baseline)
- Strongest result (FM dominance) unrelated to proposed method
- Controller-path issues create concern about comparison cleanliness

**What Would Move Toward Accept**:
- Reduce to one claim
- Recompute all results on corrected stack
- Add stronger, correctly named baselines
- Show robustness across multiple scenarios and seeds
- Demonstrate stable gain with constructive method (CAVS)
