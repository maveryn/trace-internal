# `task_three_d__surface_fixture__color_count_after_operations_value`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query id: `single`
- Answer type: `integer`
- Annotation type: unordered `point_set`

## Program Contract
- `initial_count(filter(surface_fixture_elements, present=true, element_type=target_element_type, color_name=target_color_name)) + sum(signed_count(operation) for operation in operations if operation.color_name=target_color_name); scene=surface_fixture; scope=color_count_after_operations_value`

## Contract
The image shows one projected fixture surface with repeated colored elements.
The prompt gives exactly three hypothetical add/remove operations over the same
element family and asks for the final number of elements of the requested target
color after all operations are applied.

The answer is the integer final count:

1. Count original visible present cells whose
   `element_type == target_element_type` and
   `color_name == target_color_name`.
2. Add counts from hypothetical target-color add operations.
3. Subtract counts from hypothetical target-color remove operations.

Operations for non-target colors are distractors and do not change the answer.
Generation guarantees the target-color count changes and remains nonnegative.

## Annotation Contract
Annotation is a `point_set` containing one center point for each original visible
target-color surface element used as the starting count. Hypothetical added
elements, removed elements after the text operations, non-target colors, the
fixture panel, and decorative context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_surface_fixture_v1` under
`prompts/three_d/surface_fixture/`. The trace records scene variant, target
element type, target color, active colors, initial color counts, operation list,
final color counts, explicit cell metadata, projected element centers, and the
solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.
