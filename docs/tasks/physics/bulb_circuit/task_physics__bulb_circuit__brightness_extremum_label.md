# `task_physics__bulb_circuit__brightness_extremum_label`

## Summary
- Domain: `physics`
- Scene id: `bulb_circuit`
- Implementation scene: `circuits`
- Implementation source: `trace/tasks/physics/circuits/bulb_brightness.py`

## Task Contract
Selects the labeled bulb that is brightest or dimmest in a visible ideal-battery circuit.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `brightest_bulb_label` | `label(arg_extreme(bulbs, power_in_visible_circuit, direction=brightest)); scene=bulb_circuit; scope=brightness_extremum_label; query_branch=brightest_bulb_label` |
| `dimmest_bulb_label` | `label(arg_extreme(bulbs, power_in_visible_circuit, direction=dimmest)); scene=bulb_circuit; scope=brightness_extremum_label; query_branch=dimmest_bulb_label` |

## Program Metadata
- Program signatures: `physics.bulb_brightness_extremum_label`
- Base program contract: `label(arg_extreme(bulbs, power_in_visible_circuit, direction=brightest_or_dimmest)); scene=bulb_circuit; scope=brightness_extremum_label`
- Parameter axes: `query_id`, `scene_variant`
- Arguments:
  - `bulbs`: semantic_role; allowed `visible_labeled_bulbs_b1_through_b5_with_resistance_labels`; source `program_schema_concrete`
  - `circuit_topology`: semantic_role; allowed `visible_series_parallel_bulb_topology`; source `program_schema_concrete`
  - `target_direction`: query_operand; allowed `brightest|dimmest`; source `query_id`
- Argument metadata status: `curated`
- Supported query ids: `brightest_bulb_label`, `dimmest_bulb_label`

## Answer Contract
- Answer schema: `string`
- Generator `answer_gt.type`: `string`
- The answer value is the selected visible bulb label, for example `B2`.

## Annotation Contract
- Annotation schema: `keyed_bbox_map`
- Generator `annotation_gt.type`: `keyed_bbox_map`
- Annotation is keyed by visible bulb labels `B1` through `B5`.
- Annotation must mark minimal visual witnesses from the final rendered diagram: the bulb symbol and its resistance label. Annotation must not mark wires, battery terminals, decorative chrome, or inferred brightness ranks.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, visible resistance values, computed powers, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep the circuit topology, bulb labels, resistance labels, and ideal battery visible; glow intensity must not encode the answer.
