# Documents Task-Unit Audit

Task-unit audit for `domain=documents` using `docs/workflows/TASK_UNIT_AUDIT.md`.

## Domain summary
1. The documents domain is healthy as a task-unit inventory.
2. The active document tasks all reuse the same page-like grammar, but they correspond to distinct grounding jobs:
   - field lookup,
   - section-local arithmetic,
   - section-local extremum selection,
   - section membership localization,
   - checkbox counting.
3. No current documents task looks like a merge, split, or retire candidate.
4. Recommended domain outcome:
   - `Keep`: `5`
   - `Split`: `0`
   - `Merge`: `0`
   - `Retire`: `0`

## Task findings

### `task_documents_readout_field_value`
- Outcome: `Keep`
- Why: one coherent field-lookup grounding family over structured documents.
- Scene variety: moderate (`form_sheet|invoice_sheet|receipt_sheet`) with meaningful page-grammar changes.
- Query variety: strong (`lookup_identifier|lookup_name|lookup_date|lookup_contact|lookup_amount`)
- Grounding necessity: strong; the model must locate the queried field and read the exact rendered value.
- Evidence fit: good; ordered `[label_bbox, value_bbox]` stays local and natural.
- Follow-up: none required now.

### `task_documents_arithmetic_section_expression_value`
- Outcome: `Keep`
- Why: one coherent section-local arithmetic family rather than a thin extension of field readout.
- Scene variety: moderate (`form_sheet|invoice_sheet|receipt_sheet`)
- Query variety: moderate (`sum_two_amounts_in_section|difference_two_amounts_in_section|sum_minus_amount_in_section`)
- Grounding necessity: strong; the model must localize one section, identify the named operands, and compute a derived value not printed on the page.
- Evidence fit: good; ordered operand-value `bbox_set` stays local and supports the computation naturally.
- Follow-up: none required now.

### `task_documents_relation_section_extremum_value`
- Outcome: `Keep`
- Why: one coherent section-local comparison/extremum family with a stable grounding job.
- Scene variety: moderate; page grammar varies and date-vs-amount subcases still feel like the same section-local extremum problem.
- Query variety: strong (`earliest_date_in_section|latest_date_in_section|largest_amount_in_section|smallest_amount_in_section`)
- Grounding necessity: strong; the model must localize the relevant section and compare multiple rendered values.
- Evidence fit: good; single winning-value `bbox_set` is local and natural for an extremum answer.
- Follow-up: none required now.

### `task_documents_layout_section_membership_label`
- Outcome: `Keep`
- Why: one coherent section-membership localization family. The answer is a section title, but the grounding job is still stable across its cue variants.
- Scene variety: moderate (`form_sheet|invoice_sheet|receipt_sheet`)
- Query variety: moderate (`section_of_field_label|section_of_field_value|section_of_label_value_pair`)
- Grounding necessity: strong; the model must map a cue to the correct visible section grouping on the page.
- Evidence fit: good; section-header `bbox_set` is local and appropriately grounded.
- Follow-up: none required now.

### `task_documents_selection_checkbox_count`
- Outcome: `Keep`
- Why: one distinct checkbox-selection family, not just a small variant of the other section-local tasks.
- Scene variety: moderate (`form_sheet|invoice_sheet|receipt_sheet`)
- Query variety: modest but sufficient (`checked_box_count|unchecked_box_count`)
- Grounding necessity: strong; the model must locate the named checkbox section and visually count state-marked boxes.
- Evidence fit: good; counted checkbox boxes are the natural witness, and empty evidence for zero-count cases still fits the contract.
- Follow-up: none required now.

## Recommended next action
1. Leave the documents task-unit inventory unchanged for now.
2. Revisit only if future document growth starts adding tasks that are too close to field lookup or section-local arithmetic without adding a genuinely new grounding job.
