# Refinement Report

**Problem**: 在外生时间序列驱动控制里，如何让更好的 forecasting 稳定转化成更好的下游控制，而不是只降低平均 forecast error。
**Initial Approach**: 同时探索 forecast + QP、decision-focused training、uncertainty fallback、language-conditioned routing、可选 Grid2Op transfer。
**Date**: 2026-03-25
**Rounds**: 2
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

## Output Files
- Review summary: `refine-logs/REVIEW_SUMMARY.md`
- Final proposal: `refine-logs/FINAL_PROPOSAL.md`
- Round 2 external review: `refine-logs/round-2-review.md`
- Round 2 refinement: `refine-logs/round-2-refinement.md`

## Score Evolution

| Round | Problem Fidelity | Method Specificity | Contribution Quality | Frontier Leverage | Feasibility | Validation Focus | Venue Readiness | Overall | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 9 | 5 | 5 | 6 | 8 | 5 | 5 | 6.0 | REVISE |
| 1 | 9 | 8 | 7 | 7 | 8 | 8 | 7 | 7.7 | REVISE |
| 2 | 9 | 7 | 7 | 6 | 8 | 7 | 6 | 7.0 | REVISE |

## Round-by-Round Review Record

| Round | Main Reviewer Concerns | What Was Changed | Result |
|---|---|---|---|
| 1 | broad idea 过宽；需要唯一主贡献；routing 要不要当主线还不清楚 | 把 thesis 先压到 high-level routing | partial |
| 2 | language necessity 不足；routing 像 wrapper；真正 bottleneck 在 forecast-side target mismatch | pivot 到 CSFT；routing 降级为 appendix / future work | resolved |

## Final Proposal Snapshot
- 论文主线改成 **Controller-Sensitive Forecast Training (CSFT)**。
- 固定 `forecast -> qp_carbon -> CityLearn` 主闭环，不改 controller。
- 对每个 forecast cell 生成 finite-difference controller sensitivity label。
- 用 mixed weighted loss 微调 forecaster，让 capacity 集中到 controller-critical future cells。
- 主 defense 不是“大模型更强”，而是“controller-sensitive weighting 比 heuristic weighting 更对题”。

## Method Evolution Highlights
1. 从 broad roadmap 收缩到单一机制。
2. 从 language-conditioned routing pivot 到 forecast-side controller-sensitive supervision。
3. 从多模块叙事改成“固定 controller + weighted forecast loss”的最小方法包。

## Pushback / Drift Log

| Round | Reviewer Said | Author Response | Outcome |
|---|---|---|---|
| 1 | 不要把 broad roadmap 当论文 | 接受，先收缩到 routing thesis | accepted |
| 2 | 不要继续押 language main thesis | 接受，直接 pivot 到 CSFT | accepted |
| 2 | A2 / A3 / A4 也可以 | 只保留 A1 为主方法，A2 当 baseline，A3 当 fallback，A4 不进第一篇 | accepted |

## Claims Matrix

| Possible outcome | Allowed claim | Must drop |
|---|---|---|
| CSFT clearly beats uniform + heuristic weighting on control KPIs and top-sensitivity forecast error | 强主张：uniform forecast loss 不适合 fixed forecast-then-control；controller-sensitive weighting 更合适 | 不需要额外 routing thesis |
| CSFT only modestly beats uniform and mostly on stress subsets | 中等主张：controller-sensitive weighting 在 control-critical regimes 更有效 | 泛化到所有 regimes 的强说法 |
| CSFT matches heuristic weighting | 弱主张：controller-aware supervision 有潜力，但 finite-difference superiority 未站稳 | “mechanistic superiority” |
| CSFT fails to beat uniform | 主 thesis 不成立，需要重新想 bottleneck | 整个 CSFT 主张 |

## Prioritized TODO List

1. **实现离线 sensitivity label generation**
   - 输出 `H x C` sensitivity map
   - 支持 `qp_carbon` 和 `qp_current` 两种 label generation
2. **实现 mixed weighted loss 训练路径**
   - baseline uniform
   - event-window weighting
   - CSFT
3. **做 pilot stability check**
   - sensitivity 分布
   - clipping / normalization
   - top-decile bucket statistics
4. **跑最小主实验包**
   - one backbone
   - one controller
   - standard + stress subsets
5. **做 matched vs mismatched controller ablation**
6. **做 mechanism plots**
   - error reduction vs sensitivity decile
   - average sensitivity heatmap

## Remaining Weaknesses
- 当前还没有 CSFT 实验结果
- sensitivity labels 可能噪声较大
- 如果 oracle gap 缩小不明显，论文会停在“合理但不够强”
- 目前还是 CityLearn 单环境，外推要很克制

## Raw Reviewer Responses

完整 raw reviewer 输出保存在：
- `refine-logs/round-2-review.md`

## Next Steps
- 直接进入 `/experiment-plan`，把 CSFT proposal 变成具体实验路线图。
- 然后进入实现与首轮 pilot。
