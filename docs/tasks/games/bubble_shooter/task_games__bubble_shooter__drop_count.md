# `task_games__bubble_shooter__drop_count`

## Contract
1. Domain: `games`
2. Scene id: `bubble_shooter`
3. Public task id: `task_games__bubble_shooter__drop_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(disconnected_bubbles_after_pop(marked_shot)); scene=bubble_shooter; scope=drop_count`

## Program Contract
- `count(disconnected_bubbles_after_pop(marked_shot)); scene=bubble_shooter; scope=drop_count`

## Generation Notes
1. This task is owned by the scene-package public file `trace/tasks/games/bubble_shooter/drop_count.py`.
2. The public task id selects the objective; `query_id` is `single`.
3. Annotation is projected from the same generated game state used for answer verification.
