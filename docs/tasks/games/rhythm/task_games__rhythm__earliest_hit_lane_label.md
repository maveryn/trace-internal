# `task_games__rhythm__earliest_hit_lane_label`

## Program Contract
- Domain: `games`
- Scene: `rhythm`
- Public task id: `task_games__rhythm__earliest_hit_lane_label`
- Supported `query_id` values: `single`
- Answer schema: `integer_value`
- Annotation schema: `bbox`
- Program schema: `argmin(filter(notes, note_in_hit_window(note, beat_window)=true), metric=bottom_row_from_hit_line).lane_label; scene=rhythm; scope=earliest_hit_lane_label`
- Program code: `argmin.rhythm.earliest_hit_lane`

## Notes
- The sampled scene has one uniquely earliest hitting note by construction.
- Annotation is the scalar bbox around that earliest note.
- Scalar annotation checked: true.
