# `task_three_d__surface_fixture__repeated_element_count`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Task group: `spatial`
- Query id: `element_type_count`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`
- Status: pending_v0_review

## Contract
The image shows one projected fixture surface with a repeated element family:
tiles, holes, slots, compartments, vents, windows, doors, or drawer pulls. The
prompt asks for the number of visible repeated surface elements of that family.

The scene variant determines the counted element type:

- `wall_tile_panel` counts `tile`
- `perforated_panel` counts `hole`
- `slot_board` counts `slot`
- `compartment_tray` counts `compartment`
- `vent_panel` counts `vent`
- `window_grid` counts `window`
- `door_bank` counts `door`
- `drawer_pull_panel` counts `drawer_pull`

The answer is the integer count of finalized elements whose `element_type`
matches the sampled `target_element_type`. Pixels are render output, not
verifier source of truth.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-element bounding box for each
counted tile, hole, slot, compartment, vent, window, door, or drawer pull. The
fixture panel, screw heads, and background context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_spatial_v0` under `prompts/three_d/spatial/`.
The trace records scene variant, target element type, target element ids,
surface projection metadata, projected element boxes, and the solver count
predicate.

## Calibration
Fresh v0 task review, distribution check, scene review, and qwen25vl7b
solve-rate calibration are pending. Only artifacts generated from current
code/config with `calibration_baseline: "v0"` should be used as current
acceptance annotation.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.
