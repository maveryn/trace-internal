# `task_geometry__tangent_packing__two_circles_in_rectangle_radius_from_gap_area`

## Contract
1. Domain: `geometry`
2. Scene id: `tangent_packing`
3. Task id: `task_geometry__tangent_packing__two_circles_in_rectangle_radius_from_gap_area`
4. Supported `query_id`: `single`
5. Answer schema: `number`
6. Answer precision: `one_decimal`
7. Annotation schema: `bbox`

## Program Contract
- `inverse_curvilinear_gap_measure(container=rectangle, packed_shape=two_equal_circles, given=shaded_area, target=circle_radius); scene=tangent_packing; scope=two_circles_in_rectangle_radius_from_gap_area`

## Prompt Bundle
- Prompt text is loaded from the v1 scene prompt bundle configured for `tangent_packing`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation is one scalar pixel bbox around the marked target geometric region or shape, excluding numeric labels and measurement text.

The answer placeholder label is not a separate annotation witness. Formula metadata remains private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/tangent_packing.yaml`
- Task module: `trace/tasks/geometry/tangent_packing/two_circles_in_rectangle_radius_from_gap_area.py`
