# Auto Review Note: Round 2 Forecast Baseline（2026-03-20）

## 当前问题

用户的质疑里，最基础也最有杀伤力的一条是：

> 当前高层路由的所有结论，会不会只是建立在一个过弱的 `GRU` backbone 上？

如果这个问题不先回答，那么：

- 冻结低层系统的合理性站不住
- 高层路由的增益也站不住
- 当前 tiny margin 更容易被解释成“低层太弱，导致上层比较没有意义”

## 候选实验方向

### 方案 A：先补 stronger forecast baseline

- 目标：验证 `GRU` 是否是当前系统瓶颈
- 方式：新增一个实现成本低、但比 `GRU` 更现代的时序 baseline
- 候选：`TSMixer`

优点：
- 实现成本低
- 与当前数据形态兼容
- 不依赖外部大模型权重
- 足以回答“GRU-only 是否太弱”

缺点：
- 不能一步回答 foundation model 问题

### 方案 B：直接上 PatchTST

优点：
- 学术上更强
- reviewer 更熟悉

缺点：
- 实现和调参成本更高
- 当前一轮内风险更大

### 方案 C：直接上 Chronos / TimesFM / MOMENT

优点：
- 最能回应 foundation model 质疑

缺点：
- 依赖和推理路径更重
- 一轮内容易被工程问题拖住
- 会把“下游控制变化”与“外部预训练模型使用”纠缠在一起

## Review 决策

本轮选择 **方案 A：先补 `TSMixer`**。

理由：

1. 它足够强，可以作为 `GRU` 的第一组 stronger baseline
2. 它足够轻，能快速融入当前训练和评估链路
3. 如果连 `TSMixer` 都无法显著改变当前结论，那么就更有理由下一轮再去决定是否真的需要 foundation model

## 本轮实验包

### 实验 1：forecasting baseline

比较：
- `GRU`
- `TSMixer`

指标：
- test MSE
- test MAE

### 实验 2：下游控制 baseline

比较：
- `GRU + QP`
- `TSMixer + QP`
- `RBC`

指标：
- `cost`
- `carbon`
- `peak`

### 实验 3：高层路由稳定性检查（最小版）

比较：
- `fixed_reserve` + stronger backbone
- `text_v4` + stronger backbone

目标：
- 看 stronger backbone 是否改变高层结论方向

## GPU 约束

- 小测试：`GPU 3`
- 完整训练：`GPU 2`

## 成功标准

如果 `TSMixer` 相比 `GRU`：

- 预测明显更好
- 或者下游控制明显更好

那么当前论文必须补 stronger low-level baseline。

如果 `TSMixer` 没有显著改变结果，则说明：

- 当前高层问题不太可能只是 `GRU` 太弱导致的假象
- 下一轮才更值得去升级 protocol 或真实 LLM router
