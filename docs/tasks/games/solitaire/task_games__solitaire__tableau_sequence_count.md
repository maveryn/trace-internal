# `task_games__solitaire__tableau_sequence_count`

## Contract
1. Domain: `games`
2. Scene id: `solitaire`
3. Public task id: `task_games__solitaire__tableau_sequence_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count(adjacent_tableau_pairs(descending_one_rank_and_opposite_color)); scene=solitaire; scope=tableau_sequence_count`
8. Scalar annotation checked: `true`

## Program Contract
- `count(adjacent_tableau_pairs(descending_one_rank_and_opposite_color)); scene=solitaire; scope=tableau_sequence_count`

## Generation Notes
1. Count only directly adjacent visible same-column pairs.
2. A counted pair has the lower card exactly one rank lower than the card above and opposite color.
3. Annotation contains unique card bboxes for cards participating in counted adjacent pairs.
4. Prompt wording comes from `prompts/games/solitaire/games_solitaire_v1.json`.
