# `task_geometry_analytical_2d_composite_area`

## 1) Identity
1. Domain: `geometry`
2. Task group: `analytical_2d`
3. Task id: `task_geometry_analytical_2d_composite_area`
4. Objective: compute the area of one shaded composite 2D region from annotated analytical geometry scenes.

## 2) Scene + task contract
1. Scene type: one annotated analytical 2D scene with one shaded target region; auxiliary constructions or coupled polygonal shapes are allowed when they define the target area.
2. Supported `task_variant` values:
   - `rectangle_inner_cutout`
   - `rectangle_triangle_cutout`
   - `rectangle_triangle_union`
   - `l_shape_cutout`
   - `step_rectangles_union`
3. Background: solid analytical canvas (no graph paper).
4. `answer_gt.type`: `integer`
5. Answer semantics: exact integer area in square units.
6. `evidence_gt.type`: `measurement_ref_map`
7. Evidence value semantics: JSON object keyed by measurement annotation token (`"AB"`, `"CD"`, ...) with the shown integer measurement value.
8. Shading policy: the target region is rendered with light shaded fill; cutout regions are rendered with background fill while keeping visible outlines.
9. Point-label policy: render only the vertex/anchor labels needed to identify evidence annotations or the composite construction.

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_analytical_composite_area_v1`
2. `task_family_key`: `analytical_composite_area_scene`
3. `task_key`: `analytical_composite_area_query`
4. Required slots:
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
5. Variant-specific slot source: `configs/domains/geometry/analytical_2d.yaml` under `prompt.task_overrides.task_geometry_analytical_2d_composite_area`
6. Output modes:
   - `answer_only`
   - `answer_and_evidence`

## 4) Determinism + constraints
1. Seed namespace: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Variant policy: flat `task_variant` weights with balanced deterministic cycling enabled by default.
3. Inputs policy: givens are sampled as integers and constructed so the composite-area answer is integer by construction.
4. Acceptance rule: sampled area must stay within inclusive `answer_min` / `answer_max` bounds.
5. No-auto-relaxation guarantee: reject/resample on infeasible geometry, out-of-range answers, or non-integral cutout/union constructions.
6. Rendering-fit policy: the analytical scene reserves explicit border margin and uses reduced fill ratio for composite scenes so shaded regions, labels, and annotations stay separated from the canvas edge.

## 5) Complexity + tests
1. Complexity components: `task_variant`, integer answer magnitude.
2. Determinism test: `tests/test_geometry_analytical_2d_composite_area_contracts.py`
3. Behavior/contract test: `tests/test_geometry_analytical_2d_composite_area_tasks.py`
4. Prompt metadata/bundle checks: `tests/test_prompt_system.py`
