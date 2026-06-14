# `task_games__pinball_table__first_hit_object_label`

## Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/pinball_table/`
3. Scene id: `pinball_table`
4. Public task id: `task_games__pinball_table__first_hit_object_label`
5. Supported `query_id` values: `first_hit_object_label`
6. Answer schema: `string_label`
7. Annotation schema: `point_set`
8. Program schema: `label(first_collision(straight_launch_path, labeled_pinball_objects)); scene=pinball_table; scope=first_hit_object_label`

## Generation Notes
1. The scene renders a tilted pinball playfield with one ball, one straight launch cue, flippers, slingshots, rails, bumpers, lanes, and labeled targets.
2. Labeled bumpers, drop targets, rollover lanes, and standup targets are answer candidates; flippers, rails, posts, and slingshots are decorative playfield structure.
3. The target answer is unique by construction: extending the cue intersects the selected object before any other labeled object.
4. Annotation is one pixel point at the center of the first-hit object, projected from the same generated geometry used for verification.
