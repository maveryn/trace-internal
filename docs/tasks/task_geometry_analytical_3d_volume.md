# `task_geometry_analytical_3d_volume`

## 1) Identity
1. Domain: `geometry`
2. Task group: `analytical_3d`
3. Task id: `task_geometry_analytical_3d_volume`
4. Objective: compute volume from one annotated 3D solid.

## 2) Scene + task contract
1. Entities/relations: exactly one target 3D solid (`rectangular_prism`, `triangular_prism`, `square_pyramid`, `cylinder`, `cone`, or `sphere`).
2. Supported `task_variant` values:
   - `rectangular_prism_given_lwh`
   - `triangular_prism_given_b_h_l`
   - `square_pyramid_given_base_height`
   - `cylinder_given_r_h`
   - `cone_given_r_h`
   - `sphere_given_r`
3. Background: solid (non-graph-paper) analytical canvas.
4. `answer_gt.type`:
   - polyhedra variants: `integer`,
   - cylinder/cone/sphere variants: `pi_expression` (`kπ`).
5. Default `evidence_gt.type`: `measurement_ref_map`.
6. Evidence value semantics: object keyed by annotation token (`"AB"`, `"CD"`, ...) where each value is the shown measurement value.
7. Alternate evidence forms: projected `measurement_ref_map` + annotation-center `pixel_point_set` / `pixel_annotation_centers` in trace.
8. Overlap/touch policy: single object only.

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_analytical_volume_v1`
2. `task_family_key`: `analytical_single_solid`
3. `task_key`: `analytical_volume_query`
4. Task-variant mapping: per-variant `question_text_<task_variant>` slot values come from task-group prompt defaults.
5. Required slots:
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`,
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`.
6. Slot source:
   - shared JSON-format contracts from `configs/domains/geometry/base.yaml` (`prompt.shared`),
   - analytical_3d family slots from `configs/domains/geometry/analytical_3d.yaml` (`prompt.shared` + `prompt.task_overrides.task_geometry_analytical_3d_volume`).
7. Output modes:
   - `answer_only`
   - `answer_and_evidence`

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: one target solid + one volume query per scene.
3. Reject/resample conditions: infeasible dimension tuples for current variant and answer bounds.
4. No-auto-relaxation guarantee: generation fails on unmet constraints.
5. Variant policy:
   - balanced variant sampling is enabled by default,
   - default variant weights are uniform across the six task variants.
6. Integer/π policy:
   - polyhedra variants return integer volumes,
   - cylinder/cone/sphere return `kπ` answers with integer coefficient `k`.

## 5) Complexity + tests
1. Complexity definition/components: task-variant family + answer magnitude.
2. Determinism test: `tests/test_geometry_analytical_3d_volume_contracts.py`.
3. Answer/evidence consistency test: `tests/test_geometry_analytical_3d_volume_tasks.py`.
4. Prompt metadata/placeholder test: `tests/test_prompt_system.py`.
5. Constraint-specific tests: per-variant answer-type enforcement and balanced default variant sampling checks.
