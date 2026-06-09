# `task_graph__phylogeny_tree__clade_leaf_count`

## Summary
1. Domain: `graph`
2. Scene id: `phylogeny_tree`
3. Task group: `counting`
4. Task id: `task_graph__phylogeny_tree__clade_leaf_count`
5. Objective: count descendant taxon leaves in a marked clade.

## Query IDs
1. `marked_clade_leaf_count`
2. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `point_set`.
3. Annotation marks terminal centers for every descendant taxon in the marked clade.
4. Count tasks require `answer_gt.value == len(annotation_gt.value)` unless the annotation schema is keyed or sequence based.

## Rendering Contract
1. The scene uses the graph-domain renderer for `phylogeny_tree`.
2. Branch rotation, child order, branch length, style, fonts, panel treatment, and post-render noise are non-semantic and recorded in trace metadata.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from graph prompt templates and task-group config, not hardcoded user-facing text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
