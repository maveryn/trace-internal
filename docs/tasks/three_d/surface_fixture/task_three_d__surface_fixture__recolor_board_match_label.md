# `task_three_d__surface_fixture__recolor_board_match_label`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query id: `single`
- Answer type: `option_letter`
- Annotation type: `bbox`

## Program Contract
- `match(option_board where fixed_position_color_state == recolor(original_fixed_position_color_state, source_color, destination_color)); scene=surface_fixture; scope=recolor_board_match_label`

## Contract
The image shows one original projected fixture board and four labeled candidate
fixture boards. The prompt gives exactly one hypothetical recolor rule of the
form `source_color -> destination_color` and asks which candidate board could be
the result.

All objects of the source color on the original board become the destination
color. Other colors are unchanged. Candidate boards keep the same visible cell
positions as the original board; only object colors change.
Generated named-color instances use readout-safe fixture variants and avoid
near-color distractors among the active semantic colors.

The answer is the single capital letter of the unique candidate board whose
fixed-position color state matches the final recolored original board.

## Annotation Contract
Annotation is the bounding box around the selected candidate board.
Individual objects, the original board, option labels alone, and
decorative context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_surface_fixture_v1` under
`prompts/three_d/surface_fixture/`. The trace records scene variant, target
element type, active colors, source color, destination color, original color
state by cell, final color state by cell, option color states, selected option
bbox, explicit cell metadata, and projected panel/object boxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.
