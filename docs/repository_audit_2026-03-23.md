# 仓库审计（dated reference, 2026-03-23）

这个文件只保留 2026-03-23 当天的一次审计结论，用来解释为什么后面整理了文档结构。

它不再定义当前仓库的文档优先级，也不再承担当前实现说明角色。

当前主阅读路径是：

1. `README.md`
2. `CLAUDE.md`
3. `INSTRUCTION.md`
4. `code/`、`tests/`、`configs/`

当前事实优先级是：

1. `code + tests`
2. `CLAUDE.md`
3. `README.md`
4. `INSTRUCTION.md`
5. dated docs / `refine-logs/` / older specs

## 这份 dated audit 还保留什么价值

它现在主要保留两类信息：

- 2026-03-23 当天发现过哪些文档问题
- 为什么后面要把 live docs 压成 `README.md -> CLAUDE.md -> INSTRUCTION.md -> code/tests/configs`

## 当时发现过的核心问题

当时最重要的几个问题是：

1. `AGENTS.md` 和其他主文档在 authority 上冲突
2. 一些旧文档还把 `scripts/train_gru.py` 写成主训练入口
3. 一些旧文档还把 `LLMRouter.route()` 写成未实现
4. `README.md`、`INSTRUCTION.md`、dated review docs 混入了不同层级的信息
5. 历史判断和当前工程事实没有分开

## 不要再用它判断什么

不要再用这份 dated audit 判断：

- 当前主训练入口
- 当前主评估 runner
- 当前哪些模块算 core supported path
- 当前哪些结论已经能写成稳定事实
- 当前哪个文档优先级最高

这些问题现在请直接看：

- `CLAUDE.md`
- `README.md`
- `INSTRUCTION.md`
- `code/`、`tests/`、`configs/`

## 保留这份文件的原因

保留它，是为了让后续读者知道：仓库文档曾经出现过角色混写和旧事实残留，后面的整理不是随意改写，而是为了解决这些具体问题。
