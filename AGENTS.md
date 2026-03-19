# AGENTS.md

## 1. 文档定位

本文件是本仓库的主工作约定文档，覆盖两条主线：

1. 工程开发约定：模块边界、实现顺序、测试与复现要求、结果产物管理。
2. 研究文档维护约定：如何使用和更新 `README.md`、`INSTRUCTION.md`、`CLAUDE.md` 及其他研究文档。

后续任何代理、人类开发者或自动化工具进入本仓库时，应优先阅读本文件，再开展工作。

## 2. 核心原则

### 2.1 第一性原理

请使用第一性原理思考。你不能总是假设我非常清楚自己想要什么和该怎么得到。请保持审慎，从原始需求和问题出发，如果动机和目标不清晰，停下来和我讨论。

### 2.2 方案规范

当需要你给出修改或重构方案时，必须符合以下规范：

- 不允许给出兼容性或补丁性的方案。
- 不允许过度设计，保持最短路径实现，且不能违反上一条要求。
- 不允许自行给出我提供的需求以外的方案，例如一些兜底和降级方案，这可能导致业务逻辑偏移问题。
- 必须确保方案的逻辑正确，必须经过全链路的逻辑验证。

### 2.3 一条硬规则

不允许仓库文档长期处于“代码已经变了，文档还停留在旧状态”的状态。  
如果发现漂移，应优先修正文档，再继续扩展功能。

## 3. 当前项目快照

以下信息是从最近几轮工作中压缩出来的当前事实，后续开发默认以此为起点。

### 3.1 仓库事实

- GitHub 仓库已发布：`https://github.com/Ringhu/LCDFFC`
- 当前可见性：`public`
- 当前主分支：`main`
- 当前仓库状态：本地工作区应优先保持与 `origin/main` 对齐
- 当前阶段判断：`Sprint 2` 已在本地缓存的 2023 场景下通过 `RBC` 验收，但 `oracle` 诊断链路仍待修正

### 3.2 当前真实实现状态

已实现：

- `data/prepare_citylearn.py`
- `data/dataset.py`
- `scripts/train_gru.py`
- `controllers/qp_controller.py`
- `controllers/safe_fallback.py`
- `eval/run_rbc.py`
- `eval/run_controller.py`
- `eval/run_all.py`
- `llm_router/prompt_templates.py`
- `llm_router/json_schema.py`
- `scripts/generate_instruction_data.py`
- `tests/test_smoke.py`

未真正实现或未闭环：

- `LLMRouter.route()`
- deterministic LLM fallback
- `SPO+` 训练路径
- uncertainty ensemble 路径
- RL baseline
- OOD 评估脚本

### 3.3 当前关键结论

- 主线仍然正确：`CityLearn -> fixed-weight forecast + QP -> uncertainty -> decision-focused -> LLM router`
- 当前最大问题不是扩功能，而是先让固定权重 `forecast + QP` 过 `RBC` 验收线
- 修正控制器量纲、共享动作建模、SOC 读取和 rollout warm-start 后，`learned forecast + QP` 已在本地缓存的 2023 场景下优于 `RBC`
- 当前仍未闭环的关键问题转为：`oracle` 诊断路径显著劣化，说明 oracle target 与在线控制时序可能仍有错位或语义不一致
- 当前保存的旧结论 `myopic≈RBC / oracle<RBC` 不能再直接作为控制器主问题的依据，必须以修正后的新复现实验为准
- 当前环境历史上出现过 `cvxpy` 缺失，导致 `tests/test_qp.py` 无法直接运行；继续开发前优先检查依赖是否齐全

### 3.4 当前默认优先级

除非用户明确改方向，否则按下面顺序工作：

1. 修正文档与代码事实漂移
2. 恢复环境可复现性
3. 复现并诊断 `RBC` 与 `forecast_qp` 差距
4. 让固定权重闭环先过验收
5. 再进入 uncertainty / decision-focused / LLM router

### 3.5 当前公开仓库发布规则

公开仓库中不应提交以下内容：

- `artifacts/`
- `reports/`
- `.claude/`
- `__pycache__/`
- `chat.md`
- `CODEX.md`
- `codex-execution-plan-2026-03-18.md`
- `floating-hugging-kay.md`

发布前必须重新检查 `.gitignore` 是否仍覆盖这些内容，并确认没有：

- 大体积产物文件
- 本地缓存
- token、密钥、密码、私有对话材料

## 4. 研究与工程主线

### 4.1 当前主线

当前主线不是“RL + LLM agent 一起上”，而是：

1. 先在 `CityLearn Challenge 2023` 上打穿 `forecast-then-control`
2. 先过 `RBC` 基线
3. 再做 uncertainty-aware fallback
4. 再做 decision-focused learning
5. 最后再接 LLM preference router
6. `Grid2Op` 是第二阶段验证，不是第一阶段主战场

### 4.2 LLM 角色边界

LLM 的角色必须保持为：

- 高层偏好/约束/模式路由器
- 输出结构化 `weights / constraints / mode`
- 不能直接输出底层连续动作

## 5. 工程开发约定

### 5.1 模块职责

- `data/`：数据提取、窗口数据集、标准化和统计信息
- `models/`：预测模型与训练相关逻辑
- `controllers/`：QP/MPC、安全回退、控制策略
- `eval/`：基线、端到端评估、KPI 统计、实验对比
- `llm_router/`：Prompt、Schema、LLM 路由与确定性回退
- `scripts/`：训练、数据生成、聚合、绘图等可执行脚本
- `reports/`：结果、图、表
- `artifacts/`：中间产物、模型权重、数据缓存

### 5.2 默认开发顺序

默认按下面顺序推进，不跳步：

1. 让文档与代码事实一致
2. 让环境可复现
3. 让固定权重 `forecast + QP` 稳定跑通
4. 让结果达到或接近 `RBC` 验收线
5. 再进入 uncertainty
6. 再进入 decision-focused
7. 再进入 LLM router
8. 最后做 RL baseline、OOD 和论文大表

### 5.3 代码修改要求

- 改公共接口时，必须同步更新相关文档。
- 改配置读取方式时，必须同步更新 `README.md` 和对应配置说明。
- 新增可运行脚本时，必须说明输入、输出、默认路径。
- 新增实验结果时，必须落到 `reports/` 或 `artifacts/`，不能只留在口头描述里。

### 5.4 测试与验收

至少维护三层检查：

1. `smoke test`
2. 模块级单测
3. 端到端评估结果

如果实现了代码但没有对应验证，状态只能写“部分完成”，不能写“完成”。

## 6. 文档体系与使用方式

### 6.1 文档优先级

当多个文档存在重叠信息时，按下面顺序理解：

1. `AGENTS.md`
2. `chat.md`
3. `INSTRUCTION.md`
4. `CLAUDE.md`
5. `README.md`

如果 `README.md`、`INSTRUCTION.md`、`CLAUDE.md` 与实际代码不一致，应以代码事实和本文件更新规则为准，随后立刻修正文档。

### 6.2 各文档职责

`AGENTS.md`：

- 当前仓库的实际工作规则和文档同步规则。
- 记录长期有效的开发与维护约定。

`chat.md`：

- 研究意图、论文路线、阶段验收标准的来源文档。
- 记录最初的研究目标、问题定义、方法主线和论文故事。
- 提供阶段性验收标准，例如先做 `CityLearn`、先做 `central_agent=True`、先做 battery-only control、先做 fixed-weight `forecast + QP/MPC`、先证明闭环优于或至少打平 `RBC`。

`INSTRUCTION.md`：

- 实验推进顺序、Sprint 任务、止损点。
- 回答“现在应该做什么”“接下来按什么顺序推进”。

`CLAUDE.md`：

- 工程结构、接口、编码规范、模块边界。
- 回答“应该怎么组织代码”“哪些模块能互相依赖”。

`README.md`：

- 对外概览、快速开始、当前可运行入口。
- 面向首次进入仓库的读者。

### 6.3 四个核心文档怎么用

使用 `chat.md` 时：

- 它是研究意图参考文档，不是日常进度日志。
- 不要把开发进度回写到 `chat.md`。
- 新工作开始前，应先对照 `chat.md`，确认没有偏离主线。

使用 `CLAUDE.md` 时：

- 当模块边界、公共接口、配置范式、关键编码规范发生变化时更新。
- 它记录的是稳定工程约定，不记录细碎实验结果。
- 如果某项能力尚未实现，不要在 `CLAUDE.md` 中把它写成已完成能力。

使用 `INSTRUCTION.md` 时：

- 当 Sprint 状态变化时更新。
- 当新增止损点、验收标准、实验分支时更新。
- 当某个 Sprint 已完成或被推迟，应把状态写清楚。
- 它记录的是执行计划与阶段状态，不是对外介绍。

使用 `README.md` 时：

- 当入口命令、依赖、目录结构、当前可运行功能发生变化时更新。
- `README.md` 只能写当前真实可运行的内容。
- 不得把未来计划、未完成模块、研究愿景写成“已经支持”。

## 7. 文档维护约定

### 7.1 哪些变更必须更新文档

出现下列情况时，必须同步更新至少一个 md 文件：

1. 新增或删除公共脚本入口
2. 模块职责变化
3. 接口签名变化
4. 当前主实验结论变化
5. Sprint 状态变化
6. 基线结果变化
7. 已实现/未实现边界变化

### 7.2 每个文档的更新触发条件

更新 `README.md`：

- 快速开始命令变化
- 依赖变化
- 当前可用功能变化
- 目录结构变化

更新 `INSTRUCTION.md`：

- Sprint 完成、推迟或重排
- 止损点变化
- 新实验阶段加入
- 当前阶段结论变化

更新 `CLAUDE.md`：

- 架构图变化
- 模块 ownership 变化
- 公共接口变化
- 工程约束变化

更新 `AGENTS.md`：

- 工作规则变化
- 文档同步机制变化
- 研究与工程协作方式变化
- 新增长期约定

新增或调整 Git 工作流时：

- 如果提交、推送、hook 或发布流程发生变化，必须同步更新 `AGENTS.md`

### 7.3 进度回写原则

除 `chat.md` 外，其他 md 文档都应按职责及时回写进度，但必须遵守：

1. 按职责写，不要把所有内容都堆进一个文档。
2. 写事实，不写愿景冒充事实。
3. 写当前状态，不写过时状态。
4. 写变化原因和影响，不要只改结论不改上下文。

### 7.4 当前推荐的状态表达方式

在 `INSTRUCTION.md` 或相关进度文档中，优先使用下面的描述：

- `已完成`：代码、测试、结果三者都到位
- `部分完成`：代码已有，但测试或结果未闭环
- `待验证`：已有实现，但尚未通过当前阶段验收
- `阻塞中`：缺依赖、缺环境、结果明显不达标或设计需要回退

推荐把每次工作结果归为四类之一：

- `已实现`
- `部分实现`
- `已验证`
- `已阻塞`

不要只写“完成”，要说明是：

- 代码完成但未验证
- 验证通过
- 有结果但未达验收线
- 由于环境或依赖阻塞

### 7.5 当前仓库的文档维护重点

当前阶段应重点维护以下内容：

1. `README.md` 的入口命令必须和真实脚本一致
2. `INSTRUCTION.md` 必须反映当前实际已完成到哪个 Sprint
3. `CLAUDE.md` 不应把 `SPO+` 和 `LLM router` 写成已完成实现
4. `AGENTS.md` 负责约束“文档必须和代码事实同步”

## 8. 执行流程

### 8.1 最小执行清单

任何代理进入本仓库工作时，先做这几件事：

1. 阅读 `AGENTS.md`
2. 用 `chat.md` 校准主线和验收标准
3. 用 `INSTRUCTION.md` 判断当前所处阶段
4. 用 `CLAUDE.md` 理解模块边界和接口
5. 用 `README.md` 检查当前对外说明是否仍准确
6. 完成工作后，按本文件规则回写相关 md 文档

### 8.2 推荐的文档同步流程

每次完成一个可识别的开发动作后，按下面顺序检查：

1. 代码是否已经可运行或至少可验证
2. `reports/` 或 `artifacts/` 是否已有对应产物
3. `README.md` 是否仍然描述真实入口和能力
4. `INSTRUCTION.md` 是否需要更新当前 Sprint 状态
5. `CLAUDE.md` 是否需要更新接口或模块约定
6. `AGENTS.md` 是否需要更新工作流程或长期规则

### 8.3 提交与推送约定

- 每完成一个可识别的步骤，应形成一次独立提交。
- 提交完成后，应立即推送到 `origin/main`，不要长期堆积本地未发布改动。
- 仓库当前使用本地 `post-commit` hook 自动执行推送；如果 hook、分支或远程发生变化，需重新确认该流程仍可用。
