# `task_physics__bridge_circuit__bridge_missing_resistance_value`

## Summary
- Domain: `physics`
- Scene id: `bridge_circuit`
- Implementation task group: `circuits`
- Implementation source: `trace/tasks/physics/circuits/bridge_balance.py`
- Contract-v0 migration decision: `new_extension_task`
- Public mapping: `task_physics__bridge_circuit__bridge_missing_resistance_value` -> `task_physics__bridge_circuit__bridge_missing_resistance_value`
- Status: `pending_v0_manual_review_and_solve_rate`

## Task Contract
Computes the missing resistor value in a balanced bridge circuit from the visible resistor labels and zero-current bridge meter.

This public task id is a stable contract-v0 unit: one physics scene id plus one objective contract. Query ids may vary only narrow operands or parameters inside that same program contract.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `missing_bridge_resistance` | `solve_balanced_bridge_resistance(resistors_r1_r2_r3_r4, zero_meter_condition, unknown_slot); scene=bridge_circuit; scope=bridge_missing_resistance_value; query_branch=missing_bridge_resistance` |

## Program Metadata
- Program signatures: `physics.bridge_missing_resistance_value`
- Base program contract: `solve_balanced_bridge_resistance(resistors_r1_r2_r3_r4, zero_meter_condition, unknown_slot); scene=bridge_circuit; scope=bridge_missing_resistance_value`
- Parameter axes: `query_id`, `scene_variant`, `missing_resistor`
- Arguments:
  - `resistors_r1_r2_r3_r4`: semantic_role; allowed `visible_bridge_resistors_with_known_values_and_one_unknown`; source `program_schema_concrete`
  - `zero_meter_condition`: semantic_role; allowed `visible_bridge_meter_reading_zero`; source `program_schema_concrete`
  - `unknown_slot`: query_operand; allowed `R1|R2|R3|R4`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `missing_bridge_resistance`

## Answer Contract
- Answer schema: `integer`
- Generator `answer_gt.type`: `integer`
- The answer value is the missing resistance in ohms.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation is keyed by the known visible resistor labels, plus `target_resistor` and `zero_meter`.
- Annotation must mark minimal visual witnesses from the final rendered diagram: the resistor symbols with their labels, the question-mark target resistor, and the zero meter. Annotation must not mark wires, decorative frame chrome, or inferred bridge-ratio products.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, known resistor values, missing slot, zero-meter condition, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep the bridge topology, resistor labels, question-mark target, and zero meter visible.

## Review Artifacts
- Task review artifacts: `review/task-reviews/physics/bridge_circuit/task_physics__bridge_circuit__bridge_missing_resistance_value/`
- Browser review app manual audit state and issue threads are the source of truth for reviewer acceptance.
- Current solve-rate acceptance must be read from `review/calibration_sweep_status.json` or `.md`; historical solve-rate notes in task docs are intentionally omitted.
