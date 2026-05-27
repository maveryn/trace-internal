# `task_physics__lever__missing_weight_balance_value`

## Summary
- Domain: `physics`
- Scene id: `lever`
- Task group: `mechanics`
- Query id: `missing_weight_to_balance`
- Answer type: `integer`
- Evidence type: one-box `bbox_set`

## Contract
The image shows one lever with a marked red `?` weight block. The task asks for the missing weight value that balances the lever. The calibrated public mix samples missing weights from `1..6`, uses the textured-beam variant, and caps each side at two shown weights.

Evidence is the bounding box of the marked `?` weight block. Scene variants adjust the lever presentation but keep the same balance equation and evidence contract.

## Prompt And Trace
Prompt bundle: `physics_mechanics_v0`; family key: `lever_balance_diagram`; task key: `lever_balance_query`; query variant key: `missing_weight_to_balance`.

Public outputs use `query_variant="default"` and `query_id="missing_weight_to_balance"`. The trace records known torques, placeholder side and distance, visible weight specs, and evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized lever layout.
