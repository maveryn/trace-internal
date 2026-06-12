# `task_three_d__surface_fixture__state_element_count`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query id: `element_state_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows one projected fixture surface with repeated elements that have
visible states, such as open/closed, lit/unlit, pressed, intact, or cracked.
The prompt asks for the number of elements in the requested state.

The answer is the integer count of finalized present cells whose
`element_type == target_element_type` and `state == target_state`.

## Annotation Contract
Annotation is a `bbox_set` containing one bounding box around each counted
surface element in the requested state. Other states, the fixture panel, and
decorative context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_surface_fixture_v0` under `prompts/three_d/surface_fixture/`.
The trace records scene variant, target element type, target state, explicit
cell metadata, projected element boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b
solve-rate calibration are pending.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.

