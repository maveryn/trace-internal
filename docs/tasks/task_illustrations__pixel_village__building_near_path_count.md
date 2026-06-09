# `task_illustrations__pixel_village__building_near_path_count`

## Summary
- Domain: `illustrations`
- Scene id: `pixel_village`
- Implementation task group: `counting`
- Implementation source: `trace/tasks/illustrations/counting/pixel_village_count.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__pixel_village__building_near_path_count` -> `task_illustrations__pixel_village__building_near_path_count`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Counts buildings near visible village paths.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `building_near_path_count` | `count(filter(pixel_village_buildings, chebyshev_distance(tile_footprint(building), path_tiles) <= near_path_tile_distance)); scene=pixel_village; scope=building_near_path_count; query_branch=building_near_path_count` |

## Program Metadata
- Program signatures: `count.spatial_relation`
- Base program contract: `count(filter(pixel_village_buildings, chebyshev_distance(tile_footprint(building), path_tiles) <= near_path_tile_distance)); scene=pixel_village; scope=building_near_path_count`
- Parameter axes: `near_path_tile_distance`
- Default relation definition: a building is near a path when its tile footprint is within one grid tile of any path tile, using Chebyshev tile distance.
- Argument metadata status: `curated`
- Supported query ids: `building_near_path_count`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a positive integer derived from the same execution trace as the annotation.
- Generated instances must keep the selected target count at or below the configured cap, currently `8`.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted building.
- Annotation must not include path tiles or non-counted buildings.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations counting prompt bundle.
- Prompt wording uses public spatial language such as `near a path`; the exact tile-distance rule is recorded in metadata.
- Counted building ids, path tiles, near-path distance, renderer metadata, and projected bboxes must be recorded in the trace.

## Review Artifacts
- Task review artifacts: `review/task-reviews/illustrations/pixel_village/task_illustrations__pixel_village__building_near_path_count/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
