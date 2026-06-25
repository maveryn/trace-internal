# `task_three_d__conveyor__belt_total_object_count`

## Summary
- Domain: `three_d`
- Scene id: `conveyor`
- Scene package: `conveyor`
- Query ids: `single` publicly; internal query id `belt_total_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Annotation schema: `bbox_set`

## Program Contract
- `count(filter(conveyor_objects, belt_key=target_belt_key)); scene=conveyor; scope=belt_total_object_count`

## Contract
The image shows one 3D conveyor carousel with two visible concentric
elliptical belts: an inner belt and an outer belt. The belts are distinguished
by position, not by text written on the image. Small 3D objects sit on the belt
surfaces.

Each generated instance uses one sampled object type across both belts. Object
colors may vary, but color is not part of the task predicate. The task asks for
the total number of visible objects on the requested belt.

The target belt is sampled as a generation axis. If the target belt is `inner`,
the answer support is `1..8`. If the target belt is `outer`, the answer support
is `1..12`.

## Annotation Contract
Annotation is a `bbox_set` containing one `[x0, y0, x1, y1]` pixel box around
each counted object on the requested belt. Objects on the other belt, belt
surfaces, arrows, and decorative station context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_conveyor_v1` under
`prompts/three_d/conveyor/`. The prompt asks for total objects on the
`INNER` or `OUTER` belt and does not mention the sampled object type or colors.

The trace records scene variant, belt records, target belt, sampled object type,
object specs, projected object boxes and centers, camera, projection frame, and
solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized conveyor trace.
