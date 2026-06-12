# `task_illustrations__single_object_figure__visible_part_count`

## Summary
- Domain: `illustrations`
- Scene id: `single_object_figure`
- Implementation scene package: `single_object_figure`
- Implementation source: `trace/tasks/illustrations/single_object_figure/visible_part_count.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__single_object_figure__visible_part_count` -> `task_illustrations__single_object_figure__visible_part_count`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Counts visible semantic parts on one single-object illustration.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `airplane_visible_wing_count` | `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count; query_branch=airplane_visible_wing_count` |
| `bicycle_visible_wheel_count` | `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count; query_branch=bicycle_visible_wheel_count` |
| `bird_visible_leg_count` | `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count; query_branch=bird_visible_leg_count` |
| `butterfly_visible_wing_count` | `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count; query_branch=butterfly_visible_wing_count` |
| `chair_visible_leg_count` | `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count; query_branch=chair_visible_leg_count` |
| `clover_visible_leaf_count` | `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count; query_branch=clover_visible_leaf_count` |
| `fork_visible_tine_count` | `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count; query_branch=fork_visible_tine_count` |
| `glove_visible_finger_count` | `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count; query_branch=glove_visible_finger_count` |
| `quadruped_visible_leg_count` | `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count; query_branch=quadruped_visible_leg_count` |
| `snowflake_visible_arm_count` | `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count; query_branch=snowflake_visible_arm_count` |
| `star_visible_point_count` | `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count; query_branch=star_visible_point_count` |
| `traffic_light_visible_lens_count` | `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count; query_branch=traffic_light_visible_lens_count` |

## Program Metadata
- Program signatures: `count.entity`
- Base program contract: `count(visible_parts(target_object, part_type)); scene=single_object_figure; scope=visible_part_count`
- Parameter axes: `fixed_query`
- Arguments:
  - `part_type`: semantic_role; allowed `arm`, `finger`, `leaf`, `leg`, `lens`, `point`, `tine`, `wheel`, `wing`; source `program_schema_concrete`
  - `target_object`: semantic_role; allowed `airplane`, `bicycle`, `bird`, `butterfly`, `chair`, `clover`, `fork`, `glove`, `quadruped`, `snowflake`, `star`, `traffic_light`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `airplane_visible_wing_count`, `bicycle_visible_wheel_count`, `bird_visible_leg_count`, `butterfly_visible_wing_count`, `chair_visible_leg_count`, `clover_visible_leaf_count`, `fork_visible_tine_count`, `glove_visible_finger_count`, `quadruped_visible_leg_count`, `snowflake_visible_arm_count`, `star_visible_point_count`, `traffic_light_visible_lens_count`

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
- Task review artifacts: `review/task-reviews/illustrations/single_object_figure/task_illustrations__single_object_figure__visible_part_count/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
