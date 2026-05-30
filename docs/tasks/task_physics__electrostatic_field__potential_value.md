# `task_physics__electrostatic_field__potential_value`

## Summary
- Domain: `physics`
- Scene id: `electrostatic_field`
- Task group: `electrostatics`
- Query id: `potential_value`
- Answer type: `integer`
- Evidence type: `keyed_point_map`

## Contract
The image shows three fixed point charges labeled by combined key/value tags such as `Q1=+4`, a marked point `P`, and visible distance labels from each charge to `P`. The prompt asks for the signed electric potential at `P` using `k=1` and `V=sum(q/r)`.

Charge values and distances are constructed so each contribution is an integer and the final answer is a signed integer.

## Evidence
Prompt-facing evidence is a `keyed_point_map` over fixed charge marker centers and the point `P` marker center, with keys `Q1`, `Q2`, `Q3`, and `P`. Charge and distance values remain visible attributes and trace metadata.

## Prompt And Trace
Prompt bundle: `physics_electrostatics_v0`; scene key: `electrostatics_field_map`; task key: `electrostatics_field_map_query`; query key: `potential_value`.

Outputs `query_id="potential_value"`. The trace records charge values, distances, integer potential contributions, the final potential value, and input-witness evidence entity/key mapping.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized potential scenario.
