# LCDFFC 实验指南

## 当前阶段摘要

当前仓库状态不是“从 Sprint 0 开始”，而是：

- `Sprint 0`：已完成
- `Sprint 1`：基本完成
- `Sprint 2`：已在本地缓存的 2023 场景下通过 `RBC` 验收，`oracle` 诊断链路仍待修正
- `Sprint 3+`：尚未进入实做阶段，只有少量骨架或接口预留

当前最优先目标不再是“证明 learned+QP 能否过 `RBC`”，而是先把 `Sprint 2` 的诊断链路补齐：解释为什么 `oracle` 模式仍显著劣化，并把通过验收的配置、结果和文档固定下来。

## 总体目标

在 CityLearn Challenge 2023 上实现最小可行的 forecast-then-control 系统，先打穿固定权重闭环，再逐步加入 decision-focused learning 和 LLM 偏好路由。

---

## Sprint 计划

### Sprint 0：项目脚手架（已完成）

**目标**：建立完整的项目结构和文档。

- [x] 创建目录结构
- [x] 编写 CLAUDE.md / README.md / INSTRUCTION.md
- [x] 创建各模块骨架（`__init__.py` + 接口定义）
- [x] 编写 Agent Prompt 文件
- [x] 配置文件模板

**验收标准**：`python tests/test_smoke.py` 通过。

---

### Sprint 1：数据 + 预测模型（基本完成）

**目标**：跑通 CityLearn 数据提取 → GRU 训练 → 预测输出。

**Agent A（数据）任务**：
1. 实现 `data/prepare_citylearn.py`：从 CityLearn schema 提取历史数据
2. 实现 `data/dataset.py`：滑动窗口 Dataset，输出 `(history, future_target)` 对
3. 输出 `artifacts/data_summary.json`，包含特征维度、时间范围等

**Agent B（预测）任务**：
1. 实现 `models/gru_forecaster.py`：标准 GRU，支持多步预测
2. 训练脚本：MSE loss，early stopping
3. 输出训练曲线到 `reports/`

**止损点**：
- 如果 CityLearn 数据提取卡住超过 2 小时 → 改用 CSV 导出 + 手动加载
- 如果 GRU 训练 loss 不下降 → 检查数据标准化和学习率

---

### Sprint 2：控制器 + 基线评估（基本完成，诊断待补齐）

**目标**：QP 控制器 + RBC 基线，端到端跑通 CityLearn 评估。

**Agent C（控制器）任务**：
1. 实现 `controllers/qp_controller.py`：
   - 目标函数：`w_cost * cost + w_carbon * carbon + w_peak * peak_proxy + w_smooth * smoothness`
   - 约束：SOC bounds、charge/discharge rate bounds
   - 接口：`act(state, forecast, weights, constraints) -> action`
2. 实现 `controllers/safe_fallback.py`：保守回退策略（不充不放或基于规则）
3. Receding horizon：24 步规划，执行第一步

**Agent D（评估）任务**：
1. 实现 `eval/run_rbc.py`：CityLearn 自带 RBC 作为基线
2. 实现 `eval/run_controller.py`：加载预测模型 + QP 控制器，跑完整 episode
3. 实现 `eval/metrics.py`：计算 cost, carbon, peak, ramping 等 KPI
4. 对比表输出到 `reports/`

**止损点**：
- 如果 cvxpy 求解不稳定 → 放松约束或增加正则项
- 如果 QP 控制器不如 RBC → 检查预测质量和权重设置

**当前状态补充**：

- `controllers/qp_controller.py`、`eval/run_rbc.py`、`eval/run_controller.py`、`eval/run_all.py` 已存在
- 修正控制器量纲、共享动作建模、SOC 读取和 rollout warm-start 后，`learned forecast + QP` 在本地缓存的 2023 场景下已优于 `RBC`
- 当前环境历史上出现过 `cvxpy` 缺失，进入下一阶段前先恢复可复现运行
- 当前已补 `learned / oracle / myopic` 三种诊断模式
- 当前新复现实验结果显示：
  - `learned`: cost `32.4935`, carbon `496.2018`, peak `14.9950`
  - `RBC`: cost `33.0114`, carbon `499.6858`, peak `16.4417`
  - `myopic`: cost `33.0120`, carbon `499.6928`, peak `16.4417`，基本打平 `RBC`
  - `oracle`: cost `33.6512`, carbon `510.9105`, peak `17.1023`，仍明显劣于 `RBC`
- 当前已确认 `oracle_data` 与零动作 rollout 的 `price/load/solar` 时序一致，且 `CLARABEL -> OSQP` 求解顺序已消除一类退化解
- 因此下一步不应直接进入 uncertainty，而应先解释为什么 oracle target 在当前控制目标下会系统性劣化，并把当前通过验收的 learned 配置和命令固化

---

### Sprint 3：Decision-Focused Learning（未开始）

**目标**：引入 SPO+ loss，让预测模型直接优化决策质量。

**关键实现**：
1. 在 `models/` 中添加 SPO+ loss 计算
2. 需要对 QP 层做 cost perturbation（`c + 2*c_hat - c_true`）
3. 重新训练 GRU，对比 MSE-only vs SPO+ 的下游控制性能

**止损点**：
- SPO+ 梯度数值不稳定 → 增大 perturbation epsilon 或 clip 梯度
- 训练后性能无提升 → 检查 QP 的最优解是否对 cost 向量足够敏感

---

### Sprint 4：LLM 偏好路由器（未开始，仅有骨架）

**目标**：用 LLM 根据场景上下文生成控制器权重和约束。

**Agent E（LLM 路由）任务**：
1. 实现 `llm_router/prompt_templates.py`：场景描述 + 输出格式要求
2. 实现 `llm_router/json_schema.py`：输出 schema 定义和校验
3. 实现 `llm_router/router.py`：调用 LLM，解析 JSON 输出
4. 实现 `scripts/generate_instruction_data.py`：生成合成 instruction 数据

**LLM 选择**：
- 第一版：prompt-only，使用本地 Qwen2.5-7B-Instruct（通过 vLLM 部署）
- 后续：可基于合成数据做 LoRA 微调

**止损点**：
- LLM 输出格式不稳定 → 增加 few-shot examples 或 constrained decoding
- 延迟太高 → 降低调用频率（每小时调用一次而非每步调用）

**当前状态补充**：

- `prompt_templates.py`、`json_schema.py`、`generate_instruction_data.py` 已有
- `LLMRouter.route()` 尚未实现
- deterministic fallback 尚未补齐

---

### Sprint 5：消融实验 + 论文（未开始）

**目标**：完成消融实验，撰写论文。

**消融维度**：
1. MSE-only vs SPO+ loss
2. Fixed weights vs LLM-routed weights
3. 有/无安全回退
4. GRU vs TSMixer/PatchTST（如时间允许）

**论文结构（初步）**：
1. Introduction：预测-控制分离的问题 + LLM 作为偏好接口的动机
2. Related Work：decision-focused learning, MPC for buildings, LLM for control
3. Method：架构、SPO+、LLM router
4. Experiments：CityLearn 2023, baselines, ablations
5. Conclusion

---

## Agent 任务分配

| Agent | 负责模块 | 不可修改 |
|-------|---------|---------|
| Agent A | `data/` | models, controllers, eval, llm_router |
| Agent B | `models/` | data, controllers, eval, llm_router |
| Agent C | `controllers/` | data, models, eval, llm_router |
| Agent D | `eval/` | data, models, controllers, llm_router |
| Agent E | `llm_router/`, `scripts/` | data, models, controllers, eval |

每个 Agent 只修改自己负责的目录，通过 `__init__.py` 暴露的公共接口与其他模块交互。

## 当前执行顺序

在当前阶段，按以下顺序推进，不跳步：

1. 修正文档、配置、入口命令与代码事实漂移
2. 恢复环境可复现性
3. 重新跑 `RBC` 与 `forecast_qp`
4. 用 `learned / oracle / myopic` 诊断差距来自预测、权重、特征映射还是动作注入
5. 先让固定权重闭环过验收，再进入 `Sprint 3+`

## 当前文档维护要求

- `README.md` 只能写当前真实可运行的能力
- `CLAUDE.md` 不得把 `SPO+` 和 `LLM router` 写成已完成实现
- `AGENTS.md` 是主工作约定文档，若本文件与其冲突，以 `AGENTS.md` 为准

---

## 配置管理

所有超参数统一放在 `configs/*.yaml` 中：
- `data.yaml`：数据路径、特征选择、窗口大小
- `forecast.yaml`：模型结构、训练超参数
- `controller.yaml`：QP 权重、约束参数、horizon
- `eval.yaml`：评估场景、基线配置
- `llm_router.yaml`：LLM 模型路径、prompt 参数

---

## 关键设计决策

1. **为什么用 cvxpy 而不是端到端可微分层？**
   - cvxpy + OSQP 更稳定，SPO+ 不需要 QP 层可微分（只需要前向求解）
   - 后续可替换为 cvxpylayers 做端到端对比

2. **为什么用 central_agent 模式？**
   - 简化第一版实现，所有建筑共享一个控制策略
   - 后续可扩展为分布式/分层控制

3. **为什么 LLM 是 prompt-only？**
   - 快速验证 LLM 作为偏好接口的可行性
   - LoRA 微调是增量改进，不影响架构设计
