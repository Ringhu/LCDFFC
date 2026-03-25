# Experiment Plan

**Problem**: 在外生时间序列驱动控制里，更好的 forecasting 不该只降低平均误差，还要稳定转化成更好的下游控制 KPI。
**Method Thesis**: Uniform forecast loss 学错了目标；用 frozen controller 的局部敏感度重加权 forecast training，能让模型优先修正 controller-critical future errors。
**Date**: 2026-03-25

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|-------|-----------------|-----------------------------|---------------|
| C1: CSFT 比 uniform forecast training 更稳定地改善固定 `qp_carbon` 的下游 `cost / carbon / peak` | 这是主论文的机制主张 | 在 standard test 和 stress subsets 上，CSFT 持续优于 uniform loss，并且不输给 heuristic weighting | B1, B3 |
| C2: 增益来自 controller-critical future cells 上的误差下降，而不是 generic reweighting 或训练波动 | 不做这个，reviewer 会说只是巧合或手工 weighting | 高敏感度 decile 的 forecast error 明显下降；matched-controller labels 明显优于 mismatched labels | B2, B3 |
| Anti-claim A1: 增益只来自简单 heuristic weighting | 这是最直接的反驳点 | `event-window` / `manual horizon weighting` 都输给 CSFT | B3 |
| Anti-claim A2: 增益只来自换 controller 或换 backbone | 当前仓库已有大量这类历史结果，主论文要避免被带偏 | 主论文固定 `qp_carbon` 和单一 backbone，只改训练目标 | B1 |

## Paper Storyline
- Main paper must prove:
  - fixed `forecast -> qp_carbon -> CityLearn` 下，uniform loss 不适合这个 control objective
  - CSFT 能在不改 controller 的前提下，稳定改善下游 KPI
  - 这种改善来自 controller-sensitive cells 上的误差再分配
- Appendix can support:
  - sensitivity heatmap 细节
  - label generation compute 开销统计
  - 一个可选 backbone replication
  - routing motivation 一页图
- Experiments intentionally cut:
  - language-conditioned routing 主表
  - fallback robustness 主表
  - Grid2Op transfer
  - full differentiable decision-focused baseline
  - backbone zoo

## Experiment Blocks

### Block 1: Main Anchor Result — CSFT 是否改善固定 forecast-then-control
- **Claim tested**: C1
- **Why this block exists**: 这是整篇论文的主表。没有这块，整篇论文没有立足点。
- **Dataset / split / task**:
  - 数据：当前 `CityLearn 2023` 主数据路径，对应 `artifacts/forecast_data.npz`
  - 划分：chronological split，train 70% / val 10% / test 20%
  - 任务：固定 `qp_carbon` controller，下游闭环评估
- **Compared systems**:
  1. uniform-loss GRU forecaster
  2. CSFT-GRU
  3. oracle forecast + `qp_carbon` 上界
  4. optional naive / persistence forecast + `qp_carbon`，仅当实现代价很低
- **Metrics**:
  - 主指标：total cost、total carbon、peak load
  - 辅指标：ramping、oracle gap closure
  - forecast side：overall MAE / RMSE
- **Setup details**:
  - 主 backbone：`GRU`
  - 主 controller：`qp_carbon`
  - 预测通道：当前 repo 中 controller 消费的 forecast columns，中心是 `[price, load, solar]`
  - `carbon_intensity` 在主实验里保持现有控制路径，不把“学习 carbon forecast”引入第一篇主线
  - seeds：3
  - 训练 / 推理用 `GPU 2`
- **Success criterion**:
  - CSFT 相对 uniform loss 在 3 个 seeds 上对 `cost / carbon` 给出一致改善
  - `peak` 不出现明显退化
  - 相对 oracle gap 有非平凡缩小
- **Failure interpretation**:
  - 如果只提升 forecast 不提升 control，主 thesis 不成立
  - 如果只在单个 seed 或单个指标上变好，论文说法要明显减弱
- **Table / figure target**:
  - Main Table 1：uniform vs CSFT vs oracle
  - Figure 1：oracle gap closure bar chart
- **Priority**: MUST-RUN

### Block 2: Mechanism Validation — 改善是不是集中在高敏感度 future cells
- **Claim tested**: C2
- **Why this block exists**: 这是机制图。没有这块，CSFT 会被看成普通 reweighting trick。
- **Dataset / split / task**:
  - 使用与 Block 1 相同的 test split
  - 每个 forecast cell 用离线 sensitivity labels 分成 deciles
- **Compared systems**:
  1. uniform-loss GRU
  2. CSFT-GRU
- **Metrics**:
  - overall RMSE / MAE
  - top-sensitivity-decile RMSE / MAE
  - decile-wise error reduction
  - action deviation / stage-loss deviation on top-decile perturbation slices（如果额外代价低）
- **Setup details**:
  - sensitivity label：对每个 `(h, c)` 做 finite-difference perturbation
  - label 使用一步 stage objective sensitivity，不用 full rollout regret
  - label 处理：95 分位 clipping + per-sample normalization
- **Success criterion**:
  - overall forecast error 变化不大
  - 高敏感度 decile 上的误差下降明显，大于低敏感度 decile
- **Failure interpretation**:
  - 如果所有 decile 都差不多，说明 CSFT 没有把容量重新分配到 controller-critical cells
- **Table / figure target**:
  - Figure 2：forecast error reduction vs sensitivity decile
  - Figure 3：average horizon × channel sensitivity heatmap
- **Priority**: MUST-RUN

### Block 3: Novelty Isolation — finite-difference sensitivity 是否比 heuristic weighting 更对题
- **Claim tested**: C1 + C2 + Anti-claim A1
- **Why this block exists**: reviewer 一定会问“你这个是不是就是手工强调关键窗口”。
- **Dataset / split / task**:
  - 与 Block 1 相同
  - 同样在 `qp_carbon` 下闭环评估
- **Compared systems**:
  1. uniform loss
  2. manual horizon weighting
  3. event-window weighting
  4. CSFT
- **Metrics**:
  - total cost、total carbon、peak load
  - top-decile forecast MAE / RMSE
- **Setup details**:
  - manual horizon weighting：强调近端控制窗口
  - event-window weighting：按 price spike / carbon spike / peak-load windows 做 coarse weighting
  - 其余训练 budget 完全相同
- **Success criterion**:
  - CSFT 明显优于两个 heuristic weighting baselines
- **Failure interpretation**:
  - 如果 event-only 或 horizon-only 跟 CSFT 打平，主张要降成“controller-aware weighting 有帮助”，不能再强调 finite-difference superiority
- **Table / figure target**:
  - Main Table 2：uniform / heuristic / event / CSFT 对比
- **Priority**: MUST-RUN

### Block 4: Controller-Specificity Check — label 是否真的是 controller-specific
- **Claim tested**: C2
- **Why this block exists**: 这是最强的机制 defense。它能说明 label 不是 generic importance map。
- **Dataset / split / task**:
  - 与 Block 1 相同
- **Compared systems**:
  1. CSFT with `qp_carbon` labels, eval with `qp_carbon`
  2. CSFT with `qp_current` labels, eval with `qp_carbon`
  3. optional reverse direction only if主结果已经很强
- **Metrics**:
  - total cost、total carbon、peak load
  - oracle gap closure
  - top-decile forecast error
- **Setup details**:
  - 唯一变化是 label generator 用哪个 controller
  - backbone、loss、training budget 全保持一致
- **Success criterion**:
  - matched-controller labels 明显优于 mismatched labels
- **Failure interpretation**:
  - 如果二者差不多，论文要改成 generic control-aware weighting，而不是 controller-sensitive weighting
- **Table / figure target**:
  - Main Table 3 或主文末表
- **Priority**: MUST-RUN

### Block 5: Simplicity / Stability Check — mixed loss 和 label 稳定性够不够
- **Claim tested**: 方法没有靠过度设计才跑起来
- **Why this block exists**: reviewer 会担心 CSFT 过拟合 spikes，或者只是纯 weighted loss 的偶然收益。
- **Dataset / split / task**:
  - val split + full test split
- **Compared systems**:
  1. pure weighted loss (`alpha=0`)
  2. mixed loss (`alpha=0.5`)
  3. optional `alpha=0.75`
- **Metrics**:
  - val loss stability
  - main KPIs
  - label distribution stats
- **Setup details**:
  - 对 sensitivity label 统计分布、top-k mass、跨相邻窗口 rank correlation
- **Success criterion**:
  - mixed loss 更稳，且不牺牲主表结果
- **Failure interpretation**:
  - 如果 pure weighted loss 更好且更稳，方法实现要简化
  - 如果 label 分布极端尖锐，先修 label pipeline 再谈 full run
- **Table / figure target**:
  - Appendix Table A1
  - Appendix Figure A1
- **Priority**: MUST-RUN

### Block 6: Optional Extension — 单个附加 backbone replication
- **Claim tested**: 方向不是只对一个 trainable backbone 成立
- **Why this block exists**: 这不是主论文必须项，但如果主结果够强，可以提升说服力。
- **Dataset / split / task**:
  - 与主设置相同
- **Compared systems**:
  - second stable backbone uniform vs CSFT
- **Metrics**:
  - 与 Block 1 相同
- **Setup details**:
  - 只选一个额外 backbone，不做 zoo
  - 只有在主 backbone 已经出现正结果后才运行
- **Success criterion**:
  - 改善方向一致，哪怕绝对幅度不同
- **Failure interpretation**:
  - 结论收窄为“compatible with GRU-class setup”
- **Table / figure target**:
  - Appendix Table A2
- **Priority**: NICE-TO-HAVE

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|-----------|------|------|---------------|------|------|
| M0 | 跑通 sensitivity label pipeline | label sanity + distribution stats + one toy batch overfit | 如果 label 极端尖锐或几乎全平，就先修 label 再训练 | 低 GPU / 中 CPU | finite-difference 太噪 |
| M1 | 复现 uniform baseline 和 oracle upper bound | GRU uniform + oracle eval | 如果 uniform / oracle gap 本身不稳定，先修数据切分和评估脚本 | 低到中 | metric 或 split 定义不稳 |
| M2 | 先看 CSFT 有没有信号 | 1-seed CSFT vs uniform on val/test | 如果 `cost / carbon` 没有正信号，先停，不展开 3 seeds | 中 | 主 thesis 太弱 |
| M3 | 做主表和关键 ablations | 3-seed CSFT + heuristic baselines + matched/mismatched | 如果 CSFT 不能稳定赢 heuristic，就把 claim 改弱 | 中到高 | finite-difference superiority 站不住 |
| M4 | 做机制图和 appendix 稳定性 | decile plots + mixed/pure + label stats | 如果机制图讲不清，主文说法要明显减弱 | 低到中 | 结果像普通 trick |
| M5 | 可选 replication | second backbone uniform vs CSFT | 只有主结果已正才做 | 中 | 花算力但收益小 |

## Compute and Data Budget
- **Total estimated GPU-hours**:
  - M0-M1: 低
  - M2: 低到中
  - M3: 中
  - 全部 must-run 合计：中等预算，重点不是 GPU，而是 offline QP label generation
- **Data preparation needs**:
  - 复用当前 `artifacts/forecast_data.npz`
  - 生成 chronological split 索引
  - 生成 stress subset masks（price/carbon/load 90th percentile）
- **Human evaluation needs**:
  - 无
- **Biggest bottleneck**:
  - sensitivity label generation 的稳定性与计算开销

## Risks and Mitigations
- **Risk**: finite-difference sensitivity 太噪
  - **Mitigation**: channel-scaled `delta`，95 分位 clipping，per-sample normalization，先做 pilot 再全量
- **Risk**: CSFT 只提升 forecast，不提升 control
  - **Mitigation**: 把 stop/go gate 放在 M2；先看 `cost / carbon` 是否动，再决定要不要铺开
- **Risk**: CSFT 只是 heuristic weighting 的换皮
  - **Mitigation**: 强制保留 `manual horizon` 和 `event-window` 两个 baselines
- **Risk**: 主结果只在某个 seed 或某个 stress subset 有效
  - **Mitigation**: 必做 3 seeds；主表必须同时给 standard test 和 stress subsets
- **Risk**: routing 历史结果继续干扰主线
  - **Mitigation**: 当前主计划完全不把 routing 放进 main blocks

## Final Checklist
- [ ] Main paper tables are covered
- [ ] Novelty is isolated
- [ ] Simplicity is defended
- [ ] Frontier contribution is explicitly not claimed in the main paper
- [ ] Nice-to-have runs are separated from must-run runs
