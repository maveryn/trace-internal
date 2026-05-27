# `task_physics__paired_resistor__missing_resistor_value`

## Summary
- Domain: `physics`
- Scene id: `paired_resistor`
- Task group: `circuits`
- Query id: `missing_resistor_value`
- Answer type: `integer`
- Evidence type: one-box `bbox_set`

## Contract
The image shows two side-by-side resistor networks between terminals `A` and `B` with an equality cue. The left circuit has one red `?` resistor. The task asks for the integer value that makes the left and right equivalent resistances equal.

Evidence is the bounding box of the marked red `?` resistor in the left circuit. Scene variation may choose the implemented circuit scaffold but must preserve the paired-network equality contract.

Calibrated public sampling uses missing-resistor answers from `{1, 3, 4, 5, 6, 8}`. The paired scene also displays the common total resistance and the known left-side resistance excluding the red `?`.

## Prompt And Trace
Prompt bundle: `physics_circuits_v0`; family key: `resistor_network_diagram`; task key: `equivalent_resistance_query`; query variant key: `missing_resistor_value`.

Public outputs use `query_variant="default"` and `query_id="missing_resistor_value"`. The trace records both circuit layouts, the paired total resistance, the missing resistor location, and evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized paired-circuit layout, and infeasible explicit targets are rejected.
