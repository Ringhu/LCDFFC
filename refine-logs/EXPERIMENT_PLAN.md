# Experiment Plan

**Problem**: 在固定 `forecast -> qp_carbon -> CityLearn` 闭环里，怎样让 forecast training 真正服务下游控制 KPI，而不只是降低平均 forecast error。
**Method Thesis**: After raw slot-wise CSFT fails its own utility gate, the smallest remaining controller-aware route is a controller-dual prior: a fixed horizon×channel relevance map derived from the QP structure and used as a low-entropy forecast weighting prior.
**Date**: 2026-03-26

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|-------|-----------------|-----------------------------|---------------|
| C1: raw slot-wise CSFT is formally falsified in the current setting | 这决定我们能不能继续合理地扩原始 CSFT 主线 | R201 PASS + R202 FAIL；oracle 对齐正确，但 raw-CSFT 在 top-decile MAE 上仍比 uniform 更差 | B1 |
| C2: a controller-dual prior is a stronger and more defensible supervision target than raw-CSFT | 这是新的主方法主张 | controller-dual prior rerun 优于 raw-CSFT，并且至少不弱于最强简单 heuristic；同时其 prior 形状不能退化成 generic horizon mask | B2, B3 |
| Anti-claim A1: gain only comes from a generic front-loaded heuristic | reviewer 最容易说“这不就是近端 horizon weighting” | controller-dual prior 在表征上与 manual horizon mask 显著不同，且结果上优于或明显不同于 strongest simple heuristic | B2, B3 |
| Anti-claim A2: controller-aware weighting line is exhausted after raw-CSFT failure | 如果 pivot 后仍然不行，这整条 paper route 就该降级 | dual-prior rerun 若仍无信号，则尽早停止 controller-aware weighting 主线 | B2 |

## Paper Storyline
- Main paper must prove:
  - raw slot-wise CSFT 在当前 setting 下已经被正式否掉，不能再当主路线继续扩
  - fixed-QP controller 仍然能提供一个更低方差、更 controller-specific 的 prior
  - 这个 controller-dual prior 比 raw-CSFT 更好，并且不退化成简单 heuristic
- Appendix can support:
  - preflight 细节与 decile table
  - prior 与 heuristic 的相似度分析细节
  - `ramping`、更多分布图、更多 controller-specificity 结果
  - optional multi-seed strengthening（仅当单次 rerun 为正）
- Experiments intentionally cut:
  - raw-CSFT stabilized rerun
  - 多 backbone 扩展
  - RL / routing / foundation-model 对照
  - 大规模 heuristic 家族矩阵
  - bucketed / top-K prior 家族搜索

## Experiment Blocks

### Block 1: Frozen Falsification Evidence — Raw-CSFT Should Not Be Scaled
- **Claim tested**: C1
- **Why this block exists**: 这块是新 pivot 的起点。没有它，paper 会显得像随意换方向，而不是从严格负结果中收敛。
- **Dataset / split / task**:
  - 数据：当前 `artifacts/forecast_data.npz`
  - split：existing chronological split / test artifacts
  - task：固定并引用已经完成的 R201 / R202
- **Compared systems**:
  1. oracle slices vs env future
  2. uniform GRU vs raw-CSFT GRU
- **Metrics**:
  - decisive: oracle `max_abs_error`
  - decisive: top-decile MAE ratio
  - secondary: decile-wise MAE table
- **Setup details**:
  - no retraining
  - directly reuse `reports/csft_pilot/r201_oracle_alignment.json`
  - directly reuse `reports/csft_pilot/r202_raw_label_utility.json`
- **Success criterion**:
  - formal conclusion is clear: oracle path is valid, raw-CSFT utility gate fails
- **Failure interpretation**:
  - if this evidence is not accepted as frozen ground truth, then the paper lacks a rigorous reason to pivot
- **Table / figure target**:
  - Main Figure 1: preflight summary
  - Appendix Table A1: decile-wise MAE table
- **Priority**: MUST-RUN (already done; now paper-facing packaging)

### Block 2: Main Anchor Result — Controller-Dual Prior Rerun
- **Claim tested**: C2
- **Why this block exists**: 这是新方法的唯一主表。如果它不给正信号，controller-aware weighting 这条主线就该停止。
- **Dataset / split / task**:
  - 数据：当前 CityLearn 2023 主数据路径
  - split：same chronological train/val/test as existing GRU runs
  - task：固定 `qp_carbon` 下的 controller-dual prior 单次 rerun
- **Compared systems**:
  1. uniform GRU baseline
  2. raw-CSFT GRU pilot
  3. controller-dual prior GRU (new)
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
    - derive horizon×channel relevance from QP analytic objective coefficients and, where available, active-constraint dual information
    - apply channel-wise normalization using either train target std or uniform-baseline per-channel MAE
    - normalize prior to mean 1 over `(h,c)`
  - training loss:
    - fixed mixed Huber loss
    - fixed `alpha`
    - no per-sample weight variation
  - seeds: 1
- **Success criterion**:
  - controller-dual prior beats raw-CSFT on high-prior-cell MAE
  - overall MAE is at least close to uniform
  - at least one of `cost` / `carbon` improves vs uniform without unacceptable `peak` degradation
- **Failure interpretation**:
  - if this single rerun is weak, stop controller-aware weighting as the main paper route rather than scaling it
- **Table / figure target**:
  - Main Table 1: uniform vs raw-CSFT vs controller-dual prior
- **Priority**: MUST-RUN

### Block 3: Novelty / Simplicity Check — Dual Prior vs Strongest Simple Heuristic
- **Claim tested**: C2 + Anti-claim A1
- **Why this block exists**: reviewer 会直接问“你这个是不是只是一个更花哨的 front-loaded horizon weighting”。
- **Dataset / split / task**:
  - same as Block 2
  - only after the controller-dual prior rerun is available
- **Compared systems**:
  1. strongest simple heuristic baseline（只保留一个，优先 `manual_horizon` 或更成熟的 `event-window`）
  2. controller-dual prior GRU
- **Metrics**:
  - decisive: high-prior-cell MAE
  - decisive: overall MAE
  - decisive: `cost`, `carbon`, `peak`
  - characterization: similarity between controller-dual prior and heuristic mask（correlation / relative entropy / overlap）
- **Setup details**:
  - same backbone, same controller, same train budget
  - no extra model family
  - seeds: 1 initially
- **Success criterion**:
  - controller-dual prior is either better than the strongest heuristic baseline, or clearly different in shape while giving competitive KPI gains
- **Failure interpretation**:
  - if the prior is highly correlated with the heuristic and not better in results, then claim weakens to controller-justified heuristic weighting
- **Table / figure target**:
  - Main Figure 2: prior vs heuristic characterization
  - Main / Appendix Table 2: heuristic vs dual-prior comparison
- **Priority**: MUST-RUN

### Block 4: Failure Analysis / Mechanism Figure
- **Claim tested**: supports C1/C2
- **Why this block exists**: 这块负责把“为什么 raw-CSFT 死了，而 dual prior 可能还活着”讲清楚。
- **Dataset / split / task**:
  - test split
  - preflight artifacts + all model predictions + extracted prior
- **Compared systems**:
  1. uniform
  2. raw-CSFT
  3. controller-dual prior
- **Metrics**:
  - decile-wise MAE curves
  - high-prior-cell vs low-prior-cell MAE
  - prior heatmap over horizon×channel
- **Setup details**:
  - no additional training beyond Block 2
- **Success criterion**:
  - mechanism figure clearly shows that raw-CSFT is noisy/ineffective while the dual prior is lower-variance and more interpretable
- **Failure interpretation**:
  - if this figure is not convincing, the method may still read as a local patch
- **Table / figure target**:
  - Figure 3: decile/high-prior-cell MAE comparison
  - Figure 4: controller-dual prior heatmap
- **Priority**: MUST-RUN

### Block 5: Conditional Strengthening — Multi-seed or Controller-Specificity Check
- **Claim tested**: optional strengthening of C2
- **Why this block exists**: 只有当 controller-dual prior 单次 rerun 是正的，才值得加更强 defense。
- **Dataset / split / task**:
  - same as Block 2
  - conditional on Block 2 positive signal
- **Compared systems**:
  1. controller-dual prior (3 seeds) or
  2. matched vs altered controller-derived prior
- **Metrics**:
  - same primary KPI set
- **Setup details**:
  - run only one strengthening family, not both, unless the main result is very strong
- **Success criterion**:
  - positive direction remains stable or becomes more clearly controller-specific
- **Failure interpretation**:
  - if strengthening fails, keep the claim narrow and avoid overselling
- **Table / figure target**:
  - Appendix first, main only if very clean
- **Priority**: NICE-TO-HAVE

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|-----------|------|------|---------------|------|------|
| M0 | Freeze falsification evidence | P201 package R201/R202 into paper-facing summary | If the frozen evidence is not cleanly reported, pivot lacks foundation | Very low | Users/reviewers may still think pivot is arbitrary |
| M1 | Extract controller-dual prior | P202 prior extraction + sanity plots | Continue only if prior is not trivially identical to a simple horizon mask | Low CPU | Prior may collapse into heuristic shape |
| M2 | Run main pivot method | P203 controller-dual prior GRU rerun | Continue only if raw-CSFT is beaten and early KPI signal appears | Low GPU | New route may still be too weak |
| M3 | Defend novelty against heuristic | P204 strongest heuristic rerun/compare | If heuristic dominates, weaken or stop the claim | Low to medium | Claim collapses to heuristic weighting |
| M4 | Mechanism packaging | P205 figures/tables package | Required for paper interpretation regardless of positive/negative result | Low | Story may remain patch-like |
| M5 | Optional strengthening | P206 multi-seed or controller-specificity | Only if P203 is clearly positive | Medium | Additional compute with limited upside |

## Compute and Data Budget
- **Total estimated GPU-hours**:
  - M0–M1: negligible GPU
  - M2: low (one GRU rerun)
  - M3: low to medium (one strongest heuristic family only)
  - M4: negligible GPU
  - total must-run budget remains low
- **Data preparation needs**:
  - reuse existing split and checkpoints
  - add one prior-extraction script from `qp_controller.py`
  - save prior matrix and its metadata for reproducibility
- **Human evaluation needs**:
  - none
- **Biggest bottleneck**:
  - not compute; the main bottleneck is whether the controller-dual prior is genuinely controller-specific rather than just another horizon heuristic

## Risks and Mitigations
- **Risk**: controller-dual prior ends up highly correlated with manual horizon weighting
  - **Mitigation**: explicitly characterize prior-vs-heuristic similarity and weaken the claim if necessary
- **Risk**: dual prior beats raw-CSFT but still does not improve control KPIs
  - **Mitigation**: stop controller-aware weighting as a main route; keep it as a negative-result analysis if useful
- **Risk**: analytic dual/gradient extraction is harder than expected from current controller code
  - **Mitigation**: use the simplest controller-consistent analytic surrogate available from the QP objective first, before full dual instrumentation
- **Risk**: reviewer sees the pivot as arbitrary method hopping
  - **Mitigation**: make Block 1 a frozen falsification story so the pivot is causally justified by evidence
- **Risk**: too many comparison branches dilute the story
  - **Mitigation**: keep only one heuristic family and one conditional strengthening block

## Final Checklist
- [ ] Main paper tables are covered
- [ ] Novelty is isolated
- [ ] Simplicity is defended
- [ ] Frontier contribution is explicitly not claimed
- [ ] Nice-to-have runs are separated from must-run runs
