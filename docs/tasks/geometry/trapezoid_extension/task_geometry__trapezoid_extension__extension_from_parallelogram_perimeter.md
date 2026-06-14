# `task_geometry__trapezoid_extension__extension_from_parallelogram_perimeter`

## Contract
1. Domain: `geometry`
2. Scene id: `trapezoid_extension`
5. Query id: `extension_from_parallelogram_perimeter`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `solve_formula(visible_trapezoid_extension_measurements, unknown_role=length_measure, formula_schema=extension_from_parallelogram_perimeter); scene=trapezoid_extension; scope=extension_from_parallelogram_perimeter`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `trapezoid_extension`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/trapezoid_extension.yaml`
- Task module: `trace/tasks/geometry/trapezoid_extension/extension_from_parallelogram_perimeter.py`
