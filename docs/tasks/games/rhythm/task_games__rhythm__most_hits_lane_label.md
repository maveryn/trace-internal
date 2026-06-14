# `task_games__rhythm__most_hits_lane_label`

## Contract
1. Domain: `games`
2. Scene: `rhythm`
3. Scene id: `rhythm`
4. Public task id: `task_games__rhythm__most_hits_lane_label`
5. Supported `query_id` values: `most_hits_lane_label`
6. Answer schema: `integer_value`
7. Annotation schema: `bbox_set`
8. Program schema: `integer_label(arg_extreme(lanes, metric=count(filter(notes, lane=lane and note_in_hit_window(note, beat_window)=True)), direction=highest)); scene=rhythm; scope=most_hits_lane_label`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation is projected from the same generated game state used for answer verification.
