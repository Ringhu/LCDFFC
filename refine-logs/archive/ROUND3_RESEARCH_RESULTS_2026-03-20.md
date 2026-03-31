# Round 3 结果：PatchTST + Event-Driven Protocol + Real LLM Router（2026-03-20）

## 1. 本轮为什么做

本轮直接回应用户提出的三类质疑：

1. low-level forecasting baseline 不能只有 `GRU`
2. preference-shift 协议不能只靠人工四段等长切分
3. 所谓 language router 不能一直停留在规则/模板层，至少要有一个真实可运行的 prompt-only LLM 版本

对应的 reviewed note 是：

- `refine-logs/auto-review/2026-03-20-round3-master-review.md`
- `refine-logs/auto-review/2026-03-20-round3-patchtst-review.md`
- `refine-logs/auto-review/2026-03-20-round3-event-driven-review.md`
- `refine-logs/auto-review/2026-03-20-round3-llm-router-review.md`

## 2. Step 2：PatchTST stronger baseline

### 2.1 新增实现

- `models/patchtst_forecaster.py`
- `configs/forecast_patchtst.yaml`
- `eval/run_controller.py` / `eval/run_preference_shift.py` 继续复用 `models/factory.py`
- `tests/test_forecaster_factory.py`

### 2.2 forecasting 指标

| Backbone | overall_mse | overall_mae |
|---|---:|---:|
| GRU | 0.9323 | 0.3580 |
| TSMixer | 0.9422 | 0.3850 |
| PatchTST | 1.1984 | 0.4819 |

结论：

- 单看 forecasting 指标，`PatchTST` 明显弱于 `GRU / TSMixer`
- 所以“只要换成 `PatchTST` 就会更强”这个直觉，在当前工程设置下并不成立

### 2.3 下游控制指标

| Run | cost | carbon | peak | ramping |
|---|---:|---:|---:|---:|
| GRU + QP | 32.0099 | 488.5686 | 15.8135 | 853.9113 |
| TSMixer + QP | 32.6081 | 496.0019 | 15.9166 | 909.8013 |
| PatchTST + QP | 31.7192 | 483.0497 | 16.1183 | 871.9708 |

结论：

- `PatchTST` 并没有带来“全面更好”的结果
- 它的表现是：`cost / carbon` 更好，但 `peak / ramping` 更差
- 这说明一个更关键的问题：

> forecasting MSE 更低，不等于 downstream control 一定更好；而 forecasting MSE 更差，也不等于所有控制指标都会一起变差。

这反而强化了后续 `decision-focused` 路线的合理性。

## 3. Step 3：event-driven preference protocol

### 3.1 新增实现

- `eval/preference_protocols.py`
- `eval/run_preference_shift.py` 新增 `--schedule_type event_driven`
- `tests/test_preference_shift.py` 新增 event-driven 协议测试

### 3.2 协议设计要点

新协议不再把 episode 均匀切成四段，而是基于 oracle 序列做事件触发：

- 高 price -> `cost`
- 高 carbon -> `carbon`
- 高 net load / grid stress -> `peak`
- 未来风险高但当前仍有准备窗口 -> `reserve`
- 其余时段 -> `balanced`

并引入：

- `min_segment_len`
- persistence / cooldown

因此它比旧协议更接近“运营者为什么此刻会切换偏好”。

### 3.3 event-driven 结果

当前使用 `GRU` backbone，完整比较：

| Run | avg_preference_score | avg_regret_to_best_single_fixed |
|---|---:|---:|
| event_fixed_peak | 1.165603 | 0.000000 |
| event_llm_prompt_v1 | 1.166728 | 0.001125 |
| event_fixed_carbon | 1.166689 | 0.001087 |
| event_fixed_balanced | 1.166960 | 0.001357 |
| event_text_best | 1.171089 | 0.005486 |
| event_fixed_reserve | 1.173321 | 0.007718 |
| event_heuristic | 1.177060 | 0.011457 |
| event_fixed_cost | 1.178798 | 0.013195 |

核心结论：

- 在更真实的 event-driven 协议下，当前 best 不再是 `text_best`
- 新 best single fixed 变成了 `event_fixed_peak`
- `text_best` 和 `heuristic` 都明显弱于 `fixed_peak`

这意味着：

> 旧的四段等长协议确实偏乐观，它放大了 text-based surrogate router 的优势。

所以后续论文如果继续写高层 preference routing，主协议必须至少同时报告 event-driven 版本。

## 4. Step 4：真实 prompt-only LLM router

### 4.1 新增实现

- `llm_router/router.py`：最小可运行 `LLMRouter.route()`
- `llm_router/prompt_templates.py`
- `llm_router/json_schema.py`
- `configs/llm_router.yaml`
- `tests/test_llm_router.py`

当前实现特点：

- 使用本地缓存 `Qwen/Qwen2.5-0.5B-Instruct`
- `transformers` 推理
- prompt-only
- 输出 JSON 后做 schema 校验与权重归一化
- 按 instruction 做 segment 级缓存，不在 segment 内重复生成

### 4.2 sanity 结果

`GPU 3` 120-step sanity：

- `num_calls = 8`
- `num_parse_failures = 0`
- `num_fallbacks = 0`
- `total_latency_sec = 16.17`

说明：

- 真实 `LLMRouter.route()` 已经不是空接口
- 当前 prompt / parser 路径是稳定可运行的

### 4.3 event-driven 完整结果

`GPU 2` 完整 719-step：

- `cost = 30.2554`
- `carbon = 461.7450`
- `peak = 15.9142`
- `ramping = 856.0266`
- `num_calls = 48`
- `num_parse_failures = 0`
- `num_fallbacks = 0`
- `total_latency_sec = 90.15`

在 event-driven 汇总里：

- `event_llm_prompt_v1` 的 `avg_preference_score = 1.166728`
- 它没有超过 `event_fixed_peak = 1.165603`
- 但它优于 `event_text_best = 1.171089` 和 `event_heuristic = 1.177060`

结论：

- 真实 LLM router 已经“可运行、可复现、可比较”
- 它目前不是最优方法
- 但它并没有输给现有 rule/text surrogate，反而在当前 event-driven 协议下排到了第二梯队最前面

这说明：

> “做真实 LLM router 完全没有价值”这个说法不成立；更准确的说法是：真实 prompt-only LLM router 值得继续研究，但当前还没有强到能压过最佳固定 expert。

## 5. Round 3 的整体判断

本轮最重要的结论有 3 条：

1. `PatchTST` 进一步证明了 low-level backbone 会改变控制 trade-off，而且 forecasting 误差与控制表现并不严格同向。
2. event-driven 协议显著收紧了旧的高层结论，当前 `text_best` 不再是最强方法。
3. 真实 `LLMRouter.route()` 已经被打通，并且其结果优于现有 surrogate router，但仍未超过最佳固定 expert。

## 6. 这意味着什么

### 6.1 哪些说法必须收紧

- 不能再说“当前高层结论已经稳定成立”
- 不能再说“旧四段协议足够代表真实 preference-shift”
- 不能再说“真实 LLM router 还没有任何可运行结果”

### 6.2 哪些说法可以保留

- `forecast + QP` 作为 low-level backbone 仍然是有效主线
- 当前问题已经不适合继续微调 `text_v8`
- 真实 prompt-only LLM router 是值得继续推进的方向，但需要更强比较协议和更强 low-level backbone 一起验证

## 7. 下一步建议

按优先级，下一步最合理的是：

1. **把 event-driven protocol 升级为主协议**
   - 后续所有高层 routing 结果至少同时报告 default + event-driven
2. **在 `PatchTST` backbone 下补一轮最小 event-driven 检查**
   - 不需要跑全套，只需验证 `fixed_peak / text_best / llm_prompt_v1`
3. **不要立刻做复杂 agent 版 LLM**
   - 先把 prompt-only 版本与 fixed expert 的差距分析清楚
4. **如果继续冲论文主张，应该转成更保守的表述**
   - 从“language routing beats fixed weights”收紧为
   - “event-driven preference adaptation is harder than the default protocol suggests; a real prompt-only LLM router is feasible and competitive, but the best fixed expert remains a strong baseline”
