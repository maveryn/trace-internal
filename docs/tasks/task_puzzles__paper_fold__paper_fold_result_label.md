# `task_puzzles__paper_fold__paper_fold_result_label`

## Task
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__paper_fold__paper_fold_result_label`
4. Scene id: `paper_fold`
5. Answer type: `option_letter`
6. Evidence type: `bbox_set`

## Contract
1. Public `query_variant`: `default`
2. `query_id`: `paper_fold_result`
3. The scene shows one paper-fold reference transformation and `5..6` labeled result options.
4. Parameter axis: `fold_axis=vertical|horizontal`
5. Scene axis: `fold_strip|fold_card|fold_outline`
6. Prompt-facing evidence is exactly one bbox for the winning option image.
7. `execution_trace.internal_query_variant` records the fold-axis renderer grammar.
