# `task_games__rhythm__lane_note_score_value`

## Program Contract
- Domain: `games`
- Scene: `rhythm`
- Public task id: `task_games__rhythm__lane_note_score_value`
- Supported `query_id` values: `single`
- Answer schema: `integer_value`
- Annotation schema: `bbox_set`
- Program schema: `sum(map(filter(notes, lane=target_lane), color_score(note.color_key))); scene=rhythm; scope=lane_note_score_value`
- Program code: `sum.lookup.rhythm_lane_note_score`

## Notes
- `target_lane` is prompt-bound by lane number.
- The side score palette maps note colors to integer score values.
- A long vertical note scores once.
- Annotation bboxes are all note objects in the specified lane that contribute to the score.
- Scalar annotation checked: true.
