# Pipeline Summary

**Problem**: fixed-objective forecast-control does not adapt gracefully when operator preferences shift online  
**Final Method Thesis**: use a language-conditioned high-level router to change low-level QP objectives and constraints without retraining the forecast-control stack  
**Final Verdict**: `REVISE`  
**Date**: 2026-03-19

## Final Deliverables
- Proposal: `refine-logs/FINAL_PROPOSAL.md`
- Review summary: `refine-logs/REVIEW_SUMMARY.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Experiment tracker: `refine-logs/EXPERIMENT_TRACKER.md`

## Contribution Snapshot
- Dominant contribution:
  language-conditioned dynamic objective routing for forecast-then-control
- Optional supporting contribution:
  deterministic fallback for safe routing
- Explicitly rejected complexity:
  make DFL, uncertainty, and second-benchmark transfer co-equal main contributions

## Must-Prove Claims
- The same low-level controller can adapt online to changing preferences without retraining.
- Language-conditioned routing is meaningfully better or at least more expressive than simpler alternatives.

## First Runs to Launch
1. Build preference-shift evaluation regimes and scoring.
2. Reproduce fixed-weight baselines for each objective emphasis.
3. Compare heuristic router vs language-conditioned router on the preference-shift task.

## Main Risks
- Language is unnecessary:
  A structured non-language router may match performance.
- Preference shifts look artificial:
  Reviewer skepticism if regimes are not realistic.
- Low-level control contamination:
  Base-loop instability could blur the novelty claim.

## Next Action
- Proceed to `/run-experiment`
