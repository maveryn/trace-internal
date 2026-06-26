# `task_three_d__object_cluster__multi_attribute_xor_count`

## Summary
- Domain: `three_d`
- Scene id: `object_cluster`
- Package: `trace/tasks/three_d/object_cluster/`
- Supported `query_id`: `single`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Annotation schema: `bbox_set`

## Program Contract
`count(filter(object_cluster_objects, exactly_one(shape_type = target_shape_type, color_name = target_color_name))); scene=object_cluster; scope=multi_attribute_xor_count`

## Contract
The image shows many small synthetic perspective 3D colored objects arranged on a plain surface. The prompt asks how many objects match exactly one of two conditions: the object is the named type, or the object has the named color. Objects matching both conditions are explicitly excluded. Prompt-facing semantic colors include the canonical color hex label, for example `red [#E63232]`.

The answer is the integer count of finalized clustered objects whose recorded `shape_type` equals the sampled target type XOR whose recorded `color_name` equals the sampled target color. Generation includes at least one structured overlap distractor, such as a red cube when the prompt asks for objects that are exactly one of cubes or red objects. Generated color distractors avoid near-color named pairs such as blue/cyan/purple and red/maroon/magenta. Wrong-type distractors avoid target-confusable object families such as card/envelope/book, sphere/button, cup/bowl/tray, lantern/candle, and pencil/ruler.

## Annotation Contract
Annotation is a `bbox_set` containing one `[x0, y0, x1, y1]` pixel box around each counted object satisfying exactly one predicate condition. The annotation set is unordered because all counted witnesses have the same role and overlap objects are not counted.

## Prompt And Trace
The prompt bundle is `three_d_object_cluster_v1` under `prompts/three_d/object_cluster/`. The trace records camera pose, projection frame, object world coordinates, sampled dimensions, prompt-facing object names, semantic colors, target type/color, target object ids, shape/color/property counts, projected object boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config defaults, prompt bundle, and code versions. Answers and annotation come from the same finalized 3D scene trace.
