# `task_geometry__circle_theorem__cyclic_quadrilateral_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `circle_theorem`
5. Query id: `opposite_angle_supplement`, `exterior_angle_from_opposite_interior`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `derive_geometry_metric(visible_cyclic_quadrilateral_angles, derivation_rule=cyclic_opposite_or_exterior_angle, output_role=angle_measure); scene=circle_theorem; scope=cyclic_quadrilateral_angle_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `circle_theorem`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points for the four cyclic vertices, plus the extension point when the queried angle is exterior. Numeric angle labels and the `?` cue are visible annotations plus verifier metadata, not separate annotation objects.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/circle_theorem.yaml`
- Task module: `trace/tasks/geometry/circle_theorem/cyclic_quadrilateral_angle_value.py`
