# `task_graph__pedigree_chart__relationship_label`

## Summary
1. Domain: `graph`
2. Scene id: `pedigree_chart`
3. Source package: `trace/tasks/graph/pedigree_chart/relationship_label.py`
4. Task id: `task_graph__pedigree_chart__relationship_label`
5. Objective: select the rendered option letter that gives the family relationship of one labeled person to another.

## Program Contract
- `select(option_label where option_value == relationship(person_a, person_b)); output=option_letter; annotation=bbox_set(person_symbol_witnesses); scene=pedigree_chart; scope=relationship_label`
- Supported `query_id`: `single`
- Internal prompt query key: `relationship_label_between_two_people`

## Answer And Annotation
1. Answer type: `option_letter`.
2. Annotation schema: `bbox_set`.
3. Annotation boxes mark the queried people plus any intermediate/shared person symbols needed to verify the relationship.
4. Role-to-person ids are recorded in trace metadata.
5. The selected option is the answer, not annotation.

## Rendering Contract
1. The scene uses pedigree notation: squares are male individuals and circles are female individuals.
2. Generation rows, individual labels, spouse connectors, and descent/sibling connectors are semantic.
3. The queried people may be highlighted for scan support.
4. Six relationship options are rendered inside the image.

## Prompt Contract
1. Prompt text comes from `prompts/graph/pedigree_chart/graph_pedigree_chart_v1.json`.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with bbox-set annotation.
