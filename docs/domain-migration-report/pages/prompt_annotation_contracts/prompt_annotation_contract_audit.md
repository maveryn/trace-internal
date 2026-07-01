# Prompt/Annotation Contract Audit

- tasks: `80`
- expected public-facing query ids: `107`
- sampled query ids: `107`
- sampled instances: `107`
- issues: `6`
- issue categories: `{'annotation_prompt': 6}`
- report directory: `docs/domain-migration-report/pages/prompt_annotation_contracts`

Artifacts:
- Prompt redundancy: `docs/domain-migration-report/pages/prompt_annotation_contracts/prompt_redundancy_audit.md`
- Annotation prompt clarity: `docs/domain-migration-report/pages/prompt_annotation_contracts/annotation_prompt_audit.md`
- Annotation projection validation: `docs/domain-migration-report/pages/prompt_annotation_contracts/annotation_projection_validation.md`
- Annotation overlay samples: `docs/domain-migration-report/pages/prompt_annotation_contracts/annotation_overlay_samples`
- Machine-readable report: `docs/domain-migration-report/pages/prompt_annotation_contracts/prompt_annotation_audit.json`

## Domain Task Counts

| domain | tasks |
| --- | ---: |
| pages | 80 |

## Highest Priority Issues

| severity | category | code | task | variant | mode | message |
| --- | --- | --- | --- | --- | --- | --- |
| warning | annotation_prompt | missing_bbox_notation | task_pages__navigation_flow__navigation_path_target_label | menu_path_target_label | answer_and_annotation | bbox annotation prompt should explicitly use [x0, y0, x1, y1] pixel boxes. |
| warning | annotation_prompt | missing_bbox_notation | task_pages__navigation_flow__navigation_path_target_label | ribbon_group_command_label | answer_and_annotation | bbox annotation prompt should explicitly use [x0, y0, x1, y1] pixel boxes. |
| warning | annotation_prompt | missing_bbox_notation | task_pages__navigation_flow__navigation_path_target_label | sidebar_tree_target_label | answer_and_annotation | bbox annotation prompt should explicitly use [x0, y0, x1, y1] pixel boxes. |
| warning | annotation_prompt | missing_bbox_notation | task_pages__navigation_flow__same_group_target_label | single | answer_and_annotation | bbox annotation prompt should explicitly use [x0, y0, x1, y1] pixel boxes. |
| warning | annotation_prompt | missing_pixel_space_wording | task_pages__schema__join_path_length_value | single | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_pages__schema__relationship_count | single | answer_and_annotation | segment_set prompt should state that annotation coordinates are in pixel space. |
