# `task_games__space_shooter__highest_threat_label`

## Contract
1. Domain: `games`
2. Task group: `space_shooter`
3. Scene id: `space_shooter`
4. Public task id: `task_games__space_shooter__highest_threat_label`
5. Supported `query_id` values: `highest_threat_label`
6. Answer schema: `string_label`
7. Annotation schema: `bbox_set`
8. Program schema: `label(arg_extreme(enemies, metric=threat_score(enemy), direction=highest)); scene=space_shooter; scope=highest_threat_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
