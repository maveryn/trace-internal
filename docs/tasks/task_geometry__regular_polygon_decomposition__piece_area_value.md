# `task_geometry__regular_polygon_decomposition__piece_area_value`

## Summary
1. Domain: `geometry`
2. Scene id: `regular_polygon_decomposition`
3. Task group: `measurement`
4. Task id: `task_geometry__regular_polygon_decomposition__piece_area_value`
5. Objective: compute the area of one regular-polygon wedge or shaded wedge group.

## Query IDs
1. `single_wedge_area_from_total`
2. `shaded_wedges_area_from_total`
3. `wedge_area_from_side_and_apothem`
4. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `integer` or `number`, depending on the sampled measurement.
2. Annotation type: `keyed_point_map`.
3. Annotation maps role names to pixel points at the polygon center, wedge boundary vertices, and target-region midpoint.

## Rendering Contract
1. The scene renders a regular polygon decomposed into equal triangular wedges from its center.
2. The target region is marked by shading.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from `geometry_regular_polygon_decomposition_v0`.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the keyed map schema above.
