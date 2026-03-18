# `task_geometry_analytical_2d_area`

## 1) Identity
1. Domain: `geometry`
2. Task group: `analytical_2d`
3. Task id: `task_geometry_analytical_2d_area`
4. Objective: compute area from annotated single-shape analytical geometry scenes.

## 2) Scene + task contract
1. Entities/relations: exactly one target shape (`rectangle`, `triangle`, `parallelogram`, `trapezoid`, `rhombus`, `circle`, or `ellipse`).
2. Polygon labeling rule: polygon cases render labels for every polygon vertex even when that vertex is not part of a shown measurement annotation.
3. Background: solid (non-graph-paper) analytical canvas; shape coordinates are not required to align to visible lattice marks.
4. Supported `task_variant` values: shape+mode case ids (`<shape>_<mode>`), for example `rectangle_explicit`, `triangle_derived`, `circle_explicit`, `ellipse_derived`.
5. `answer_gt.type`:
   - polygons: `integer`,
   - circle/ellipse: `pi_expression` (`kπ`).
6. Default `evidence_gt.type`: `measurement_ref_map`.
7. Evidence value semantics: object keyed by annotation token (`"AB"`, `"CD"`, ...) where each value is the shown measurement value.
8. Circle area evidence policy: explicit mode uses radius annotation; derived mode uses diameter annotation (not circumference).
9. Alternate evidence forms: projected `measurement_ref_map` + annotation-center `pixel_point_set` / `pixel_annotation_centers` in trace.
10. Overlap/touch policy: single object only.

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_analytical_area_v1`
2. `task_family_key`: `analytical_single_shape`
3. `task_key`: `analytical_area_query`
4. Task-variant mapping: per-case slots (`question_text_<case_id>`, `json_example_<case_id>`, evidence/answer hints) are selected from sampled `task_variant`.
5. Required slots:
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`,
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`.
6. Slot source:
   - shared JSON-format contracts from `configs/domains/geometry/base.yaml` (`prompt.shared`),
   - analytical-family slots from `configs/domains/geometry/analytical_2d.yaml` (`prompt.shared` + `prompt.task_overrides.task_geometry_analytical_2d_area`).
7. Output modes:
   - `answer_only`
   - `answer_and_evidence`

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: one target shape + one formula-instantiation per scene.
3. Reject/resample conditions: infeasible dimension tuples for current answer bounds or scene-fit constraints.
4. No-auto-relaxation guarantee: generation fails on unmet constraints.
5. Variant policy:
   - one explicit and one derived mode per shape family,
   - balanced shape and mode sampling is enabled by default.
6. Answer bounds: shared scalar range applies to integer areas and `k` in `kπ` answers.
7. Unit-scale policy: analytical shape-unit spacing is controlled by analytical render params (`analytical_unit_spacing_px`, `analytical_unit_padding_px`) and is decoupled from graph-paper cell limits used by measurement tasks.

## 5) Complexity + tests
1. Complexity definition/components: shape family + reasoning mode + answer magnitude.
2. Determinism test: `tests/test_geometry_analytical_area_contracts.py`.
3. Answer/evidence consistency test: `tests/test_geometry_analytical_area_tasks.py`.
4. Prompt metadata/placeholder test: `tests/test_prompt_system.py`.
5. Constraint-specific tests: variant-balance checks and case-matched prompt-example cardinality checks.
