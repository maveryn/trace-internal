# `task_puzzles__word_search__search_present_word_count`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `word_search`
3. Task group: `word`
4. Task id: `task_puzzles__word_search__search_present_word_count`

## Query Contract
1. Branch metadata: `query_id`
2. `query_id`: `present_word_count`
3. Prompt asks how many of the five word-bank words appear in the grid.
4. Internal variation:
   - grid size: `7..9`
   - word length: `3..4`
   - word bank size: `5`
   - answer support: `1..5`
   - scene variant: `word_search_classic|word_search_notebook|word_search_card`

## Answer And Annotation
1. `answer_gt.type = integer`
2. `answer_gt.value` is the number of word-bank words present in the grid.
3. `annotation_gt.type = bbox_set`
4. Annotation contains each present word-chip box followed by ordered grid-cell boxes for present words.

## Trace Contract
1. `execution_trace.word_bank` records all listed words.
2. `execution_trace.present_words` records the listed words actually present in the grid.
3. `execution_trace.placements` records one unique placement for each present word.
4. `execution_trace.supporting_item_ids` records present word chips and ordered supporting cells.

## Prompt Contract
1. Bundle: `puzzles_word_v0`
2. Scene key: `word_search`
3. Task key: `word_search_query`
4. Query key: `present_word_count`
