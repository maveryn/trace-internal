# `task_graph__automaton__nfa_accepted_string_label`

## Summary
1. Domain: `graph`
2. Scene id: `automaton`
3. Source package: `automaton`
4. Task id: `task_graph__automaton__nfa_accepted_string_label`
5. Objective: choose the candidate input string accepted by a nondeterministic finite automaton.

## Query IDs
1. `nfa_accepted_string_label`
2. Query ids are internal replay metadata; public sampling is at the task-id level.

## Answer And Annotation
1. Answer type: `string`.
2. Annotation type: `point_sequence`.
3. Annotation marks minimal pixel-space visual witnesses for the answer, not answer labels or non-witness annotations.
4. Count tasks require `answer_gt.value == len(annotation_gt.value)` unless the annotation schema is keyed or sequence based.

## Rendering Contract
1. The scene uses the graph-domain renderer for `automaton`.
2. Visual style, fonts, panel treatment, layout jitter, and post-render noise are non-semantic and must be recorded in trace metadata.
3. Annotation projection is computed after final layout and style placement.

## Prompt Contract
1. Prompt text comes from `prompts/graph/automaton/automaton_v0.json` and `configs/domains/graph/automaton.yaml`, not hardcoded user-facing text.
2. Answer-only mode emits `{"answer": ...}`.
3. Answer-and-annotation mode emits `{"annotation": ..., "answer": ...}` with annotation matching the schema above.

## Files
1. Implementation: `trace/tasks/graph/automaton/nfa_accepted_string_label.py`
2. Shared scene logic: `trace/tasks/graph/automaton/shared/string_acceptance.py`
3. Config: `configs/domains/graph/automaton.yaml`
4. Prompts: `prompts/graph/automaton/automaton_v0.json`
