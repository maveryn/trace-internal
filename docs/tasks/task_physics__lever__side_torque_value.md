# `task_physics__lever__side_torque_value`

## Summary
- Domain: `physics`
- Scene id: `lever`
- Task group: `mechanics`
- Query id: `side_torque`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`

## Contract
The image shows one lever with a fulcrum, integer distance marks, and labeled weight blocks. The task asks for the total torque on the queried side of the fulcrum.

Evidence is the set of weight-block bounding boxes on the queried side. `torque_side=left|right` is a role mirror inside the task, not a public task split.

## Prompt And Trace
Prompt bundle: `physics_mechanics_v0`; family key: `lever_balance_diagram`; task key: `lever_balance_query`; query id key: `side_torque`.

Outputs `query_id="side_torque"`. The trace records the side, weight specs, distances, relevant weight ids, and evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized lever layout.
