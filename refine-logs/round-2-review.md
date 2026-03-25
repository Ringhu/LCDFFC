# Round 2 Review (Codex External Review)

## Context

这轮 review 不再围绕 language router 主线继续扩，而是先判断主论文该不该 pivot。

外部 reviewer 的核心结论很直接：

- 第一篇更强的锚点不是 language-conditioned routing。
- 更强的锚点是 **controller-sensitive forecast refinement**。
- 当前 routing 结果还不足以支撑顶会主线，除非 text router 明显超过 numeric 和 fixed baselines。
- 现有仓库最有价值的部分，是已经跑通的 `forecast -> fixed QP -> CityLearn` 基础设施，以及 controller-family / backbone diagnosis 给出的稳定信号。

## Round 2 Review — Part A

<details>
<summary>External raw response: anchor choice and claim map</summary>

## Recommended anchor

**Anchor A, but sharpened**:
**Controller-sensitive forecast refinement for fixed forecast→QP control**.

**Why this is the best first paper**
- It matches the real bottleneck: **forecast error is not equally important for downstream control**.
- It gives you a **real ML contribution**, not just a system assembly.
- It uses your current repo exactly as it should be used: **stable infrastructure + evaluation harness**, not fake novelty.
- It avoids the biggest current weakness of Anchor B: **you have not shown language is necessary**.

**My ranking**
1. **A (best)**: controller-critical forecast refinement
2. **Third backup**: structured **preference-conditioned expert routing** *without* language as main claim
3. **B as currently framed**: language-conditioned routing

**Bluntly:** the current B story is **not yet a NeurIPS/ICML main-track story**. It becomes viable only if **O1** happens cleanly.

---

## Scores table

**For the direction I recommend: sharpened Anchor A**

| Dimension | Score |
|---|---:|
| Problem Fidelity | 9/10 |
| Method Specificity | 7/10 |
| Contribution Quality | 7/10 |
| Frontier Leverage | 6/10 |
| Feasibility | 8/10 |
| Validation Focus | 7/10 |
| Venue Readiness | 6/10 |
| **OVERALL SCORE** | **7/10** |

**Interpretation:** promising, but **not ready**.
If you keep B as the main thesis today, I’d put it closer to **5/10 overall**.

---

## Verdict

**REVISE**

The repo is a **good platform**.
It is **not yet a good top-venue paper** until you compress it into **one sharp claim**.

---

## Main weaknesses

### 1. The current novelty is too “wrapper-like”
Right now the strongest story sounds like:

> “We already have forecast + QP; now we add a router over weights.”

That is usually **not enough** for a top venue unless the empirical win is very strong and the setting is clearly important.

### 2. Language is not yet justified
Your own signals already say:
- text/numeric routers are mixed
- text does not clearly dominate numeric
- fixed experts remain hard to beat
- regime-wise oracle is still above you

A reviewer will ask:
**Why is this an LLM paper at all? Why not a small parser or numeric preference vector?**

### 3. The benchmark story is still too easy to dismiss
Current risks:
- preference shifts may look synthetic
- fallback corruption is weak
- CityLearn-only evidence can look narrow
- strong fixed controllers may already absorb most gains

That makes the paper feel like **benchmark engineering**, not scientific insight.

---

## Minimal experiment package

### If you follow my recommendation (Anchor A)

### Core method
Implement **one** small method only:

**Controller-sensitivity-weighted forecast loss**
- fixed low-level QP controller
- compute which forecast horizons/channels matter most to downstream objective
- weight forecast training accordingly

Use the **smallest adequate mechanism**:
- finite-difference sensitivity or
- dual/saliency-derived importance from the QP

Do **not** build a large end-to-end differentiable system.

### Baselines
Only these:
1. **Vanilla uniform forecast loss**
2. **Heuristic horizon weighting**
   - later horizons or manually chosen control window
3. **Heuristic channel weighting**
   - manually chosen exogenous channels
4. **Your proposed controller-sensitivity weighting**

If you have time for one more, add a **small-scale decision-focused baseline**.
If not, don’t let that block the first pass.

### Models
- **1 strong trainable classic backbone**
- **1 foundation-backed variant only if adapter/fine-tuning is already easy**
- If not easy, **skip it**. Don’t burn the week there.

### Evaluation
- **1 main controller**: likely `qp_carbon` since it already looks strongest
- **3 seeds**
- **2 scenario families**:
  1. standard evaluation episodes
  2. stress slices with high carbon / high price periods

### Metrics
Report both:
- **forecast metrics** by horizon/channel
- **downstream KPIs**: at least cost, carbon, peak

### Must-have analysis
These matter more than extra benchmarks:
1. **Show downstream gains at matched or near-matched forecast error**
2. **Show improvements concentrate on controller-critical windows/channels**
3. **Show the controller sensitivity map is predictive of useful error reduction**

### Do **not** spend GPU week on
- fallback corruption
- free-form text generation
- Grid2Op transfer
- new optimizer
- end-to-end RL
- many backbones

---

## Results-to-claims matrix

| Outcome | What is still defensible | What to drop |
|---|---|---|
| **O1**: text router clearly beats all fixed and numeric baselines | **Constrained language-conditioned expert routing** can adapt objectives online without retraining low-level control | Drop any claim about open-ended language reasoning or free continuous text→weight generation unless directly proven |
| **O2**: text matches numeric, both beat fixed | **Preference-conditioned routing works**; language is a usable interface | Drop “language is the key innovation” |
| **O3**: numeric beats text, both modestly beat fixed | **Structured preference routing** may help; language is not needed | Drop LLM-centric thesis entirely |
| **O4**: no router beats strongest fixed | Little paper-level claim survives for B | Drop routing as main thesis; pivot to A |

---

## If needed, alternative thesis

Yes: **language is probably not the right main thesis**.

### Better paper thesis
> **Uniform forecast accuracy is the wrong training target for forecast-then-control.
A controller-sensitive forecast objective improves downstream energy control without changing the controller.**

Why this fits your codebase:
- you already have the full forecast→control loop
- you already know controller choice changes downstream KPIs
- you already support multiple forecast backbones
- you do **not** need to pretend LLM is central

### What B becomes under this thesis
- motivation
- appendix
- or a separate smaller paper/workshop submission:
  - “preference-conditioned expert routing”
  - **not** “LLM energy control”

---

## Final recommendation in 5 bullets

- **Make Paper 1 about Anchor A**, not language routing.
- Treat the current forecast+QP stack and routing harness as **engineering base, not novelty**.
- If you keep B alive, reframe it as **preference-conditioned expert routing**, and only if **O1/O2** happens.
- Your highest-lift experiment is **one controller-sensitive forecast loss + tight causal analysis**, not more prompt variants.
- Kill weak side claims now: **fallback robustness, open-ended language control, giant roadmap, multi-domain transfer**.

</details>

## Round 2 Review — Part B

<details>
<summary>External raw response: concrete method choice for the pivot</summary>

## 1. Strongest minimal method formulation

### Recommendation: **A1**
**Finite-difference controller sensitivity per forecast slot/channel, used as loss weights.**

This is the cleanest and strongest formulation for this repo.

### Why A1 is the right choice
- It **directly matches the thesis**: some forecast errors matter more because they change control.
- It keeps the controller **fully frozen**.
- It avoids full differentiable decision-focused training.
- It is **mechanistic**, not heuristic.
- It is small enough to be a paper.

### Reject the others
- **A2 event-window weighting**: good baseline, **not good main method**. Too heuristic. A reviewer will say “you hand-coded the answer.”
- **A3 hybrid**: reasonable engineering fallback **if A1 is too noisy**, but worse as the main thesis because it muddies the contribution.
- **A4 local regret weighting from short rollouts**: too close to full decision-focused training, more compute/noise, not worth it for Paper 1.

### Short version
Start with **A1 as the paper method**.
Use **A2 as a baseline**.
Keep **A3 only as fallback** if A1 is unstable in pilot runs.
Do **not** lead with A4.

---

## 2. Exact small-but-paper-worthy method package

## Method name
Something like:

**Controller-Sensitive Forecast Training (CSFT)**

---

## What is frozen
- CityLearn environment
- data pipeline
- forecasting architecture/backbone
- controller structure
- controller weights/objective
- main controller choice: **`qp_carbon`**

No retraining or modification of the low-level controller.

---

## What is new
One offline label-generation step + one weighted forecast loss.

### New signal
For each training sample and each forecast cell `(horizon h, channel c)`, compute a **local controller sensitivity score**.

Let:
- `x_t`: current context/state
- `y_t ∈ R^{H×C}`: true future exogenous trajectory
- `π_qp(x_t, y)` = first action from frozen `qp_carbon` using forecast `y`

For each `(h,c)`:
1. Perturb the true future at that cell:
   - `y+ = y_t + δ_c e_{h,c}`
   - `y- = y_t - δ_c e_{h,c}`
2. Re-solve the frozen QP twice:
   - `a+ = π_qp(x_t, y+)`
   - `a- = π_qp(x_t, y-)`
3. Measure how much the executed control-relevant quantity changes.

### Recommended sensitivity target
Use **first-action stage-loss sensitivity**, not full rollout regret.

\[
s_{t,h,c} = \frac{| \ell_t(a^+) - \ell_t(a^-) |}{2\delta_c}
\]

where `ℓ_t` is the one-step control objective induced by `qp_carbon` at time `t`
(cost/carbon/peak penalty as used by the controller).

This is better than pure action-distance because it stays tied to the objective.

---

## What labels/signals are computed offline
For every training sample:
- a sensitivity map `S_t ∈ R^{H×C}`
- optional normalized version `Ŝ_t`

### Normalization
You should normalize/clamp, otherwise weights will be noisy.

Recommended:
1. clip `s_{t,h,c}` at the training-set 95th percentile
2. normalize within sample:

\[
\tilde{s}_{t,h,c} = \frac{s_{t,h,c}}{\epsilon + \frac{1}{HC}\sum_{h,c}s_{t,h,c}}
\]

This keeps average weight scale stable.

Use `δ_c = 0.1 × std(channel c)` or similar channel-scaled perturbation.

---

## Training loss
Use a **mixed** loss, not pure weighted loss.

\[
L_t
=
\alpha \sum_{h,c} \ell_{pred}(\hat y_{t,h,c}, y_{t,h,c})
+
(1-\alpha)\sum_{h,c}\tilde{s}_{t,h,c}\,\ell_{pred}(\hat y_{t,h,c}, y_{t,h,c})
\]

Recommended:
- `ℓ_pred`: Huber or MAE
- `α`: start at **0.5**

Why mixed:
- pure sensitivity weighting can overfit rare spikes
- mixed loss preserves baseline forecast quality while shifting capacity toward control-critical cells

---

## Key diagnostic plot
### One plot I most want to see:
**Forecast error reduction vs controller-sensitivity decile**

- bucket forecast cells by sensitivity decile from the offline labels
- compare uniform-loss model vs CSFT
- y-axis: RMSE/MAE reduction
- x-axis: sensitivity decile

**Expected pattern:**
little change in low-sensitivity cells, clear improvement in top deciles.

That plot is more convincing than a raw heatmap.

Secondary plot:
- average horizon×channel sensitivity map under `qp_carbon`

---

## 3. Minimal experiment package

This is the smallest package that would make me take it seriously.

## Main setup
- **One primary forecasting backbone only**
  - pick the strongest stable trainable one already in repo
- **One fixed controller only for main claim**
  - `qp_carbon`

Do not do a backbone zoo.

---

## Exact baselines
### Main baselines
1. **Uniform-loss forecaster**
   same backbone, same training budget
2. **Manual horizon-weighted loss**
   simple control-window prior
3. **Event-window weighting (A2)**
   top price/carbon/peak windows upweighted
4. **Proposed CSFT (A1)**

### Context-only references
5. **Perfect-forecast upper bound** under `qp_carbon`
6. **Naive/persistence forecast** under `qp_carbon` if already cheap

---

## Exact ablations
These matter more than extra datasets.

1. **Local vs mismatched-controller labels**
   - train CSFT using `qp_carbon` sensitivities
   - train same method using `qp_current` sensitivities
   - evaluate both under `qp_carbon`

This is extremely important. It tests whether the method is really controller-specific.

2. **Mixed loss vs pure weighted loss**
   - `α=0.5` vs `α=0`

3. **Event-only vs finite-difference**
   - shows heuristics are not enough

If budget is tight, these 3 ablations are enough.

---

## Exact splits / scenario types
Use **one main CityLearn setup only**.

### Split
Chronological split, not random:
- train: first 70%
- val: next 10%
- test: final 20%

### Test subsets
Report three test views:
1. **Standard test**
2. **Carbon/price stress subset**
   - timesteps/windows where carbon intensity or price is above training 90th percentile
3. **Peak-load stress subset**
   - timesteps/windows where district load is above training 90th percentile

This is enough. Do not add Grid2Op or extra domains.

---

## Exact metrics
### Forecast metrics
Report:
- overall RMSE/MAE
- **top-sensitivity-decile RMSE/MAE**
- optional per-horizon summary if cheap

### Control metrics
Report at least:
- **total cost**
- **total carbon**
- **peak load**

If the repo already uses an aggregate CityLearn score, include it as secondary only.

---

## What result pattern moves my score from 7 → 8.5+
I would become genuinely interested if you show:

1. **Consistent downstream gains**
   - e.g. `CSFT` improves **carbon by ~5%+**
   - and **cost by ~3%+**
   - with no major peak degradation

2. **Heuristic baselines lose clearly**
   - beats horizon weighting and event-window weighting by a meaningful margin

3. **Mechanism is validated**
   - overall RMSE changes little
   - but **high-sensitivity decile RMSE improves a lot** (say 10%+)

4. **Controller-specificity shows up**
   - `qp_carbon`-labeled training helps `qp_carbon`
   - mismatched-controller labels help much less

5. **Gap-to-oracle closes nontrivially**
   - closes ~25%+ of the downstream gap between uniform forecast and perfect forecast

If you get that pattern, this becomes a serious paper.

---

## 4. Should routing stay in the main paper?

### Recommendation: **include a tiny appendix/motivation experiment only**
Not a secondary claim.

Why:
- routing is a different paper
- it will dilute the thesis
- you do not yet have strong evidence that language is necessary

### Best use of routing in this paper
At most:
- one appendix figure showing that different controller objectives induce different sensitivity maps
- or one short note that objective shifts motivate future objective-conditioned CSFT

But **no routing performance table in the main results**.

If space is tight: cut it entirely.

---

## 5. Mock top-venue review for the pivoted paper

### Summary
This paper studies forecast-then-control for energy management and argues that uniform forecast error is a poor training target when downstream control is performed by a fixed MPC/QP controller. The authors propose controller-sensitive forecast training, where each forecast slot/channel is weighted by an offline finite-difference estimate of how perturbations affect the frozen controller’s one-step objective. Experiments on CityLearn with a fixed `qp_carbon` controller show modest but consistent improvements in downstream cost/carbon metrics over uniform-loss training, while overall forecast error changes only slightly. Additional analyses suggest gains concentrate on control-sensitive forecast cells.

### Strengths
- Clear and relevant problem formulation
- Good decision to keep controller fixed; avoids confounding from co-training
- Method is simple and reasonably elegant
- Mechanistic evaluation is stronger than typical “better forecast, better control” claims
- Controller-matched vs mismatched sensitivity analysis is a strong diagnostic if included

### Weaknesses
- Experimental scope is still limited: effectively one environment and one main controller
- Improvements are moderate, not decisive
- Sensitivity labels require many offline QP solves; computational overhead is not fully analyzed
- No theoretical characterization of when local sensitivity weighting should help
- Generalization beyond CityLearn remains unclear

### Score
**6/10 — borderline / weak accept to weak reject depending reviewer pool**

### Confidence
**4/5**

### What would move it toward accept
- stronger matched-vs-mismatched controller evidence
- clearer gains on stress subsets
- one additional robustness check beyond the main setup
- stronger proof that gains come from reallocating forecast accuracy, not just lucky training variance
- modest compute-cost analysis for label generation

---

## Bottom line

- **Choose A1**
- **Do not lead with A2/A3/A4**
- **Keep the controller frozen**
- **Make controller-matched sensitivity the core empirical story**
- **Keep routing out of the main claim**

</details>
