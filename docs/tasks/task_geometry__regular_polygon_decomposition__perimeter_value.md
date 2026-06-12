# `task_geometry__regular_polygon_decomposition__perimeter_value`

## Summary
1. Domain: `geometry`
2. Scene id: `regular_polygon_decomposition`
3. Scene package: `measurement`
4. Task id: `task_geometry__regular_polygon_decomposition__perimeter_value`
5. Objective: compute the total perimeter of a regular polygon from a side length or from total area plus apothem.

## Query IDs
1. `perimeter_from_side_length`
2. `perimeter_from_total_area_and_apothem`
3. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `keyed_point_map`.
3. Annotation maps role names to pixel points at the polygon center, support side endpoints, and the apothem foot when the apothem is part of the query.

## Rendering Contract
1. The scene renders a regular polygon decomposed into equal triangular wedges from its center.
2. The support side length or the total-area/apothem labels are visible annotations, not public annotation.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from `geometry_regular_polygon_decomposition_v0`.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the keyed map schema above.
