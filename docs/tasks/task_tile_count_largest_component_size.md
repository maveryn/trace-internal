# `task_tile_count_largest_component_size`

## 1) Identity
1. Domain: `tile`
2. Task group: `count`
3. Task id: `task_tile_count_largest_component_size`
4. Objective: return the size of the unique largest 4-neighbor connected component formed by a queried color, with coordinate-grounded evidence for that winning component only.

## 2) Scene + task contract
1. Supported `task_variant` values: `largest_component_size`
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `grid_point_set`
4. Scene geometry:
   - exactly one dense `rows x cols` board,
   - `tiling_type="rectangular_tiling"`,
   - canonical tile coordinates are zero-based `(row, col)` with top-left origin.
5. Generation guarantees:
   - sampled named-color palette size is in the configured range,
   - every sampled palette color appears at least once on the board,
   - the queried color always has at least `2` connected components,
   - the queried color's largest component is unique,
   - each instance samples a target largest-component size uniformly from the configured range,
   - by default, the task uses `2..10`, capped by the resolved board/palette capacity when a smaller explicit board makes `10` impossible,
   - boards are rejected unless at least one sampled palette color realizes that target under the uniqueness rule,
   - the queried color is then sampled uniformly from the colors that realize the target answer on the accepted board.
6. Connectivity rule:
   - component counting uses 4-neighbor adjacency only (`up`, `down`, `left`, `right`),
   - diagonal touching does not merge components.

## 3) Prompt contract
1. Bundle: `tile_count_v1`
2. `task_family_key`: `rectangular_tile_board`
3. `task_key`: `largest_component_size_query`
4. Required slots:
   - task-family: `rows`, `cols`
   - task: `query_color`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Slot source:
   - shared JSON-format contracts from `configs/domains/tile/base.yaml` (`prompt.shared`),
   - task-group prompt slots from `configs/domains/tile/count.yaml`.
6. Modes: `answer_only`, `answer_and_evidence`
7. Variant policy: exactly 5 prompt variants for each required task-family/task/mode key.
8. `query_color` is passed to the prompt as `<color_name> [#RRGGBB]`.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the row-major sorted list of only the winning largest-component tile coordinates: `[[row, col], ...]`.
2. `witness_symbolic` stores the winning stable tile ids (`cell_{row}_{col}`) as an `id_set`.
3. `projected_evidence` includes:
   - `grid_point_set`
   - `pixel_point_set`
   - `bbox_set`
4. `execution_trace.components` stores all query-color connected components as trace-only structure:
   - component index,
   - row-major tile coordinates,
   - matching stable tile ids,
   - component size,
   - whether that component is the winning largest component.
5. `scene_ir.entities` annotate each matched tile with `query_component_index` and `is_largest_component`.
6. `execution_trace` also records:
   - `query_selection_strategy`,
   - `target_largest_component_size`,
   - `target_largest_component_size_range`,
   - `available_largest_component_sizes`,
   - `component_counts_by_color_name`,
   - `largest_component_index`.

## 5) Visual policy
1. Background and post-image noise use the merged tile-domain visual defaults from `configs/domains/tile/base.yaml`.
2. Tile-domain defaults for this task use non-grid backgrounds only; graph-paper or external grid backgrounds are not allowed.
3. Row labels are rendered on the left gutter and column labels are rendered on the top gutter.
4. Canvas size is derived from the sampled board geometry rather than fixed globally.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and winning-component evidence come from the same sampled board state.
3. Non-unique largest components for the queried color are rejected instead of tie-broken.
4. No semantic auto-relaxation.
