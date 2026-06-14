# `task_games__bubble_shooter__pop_count`

## Contract
1. Domain: `games`
2. Scene id: `bubble_shooter`
3. Public task id: `task_games__bubble_shooter__pop_count`
4. Supported `query_id` values: `default`
5. Answer schema: `integer_count`
6. Annotation schema: `point_set`
7. Program schema: `count(popped_bubbles_after_marked_shot); scene=bubble_shooter; scope=pop_count`

## Program Contract
- `count(popped_bubbles_after_marked_shot); scene=bubble_shooter; scope=pop_count`

## Generation Notes
1. This task is owned by the scene-package public file `trace/tasks/games/bubble_shooter/pop_count.py`.
2. The public task id selects the objective; `query_id` is `default`.
3. Annotation is projected from the same generated game state used for answer verification.
