# `task_icons__pair_grid__pair_attribute_rule_count`

## 1) Identity
1. Domain: `icons`
2. Scene id: `pair_grid`
3. Task group: `transformation`
4. Task id: `task_icons__pair_grid__pair_attribute_rule_count`
5. Objective: count labeled Scene cells that apply the same color/size attribute-edit rule as the Reference pair.

## 2) Scene + Task Contract
1. Entities/relations: one two-panel image with a `Reference` before/after pair on the left and a labeled `Scene` grid of before/after icon pairs on the right.
2. Supported `query_id` values: `color_only_change`, `size_only_change`, and `color_and_size_change`.
3. Public outputs use `query_variant="default"` and record the sampled branch in `query_id`.
4. Answer type: `answer_gt.type = integer`.
5. Evidence type: `evidence_gt.type = bbox_set` over full matching Scene cells, sorted top-to-bottom then left-to-right.
6. Rule policy: matching means the same changed attribute set as the Reference pair, not the same exact color values. Geometric rotations/flips are excluded and remain covered by `task_icons__pair_grid__pair_geometric_transform_count`.
7. Count policy: `target_count` is sampled independently from `0..4`, `distractor_count` from `1..9`, and `object_count = target_count + distractor_count` is constrained to `4..9`.

## 3) Prompt Contract
1. `prompt_bundle_id`: `icons_transformation_v0`
2. `scene_key`: `reference_pair_grid_transformation`
3. `task_key`: `transformation_query`
4. Answer+evidence JSON shape: `{"evidence":[[336,104,506,274],[532,104,702,274]],"answer":2}`
5. Answer-only JSON shape: `{"answer":2}`
6. Evidence prompt asks for `[x0, y0, x1, y1]` pixel boxes around matching Scene cells.

## 4) Determinism + Constraints
1. Seed namespace: scene-level RNG via `spawn_rng(instance_seed, "scene")`.
2. The sampled attribute rule is balanced across the three query ids under review/default sampling.
3. Target/distractor count sampling is decoupled from attribute-rule cycling under the normal seeded sampler.
4. The Reference pair and all Scene pairs reuse one icon type within each pair; only color and/or size changes define the rule.
5. Distractors use the other two attribute-rule types, so the task cannot be solved by looking for any before/after change.

## 5) Complexity + Tests
1. Complexity components: visual scan, rule inference, ambiguity, and clutter.
2. Determinism/build tests: `tests/test_icons_transformation_pair_attribute_rule_count_tasks.py`
3. Prompt/config coverage: `tests/test_task_group_config.py`
