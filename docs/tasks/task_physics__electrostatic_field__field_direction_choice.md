# `task_physics__electrostatic_field__field_direction_choice`

## Summary
- Domain: `physics`
- Scene id: `electrostatic_field`
- Task group: `electrostatics`
- Query id: `field_direction_choice`
- Answer type: `option_letter`
- Evidence type: `keyed_point_map`

## Contract
The image shows a coordinate grid with fixed point charges labeled by combined key/value tags such as `Q1=+4`, a marked point `P`, and eight labeled candidate direction arrows. The prompt asks which arrow points in the direction of the requested vector.

The internal `direction_mode` is `electric_field_direction|force_on_positive_charge|force_on_negative_charge`. Direction prompts include the positive/negative test-charge convention so force-direction branches remain explicit.

## Evidence
Prompt-facing evidence is a `keyed_point_map` over the fixed charge marker centers and the point `P` marker center, with keys `Q1`, `Q2`, `Q3`, and `P`. Candidate arrows remain visible answer options and trace metadata.

## Prompt And Trace
Prompt bundle: `physics_electrostatics_v0`; scene key: `electrostatics_field_map`; task key: `electrostatics_field_map_query`; query key: `field_direction_choice`.

Outputs `query_id="field_direction_choice"`. The trace records the resolved direction mode, requested direction, charge coordinates, option-arrow directions, selected option letter, and input-witness evidence entity/key mapping.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized field-map scenario.
