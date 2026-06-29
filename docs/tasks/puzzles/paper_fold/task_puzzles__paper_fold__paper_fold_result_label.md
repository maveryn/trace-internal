# `task_puzzles__paper_fold__paper_fold_result_label`

## Task
1. Domain: `puzzles`
2. Scene: `paper_fold`
3. Task id: `task_puzzles__paper_fold__paper_fold_result_label`
4. Scene id: `paper_fold`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox`

## Program Contract
`select_label(folded_result.option, rule=single_axis_paper_fold_mark_projection); scene=paper_fold; scope=paper_fold_result_label`

## Contract
1. Public `query_id`: `single`
2. The scene shows one paper-fold reference transformation and `5..6` labeled result options.
3. Parameter axis: `fold_axis=vertical|horizontal`
4. Scene axis: `fold_strip|fold_card|fold_outline`
5. Answer is the selected folded-result option letter.
6. Annotation is exactly one image-pixel bbox around the winning option image.
7. `execution_trace.internal_grammar_id` records the scene-local fold-result grammar.
8. `scalar_annotation_checked=true`
