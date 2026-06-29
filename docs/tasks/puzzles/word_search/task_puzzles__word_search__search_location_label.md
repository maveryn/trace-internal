# `task_puzzles__word_search__search_location_label`

## Program Contract
`select_label(location_option, rule=target_word_start_cell_and_direction); scene=word_search; scope=search_location_label`

The scene shows a labeled word-search grid and option cards. The prompt names a
target word. The task finds the unique word placement and returns the option
letter whose start row, start column, and direction code match that placement.

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `answer_gt.value` is the correct option label.
3. `annotation_gt.type = bbox_sequence`
4. Annotation schema: `bbox_sequence`
5. Annotation is the ordered sequence of grid-cell bounding boxes for the found
   word, from first letter to last letter.
6. `scalar_annotation_checked = true`; this task has multiple ordered cell
   witnesses.

## Query Contract
1. Public `query_id`: `single`
2. Option labels are visible answer candidates, not public query branches.
3. Internal variation covers word, direction, option count, grid size, and scene
   styling only.

## Prompt Contract
1. Bundle: `puzzles_word_search_v1`
2. Scene key: `word_search`
3. Task key: `search_location_label_query`
4. Prompt query key: `search_location_label`
