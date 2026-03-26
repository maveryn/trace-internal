# `task_tile_topology_hole_count`

## 1) Identity
1. Domain: `tile`
2. Task group: `topology`
3. Task id: `task_tile_topology_hole_count`
4. Objective: return the number of enclosed white holes formed by black wall tiles on one labeled rectangular board.

## 2) Scene + task contract
1. Supported `task_variant` values: `hole_count`
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `grid_point_set`
4. Scene geometry:
   - exactly one dense `rows x cols` board,
   - `tiling_type="rectangular_tiling"`,
   - canonical tile coordinates are zero-based `(row, col)` with top-left origin.
5. Generation guarantees:
   - the outer board boundary is white and forms exactly one exterior white component,
   - black cells form exactly one connected wall component,
   - each counted hole is a 4-neighbor white region with area at least `1`,
   - counted holes never touch the board boundary,
   - sampled boards are constructed to match an exact target answer over the configured `answer_min..answer_max` range whenever the allowed board bounds can realize it.

## 3) Prompt contract
1. Bundle: `tile_topology_v1`
2. `task_family_key`: `rectangular_tile_board`
3. `task_key`: `hole_count_query`
4. Required slots:
   - task-family: `rows`, `cols`
   - task: `wall_color`, `hole_color`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Slot source:
   - shared JSON-format contracts from `configs/domains/tile/base.yaml` (`prompt.shared`),
   - task-group prompt slots from `configs/domains/tile/topology.yaml`.
6. Modes: `answer_only`, `answer_and_evidence`
7. Variant policy: exactly 5 prompt variants for each required task-family/task/mode key.
8. Prompt-facing named colors include canonical hex labels in brackets.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the row-major sorted list of one canonical witness coordinate per hole: `[[row, col], ...]`.
2. Each witness coordinate is the row-major minimum coordinate inside one enclosed white hole.
3. `witness_symbolic` stores the witness tile ids as an `id_set`.
4. `projected_evidence` includes:
   - `grid_point_set`
   - `pixel_point_set`
   - `bbox_set`
5. `execution_trace` records:
   - target hole-count range and selected target,
   - full enclosed hole cell sets and per-hole witness coordinates,
   - exterior white component cells,
   - full black wall cell set,
   - white/black component counts.

## 5) Visual policy
1. Background and post-image noise use the merged tile-domain visual defaults from `configs/domains/tile/base.yaml`.
2. Tile-domain defaults for this task use non-grid backgrounds only; graph-paper or external grid backgrounds are not allowed.
3. White tiles use the reserved `white [#FFFFFF]` role for background and holes, and black tiles use the reserved `black [#000000]` role for walls.
4. Row labels are rendered on the left gutter and column labels are rendered on the top gutter.
5. Canvas size is derived from the sampled board geometry rather than fixed globally.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and hole-witness evidence come from the same sampled black/white topology.
3. No semantic auto-relaxation.
