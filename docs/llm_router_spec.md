# LLM Router 最小规格说明

## 当前定位

LLM router 不是当前第一阶段主闭环的一部分。  
它的角色被限定为高层偏好和约束路由器，不能直接输出底层连续动作。

## 目标输出

最终可用版本应输出结构化对象，至少包含：

- `weights`
- `constraints`
- `mode`

其中：

- `weights` 用于调整 QP 目标权重
- `constraints` 用于调整高层控制约束，例如 `reserve_soc`
- `mode` 用于表达策略模式，例如 `cost_first`、`carbon_first`、`balanced`

## 当前代码状态

当前已存在：

- `llm_router/prompt_templates.py`
- `llm_router/json_schema.py`
- `scripts/generate_instruction_data.py`

当前未完成：

- `LLMRouter.route()`
- 真正的模型调用逻辑
- deterministic fallback
- 将 `mode` 纳入 schema 与控制调用链

## 设计约束

- 调用频率应低于底层控制频率，优先按小时级或更低频率调用
- 输出必须是结构化 JSON，而不是自由文本
- 即使 LLM 不可用，也必须能退回到确定性默认策略
- 在第一阶段验收通过前，不应把该模块当作当前主结果来源

## 当前文档要求

在 `README.md`、`CLAUDE.md`、`INSTRUCTION.md` 等文档中，不得把 LLM router 写成已完成的可运行能力。当前只能写成：

- 已有 prompt/schema 骨架
- 尚未接入真实 runtime 路由
