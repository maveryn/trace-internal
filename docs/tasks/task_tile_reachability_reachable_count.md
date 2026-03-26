# `task_tile_reachability_reachable_count`

## 1) Identity
1. Domain: `tile`
2. Task group: `reachability`
3. Task id: `task_tile_reachability_reachable_count`
4. Objective: return the number of board tiles reachable from one marked start tile under 4-neighbor movement through non-obstacle cells.

## 2) Scene + task contract
1. Supported `task_variant` values: `reachable_count`
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `grid_point_set`
4. Scene geometry:
   - exactly one dense `rows x cols` board,
   - `tiling_type="rectangular_tiling"`,
   - canonical tile coordinates are zero-based `(row, col)` with top-left origin.
5. Generation guarantees:
   - exactly one start tile,
   - obstacle tiles are blocked and use the reserved black role,
   - reachable count is computed symbolically with 4-neighbor BFS over non-obstacle cells,
   - sampled boards are rejected unless reachable fraction is within configured bounds,
   - sampled boards are rejected when reachable count exceeds configured `answer_max`,
   - the start-tile color is sampled from the shared 10-color named palette.

## 3) Prompt contract
1. Bundle: `tile_reachability_v1`
2. `task_family_key`: `rectangular_tile_board`
3. `task_key`: `reachable_count_query`
4. Required slots:
   - task-family: `rows`, `cols`
   - task: `obstacle_color`, `start_color`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Slot source:
   - shared JSON-format contracts from `configs/domains/tile/base.yaml` (`prompt.shared`),
   - task-group prompt slots from `configs/domains/tile/reachability.yaml`.
6. Modes: `answer_only`, `answer_and_evidence`
7. Variant policy: exactly 5 prompt variants for each required task-family/task/mode key.
8. Prompt-facing named colors include canonical hex labels in brackets.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the row-major sorted list of all reachable tile coordinates, including the start tile: `[[row, col], ...]`.
2. `witness_symbolic` stores the reachable stable tile ids (`cell_{row}_{col}`) as an `id_set`.
3. `projected_evidence` includes:
   - `grid_point_set`
   - `pixel_point_set`
   - `bbox_set`
4. `scene_ir.relations.adjacency_open` stores the open-cell 4-neighbor relation keyed by stable tile ids.
5. `execution_trace` records:
   - configured `answer_max`,
   - start color name/rgb/label,
   - start coordinate/id,
   - blocked coordinates/ids,
   - reachable coordinates/ids,
   - realized obstacle/reachable fractions.

## 5) Visual policy
1. Background and post-image noise use the merged tile-domain visual defaults from `configs/domains/tile/base.yaml`.
2. Tile-domain defaults for this task use non-grid backgrounds only; graph-paper or external grid backgrounds are not allowed.
3. Obstacles are rendered as black tiles, the start tile uses one sampled color from the shared 10-color named palette, and other open tiles use a neutral light fill.
4. Row labels are rendered on the left gutter and column labels are rendered on the top gutter.
5. Canvas size is derived from the sampled board geometry rather than fixed globally.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and reachable-set evidence come from the same sampled blocked-grid state.
3. No semantic auto-relaxation.
