# `task_games__rhythm__earliest_hit_lane_label`

## Contract
1. Domain: `games`
2. Scene: `rhythm`
3. Scene id: `rhythm`
4. Public task id: `task_games__rhythm__earliest_hit_lane_label`
5. Supported `query_id` values: `earliest_hit_lane_label`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`
8. Program schema: `integer_label(arg_extreme(filter(notes, note_in_hit_window(note, beat_window)=True), metric=bottom_distance_to_hit_line, direction=lowest).lane); scene=rhythm; scope=earliest_hit_lane_label`

## Generation Notes
1. This task follows the contract-v0 public taxonomy mapping in `review/taxonomy-audit/contract_v0_reanalysis/`.
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
