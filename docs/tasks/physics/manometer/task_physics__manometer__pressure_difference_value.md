# `task_physics__manometer__pressure_difference_value`

## Summary
- Domain: `physics`
- Scene id: `manometer`
- Implementation scene: `fluids`
- Implementation source: `trace/tasks/physics/fluids/manometer.py`

## Task Contract
Computes the absolute pressure difference between two labeled manometer pressure points from a visible liquid-column height difference and a visible `rho g` conversion label.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `u_tube_pressure_difference` | `integer(abs_pressure_difference(point_a, point_b, height_difference, rho_g_conversion)); scene=manometer; scope=pressure_difference_value` |

## Program Metadata
- Program signatures: `physics.manometer_pressure_difference`
- Base program contract: `integer(abs(height_cm * kpa_per_cm)); scene=manometer; scope=pressure_difference_value`
- Parameter axes: `height_cm`, `kpa_per_cm`, `higher_pressure_side`
- Arguments:
  - `point_a`: semantic_role; allowed `visible_left_pressure_point_label`; source `program_schema_concrete`
  - `point_b`: semantic_role; allowed `visible_right_pressure_point_label`; source `program_schema_concrete`
  - `height_difference`: query_operand; allowed `integer_centimeter_liquid_level_difference`; source `program_schema_concrete`
  - `rho_g_conversion`: query_operand; allowed `integer_kpa_per_cm_conversion_label`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `u_tube_pressure_difference`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- The answer value is the absolute pressure difference in `kPa`.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys: `left_pressure_point`, `right_pressure_point`, `height_difference`, `fluid_density_label`
- Annotation must mark the minimal visible witnesses needed to compute the pressure difference. It must not mark decorative glass, background grid lines, or derived answer text.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics fluids prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, height difference, conversion factor, side orientation, fluid color, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep the height marker and conversion label readable and avoid multi-fluid stacks in the first calibrated version.
