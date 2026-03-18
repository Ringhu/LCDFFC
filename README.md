# LCDFFC: Language-Conditioned Decision-Focused Forecast-Control

## 项目简介

本项目面向 **CityLearn Challenge 2023**，目标是实现一个最小可行的 **forecast-then-control** 闭环系统：

1. 用历史观测训练 GRU 预测器。
2. 用固定权重 QP 控制器生成电池动作。
3. 在 `central_agent=True`、battery-only 设定下与 `RBC` 基线对比。

当前仓库的工作重点是先完成第一阶段验收：让固定权重 `forecast + QP` 至少在 `cost / carbon / peak` 中 2 项打平或优于 `RBC`。  
`SPO+`、uncertainty-aware fallback 和 LLM router 仍属于后续阶段，其中部分目录目前只有骨架或接口预留。

## 当前实现范围

已可用：

- `data/prepare_citylearn.py`：从 CityLearn 提取原始时序并生成 `forecast_data.npz`
- `data/dataset.py`：滑动窗口数据集与标准化统计
- `scripts/train_gru.py`：GRU 训练入口
- `controllers/qp_controller.py`：固定权重 QP 控制器
- `controllers/safe_fallback.py`：零动作回退
- `eval/run_rbc.py`：基线评估
- `eval/run_controller.py`：forecast + QP 端到端评估
- `eval/run_all.py`：结果聚合
- `eval/run_controller.py --forecast_mode {learned,oracle,myopic}`：第一阶段诊断模式

未闭环或未实现：

- `SPO+` 训练路径
- uncertainty ensemble 与 uncertainty-aware gating
- 真正可用的 `LLMRouter.route()`
- deterministic LLM fallback
- RL baseline 与 OOD 评估

## 当前研究框架

第一阶段当前真实闭环：

```text
CityLearn observation -> GRU forecaster -> QP controller -> CityLearn env
```

完整研究路线仍然是：

```text
forecast + QP -> uncertainty-aware fallback -> decision-focused learning -> LLM router
```

其中 LLM 的角色被限定为高层偏好/约束路由器，不直接输出底层连续动作。

## 技术栈

- Python 3.10+
- CityLearn 2.1+（`central_agent=True`）
- PyTorch
- cvxpy + OSQP
- YAML 配置（`configs/*.yaml`）

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 从 CityLearn 提取数据
python data/prepare_citylearn.py \
  --schema citylearn_challenge_2023_phase_1 \
  --output_dir artifacts/

# 3. 训练 GRU 预测器
python scripts/train_gru.py \
  --config configs/forecast.yaml \
  --data_path artifacts/forecast_data.npz \
  --device cpu

# 4. 运行基线
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
  --schema /cluster/home/user1/.cache/citylearn/v2.5.0/datasets/citylearn_challenge_2023_phase_1/schema.json \
  --forecast_config configs/forecast.yaml \
  --controller_config configs/controller.yaml \
  --output_dir reports/ \
  --tag oracle_qp \
  --forecast_mode oracle \
  --oracle_data artifacts/forecast_data.npz \
  --device cpu
```

## 目录结构

```text
LCDFFC/
├── AGENTS.md                 # 主工作约定文档
├── CLAUDE.md                 # 工程结构与接口约定
├── INSTRUCTION.md            # Sprint 与实验推进文档
├── README.md                 # 对外概览与运行入口
├── configs/                  # 配置文件
├── controllers/              # QP 控制器与回退策略
├── data/                     # 数据提取与数据集
├── docs/                     # 规格说明、汇报和辅助文档
├── eval/                     # 基线、端到端评估、结果聚合
├── llm_router/               # Prompt、schema、router 骨架
├── models/                   # 预测模型
├── scripts/                  # 训练与辅助脚本
├── tests/                    # 测试
├── reports/                  # 评估输出，默认不入库
└── artifacts/                # 数据与权重产物，默认不入库
```

## 当前已知问题

- 现有保存结果里，`forecast_qp` 仍未稳定优于 `RBC`
- 当前新增诊断结果显示：`myopic` 几乎打平 `RBC`，但 `oracle` 仍未优于 `RBC`
- 当前环境可能缺少 `cvxpy`，导致 `tests/test_qp.py` 无法直接运行
- 文档和代码曾发生过漂移，当前以 `AGENTS.md` 为主工作约定

## 许可证

仓库已公开，但当前尚未添加正式 `LICENSE` 文件。
