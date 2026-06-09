# `task_illustrations__pixel_village__person_path_count`

## Summary
- Domain: `illustrations`
- Scene id: `pixel_village`
- Implementation task group: `counting`
- Implementation source: `trace/tasks/illustrations/counting/pixel_village_count.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__pixel_village__person_path_count` -> `task_illustrations__pixel_village__person_path_count`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Counts people whose occupied tile footprint intersects a visible path tile in a top-down pixel village.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `people_on_path_count` | `count(filter(pixel_village_people, intersects(tile_footprint(person), path_tiles))); scene=pixel_village; scope=person_path_count; query_branch=people_on_path_count` |

## Program Metadata
- Program signatures: `count.spatial_relation`
- Base program contract: `count(filter(pixel_village_people, intersects(tile_footprint(person), path_tiles))); scene=pixel_village; scope=person_path_count`
- Parameter axes: `path_person_count`
- Arguments:
  - `person`: semantic_role; allowed `pixel_village_person`; source `program_schema_concrete`
  - `pixel_village_people`: semantic_role; allowed `visible_pixel_village_people`; source `program_schema_concrete`
  - `path_tiles`: semantic_role; allowed `visible_pixel_village_path_tiles`; source `scene_trace`
- Argument metadata status: `curated`
- Supported query ids: `people_on_path_count`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a positive integer derived from the same execution trace as the annotation.
- Non-counted background people must be rendered outside the configured one-tile path clearance neighborhood.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted person on a path.
- Annotation must not include the path tiles themselves or context-only village regions.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations counting prompt bundle.
- Public prompts use `people` or `person`, not the internal renderer label `villager`.
- Path membership is defined by metadata tile-footprint intersection, not pixel-color inference.
- Counted person ids, path tiles, background-person path clearance, renderer metadata, and projected bboxes must be recorded in the trace.

## Review Artifacts
- Task review artifacts: `review/task-reviews/illustrations/pixel_village/task_illustrations__pixel_village__person_path_count/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
