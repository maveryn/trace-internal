# `task_puzzles__logic_grid__grid_king_non_touch_label`

## Contract

1. Domain: `puzzles`
2. Scene package: `trace/tasks/puzzles/logic_grid/`
3. Scene id: `logic_grid`
4. Public task id: `task_puzzles__logic_grid__grid_king_non_touch_label`
5. Supported `query_id` values: `single`
6. Prompt query key: `king_non_touch`
7. Answer schema: `option_letter`
8. Annotation schema: `bbox_map`
9. Program schema: `select_option(logic_grid.missing_shape, rule=no_identical_side_or_corner_touch, options=6); scene=logic_grid; scope=grid_king_non_touch_label`

## Program Contract

- `select_option(logic_grid.missing_shape, rule=no_identical_side_or_corner_touch, options=6); scene=logic_grid; scope=grid_king_non_touch_label`

## Query Contract

- Supported public `query_id`: `single`
- The semantic rule is fixed: identical shapes may not touch by side or corner.
- Scene treatment, board size, answer-label position, symbol order, font, and palette/theme choices are generation or render axes, not public taxonomy axes.

## Generation Contract

- The renderer shows one square shape grid with one `?` cell and exactly six labeled image options.
- Exactly one option label is valid under the no-identical-side-or-corner-touch rule.
- Board size is sampled from `3x3..5x5`.
- Supported scene variants are `logic_strip`, `logic_card`, and `logic_outline`.
- The correct option is sampled uniformly from six option positions unless explicitly pinned for tests.

## Prompt Contract

- Bundle: `puzzles_logic_grid_v1`
- `scene_key`: `logic_grid`
- `task_key`: `grid_king_non_touch_label_query`
- `query_key`: `king_non_touch`
- Prompt-facing answer is the selected option label.
- Prompt-facing annotation is a `bbox_map` with image-pixel boxes for `source_grid` and `selected_option`.

## Annotation + Trace Contract

- `answer_gt.type`: `option_letter`
- `annotation_gt.type`: `bbox_map`
- `annotation_gt.value.source_grid`: bbox around the source grid.
- `annotation_gt.value.selected_option`: bbox around the selected option panel.
- `projected_annotation` includes `bbox_map`, `pixel_bbox_map`, and `value`.
- `render_map.option_panel_bboxes_px` stores option-panel bboxes keyed by `option_panel_id`.
- `execution_trace` records the public query, fixed semantic rule, neighboring shape set, option specs, answer option id/label, and solver trace.
- Answer and annotation are both projected from the same correct option id.

## Determinism

- Deterministic sampling/rendering from `instance_seed`, scene config, prompt bundle, and code version.
- No semantic auto-relaxation is used to force acceptance.
