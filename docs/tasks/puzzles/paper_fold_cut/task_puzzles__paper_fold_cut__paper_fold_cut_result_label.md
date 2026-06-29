# `task_puzzles__paper_fold_cut__paper_fold_cut_result_label`

## Task
1. Domain: `puzzles`
2. Scene: `paper_fold_cut`
3. Task id: `task_puzzles__paper_fold_cut__paper_fold_cut_result_label`
4. Scene id: `paper_fold_cut`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox`

## Program Contract
`select_label(unfolded_result.option, rule=paper_fold_cut_unfolded_hole_pattern); scene=paper_fold_cut; scope=paper_fold_cut_result_label`

## Contract
1. Public `query_id`: `single`
2. The scene shows one fold-and-cut reference transformation and `5..6` labeled unfolded-result options.
3. Parameter axes: `fold_count=1|2`; `fold_axis=vertical|horizontal` selects the one-fold axis or the first fold of a two-fold sequence.
4. Scene axis: `fold_strip|fold_card|fold_outline`
5. Rendered cut holes use one sampled shape per instance: `circle|square|diamond|rounded_square`.
6. Answer is the selected unfolded-result option letter.
7. Annotation is exactly one image-pixel bbox around the winning option image.
8. `execution_trace.internal_grammar_id` records the fold-count and fold-axis renderer grammar.
9. `scalar_annotation_checked=true`
