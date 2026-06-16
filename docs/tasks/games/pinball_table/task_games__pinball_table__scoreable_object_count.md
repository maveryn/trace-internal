# `task_games__pinball_table__scoreable_object_count`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/pinball_table/`
3. Scene id: `pinball_table`
4. Public task id: `task_games__pinball_table__scoreable_object_count`
5. Supported `query_id` values: `single`
6. Answer schema: `integer`
7. Annotation schema: `point_set`

## Program Contract
`count(object for object in pinball_objects if object.has_numeric_score_label); scene=pinball_table; scope=scoreable_object_count`

## Generation Notes
1. The scene renders a tilted pinball playfield with one ball, decorative table elements, and 5 to 8 visible table objects.
2. Scoreable objects display numeric score labels. Non-scoreable distractors display letter labels only.
3. The answer is the number of scoreable objects, balanced across 1 to 6 when the visible object count allows it.
4. Annotation is an unordered point set containing the pixel center of every scoreable object.
