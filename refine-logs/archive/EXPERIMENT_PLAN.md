# Experiment Plan

**Problem**: 在固定 `forecast -> qp_carbon -> CityLearn` 闭环里，怎样让 forecast training 真正服务下游控制 KPI，而不只是降低平均 forecast error。
**Method Thesis**: After raw slot-wise CSFT is falsified and offline dual extraction fails on train windows, the strongest remaining fixed-controller route is a replay-calibrated controller prior: derive a low-entropy horizon×channel weighting prior only from controller states that are known to solve successfully during actual replay, then use that prior for forecast training.
**Date**: 2026-03-26

## Claim Map
| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|-------|-----------------|-----------------------------|---------------|
| C1: raw slot-wise CSFT should be treated as a frozen negative result, not scaled further | 这为新的 pivot 提供严格因果基础，而不是随意换方法 | R201 PASS, R202 FAIL, and the route is explicitly frozen as falsified in this setting | B1 |
| C2: replay-calibrated controller prior is a more executable and lower-variance controller-aware supervision target than both raw-CSFT and failed offline dual extraction | 这是新的主方法主张，必须说明它既不是 raw-CSFT，也不是 heuristic patch | replay-prior rerun beats raw-CSFT and at least matches the strongest simple heuristic, while the prior is derived from real successful controller solves rather than arbitrary masks | B2, B3 |
| Anti-claim A1: the gain only comes from generic horizon weighting | reviewer 最容易说“这就是前几个 horizon 更重要” | replay prior is measurably different from manual horizon weighting and is built from replay-solved controller states | B3 |
| Anti-claim A2: controller-aware weighting line is exhausted after raw-CSFT failure | 如果 replay-prior 也不行，这条主线就该停 | replay-prior rerun fails to improve over heuristic/uniform under the same budget | B2 |

## Paper Storyline
- Main paper must prove:
  - raw-CSFT 在当前 setting 下已经被正式否掉，不能继续扩
  - offline train-window dual extraction 也不通，说明问题不仅是 smoothing，而是 supervision extraction interface 本身失配
  - 但 fixed controller 的真实成功求解轨迹仍然可以提供一个更可信的 replay-calibrated prior
  - 这个 prior 比 raw-CSFT 更可执行，并且不只是 heuristic horizon mask
- Appendix can support:
  - R201/R202 细节与 decile table
  - offline dual extraction 失败的技术诊断摘要
  - replay prior vs heuristic 的相似度分析细节
  - `ramping`、更多分布图、可选 multi-seed strengthening
- Experiments intentionally cut:
  - raw-CSFT stabilized rerun
  - offline train-window controller-dual prior rerun
  - 多 backbone 扩展
  - RL / routing / foundation-model 对照
  - 大规模 heuristic family sweep

## Experiment Blocks

### Block 1: Frozen Falsification and Interface Failure Summary
- **Claim tested**: C1
- **Why this block exists**: 这块负责把新的 pivot 固定成“被结果逼出来的下一步”，而不是方法跳跃。
- **Dataset / split / task**:
  - 现有 `forecast_data.npz` + 现有 preflight / diagnostic artifacts
  - task: package raw-CSFT falsification and offline dual-extraction failure
- **Compared systems**:
  1. oracle alignment result (R201)
  2. raw-CSFT utility result (R202)
  3. offline dual-prior extraction failure (P202 current diagnosis)
- **Metrics**:
  - decisive: oracle `max_abs_error`
  - decisive: top-decile MAE ratio for raw-CSFT
  - decisive: solved-with-diagnostics rate on sampled train windows
- **Setup details**:
  - no retraining
  - just package existing artifacts into a concise summary table
- **Success criterion**:
  - the falsification story is unambiguous: oracle is valid, raw-CSFT utility fails, offline dual extraction is not executable on train windows
- **Failure interpretation**:
  - if this story is not cleanly reported, replay-prior pivot will still look arbitrary
- **Table / figure target**:
  - Main Figure 1: falsification / interface-failure summary
  - Appendix Table A1: detailed preflight + interface stats
- **Priority**: MUST-RUN (mostly packaging)

### Block 2: Main Anchor Result — Replay-Calibrated Prior Rerun
- **Claim tested**: C2
- **Why this block exists**: 这是新主方法唯一值得跑的主表。如果它不给信号，这条 controller-aware weighting 主线就该进一步降级。
- **Dataset / split / task**:
  - 数据：当前 CityLearn 2023 主路径
  - split：same chronological train/val/test as existing GRU runs
  - task：固定 `qp_carbon` 下的 replay-calibrated prior 单次 rerun
- **Compared systems**:
  1. uniform GRU baseline
  2. raw-CSFT GRU pilot
  3. replay-calibrated-prior GRU (new)
- **Metrics**:
  - decisive: high-prior-cell MAE
  - decisive: overall MAE
  - decisive: `cost`, `carbon`, `peak`
  - secondary: `ramping`
- **Setup details**:
  - backbone: existing GRU
  - controller: fixed `qp_carbon`
  - GPU: GPU 2 only
  - prior extraction:
    - run the controller on trajectories / contexts where it already solves successfully in replay
    - aggregate controller-relevance statistics over those successful states only
    - compress to one horizon×channel prior `G(h,c)`
    - normalize `G` to mean 1 over `(h,c)`
  - loss:
    - fixed mixed Huber loss
    - fixed `alpha`
    - no per-sample weighting
  - seeds: 1
- **Success criterion**:
  - replay-prior beats raw-CSFT on high-prior-cell MAE
  - overall MAE stays close to uniform
  - at least one of `cost` / `carbon` improves without unacceptable `peak` degradation
- **Failure interpretation**:
  - if this single rerun is weak, stop controller-aware weighting as the main route rather than scaling it further
- **Table / figure target**:
  - Main Table 1: uniform vs raw-CSFT vs replay-prior
- **Priority**: MUST-RUN

### Block 3: Novelty / Simplicity Check — Replay Prior vs Strongest Simple Heuristic
- **Claim tested**: C2 + Anti-claim A1
- **Why this block exists**: reviewer 会直接问 replay prior 是不是只是一个更好看的 horizon heuristic。
- **Dataset / split / task**:
  - same as Block 2
  - only after replay-prior rerun is available
- **Compared systems**:
  1. strongest simple heuristic baseline（只保留一个，优先 `manual_horizon`，除非 `event-window` 更成熟）
  2. replay-prior GRU
- **Metrics**:
  - decisive: high-prior-cell MAE
  - decisive: overall MAE
  - decisive: `cost`, `carbon`, `peak`
  - characterization: replay prior vs heuristic similarity（correlation / overlap / relative entropy）
- **Setup details**:
  - same backbone, same controller, same budget
  - no extra method family
  - seeds: 1 initially
- **Success criterion**:
  - replay prior is better than or clearly different from the strongest heuristic baseline
- **Failure interpretation**:
  - if it is highly similar and not better, the claim weakens to controller-justified heuristic weighting
- **Table / figure target**:
  - Main Figure 2: replay prior vs heuristic comparison
  - Main/Appendix Table 2: heuristic vs replay-prior results
- **Priority**: MUST-RUN

### Block 4: Failure Analysis / Mechanism Figure
- **Claim tested**: supports C1/C2
- **Why this block exists**: 这块负责解释为什么 raw-CSFT 和 offline dual prior 都失败，而 replay-prior 仍然值得试。
- **Dataset / split / task**:
  - test split + replay prior artifacts + existing predictions
- **Compared systems**:
  1. uniform
  2. raw-CSFT
  3. replay-prior
- **Metrics**:
  - decile-wise MAE curves
  - high-prior-cell vs low-prior-cell MAE
  - replay-prior heatmap over horizon×channel
  - solved-state coverage statistics used to build the prior
- **Setup details**:
  - no additional training beyond Block 2
- **Success criterion**:
  - figure clearly shows that replay prior is lower-variance and built from valid controller states
- **Failure interpretation**:
  - if the figure is weak, method may still read as a patch rather than a mechanism
- **Table / figure target**:
  - Figure 3: error concentration curves
  - Figure 4: replay-prior heatmap + solved-state coverage
- **Priority**: MUST-RUN

### Block 5: Conditional Strengthening — Multi-seed or Controller-Specificity Check
- **Claim tested**: optional strengthening of C2
- **Why this block exists**: 只有 replay-prior 单次结果明显为正时，才值得加 stronger defense。
- **Dataset / split / task**:
  - same as Block 2
  - conditional on Block 2 positive signal
- **Compared systems**:
  1. replay-prior (3 seeds) or
  2. alternative controller-derived replay prior (if easy)
- **Metrics**:
  - same primary KPI set
- **Setup details**:
  - run only one strengthening family, not both
- **Success criterion**:
  - positive direction remains stable or becomes more clearly controller-specific
- **Failure interpretation**:
  - if strengthening fails, keep the claim narrow
- **Table / figure target**:
  - Appendix first, promote only if very clean
- **Priority**: NICE-TO-HAVE

## Run Order and Milestones
| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|-----------|------|------|---------------|------|------|
| M0 | Freeze falsification summary | Q201 package R201/R202 + offline-dual failure stats | If the falsification story is not cleanly frozen, pivot lacks justification | Very low | Method hop still looks arbitrary |
| M1 | Build replay-calibrated prior | Q202 extract replay prior + sanity plots | Continue only if prior has non-zero mass and is not trivially identical to manual horizon weighting | Low | Prior may still collapse to heuristic |
| M2 | Run main replay-prior method | Q203 replay-prior GRU rerun | Continue only if raw-CSFT is beaten and early KPI signal appears | Low GPU | New route may still be too weak |
| M3 | Defend novelty against strongest heuristic | Q204 strongest heuristic compare | If heuristic dominates, weaken or stop the claim | Low to medium | Claim collapses to heuristic weighting |
| M4 | Mechanism packaging | Q205 figures/tables package | Required regardless of positive/negative result | Low | Story may still feel patch-like |
| M5 | Optional strengthening | Q206 multi-seed or alternative replay-prior | Only if Q203 is clearly positive | Medium | Extra compute with limited upside |

## Compute and Data Budget
- **Total estimated GPU-hours**:
  - M0–M1: negligible GPU
  - M2: low (one GRU rerun)
  - M3: low to medium (one strongest heuristic family)
  - M4: negligible GPU
  - total must-run budget remains low
- **Data preparation needs**:
  - reuse existing split and checkpoints
  - add one replay-prior extraction script that works from successful replay states
  - save prior matrix and solved-state coverage metadata
- **Human evaluation needs**:
  - none
- **Biggest bottleneck**:
  - not compute; the main bottleneck is whether replay-derived successful controller states provide a prior that is both non-trivial and non-heuristic

## Risks and Mitigations
- **Risk**: replay prior still collapses to a generic front-loaded mask
  - **Mitigation**: explicitly characterize similarity to manual horizon weighting and weaken claim if needed
- **Risk**: replay prior improves error concentration but not control KPIs
  - **Mitigation**: stop controller-aware weighting as a main route
- **Risk**: extracting replay-successful controller states is more cumbersome than expected
  - **Mitigation**: start with one successful baseline replay trajectory before broadening extraction scope
- **Risk**: reviewer sees another pivot as arbitrary
  - **Mitigation**: keep Block 1 as frozen evidence showing both raw-CSFT and offline dual-extraction failed for concrete reasons
- **Risk**: too many variants dilute the story
  - **Mitigation**: keep one prior method, one heuristic baseline, one conditional strengthening block

## Final Checklist
- [ ] Main paper tables are covered
- [ ] Novelty is isolated
- [ ] Simplicity is defended
- [ ] Frontier contribution is explicitly not claimed
- [ ] Nice-to-have runs are separated from must-run runs
