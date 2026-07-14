# RLVR Task Supervision Policy

This document defines how TRACE tasks choose their RLVR output and reward
mode. It is a training policy, not a public task, prompt, answer, or annotation
contract.

## Principle

Every active task has one fixed `trace_supervision_mode`:

- `answer`
- `answer_and_annotation`

The mode is assigned per task. Every generated row for that task uses the same
mode, while different tasks in the same scene may use different modes. Do not
infer the mode from domain or scene alone.

Use `answer` by default. Opt into `answer_and_annotation` only when annotation
adds useful grounding supervision beyond the answer itself. The existence of a
valid `annotation_gt` contract is not sufficient reason to train on it.

## Annotation Value Test

Annotation adds training value when it does at least one of the following:

- localizes the visible object, region, cell, mark, or control that is the
  answer;
- identifies exactly the visible objects contributing to a direct count;
- establishes useful correspondence between a semantic answer and image
  content;
- provides meaningful spatial partial credit among otherwise different
  rollouts.

Annotation does not add enough value when it only:

- marks the selected MCQ option or option panel;
- repeats information already encoded by the answer label;
- marks prompt-given points, an entire analytical-geometry shape, a whole
  panel, or another broad region that does not distinguish the answer;
- records a verbose collection of operands or intermediate steps after the
  answer has been computed;
- remains effectively constant across different valid answers or task
  instances.

## Canonical Decision Categories

`answer_and_annotation` has exactly two valid rationales:

- `visible_enumeration`: the annotation contains one compact witness for each
  directly counted visible item or relation. The witness collection must map
  cleanly to the answer units; do not add prompt references or unrelated
  boundary objects.
- `target_grounding`: the annotation localizes one answer-bearing visual
  target or a fixed small role-specific set whose spatial correspondence is
  material to the task.

`answer` uses these rationales:

- `derived_reasoning`: arithmetic, aggregation, ranking, inference,
  simulation, transformation, or other reasoning is the useful supervision;
- `redundant_option_annotation`: annotation only identifies a detached option
  or candidate panel;
- `redundant_context_annotation`: annotation marks broad containers,
  prompt-given operands, or extra context rather than answer units;
- `conservative_answer_default`: neither positive annotation rule is clearly
  satisfied.

Annotation wire types such as `point`, `bbox`, `segment`, sets, sequences, and
keyed maps do not determine the category. Judge the semantic role of the
annotation. If any supported query variant of one task fails the selected
annotation rule, the complete task uses `answer`.

## High-Confidence Assignment Rules

Assign `answer_and_annotation` when the task directly:

- locates or selects a visible object, region, cell, chart mark, or UI element;
- counts visible objects and the annotation marks exactly the counted set;
- reads a visible label or value from one naturally grounded target;
- answers a spatial-grounding question whose annotation identifies the
  relevant visible target or relation.

For charts, marking the final winner of an extremum, ranking, aggregate, or
candidate-wide comparison is not sufficient reason to use annotation. These
tasks are answer-only unless localization is itself a material spatial
operation, such as finding a threshold crossing, selecting the nearest visible
region or point, or choosing an option marker embedded in the plot.

Assign `answer` when the task primarily requires:

- MCQ or option-label selection;
- arithmetic, aggregation, comparison of derived quantities, formula use, or
  analytical geometry;
- symbolic inference, rule induction, transformation, simulation, or
  counterfactual reasoning;
- puzzle completion, game reasoning, or multi-step scientific reasoning;
- an annotation that is redundant, broad, or artificial under the annotation
  value test.

Direct shape counting or direct point/segment selection may still use
annotation. Geometry calculations, proofs, and geometry MCQs should normally
remain answer-only.

Reasoning difficulty alone does not forbid `target_grounding`. A game, puzzle,
geometry, or illustration task may use it when the answer is an actual labeled
cell, object, mark, or fixed spatial relation inside the primary scene. Do not
use it when annotation only repeats a detached option, marks every operand, or
boxes the final winner of a non-spatial aggregate.

For charts, keep derived numeric differences, totals, aggregates,
counterfactual values, ranks, extrema, and multi-mark calculations answer-only
when their annotations reproduce operands or only mark the final winner. A
direct value readout from one naturally grounded mark may use
`answer_and_annotation`.

Chart counts use `answer_and_annotation` only when each counted unit has a
compact visual witness, such as a mark point, relation segment, cell box, or
region location, and the witness collection corresponds directly to the
answer. Use answer-only for nested counts and for annotations made of broad
rows, panels, cards, or other containers that do not isolate the counted
primitive.

Treat option layouts by their visual role. Selecting from a separate MCQ
option panel is answer-only. Selecting an option marker embedded in the chart
itself may use `answer_and_annotation` when that marker is the actual visual
target rather than a redundant answer label.

For Three-D tasks, use `answer_and_annotation` for exact visible counts and
for selections whose annotation localizes the actual rendered object or marked
point in the 3D scene. This remains direct grounding when the answer is an
option letter, provided the annotation targets the scene object rather than a
separate option card. Keep arithmetic combinations, hypothetical edits or
transfers, and annotations that only record prompt-given operands answer-only.
Separate text cards, candidate boards, or candidate panels whose annotation
merely duplicates the selected option letter are also answer-only.

## Conservative Resolution

There is no unresolved mode in the policy manifest. During an audit, inspect
borderline extrema, paths, keyed maps, sequences, and heterogeneous witnesses
manually. If the task does not clearly satisfy `visible_enumeration` or
`target_grounding`, assign `answer` with `conservative_answer_default` rather
than preserving an ambiguous annotation assignment.

## Policy Artifact

The versioned task-to-mode manifest is
`rlvr/task_supervision/trace_supervision_policy_v1.json`. During the audit its
`status` is `draft`, and `reviewed_scenes` records the scenes whose complete
active task set has been assigned. A reviewed scene must not have unmapped
tasks. Unreviewed scenes remain visibly unreviewed; they do not inherit a
runtime default in the manifest.

Before release, every active public task id must appear exactly once and the
manifest status must be updated from `draft`. Record a review rationale
separately from the runtime mode so decisions remain inspectable.

Recommended audit fields:

```text
domain
scene_id
task_id
answer_schema
annotation_schema
program_code
representative_prompt
preliminary_mode
decision_rule
confidence
final_mode
manual_rationale
```

Rationale values are mode-specific and validated by
`trace.core.task_supervision_policy`; legacy or cross-mode values are invalid.

## Runtime Selection

The source dataset keeps both prompt variants and both ground-truth payloads.
The training loader selects the active prompt and reward mode from the task's
effective supervision mode:

| supervision mode | user prompt | required final payload | task reward |
| --- | --- | --- | --- |
| `answer` | `prompt_answer` | `{"answer": ...}` | answer |
| `answer_and_annotation` | `prompt_answer_and_annotation` | `{"answer": ..., "annotation": ...}` | normalized answer plus annotation |

`answer_gt` remains available in both modes. `annotation_gt` and
`reward_contract` remain stored for review and diagnostics even when a task is
trained in answer mode.

`task_conditioned` is a run-level policy, not a third row contract. For every
row, the loader resolves `trace_supervision_mode` and selects all three of the
following together:

- `answer`: `prompt_answer`, the answer system prompt, and answer reward;
- `answer_and_annotation`: `prompt_answer_and_annotation`, the annotation
  system prompt, and answer-plus-annotation reward.

Do not combine one row's prompt with the other mode's system prompt or reward.
There is no fallback when `trace_supervision_mode` is missing or invalid.

A training batch may contain both concrete modes. Each row is tokenized with
its own system prompt, and all rollouts for one GRPO prompt inherit that row's
same prompt and reward contract. Batch mixing does not change the per-prompt
advantage normalization.

Run-level modes preserve the earlier ablations:

- `answer`: force every row to `answer`;
- `answer_and_annotation`: force every row to `answer_and_annotation`;
- `task_conditioned`: use the versioned task mapping.

## Review And Validation Gates

Before training a task-conditioned run, verify:

1. the manifest covers the complete active task inventory with no stale ids;
2. every task has exactly one final mode;
3. all rows from one task resolve to the same mode;
4. selected user and system prompts match the resolved mode;
5. answer rows ignore annotation reward and require answer-only JSON;
6. annotation rows require and score both answer and annotation;
7. a mixed batch containing both modes passes reward and format tests;
8. assignment counts are reported by domain, program family, answer schema,
   and annotation schema without forcing an artificial 50/50 balance.

The browser review app scene table shows the current supervision schema,
rationale, and notes for every mapped task. Use that surface to inspect scene
consistency; an `unreviewed` row is a missing decision, not an answer-mode
default. The separate **Supervision mapping** audit checkbox records human
acceptance of the displayed decision. It defaults to unchecked and is required
for overall manual review completion.

Automatically assigned tasks still require scene-level spot checks. Every
ambiguous task requires an explicit manual decision before the policy is used
for a full run.

When policy decisions are re-audited, invalidate the separate human
**Supervision mapping** checkbox without changing other task-review gates:

```bash
python scripts/reset_task_supervision_review.py
python scripts/reset_task_supervision_review.py --apply
```
