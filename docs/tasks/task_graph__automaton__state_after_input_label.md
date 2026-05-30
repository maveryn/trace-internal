# `task_graph__automaton__state_after_input_label`

## 1) Identity
1. Domain: `graph`
2. Task group: `relation`
3. Scene id: `automaton`
4. Task id: `task_graph__automaton__state_after_input_label`
5. Objective: follow a short input string through a visible deterministic state-transition diagram and report the reached state label.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `final_state_label` or `transition_step_state_label`
3. `answer_gt.type`: `string`
4. `evidence_gt.type`: `point_sequence`
5. Scene contract:
   - one single-panel directed state-transition diagram,
   - states are labeled `A`, `B`, `C`, ...,
   - a start arrow marks the start state,
   - accepting states use a double-ring glyph as non-query visual automaton context,
   - transition symbols are visible edge labels from `{0,1}`,
   - default state count is `4..6` and default input length is `3..6`.
6. Query contract:
   - `final_state_label` asks for the state reached after reading the full input,
   - `transition_step_state_label` asks for the state reached after the first `k` input symbols,
   - the simulation path is deterministic by construction for the shown input.

## 3) Prompt Contract
1. Bundle: `graph_relation_v0`
2. `scene_key`: `automaton_state_relation`
3. `task_key`: `automaton_state_simulation_label_query`
4. Modes: `answer_only`, `answer_and_evidence`
5. Answer-only JSON shape: `{"answer":"C"}`
6. Answer+evidence JSON shape: `{"evidence":[[150,250],[310,190],[480,230]],"answer":"C"}`
7. Prompt-facing evidence is an ordered list of pixel-space state-center points, starting at the start state and ending at the answer state.

## 4) Evidence + Trace Contract
1. Prompt-facing evidence is the ordered `point_sequence` of visited state centers.
2. `answer_gt.value` equals `execution_trace.answer_state_label`.
3. `execution_trace.input_string` records the full input string.
4. `execution_trace.transition_step_count` records the number of consumed input symbols used for the answer.
5. `execution_trace.transition_function` records the deterministic transition table.
6. `execution_trace.used_transition_edges` and `used_transition_label_bboxes` record the visible transition labels followed by the simulation.
7. `scene_ir.entities` stores state geometry, transition geometry, transition labels, start-state flags, accepting-state flags, and answer-state flags.
8. `projected_evidence` includes the public `point_sequence` and supporting transition-label bboxes for auditing.

## 5) Visual Policy
1. Rendering uses the shared graph light-panel style and role-appropriate shared font pool from `configs/domains/graph/base.yaml`.
2. State layout, whole-image transform, edge routing, and node color are visual variation only.
3. Optional shared graph context text can appear as non-answer visual context, with state evidence projected after final layout jitter.
4. State labels, transition labels, and the start marker use readable text styles with recorded contrast metadata.
5. The start state is haloed and has an incoming start arrow; accepting states have an inner ring but are not queried in this task.
6. Post-render graph noise follows the graph-domain coordinate-preserving noise policy.

## 6) Determinism + Constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same finalized transition table and rendered state centers.
3. No semantic auto-relaxation: failures do not weaken determinism, path consistency, or transition-label visibility.

## 7) Complexity + Tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_relation_automaton_state_simulation_label_tasks.py`
