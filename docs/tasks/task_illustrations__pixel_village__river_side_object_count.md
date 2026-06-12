# `task_illustrations__pixel_village__river_side_object_count`

## Summary
- Domain: `illustrations`
- Scene id: `pixel_village`
- Implementation scene package: `pixel_village`
- Implementation source: `trace/tasks/illustrations/pixel_village/river_side_object_count.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__pixel_village__river_side_object_count` -> `task_illustrations__pixel_village__river_side_object_count`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Counts visible target entities that lie strictly on one named side of the river.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `river_side_object_count` | `count(filter(pixel_village_entities, target_entity_type(entity)=target_object and strict_side_of_river(entity_tile_footprint, river_side))); scene=pixel_village; scope=river_side_object_count; query_branch=river_side_object_count` |

## Program Metadata
- Program signatures: `count.spatial_relation_membership`
- Base program contract: `count(filter(pixel_village_entities, target_entity_type(entity)=target_object and strict_side_of_river(entity_tile_footprint, river_side))); scene=pixel_village; scope=river_side_object_count`
- Parameter axes: `target_object`, `river_side`
- Arguments:
  - `entity`: semantic_role; allowed `pixel_village_entity`; source `program_schema_concrete`
  - `pixel_village_entities`: semantic_role; allowed `visible_pixel_village_entities`; source `program_schema_concrete`
  - `target_object`: semantic_role; allowed `building`, `person`, `tree`; source `parameter_axes`
  - `river_side`: spatial_relation; allowed `left`, `right`, `above`, `below`; source `parameter_axes`
- Argument metadata status: `curated`
- Supported query ids: `river_side_object_count`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a positive integer derived from the same execution trace as the annotation.
- Generated instances force a visible balanced river and keep the selected target count at or below the configured cap, currently `8`.
- Tree-count instances suppress cemetery territory so cemetery dead-tree decor is not an ambiguous non-counted witness.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted entity.
- Annotation must not include the river, bridge, paths, whole territories, or context-only regions.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations counting prompt bundle.
- Public prompts use ordinary spatial language such as `left of the river`, not tile or water-bound terminology.
- For `left`/`right`, the renderer forces a vertical river; for `above`/`below`, it forces a horizontal river.
- An entity counts only when its full tile footprint lies strictly on the requested side of the river bounds.
- Render-only attributes such as gender, facing, tree subtype, door state, roof style, season, and territory styling must not be queried.
- Counted entity ids, target object, target public name, river side, river orientation, river bounds, renderer metadata, and projected bboxes must be recorded in the trace.

## Review Artifacts
- Task review artifacts: `review/task-reviews/illustrations/pixel_village/task_illustrations__pixel_village__river_side_object_count/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
