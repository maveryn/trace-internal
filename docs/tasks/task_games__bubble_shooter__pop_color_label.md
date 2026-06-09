# `task_games__bubble_shooter__pop_color_label`

## Contract
1. Domain: `games`
2. Task group: `bubble_shooter`
3. Scene id: `bubble_shooter`
4. Public task id: `task_games__bubble_shooter__pop_color_label`
5. Supported `query_id` values: `pop_color_label`
6. Answer schema: `string_label`
7. Annotation schema: `point_set`
8. Program schema: `label(color(inserted_group(marked_shot))); scene=bubble_shooter; scope=pop_color_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
