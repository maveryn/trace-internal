# Cross-Domain Program-Schema Reconciliation

This file lists canonical program signatures reused across scenes/domains.
Reuse here means taxonomy terminology has been merged; it does not merge public tasks across scenes.

- Canonical signatures: 138
- Reused in multiple scenes/domains: 59

| Program signature | Domains | Scene count | Definition | Do-not-merge boundary |
| --- | --- | ---: | --- | --- |
| `selection.direct_label` | charts | games | geometry | graph | icons | illustrations | misc | pages | physics | puzzles | 57 | Return a label selected from visible support by a stable query rule. | Do not merge with numeric or count answers. |
| `count.direct_cardinality` | charts | games | geometry | graph | icons | illustrations | misc | pages | physics | puzzles | three_d | 55 | Count visible units selected by a single role, attribute, or narrow predicate. | Do not merge with interval, path, counterfactual, or multi-step derived counts. |
| `formula.solve_unknown` | geometry | physics | 44 | Use a domain formula/rule schema to solve a numeric unknown. | Do not merge across formula schemas that require different intermediate geometric/physical quantities. |
| `selection.extreme_metric_label` | charts | games | geometry | icons | pages | physics | puzzles | 42 | Select the label of an item with an extreme metric. | Do not merge with ranked non-extreme or threshold-count tasks. |
| `selection.option_match` | charts | games | geometry | graph | icons | illustrations | misc | pages | puzzles | 41 | Choose an option panel/label matching a visual rule or transformation. | Do not merge with free string-label lookup tasks. |
| `count.single_attribute_membership` | charts | games | graph | icons | illustrations | pages | puzzles | three_d | 25 | Count visible entities selected by membership on one attribute axis. | Do not merge with multi-attribute Boolean, scoped, relation, arithmetic, or counterfactual count programs. |
| `count.one_bound_threshold` | charts | games | 23 | Count visible units satisfying a one-bound threshold predicate. | Do not merge with interval predicates or multi-condition predicates. |
| `numeric.derived_metric` | charts | geometry | pages | puzzles | 20 | Compute a derived metric such as ratio, rate, percent/share conversion, or angle conversion. | Do not merge with direct value lookup or simple sum. |
| `numeric.direct_or_derived_value` | charts | games | graph | icons | misc | pages | puzzles | 20 | Return a numeric value computed from selected visible support. | Do not merge with counting or label-selection tasks. |
| `numeric.difference_or_change` | charts | geometry | pages | physics | 18 | Compute a numeric difference/change between two selected supports. | Do not merge with aggregate totals or ratio/rate programs. |
| `count.scoped_attribute` | charts | geometry | icons | illustrations | pages | puzzles | three_d | 17 | Count visible entities after selecting a spatial or structural scope, then applying an attribute selector. | Do not merge with unscoped attribute counts or group-level predicate counts. |
| `numeric.aggregate_sum` | charts | geometry | pages | 17 | Sum or total values over a selected support set. | Do not merge with difference, ratio, or counterfactual programs. |
| `game.legal_or_safe_action_count` | games | 15 | Count visible candidate actions/moves satisfying a game legality, safety, or immediate-tactic rule. | Do not merge with static piece/object attribute counts or simulated board-effect counts. |
| `selection.ranked_item` | charts | games | icons | pages | 14 | Select a label/item by rank under a metric or order. | Do not merge with direct lookup or unordered predicate count. |
| `count.interval_predicate` | charts | pages | 10 | Count visible units satisfying a two-bound interval predicate. | Do not merge with one-bound threshold or categorical equality counts. |
| `count.multi_attribute_and` | games | graph | icons | pages | three_d | 10 | Count visible entities satisfying multiple attribute predicates conjunctively. | Do not merge with one-attribute membership, OR, XOR, exclusion, complement, scoped, or arithmetic counts. |
| `game.pattern_or_state_count` | games | 10 | Count game units satisfying a board/card/rule pattern or state predicate. | Do not merge with legal-action or simulated-effect counts. |
| `count.relation_attribute` | illustrations | pages | puzzles | three_d | 8 | Count entities selected by a visible relation to another entity, region, path, or support object. | Do not merge with unscoped attribute counts or metric-reference comparisons. |
| `lookup.role_bound_label` | pages | 8 | Read a role-bound label from a visible structured record. | Do not merge with ranked selection or option-image matching. |
| `numeric.summary_statistic` | charts | geometry | 6 | Apply a sampled summary/aggregate statistic such as sum, mean, median, or average over selected visible values. | Do not merge with tasks that add a different selection, filter, or nested aggregation stage. |
| `count.group_predicate` | charts | icons | 5 | Count groups whose visible aggregate/member predicate satisfies the query condition. | Do not merge with scoped object counts inside one group or direct entity counts. |
| `game.reference_or_route_relation_count` | games | 5 | Count game units selected by relation to a reference item, marked group, shot line, or route. | Do not merge with unreferenced attribute counts or legal-action counts. |
| `path.shortest_path_value` | games | graph | puzzles | 5 | Find an optimal shortest path or its length over an explicit graph-like scene. | Do not merge with reachability, longest path, route-following, or arbitrary ordered-path lookup. |
| `selection.rule_violation` | graph | icons | puzzles | 5 | Find the visible item/cell/index that violates a displayed or implicit rule. | Do not merge with completion or valid-option selection. |
| `simulation.discrete_state_update` | games | graph | misc | 5 | Simulate a discrete state-update system under visible rules. | Do not merge with static lookup or single-step counterfactual edits. |
| `topology.reachable_set` | games | graph | puzzles | 5 | Construct the set of reachable nodes/cells/regions under movement rules. | Do not merge with shortest path, longest path, or unconstrained direct counts. |
| `count.adjacency_relation` | charts | games | graph | three_d | 4 | Count units related to a reference by adjacency/neighborhood. | Do not merge with unscoped predicate counts. |
| `count.counterfactual` | icons | illustrations | puzzles | three_d | 4 | Apply a specified edit to the scene, then count objects selected from the edited state. | Do not merge with static attribute, scoped, relation, or arithmetic counts. |
| `count.entity` | illustrations | pages | puzzles | 4 | Count all visible candidate entities in the task support set. | Do not merge with attribute-filtered, scoped, relation, rule-derived, or counterfactual counts. |
| `count.pairwise_comparison` | charts | 4 | Count aligned items where one visible value/series/profile wins against another. | Do not merge with one-bound threshold counts against a fixed threshold/reference value. |
| `counterfactual.transform_then_answer` | charts | graph | puzzles | 4 | Apply a specified hypothetical edit before computing the answer. | Do not merge with direct readout/count tasks without a scene transform. |
| `numeric.extreme_metric_value` | charts | games | graph | 4 | Select an extreme item and return its numeric metric. | Do not merge with label-returning extremum tasks when answer schema differs. |
| `selection.nearest_label` | charts | games | 4 | Select the visible candidate nearest to a reference under a scene metric. | Do not merge with generic extremum unless the metric is explicitly distance-to-reference. |
| `selection.option_value_match` | games | puzzles | 4 | Compute a scene value, then select the visible option label whose option value matches it. | Do not merge with free-form numeric answers or option tasks that match only a visual pattern. |
| `count.composite_predicate` | games | pages | three_d | 3 | Count units satisfying a compound or attribute-binding predicate. | Do not merge with single-attribute counts if the program must bind multiple attributes or roles. |
| `count.intersection_or_crossing` | charts | geometry | 3 | Count geometric or chart-primitive intersections/crossings. | Do not merge with threshold or category counts. |
| `count.multi_attribute_exclusion` | icons | three_d | 3 | Count visible entities satisfying one attribute predicate while excluding another. | Do not merge with AND, OR, XOR, or complement counts. |
| `count.multi_attribute_or` | icons | three_d | 3 | Count visible entities satisfying an inclusive OR across multiple attribute predicates. | Do not merge with single-axis set membership or arithmetic sums of separate counts. |
| `game.simulated_effect_count` | games | 3 | Simulate a marked game action and count the resulting effect events. | Do not merge with static counts or legal-action counting. |
| `graph.cut_structure_count` | graph | 3 | Count graph structures whose removal or cut property changes connectivity/flow. | Do not merge with component counting, degree filters, or simple attribute counts. |
| `numeric.ranked_difference` | charts | 3 | Rank items by a metric, then compute a difference between selected ranked items. | Do not merge with direct extremum label selection. |
| `program.unclassified_direct` | pages | physics | 3 | Fallback direct-answer program; review manually if this appears often. | Do not merge without manual inspection. |
| `count.multi_attribute_xor` | icons | three_d | 2 | Count visible entities satisfying exactly one of multiple attribute predicates. | Do not merge with inclusive OR or exclusion/complement counts. |
| `count.reference_metric_relation` | icons | pages | 2 | Count entities whose numeric/metric attribute has a relation to a reference entity. | Do not merge with exact attribute-match reference counts. |
| `count.sequence_or_line_pattern` | charts | games | 2 | Count contiguous runs, lines, streaks, or pattern instances. | Do not merge with unordered object counts. |
| `geometry.relation_count` | geometry | 2 | Count visible geometric entities satisfying a geometric relation to a reference object. | Do not merge with raw object-type counts or formula-solving tasks. |
| `graph.component_count_or_size` | graph | 2 | Construct connected components before returning a component count or size. | Do not merge with local degree, path, cut-structure, or simple attribute-count programs. |
| `graph.minimum_spanning_tree` | graph | 2 | Construct or score a minimum spanning tree. | Do not merge with shortest path or flow/cut programs. |
| `graph.path_distance_filter_count` | graph | 2 | Count graph nodes at an exact path distance from a reference node. | Do not merge with simple route membership counts or shortest-path value tasks. |
| `graph.traversal_order` | graph | 2 | Follow a specified graph traversal order. | Do not merge BFS and DFS if the traversal rule is not a parameter inside one task. |
| `numeric.count_arithmetic` | icons | three_d | 2 | Combine two selector counts with a sampled arithmetic operation. | Do not merge with Boolean OR, direct single-selector counts, or counterfactual counts. |
| `numeric.ranked_value` | charts | 2 | Select an item by rank under a metric/order and return its numeric value. | Do not merge with label-returning ranked selection when answer schema differs. |
| `path.longest_path_value` | games | graph | 2 | Find an optimal longest path under the scene's constraints. | Do not merge with shortest path; the optimization objective differs. |
| `physics.direction_or_sign_rule` | physics | 2 | Use a physics sign/direction rule over the diagram. | Do not merge with numeric formula solving. |
| `probability.event_fraction` | misc | 2 | Compute a reduced fraction from a visible finite sample space. | Do not merge if the sample-space product/conditioning schema changes. |
| `puzzle.valid_candidate_count` | puzzles | 2 | Count candidates satisfying the puzzle's rule constraints or search rule. | Do not merge with static attribute counts or rule-violation counts. |
| `selection.adjacency_relation_label` | graph | icons | 2 | Select the single node satisfying a visible adjacency/predecessor/successor relation to a reference node. | Do not merge with adjacency-relation counts or path-derived label selection. |
| `sequence.longest_run_length` | charts | games | 2 | Find contiguous runs under a sequence rule and return the longest run length. | Do not merge with counting run instances or direct value lookup. |
| `sequence.threshold_crossing_label` | charts | 2 | Scan an ordered sequence and return the first label satisfying a threshold predicate. | Do not merge with unordered threshold counts or extremum selection. |
