# Graph Scene-Package Migration Plan

## Scope

Graph currently has 61 active public tasks across 10 scenes. The migration is proceeding scene by scene. `pedigree_chart`, `phylogeny_tree`, and `automaton` are completed scene-package pilots.

## Target Layout

The scene-package target is:

- `trace/tasks/graph/<scene_id>/<objective_contract>.py`
- `trace/tasks/graph/<scene_id>/shared/` for scene-local helpers
- `configs/domains/graph/<scene_id>.yaml`
- `prompts/graph/<scene_id>/<bundle_id>.json`

One public task id maps to one Python task file. Retired or migrated legacy modules should be deleted, not aliased.

## Completed Pilots

### `pedigree_chart`

Old route:

- `trace/tasks/graph/relation/pedigree_chart_relation.py`
- `configs/domains/graph/relation.yaml`
- `prompts/graph/relation/graph_relation_v0.json`

New route:

- `trace/tasks/graph/pedigree_chart/relationship_label.py`
- `trace/tasks/graph/pedigree_chart/relatedness_coefficient_label.py`
- `trace/tasks/graph/pedigree_chart/shared/scene.py`
- `trace/tasks/graph/pedigree_chart/shared/task_common.py`
- `configs/domains/graph/pedigree_chart.yaml`
- `prompts/graph/pedigree_chart/pedigree_chart_v0.json`

Public ids stay unchanged:

- `task_graph__pedigree_chart__relationship_label`
- `task_graph__pedigree_chart__relatedness_coefficient_label`

### `phylogeny_tree`

Old route:

- `trace/tasks/graph/counting/phylogeny_tree_count.py`
- `trace/tasks/graph/relation/phylogeny_tree_relation.py`
- `trace/tasks/graph/shared/phylogeny_tree_scene.py`
- `configs/domains/graph/counting.yaml`
- `configs/domains/graph/relation.yaml`
- `prompts/graph/counting/graph_counting_v0.json`
- `prompts/graph/relation/graph_relation_v0.json`

New route:

- `trace/tasks/graph/phylogeny_tree/clade_leaf_count.py`
- `trace/tasks/graph/phylogeny_tree/sister_leaf_label.py`
- `trace/tasks/graph/phylogeny_tree/mrca_clade_membership_count.py`
- `trace/tasks/graph/phylogeny_tree/topology_outlier_label.py`
- `trace/tasks/graph/phylogeny_tree/shared/scene.py`
- `trace/tasks/graph/phylogeny_tree/shared/task_common.py`
- `configs/domains/graph/phylogeny_tree.yaml`
- `prompts/graph/phylogeny_tree/phylogeny_tree_v0.json`

Public ids stay unchanged:

- `task_graph__phylogeny_tree__clade_leaf_count`
- `task_graph__phylogeny_tree__mrca_clade_membership_count`
- `task_graph__phylogeny_tree__sister_leaf_label`
- `task_graph__phylogeny_tree__topology_outlier_label`

### `automaton`

Old route:

- `trace/tasks/graph/relation/automaton_state_simulation_label.py`
- `trace/tasks/graph/relation/automaton_string_acceptance_label.py`
- `trace/tasks/graph/relation/automaton_nondeterministic_state_count.py`
- `configs/domains/graph/relation.yaml`
- `prompts/graph/relation/graph_relation_v0.json`

New route:

- `trace/tasks/graph/automaton/state_after_input_label.py`
- `trace/tasks/graph/automaton/dfa_accepted_string_label.py`
- `trace/tasks/graph/automaton/nfa_accepted_string_label.py`
- `trace/tasks/graph/automaton/nondeterministic_state_count.py`
- `trace/tasks/graph/automaton/shared/state_simulation.py`
- `trace/tasks/graph/automaton/shared/string_acceptance.py`
- `configs/domains/graph/automaton.yaml`
- `prompts/graph/automaton/automaton_v0.json`

Public ids stay unchanged:

- `task_graph__automaton__dfa_accepted_string_label`
- `task_graph__automaton__nfa_accepted_string_label`
- `task_graph__automaton__nondeterministic_state_count`
- `task_graph__automaton__state_after_input_label`

## Follow-Up Waves

After the completed pilots pass review/tests, migrate graph scene families in this order:

1. `binary_tree`
2. `metro`
3. `pipe_network`
4. `flow_network`
5. `graph_options`
6. `adjacency`
7. `node_link`

Do not add `graph` to the scene-package enforcement allowlist until all graph scenes are migrated and legacy `scene_id` dependencies are gone for the domain.
