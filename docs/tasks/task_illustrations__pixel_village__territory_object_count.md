# `task_illustrations__pixel_village__territory_object_count`

## Summary
- Domain: `illustrations`
- Scene id: `pixel_village`
- Implementation scene package: `pixel_village`
- Implementation source: `trace/tasks/illustrations/pixel_village/territory_object_count.py`
- Contract-v0 migration decision: `keep`
- Public mapping: `task_illustrations__pixel_village__territory_object_count` -> `task_illustrations__pixel_village__territory_object_count`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Counts target entities inside one semantic pixel-village territory.

This public task id is a stable contract-v0 unit: one renderer scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `territory_object_count` | `count(filter(pixel_village_entities, territory_id(entity)=target_territory and public_name(entity)=target_public_name)); scene=pixel_village; scope=territory_object_count; query_branch=territory_object_count` |

## Program Metadata
- Program signatures: `count.scoped_attribute_membership`
- Base program contract: `count(filter(pixel_village_entities, territory_id(entity)=target_territory and public_name(entity)=target_public_name)); scene=pixel_village; scope=territory_object_count`
- Parameter axes: `territory_object`
- Supported operands: `cemetery_grave_marker`, `orchard_tree`
- Argument metadata status: `curated`
- Supported query ids: `territory_object_count`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a positive integer derived from the same execution trace as the annotation.
- Generated instances must keep the selected target count at or below the configured cap, currently `8`.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted entity in the target territory.
- Annotation must not include whole territories, fences, paths, or context-only regions.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations counting prompt bundle.
- Public prompts must name the territory and target public object type.
- The relevant territory is forced present for the sampled operand and the force constraint is recorded in trace metadata.
- Counted entity ids, territory id, target public name, renderer metadata, and projected bboxes must be recorded in the trace.

## Review Artifacts
- Task review artifacts: `review/task-reviews/illustrations/pixel_village/task_illustrations__pixel_village__territory_object_count/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
