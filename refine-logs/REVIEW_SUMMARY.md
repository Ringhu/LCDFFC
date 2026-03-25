# Review Summary

**Problem**: 在外生时间序列驱动控制里，如何让更好的 forecasting 稳定转化成更好的下游控制，而不是只降低平均 forecast error。
**Initial Approach**: 最初同时考虑 decision-focused training、uncertainty fallback、language-conditioned routing、Grid2Op transfer。
**Date**: 2026-03-25
**Rounds**: 2 external review rounds + 2 internal refinement writes
**Final Score**: 7.0 / 10
**Final Verdict**: REVISE

## Problem Anchor
- Bottom-line problem:
  Build a publishable method for exogenous time-series-driven control where better forecasting translates into reliable downstream control gains rather than only lower forecast error.
- Must-solve bottleneck:
  In forecast-then-control pipelines, the controller only cares about a small subset of future windows and channels, but standard training treats all forecast errors roughly equally. This mismatch is why stronger forecasters often fail to produce stable KPI gains.
- Non-goals:
  Not trying to build a new time-series foundation model, not using LLMs to output low-level actions, not making RL the main method, and not forcing a multi-environment paper in the first version.
- Constraints:
  Start from CityLearn battery control, keep the current low-level QP stack fixed, use modest compute, and keep the main method small enough to implement and validate quickly in the current repository.
- Success condition:
  With the same controller, the proposed training method should produce more consistent cost / carbon / peak improvements than plain uniform forecast training, and the gain should be traceable to better accuracy on controller-critical future windows.

## Round-by-Round Resolution Log

| Round | Main Reviewer Concerns | What This Round Simplified / Changed | Solved? | Remaining Risk |
|---|---|---|---|---|
| 1 | broad idea 太宽；主贡献不唯一；routing 还不够 paper-tight | 先把 thesis 从 broad roadmap 缩到 high-level routing | partial | language 是否必要仍然答不出来 |
| 2 | routing 像 wrapper；language necessity 不足；主论文更该押 forecast-side bottleneck | 明确 pivot 到 CSFT：固定 controller，只改 forecast loss；routing 降到 appendix / future work | yes | sensitivity labels 是否足够稳、增益是否足够大 |

## Overall Evolution
- 最初的 broad plan 更像研究路线图，不像一篇论文。
- 第一轮收缩把多条线先压到 routing thesis，但外部 reviewer 继续指出 language 证据不够。
- 第二轮 review 给出更清楚的结论：**第一篇论文的真正主线应该是 controller-sensitive forecast refinement，而不是 language-conditioned routing。**
- 最终 proposal 把新方法压到一个机制：离线 sensitivity labels + mixed weighted forecast loss。
- 实验包也被压缩到：一个主 controller、一个主 backbone、三个关键 ablations、三个 test views。

## Final Status
- Anchor status: preserved
- Focus status: tight
- Modernity status: intentionally conservative
- Strongest parts of final method:
  - 机制小
  - 和当前 repo 主路径完全匹配
  - 有清楚的 matched / mismatched controller defense
  - 有明确的 mechanism plot
- Remaining weaknesses:
  - 还没有真实结果支撑 CSFT
  - sensitivity label generation 可能有噪声
  - 如果增益只在个别 slice 出现，论文还不够强

## Final Recommendation
1. 主论文改成 CSFT，不再主打 routing。
2. 主 controller 固定 `qp_carbon`。
3. 先只用一个主 backbone 跑通最小验证包。
4. routing 不进主结果，最多放 appendix motivation。
5. 下一步直接进入 experiment plan / implementation，而不是继续做 idea-level 扩展。
