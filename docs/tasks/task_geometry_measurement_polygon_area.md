# `task_geometry_measurement_polygon_area`

## 1) Identity
1. Domain: `geometry`
2. Task group: `measurement`
3. Task id: `task_geometry_measurement_polygon_area`
4. Objective: measure polygon area from a single polygon scene.

## 2) Scene + query contract
1. Entities/relations: one polygon entity (integer-grid template with transform), with `polygon_sides` sampled from `{3, 4, 5}`.
2. Supported `query_type` values: `measure`.
3. `answer_gt.type`: `integer` (square units).
4. Default `evidence_gt.type`: `grid_point_set`.
5. Alternate evidence forms: projected `point_set`/`point_path` and `grid_point_path` in trace.
6. Overlap/touch policy: single object only.

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_measurement_v2`
2. `task_type_key`: `measurement_single_object`
3. Query-type mapping: `measure -> polygon area question`.
4. Required slots: `object_description`, `question_text`; and for answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`.
5. Static prompt slot source: `question_text` is provided by `configs/domains/geometry/measurement.yaml` (`prompt.task_overrides.task_geometry_measurement_polygon_area.question_text`).
6. Variant counts (task/query/mode): minimum 10 templates per required key.
7. Output modes:
   - `answer_only`
   - `answer_and_evidence`

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: single target polygon only.
3. Reject/resample conditions: no feasible procedural polygon for requested side set, off-canvas transformed polygon.
4. No-auto-relaxation guarantee: generation fails on unmet constraints.
5. Structural diversity policy: polygons are procedurally sampled per instance (not from a tiny fixed template bank) to reduce cross-seed visual similarity.
6. Graph-paper reference cues: center-origin marker includes axis arrows plus signed integer scale labels across the full visible axis range (no origin text label).
7. Graph-paper color variation: minor/major/axis colors are sampled from constrained ranges per instance, with axis lines always darker than grid lines.
8. Answer bounds: `area_square_units` is constrained to `[8, 32]` by task-group config.

## 5) Complexity + tests
1. Complexity definition/components: polygon sides + area magnitude.
2. Determinism test: `tests/test_geometry_measurement_contracts.py`.
3. Answer/evidence consistency test: `tests/test_geometry_measurement_tasks.py`.
4. Prompt metadata/placeholder test: `tests/test_prompt_system.py`.
5. Constraint-specific tests: lattice-projected vertex evidence and answer-vs-scene attr equality.
