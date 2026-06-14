# `task_physics__electrostatic_field__field_direction_choice`

## Summary
- Domain: `physics`
- Scene id: `electrostatic_field`
- Implementation scene: `electrostatics`
- Implementation source: `trace/tasks/physics/electrostatics/field_map.py`

## Task Contract
Selects the direction of the electric field or force at a marked point from visible point charges.

## Query Branches

| Query id | Program schema |
| --- | --- |
| `field_direction_choice` | `option_letter(direction(net_field(charges_q1_q2_q3, point_p), mode=direction_mode)); scene=electrostatic_field; scope=field_direction_choice` |

## Program Metadata
- Program signatures: `physics.electric_field_direction_choice`
- Base program contract: `option_letter(direction(net_field(charges_q1_q2_q3, point_p), mode=direction_mode)); scene=electrostatic_field; scope=field_direction_choice`
- Parameter axes: `direction_mode`
- Arguments:
  - `charges_q1_q2_q3`: semantic_role; allowed `visible_point_charges_Q1_Q2_Q3`; source `program_schema_concrete`
  - `direction_mode`: semantic_role; allowed `electric_field_direction`, `force_on_negative_charge`, `force_on_positive_charge`; source `program_schema_concrete`
  - `point_p`: semantic_role; allowed `visible_point_P`; source `program_schema_concrete`
- Argument metadata status: `curated`
- Supported query ids: `field_direction_choice`

## Answer Contract
- Answer schema: `option_letter`
- Generator `answer_gt.type`: `option_letter`
- The answer value is the selected visible option letter.

## Annotation Contract
- Annotation schema: `keyed_point_map`
- Generator `annotation_gt.type`: `keyed_point_map`
- Annotation is keyed because point witnesses have distinct roles; each key maps to the final-image pixel point for that role.
- Annotation must mark minimal visual witnesses from the final rendered diagram, not answer labels, option choices, decorative chrome, or derived numeric annotations unless those are the queried visual witnesses.
- Annotation and answer must be projected from the same generated execution trace, not inferred from pixels or prompt text.

## Prompt And Trace Requirements
- Prompt text must come from the physics prompt bundles, with scene and task/query layers selected deterministically and recorded in metadata.
- Render randomness, sampled fonts/styles, query operands, formula quantities, and verifier payloads must be explicit in the instance trace.
- Diagrams must keep all quantities required for the physics computation visible or explicitly stated by the task prompt contract.
