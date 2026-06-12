# `task_physics__thermal_mixing__final_temperature_value`

## Summary
- Domain: `physics`
- Scene id: `thermal_mixing`
- Implementation scene: `thermodynamics`
- Implementation source: `trace/tasks/physics/thermodynamics/thermal_mixing.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__thermal_mixing__final_temperature_value` -> `task_physics__thermal_mixing__final_temperature_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Computes the final equilibrium temperature after equal amounts of the same liquid are mixed in an insulated container.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids vary only the narrow equal-amount final-temperature branch; cup count and initial temperatures are internal parameter axes.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `equal_amount_final_temperature` | `integer(average(initial_temperatures_same_liquid_equal_amounts_insulated_system)); scene=thermal_mixing; scope=final_temperature_value` |

## Program Metadata
- Program signatures: `physics.final_temperature_value`
- Base program contract: `integer(average(initial_temperatures_same_liquid_equal_amounts_insulated_system)); scene=thermal_mixing; scope=final_temperature_value`
- Parameter axes: `cup_count`, `initial_temperature_set`, `final_temperature_c`
- Arguments:
  - `initial_temperatures`: visual_operand_set; allowed `2..4 visible Celsius cup labels`; source `program_schema_concrete`
  - `same_liquid`: semantic_condition; allowed `true`; source `prompt_and_scene_contract`
  - `equal_amounts`: semantic_condition; allowed `true`; source `prompt_and_scene_contract`
  - `insulated_system`: semantic_condition; allowed `true`; source `prompt_and_scene_contract`
- Argument metadata status: `curated`
- Supported query ids: `equal_amount_final_temperature`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- The answer value is the integer final equilibrium temperature in degrees Celsius.

## Annotation Contract
- Annotation schema: `bbox_set`
- Generator `annotation_gt.type`: `bbox_set`
- Annotation is an unordered set of bounding boxes around the initial cups and their visible temperature labels.
- Annotation must not mark the final mixing container, the hidden derived final temperature, decorative arrows, title text, background grid, or prompt-only assumptions.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, cup count, initial temperature set, final average, and verifier payloads must be explicit in the instance trace.
- Initial temperatures must be constructed so their average is an integer. Cup order, liquid color, cup count, and layout must remain non-semantic visual variation axes.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/thermal_mixing/task_physics__thermal_mixing__final_temperature_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
