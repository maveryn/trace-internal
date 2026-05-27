# `task_physics__collision__sticky_collision_direction_choice`

## Summary
- Domain: `physics`
- Scene id: `collision`
- Task group: `mechanics`
- Query id: `direction_choice`
- Answer type: `option_letter`
- Evidence type: unordered `bbox_set`

## Contract
The image shows two pucks moving along perpendicular paths toward a sticky collision. Puck A moves horizontally and puck B moves vertically; each puck has visible mass, speed, and direction. The stuck `A+B` puck shows the combined mass, and six labeled candidate arrows show possible post-collision directions.

The task asks which candidate arrow matches the direction of the stuck pair after conserving horizontal and vertical momentum.

## Evidence
Prompt-facing evidence is the bounding box of the correct candidate arrow option.

## Prompt And Trace
Prompt bundle: `physics_mechanics_v0`; scene key: `sticky_collision_diagram`; task key: `sticky_collision_query`; query key: `direction_choice`.

Public outputs use `query_variant="default"` and `query_id="direction_choice"`. The trace records puck masses, input speeds, signed momenta, final velocity components, the correct option letter, option angles, and evidence entity ids.

## Determinism
Generation is deterministic from `instance_seed`. Answers and evidence come from the same finalized collision scene.
