# `task_geometry__regular_polygon_decomposition__central_angle_value`

## Summary
1. Domain: `geometry`
2. Scene id: `regular_polygon_decomposition`
3. Scene package: `regular_polygon_decomposition`
4. Task id: `task_geometry__regular_polygon_decomposition__central_angle_value`
5. Objective: compute the central angle of one wedge or a marked group of wedges in a regular polygon.

## Query IDs
1. `single_wedge_central_angle`
2. `marked_wedges_central_angle`
3. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `keyed_point_map`.
3. Annotation maps role names to pixel points at the polygon center and angle-ray endpoints.

## Rendering Contract
1. The scene renders a regular polygon decomposed into equal triangular wedges from its center.
2. The target central angle is marked at the polygon center.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from `geometry_regular_polygon_decomposition_v0`.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the keyed map schema above.
