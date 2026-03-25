# Experiment Plan

**Problem**: 在固定 `forecast -> qp_carbon -> CityLearn` 闭环里，怎样让 forecast training 真正服务下游控制 KPI，而不只是降低平均 forecast error。
**Method Thesis**: Raw finite-difference controller sensitivities should only be used for forecast training after passing a numerical preflight validity gate and a fixed stabilization operator.
**Date**: 2026-03-26

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|-------|-----------------|-----------------------------|---------------|
| C1: raw controller-sensitive labels are only usable if they pass a numerical preflight gate | 如果这个 gate 不成立，后面所有 stabilized-CSFT 都没有意义 | oracle alignment 通过；raw-CSFT 在 top-decile MAE 上不比 uniform 差超过 5% | B1 |
| C2: fixed stabilization operator can recover controller-critical fitting and early KPI signal without unacceptable aggregate degradation | 这是当前 paper 的主方法主张 | stabilized-CSFT 满足 acceptance rule：top-decile MAE 更低、overall MAE 不劣化超过 1%、`cost` 或 `carbon` 至少一个改善、`peak` 不劣化超过 1% | B2, B3 |
| Anti-claim A1: gain only comes from arbitrary weight tuning or post-hoc metric cherry-picking | reviewer 最容易质疑这只是 recipe tuning | operator 全固定；只跑一个 rerun；用预注册 acceptance rule 判定 | B1, B2 |
| Anti-claim A2: even softened weighting is no better than simpler control-aware heuristics | 如果 heuristic 就够了，方法贡献要降级 | stabilized-CSFT 至少不弱于 strongest simple heuristic baseline，或明确把 heuristic comparison 留到 gate 通过后再做 | B3 |

## Paper Storyline
- Main paper must prove:
  - 当前 raw-CSFT 不是一个可直接扩展的方法，必须先经过 numerical preflight
  - 通过 preflight 后，固定 stabilization operator 能把 raw sensitivities 变成可训练监督
  - 这个监督至少能先在 controller-critical cells 上恢复正向信号，并带来早期 control KPI 改善
- Appendix can support:
  - operator 的 mechanistic justification
  - label storage / horizon indexing / channel ordering 细节
  - `ramping`、distribution stats、更多可视化
  - controller-specificity 或 heuristic expansion（仅当主线通过 gate 后）
- Experiments intentionally cut:
  - 多 backbone 扩展
  - 多 seed 扩展（在 single-run gate 没过前不做）
  - RL / routing / foundation-model 对照
  - bucketed fallback 主方法
  - 大规模 heuristic matrix

## Experiment Blocks

### Block 1: Numerical Preflight Gate
- **Claim tested**: C1
- **Why this block exists**: 这是整条路线的 stop/go gate。没有它，stabilized-CSFT 只是继续在可疑 supervision 上加工程修补。
- **Dataset / split / task**:
  - 数据：当前 `artifacts/forecast_data.npz` 对应的 chronological split
  - split：existing test split + matched oracle slices
  - task：验证 oracle 路径与 raw label utility
- **Compared systems**:
  1. oracle slices vs environment-derived future truth
  2. existing uniform checkpoint (`R103/R112` line)
  3. existing raw-CSFT checkpoint (`R105/R113` line)
- **Metrics**:
  - decisive: oracle `max_abs_error` on first 20 matched steps for `price/load/solar`
  - decisive: top-decile MAE ratio = `MAE_raw_csft / MAE_uniform`
  - secondary: full decile-wise MAE table
- **Setup details**:
  - no retraining
  - use current test labels `artifacts/csft_labels_qp_carbon_test.npz`
  - top decile defined by test-label sensitivity ranking over all `(sample, horizon, channel)` cells
  - PASS iff:
    - `max_abs_error <= 1e-6` for each channel
    - raw-CSFT top-decile MAE is not worse than uniform by more than 5%
- **Success criterion**:
  - preflight PASS
- **Failure interpretation**:
  - oracle FAIL => first fix oracle/eval path, do not run stabilized-CSFT
  - utility FAIL => raw slot-wise CSFT is not a viable route in current form; do not scale this paper line
- **Table / figure target**:
  - Main Table 1 (left panel) or Figure 1: preflight PASS/FAIL summary
  - Appendix Table A1: decile-wise MAE table
- **Priority**: MUST-RUN

### Block 2: Main Anchor Result — One Stabilized-CSFT Rerun
- **Claim tested**: C2
- **Why this block exists**: 这是主方法的第一性证据。只要这一步不能给出正信号，就不值得继续做更大规模实验。
- **Dataset / split / task**:
  - 数据：当前 CityLearn 2023 主数据路径
  - split：same chronological train/val/test as current GRU runs
  - task：固定 `qp_carbon` 下的 stabilized-CSFT 单次 rerun
- **Compared systems**:
  1. uniform GRU baseline
  2. raw-CSFT GRU pilot
  3. stabilized-CSFT GRU (new)
- **Metrics**:
  - decisive: top-decile MAE
  - decisive: overall MAE
  - decisive: `cost`, `carbon`, `peak`
  - secondary: `ramping`
- **Setup details**:
  - backbone: existing GRU
  - controller: fixed `qp_carbon`
  - GPU: GPU 2 only
  - stabilization operator fixed to:
    - `q95_train` clipping over positive raw train sensitivities
    - `m_train` = median over positive clipped raw train sensitivities
    - `eps = 1e-8`
    - `u = log1p(s_clip / (m_train + eps))`
    - per-sample normalization
  - loss:
    - Huber delta = `1.0`
    - `alpha = 0.85`
  - seeds: 1 (this stage intentionally single-run)
- **Success criterion**:
  - all four acceptance-rule conditions hold:
    1. top-decile MAE < uniform
    2. overall MAE no worse than uniform by >1%
    3. at least one of `cost` or `carbon` improves
    4. `peak` no worse than uniform by >1%
- **Failure interpretation**:
  - if acceptance rule fails, do not scale to 3 seeds or more baselines; this route remains REVISE or should be stopped
- **Table / figure target**:
  - Main Table 1 (right panel): uniform vs raw-CSFT vs stabilized-CSFT
- **Priority**: MUST-RUN

### Block 3: Novelty / Simplicity Check — Strongest Simple Heuristic vs Stabilized-CSFT
- **Claim tested**: C2 + Anti-claim A2
- **Why this block exists**: 如果 stabilized-CSFT 过 gate，reviewer 下一句就是“是不是简单 heuristic weighting 就够了？”
- **Dataset / split / task**:
  - 与 Block 2 相同
  - 仅在 Block 2 成功后运行
- **Compared systems**:
  1. uniform
  2. strongest simple heuristic baseline（优先 `event-window weighting`；若已有实现更成熟则用 `manual horizon weighting`）
  3. stabilized-CSFT
- **Metrics**:
  - decisive: top-decile MAE, overall MAE
  - decisive: `cost`, `carbon`, `peak`
- **Setup details**:
  - heuristic baseline 只保留一个最强简单家族，避免 baseline list 过长
  - same backbone, same budget, same controller
  - seeds: 1 initially; 3 only if stabilized-CSFT already clearly positive
- **Success criterion**:
  - stabilized-CSFT 至少不弱于 strongest simple heuristic on primary KPIs and top-decile MAE
- **Failure interpretation**:
  - if heuristic ties or wins, paper claim must weaken to “simple control-aware weighting may suffice”
- **Table / figure target**:
  - Main Table 2 or appendix if effect is weak
- **Priority**: MUST-RUN only if Block 2 passes, otherwise CUT

### Block 4: Failure Analysis / Mechanism Figure
- **Claim tested**: supports C1/C2
- **Why this block exists**: 即使结果是负的，也需要一张机制图把结论讲清楚。
- **Dataset / split / task**:
  - test split
  - preflight outputs + all available model predictions
- **Compared systems**:
  1. uniform
  2. raw-CSFT
  3. stabilized-CSFT (if available)
- **Metrics**:
  - full decile-wise MAE curve
  - sensitivity distribution before/after operator
  - acceptance-rule dashboard
- **Setup details**:
  - no extra training
  - can be generated after Block 1 and Block 2
- **Success criterion**:
  - mechanism figure clearly shows whether stabilization changed the supervision distribution and whether gains concentrated on critical cells
- **Failure interpretation**:
  - if the figure remains flat or inconsistent, the story is not yet mechanism-level
- **Table / figure target**:
  - Figure 2: decile-wise MAE curve
  - Figure 3: raw vs stabilized sensitivity distribution / operator effect
- **Priority**: MUST-RUN

### Block 5: Controller-Specificity Check (Conditional)
- **Claim tested**: optional strengthening of C2
- **Why this block exists**: 只有主线已经有正信号时，才值得证明 signal 真是 controller-specific，而不是 generic importance map。
- **Dataset / split / task**:
  - same as Block 2
  - only if Block 2 passes convincingly
- **Compared systems**:
  1. stabilized-CSFT with `qp_carbon` labels
  2. stabilized-CSFT with mismatched labels (e.g. `qp_current`)
- **Metrics**:
  - top-decile MAE
  - `cost`, `carbon`, `peak`
- **Setup details**:
  - same operator, same backbone, same budget; only label source changes
  - seeds: 1 initially
- **Success criterion**:
  - matched labels outperform mismatched labels on primary KPI story
- **Failure interpretation**:
  - if no gap appears, claim should weaken from controller-sensitive to generic control-aware weighting
- **Table / figure target**:
  - Appendix first, promote to main only if very clean
- **Priority**: NICE-TO-HAVE

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|-----------|------|------|---------------|------|------|
| M0 | Verify numerical preflight gate | R201 oracle alignment, R202 raw-label utility | If either fails, stop this route and do not launch stabilized rerun | Very low | Oracle path or label ranking may already kill the method |
| M1 | Run main stabilized rerun | R203 stabilized-CSFT train+eval | Continue only if acceptance rule passes | Low | Method may still be too weak even after stabilization |
| M2 | Defend against strongest simple alternative | R204 strongest heuristic baseline (conditional) | Only run if R203 passes | Low to medium | Heuristic may explain away the gain |
| M3 | Produce mechanism figures and paper tables | R205 plots/tables package | Required for paper interpretation regardless of positive/negative outcome | Low | Story may remain unclear if effects are noisy |
| M4 | Optional strengthening | R206 controller-specificity check | Only if R203 is clearly positive | Medium | Extra compute without affecting main conclusion |

## Compute and Data Budget
- **Total estimated GPU-hours**:
  - M0: negligible GPU, mostly analysis
  - M1: low (one GRU rerun)
  - M2: low to medium, conditional
  - M3: negligible GPU
  - Total must-run before scale-up: low budget
- **Data preparation needs**:
  - reuse current chronological split
  - reuse existing checkpoint and label artifacts
  - ensure oracle slice extraction and env-future extraction are deterministic and matched by episode/time index
- **Human evaluation needs**:
  - none
- **Biggest bottleneck**:
  - not compute; the main bottleneck is whether preflight passes and whether stabilized weighting yields any real signal

## Risks and Mitigations
- **Risk**: oracle alignment bug invalidates both oracle comparison and label interpretation
  - **Mitigation**: make oracle alignment the very first run and block all later runs on it
- **Risk**: raw label utility test fails immediately
  - **Mitigation**: treat that as a useful falsification result and pivot early instead of scaling CSFT
- **Risk**: stabilized operator improves critical cells but not control KPIs
  - **Mitigation**: use the pre-registered acceptance rule; if it fails, stop and do not expand seeds/backbones
- **Risk**: reviewer says the gain is just heuristic weighting
  - **Mitigation**: run only the strongest simple heuristic baseline after the main rerun passes
- **Risk**: pseudo-novelty criticism remains
  - **Mitigation**: in paper text, explicitly justify why clipping + `log1p` + per-sample normalization is a scale-control mechanism rather than arbitrary recipe tuning

## Final Checklist
- [ ] Main paper tables are covered
- [ ] Novelty is isolated
- [ ] Simplicity is defended
- [ ] Frontier contribution is explicitly not claimed
- [ ] Nice-to-have runs are separated from must-run runs
