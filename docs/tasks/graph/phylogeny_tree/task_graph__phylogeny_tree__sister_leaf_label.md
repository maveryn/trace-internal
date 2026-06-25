# `task_graph__phylogeny_tree__sister_leaf_label`

## Summary
1. Domain: `graph`
2. Scene id: `phylogeny_tree`
3. Source package: `phylogeny_tree`
4. Task id: `task_graph__phylogeny_tree__sister_leaf_label`
5. Objective: identify the sister taxon leaf of a queried taxon.

## Program Contract
select(label(leaf) where shares_immediate_parent(leaf, queried_leaf)); output=string; annotation=point(sister_leaf_center); scene=phylogeny_tree; scope=sister_leaf_label

## Query IDs
1. Supported `query_id`: `single`.
2. The prompt objective key is `sister_leaf_label`; it is trace metadata, not a public query branch.

## Answer And Annotation
1. Answer type: `string`.
2. Annotation schema: `point`.
3. Annotation is the center point of the answer sister taxon leaf.
4. Query leaf, sister leaf, and shared-parent ids are recorded in trace metadata.

## Rendering Contract
1. The scene renders a rooted cladogram with labeled terminal taxa.
2. Leaf labels are prompt-facing taxon labels; internal branch points are unlabeled.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from `prompts/graph/phylogeny_tree/graph_phylogeny_tree_v1.json`.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
