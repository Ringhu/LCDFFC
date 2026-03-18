# LCDFFC: Language-Conditioned Decision-Focused Forecast-Control

## 项目简介

本项目在 **CityLearn Challenge 2023** 场景下，构建一个 **预测-控制（forecast-then-control）** 系统，核心创新点包括：

1. **决策聚焦学习（Decision-Focused Learning）**：使用 SPO+ surrogate loss，让预测模型直接优化下游控制决策质量，而非单纯最小化预测误差。
2. **LLM 偏好路由器**：利用大语言模型（Qwen2.5-7B-Instruct）作为高层策略路由器，根据场景上下文动态调整控制器的目标权重和约束条件。
3. **QP-MPC 控制器**：基于 cvxpy 的二次规划控制器，采用滚动时域（receding horizon）方式，24 步规划、执行第一步。

## 研究框架

```
                    ┌─────────────────────┐
                    │  LLM 偏好路由器       │
                    │  (Qwen2.5-7B)       │
                    └────────┬────────────┘
                             │ weights, constraints
                             ▼
观测数据 ──► GRU 预测器 ──► QP-MPC 控制器 ──► CityLearn 环境
                 ▲                │
                 │    SPO+ loss   │
                 └────────────────┘
```

### 模块划分

| 模块 | 目录 | 职责 |
|------|------|------|
| 数据 | `data/` | CityLearn 数据提取、预处理、DataLoader |
| 预测 | `models/` | 时序预测模型（GRU → TSMixer/PatchTST） |
| 控制 | `controllers/` | QP/MPC 控制器、安全回退策略 |
| 评估 | `eval/` | RBC 基线、端到端评估、KPI 指标 |
| LLM 路由 | `llm_router/` | Prompt 模板、JSON schema、路由逻辑 |

## 技术栈

- **Python 3.10+**
- **CityLearn 2.1+**（`central_agent=True` 模式）
- **PyTorch**：预测模型训练
- **cvxpy + OSQP**：二次规划求解
- **vLLM / transformers**：本地 LLM 推理
- **配置管理**：`configs/*.yaml`

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 准备数据
python data/prepare_citylearn.py

# 3. 训练预测模型（标准 MSE）
python models/gru_forecaster.py --config configs/forecast.yaml

# 4. 运行 RBC 基线
python eval/run_rbc.py

# 5. 运行 forecast-control 系统
python eval/run_controller.py --config configs/controller.yaml
```

## 目录结构

```
LCDFFC/
├── CLAUDE.md                 # Claude Code 项目规范（英文）
├── README.md                 # 本文件
├── INSTRUCTION.md            # 详细实验指南（中文）
├── requirements.txt
├── configs/                  # 配置文件
├── data/                     # 数据模块
├── models/                   # 预测模块
├── controllers/              # 控制模块
├── eval/                     # 评估模块
├── llm_router/               # LLM 路由模块
├── scripts/                  # 辅助脚本
├── tests/                    # 测试
├── docs/agent_prompts/       # Sub-agent 提示词
├── reports/                  # 实验报告
└── artifacts/                # 模型权重、中间产物
```

## 目标会议

CCF-A 级会议（NeurIPS / ICML / AAAI）

## 许可证

研究用途，暂未公开发布。
