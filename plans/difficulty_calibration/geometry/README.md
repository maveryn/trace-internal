# Geometry Calibration

Historical note: the numeric task stats in this table are from the earlier `Qwen/Qwen3-VL-2B-Instruct` 32-rollout probe and should be treated as reference only. Active calibration work should use fresh `Qwen/Qwen3-VL-8B-Instruct` `200 x 32` probes.
Tasks in this domain: 10

| Task | Direction | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Low omission frac | High omission frac | Task record |
|---|---|---:|---:|---:|---:|---:|---|
| task_geometry_analytical_2d_value | make_harder | 0.5135 | 0.0422 | 0.0484 | 0.1242 | 0.2625 | [task_geometry_analytical_2d_value](task_geometry_analytical_2d_value.md) |
| task_geometry_analytical_3d_value | make_harder | 0.4974 | 0.1437 | 0.0133 | 0.2016 | 0.2578 | [task_geometry_analytical_3d_value](task_geometry_analytical_3d_value.md) |
| task_geometry_comparison_value | review | 0.2738 | 0.0375 | 0.0000 | 0.2227 | 0.0203 | [task_geometry_comparison_value](task_geometry_comparison_value.md) |
| task_geometry_coordinate_relation | make_easier | 0.1079 | 0.1461 | 0.0000 | 0.6273 | 0.0000 | [task_geometry_coordinate_relation](task_geometry_coordinate_relation.md) |
| task_geometry_counting_value | make_easier | 0.3228 | 0.0797 | 0.0117 | 0.2914 | 0.1195 | [task_geometry_counting_value](task_geometry_counting_value.md) |
| task_geometry_graphing_count | make_easier | 0.1127 | 0.2625 | 0.0000 | 0.6992 | 0.0031 | [task_geometry_graphing_count](task_geometry_graphing_count.md) |
| task_geometry_measurement_value | make_easier | 0.2344 | 0.1961 | 0.0039 | 0.4555 | 0.0656 | [task_geometry_measurement_value](task_geometry_measurement_value.md) |
| task_geometry_similarity_count | make_easier | 0.1674 | 0.0594 | 0.0000 | 0.4031 | 0.0000 | [task_geometry_similarity_count](task_geometry_similarity_count.md) |
| task_geometry_solid_view_count | make_easier | 0.0904 | 0.1484 | 0.0000 | 0.6914 | 0.0000 | [task_geometry_solid_view_count](task_geometry_solid_view_count.md) |
| task_geometry_transformation_match | make_easier | 0.1119 | 0.1070 | 0.0000 | 0.5656 | 0.0000 | [task_geometry_transformation_match](task_geometry_transformation_match.md) |
