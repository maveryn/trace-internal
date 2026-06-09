# `task_graph__graph_options__contained_subgraph_label`

## Summary
1. Domain: `graph`
2. Scene id: `graph_options`
3. Task group: `relation`
4. Task id: `task_graph__graph_options__contained_subgraph_label`
5. Objective: select which option graph is contained in the target graph.

## Query IDs
1. `contained_subgraph_label`
2. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `option_letter`.
2. Annotation type: `bbox_set`.
3. Annotation marks minimal pixel-space visual witnesses for the answer, not answer labels or non-witness annotations.
4. Count tasks require `answer_gt.value == len(annotation_gt.value)` unless the annotation schema is keyed or sequence based.

## Rendering Contract
1. The scene uses the graph-domain renderer for `graph_options`.
2. Visual style, fonts, panel treatment, layout jitter, and post-render noise are non-semantic and must be recorded in trace metadata.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from graph prompt templates and task-group config, not hardcoded user-facing text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
