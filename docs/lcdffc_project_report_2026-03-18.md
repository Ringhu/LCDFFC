# LCDFFC 项目汇报（dated report, 2026-03-18）

这个文件只保留 2026-03-18 当天的一次阶段汇报，不再承担当前仓库事实源角色。

当前主阅读路径是：

1. `README.md`
2. `CLAUDE.md`
3. `INSTRUCTION.md`
4. `code/`、`tests/`、`configs/`

如果文档和代码不一致，以 `code + tests` 为准。

## 这份 dated report 还保留什么价值

它现在主要保留两类信息：

- 项目在 2026-03-18 当天是怎么分阶段描述的
- 当时的 broad research framing 是什么

## 不要再用它判断什么

不要再用这个文件判断：

- 当前主训练脚本
- 当前 backbone 范围
- 当前是否 still GRU-only
- 当前 baseline 结论
- 当前哪些能力已经完成

这些问题现在请直接看：

- `README.md`
- `CLAUDE.md`
- `INSTRUCTION.md`
- `models/factory.py`
- `eval/run_controller.py`
- `llm_router/router.py`
- `tests/`

## 保留它的原因

保留它，是为了记录仓库较早阶段是如何描述研究目标和阶段划分的。它现在只算历史材料，不算 live docs。
