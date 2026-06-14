# `task_graph__node_link__largest_chordless_cycle_size`

## Summary
1. Domain: `graph`
2. Scene id: `node_link`
3. Scene: `relation`
4. Task id: `task_graph__node_link__largest_chordless_cycle_size`
5. Objective: return the number of nodes in the largest chordless cycle of one undirected graph.

## Query IDs
1. `largest_chordless_cycle_size`
2. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `integer`.
2. Annotation type: `point_sequence`.
3. Annotation is an ordered sequence of node-center pixel points around one largest chordless cycle.
4. `answer_gt.value == len(annotation_gt.value)` by construction.

## Rendering Contract
1. The scene uses the shared graph-domain `node_link` renderer.
2. The graph is simple, undirected, connected, and may contain multiple cycles.
3. Node labels, node colors, node shapes, edge routing, layout, transforms, backgrounds, and post-render noise are non-semantic and recorded in trace metadata.
4. Annotation projection is computed after final layout and style placement.

## Generation Contract
1. Target largest chordless cycle size is sampled from `3..7`.
2. Node count is sampled from `8..10`.
3. The sampler constructs a target chordless cycle, adds a second small cycle so the graph is not unicyclic, attaches remaining nodes, and keeps extra distractor edges only when the finalized graph's largest chordless cycle size remains the target.
4. Final verification uses the finalized adjacency map; answers and annotation are not inferred from the construction recipe alone.

## Prompt Contract
1. Prompt text comes from `graph_relation_v0`, not hardcoded task text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with ordered point-sequence annotation.

## Tests
1. Behavior tests: `tests/test_graph_relation_largest_chordless_cycle_size_tasks.py`
2. Contract tests: `tests/test_graph_relation_largest_chordless_cycle_size_contracts.py`
