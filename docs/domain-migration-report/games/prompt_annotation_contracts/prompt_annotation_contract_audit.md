# Prompt/Annotation Contract Audit

- tasks: `160`
- expected public-facing query ids: `207`
- sampled query ids: `207`
- sampled instances: `207`
- issues: `8`
- issue categories: `{'annotation_prompt': 8}`
- report directory: `docs/domain-migration-report/games/prompt_annotation_contracts`

Artifacts:
- Prompt redundancy: `docs/domain-migration-report/games/prompt_annotation_contracts/prompt_redundancy_audit.md`
- Annotation prompt clarity: `docs/domain-migration-report/games/prompt_annotation_contracts/annotation_prompt_audit.md`
- Annotation projection validation: `docs/domain-migration-report/games/prompt_annotation_contracts/annotation_projection_validation.md`
- Annotation overlay samples: `docs/domain-migration-report/games/prompt_annotation_contracts/annotation_overlay_samples`
- Machine-readable report: `docs/domain-migration-report/games/prompt_annotation_contracts/prompt_annotation_audit.json`

## Domain Task Counts

| domain | tasks |
| --- | ---: |
| games | 160 |

## Highest Priority Issues

| severity | category | code | task | variant | mode | message |
| --- | --- | --- | --- | --- | --- | --- |
| warning | annotation_prompt | missing_pixel_space_wording | task_games__bingo__completed_line_sum_value | single | answer_and_annotation | point_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_games__bowling__first_pin_hit_label | single | answer_and_annotation | point prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_games__connect_four__winning_move_column_label | single | answer_and_annotation | point prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_games__crossing__first_exit_object_label | single | answer_and_annotation | point prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_games__crossing__hit_object_label | single | answer_and_annotation | point prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_games__pacman__next_item_label | single | answer_and_annotation | point prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_games__pacman__pellet_count_before_ghost | single | answer_and_annotation | point_set_map prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_keyed_annotation_wording | task_games__pacman__pellet_count_before_ghost | single | answer_and_annotation | point_set_map prompt should state that annotation is an object/dictionary keyed by witness role. |
