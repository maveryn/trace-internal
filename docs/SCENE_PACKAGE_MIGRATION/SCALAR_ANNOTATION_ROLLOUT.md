# Scalar Annotation Rollout

This rollout adds scalar annotation contracts for tasks with exactly one visual
witness. It applies across all domains, not only charts.

## Goal

Tasks that always ask for one point or one box should not encode that witness as
a one-item set. The public annotation contract should match the task contract:

- one point: `point` with value `[x, y]`
- one box: `bbox` with value `[x0, y0, x1, y1]`
- one line/edge/path segment: `segment` with value `[[x0, y0], [x1, y1]]`
- variable homogeneous witnesses: `point_set` / `bbox_set`
- multiple unordered line/edge/path witnesses: `segment_set`
- ordered homogeneous witnesses: `point_sequence` / `bbox_sequence`
- key-bound witnesses: map types

Do not use a map annotation just to avoid a one-item array. Map annotation is
for binding multiple semantic roles. A single selected object, endpoint, mark,
or region should use `bbox`, `point`, or `segment` directly, not a one-key
`bbox_map` or `point_map`.

Before deciding scalar versus set, choose the underlying geometry by the visual
primitive:

- area-like witnesses such as cells, tiles, board squares, cards, GUI controls,
  text boxes, page regions, bars, or image patches use bbox-family contracts;
- localized features or compact object centers such as chart marks, graph nodes,
  vertices, intersections, dots, balls, tokens, or pointer tips use point-family
  contracts;
- line-like witnesses such as edges, routes, row/column spans, shot paths,
  trend intervals, geometry sides, or vectors use segment-family contracts.

These defaults are repo-wide. Domain-specific annotation guidelines will refine
common cases, and task-specific exceptions are allowed when documented in the
task contract. Similar scenes inside a domain should not use different
annotation geometry for the same visual primitive without a documented reason.

## Contract Policy

Use scalar annotation only when the task contract guarantees exactly one
witness for every valid instance and every query id.

Use scalar annotation for:

- selected mark/interval/region center where one answer item is selected;
- selected object box where one answer item is selected;
- selected visual line, edge, or path segment where exactly one segment is the
  witness;
- single answer option mark when the option itself is the visual witness and no
  separate reference role must be bound.

Do not use scalar annotation for:

- count tasks, even if some answers are one;
- tasks where the number of witnesses can vary by sample;
- multi-segment paths, routes, ordered steps, or sequences;
- tasks with multiple semantic roles such as reference and selected item,
  source and target, input and output, or before and after;
- option-image tasks where reference and selected-option witnesses both need to
  be verified.

If a task currently uses `point_set` or `bbox_set` with exactly one item only
because scalar contracts did not exist, migrate it to `point` or `bbox`.
If a task currently uses a one-item `segment_set` for exactly one line, edge, or
path witness, migrate it to `segment`. Segment endpoint order is ignored by
reward scoring.

## Stage 1: Wire Core Contracts

Before changing tasks, add first-class public annotation types:

- `point`
- `bbox`
- `segment`

Update all core surfaces together:

- annotation type registry source;
- reward contract resolver;
- reward scorer normalization and scoring;
- annotation sanitization and projected annotation payloads;
- validation/export paths that check annotation types;
- review overlay/rendering paths if they need scalar display handling;
- docs/contracts reward and annotation tables;
- tests for scalar point and scalar bbox scoring, sanitization, validation, and
  export behavior.

The scalar scorer should match the existing one-witness behavior of the set
scorers without accepting extra witnesses. A scalar prediction is one point or
one box, not a list of points or boxes.

Do not update task prompts or task code until these public contracts are wired
and tested.

## Stage 2: Build The Inventory

After scalar contracts exist, inventory all active tasks across all domains.

For each task, record:

- domain and scene id;
- public task id;
- current annotation type;
- whether the task is scene-package review-ready or otherwise migrated enough
  to have current migration test status;
- whether the task contract guarantees exactly one point or one box;
- whether any query id changes witness count or role structure;
- proposed target annotation type.

Classify tasks as:

- `scalar_point_candidate`
- `scalar_bbox_candidate`
- `scalar_segment_candidate`
- `stay_set_or_sequence`
- `stay_map`
- `needs_manual_decision`

Use `scripts/inventory_scalar_annotations.py` for the Stage 2 static pass. By
default it reads `docs/ACTIVE_TASK_INVENTORY.md` and task docs without importing
the global task registry. It writes:

- `review/scalar-annotation/stage2_inventory.json`
- `review/scalar-annotation/stage2_inventory.md`

Direct task generation is optional and must be requested explicitly with
`--smoke-samples`; it is not part of the default static inventory.

Use current source, prompt assets, task docs, tests, and review artifacts. Do
not infer scalar eligibility from one sample. The contract must guarantee one
witness by construction.

## Stage 3: Update Tasks And Prompts

For every scalar candidate, update the task contract consistently:

- generated `annotation_gt.type`;
- generated `annotation_gt.value`;
- `projected_annotation` shape;
- prompt annotation instruction and example;
- task docs under `docs/tasks/<domain>/<scene_id>/<task_id>.md`;
- focused tests;
- taxonomy review metadata and app-visible annotation schema.

Prompt examples must show the scalar shape:

```json
{"annotation":[320,180],"answer":"B"}
```

or:

```json
{"annotation":[120,80,210,160],"answer":"B"}
```

or:

```json
{"annotation":[[120,80],[210,160]],"answer":"B"}
```

Keep the established prompt order for the domain. If the domain asks for
annotation before answer, keep that order.

For tasks that are not yet scene-package migrated, still update prompts,
examples, docs, and generator output when the task has a guaranteed single
witness. Do not wait for scene migration to remove one-item annotation arrays.

## Stage 4: Review State For Migrated Tasks

After scalar annotation contracts are introduced, annotation review must be
reset for every migrated task in the browser app, not only tasks that convert to
`point` or `bbox`. The reviewer needs to re-check that each migrated task either
uses scalar annotation where required or intentionally keeps a set, sequence, or
map contract.

Use `scripts/reset_scalar_annotation_review.py` for this reset. Run it once in
dry-run mode, then with `--apply` after checking the report. The script targets
active tasks whose scenes are registered as scene-package review candidates,
updates only existing review rows with `annotation_pass=true`, and writes reports
under `review/scalar-annotation/`.

For every migrated task:

- keep existing non-annotation statuses unchanged;
- set only the task-level human `Annotation` review checkbox/status to false;
- do not create audit rows for tasks with no review row; they already render as
  unchecked;
- preserve issue history and other review notes;
- regenerate task-review artifacts after the task passes its scene-scoped
  migration gates when the task prompt, annotation payload, or task review
  artifacts changed;
- reload the review app index after artifact changes.

Do not mark the annotation gate accepted. Human review must inspect the prompt,
image overlay, annotation payload, and samples after this rollout, including
tasks that remain on set, sequence, or map annotation contracts.

## Stage 5: Migration Checklist Integration

During every scene-package migration, the agent must verify scalar annotation
eligibility before generating task reviews:

- If a task always has exactly one point witness, use `point`.
- If a task always has exactly one box witness, use `bbox`.
- If a task always has exactly one line/edge/path segment witness, use
  `segment`.
- If a task can have zero, one, or many homogeneous witnesses, use a set.
- If a task can have zero, one, or many unordered line/edge/path witnesses, use
  `segment_set`.
- If a task has ordered witnesses, use a sequence.
- If a task has role-bound witnesses, use a map annotation.

This decision is part of taxonomy review because annotation schema is part of
the public task contract. A migrated scene must not pass taxonomy review while
using a one-item set for a guaranteed-single witness task.

Record this review in
`review/task-reviews/<domain>/<scene_id>/taxonomy_review_status.json` as
`checklist.scalar_annotation_checked=true`. `scripts/run_task_review.py` rejects
review artifact generation for registered scene-package review candidates when
that checklist bit is missing or false, or when static task-doc classification
still finds an automatic scalar point/bbox candidate.

## Validation Gates

The rollout is not complete until:

- scalar public contracts are registered and tested;
- no scalar-eligible task still asks for a one-item `point_set`, `bbox_set`, or
  `segment_set`;
- all affected prompts and task docs show scalar annotation examples;
- migrated affected tasks have fresh review artifacts;
- all migrated tasks have annotation human-review status reset;
- review app scalar overlays display correctly;
- `rg` checks show no prompt/doc wording that asks for an array/list/set when
  the task now uses scalar annotation.

Keep behavior changes focused on annotation shape. Do not combine this rollout
with task split/merge, solve-rate tuning, or renderer redesign unless a task is
blocked by the annotation change.
