# `task_geometry__rectangular_solid__cube_edge_from_frame_length_value`

## Contract
1. Domain: `geometry`
2. Scene id: `rectangular_solid`
5. Query ids: `cube_edge_from_total_frame`, `cube_edge_from_partial_frame`
6. Answer schema: `integer_value`
7. Annotation schema: `keyed_bbox_map`

## Program Contract
- `solve_formula(visible_cube_frame_length_measurement, unknown_role=cube_edge, formula_schema=cube_edge_from_frame_length); scene=rectangular_solid; scope=cube_edge_from_frame_length_value`

## Prompt Bundle
- Prompt text is loaded from `geometry_rectangular_solid_v0`.
- Prompt modes: `answer_only` and `answer_and_annotation`.

## Annotation
Prompt-facing annotation uses pixel-space witnesses only. Annotation is a keyed bbox map with `frame_bbox`, `given_length_region_bbox`, and `target_edge_bbox`. Frame-length readouts, highlighted strokes, edge labels, and the `s ?` marker are visible annotations plus private verifier metadata.

## Determinism
Generation is deterministic for a fixed seed, params, config, and prompt bundle version.

## Source
- Config: `configs/domains/geometry/rectangular_solid.yaml`
- Task module: `trace/tasks/geometry/rectangular_solid/cube_edge_from_frame_length_value.py`
