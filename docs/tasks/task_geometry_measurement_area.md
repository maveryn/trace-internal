# `task_geometry_measurement_area`

## 1) Identity
1. Domain: `geometry`
2. Task group: `measurement`
3. Task id: `task_geometry_measurement_area`
4. Objective: measure single-shape area from one graph-paper scene.

## 2) Scene + task contract
1. Entities/relations: exactly one target shape.
   - Polygon variants: triangle/quadrilateral.
   - Conic variant: axis-aligned ellipse with integer center + integer semiaxes.
2. Supported `task_variant` values: `triangle`, `quadrilateral`, `ellipse`.
3. `answer_gt.type`:
   - polygons: `integer` (square units),
   - ellipse: `pi_expression` (`kπ`).
4. `evidence_gt.type`:
   - polygon variants: `graph_point_set`,
   - ellipse variant: `graph_point`.
5. Evidence value semantics:
   - polygons: unlabeled graph-paper vertex set in graph units,
   - ellipse: one graph-paper center point `[x, y]`.
6. Alternate evidence forms: projected `pixel_point_map` + `grid_point_map` and derived pixel/grid set/path projections in trace.
7. Polygon variants reject adjacent collinear vertices, so sampled triangles/quadrilaterals remain visually non-degenerate.
8. The rendered image does not place vertex/reference labels on the shape; evidence is coordinate-only.
9. Overlap/touch policy: single object only.

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_measurement_v1`
2. `task_family_key`: `measurement_single_object`
3. `task_key`: `measurement_query`
4. Task-variant mapping: slot-driven `question_text`, `evidence_hint`, and `json_example` values depend on the sampled shape variant.
5. Required slots:
   - shared: `object_description`, `question_text`,
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`,
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`.
6. Slot source:
   - shared JSON-format contracts from `configs/domains/geometry/base.yaml` (`prompt.shared`),
   - measurement-family prompt slots from `configs/domains/geometry/measurement.yaml` (`prompt.shared`),
   - shape-specific question/evidence/example slots from `prompt.task_overrides.task_geometry_measurement_area` (`question_text_polygon`, `question_text_ellipse`, `evidence_hint_polygon`, `evidence_hint_ellipse`, and polygon side-count matched `json_example_triangle|quadrilateral`).
7. Answer-only JSON shape: `{"answer":<value>}` where `<value>` is integer or `kπ` per variant.
8. Variant counts (task-family/task/mode): exactly 5 templates per required key.
9. Output modes:
   - `answer_only`
   - `answer_and_evidence`

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: single target shape only.
3. Reject/resample conditions: no feasible sampled shape for requested variant/bounds, or off-canvas placement under current scene constraints.
4. No-auto-relaxation guarantee: generation fails on unmet constraints.
5. Structural diversity policy: polygons are procedurally sampled per instance (not from a tiny fixed template bank) to reduce cross-seed visual similarity.
6. Graph-paper reference cues: center-origin marker includes axis arrows plus signed integer scale labels across the full visible axis range (no origin text label).
7. Graph-paper color variation: minor/major/axis colors are sampled from constrained ranges per instance, with axis lines always darker than grid lines.
8. Answer bounds: area target scalar `k` is constrained to `[8, 96]` by task-group config (`integer` for polygons, `kπ` coefficient for ellipse).
9. Default variant sampling weights: triangle/quadrilateral/ellipse = 1:1:1.
10. Triangle sampling policy:
   - triangle area targets are sampled from exact feasible support before scene placement.
   - triangles are then constructed from integer-edge lattice specs that realize the selected area, avoiding collapse to a tiny answer set under generic polygon rejection.
11. Quadrilateral sampling policy:
   - quadrilateral area targets are sampled from exact feasible support before scene placement.
   - selected targets are realized by a constructive integer-edge quadrilateral catalog (rectangles + parallelograms), so answer balancing improves without breaking the shared polygon perimeter contract.

## 5) Complexity + tests
1. Complexity definition/components: shape variant + area magnitude.
2. Determinism test: `tests/test_geometry_measurement_contracts.py`.
3. Answer/evidence consistency test: `tests/test_geometry_measurement_tasks.py`.
4. Prompt metadata/placeholder test: `tests/test_prompt_system.py`.
5. Constraint-specific tests: polygon vertex projection, conic center projection, and answer-vs-scene attr equality.
