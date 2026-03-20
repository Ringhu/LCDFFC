# Auto Review Note: Round 3 总设计（2026-03-20）

## 1. 为什么进入 Round 3

上一轮 `TSMixer` stronger-baseline 实验已经说明两件事：

1. 当前高层结论对 low-level backbone 仍然敏感。
2. 在 stronger baseline 和更真实协议没有补齐之前，继续微调 `text_v8` 价值很低。

用户这一轮提出的反馈本质上要求我们补三类证据：

- low-level forecasting baseline 不能只有 `GRU`
- preference-shift 协议不能只靠人工四段等长切分
- 所谓 language router 不能一直停留在规则/模板层，至少要给出一个真实可运行的 prompt-only LLM 版本

因此本轮不再把重点放在手工调 expert rule，而是按下面顺序推进：

1. `PatchTST` stronger forecasting baseline
2. event-driven preference-shift protocol
3. 最小真实 `LLMRouter`

## 2. 为什么按这个顺序做

### 2.1 先做 `PatchTST`

理由：

- 这是对“为什么 low-level 不重训 / 为什么只有 `GRU`”最直接的回应。
- `transformers` 已内置 `PatchTST`，当前环境中实现成本可控。
- 如果 `PatchTST` 明显优于 `GRU`，则后续高层结论必须改写；如果不优于，也能把“GRU-only 太弱”这个质疑进一步收窄。

### 2.2 再做 event-driven protocol

理由：

- 即使 backbone 问题回答了，现有四段等长协议仍然过于理想化。
- event-driven 协议更接近真实 operator instruction：事件触发、持续时间不固定、存在 regime persistence。
- 它能直接回答“什么样的偏好切换是好的、如何切换、如何作为 baseline”。

### 2.3 最后做真实 `LLMRouter`

理由：

- 如果先做 LLM router，而 low-level 和 protocol 还不稳，会把所有不确定性缠在一起。
- 先稳住 backbone 和 protocol，再把真实 LLM 放进来，实验解释会干净很多。
- 当前机器有本地缓存的小型 Qwen instruct 模型，可以先做 prompt-only LLM router，而不是直接引入复杂 agent 编排。

## 3. Round 3 的总成功标准

本轮不是追求“一步把论文做完”，而是回答三个更基础的问题：

1. `PatchTST` 是否改变当前 `GRU` 主线判断？
2. 更真实的 event-driven protocol 下，当前 fixed / heuristic / text 方法的相对关系是否稳定？
3. 真实 LLM router 是否至少能跑通、可复现，并在 event-driven protocol 下形成有意义的可比结果？

只要这三个问题能被清楚回答，本轮就是成功的。

## 4. 本轮不做什么

为了保证因果清晰，本轮明确不做：

- 不继续做 `text_v8`
- 不在同一轮同时引入 OOD weather / transfer
- 不把真实 LLM router 直接包装成 agent 系统
- 不同时重构 QP controller 或 fallback 机制

这些内容要么已经有初步结论，要么会把本轮实验解释搅乱。

## 5. 产出要求

本轮结束后，至少新增或更新：

- reviewed notes（本文件 + 每一步单独 review）
- stronger forecast baseline 结果文档
- event-driven protocol 结果文档
- real LLM router 结果文档
- `EXPERIMENT_TRACKER.md`

并且每一步都要在开始前给出：

- 具体实验目的
- 为什么这样设计是合理的
- 成功/失败分别意味着什么
