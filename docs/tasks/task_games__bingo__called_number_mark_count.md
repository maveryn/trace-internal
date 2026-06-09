# `task_games__bingo__called_number_mark_count`

## Contract
1. Domain: `games`
2. Task group: `bingo`
3. Scene id: `bingo`
4. Public task id: `task_games__bingo__called_number_mark_count`
5. Supported `query_id` values: `called_marked_number_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(called_numbers(card), is_marked(cell_for_called_number))); scene=bingo; scope=called_number_mark_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation marks the card cells for called numbers that are currently marked.
