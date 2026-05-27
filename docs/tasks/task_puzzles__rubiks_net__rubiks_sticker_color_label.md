# `task_puzzles__rubiks_net__rubiks_sticker_color_label`

## Summary
1. Domain: `puzzles`
2. Task group: `spatial`
3. Task id: `task_puzzles__rubiks_net__rubiks_sticker_color_label`
4. Scene id: `rubiks_net`
5. Goal: choose the labeled color-swatch option for a queried sticker on a Rubik-style cube net.

## Contract
1. Branch metadata: `query_id`
2. `query_id`: `static_sticker_color_label|one_move_sticker_color_label|short_sequence_sticker_color_label`
3. Answer type: `option_letter`
4. Evidence type: `bbox_set`
5. Evidence targets: exactly one bbox for the selected color-swatch option panel
6. Scene variants: `classic_net|paper_net|cool_net`
7. Color policy: sticker colors are sampled from the shared TRACE named-color palette and recorded in trace metadata; the answer is the option letter, not a free-form color name.
