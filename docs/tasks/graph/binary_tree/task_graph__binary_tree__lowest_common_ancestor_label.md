# `task_graph__binary_tree__lowest_common_ancestor_label`

## Program Contract
- `label(lowest_common_ancestor(binary_tree, node_a, node_b)); scene=binary_tree; scope=lowest_common_ancestor_label`

## Summary
1. Domain: `graph`
2. Scene id: `binary_tree`
3. Scene: `relation`
4. Task id: `task_graph__binary_tree__lowest_common_ancestor_label`
5. Objective: return the lowest common ancestor label for two binary-tree nodes.

## Query IDs
1. `lowest_common_ancestor_label`
2. Query ids are internal replay metadata; public sampling is at the task-id level.
3. The hidden generation axis `relation_answer_scope` targets non-root LCAs 75% of the time and root LCAs 25% of the time; it is recorded in trace metadata and is not a public query branch.

## Answer And Annotation
1. Answer type: `string`.
2. Annotation type: `keyed_point_map`.
3. Annotation marks role-bound node-center pixel points for `node_a`, `node_b`, and `lowest_common_ancestor`.
4. Count tasks require `answer_gt.value == len(annotation_gt.value)` unless the annotation schema is keyed or sequence based.

## Rendering Contract
1. The scene uses the graph-domain renderer for `binary_tree`.
2. Visual style, fonts, panel treatment, layout jitter, and post-render noise are non-semantic and must be recorded in trace metadata.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from graph prompt templates and scene config, not hardcoded user-facing text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
