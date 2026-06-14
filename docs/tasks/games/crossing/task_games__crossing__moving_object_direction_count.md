# `task_games__crossing__moving_object_direction_count`

## Contract
1. Domain: `games`
2. Scene id: `crossing`
3. Public task id: `task_games__crossing__moving_object_direction_count`
4. Supported `query_id` values: `left_moving_object_count`, `right_moving_object_count`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(filter(moving_objects, direction == requested_direction)); scene=crossing; scope=moving_object_direction_count`

## Generation Notes
2. Query ids are internal replay/sampling keys and do not define public task units.
3. Annotation marks the moving objects whose visible arrows point in the requested direction.
