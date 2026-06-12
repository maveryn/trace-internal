# `task_illustrations__park_playground__playground_equipment_count`

## Summary
- Domain: `illustrations`
- Scene id: `park_playground`
- Implementation scene: `counting`
- Implementation source: `trace/tasks/illustrations/counting/playground_equipment_count.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__park_playground__playground_equipment_count` -> `task_illustrations__park_playground__playground_equipment_count`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Counts visible playground-equipment items of one sampled type.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `climbing_frame_count` | `count(filter(playground_equipment, equipment_type(equipment)=target_equipment)); scene=park_playground; scope=playground_equipment_count; query_branch=climbing_frame_count` |
| `seesaw_count` | `count(filter(playground_equipment, equipment_type(equipment)=target_equipment)); scene=park_playground; scope=playground_equipment_count; query_branch=seesaw_count` |
| `slide_count` | `count(filter(playground_equipment, equipment_type(equipment)=target_equipment)); scene=park_playground; scope=playground_equipment_count; query_branch=slide_count` |
| `swing_set_count` | `count(filter(playground_equipment, equipment_type(equipment)=target_equipment)); scene=park_playground; scope=playground_equipment_count; query_branch=swing_set_count` |

## Program Metadata
- Program signatures: `count.single_attribute_membership`
- Base program contract: `count(filter(playground_equipment, equipment_type(equipment)=target_equipment)); scene=park_playground; scope=playground_equipment_count`
- Parameter axes: `fixed_query`
- Arguments:
  - `equipment`: semantic_role; allowed `playground_equipment_instance`; source `program_schema_concrete`
  - `playground_equipment`: semantic_role; allowed `visible_playground_equipment`; source `program_schema_concrete`
  - `target_equipment`: semantic_role; allowed `climbing_frame`, `seesaw`, `slide`, `swing_set`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `climbing_frame_count`, `seesaw_count`, `slide_count`, `swing_set_count`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a non-negative integer derived from the same execution trace as the annotation.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted/selected visual witness. Do not include labels, numeric annotations, or context-only regions.
- Annotation and answer must be projected from the same generated scene trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, and verifier payloads must be explicit in the instance trace.
- Distractor/context text may be rendered only when it is part of the scene grammar and must not be treated as annotation unless it is the queried visual witness.

## Review Artifacts
- Task review artifacts: `review/task-reviews/illustrations/park_playground/task_illustrations__park_playground__playground_equipment_count/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
