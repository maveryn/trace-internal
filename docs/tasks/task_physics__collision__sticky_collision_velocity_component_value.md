# `task_physics__collision__sticky_collision_velocity_component_value`

## Summary
- Domain: `physics`
- Scene id: `collision`
- Task group: `mechanics`
- Query id: `velocity_component`
- Answer type: `integer`
- Evidence type: `keyed_point_map`

## Contract
The image shows two pucks moving along perpendicular paths toward a sticky collision. Puck A contributes the horizontal momentum, puck B contributes the vertical momentum, and the stuck `A+B` puck shows the combined mass.

The public task asks for one signed final velocity component in m/s after the pucks stick. The internal `component_axis` query id selects `x` or `y`; `x` uses right as positive and left as negative, while `y` uses up as positive and down as negative.

## Evidence
Prompt-facing evidence is a `keyed_point_map` over the centers of puck roles `A`, `B`, and `A+B`. For `component_axis=x`, puck A is the queried input component; for `component_axis=y`, puck B is the queried input component.

## Prompt And Trace
Prompt bundle: `physics_mechanics_v0`; scene key: `sticky_collision_diagram`; task key: `sticky_collision_query`; query key: `velocity_component`.

Outputs `query_id="velocity_component"`. The trace records `component_axis`, puck masses, speeds, directions, signed momenta, final velocity components, option arrows, and input-witness evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized collision scene.
