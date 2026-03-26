# Tesserae Task Inventory

This document is a TRACE-side reference for `/home/jovyan/work/tesserae`.
It is meant to help us identify candidate tasks to port or re-implement in TRACE.

Date inspected: 2026-03-26

Scope:
- committed local branches in Tesserae,
- divergent `origin/*` branches with distinct task surfaces,
- the current dirty working tree on branch `dsl`.

Method:
- task families were inventoried from committed task modules under `tesserae/tasks/`,
- branch surfaces were grouped when they exposed the same task ids,
- deprecated tasks are listed when code still exists but the task is intentionally unregistered,
- the current `dsl` checkout is dirty, so its untracked DSL tasks are called out separately from the committed `dsl` branch tip.

## Baseline: local `main`

Representative branch:
- `main` at `58f007f`

Registered task surface on local `main`:
- Diagram (8): `diagram_boxplot_median_rank`, `diagram_category_count`, `diagram_order_pattern`, `diagram_radial_ratio`, `diagram_scatter_regression`, `diagram_stat_category`, `diagram_stat_value`, `diagram_venn_intersection`
- Geometry (18): `geometry_angle`, `geometry_area`, `geometry_bead_cycle`, `geometry_collinearity`, `geometry_convexity`, `geometry_intersection_count`, `geometry_movement_pattern`, `geometry_parallel_count`, `geometry_point_in_polygon_count`, `geometry_point_to_line_distance`, `geometry_raven_progression`, `geometry_rotational_symmetry`, `geometry_segment_count`, `geometry_segment_length`, `geometry_shape_count`, `geometry_similarity_class`, `geometry_slope`, `geometry_stacked_count`
- Graph (1): `graph_cycle_count`
- Icon (12): `icon_color_set`, `icon_composition`, `icon_count`, `icon_identity_set`, `icon_mirror_symmetry`, `icon_noise_edits`, `icon_occlusion_order`, `icon_orientation`, `icon_pair_transform`, `icon_relative_position`, `icon_size`, `icon_wallpaper_groups`
- Natural (3 registered): `natural_intruder_patch`, `natural_object_classification`, `natural_patch_correspondence`
- Tile (10): `tile_cell_count`, `tile_color_multiset`, `tile_composition`, `tile_equivalence`, `tile_glyph_set`, `tile_hole_count`, `tile_line_length`, `tile_maze_reachability`, `tile_perimeter`, `tile_shortest_path`

Implemented but deprecated on local `main`:
- `natural_noise_edits`
- `natural_stuff_category`

Summary:
- local `main` is the stable 52-registered-task surface described in Tesserae's current `README.md`,
- the codebase still contains the two deprecated natural tasks above, so the total implemented module surface is 54 task modules.

## Branch Groups

### 1. Prism branches

Branches with the same task surface:
- `prism` at `f683e969`
- `dsl` at `f683e969` (committed tip only)
- `count` at `cdaf4faf`
- `origin/prism` at `b2099a38`
- `origin/count` at `16095e03`

Delta from local `main`:
- adds `prism_icon_count`

Task type added:
- Prism (1): `prism_icon_count`

Notes:
- `prism_icon_count` is a non-grid icon counting/localization task,
- it supports structured attribute-plus-spatial queries and uses `bbox` or `integer` answer modes,
- the `count` branches appear to add curriculum / parquet / upload tooling on top of the same Prism task surface rather than adding new task types.

### 2. Double-grid branch

Branch:
- `double-grid` at `fe34c3ed`

Delta from local `main`:
- adds `geometry_shape_set`
- adds `tile_hole_presence`
- uses older icon task ids: `icon_color`, `icon_identity`, `icon_similar_transformation`, `icon_nonsimilar_transformation`
- drops `geometry_movement_pattern`
- drops `graph_cycle_count`
- predates newer renamed icon task ids `icon_color_set`, `icon_identity_set`, and consolidated `icon_pair_transform`

Task surface interpretation:
- this is an older compare-style branch with a similar overall family spread,
- it is useful mostly as a source for legacy task formulations and pre-rename implementations.

### 3. Experimental branch

Branch:
- `experimental` at `12dec849`

Delta from local `main`:
- adds `natural_patch_flip`
- adds `natural_patch_rotation`
- adds `natural_thing_vs_stuff`
- adds `tile_movement_rule`
- drops `geometry_movement_pattern`

Task types added:
- Natural perturbation / classification tasks: `natural_patch_flip`, `natural_patch_rotation`, `natural_thing_vs_stuff`
- Tile rule/state task: `tile_movement_rule`

### 4. Odd-one-out branch

Branch:
- `odd-one-out` at `96cd8b0f`

Delta from local `main`:
- adds `natural_patch_flip`
- adds `natural_patch_rotation`
- adds `natural_thing_vs_stuff`
- adds `tile_movement_rule`
- drops `geometry_movement_pattern`
- drops `natural_patch_correspondence`

Task surface interpretation:
- this looks like an experimental line closer to odd-one-out / compare task development,
- relative to `experimental`, it also removes `natural_patch_correspondence`.

### 5. `origin/dev`

Branch:
- `origin/dev` at `762de86b`

Delta from local `main`:
- adds `tile_movement_rule`
- drops `geometry_movement_pattern`

Task surface interpretation:
- this is a narrower task-surface variant than `experimental`,
- it keeps the core families but only adds the tile movement-rule task.

### 6. Puzzle experiment branch

Branch:
- `experimental-puzzle-tictactoe-x-wins` at `d772b2e7`

Delta from local `main`:
- adds `natural_patch_flip`
- adds `natural_patch_rotation`
- adds `natural_thing_vs_stuff`
- adds `tile_movement_rule`
- adds `puzzle_tictactoe_x_wins`
- drops `geometry_movement_pattern`

Task type added beyond `experimental`:
- Puzzle (1): `puzzle_tictactoe_x_wins`

Interpretation:
- this branch extends the experimental task surface with a dedicated puzzle family,
- `puzzle_tictactoe_x_wins` is an odd-one-out grid task over rendered tic-tac-toe boards where the model selects cells in which X wins.

### 7. Remote `origin/main`

Branch:
- `origin/main` at `cb91facf`

Important divergence:
- local `main` and `origin/main` do not have the same task surface

Delta from local `main`:
- adds the `tessarae_*` family of 10 single-board integer-answer tasks

Task family added:
- Tessarae (10):
  - `tessarae_t1_color_count`
  - `tessarae_t2_shortest_path_unique`
  - `tessarae_t3_color_components`
  - `tessarae_t4_match3_rows`
  - `tessarae_t5_vertical_symmetry`
  - `tessarae_t6_holes_black`
  - `tessarae_t7_horizontal_symmetry`
  - `tessarae_t8_match3_cols`
  - `tessarae_t9_reachability_count`
  - `tessarae_t10_gravity_max_drop`

Interpretation:
- this branch adds a separate single-board tile-reasoning family,
- unlike the standard grid/index-list tasks, the Tessarae family is framed around direct integer answers plus explicit trace evidence,
- these are especially relevant if we want TRACE versions of board-state or state-transition tasks rather than cell-selection tasks.

### 8. Upload / infra branch

Branch:
- `hf-upload-script` at `833bbd50`

Task surface:
- no task modules under `tesserae/tasks/`

Interpretation:
- treat this as an infrastructure-only branch, not a source of tasks to port.

## Current Dirty Working Tree on `dsl`

Current checkout:
- branch `dsl`
- working tree is dirty and contains untracked task code not present in the committed `dsl` branch tip

Observed untracked task family:
- DSL (8):
  - `dsl_grid_match_color`
  - `dsl_grid_match_shape`
  - `dsl_grid_match_condition`
  - `dsl_grid_match_condition_quadrant`
  - `dsl_canvas_count_condition_evidence`
  - `dsl_canvas_count_inside_region_evidence`
  - `dsl_canvas_count_near_center_evidence`
  - `dsl_tile_shortest_path_evidence`

Interpretation:
- these appear to be DSL-driven wrappers over reusable scene/query templates,
- they are not yet part of the committed `dsl` branch task surface,
- if we plan to port from Tesserae soon, these are worth re-checking before implementation because they may still be in flux.

## Practical Porting Notes

Good Tesserae sources for TRACE-style re-implementation:
- `origin/main` Tessarae tasks if we want single-board integer-answer tile/state tasks
- Prism branches if we want non-grid count-and-localize icon tasks with structured predicates
- current dirty `dsl` worktree if we want DSL-driven evidence-heavy tasks
- `experimental-puzzle-tictactoe-x-wins` if we want puzzle-style board reasoning

Lower-priority or mostly historical references:
- `double-grid` for legacy compare/rename history
- `hf-upload-script` for infra only

## Quick Reference

Branch groups by task surface:
- Baseline local main: `main`
- Baseline plus Prism: `prism`, `dsl` (committed tip), `count`, `origin/prism`, `origin/count`
- Baseline plus Tessarae family: `origin/main`
- Experimental extras: `experimental`
- Experimental plus puzzle: `experimental-puzzle-tictactoe-x-wins`
- Odd-one-out variant: `odd-one-out`
- Narrow dev variant: `origin/dev`
- Legacy pre-rename surface: `double-grid`
- Infra only: `hf-upload-script`
- Uncommitted working-tree extras on `dsl`: current filesystem state under `/home/jovyan/work/tesserae`
