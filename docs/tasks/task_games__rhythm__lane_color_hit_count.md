# `task_games__rhythm__lane_color_hit_count`

## Contract
1. Domain: `games`
2. Task group: `rhythm`
3. Scene id: `rhythm`
4. Public task id: `task_games__rhythm__lane_color_hit_count`
5. Supported `query_id` values: `lane_color_hit_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(notes, lane=target_lane and note_color=target_color and note_in_hit_window(note, beat_window)=True)); scene=rhythm; scope=lane_color_hit_count`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
