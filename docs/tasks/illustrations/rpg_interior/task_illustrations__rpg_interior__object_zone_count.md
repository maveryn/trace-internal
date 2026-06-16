# `task_illustrations__rpg_interior__object_zone_count`

## Summary
- Domain: `illustrations`
- Scene id: `rpg_interior`
- Implementation scene package: `rpg_interior`
- Implementation source: `trace/tasks/illustrations/rpg_interior/object_zone_count.py`

## Task Contract
Counts visible small props of one sampled object type that are placed in or on one sampled RPG interior zone.

## Program Contract
`count(filter(visible_rpg_interior_objects, object_type(object)=target_object_type and in_zone(object, target_zone))); scene=rpg_interior; scope=object_zone_count`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `single` | `count(filter(visible_rpg_interior_objects, object_type(object)=target_object_type and in_zone(object, target_zone))); scene=rpg_interior; scope=object_zone_count` |

## Program Metadata
- Program signatures: `count.scoped_attribute`
- Base program contract: `count(filter(visible_rpg_interior_objects, object_type(object)=target_object_type and in_zone(object, target_zone))); scene=rpg_interior; scope=object_zone_count`
- Parameter axes: `target_object_type`, `target_zone`
- Arguments:
  - `visible_rpg_interior_objects`: semantic_role; allowed `visible_countable_rpg_interior_props`; source `program_schema_concrete`
  - `target_object_type`: object_type; allowed `bottle|bowl|candle|mug|plate|pot`; source `parameter_axes`
  - `target_zone`: spatial_scope; allowed `counter|shelf|table|storage_corner`; source `parameter_axes`
- Argument metadata status: `curated`
- Supported query ids: `single`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a positive integer in `1..5`, derived from the same execution trace as the annotation.

## Annotation Contract
- Annotation schema: `point_set`
- Generator `annotation_gt.type`: `point_set`
- Annotation is an unordered set of final-image pixel points, one near the center of each counted object.
- Annotation excludes the zone surface, room walls, large fixtures, characters, distractors, and context-only objects.

## Prompt And Trace Requirements
- Prompt text must come from `prompts/illustrations/rpg_interior/illustrations_rpg_interior_v0.json`.
- Public prompts use ordinary zone language such as `on the counter`, `on the shelf`, or `in the storage corner`.
- Render-only attributes such as room variant, floor pattern, palette, and prop colors must not be query ids.
- Counted entity ids, target object type, target zone, zone relation phrase, renderer metadata, projected points, and diagnostic bboxes must be recorded in the trace.
