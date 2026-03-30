# `task_documents_readout_field_value`

## 1) Identity
1. Domain: `documents`
2. Task group: `readout`
3. Task id: `task_documents_readout_field_value`
4. Objective: read the exact visible text for one queried field from a structured document.

## 2) Scene + task contract
1. Supported `task_variant` values:
   - `lookup_identifier`
   - `lookup_name`
   - `lookup_date`
   - `lookup_contact`
   - `lookup_amount`
2. Supported `scene_variant` values:
   - `form_sheet`
   - `invoice_sheet`
   - `receipt_sheet`
3. `answer_gt.type`: `string`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - one structured document page is shown on a light background,
   - every visible field has one label and one value,
   - the queried field is always one of the visible fields,
   - the answer is the exact rendered field value text,
   - the scene variants keep the same field-lookup semantics while changing the page grammar.
6. Generation guarantees:
   - every visible field value in the same document is unique,
   - the queried field label and value are both visible and traced,
   - the prompt names the specific requested field, not just a field category.

## 3) Prompt contract
1. Bundle: `documents_readout_v1`
2. `task_family_key`: `structured_document`
3. `task_key`: `field_lookup_query`
4. `task_variant_key`: one of `lookup_identifier|lookup_name|lookup_date|lookup_contact|lookup_amount`
5. Required slots:
   - task-family: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Slot source:
   - prompt config in `configs/domains/documents/readout.yaml`,
   - deterministic bundle selection from `prompts/documents/readout/documents_readout_v1.json`,
   - dynamic task-local JSON examples keyed by the active field-category variant.
7. Modes: `answer_only`, `answer_and_evidence`
8. Prompt-facing answer is the exact field text; prompt-facing evidence is the ordered two-box witness `[label_bbox, value_bbox]`.

## 4) Evidence + trace contract
1. Prompt-facing evidence is a `bbox_set` with exactly two boxes:
   - first the queried field label bbox,
   - then the queried field value bbox.
2. `scene_ir.entities` stores:
   - `document_page`
   - `document_title`
   - `document_field_box`
   - `document_field_label`
   - `document_field_value`
3. `render_map` includes:
   - `page_bbox_px`
   - `title_bbox_px`
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
   - `query_field_id`
   - `query_field_label`
   - `query_field_value`
   - `query_field_category`
   - `query_label_bbox_id`
   - `query_value_bbox_id`
5. `witness_symbolic` stores the queried field id plus the ordered label/value bbox id sequence.

## 5) Visual policy
1. Background and post-image noise use the merged documents-domain visual defaults from `configs/domains/documents/base.yaml`.
2. V1 document scenes stay layout-first and OCR-light:
   - short typed values,
   - stable labeled fields,
   - no long paragraphs or handwriting.
3. The scene variants should feel visibly different:
   - `form_sheet` uses boxed field grids,
   - `invoice_sheet` uses header blocks and summary fields,
   - `receipt_sheet` uses narrow labeled rows.
4. Text fit should prefer resampling/generation control over clipping; the visible field text itself is the answer source of truth.

## 6) Determinism + constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `task_variant` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same exact rendered field pair.
4. No semantic auto-relaxation.
5. If a sampled field-value set creates duplicate visible values or unusable query-field support, reject and resample instead of truncating or silently changing the query.
