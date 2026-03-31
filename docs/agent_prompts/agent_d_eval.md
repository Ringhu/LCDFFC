# Agent D: 评估模块

## 角色

你负责 `eval/` 模块。**不要修改** data, models, controllers, llm_router 目录下的任何文件。

## 负责文件

- `eval/__init__.py`
- `eval/run_zero_action.py`
- `eval/run_controller.py`
- `eval/run_all.py`
- `eval/metrics.py`
- `configs/eval.yaml`

## 目标

1. **实现 `run_zero_action.py`**：
   - 使用 zero-action battery baseline 跑完整 episode
   - 记录每步的 observation、action、reward
   - 计算并保存 KPI（cost, carbon, peak, ramping）

2. **实现 `run_controller.py`**：
   - 加载训练好的预测模型（从 `artifacts/checkpoints/`）
   - 加载 QP 控制器配置（从 `configs/controller.yaml`）
   - 跑完整 CityLearn episode：
     ```
     每步: obs → forecaster.predict() → controller.act() → env.step()
     ```
   - 记录 KPI、存储轨迹

3. **实现 `run_all.py`**：
   - 串联所有 baseline 和方法
   - 生成对比表（CSV + 打印）
   - 生成 KPI 对比图（bar chart）
   - 保存到 `reports/`

4. **完善 `metrics.py`**：
   - 已有基本 KPI 计算函数
   - 添加 CityLearn 官方评估指标（如有）
   - 支持 per-building 和 aggregate 指标

## CityLearn 评估循环

```python
from citylearn.citylearn import CityLearnEnv

env = CityLearnEnv(schema=schema_path, central_agent=True)
obs = env.reset()

done = False
while not done:
    # 用 forecaster 和 controller 生成 action
    action = ...  # list of lists for central_agent
    obs, reward, done, info = env.step(action)

# 评估
kpis = compute_all_kpis(...)
```

## 报告格式

```
reports/
├── zero_action_kpis.json
├── forecast_qp_kpis.json
├── comparison_table.csv
└── comparison_plot.png
```

## 止损点

- CityLearn env 跑不通 → 检查 schema 路径和版本兼容性
- KPI 计算有歧义 → 参考 CityLearn 官方评估代码
