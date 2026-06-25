# `task_three_d__carousel__between_marked_items_count`

## Summary
- Domain: `three_d`
- Scene id: `carousel`
- Scene package: `carousel`
- Query ids: `between_color_anchors_count`, `between_object_anchors_count`
- Answer type: `integer`
- Annotation type: `bbox_set`
- Annotation schema: `bbox_set`

## Program Contract
- `count(belt_cycle[target_belt_key][(start_anchor_index+k) mod n] for k=1..target_count before end_anchor_index); scene=carousel; scope=between_marked_items_count`
- `count(belt_cycle[target_belt_key][(start_anchor_index+k) mod n] for k=1..target_count before end_anchor_index); scene=carousel; scope=between_marked_items_count`

## Contract
The image shows one 3D conveyor carousel with two visible concentric
elliptical belts: an inner belt and an outer belt. The task selects one belt
and marks two anchor objects on that belt with red boxes and labels `A` and
`B`.

The answer is the number of objects strictly between `A` and `B` when moving
from `A` to `B` in the visible belt-arrow direction. The marked anchor objects
are excluded from the count. Because the belt is cyclic, the `A` and `B`
labels define the ordered path.

For `between_color_anchors_count`, anchor descriptions in the prompt use the
anchor color labels. For `between_object_anchors_count`, anchor descriptions
use the anchor object names. The program is otherwise the same; the query id
branch only changes the prompt-facing anchor descriptor.

Answer support is `1..5`. The inner belt contains at most 8 objects and the
outer belt contains at most 12 objects.

## Annotation Contract
Annotation is a `bbox_set`. Each box marks one counted object strictly between
the marked anchors along the belt-arrow direction. The marked anchor objects,
marker boxes, labels, belt surfaces, arrows, and decorative context are not
annotation.

## Prompt And Trace
The prompt bundle is `three_d_carousel_v1` under
`prompts/three_d/carousel/`. Named color prompts use the canonical repo-wide
color format, such as `blue [#2D75E6]`.

The trace records scene variant, selected belt key, marked anchor object ids,
anchor labels, belt object sequence, counted between-object ids, object specs,
projected object boxes and centers, camera, projection frame, and solver count
predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from
the same finalized carousel trace.
