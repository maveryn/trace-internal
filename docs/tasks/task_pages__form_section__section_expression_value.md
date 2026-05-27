# `task_pages__form_section__section_expression_value`

## 1) Identity
1. Domain: `pages`
2. Task group: `arithmetic`
3. Task id: `task_pages__form_section__section_expression_value`
4. Objective: locate the named section in a structured document, read the referenced amount fields, compute the requested expression, and return the exact derived amount.

## 2) Scene + task contract
1. Supported `query_variant` values:
   - `sum_two_amounts_in_section`
   - `difference_two_amounts_in_section`
   - `sum_minus_amount_in_section`
2. Supported `scene_variant` values:
   - `form_sheet`
   - `invoice_sheet`
   - `receipt_sheet`
3. `answer_gt.type`: `string`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one structured document page is shown on a light background,
   - the page contains visible named sections with labeled fields and values,
   - only one named section is relevant to the prompt,
   - the queried section contains at least eight visible amount fields, only two or three of which are operands,
   - the answer is not read directly from the page; it is computed from the visible operand values named in the prompt,
   - the active scene variants keep the same section-local arithmetic semantics while changing the page grammar.
6. Generation guarantees:
   - every amount value in the queried section is unique,
   - operands are sampled from the full queried-section amount candidate pool,
   - the queried section is visibly labeled in the rendered document,
   - the computed result is positive,
   - the computed result does not duplicate any visible field value on the page.

## 3) Prompt contract
1. Bundle: `pages_arithmetic_v0`
2. `scene_key`: `structured_document_sections`
3. `task_key`: `section_expression_query`
4. `query_key`: one of `sum_two_amounts_in_section|difference_two_amounts_in_section|sum_minus_amount_in_section`
5. Required slots:
   - scene: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/pages/arithmetic.yaml`,
   - deterministic bundle selection from `prompts/pages/arithmetic/pages_arithmetic_v0.json`,
   - dynamic task-local JSON examples keyed by the active expression variant.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the computed amount string; prompt-facing evidence is the ordered operand value boxes only.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` containing one box for each operand value named in the prompt, in expression order.
2. `scene_ir.entities` stores:
   - `document_page`
   - `document_title`
   - `document_section`
   - `document_section_label`
   - `document_field_box`
   - `document_field_label`
   - `document_field_value`
3. `render_map` includes:
   - `page_bbox_px`
   - `title_bbox_px`
   - `section_label_bboxes_px`
   - `section_box_bboxes_px`
   - `field_label_bboxes_px`
   - `field_value_bboxes_px`
   - `field_box_bboxes_px`
4. `execution_trace` records:
   - `query_variant`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `scene_title`
   - `question_text`
   - `field_count`
   - `field_specs`
   - `section_specs`
   - `query_section_id`
   - `query_section_label`
   - `target_amount_candidate_count`
   - `target_amount_candidate_field_ids`
   - `operand_field_ids`
   - `operand_field_labels`
   - `operand_field_values`
   - `operand_value_bbox_ids`
   - `operator_sequence`
   - `expression_operand_cents`
   - `result_cents`
   - `result_value`
5. `witness_symbolic` stores the ordered operand field ids plus their ordered operand value bbox ids.

## 5) Visual policy
1. Background and post-image noise use the merged pages-domain visual defaults from `configs/domains/pages/base.yaml`.
2. Arithmetic page scenes stay layout-first and OCR-light:
   - short typed values,
   - stable labeled fields,
   - visible section headers,
   - no long paragraphs or handwriting.
3. The scene variants should feel visibly different:
   - `form_sheet` uses boxed field grids with grouped section chrome,
   - `invoice_sheet` uses labeled section blocks for parties, dates, and billing summary,
   - `receipt_sheet` uses narrow row groups with visible section headings.
4. Arithmetic reasoning should stay local:
   - the prompt names one section explicitly,
   - the expression uses only visible amounts inside that section,
   - evidence stays on the operand values rather than widening to the whole section or page.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `query_variant` and `scene_variant` are sampled independently at the policy level; balanced review sampling decouples their seeded sampling cycles so equal-cardinality axes cover the cross-product.
3. Answers and evidence come from the same exact rendered operand values and computed trace payload.
4. No semantic auto-relaxation.
5. If a sampled scene creates duplicate visible values, a non-positive result, or a computed result that already appears elsewhere on the page, reject and resample instead of silently changing the query.
