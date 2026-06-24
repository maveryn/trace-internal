# `task_geometry__rectangular_solid__cube_edge_from_frame_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `rectangular_solid`
3. Task id: `task_geometry__rectangular_solid__cube_edge_from_frame_length_value`
4. Supported `query_id` values: `cube_edge_from_total_frame`, `cube_edge_from_partial_frame`
5. Answer schema: `integer_value`
6. Annotation schema: `bbox_map`
7. Scalar annotation checked: `true` (not scalar-eligible; the task always binds frame, given-length region, and target edge roles)

## Program Contract
- `solve_formula(cube_wire_frame_length_measurement, unknown_role=cube_edge, formula_schema=edge_length_from_frame_edge_count); scene=rectangular_solid; scope=cube_edge_from_frame_length_value`

## Query Semantics
- `cube_edge_from_total_frame` asks for the cube edge length from the total visible cube frame length.
- `cube_edge_from_partial_frame` asks for the cube edge length from the highlighted portion of the cube frame.
- The sampled edge length, highlighted path, highlighted edge count, style, font, and layout jitter are internal replay metadata.

## Prompt Bundle
- Prompt text is loaded from `prompts/geometry/rectangular_solid/geometry_rectangular_solid_v1.json`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space keyed boxes: `frame_bbox`, `given_length_region_bbox`, and `target_edge_bbox`. Frame-length readouts, highlighted strokes, edge labels, and the `?` marker remain visible diagram content and private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/rectangular_solid.yaml`
- Prompt bundle: `prompts/geometry/rectangular_solid/geometry_rectangular_solid_v1.json`
- Task module: `trace/tasks/geometry/rectangular_solid/cube_edge_from_frame_length_value.py`
