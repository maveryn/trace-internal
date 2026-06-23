# `task_icons__two_anchor__between_anchors_count`

## Program Contract

`counting.spatial_region_count(scene=two_anchor, scope=non_anchor_icons, region=vertical_strip_between_marked_anchors|horizontal_strip_between_marked_anchors, target=center_inside_region, output=count)`

## Identity

- Domain: `icons`
- Scene id: `two_anchor`
- Task id: `task_icons__two_anchor__between_anchors_count`
- Objective contract: count the non-anchor icons whose centers lie in the requested strip between two marked anchors.

## Contract

- Supported `query_id` values: `inside_vertical_strip`, `inside_horizontal_strip`.
- Answer schema: `integer`.
- Annotation schema: `bbox_set`.
- The image contains one panel with two icons marked `A` and `B` plus additional unmarked icons.
- The two anchors share the same icon type, tint, and rotation; they are alignment markers and are never counted.
- `inside_vertical_strip` asks for non-anchor icons whose centers lie horizontally between the anchor centers.
- `inside_horizontal_strip` asks for non-anchor icons whose centers lie vertically between the anchor centers.
- The boundary margin keeps positive and negative icon centers away from the strip boundary.
- The annotation contains boxes for counted non-anchor icons only, sorted top-to-bottom then left-to-right. Empty annotation is valid when the answer is `0`.

## Generation

- `target_count` is sampled from `0..5`.
- `distractor_count` is sampled from `1..10`.
- `object_count = target_count + distractor_count`; the two anchors are additional objects.
- Candidate icons use an icon type different from the anchors. Candidate tints and rotations may vary.
- Query selection is task-owned and uniform unless a supported `query_id` is explicitly supplied.
- Generation rejects samples that cannot place icons under the strip, margin, and overlap constraints.

## Prompt

- Prompt bundle: `icons_two_anchor_v1`
- `scene_key`: `two_anchor_scene`
- `task_key`: `between_anchors_count`
- Query templates ask for the vertical or horizontal strip count.
- Answer-only JSON shape: `{"answer":2}`
- Answer+annotation JSON shape: `{"annotation":[[312,180,372,240],[540,286,612,358]],"answer":2}`

## Annotation

- `bbox_set` is used because the number of counted witnesses can be zero, one, or more.
- Boxes mark the full visible counted icons rather than the anchor markers.
- Anchor boxes remain in trace metadata but are not part of `annotation_gt`.

## Tests

- Behavior and trace tests: `tests/test_icons_relation_between_two_anchors_count_tasks.py`
- Determinism/build tests: `tests/test_icons_relation_between_two_anchors_count_contracts.py`
- Config and prompt bundle tests: `tests/test_icons_scene_config.py`, `tests/test_prompt_system.py`
- Scene-package migration gates: `tests/test_scene_package_migration_contracts.py`, `tests/test_scene_package_review_candidate_contracts.py`
