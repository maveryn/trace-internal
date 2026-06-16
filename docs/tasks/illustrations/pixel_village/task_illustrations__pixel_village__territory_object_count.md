# `task_illustrations__pixel_village__territory_object_count`

## Summary
- Domain: `illustrations`
- Scene id: `pixel_village`
- Implementation scene package: `pixel_village`
- Implementation source: `trace/tasks/illustrations/pixel_village/territory_object_count.py`

## Task Contract
Counts target entities inside one semantic pixel-village territory.

## Program Contract
`count(filter(pixel_village_entities, territory_id(entity)=target_territory and public_name(entity)=target_public_name)); scene=pixel_village; scope=territory_object_count`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `count(filter(pixel_village_entities, territory_id(entity)=target_territory and public_name(entity)=target_public_name)); scene=pixel_village; scope=territory_object_count` |

## Program Metadata
- Program signatures: `count.scoped_attribute_membership`
- Base program contract: `count(filter(pixel_village_entities, territory_id(entity)=target_territory and public_name(entity)=target_public_name)); scene=pixel_village; scope=territory_object_count`
- Parameter axes: `territory_object`
- Supported operands: `cemetery_grave_marker`, `orchard_tree`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a positive integer derived from the same execution trace as the annotation.
- Generated instances must keep the selected target count at or below the configured cap, currently `9`.

## Annotation Contract
- Annotation schema: `point_set`
- Generator `annotation_gt.type`: `point_set`
- Annotation is an unordered set of final-image pixel points, one near the center of each counted entity in the target territory.
- Annotation must not include whole territories, fences, paths, or context-only regions.

## Prompt And Trace Requirements
- Prompt text must come from the illustrations counting prompt bundle.
- Public prompts must name the territory and target public object type.
- The relevant territory is forced present for the sampled operand and the force constraint is recorded in trace metadata.
- Counted entity ids, territory id, target public name, renderer metadata, projected points, and diagnostic bboxes must be recorded in the trace.
