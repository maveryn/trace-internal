# `task_icons__single_transform_options__geometric_transform_result_label`

## Program Contract

`selection.geometric_transform_result_label(scene=single_transform_options, scope=labeled_option_cells, source=reference_icon, operation=rotate_90_clockwise|rotate_90_counterclockwise|rotate_180|flip_horizontal|flip_vertical, output=option_letter)`

## Identity

- Domain: `icons`
- Scene id: `single_transform_options`
- Task id: `task_icons__single_transform_options__geometric_transform_result_label`
- Objective: select the labeled option that shows a Reference icon after one geometric transform.

## Contract

- Supported `query_id` values: `rotate_90_clockwise_result_label`, `rotate_90_counterclockwise_result_label`, `rotate_180_result_label`, `flip_horizontal_result_label`, `flip_vertical_result_label`.
- Answer schema: `option_letter`.
- Annotation schema: `bbox_map`, keyed by `reference_icon` and `selected_option`.
- The rendered image has one Reference icon with a visible transform cue and six labeled option cells.
- Exactly one option cell shows the Reference icon after the queried transform.
- Distractors are the other supported transform results of the same Reference icon.

## Generation

- Uses the curated non-symmetric icon pool so identity, rotation, and flip signatures remain visually distinct.
- All six option icons share one tint within an instance, so the answer depends on geometric transform rather than color.
- The Reference icon and option icons use the same nominal icon size.
- Query selection is task-owned and uniform unless an explicit supported `query_id` is supplied.
- `object_count` is fixed at `6` because this task is a six-option visual MCQ.

## Prompt

- Prompt bundle: `icons_single_transform_options_v1`
- `scene_key`: `single_transform_options_transformation`
- `task_key`: `transformation_query`
- Query templates name the requested transform and ask for the option letter.
- Answer-only JSON shape: `{"answer":"C"}`
- Answer+annotation JSON shape: `{"annotation":{"reference_icon":[82,144,250,312],"selected_option":[532,104,702,274]},"answer":"C"}`

## Annotation

- `reference_icon` marks the visible Reference icon bbox.
- `selected_option` marks the full selected option cell bbox, not just the transformed icon.
- The annotation is keyed because the two boxes have different semantic roles.

## Tests

- Behavior and trace tests: `tests/test_icons_transformation_single_transform_options_tasks.py`
- Config and prompt bundle tests: `tests/test_icons_scene_config.py`
- Scene-package migration gates: `tests/test_scene_package_migration_contracts.py`
