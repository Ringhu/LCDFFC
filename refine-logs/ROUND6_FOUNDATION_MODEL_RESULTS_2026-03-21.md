# Round 6 结果：Moirai / Chronos-2 / TimesFM 2.5 / MOMENT（2026-03-21）

## 1. 本轮目标

这轮直接回应用户的新要求：

- 尝试 `Moirai`、`Chronos-2`、`TimesFM 2.5`、`MOMENT`
- 先做 reviewed feasibility 设计
- 查官方资料与官方推荐用法
- 下载模型权重并实际跑出结果

对应的 reviewed design 是：

- `refine-logs/auto-review/2026-03-21-round6-foundation-model-review.md`

## 2. 本轮实际采用的方法

为了避免四个 foundation model 的训练范式差异把变量重新缠在一起，本轮统一采用：

> **官方推荐的最小可运行 inference / zero-shot forecasting 路线**

然后分两层评测：

1. rolling forecast metric
2. `foundation forecast + QP` 下游控制

## 3. 官方使用路径与落地情况

### 3.1 Chronos-2

- 官方包：`chronos-forecasting`
- 官方模型：`amazon/chronos-2`
- 本轮使用：`Chronos2Pipeline.from_pretrained(...) + predict(...)`
- 状态：已跑通

### 3.2 Moirai

- 官方包：`uni2ts`
- 官方模型：`Salesforce/moirai-2.0-R-small`
- 本轮使用：`Moirai2Module.from_pretrained(...) + Moirai2Forecast(...)`
- 状态：已跑通
- 说明：本轮实际用的是 `Moirai2` 路线，不是旧版 `Moirai v1`

### 3.3 TimesFM 2.5

- 官方包：`timesfm`
- 官方 HF 模型：`google/timesfm-2.5-200m-transformers`
- 本轮使用：先按官方文档升级到 source-based `transformers`，再使用 `TimesFm2_5ModelForPrediction`
- 状态：已跑通
- 说明：稳定版 `transformers` 不暴露 2.5 专用类，必须切到官方文档要求的源码版路径

### 3.4 MOMENT

- 官方包：`momentfm`
- 官方模型：`AutonLab/MOMENT-1-small`
- 本轮使用：`MOMENTPipeline.from_pretrained(..., task_name='forecasting') + forecast(...)`
- 状态：已跑通
- 重要 caveat：官方会直接警告 “Only reconstruction head is pre-trained. forecasting head must be fine-tuned.”

因此，`MOMENT` 本轮结果应解释为：

> 按官方最小 forecasting 路线可运行，但不是一个已经为 zero-shot forecasting 充分准备好的强基线。

## 4. Rolling forecast 结果

评测设置：

- 数据：`artifacts/forecast_data.npz`
- test 起点：`612`
- horizon：`24`
- context_length：`512`
- 目标通道：price / non_shiftable_load / solar

### 4.1 总表

| Model | overall_mse | overall_mae | avg_call_sec |
|---|---:|---:|---:|
| Moirai2 | 0.1457 | 0.0777 | 0.0358 |
| TimesFM 2.5 | 0.1476 | 0.0815 | 0.0585 |
| Chronos-2 | 0.2428 | 0.2583 | 0.0298 |
| MOMENT | 0.2520 | 0.2644 | 0.0127 |

### 4.2 分项表现

#### Moirai2

- price: `mse 7.61e-07`, `mae 4.71e-04`
- load: `mse 0.4352`, `mae 0.2050`
- solar: `mse 0.0020`, `mae 0.0275`

#### TimesFM 2.5

- price: `mse 1.95e-07`, `mae 2.75e-04`
- load: `mse 0.4386`, `mae 0.2064`
- solar: `mse 0.0043`, `mae 0.0378`

#### Chronos-2

- price: `mse 8.96e-05`, `mae 0.00546`
- load: `mse 0.4521`, `mae 0.2985`
- solar: `mse 0.2763`, `mae 0.4710`

#### MOMENT

- price: `mse 9.37e-05`, `mae 0.00559`
- load: `mse 0.4644`, `mae 0.3142`
- solar: `mse 0.2917`, `mae 0.4734`

## 5. Rolling forecast 结论

当前这四个 foundation family，在本轮统一 zero-shot 评测下的排序很清楚：

1. `Moirai2`
2. `TimesFM 2.5`
3. `Chronos-2`
4. `MOMENT`

其中：

- `Moirai2` 和 `TimesFM 2.5` 明显领先
- `Chronos-2` 次之
- `MOMENT` 最弱，而且其官方 warning 说明这条 zero-shot forecasting 路线本身就不强

## 6. 下游控制结果

固定控制设置：

- controller：`QP`
- 权重：`cost 0.15 / carbon 0.10 / peak 0.65 / smooth 0.10`
- reserve_soc：`0.2`
- horizon：`24`
- context_length：`512`

### 6.1 总表

| Model | cost | carbon | peak | ramping |
|---|---:|---:|---:|---:|
| Moirai2 + QP | 29.2140 | 447.0601 | 15.1225 | 791.7540 |
| TimesFM 2.5 + QP | 29.4396 | 449.6589 | 15.3452 | 809.6941 |
| Chronos-2 + QP | 31.5445 | 477.9899 | 16.4417 | 856.3563 |
| MOMENT + QP | 31.5444 | 477.9883 | 16.4417 | 856.3507 |

### 6.2 对比当前 strongest non-foundation baseline

Round 4 里当前 strongest low-level backbone 是：

- `Granite + QP`
- cost `31.6027`
- carbon `480.3075`
- peak `14.5422`
- ramping `827.7849`

对比后可以看到：

- `Moirai2 + QP` 和 `TimesFM 2.5 + QP` 在 `cost / carbon / ramping` 上明显优于 `Granite + QP`
- 但它们在 `peak` 上仍弱于 `Granite + QP`
- `Chronos-2 + QP` 和 `MOMENT + QP` 整体不如 `Granite + QP`

## 7. 本轮最关键的结论

### 7.1 foundation model 里最强的不是 Chronos-2，而是 Moirai2

这是本轮最直接的新事实：

> 在当前项目和当前 zero-shot 设定下，`Moirai2` 是四个 foundation family 里最强的一个，`TimesFM 2.5` 紧随其后。

### 7.2 TimesFM 2.5 不是“不能用”，而是环境要求更苛刻

- 稳定版 `transformers` 不够
- 官方 HF 文档要求 source version
- 切到 source version 后，`TimesFm2_5ModelForPrediction` 才真正可用

所以 `TimesFM 2.5` 的使用门槛高于其他几项，但它的结果是值得的。

### 7.3 MOMENT 当前不适合作为强 zero-shot baseline

不是因为它完全跑不通，而是因为：

- 官方就提示 forecasting head 未预训练
- 在当前 zero-shot 路线下，它的结果也确实最弱

所以当前最合理的表述是：

> `MOMENT` 已被成功接入并跑通，但其 zero-shot forecasting 路线在当前项目里不具备竞争力。

## 8. 对你问题的直接回答

你问“其他 time-series foundation model 结果是什么样的”，按本轮实际结果，直接回答就是：

- **Moirai2**：四者里最好，rolling forecast 第一，下游控制也第一。
- **TimesFM 2.5**：四者里第二强，rolling forecast 非常接近 Moirai2，下游控制也明显优于 `Chronos-2 / MOMENT`。
- **Chronos-2**：能跑通，但无论 forecast 还是 control 都弱于 `Moirai2 / TimesFM 2.5`。
- **MOMENT**：能跑通，但官方 zero-shot forecasting 路线本身就不强，在当前项目里结果最弱。

## 9. 这对后续研究意味着什么

现在 low-level backbone 的 strongest 候选已经变成两条：

1. `Granite + QP`
   - 更强的 `peak` 控制
2. `Moirai2 + QP`
   - 更强的 `cost / carbon / ramping`

这意味着下一步最合理的问题不再是“还有没有更多 foundation model 没试”，而是：

> 是不是应该进入 `controller baseline + objective trade-off` 这一轮，专门分析为什么不同 backbone 会把 `peak` 和 `cost/carbon` 的平衡点推向不同方向。
