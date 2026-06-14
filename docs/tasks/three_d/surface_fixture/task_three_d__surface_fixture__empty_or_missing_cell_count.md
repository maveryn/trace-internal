# `task_three_d__surface_fixture__empty_or_missing_cell_count`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query id: `single`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`

## Program Contract
- `count(filter(surface_fixture_cells, present=false)); scene=surface_fixture; scope=empty_or_missing_cell_count`

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
The prompt bundle is `three_d_surface_fixture_v1` under `prompts/three_d/surface_fixture/`.
The trace records scene variant, target element type, explicit present/missing
cell metadata, projected missing-position boxes, and the solver count predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.
