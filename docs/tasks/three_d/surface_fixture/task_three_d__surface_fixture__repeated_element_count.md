# `task_three_d__surface_fixture__repeated_element_count`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query id: `single`
- Answer type: `integer`
- Annotation type: unordered `bbox_set`

## Program Contract
- `count(filter(surface_fixture_elements, present=true, element_type=target_element_type)); scene=surface_fixture; scope=repeated_element_count`

## Contract
The image shows one projected fixture surface with a repeated element family:
tiles, holes, slots, compartments, vents, windows, doors, drawer pulls, bricks,
pavers, lockers, mailboxes, drive bays, buttons, solar panels, screws, hex
nuts, washers, sockets, hooks, indicator lights, brackets, U-bolts, or pipes.
The prompt asks for the number of visible repeated surface elements of that
family.

The scene variant determines the counted element type:

- `wall_tile_panel` counts `tile`
- `perforated_panel` counts `hole`
- `slot_board` counts `slot`
- `compartment_tray` counts `compartment`
- `vent_panel` counts `vent`
- `window_grid` counts `window`
- `door_bank` counts `door`
- `drawer_pull_panel` counts `drawer_pull`
- `brick_wall` counts `brick`
- `paver_floor` counts `paver`
- `locker_bank` counts `locker`
- `mailbox_bank` counts `mailbox`
- `server_rack` counts `drive_bay`
- `control_panel` counts `button`
- `solar_panel_array` counts `solar_panel`
- `screw_plate` counts `screw`
- `hex_nut_plate` counts `hex_nut`
- `washer_plate` counts `washer`
- `socket_bank` counts `socket`
- `hook_board` counts `hook`
- `indicator_light_panel` counts `light`
- `bracket_panel` counts `bracket`
- `u_bolt_plate` counts `u_bolt`
- `pipe_rack` counts `pipe`

The answer is the integer count of finalized elements whose `element_type`
matches the sampled `target_element_type`. Pixels are render output, not
verifier source of truth.

## Annotation Contract
Annotation is a `bbox_set` containing one whole-element bounding box for each
counted repeated surface element. The fixture panel, screw heads, and
background context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_surface_fixture_v1` under `prompts/three_d/surface_fixture/`.
The trace records scene variant, target element type, target element ids,
surface projection metadata, projected element boxes, and the solver count
predicate.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.
