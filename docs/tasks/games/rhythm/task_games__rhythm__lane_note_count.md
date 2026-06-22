# `task_games__rhythm__lane_note_count`

## Program Contract
- Domain: `games`
- Scene: `rhythm`
- Public task id: `task_games__rhythm__lane_note_count`
- Supported `query_id` values: `single`
- Answer schema: `integer_count`
- Annotation schema: `bbox_set`
- Program schema: `count(filter(notes, lane=target_lane)); scene=rhythm; scope=lane_note_count`
- Program code: `count.filter.rhythm_lane_notes`

## Notes
- `target_lane` is prompt-bound by lane number.
- A long vertical note counts as one note object.
- Annotation bboxes are all note objects in the specified lane.
- Scalar annotation checked: true.
