# `task_three_d__surface_fixture__recolor_board_match_label`

## Summary
- Domain: `three_d`
- Scene id: `surface_fixture`
- Scene package: `surface_fixture`
- Query id: `single`
- Answer type: `option_letter`
- Annotation type: unordered `bbox_set`

## Program Contract
- `match(option_board where color_counts == recolor_counts(original_color_counts, source_color, destination_color)); scene=surface_fixture; scope=recolor_board_match_label`

## Contract
The image shows one original projected fixture board and four labeled candidate
fixture boards. The prompt gives exactly one hypothetical recolor rule of the
form `source_color -> destination_color` and asks which candidate board could be
the result.

All objects of the source color on the original board become the destination
color. Other colors are unchanged. Candidate boards may rearrange objects, so
only the final color-count vector matters.

The answer is the single capital letter of the unique candidate board whose
visible color counts match the final recolored original board.

## Annotation Contract
Annotation is a `bbox_set` containing one box around the selected candidate
board. Individual objects, the original board, option labels alone, and
decorative context are not annotation.

## Prompt And Trace
The prompt bundle is `three_d_surface_fixture_v1` under
`prompts/three_d/surface_fixture/`. The trace records scene variant, target
element type, active colors, source color, destination color, original color
counts, final color counts, option color counts, selected option bbox, explicit
cell metadata, and projected panel/object boxes.

## Determinism
Generation is deterministic from `instance_seed`, explicit params, config
defaults, prompt bundle, and code versions. Answers and annotation come from the
same finalized fixture trace.
