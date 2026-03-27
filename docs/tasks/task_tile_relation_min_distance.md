# `task_tile_relation_min_distance`

## 1) Identity
1. Domain: `tile`
2. Task group: `relation`
3. Task id: `task_tile_relation_min_distance`
4. Objective: return the minimum orthogonal step distance between two connected colored regions, with a unique shortest-path witness between the unique closest pair.

## 2) Scene + task contract
1. Supported `task_variant` values: `min_distance`
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `grid_point_path`
4. Scene geometry:
   - exactly one dense `rows x cols` board,
   - `tiling_type="rectangular_tiling"`,
   - canonical tile coordinates are zero-based `(row, col)` with top-left origin.
5. Generation guarantees:
   - the board contains exactly one connected component of `color_a` and one connected component of `color_b`,
   - all other tiles use the reserved white background role,
   - the queried colors have one unique closest cell pair,
   - the closest pair is aligned on one row or one column, so the shortest-path evidence is a unique straight path,
   - target answers are sampled uniformly from the configured distance range and capped by `max(rows_max, cols_max) - 1`.

## 3) Prompt contract
1. Bundle: `tile_relation_v1`
2. `task_family_key`: `rectangular_tile_board`
3. `task_key`: `min_distance_query`
4. Required slots:
   - task-family: `rows`, `cols`
   - task: `background_color`, `color_a`, `color_b`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Slot source:
   - shared JSON-format contracts from `configs/domains/tile/base.yaml` (`prompt.shared`),
   - task-group prompt slots from `configs/domains/tile/relation.yaml`.
6. Modes: `answer_only`, `answer_and_evidence`
7. Variant policy: exactly 5 prompt variants for each required task-family/task/mode key.
8. Prompt-facing named colors include canonical hex labels in brackets.

## 4) Evidence + trace contract
1. Prompt-facing evidence is one ordered `grid_point_path` from the closest `color_a` tile to the closest `color_b` tile, including both endpoints.
2. `witness_symbolic` stores that witness as an `id_path`.
3. `projected_evidence` includes:
   - `grid_point_path`
   - `pixel_point_path`
   - `bbox_set`
4. `scene_ir.relations.adjacency_open` stores the full open-grid 4-neighbor relation keyed by stable tile ids.
5. `execution_trace` records:
   - target-distance range and chosen target,
   - distance axis (`horizontal` or `vertical`),
   - background/query-color labels and RGB values,
   - both connected components and their stable ids,
   - the unique closest pair and shortest-path witness.

## 5) Visual policy
1. Background and post-image noise use the merged tile-domain visual defaults from `configs/domains/tile/base.yaml`.
2. Tile-domain defaults for this task use non-grid backgrounds only; graph-paper or external grid backgrounds are not allowed.
3. Row labels are rendered on the left gutter and column labels are rendered on the top gutter.
4. Canvas size is derived from the sampled board geometry rather than fixed globally.
5. This task uses the standard rectangular-cell tile sampler rather than forcing square tiles.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and path evidence come from the same constructed closest-pair relation.
3. The generator fails fast if the constructed components would introduce a second equal-distance pair.
4. No semantic auto-relaxation.
