# `task_graph__phylogeny_tree__sister_leaf_label`

## Summary
1. Domain: `graph`
2. Scene id: `phylogeny_tree`
3. Source package: `phylogeny_tree`
4. Task id: `task_graph__phylogeny_tree__sister_leaf_label`
5. Objective: identify the sister taxon leaf of a queried taxon.

## Query IDs
1. `sister_leaf_label`
2. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `string`.
2. Annotation type: `keyed_bbox_map`.
3. Annotation keys are `target_leaf`, `sister_leaf`, and `shared_parent`.
4. Annotation marks minimal visual witnesses for the relation, not answer labels or numeric annotations.

## Rendering Contract
1. The scene uses the graph-domain renderer for `phylogeny_tree`.
2. Leaf labels are prompt-facing taxon labels; internal branch points are unlabeled.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from `prompts/graph/phylogeny_tree/phylogeny_tree_v0.json` and `configs/domains/graph/phylogeny_tree.yaml`, not hardcoded user-facing text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
