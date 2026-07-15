# Templated Rationale Target Guidelines

This document defines the standard for adding metadata-generated rationale
targets to Trace. Rationale targets are optional synthetic response targets for
review, distillation, or later supervised/RLVR variants. They are not a
replacement for verifiers, annotation payloads, or final JSON answer contracts.

## Scope

Rationale targets may be generated for every public task and every internal
`query_id`, in both output modes:

- `answer_only`
- `answer_and_annotation`

Each mode should support two detail levels:

- `concise`: short explanation plus final JSON
- `detailed`: structured solution explanation plus final JSON

The initial implementation should store rationale targets in sidecar/review
artifacts, not in the `TrainInstance` ABI. Extend the training ABI only after a
separate decision on how these targets will be consumed.

## Query ID Alignment

Use `query_id` as the canonical field and **query id** as the prose term.
Do not use **task variant** for this feature; `task_id` remains the public
sampling unit.

For rationale generation, a query id is any task-internal branch that
requires a distinct rationale template family. This is now the practical test
for whether a branch needs its own `query_id`.

Required alignment:

1. Every active `query_id` must map to one rationale template family for each
   supported output mode and detail level.
2. A rationale template family may contain several wording variants, but they
   must explain the same reasoning structure.
3. If two branches stay inside the same public task but require different
   reasoning prose, operation order, annotation explanation, or answer transform,
   split them into different `query_id` values.
4. If two branches differ only by slot values inside the same reasoning
   structure, they may share a `query_id`; for example, a single template can
   use slots such as `{extremum_direction}`, `{axis_name}`, or
   `{comparison_operator}` when the reasoning steps stay identical.
5. Scene/render/style variants, object counts, labels, sampled numeric values,
   and difficulty knobs are not query ids unless they change the rationale
   template family.
6. Branches that require different algorithmic/objective families should be
   separate public tasks, not merely separate `query_id` values, even if their
   rationale templates could be written in the same prose style.

## Core Contract

Every rationale target must satisfy these rules:

1. The final response ends with exactly one valid JSON object.
2. No text appears after the final JSON object.
3. Final JSON keeps the existing output-mode schema:
   - `answer_only`: `{"answer": ...}`
   - `answer_and_annotation`: the current answer/annotation schema for that task.
4. The rationale text is generated only from task metadata, execution traces,
   verifier witnesses, and projected annotation. It must never infer from pixels.
5. The rationale cannot introduce facts that are not in the scene, prompt, or
   verifier trace.
6. The rationale cannot change task semantics, answer distribution, annotation
   format, prompt wording, solve-rate calibration, or reward calculation unless
   that use is explicitly approved.
7. Template choice must be deterministic by seed, task id, `query_id`, output
   mode, and detail level.
8. Template ids, bundle versions, selected variant indices, and slot values
   must be recorded in metadata.

## Recommended Response Shape

Use a stable structure so all domains can be inspected consistently.

Concise target:

1. Identify the requested scope or object.
2. State the decisive operation or comparison.
3. State the result.
4. Emit the final JSON.

Detailed target:

1. `Scope`: identify the visible region, item set, chart series, board cells,
   graph nodes, document fields, or other answer-bearing entities.
2. `Annotation`: name the values, labels, entities, or witness objects used.
3. `Operation`: describe the rule, arithmetic, ordering, comparison, traversal,
   lookup, or transformation applied.
4. `Check`: state the computed/selected result and, when useful, why competing
   candidates are not selected.
5. Final JSON.

Do not require these headings in every target. They are a design scaffold. Some
short tasks can use one or two natural sentences, but the same logical fields
must be recoverable during review.

## Length Guidelines

Rationale length is domain- and task-dependent. The repo-wide requirement is not
a fixed sentence count; it is that each domain defines what `concise` and
`detailed` mean for its own reasoning style before implementation.

Shared constraints:

- `concise` should include only the minimum reasoning needed to make the final
  answer auditable.
- `detailed` may include multi-step derivations when the task genuinely requires
  them, such as geometry theorem chains, physics equations, graph traversals, or
  long reconciliation lookups.
- Avoid long enumerations unless the task answer requires listing/counting many
  witnesses.
- Do not include pixel coordinates in prose unless the task itself asks for
  coordinates. Pixel-space annotation belongs in the final JSON annotation field.
- Do not include redundant restatements of the full prompt.

Each domain policy must set its own expected length profile and should include a
length smoke check before rationale targets are used for training.

## Template Assets

Rationale templates should be external assets, not hardcoded task-module text.
Use a structure parallel to prompt bundles:

```text
rationales/<domain>/<scene_id>/<bundle>.json
```

Each bundle should expose templates by:

- `task_key`
- optional `query_key`
- `output_mode`: `answer_only` or `answer_and_annotation`
- `detail_level`: `concise` or `detailed`

Slots should come from the same typed execution trace used to build the answer
and annotation. Prefer explicit slots such as:

- `target_label`
- `scope_label`
- `selected_values`
- `operation_expression`
- `computed_value`
- `comparison_candidates`
- `winner_label`
- `annotation_role_summary`
- `final_json`

Do not build rationales by string-parsing prompts.

## Metadata

Each generated instance with rationale targets should record:

- rationale bundle id and schema version
- selected template key and template index
- output mode and detail level
- task id, scene id, and `query_id`
- slot names and primitive slot values used by the template
- final rendered rationale text hash
- source trace fields used to populate rationale slots

If a rationale cannot be generated safely, record an explicit missing reason
instead of falling back to a generic explanation.

## Annotation-Mode Rules

For `answer_and_annotation`:

- The rationale should explain why the annotation objects are sufficient for the
  answer.
- The prose should refer to annotation semantically, such as selected bars,
  queried row cells, traversed path edges, counted icons, or chosen option
  panels.
- The final JSON remains the only place where the machine-verifiable annotation
  array appears.
- Annotation prose and JSON annotation must come from the same projected annotation
  trace.
- If the answer is `unanswerable`, the rationale must name the checked scope
  and the missing requested entity; annotation should follow the task's documented
  unanswerable annotation contract.

## Quality Gates

Before enabling rationale targets for a domain:

1. Render examples for every active task and every `query_id`.
2. Verify both output modes and both detail levels.
3. Parse the final JSON from every target with the same parser used by reward
   code.
4. Confirm final JSON equals the verifier ground truth.
5. Confirm annotation JSON equals the projected annotation ground truth in annotation
   mode.
6. Check that rationales do not mention hidden metadata names, internal ids,
   unsupported units, answer balancing, random seeds, or generation mechanics.
7. Check that no rationale says the model "looks at" an object that is only in
   private metadata and not visible in the image.
8. Run a length summary by domain, task, query, mode, and detail level.
9. Include representative rationales in scene review artifacts and inspect them
   in the browser review app before using them for any training experiment.

## Domain Adaptation Checklist

Each domain should add a short local rationale policy before implementation.
The policy should define:

- allowed operation verbs;
- preferred witness names;
- acceptable arithmetic notation;
- how to describe annotation;
- how to describe uncertainty or unanswerable branches;
- prohibited shortcuts that would make the task easier than the prompt.

The adaptation should be domain-level first, then scene/task-specific only when
needed.

### Charts

Use chart-native language:

- `read`, `compare`, `rank`, `sum`, `subtract`, `count`, `filter`, `trace`,
  `follow`, `aggregate`, `select`.
- Name chart roles explicitly: category, series, axis value, legend entry,
  panel, bin, region, flow, marker, interval, segment.
- For arithmetic tasks, include the exact expression when values are exact in
  metadata.
- For ranking/extremum tasks, list only the decisive candidates unless the task
  requires exhaustive comparison.
- For annotation mode, describe the selected marks, cells, regions, or panels;
  leave bbox arrays to final JSON.
- Do not imply visual readout precision beyond the rendered contract.

### Pages

Use document/layout language:

- section, card, row, field, form, item, status, timeline event, schedule block,
  process step, database table, concept-map node.
- Explain lookup path before arithmetic when both are involved.
- For cross-form tasks, name the matched keys/items and then the reconciliation
  operation.
- For process diagrams, distinguish visual order from graph reachability if the
  task is not meant to be graph-domain reasoning.

### Graph

Use graph-theoretic language:

- node, edge, neighbor, path, degree, component, reachable set, source, target,
  cut, flow.
- For traversal tasks, name the start condition and stopping condition.
- For optimization tasks, cite the witness structure, such as selected path,
  bottleneck edge, cut edge set, or matched nodes.
- Avoid decorative-layout language unless the task depends on spatial layout.

### Geometry

Use geometric construction language:

- point, segment, angle, polygon, circle, arc, radius, coordinate, slope,
  intersection, area, perimeter, symmetry, transformation.
- Separate visible givens from derived quantities.
- Show formulas only when the formula is part of the intended reasoning.
- For coordinate tasks, state graph-coordinate values in prose and keep
  pixel-space points in annotation JSON.

### Puzzles And Games

Use rule-state language:

- board, cell, row, column, piece, option, move, legal, forced, adjacent,
  matching, captured, reachable, path.
- State the visible rule being applied and the specific checked candidates.
- For multiple-choice/option tasks, explain why the selected option satisfies
  the rule; avoid over-explaining every distractor unless needed.

### Icons And Illustrations

Use object/attribute/relation language:

- object type, color, shape, orientation, row, group, reference, candidate,
  left/right/above/below, overlap, count.
- For relation chains, state the anchor object first and then the relation.
- Do not use natural-image claims beyond the synthetic object metadata.

### Physics

Use setup/rule/calculation language:

- component, force, torque, current, resistance, pressure, ray, lens, wave,
  proportionality, conservation, equilibrium.
- State the visible rule or diagram convention before applying it.
- Keep physical assumptions limited to the documented task rule.
- Include equations only when they are directly supported by the verifier trace.

## Implementation Order

1. Build the shared rationale asset schema and renderer.
2. Add parser tests that prove final JSON remains valid for all four target
   forms.
3. Add one pilot scene with all active `query_id` values covered.
4. Add scene-review sidecar fields for concise/detailed answer-only and
   answer+annotation rationale targets so the browser review app can display
   them.
5. Review the pilot manually.
6. Expand one domain at a time.
7. Only after all review gates pass, decide whether to expose rationale targets
   in training/export artifacts.
