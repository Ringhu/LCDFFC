# Final Proposal

**Date**: 2026-03-19  
**Verdict**: `REVISE, BUT STRONG AND FEASIBLE AFTER FOCUSING`

## Problem Anchor

The project should be framed around this problem:

> In exogenous sequential control, the desired tradeoff between cost, carbon, peak shaving, and resilience can change over time, but most learned or optimized controllers are tuned to one fixed objective and do not adapt cleanly without retraining.

This is the problem worth solving. It is sharper and more paper-worthy than "use forecasting plus control on CityLearn."

## Why the Current Idea Is Not Yet Mature Enough as a Paper

The current broad idea mixes too many layers:

- forecast + QP
- uncertainty-aware fallback
- decision-focused training
- LLM preference routing
- optional Grid2Op transfer

As an implementation roadmap, that is fine. As a first top-venue paper, it is too wide. The current repo already proves one important thing: the base `forecast + QP` loop is viable and now beats RBC in the validated local setting. That means the base loop should become the **platform**, not the main claimed novelty.

## Final Method Thesis

**Language-conditioned dynamic objective routing for forecast-then-control under preference shifts.**

More concretely:

1. keep the existing forecast + QP low-level controller fixed
2. summarize the current control context into a compact structured state
3. interpret a human-readable preference/instruction
4. output structured QP weights and constraints
5. adapt the controller online without retraining the low-level loop

## Dominant Contribution

The dominant contribution should be:

> A language-conditioned high-level routing mechanism that changes low-level optimization objectives and constraints online for exogenous sequential control.

This is stronger than claiming "we use an LLM in energy control." It also keeps the LLM in a role that is consistent with current engineering facts in the repo.

## Supporting Contribution

At most one supporting contribution should be kept:

> A deterministic structured fallback that guarantees safe and valid routing outputs when the language layer is uncertain or fails validation.

This supports deployability and robustness without creating a second paper.

## Explicitly Rejected Complexity

To keep the paper sharp, the following should **not** be primary claims in the same paper:

- a new forecasting backbone
- a full decision-focused training story
- uncertainty ensemble as a co-equal main contribution
- Grid2Op as a required second benchmark before the CityLearn story is finished
- LLM direct action generation

## Why This Thesis Is Feasible

This route is feasible because the repo already contains the necessary stable substrate:

- `data/prepare_citylearn.py`
- `data/dataset.py`
- `scripts/train_gru.py`
- `controllers/qp_controller.py`
- `eval/run_rbc.py`
- `eval/run_controller.py`
- `llm_router/prompt_templates.py`
- `llm_router/json_schema.py`

The missing piece is not a full new stack. The missing piece is a well-defined routing layer and the evaluation protocol that proves its value.

## Current Engineering Readiness

The engineering maturity is already respectable:

- the base loop is implemented
- local reproducibility exists
- the refined `learned forecast + QP` result beats RBC in the validated local setting
- diagnostics already exist for `learned / oracle / myopic`

This means the project is **mature enough to support a real paper iteration**, but **not mature enough to claim a final top-venue story today**.

## Novelty Assessment

### What is *not* novel enough

The following by themselves are not enough for top-venue novelty:

- GRU forecasting on CityLearn
- QP control on CityLearn
- beating RBC with a tuned forecast-control loop
- "LLM outputs objective weights" without a sharper claim

These are solid engineering milestones, but not yet enough novelty.

### What could be novel enough

This becomes potentially strong if the paper proves:

1. the controller can adapt online to changing high-level preferences **without retraining**
2. language is a meaningful interface, not just decoration
3. the low-level control quality remains competitive or better under those preference shifts
4. simpler alternatives do not fully explain away the gains

That novelty is not guaranteed yet, but it is plausible and defensible.

## Relation to Nearby Work

The refined idea sits between three clusters of prior work:

1. **CityLearn / hierarchical / optimization-based control**
   Existing CityLearn work already shows that optimization-heavy and hierarchical controllers can be competitive. So the paper should not claim novelty at the level of "forecast + control exists."

2. **Decision-focused learning**
   This literature motivates why predictive quality should be judged by downstream decision value, but it is not necessary to make DFL the main claim in the first paper.

3. **LLM for control / optimization / energy systems**
   Recent work suggests LLMs are most credible when they act as high-level planners, interfaces, or optimization assistants, not low-level numeric controllers. This supports the refined placement of language in the system.

Representative references for this assessment:

- CityLearn benchmark / environment: https://pypi.org/project/citylearn/
- CityLearn challenge winning optimization-style controller: https://jinming.tech/papers/2023-aaai-citylearn-winning-solution.html
- Hierarchical RL-MPC for cluster energy management: https://doi.org/10.1016/j.enbuild.2025.116879
- LLM-based interpretable building control: https://dblp.org/rec/journals/corr/abs-2402-09584
- Decision-focused energy management / robust optimization: https://doi.org/10.1016/j.apenergy.2025.127343

## What Would Make the Idea Feel CCF-A Ready

The paper would feel much more mature if it can say:

> We are not proposing a new low-level energy controller. We are proposing a new way to adapt an existing forecast-control stack to shifting human-level objectives online, using language as a structured control interface.

That is a clearer, sharper thesis than the current roadmap-style narrative.

## Final Recommendation

### Maturity
- **Current engineering maturity**: high enough to support a real paper iteration
- **Current paper maturity**: not yet mature enough as currently framed

### Feasibility
- **Base system feasibility**: yes
- **Refined paper feasibility**: yes, if the scope is narrowed as above

### Novelty
- **Current implemented novelty**: insufficient for a strong CCF-A paper
- **Refined proposal novelty**: potentially sufficient, but only if the paper isolates the language-conditioned adaptation claim and defends it against simpler alternatives

## Best Next Step

Do **not** broaden the system further first.

Instead:

1. freeze the low-level forecast + QP stack
2. implement a minimal routing layer
3. build a preference-shift evaluation protocol
4. test language against simpler structured routers

If those runs are positive, the idea becomes much closer to paper-ready.
