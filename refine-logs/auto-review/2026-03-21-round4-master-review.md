# Auto Review Note: Round 4 总设计（2026-03-21）

## 1. 本轮为什么进入 Round 4

Round 3 之后，当前研究状态已经很清楚：

1. 旧四段协议偏乐观，event-driven 协议应升级为主协议。
2. `text_best` 在主协议下不再是最强方法。
3. 真实 prompt-only `LLMRouter.route()` 已经可运行，但还没有压过最佳固定 expert。
4. 用户关于“low-level backbone 还试得不够、foundation model 还没覆盖”的质疑仍然成立。

因此 Round 4 的核心目标不是继续调 router，而是：

- 扩展更多 low-level forecasting backbone
- 检查这些 backbone 是否进一步改变 high-level 结论
- 同时盘点用户 critical review 里还有哪些点仍未覆盖

## 2. 当前尚未覆盖完的 review 点

截至 Round 3，已经覆盖的点：

- stronger forecasting baseline 不止 `GRU`
- event-driven protocol
- 真实 prompt-only `LLMRouter.route()`

仍未充分覆盖的点：

1. **更多 former / foundation model backbone**
2. **`QP` 与更强控制 baseline 的比较**
3. **更强的统计证据与更大 margin**
4. **OOD / transfer**

本轮优先覆盖第 1 点，并做第 2 点的 reviewed 盘点，但不在本轮强行同时做完所有内容。

## 3. 为什么这轮优先继续做 backbone 扩展

理由有三条：

1. 这是用户这轮最直接、最明确的要求。
2. Round 3 已经证明 high-level 结论对 low-level backbone 敏感。
3. 如果 backbone 还没有试够，继续做控制 baseline 或更强高层叙事，解释仍然不干净。

## 4. 本轮的执行顺序

1. 先写 backbone feasibility review。
2. 实现并测试：
   - 一个新的 former 类 baseline
   - 一个本机可运行的 foundation-like baseline
3. 先跑 forecasting + downstream control。
4. 再在 event-driven 主协议下做最小 high-level transfer 检查：
   - `fixed_peak`
   - `text_best`
   - `llm_prompt_v1`
5. 最后再汇总：哪些 review 点被覆盖了，哪些还没覆盖。

## 5. 本轮不做什么

- 不直接做复杂 agent LLM
- 不直接做新的 RL / MPC family
- 不直接做 OOD weather / transfer

原因：

> 如果这轮同时把 backbone、controller family、OOD 全缠在一起，依然无法回答“到底是哪一层改变了结论”。
