# `task_games__crossing__first_exit_object_label`

## Contract
1. Domain: `games`
2. Scene id: `crossing`
3. Public task id: `task_games__crossing__first_exit_object_label`
4. Supported `query_id` values: `single`
5. Answer schema: `label_string`
6. Annotation schema: `point`
7. Program schema: `label(argmin(labeled_moving_objects, exit_tick(object, lane_count, direction))); scene=crossing; scope=first_exit_object_label`

## Program Contract
- `label(argmin(labeled_moving_objects, exit_tick(object, lane_count, direction))); scene=crossing; scope=first_exit_object_label`

## Generation Notes
1. Exactly four moving objects are labeled `A` through `D`; the answer is one of those labels.
2. The scene has no runner route; each labeled object moves horizontally by one lane cell per tick.
3. The target labeled object is the unique labeled object that exits past a left or right edge first.
4. Annotation is the center point of the labeled moving object that leaves the board first.
