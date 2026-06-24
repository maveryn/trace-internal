# `task_geometry__tangent_packing__two_circles_in_rectangle_radius_from_gap_area`

## Contract
1. Domain: `geometry`
2. Scene id: `tangent_packing`
5. Query id: `single`
6. Answer schema: `number` rounded to one decimal place
7. Annotation schema: `bbox_map`

## Program Contract
- `inverse_curvilinear_gap_measure(container=rectangle, packed_shape=two_equal_circles, given=shaded_area, target=circle_radius); scene=tangent_packing; scope=two_circles_in_rectangle_radius_from_gap_area`

## Prompt Bundle
- Prompt text is loaded from the v1 scene prompt bundle configured for `tangent_packing`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a role-bound pixel bbox map with exactly these keys:

- `target_cue`
- `packing_region`
- `support_measurement`

Numeric labels and formula metadata remain private verifier metadata unless they are visible witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/tangent_packing.yaml`
- Task module: `trace/tasks/geometry/tangent_packing/two_circles_in_rectangle_radius_from_gap_area.py`
