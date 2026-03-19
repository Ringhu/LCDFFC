# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R001 | M0 | define regime protocol | preference schedule generator | val | protocol sanity | MUST | TODO | cost/carbon/peak/reserve regimes |
| R002 | M0 | scoring sanity | preference-matched KPI scorer | val | regret / match score | MUST | TODO | align with fixed baselines |
| R003 | M1 | baseline | fixed-weight learned forecast + QP | test | cost/carbon/peak | MUST | DONE | current validated base loop exists |
| R004 | M1 | baseline | fixed-weight variants per objective | test | cost/carbon/peak | MUST | TODO | one tuned setting per objective |
| R005 | M2 | prototype | heuristic rule router | test | regime regret | MUST | TODO | first high-level adaptation baseline |
| R006 | M2 | prototype | language-conditioned router v1 | test | regime regret | MUST | TODO | simple templated text prompts |
| R007 | M3 | ablation | structured numeric router | test | regime regret | MUST | TODO | no language |
| R008 | M3 | ablation | no-router fixed weights | test | regime regret | MUST | TODO | deletion baseline |
| R009 | M4 | robustness | text router + deterministic fallback | shifted | validity / KPI | MUST | TODO | malformed or low-confidence outputs |
| R010 | M5 | extension | best router under OOD price/weather | shifted | degradation | NICE | TODO | only after main claim succeeds |
