# Experiment Plan

**Problem**: Fixed-objective forecast-control does not adapt cleanly when operator preferences shift between cost, carbon, peak shaving, and resilience.  
**Method Thesis**: Use a language-conditioned router to change QP objectives/constraints online while keeping the low-level forecast + controller fixed.  
**Date**: 2026-03-19

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|---|---|---|---|
| C1: Dynamic objective adaptation without retraining | This is the actual paper thesis | Better KPI tradeoff than fixed weights under preference-shift episodes | B1 |
| C2: Language is justified, not decorative | Prevents novelty collapse | LLM/text router beats or generalizes better than simpler structured alternatives | B2, B3 |

## Paper Storyline

- Main paper must prove:
  - adaptation to changing objectives without low-level retraining
  - necessity or meaningful utility of language-conditioned routing
- Appendix can support:
  - fallback details
  - extra robustness plots
  - optional cross-seed analyses
- Experiments intentionally cut:
  - full DFL paper
  - full uncertainty ensemble paper
  - full Grid2Op transfer story

## Experiment Blocks

### Block 1: Main Anchor Result — Preference-Shift Evaluation
- Claim tested:
  C1
- Why this block exists:
  The paper lives or dies on whether the same low-level controller can adapt online to different preferences.
- Dataset / split / task:
  CityLearn 2023 Phase 1, with scripted preference regimes over a single episode or multiple held-out episodes.
- Compared systems:
  - fixed-weight learned forecast + QP
  - fixed-weight hand-tuned variants for each objective emphasis
  - heuristic rule router
  - refined language-conditioned router
- Metrics:
  - preference-matched KPI score
  - regret to best fixed controller for that regime
  - switch adaptation lag
- Setup details:
  Keep the low-level forecaster and QP fixed. Only route weights/constraints.
- Success criterion:
  Router matches or beats fixed controllers under changing regimes without retraining.
- Failure interpretation:
  The claimed adaptation advantage is weak or absent.
- Table / figure target:
  Main table + regime-shift figure.
- Priority:
  MUST-RUN

### Block 2: Novelty Isolation — Language vs Structured Preference Router
- Claim tested:
  C2
- Why this block exists:
  Without this, reviewers can say language is just decoration.
- Dataset / split / task:
  Same preference-shift task as Block 1.
- Compared systems:
  - text-conditioned router
  - numeric preference-vector router
  - rule-based router
- Metrics:
  - KPI regret
  - generalization to unseen or compositional preference prompts
- Setup details:
  Match low-level controller and evaluation schedule exactly.
- Success criterion:
  Language-conditioned routing provides either better generalization or meaningfully lower manual engineering burden with no control penalty.
- Failure interpretation:
  Downgrade the claim to generic preference-conditioned routing.
- Table / figure target:
  Main ablation table.
- Priority:
  MUST-RUN

### Block 3: Simplicity / Deletion Check
- Claim tested:
  The method is elegant and not overbuilt.
- Why this block exists:
  Reviewers will ask whether a much simpler router is enough.
- Dataset / split / task:
  Same anchor evaluation.
- Compared systems:
  - full text router
  - heuristic router only
  - no router (fixed weights)
- Metrics:
  same as Block 1, plus implementation complexity summary
- Setup details:
  Keep all else fixed.
- Success criterion:
  Full method wins or at least clearly justifies its extra complexity.
- Failure interpretation:
  Simpler method may be the better paper.
- Table / figure target:
  Compact deletion study in main paper or appendix depending on strength.
- Priority:
  MUST-RUN

### Block 4: Fallback / Robustness Check
- Claim tested:
  The routing layer is safe enough to be usable.
- Why this block exists:
  Safety is important, but this should not dominate the paper.
- Dataset / split / task:
  Preference shifts + noisy summary / invalid output scenarios.
- Compared systems:
  - router without fallback
  - router with deterministic fallback
- Metrics:
  invalid-output rate, KPI degradation, feasibility violations
- Setup details:
  Inject malformed or low-confidence routing cases.
- Success criterion:
  fallback protects feasibility with limited KPI cost.
- Failure interpretation:
  System is brittle and less credible.
- Table / figure target:
  Appendix or compact safety table.
- Priority:
  MUST-RUN

### Block 5: Optional Transfer or OOD Extension
- Claim tested:
  The idea is not narrowly tied to one schedule.
- Why this block exists:
  Strengthens the story if early results are good.
- Dataset / split / task:
  OOD weather/price variants or optional second benchmark later.
- Compared systems:
  best fixed baseline vs best router variant
- Metrics:
  degradation under shift
- Setup details:
  Only run after Blocks 1-4 succeed.
- Success criterion:
  Reasonable stability.
- Failure interpretation:
  Keep the paper narrower.
- Table / figure target:
  appendix or later extension.
- Priority:
  NICE-TO-HAVE

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|---|---|---|---|---|---|
| M0 | define preference regimes and metric logic | regime scripts + scoring checks | if metrics unclear, stop | low | evaluation ambiguity |
| M1 | baseline reproduction | fixed-weight variants + current learned controller | if fixed baselines unstable, stop | low | poor comparability |
| M2 | main router prototype | heuristic + text or text-like router | if no gain under shifts, rethink thesis | moderate | weak main claim |
| M3 | novelty isolation | text vs numeric vs rule router | if language adds nothing, downgrade claim | moderate | novelty collapse |
| M4 | fallback robustness | fallback ablation | if brittle, keep as future work | low-moderate | safety weakness |

## Compute and Data Budget

- Total estimated GPU-hours:
  modest if the low-level forecaster is frozen and routing is lightweight
- Data preparation needs:
  synthetic preference schedules and compact scenario summaries
- Human evaluation needs:
  none for first pass
- Biggest bottleneck:
  designing a convincing preference-shift protocol that is realistic enough

## Risks and Mitigations

- Risk:
  language-conditioned routing is no better than a numeric preference vector.
  - Mitigation:
    narrow the paper to preference-conditioned routing rather than forcing an LLM novelty claim.
- Risk:
  the shift task looks artificial.
  - Mitigation:
    tie preference regimes to realistic operator narratives.
- Risk:
  low-level controller issues contaminate routing evaluation.
  - Mitigation:
    freeze the current validated `forecast + QP` stack before router experiments.

## Final Checklist

- [ ] Main paper tables are covered
- [ ] Novelty is isolated
- [ ] Simplicity is defended
- [ ] Frontier contribution is justified or explicitly downgraded
- [ ] Nice-to-have runs are separated from must-run runs
