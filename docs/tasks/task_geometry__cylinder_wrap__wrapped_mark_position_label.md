# `task_geometry__cylinder_wrap__wrapped_mark_position_label`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `cylinder_wrap`
4. Public task id follows taxonomy-v0 `task_geometry__<scene_id>__<objective_contract>`.
5. Query id: `wrapped_mark_position_label`
6. Answer schema: `option_letter`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `label(select_rim_candidate(rim_positions, unwrap_mapping(strip_mark))); scene=cylinder_wrap; scope=wrapped_mark_position_label`

## Prompt Bundle
- Prompt text is loaded from the geometry prompt bundle configured for this task group/task override.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/cylinder_wrap.py`
