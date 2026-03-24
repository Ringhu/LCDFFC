# LCDFFC 与 CityLearn 解释（dated reference, 2026-03-19）

这个文件只保留 2026-03-19 当天对项目背景和 CityLearn 场景的一次解释，不再承担当前仓库事实源角色。

当前主阅读路径是：

1. `README.md`
2. `CLAUDE.md`
3. `INSTRUCTION.md`
4. `code/`、`tests/`、`configs/`

如果文档和代码不一致，以 `code + tests` 为准。

## 这份 dated 说明还能回答什么

它现在只适合回答：

- 当时为什么把 CityLearn 当作主实验环境
- 当时为什么强调 battery-only、centralized forecast-then-control 的理解方式
- 当时项目最初是如何向新读者解释的

## 不要再用它判断什么

不要再用这个文件判断：

- 当前主闭环是否仍然是 GRU-only
- 当前基线和 KPI 结论
- 当前主训练脚本
- 当前是否已经完成某个扩展方向

这些问题现在请直接看：

- `README.md`
- `CLAUDE.md`
- `INSTRUCTION.md`
- `data/prepare_citylearn.py`
- `scripts/train_forecaster.py`
- `models/factory.py`
- `eval/run_controller.py`

## 保留它的原因

保留它，是因为它还能帮助读者理解：项目最早是怎么把 CityLearn、预测和控制关系讲清楚的。但它不再是当前实现说明。
