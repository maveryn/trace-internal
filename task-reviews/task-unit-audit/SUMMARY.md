# TRACE Task-Unit Audit Summary

Cross-domain summary of the task-unit audit using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Overall outcome
1. Audited active tasks: `100`
2. Recommended outcomes:
   - `Keep`: `91`
   - `Split now`: `2`
   - `Latent split`: `7`
   - `Merge`: `0`
   - `Retire`: `0`
3. Main conclusion:
   - the current TRACE inventory is strong overall,
   - the main rebalancing need is a small set of **over-broad task ids** where one task currently mixes multiple visual-grounding families,
   - only a subset of those should be split immediately,
   - the rest are better treated as **latent splits** until both child families would be healthy standalone tasks,
   - there are **no current merge recommendations** and **no retire recommendations**.

## Interpretation
1. `Split now` means the current task is over-broad **and** the resulting child tasks already look broad enough to stand alone.
2. `Latent split` means the current task is over-broad, but at least one child family would still be too narrow if split today.
3. This distinction follows `docs/core/TASK_UNIT_POLICY.md`: different grounding families matter, but we should not create undersized tasks just because a split is conceptually clean.

## Domain-by-domain summary

### Stable as-is
- `diagrams`: `5 Keep`
- `documents`: `5 Keep`
- `graph`: `10 Keep`
- `puzzles`: `10 Keep`
- `temporal`: `5 Keep`
- `tile`: `10 Keep`

### Mostly healthy, with one split pressure point
- `charts`: `9 Keep`, `1 Split now`
- `geometry`: `9 Keep`, `1 Latent split`
- `icons`: `9 Keep`, `1 Latent split`

### Healthy, but with multiple over-broad task ids
- `games`: `8 Keep`, `2 Latent split`
- `physics`: `3 Keep`, `2 Latent split`
- `tables`: `8 Keep`, `1 Split now`, `1 Latent split`

## Split now

### Charts
- `task_charts_composition_subset_value`
  - split stacked-category composition readout
  - from pie/donut subset-share composition

### Tables
- `task_tables_counting_value_count`
  - split single-column threshold / interval counting
  - from pairwise row-wise column comparison counting

## Latent split

### Games
- `task_games_cards_hand_count`
  - split unordered hand-property counting
  - from ordered display-sequence / run reasoning
- `task_games_reversi_move_count`
  - split legal-destination counting
  - from marked-move flip-consequence reasoning

### Geometry
- `task_geometry_coordinate_relation`
  - split segment relation counting
  - from point relation counting
  - and from polygon interior lattice counting

### Icons
- `task_icons_pattern_structured_violation`
  - split numbered row-sequence violation
  - from numbered-grid rule violation

### Physics
- `task_physics_circuits_equivalent_resistance`
  - split full-network equivalent-resistance readout
  - from marked missing-resistor inference
- `task_physics_optics_ray_trace`
  - split bounce-point counting
  - from target-hit counting

### Tables
- `task_tables_statistics_summary_value`
  - split column summaries
  - from row summaries
  - and from full-table summaries

## No current merge recommendations
1. No audited domain produced a convincing merge case.
2. The current issue is not duplicate task ids; it is a small number of broad task ids that contain more than one grounding family.

## Watchlist only
These are still `Keep` for now, but they are worth revisiting if their families grow:
- `task_temporal_schedule_day_planner`
- `task_tables_statistics_summary_label`
- `task_physics_mechanics_force_diagram`
- `task_physics_mechanics_lever_balance`
- `task_physics_mechanics_spring_extension`

## Suggested rebalancing order
If we rebalance incrementally, the cleanest first wave is:
1. `task_charts_composition_subset_value`
2. `task_tables_counting_value_count`

Second wave, only after broadening the thinner child families:
3. `task_physics_circuits_equivalent_resistance`
4. `task_games_cards_hand_count`
5. `task_games_reversi_move_count`
6. `task_geometry_coordinate_relation`
7. `task_icons_pattern_structured_violation`
8. `task_physics_optics_ray_trace`
9. `task_tables_statistics_summary_value`

Rationale:
- the first wave already has plausible healthy children today,
- the second wave contains real over-broad tasks, but splitting them immediately risks creating child tasks that are too narrow.
