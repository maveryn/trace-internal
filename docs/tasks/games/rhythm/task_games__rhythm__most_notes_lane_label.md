# `task_games__rhythm__most_notes_lane_label`

## Program Contract
- Domain: `games`
- Scene: `rhythm`
- Public task id: `task_games__rhythm__most_notes_lane_label`
- Supported `query_id` values: `single`
- Answer schema: `integer_value`
- Annotation schema: `bbox_set`
- Program schema: `argmax(lanes, metric=count(filter(notes, lane=lane))).label; scene=rhythm; scope=most_notes_lane_label`
- Program code: `argmax.rhythm.most_notes_lane`

## Notes
- The sampled scene has one lane with a unique maximum note-object count.
- A long vertical note counts as one note object.
- Annotation bboxes are all note objects in the winning lane.
- Scalar annotation checked: true.
