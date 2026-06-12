# `task_games__dots_and_boxes__three_sided_box_count`

## Contract
1. Domain: `games`
2. Scene id: `dots_and_boxes`
3. Public task id: `task_games__dots_and_boxes__three_sided_box_count`
4. Supported `query_id` values: `three_sided_box_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(boxes, drawn_side_count(box) = 3)); scene=dots_and_boxes; scope=three_sided_box_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
