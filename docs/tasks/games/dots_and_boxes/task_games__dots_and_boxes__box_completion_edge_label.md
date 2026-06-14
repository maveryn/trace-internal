# `task_games__dots_and_boxes__box_completion_edge_label`

## Contract
1. Domain: `games`
2. Scene id: `dots_and_boxes`
3. Public task id: `task_games__dots_and_boxes__box_completion_edge_label`
4. Supported `query_id` values: `single`
5. Answer schema: `option_letter`
6. Annotation schema: `point_pair_set`
7. Program schema: `label(argmax_option(candidate_edges, completes_box(edge))); scene=dots_and_boxes; scope=box_completion_edge_label`

## Program Contract
`label(argmax_option(candidate_edges, completes_box(edge))); scene=dots_and_boxes; scope=box_completion_edge_label`

## Generation Notes
1. The scene renders exactly six dashed missing-edge options labeled `A` through `F`.
2. Exactly one dashed option line completes a box if drawn.
3. Query ids are internal replay/sampling keys and do not define public task units.
4. Annotation is the endpoint point-pair of the selected dashed option line, projected from the same generated game state used for answer verification.
