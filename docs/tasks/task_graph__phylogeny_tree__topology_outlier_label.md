# `task_graph__phylogeny_tree__topology_outlier_label`

## Summary
1. Domain: `graph`
2. Scene id: `phylogeny_tree`
3. Task group: `relation`
4. Task id: `task_graph__phylogeny_tree__topology_outlier_label`
5. Objective: choose the only option cladogram with a different rooted topology.

## Query IDs
1. `topology_outlier_label`
2. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `string` option letter.
2. Annotation type: `bbox_set`.
3. Annotation is exactly one option-panel bbox for the selected visual option.
4. Option bboxes are allowed because this is a true visual option-image task.

## Rendering Contract
1. The scene uses the graph-domain renderer for `phylogeny_tree` option panels.
2. Options `A` through `F` use fixed panel positions.
3. Five options are topology-equivalent rotations/layout variants; one option has a different rooted clade signature over the same taxon labels.

## Prompt Contract
1. Prompt text comes from graph prompt templates and task-group config, not hardcoded user-facing text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.
