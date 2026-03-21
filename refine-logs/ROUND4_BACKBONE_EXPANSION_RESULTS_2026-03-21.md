# Round 4 结果：Backbone Expansion + Event-Driven Transfer（2026-03-21）

## 1. 本轮目标

Round 4 直接回应两类问题：

1. 还有很多 low-level backbone 没试，尤其是更多 former 和 foundation-like 模型。
2. Round 3 虽然已经把 event-driven 协议立起来了，但还不知道 high-level 结论在更多 backbone 下是否稳定。

本轮对应的 reviewed design 是：

- `refine-logs/auto-review/2026-03-21-round4-master-review.md`
- `refine-logs/auto-review/2026-03-21-round4-backbone-feasibility-review.md`
- `refine-logs/auto-review/2026-03-21-round4-uncovered-gap-review.md`

## 2. 本轮真正执行了哪些 backbone

### 2.1 former 类

- `TransformerEncoder forecaster`

### 2.2 foundation-like 类

- `Granite PatchTST initialized forecaster`

### 2.3 已尝试但当前机器未形成可运行 baseline 的 foundation model

- `amazon/chronos-t5-small / large`
  - 当前缓存里只有 `config.json`
- `amazon/chronos-2`
  - 虽然有 `model.safetensors`，但当前机器缺少可直接运行的 Chronos tokenizer/runtime 路径
- `TimesFM`
  - 当前环境无 `timesfm` 库
- `MOMENT`
  - 当前环境无 `momentfm` 库

因此，这一轮不能把 Chronos / TimesFM / MOMENT 写成“已经对比过”，只能写成：

> 已做可行性检查，但在当前机器条件下尚未形成可运行 baseline。

## 3. forecasting 结果总表

| Backbone | overall_mse | overall_mae |
|---|---:|---:|
| GRU | 0.9323 | 0.3580 |
| TSMixer | 0.9422 | 0.3850 |
| Transformer | 0.9460 | 0.3890 |
| Granite PatchTST init | 1.0543 | 0.4692 |
| PatchTST | 1.1984 | 0.4819 |

结论：

- 单看 forecasting 指标，`GRU` 仍然最好。
- 新增的 `Transformer` 与 `TSMixer` 接近，但没有超过 `GRU`。
- `Granite` 的 forecasting 指标并不强，明显弱于 `GRU / TSMixer / Transformer`。

## 4. downstream control 结果总表

| Run | cost | carbon | peak | ramping |
|---|---:|---:|---:|---:|
| GRU + QP | 32.0099 | 488.5686 | 15.8135 | 853.9113 |
| TSMixer + QP | 32.6081 | 496.0019 | 15.9166 | 909.8013 |
| PatchTST + QP | 31.7192 | 483.0497 | 16.1183 | 871.9708 |
| Transformer + QP | 32.4926 | 492.1836 | 15.2551 | 877.8787 |
| Granite + QP | 31.6027 | 480.3075 | 14.5422 | 827.7849 |

### 4.1 结论 1：forecasting 指标与控制结果继续解耦

本轮最关键的 low-level 发现是：

- `GRU` 仍然有最好的 forecasting MSE/MAE
- 但 `Granite + QP` 给出了目前最强的下游控制结果

这再次证明：

> forecasting loss 不是决定控制表现的充分统计量。

### 4.2 结论 2：当前最强 low-level backbone 已经不是 `GRU`

如果按 downstream control 来看，当前排序大致是：

1. `Granite + QP`
2. `PatchTST + QP`
3. `GRU + QP`
4. `Transformer + QP`
5. `TSMixer + QP`

至少在当前单场景结果里，`Granite` 已经把 low-level backbone 的结论改写了。

## 5. event-driven 主协议下的最小 high-level transfer

本轮对每个新 backbone 只跑：

- `fixed_peak`
- `text_best`
- `llm_prompt_v1`

理由：

- `fixed_peak` 是当前 event-driven 主协议下的最强单一固定 expert
- `text_best` 是当前 surrogate router 代表
- `llm_prompt_v1` 是当前真实 prompt-only LLM router 代表

## 6. Transformer backbone 下的结果

### 6.1 KPI

- `transformer_event_fixed_peak`
  - cost `30.5444`, carbon `462.7073`, peak `15.2547`, ramping `873.1958`
- `transformer_event_text_best`
  - cost `30.7672`, carbon `465.7325`, peak `15.2494`, ramping `881.6796`
- `transformer_event_llm_prompt_v1`
  - cost `30.4512`, carbon `463.0349`, peak `15.2494`, ramping `874.8934`

### 6.2 汇总分数

- `fixed_peak`: `avg_preference_score = 1.045753`
- `text_best`: `1.054501`
- `llm_prompt_v1`: `1.044047`

结论：

- 在 `Transformer` backbone 下，`llm_prompt_v1` 已经略优于 `fixed_peak`
- `text_best` 仍然最差

这说明：

> 对某些 low-level backbone，真实 prompt-only LLM router 已经开始出现超过最佳固定 expert 的信号，而 surrogate text router 反而没有跟上。

## 7. Granite backbone 下的结果

### 7.1 KPI

- `granite_event_fixed_peak`
  - cost `29.6037`, carbon `451.1195`, peak `14.5104`, ramping `825.2427`
- `granite_event_text_best`
  - cost `29.8987`, carbon `454.9772`, peak `14.5201`, ramping `829.6797`
- `granite_event_llm_prompt_v1`
  - cost `30.1119`, carbon `460.0036`, peak `15.1225`, ramping `852.1870`

### 7.2 汇总分数

- `fixed_peak`: `avg_preference_score = 1.034519`
- `text_best`: `1.040650`
- `llm_prompt_v1`: `1.055199`

结论：

- 在当前最强 low-level backbone `Granite` 下，`fixed_peak` 仍然最好
- `text_best` 和 `llm_prompt_v1` 都没有追上它
- 而且 `llm_prompt_v1` 在这个 backbone 下退化更明显

## 8. Round 4 的核心结论

### 8.1 结论 1：用户关于“low-level backbone 还没试够”的质疑是对的

Round 4 已经证明：

- low-level backbone 仍然会显著改变 high-level 结论
- 所以在 backbone 没试够之前，不能过早把高层方法写成稳定结论

### 8.2 结论 2：foundation-like backbone 真正改变了当前 low-level 排名

虽然 `Granite` 的 forecasting 指标不强，但它给出了目前最好的 downstream control。

这意味着：

> 当前 low-level backbone 的最优性不能再按 forecasting loss 排序，而必须按 downstream control 排序。

### 8.3 结论 3：high-level 结论在 backbone 之间仍不稳定

- `Transformer` 下：`llm_prompt_v1` 略优于 `fixed_peak`
- `Granite` 下：`fixed_peak` 明显优于 `llm_prompt_v1`

所以当前最准确的判断是：

> event-driven 主协议已经比旧四段协议强很多，但 high-level 排序仍然依赖 low-level backbone，因此当前研究还不适合把“LLM router 优于 fixed expert”写成稳定主结论。

## 9. 对 critical review 的覆盖进度

### 9.1 本轮已新增覆盖

- 更多 former backbone：已覆盖
- 可运行的 foundation-like backbone：已覆盖
- “当前结论会不会只是某一个 backbone 的偶然现象”：已进一步覆盖

### 9.2 仍未覆盖完

- `QP` vs 更强 controller family baseline
- 多 episode / 统计区间
- OOD / transfer

## 10. 下一步建议

当前最合理的下一步已经比 Round 3 更清晰：

1. **进入 controller baseline round**
   - 单开一轮 reviewed 设计
   - 比较 `QP` 与一个新的 low-level control family
2. **把 `Granite + event-driven` 当作当前 strongest low-level setting**
   - 后续高层实验优先在这个 setting 下做
3. **不要再把 surrogate text router 当作默认主线**
   - 它在 Round 4 的两组 backbone 下都没有赢
4. **真实 LLM router 继续保留，但主张必须收紧**
   - 当前只能说它在部分 backbone 下有正信号
   - 不能说它已经稳定优于 fixed expert
