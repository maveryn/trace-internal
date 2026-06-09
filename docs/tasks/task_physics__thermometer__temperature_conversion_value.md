# `task_physics__thermometer__temperature_conversion_value`

## Summary
- Domain: `physics`
- Scene id: `thermometer`
- Implementation task group: `thermodynamics`
- Implementation source: `trace/tasks/physics/thermodynamics/thermometer.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__thermometer__temperature_conversion_value` -> `task_physics__thermometer__temperature_conversion_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Reads a source temperature from a visible thermometer scale and converts it to the other temperature unit.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query variation is limited to conversion direction and thermometer scale profile inside the same readout-plus-conversion program.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `celsius_to_fahrenheit_value` | `integer(convert_temperature(read_scale_value(liquid_level, thermometer_scale, unit=C), C, F)); scene=thermometer; scope=temperature_conversion_value` |
| `fahrenheit_to_celsius_value` | `integer(convert_temperature(read_scale_value(liquid_level, thermometer_scale, unit=F), F, C)); scene=thermometer; scope=temperature_conversion_value` |

## Program Metadata
- Program signatures: `physics.thermometer_temperature_conversion`
- Base program contract: `integer(convert_temperature(read_scale_value(liquid_level, thermometer_scale, source_unit), source_unit, target_unit)); scene=thermometer; scope=temperature_conversion_value`
- Parameter axes: `query_id`, `scale_profile`, `source_temperature`, `target_answer`
- Arguments:
  - `liquid_level`: semantic_role; allowed `visible_liquid_column_top`; source `program_schema_concrete`
  - `scale_region`: query_operand; allowed `visible_tick_scale_with_numeric_labels`; source `program_schema_concrete`
  - `source_unit_label`: query_operand; allowed `C|F`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `celsius_to_fahrenheit_value`, `fahrenheit_to_celsius_value`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- The answer value is the integer converted temperature in the target unit requested by the prompt.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation keys: `liquid_level`, `scale_region`, `source_unit_label`
- Annotation must mark the minimal visible witnesses needed to read the source temperature. It must not mark derived answer text, a hidden conversion result, or decorative thermometer casing alone.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics thermodynamics prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- The prompt must include the relevant temperature-conversion formula so the task does not depend on hidden unit-conversion assumptions.
- Render randomness, sampled fonts/styles, query id, scale profile, source temperature, source unit, target unit, target answer, and verifier payloads must be explicit in the instance trace.
- First-version diagrams keep source temperatures tick-aligned and target answers integer-valued.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/thermometer/task_physics__thermometer__temperature_conversion_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
