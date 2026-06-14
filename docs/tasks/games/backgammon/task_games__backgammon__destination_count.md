# `task_games__backgammon__destination_count`

## Contract
1. Domain: `games`
2. Scene id: `backgammon`
3. Public task id: `task_games__backgammon__destination_count`
4. Supported `query_id` values: `blocked_destination_count`, `hit_move_count`, `legal_move_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(candidate_destinations(dice_rolls, board_state), destination_status)); scene=backgammon; scope=destination_count`

## Program Contract
- `count(filter(candidate_destinations(dice_rolls, board_state), destination_status)); scene=backgammon; scope=destination_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from numbered destination point bboxes, not individual checker bboxes.
