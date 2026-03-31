# Refinement Report

## Score Evolution

| Round | Overall | Verdict | Key Change |
|-------|---------|---------|------------|
| 0 (GPT-5.4 review) | 4/10 | REVISE | Initial multi-line state; three bundled contributions |

## Method Evolution

### Generation 1: CSFT (archived)
- Context-sensitive fine-tuning: weight forecast loss by controller sensitivity
- Raw-CSFT falsified (R202 ratio > 1.05 threshold)
- Controller-dual prior: offline QP infeasible
- Replay-prior: improved forecast MAE but worsened control KPIs
- Conclusion: sensitivity is useful for evaluation, not for direct training weighting

### Generation 2: CAVS (current)
- Pivot triggered by GPT-5.4 review (2026-03-27)
- Core insight: use controller sensitivity for model *selection* instead of model *training*
- CAVS = sensitivity-weighted forecast error as model selection criterion
- Smallest adequate intervention: no new architecture, no retraining, just a scoring function

## Remaining Weaknesses

1. CAVS advantage is hypothesized but not yet empirically validated
2. Sensitivity map computation cost not yet benchmarked
3. Single controller family (QP) — unclear if results transfer to other controller types
4. CityLearn-specific — generalization to other domains not addressed
5. CAVS-local (per-window sensitivity) may be too expensive for practical use

## What Changed in This Pivot

- Dropped CSFT as main contribution → archived
- Dropped LLM routing as main contribution → archived
- Elevated forecast-control misalignment from observation to thesis
- Added CAVS as constructive method
- Expanded experimental scope from 1 scenario to 5+3 scenarios
- Added multi-seed requirement (3 seeds)
- Added explicit baseline separation (zero-action, myopic-QP, oracle variants, with any real rule-based controller treated separately)
