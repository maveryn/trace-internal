# `geometry_angle_value_query`

## 1) Identity
1. Domain: `geometry`
2. Task group: `measurement`
3. Task id: `geometry_angle_value_query`
4. Objective: answer an angle-value query and return grounded vertex evidence.

## 2) Scene + query contract
1. Query types:
   - `min`, `max`, `median`, `closest_to_x`, `smallest_above_x`, `largest_below_x`, `difference_max_min`
2. `answer_gt.type`: `integer`
3. Default evidence:
   - `grid_point_set` (single-target queries)
   - `grid_point_path` (`difference_max_min`)
4. Trace also stores pixel projections (`point_set`, `point_path`).
5. Candidate count is sampled from `3..7` (odd-only for `median`).
6. Layout policy: non-overlap/touch with minimum one graph-square clearance.

## 3) Prompt contract
1. Bundle: `geometry_measurement_v1`
2. Task type key: `measurement_value_query`
3. Modes: `answer_only`, `answer_and_evidence`
4. Required slots include:
   - `candidate_count`, `entity_plural`, `value_name_singular`, `unit_name`,
   - `evidence_hint`,
   - `target_x` (threshold/closest queries)
5. Variant policy: at least 10 templates per required task/query/mode key.

## 4) Determinism + constraints
1. Deterministic generation from `instance_seed`.
2. Answer target sampled uniformly over feasible answers for selected `query_type`.
3. Distractors may duplicate, but final selected answer witness is unique.
4. One ray per angle is axis-aligned (horizontal/vertical).
5. No semantic auto-relaxation; invalid layouts/queries are rejected and resampled.

## 5) Visual policy
1. Graph-paper background is enforced.
2. Vertices snap to graph intersections.
3. Canvas size sampled from `[512, 1024]`; graph cells sampled from `[12, 24]`.
4. Center axes + origin marker are rendered and frame metadata is stored in trace.
5. Post-image noise default apply probability: `0.5`.
