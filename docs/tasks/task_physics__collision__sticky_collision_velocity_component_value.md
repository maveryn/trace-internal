# `task_physics__collision__sticky_collision_velocity_component_value`

## Summary
- Domain: `physics`
- Scene id: `collision`
- Task group: `mechanics`
- Query id: `velocity_component`
- Answer type: `integer`
- Evidence type: unordered `bbox_set`

## Contract
The image shows two pucks moving along perpendicular paths toward a sticky collision. Puck A contributes the horizontal momentum, puck B contributes the vertical momentum, and the stuck `A+B` puck shows the combined mass.

The public task asks for one signed final velocity component in m/s after the pucks stick. The internal `component_axis` query id selects `x` or `y`; `x` uses right as positive and left as negative, while `y` uses up as positive and down as negative.

## Evidence
Prompt-facing evidence contains one bbox around the queried component's momentum witnesses and the combined-mass label. For `component_axis=x`, that witness region covers puck A, its motion arrow, its mass and speed labels, and the combined-mass label. For `component_axis=y`, it covers the corresponding puck B witnesses and the combined-mass label.

## Prompt And Trace
Prompt bundle: `physics_mechanics_v0`; scene key: `sticky_collision_diagram`; task key: `sticky_collision_query`; query key: `velocity_component`.

Outputs `query_id="velocity_component"`. The trace records `component_axis`, puck masses, speeds, directions, signed momenta, final velocity components, option arrows, and evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized collision scene.
