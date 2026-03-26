# `task_tile_pattern_match3_run_count`

## 1) Identity
1. Domain: `tile`
2. Task group: `pattern`
3. Task id: `task_tile_pattern_match3_run_count`
4. Objective: return how many rows or columns contain at least one run of 3 or more consecutive tiles of a queried color, with one canonical witness run per counted line.

## 2) Scene + task contract
1. Supported `task_variant` values: `rows`, `cols`
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `grid_point_set`
4. Scene geometry:
   - exactly one dense `rows x cols` board,
   - `tiling_type="rectangular_tiling"`,
   - canonical tile coordinates are zero-based `(row, col)` with top-left origin.
5. Generation guarantees:
   - the task samples a specific query color from the board palette and includes it in the prompt as `name [#RRGGBB]`,
   - `run_length` is fixed to `3` in the active config,
   - one task variant is chosen deterministically (`rows` or `cols`) unless explicitly overridden,
   - each instance samples a target qualifying-line count uniformly from `[1, rows_max]` for the row variant or `[1, cols_max]` for the column variant,
   - the board shape is then chosen only from shapes that can support that target while leaving at least some non-query tiles on the board,
   - the board is constructed to realize that exact target count.
6. Counting rule:
   - a row or column counts once if it contains at least one contiguous query-color run of length `3` or greater,
   - longer runs still count once,
   - multiple qualifying runs on the same row or column still count once.

## 3) Prompt contract
1. Bundle: `tile_pattern_v1`
2. `task_family_key`: `rectangular_tile_board`
3. `task_key`: `match3_run_count_query`
4. Required slots:
   - task-family: `rows`, `cols`
   - task: `line_axis`, `run_length`, `query_color`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Slot source:
   - shared JSON-format contracts from `configs/domains/tile/base.yaml` (`prompt.shared`),
   - task-group prompt slots from `configs/domains/tile/pattern.yaml`.
6. Modes: `answer_only`, `answer_and_evidence`
7. Variant policy: exactly 5 prompt variants for each required task-family/task/mode key.
8. Prompt examples are variant-aware:
   - row variant uses a row-based witness example,
   - column variant uses a column-based witness example.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the row-major sorted list of coordinates for one canonical 3-tile witness run from each counted line.
2. `witness_symbolic` stores the stable tile ids of those witness cells as an `id_set`.
3. `projected_evidence` includes:
   - `grid_point_set`
   - `pixel_point_set`
   - `bbox_set`
4. `execution_trace.qualifying_runs` stores grouped trace-only witness runs:
   - run index,
   - counted line index,
   - row/column coordinates,
   - stable tile ids.
5. `scene_ir.entities` annotate witness tiles with `canonical_run_index`, `qualifying_line_index`, and `is_canonical_run_evidence`.
6. `execution_trace` also records:
   - `line_axis`,
   - `run_length`,
   - `construction_strategy`,
   - `target_qualifying_line_count`,
   - `target_qualifying_line_count_range`,
   - `qualifying_line_indices`.

## 5) Visual policy
1. Background and post-image noise use the merged tile-domain visual defaults from `configs/domains/tile/base.yaml`.
2. Tile-domain defaults for this task use non-grid backgrounds only; graph-paper or external grid backgrounds are not allowed.
3. Row labels are rendered on the left gutter and column labels are rendered on the top gutter.
4. Canvas size is derived from the sampled board geometry rather than fixed globally.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and witness-run evidence come from the same constructed board state.
3. Longer runs are reduced to one canonical 3-cell witness run per counted line for prompt-facing evidence.
4. No semantic auto-relaxation.
