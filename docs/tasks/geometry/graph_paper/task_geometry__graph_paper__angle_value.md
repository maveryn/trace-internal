# `task_geometry__graph_paper__angle_value`

## Contract
1. Domain: `geometry`
2. Scene id: `graph_paper`
3. Task id: `task_geometry__graph_paper__angle_value`
4. Supported `query_id`: `single`
5. Answer schema: `integer`
6. Annotation schema: `point_map`

## Program Contract
- `measure_single_angle(target=angle_A, output_role=angle_degrees); scene=graph_paper; scope=single_angle`

## Prompt Bundle
- Prompt text is loaded from `geometry_graph_paper_v1`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
The annotation is a keyed pixel point map with keys `ray_a`, `vertex`, and `ray_b` for the measured angle.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.
