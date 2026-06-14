# `task_geometry__paper_fold__paper_fold_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `paper_fold`
5. Query id: `fold_angle_from_total_label`
6. Answer schema: `decimal_value_1dp`
7. Annotation schema: `bbox_set`

## Program Contract
- `solve_formula(visible_paper_fold_measurements, unknown_role=angle_measure, formula_schema=fold_crease_bisects_total_angle); scene=paper_fold; scope=paper_fold_angle_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `paper_fold`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Keyed annotation is used where witness roles matter; graph coordinates, formulas, labels, and construction metadata remain private verifier metadata unless they are themselves visual witnesses.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/paper_fold.yaml`
- Task module: `trace/tasks/geometry/paper_fold/paper_fold_angle_value.py`
