# LCDFFC 旧最小系统规格（legacy）

这个文件只保留早期阶段的系统规格痕迹，不再作为当前仓库事实源。

当前主阅读路径是：

1. `README.md`
2. `CLAUDE.md`
3. `INSTRUCTION.md`
4. `code/`、`tests/`、`configs/`

## 这个旧规格原来在描述什么

它原来描述的是最早一版 phase-1 目标：

- 在 `CityLearn Challenge 2023` 上先跑通 fixed-weight forecast-then-control
- 先比较 low-level controller 和 baseline
- 先做最小可运行路径，再考虑后续高层模块

## 现在和这份旧规格不一样的地方

下面这些现在都不该再按本文件理解：

- 当前主训练入口不是只看 `scripts/train_gru.py`，而是 `scripts/train_forecaster.py`
- 仓库不是 GRU-only
- `LLMRouter.route()` 不是空接口，它已经有最小 prompt-only 实现
- 当前 repo 事实不能靠这份旧规格判断，要看 `code + tests` 和 `CLAUDE.md`

## 保留这份文件的原因

它仍然有一个用途：说明这个仓库最早是从“先把 CityLearn 第一条可运行路径做出来”开始的。

如果你要看当前实现，不要继续读这份文件，直接去看：

- `README.md`
- `CLAUDE.md`
- `INSTRUCTION.md`
- `models/factory.py`
- `eval/run_controller.py`
- `llm_router/router.py`
