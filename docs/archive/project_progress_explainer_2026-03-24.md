# LCDFFC 进度解释（dated, archive）

这个文件只保留 2026-03-24 当天对项目状态的一次解释，不再承担当前仓库事实源角色。

当前主阅读路径是：

1. `README.md`
2. `CLAUDE.md`
3. `INSTRUCTION.md`
4. `code/`、`tests/`、`configs/`

如果文档和代码不一致，以 `code + tests` 为准。完整事实优先级看 `CLAUDE.md`。

## 这份 dated 说明还能回答什么

它现在只适合回答这些问题：

- 2026-03-24 当天为什么把项目写成 `post-prototype, pre-consolidation research platform`
- 当时为什么认为仓库已经不是 GRU-only
- 当时为什么强调 `LLMRouter.route()` 已有最小 prompt-only 实现
- 当时为什么建议先固定 reference low-level stack，再做 preference 和 routing 验证

## 不要再用它判断什么

不要再用这个文件判断：

- 当前主训练入口
- 当前主评估协议
- 当前哪些能力算 core supported path
- 当前 router 是否已经足够成熟
- 当前论文该写多强的结论

这些问题现在请直接看：

- `CLAUDE.md`
- `README.md`
- `INSTRUCTION.md`
- `models/factory.py`
- `eval/run_controller.py`
- `llm_router/router.py`
- `tests/`

## 这份文件保留的最小结论

截至 2026-03-24，这几个判断当时成立：

- 仓库已经不是 GRU-only 原型
- `LLMRouter.route()` 已经存在最小 prompt-only 实现
- 仓库已经有多条实验路径，但还没把当前主底座完全确定下来
- 文档的主要问题不是材料太少，而是当前事实、阶段判断和历史记录写在了一起

如果你现在想了解仓库，请不要继续从这份 dated 说明开始读。
