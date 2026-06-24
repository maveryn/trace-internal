# `task_geometry__trapezoid_extension__extension_from_parallelogram_perimeter`

## Contract
1. Domain: `geometry`
2. Scene id: `trapezoid_extension`
3. Task id: `task_geometry__trapezoid_extension__extension_from_parallelogram_perimeter`
4. Supported `query_id` values: `single`
5. Answer schema: `number` rounded to one decimal place
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task binds multiple heterogeneous visual witnesses)

## Program Contract
- `solve_formula(visible_trapezoid_extension_measurements, unknown_role=length_measure, formula_schema=extension_from_parallelogram_perimeter); scene=trapezoid_extension; scope=extension_from_parallelogram_perimeter`

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/trapezoid_extension/geometry_trapezoid_extension_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses a role-bound pixel bbox map with exactly these keys:

- `target_cue`
- `original_trapezoid`
- `dashed_parallelogram_completion`
- `supporting_visible_labels`

Numeric formulas and construction metadata remain private verifier metadata unless they are visible witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/trapezoid_extension.yaml`
- Prompt bundle: `prompts/geometry/trapezoid_extension/geometry_trapezoid_extension_v1.json`
- Task module: `trace/tasks/geometry/trapezoid_extension/extension_from_parallelogram_perimeter.py`
