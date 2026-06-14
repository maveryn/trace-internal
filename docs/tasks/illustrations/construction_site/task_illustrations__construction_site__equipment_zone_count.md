# `task_illustrations__construction_site__equipment_zone_count`

## Summary
- Domain: `illustrations`
- Scene id: `construction_site`
- Implementation scene: `construction_site`
- Implementation source: `trace/tasks/illustrations/construction_site/equipment_zone_count.py`

## Contract
1. Domain: `illustrations`
2. Scene id: `construction_site`
3. Public task id: `task_illustrations__construction_site__equipment_zone_count`
4. Supported `query_id` values: `vehicle_in_zone_count`
5. Query ids: `vehicle_in_zone_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(construction_vehicles, zone(vehicle)=target_zone)); scene=construction_site; scope=equipment_zone_count`

## Program Contract
- `count(filter(construction_vehicles, zone(vehicle)=target_zone)); scene=construction_site; scope=equipment_zone_count`

## Task Contract
Counts visible construction vehicles/equipment assigned to one named construction-zone scope.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `vehicle_in_zone_count` | `count(filter(construction_vehicles, zone(vehicle)=target_zone)); scene=construction_site; scope=equipment_zone_count` |

## Program Metadata
- Program signatures: `count.scoped_attribute`
- Base program contract: `count(filter(construction_vehicles, zone(vehicle)=target_zone)); scene=construction_site; scope=equipment_zone_count`
- Parameter axes: `target_zone`
- Arguments:
  - `construction_vehicles`: semantic_role; allowed `visible_construction_vehicles`; source `program_schema_concrete`
  - `target_zone`: semantic_role; allowed `excavation_zone`, `loading_zone`, `roadwork_zone`; source `sampled_scene_value`
  - `vehicle`: semantic_role; allowed `construction_vehicle_instance`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `vehicle_in_zone_count`
- `target_zone` is sampled/overridden through task parameters and recorded in trace metadata; it is not a public query-id branch because the prompt resolves the concrete zone name before asking the same count operation.

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- Supported answer range: `0..4`
- The answer value is a non-negative integer derived from the same execution trace as the annotation.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted/selected visual witness. Do not include labels, numeric annotations, or context-only regions.
- When the answer is `0`, annotation is an empty bbox set.
- Annotation and answer must be projected from the same generated scene trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the `illustrations_construction_site_v1` scene prompt bundle, with scene/task/output layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, and verifier payloads must be explicit in the instance trace.
- Distractor/context text may be rendered only when it is part of the scene grammar and must not be treated as annotation unless it is the queried visual witness.
