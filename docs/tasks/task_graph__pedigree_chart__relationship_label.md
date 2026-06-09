# `task_graph__pedigree_chart__relationship_label`

## Summary
1. Domain: `graph`
2. Scene id: `pedigree_chart`
3. Task group: `relation`
4. Task id: `task_graph__pedigree_chart__relationship_label`
5. Objective: select the visual option giving the family relationship of one labeled person to another labeled person.

## Query IDs
1. `relationship_label_between_two_people`
2. Relationship labels are sampled from `parent`, `child`, `sibling`, `partner`, `grandparent`, and `grandchild`.
3. The rendered answer options always use labels `A` through `F`.
4. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `option_letter`.
2. Annotation type: `keyed_bbox_map`.
3. Annotation uses role keys such as `person_a`, `person_b`, and optional bridge roles such as `shared_parent_1`, `shared_parent_2`, or `middle_parent`.
4. Annotation marks minimal person-symbol boxes for the pedigree witnesses. The selected rendered option is the answer choice and is not public annotation.

## Rendering Contract
1. The scene uses pedigree notation: squares are male individuals and circles are female individuals.
2. Generation rows, individual labels, spouse connectors, and descent/sibling connectors are semantic.
3. The queried people may be visually highlighted for scan support.
4. Six relationship options are rendered inside the image; the prompt must not list prompt-only answer choices.

## Prompt Contract
1. Prompt text comes from graph prompt templates and task-group config.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with keyed bbox annotation.
