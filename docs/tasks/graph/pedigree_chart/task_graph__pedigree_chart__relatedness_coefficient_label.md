# `task_graph__pedigree_chart__relatedness_coefficient_label`

## Summary
1. Domain: `graph`
2. Scene id: `pedigree_chart`
3. Source package: `trace/tasks/graph/pedigree_chart/relatedness_coefficient_label.py`
4. Task id: `task_graph__pedigree_chart__relatedness_coefficient_label`
5. Objective: select the rendered option letter that gives the coefficient of relatedness between two labeled people.

## Program Contract
- `select(option_label where option_value == relatedness_coefficient(person_a, person_b)); output=option_letter; annotation=bbox_map(person_symbol_and_path_witnesses); scene=pedigree_chart; scope=relatedness_coefficient_label`
- Supported `query_id`: `single`
- Internal prompt query key: `relatedness_coefficient_between_two_people`

## Answer And Annotation
1. Answer type: `option_letter`.
2. Annotation schema: `bbox_map`.
3. Required annotation keys: `person_a`, `person_b`.
4. Optional annotation keys include shared-ancestor and path-witness roles when the coefficient comes from one or more contributing family paths.
5. Annotation marks minimal person-symbol boxes for the pedigree witnesses. The selected option is the answer, not annotation.

## Rendering Contract
1. The scene uses pedigree notation: squares are male individuals and circles are female individuals.
2. Generation rows, individual labels, spouse connectors, and descent/sibling connectors are semantic.
3. The queried people may be highlighted for scan support.
4. Six fraction options are rendered inside the image.

## Prompt Contract
1. Prompt text comes from `prompts/graph/pedigree_chart/graph_pedigree_chart_v1.json`.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with keyed bbox annotation.
