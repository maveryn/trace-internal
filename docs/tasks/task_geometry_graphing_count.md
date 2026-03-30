# `task_geometry_graphing_count`

## 1) Identity
1. Domain: `geometry`
2. Task group: `graphing`
3. Task id: `task_geometry_graphing_count`
4. Objective: reason over one plotted simple function on graph paper and count visible x-axis or dashed-line meeting points (including tangencies), or count visible turning/extremum points.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `quadratic`
   - `absolute_value`
   - `cubic`
   - `sinusoid`
   - `piecewise_linear`
2. Supported `query_variant` values:
   - `x_intercept_count`
   - `horizontal_line_intersection_count`
   - `turning_point_count`
   - `local_minima_count`
   - `local_maxima_count`
3. Compatibility:
   - `quadratic` supports `x_intercept_count|horizontal_line_intersection_count`
   - `absolute_value` supports `x_intercept_count|horizontal_line_intersection_count`
   - `cubic` supports `x_intercept_count|horizontal_line_intersection_count`
   - `sinusoid` supports `x_intercept_count|horizontal_line_intersection_count|turning_point_count|local_minima_count|local_maxima_count`
   - `piecewise_linear` supports `x_intercept_count|horizontal_line_intersection_count|turning_point_count|local_minima_count|local_maxima_count`
4. Every scene uses one centered fixed `20 x 20` graph-paper window with the plotted graph as the main object; horizontal-line queries also include one dashed guide line `y = c`.
5. `answer_gt.type` is `integer` for every variant.
6. `evidence_gt.type` is `graph_point_set` for every variant.

## 3) Prompt contract
1. Bundle: `geometry_graphing_v1`
2. The family stem introduces one graph-paper plot with family-neutral wording; the prompt does not need to name the underlying function family.
3. `task_variant` carries the question wording:
   - `x_intercept_count` asks how many visible points the graph meets the x-axis at, including tangencies where the graph only touches the axis,
   - `horizontal_line_intersection_count` asks how many visible points the graph meets the dashed horizontal line `y = c` at, including tangencies where the graph only touches the line,
   - `turning_point_count` asks how many turning points are visible in the graph window, including the valid zero-turning-point case for straight piecewise segments,
   - `local_minima_count` asks how many local minima are visible in the graph window,
   - `local_maxima_count` asks how many local maxima are visible in the graph window.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the unordered `graph_point_set` of every graph-paper coordinate `[x, y]` satisfying the question.
2. The answer is always `len(evidence_gt.value)`.
3. Zero-count cases keep the same `graph_point_set` contract and use `[]` evidence.
4. `projected_evidence` preserves pixel-space projections for every witness point.
5. `scene_ir.relations`, `query_spec.params`, and `execution_trace` record:
   - `scene_variant`
   - `query_variant`
   - `target_count`
   - the sampled function parameters or piecewise vertices
   - the evidence-point graph coordinates
   - `query_line_y` when a dashed guide line is present

## 5) Determinism + constraints
1. Deterministic generation from `instance_seed`.
2. `quadratic` and `absolute_value` scenes are sampled so all counted witness points land on integer graph-paper coordinates.
3. `cubic` scenes use factored integer-root forms, so x-axis or dashed-line witnesses land on integer graph-paper coordinates.
4. `sinusoid` scenes use constrained period/phase choices so counted intersections and extrema land on integer graph-paper coordinates.
5. `piecewise_linear` scenes place the counted intersections or turning points on lattice vertices, so the prompt-facing `graph_point_set` evidence stays exact.
6. Dashed horizontal-line queries never use `y = 0`; the x-axis remains visually distinct from the query line.
7. `turning_point_count`, `local_minima_count`, and `local_maxima_count` are only asked on `piecewise_linear|sinusoid` scenes, where the visible extrema are unambiguous and every witness remains a graph-paper coordinate.

## 6) Complexity + tests
1. Complexity uses:
   - `visual_scan`
   - `graphing_reasoning`
   - `ambiguity`
   - `output_burden`
2. Behavior tests: `tests/test_geometry_consolidated_tasks.py`
3. Contract/config tests:
   - `tests/test_geometry_graphing_count_contracts.py`
   - `tests/test_geometry_graphing_task_group_config.py`
