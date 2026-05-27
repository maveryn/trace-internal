# `task_physics__electrostatic_field__zero_field_point_label`

## Summary
- Domain: `physics`
- Scene id: `electrostatic_field`
- Task group: `electrostatics`
- Query id: `zero_field_point_label`
- Answer type: `option_letter`
- Evidence type: unordered `bbox_set`

## Contract
The image shows two unequal same-sign fixed charges arranged on one grid axis and six labeled candidate points. The prompt asks which labeled point has zero net electric field.

The correct point is constructed between the charges using a `1:4` charge-magnitude ratio and matching `1:2` distance ratio, so the field magnitudes cancel without making the answer the visual midpoint. Distractor points are visible nearby candidate locations on and off the charge axis.

## Evidence
Prompt-facing evidence is one bounding box around the correct labeled candidate point.

## Prompt And Trace
Prompt bundle: `physics_electrostatics_v0`; scene key: `electrostatics_field_map`; task key: `electrostatics_field_map_query`; query key: `zero_field_point_label`.

Outputs `query_id="zero_field_point_label"`. The trace records the charge-axis orientation, charge coordinates, candidate point coordinates, selected option letter, and evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized field-map scenario.
