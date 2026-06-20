# `task_games__rhythm__most_hits_lane_label`

## Program Contract
- Domain: `games`
- Scene: `rhythm`
- Public task id: `task_games__rhythm__most_hits_lane_label`
- Supported `query_id` values: `single`
- Answer schema: `integer_value`
- Annotation schema: `bbox_set`
- Program code: `argmax(lanes, metric=count(filter(notes, lane=lane and note_in_hit_window(note, beat_window)=true))).label; scene=rhythm; scope=most_hits_lane_label`

## Notes
- The sampled scene has a unique winning lane by construction.
- Annotation bboxes are the hitting notes in the winning lane.
- Scalar annotation checked: true.
