# `task_puzzles__logic_grid__grid_uniqueness_completion_label`

## Contract

1. Domain: `puzzles`
2. Scene package: `trace/tasks/puzzles/logic_grid/`
3. Scene id: `logic_grid`
4. Public task id: `task_puzzles__logic_grid__grid_uniqueness_completion_label`
5. Supported `query_id` values: `axis_uniqueness`, `row_and_column_uniqueness`
6. Prompt query keys: `axis_uniqueness`, `row_and_column_uniqueness`
7. Answer schema: `option_letter`
8. Annotation schema: `bbox_map`
9. Program schema: `select_option(logic_grid.missing_shape, rule=row_or_column_uniqueness|row_and_column_uniqueness, options=6); scene=logic_grid; scope=grid_uniqueness_completion_label`

## Program Contract

- `select_option(logic_grid.missing_shape, rule=row_or_column_uniqueness|row_and_column_uniqueness, options=6); scene=logic_grid; scope=grid_uniqueness_completion_label`

## Query Contract

- `axis_uniqueness`: infer the missing shape from either the row or column through the `?` cell. The sampled axis is recorded as `uniqueness_axis=row|column` in trace metadata.
- `row_and_column_uniqueness`: infer the missing shape from both the row and column through the `?` cell.
- Scene treatment, board size, sampled axis, answer-label position, symbol order, font, and palette/theme choices are generation or render axes, not public taxonomy axes.

## Generation Contract

- The renderer shows one square shape grid with one `?` cell and exactly six labeled image options.
- Exactly one option label completes the missing cell under the selected uniqueness rule.
- Board size is sampled from `5x5..7x7`.
- Supported scene variants are `logic_strip`, `logic_card`, and `logic_outline`.
- The correct option is sampled uniformly from six option positions unless explicitly pinned for tests.

## Prompt Contract

- Bundle: `puzzles_logic_grid_v1`
- `scene_key`: `logic_grid`
- `task_key`: `grid_uniqueness_completion_label_query`
- Prompt-facing answer is the selected option label.
- Prompt-facing annotation is a `bbox_map` with image-pixel boxes for `source_grid` and `selected_option`.

## Annotation + Trace Contract

- `answer_gt.type`: `option_letter`
- `annotation_gt.type`: `bbox_map`
- `annotation_gt.value.source_grid`: bbox around the source grid.
- `annotation_gt.value.selected_option`: bbox around the selected option panel.
- `projected_annotation` includes `bbox_map`, `pixel_bbox_map`, and `value`.
- `render_map.option_panel_bboxes_px` stores option-panel bboxes keyed by `option_panel_id`.
- `execution_trace` records the public query, semantic rule, sampled axis, board values, option specs, answer option id/label, and solver trace.
- Answer and annotation are both projected from the same correct option id.

## Determinism

- Deterministic sampling/rendering from `instance_seed`, scene config, prompt bundle, and code version.
- No semantic auto-relaxation is used to force acceptance.
