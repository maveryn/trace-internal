# `task_games__solitaire__foundation_ready_count`

## Contract
1. Domain: `games`
2. Scene id: `solitaire`
3. Public task id: `task_games__solitaire__foundation_ready_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count(exposed_tableau_cards(can_move_to_foundation)); scene=solitaire; scope=foundation_ready_count`
8. Scalar annotation checked: `true`

## Program Contract
- `count(exposed_tableau_cards(can_move_to_foundation)); scene=solitaire; scope=foundation_ready_count`

## Generation Notes
1. Count only exposed tableau cards, using the visible foundation suit and top-rank state.
2. Annotation contains bboxes for the counted exposed cards plus the foundation piles used to decide the count.
3. Prompt wording comes from `prompts/games/solitaire/games_solitaire_v1.json`.
