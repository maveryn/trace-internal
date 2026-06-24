# `task_games__solitaire__move_legality_label`

## Contract
1. Domain: `games`
2. Scene id: `solitaire`
3. Public task id: `task_games__solitaire__move_legality_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox_map`
7. Program schema: `select_option(legal_solitaire_move); scene=solitaire; scope=move_legality_label`
8. Scalar annotation checked: `true`

## Program Contract
- `select_option(legal_solitaire_move); scene=solitaire; scope=move_legality_label`

## Generation Notes
1. The scene shows tableau columns, four foundation piles, and move options.
2. Exactly four visible options are shown, and exactly one option is legal by solitaire tableau/foundation rules.
3. Annotation is a bbox map with `source_card` and `target` roles for the legal move.
4. Prompt wording comes from `prompts/games/solitaire/games_solitaire_v1.json`.
