# `task_physics__spring__spring_missing_value`

## Summary
- Domain: `physics`
- Scene id: `spring`
- Task group: `mechanics`
- Query id: `missing_value`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`

## Contract
The image shows two identical springs with rulers and weight blocks. The task asks for a missing weight or missing extension using the proportional relation represented by the reference spring.

Evidence contains the reference weight and extension markers plus the queried marked value and its paired shown measurement. `solve_for=weight|extension` is an inverse parameter inside this task.

## Prompt And Trace
Prompt bundle: `physics_mechanics_v0`; family key: `paired_spring_diagram`; task key: `spring_extension_query`; query variant key: `missing_value`.

Public outputs use `query_variant="default"` and `query_id="missing_value"`. The trace records the scale factor, solve target, measurements, answer support, and evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized spring layout.
