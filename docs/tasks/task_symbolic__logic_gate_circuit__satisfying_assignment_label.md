# `task_symbolic__logic_gate_circuit__satisfying_assignment_label`

## Public Taxonomy
1. Domain: `symbolic`
2. Scene id: `logic_gate_circuit`
3. Scene: `notation`
4. Task id: `task_symbolic__logic_gate_circuit__satisfying_assignment_label`

## Query Contract
1. Query metadata: `query_id`
2. Supported `query_id` values:
   - `assignment_outputs_one_label`
   - `assignment_outputs_zero_label`
3. Prompts ask which visible assignment option makes the source circuit's final `OUT` node evaluate to `1` or `0`.
4. Each instance shows one source circuit and exactly six assignment-option rows labeled `A..F`.
5. Inputs are named `x`, `y`, and `z`.

## Answer And Annotation
1. `answer_gt.type = option_letter`
2. `answer_gt.value` is the single correct assignment-option label.
3. `annotation_gt.type = keyed_bbox_map`
4. Annotation uses keys `source_circuit` and `selected_option`.
5. Distractor assignment rows, gate bboxes, and output-node points are not prompt-facing annotation.

## Trace Contract
1. `execution_trace.source_circuit` records the visible circuit grammar.
2. `execution_trace.candidates` records each option label, assignment values, computed output value, and correctness flag.
3. `execution_trace.logic_gate_metadata.correct_assignment` records the unique satisfying assignment.
4. `execution_trace.target_output_value` records the queried output value.
5. `render_map.item_bboxes_px` exposes the source-circuit bbox and candidate-row bboxes after final layout.

## Prompt Contract
1. Bundle: `symbolic_v0`
2. Scene key: `logic_gate_circuit`
3. Task key: `logic_gate_satisfying_assignment_label`
4. Query keys: `assignment_outputs_one_label` or `assignment_outputs_zero_label`
5. Prompt wording must refer to the visible source circuit and visual assignment rows, not prompt-only answer choices.

## Determinism + Constraints
1. Deterministic generation and rendering from `instance_seed`.
2. Unique-answer policy: the source circuit is constructed so exactly one shown assignment row has the queried output value.
3. Supported visible gates are `AND`, `OR`, `NOT`, `XOR`, `NAND`, and `NOR`.
