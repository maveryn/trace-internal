# `task_graph__automaton__nondeterministic_state_count`

## Identity
1. Domain: `graph`
1. Scene id: `automaton`
1. Source package: `automaton`
1. Task id: `task_graph__automaton__nondeterministic_state_count`
1. Query id: `nondeterministic_state_count`

## Contract
The image shows a finite-state transition diagram with state labels, directed
transition arrows, visible transition labels, a start arrow, and optional
double-ring accepting states. The task asks how many states have
nondeterministic outgoing transitions.

A state counts as nondeterministic when either:

1. It has an outgoing epsilon transition, rendered with label `eps`.
1. It has two or more outgoing transitions with the same input label.

Missing outgoing transitions do not count as nondeterminism.

## Answer And Annotation
1. Answer type: `integer`.
1. Annotation type: `point_set`.
1. Annotation contains one pixel point at the center of each counted source
   state. For answer `0`, annotation is an empty point set.
1. Audit metadata also records the witness transition labels and their
   projected label boxes, but those boxes are not the verifier annotation.

## Sampling
1. State count: `4..6`.
1. Target answer support: `0..5`, capped by state count.
1. Nondeterminism is introduced only through `eps` transitions or duplicate
   outgoing labels.
1. Layout, transform, edge routing, node color, backgrounds, and post-image
   noise follow `configs/domains/graph/automaton.yaml` and graph-domain base defaults.

## Files
1. Implementation:
   `trace/tasks/graph/automaton/nondeterministic_state_count.py`
1. Shared scene logic:
   `trace/tasks/graph/automaton/shared/state_simulation.py`
1. Config: `configs/domains/graph/automaton.yaml`
1. Prompts: `prompts/graph/automaton/automaton_v0.json`
1. Tests:
   `tests/test_graph_relation_automaton_nondeterministic_state_count_tasks.py`
