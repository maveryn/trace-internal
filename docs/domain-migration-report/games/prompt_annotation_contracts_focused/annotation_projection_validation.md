# Annotation Projection Validation

- sampled instances: `7`
- query ids covered: `7`
- annotation projection/geometry issues: `0`
- annotation types: `{'bbox': 1, 'bbox_set': 6}`
- tasks with incomplete coverage or generation errors: `0`

## Coverage

| task | expected query ids | collected counts | generated | issues |
| --- | --- | --- | ---: | --- |
| task_games__connect_four__column_disc_profile_label | `column_disc_profile_label` | `{'column_disc_profile_label': 1}` | 1 | `` |
| task_games__connect_four__winning_move_count | `winning_move_count` | `{'winning_move_count': 1}` | 1 | `` |
| task_games__crossing__moving_object_direction_count | `left_moving_object_count, right_moving_object_count` | `{'left_moving_object_count': 1, 'right_moving_object_count': 1}` | 2 | `` |
| task_games__darts__bullseye_membership_count | `inside_bullseye_count, outside_bullseye_count` | `{'inside_bullseye_count': 1, 'outside_bullseye_count': 1}` | 2 | `` |
| task_games__lane_runner__safe_path_label | `single` | `{'single': 1}` | 2 | `` |

## Issues

No issues found.
