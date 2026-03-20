# 用户反馈整理（2026-03-20）

本轮研究需要正面回应以下质疑：

1. “冻结低层系统”不等于“低层已经最优”，当前缺少更强低层 baseline。
2. 当前 `preference-shift` 协议太人工，固定四段切换未必足够可信。
3. 当前预测层只有 `GRU`，缺少更强时序模型对比，例如 `PatchTST`、`TSMixer` 或 foundation model。
4. 当前控制层只有 `QP`，不能直接写成最优控制器。
5. 当前所谓语言路由并不是真实的 `LLM + agent`，`LLMRouter.route()` 仍未实现。
6. 当前主结果里的 margin 很小，`avg_regret_to_best_fixed` 和 `avg_regret_to_best_single_fixed` 接近 0，说明区分度和证据强度都不足。
7. 当前更适合开始写内部论文骨架，而不是直接按投稿版标准宣称“已经够了”。

## 本轮研究目标

本轮不再继续局部调 router，而是优先回答下面这个更基础的问题：

> 当前高层路由的结论，会不会只是建立在一个过弱的低层预测 backbone 上？

## 本轮采取的策略

1. 先补一个 stronger forecast baseline
2. 在相同下游控制链路下比较它和 `GRU` 的 forecasting 结果与闭环控制结果
3. 如果 stronger baseline 没有显著改变当前结论，再进入下一轮协议升级或真实 LLM router 实现

## 本轮暂不做的事情

- 不同时做真实 LLM router
- 不同时做新的控制器 family
- 不同时做更复杂的 OOD / transfer

原因：

> 这些改动如果同时发生，会重新把变量缠在一起，无法判断到底是谁改变了结果。
