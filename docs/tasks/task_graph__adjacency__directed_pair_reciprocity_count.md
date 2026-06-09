# `task_graph__adjacency__directed_pair_reciprocity_count`

## Summary
1. Domain: `graph`
2. Scene id: `adjacency`
3. Task group: `counting`
4. Task id: `task_graph__adjacency__directed_pair_reciprocity_count`
5. Objective: count unordered node pairs in a directed adjacency matrix by reciprocal edge state.

## Query IDs
1. `one_way_pair_count`: count unordered pairs where exactly one mirrored off-diagonal matrix cell is `1`.
2. `mutual_pair_count`: count unordered pairs where both mirrored off-diagonal matrix cells are `1`.
3. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `bbox_set`.
3. Annotation marks both mirrored matrix cells for every counted unordered pair.
4. Zero-answer instances use an empty annotation array.

## Rendering Contract
1. The scene uses the graph-domain adjacency-matrix renderer.
2. The graph is directed; rows point to columns.
3. Diagonal cells are excluded from pair counting.
4. Visual style, fonts, panel treatment, context text, and post-render noise are non-semantic and recorded in trace metadata.
5. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from graph prompt templates and task-group config, not hardcoded user-facing text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
