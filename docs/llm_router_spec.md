# LLM Router 模块旧规格（legacy）

这个文件只保留早期 router 设计想法，不再作为当前实现说明。

当前 router 事实请看：

- `llm_router/router.py`
- `tests/test_llm_router.py`
- `CLAUDE.md`
- `README.md`

## 当前代码里已经存在什么

当前代码里已经有：

- `LLMRouter.route()`
- prompt context 构造
- transformers backend 的 lazy load
- JSON parse
- bad JSON 时回到默认 profile

所以这份旧规格里“`route()` 未实现”这类说法现在都失效了。

## 这个模块现在该怎么描述

当前更准确的说法是：

- 它是 high-level preference / constraint router
- 它输出结构化 `weights / constraints / mode`
- 它不输出底层连续动作
- 它现在只是最小 prompt-only 实验模块，不是 production router

## 现在还没完成什么

下面这些仍然不能写成完成：

- 更完整的 `mode` 到 controller 调用链映射
- 更强的 robustness 证据
- 出错时退回固定规则的完整路径
- agentic runtime 或 production deployment

## 保留这份文件的原因

它还能用来说明最早 router 设计想强调的边界：LLM 只负责高层偏好，不直接接管低层动作。
