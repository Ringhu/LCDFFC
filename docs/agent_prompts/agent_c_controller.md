# Agent C: 控制器模块

## 角色

你负责 `controllers/` 模块。**不要修改** data, models, eval, llm_router 目录下的任何文件。

## 负责文件

- `controllers/__init__.py`
- `controllers/qp_controller.py`
- `controllers/safe_fallback.py`
- `configs/controller.yaml`

## 目标

1. **实现 `qp_controller.py` 的 `act()` 方法**：
   - 只控制 battery charge/discharge（第一版）
   - 目标函数：
     - `w_cost * Σ(price[t] * net_load[t])`：电费
     - `w_carbon * Σ(carbon[t] * net_load[t])`：碳排放
     - `w_peak * max(net_load)`：峰值（用二次近似）
     - `w_smooth * Σ(action[t] - action[t-1])²`：动作平滑
   - 约束：
     - SOC bounds: `soc_min <= soc[t] <= soc_max`
     - Charge/discharge rate: `-p_max <= action[t] <= p_max`
     - 可选 reserve constraint: `soc[T] >= reserve_soc`

2. **Receding horizon MPC**：
   - 规划 24 步，只执行第一个动作
   - 每步重新求解，使用最新 SOC 和预测

3. **实现 `safe_fallback.py`**：
   - 保守回退策略（零动作 or 简单规则）
   - 当 QP 不可行时自动触发
   - 当 forecast 置信度低时可手动触发

4. **数值稳定性**：
   - 使用 OSQP 后端，支持 warm-start
   - 处理求解失败的情况（返回 fallback）
   - 为 SPO+ 预留 cost perturbation 接口

## 接口约定

```python
from controllers import QPController, SafeFallback

ctrl = QPController(horizon=24, battery_capacity=6.4, soc_min=0.0, soc_max=1.0, p_max=1.0)
action = ctrl.act(
    state={"soc": 0.5},
    forecast=np.zeros((24, 3)),  # (horizon, num_features)
    weights={"cost": 0.4, "carbon": 0.2, "peak": 0.3, "smooth": 0.1},
    constraints={"reserve_soc": 0.2}
)
# action: np.ndarray, shape depends on num_buildings

fb = SafeFallback()
safe_action = fb.act(state={"soc": [0.5]})
```

## SPO+ 预留接口

```python
# Sprint 3 时需要的接口
def solve_with_perturbed_cost(self, cost_vector: np.ndarray, ...) -> np.ndarray:
    """用 perturbed cost 向量求解 QP，返回最优解。"""
    # SPO+ 需要: z*(2*c_hat - c_true)
```

## 止损点

- cvxpy 求解不稳定 → 放松约束、增大正则项、检查问题凸性
- QP 不如 zero-action 或显式 rule-based baseline → 调整权重、检查预测质量
