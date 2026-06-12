# Graph Task Setup

## Purpose
Define the active graph-domain public task surface and shared scene contracts.

For cross-domain rollups, use `docs/ACTIVE_TASK_INVENTORY.md`. This file is the graph-domain contract for task design and implementation.

## Current Scope
1. `domain = graph`
2. Active public graph tasks use taxonomy-v0 scene-package ids. Some pending
   scenes may still have legacy implementation package names internally, but
   the public surface is `domain -> scene_id -> task_id`.
3. Active public graph task count: `61`
4. Active public graph scene count: `10`

## Active Tasks

### `adjacency` (5)

1. `task_graph__adjacency__directed_pair_reciprocity_count`
1. `task_graph__adjacency__directed_strong_component_count`
1. `task_graph__adjacency__mst_weight`
1. `task_graph__adjacency__traversal_kth_label`
1. `task_graph__adjacency__undirected_component_count`

### `automaton` (4)

1. `task_graph__automaton__dfa_accepted_string_label`
1. `task_graph__automaton__nfa_accepted_string_label`
1. `task_graph__automaton__nondeterministic_state_count`
1. `task_graph__automaton__state_after_input_label`

### `binary_tree` (7)

1. `task_graph__binary_tree__bst_path_operation_label`
1. `task_graph__binary_tree__child_structure_node_count`
1. `task_graph__binary_tree__depth_level_node_count`
1. `task_graph__binary_tree__heap_property_violation_label`
1. `task_graph__binary_tree__local_relative_node_label`
1. `task_graph__binary_tree__lowest_common_ancestor_label`
1. `task_graph__binary_tree__traversal_kth_label`

### `flow_network` (2)

1. `task_graph__flow_network__max_flow_value`
1. `task_graph__flow_network__min_cut_edge_count`

### `graph_options` (2)

1. `task_graph__graph_options__contained_subgraph_label`
1. `task_graph__graph_options__same_structure_label`

### `metro` (4)

1. `task_graph__metro__exact_distance_station_count`
1. `task_graph__metro__shortest_path_length`
1. `task_graph__metro__station_membership_count`
1. `task_graph__metro__transfer_count`

### `node_link` (27)

1. `task_graph__node_link__articulation_point_count`
1. `task_graph__node_link__bridge_count`
1. `task_graph__node_link__common_related_node_count`
1. `task_graph__node_link__component_size_after_edge_edit`
1. `task_graph__node_link__cross_color_edge_count`
1. `task_graph__node_link__degree_after_removal_filter_count`
1. `task_graph__node_link__degree_extremum_value`
1. `task_graph__node_link__degree_value_filter_count`
1. `task_graph__node_link__edge_between_nodes_label`
1. `task_graph__node_link__edge_color_count`
1. `task_graph__node_link__edge_text_count`
1. `task_graph__node_link__hamiltonian_cycle_neighbor_label`
1. `task_graph__node_link__isolated_after_removal_count`
1. `task_graph__node_link__largest_chordless_cycle_size`
1. `task_graph__node_link__largest_component_size`
1. `task_graph__node_link__longest_path_length`
1. `task_graph__node_link__mst_weight`
1. `task_graph__node_link__named_node_degree_value`
1. `task_graph__node_link__node_color_count`
1. `task_graph__node_link__reachable_count`
1. `task_graph__node_link__reachable_count_after_edge_edit`
1. `task_graph__node_link__same_component_count`
1. `task_graph__node_link__shortest_path_first_edge_label`
1. `task_graph__node_link__shortest_path_length`
1. `task_graph__node_link__topological_position_value`
1. `task_graph__node_link__unique_cycle_size`
1. `task_graph__node_link__unique_related_node_label`

### `pedigree_chart` (2)

1. `task_graph__pedigree_chart__relatedness_coefficient_label`
1. `task_graph__pedigree_chart__relationship_label`

### `phylogeny_tree` (4)

1. `task_graph__phylogeny_tree__clade_leaf_count`
1. `task_graph__phylogeny_tree__mrca_clade_membership_count`
1. `task_graph__phylogeny_tree__sister_leaf_label`
1. `task_graph__phylogeny_tree__topology_outlier_label`

### `pipe_network` (4)

1. `task_graph__pipe_network__bridge_count`
1. `task_graph__pipe_network__pipe_exact_distance_count`
1. `task_graph__pipe_network__pipe_reachable_junction_count`
1. `task_graph__pipe_network__shortest_path_length`

## Scene Contract
1. `node_link` renders simple undirected or directed node-link diagrams with labeled nodes, optional edge labels/colors, graph layout variation, readable text, bounded content jitter, optional non-answer context text, and graph-domain post-render noise.
2. `pipe_network` renders labeled junctions connected by open or blocked cylindrical pipe segments; blocked-pipe markers are scene-native distractors.
3. `metro` renders colored route lines with labeled stations and route legends.
4. `automaton` renders directed state-transition diagrams with start arrows, accepting-state rings, visible transition-symbol labels, and optional candidate-string panels.
5. `flow_network` renders directed capacity networks with source/sink roles and visible capacities.
6. `graph_options` renders one reference or target graph above six visual option graphs; selected option panel bboxes are allowed annotation for these true visual-option tasks.
7. `binary_tree` renders one top-down ordered binary tree; left/right semantics come from horizontal placement in the rendered tree.
8. `adjacency` renders adjacency-list, adjacency-matrix, and weighted-adjacency-matrix panels for representation-level graph reasoning.
9. `pedigree_chart` renders family pedigree notation with sex-coded symbols, generation rows, spouse connectors, and descent/sibling connectors. Active tasks use the family graph for relationship and relatedness reasoning; disease-status and inheritance-model tasks are retired.
10. `phylogeny_tree` renders rooted cladograms with labeled terminal taxa and unlabeled internal branch points; child order, branch length, and drawing layout are non-semantic unless a task explicitly asks about a visible option panel.
11. All graph scenes use the approved shared font pool by role, readable foreground/background text contrast for answer-relevant text, scene-appropriate style variation, and annotation projection after final layout.
12. Graph-domain post-render noise probability resolves to `0.50` for current graph generation unless a scene has a documented task-specific exception.

## Contract-V0 Task Boundaries
1. Public task ids use `task_graph__<scene_id>__<objective_contract>` and are the sampling surface.
2. `query_id` is internal replay metadata and may vary only within one stable scene, answer schema, annotation schema, and program contract.
3. Former broad graph tasks have been split into narrower public tasks where branches had different program contracts, such as direct reachability vs reachability after an edge edit, local binary-tree relation vs lowest-common-ancestor, and edge-between lookup vs shortest-path first-edge lookup.
4. Retired pre-v0 public ids must not be registered, documented, configured, or kept as review folders.

## Annotation Rules
1. Node, junction, and station count tasks use `point_set`: unordered `[x,y]` pixel points at matching centers.
2. Path, traversal, and ordered-cycle tasks use `point_sequence` or `bbox_sequence` in traversal order.
3. Edge-count tasks with geometric edge annotation use `point_pair_set`; endpoint order is semantically unordered unless the task explicitly asks about directed arrows.
4. Visible text-label tasks use `bbox_set` around the visible text label that answers or witnesses the lookup.
5. Graph option-selection tasks use one option-panel `bbox_set` because the option image itself is the visual answer candidate.
6. Binary-tree count tasks use `bbox_set`; binary-tree role relations use `keyed_bbox_map` when witness roles matter.
7. Largest chordless-cycle size and Hamiltonian-cycle neighbor lookup use `point_sequence` around the relevant ordered cycle; unique-cycle size uses `point_set` because ordering is not needed for that simpler unicyclic witness.
8. Phylogeny clade count uses `point_set` over descendant taxon terminals; phylogeny sister/MRCA role relations use `keyed_bbox_map`; phylogeny option topology uses one selected option-panel `bbox_set`.
9. Pedigree relationship and relatedness tasks use role-bound `keyed_bbox_map` over the queried people and any needed family-path witnesses; rendered relationship/fraction options are answer choices, not prompt-facing annotation.
10. Automaton state simulation and string acceptance use `point_sequence` for the visited state centers in transition order.
11. Directed adjacency reciprocal-pair counts use `bbox_set` around both mirrored off-diagonal matrix cells for every counted unordered pair; zero-answer cases use an empty `bbox_set`.
12. Annotation and answers must come from the same execution trace; verifiers rely on metadata/projections, not pixels as source of truth.

## Implementation Notes
1. Internal source helpers may remain only for non-migrated scenes when they are private implementation routing and not exposed as retired public ids.
2. Migrated scene packages keep one public task per Python file under `trace/tasks/graph/<scene_id>/` and keep scene-local reusable code under `trace/tasks/graph/<scene_id>/shared/`.
3. Public wrapper outputs must rewrite `scene_ir.task_id`, `query_spec.task_id`, and `execution_trace.task_id` to the final public task id when wrappers are still used inside legacy packages.
4. Prompt text remains external to task code and must select annotation instructions from the same concrete `query_id` as the question text.
5. Review artifacts belong under `review/task-reviews/graph/<scene_id>/<task_id>/` for final public ids only.

## Maintenance Organization
1. Node-link tasks should resolve common non-semantic visual axes through `trace/tasks/graph/node_link/shared/sampling.py`: layout, label style, node shape, layout transform, edge routing, and node color. Tasks with semantic color queries or no routed-edge style axis should call the helper with the relevant optional axis disabled and keep the semantic/static axis local. Task modules should keep semantic query-axis resolution local unless at least two tasks share the same program contract.
2. Node-link render dataclasses and public render constants live in `trace/tasks/graph/shared/node_link_render_types.py`; `graph_scene.py` is only the compatibility facade. Renderer behavior is split across focused `node_link_*` modules for projection, panel/context handling, layout projection, geometry, edge routing/labels, node drawing, and orchestration.
3. Task-local support selection that only needs deterministic decoupling from already-balanced axes should use `trace/tasks/graph/shared/task_scaffolding.py`; do not reintroduce private `_node_count_selection_index` hash helpers or inline visual-axis resolution for new graph tasks.
4. Non-migrated graph scenes may still use legacy config loader boundaries. Do
   not add migrated scene overrides back into those broad files.
5. `adjacency` is migrated to review-candidate scene-package layout:
   implementation files live under `trace/tasks/graph/adjacency/`, config lives
   in `configs/domains/graph/adjacency.yaml`, and prompt templates live in
   `prompts/graph/adjacency/graph_adjacency_v1.json`.
6. `pedigree_chart` is migrated to scene-package layout: implementation files live under `trace/tasks/graph/pedigree_chart/`, config lives in `configs/domains/graph/pedigree_chart.yaml`, and prompt templates live in `prompts/graph/pedigree_chart/pedigree_chart_v0.json`.
7. `phylogeny_tree` is migrated to scene-package layout: implementation files live under `trace/tasks/graph/phylogeny_tree/`, config lives in `configs/domains/graph/phylogeny_tree.yaml`, and prompt templates live in `prompts/graph/phylogeny_tree/phylogeny_tree_v0.json`.
8. `automaton` is migrated to scene-package layout: implementation files live under `trace/tasks/graph/automaton/`, config lives in `configs/domains/graph/automaton.yaml`, and prompt templates live in `prompts/graph/automaton/automaton_v0.json`.
