# `task_graph__node_link__edge_between_nodes_label`

## Summary
1. Domain: `graph`
2. Scene id: `node_link`
3. Scene: `node_link`
4. Task id: `task_graph__node_link__edge_between_nodes_label`
5. Objective: return the visible text label on the edge between two named nodes.

## Query IDs
1. `edge_between_nodes_label|directed_edge_between_nodes_label`
2. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `string`.
2. Annotation type: `bbox_set`.
3. Annotation marks minimal pixel-space visual witnesses for the answer, not answer labels or non-witness annotations.
4. Count tasks require `answer_gt.value == len(annotation_gt.value)` unless the annotation schema is keyed or sequence based.

## Rendering Contract
1. The scene uses the graph-domain renderer for `node_link`.
2. Visual style, fonts, panel treatment, layout jitter, and post-render noise are non-semantic and must be recorded in trace metadata.
3. Annotation projection is computed after final layout and style placement.
4. Visible edge labels are sampled from the shared label manifest with per-instance support size `16`.
5. Edge labels are lowercase text of `3..5` characters and are filtered so they do not duplicate any visible node label.
6. Instances cap visible labeled edges at `12`; edge-label boxes must be collision-free with node boxes and other edge-label boxes.

## Prompt Contract
1. Prompt text comes from graph prompt templates and scene config, not hardcoded user-facing text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
