# `task_geometry_measurement_angle`

## 1) Identity
1. Domain: `geometry`
2. Task group: `measurement`
3. Task id: `task_geometry_measurement_angle`
4. Objective: measure one target angle from a single-object scene.

## 2) Scene + task contract
1. Entities/relations: one entity (`angle` or `line_intersection` source variant); no inter-entity relations.
2. Supported `task_variant` values: `primitive_angle`, `intersection_angle`.
3. `answer_gt.type`: `integer` (angle measure in degrees rounded to the nearest integer).
4. Default `evidence_gt.type`: `graph_point_set` (exactly 3 integer graph-paper points for the queried angle: the vertex and the two ray endpoints).
5. Alternate evidence forms: projected `point_map` + `grid_point_map` and derived set/path projections in trace.
6. Overlap/touch policy: single object only (no multi-object overlap constraints needed).

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_angle_measure_v1`
2. `task_family_key`: `measurement_single_object`
3. `task_key`: `measurement_angle_value`
4. Task-variant mapping: slot-driven question/evidence values depend on the sampled angle scene variant/source kind.
5. Answer+evidence JSON shape: `{"evidence":[[x1,y1],[x2,y2],[x3,y3]],"answer":<DEGREES_AS_INTEGER>}` where evidence holds the queried angle's three graph-paper points.
6. Answer-only JSON shape: `{"answer":<DEGREES_AS_INTEGER>}`.
7. Required slots:
   - shared: `object_description`, `question_text`,
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`,
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`.
8. Variant counts (task-family/task/mode): exactly 5 templates per required key.
9. Output modes:
   - `answer_only`
   - `answer_and_evidence`

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: single target angle only.
3. Reject/resample conditions: invalid source-kind config, no feasible source construction for requested target angle, off-canvas geometry.
4. No-auto-relaxation guarantee: generation fails on unmet constraints instead of relaxing them.
5. Label rendering: TrueType labels use canvas/spacing-proportional font sizing with outline stroke and overlap-aware placement that avoids geometry lines/other labels when feasible.
6. Structural diversity policy: primitive-angle scenes and line-intersection scenes are both sampled; line-intersection scenes use two crossing segments through the labeled vertex.
7. Source variants: `primitive_angle` and `intersection_lines`.
8. Minimum-ray constraint: every measured angle arm is at least 2 graph units from vertex to endpoint (`min_ray_length_units=2` by default).
9. Axis-alignment policy: every sampled scene has at least one measured ray/line axis-aligned; this holds for both `primitive_angle` and `intersection_angle` variants.
10. Sampling policy: defaults use deterministic balanced sampling (`balanced_sampling=true`) keyed by `_sampling_index` (builder/sample scripts inject this) so source kinds and feasible target answers (`30..150`, constrained by geometry feasibility) are evenly spread over generation cycles unless explicitly overridden.
11. Numeric response policy: prompt asks for the angle measure rounded to the nearest integer degree; accepted constructions must satisfy `|raw_angle_degrees - target_angle| <= 0.05`.
12. Graph-paper reference cues: center-origin marker includes axis arrows plus signed integer scale labels across the full visible axis range (no origin text label).
13. Graph-paper color variation: minor/major/axis colors are sampled from a constrained range per instance, with axis lines always darker than grid lines.

## 5) Complexity + tests
1. Complexity definition/components: variant type + target angle magnitude.
2. Determinism test: `tests/test_geometry_measurement_contracts.py`.
3. Answer/evidence consistency test: `tests/test_geometry_measurement_tasks.py`.
4. Prompt metadata/placeholder test: `tests/test_prompt_system.py`.
5. Constraint-specific tests: 3-point graph-lattice evidence projection, nearest-integer angle consistency checks, and axis-aligned-ray enforcement.
