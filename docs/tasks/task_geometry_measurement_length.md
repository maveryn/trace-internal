# `task_geometry_measurement_length`

## 1) Identity
1. Domain: `geometry`
2. Task group: `measurement`
3. Task id: `task_geometry_measurement_length`
4. Objective: measure one target segment length from a single-object scene.

## 2) Scene + query contract
1. Entities/relations: one entity (`segment`, `polygon`, `circle`, or `ellipse` variant); no inter-entity relations.
2. Supported `query_type` values: `measure`.
3. `answer_gt.type`: `integer`.
4. Default `evidence_gt.type`: `grid_point_map` with variant-specific cardinality:
   - circle variants (`circle_radius`, `circle_diameter`): one labeled center point,
   - non-circle variants: two labeled endpoints.
5. Alternate evidence forms: projected `point_map` + `grid_point_map` and derived set/path projections in trace.
6. Overlap/touch policy: single object only (no multi-object overlap constraints needed).

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_measurement_v1`
2. `task_type_key`: `measurement_single_object`
3. Query-type mapping: `measure -> variant-specific length question`:
   - segment: labeled endpoint pair,
   - polygon: labeled side pair,
   - circle: radius or diameter,
   - ellipse: major/minor axis.
4. Answer+evidence JSON shape is variant-specific via labeled point maps:
   - circle variants: `{"evidence":{"O":[x,y]},"answer":<integer>}`,
   - non-circle variants: `{"evidence":{"A":[x1,y1],"B":[x2,y2]},"answer":<integer>}`.
5. Answer-only JSON shape: `{"answer":<integer>}`.
6. Required slots:
   - shared: `object_description`, `question_text`,
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`,
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`.
7. Slot source:
   - shared JSON-format contracts from `configs/domains/geometry/base.yaml` (`prompt.shared`),
   - measurement-family prompt slots from `configs/domains/geometry/measurement.yaml` (`prompt.shared` + `prompt.task_overrides.task_geometry_measurement_length`).
8. Variant counts (task/query/mode): minimum 10 templates per required key.
9. Output modes:
   - `answer_only`
   - `answer_and_evidence`

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: single measured segment/axis per scene.
3. Reject/resample conditions: unsupported variant config, no feasible integer-length candidate for configured bounds/context, off-canvas geometry.
4. No-auto-relaxation guarantee: generation fails on unmet constraints instead of relaxing them.
5. Integer policy:
   - all reported length answers are integers,
   - polygon vertices and measured endpoints are graph-lattice aligned.
6. Supported variants:
   - `segment`,
   - `triangle` / `quadrilateral` / `pentagon` side length,
   - `circle_radius` / `circle_diameter`,
   - `ellipse_major_axis` / `ellipse_minor_axis`.
7. Default answer-range policy:
   - configured length answers are constrained to `[2, 8]`.
8. Rendering policy for conics:
   - circle/ellipse tasks do not draw helper radius/diameter/axis segments.
   - circle evidence uses center point only.
   - ellipse evidence uses major/minor axis endpoints.
9. Graph-bounds policy:
   - sampled measured endpoints and conic extents must remain inside the visible graph-paper draw region.

## 5) Complexity + tests
1. Complexity definition/components: shape variant + answer magnitude.
2. Determinism test: `tests/test_geometry_measurement_contracts.py`.
3. Answer/evidence consistency test: `tests/test_geometry_measurement_tasks.py`.
4. Prompt metadata/placeholder test: `tests/test_prompt_system.py`.
5. Constraint-specific tests: integer answer guarantees, 2-point graph-lattice evidence projection, and variant-balance checks.
