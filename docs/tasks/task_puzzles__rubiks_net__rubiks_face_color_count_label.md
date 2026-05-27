# `task_puzzles__rubiks_net__rubiks_face_color_count_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__rubiks_net__rubiks_face_color_count_label`
4. Scene id: `rubiks_net`
5. Goal: choose the labeled numeric option for how many stickers on a queried face match the target color swatch.

## Contract
1. Public `query_variant`: `default`
2. `query_id`: `static_face_color_count_label|one_move_face_color_count_label|short_sequence_face_color_count_label`
3. Answer type: `option_letter`
4. Evidence type: `bbox_set`
5. Evidence targets: exactly one bbox for the selected numeric option panel
6. Scene variants: `classic_net|paper_net|cool_net`
7. Color policy: the prompt points to an on-image target swatch instead of requiring a free-form color answer; target color identity and counted sticker ids are recorded in trace metadata.
