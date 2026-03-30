# `task_documents_layout_section_membership_label`

## 1) Identity
1. Domain: `documents`
2. Task group: `layout`
3. Task id: `task_documents_layout_section_membership_label`
4. Objective: locate which named section contains a queried field label, visible value, or matching label-value pair, and return the exact visible section title.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `section_of_field_label`
   - `section_of_field_value`
   - `section_of_label_value_pair`
2. Supported `scene_variant` values:
   - `form_sheet`
   - `invoice_sheet`
   - `receipt_sheet`
3. `answer_gt.type`: `string`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one structured document page is shown on a light background,
   - the page contains visible named sections with grouped labeled fields,
   - the prompt asks which section contains one queried field cue,
   - the answer is the exact visible section title, not a field value,
   - the active scene variants keep the same section-membership semantics while changing the page grammar.
6. Generation guarantees:
   - visible field values are unique within one page,
   - section titles are unique on the page,
   - the queried field/value cue maps to exactly one rendered section.

## 3) Prompt contract
1. Bundle: `documents_layout_v1`
2. `task_family_key`: `structured_document_sections`
3. `task_key`: `section_membership_query`
4. `task_variant_key`: one of `section_of_field_label|section_of_field_value|section_of_label_value_pair`
5. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/documents/layout.yaml`,
   - deterministic bundle selection from `prompts/documents/layout/documents_layout_v1.json`,
   - dynamic task-local JSON examples keyed by the active section-membership variant.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact section title shown in the document; prompt-facing evidence is the single matching section-header bbox.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` with exactly one box:
   - the bbox of the matching section header.
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
   - `query_field_id`
   - `query_field_label`
   - `query_field_value`
   - `query_section_id`
   - `query_section_label`
   - `query_section_label_bbox_id`
5. `witness_symbolic` stores the queried field id plus the single matching section-header bbox id.

## 5) Visual policy
1. Background and post-image noise use the merged documents-domain visual defaults from `configs/domains/documents/base.yaml`.
2. V1 layout document scenes stay layout-first and OCR-light:
   - short typed values,
   - stable labeled fields,
   - visible section headers,
   - no long paragraphs or handwriting.
3. The scene variants should feel visibly different:
   - `form_sheet` uses boxed field grids with grouped section chrome,
   - `invoice_sheet` uses labeled section blocks for parties, dates, and billing summary,
   - `receipt_sheet` uses narrow row groups with visible section headings.
4. Layout reasoning should stay local:
   - the prompt references a field cue that appears exactly once,
   - the answer is the containing section title,
   - evidence stays on the section header rather than widening to the whole page.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same exact rendered section header.
4. No semantic auto-relaxation.
5. If a sampled scene creates duplicate visible field values or an ambiguous field cue that could refer to multiple sections, reject and resample instead of silently changing the query.
