# Auto Review Note: Round 4 Backbone Feasibility（2026-03-21）

## 1. 用户要求

用户明确要求：

- 继续尝试更多 low-level backbone
- 包括各种 former
- 包括各种 time-series foundation model
- 每次实验前必须先 review 可行性和必要性

## 2. 候选 backbone 矩阵

### 2.1 former / classical deep forecasting

候选：

- TransformerEncoder forecaster
- TimeSeriesTransformer
- Informer / Autoformer

### 2.2 foundation / pretrained TS model

候选：

- `amazon/chronos-*`
- `TimesFM`
- `MOMENT`
- `ibm-granite/granite-timeseries-patchtst`

## 3. 本机可行性检查结论

### 3.1 已确认可运行

- `TransformerEncoder`：本地自实现，完全可行
- `ibm-granite/granite-timeseries-patchtst`：本机缓存中已有完整 `model.safetensors`，且可通过 `transformers.PatchTSTForPrediction.from_pretrained(..., local_files_only=True)` 加载

### 3.2 已尝试但当前不可直接运行

- `amazon/chronos-t5-small / large`
  - 当前缓存里只有 `config.json`，没有完整 tokenizer/runtime 支持
- `amazon/chronos-2`
  - 有 `model.safetensors`，但当前机器缺少可直接运行的 Chronos runtime / tokenizer 路径
- `TimesFM`
  - 当前环境无 `timesfm` 库
- `MOMENT`
  - 当前环境无 `momentfm` 库

## 4. Review 决策

本轮真正执行的 backbone 是：

1. **TransformerEncoder forecaster**
   - 回答“再补一个 former 类模型会怎样”
2. **Granite PatchTST initialized forecaster**
   - 回答“一个本地可运行的 foundation-like / pretrained backbone 会怎样”

同时把下面内容写入结果文档，但不把它们伪装成已跑通：

- Chronos：已做可行性尝试，但当前机器缺 tokenizer/runtime，不能形成可运行 baseline
- TimesFM / MOMENT：当前环境未安装对应库，未形成可运行 baseline

## 5. 为什么这个选择是合理的

- 它直接覆盖“former + foundation”两大类
- 它不依赖额外下载大模型权重
- 它不会因为外部依赖阻塞而拖慢整个 round
- 它能让本轮的结论保持可复现，而不是停留在空泛 wishlist

## 6. 本轮实验包

### 实验 A：former baseline

- `TransformerEncoder`
- GPU3 sanity -> GPU2 full train -> downstream `+ QP`

### 实验 B：foundation-like baseline

- Granite PatchTST initialized forecaster
- GPU3 sanity -> GPU2 full train -> downstream `+ QP`

### 实验 C：主协议下最小 high-level transfer

对每个新 backbone，只跑：

- `fixed_peak`
- `text_best`
- `llm_prompt_v1`

理由：

- `fixed_peak` 是当前 event-driven 主协议下的最强固定 expert
- `text_best` 是当前 surrogate router 代表
- `llm_prompt_v1` 是当前真实 LLM router 代表

## 7. 成功标准

- 若新 backbone 明显改变 `fixed_peak / text_best / llm_prompt_v1` 的排序，说明当前 high-level 结论仍然强依赖 backbone。
- 若排序稳定，说明 event-driven 结论开始变得更稳。
