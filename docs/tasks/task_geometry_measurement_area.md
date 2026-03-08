# `task_geometry_measurement_area`

## 1) Identity
1. Domain: `geometry`
2. Task group: `measurement`
3. Task id: `task_geometry_measurement_area`
4. Objective: measure single-shape area from one graph-paper scene.

## 2) Scene + query contract
1. Entities/relations: exactly one target shape.
   - Polygon variants: triangle/quadrilateral.
   - Conic variant: axis-aligned ellipse with integer center + integer semiaxes.
2. Supported `query_type` values: `measure`.
3. `answer_gt.type`:
   - polygons: `integer` (square units),
   - ellipse: `pi_expression` (`kπ`).
4. Default `evidence_gt.type`: `grid_point_map`.
5. Evidence value semantics:
   - polygons: labeled vertex map in graph units,
   - ellipse: labeled 3-point map (`center`, `axis-x endpoint`, `axis-y endpoint`) in graph units.
6. Alternate evidence forms: projected `point_map` + `grid_point_map` and derived set/path projections in trace.
7. Overlap/touch policy: single object only.

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_measurement_v1`
2. `task_type_key`: `measurement_single_object`
3. Query-type mapping: `measure -> shape-specific area question`.
4. Required slots:
   - shared: `object_description`, `question_text`,
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`,
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`.
5. Slot source:
   - shared JSON-format contracts from `configs/domains/geometry/base.yaml` (`prompt.shared`),
   - measurement-family prompt slots from `configs/domains/geometry/measurement.yaml` (`prompt.shared`),
   - shape-specific question/example slots from `prompt.task_overrides.task_geometry_measurement_area` (`question_text_polygon`, `question_text_ellipse`, and polygon side-count matched `json_example_triangle|quadrilateral`).
6. Answer-only JSON shape: `{"answer":<value>}` where `<value>` is integer or `kπ` per variant.
7. Variant counts (task/query/mode): minimum 10 templates per required key.
8. Output modes:
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
8. Answer bounds: area target scalar `k` is constrained to `[8, 32]` by task-group config (`integer` for polygons, `kπ` coefficient for ellipse).
9. Default variant sampling weights: triangle/quadrilateral/ellipse = 1:1:1.

## 5) Complexity + tests
1. Complexity definition/components: shape variant + area magnitude.
2. Determinism test: `tests/test_geometry_measurement_contracts.py`.
3. Answer/evidence consistency test: `tests/test_geometry_measurement_tasks.py`.
4. Prompt metadata/placeholder test: `tests/test_prompt_system.py`.
5. Constraint-specific tests: polygon vertex projection, conic center projection, and answer-vs-scene attr equality.
