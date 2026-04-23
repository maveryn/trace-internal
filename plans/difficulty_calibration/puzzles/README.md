# Puzzles Calibration

Historical note: the numeric task stats in this table are from the earlier `Qwen/Qwen3-VL-2B-Instruct` 32-rollout probe and should be treated as reference only. Active calibration work should use fresh `Qwen/Qwen3-VL-8B-Instruct` `200 x 32` probes.
Tasks in this domain: 10

| Task | Direction | Positive rollout rate | Zero-solve rate | Perfect-solve rate | Low omission frac | High omission frac | Task record |
|---|---|---:|---:|---:|---:|---:|---|
| task_puzzles_arithmetic_balance_value | make_easier | 0.0855 | 0.3305 | 0.0000 | 0.7406 | 0.0063 | [task_puzzles_arithmetic_balance_value](task_puzzles_arithmetic_balance_value.md) |
| task_puzzles_arithmetic_equation_value | make_harder | 0.5690 | 0.0078 | 0.2703 | 0.0945 | 0.3672 | [task_puzzles_arithmetic_equation_value](task_puzzles_arithmetic_equation_value.md) |
| task_puzzles_arithmetic_grid_value | make_easier | 0.0466 | 0.4844 | 0.0000 | 0.8867 | 0.0008 | [task_puzzles_arithmetic_grid_value](task_puzzles_arithmetic_grid_value.md) |
| task_puzzles_logic_adjacency_completion_label | make_easier | 0.0414 | 0.4344 | 0.0000 | 0.9102 | 0.0000 | [task_puzzles_logic_adjacency_completion_label](task_puzzles_logic_adjacency_completion_label.md) |
| task_puzzles_logic_grid_completion_label | make_easier | 0.0931 | 0.3195 | 0.0000 | 0.7234 | 0.0016 | [task_puzzles_logic_grid_completion_label](task_puzzles_logic_grid_completion_label.md) |
| task_puzzles_spatial_assembly_label | make_easier | 0.1412 | 0.0617 | 0.0000 | 0.4633 | 0.0000 | [task_puzzles_spatial_assembly_label](task_puzzles_spatial_assembly_label.md) |
| task_puzzles_spatial_cube_removal_count | make_easier | 0.1711 | 0.0781 | 0.0000 | 0.4367 | 0.0023 | [task_puzzles_spatial_cube_removal_count](task_puzzles_spatial_cube_removal_count.md) |
| task_puzzles_spatial_fold_result_label | make_easier | 0.1367 | 0.0500 | 0.0000 | 0.4461 | 0.0000 | [task_puzzles_spatial_fold_result_label](task_puzzles_spatial_fold_result_label.md) |
| task_puzzles_spatial_overlay_result_label | review | 0.2768 | 0.0141 | 0.0008 | 0.1664 | 0.0156 | [task_puzzles_spatial_overlay_result_label](task_puzzles_spatial_overlay_result_label.md) |
| task_puzzles_topology_bead_equivalence_count | make_easier | 0.1129 | 0.1742 | 0.0000 | 0.5836 | 0.0000 | [task_puzzles_topology_bead_equivalence_count](task_puzzles_topology_bead_equivalence_count.md) |
