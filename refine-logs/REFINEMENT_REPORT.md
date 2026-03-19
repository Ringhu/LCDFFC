# Refinement Report

**Date**: 2026-03-19  
**Initial Verdict**: `REVISE`  
**Final Verdict**: `REVISE, BUT CLEARLY ACTIONABLE`

## What Changed During Refinement

### Before

The project narrative implicitly tried to combine:

- fixed-weight forecast + QP
- uncertainty-aware fallback
- decision-focused learning
- LLM preference routing
- optional Grid2Op transfer

This was a reasonable research roadmap but a weak single-paper thesis.

### After

The refined paper story became:

> Keep the low-level forecast + QP controller fixed, and make the paper about high-level language-conditioned objective adaptation.

## Why This Is Better

1. It gives the paper one dominant contribution.
2. It reuses the strongest verified engineering asset in the repo.
3. It places the LLM in the most defensible role.
4. It creates a clean novelty-isolation experiment.

## Claims Matrix

| Outcome | Allowed Claim |
|---|---|
| LLM router beats fixed weights and simpler routers under preference shifts | Strong claim: language-conditioned objective routing improves adaptive control without retraining |
| LLM router ties a non-language structured router | Downgraded claim: preference-conditioned routing matters, but language itself is not necessary |
| LLM router loses to a simple rule router | No strong language claim; paper should pivot away from LLM novelty |
| Fixed low-level loop remains strong while router helps only under shifts | Good focused paper story |
| Router hurts core KPI even under the right preference | Thesis needs rethink or scope reduction |

## Current Risk Register

### Risk 1
The language layer is unnecessary.

- Mitigation:
  include a structured non-language router baseline and a rule-based router.

### Risk 2
The preference-shift task looks synthetic.

- Mitigation:
  design preference schedules tied to realistic operator scenarios such as price spikes, carbon alerts, and grid stress windows.

### Risk 3
The paper overclaims generality from one environment.

- Mitigation:
  keep the main claim tied to exogenous sequential control with CityLearn as the anchor; treat Grid2Op as optional later validation.

## Bottom-Line Recommendation

The project should move forward under the refined thesis. The right next step is not more architecture. The right next step is a clean experiment package that tests whether language-conditioned routing is truly necessary and valuable.
