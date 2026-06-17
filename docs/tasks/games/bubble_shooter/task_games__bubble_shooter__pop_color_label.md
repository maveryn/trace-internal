# `task_games__bubble_shooter__pop_color_label`

## Contract
1. Domain: `games`
2. Scene id: `bubble_shooter`
3. Public task id: `task_games__bubble_shooter__pop_color_label`
4. Supported `query_id` values: `single`
5. Answer schema: `string_label`
6. Annotation schema: `bbox_set`
7. Program schema: `label(color(inserted_group(marked_shot))); scene=bubble_shooter; scope=pop_color_label`

## Program Contract
- `label(color(inserted_group(marked_shot))); scene=bubble_shooter; scope=pop_color_label`

## Generation Notes
1. This task is owned by the scene-package public file `trace/tasks/games/bubble_shooter/pop_color_label.py`.
2. The public task id selects the objective; `query_id` is `single`.
3. Annotation is projected from the same generated game state used for answer verification.
