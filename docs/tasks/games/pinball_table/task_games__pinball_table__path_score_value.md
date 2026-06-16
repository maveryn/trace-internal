# `task_games__pinball_table__path_score_value`

## Program Contract
1. Domain: `games`
2. Scene package: `trace/tasks/games/pinball_table/`
3. Scene id: `pinball_table`
4. Public task id: `task_games__pinball_table__path_score_value`
5. Supported `query_id` values: `single`
6. Answer schema: `integer`
7. Annotation schema: `point_sequence`
8. Program schema: `sum(score(hit_object) for hit_object in ordered_scoring_hits_along_visible_path); scene=pinball_table; scope=path_score_value`

## Generation Notes
1. The scene renders a tilted pinball playfield with one ball, a full drawn ball path that travels to a rail/top edge and then continues to the bottom edge, plus flippers, slingshots, rails, bumpers, lanes, and scored targets.
2. The path uses 3 or 4 visible segments with broad turn angles so it reads as a clean pinball trajectory rather than a dense zig-zag. It may include visible side/top ricochets and target rebounds; the model follows the drawn path rather than inferring hidden bounce physics.
3. Each answer candidate target displays a score value. Decorative flippers, rails, posts, and slingshots do not score.
4. Annotation is the ordered sequence of pixel center points for scored-target hits along the drawn path. If the same scored target is hit twice, its center point appears twice in the annotation sequence and its score is added twice.
