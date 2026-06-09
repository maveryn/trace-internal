# `task_graph__phylogeny_tree__mrca_clade_membership_count`

## Summary
1. Domain: `graph`
2. Scene id: `phylogeny_tree`
3. Task group: `relation`
4. Task id: `task_graph__phylogeny_tree__mrca_clade_membership_count`
5. Objective: count descendant taxa of the most recent common ancestor of two queried taxa.

## Query IDs
1. `mrca_leaf_count`
2. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `keyed_bbox_map`.
3. Annotation keys are `query_leaf_1`, `query_leaf_2`, and `mrca`; descendant leaf labels are recorded in trace metadata.
4. Annotation marks minimal visual witnesses for the MRCA relation.

## Rendering Contract
1. The scene uses the graph-domain renderer for `phylogeny_tree`.
2. The MRCA clade may be highlighted as a visual aid, but the answer is derived from the tree topology metadata.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from graph prompt templates and task-group config, not hardcoded user-facing text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
