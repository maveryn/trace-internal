# `task_graph__phylogeny_tree__mrca_clade_membership_count`

## Summary
1. Domain: `graph`
2. Scene id: `phylogeny_tree`
3. Source package: `phylogeny_tree`
4. Task id: `task_graph__phylogeny_tree__mrca_clade_membership_count`
5. Objective: count descendant taxa of the most recent common ancestor of two queried taxa.

## Program Contract
count(leaves(descendant_of(mrca(query_leaf_1,query_leaf_2)))); output=integer; annotation=bbox_map(query_leaf_1,query_leaf_2,mrca); scene=phylogeny_tree; scope=mrca_clade_membership_count

## Query IDs
1. Supported `query_id`: `single`.
2. The prompt objective key is `mrca_leaf_count`; it is trace metadata, not a public query branch.

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation schema: `bbox_map`.
3. Annotation keys are `query_leaf_1`, `query_leaf_2`, and `mrca`.
4. Descendant leaf labels are recorded in trace metadata; annotation marks only the role-bound visual witnesses.

## Rendering Contract
1. The scene renders a rooted cladogram with labeled terminal taxa.
2. The queried MRCA clade is not visually highlighted; the solver must infer it from the two named taxa and the generated tree topology.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from `prompts/graph/phylogeny_tree/graph_phylogeny_tree_v1.json`.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
