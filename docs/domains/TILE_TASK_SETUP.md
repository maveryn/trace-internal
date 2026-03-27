# Tile Task Setup

## Purpose
This document defines the concrete v1 setup for TRACE tile tasks ported or re-implemented from Tesserae.
It is the source of truth for board geometry, coordinate grounding, and evidence conventions used by future tile-domain tasks.

## Scope
1. Applies to new TRACE tile tasks that render one board and ask questions about that board.
2. Focuses on coordinate-grounded rectangular tilings.
3. Non-goals for v1:
   - hex tilings,
   - triangular tilings,
   - circular/radial tilings,
   - multi-board comparison panels,
   - ragged or non-dense board silhouettes.

## Taxonomy
1. Keep `domain=tile`.
2. Keep `task_group` tied to reasoning mode (`path`, `count`, `reachability`, etc.), not to tiling family.
3. Record the board geometry in scene/render metadata via `tiling_type="rectangular_tiling"`.

## Core Board Contract
1. Each instance renders exactly one board.
2. Board index space is a dense `rows x cols` rectangle.
3. Every coordinate `(row, col)` with `0 <= row < rows` and `0 <= col < cols` names exactly one tile.
4. Tasks may mark tiles as blocked, empty, colored, highlighted, or target-bearing, but they must not treat in-bounds coordinates as missing.
5. Rectangular boards are allowed; tile shape is a uniform rectangle and is not required to be square.
6. Shared rectangular tile-board defaults use `rows, cols in [3, 7]`; larger boards should be treated as explicit task overrides rather than the domain default.

## Coordinate Frames

### Tile Coordinates (Canonical)
1. Public tile coordinates are zero-based `(row, col)`.
2. `(0, 0)` is the top-left tile.
3. `row` increases downward.
4. `col` increases to the right.
5. Row-major order is the canonical deterministic ordering for tile sets and coordinate lists.
6. Stable symbolic ids use the existing format `cell_{row}_{col}`.

### Pixel Coordinates (Derived)
1. Pixel origin is the top-left pixel `(0, 0)`.
2. Pixel coordinates use `(x, y)`.
3. Tile coordinates are the source of truth; pixel geometry is derived evidence only.

## Visual Indexing Requirements
1. If a task expects coordinate-grounded evidence or coordinate answers, the image must make the coordinate system discoverable.
2. Default policy: render column labels across the top gutter and row labels down the left gutter.
3. Do not place text inside every tile by default; keep the board visually clean unless a task specifically requires per-tile text.
4. The board may be centered within the canvas, but centering must not change the coordinate contract.
5. Tile tasks must not use external graph-paper or grid backgrounds by default, because those create a second competing coordinate system around the board.
6. Default tile-domain backgrounds should be solid or otherwise low-structure so the board itself remains the only grid-like scaffold in the image.

## Tile Geometry
1. Each board uses one uniform tile width and one uniform tile height.
2. Square tiles are not a separate tiling mode; they occur naturally when sampled width and height match.
3. Sample one `short_side_px` per board from `[32, 48]`.
4. Sample one `aspect_ratio` per board from `[1.0, 2.0]`, where `aspect_ratio = max(width, height) / min(width, height)`.
5. Sample one orientation per board:
   - wide: `(tile_width_px, tile_height_px) = (round(short_side_px * aspect_ratio), short_side_px)`
   - tall: `(tile_width_px, tile_height_px) = (short_side_px, round(short_side_px * aspect_ratio))`
6. All tiles in the same board share the same realized `tile_width_px` and `tile_height_px`.
7. If a sampled board does not fit the target canvas while keeping `short_side_px >= 32`, resample board/layout parameters instead of shrinking below the minimum.
8. Task-specific render overrides may force square tiles when equal-cost movement would look visually misleading under rectangular cells; `task_tile_path_shortest_path` and `task_tile_path_reachable_target_count` are the current examples.

## Adjacency / Topology
1. `rectangular_tiling` uses 4-neighbor adjacency by default: up, down, left, right.
2. Diagonal adjacency is not implied.
3. If a task needs a different neighborhood rule, it must declare it explicitly in task docs and trace metadata.

## Trace And Metadata Contract
1. `scene_ir.entities` should keep one `tile_cell` entity per board coordinate.
2. Each `tile_cell` entity should at minimum record:
   - `row`
   - `col`
   - task-specific attrs such as `blocked`, `color`, `role`, or `value`
3. `render_spec` and/or `render_map` should record enough geometry to project tile coordinates into pixel space deterministically:
   - `tiling_type`
   - `rows`
   - `cols`
   - `tile_width_px`
   - `tile_height_px`
   - board origin in pixels
   - coordinate-label gutter sizes when present
4. `witness_symbolic` should stay tile-based (`id_set`, `id_path`, or task-specific symbolic facts keyed by `cell_{row}_{col}`).
5. `projected_evidence` may include derived pixel artifacts such as:
   - `pixel_point_set`
   - `pixel_point_path`
   - `bbox_set`

## Prompt-Facing Evidence Policy
1. Prefer tile-coordinate evidence over pixel evidence for new rectangular tile tasks.
2. Default evidence types:
   - unordered tile sets: `grid_point_set`
   - ordered tile paths: `grid_point_path`
3. For tile tasks, `grid_point_*` payloads use integer `[row, col]` pairs in tile-grid coordinates.
4. Canonical ordering rules:
   - `grid_point_set`: row-major sorted `[[row, col], ...]`
   - `grid_point_path`: path order `[[row, col], ...]`
5. Keep pixel-space projections in trace for overlays/review, but do not make them the primary evidence contract unless a task specifically needs pixel boxes.
6. Active rectangular tile tasks should use `grid_point_set` / `grid_point_path` as the public evidence contract unless a task-specific doc explicitly justifies a different primary evidence type.

## Answer-Type Guidance
1. Current registered answer types favor scalar outputs (`integer`, `number`, etc.), while tile coordinates already fit naturally in evidence via `grid_point_set` and `grid_point_path`.
2. Initial TRACE ports should therefore prefer tasks with:
   - scalar answers, and
   - coordinate-grounded evidence
3. Good early candidates under this rule include:
   - shortest-path length,
   - reachability count,
   - connected-component count,
   - cell count under attribute predicates,
   - perimeter / hole-count style questions when the answer is numeric
4. Pure "return the set of tiles" answer tasks can come later if we add a dedicated answer-type contract or a stable JSON encoding policy for coordinate answers.

## Compatibility Note
1. `task_tile_path_shortest_path` and `task_tile_path_reachable_target_count` now follow this document's rectangular-board and tile-coordinate evidence policy.
2. Their deliberate geometry exception is square-only cells, which keep movement cues visually uniform.
3. `task_tile_transition_gravity_max_drop` is a current example of a scalar transition task that still uses tile-coordinate `grid_point_path` evidence for the winning mover trajectory.
4. `task_tile_relation_min_distance` is a current example of a rectangular-cell task that still uses `grid_point_path` evidence because its witness is a unique straight row/column segment and the answer is defined in orthogonal steps rather than free-form movement cost.
