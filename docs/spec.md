# LCDFFC 最小系统规格

## 目的

本项目的第一阶段目标是在 `CityLearn Challenge 2023` 中建立一个可复现的 `forecast-then-control` 闭环，并验证固定权重 `forecast + QP` 是否能够在关键 KPI 上打平或优于 `RBC`。

## 当前闭环

当前真实可执行的数据流如下：

1. `data/prepare_citylearn.py` 从 CityLearn 环境导出时序数据。
2. `scripts/train_gru.py` 训练 GRU 预测器。
3. `eval/run_rbc.py` 运行基线。
4. `eval/run_controller.py` 加载预测模型和 `QPController`，执行滚动控制。
5. `eval/run_all.py` 聚合 KPI 结果。

## 当前阶段边界

当前已进入实现的部分：

- CityLearn 数据提取
- 滑动窗口数据集
- GRU 预测器训练
- 固定权重 QP 控制器
- 零动作回退
- `RBC` 与 `forecast_qp` 评估

当前未闭环的部分：

- `SPO+` 训练
- uncertainty-aware fallback
- 真正可用的 LLM router
- RL baseline
- OOD 评估

## 第一阶段验收

第一阶段验收标准以 `chat.md` 为准，最小化表达如下：

- 场景：`CityLearn Challenge 2023`
- 模式：`central_agent=True`
- 控制对象：battery-only
- 控制框架：fixed-weight `forecast + QP/MPC`
- 结果要求：`cost / carbon / peak` 中至少 2 项打平或优于 `RBC`

## 当前主要阻塞

- 历史保存结果中，`forecast_qp` 仍未稳定优于 `RBC`
- 当前环境可能缺少 `cvxpy`，使 QP 路径无法直接复现
- 文档、配置和代码事实曾发生漂移，需要持续收口

## 当前诊断结论

当前已经补充三种评估模式：

- `learned`
- `oracle`
- `myopic`

最新复现结果表明：

- `learned` 仍明显落后于 `RBC`
- `myopic` 几乎打平 `RBC`
- `oracle` 仍未优于 `RBC`

因此下一轮优先怀疑控制目标、权重设置、特征映射或动作注入，而不是先把问题全部归因于预测误差。
