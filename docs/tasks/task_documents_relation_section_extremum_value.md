# `task_documents_relation_section_extremum_value`

## 1) Identity
1. Domain: `documents`
2. Task group: `relation`
3. Task id: `task_documents_relation_section_extremum_value`
4. Objective: locate the named section in a structured document and return the exact visible date or amount that is extremal within that section.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `earliest_date_in_section`
   - `latest_date_in_section`
   - `largest_amount_in_section`
   - `smallest_amount_in_section`
2. Supported `scene_variant` values:
   - `form_sheet`
   - `invoice_sheet`
   - `receipt_sheet`
3. Compatibility:
   - date variants support `form_sheet|invoice_sheet|receipt_sheet`
   - amount variants support `invoice_sheet|receipt_sheet`
4. `answer_gt.type`: `string`
5. `evidence_gt.type`: `bbox_set`
6. Scene contract:
   - one structured document page is shown on a light background,
   - the page contains visible named sections, each grouping a subset of labeled fields,
   - only one named section is relevant to the prompt,
   - the answer is the exact visible value text for the winning date or amount inside that named section,
   - the active scene variants keep the same section-local extremum semantics while changing the page grammar.
7. Generation guarantees:
   - every compared value in the queried section is unique,
   - the queried section is visibly labeled in the rendered document,
   - the winning value is unique by construction.

## 3) Prompt contract
1. Bundle: `documents_relation_v1`
2. `task_family_key`: `structured_document_sections`
3. `task_key`: `section_extremum_query`
4. `task_variant_key`: one of `earliest_date_in_section|latest_date_in_section|largest_amount_in_section|smallest_amount_in_section`
5. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/documents/relation.yaml`,
   - deterministic bundle selection from `prompts/documents/relation/documents_relation_v1.json`,
   - dynamic task-local JSON examples keyed by the active extremum variant.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact winning value text; prompt-facing evidence is the single winning value bbox.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` with exactly one box:
   - the bbox of the winning visible value inside the queried section.
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
   - `task_variant`
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
   - `comparison_kind`
   - `compared_field_ids`
   - `compared_field_labels`
   - `compared_field_value_bbox_ids`
   - `candidate_sort_values`
   - `winning_field_id`
   - `winning_field_label`
   - `winning_field_value`
   - `winning_value_bbox_id`
   - `winning_sort_value`
5. `witness_symbolic` stores the winning field id plus the single winning value bbox id.

## 5) Visual policy
1. Background and post-image noise use the merged documents-domain visual defaults from `configs/domains/documents/base.yaml`.
2. V1 section-local relation scenes stay layout-first and OCR-light:
   - short typed values,
   - stable labeled fields,
   - visible section headers,
   - no long paragraphs or handwriting.
3. The scene variants should feel visibly different:
   - `form_sheet` uses boxed field grids with grouped section chrome,
   - `invoice_sheet` uses labeled section blocks for dates and billing summary,
   - `receipt_sheet` uses narrow row groups with visible section headings.
4. Section reasoning should stay local:
   - the prompt names one section explicitly,
   - only values inside that section determine the answer,
   - evidence stays on the winning value itself rather than all compared values.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level, subject to the scene-compatibility rules for the active extremum variant.
3. Answers and evidence come from the same exact rendered value field.
4. No semantic auto-relaxation.
5. If a sampled section creates duplicate comparable values or no unique extremum winner, reject and resample instead of silently changing the query.
