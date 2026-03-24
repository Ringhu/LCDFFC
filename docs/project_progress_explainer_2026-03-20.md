# LCDFFC 进度解释（dated, archive, 2026-03-20）

这个文件只保留 2026-03-20 当天的一次阶段解释，不再承担当前仓库事实源角色。

当前主阅读路径是：

1. `README.md`
2. `CLAUDE.md`
3. `INSTRUCTION.md`
4. `code/`、`tests/`、`configs/`

如果文档和代码不一致，以 `code + tests` 为准。完整事实优先级看 `CLAUDE.md`。

## 这份 dated 说明还能回答什么

它现在只适合回答：

- 2026-03-20 当天是怎么向新读者解释项目背景的
- 当时为什么把问题写成 forecasting + control + 高层语言路由
- 当时项目理解里哪些部分还偏早期

## 不要再用它判断什么

不要再用这个文件判断：

- 当前主训练入口
- 当前主评估协议
- 当前哪些模块算 core supported path
- 当前基线是否已经稳定超过或打平
- 当前高层 router 的成熟度

这些问题现在请直接看：

- `README.md`
- `CLAUDE.md`
- `INSTRUCTION.md`
- `models/factory.py`
- `eval/run_controller.py`
- `llm_router/router.py`
- `tests/`

## 保留它的原因

保留它，是为了让后续读者知道：仓库早期有一批“从 0 开始解释项目”的材料。这些材料对理解当时的研究说法有用，但不该继续冒充当前工程说明。
