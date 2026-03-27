# `task_tile_graph_degree_count`

## 1) Identity
1. Domain: `tile`
2. Task group: `graph`
3. Task id: `task_tile_graph_degree_count`
4. Objective: return the number of queried-color tiles whose same-color orthogonal-neighbor count equals one requested integer degree.

## 2) Scene + task contract
1. Supported `task_variant` values: `degree_count`
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `grid_point_set`
4. Scene geometry:
   - exactly one dense `rows x cols` board,
   - `tiling_type="rectangular_tiling"`,
   - canonical tile coordinates are zero-based `(row, col)` with top-left origin.
5. Generation guarantees:
   - exactly one queried named color per instance,
   - same-color degree uses 4-neighbor orthogonal adjacency only,
   - sampled boards are rejected unless they realize one exact `(degree, answer_count)` target pair,
   - prompt-facing evidence is the full row-major set of tiles matching both the queried color and the requested same-color degree.

## 3) Prompt contract
1. Bundle: `tile_graph_v1`
2. `task_family_key`: `rectangular_tile_board`
3. `task_key`: `degree_count_query`
4. Required slots:
   - task-family: `rows`, `cols`
   - task: `query_color`, `neighbor_degree`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Slot source:
   - shared JSON-format contracts from `configs/domains/tile/base.yaml` (`prompt.shared`),
   - task-group prompt slots from `configs/domains/tile/graph.yaml`.
6. Modes: `answer_only`, `answer_and_evidence`
7. Variant policy: exactly 5 prompt variants for each required task-family/task/mode key.
8. Prompt-facing named colors include canonical hex labels in brackets.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the row-major sorted list of all matching tile coordinates: `[[row, col], ...]`.
2. `witness_symbolic` stores the matching stable tile ids as an `id_set`.
3. `projected_evidence` includes:
   - `grid_point_set`
   - `pixel_point_set`
   - `bbox_set`
4. `execution_trace` records:
   - target degree and target answer-count ranges,
   - all queried-color coordinates,
   - the matching coordinates/ids,
   - per-color same-color degree histograms,
   - per-cell same-color degree values keyed by `cell_{row}_{col}`.

## 5) Visual policy
1. Background and post-image noise use the merged tile-domain visual defaults from `configs/domains/tile/base.yaml`.
2. Tile-domain defaults for this task use non-grid backgrounds only; graph-paper or external grid backgrounds are not allowed.
3. Query colors come from the shared named-color palette and use prompt labels with hex suffixes.
4. Row labels are rendered on the left gutter and column labels are rendered on the top gutter.
5. Canvas size is derived from the sampled board geometry rather than fixed globally.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and coordinate evidence come from the same sampled named-color board and the same-color degree computation on that board.
3. No semantic auto-relaxation.
