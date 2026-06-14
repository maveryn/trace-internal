# `task_physics__gear_train__output_speed_value`

## Summary
- Domain: `physics`
- Scene id: `gear_train`
- Implementation scene: `mechanics`
- Implementation source: `trace/tasks/physics/mechanics/gear_train.py`

## Task Contract
Computes the marked output gear speed from a simple directly meshed gear train with visible tooth-count labels and a visible input rpm label.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `simple_gear_ratio_output_speed` | `integer(input_rpm * input_gear_tooth_count / output_gear_tooth_count); scene=gear_train; scope=output_speed_value` |

## Program Metadata
- Program signatures: `physics.gear_train_output_speed`
- Base program contract: `integer(solve_simple_gear_ratio(input_rpm, input_teeth, output_teeth)); scene=gear_train; scope=output_speed_value`
- Parameter axes: `scene_variant`, `gear_count`, `input_teeth`, `output_teeth`, `idler_teeth`, `input_rpm`
- Arguments:
  - `input_gear`: query_operand; allowed `visible_input_gear_with_tooth_count_and_input_rpm_label`; source `program_schema_concrete`
  - `output_gear`: output_binding; allowed `visible_marked_output_gear_with_tooth_count`; source `program_schema_concrete`
  - `gear_train`: semantic_role; allowed `complete_visible_direct_mesh_train`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `simple_gear_ratio_output_speed`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- The answer value is the marked output gear's integer rotational speed in `rpm`.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys: `input_gear`, `output_gear`, `gear_train`
- Annotation must mark the visible gear witnesses and labels needed to compute the output speed. It must not mark decorative panel/background elements or derived output speed text.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics mechanics prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, gear count, tooth counts, input rpm, layout variant, colors, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep tooth-count labels and the input rpm label readable. Idler gears may appear, but first-version semantics use only the input and output tooth counts for the speed ratio.
