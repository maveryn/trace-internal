# `task_puzzles__logic_grid__grid_uniqueness_completion_label`

## Summary
1. Domain: `puzzles`
2. Task group: `logic`
3. Task id: `task_puzzles__logic_grid__grid_uniqueness_completion_label`
4. Scene id: `logic_grid`
5. Goal: choose the option that fills one missing cell in a row/column uniqueness grid.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `grid_uniqueness_completion`
3. Internal `uniqueness_query`: `axis_uniqueness|row_and_column_uniqueness`
4. `axis_uniqueness` samples `uniqueness_axis=row|column`
5. Board size: `5x5..7x7`
6. Answer type: `option_letter`
7. Annotation type: `keyed_bbox_map`
8. Annotation target: role-keyed `source_grid` and `selected_option` bboxes
9. Scene variants: `logic_strip|logic_card|logic_outline`
10. Render metadata records the sampled shared panel style and global label font under `render_spec.text_style.font`.
