# `task_games__lane_runner__path_coin_count`

## Contract
1. Domain: `games`
2. Scene id: `lane_runner`
4. Public task id: `task_games__lane_runner__path_coin_count`
5. Supported `query_id` values: `path_coin_count`

## Program
1. The scene shows a two-lane runner track with row cells, a start marker, a finish band, visible coins, and one shown path.
2. The shown path advances one row per step and may stay in the same lane or switch diagonally to the other lane.
3. The task asks how many coins are collected by the shown path.
4. Program schema: `count(intersection(coins, shown_path_cells)); scene=lane_runner; scope=path_coin_count`

## Answer And Annotation
1. `answer_gt.type`: `integer`.
2. `annotation_gt.type`: `point_set`.
3. Annotation points are the centers of every coin collected by the shown path.
4. Off-path coins, including same-row parallel distractors, are not annotation.
