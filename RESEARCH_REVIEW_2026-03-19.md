# Research Review (2026-03-19)

## Scope

This document records a full local run of the requested research review and refinement pipeline for the current LCDFFC project.

## What Was Reviewed

### Project reality

- Working base system:
  GRU forecaster + QP controller + CityLearn evaluation
- Current repo scope:
  future plans for uncertainty, decision-focused learning, and LLM routing
- Current validated result:
  learned `forecast + QP` beats RBC in the local validated setting

### Narrative documents

- `AGENTS.md`
- `README.md`
- `INSTRUCTION.md`
- `CLAUDE.md`
- `chat.md`
- relevant docs under `docs/`

### Related-work reference points

This review also checked the broad neighborhood of:

- CityLearn / building energy control benchmark work
- decision-focused learning for control-relevant prediction
- LLM-assisted control / optimization / high-level routing
- recent building-energy LLM papers

Representative references used for the novelty check:

- CityLearn environment overview: https://pypi.org/project/citylearn/
- CityLearn challenge winning optimization-style policy: https://jinming.tech/papers/2023-aaai-citylearn-winning-solution.html
- Hierarchical RL-MPC on CityLearn-like cluster control: https://doi.org/10.1016/j.enbuild.2025.116879
- LLM-based interpretable building control: https://dblp.org/rec/journals/corr/abs-2402-09584
- Decision-focused energy management with robust optimization: https://doi.org/10.1016/j.apenergy.2025.127343
- Decision-focused optimal PV-battery scheduling: https://doi.org/10.1016/j.est.2026.121152

## Round-by-Round Summary

### Round 0: Broad-Idea Assessment

The project currently combines several interesting directions:

- forecast + QP
- uncertainty-aware control
- decision-focused training
- LLM preference routing
- optional second benchmark transfer

Assessment:

- good roadmap
- weak single-paper thesis

### Round 1: Critical Review

Main criticisms:

1. no dominant contribution yet
2. current implemented novelty is not enough by itself
3. the LLM role is plausible but under-specified
4. the evaluation story does not isolate the paper claim

Verdict:

`REVISE`

### Round 1: Refinement

The paper was narrowed to:

> language-conditioned dynamic objective routing for forecast-then-control under preference shifts

This preserves the original problem while avoiding contribution sprawl.

## Final Consensus

### Is the current engineering mature?

Yes, for a first serious research substrate.

The repo is no longer just a skeleton. It has:

- a functioning data extraction path
- a functioning forecast model
- a functioning optimization controller
- end-to-end evaluation
- a validated result that beats RBC in the current local setting

### Is the current paper idea mature?

Not yet, if you keep the whole roadmap in one paper.

The broad idea is still too wide and reads as multiple papers forced into one.

### Is it feasible?

Yes.

The refined version is especially feasible because it builds directly on the existing validated low-level stack instead of replacing it.

### Is it novel enough?

Two answers are needed here:

1. **Current implemented system alone**:
   no, not enough novelty for a strong CCF-A venue.
2. **Refined proposal**:
   potentially yes, but only if the paper sharply focuses on language-conditioned online objective adaptation and proves that the language layer is not decorative.

## Results-to-Claims Matrix

| Experimental outcome | Allowed claim |
|---|---|
| Language router clearly beats fixed weights and simple routers under preference shifts | Strong paper claim survives |
| Language router ties numeric preference router | Claim must be downgraded to preference-conditioned routing |
| Language router loses to heuristic router | LLM novelty does not survive |
| Fixed low-level loop stays strong, router adds adaptive value | Good final story |
| Router breaks robustness or feasibility | Keep LLM part as future work |

## Prioritized TODO List

1. Freeze the current validated low-level `forecast + QP` loop as the base platform.
2. Define realistic preference-shift evaluation regimes.
3. Implement a minimal heuristic router.
4. Implement a minimal language-conditioned router.
5. Compare against fixed weights and non-language structured baselines.
6. Only after novelty isolation succeeds, decide whether uncertainty or DFL belong in the same paper.

## Rough Compute and Execution View

- Base loop already runs locally and is practical.
- The refined router study should be moderate-cost if the low-level stack stays frozen.
- The highest risk is not compute. It is evaluation design and claim isolation.

## Paper Outline Suggestion

1. Introduction
   - exogenous sequential control
   - fixed-objective controller limitation
   - language-conditioned objective adaptation
2. Problem Setting
   - CityLearn multi-objective battery control
   - preference-shift setting
3. Method
   - fixed low-level forecast + control
   - high-level language-conditioned router
   - structured fallback
4. Experiments
   - main anchor result
   - novelty isolation
   - simplicity / necessity check
   - robustness
5. Discussion
   - when language is necessary
   - when simpler routing is enough

## Final Bottom-Line Judgment

- **Idea maturity today**: medium
- **Engineering maturity today**: medium-high
- **Feasibility**: high
- **Novelty today**: insufficient as implemented, potentially sufficient after focus
- **Best next step**: execute the refined experiment plan, not more architecture expansion
