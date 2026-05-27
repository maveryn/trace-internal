# Merge/Split Refactor Reference

Date: 2026-05-27

This is the action reference for task merge/split work. The decision record is
`plans/DOMAIN_MERGE_SPLIT_CANDIDATES.md`; this file restates only the current
high-confidence refactor candidates in a form that can be followed during
domain-local migration.

## Refactor Rules

1. Apply changes domain by domain.
2. Do not keep retired public task ids as disabled compatibility tasks; delete
   old registrations, docs, configs, prompts, tests, and task-review artifacts
   once their replacement is in place.
3. Preserve task-internal branches as `query_id`s on the merged task.
4. Do not rerun solve rate only because a public id changes. Regenerate task and
   scene review artifacts with the new ids. If a merged or split task has no
   valid current solve-rate mapping, leave solve-rate cells blank and note that
   calibration must be rerun.
5. If implementation reveals a hidden answer/evidence mismatch, stop and move
   that candidate back to explicit keep rather than forcing a merge.
6. After each domain pass, run the taxonomy/inventory checks and verify that no
   old public task ids remain in active docs, configs, prompts, imports, or
   generated review indexes.

## Count Summary

| Domain | Current Tasks | Merge Delta | Split Delta | Projected Tasks |
| --- | ---: | ---: | ---: | ---: |
| charts | 100 | -7 | 0 | 93 |
| games | 80 | 0 | 0 | 80 |
| geometry | 75 | -1 | 0 | 74 |
| graph | 39 | 0 | +1 | 40 |
| icons | 28 | -6 | 0 | 22 |
| illustrations | 24 | 0 | 0 | 24 |
| pages | 29 | -5 | +1 | 25 |
| physics | 20 | -2 | 0 | 18 |
| puzzles | 77 | 0 | 0 | 77 |
| three_d | 15 | -1 | 0 | 14 |
| **Total** | **487** | **-22** | **+2** | **467** |

## Merge Candidates

### charts

| Scene | Source Task Ids | Suggested Target Id | Delta | Refactor Note |
| --- | --- | --- | ---: | --- |
| `bar_3d` | `task_charts__bar_3d__axis_total_value`; `task_charts__bar_3d__axis_gap_value` | `task_charts__bar_3d__axis_aggregate_value` | -1 | Keep total/gap as `query_id`s over the same axis/category/series support. |
| `dashboard` | `task_charts__dashboard__source_rank_target_value`; `task_charts__dashboard__source_rank_difference_value` | `task_charts__dashboard__source_rank_metric_value` | -1 | Keep target lookup and difference as query branches over source-ranked cards. |
| `part_whole` | `task_charts__part_whole__order_share_sum_value`; `task_charts__part_whole__order_count_conversion_value`; `task_charts__part_whole__order_sector_angle_value` | `task_charts__part_whole__ordered_segment_value` | -2 | Preserve share-sum, share-to-count, and share-to-angle as query ids. |
| `region_map` | `task_charts__region_map__region_category_count`; `task_charts__region_map__region_value_count` | `task_charts__region_map__legend_predicate_region_count` | -1 | Categorical and numeric legend predicates become query-local predicate forms. |
| `pictogram` | `task_charts__pictogram__category_total_value`; `task_charts__pictogram__group_difference_value` | `task_charts__pictogram__group_arithmetic_value` | -1 | Keep group total and group difference as arithmetic query ids. |
| `violin` | `task_charts__violin__feature_extremum_label`; `task_charts__violin__shape_feature_label` | `task_charts__violin__distribution_feature_label` | -1 | Keep mode/support/bimodal distribution-shape branches as query ids. |

### geometry

| Scene | Source Task Ids | Suggested Target Id | Delta | Refactor Note |
| --- | --- | --- | ---: | --- |
| `area_partition` | `task_geometry__area_partition__parallelogram_area_partition_total_area_value`; `task_geometry__area_partition__triangle_area_partition_total_area_value` | `task_geometry__area_partition__total_area_value` | -1 | Triangle vs parallelogram becomes a scene-representation parameter. |

### icons

| Scene | Source Task Ids | Suggested Target Id | Delta | Refactor Note |
| --- | --- | --- | ---: | --- |
| `reference_canvas` | `task_icons__reference_canvas__attribute_match_count`; `task_icons__reference_canvas__size_relation_count` | `task_icons__reference_canvas__reference_predicate_count` | -1 | Attribute equality and size relation become predicate query ids. |
| `named_field` | `task_icons__named_field__shape_count`; `task_icons__named_field__shape_attribute_boolean_count` | `task_icons__named_field__shape_attribute_predicate_count` | -1 | Single-shape and shape+attribute predicates become query branches. |
| `named_field` | `task_icons__named_field__shape_pair_total_count`; `task_icons__named_field__shape_pair_difference_count` | `task_icons__named_field__shape_pair_arithmetic_count` | -1 | Keep total and difference as local arithmetic query ids. |
| `paired_canvas` | `task_icons__paired_canvas__panel_attribute_change_count`; `task_icons__paired_canvas__panel_movement_direction_count` | `task_icons__paired_canvas__pairwise_change_count` | -1 | Only pairwise right-panel change counts merge. Do not include exact-match or added/missing tasks. |
| `pattern_grid` | `task_icons__pattern_grid__color_pattern_violation_index`; `task_icons__pattern_grid__size_pattern_violation_index` | `task_icons__pattern_grid__attribute_pattern_violation_index` | -1 | Color vs size is the attribute axis for the same pattern violation. |
| `pair_grid` | `task_icons__pair_grid__pair_attribute_rule_count`; `task_icons__pair_grid__pair_geometric_transform_count` | `task_icons__pair_grid__pair_relation_count` | -1 | Attribute and geometric relation rules become query ids over icon pairs. |

### pages

| Scene | Source Task Ids | Suggested Target Id | Delta | Refactor Note |
| --- | --- | --- | ---: | --- |
| `concept_map` | `task_pages__concept_map__branch_item_count`; `task_pages__concept_map__filtered_node_count` | `task_pages__concept_map__node_filter_count` | -1 | Branch-child and marked-child counts become node-filter query ids. |
| `infographic` | `task_pages__infographic__filtered_metric_total_value`; `task_pages__infographic__column_profile_comparison_value`; `task_pages__infographic__metric_arithmetic_value` | `task_pages__infographic__metric_arithmetic_value` | -2 | Extend the existing metric arithmetic task to include filtered totals and filtered-section differences. |
| `infographic` | `task_pages__infographic__filtered_section_extremum_label`; `task_pages__infographic__section_ranked_total_label` | `task_pages__infographic__section_rank_label` | -1 | Filtered-section extremum and ranked-section total become section-rank query ids. |
| `schedule` | `task_pages__schedule__longer_than_reference_count`; `task_pages__schedule__overlap_count` | `task_pages__schedule__reference_interval_count` | -1 | Longer-than and overlap are relation predicates to one reference interval/block. |

### physics

| Scene | Source Task Ids | Suggested Target Id | Delta | Refactor Note |
| --- | --- | --- | ---: | --- |
| `lever` | `task_physics__lever__missing_weight_balance_value`; `task_physics__lever__side_torque_value` | `task_physics__lever__torque_balance_value` | -1 | Missing weight and side torque are algebraic query branches over torque balance. |
| `spring` | `task_physics__spring__spring_extension_difference`; `task_physics__spring__spring_missing_value` | `task_physics__spring__spring_relation_value` | -1 | Difference and missing-value branches share the same spring relation. |

### three_d

| Scene | Source Task Ids | Suggested Target Id | Delta | Refactor Note |
| --- | --- | --- | ---: | --- |
| `object_scene` | `task_three_d__object_scene__camera_distance_extremum_label`; `task_three_d__object_scene__height_extremum_label` | `task_three_d__object_scene__metric_extremum_label` | -1 | Camera distance and vertical height are metric-axis query branches. |

## Split Candidates

### graph

| Scene | Source Task Id | Suggested Target Ids | Delta | Refactor Note |
| --- | --- | --- | ---: | --- |
| `binary_tree` | `task_graph__binary_tree__tree_operation_label` | `task_graph__binary_tree__bst_path_operation_label`; `task_graph__binary_tree__heap_property_violation_label` | +1 | BST search/insert follows a path rule. Heap violation is a property scan. They should not share one public task id. |

### pages

| Scene | Source Task Id | Suggested Target Ids | Delta | Refactor Note |
| --- | --- | --- | ---: | --- |
| `hierarchy` | `task_pages__hierarchy__tree_count` | `task_pages__hierarchy__path_length_count`; `task_pages__hierarchy__subtree_descendant_count` | +1 | Path-length tracing and subtree-size counting are different hierarchy objectives. |

## Explicit Non-Merges

These pairs/groups were reviewed and should stay separate unless the task-unit
policy changes again.

### charts

- `task_charts__single_series__order_statistic_label` and
  `task_charts__single_series__order_statistic_value`: label selection vs
  numeric value answer role.
- `task_charts__sankey__node_side_total_value` and
  `task_charts__sankey__path_value`: node-side aggregation vs path/bottleneck
  tracing.
- `task_charts__scatter_cluster__cluster_feature_extremum_label` and
  `task_charts__scatter_cluster__cluster_trend_direction_label`:
  spread/separation extremum vs trend-direction classification.
- Heatmap cell extremum, conditional-axis extremum, and run-length extremum:
  different support/search patterns.

### graph

- `task_graph__binary_tree__node_relation_label` stays one task; direct-child
  and LCA are one binary-tree node-relation labeling family.
- `task_graph__graph_options__structure_match_label` stays one task; exact
  match and contained-subgraph match are one graph-option structural matching
  family.
- `task_graph__node_link__shortest_path_length` and
  `task_graph__node_link__longest_path_length` stay separate; shortest and
  longest path are different graph algorithms.
- `task_graph__flow_network__max_flow_value` and
  `task_graph__flow_network__min_cut_edge_count` stay separate; they have
  different optimization contracts.
- Node-color, edge-color, and cross-color edge counts stay separate because the
  primary witness kind differs.

### icons

- `task_icons__reference_canvas__anchor_position_count` stays separate from
  other reference-canvas counts because it adds an anchor object and spatial
  relation search.
- `task_icons__named_field__region_shape_count` and
  `task_icons__named_field__closer_to_reference_count` stay separate because
  marked-region membership and distance-to-reference comparisons change the
  visual search pattern.
- Mirror-grid symmetry counting and reflection-option matching stay separate
  because one counts symmetric cells and the other selects an option.
- `task_icons__paired_canvas__panel_exact_match_count` and
  `task_icons__paired_canvas__panel_difference_count` stay separate from
  pairwise transformation counts.

### illustrations

- No illustration merges are currently approved.
- Construction-site equipment, material-stack, and worker-attribute counts stay
  separate.
- Indoor-room container, surface, and side-relation counts stay separate.
- Market customer-at-shop and shop-attribute counts stay separate.
- Park person and equipment counts stay separate.
- `object_field__object_type_count`, `object_field__named_object_side_count`,
  and `object_field__visible_part_count` stay separate.
- `image_cutout_board__jigsaw_piece_order` and
  `image_cutout_board__rotated_tile_label` stay separate.

### pages

- `task_pages__schedule__maximum_non_overlapping_count` stays separate from
  schedule reference-interval counts.
- `task_pages__schema__field_role_count` and
  `task_pages__schema__relationship_count` stay separate.
- Process-flow actor handoff, filtered-node count, and condition-path endpoint
  label tasks stay separate.

### physics

- Collision direction choice and velocity component value stay separate because
  answer schema and target quantity differ.
- Electrostatic field direction, potential, and zero-field point tasks stay
  separate.
- Ray-optics bounce count and target-hit count stay separate.

### puzzles

- No puzzle merges or splits are currently approved.
- Arithmetic-constraint and operator-grid branches stay inside their existing
  public task ids.
- Music `pitch_interval_label`, `key_scale_label`, and `meter_rhythm_label`
  stay as coherent named-concept tasks.
- Cell-board path distance and reachability count stay separate.
- Maze exit label and reachable-exit count stay separate.
- Raven-matrix and voxel-cube families stay separate.

### three_d

- `task_three_d__object_scene__reference_nearest_label` stays separate from
  global metric extrema.
- `task_three_d__object_scene__occlusion_order_label` stays separate from
  metric extrema.
- Street and warehouse scene relation tasks stay separate for now.

## Per-Candidate Migration Checklist

For each merge or split:

1. Update public task registrations and taxonomy entries.
2. Move task-internal branches into explicit `query_id`s.
3. Update prompt bundles so scene/task/query layering still has no redundant
   text.
4. Update domain config entries and remove old task-specific config blocks.
5. Update docs and skills without mentioning the old task id history.
6. Regenerate task/scene review Excel artifacts with the new ids.
7. Delete stale task-review folders for removed ids.
8. Run registry/taxonomy/doc consistency checks.
