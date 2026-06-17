# `task_games__dots_and_boxes__completable_box_label`

## Contract
1. Domain: `games`
2. Scene id: `dots_and_boxes`
3. Public task id: `task_games__dots_and_boxes__completable_box_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `bbox`
7. Program schema: `label(filter(candidate_boxes, drawn_side_count(box)=3)); scene=dots_and_boxes; scope=completable_box_label`

## Program Contract
`label(filter(candidate_boxes, drawn_side_count(box)=3)); scene=dots_and_boxes; scope=completable_box_label`

## Generation Notes
1. The scene renders exactly six labeled box options `A` through `F`.
2. Exactly one labeled option box has exactly three drawn sides and can be completed by drawing one missing side.
3. Query ids are internal replay/sampling keys and do not define public task units.
4. Annotation is the full-cell bounding box of the selected labeled box, projected from the same generated game state used for answer verification.
