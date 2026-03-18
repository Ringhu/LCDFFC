# LCDFFC 项目阶段汇报（2026-03-18）

## 1. 工程目的

LCDFFC 的目标是在 `CityLearn Challenge 2023` 上实现一个面向外生时间序列驱动控制的 `forecast-then-control` 系统，并逐步发展为可投稿到 CCF-A 会议或期刊的研究原型。项目当前选择以建筑群储能控制为主场景，将数值时序建模、优化控制和 LLM 高层路由结合起来，形成一条风险可控、可快速验证的研究路线。

从工程角度看，本项目不是简单训练一个 RL agent，而是希望先完成一个稳定、可解释、可复现实验闭环：输入多变量时序观测，预测关键未来量，利用 QP/MPC 输出电池动作，再在 CityLearn 环境中评估成本、碳排、峰值和爬坡等 KPI。

## 2. 研究意义

这个项目的研究意义主要体现在三个方面。

第一，它试图打通“时间序列预测”和“顺序决策控制”之间的链路。许多时序工作只关注预测误差，但对控制任务来说，更关键的是预测是否真的改善了决策质量。

第二，它采用“数值模型做底层预测与控制，LLM 做高层偏好与约束路由”的思路，避免了让 LLM 直接输出连续控制动作所带来的稳定性和可验证性问题。这条路线更符合当前顶会对结构化混合方法的偏好。

第三，项目从一开始就强调鲁棒性和可扩展性。CityLearn 用作第一阶段主验证环境，后续可以扩展到 Grid2Op 作为第二 benchmark，从而把论文故事从单任务工程原型提升为更具通用性的外生时序驱动控制框架。

## 3. 要解决的问题

当前项目希望解决以下几个核心问题：

1. 在存在天气、电价、碳强度和建筑负荷波动的情况下，如何利用短期时序预测提升储能控制质量。
2. 如何让控制目标不仅固定为单一 reward，而是可以面向成本、碳排、峰值和安全约束进行多目标调节。
3. 如何避免“预测指标变好但控制结果不变好”的问题，即让预测真正服务于下游决策。
4. 如何在未来引入不确定性估计和 LLM 偏好路由后，仍然保持控制系统可解释、可回退和可验证。

简化地说，项目当前的核心科学问题是：**面向外生时间序列驱动的建筑群储能控制，如何构建一个既能快速验证、又具备论文扩展潜力的预测-控制一体化研究框架。**

## 4. 研究方法

项目目前采用的是分层研究方法。

### 4.1 当前已落地的方法主干

- 数据层：从 CityLearn 环境提取历史观测，构造滑动窗口数据集，并完成标准化处理。
- 预测层：使用 GRU 作为第一版多步预测模型，生成后续控制需要的关键预测量。
- 控制层：使用基于 `cvxpy` 的 QP/MPC 控制器，根据预测结果和固定权重输出单步储能动作。
- 评估层：以 RBC 作为基线，计算 `cost`、`carbon`、`peak`、`ramping` 等指标。

### 4.2 规划中的扩展方法

- Decision-focused learning：后续引入 `SPO+`，让预测训练直接面向控制目标，而不只是最小化 MSE。
- Uncertainty-aware fallback：通过 ensemble 或其他不确定性估计，在高风险时段自动收紧约束或回退到保守模式。
- LLM preference router：由 LLM 输出高层 `weights / constraints / mode`，只调整目标与约束，不直接输出底层连续动作。

### 4.3 方法论原则

项目遵循一个重要原则：**先做固定权重 forecast + QP 的可复现闭环，再做 uncertainty，再做 decision-focused，再做 LLM router。** 这样可以把工程风险和研究风险逐层拆开，而不是一开始把所有新模块叠加在一起。

## 5. 研究整体流程

结合当前文档，整个项目可以分成以下阶段：

### Phase 0：项目脚手架

- 建立目录结构、模块边界、配置文件和基础文档。

### Phase 1：数据与预测

- 从 CityLearn 提取数据。
- 构建滑动窗口数据集。
- 训练第一版 GRU 预测模型。

### Phase 2：控制与基线评估

- 实现固定权重 QP/MPC 控制器。
- 跑通 RBC 基线。
- 完成预测 + 控制的端到端评估。

### Phase 3：鲁棒性增强

- 引入不确定性估计。
- 增加安全回退与 conservative mode。
- 做轻量 OOD 评估。

### Phase 4：Decision-Focused Learning

- 引入 `SPO+` 或类似损失。
- 比较 MSE-only 与 decision-focused 的下游控制效果。

### Phase 5：LLM 偏好路由器

- 用 LLM 根据结构化上下文输出控制权重、约束和模式。
- 评估它与手工规则权重的对比表现。

### Phase 6：论文化与第二验证环境

- 系统消融实验。
- OOD 与鲁棒性实验。
- 如主线稳定，再迁移到 Grid2Op 做第二 benchmark。

## 6. 目前进度

### 6.1 已完成内容

当前仓库已经完成了以下内容：

- 项目脚手架、模块边界和基础配置。
- `data/prepare_citylearn.py` 与 `data/dataset.py`。
- `scripts/train_gru.py` 与基础 GRU 预测模型。
- `controllers/qp_controller.py` 与 `controllers/safe_fallback.py`。
- `eval/run_rbc.py`、`eval/run_controller.py`、`eval/run_all.py`。
- `llm_router/prompt_templates.py`、`llm_router/json_schema.py`。
- `scripts/generate_instruction_data.py`。
- `tests/test_smoke.py`。
- GitHub 公开仓库已经发布：`https://github.com/Ringhu/LCDFFC`。

### 6.2 当前未完成内容

以下内容仍未真正落地或未形成可验证闭环：

- `LLMRouter.route()` 及其 deterministic fallback。
- `SPO+` 训练路径。
- uncertainty ensemble 路径。
- RL baseline。
- OOD 评估脚本。

### 6.3 当前结果与阶段判断

从已有结果看，项目已经进入“核心闭环已实现，但尚未通过阶段验收”的状态。

当前保存结果显示：

- `2023` 数据上，`forecast_qp` 在 `cost`、`carbon`、`peak`、`ramping` 上都略差于 `RBC`。
- `2022` 数据上，`forecast_qp_2022` 也没有体现出优于 `RBC` 的稳定优势。

这意味着项目目前**完成了 Sprint 2 的大部分工程实现，但还没有完成 Sprint 2 的研究验收**。换句话说，当前最大的工作重点不是继续堆新模块，而是先诊断并缩小 `forecast_qp` 与 `RBC` 的差距。

## 7. 当前主要问题与下一步计划

### 7.1 当前主要问题

1. 文档与代码事实还存在漂移，部分文档对 `SPO+` 和 `LLM router` 的描述偏超前。
2. 当前固定权重 `forecast + QP` 尚未通过基线验收。
3. 环境可复现性仍需继续核对，例如 `cvxpy` 依赖问题曾导致 QP 相关测试无法直接运行。

### 7.2 下一步计划

下一阶段建议按下面顺序推进：

1. 修正文档与代码事实漂移。
2. 恢复环境可复现性，重新跑通关键测试与评估。
3. 增加 `oracle forecast`、`official forecast only`、`no-forecast/myopic` 对照实验，定位问题来源。
4. 调整固定权重和控制约束，优先让固定权重闭环通过 `RBC` 验收线。
5. 只有在上述目标达成后，再继续 uncertainty、decision-focused 和 LLM router。

## 8. 当前结论

总体来看，LCDFFC 已经完成了从研究想法到工程原型的第一步：项目结构、基础数据链路、预测模型、控制器和评估框架已经成型，具备了继续深入的基础。

但从研究进度上看，项目目前仍处在“从原型走向有效结果”的关键转折点。当前最重要的任务不是扩展模块数量，而是让第一条主线真正站稳：**用固定权重的 forecast + QP 在 CityLearn 上稳定证明预测对控制是有帮助的。**
