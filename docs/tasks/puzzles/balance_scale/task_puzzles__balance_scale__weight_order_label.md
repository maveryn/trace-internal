# `task_puzzles__balance_scale__weight_order_label`

## Program Contract
`select_option(balance_comparison_grammar, target=lightest_to_heaviest_order, unknowns=A|B|C, panels=3); scene=balance_scale; scope=weight_order_label`

## 2) Scene + task contract
1. Entities/relations: Three pan-scale comparison panels over three unknown object labels, using direct-offset, shared-object-context, or aggregate comparison expressions, plus a query row with four visual order options.
2. Supported `query_id` values: `single`
3. `answer_gt.type`: `string`
4. Annotation schema: `bbox_set`
5. Alternate annotation forms: none
6. Annotation witness policy: bbox-set marks the three comparison-scale panels used to infer the order.
7. Overlap/touch policy: comparison-scale bboxes may cover full scale panels; do not annotate the selected option label.

## 3) Prompt contract
1. `prompt_bundle_id`: `puzzles_balance_scale_v1`
2. `scene_key`: `balance_scale`
3. `task_key`: `balance_scale_query`
4. Optional query-id prompt mapping: public `single` uses prompt query key `weight_order_label`.
5. Required slots:
   - answer-only mode: `answer_hint`, `json_example_answer_only`
   - answer+annotation mode: `annotation_hint`, `answer_hint`, `json_example`
6. JSON example validity rule: the example must use a bbox-set with three scale-panel boxes and an option-label answer.
7. Variant counts: 5 scene templates, 5 query templates, and 5 output templates per output mode.
8. Output modes: `answer_only`, `answer_and_annotation`

## 4) Determinism + constraints
1. Seed namespaces used: task-local object order/comparison namespaces plus shared balance scene/style/font/unit-size namespaces.
2. Unique-answer policy: generated comparison panels must force a unique lightest-to-heaviest order over the configured weight support.
3. Reject/resample conditions: identical pan expressions, redundant same numeric tokens on both sides, any panel count other than three, ambiguous order, non-four-option query row, or missing scale-panel bboxes raise and retry within `max_attempts`.
4. No-auto-relaxation guarantee: semantic constraints are not relaxed; generation retries rather than accepting ambiguous comparisons.

## 5) Tests
1. Determinism test: `tests/test_puzzles_balance_scale_tasks.py::test_weight_order_task_is_deterministic`
2. Answer/annotation consistency test: `tests/test_puzzles_balance_scale_tasks.py::test_weight_order_task_emits_public_contract`
3. Prompt metadata/placeholder test: covered by scene-package review gates and prompt-system tests.
4. Constraint-specific tests: `tests/test_puzzles_balance_scale_tasks.py::test_weight_order_comparisons_imply_one_option`
