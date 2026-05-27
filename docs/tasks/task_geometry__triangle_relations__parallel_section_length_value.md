# `task_geometry__triangle_relations__parallel_section_length_value`

## Contract
1. Domain: `geometry`
2. Task group: `measurement`
3. Scene id: `triangle_relations`
4. Public query variant: `default`
5. Query id: one of `parallel_section_cross_length` or `parallel_section_base_length`
6. Answer type: `integer`
7. Evidence type: `bbox_set`

## Prompt Bundle
- Bundle id: `geometry_analytical_measurement_v0`
- Prompt modes: `answer_only` and `answer_and_evidence`

## Behavior
Infer a nested-triangle cross-section length or base length using the scale factor created by a segment parallel to one side.

## Evidence
Prompt-facing evidence is a `bbox_set`: the target segment cue first, followed by the side-section labels, known parallel-section label, and parallel marks needed for the computation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/measurement.yaml`
- Task module: `trace/tasks/geometry/measurement/composite_measurement.py`
