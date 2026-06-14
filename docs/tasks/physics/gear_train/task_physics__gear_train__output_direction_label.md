# `task_physics__gear_train__output_direction_label`

## Summary
- Domain: `physics`
- Scene id: `gear_train`
- Implementation scene: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/gear_train.py`

## Task Contract
Determines the rotation direction of a marked output gear from a visible simple meshed gear train and an input rotation arrow.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `marked_output_direction` | `string(direction(propagate_adjacent_mesh_reversals(input_gear_rotation, gear_count), target=marked_output_gear)); scene=gear_train; scope=output_direction_label` |

## Program Metadata
- Program signatures: `physics.gear_train_output_direction`
- Base program contract: `string(propagate_adjacent_mesh_reversals(input_direction, gear_count)); scene=gear_train; scope=output_direction_label`
- Parameter axes: `scene_variant`, `gear_count`, `input_direction`, `gear_radii`, `gear_layout`
- Arguments:
  - `input_gear`: query_operand; allowed `visible_first_gear_marked_by_input_rotation_arrow`; source `program_schema_concrete`
  - `input_rotation_arrow`: query_operand; allowed `visible_clockwise_or_counterclockwise_arrow`; source `program_schema_concrete`
  - `output_gear`: output_binding; allowed `visible_marked_last_gear`; source `program_schema_concrete`
  - `gear_train`: semantic_role; allowed `complete_visible_direct_mesh_train`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `marked_output_direction`

## Answer Contract
- Answer schema: `string`
- Generator `answer_gt.type`: `string`
- The answer value is exactly `clockwise` or `counterclockwise`.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys: `input_gear`, `input_rotation_arrow`, `output_gear`, `gear_train`
- Annotation must mark the visible gear witnesses used to propagate mesh reversals. It must not mark a solved output arrow, decorative panel/background elements, or prompt text.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics mechanics prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, gear count, gear radii, input direction, layout variant, colors, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep adjacent gear contacts visually unambiguous and must not draw the solved output direction.
