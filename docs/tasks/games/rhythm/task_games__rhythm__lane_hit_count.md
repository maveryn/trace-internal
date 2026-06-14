# `task_games__rhythm__lane_hit_count`

## Contract
1. Domain: `games`
2. Scene: `rhythm`
3. Scene id: `rhythm`
4. Public task id: `task_games__rhythm__lane_hit_count`
5. Supported `query_id` values: `lane_hit_count`
6. Answer schema: `integer_count`
7. Annotation schema: `bbox_set`
8. Program schema: `count(filter(notes, lane=target_lane and note_in_hit_window(note, beat_window)=True)); scene=rhythm; scope=lane_hit_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
