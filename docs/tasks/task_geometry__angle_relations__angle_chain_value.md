# `task_geometry__angle_relations__angle_chain_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `angle_relations`
4. Public query id: `default`
5. Query id: one of `triangle_exterior_angle` or `parallel_supplement_angle`
6. Answer type: `integer`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_analytical_measurement_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Infer a missing angle in an angle-relation diagram from visible angle labels and constraint marks.

## Evidence
Prompt-facing evidence is a `bbox_set`: the target cue first, followed by the supporting visible labels or marks needed for the computation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/composite_measurement.py`
