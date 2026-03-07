# `task_geometry_measurement_angle`

## 1) Identity
1. Domain: `geometry`
2. Task group: `measurement`
3. Task id: `task_geometry_measurement_angle`
4. Objective: measure one target angle from a single-object scene.

## 2) Scene + query contract
1. Entities/relations: one entity (`angle`, `polygon`, or `line_intersection` source variant); no inter-entity relations.
2. Supported `query_type` values: `measure`.
3. `answer_gt.type`: `option_letter` (selected MCQ option label `A..E`; underlying target angle degrees remain in trace metadata).
4. Default `evidence_gt.type`: `grid_point_set` (ordered 3-point set `[ray endpoint A, vertex, ray endpoint B]` in integer graph units).
5. Alternate evidence forms: projected `point_set`/`point_path` and `grid_point_path` in trace.
6. Overlap/touch policy: single object only (no multi-object overlap constraints needed).

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_angle_measure_v1`
2. `task_type_key`: `measurement_single_object`
3. Query-type mapping: `measure -> angle question text + 5-option MCQ list + option-letter selection instruction`; answer+evidence mode uses evidence-first JSON with shared contract text plus task-specific rules.
4. Answer+evidence JSON shape: `{"evidence":[[x1,y1],[x2,y2],[x3,y3]],"answer":"<OPTION_LETTER>"}` where evidence holds the angle-point triplet.
5. Required slots: `object_description`, `question_text`, `options_text`, `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example` (for answer+evidence mode).
6. Variant counts (task/query/mode): minimum 10 templates per required key.
7. Output modes:
   - `answer_only`
   - `answer_and_evidence`

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: single target angle only.
3. Reject/resample conditions: invalid source-kind config, no feasible source construction for requested target angle, off-canvas geometry.
4. No-auto-relaxation guarantee: generation fails on unmet constraints instead of relaxing them.
5. Label rendering: TrueType labels use canvas/spacing-proportional font sizing with outline stroke and overlap-aware placement that avoids geometry lines/other labels when feasible.
6. Structural diversity policy: polygon-source scenes use triangle/quadrilateral constructions; line-intersection scenes use two crossing segments through the labeled vertex.
7. Source variants: `primitive_angle`, `triangle`, `quadrilateral`, and `intersection_lines`.
8. Minimum-ray constraint: every measured angle arm is at least 2 graph units from vertex to endpoint (`min_ray_length_units=2` by default).
9. Sampling policy: defaults use deterministic balanced sampling (`balanced_sampling=true`) keyed by `_sampling_index` (builder/sample scripts inject this) so source kinds and feasible target answers (`30..150`, constrained by geometry feasibility) are evenly spread over generation cycles unless explicitly overridden.
10. MCQ policy: each prompt shows 5 unique options; 4 distractors are sampled uniformly from values in `[answer-30, answer-5] U [answer+5, answer+30]` clipped to `[30,150]`; ground-truth answer is the selected option letter (`A..E`).
11. Graph-paper reference cues: center-origin marker includes axis arrows plus signed integer scale labels across the full visible axis range (no origin text label).
12. Graph-paper color variation: minor/major/axis colors are sampled from a constrained range per instance, with axis lines always darker than grid lines.

## 5) Complexity + tests
1. Complexity definition/components: variant type + target angle magnitude.
2. Determinism test: `tests/test_geometry_measurement_contracts.py`.
3. Answer/evidence consistency test: `tests/test_geometry_measurement_tasks.py`.
4. Prompt metadata/placeholder test: `tests/test_prompt_system.py`.
5. Constraint-specific tests: ordered 3-point graph-lattice evidence projection and MCQ answer consistency checks.
