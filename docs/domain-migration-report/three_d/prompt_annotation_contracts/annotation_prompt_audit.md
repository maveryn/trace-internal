# Annotation Prompt Audit

- annotation prompt issues: `11`

## Issues

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
