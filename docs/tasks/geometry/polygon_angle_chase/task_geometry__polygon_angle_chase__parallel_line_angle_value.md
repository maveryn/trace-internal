# `task_geometry__polygon_angle_chase__parallel_line_angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `polygon_angle_chase`
5. Query id: `single_transversal_chain`, `two_transversal_angle_sum`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_point_map`

## Program Contract
- `derive_geometry_metric(visible_parallel_line_angle_measurements, derivation_rule=parallel_transversal_angle_relations, output_role=angle_measure); scene=polygon_angle_chase; scope=parallel_line_angle_value`

## Prompt Bundle
- Prompt text is loaded from the scene prompt bundle configured for `polygon_angle_chase`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses keyed pixel points at the target angle vertex and the supporting angle or intersection vertices needed for the relation chain. Visible degree labels, angle arcs, and parallel marks are annotations plus verifier metadata, not separate public annotation.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/polygon_angle_chase.yaml`
- Prompt bundle: `prompts/geometry/polygon_angle_chase/geometry_polygon_angle_chase_v0.json`
- Task module: `trace/tasks/geometry/polygon_angle_chase/parallel_line_angle_value.py`
