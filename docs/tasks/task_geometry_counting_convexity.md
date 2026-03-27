# `task_geometry_counting_convexity`

## 1) Identity
1. Domain: `geometry`
2. Task group: `counting`
3. Task id: `task_geometry_counting_convexity`
4. Objective: count how many labeled polygons in one non-grid geometry scene are convex or concave.

## 2) Scene + task contract
1. Entities/relations: `6..9` labeled polygons in one plain-background scene; counting relation over polygon convexity class.
2. Supported `task_variant` values: `convex_polygon`, `concave_polygon`.
3. Polygon families used in the scene: quadrilateral, pentagon, and hexagon only.
4. Answer type: `answer_gt.type = integer`.
5. Evidence type: `evidence_gt.type = label_set` (sorted labels of all polygons that match the requested convexity class).
6. Target-count policy: default feasible counts are `1..object_count-1`, and target counts are sampled from the global feasible support before object count so integer answers stay balanced across scene sizes.
7. Class-separation policy: concave polygons must have one clear reflex indentation; polygons with adjacent collinear edges or self-intersections are rejected as `degenerate` instead of being treated as borderline convex/concave examples.
8. Label policy: each polygon gets one object label; labels identify whole polygons, not their vertices.

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_counting_v1`
2. `task_family_key`: `counting_scene`
3. `task_key`: `counting_query`
4. Answer+evidence JSON shape: `{"evidence":["B","D","G"],"answer":3}`
5. Answer-only JSON shape: `{"answer":3}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: no graph-paper language and no textual option list.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the matching-label set is constructed first, then rendered; answer and evidence come from the same matching-label trace.
3. Reject/resample conditions: unsupported variant/object-count/target-count config, no feasible convex/concave polygon placement for the requested positive/negative split, degenerate polygon classification, or off-canvas placement.
4. No-auto-relaxation guarantee: generation fails on unmet class/layout constraints instead of weakening convexity separation.
5. Background policy: plain solid backgrounds only for v1; hidden graph-unit layout coordinates remain trace-only and are not rendered.
6. Balanced defaults: uniform variant selections use deterministic `_sampling_index` cycling when present.

## 5) Complexity + tests
1. Complexity definition/components: object count + target count + task variant.
2. Determinism/build tests: `tests/test_geometry_counting_convexity_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_geometry_counting_convexity_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
