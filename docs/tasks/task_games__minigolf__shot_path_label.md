# `task_games__minigolf__shot_path_label`

## Contract
1. Domain: `games`
2. Task group: `minigolf`
3. Scene id: `minigolf`
4. Public task id: `task_games__minigolf__shot_path_label`
5. Supported `query_id` values: `shot_path_label`
6. Answer schema: `string_label`
7. Annotation schema: `point_pair_set`
8. Program schema: `label(select_option(shot_paths, option_rule=path_satisfies_target)); scene=minigolf; scope=shot_path_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
