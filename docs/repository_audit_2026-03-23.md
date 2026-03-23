# 仓库审计报告（2026-03-23）

## 1. 审计目的与方法

本次审计的目标不是继续在旧文档上局部修补，而是重新建立一份以当前事实为中心的仓库状态判断，用来回答四个问题：

1. 当前工程到底实现到了哪里。
2. 当前状态与最初 main research idea 之间是否发生了偏离。
3. 现在最准确的阶段定位是什么。
4. 后续应该先收敛哪些工程与研究问题。

### 1.1 证据来源

本次结论来自四类证据的交叉核对：

- **代码实现**：`data/`、`models/`、`controllers/`、`eval/`、`llm_router/`、`scripts/`
- **测试边界**：`tests/` 中与 forecaster factory、QP controller、LLM router、controller modes、preference shift 相关的测试
- **当前顶层文档**：`AGENTS.md`、`CLAUDE.md`、`README.md`、`INSTRUCTION.md`、`docs/spec.md`、`docs/llm_router_spec.md`
- **dated research / refine logs**：`RESEARCH_REVIEW_2026-03-19.md`、`RESEARCH_REVIEW_2026-03-20_CRITICAL.md`、`RESEARCH_REVIEW_2026-03-20_PAPER_GATE.md`、`refine-logs/*.md`

### 1.2 事实优先级

本次审计采用如下优先级：

1. **代码 + 测试**：实现事实的最高来源。
2. **`AGENTS.md`**：仓库工作规则与文档职责边界。
3. **`CLAUDE.md`**：稳定工程契约。
4. **`README.md`**：对外概览与入口说明。
5. **`INSTRUCTION.md`**：阶段推进与执行计划。
6. **dated reviews / refine logs**：历史研究判断、实验记录、paper-facing 材料。

若文档与代码/测试冲突，默认以代码与测试为准，再反向修正文档。

### 1.3 文档角色与漂移矩阵摘要

| 文档类型 | 代表文件 | 当前角色 | 容易漂移的部分 |
|---|---|---|---|
| 当前工程/流程契约 | `AGENTS.md`、旧 `CLAUDE.md` | 工作规则、工程结构、文档职责 | 容易把某一轮状态快照误写成长期事实 |
| 对外概览 | `README.md` | 当前可运行能力、入口脚本、目录说明 | 容易混入本地实验结论与时间敏感说法 |
| 执行计划 | `INSTRUCTION.md` | Sprint、推进顺序、止损点 | 容易把阶段性结论写成当前永久状态 |
| 历史规格 | `docs/spec.md`、`docs/llm_router_spec.md` | 设计意图、早期接口假设 | 最容易与当前实现脱节 |
| 历史研究评审/实验日志 | `RESEARCH_REVIEW_*`、`refine-logs/*` | 研究收缩、扩展、阶段性结论 | 结论通常只对特定时间点、特定协议或特定 backbone 成立 |

### 1.4 这次审计发现的核心漂移点

1. **仓库已不是 GRU-only 原型，但部分文档仍在按 GRU-only 叙述。**
2. **`LLMRouter.route()` 已有最小 prompt-only 实现，但部分旧文档仍写成未实现。**
3. **研究 review 与 refine logs 中包含大量有效历史判断，但它们不是当前工程契约。**
4. **关于 Sprint 2 / RBC 验收是否已通过，文档之间存在互相冲突的表述；当前测试不能独立支撑“已稳定过线”的长期事实。**
5. **README、INSTRUCTION、CLAUDE、research review 在“当前事实 / 历史判断 / paper-facing 叙述”三层之间发生了混写。**

---

## 2. 当前工程真实架构

### 2.1 当前主可运行路径

当前代码最稳妥、最可辩护的主路径不是“GRU + QP 的单一原型”，而是：

```text
CityLearn observation
  -> centralized feature extraction / history window
  -> forecasting backbone 或 diagnostic forecast mode
  -> QP controller
  -> CityLearn env
```

其中：

- forecast backbone 由 `models.factory.build_forecaster` 统一构建：`models/factory.py:12`
- 主评估入口为 `eval/run_controller.py:155`
- 控制器为 `controllers/qp_controller.py:25`
- `run_controller` 明确支持三种 forecast mode：`learned / oracle / myopic`：`eval/run_controller.py:165`、`eval/run_controller.py:345`

### 2.2 当前支持的 forecasting 范围

当前仓库已实现的 forecasting backbone 不止 GRU，而是至少包括：

- `gru`
- `tsmixer`
- `patchtst`
- `transformer`
- `granite_patchtst`

证据：

- `models/factory.py:12`
- `tests/test_forecaster_factory.py:13`

但需要强调：

- `tests/test_forecaster_factory.py` 主要验证的是**工厂可实例化**与**forward 输出 shape**，并不等价于五类 backbone 都已完成同等强度的端到端验收：`tests/test_forecaster_factory.py:13`

### 2.3 当前支持的 controller / evaluation 范围

当前低层控制主干是共享动作、分楼 SOC 跟踪的 QP battery controller：

- 控制器入口：`controllers/qp_controller.py:87`
- 支持 reserve SOC、max charge、heterogeneous battery 参数：`controllers/qp_controller.py:230`
- 失败回退目前是零动作 `SafeFallback`，不是复杂安全策略：`controllers/qp_controller.py:68`

当前评估范围包括：

- `eval/run_controller.py`：forecast + QP 闭环：`eval/run_controller.py:155`
- `eval/run_rbc.py`：零动作 / default building behavior 基线：`eval/run_rbc.py:18`
- `eval/run_preference_shift.py`：偏好切换与路由实验入口
- `eval/run_foundation_control.py`：foundation forecast + QP 控制实验入口
- `eval/run_foundation_controller_compare.py`：同一 foundation forecast 下的 controller family 对比

这里需要明确一个经常被误写的事实：

- `eval/run_rbc.py` 并不是仓库内显式实现的 RBC 控制器，而是用 **zero action** 跑 CityLearn，依赖环境内部默认行为形成基线：`eval/run_rbc.py:19`、`eval/run_rbc.py:21`

### 2.4 当前 routing 范围

当前 `LLMRouter.route()` 并非纯 skeleton，而是已经有一个最小 prompt-only 实现：

- Prompt context 构建：`llm_router/router.py:44`
- lazy load transformers backend：`llm_router/router.py:68`
- JSON 解析与归一化：`llm_router/router.py:79`
- parse failure fallback 到默认 profile：`llm_router/router.py:104`

测试边界也支持这一点：

- 权重归一化与约束截断：`tests/test_llm_router.py:23`
- instruction 级缓存：`tests/test_llm_router.py:32`
- bad JSON fallback：`tests/test_llm_router.py:43`

但这仍然只能被称为：

- **最小 prompt-only 路由实现**
- **实验性高层策略接口**

不能称为：

- production-ready router
- deterministic-fallback-complete router
- robust agent system

### 2.5 三层能力分级

#### A. Core supported path

当前最稳定、最适合写入工程契约的能力：

- CityLearn 数据提取与集中式时序构造：`data/prepare_citylearn.py`
- 滑动窗口 dataset 与标准化统计：`data/dataset.py`
- 统一 forecasting 训练入口：`scripts/train_forecaster.py`
- forecast + QP 主闭环：`eval/run_controller.py`
- `learned / oracle / myopic` 三种诊断模式：`eval/run_controller.py:165`
- QP controller 与零动作 fallback：`controllers/qp_controller.py`、`controllers/safe_fallback.py`

#### B. Supported experimental path

代码与部分测试已经成型，但更适合写成“实验扩展”而非“稳定主路径”的能力：

- 多 backbone forecasting factory：`models/factory.py`
- 偏好切换与 event-driven 协议：`eval/run_preference_shift.py`、`tests/test_preference_shift.py`
- 文本/规则 preference routers：`llm_router/preference_routers.py`
- 最小 prompt-only `LLMRouter`：`llm_router/router.py`
- foundation forecast 控制评测：`eval/run_foundation_control.py`
- foundation forecast 下的 controller family 对比：`eval/run_foundation_controller_compare.py`
- heuristic / action-grid controller baselines：`controllers/baseline_controllers.py`、`tests/test_controller_baselines.py`

#### C. Planned / partial path

当前只能写成“部分接口存在”或“未闭环”的能力：

- SPO+ / decision-focused end-to-end 训练路径
- uncertainty-aware ensemble / gating 完整路径
- production-grade deterministic fallback for router
- RL baseline
- OOD 完整评估闭环

其中 `controllers/qp_controller.py:261` 的 `solve_with_cost_vector()` 说明仓库确实存在面向 SPO+ 的局部接口线索，但还不能据此声称完整 decision-focused 训练已实现。

---

## 3. 当前工程进展

### 3.1 从原型到研究平台的真实演进

从当前代码现实看，仓库已经从“单一 GRU + QP 的最小原型”演进到了一个更宽的研究平台，主要扩展在三条线上：

1. **预测侧扩展**：从 GRU 扩展到多种 forecasting backbone，并通过统一工厂与统一训练脚本接入。
2. **评估侧扩展**：从单一路径评估扩展到 `learned / oracle / myopic` 诊断、preference-shift 协议、foundation control、controller compare。
3. **高层策略侧扩展**：从最初的 router 规格设计，演进到规则 router、text router、最小 prompt-only LLM router 的实验框架。

### 3.2 当前阶段的最准确定位

当前项目不再适合被描述为：

- “Sprint 0/1 阶段的脚手架项目”
- “只有 GRU + QP 的最小闭环”
- “已经完成所有 main research idea 闭环”

更准确的阶段定位是：

> **一个已经越过最小原型阶段、具备多条实验路径，但尚未完成工程收敛与统一验收的研究平台。**

如果需要更短的英文标签，可以写为：

> **post-prototype, pre-consolidation research platform**

不建议直接写成“post-baseline”，因为当前仓库内可见的测试与稳定契约还不足以把“已稳定通过 RBC 验收”固化成无条件事实。

### 3.3 当前哪些进展可以视为真实完成

以下进展是可以站稳的：

- 预测 backbone 已从单一 GRU 扩展为多 backbone 工厂。
- `run_controller` 已形成明确的主评估入口，并支持 `learned / oracle / myopic` 诊断模式。
- QP controller 已有较完整的约束与求解逻辑，并配有专门测试。
- LLM router 不再只是空接口，而是存在最小 prompt-only 实现。
- 高层 preference-shift / router 实验框架已形成较多代码资产。
- foundation-model 相关评估脚本已经进入仓库，而不是只停留在文档设想层。

### 3.4 当前哪些进展仍不能写成“完成”

以下内容目前仍不能写成稳定完成：

- “仓库已经稳定打平或超过 RBC”
- “LLM router 已经形成 production-ready 闭环”
- “SPO+ 已进入 end-to-end 可复现实验阶段”
- “所有 backbone 都已完成同等强度的闭环验证”
- “高层路由结论已经跨 backbone、跨协议稳定成立”

---

## 4. 是否偏离了 main research idea

### 4.1 原始 broad idea

从早期文档与当前仓库命名看，原始 broad idea 是：

- 在 CityLearn 上做 forecast-then-control
- 逐步引入 decision-focused learning
- 再把 LLM 放在高层，做偏好/约束/模式路由

这条 broad idea 本身并没有被完全放弃。

### 4.2 后续 research review 的收缩

`RESEARCH_REVIEW_2026-03-19.md`、`RESEARCH_REVIEW_2026-03-20_CRITICAL.md`、`RESEARCH_REVIEW_2026-03-20_PAPER_GATE.md` 的共同作用，是把 broad idea 收缩成一个更聚焦的 paper thesis：

- 不把低层 forecast + control 本身当主要 novelty
- 把论文主张尽量聚焦到“language-conditioned high-level preference routing over a frozen low-level loop”
- 避免把“所有东西都做”写成论文故事

这种变化本质上是**研究主张的收缩**，不是工程实现的偏离。

### 4.3 后续实验的再扩展

之后的 rounds 又在两个方向上把仓库重新扩展了：

1. **低层能力扩展**：更强 backbone、foundation model、controller baseline diagnosis。
2. **高层协议扩展**：event-driven preference schedules、text router 迭代、route corruption 分析。

这类扩展有一部分是必要的，因为它们回答的是：

- 当前 bottleneck 在 forecast、controller 还是 routing？
- 高层路由结论是否依赖特定 backbone？
- QP 是否真的是主要短板？

也就是说，这些扩展不应被简单定义为“跑偏”。

### 4.4 最终判断：不是简单的“偏离 / 未偏离”二选一

更准确的结论是：

- **没有偏离 broad main idea**：forecast-control + decision-focused + high-level routing 这条总路线仍在。
- **发生了 paper thesis 的收缩**：研究 review 期间，主张被压缩到更可辩护的高层语言路由故事。
- **发生了必要的工程/实验再扩展**：后续为了定位 bottleneck 和补足证据，仓库扩大到了 multi-backbone、foundation model、controller diagnosis。
- **真正的问题不是“研究方向跑偏”，而是“文档没有及时把收缩后的 thesis、扩展后的代码现实、历史结论的时效性区分开”。**

因此，本仓库当前的主要问题是：

> **文档层级漂移与叙述混层**，而不是单纯的 research idea 偏离。

---

## 5. 当前已经站稳的结论

### 5.1 可当作稳定工程事实的结论

1. 仓库当前不是 GRU-only，forecasting backbone 已通过工厂扩展到多种类型。
2. `run_controller` 是当前主闭环入口，并支持 `learned / oracle / myopic` 三种诊断模式。
3. `LLMRouter.route()` 已有最小 prompt-only 实现，不应再写成“未实现”。
4. QP controller 是当前最成熟、测试最充分的低层组件之一。
5. `run_rbc.py` 当前实现的是 zero-action / default building behavior 基线，不应被误写为仓库内显式实现的独立 RBC policy。
6. foundation-model control 与 preference-shift 实验脚本已进入代码库，但应归入实验扩展层，而不是当前稳定主路径。

### 5.2 只能在特定条件下成立的结论

以下结论即使来自已有 round 结果，也应保留时间与协议条件：

- 某个 text router 版本在某轮协议下表现最好
- 某个 backbone 在某组 KPI 上是“当前最强”
- `qp_carbon` 相对 `qp_current` 的优势量级
- 某轮 foundation backbone 的名次排序

这些结论更适合保留在 dated review / refine logs 中，不应直接写入稳定工程契约。

### 5.3 当前不能站稳的结论

1. “Sprint 2 已经稳定通过 RBC 验收”
2. “当前主路径只有 GRU”
3. “LLMRouter.route() 未实现”
4. “LLM router 已是 production-ready agent system”
5. “所有扩展路径都已达到与主闭环同等成熟度”

---

## 6. 当前仍然缺什么

### 6.1 文档层面

1. 缺一份明确区分 **implemented / experimental / planned** 的仓库级审计文档。
2. 缺一份只描述稳定工程契约、不过度混入研究日记的 `CLAUDE.md`。
3. 当前多个文档对 RBC 验收状态、router 实现状态、主路径范围存在冲突。
4. 缺一份“当前主协议 / 当前主对比 / 当前主 artifact”的固定说明，导致后来者容易把历史结果当当前事实。

### 6.2 工程层面

1. 缺一个更清晰的“当前推荐主路径”与“实验扩展路径”分层。
2. 缺以统一协议支撑的 backbone / controller / router 对照矩阵。
3. prompt-only router 仍缺 deterministic fallback 完整闭环。
4. SPO+ 只有接口线索，没有完整训练闭环。
5. acceptance status 没有被固化为单一、可复现、可追溯的 artifact 规范。

### 6.3 研究层面

1. 低层主结论与高层主结论尚未收敛成一条稳定论文线。
2. 高层 routing 结论是否跨 backbone 稳定，仍需谨慎。
3. 低层 bottleneck 的最终解释仍未完全固化为统一结论。
4. broad idea、focused thesis、工程现实三者之间仍缺一套统一表达。

---

## 7. 下一步建议

### 7.1 优先做什么

1. **先固定文档层级**：
   - `CLAUDE.md` 只保留稳定工程契约。
   - `README.md` 只写当前对外概览与真实入口。
   - `INSTRUCTION.md` 保留阶段推进与执行顺序。
   - dated reviews / refine logs 明确保留为历史研究材料。

2. **再固定一个当前主评估协议**：
   - 明确当前推荐 backbone、controller config、forecast mode、baseline、输出 artifact 路径。
   - 让“是否通过当前验收”依赖可复现实验产物，而不是散落在 prose 中的结论。

3. **把仓库能力按 tier 管理**：
   - core supported path
   - supported experimental path
   - planned / partial path

### 7.2 哪些方向不应继续盲目扩展

1. 不应继续在没有统一协议前，盲目堆更多 router 版本命名。
2. 不应继续在没有统一主指标前，盲目堆更多 backbone 排名叙述。
3. 不应在 deterministic fallback 未补齐前，把 prompt-only router 写成“可用生产模块”。
4. 不应在 acceptance artifact 未固定前，继续放大“已过 RBC”这一类结论。

### 7.3 哪些问题应先收敛成稳定工程契约

1. 当前主闭环到底如何表述。
2. 当前哪些 runner 属于主路径，哪些属于研究扩展。
3. 当前哪些能力只是接口存在，哪些能力已经被测试承认。
4. 当前文档冲突时的解释顺序。

---

## 8. 附录：关键证据文件索引

### 8.1 主闭环与能力边界

- `data/prepare_citylearn.py`
- `data/dataset.py`
- `scripts/train_forecaster.py`
- `models/factory.py:12`
- `eval/run_controller.py:155`
- `controllers/qp_controller.py:25`
- `controllers/safe_fallback.py`

### 8.2 测试支持边界

- `tests/test_smoke.py`
- `tests/test_qp.py`
- `tests/test_run_controller_modes.py:20`
- `tests/test_forecaster_factory.py:13`
- `tests/test_llm_router.py:23`
- `tests/test_controller_baselines.py:13`
- `tests/test_preference_shift.py:19`

### 8.3 routing 与实验扩展

- `llm_router/router.py:15`
- `llm_router/preference_routers.py`
- `eval/run_preference_shift.py`
- `eval/run_foundation_control.py`
- `eval/run_foundation_controller_compare.py`
- `controllers/baseline_controllers.py`

### 8.4 文档角色与漂移判断依据

- `AGENTS.md`
- `CLAUDE.md`（重写前版本）
- `README.md`
- `INSTRUCTION.md`
- `docs/spec.md`
- `docs/llm_router_spec.md`
- `RESEARCH_REVIEW_2026-03-19.md`
- `RESEARCH_REVIEW_2026-03-20_CRITICAL.md`
- `RESEARCH_REVIEW_2026-03-20_PAPER_GATE.md`
- `refine-logs/EXPERIMENT_TRACKER.md`
- `refine-logs/ROUND3_RESEARCH_RESULTS_2026-03-20.md`
- `refine-logs/ROUND4_BACKBONE_EXPANSION_RESULTS_2026-03-21.md`
- `refine-logs/ROUND6_FOUNDATION_MODEL_RESULTS_2026-03-21.md`
- `refine-logs/ROUND7_CONTROLLER_DIAGNOSIS_RESULTS_2026-03-21.md`

---

## 9. 审计结论（一句话版）

当前仓库的主要矛盾不是“研究想法已经偏离”，而是：**代码已经从最小 GRU+QP 原型演进成多路径研究平台，但文档系统仍在混写当前工程契约、历史研究判断与 paper-facing 叙述，导致仓库状态被时间漂移掩盖。**
