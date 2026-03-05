# `tile_shortest_path`

## 1) Identity
1. Domain: `tile`
2. Task group: `path`
3. Task id: `tile_shortest_path`
4. Objective: return shortest-path length with grounded path evidence.

## 2) Scene + query contract
1. Query type: `shortest_path`
2. `answer_gt.type`: `integer`
3. Default evidence type: `point_path`
4. Alternate evidence type: `bbox_set`
5. Generation guarantees:
   - start and goal are distinct open cells,
   - maze has exactly one shortest path.

## 3) Prompt contract
1. Bundle: `tile_path_v1`
2. Task type key: `maze_path`
3. Required slots: `rows`, `cols`, `evidence_hint`
4. Modes: `answer_only`, `answer_and_evidence`
5. Variant policy: at least 10 variants for each required task/query/mode key.

## 4) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Non-unique or invalid mazes are rejected/resampled.
3. No semantic auto-relaxation.

## 5) Visual policy
1. Background defaults come from `configs/domains/tile/path.yaml`.
2. Post-image noise defaults are disabled (`apply_prob = 0.0`).
3. Applied background/noise metadata is emitted in trace.
