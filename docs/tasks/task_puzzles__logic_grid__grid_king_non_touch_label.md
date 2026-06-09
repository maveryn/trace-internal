# `task_puzzles__logic_grid__grid_king_non_touch_label`

## Summary
1. Domain: `puzzles`
2. Task group: `logic`
3. Task id: `task_puzzles__logic_grid__grid_king_non_touch_label`
4. Scene id: `logic_grid`
5. Goal: choose the option that fills one missing cell while identical symbols do not touch by edge or corner.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `king_non_touch`
3. Board size: `3x3..5x5`
4. Answer type: `option_letter`
5. Annotation type: `keyed_bbox_map`
6. Annotation target: role-keyed `source_grid` and `selected_option` bboxes
7. Scene variants: `logic_strip|logic_card|logic_outline`
8. Render metadata records the sampled shared panel style and global label font under `render_spec.text_style.font`.
