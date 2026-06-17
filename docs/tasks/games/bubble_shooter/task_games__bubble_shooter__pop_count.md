# `task_games__bubble_shooter__pop_count`

## Contract
1. Domain: `games`
2. Scene id: `bubble_shooter`
3. Public task id: `task_games__bubble_shooter__pop_count`
4. Supported `query_id` values: `single`
5. Answer schema: `integer_count`
6. Annotation schema: `bbox_set`
7. Program schema: `count(existing_same_color_component_adjacent_to(marked_landing_slot, shooter_color)) if component_size_plus_shooter >= 3 else 0; scene=bubble_shooter; scope=pop_count`

## Program Contract
- `count(existing_same_color_component_adjacent_to(marked_landing_slot, shooter_color)) if component_size_plus_shooter >= 3 else 0; scene=bubble_shooter; scope=pop_count`
- The inserted shooter bubble is used only to trigger the match threshold; it is not included in the answer or annotation.

## Generation Notes
1. This task is owned by the scene-package public file `trace/tasks/games/bubble_shooter/pop_count.py`.
2. The public task id selects the objective; `query_id` is `single`.
3. Annotation is projected from the same generated game state used for answer verification.
