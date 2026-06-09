# `task_graph__pedigree_chart__relatedness_coefficient_label`

## Summary
1. Domain: `graph`
2. Scene id: `pedigree_chart`
3. Task group: `relation`
4. Task id: `task_graph__pedigree_chart__relatedness_coefficient_label`
5. Objective: select the visual option giving the coefficient of relatedness between two labeled people.

## Query IDs
1. `relatedness_coefficient_between_two_people`
2. Target relatedness coefficients are sampled from `0`, `1/8`, `1/4`, `3/8`, and `1/2`.
3. The rendered answer options always use labels `A` through `F`.
4. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `option_letter`.
2. Annotation type: `keyed_bbox_map`.
3. Annotation always includes `person_a` and `person_b`.
4. Annotation may include keyed shared-ancestor and path-witness roles when the coefficient comes from one or more contributing family paths.
5. Annotation marks minimal person-symbol boxes for the pedigree witnesses. The selected rendered option is the answer choice and is not public annotation.

## Rendering Contract
1. The scene uses pedigree notation: squares are male individuals and circles are female individuals.
2. Generation rows, individual labels, spouse connectors, and descent/sibling connectors are semantic.
3. The queried people may be visually highlighted for scan support.
4. Six fraction options are rendered inside the image; the prompt must not list prompt-only answer choices.

## Prompt Contract
1. Prompt text comes from graph prompt templates and task-group config.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with keyed bbox annotation.
