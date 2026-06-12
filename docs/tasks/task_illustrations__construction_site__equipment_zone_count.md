# `task_illustrations__construction_site__equipment_zone_count`

## Summary
- Domain: `illustrations`
- Scene id: `construction_site`
- Implementation scene: `counting`
- Implementation source: `trace/tasks/illustrations/counting/equipment_in_zone_count.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__construction_site__equipment_zone_count` -> `task_illustrations__construction_site__equipment_zone_count`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Counts visible construction vehicles/equipment assigned to one named construction-zone scope.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `vehicle_in_excavation_zone_count` | `count(filter(construction_vehicles, zone(vehicle)=target_zone)); scene=construction_site; scope=equipment_zone_count; query_branch=vehicle_in_excavation_zone_count` |
| `vehicle_in_loading_zone_count` | `count(filter(construction_vehicles, zone(vehicle)=target_zone)); scene=construction_site; scope=equipment_zone_count; query_branch=vehicle_in_loading_zone_count` |
| `vehicle_in_roadwork_zone_count` | `count(filter(construction_vehicles, zone(vehicle)=target_zone)); scene=construction_site; scope=equipment_zone_count; query_branch=vehicle_in_roadwork_zone_count` |

## Program Metadata
- Program signatures: `count.scoped_attribute`
- Base program contract: `count(filter(construction_vehicles, zone(vehicle)=target_zone)); scene=construction_site; scope=equipment_zone_count`
- Parameter axes: `fixed_query`
- Arguments:
  - `construction_vehicles`: semantic_role; allowed `visible_construction_vehicles`; source `program_schema_concrete`
  - `target_zone`: semantic_role; allowed `excavation_zone`, `loading_zone`, `roadwork_zone`; source `program_schema_concrete`
  - `vehicle`: semantic_role; allowed `construction_vehicle_instance`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `vehicle_in_excavation_zone_count`, `vehicle_in_loading_zone_count`, `vehicle_in_roadwork_zone_count`

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
- Task review artifacts: `review/task-reviews/illustrations/construction_site/task_illustrations__construction_site__equipment_zone_count/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
