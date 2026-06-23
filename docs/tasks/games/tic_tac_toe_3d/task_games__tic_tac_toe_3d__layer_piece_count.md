# `task_games__tic_tac_toe_3d__layer_piece_count`

## Contract
1. Domain: `games`
2. Scene: `tic_tac_toe_3d`
3. Scene id: `tic_tac_toe_3d`
4. Public task id: `task_games__tic_tac_toe_3d__layer_piece_count`
5. Supported `query_id` values: `x_piece_count_in_layer`, `o_piece_count_in_layer`
6. Answer schema: `integer_count`
7. Annotation schema: `point_set`

## Program Contract
`count(layer_cells where mark=target_player); scene=tic_tac_toe_3d; scope=layer_piece_count`

## Generation Notes
1. Query ids are internal replay/sampling keys and do not define public task units.
2. The target layer is sampled from top, middle, and bottom.
3. Annotation is projected from the centers of every matching X or O piece in the requested layer; zero-count answers use an empty `point_set`.
