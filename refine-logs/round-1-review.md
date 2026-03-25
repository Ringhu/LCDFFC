# Round 1 Review

## Context

这轮 review 针对的是 **CSFT pilot 失败之后** 的新 proposal，重点不再是“继续扩方法”，而是判断：

1. 当前负结果是否能被收束成一个 publishable 的机制问题；
2. 这个“稳定化 controller-sensitive supervision”路线，是否已经足够像一个方法，而不是 debug 清单。

## Parsed Scores

| Dimension | Score | Notes |
|---|---:|---|
| Problem Fidelity | 8.5 | 仍然紧扣“forecast training 要服务下游 control KPI”这个原始问题 |
| Method Specificity | 7.5 | 主接口和训练路径已经清楚，但具体 operator 还没完全冻结 |
| Contribution Quality | 7.0 | 机制主线清楚了，但还容易被看成 weight tuning + diagnostics |
| Frontier Leverage | 8.0 | 保持克制是对的，没有不必要的 buzzword |
| Feasibility | 8.5 | 低成本、可复用现有 checkpoint 和 pipeline |
| Validation Focus | 8.0 | 实验块很精简，而且直接围绕 claim |
| Venue Readiness | 6.0 | 还偏像 troubleshooting protocol，不像 paper-ready method |

## Overall Score

**7.8 / 10**

## Verdict

**REVISE**

## Main Weakness Below 7

### Venue Readiness — 6.0
- **Specific weakness**:
  当前 proposal 仍然像“先检查、再修权重、再看结果”的流程，而不是一个清楚的算法性贡献。可选 fallback（如 bucketed weights）也会让主线变松。
- **Concrete fix at the method level**:
  冻结一个**唯一的 stabilized-weight operator**，并预注册一个**清楚的 acceptance criterion**。
  - 例如：`clip@q95 -> log1p(s/tau) -> per-sample normalize -> alpha=0.85`
  - 并规定：必须同时满足“top-decile error 改善”以及“至少一个 KPI 改善且 overall MAE 不超过容忍退化阈值”，否则就不把它当作有效方法。
- **Priority**: IMPORTANT

## Simplification Opportunities

1. 把 bucketed-weight fallback 从主方法里删掉，只保留为 contingency / appendix note。
2. 把 D1 + D2 合并成一个统一的 `label validity preflight`，避免 proposal 读起来像流程图。
3. 不再列多个 transform/search space；固定一个 transform 和一个 `alpha`。

## Modernization Opportunities

**NONE**

## Drift Warning

**NONE**

## Raw External Response

<details>
<summary>Codex raw review</summary>

Below is a method‑focused review aligned with your constraints (smallest adequate mechanism, no contribution sprawl, no extra experiments unless core‑claim‑critical).

---

## Scores (1–10)

1. **Problem Fidelity: 8.5**
   You stay anchored to “forecast training that improves downstream control KPIs” and keep the fixed controller + dataset + backbone. The method is explicitly about repairing the supervision signal, not changing the problem.

2. **Method Specificity: 7.5**
   Most interfaces are clear (weights → loss, same pipeline), but key choices remain under‑specified (exact alignment check tolerance, precise clipping quantile, transform choice, smoothing kernel/window, acceptance criteria).

3. **Contribution Quality: 7.0**
   There is one dominant mechanism (stabilized controller‑sensitive supervision), but novelty risks being perceived as “weight tuning + diagnostics” unless you freeze a single, crisp operator and success criterion.

4. **Frontier Leverage: 8.0**
   Appropriately avoids buzzwords; modernity isn’t the bottleneck here.

5. **Feasibility: 8.5**
   Minimal compute, reuses checkpoints, no new models.

6. **Validation Focus: 8.0**
   The diagnostic‑first loop is minimal and directly tied to claims. No obvious bloat.

7. **Venue Readiness: 6.0**
   As written, it still reads like a careful troubleshooting protocol rather than a tight, publishable method. Needs a single frozen mechanism + pre‑specified pass/fail criterion to feel like a contribution, not a process.

---

## OVERALL SCORE (weighted) = **7.8 / 10**

(Weighted by: PF 15%, MS 20%, CQ 20%, FL 10%, Feas 15%, VF 15%, VR 5%)

---

## Weaknesses for Scores < 7

### 7) Venue Readiness — **6.0**
**Weakness:**
The “method” is currently a pipeline of checks and optional transforms. Reviewers may see this as “diagnose, then tune weights,” not a crisp algorithmic contribution. The optional fallback (bucketed weights) also weakens focus unless explicitly scoped as contingency.

**Concrete Method‑Level Fix:**
Lock down a **single stabilized‑weight operator** and **pre‑register its acceptance criterion**. For example:
- **Operator:** clip at train‑q95, apply `log1p(s/τ)` with fixed τ, per‑sample normalize, fixed `alpha=0.85`, no smoothing unless D1 shows rank signal but high variance.
- **Acceptance:** must improve **top‑decile error** *and* at least one KPI without degrading overall MAE beyond a stated tolerance.
If it fails, **explicitly scope the paper** as a falsification of raw CSFT rather than a method claim. This keeps the contribution sharp either way.

**Priority:** IMPORTANT

---

## Simplification Opportunities (delete/merge/reuse)

1. **Remove the bucketed‑weight fallback from the main method.** Keep it as a contingency note or appendix. This tightens the single‑mechanism story.
2. **Collapse D1+D2 into one “label validity check” preflight script.** This reduces procedural sprawl and makes the method feel more like a single algorithm.
3. **Pick one transform + one alpha.** Listing multiple transforms (sqrt/log1p + smoothing + rank‑binning) reads like a search space. Freeze one to avoid “tuning.”

---

## Modernization Opportunities

**NONE** — The bottleneck is supervision validity, not model capacity or modern architecture. Any “modernization” would add noise, not signal.

---

## Drift Warning

**NONE** — The proposal remains anchored to the original control‑sensitive forecasting problem.

---

## Verdict: **REVISE**

Promising and well‑scoped, but not yet venue‑ready. Tighten to a single frozen stabilization operator with explicit acceptance criteria so the paper reads as a **mechanism**, not a **debugging checklist**.

</details>
