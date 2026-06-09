# `task_games__space_shooter__clear_shot_score_value`

## Contract
1. Domain: `games`
2. Task group: `space_shooter`
3. Scene id: `space_shooter`
4. Public task id: `task_games__space_shooter__clear_shot_score_value`
5. Supported `query_id` values: `clear_shot_score_value`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`
8. Program schema: `sum(score(enemy) for enemy in enemy_targets if shot_line_blocked(enemy)=False); scene=space_shooter; scope=clear_shot_score_value`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
