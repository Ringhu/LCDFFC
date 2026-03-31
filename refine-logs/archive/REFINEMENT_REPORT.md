# Refinement Report

**Problem**: 在固定 `forecast -> qp_carbon -> CityLearn` 闭环里，怎样让 forecast training 真正服务下游控制 KPI，而不只是降低平均 forecast error。
**Initial Approach**: 起点是原始 CSFT pilot 失败后的重新收敛：不再直接扩实验，而是先把“负结果说明了什么”压缩成一个最小、可证伪、可发表的方法表达。
**Date**: 2026-03-26
**Rounds**: 3 / 5
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

## Output Files
- Review summary: `refine-logs/REVIEW_SUMMARY.md`
- Final proposal: `refine-logs/FINAL_PROPOSAL.md`
- Score history: `refine-logs/score-history.md`
- Round reviews: `refine-logs/round-1-review.md`, `refine-logs/round-2-review.md`, `refine-logs/round-3-review.md`
- Round refinements: `refine-logs/round-1-refinement.md`, `refine-logs/round-2-refinement.md`

## Score Evolution

| Round | Problem Fidelity | Method Specificity | Contribution Quality | Frontier Leverage | Feasibility | Validation Focus | Venue Readiness | Overall | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 8.5 | 7.5 | 7.0 | 8.0 | 8.5 | 8.0 | 6.0 | 7.8 | REVISE |
| 2 | 8.5 | 8.5 | 8.0 | 8.0 | 8.5 | 8.5 | 6.5 | 8.3 | REVISE |
| 3 | 8.8 | 9.0 | 8.3 | 8.5 | 8.7 | 8.7 | 7.5 | 8.6 | REVISE |

## Round-by-Round Review Record

| Round | Main Reviewer Concerns | What Was Changed | Result |
|---|---|---|---|
| 1 | proposal 更像 debugging checklist，operator 不够固定 | 冻结单一 stabilization operator，删掉 fallback 主线，压缩为 preflight + rerun | partial |
| 2 | preflight 仍有定性表达，仍像谨慎工程修复 | 将阈值、统计量、Huber 参数、acceptance rule 全部数值化 | resolved |
| 3 | pseudo-novelty 与复现细节还需加强 | reviewer 基本认可其为单一算法，但要求再补 mechanism justification 与 data interface details | partial |

## Final Proposal Snapshot
- Canonical clean version lives in `refine-logs/FINAL_PROPOSAL.md`
- Final thesis in 5 bullets:
  - raw controller-sensitive labels 不能直接拿来训练 forecast model
  - 必须先经过一个数值化的 preflight validity gate
  - 只有 preflight 通过后，才允许用固定 stabilization operator 构造 mixed-loss weights
  - 只跑一个 stabilized-CSFT rerun 就足够做 stop/go decision
  - 如果 preflight 或 acceptance rule 失败，就应该尽早 falsify 当前 raw-CSFT 路线，而不是继续扩算力

## Method Evolution Highlights
1. 从开放式“继续诊断 CSFT”收敛成单一算法：`preflight gate + fixed operator + one rerun`
2. 从定性流程改成完全数值化的 PASS/FAIL 方法描述
3. 明确放弃所有与当前问题无关的扩展：routing、RL、backbone zoo、bucketed fallback

## Pushback / Drift Log
| Round | Reviewer Said | Author Response | Outcome |
|---|---|---|---|
| 1 | 这更像 tuning + diagnostics，不像方法 | 冻结唯一 operator，不再列 transform 搜索空间 | accepted |
| 2 | preflight 仍有 narrative-style 判定 | 所有 preflight 和 acceptance 条件全部数值化 | accepted |
| 3 | 还差 mechanism justification 与接口定义 | 保留为最后剩余弱点，不再扩展方法本体 | accepted |

## Remaining Weaknesses
- 还需要补 2-3 句 mechanistic justification，解释为什么 `clip + log1p + per-sample normalize` 是合理 operator，而不是任意 recipe。
- 还需要在最终实现说明中冻结 horizon indexing、channel ordering、label storage 细节。
- 当前分数 8.6，说明路线已明显收敛，但还没有达到 READY。

## Raw Reviewer Responses

<details>
<summary>Round 1 Review</summary>

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

<details>
<summary>Round 2 Review</summary>

Below is a direct, method‑focused re‑evaluation per your requested checks and the same output format.

---

## Anchor / Focus Checks
- **Problem Anchor:** **Preserved.** You still target controller‑critical forecasting that improves downstream KPIs under the fixed controller.
- **Dominant Contribution:** **Sharper.** Now clearly a single operator + preflight gate, no fallback sprawl.
- **Method Simplicity:** **Simpler.** Fixed operator, fixed alpha, no alternative transforms or bucketed weights.
- **Frontier Leverage:** **Appropriate.** No forced modern primitives; that’s correct for a supervision‑quality bottleneck.

---

## 7 Scores (1–10)

1. **Problem Fidelity:** 8.5
2. **Method Specificity:** 8.5
3. **Contribution Quality:** 8.0
4. **Frontier Leverage:** 8.0
5. **Feasibility:** 8.5
6. **Validation Focus:** 8.5
7. **Venue Readiness:** 6.5

**OVERALL SCORE (weighted): 8.3 / 10**

---

## Weaknesses for Scores < 7

### Venue Readiness — **6.5**
**Specific weakness:**
Even with the fixed operator, the story can still read as “a gating check + stabilized weights,” i.e., an engineering fix rather than a crisp mechanism. The preflight’s “not catastrophically losing” criterion is still qualitative, which makes the method feel less like a pre‑registered algorithm and more like a cautious diagnostic.

**Concrete method‑level fix:**
Make the preflight gate fully **numerical and executable**:
- Define **oracle alignment tolerance** (e.g., max abs error ≤ 1e‑6 on first 20 steps).
- Define **top‑decile failure threshold** (e.g., raw‑CSFT top‑decile MAE worse than uniform by >5% → fail).
- Define **Huber delta** (e.g., delta = 1.0 or train‑residual P90) and **epsilon** for normalization.
This converts the “gate” into a reproducible algorithmic precondition, not a reviewer‑perceived checklist.

**Priority:** IMPORTANT

---

## Drift Warning
**NONE**

---

## Simplification Opportunities
1. **Drop MSE entirely from the core claims.** Keep MAE + KPIs only, to avoid dual‑metric ambiguity.
2. **Remove ramping from the critical metric set** unless it is part of the acceptance rule.
3. **Collapse preflight output to a single PASS/FAIL flag** used by the training script (no narrative checks).

---

## Modernization Opportunities
**NONE**

---

## Remaining Action Items (method‑level, minimal)
1. **Numericalize all preflight thresholds** (oracle tolerance, top‑decile fail threshold).
2. **Freeze Huber delta and epsilon** in the method spec.
3. **Specify how median_positive_train is computed** (global over train set? per‑channel? per‑sample?).
4. **Ensure deterministic evaluation** (fixed seed, fixed data slice) so the pre‑registered acceptance rule is unambiguous.

---

## Verdict
**REVISE**

You are close: the proposal is now focused and concrete. To clear the venue‑readiness bar, tighten the preflight to explicit numbers and freeze every remaining “small choice” so reviewers see a single, falsifiable algorithm rather than a careful tuning protocol.

</details>

<details>
<summary>Round 3 Review</summary>

**Anchor / Focus Check**
- **Problem Anchor:** **Preserved** (still about controller‑critical forecasting improving downstream KPIs under fixed controller).
- **Dominant contribution:** **Sharper** (single gate + single operator, no fallback branches).
- **Method complexity:** **Simpler** (fully specified, minimal knobs).
- **Frontier leverage:** **Appropriate** (no forced modern primitives; supervision‑quality is the bottleneck).

---

## 7 Scores (1–10)
1. **Problem Fidelity:** 8.8
2. **Method Specificity:** 9.0
3. **Contribution Quality:** 8.3
4. **Frontier Leverage:** 8.5
5. **Feasibility:** 8.7
6. **Validation Focus:** 8.7
7. **Venue Readiness:** 7.5

**OVERALL SCORE (weighted): 8.6 / 10**

---

## Weaknesses for Scores < 7
**NONE**

---

## Simplification Opportunities
**NONE** (already minimal and focused)

---

## Modernization Opportunities
**NONE**

---

## Drift Warning
**NONE**

---

## Remaining Action Items (method‑level, minimal)
1. **Neutralize pseudo‑novelty risk:** add 2–3 lines of *mechanistic justification* for the operator (e.g., clipping bounds influence; log1p yields sublinear sensitivity; per‑sample normalization makes weights scale‑invariant). This is not a new experiment; it is the missing mechanism story.
2. **Freeze the data interface details:** explicitly state how sensitivity labels are computed and stored (e.g., grid, horizon indexing, channel ordering), so the gate/weights are unambiguous to reproduce.
3. **Clarify the numerical scale for Huber (delta=1.0):** tie it to standardized targets (e.g., z‑scored per channel) or state the raw units so “1.0” is meaningful and not arbitrary.

---

## Verdict
**REVISE**

You now have a clean, algorithmic method with a clear go/no‑go gate. To reach READY, you still need a tighter mechanism justification and a fully specified data interface so the contribution reads as a reproducible algorithm rather than a careful but arbitrary recipe.

</details>

## Next Steps
- If continuing this line: run `/experiment-plan` or directly execute the numerical preflight + one stabilized rerun.
- If the preflight fails: do not scale CSFT; instead treat this as a falsification result and pivot.
- If the preflight passes but the acceptance rule fails: narrow the claim or stop this route early.
