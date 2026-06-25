# `task_games__solitaire__tableau_destination_count_value`

## Contract
1. Domain: `games`
2. Scene id: `solitaire`
3. Public task id: `task_games__solitaire__tableau_destination_count_value`
4. Supported `query_id` values: `single`
5. Answer schema: `integer`
6. Annotation schema: `bbox_set`
7. Program schema: `count(tableau_columns(can_receive_marked_card)); scene=solitaire; scope=tableau_destination_count_value`
8. Scalar annotation checked: `true`

## Program Contract
- `count(tableau_columns(can_receive_marked_card)); scene=solitaire; scope=tableau_destination_count_value`

## Generation Notes
1. Exactly one exposed tableau card is visibly marked.
2. Count exposed tableau top-card destinations where the marked source card can be placed by the tableau rule: target rank exactly one higher and opposite color.
3. If the marked source card is a King, empty tableau columns count as legal destinations.
4. Foundation piles and hidden/decorative cards are not counted as destinations.
5. Annotation contains the bboxes for legal exposed top-card destinations and legal empty-column slots.
6. Prompt wording comes from `prompts/games/solitaire/games_solitaire_v1.json`.
