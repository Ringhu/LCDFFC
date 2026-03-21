# Auto Review Note: Round 6 Foundation Models（2026-03-21）

## 1. 用户要求

本轮用户明确要求：

- 尝试 `Moirai`、`Chronos-2`、`TimesFM 2.5`、`MOMENT`
- 先 review，再查官方资料，再下载模型权重和依赖
- 最后给出这些 foundation model 的实验结果

## 2. 官方资料调研结论

### 2.1 Moirai

官方来源：

- Salesforce AI Research `uni2ts`
- 官方 Hugging Face `Salesforce/moirai-*`

官方推荐用法：

- 安装 `uni2ts`
- 使用 `MoiraiForecast / Moirai2Forecast` + `from_pretrained(...)`
- 主要定位是 zero-shot / fine-tuning forecasting

### 2.2 Chronos-2

官方来源：

- Amazon `chronos-forecasting`
- 官方 Hugging Face `amazon/chronos-2`

官方推荐用法：

- 安装 `chronos-forecasting>=2.0`
- 使用 `Chronos2Pipeline.from_pretrained(...)`
- 官方示例主打 zero-shot forecasting

### 2.3 TimesFM 2.5

官方来源：

- Google Research `timesfm`
- Hugging Face `google/timesfm-2.5-200m-transformers`
- Hugging Face Transformers 文档 `TimesFM 2.5`

官方推荐用法：

- 可直接使用 `transformers.TimesFm2_5ModelForPrediction.from_pretrained(...)`
- 官方文档给出了 zero-shot forecasting 示例

### 2.4 MOMENT

官方来源：

- `momentfm` / `moment` GitHub
- Hugging Face `AutonLab/MOMENT-*`

官方推荐用法：

- 安装 `momentfm`
- 使用 `MOMENTPipeline.from_pretrained(...)`
- forecasting 也是官方支持任务之一

## 3. Review 决策：这一轮怎么做才合理

### 3.1 不做“各模型各自复杂微调”

理由：

- 四个 foundation model 的 fine-tuning 方式差异太大
- 如果这一轮同时实现四套微调脚本，变量会重新缠在一起
- 用户当前最想知道的是：

> 这些 foundation model 按官方推荐方式实际跑起来以后，结果到底是什么样

因此本轮优先选择：

> **官方推荐的最小可运行 inference / zero-shot 用法**

### 3.2 统一评测协议

为了让四个模型能在同一框架下比较，本轮采用统一的评测方式：

1. 只预测当前项目真正需要的 3 个 target channel：
   - `electricity_pricing`
   - `non_shiftable_load_avg`
   - `solar_generation_avg`
2. 先做 rolling forecast metric
3. 对通过 sanity 且 runtime 可接受的模型，再跑 downstream `+ QP` 控制

### 3.3 为什么这样设计合理

- 这和官方“先 zero-shot inference”的推荐一致
- 这能最快回答“这些模型到底能不能在当前项目里工作”
- 这避免把“foundation model 能力”和“我们对它做了多少 task-specific hacking”混在一起

## 4. 本轮实验顺序

### Step A：依赖和权重下载

按官方方法安装：

- `uni2ts`
- `chronos-forecasting`
- `momentfm`
- `TimesFM 2.5` 优先直接用现有 `transformers`，若不够再补官方包

### Step B：GPU3 official-use sanity

对每个模型只做一个最小 forecast sanity：

- 能否加载
- 能否生成 horizon=24 预测
- 输出 shape / dtype 是否正确
- 单次延迟是否可接受

### Step C：完整 rolling forecast 评测

对通过 sanity 的模型统一计算：

- test `overall_mse`
- test `overall_mae`
- 每个 target 的分项误差

### Step D：downstream control

对通过 Step C 且 runtime 可接受的模型，再跑：

- `foundation forecast + QP`

## 5. 成功标准

- 至少把四个模型都跑到“是否可用”的结论
- 至少给出 rolling forecast 结果
- 对能承受 full run 的模型，再给 downstream control 结果

## 6. 本轮不做什么

- 不把某个 foundation model 微调到最好再比较
- 不直接把 foundation model round 和 controller baseline round 混在一起
- 不把单次失败误写成“模型本身无效”

## 7. 结果解释原则

如果模型跑不起来，结果文档必须区分：

1. 官方依赖/权重当前无法在本机复现
2. 模型能运行，但 forecast 结果差
3. forecast 结果可以，但 downstream control 不好

这三类不能混写成同一个“失败”。
