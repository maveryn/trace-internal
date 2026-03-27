# `task_geometry_comparison_area`

## 1) Identity
1. Domain: `geometry`
2. Task group: `comparison`
3. Task id: `task_geometry_comparison_area`
4. Objective: compare multiple labeled graph-paper rectangles and choose the unique largest/smallest area winner.

## 2) Scene + task contract
1. Entities/relations: `4..6` rectangle entities in one graph-paper scene; comparison relation over area in square units.
2. Supported `task_variant` values: one current scene variant, `rectangle_set`.
3. Answer type: `answer_gt.type = option_letter` (single-letter label of the winning rectangle).
4. Evidence type: `evidence_gt.type = graph_point_set` (four integer graph-paper points for the winning rectangle vertices).
5. Query types: `largest`, `smallest`.
6. Winner-gap policy: one unique winner is required with `gap_norm >= 0.20`, where `gap_norm = |winner - runner_up| / (max(values) - min(values))`; this task also requires `gap_abs >= 6` square units.
7. Label policy: visible answer labels are sampled independently from slot/layout order so answer-label distributions stay balanced.

## 3) Prompt contract
1. `prompt_bundle_id`: `geometry_comparison_v1`
2. `task_family_key`: `comparison_graph_scene`
3. `task_key`: `comparison_query`
4. Answer+evidence JSON shape: `{"evidence":[[x1,y1],[x2,y2],[x3,y3],[x4,y4]],"answer":"B"}`
5. Answer-only JSON shape: `{"answer":"B"}`
6. Required slots:
   - shared: `object_description`, `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
7. Variant counts (task-family/task/mode): exactly 5 templates per required key.
8. Prompt style: no textual option list; choices live only in the labeled image.

## 4) Determinism + constraints
1. Seed namespaces used: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. Unique-answer policy: exactly one winner label by construction.
3. Reject/resample conditions: unsupported query/object-count config, no feasible rectangle set meeting the gap rule, or off-canvas geometry.
4. No-auto-relaxation guarantee: generation fails on unmet constraints instead of weakening the winner-gap or layout rules.
5. Graph-paper construction: each rectangle uses lattice-aligned vertices and integer side lengths.
6. Balanced defaults: `balanced_sampling=true` cycles query type (`largest`/`smallest`) and object count (`4/5/6`) over `_sampling_index` prefixes when no explicit overrides are supplied.

## 5) Complexity + tests
1. Complexity definition/components: object count + normalized winner gap + query type.
2. Determinism/build tests: `tests/test_geometry_comparison_area_contracts.py`
3. Behavior/trace/prompt tests: `tests/test_geometry_comparison_area_tasks.py`
4. Prompt bundle/config tests: `tests/test_prompt_system.py`, `tests/test_task_group_config.py`
