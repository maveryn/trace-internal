# `task_misc__logic_gate_circuit__output_value_count`

## Public Taxonomy
1. Domain: `misc`
2. Scene id: `logic_gate_circuit`
3. Task group: `notation`
4. Task id: `task_misc__logic_gate_circuit__output_value_count`

## Query Contract
1. Query metadata: `query_id`
2. Supported `query_id` values:
   - `output_one_count`
   - `output_zero_count`
3. Prompts ask for the number of shown circuits whose final `OUT` node evaluates to `1` or `0`.
4. V1 answer support is `0..6`.
5. Each instance shows exactly six independent circuit panels.

## Answer And Annotation
1. `answer_gt.type = integer`
2. `answer_gt.value` is the number of circuits matching the queried output value.
3. `annotation_gt.type = point_set`
4. Annotation contains the center point of every final `OUT` node whose circuit matches the queried output value.
5. Gate bboxes, input labels, wire segments, and nonmatching output nodes are not prompt-facing annotation.

## Trace Contract
1. `execution_trace.circuits` records visible inputs, gates, and computed output value for each circuit.
2. `execution_trace.target_output_value` records the queried output value.
3. `execution_trace.annotation_output_ids` records the final output-node ids used for point projection.
4. `render_map.output_points_px` exposes final output-node centers after final layout.
5. `render_map.item_bboxes_px` exposes circuit, gate, input, and output-node boxes for audit tooling.

## Prompt Contract
1. Bundle: `misc_v0`
2. Scene key: `logic_gate_circuit`
3. Task key: `logic_gate_output_value_count`
4. Query keys: `output_one_count` or `output_zero_count`
5. Prompt wording must ask from visible gate labels, wires, and input values. It must not reveal hidden computed output values.

## Determinism + Constraints
1. Deterministic generation and rendering from `instance_seed`.
2. Unique-answer policy: the sampler constructs exactly the requested number of circuits with the queried output value.
3. Supported visible gates are `AND`, `OR`, `NOT`, `XOR`, `NAND`, and `NOR`.
4. Every visible input and every visible gate contributes to the final output.
