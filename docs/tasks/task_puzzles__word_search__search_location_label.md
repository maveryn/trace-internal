# `task_puzzles__word_search__search_location_label`

## Public Taxonomy
1. Domain: `puzzles`
2. Scene id: `word_search`
3. Task group: `word`
4. Task id: `task_puzzles__word_search__search_location_label`

## Query Contract
1. Branch metadata: `query_id`
2. `query_id`: `word_location_label`
3. Prompt asks for the option that gives the start row, start column, and compact direction code of one target word.
4. Internal variation:
   - grid size: `7..9`
   - word length: `3..4`
   - option count: `6..8`
   - scene variant: `word_search_classic|word_search_notebook|word_search_card`

## Answer And Evidence
1. `answer_gt.type = option_letter`
2. `answer_gt.value` is the capital-letter label of the correct option.
3. `evidence_gt.type = bbox_set`
4. Evidence contains the selected option box followed by ordered cell boxes for the target word path.

## Trace Contract
1. `execution_trace.placements` records the target word, 1-based start cell, direction, and ordered grid cells.
2. `execution_trace.option_specs` records every option, its compact direction code, and the unique correct option.
3. `execution_trace.supporting_item_ids` records the option id followed by ordered word-cell ids.

## Prompt Contract
1. Bundle: `puzzles_word_v0`
2. Scene key: `word_search`
3. Task key: `word_search_query`
4. Query key: `word_location_label`
