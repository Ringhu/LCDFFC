# Review Summary

**Problem**: 在固定 `forecast -> qp_carbon -> CityLearn` 闭环里，怎样让 forecast training 真正服务下游控制 KPI，而不只是降低平均 forecast error。
**Initial Approach**: 最初的主线是更广义的 CSFT 设想，但最新 pilot 显示 raw finite-difference sensitivity weighting 会同时伤害 forecast 与 control，因此本轮 refine 的目标变成：把负结果压缩成一个最小、可证伪、可实现的方法路线。
**Date**: 2026-03-26
**Rounds**: 3
**Final Score**: 8.6 / 10
**Final Verdict**: REVISE

## Problem Anchor
- Bottom-line problem:
  Build a publishable method for exogenous time-series-driven control where forecast training improves downstream control KPIs, not just average forecast error.
- Must-solve bottleneck:
  In forecast-then-control pipelines, the controller only cares about a small subset of future windows and channels, but the current raw cell-wise CSFT labels appear too sharp, too noisy, or misaligned to provide useful supervision. The current pilot suggests that naive controller-sensitive weighting can hurt both forecasting and control.
- Non-goals:
  Not scaling to more seeds/backbones yet, not introducing a new controller, not switching to end-to-end RL, not making language routing part of the main story, and not claiming a final paper-ready method before pilot failure is explained.
- Constraints:
  Start from the current CityLearn + GRU + fixed `qp_carbon` stack, use the existing chronological split and artifacts, keep compute modest, use GPU 2 only for training/inference, and prefer diagnostics that reuse existing checkpoints before new full reruns.
- Success condition:
  After a small diagnostic-and-refinement loop, either (a) a softened controller-sensitive training objective shows better error on controller-critical cells and at least early positive KPI signal over uniform training, or (b) we can confidently falsify the current raw-label route and pivot without wasting more compute.

## Round-by-Round Resolution Log

| Round | Main Reviewer Concerns | What This Round Simplified / Modernized | Solved? | Remaining Risk |
|---|---|---|---|---|
| 1 | 更像 debug checklist，不像方法；operator 没冻结 | 冻结单一 stabilization operator，删掉 fallback 主线 | partial | 还缺明确数值阈值 |
| 2 | preflight 仍有定性表达；接受标准还不够算法化 | 将 preflight、Huber、epsilon、统计量、acceptance rule 全部数值化 | yes | 还缺机制解释与数据接口说明 |
| 3 | 主要担心 pseudo-novelty 和复现细节不够明确 | 外部 reviewer 已认可其为单一、最小、算法化方法 | partial | 仍需补 operator 的 mechanistic justification |

## Overall Evolution
- 从“CSFT 为什么失败，接下来怎么查”转成“什么样的 controller-derived supervision 才值得训练”。
- 从开放式 diagnosis loop 收紧成一个 **single numerical preflight gate + single stabilization operator**。
- 删除了 transform search space、bucketed fallback、额外分支，让方法变成一个唯一配方。
- 不再追求 modernity，明确把问题界定为 supervision-quality bottleneck。
- 用负结果本身反过来 sharpen 论文问题，而不是回避失败。

## Final Status
- Anchor status: preserved
- Focus status: tight
- Modernity status: intentionally conservative
- Strongest parts of final method:
  - 完全固定的 preflight gate
  - 完全固定的 stabilized operator
  - 只需一个 rerun 就能 stop/go
  - 明确的 acceptance rule，避免事后解释
- Remaining weaknesses:
  - 还需要补一小段 operator 的 mechanistic justification
  - 还需要在最终实现文档中明确 horizon indexing / channel ordering / label storage 接口
  - 当前最终 verdict 仍是 REVISE，不是 READY
