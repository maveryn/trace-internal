# `task_graph__binary_tree__depth_level_node_count`

## Program Contract
- `count(filter(nodes(binary_tree), depth=target_depth)); scene=binary_tree; scope=depth_level_node_count`

## Summary
1. Domain: `graph`
2. Scene id: `binary_tree`
3. Scene: `counting`
4. Task id: `task_graph__binary_tree__depth_level_node_count`
5. Objective: count binary-tree nodes at a specified depth.

## Query IDs
1. `depth_level_node_count`
2. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `point_set`.
3. Annotation marks node-center pixel points for every node at the requested depth.
4. Count tasks require `answer_gt.value == len(annotation_gt.value)` unless the annotation schema is keyed or sequence based.

## Rendering Contract
1. The scene uses the graph-domain renderer for `binary_tree`.
2. Visual style, fonts, panel treatment, layout jitter, and post-render noise are non-semantic and must be recorded in trace metadata.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from graph prompt templates and scene config, not hardcoded user-facing text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
