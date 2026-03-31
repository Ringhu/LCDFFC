# Agent A: 数据模块

## 角色

你负责 `data/` 模块。**不要修改** models, controllers, eval, llm_router 目录下的任何文件。

## 负责文件

- `data/__init__.py`
- `data/prepare_citylearn.py`
- `data/dataset.py`
- `configs/data.yaml`

## 目标

1. **实现 `prepare_citylearn.py`**：
   - 从 CityLearn Challenge 2023 Phase 1 的 schema.json 加载环境
   - 运行一个 episode（使用 zero-action 或默认 building behavior），记录所有观测数据
   - 提取关键特征：non_shiftable_load, solar_generation, electricity_pricing, carbon_intensity, outdoor_dry_bulb_temperature, hour, day_type
   - 保存为 CSV 和 NPZ 格式到 `artifacts/`
   - 输出 `artifacts/data_summary.json`，包含特征维度、时间范围、基本统计

2. **实现 `dataset.py`**：
   - CityLearnDataset 已有骨架，确保滑动窗口逻辑正确
   - 添加数据标准化（z-score），保存 mean/std 到 artifacts
   - 支持 train/val/test 划分
   - 返回 `(history, future_target)` 对

3. **数据验证**：
   - 检查缺失值、异常值
   - 确保时间连续性
   - 输出数据质量报告

## 接口约定

```python
# 其他模块通过这个接口使用数据
from data import CityLearnDataset

dataset = CityLearnDataset(data, history_len=24, horizon=24, target_cols=[0, 1, 2])
history, target = dataset[0]
# history: (24, num_features), target: (24, num_targets)
```

## CityLearn 参考

```python
from citylearn.citylearn import CityLearnEnv

env = CityLearnEnv(schema="path/to/schema.json", central_agent=True)
obs = env.reset()
# obs 是一个 list of lists（central_agent 模式下只有一个元素）
```

## 止损点

- 如果 CityLearn 安装或 schema 加载卡住超过 2 小时 → 改用手动 CSV 导出
- 确保输出格式固定，下游模块可以直接用
