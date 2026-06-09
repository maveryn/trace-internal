# `task_physics__circuit_state_change__bulb_brightness_change_label`

## Summary
- Domain: `physics`
- Scene id: `circuit_state_change`
- Implementation task group: `circuits`
- Implementation source: `trace/tasks/physics/circuits/state_change_brightness.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__circuit_state_change__bulb_brightness_change_label` -> `task_physics__circuit_state_change__bulb_brightness_change_label`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the labeled bulb whose brightness changes in the requested way after a visible switch action.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `brightens_after_switch_change` | `label(select(bulbs, brightness_change_after_switch_action(bulb)=brightens)); scene=circuit_state_change; scope=bulb_brightness_change_label; query_branch=brightens_after_switch_change` |
| `dims_after_switch_change` | `label(select(bulbs, brightness_change_after_switch_action(bulb)=dims)); scene=circuit_state_change; scope=bulb_brightness_change_label; query_branch=dims_after_switch_change` |
| `turns_on_after_switch_change` | `label(select(bulbs, brightness_change_after_switch_action(bulb)=turns_on)); scene=circuit_state_change; scope=bulb_brightness_change_label; query_branch=turns_on_after_switch_change` |
| `turns_off_after_switch_change` | `label(select(bulbs, brightness_change_after_switch_action(bulb)=turns_off)); scene=circuit_state_change; scope=bulb_brightness_change_label; query_branch=turns_off_after_switch_change` |

## Program Metadata
- Program signatures: `physics.circuit_state_change_bulb_brightness_change_label`
- Base program contract: `label(select(bulbs, brightness_change_after_switch_action(bulb)=target_change_class)); scene=circuit_state_change; scope=bulb_brightness_change_label`
- Parameter axes: `query_id`, `switch_action`, `resistance_values`, `target_label`, `accent_color_name`
- Arguments:
  - `bulbs`: semantic_role; allowed `visible_labeled_bulbs_b1_through_b5_with_resistance_labels`; source `program_schema_concrete`
  - `switch_action`: semantic_role; allowed `opens|closes`; source `program_schema_concrete`
  - `target_change_class`: query_operand; allowed `brightens|dims|turns_on|turns_off`; source `query_id`
  - `circuit_topology`: semantic_role; allowed `series_bulb_plus_switch_controlled_parallel_branch_with_unchanged_reference_branch`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `brightens_after_switch_change`, `dims_after_switch_change`, `turns_on_after_switch_change`, `turns_off_after_switch_change`

## Answer Contract
- Answer schema: `string`
- Generator `answer_gt.type`: `string`
- The answer value is the selected visible bulb label, for example `B2`.
- Each generated instance must have exactly one bulb matching the queried change class.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation is keyed by `changed_switch` and visible bulb labels `B1` through `B5`.
- Annotation must mark the switch-action cue and the bulb symbols with their resistance labels. Annotation must not mark wires, battery terminals, decorative chrome, inferred current paths, or derived brightness values.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics circuits prompt bundle, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, switch action, visible resistance values, before/after power values, change classes, and verifier payloads must be explicit in the instance trace.
- Bulbs must not visually glow or otherwise encode the answer; the selection comes from comparing the circuit before and after the switch action.
- This task must remain separate from `task_physics__bulb_circuit__brightness_extremum_label`, which asks a static brightest/dimmest ranking.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/circuit_state_change/task_physics__circuit_state_change__bulb_brightness_change_label/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
