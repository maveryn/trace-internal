# `task_tile_transition_gravity_max_drop`

## 1) Identity
1. Domain: `tile`
2. Task group: `transition`
3. Task id: `task_tile_transition_gravity_max_drop`
4. Objective: return the unique maximum downward drop distance when one colored tile in each column falls straight down under gravity.

## 2) Scene + task contract
1. Supported `task_variant` values: `gravity_max_drop`
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `grid_point_path`
4. Scene geometry:
   - exactly one dense `rows x cols` board,
   - `tiling_type="rectangular_tiling"`,
   - canonical tile coordinates are zero-based `(row, col)` with top-left origin.
5. Scene roles:
   - one `drop_color` tile appears in each column,
   - black tiles are fixed bottom-contiguous obstacles,
   - white tiles are empty traversable board cells.
6. Transition rule:
   - every drop tile falls straight downward within its own column,
   - falling stops at the cell directly above the bottom-most obstacle stack in that column, or at the bottom edge if the column has no obstacles,
   - drop distance is measured in tile rows moved downward.
7. Generation guarantees:
   - each instance samples a target answer uniformly from `[1, rows_max - 2]` under the shared `3..7` board policy,
   - smaller explicit row bounds cap that target range automatically,
   - the board shape is chosen only from shapes that can realize the target,
   - exactly one column attains the target max-drop answer,
   - all other columns have strictly smaller drop distances.

## 3) Prompt contract
1. Bundle: `tile_transition_v1`
2. `task_family_key`: `rectangular_tile_board`
3. `task_key`: `gravity_max_drop_query`
4. Required slots:
   - task-family: `rows`, `cols`
   - task: `drop_color`, `obstacle_color`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Slot source:
   - shared JSON-format contracts from `configs/domains/tile/base.yaml` (`prompt.shared`),
   - task-group prompt slots from `configs/domains/tile/transition.yaml`.
6. Modes: `answer_only`, `answer_and_evidence`
7. Variant policy: exactly 5 prompt variants for each required task-family/task/mode key.
8. Prompt text names both the moving tile color and the obstacle color as `name [#RRGGBB]`.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the ordered winning drop trajectory as `[[row, col], ...]`, including both the source and final cells.
2. `witness_symbolic` stores that trajectory as an `id_path`.
3. `projected_evidence` includes:
   - `grid_point_path`
   - `pixel_point_path`
   - `bbox_set`
4. `scene_ir.entities` annotate cells with:
   - `role` (`drop_tile`, `obstacle`, `empty`)
   - `is_winning_path`
   - `is_winning_source`
5. `execution_trace` records:
   - the sampled target-answer range and realized target,
   - `winner_col`,
   - winner start/final coords and winner path,
   - obstacle heights by column,
   - all source cells, final cells, and drop distances,
   - `unique_max = true`.

## 5) Visual policy
1. Background and post-image noise use the merged tile-domain visual defaults from `configs/domains/tile/base.yaml`.
2. Tile-domain defaults for this task use non-grid backgrounds only; graph-paper or external grid backgrounds are not allowed.
3. Row labels are rendered on the left gutter and column labels are rendered on the top gutter.
4. Canvas size is derived from the sampled board geometry rather than fixed globally.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and winner-trajectory evidence come from the same constructed board state.
3. The winning column is unique by construction; ties are rejected at construction time rather than broken afterward.
4. No semantic auto-relaxation.
