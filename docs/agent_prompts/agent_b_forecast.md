# Agent B: 预测模块

## 角色

你负责 `models/` 模块。**不要修改** data, controllers, eval, llm_router 目录下的任何文件。

## 负责文件

- `models/__init__.py`
- `models/base_forecaster.py`
- `models/gru_forecaster.py`
- `configs/forecast.yaml`

## 目标

### Sprint 1: 标准 GRU 预测

1. **完善 `gru_forecaster.py`**：
   - GRU encoder + linear decoder 已有骨架
   - 添加完整的训练脚本（`if __name__ == "__main__"` 块）
   - 支持从 `configs/forecast.yaml` 加载配置
   - 实现 early stopping、学习率调度
   - 保存最优模型到 `artifacts/checkpoints/`
   - 输出训练/验证 loss 曲线到 `reports/`

2. **训练流程**：
   ```python
   # 加载数据
   from data import CityLearnDataset
   dataset = CityLearnDataset(data, history_len=24, horizon=24, target_cols=[0,1,2])

   # 训练
   model = GRUForecaster(input_dim=7, hidden_dim=64, output_dim=3, horizon=24)
   # MSE loss, Adam optimizer, early stopping
   ```

3. **评估指标**：
   - 报告 MSE, MAE, MAPE（per target column）
   - 保存预测 vs 真实值的可视化

### Sprint 3: SPO+ Loss（后续）

4. **添加 SPO+ loss**：
   - 在 `models/` 下新增 `spo_loss.py`
   - SPO+ surrogate: `max(0, (2*c_hat - c_true)^T * z_star(c_hat))` 的近似
   - 需要调用 controller 的 QP 求解作为 oracle
   - 对比 MSE-only vs SPO+ 的下游性能

## 接口约定

```python
from models import GRUForecaster

model = GRUForecaster(input_dim=7, hidden_dim=64, output_dim=3, horizon=24)
# 训练
result = model.train_step((history_batch, target_batch), loss_fn=nn.MSELoss())
# 推理
predictions = model.predict(history_batch, horizon=24)  # (batch, 24, 3)
```

## 止损点

- GRU 训练 loss 不下降 → 检查数据标准化、学习率（试 1e-4 到 1e-2）
- 预测质量差 → 增加 hidden_dim 或 num_layers，检查数据质量
