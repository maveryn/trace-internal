# `task_games__solitaire__cascade_card_at_depth_label`

## Contract
1. Domain: `games`
2. Scene id: `solitaire`
3. Public task id: `task_games__solitaire__cascade_card_at_depth_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox`
7. Program schema: `select_option(card_at_visible_depth(column, depth)); scene=solitaire; scope=cascade_card_at_depth_label`
8. Scalar annotation checked: `true`

## Program Contract
- `select_option(card_at_visible_depth(column, depth)); scene=solitaire; scope=cascade_card_at_depth_label`

## Generation Notes
1. The prompt names a 1-based tableau column and a visible depth counted from the top of that column.
2. The visual options show card faces, and exactly one option matches the target tableau card.
3. Annotation is the scalar bbox of the target card in the tableau, not the option card.
4. Prompt wording comes from `prompts/games/solitaire/games_solitaire_v1.json`.
