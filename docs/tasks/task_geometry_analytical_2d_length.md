# `task_geometry_analytical_2d_length`

## 1) Identity
1. Domain: `geometry`
2. Task group: `analytical_2d`
3. Task id: `task_geometry_analytical_2d_length`
4. Objective: compute a derived 2D length from annotated analytical geometry scenes.

## 2) Scene + task contract
1. Scene type: one annotated 2D geometry scene, potentially with auxiliary constructions or multiple coupled shapes.
2. Supported `task_variant` values:
   - `triangle_altitude_side`
   - `rectangle_diagonal_side`
   - `rhombus_diagonal_side`
   - `isosceles_trapezoid_leg`
   - `inscribed_square_side`
   - `circle_chord_length`
3. Background: solid analytical canvas (no graph paper).
4. `answer_gt.type`: `number`
5. Answer semantics: rounded to the nearest tenth.
6. `evidence_gt.type`: `measurement_ref_map`
7. Evidence value semantics: JSON object keyed by measurement annotation token (`"AB"`, `"CD"`, ...) with the shown integer measurement value.
8. Point-label policy: render vertex/anchor labels needed to identify the target segment and evidence annotations.
9. Auxiliary-construction policy: helper lines (altitudes, diagonals, center-to-chord distance, diameter guides) may be drawn when required by the derivation.

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_analytical_length_v1`
2. `task_family_key`: `analytical_length_scene`
3. `task_key`: `analytical_length_query`
4. Required slots:
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Variant-specific slot source: `configs/domains/geometry/analytical_2d.yaml` under `prompt.task_overrides.task_geometry_analytical_2d_length`
6. Output modes:
   - `answer_only`
   - `answer_and_evidence`

## 4) Determinism + constraints
1. Seed namespace: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Variant policy: flat `task_variant` weights with balanced deterministic cycling enabled by default.
3. Inputs policy: givens are sampled as integers; the target answer may be non-integer and is rounded to one decimal place.
4. Acceptance rule: sampled raw length must round into the configured inclusive `answer_min` / `answer_max` range.
5. No-auto-relaxation guarantee: reject/resample on infeasible geometry or out-of-range rounded answers.
6. Rendering-fit policy: the scene is scaled with reserved border margin so labels and constructions remain visually separated from the canvas edge.

## 5) Complexity + tests
1. Complexity components: `task_variant`, rounded answer magnitude.
2. Determinism test: `tests/test_geometry_analytical_2d_length_contracts.py`
3. Behavior/contract test: `tests/test_geometry_analytical_2d_length_tasks.py`
4. Prompt metadata/bundle checks: `tests/test_prompt_system.py`
