# `task_tile_symmetry_violation_count`

## 1) Identity
1. Domain: `tile`
2. Task group: `symmetry`
3. Task id: `task_tile_symmetry_violation_count`
4. Objective: return the number of counted-side tiles that violate a mirror-symmetry constraint.

## 2) Scene + task contract
1. Supported `task_variant` values: `vertical`, `horizontal`
2. `answer_gt.type`: `integer`
3. `evidence_gt.type`: `grid_point_set`
4. Scene geometry:
   - exactly one dense `rows x cols` board,
   - `tiling_type="rectangular_tiling"`,
   - canonical tile coordinates are zero-based `(row, col)` with top-left origin.
5. Generation guarantees:
   - one task variant is chosen deterministically (`vertical` or `horizontal`) unless explicitly overridden,
   - each instance samples a target violation count uniformly from `1..10`,
   - board shape is then sampled only from shapes that can support that target under the selected mirror axis,
   - the board is constructed from an exact mirror-symmetric template plus exactly `target_violation_count` counted-side color mismatches.
6. Counting rule:
   - vertical variant counts only violating tiles on the right side,
   - horizontal variant counts only violating tiles on the bottom side,
   - centerline tiles mirror to themselves and are never counted as violations.

## 3) Prompt contract
1. Bundle: `tile_symmetry_v1`
2. `task_family_key`: `rectangular_tile_board`
3. `task_key`: `symmetry_violation_count_query`
4. Required slots:
   - task-family: `rows`, `cols`
   - task: `mirror_axis`, `counted_side`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Slot source:
   - shared JSON-format contracts from `configs/domains/tile/base.yaml` (`prompt.shared`),
   - task-group prompt slots from `configs/domains/tile/symmetry.yaml`.
6. Modes: `answer_only`, `answer_and_evidence`
7. Variant policy: exactly 5 prompt variants for each required task-family/task/mode key.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the row-major sorted list of all violating counted-side tile coordinates: `[[row, col], ...]`.
2. `witness_symbolic` stores the violating stable tile ids (`cell_{row}_{col}`) as an `id_set`.
3. `projected_evidence` includes:
   - `grid_point_set`
   - `pixel_point_set`
   - `bbox_set`
4. `scene_ir.relations.mirror_partner` stores the deterministic mirror partner for each tile id.
5. `execution_trace` records:
   - `mirror_axis` and `counted_side`,
   - target violation count and target range,
   - board capacity under the chosen mirror axis,
   - counted-side coordinates/ids,
   - violation coordinates/ids,
   - per-pair mirror metadata and centerline coordinates.

## 5) Visual policy
1. Background and post-image noise use the merged tile-domain visual defaults from `configs/domains/tile/base.yaml`.
2. Tile-domain defaults for this task use non-grid backgrounds only; graph-paper or external grid backgrounds are not allowed.
3. Row labels are rendered on the left gutter and column labels are rendered on the top gutter.
4. Canvas size is derived from the sampled board geometry rather than fixed globally.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and violation evidence come from the same constructed board state.
3. No semantic auto-relaxation.
