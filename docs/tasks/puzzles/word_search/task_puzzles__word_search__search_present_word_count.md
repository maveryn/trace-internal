# `task_puzzles__word_search__search_present_word_count`

## Program Contract
`count(word_bank_entry, predicate=appears_in_grid); scene=word_search; scope=search_present_word_count`

The scene shows a labeled word-search grid and a word bank. The task searches
for each listed word and counts the word-bank entries that are actually present
in the grid.

## Answer And Annotation
1. `answer_gt.type = integer`
2. `answer_gt.value` is the number of listed words present in the grid.
3. `annotation_gt.type = segment_set`
4. Annotation schema: `segment_set`
5. Annotation contains one image-pixel segment for each present word, from the
   first-letter cell center to the last-letter cell center.
6. `scalar_annotation_checked = true`; this task has a variable-size witness
   set.

## Query Contract
1. Public `query_id`: `single`
2. Internal variation covers word bank, present count, word placements, grid
   size, and scene styling only.

## Prompt Contract
1. Bundle: `puzzles_word_search_v1`
2. Scene key: `word_search`
3. Task key: `search_present_word_count_query`
4. Prompt query key: `search_present_word_count`
