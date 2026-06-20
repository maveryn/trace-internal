# `task_three_d__object_cluster__total_object_count`

## Summary
- Domain: `three_d`
- Scene id: `object_cluster`
- Package: `trace/tasks/three_d/object_cluster/`
- Supported `query_id`: `single`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Annotation schema: `bbox_set`

## Program Contract
`count(filter(object_cluster_objects, is_countable_object = true)); scene=object_cluster; scope=total_object_count`

## Contract
The image shows many small synthetic perspective 3D objects arranged on a plain
surface. The objects remain visually clustered, but generation may use one or
more local centers with continuous compactness variation so scenes range from
more compact to more spread out. This level-0 cluster task asks for the total
number of visible objects, without filtering by object type, color, relation, or
region.

Generation uses a one-type object set: all visible objects are countable
instances from one sampled color-safe object type. The sampled object type,
cluster count, compactness, and object colors are render variety metadata only
and are not named in the prompt. There are no unrelated distractor objects in
this task. The default generated object-count support is `6-20`.

Visible objects use 2-4 canonical named colors for non-semantic visual variety
when the count permits. The color distribution is recorded in trace metadata as
`color_role = non_semantic_visual_variation`, `visual_color_names`, and
`visual_color_counts`; color is not part of the answer predicate.

The answer is the integer count of finalized visible objects with
`is_countable_object = true`. Pixels are render output, not verifier source of
truth.

## Annotation Contract
Annotation is a `bbox_set` containing one `[x0, y0, x1, y1]` pixel box around
each counted object.
The annotation set is unordered because all witnesses have the same semantic
role and annotation cardinality matches the answer.

## Prompt And Trace
The prompt bundle is `three_d_object_cluster_v1` under `prompts/three_d/object_cluster/`.
The trace records camera pose, projection frame, object world coordinates,
sampled dimensions, primary object type metadata, cluster layout metadata,
composition offset metadata, non-semantic color distribution, rendered
readability stats, all counted object ids, projected object boxes, and the
solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized 3D scene trace.
