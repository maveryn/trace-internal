# `task_geometry_solid_view_count`

## 1) Identity
1. Domain: `geometry`
2. Task group: `solid`
3. Task id: `task_geometry_solid_view_count`
4. Objective: reason from a rendered 3D cube stack to one requested orthographic view and count how many unit cells should be filled in that query view.

## 2) Scene + task contract
1. Supported `scene_variant` values:
   - `cube_stack`
2. Supported `query_variant` values:
   - `top_view_visible_count`
   - `front_view_visible_count`
   - `right_view_visible_count`
3. The scene uses one two-panel scaffold:
   - left panel: one stacked-cube isometric drawing,
   - right panel: one empty orthographic query grid titled with the requested view.
4. The query grid is cropped to the occupied orthographic support for the requested view, so the right panel does not carry decorative empty rows or columns outside the true projection footprint.
5. View conventions:
   - `Front view` means looking straight at the left vertical face of the drawn stack.
   - `Right view` means looking straight at the right vertical face of the drawn stack.
6. `answer_gt.type` is `integer`.
7. `evidence_gt.type` is `bbox_set`.

## 3) Prompt contract
1. Bundle: `geometry_solid_v1`
2. Task-family stem introduces one cube stack on the left plus one empty query grid on the right.
3. `task_variant` carries the question wording:
   - `top_view_visible_count` asks how many unit squares should be filled in the Top view grid,
   - `front_view_visible_count` asks how many unit squares should be filled in the Front view grid and explicitly states that this means the left vertical face of the drawn stack,
   - `right_view_visible_count` asks how many unit squares should be filled in the Right view grid and explicitly states that this means the right vertical face of the drawn stack.

## 4) Evidence + trace contract
1. Prompt-facing evidence is the unordered `bbox_set` of every query-grid cell that should be filled for the requested orthographic view.
2. The answer is always `len(evidence_gt.value)`.
3. `projected_evidence` stores:
   - the query-panel bbox,
   - the query-grid bbox,
   - the query-grid dimensions,
   - the visible-cell `pixel_bbox_set`,
   - the symbolic projection-cell coordinates.
4. The query-grid dimensions and projection-cell coordinates are normalized to that tight occupied orthographic support.
5. `scene_ir.relations`, `query_spec.params`, and `execution_trace` record:
   - `scene_variant`
   - `query_variant`
   - `target_count`
   - the cube-stack footprint/heights
   - the visible counts for `top|front|right`
   - the projection-cell coordinates for the requested view

## 5) Determinism + constraints
1. Deterministic generation from `instance_seed`.
2. Cube stacks are sampled from connected footprint heights on a small integer footprint, then expanded into occupied cubes.
3. Generation enforces:
   - at least `2` occupied footprint cells,
   - stack max height at least `2`,
   - at least `2` distinct counts across the three view types,
   - exact realization of the sampled `target_count`,
   - the queried orthographic projection is not allowed to fill its entire cropped query grid by default.
4. The right query panel is intentionally blank apart from the grid/title; the solver must infer which cells would be occupied from the 3D stack.
5. The prompt-facing evidence stays on the visible query-grid cells rather than inventing synthetic labels for those cells.
6. Orthographic query panels should never reserve extra empty border columns or rows that come only from latent stack padding rather than the requested view itself.

## 6) Complexity + tests
1. Complexity uses:
   - `visual_scan`
   - `projection_reasoning`
   - `ambiguity`
   - `output_burden`
2. Behavior tests: `tests/test_geometry_consolidated_tasks.py`
3. Contract/config tests:
   - `tests/test_geometry_solid_view_count_contracts.py`
   - `tests/test_geometry_solid_view_task_group_config.py`
