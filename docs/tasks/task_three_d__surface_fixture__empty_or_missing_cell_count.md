# `task_three_d__surface_fixture__empty_or_missing_cell_count`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query id: `empty_or_missing_cell_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows one projected fixture surface arranged as a visible grid, with
some positions intentionally empty or missing. The prompt asks for the number of
missing positions.

The answer is the integer count of finalized cells whose `present == false`.

## Annotation Contract
Annotation is a `bbox_set` containing one bounding box around each counted
missing fixture position. Present elements, the fixture panel, and decorative
context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_surface_fixture_v0` under `prompts/three_d/surface_fixture/`.
The trace records scene variant, target element type, explicit present/missing
cell metadata, projected missing-position boxes, and the solver count predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b
solve-rate calibration are pending.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.

