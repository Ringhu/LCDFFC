# Research Proposal: Refined Route After Review (Round 1)

## Problem Anchor
- Bottom-line problem:
  In exogenous sequential control, operator objectives can shift over time, but low-level controllers are usually tuned to one fixed reward tradeoff.
- Must-solve bottleneck:
  A forecast-control system that works under one fixed weight setting is not enough if the deployment setting requires changing emphasis between cost, carbon, peak reduction, and reserve behavior without retraining.
- Non-goals:
  No LLM direct action, no end-to-end RL as the primary contribution, no large benchmark sweep before the method is stable.
- Constraints:
  Start from the current CityLearn-based `forecast + QP` system that already beats RBC. Keep the low-level loop simple and reproducible.
- Success condition:
  Show that a single trained system can adapt to changing high-level textual preferences by routing solver objectives/constraints, while simpler alternatives are either weaker or less expressive.

## Technical Gap

Current CityLearn-style controllers usually fall into two camps:

1. fixed objective control or hand-tuned optimization
2. policy learning tuned to one reward specification

Both are weak when the desired objective changes online. The missing mechanism is not a larger low-level controller. The missing mechanism is a compact way to translate human-readable objective changes into the optimization layer without retraining the entire controller.

## Method Thesis

**One-sentence thesis**:
Use a language-conditioned high-level router to map compact scenario summaries and textual operator intent into QP objective weights and safety constraints, while keeping the low-level forecast + controller stack fixed.

## Contribution Focus
- Dominant contribution:
  Language-conditioned dynamic objective routing for forecast-then-control under preference shifts.
- Optional supporting contribution:
  A deterministic safety fallback / structured fallback when router output is low-confidence or invalid.
- Explicit non-contributions:
  Not claiming a new forecasting backbone, not claiming a new optimizer, not claiming a new RL algorithm.

## Proposed Method

### Complexity Budget
- Frozen / reused backbone:
  CityLearn environment, current feature extraction, current GRU forecaster, current QP controller.
- New trainable components:
  A small routing layer and, if needed, a lightweight LLM interface or distilled router.
- Tempting additions intentionally not used:
  Decision-focused retraining as the main story, uncertainty ensemble as a core claim, Grid2Op as a required primary benchmark.

### System Overview

```text
CityLearn observations
  -> compact scenario summary
  -> language-conditioned objective router
  -> QP weights / constraints / mode
  -> fixed GRU + fixed QP low-level control
  -> battery action
  -> CityLearn rollout
```

### Core Mechanism

The key mechanism is **not** "LLM makes decisions." The mechanism is:

1. summarize the current state and predicted near-future control context
2. condition on a textual preference such as
   - "cost first"
   - "carbon first"
   - "peak shaving under grid stress"
   - "reserve SOC for resilience"
3. route this into a structured output:
   - objective weights
   - optional hard constraints
   - operating mode
4. let the fixed low-level controller solve the actual action

This makes the paper about **adaptation of objectives**, not about replacing optimization with language.

### Modern Primitive Usage

- Primitive:
  LLM or distilled language-conditioned router
- Exact role:
  high-level preference interpreter and structured objective router
- Why this is more natural than a classic alternative:
  the key deployment argument is that operator intent can be expressed as human-readable instructions or changing policy goals without retraining the controller

### Integration into the Base Pipeline

The current repo already has the right low-level separation:

- GRU forecasts key exogenous signals
- QP consumes forecasts plus weights/constraints

The refined method inserts the router *above* the controller:

```text
summary + instruction -> router -> {weights, constraints, mode} -> QP
```

This preserves the existing working base loop and sharply limits extra complexity.

### Training Plan

1. Build synthetic or templated preference scenarios:
   - cost-priority
   - carbon-priority
   - peak-priority
   - reserve-priority
   - mixed or switching preferences
2. Start with a deterministic heuristic teacher that maps structured summaries to weights.
3. Use this to create a supervised routing dataset.
4. Compare:
   - hand-coded heuristic router
   - structured non-language learned router
   - language-conditioned router
5. Keep the low-level GRU + QP fixed during initial routing experiments.

### Failure Modes and Diagnostics
- Failure:
  language is unnecessary; a structured numeric router matches all gains.
  - Interpretation:
    downgrade the claim from "language-conditioned routing" to "preference-conditioned routing."
- Failure:
  the routing layer produces unstable or invalid control weights.
  - Mitigation:
    constrained JSON schema, deterministic fallback, and cached mode set.
- Failure:
  gains only appear in synthetic preference switches and not in realistic OOD or regime shifts.
  - Mitigation:
    restrict claims to controllable preference adaptation, not broad robustness.

### Novelty and Elegance Argument

This refined route is stronger because it makes a single mechanism claim:

> A forecast-control system can adapt its objective online from human-readable high-level preferences without retraining the low-level policy/controller.

That is narrower, more defensible, and more publishable than claiming new forecasting, new optimization, new uncertainty handling, and new language control all at once.

## Claim-Driven Validation Sketch

### Claim 1: Dynamic objective adaptation
- Minimal experiment:
  preference-shift episodes with changing cost/carbon/peak/reserve priorities.
- Baselines / ablations:
  fixed-weight controller, heuristic rule router, structured non-language learned router.
- Metric:
  KPI regret relative to the best preference-matched controller and switch adaptation quality.
- Expected evidence:
  the refined method adapts without retraining and beats fixed-weight controllers under shifting preferences.

### Claim 2: Language is useful enough to justify itself
- Minimal experiment:
  compare language-conditioned routing to equivalent structured preference encodings.
- Baselines / ablations:
  text router vs numeric preference vector router vs rule mapping.
- Metric:
  generalization to compositional or previously unseen preference descriptions.
- Expected evidence:
  language gives either better flexibility or lower manual engineering cost without hurting control quality.
