# `task_tile_path_shortest_path`

## 1) Identity
1. Domain: `tile`
2. Task group: `path`
3. Task id: `task_tile_path_shortest_path`
4. Objective: return shortest-path length with coordinate-grounded path evidence.

## 2) Scene + task contract
1. Supported `task_variant` values: `shortest_path`
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `grid_point_path`
4. Scene geometry:
   - exactly one dense `rows x cols` board,
   - `tiling_type="rectangular_tiling"`,
   - canonical tile coordinates are zero-based `(row, col)` with top-left origin,
   - this task forces square tiles (`tile_width_px == tile_height_px`) so step counts do not look direction-dependent.
5. Generation guarantees:
   - start and goal are distinct open cells,
   - maze has exactly one shortest path,
   - obstacle tiles are blocked and use the reserved black role,
   - start and goal tiles use fixed role colors `green [#37B94B]` and `red [#E63232]`,
   - each instance samples a target shortest-path length from the configured range and accepts only mazes whose unique shortest path matches that target exactly.

## 3) Prompt contract
1. Bundle: `tile_path_v1`
2. `task_family_key`: `rectangular_tile_board`
3. `task_key`: `shortest_path_query`
4. Required slots:
   - task-family: `rows`, `cols`
   - task: `obstacle_color`, `start_color`, `goal_color`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Slot source:
   - shared JSON-format contracts from `configs/domains/tile/base.yaml` (`prompt.shared`),
   - task-group prompt slots from `configs/domains/tile/path.yaml` (`prompt.shared`).
6. Modes: `answer_only`, `answer_and_evidence`
7. Variant policy: exactly 5 prompt variants for each required task-family/task/mode key.
8. Prompt-facing role colors include canonical hex labels in brackets.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the ordered list of shortest-path tile coordinates, including the start and goal tiles: `[[row, col], ...]`.
2. `witness_symbolic` stores the shortest-path stable tile ids (`cell_{row}_{col}`) as an `id_path`.
3. `projected_evidence` includes:
   - `grid_point_path`
   - `pixel_point_path`
   - `bbox_set`
4. `scene_ir.relations.adjacency_open` stores the open-cell 4-neighbor relation keyed by stable tile ids.
5. `execution_trace` records:
   - target shortest-path value and configured target range,
   - role color labels/rgb values,
   - start and goal coordinates/ids,
   - blocked coordinates/ids,
   - shortest-path coordinates/ids.

## 5) Visual policy
1. Background and post-image noise use the merged tile-domain visual defaults from `configs/domains/tile/base.yaml`.
2. Tile-domain defaults for this task use non-grid backgrounds only; graph-paper or external grid backgrounds are not allowed.
3. Obstacles are rendered as black tiles, the start tile is green, the goal tile is red, and other open tiles use a neutral light fill.
4. Row labels are rendered on the left gutter and column labels are rendered on the top gutter.
5. Canvas size is derived from the sampled board geometry rather than fixed globally.
6. Post-image noise defaults are disabled (`apply_prob = 0.0`).
7. Applied background/noise metadata is emitted in trace.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Non-unique or invalid mazes are rejected/resampled.
3. Answers and path evidence come from the same sampled blocked-grid state.
4. No semantic auto-relaxation.
