# LCDFFC 研究进度报告（基于当前仓库文档）

**日期**：2026-03-27  
**范围**：基于当前仓库中的研究与工程文档整理，不额外把旧文档当作当前实现事实。若文档与代码/测试冲突，应以 `code/` 与 `tests/` 为准。  
**当前阶段判断**：`post-prototype, pre-consolidation research platform`

## 1. 执行摘要

截至 2026-03-27，LCDFFC 已经从早期的单一路径原型，演进为一个围绕 `CityLearn Challenge 2023` 的 `forecast-then-control` 研究平台。工程层面，数据提取、统一 forecasting 训练入口、QP 控制器、主评估 runner、diagnostic forecast mode、多 backbone 实验入口、foundation model 对照、最小 prompt-only `LLMRouter` 等关键部件都已经具备。项目不再是 `GRU-only` 原型，但也还没有收敛成一个单一、稳定、可直接投稿的论文故事。

从研究叙事上看，项目经历了两次明显收缩。第一阶段主线是“固定低层 `forecast + QP`，用语言条件化高层路由在线适配 preference shift”；这条线曾在旧协议下得到正向结果，并形成了 `text_v4`、误差分析和 fallback 安全性分析。第二阶段在更强 baseline、更真实协议和更广 low-level 比较下，这条叙事被显著削弱：高层结论对 backbone 和协议敏感，真实 prompt-only LLM router 虽可运行、可比较，但并未稳定超过最强 fixed expert。

最新一轮文档材料表明，项目的最强可发表信号已经从“language-conditioned routing”转向“forecast-control misalignment”。最值得继续推进的主线，不再是继续扩 router 版本，而是系统证明：平均 forecast error 不是下游 control 质量的可靠代理指标，并进一步验证一个控制感知的模型选择分数是否优于 `MSE / MAE`。

## 2. 文档口径与可信度说明

当前文档反复给出的主阅读路径是：

1. `README.md`
2. `CLAUDE.md`
3. `INSTRUCTION.md`
4. `code/`、`tests/`、`configs/`

但当前工作区中未找到 `CLAUDE.md`。因此，按实际可读文档，本报告采用如下口径：

1. `README.md` 与 `INSTRUCTION.md` 作为当前 live 文档
2. `docs/` 中的 reference / dated 说明用于补充背景与阶段变化
3. `refine-logs/` 与顶层 `RESEARCH_REVIEW_*.md` 用于恢复实验时间线、review 决策与研究转向

基于这些文档，可以明确得到两个结论：

- 仓库当前最稳定的工程描述是“主闭环已打通，但研究叙事仍在收缩与重构中”。
- 很多旧文档已明确声明自己只是历史材料，不能再用来判断当前主训练入口、当前主评估协议、当前能力边界或当前论文主结论。

## 3. 工程进展

按 `README.md` 与相关说明文档，当前工程已经完成或打通的部分包括：

- `data/prepare_citylearn.py` 已承担 CityLearn 数据提取与训练数据生成入口。
- `data/dataset.py` 已支持滑动窗口数据集和标准化统计。
- `scripts/train_forecaster.py` 已成为统一 forecasting 训练入口，不再局限于 `GRU`。
- `models/factory.py` 已支持多 backbone 构建，包括 `gru / tsmixer / patchtst / transformer / granite_patchtst`。
- `controllers/qp_controller.py` 已是当前主控制器；`controllers/safe_fallback.py` 提供零动作回退。
- `eval/run_controller.py` 已是 forecast + control 的主评估入口，并支持 `learned / oracle / myopic` 诊断模式。
- `eval/run_preference_shift.py`、`eval/run_foundation_control.py`、`eval/run_foundation_controller_compare.py` 等脚本已把高层路由、foundation forecast 和 controller family 对照纳入统一实验框架。
- `llm_router/router.py` 已具有最小 prompt-only `LLMRouter.route()`；`llm_router/preference_routers.py` 保留规则与文本路由实验路径。

同时，文档也持续强调以下边界仍然有效：

- 不能把当前系统写成完整 `SPO+` / end-to-end decision-focused 训练系统。
- 不能把当前 router 写成 production-ready 或 agentic LLM system。
- 不能把 `RL baseline`、完整 `OOD`、完整 fallback runtime、完整 `mode` 链路写成已完成能力。

这说明工程已经进入“平台化实验阶段”，但还没有进入“能力闭环完成阶段”。

## 4. 研究进展时间线

### 4.1 早期研究收缩：从 broad idea 到 focused thesis

顶层 `chat.md`、`RESEARCH_REVIEW_2026-03-19.md` 和 `RESEARCH_REVIEW_2026-03-20_PAPER_GATE.md` 共同显示，项目最初的大叙事是：

- 时序分析 + 预测
- 优化控制 / decision-focused learning
- LLM 高层偏好路由
- 后续迁移到更多环境

但 review 很快指出，这样的 broad idea 对单篇论文来说过宽。于是项目在 2026-03-19 到 2026-03-20 期间被收缩成一个更集中的 thesis：

- 固定低层 `forecast + QP`
- 在 `CityLearn preference-shift` 协议下做高层偏好适配
- 以语言条件化高层路由作为主贡献
- 辅以误差分析与安全性分析

这一阶段的重要意义是：项目首次形成了“可以写 focused paper，但还不能写 broad paper”的判断框架。

### 4.2 Routing 线的正向进展

`refine-logs/PAPER_FACING_SUMMARY_2026-03-20.md` 和 `RESEARCH_REVIEW_2026-03-20_PAPER_GATE.md` 记录了 routing 线曾经达到的最好状态：

- `text_v4` 被认为是当前 best router。
- 在当时的 `preference-shift` 协议下，`text_v4` 优于最佳单一固定控制器 `fixed_reserve`。
- 误差来源已被拆解到 `reserve` 和 `carbon` 两个 regime。
- fallback 的保护作用已经有较完整的安全性证据。
- `v5 / v6 / v7` 未能超过 `v4`，说明局部 guard 调优趋于饱和。

因此，按 2026-03-20 的文档口径，项目已经具备：

- 主结果
- 误差分析
- 安全性分析
- 支撑“为何当前 best 就是 best”的负结果

这也是当时 Gate Review 给出“可以开始写 focused paper”的原因。

### 4.3 强基线与更真实协议带来的收紧

从 `ROUND2_FORECAST_BASELINE_RESULTS_2026-03-20.md` 到 `ROUND4_BACKBONE_EXPANSION_RESULTS_2026-03-21.md`，研究重点转向“当前高层结论是否只是弱低层和弱协议下的假象”。

关键进展包括：

- 引入 `TSMixer` 作为 stronger baseline，但它没有在当前设置下超过 `GRU`。
- 引入 `PatchTST` 后发现：forecasting 指标更差，但某些 control KPI 反而更好。
- 引入 event-driven preference protocol 后，旧的四段等长协议被证明偏乐观，`text_best` 不再是最强方法。
- 真实 prompt-only `LLMRouter.route()` 被打通，说明“真实 LLM router”不再只是空接口。
- 在 `Transformer` backbone 下，`llm_prompt_v1` 曾出现略优于 `fixed_peak` 的信号；但在 `Granite` backbone 下，最强 fixed expert 仍然明显更好。

这一阶段的核心结论是：

- low-level backbone 会显著改变 high-level 排序；
- protocol 会显著改变结论强度；
- 真实 LLM router 具备实验价值，但当前没有稳定赢过 strongest fixed expert。

因此，routing 线从“可以写 focused paper”进一步收缩为“存在局部正信号，但不足以支撑稳定强主张”。

### 4.4 Foundation model 与 controller diagnosis

`ROUND6_FOUNDATION_MODEL_RESULTS_2026-03-21.md` 与 `ROUND7_CONTROLLER_DIAGNOSIS_RESULTS_2026-03-21.md` 把研究重心进一步拉回 low-level。

这一阶段得到的关键事实包括：

- 在统一 zero-shot forecasting 比较下，`Moirai2` 最强，`TimesFM 2.5` 第二，`Chronos-2` 和 `MOMENT` 明显更弱。
- 在下游控制中，`Moirai2 + QP` 与 `TimesFM 2.5 + QP` 在 `cost / carbon / ramping` 上明显优于此前 strongest non-foundation baseline `Granite + QP`，但 `Granite + QP` 在 `peak` 上仍有优势。
- `controllers/qp_controller.py` 的 `carbon_intensity` 输入在部分主脚本中曾未被真正传入；修正为 `qp_carbon` 后，效果稳定优于 `qp_current`，但提升量级不大。
- 非 QP controller family（如 `forecast_heuristic`、`action_grid`）并没有打败 QP。

这一阶段的最重要认识是：

> forecasting 排名、foundation model 能力和 downstream control 排名之间，不存在简单单调关系。

这为后续“forecast-control misalignment”主线提供了直接证据。

### 4.5 CSFT 线的收缩、失败与保留价值

2026-03-26 之后，文档重心从 routing 线继续转向 controller-sensitive forecast training（CSFT）。

`FINAL_PROPOSAL.md`、`REVIEW_SUMMARY.md`、`REFINEMENT_REPORT.md` 与 `EXPERIMENT_RESULTS.md` 共同显示：

- 项目曾尝试把 controller-derived sensitivity 作为预测训练信号。
- 最小化后的方法收缩为：`single numerical preflight gate + fixed stabilization operator + one rerun`。
- raw-CSFT 已被当前证据证伪：`R202` 中 raw-CSFT 的 top-decile MAE 比 uniform 更差，且超过允许阈值。
- offline dual prior 提取失败。
- replay-calibrated prior 成功构建，并显著改善 forecast MAE。
- 但 replay-prior 在主 control KPI 上仍略弱于 uniform，只在 `ramping` 上略优。

因此，CSFT 线目前的状态不是“方法已经成立”，而是：

- 原始训练路线失败；
- 负结果被压缩成可解释、可复现的研究问题；
- replay prior 给出了一条仍可保留的机制信号；
- 但尚不足以形成可投稿的正向方法主张。

## 5. 当前最稳的研究结论

综合当前文档，以下判断可以被视为当前最稳的阶段性结论：

1. 项目已经完成从原型到研究平台的工程转变，但尚未收敛为单一论文故事。
2. 当前 low-level 主路径是“forecast backbone 或 diagnostic forecast mode -> QP controller -> CityLearn env”。
3. `QP` 仍然是当前最有效、最可解释的 controller family；主要问题不是“QP 完全不行”，而是输入完整性与多 KPI trade-off。
4. routing 线已经证明：
   - 最小 prompt-only `LLMRouter.route()` 可运行；
   - 语言条件化高层路由不是空想；
   - 但它目前不应被写成 production system，更不能写成稳定优于 strongest fixed expert 的结论。
5. stronger backbone 与 foundation model 比较已经证明：
   - 平均 forecast 指标与 downstream control 指标并不严格同向；
   - 强 forecast 模型不必然带来最优 control，反之亦然。
6. raw-CSFT 训练路线在当前 setting 下已被证伪，不应再继续写成主方法。
7. controller-sensitive 信息的更合理价值，当前更像是“评估 / 模型选择信号”，而不是“直接加权训练信号”。

## 6. 当前最可能的论文方向

`refine-logs/RESEARCH_REVIEW_2026-03-27.md` 给出了目前最明确的重新定位：

- 当前项目不应再把 `CSFT + backbone benchmarking + LLM routing` 三条线并列捆绑。
- 最强经验信号已经变成 **forecast-control misalignment**。
- 最合理的论文方向是：
  - 证明平均 forecast error 不是 downstream control 的可靠代理；
  - 在多场景下系统展示 ranking reversal；
  - 再提出并验证一个控制感知验证分数（CAVS）用于模型选择。

按这份最新 review，当前 bundled 版本只值 `4/10`；但如果转向 misalignment 方向，并完成多场景与建设性方法验证，则仍有中等概率冲击较强 venue。

## 7. 当前短板与风险

当前文档反复出现的主要短板有：

1. **研究主线分裂**
   - routing、backbone benchmark、foundation model、CSFT、misalignment 仍同时存在，论文主张不够单一。
2. **证据覆盖范围偏窄**
   - 多数关键结果仍集中在单场景、单 seed、单 controller family。
3. **高层结论稳定性不足**
   - backbone 与 protocol 一变，高层排序就可能变化。
4. **方法正向性不足**
   - routing 线有局部正向，但优势有限；
   - CSFT 线尚未在主 control KPI 上形成胜利。
5. **文档层仍有残留不一致**
   - 多份文档把 `CLAUDE.md` 作为核心 live 文档，但当前工作区未找到该文件；
   - 这意味着文档治理已改善，但还未完全闭环。

## 8. 建议的下一步

如果按当前全部文档综合判断，最合理的下一步不是继续横向扩实验名词，而是继续收缩：

1. 固定 corrected low-level reference stack，优先 `qp_carbon` 路径。
2. 以多场景、多 backbone 的主表重新组织 low-level 结果，明确 ranking reversal 是否可复现。
3. 把 sensitivity / prior 的角色从“训练权重”转向“控制感知验证或模型选择信号”。
4. 按 `RESEARCH_REVIEW_2026-03-27.md` 的顺序推进：
   - E01：固定修正后的基础栈
   - E02-E05：形成多场景 benchmark 与 misalignment 证据
   - E07-E09：机制分析与 CAVS
5. 暂停继续堆新 router 版本、弱 controller baseline 或 broad-paper 叙事。

## 9. 一句话结论

LCDFFC 当前最准确的研究状态不是“一个已经稳定成立的语言路由论文”，也不是“一个已经验证成功的 decision-focused 训练方法”，而是：

> 一个已经完成工程平台化、并通过多轮负结果与 stronger baseline 把问题逐步收缩出来的研究系统；其当前最强、最值得继续推进的论文信号，是 forecast metric 与 downstream control quality 之间的系统性错配。

## 10. 本报告综合的主要文档

本报告主要综合了以下文档簇：

- `README.md`
- `INSTRUCTION.md`
- `docs/data_spec.md`
- `docs/llm_router_spec.md`
- `docs/tmp_next_experiment_plan_2026-03-24.md`
- `docs/lcdffc_project_report_2026-03-18.md`
- `docs/project_progress_explainer_2026-03-20.md`
- `docs/project_progress_explainer_2026-03-24.md`
- `docs/repository_audit_2026-03-23.md`
- `RESEARCH_REVIEW_2026-03-19.md`
- `RESEARCH_REVIEW_2026-03-20_PAPER_GATE.md`
- `RESEARCH_REVIEW_2026-03-20_CRITICAL.md`
- `refine-logs/PAPER_FACING_SUMMARY_2026-03-20.md`
- `refine-logs/PIPELINE_SUMMARY.md`
- `refine-logs/ROUND2_FORECAST_BASELINE_RESULTS_2026-03-20.md`
- `refine-logs/ROUND3_RESEARCH_RESULTS_2026-03-20.md`
- `refine-logs/ROUND4_BACKBONE_EXPANSION_RESULTS_2026-03-21.md`
- `refine-logs/ROUND6_FOUNDATION_MODEL_RESULTS_2026-03-21.md`
- `refine-logs/ROUND7_CONTROLLER_DIAGNOSIS_RESULTS_2026-03-21.md`
- `refine-logs/FINAL_PROPOSAL.md`
- `refine-logs/REVIEW_SUMMARY.md`
- `refine-logs/REFINEMENT_REPORT.md`
- `refine-logs/EXPERIMENT_RESULTS.md`
- `refine-logs/EXPERIMENT_TRACKER.md`
- `refine-logs/RESEARCH_REVIEW_2026-03-27.md`
- `refine-logs/README.md`
- `chat.md`
