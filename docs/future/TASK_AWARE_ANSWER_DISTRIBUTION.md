# Task-Aware Answer Distribution Policy Proposal

## Status

This is a non-normative future-version proposal. It does not change Trace's
current answer-distribution gates, task contracts, review workflow, calibration
workflow, or generated datasets.

The active Trace v0 policy remains defined by
`docs/workflows/BUILD_VALIDATION.md`: each query currently requires at least
four observed unique answers and a top-answer frequency below one third.

## Motivation

One global answer-distribution rule is easy to enforce, but it excludes useful
tasks whose valid answer spaces have fundamentally different shapes.

Examples include:

- a visual multiple-choice task with four options;
- an analytical-geometry measurement with dozens of numeric answers;
- an integer counting task with a compact range;
- a chart lookup returning labels from a broad vocabulary;
- a two-player game outcome with only two semantically valid answers.

These tasks should not be required to satisfy the same minimum support size or
maximum answer frequency. At the same time, Trace should not permit arbitrary
per-task thresholds that hide degenerate samplers. A future policy should use a
small, versioned catalog of semantic distribution profiles.

## Design Principles

1. Distribution requirements follow the answer program, not the domain name.
   A broad numeric measurement should use the same policy whether it appears in
   geometry, physics, charts, or another domain.
2. Every active task declares one distribution profile explicitly. The checker
   must not infer a permissive policy from an observed failure.
3. Profiles are centralized and versioned. Individual task configs must not
   carry arbitrary gate thresholds.
4. Review generation and exact calibration-parquet validation resolve the same
   profile and policy version.
5. Checks remain per query id as well as task-level summaries. Query variation
   must not conceal a degenerate branch.
6. A profile may relax one dimension only when the task's semantics require it.
   Binary outcomes can allow two answers, but must still demonstrate coverage of
   both outcomes.
7. Distribution acceptance is separate from solve-rate difficulty. A balanced
   task can still be too easy or too hard.

## Proposed Contract

Each public task should declare a stable profile identifier in task metadata
and its task documentation, for example:

```json
{
  "answer_distribution": {
    "profile_id": "integer_count_v1",
    "policy_version": "task_aware_distribution_v1"
  }
}
```

The profile declaration describes the semantic shape of the answer space. It
does not contain task-local thresholds. A central resolver maps the profile id
to validation rules.

The answer schema alone is insufficient for selecting a profile. An `integer`
can represent a compact count, a broad measurement, an option index, or a game
score. The task's program contract must therefore declare the intended profile.

## Initial Profile Families

The exact profile names and thresholds require a repository-wide audit. The
first policy should cover at least these semantic families:

| Profile family | Typical tasks | Intended policy shape |
| --- | --- | --- |
| Visual choice | MCQ and visual option panels | Require a minimum option count, normally at least four, and reasonable coverage of every option |
| Finite label | Named nodes, categories, states, or visible labels | Require broad label coverage and a low top-label frequency relative to the declared support |
| Integer count | Visible object, icon, edge, or event counts | Permit a compact count range while preventing one count from dominating |
| Broad discrete measurement | Analytical geometry, physics, and computed integer values | Require a substantially larger observed support and low answer concentration |
| Continuous or rounded number | Measurements rounded to a declared precision | Evaluate canonicalized values, range coverage, and concentration without treating insignificant floating-point differences as diversity |
| Binary or small outcome | Win/loss, player outcome, valid/invalid state, or other genuinely small semantic supports | Permit two or a few answers while requiring every declared outcome and limiting majority-class dominance |
| Ordered or ordinal label | Low/medium/high, direction, rank, or bounded state progression | Require coverage appropriate to the declared ordered support and guard against endpoint collapse |

Illustrative policy direction, not final thresholds:

- visual-choice tasks should normally expose at least four choices;
- broad numeric tasks may require dozens of distinct observed answers and a
  much lower top-answer frequency than compact counts;
- label tasks with a large source vocabulary should also have low answer
  concentration;
- compact integer counts may use a moderate concentration limit rather than a
  broad-numeric support requirement;
- genuine two-player outcome tasks may allow two answers and a majority
  frequency around three fifths, provided both outcomes occur sufficiently
  often.

These examples define the desired ordering of strictness, not approved numeric
constants.

## Declared Support And Observed Distribution

The future checker should distinguish three concepts:

1. **Semantic support**: all answers permitted by the task contract.
2. **Effective generation support**: answers reachable under the active scene
   and task configuration.
3. **Observed support**: answers present in the sampled review or calibration
   shard.

A task may have a large semantic vocabulary but reach only a few labels because
of a sampling bug. Conversely, a continuous numeric task may not have a useful
enumerable semantic support. Reports should retain these distinctions rather
than treating observed unique values as the complete answer space.

When finite support is declared, validation should report:

- declared support size;
- observed support size and coverage ratio;
- missing declared answers;
- top-answer count and frequency;
- frequency for every answer.

For broad or continuous numeric answers, validation should report:

- observed unique canonical values;
- top-answer frequency;
- numeric range and quantile coverage;
- fixed-bin concentration;
- precision or rounding contract used for canonicalization.

## Candidate Profile Semantics

### Visual Choice

The checker should use the actual option count recorded by the task rather than
assuming every label task is multiple choice. It should verify that:

- the option count meets the profile minimum;
- each option is correct in sampled instances;
- no option position dominates beyond the profile tolerance;
- answer labels are canonicalized independently of display style.

Option shuffling and balancing remain generator responsibilities. A checker
must not repair an imbalanced option sampler.

### Finite Labels

This profile covers semantic or visible string labels, not option letters. It
should be stricter when the task declares a large eligible label pool. The
report should expose whether poor diversity comes from a small eligible scene
pool or from coupled sampling logic.

### Integer Counts

Count tasks commonly have meaningful supports such as `1..5` or `1..10`. They
should not need dozens of answers, but one count should not dominate the task.
The policy can combine minimum support coverage with a moderate maximum
frequency rule.

Zero may be included when it is semantically useful. It must not be added or
removed merely to satisfy the checker.

### Broad Numeric Measurements

Analytical measurements and calculations should demonstrate much broader
answer diversity than ordinary counts. A future profile may require roughly
dozens of canonical values, low repeated-answer frequency, and useful coverage
across the numeric range.

This policy should apply by reasoning contract, not by a hardcoded geometry
domain exception.

### Binary And Small Outcomes

This profile enables tasks such as winner/loser or two-player gameplay
outcomes. It replaces the current implicit exclusion of two-answer tasks with
an explicit contract that checks:

- the declared support is genuinely small for semantic reasons;
- every outcome is observed;
- the majority outcome remains below a profile-level dominance limit;
- the task does not collapse to a constant under one query branch or config.

The checker must never automatically switch to this profile merely because it
observed only two answers. The task author must declare it, document why the
small support is intrinsic, and pass taxonomy review.

## Policy Resolution

The central policy catalog should resolve rules from:

```text
policy version
  + distribution profile id
  + declared answer schema
  + declared support metadata, when finite
  + review sample size
```

Domain and scene ids may be included in reports, but should not select the
policy. Task-local config values must not override central thresholds.

Sample-size handling should be systematic. Small random shards naturally
deviate from ideal frequencies, especially for four-choice tasks. A future
implementation should choose one documented approach, such as:

- profile-specific deterministic tolerances at approved sample sizes; or
- confidence intervals around the expected/support-constrained frequency.

It should not retain one-off exceptions for particular tasks or answer counts.

## Tooling Changes

The future rollout should update all distribution consumers together:

- task and program-contract schemas;
- task documentation template;
- answer-distribution evaluator;
- task-review generation;
- review-app distribution display;
- exact calibration-parquet preflight;
- dataset build validation;
- distribution tests and fixtures;
- generated reports and status artifacts.

Every report should record:

```json
{
  "distribution_policy_version": "task_aware_distribution_v1",
  "distribution_profile_id": "integer_count_v1",
  "resolved_rules": {},
  "observed_metrics": {},
  "pass": true
}
```

This makes acceptance reproducible even after a later profile version changes.

## Migration Plan

### Phase 1: Inventory And Classification

1. Inventory every active task's answer schema, semantic support, query ids,
   and current observed distribution.
2. Propose one profile for every task.
3. Review ambiguous cases where identical answer types represent different
   semantics.
4. Identify tasks that currently pass only because the global gate is weak for
   their answer family, as well as useful tasks currently excluded by it.

### Phase 2: Versioned Profile Catalog

1. Define the smallest profile set that covers active and planned tasks.
2. Select profile-level metrics and candidate thresholds from repository-wide
   empirical distributions.
3. Add profile ids to the task/program metadata and task-doc schema.
4. Add validation that rejects missing or incompatible profile declarations.

### Phase 3: Shadow Evaluation

1. Keep the Trace v0 global gates authoritative.
2. Run the task-aware policy in report-only mode over all tasks and exact
   calibration shards.
3. Compare false acceptance, false rejection, sampling variance, and per-query
   behavior.
4. Adjust only central profile definitions; do not add task-local exceptions.

### Phase 4: Versioned Activation

1. Activate the new policy under an explicit contract or dataset version.
2. Make task review, build validation, and calibration use the same resolver.
3. Reject tasks with missing profile metadata.
4. Remove superseded global-gate exceptions and compatibility behavior.

### Phase 5: New Task Families

After the policy is stable, reconsider task families that were previously
blocked only by the global minimum-unique-answer rule, including genuine
binary gameplay outcomes. These tasks still require normal taxonomy, visual,
prompt, annotation, distribution, and solve-rate review.

## Acceptance Gates

The task-aware policy is ready to replace the global gates only when:

- every active task has one reviewed profile assignment;
- profile selection depends on semantic contracts, not domain-specific special
  cases;
- review and calibration resolve identical policy versions and rules;
- finite-support and numeric tasks have appropriate, distinct diagnostics;
- no checker infers a relaxed profile from observed degeneracy;
- sample-size behavior is documented and tested;
- reports preserve resolved rules and policy versions;
- shadow evaluation covers every active task and query id;
- adding a binary-outcome task no longer requires weakening distribution rules
  for unrelated tasks.

## Open Decisions

The implementation phase must still determine:

- the final profile catalog and naming;
- exact thresholds for each profile;
- whether finite-support balance uses fixed tolerances or statistical tests;
- minimum approved review sample sizes by profile;
- canonicalization rules for rounded numeric answers;
- how support coverage should behave when scene constraints make some declared
  answers unreachable;
- whether outcome tasks should target uniform outcomes or preserve a documented
  natural game-state prior.

These decisions should be based on an all-task empirical audit rather than the
examples in this proposal.

