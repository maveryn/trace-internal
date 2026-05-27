# `task_physics__electrostatic_field__potential_value`

## Summary
- Domain: `physics`
- Scene id: `electrostatic_field`
- Task group: `electrostatics`
- Query id: `potential_value`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`

## Contract
The image shows three fixed point charges, a marked point `P`, and visible distance labels from each charge to `P`. The prompt asks for the signed electric potential at `P` using `k=1` and `V=sum(q/r)`.

Charge values and distances are constructed so each contribution is an integer and the final answer is a signed integer.

## Evidence
Prompt-facing evidence is one bounding box around the charges, distance labels, and point `P` used to compute the potential.

## Prompt And Trace
Prompt bundle: `physics_electrostatics_v0`; scene key: `electrostatics_field_map`; task key: `electrostatics_field_map_query`; query key: `potential_value`.

Outputs `query_id="potential_value"`. The trace records charge values, distances, integer potential contributions, the final potential value, and evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized potential scenario.
