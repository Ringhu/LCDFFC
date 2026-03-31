# Auto Review Note: PatchTST Baseline（2026-03-20）

## 当前问题

上一轮虽然已经补了 `TSMixer`，但它没有优于 `GRU`。这只能说明“第一个 stronger baseline 没赢”，还不能回答用户关于 `PatchTST` / `former` 类 forecasting baseline 的质疑。

## 候选做法

### 方案 A：自写一个近似 `PatchTST`

优点：
- 接口最容易和当前训练脚本对齐

缺点：
- reviewer 会质疑实现是否真的等价于 `PatchTST`
- 容易在实现细节上浪费时间

### 方案 B：直接接 `transformers` 内置 `PatchTST`

优点：
- 更接近标准实现
- 可信度更高
- 当前环境已经具备 `transformers` + `PatchTSTForPrediction`

缺点：
- 需要额外做一层 wrapper，把当前 7 维历史特征接到 3 维预测目标上

## Review 决策

选择 **方案 B**。

具体实现方式：

- 新增 `PatchTSTForecaster`
- 使用一个轻量输入投影，把当前 7 维历史特征映射到 3 维 target history
- 用 `transformers.PatchTSTForPrediction` 做多步预测
- 保持训练脚本、控制入口和现有 `GRU / TSMixer` 兼容

## 为什么这个设计合理

- 当前项目真正关心的是“更强 forecasting backbone 是否改变结论”，而不是严格复刻某篇论文的所有训练细节。
- 输入投影允许 `PatchTST` 仍然使用完整的 7 维上下文，而不是被迫只看 target history。
- 和手写近似版相比，这个实现更容易被接受为可信 baseline。

## 实验包

### 实验 1：GPU 3 sanity

- 短程训练 `PatchTST`
- 检查：loss 是否下降、checkpoint 是否正常保存、下游入口是否能加载

### 实验 2：GPU 2 完整训练

比较：
- `GRU`
- `TSMixer`
- `PatchTST`

指标：
- `overall_mse`
- `overall_mae`

### 实验 3：下游控制比较

比较：
- `GRU + QP`
- `TSMixer + QP`
- `PatchTST + QP`

指标：
- `cost`
- `carbon`
- `peak`
- `ramping`

## 成功标准

若 `PatchTST` 明显优于 `GRU`：
- 当前低层 backbone 结论必须更新
- 后续高层实验应至少保留 `PatchTST` 主线

若 `PatchTST` 与 `GRU` 接近或更差：
- “当前结论只是因为 `GRU` 太弱”这个质疑会进一步被削弱
- 但 stronger baseline 检查仍可继续保留为论文必要部分
