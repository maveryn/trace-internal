# `task_pages__paired_forms__reconciliation_value`

## 1) Identity
1. Domain: `pages`
2. Task group: `cross_form`
3. Task id: `task_pages__paired_forms__reconciliation_value`
4. Objective: compare two matched document forms and compute one integer reconciliation value from visible item rows.

## 2) Scene + Task Contract
1. Supported `query_id` values:
   - `total_amount_delta`
   - `shortfall_minus_overage_value`
   - `sum_absolute_quantity_differences`
2. Supported `scene_variant` values:
   - `purchase_receipt_pair`
3. `answer_gt.type`: `integer`
4. `evidence_gt.type`: `bbox_set`
5. Scene contract:
   - the image shows two side-by-side business forms: a purchase order and a receiving slip,
   - item codes match across the forms,
   - the purchase order shows ordered quantity and unit value,
   - the receiving slip shows received quantity,
   - item codes are unique within one instance,
   - receiving-slip rows are shuffled relative to purchase-order rows so row matching must use item codes.
6. Generation guarantees:
   - `item_count` is always between `6` and `9`,
   - quantities are two-digit integers by default,
   - at least one item row has a shortfall,
   - at least one item row has an overage,
   - `3..5` item rows differ between forms,
   - the computed answer is positive and not equal to a visible quantity or unit value.

## 3) Prompt Contract
1. Bundle: `pages_cross_form_v0`
2. `scene_key`: `cross_form_reconciliation`
3. `task_key`: `reconciliation_value_query`
4. `query_key`: one of `total_amount_delta|shortfall_minus_overage_value|sum_absolute_quantity_differences`
5. Required slots:
   - scene: `object_description`
   - task: `question_text`
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. Modes: `answer_only`, `answer_and_evidence`
7. Prompt-facing answer is the computed integer.

## 4) Evidence + Trace Contract
1. Prompt-facing evidence is a `bbox_set` containing the full receiving-slip row box for each item whose received quantity differs from the matching purchase-order quantity.
2. `render_map` includes panel, title, header-value, cell-value, and row bboxes.
3. `execution_trace` records item specs, answer value, item-count and value ranges, shortfall item ids, overage item ids, mismatch item ids, row-level evidence bbox ids, and private supporting cell bbox ids for audit.
4. `witness_symbolic` stores the receiving row bbox ids; `projected_evidence` stores the final unordered bbox set used by the verifier.

## 5) Visual Policy
1. The scaffold is document-like: two separate forms with headers, titles, and matched line-item sections, not a plain row/column data-display table.
2. Text stays short and typed: item codes, short item names, two-digit quantities, and two-digit unit values.
3. Evidence stays on the mismatched receiving-slip rows, not on full forms, headers, or individual answer labels.

## 6) Determinism + Constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. `query_id` and `scene_variant` are sampled independently at the policy level.
3. Answers and evidence come from the same execution trace.
4. No semantic auto-relaxation.
