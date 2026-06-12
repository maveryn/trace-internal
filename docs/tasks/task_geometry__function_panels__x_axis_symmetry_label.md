# `task_geometry__function_panels__x_axis_symmetry_label`

## Contract
1. Domain: `geometry`
2. Scene id: `function_panels`
3. Scene id: `function_panels`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `x_axis_symmetry_label`
6. Answer schema: `option_letter`
7. Annotation schema: `bbox_set`

## Program Contract
- `label(select_panel(candidate_function_panels, function_property_rule=x_axis_symmetry_label)); scene=function_panels; scope=x_axis_symmetry_label`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `function_panels`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/function_panels.yaml`
- Task module: `trace/tasks/geometry/function_panels/x_axis_symmetry_label.py`
