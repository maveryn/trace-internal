# `task_puzzles__paper_fold_cut__paper_fold_cut_result_label`

## Task
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__paper_fold_cut__paper_fold_cut_result_label`
4. Scene id: `paper_fold_cut`
5. Answer type: `option_letter`
6. Annotation type: `bbox_set`

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `paper_fold_cut_result`
3. The scene shows one paper-fold-and-cut reference transformation and `5..6` labeled unfolded result options.
4. Parameter axes:
   - `fold_count=1|2`
   - one-fold branches also sample `fold_axis=vertical|horizontal`
5. Scene axis: `fold_strip|fold_card|fold_outline`
6. Rendered cut holes use one sampled shape per instance: `circle|square|diamond|rounded_square`.
7. Prompt-facing annotation is exactly one bbox for the winning option image.
8. `execution_trace.internal_query_id` records the fold-count and fold-axis renderer grammar.
