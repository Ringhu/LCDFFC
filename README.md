# LCDFFC: Language-Conditioned Decision-Focused Forecast-Control

## 项目简介

这个仓库在 `CityLearn Challenge 2023` 上做 forecast-then-control。当前最稳的主路径是：预测 backbone 或诊断 forecast mode -> QP controller -> CityLearn env。

当前阶段更适合写成：

> post-prototype, pre-consolidation research platform

## 先看哪里

按这个顺序读：

1. `README.md`：先看项目是什么、怎么跑
2. `CLAUDE.md`：再看稳定工程约定和能力边界
3. `INSTRUCTION.md`：再看现在先做什么
4. `code/`、`tests/`、`configs/`：最后看实现细节

如果文档和代码不一致，以 `code + tests` 为准。文档优先级完整顺序在 `CLAUDE.md`。

## 当前实现范围

### Core supported path

这些是当前主路径：

- `data/prepare_citylearn.py`：提取 CityLearn 时序并生成训练数据
- `data/dataset.py`：滑动窗口数据集和标准化统计
- `scripts/train_forecaster.py`：统一 forecasting 训练入口
- `models/factory.py`：统一 forecaster 构建入口
- `controllers/qp_controller.py`：主 QP battery controller
- `controllers/safe_fallback.py`：当前零动作回退
- `eval/run_controller.py`：forecast + control 主评估入口
- `eval/run_controller.py --forecast_mode {learned,oracle,myopic}`：诊断模式

### Supported experimental path

这些已经在代码里，但更适合写成实验路径：

- 多 backbone forecasting：`gru / tsmixer / patchtst / transformer / granite_patchtst`
- `llm_router/router.py`：最小 prompt-only `LLMRouter.route()`
- `llm_router/preference_routers.py`：规则 / 文本 preference router
- `eval/run_preference_shift.py`：preference-shift / event-driven 实验
- `eval/run_foundation_control.py`：foundation forecast + control
- `eval/run_foundation_controller_compare.py`：controller family 对比
- `controllers/baseline_controllers.py`：非 QP baseline controller

### 当前还不能写成完成

- 完整 `SPO+` / decision-focused end-to-end 训练
- uncertainty-aware ensemble / gating 完整路径
- production-ready 或 agentic LLM router
- 出错时退回固定规则的完整 router 路径
- RL baseline
- 完整 OOD 评估

## 当前主可运行路径

```text
CityLearn observation
  -> centralized history/features
  -> forecasting backbone or diagnostic forecast mode
  -> controller
  -> CityLearn env
```

`eval/run_rbc.py` 当前应理解为 zero-action / default-building-behavior baseline runner，不是仓库里单独实现的一套 RBC policy。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 提取 CityLearn 数据
python data/prepare_citylearn.py \
  --schema citylearn_challenge_2023_phase_1 \
  --output_dir artifacts/

# 3. 训练 forecasting backbone
python scripts/train_forecaster.py \
  --config configs/forecast.yaml \
  --data_path artifacts/forecast_data.npz \
  --device cpu

# 4. 运行 zero-action baseline
python eval/run_rbc.py \
  --schema citylearn_challenge_2023_phase_1 \
  --output_dir reports/

# 5. 运行 forecast + QP
python eval/run_controller.py \
  --schema citylearn_challenge_2023_phase_1 \
  --checkpoint artifacts/checkpoints/gru_mse_best.pt \
  --norm_stats artifacts/norm_stats.npz \
  --forecast_config configs/forecast.yaml \
  --controller_config configs/controller.yaml \
  --output_dir reports/ \
  --tag forecast_qp

# 6. 运行诊断模式
python eval/run_controller.py \
  --schema citylearn_challenge_2023_phase_1 \
  --forecast_config configs/forecast.yaml \
  --controller_config configs/controller.yaml \
  --output_dir reports/ \
  --tag oracle_qp \
  --forecast_mode oracle \
  --oracle_data artifacts/forecast_data.npz \
  --device cpu
```

更多实验入口见：

- `eval/run_preference_shift.py`
- `eval/run_foundation_control.py`
- `eval/run_foundation_controller_compare.py`

## 推荐先读的代码和测试

配置：

- `configs/data.yaml`
- `configs/forecast.yaml`
- `configs/controller.yaml`
- `configs/eval.yaml`
- `configs/llm_router.yaml`

测试：

- `tests/test_smoke.py`
- `tests/test_forecaster_factory.py`
- `tests/test_run_controller_modes.py`
- `tests/test_qp.py`
- `tests/test_llm_router.py`
- `tests/test_controller_baselines.py`
- `tests/test_preference_shift.py`

## 目录结构

```text
LCDFFC/
├── README.md
├── CLAUDE.md
├── INSTRUCTION.md
├── AGENTS.md
├── configs/
├── data/
├── models/
├── controllers/
├── eval/
├── llm_router/
├── scripts/
├── tests/
├── docs/
├── refine-logs/
├── artifacts/
└── reports/
```

## 文档边界

- `README.md`：对外概览和入口命令
- `CLAUDE.md`：稳定工程约定和事实优先级
- `INSTRUCTION.md`：当前执行顺序
- `docs/`：参考说明和 dated 分析
- `refine-logs/`：历史实验日志和 review 记录
