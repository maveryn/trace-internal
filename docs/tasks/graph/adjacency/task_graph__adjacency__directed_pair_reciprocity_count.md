# `task_graph__adjacency__directed_pair_reciprocity_count`

## Summary
1. Domain: `graph`
2. Scene id: `adjacency`
3. Task id: `task_graph__adjacency__directed_pair_reciprocity_count`
4. Objective: count unordered node pairs in a directed adjacency matrix where both directed edges are present.
5. Implementation: `trace/tasks/graph/adjacency/directed_pair_reciprocity_count.py`.

## Query IDs
1. `mutual_pair_count`: count unordered pairs where both mirrored off-diagonal matrix cells are `1`.
2. Query ids are internal replay metadata; public sampling is at the task-id level.

## Taxonomy Contract
1. Program contract: build the unordered off-diagonal node-pair candidate set, filter pairs whose two directed matrix cells are both present, count the filtered pairs, and annotate one mirrored-cell point pair per counted pair.
2. Stable schemas: answer is `integer`; annotation is `point_pair_set`.
3. `target_count`, node labels, node count, font, style, and matrix layout are generation/render metadata, not public query branches.

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `point_pair_set`.
3. Annotation marks one point-pair per counted unordered pair, using the centers of the two mirrored matrix cells.
4. Zero-answer instances use an empty annotation array.

## Rendering Contract
1. The scene uses the graph-domain adjacency-matrix renderer.
2. The graph is directed; rows point to columns.
3. Diagonal cells are excluded from pair counting.
4. Visual style, fonts, panel treatment, context text, and post-render noise are non-semantic and recorded in trace metadata.
5. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from graph prompt templates and scene config, not hardcoded user-facing text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
