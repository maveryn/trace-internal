# `task_geometry_counting_angle`

## 1) Identity
1. Domain: `geometry`
2. Task group: `counting`
3. Task id: `task_geometry_counting_angle`
4. Objective: count how many labeled angles in one non-grid geometry scene belong to the requested class.

## 2) Scene + task contract
1. Entities/relations: `6..10` labeled angle entities in one plain-background scene; counting relation over angle class membership.
2. Supported `task_variant` values: `acute_angle`, `right_angle`, `obtuse_angle`.
3. Answer type: `answer_gt.type = integer`.
4. Evidence type: `evidence_gt.type = label_set` (sorted labels of all matching angles).
5. Target-count policy: default feasible counts are `1..object_count-1`, so v1 avoids trivial `0` and `all` scenes.
6. Boundary policy: non-right classes stay at least `10°` away from `90°` so acute/obtuse membership is visually stable.
7. Label policy: each angle gets one object label; labels identify whole objects, not vertices.

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_counting_v1`
2. `task_family_key`: `counting_scene`
3. `task_key`: `counting_query`
4. Answer+evidence JSON shape: `{"evidence":["B","D"],"answer":2}`
5. Answer-only JSON shape: `{"answer":2}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: no graph-paper language and no textual option list.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: the counted class-membership set is constructed first, then rendered; answer and evidence come from the same matching-label trace.
3. Reject/resample conditions: unsupported variant/object-count/target-count config, no feasible angle catalog support for the requested class split, or off-canvas geometry.
4. No-auto-relaxation guarantee: generation fails on unmet class/boundary/layout constraints instead of weakening the angle-class rules.
5. Background policy: plain solid backgrounds only for v1; hidden graph-unit layout coordinates remain trace-only and are not rendered.
6. Balanced defaults: uniform variant/object-count/target-count selections use deterministic `_sampling_index` cycling when present.

## 5) Complexity + tests
1. Complexity definition/components: object count + target count + task variant.
2. Determinism/build tests: `tests/test_geometry_counting_angle_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_geometry_counting_angle_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
