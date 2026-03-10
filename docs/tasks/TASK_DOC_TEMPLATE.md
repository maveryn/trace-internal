# `<task_id>` Task Doc Template

## 1) Identity
1. Domain:
2. Task group:
3. Task id:
4. Objective:

## 2) Scene + task contract
1. Entities/relations:
2. Supported `task_variant` values:
3. `answer_gt.type`:
4. Default `evidence_gt.type`:
5. Alternate evidence forms:
6. Overlap/touch policy (if applicable):

## 3) Prompt contract
1. `prompt_bundle_id`:
2. `task_family_key`:
3. `task_key`:
4. Optional task-variant prompt mapping (`task_variant_key` or slot-driven mapping):
5. Required slots:
   - answer-only mode: `json_output_contract_answer_only`, `answer_hint`, `json_example_answer_only`
   - answer+evidence mode: `json_output_contract`, `evidence_hint`, `answer_hint`, `json_example`
6. JSON example validity rule: every documented prompt JSON example must be a valid response for the active task/variant/output mode (keys, value types, and evidence cardinality/semantics).
7. Variant counts (task-family/task/task-variant/mode):
8. Output modes:
   - `answer_only`
   - `answer_and_evidence`

## 4) Determinism + constraints
1. Seed namespaces used:
2. Unique-answer policy:
3. Reject/resample conditions:
4. No-auto-relaxation guarantee:

## 5) Complexity + tests
1. Complexity definition/components:
2. Determinism test:
3. Answer/evidence consistency test:
4. Prompt metadata/placeholder test:
5. Constraint-specific tests:
