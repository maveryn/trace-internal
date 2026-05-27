# `task_graph__automaton__accepted_string_label`

## 1) Identity
1. Domain: `graph`
2. Task group: `relation`
3. Scene id: `automaton`
4. Task id: `task_graph__automaton__accepted_string_label`
5. Objective: choose the one labeled candidate input string accepted by a visible finite-state automaton.

## 2) Scene + Task Contract
1. Branch metadata: `query_id`
2. `query_id`: `dfa_accepted_string_label` or `nfa_accepted_string_label`
3. `answer_gt.type`: `string`
4. `evidence_gt.type`: `point_sequence`
5. Scene contract:
   - one directed state-transition diagram,
   - states are labeled `A`, `B`, `C`, ...,
   - a start arrow marks the start state,
   - accepting states use a double-ring glyph,
   - transition labels use binary symbols from `{0,1}`,
   - six labeled candidate input strings are shown below the diagram.
6. Query contract:
   - `dfa_accepted_string_label` asks for the option whose string is accepted by the deterministic automaton,
   - `nfa_accepted_string_label` asks for the option whose string has at least one accepting path,
   - exactly one displayed candidate string is accepted by construction.

## 3) Prompt Contract
1. Bundle: `graph_relation_v0`
2. `scene_key`: `automaton_state_relation`
3. `task_key`: `automaton_string_acceptance_label_query`
4. Modes: `answer_only`, `answer_and_evidence`
5. Answer-only JSON shape: `{"answer":"C"}`
6. Answer+evidence JSON shape: `{"evidence":[[150,250],[310,190],[480,230]],"answer":"C"}`
7. Prompt-facing evidence is one accepting state-center path for the chosen candidate string.

## 4) Evidence + Trace Contract
1. Prompt-facing evidence is the ordered `point_sequence` of state centers on one accepting path.
2. `answer_gt.value` equals `execution_trace.answer_option_label`.
3. `execution_trace.answer_input_string` records the accepted candidate string.
4. `execution_trace.candidate_strings_by_option` records every shown option.
5. `execution_trace.accepted_option_labels` must contain exactly the answer option.
6. `execution_trace.transition_function` records DFA/NFA transitions as symbol-to-target-label lists.
7. `scene_ir.entities` stores state geometry, transition geometry, accepting/start flags, and candidate-option boxes.

## 5) Visual Policy
1. Rendering uses the shared graph light-panel style and the existing automaton start/accepting glyphs.
2. State layout, whole-image transform, edge routing, and node color are visual variation only.
3. Candidate strings are drawn in a separate option panel below the state diagram.
4. Post-render graph noise follows the graph-domain coordinate-preserving noise policy.

## 6) Determinism + Constraints
1. Deterministic sampling/rendering from `instance_seed`.
2. Answers and evidence come from the same finalized transition table, candidate list, and rendered state centers.
3. No semantic auto-relaxation: failures do not weaken uniqueness, acceptance semantics, or transition-label visibility.

## 7) Complexity + Tests
1. Complexity components: `topology_reasoning`, `visual_scan`, `ambiguity`, `clutter`
2. Tests: `tests/test_graph_relation_automaton_string_acceptance_label_tasks.py`
