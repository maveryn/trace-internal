# `task_games__space_shooter__projectile_intercept_count`

## Contract
1. Domain: `games`
2. Task group: `space_shooter`
3. Scene id: `space_shooter`
4. Public task id: `task_games__space_shooter__projectile_intercept_count`
5. Supported `query_id` values: `projectile_intercept_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(projectiles, intersects_player_zone(projectile)=True)); scene=space_shooter; scope=projectile_intercept_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
