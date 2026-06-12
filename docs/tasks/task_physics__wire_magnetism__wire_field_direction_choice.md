# `task_physics__wire_magnetism__wire_field_direction_choice`

## Summary
- Domain: `physics`
- Scene id: `wire_magnetism`
- Implementation scene: `magnetism`
- Implementation source: `trace/tasks/physics/magnetism/wire_field.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__wire_magnetism__wire_field_direction_choice` -> `task_physics__wire_magnetism__wire_field_direction_choice`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Selects the magnetic-field direction at a marked point near a straight current-carrying wire.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `field_direction_at_point` | `option_letter(direction(right_hand_rule_around_current_wire(current_direction, point_p_side))); scene=wire_magnetism; scope=wire_field_direction_choice; query_branch=field_direction_at_point` |

## Program Metadata
- Program signatures: `physics.wire_field_direction_choice`
- Base program contract: `option_letter(direction(right_hand_rule_around_current_wire(current_direction, point_p_side))); scene=wire_magnetism; scope=wire_field_direction_choice`
- Parameter axes: `fixed_query`
- Arguments:
  - `current_direction`: semantic_role; allowed `visible_current_arrow_on_wire`; source `program_schema_concrete`
  - `point_p_side`: semantic_role; allowed `visible_marked_point_side_relative_to_wire`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `field_direction_at_point`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible option letter.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation is keyed because witness roles are distinct; keys include `wire_current` and `point_p`.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/wire_magnetism/task_physics__wire_magnetism__wire_field_direction_choice/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
