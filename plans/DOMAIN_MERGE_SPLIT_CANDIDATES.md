# Domain Merge/Split Candidate Summary

Date: 2026-05-27

This is a read-only taxonomy audit summary for the current default-enabled
TRACE task surface.

Scope:

- Current default tasks: `487`
- Domains audited alphabetically: `charts`, `games`, `geometry`, `graph`,
  `icons`, `illustrations`, `pages`, `physics`, `puzzles`, `three_d`
- Audit basis: current registry/taxonomy plus sampled generated contracts
  (`answer_gt.type`, `evidence_gt.type`, and observed `query_id`s).
- Re-reviewed after the objective-family granularity clarification in
  `docs/core/TASK_UNIT_POLICY.md`; borderline graph and puzzle splits were
  narrowed to coherent named-concept task units rather than per-subroutine
  units.
- Re-tightened after a second sanity pass: this file lists high-confidence
  candidates only. Broad illustrated-scene object-count merges are kept
  separate unless the current task-unit policy explicitly makes object-role
  differences irrelevant.
- Third pass generated one default sample for each listed candidate task id and
  checked public answer/evidence envelope compatibility. No listed merge
  cluster failed that basic contract screen. This is still an audit candidate
  file, not an instruction to migrate all candidates without per-domain review.
- Fourth pass tightened the `icons/paired_canvas` merge. Exact-match and
  added/missing set-difference counts are no longer listed as merge candidates
  with pairwise transformation counts.
- Fifth pass tightened `charts/scatter_cluster`. Trend-direction labeling and
  spread/separation extrema share answer/evidence envelopes, but they use
  different cluster-feature objectives and should stay separate.

Decision rule:

- Use the hard task boundary in `docs/core/TASK_UNIT_POLICY.md`.
- Merge only when scene grammar, primary witness kind, visual search pattern,
  algorithmic/objective family, and answer/evidence role match.
- Split when one public task carries multiple objective families or materially
  different visual search contracts.
- Related tasks that fail one required merge condition are kept separate.

This file records candidates only. It does not rename tasks or change task
generation.

## Summary Table

| Domain | Current Tasks | Scenes | Merge Delta | Split Delta | Projected Tasks |
| --- | ---: | ---: | ---: | ---: | ---: |
| charts | 100 | 33 | -7 | 0 | 93 |
| games | 80 | 36 | 0 | 0 | 80 |
| geometry | 75 | 23 | -1 | 0 | 74 |
| graph | 39 | 8 | 0 | +1 | 40 |
| icons | 28 | 11 | -6 | 0 | 22 |
| illustrations | 24 | 14 | 0 | 0 | 24 |
| pages | 29 | 17 | -5 | +1 | 25 |
| physics | 20 | 12 | -2 | 0 | 18 |
| puzzles | 77 | 34 | 0 | 0 | 77 |
| three_d | 15 | 4 | -1 | 0 | 14 |
| **Total** | **487** | **182** | **-22** | **+2** | **467** |

## charts

Current: `100` tasks across `33` scenes.

### Merge Candidates

1. `bar_3d`
   - Merge:
     - `task_charts__bar_3d__axis_total_value`
     - `task_charts__bar_3d__axis_gap_value`
   - Reason: both aggregate the same 3D bar values over an axis/category/series
     support. A gap is a local arithmetic transform after the same support is
     located.
   - Delta: `-1`

2. `dashboard`
   - Merge:
     - `task_charts__dashboard__source_rank_target_value`
     - `task_charts__dashboard__source_rank_difference_value`
   - Reason: both use the same source-rank lookup contract over dashboard
     cards; difference is a local arithmetic transform over the located source
     metric(s).
   - Delta: `-1`

3. `part_whole`
   - Merge:
     - `task_charts__part_whole__order_share_sum_value`
     - `task_charts__part_whole__order_count_conversion_value`
     - `task_charts__part_whole__order_sector_angle_value`
   - Reason: all use ordered/positional pie/donut segment support and the same
     share table; count and angle are answer transforms from the same located
     sector/share support.
   - Delta: `-2`

4. `region_map`
   - Merge:
     - `task_charts__region_map__region_category_count`
     - `task_charts__region_map__region_value_count`
   - Reason: both count visible map regions satisfying a legend/predicate
     condition. Categorical vs numeric legend predicates are query-local
     predicate forms.
   - Delta: `-1`

5. `pictogram`
   - Merge:
     - `task_charts__pictogram__category_total_value`
     - `task_charts__pictogram__group_difference_value`
   - Reason: both locate repeated pictogram marks for one or two named groups
     and compute an integer aggregate. Difference is a local transform over
     group totals.
   - Delta: `-1`

6. `violin`
   - Merge:
     - `task_charts__violin__feature_extremum_label`
     - `task_charts__violin__shape_feature_label`
   - Reason: both select a violin/category by a whole-violin distribution-shape
     feature.
   - Delta: `-1`

### Split Candidates

None found.

### Explicit Keeps

- `single_series__order_statistic_label` and
  `single_series__order_statistic_value` stay separate because answer role
  differs: label selection vs numeric value.
- `sankey__node_side_total_value` and `sankey__path_value` stay separate
  because node-side aggregation and path/bottleneck tracing have different
  support witnesses.
- `scatter_cluster__cluster_feature_extremum_label` and
  `scatter_cluster__cluster_trend_direction_label` stay separate because
  spread/separation extremum selection and trend-direction classification use
  different cluster-feature objectives.
- `heatmap` tasks stay separate because cell extremum, conditional-axis
  extremum, and run-length extremum use different support/search patterns.

## games

Current: `80` tasks across `36` scenes.

### Merge Candidates

None found.

### Split Candidates

None found.

### Explicit Keeps

- Game scenes generally already follow one game renderer plus separate
  objective contracts.
- Same-scene tasks such as `chess` movement, capture, check attackers, and king
  escapes remain separate because they require different legal-move or threat
  objective families.
- `chess` and `chess_variant` stay separate because the scene grammar/rules
  differ even when both expose marked-piece destination counts.

## geometry

Current: `75` tasks across `23` scenes.

### Merge Candidates

1. `area_partition`
   - Merge:
     - `task_geometry__area_partition__parallelogram_area_partition_total_area_value`
     - `task_geometry__area_partition__triangle_area_partition_total_area_value`
   - Reason: both use a partitioned outer polygon, one labeled shaded region,
     and the same `total_area_from_shaded_partition` objective. Triangle vs
     parallelogram is a scene-representation parameter, not a distinct
     objective family.
   - Delta: `-1`

### Split Candidates

None found.

### Explicit Keeps

- `function_graph__extremum_count` and
  `function_graph__reference_line_crossing_count` stay separate: turning-point
  event counting and guide-line crossing counting are different event
  objectives.
- `graph_paper` area, perimeter, length, and angle extrema stay separate
  because the measured witness type differs.
- `solid_revolution` cone/cylinder/double-cone/frustum tasks stay separate
  because each has a different solid/formula family.

## graph

Current: `39` tasks across `8` scenes.

### Merge Candidates

None found.

### Split Candidates

1. `binary_tree`
   - Split:
     - `task_graph__binary_tree__tree_operation_label`
   - Proposed public tasks:
     - BST path operation (`bst_search_terminal_label`,
       `bst_insert_parent_label`)
     - heap property violation (`heap_property_violation_label`)
   - Reason: BST search/insert follows a path rule; heap violation is a
     property scan.
   - Delta: `+1`

### Explicit Keeps

- `binary_tree__node_relation_label` stays one task. Direct-child lookup and
  lowest-common-ancestor lookup are branches of one binary-tree node-relation
  labeling family over the same node witness contract.
- `graph_options__structure_match_label` stays one task. Exact graph match and
  contained-subgraph match are branches of one graph-option structural matching
  family over the same option-panel witness contract.
- `node_link__shortest_path_length` and `node_link__longest_path_length` stay
  separate because shortest path and longest path are different graph
  algorithms.
- `flow_network__max_flow_value` and `flow_network__min_cut_edge_count` stay
  separate because they have different optimization contracts.
- Node-color counts, edge-color counts, and cross-color edge counts stay
  separate because the primary witness kind differs.

## icons

Current: `28` tasks across `11` scenes.

### Merge Candidates

1. `reference_canvas`
   - Merge:
     - `task_icons__reference_canvas__attribute_match_count`
     - `task_icons__reference_canvas__size_relation_count`
   - Reason: both count Scene icons satisfying a predicate relative to the
     Reference icon. Attribute equality and size relation are query-local
     predicate forms over the same witness set.
   - Delta: `-1`

2. `named_field`
   - Merge:
     - `task_icons__named_field__shape_count`
     - `task_icons__named_field__shape_attribute_boolean_count`
   - Reason: both count named-field icons satisfying direct visual predicates.
     A single-shape predicate is a simpler branch of the same Boolean
     shape/attribute predicate-count family.
   - Delta: `-1`

3. `named_field`
   - Merge:
     - `task_icons__named_field__shape_pair_total_count`
     - `task_icons__named_field__shape_pair_difference_count`
   - Reason: both locate two operand icon groups and compute a local arithmetic
     transform over their counts.
   - Delta: `-1`

4. `paired_canvas`
   - Merge:
     - `task_icons__paired_canvas__panel_attribute_change_count`
     - `task_icons__paired_canvas__panel_movement_direction_count`
   - Reason: both use the same paired before/after canvas, align corresponding
     left/right icon instances, and count right-panel icons whose paired
     counterpart changed in a requested way.
   - Delta: `-1`

5. `pattern_grid`
   - Merge:
     - `task_icons__pattern_grid__color_pattern_violation_index`
     - `task_icons__pattern_grid__size_pattern_violation_index`
   - Reason: both locate the one violating slot in a repeated pattern grid.
     Color vs size is the semantic attribute axis.
   - Delta: `-1`

6. `pair_grid`
   - Merge:
     - `task_icons__pair_grid__pair_attribute_rule_count`
     - `task_icons__pair_grid__pair_geometric_transform_count`
   - Reason: both count icon pairs satisfying a relation rule between the two
     members of each pair.
   - Delta: `-1`

### Split Candidates

None found.

### Explicit Keeps

- `reference_canvas__anchor_position_count` stays separate from the other
  reference-canvas counts because it adds an Anchor object and a spatial
  relation search.
- `named_field__region_shape_count` and
  `named_field__closer_to_reference_count` stay separate because marked-region
  membership and distance-to-reference comparisons change the visual search
  pattern.
- `mirror_grid` symmetry counting and reflection-option matching stay separate
  because one is counting symmetric cells and the other is option selection.
- `paired_canvas__panel_exact_match_count` and
  `paired_canvas__panel_difference_count` stay separate from pairwise
  transformation counts for now. Exact matching is a set-match/equality
  predicate, and added/missing differences can move the evidence role between
  the left and right panels.

## illustrations

Current: `24` tasks across `14` scenes.

### Merge Candidates

None found under the conservative high-confidence rule.

### Split Candidates

None found.

### Explicit Keeps

- Construction-site equipment, material-stack, and worker-attribute counts stay
  separate for now because the target object-role inventories and predicate
  families differ.
- Indoor-room container, surface, and side-relation counts stay separate for
  now because support/container relations and side-of relations use different
  relation predicates.
- Market customer-at-shop and shop-attribute counts stay separate for now
  because the primary witness role changes between customers and shops.
- Park person and equipment counts stay separate for now because person
  activity/attribute predicates and equipment-type predicates are different
  object-role families.
- `object_field__object_type_count` and `object_field__named_object_side_count`
  stay separate because direct category counting and side-of-reference
  relation counting use different visual search patterns.
- `object_field__visible_part_count` stays separate because it counts object
  parts, not scene objects.
- `image_cutout_board__jigsaw_piece_order` and
  `image_cutout_board__rotated_tile_label` stay separate because ordered piece
  reconstruction and transformed tile option selection have different witness
  semantics.
- `difference_pair__object_difference_count` stays as one task because added
  and moved object counts share the same before/after difference-count family.

## pages

Current: `29` tasks across `17` scenes.

### Merge Candidates

1. `concept_map`
   - Merge:
     - `task_pages__concept_map__branch_item_count`
     - `task_pages__concept_map__filtered_node_count`
   - Reason: both count concept-map nodes satisfying a branch/filter predicate.
   - Delta: `-1`

2. `infographic`
   - Merge:
     - `task_pages__infographic__filtered_metric_total_value`
     - `task_pages__infographic__column_profile_comparison_value`
     - `task_pages__infographic__metric_arithmetic_value`
   - Reason: all compute integer arithmetic over visually located
     infographic metric/card totals.
   - Delta: `-2`

3. `infographic`
   - Merge:
     - `task_pages__infographic__filtered_section_extremum_label`
     - `task_pages__infographic__section_ranked_total_label`
   - Reason: both select a section label by comparing aggregate section totals.
   - Delta: `-1`

4. `schedule`
   - Merge:
     - `task_pages__schedule__longer_than_reference_count`
     - `task_pages__schedule__overlap_count`
   - Reason: both count schedule blocks satisfying a relation to a reference
     interval/block.
   - Delta: `-1`

### Split Candidates

1. `hierarchy`
   - Split:
     - `task_pages__hierarchy__tree_count`
   - Proposed public tasks:
     - path length between two nodes
     - subtree descendant count
   - Reason: path-length tracing and subtree-size counting are different tree
     objectives.
   - Delta: `+1`

### Explicit Keeps

- `schedule__maximum_non_overlapping_count` stays separate because interval
  scheduling/maximal independent selection is not a local reference-block
  predicate count.
- `schema__field_role_count` and `schema__relationship_count` stay separate
  because field rows and relationship lines are different primary witnesses.
- `process_flow__actor_handoff_count`, `filtered_node_count`, and
  `condition_path_endpoint_label` stay separate because handoff arrows, process
  nodes, and path endpoints have different witness/search contracts.

## physics

Current: `20` tasks across `12` scenes.

### Merge Candidates

1. `lever`
   - Merge:
     - `task_physics__lever__missing_weight_balance_value`
     - `task_physics__lever__side_torque_value`
   - Reason: both use the same lever geometry and torque-balance arithmetic;
     missing weight and side torque are local answer transforms.
   - Delta: `-1`

2. `spring`
   - Merge:
     - `task_physics__spring__spring_extension_difference`
     - `task_physics__spring__spring_missing_value`
   - Reason: both use the same spring-force/extension relation and differ only
     in which algebraic value is requested.
   - Delta: `-1`

### Split Candidates

None found.

### Explicit Keeps

- `collision__sticky_collision_direction_choice` and
  `collision__sticky_collision_velocity_component_value` stay separate because
  they have different answer schemas and different target quantities.
- `electrostatic_field` tasks stay separate because field direction, potential,
  and zero-field point are distinct physical objectives.
- `ray_optics__ray_bounce_count` and `ray_target_hit_count` stay separate
  because bounce points and target-hit points are different primary witnesses.

## puzzles

Current: `77` tasks across `34` scenes.

### Merge Candidates

None found.

### Split Candidates

None found after applying the clarified objective-family granularity rule.

### Explicit Keeps

- `arithmetic_constraint__arithmetic_constraint_value` stays one task.
  Consecutive-window sums, equal-side/line sums, and paired-cluster sum
  relations are same-family rule templates for a compact arithmetic-constraint
  missing-value diagram.
- `arithmetic_constraint__operator_grid_value` stays one task. Operation-table
  cells and row/column total clues are same-family grid/table missing-value
  branches over the same prompt-facing witness contract.
- `music_staff__pitch_interval_label` stays one task. Note naming, interval
  naming, same-pitch checks, and transposition checks are branches of one
  pitch/interval reading family over marked staff notes.
- `music_staff__key_scale_label` stays one task. Key signature identification,
  scale-degree function labeling, and scale validation are branches of one
  key/scale interpretation family over the same staff witness contract.
- `music_staff__meter_rhythm_label` stays one task. Time-signature reading,
  meter-type labeling, and articulation-mark reading are branches of one
  rhythm/notation-mark interpretation family in this domain.
- `cell_board__path_distance` and `cell_board__reachability_count` stay
  separate because ordered path length and reachable-region set counting are
  different witness/search patterns.
- `maze__exit_reachability_label` and `maze__reachable_exit_count` stay
  separate because label selection and count/set aggregation have different
  answer/evidence roles.
- `raven_matrix` tasks stay separate because the matrix families encode
  different abstract rule systems.
- `voxel_cube` projection, count, painted-face, and structure-change tasks stay
  separate because their support witnesses differ.

## three_d

Current: `15` tasks across `4` scenes.

### Merge Candidates

1. `object_scene`
   - Merge:
     - `task_three_d__object_scene__camera_distance_extremum_label`
     - `task_three_d__object_scene__height_extremum_label`
   - Reason: both select a lettered object by ranking candidates along one
     continuous 3D spatial metric. Camera distance and vertical height are
     metric-axis query parameters under the same extremum-selection family.
   - Delta: `-1`

### Split Candidates

None found.

### Explicit Keeps

- `object_scene__reference_nearest_label` stays separate because it introduces
  an object-reference distance relation rather than a global metric axis.
- `object_scene__occlusion_order_label` stays separate because projected
  overlap/depth ordering is a different witness contract from metric extrema.
- `street` and `warehouse` relation tasks stay separate for now because the
  road-arm/lane/path contracts are scene-specific and not just metric-axis
  extrema.
