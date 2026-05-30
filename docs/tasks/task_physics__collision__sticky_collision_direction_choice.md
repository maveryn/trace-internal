# `task_physics__collision__sticky_collision_direction_choice`

## Summary
- Domain: `physics`
- Scene id: `collision`
- Task group: `mechanics`
- Query id: `direction_choice`
- Answer type: `option_letter`
- Evidence type: `keyed_point_map`

## Contract
The image shows two pucks moving along perpendicular paths toward a sticky collision. Puck A moves horizontally and puck B moves vertically; each puck has visible mass, speed, and direction. The stuck `A+B` puck shows the combined mass, and six labeled candidate arrows show possible post-collision directions.

The task asks which candidate arrow matches the direction of the stuck pair after conserving horizontal and vertical momentum.

## Evidence
Prompt-facing evidence is a `keyed_point_map` over the centers of puck roles `A`, `B`, and `A+B`. Puck speeds, masses, directions, and candidate arrows remain visible attributes and trace metadata.

## Prompt And Trace
Prompt bundle: `physics_mechanics_v0`; scene key: `sticky_collision_diagram`; task key: `sticky_collision_query`; query key: `direction_choice`.

Outputs `query_id="direction_choice"`. The trace records puck masses, input speeds, signed momenta, final velocity components, the correct option letter, option angles, and input-witness evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized collision scene.
