# `task_graph__node_link__largest_component_size`

## Summary
1. Domain: `graph`
2. Scene id: `node_link`
3. Task group: `comparison`
4. Task id: `task_graph__node_link__largest_component_size`
5. Objective: return the size of the unique largest connected component.

## Query IDs
1. `largest_component_size`
2. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `point_set`.
3. Annotation marks minimal pixel-space visual witnesses for the answer, not answer labels or non-witness annotations.
4. Count tasks require `answer_gt.value == len(annotation_gt.value)` unless the annotation schema is keyed or sequence based.

## Rendering Contract
1. The scene uses the graph-domain renderer for `node_link`.
2. Visual style, fonts, panel treatment, layout jitter, and post-render noise are non-semantic and must be recorded in trace metadata.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from graph prompt templates and task-group config, not hardcoded user-facing text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
