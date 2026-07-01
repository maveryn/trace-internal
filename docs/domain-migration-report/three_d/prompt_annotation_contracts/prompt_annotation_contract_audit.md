# Prompt/Annotation Contract Audit

- tasks: `60`
- expected public-facing query ids: `79`
- sampled query ids: `79`
- sampled instances: `79`
- issues: `11`
- issue categories: `{'annotation_prompt': 11}`
- report directory: `docs/domain-migration-report/three_d/prompt_annotation_contracts`

Artifacts:
- Prompt redundancy: `docs/domain-migration-report/three_d/prompt_annotation_contracts/prompt_redundancy_audit.md`
- Annotation prompt clarity: `docs/domain-migration-report/three_d/prompt_annotation_contracts/annotation_prompt_audit.md`
- Annotation projection validation: `docs/domain-migration-report/three_d/prompt_annotation_contracts/annotation_projection_validation.md`
- Annotation overlay samples: `docs/domain-migration-report/three_d/prompt_annotation_contracts/annotation_overlay_samples`
- Machine-readable report: `docs/domain-migration-report/three_d/prompt_annotation_contracts/prompt_annotation_audit.json`

## Domain Task Counts

| domain | tasks |
| --- | ---: |
| three_d | 60 |

## Highest Priority Issues

| severity | category | code | task | variant | mode | message |
| --- | --- | --- | --- | --- | --- | --- |
| error | annotation_prompt | negative_annotation_format_instruction | task_three_d__carousel__between_object_type_anchors_count | single | answer_and_annotation | Annotation-format prompt text must describe the requested witness category/shape; avoid non-witness exclusion instructions unless the exclusion defines the witness set boundary. |
| error | annotation_prompt | negative_annotation_format_instruction | task_three_d__conveyor__between_object_type_anchors_count | single | answer_and_annotation | Annotation-format prompt text must describe the requested witness category/shape; avoid non-witness exclusion instructions unless the exclusion defines the witness set boundary. |
| error | annotation_prompt | negative_annotation_format_instruction | task_three_d__surface_fixture__color_count_after_operations_value | single | answer_and_annotation | Annotation-format prompt text must describe the requested witness category/shape; avoid non-witness exclusion instructions unless the exclusion defines the witness set boundary. |
| warning | annotation_prompt | missing_pixel_space_wording | task_three_d__object_scene__line_side_label | left_of_directed_line | answer_and_annotation | point prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_three_d__object_scene__line_side_label | right_of_directed_line | answer_and_annotation | point prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_three_d__object_scene__marked_point_depth_extremum_label | closest_marked_point | answer_and_annotation | point prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_three_d__object_scene__marked_point_depth_extremum_label | farthest_marked_point | answer_and_annotation | point prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_three_d__object_scene__marked_point_vertical_relation_label | single | answer_and_annotation | point prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_three_d__object_scene__point_camera_distance_order_label | single | answer_and_annotation | point_map prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_three_d__object_scene__point_on_object_line_label | single | answer_and_annotation | point prompt should state that annotation coordinates are in pixel space. |
| warning | annotation_prompt | missing_pixel_space_wording | task_three_d__object_scene__reference_triangle_inside_label | single | answer_and_annotation | point prompt should state that annotation coordinates are in pixel space. |
