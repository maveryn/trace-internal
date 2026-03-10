# `task_geometry_measurement_slope`

## 1) Identity
1. Domain: `geometry`
2. Task group: `measurement`
3. Task id: `task_geometry_measurement_slope`
4. Objective: measure the slope of one displayed line on graph paper.

## 2) Scene + task contract
1. Entities/relations: one line entity; no inter-entity relations.
2. Supported `task_variant` values: `line_slope`.
3. `answer_gt.type`: `number` (slope value rounded to one decimal place).
4. `evidence_gt.type`: `grid_point_map` with one labeled point (`X`) for the x-axis crossing.
5. Construction constraints:
   - line is finite (`dx != 0`, no infinite slope),
   - line crosses the x-axis at an integer graph coordinate,
   - line passes through at least one additional integer lattice point,
   - drawn segment extends beyond both integer lattice anchor points.

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_measurement_v1`
2. `task_family_key`: `measurement_single_object`
3. `task_key`: `measurement_query`
4. Answer+evidence JSON shape: `{"evidence":{"X":[x,0]},"answer":<SLOPE_TO_ONE_DECIMAL>}`.
5. Answer-only JSON shape: `{"answer":<SLOPE_TO_ONE_DECIMAL>}`.
6. Required prompt slots:
   - shared: `object_description`, `question_text`,
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`,
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`.

## 4) Determinism + constraints
1. Seed namespace: scene RNG via `spawn_rng(instance_seed, "scene")`.
2. Sampling control: `slope_tenths_min/max`, optional explicit `target_slope_tenths`, optional weight map, and deterministic balance via `_sampling_index` when uniform defaults apply.
3. Feasibility policy: slope sampling is filtered per-scene to values that satisfy x-axis crossing + second lattice-point constraints inside the current graph bounds.
4. Reject/resample conditions: no feasible slope values for current graph/canvas bounds, no feasible placement for chosen slope, or invalid slope-range config.
5. No-auto-relaxation guarantee: hard failure when constraints are unsatisfied.

## 5) Complexity + tests
1. Complexity definition/components: absolute slope magnitude.
2. Determinism/build contract test: `tests/test_geometry_measurement_contracts.py`.
3. Answer/evidence/geometry consistency test: `tests/test_geometry_measurement_tasks.py`.
4. Prompt/config wiring test: `tests/test_task_group_config.py`.
