# `task_games__rhythm__lane_hit_count`

## Program Contract
- Domain: `games`
- Scene: `rhythm`
- Public task id: `task_games__rhythm__lane_hit_count`
- Supported `query_id` values: `single`
- Answer schema: `integer_count`
- Annotation schema: `bbox_set`
- Program code: `count(filter(notes, lane=target_lane and note_in_hit_window(note, beat_window)=true)); scene=rhythm; scope=lane_hit_count`

## Notes
- `target_lane` and `beat_window` are rendered/prompt-bound sample arguments.
- Annotation bboxes are the matching notes in the selected lane.
- Scalar annotation checked: true.
