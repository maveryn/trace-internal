# `task_games__minesweeper__reveal_outcome_label`

## Contract
1. Domain: `games`
2. Scene id: `minesweeper`
3. Public task id: `task_games__minesweeper__reveal_outcome_label`
4. Supported `query_id` values: `reveal_outcome_label`
5. Answer schema: `option_letter`
6. Annotation schema: `keyed_bbox_set_map`
7. Program schema: `option_letter(reveal_outcome(marked_hidden_cell)); scene=minesweeper; scope=reveal_outcome_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. The correct option is shown in the image alongside five distractor reveal outcomes.
4. Annotation keys are `target_cell`, `supporting_clues`, and `supporting_flags`, projected from the same generated game state used for answer verification.
