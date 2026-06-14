# `task_illustrations__indoor_room__furniture_side_count`

## Summary
- Domain: `illustrations`
- Scene id: `indoor_room`
- Implementation scene package: `indoor_room`
- Implementation source: `trace/tasks/illustrations/indoor_room/furniture_side_count.py`

## Task Contract
Counts visible small indoor objects of a sampled object type that lie on a queried image-plane side of one sampled furniture item.

## Program Contract
`count(filter(visible_room_objects, object_type(object)=target_object_type and side_relation(object, target_furniture)=query_side)); scene=indoor_room; scope=furniture_side_count`

## Query Branches

| Query id | Program schema |
| --- | --- |
| `left_side` | `count(filter(visible_room_objects, object_type(object)=target_object_type and left_of(object, target_furniture))); scene=indoor_room; scope=furniture_side_count` |
| `right_side` | `count(filter(visible_room_objects, object_type(object)=target_object_type and right_of(object, target_furniture))); scene=indoor_room; scope=furniture_side_count` |
| `above_side` | `count(filter(visible_room_objects, object_type(object)=target_object_type and above(object, target_furniture))); scene=indoor_room; scope=furniture_side_count` |
| `below_side` | `count(filter(visible_room_objects, object_type(object)=target_object_type and below(object, target_furniture))); scene=indoor_room; scope=furniture_side_count` |

## Program Metadata
- Program signatures: `count.spatial_relation_attribute`
- Base program contract: `count(filter(visible_room_objects, object_type(object)=target_object_type and side_relation(object, target_furniture)=query_side)); scene=indoor_room; scope=furniture_side_count`
- Parameter axes: `query_side`, `target_object_type`, `target_furniture`
- Arguments:
  - `visible_room_objects`: semantic_role; allowed `visible_room_objects`; source `program_schema_concrete`
  - `query_side`: relation; allowed `left_side|right_side|above_side|below_side`; source `query_id`
  - `target_object_type`: object_type; allowed `sampled_indoor_object_type`; source `trace_metadata`
  - `target_furniture`: furniture_type; allowed `table|sofa|cabinet`; source `trace_metadata`
- Argument metadata status: `curated`
- Supported query ids: `left_side`, `right_side`, `above_side`, `below_side`

## Answer Contract
- Answer schema: `integer_count`
- Generator `answer_gt.type`: `integer`
- The answer value is a non-negative integer derived from the same execution trace as the annotation.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of final-image pixel boxes, one per counted object satisfying the target type and side relation.
- Annotation excludes the reference furniture, labels, numeric annotations, and distractor/context objects.

## Prompt And Trace Requirements
- Prompt text must come from the indoor-room prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled styles, query side, target furniture, target object type, and verifier payloads must be explicit in the instance trace.
- Answer and annotation must be projected from the same generated scene trace, not inferred from pixels or prompt text.
