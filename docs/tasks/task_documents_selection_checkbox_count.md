# `task_documents_selection_checkbox_count`

## 1) Identity
1. Domain: `documents`
2. Task group: `selection`
3. Task id: `task_documents_selection_checkbox_count`
4. Objective: find the named checkbox section in a structured document and count the checked or unchecked boxes inside that section.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `checked_box_count`
   - `unchecked_box_count`
2. Supported `scene_variant` values:
   - `form_sheet`
   - `invoice_sheet`
   - `receipt_sheet`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one structured document page is shown on a light background,
   - the page contains a small set of context fields plus multiple named checkbox sections,
   - only one named section is relevant to the prompt,
   - the answer is the number of checked or unchecked boxes in that named section,
   - the scene variants keep the same checkbox-count semantics while changing the page grammar.
6. Generation guarantees:
   - the queried section is visibly labeled in the rendered document,
   - exactly four checkboxes are shown in the queried section,
   - the answer is sampled over the feasible count support `0..4`,
   - prompt-facing evidence lists the counted checkbox boxes in top-to-bottom reading order,
   - zero-count answers emit an empty prompt-facing `bbox_set`.

## 3) Prompt contract
1. Bundle: `documents_selection_v1`
2. `task_family_key`: `structured_document_sections`
3. `task_key`: `checkbox_count_query`
4. `task_variant_key`: one of `checked_box_count|unchecked_box_count`
5. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/documents/selection.yaml`,
   - deterministic bundle selection from `prompts/documents/selection/documents_selection_v1.json`,
   - dynamic task-local JSON examples keyed by the active checkbox-count variant.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the integer count; prompt-facing evidence is the ordered checkbox-box witness list.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` containing one bbox for each counted checkbox:
   - checked boxes for `checked_box_count`,
   - unchecked boxes for `unchecked_box_count`.
   - if the answer is `0`, prompt-facing evidence is an empty `bbox_set`.
2. `scene_ir.entities` stores:
   - `document_page`
   - `document_title`
   - `document_section`
   - `document_section_label`
   - `document_field_box`
   - `document_field_label`
   - `document_field_value`
   - `document_checkbox`
   - `document_checkbox_label`
3. `render_map` includes:
   - `page_bbox_px`
   - `title_bbox_px`
   - `section_label_bboxes_px`
   - `section_box_bboxes_px`
   - `field_label_bboxes_px`
   - `field_value_bboxes_px`
   - `field_box_bboxes_px`
   - `checkbox_bboxes_px`
   - `checkbox_label_bboxes_px`
4. `execution_trace` records:
   - `task_variant`
   - `scene_variant`
   - `question_format`
   - `view_family`
   - `scene_title`
   - `question_text`
   - `field_count`
   - `checkbox_item_count`
   - `context_field_specs`
   - `checkbox_section_specs`
   - `query_section_id`
   - `query_section_label`
   - `answer_count`
   - `query_selection_strategy`
   - `evidence_checkbox_bbox_ids`
   - `target_checkbox_ids`
   - `target_checkbox_states`
5. `witness_symbolic` stores the queried section id plus the ordered counted-checkbox bbox ids.

## 5) Visual policy
1. Background and post-image noise use the merged documents-domain visual defaults from `configs/domains/documents/base.yaml`.
2. V1 checkbox-selection scenes stay layout-first and OCR-light:
   - short typed context fields,
   - visible section headers,
   - explicit checkbox squares with short labels,
   - no paragraphs or handwriting.
3. The scene variants should feel visibly different:
   - `form_sheet` uses a compact form header plus stacked preference sections,
   - `invoice_sheet` uses header fields plus side-by-side option sections,
   - `receipt_sheet` uses narrow stacked rows with checkbox groups below the header rows.
4. Checkbox evidence should stay local to the counted boxes themselves rather than widening to the whole section.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same exact checkbox state assignment.
4. No semantic auto-relaxation.
5. If a sampled checkbox section cannot realize the requested answer count, reject and resample instead of silently changing the target section or answer.
