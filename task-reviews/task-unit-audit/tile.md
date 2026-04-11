# Tile Task-Unit Audit

Task-unit audit for `domain=tile` using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Domain summary
1. The tile domain is narrow by design, but its current task units are mostly well-calibrated.
2. Every task uses the same rectangular-board visual grammar, yet each one still corresponds to a distinct grounded board operation: counting, components, path, reachability, symmetry, transition, or relation.
3. The domain does not show obvious merge or split pressure right now; the main limitation is future headroom, not current task-unit quality.
4. Recommended domain outcome:
   - `Keep`: `10`
   - `Split`: `0`
   - `Merge`: `0`
   - `Retire`: `0`

## Task findings

### `task_tile_count_color_components`
- Outcome: `Keep`
- Why: one coherent connected-components-by-color family.
- Scene variety: moderate; stable rectangular-board scaffold with varied board size, palette, and component layout.
- Query variety: narrow but appropriate (`color_components`).
- Grounding necessity: strong; the solver must identify all queried-color tiles and group them by 4-neighbor connectivity.
- Evidence fit: good; all queried-color tile coordinates are the natural witness.
- Follow-up: none required now.

### `task_tile_count_color_count`
- Outcome: `Keep`
- Why: one coherent plain color-frequency family.
- Scene variety: moderate; stable rectangular-board scaffold with varied board size, palette, and color distribution.
- Query variety: narrow but appropriate (`color_count`).
- Grounding necessity: strong; the solver must locate all queried-color tiles on the board.
- Evidence fit: good; matching tile coordinates are the natural witness.
- Follow-up: none required now.

### `task_tile_count_largest_component_size`
- Outcome: `Keep`
- Why: one coherent extremum-over-components family.
- Scene variety: moderate; stable board scaffold with varied component layouts and unique-largest-component construction.
- Query variety: narrow but appropriate (`largest_component_size`).
- Grounding necessity: strong; the model must identify all queried-color components and find the unique largest one.
- Evidence fit: good; only the winning component tiles are the natural witness.
- Follow-up: none required now.

### `task_tile_path_reachable_target_count`
- Outcome: `Keep`
- Why: one coherent start-to-target reachability family on a blocked grid.
- Scene variety: moderate; stable blocked-grid scaffold with varying obstacle layouts and marked targets.
- Query variety: narrow but appropriate (`reachable_target_count`).
- Grounding necessity: strong; the solver must reason about reachability from the start tile through the board.
- Evidence fit: good; reachable marked-target coordinates are the natural witness.
- Follow-up: none required now.

### `task_tile_path_shortest_path`
- Outcome: `Keep`
- Why: one coherent unique-shortest-path family on a blocked grid.
- Scene variety: moderate; stable blocked-grid scaffold with varying maze layouts and path lengths.
- Query variety: narrow but appropriate (`shortest_path`).
- Grounding necessity: strong; the solver must trace the unique shortest path from start to goal.
- Evidence fit: good; the ordered path coordinates are the natural witness.
- Follow-up: none required now.

### `task_tile_pattern_match3_run_count`
- Outcome: `Keep`
- Why: one coherent line-run counting family.
- Scene variety: moderate; stable board scaffold with varying size, palette, run placements, and row/column axis.
- Query variety: modest but coherent (`rows|cols`).
- Grounding necessity: strong; the solver must inspect contiguous same-color runs rather than just count colors globally.
- Evidence fit: good; one canonical witness run per counted line is a sensible stable witness.
- Follow-up: none required now.

### `task_tile_reachability_region_size`
- Outcome: `Keep`
- Why: one coherent reachable-region-size family on a blocked grid.
- Scene variety: moderate; stable blocked-grid scaffold with varying start placement and reachable region geometry.
- Query variety: narrow but appropriate (`region_size`).
- Grounding necessity: strong; the solver must determine the full reachable open region from the marked start.
- Evidence fit: good; reachable tile coordinates are the natural witness.
- Follow-up: none required now.

### `task_tile_relation_min_distance`
- Outcome: `Keep`
- Why: one coherent minimum-distance-between-regions family.
- Scene variety: moderate; stable board scaffold with varying region shapes and unique closest-pair geometry.
- Query variety: narrow but appropriate (`min_distance`).
- Grounding necessity: strong; the solver must reason about the relative positions of the two connected colored regions.
- Evidence fit: good; the unique straight shortest path between the closest pair is the natural witness.
- Follow-up: none required now.

### `task_tile_symmetry_violation_count`
- Outcome: `Keep`
- Why: one coherent mirror-violation counting family.
- Scene variety: moderate; stable board scaffold with varied axis choice, counted side, and violation placement.
- Query variety: modest but coherent (`vertical|horizontal`).
- Grounding necessity: strong; the solver must compare mirrored tile pairs across the chosen axis.
- Evidence fit: good; violating counted-side tile coordinates are the natural witness.
- Follow-up: none required now.

### `task_tile_transition_gravity_max_drop`
- Outcome: `Keep`
- Why: one coherent gravity-drop transition family.
- Scene variety: moderate; stable board scaffold with varying column obstacle stacks and drop-tile placements.
- Query variety: narrow but appropriate (`gravity_max_drop`).
- Grounding necessity: strong; the solver must reason about the implied post-gravity transition, not just the static board.
- Evidence fit: good; the winning drop trajectory is the natural witness.
- Follow-up: none required now.

## Recommended next action
1. Leave the tile domain unchanged for now.
2. Treat tile as a good example of a narrow-but-coherent domain: the task units are healthy even though future expansion headroom is limited.
