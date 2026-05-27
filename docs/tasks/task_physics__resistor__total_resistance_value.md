# `task_physics__resistor__total_resistance_value`

## Summary
- Domain: `physics`
- Scene id: `resistor`
- Task group: `circuits`
- Query id: `total_resistance`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`

## Contract
The image shows one resistor network between terminals `A` and `B`. The task asks for the total equivalent resistance as an integer number of ohms.

Evidence is the set of resistor-box bounding boxes that belong to the network. Scene variation stays inside `scene_variant` (`parallel` or `simple_series_parallel`) and color/style knobs; those are not public sampling units.

Calibrated public sampling uses integer equivalent-resistance answers from `1..20` ohms and one visible parallel block with optional series resistors.

## Prompt And Trace
Prompt bundle: `physics_circuits_v0`; family key: `resistor_network_diagram`; task key: `equivalent_resistance_query`; query variant key: `total_resistance`.

Public outputs use `query_variant="default"` and `query_id="total_resistance"`. The trace keeps the internal query in `query_variant` and records the sampled scene, resistor layout, answer support, and evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized circuit layout, and unsupported or infeasible explicit targets are rejected.
