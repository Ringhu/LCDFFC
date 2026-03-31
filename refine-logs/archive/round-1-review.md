# Round 1 Review

## Context

本轮 review 针对的是 preflight failure 之后的新 pivot：

- 不是继续救 raw slot-wise CSFT；
- 而是把 raw controller relevance 压缩成一个更稳定的 global prior。

外部 reviewer 的核心意见很明确：

1. 这个 pivot 本身是连贯的；
2. 但如果 global prior 最终看起来只是一个 front-loaded heuristic mask，那么论文会塌成“controller-justified heuristic”；
3. 因此 pivot 必须进一步强调 **controller-specificity**，最好把 prior 建立在 QP 的解析梯度 / dual 信息上，而不是简单平均 finite-difference 权重。

## Parsed Scores

| Dimension | Score | Notes |
|---|---:|---|
| Problem Fidelity | 8 | 仍然紧扣 forecast-training-for-control 这个原始问题 |
| Method Specificity | 6 | prior 的统计定义、scale handling、alpha 等还不够冻结 |
| Contribution Quality | 6 | 有塌成 heuristic horizon mask 的风险 |
| Frontier Leverage | 4 | 当前更像 local patch，缺少与 decision-focused / controller-derived sensitivity 的更 principled 连接 |
| Feasibility | 9 | 低成本、可实现、与当前仓库兼容 |
| Validation Focus | 7 | 验证块不算散，但核心方法还不够强 |
| Venue Readiness | 5 | 还不够像顶会方法，除非 controller-specific prior 被立住 |

## Overall Score

**6.0 / 10**

## Verdict

**REVISE**

## Weaknesses Below 7

### Method Specificity — 6
- **Weakness**:
  `m_train`、`alpha`、channel scale handling 仍然不够明确，prior 还不完全是一个固定算法。
- **Concrete fix**:
  明确 prior 是 global 还是 per-channel normalized；固定 `alpha`；给出 channel-wise normalization，避免某个 channel 的 scale 直接泄漏到 prior。
- **Priority**: IMPORTANT

### Contribution Quality — 6
- **Weakness**:
  global prior 有塌成 hand-crafted horizon weighting 的风险。
- **Concrete fix**:
  用 **QP dual / analytic objective gradient** 代替简单的 raw finite-difference 平均，构造 controller-specific prior。
- **Priority**: CRITICAL

### Frontier Leverage — 4
- **Weakness**:
  当前写法太像 local patch，和更 principled 的 decision-focused/controller-gradient 连接不够。
- **Concrete fix**:
  增加一个简短 derivation：`G(h,c)` 近似最优控制目标对 forecast cell 的期望绝对梯度。
- **Priority**: IMPORTANT

### Venue Readiness — 5
- **Weakness**:
  如果 prior 最后和一个简单 front-loaded mask 很像，这条线会失去论文强度。
- **Concrete fix**:
  把方法主张改成 **controller-dual prior** 或 **controller-gradient prior**，并要求它在表征上明显不同于纯 horizon heuristic。
- **Priority**: CRITICAL

## Simplification Opportunities
- Drop top-K binarized prior from the main line.
- Remove redundant clipping if analytic dual/gradient prior is already smooth enough.
- Fix one alpha only; do not let this become another hyperparameter study.

## Modernization Opportunities
- 不需要引入 LLM / RL。
- 真正合适的 modern/principled move 是：用 **analytic QP gradients / dual variables** 替代 brute-force noisy raw finite differences。

## Drift Warning
如果 global prior 最终只是 generic short-horizon mask，那么方法会从“controller-aware supervision”漂移成“heuristic weighting with controller justification”。这属于需要避免的 drift。

## Raw External Response

<details>
<summary>Codex raw review</summary>

Below is a **method‑focused senior‑review** aligned to your constraints and the preflight failure.

---

## High‑level take
The pivot is coherent and genuinely anchored to the failure: it **compresses** the controller signal rather than trying to rescue raw per‑sample weights. That is a clean, minimal move.
**Main risk:** the global prior can collapse into a near‑heuristic horizon mask, making the contribution **too thin** for a top‑tier venue unless you show it is *controller‑derived* (not just “front‑loaded”). This is the critical pressure point.

---

## Scores (1–10)

1. **Problem Fidelity**: **8**
2. **Method Specificity**: **6**
3. **Contribution Quality**: **6**
4. **Frontier Leverage**: **4**
5. **Feasibility**: **9**
6. **Validation Focus**: **7**
7. **Venue Readiness**: **5**

**Overall Score (weighted)**: **6**

---

## Dimensions < 7: Weakness → Fix → Priority

### 2) Method Specificity — **6**
- **Weakness:** The prior construction is underspecified in key places: definition of `m_train`, how `alpha` is chosen, and whether `G(h,c)` is invariant to forecast scale across channels. This leaves the core method under‑determined.
- **Concrete method fix:**
  - Define `m_train` as **median(|s|)** per (h,c) or global median; state which and why.
  - Fix `alpha` to a **single constant** (e.g., 0.5) justified by the preflight gate, or compute it from a closed‑form heuristic (e.g., match the expected weighted MAE mass to uniform).
  - Add **channel‑wise normalization** for `s_(t,h,c)` before aggregation to avoid scale leakage (e.g., divide by baseline MAE per channel).
- **Priority:** **IMPORTANT**

### 3) Contribution Quality — **6**
- **Weakness:** Risk of being indistinguishable from a hand‑crafted horizon weighting; the novelty can collapse into a “controller‑justified heuristic” without a clear controller‑specific signature.
- **Concrete method fix:**
  Replace log‑aggregation with a **controller‑consistent sensitivity statistic**:
  - If `qp_carbon` is a QP, derive **dual variables or objective gradients** w.r.t. forecasted quantities and aggregate those as `G(h,c)`.
  - This keeps the same controller and data, but yields a **principled, controller‑specific prior** that is not arbitrary smoothing.
- **Priority:** **CRITICAL**

### 4) Frontier Leverage — **4**
- **Weakness:** No conceptual link to current decision‑focused forecasting literature; looks like a local patch.
- **Concrete method fix:**
  Add a **1‑paragraph derivation** (not extra modules) showing that `G(h,c)` approximates the expected absolute gradient of the controller objective w.r.t. each forecast cell, tying it to decision‑focused learning without changing the pipeline.
- **Priority:** **IMPORTANT**

### 7) Venue Readiness — **5**
- **Weakness:** As written, the paper may read as “we tried a smoother weighting and it helped,” which is too weak for NeurIPS/ICML/ICLR without stronger theoretical framing of why this is controller‑calibrated and not just heuristic.
- **Concrete method fix:**
  - **Explicitly show** in the method section that `G(h,c)` is *derived from controller sensitivities* and **differs measurably from any fixed horizon‑only heuristic** (e.g., show a two‑line table of correlation with heuristic mask or relative entropy vs. heuristic).
  - This is not an extra experiment; it is a **minimal method‑level characterization** of the prior.
- **Priority:** **CRITICAL**

---

## Simplification Opportunities
- **Drop the binarized top‑K prior** unless the continuous prior fails. It adds branching without adding conceptual strength.
- **Remove q95 clipping** if you already log‑compress and normalize; keep one compression mechanism only.
- **Fix alpha to a single constant** to avoid turning this into a hyper‑search paper.

---

## Modernization Opportunities (non‑sprawl)
- **Replace finite‑difference sensitivities with analytic QP gradients or duals** (if available).
  This is still *one prior*, not a new system, but it makes the method defensible and modern.

---

## Drift Warning
If `G(h,c)` ends up resembling a generic short‑horizon or manual mask, **the problem shifts** from “controller‑aware supervision” to “heuristic weighting with a controller justification.”
That **would be drift** from the anchored problem. Make sure the prior is demonstrably controller‑specific.

---

## Verdict
**REVISE**

The pivot is the right direction, but it must **prove controller‑specificity** at the method level to avoid collapsing into a heuristic. If you tighten the prior definition and ground it in controller gradients/duals, this can become a clean, publishable minimal‑mechanism paper.

</details>
