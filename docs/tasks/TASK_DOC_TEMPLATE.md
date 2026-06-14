# `<task_id>` Task Doc Template

## 1) Identity
1. Domain:
2. Scene id:
3. Task id:
4. Objective contract:

## 2) Scene + task contract
1. Entities/relations:
2. Supported `query_id` values:
3. `answer_gt.type`:
4. Default `annotation_gt.type`:
5. Alternate annotation forms:
6. Annotation witness policy:
   - minimal object/primitive witnesses:
   - annotation shape choice (`point_set`, `bbox_set`, `point_pair_set`,
     `keyed_point_map`, `keyed_bbox_map`, etc.):
   - keyed annotation role names, if used:
   - numeric/readout annotation handling:
   - answer-option annotation policy (only allowed for complete visual
     option-image/panel tasks with a source/reference/original image or
     region; otherwise ground source/candidate objects or primitives):
7. Overlap/touch policy (if applicable):

## 3) Prompt contract
1. `prompt_bundle_id`:
2. `scene_key`:
3. `task_key`:
4. Optional query-id prompt mapping (`query_key` or slot-driven mapping):
5. Required slots:
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `json_output_contract`, `annotation_hint`, `answer_hint`, `json_example`
6. JSON example validity rule: every documented prompt JSON example must be a valid response for the active task/variant/output mode (keys, value types, and annotation cardinality/semantics).
7. Variant counts (scene/task/query-id/mode):
8. Output modes:
   - `answer_only`
   - `answer_and_annotation`

## 4) Determinism + constraints
1. Seed namespaces used:
2. Unique-answer policy:
3. Reject/resample conditions:
4. No-auto-relaxation guarantee:

## 5) Tests
1. Determinism test:
2. Answer/annotation consistency test:
3. Prompt metadata/placeholder test:
4. Constraint-specific tests:

Do not include review status, solve-rate status, migration history, stale task ids, or stale compatibility routing unless they are part of the durable public task contract.
