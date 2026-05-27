# `task_geometry__angle_relations__algebraic_angle_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `angle_relations`
4. Public query variant: `default`
5. Query id: one of `triangle_single_extension_expression` or `triangle_double_extension_expression`
6. Answer type: `integer`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_analytical_measurement_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Solve an angle equation from a triangle angle-relation diagram with one or two extended sides and report the requested angle measure.

## Evidence
Prompt-facing evidence is a `bbox_set`: the target expression cue first, followed by the supporting exterior-angle labels or numeric angle labels needed for the computation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/composite_measurement.py`
