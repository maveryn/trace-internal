# `task_three_d__surface_fixture__adjacent_to_reference_count`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query id: `adjacent_to_reference_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`

## Contract
The image shows one projected fixture surface arranged in rows and columns with
one uniquely colored reference element. The prompt asks how many elements share
an edge with that reference element.

The answer is the integer count of finalized present cells immediately above,
below, left, or right of the reference cell.

## Annotation Contract
Annotation is a `bbox_set` containing one bounding box around each counted
edge-adjacent element. The reference element itself, diagonal neighbors,
non-neighbor elements, the fixture panel, and decorative context are not
annotation.

## Prompt And Trace
The prompt bundle is `three_d_surface_fixture_v1` under `prompts/three_d/surface_fixture/`.
The trace records scene variant, target element type, reference element id,
reference color, explicit cell metadata, projected element boxes, and the solver
count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.
