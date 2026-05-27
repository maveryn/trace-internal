# `task_puzzles__word_search__search_letter_count_value`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `word_search`
3. Task group: `word`
4. Task id: `task_puzzles__word_search__search_letter_count_value`

## Query Contract
1. Public `query_variant`: `default`
2. `query_id`: `letter_count_value`
3. Prompt asks for the number of visible cells containing a target uppercase letter.
4. Internal variation:
   - grid size: `7..9`
   - target letter count: `2..12`
   - scene variant: `word_search_classic|word_search_notebook|word_search_card`

## Answer And Evidence
1. `answer_gt.type = integer`
2. `answer_gt.value` is the count of target-letter cells.
3. `evidence_gt.type = bbox_set`
4. Evidence contains every grid-cell box where the target letter appears.

## Trace Contract
1. `execution_trace.grid` records the generated letter grid.
2. `execution_trace.target_letter` records the queried letter.
3. `execution_trace.supporting_item_ids` records every matching cell id.

## Prompt Contract
1. Bundle: `puzzles_word_v0`
2. Scene key: `word_search`
3. Task key: `word_search_query`
4. Query key: `letter_count_value`
