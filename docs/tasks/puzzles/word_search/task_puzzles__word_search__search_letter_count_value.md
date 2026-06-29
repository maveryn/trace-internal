# `task_puzzles__word_search__search_letter_count_value`

## Program Contract
`count(grid_cell, predicate=letter_equals_target); scene=word_search; scope=search_letter_count_value`

The scene shows a labeled word-search grid. The prompt names one uppercase
letter. The task counts every visible grid cell containing that letter.

## Answer And Annotation
1. `answer_gt.type = integer`
2. `answer_gt.value` is the number of target-letter cells.
3. `annotation_gt.type = bbox_set`
4. Annotation schema: `bbox_set`
5. Annotation contains every grid-cell bounding box where the target letter
   appears.
6. `scalar_annotation_checked = true`; this task has a variable-size witness
   set.

## Query Contract
1. Public `query_id`: `single`
2. Internal variation covers grid size, target letter, target count, and scene
   styling only.

## Prompt Contract
1. Bundle: `puzzles_word_search_v1`
2. Scene key: `word_search`
3. Task key: `search_letter_count_value_query`
4. Prompt query key: `search_letter_count_value`
