# `task_tile_path_reachable_target_count`

## 1) Identity
1. Domain: `tile`
2. Task group: `path`
3. Task id: `task_tile_path_reachable_target_count`
4. Objective: count how many marked target tiles are reachable from one start tile.

## 2) Scene + task contract
1. Supported `task_variant` values: `reachable_target_count`
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `grid_point_set`
4. Scene geometry:
   - exactly one dense `rows x cols` board,
   - `tiling_type="rectangular_tiling"`,
   - canonical tile coordinates are zero-based `(row, col)` with top-left origin,
   - this task forces square tiles (`tile_width_px == tile_height_px`) so movement cues stay visually symmetric.
5. Generation guarantees:
   - start is one open tile,
   - obstacle tiles are blocked and use the reserved black role,
   - marked target tiles are open tiles distinct from the start tile,
   - the task samples a target answer over the configured range and then samples a blocked board that can realize exactly that many reachable targets,
   - every instance places at least two marked targets total and keeps at least one unreachable marked target by construction,
   - start and target roles use fixed colors `green [#37B94B]` and `red [#E63232]`.

## 3) Prompt contract
1. Bundle: `tile_path_v1`
2. `task_family_key`: `rectangular_tile_board`
3. `task_key`: `reachable_target_count_query`
4. Required slots:
   - task-family: `rows`, `cols`
   - task: `obstacle_color`, `start_color`, `target_color`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Slot source:
   - shared JSON-format contracts from `configs/domains/tile/base.yaml` (`prompt.shared`),
   - task-group prompt slots from `configs/domains/tile/path.yaml` (`prompt.task_overrides.task_tile_path_reachable_target_count`).
6. Modes: `answer_only`, `answer_and_evidence`
7. Variant policy: exactly 5 prompt variants for each required task-family/task/mode key.
8. Prompt-facing role colors include canonical hex labels in brackets.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the row-major list of reachable marked-target tile coordinates: `[[row, col], ...]`.
2. `witness_symbolic` stores the reachable-target stable tile ids (`cell_{row}_{col}`) as an `id_set`.
3. `projected_evidence` includes:
   - `grid_point_set`
   - `pixel_point_set`
   - `bbox_set`
4. `scene_ir.relations.adjacency_open` stores the open-cell 4-neighbor relation keyed by stable tile ids.
5. `execution_trace` records:
   - configured answer range and selected target answer,
   - total marked-target count,
   - role color labels/rgb values,
   - start coordinate/id,
   - blocked coordinates/ids,
   - all target coordinates/ids,
   - reachable-target and unreachable-target coordinate/id partitions,
   - full reachable open-cell coordinates/ids.

## 5) Visual policy
1. Background and post-image noise use the merged tile-domain visual defaults from `configs/domains/tile/base.yaml`.
2. Tile-domain defaults for this task use non-grid backgrounds only; graph-paper or external grid backgrounds are not allowed.
3. Obstacles are rendered as black tiles, the start tile is green, marked targets are red, and other open tiles use a neutral light fill.
4. Row labels are rendered on the left gutter and column labels are rendered on the top gutter.
5. Canvas size is derived from the sampled board geometry rather than fixed globally.
6. Post-image noise defaults are disabled (`apply_prob = 0.0`).
7. Applied background/noise metadata is emitted in trace.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Boards that cannot realize the selected reachable-target answer are rejected/resampled.
3. Answers and coordinate evidence come from the same sampled blocked-grid state.
4. No semantic auto-relaxation.
