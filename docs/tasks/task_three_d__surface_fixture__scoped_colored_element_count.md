# `task_three_d__surface_fixture__scoped_colored_element_count`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query id: `scoped_element_color_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows one projected fixture surface arranged in rows and columns with
repeated colored elements. The prompt asks for the number of elements of the
requested color within one sampled row or column.

The answer is the integer count of finalized present cells matching both the
requested scope and `color_name == target_color_name`.

## Annotation Contract
Annotation is a `bbox_set` containing one bounding box around each counted
colored surface element in the requested row or column. Same-color elements
outside the scope, other colors, the fixture panel, and decorative context are
not annotation.

## Prompt And Trace
The prompt bundle is `three_d_surface_fixture_v0` under `prompts/three_d/surface_fixture/`.
The trace records scene variant, target element type, target color, scope axis,
scope index, explicit cell metadata, projected element boxes, and the solver
count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b
solve-rate calibration are pending.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.

