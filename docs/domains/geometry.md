# Geometry Task Setup

Geometry is migrated to scene-package layout: each public task id maps to `trace/tasks/geometry/<scene_id>/<objective_contract>.py`, scene-local helpers live under `<scene_id>/shared/`, and configs/prompts are scene keyed.

Geometry follows the public taxonomy `domain -> scene_id -> task_id`. Most active geometry code still uses legacy scene-package implementation routing while the scene-package migration is in progress; `angle_relations`, `area_partition`, `bearing_route`, `circle_centerline_overlap`, `circle_pair_tangents`, `circle_polygon_composite`, and `circle_theorem` are review-candidate scenes under the current scene-package gate, and human acceptance is still required after each scene passes source audit, tests, fresh review artifacts, and browser review. Sampling is over public task ids, with narrow `query_id` branches kept inside a task only when they preserve the same program contract.

Scene-package migration tracking lives in `review/taxonomy-audit/scene_package_migration/geometry.md`. Do not add `geometry` to the migrated-domain enforcement allowlist until all geometry scenes, configs, prompts, tests, and review artifacts have moved off legacy scene-package routing.

## Public Surface

- Active geometry tasks: `192`
- Active geometry scenes: `46`

| Scene package | Public task count | Primary scene ids |
|---|---:|---|
| `analytical` | 6 | `function_panels` |
| `circle` | 15 | `circle_theorem` |
| `comparison` | 4 | `graph_paper` |
| `coordinate` | 14 | `coordinate_composite`, `coordinate_panels`, `coordinate_plane` |
| `counting` | 5 | `graph_paper` |
| `graphing` | 4 | `function_graph` |
| `measurement` | 140 | `angle_relations`, `area_partition`, `bearing_route`, `circle_centerline_overlap`, `circle_pair_tangents`, `circle_polygon_composite`, `composite_shape`, `concentric_chord`, `cone_net`, `container_volume_transfer`, `cuboid_views`, `cylinder_wrap`, `graph_paper`, `incircle_tangents`, `marked_polygon_equation`, `measuring_tools`, `paper_fold`, `parallel_segment_proportion`, `polygon_angle_chase`, `pythagorean_dissection`, `pythagorean_tree`, `rectangular_solid`, `regular_polygon_decomposition`, `right_triangle_altitude_theorem`, `sector`, `similar_figure_measure_transfer`, `solid_cross_section`, `solid_formula`, `solid_revolution`, `special_quadrilateral`, `split_triangle_angle_chase`, `split_triangle_trig_chain`, `survey_traverse`, `tangent_packing`, `trapezoid_extension`, `triangle_congruence_correspondence`, `triangle_relations`, `volume_equivalence_conversion`, `wire_shape_conversion` |
| `similarity` | 2 | `shape_gallery` |
| `transformation` | 3 | `shape_gallery` |

## Contract Notes

- Annotation must be minimal pixel-space witnesses, not answer labels or private symbolic coordinates.
- Use keyed annotation when witness roles matter, such as source vs target points, input vs output dimensions, or distinct region roles.
- Numeric labels, angle marks, construction marks, formulas, and graph coordinates are visible annotations plus verifier metadata unless the task contract explicitly asks the model to ground that visible item.
- For count tasks, an empty public annotation array is valid when the answer is `0`; task docs should say this explicitly so zero-count instances are not mistaken for missing annotation.
- Geometry readout text uses the shared readout font pool and thin, chart-like strokes for legibility without over-bold labels.
- Query/support probability metadata should be built in the owning public task file or with repo-global query-selection helpers. Scene-shared helpers should receive semantic arguments, not public task ids or query ids.
- Renderer point math, pixel geometry, annotation payload normalization, and trace metadata serialization should use `trace/tasks/geometry/shared/vector2d.py`, `trace/tasks/geometry/shared/measurement_rendering.py`, `trace/tasks/geometry/shared/annotation_values.py`, and `trace/tasks/geometry/shared/metadata_serialization.py` for common point serialization, vector operations, bbox padding/clamping, clamped bbox unions, public annotation artifacts, and JSON-ready metadata conversion instead of task-local copies.
- Geometry measurement question wording belongs in prompt bundles or query templates. Task modules should pass structured slots such as labels, segment names, and object descriptions instead of constructing full user-facing question text.
- Renderers must project annotation after final layout, jitter, panel placement, and style selection.
- Compact single-object or coherent single-diagram scenes may use the shared `single_object_scene_rotation` rendering axis. It samples a non-semantic whole-diagram rotation before drawing/annotation projection, keeps text upright, preserves existing layout jitter, and records transform metadata in `render_spec.single_object_scene_rotation`. Do not apply this axis to graph-paper/coordinate scenes, paired-figure transfer scenes, option-panel scenes, measuring-tool scenes, orthographic/panel scenes, or shape/volume conversion scenes where absolute orientation or multiple separated objects are part of the scene grammar.
- Geometry technical-diagram styles use one explicit scene profile. `coordinate_grid` is reserved for scenes where axes, graph-paper scale, or coordinate-grid measurement is part of the reasoning (`coordinate_composite`, `coordinate_panels`, `coordinate_plane`, `function_graph`, `function_panels`, and `graph_paper`). All other geometry scenes should use `analytical_diagram`, which samples non-grid treatments only. Both profiles expose 12 treatments: 9 light and 3 dark. Do not mix graph and non-graph treatments within one scene unless the scene contract is explicitly changed and documented.

## Scenes And Tasks

### `angle_relations` (3)

- `task_geometry__angle_relations__algebraic_angle_value`: query_id=triangle_single_extension_expression | triangle_double_extension_expression; answer=integer_value; annotation=keyed_point_map
- `task_geometry__angle_relations__parallel_supplement_angle`: query_id=parallel_supplement_angle; answer=integer_value; annotation=keyed_point_map
- `task_geometry__angle_relations__triangle_exterior_angle`: query_id=triangle_exterior_angle; answer=integer_value; annotation=keyed_point_map

Scene-package status: source-audited review candidate; prompt bundle schema `v1`.

### `area_partition` (1)

- `task_geometry__area_partition__total_area_value`: query_id=total_area_from_shaded_partition; answer=integer_value; annotation=keyed_bbox_map
  - Scene-package status: objective-ownership complete; prompt bundle schema `v1`.

### `bearing_route` (2)

- `task_geometry__bearing_route__endpoint_position_label`: query_id=endpoint_position_label; answer=option_letter; annotation=keyed_point_map
- `task_geometry__bearing_route__final_bearing_value`: query_id=final_bearing_value; answer=integer_value; annotation=keyed_point_map

### `circle_pair_tangents` (2)

- `task_geometry__circle_pair_tangents__center_distance_value`: query_id=external_common_tangent_center_distance; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_pair_tangents__common_tangent_length_value`: query_id=external_common_tangent_length; answer=integer_value; annotation=keyed_point_map

### `circle_centerline_overlap` (1)

- `task_geometry__circle_centerline_overlap__segment_length_value`: query_id=center_distance_from_overlap, boundary_segment_from_overlap; answer=integer_value; annotation=keyed_point_map

### `circle_polygon_composite` (2)

- `task_geometry__circle_polygon_composite__square_circle_tangent_angle_value`: query_id=square_incircle_tangent_angle, square_semicircle_tangent_angle; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_polygon_composite__tangential_quadrilateral_side_length_value`: query_id=missing_side_from_tangent_quadrilateral; answer=integer_value; annotation=keyed_point_map

### `circle_theorem` (15)

- `task_geometry__circle_theorem__chord_length_from_radius_central_angle_value`: query_id=chord_length_from_radius_and_central_angle; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__circle_theorem__chord_length_from_radius_inscribed_angle_value`: query_id=chord_length_from_radius_and_inscribed_angle; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__circle_theorem__cyclic_quadrilateral_angle_value`: query_id=opposite_angle_supplement, exterior_angle_from_opposite_interior; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_theorem__diameter_perpendicular_chord_length_value`: query_id=diameter_perpendicular_chord_length; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_theorem__external_secant_angle_value`: query_id=external_two_secants_angle_from_arcs; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_theorem__inscribed_angle_value_central_angle_from_inscribed`: query_id=central_angle_from_inscribed; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_theorem__inscribed_angle_value_inscribed_angle_from_arc`: query_id=inscribed_angle_from_arc; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_theorem__inscribed_angle_value_inscribed_angle_from_central`: query_id=inscribed_angle_from_central; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_theorem__intersecting_chords_arc_measure_value`: query_id=intersecting_chords_arc_measure; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_theorem__multi_step_angle_value`: query_id=multi_step_angle_value; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_theorem__secant_secant_length_value`: query_id=secant_secant_length, secant_secant_variable_segment_length; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_theorem__tangent_chord_angle_value_tangent_chord_angle_from_arc`: query_id=tangent_chord_angle_from_arc; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_theorem__tangent_chord_angle_value_tangent_chord_angle_from_inscribed`: query_id=tangent_chord_angle_from_inscribed; answer=integer_value; annotation=keyed_point_map
- `task_geometry__circle_theorem__tangent_radius_right_triangle_length_value`: query_id=radius_from_external_distance_and_angle, tangent_length_from_radius_and_external_distance; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__circle_theorem__tangent_secant_length_value`: query_id=tangent_secant_length; answer=integer_value; annotation=keyed_point_map

### `composite_shape` (13)

- `task_geometry__composite_shape__composite_area_value`: query_id=l_shape_area, rectangle_minus_triangle_area; answer=integer_value; annotation=keyed_bbox_map
- `task_geometry__composite_shape__house_outline_perimeter`: query_id=house_outline_perimeter; answer=integer_value; annotation=keyed_bbox_map
- `task_geometry__composite_shape__missing_width_from_semicircle_cap_area`: query_id=missing_width_from_semicircle_cap_area; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__composite_shape__missing_width_from_semicircle_cutout_area`: query_id=missing_width_from_semicircle_cutout_area; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__composite_shape__rectangle_quarter_sector_cutout_area`: query_id=rectangle_quarter_sector_cutout_area; answer=decimal_value_1dp; annotation=keyed_bbox_map
- `task_geometry__composite_shape__rectangle_quarter_sector_cutout_perimeter`: query_id=rectangle_quarter_sector_cutout_perimeter; answer=decimal_value_1dp; annotation=keyed_bbox_map
- `task_geometry__composite_shape__rectangle_semicircle_cap_area`: query_id=rectangle_semicircle_cap_area; answer=decimal_value_1dp; annotation=keyed_bbox_map
- `task_geometry__composite_shape__rectangle_semicircle_cap_perimeter`: query_id=rectangle_semicircle_cap_perimeter; answer=decimal_value_1dp; annotation=keyed_bbox_map
- `task_geometry__composite_shape__rectangle_semicircle_cutout_area`: query_id=rectangle_semicircle_cutout_area; answer=decimal_value_1dp; annotation=keyed_bbox_map
- `task_geometry__composite_shape__rectangle_semicircle_cutout_perimeter`: query_id=rectangle_semicircle_cutout_perimeter; answer=decimal_value_1dp; annotation=keyed_bbox_map
- `task_geometry__composite_shape__sector_angle_from_arc_length`: query_id=sector_angle_from_arc_length; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__composite_shape__sector_angle_from_area`: query_id=sector_angle_from_area; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__composite_shape__tabbed_rectilinear_perimeter`: query_id=tabbed_rectilinear_perimeter; answer=integer_value; annotation=keyed_bbox_map

### `concentric_chord` (2)

- `task_geometry__concentric_chord__chord_length_from_radii`: query_id=chord_length_from_radii; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__concentric_chord__inner_radius_from_chord`: query_id=inner_radius_from_chord; answer=decimal_value_1dp; annotation=keyed_point_map

### `cone_net` (2)

- `task_geometry__cone_net__base_radius_from_sector_angle`: query_id=base_radius_from_sector_angle; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__cone_net__height_from_sector_angle`: query_id=height_from_sector_angle; answer=decimal_value_1dp; annotation=keyed_point_map

### `container_volume_transfer` (4)

- `task_geometry__container_volume_transfer__fill_count_value`: query_id=cone_to_cylinder_fill_count, cylinder_to_cuboid_fill_count; answer=integer_value; annotation=keyed_bbox_map
- `task_geometry__container_volume_transfer__resulting_height_value`: query_id=cone_pours_to_cylinder_height, cylinder_pours_to_cuboid_height; answer=number_value; annotation=keyed_bbox_map
- `task_geometry__container_volume_transfer__target_capacity_value`: query_id=target_capacity_from_source_and_count; answer=integer_value; annotation=keyed_bbox_map
- `task_geometry__container_volume_transfer__transferred_volume_value`: query_id=repeated_cone_pours_total_volume, repeated_cylinder_pours_total_volume; answer=integer_value; annotation=keyed_bbox_map

### `coordinate_composite` (1)

- `task_geometry__coordinate_composite__intersection_point_count`: query_id=line_circle_intersection_count, circle_circle_intersection_count, line_polygon_intersection_count, circle_polygon_intersection_count, mixed_object_intersection_count; answer=integer_count; annotation=point_set

### `coordinate_panels` (1)

- `task_geometry__coordinate_panels__quadrilateral_shape_match_label`: query_id=parallelogram_shape_match_label, rectangle_shape_match_label, rhombus_shape_match_label, square_shape_match_label; answer=option_letter; annotation=bbox_set

### `coordinate_plane` (12)

- `task_geometry__coordinate_plane__collinear_point_count`: query_id=collinear_count; answer=integer_count; annotation=point_set
- `task_geometry__coordinate_plane__locus_panel_match_label`: query_id=circle_inequality_panel_match, horizontal_halfplane_panel_match, two_inequality_panel_match, vertical_strip_panel_match; answer=option_letter; annotation=bbox_set
- `task_geometry__coordinate_plane__locus_point_label`: query_id=annulus_region_point, circle_region_point, half_plane_intersection_region_point, vertical_strip_region_point; answer=option_letter; annotation=point_set
- `task_geometry__coordinate_plane__missing_endpoint_label`: query_id=missing_endpoint_from_midpoint, missing_startpoint_from_midpoint; answer=option_letter; annotation=point_set
- `task_geometry__coordinate_plane__point_in_polygon_count`: query_id=point_in_shape_count; answer=integer_count; annotation=point_set
- `task_geometry__coordinate_plane__quadrilateral_completion_label`: query_id=parallelogram_completion_label, rectangle_completion_label, rhombus_completion_label, square_completion_label; answer=option_letter; annotation=point_set
- `task_geometry__coordinate_plane__reflected_point_label`: query_id=reflect_over_horizontal_line, reflect_over_vertical_line; answer=option_letter; annotation=point_set
- `task_geometry__coordinate_plane__rotated_point_label`: query_id=rotate_90_about_marked_center; answer=option_letter; annotation=point_set
- `task_geometry__coordinate_plane__same_quadrant_point_count`: query_id=same_quadrant_count; answer=integer_count; annotation=point_set
- `task_geometry__coordinate_plane__section_point_label`: query_id=one_third_from_p_to_q, two_thirds_from_p_to_q; answer=option_letter; annotation=point_set
- `task_geometry__coordinate_plane__segment_relation_count`: query_id=parallel_count, perpendicular_count; answer=integer_count; annotation=point_set
- `task_geometry__coordinate_plane__translated_point_label`: query_id=translate_by_reference_vector, translate_point; answer=option_letter; annotation=point_set

### `cuboid_views` (1)

- `task_geometry__cuboid_views__cuboid_projection_surface_area_value`: query_id=surface_area_from_orthographic_views; answer=decimal_value_1dp; annotation=keyed_bbox_map

### `cylinder_wrap` (2)

- `task_geometry__cylinder_wrap__surface_path_length_value`: query_id=surface_path_length_value; answer=decimal_value_1dp; annotation=keyed_bbox_map
- `task_geometry__cylinder_wrap__wrapped_mark_position_label`: query_id=wrapped_mark_position_label; answer=option_letter; annotation=keyed_point_map

### `function_graph` (4)

- `task_geometry__function_graph__average_rate_value`: query_id=average_rate_between_marked_points; answer=decimal_value_1dp; annotation=point_set
- `task_geometry__function_graph__extremum_count_local_extremum_count`: query_id=local_extremum_count; answer=integer_count; annotation=point_set
- `task_geometry__function_graph__extremum_count_turning_point_count`: query_id=turning_point_count; answer=integer_count; annotation=point_set
- `task_geometry__function_graph__reference_line_crossing_count`: query_id=reference_line_crossing_count; answer=integer_count; annotation=point_set

### `function_panels` (6)

- `task_geometry__function_panels__function_status_label`: query_id=function_status_label; answer=option_letter; annotation=bbox_set
- `task_geometry__function_panels__intersection_property_label`: query_id=circle_circle_two_intersections_label, line_circle_tangent_label, line_circle_two_intersections_label; answer=option_letter; annotation=bbox_set
- `task_geometry__function_panels__one_to_one_status_label`: query_id=one_to_one_status_label; answer=option_letter; annotation=bbox_set
- `task_geometry__function_panels__range_match_label`: query_id=range_match_label; answer=option_letter; annotation=bbox_set
- `task_geometry__function_panels__sign_interval_label`: query_id=sign_interval_negative_label, sign_interval_positive_label; answer=option_letter; annotation=bbox_set
- `task_geometry__function_panels__x_axis_symmetry_label`: query_id=x_axis_symmetry_label; answer=option_letter; annotation=bbox_set

### `graph_paper` (15)

- `task_geometry__graph_paper__angle_extremum_label`: query_id=angle_extremum; answer=option_letter; annotation=point_set
- `task_geometry__graph_paper__angle_type_count`: query_id=angle_type_count; answer=integer_count; annotation=bbox_set
- `task_geometry__graph_paper__angle_value`: query_id=angle; answer=integer_value; annotation=point_set
- `task_geometry__graph_paper__area_extremum_label`: query_id=area_extremum; answer=option_letter; annotation=point_set
- `task_geometry__graph_paper__circle_circumference_value`: query_id=perimeter; answer=symbolic_expression; annotation=point_set
- `task_geometry__graph_paper__ellipse_area_value`: query_id=area; answer=symbolic_expression; annotation=point_set
- `task_geometry__graph_paper__length_extremum_label`: query_id=length_extremum; answer=option_letter; annotation=point_set
- `task_geometry__graph_paper__line_slope_value`: query_id=slope; answer=decimal_value_1dp; annotation=point_set
- `task_geometry__graph_paper__perimeter_extremum_label`: query_id=perimeter_extremum; answer=option_letter; annotation=point_set
- `task_geometry__graph_paper__polygon_area_value`: query_id=area; answer=integer_value; annotation=point_set
- `task_geometry__graph_paper__polygon_convexity_count`: query_id=polygon_convexity_count; answer=integer_count; annotation=bbox_set
- `task_geometry__graph_paper__polygon_perimeter_value`: query_id=perimeter; answer=integer_value; annotation=point_set
- `task_geometry__graph_paper__quadrilateral_type_count`: query_id=quadrilateral_type_count; answer=integer_count; annotation=bbox_set
- `task_geometry__graph_paper__shape_type_count`: query_id=shape_type_count; answer=integer_count; annotation=bbox_set
- `task_geometry__graph_paper__triangle_type_count`: query_id=triangle_type_count; answer=integer_count; annotation=bbox_set

### `incircle_tangents` (2)

- `task_geometry__incircle_tangents__incircle_radius_from_area_value`: query_id=inradius_from_area_and_tangent_segments; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__incircle_tangents__incircle_tangent_perimeter_value`: query_id=triangle_perimeter_from_tangent_segments; answer=decimal_value_1dp; annotation=bbox_set

### `measuring_tools` (4)

- `task_geometry__measuring_tools__shape_angle_value_quadrilateral_vertex_protractor_reading`: query_id=quadrilateral_vertex_protractor_reading; answer=number; annotation=keyed_point_map
- `task_geometry__measuring_tools__shape_angle_value_triangle_vertex_protractor_reading`: query_id=triangle_vertex_protractor_reading; answer=number; annotation=keyed_point_map
- `task_geometry__measuring_tools__shape_length_value_circle_radius_ruler_reading`: query_id=circle_radius_ruler_reading; answer=number; annotation=keyed_point_map
- `task_geometry__measuring_tools__shape_length_value_polygon_side_ruler_reading`: query_id=polygon_side_ruler_reading; answer=number; annotation=keyed_point_map

### `marked_polygon_equation` (4)

- `task_geometry__marked_polygon_equation__angle_value`: query_id=marked_equal_angle_from_expression, isosceles_triangle_angle_from_expression; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__marked_polygon_equation__angle_variable_value`: query_id=marked_equal_angles_variable, isosceles_triangle_base_angle_variable, equilateral_median_right_angle_variable; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__marked_polygon_equation__side_length_value`: query_id=isosceles_triangle_side_from_expression, equilateral_triangle_side_from_expression, marked_polygon_side_from_expression, equilateral_median_side_length_from_expression; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__marked_polygon_equation__side_variable_value`: query_id=isosceles_triangle_equal_side_variable, equilateral_triangle_equal_side_variable, marked_polygon_equal_side_variable, isosceles_altitude_base_split_variable; answer=decimal_value_1dp; annotation=keyed_point_map

### `paper_fold` (1)

- `task_geometry__paper_fold__paper_fold_angle_value`: query_id=fold_angle_from_total_label; answer=decimal_value_1dp; annotation=bbox_set

### `parallel_segment_proportion` (2)

- `task_geometry__parallel_segment_proportion__segment_length_value`: query_id=triangle_side_splitter_segment_length, parallel_transversal_segment_length; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__parallel_segment_proportion__variable_value`: query_id=triangle_side_splitter_variable, parallel_transversal_segment_variable; answer=decimal_value_1dp; annotation=keyed_point_map

### `polygon_angle_chase` (3)

- `task_geometry__polygon_angle_chase__polygon_interior_angle_value`: query_id=triangle_interior_angle, quadrilateral_interior_angle, pentagon_interior_angle, hexagon_interior_angle; answer=integer_value; annotation=keyed_point_map
- `task_geometry__polygon_angle_chase__parallel_line_angle_value`: query_id=single_transversal_chain, two_transversal_angle_sum; answer=integer_value; annotation=keyed_point_map
- `task_geometry__polygon_angle_chase__symmetry_angle_value`: query_id=rectangle_diagonal_angle, reflection_axis_angle, isosceles_base_angle_chain; answer=integer_value; annotation=keyed_point_map

### `pythagorean_dissection` (1)

- `task_geometry__pythagorean_dissection__pythagorean_square_area_value`: query_id=central_square_area_from_triangle_legs; answer=decimal_value_1dp; annotation=bbox_set

### `pythagorean_tree` (1)

- `task_geometry__pythagorean_tree__missing_square_area_value`: query_id=hypotenuse_square_area, leg_square_area; answer=integer_value; annotation=keyed_bbox_map

### `rectangular_solid` (4)

- `task_geometry__rectangular_solid__cube_edge_from_frame_length_value`: query_id=cube_edge_from_total_frame, cube_edge_from_partial_frame; answer=integer_value; annotation=keyed_bbox_map
- `task_geometry__rectangular_solid__cuboid_surface_area_value`: query_id=surface_area_from_dimensions; answer=integer_value; annotation=keyed_point_map
- `task_geometry__rectangular_solid__cuboid_volume_missing_dimension_value`: query_id=missing_length_from_volume, missing_width_from_volume, missing_height_from_volume; answer=integer_value; annotation=keyed_point_map
- `task_geometry__rectangular_solid__open_box_net_dimension_value`: query_id=open_box_dimension_from_corner_cut, open_box_volume_from_net; answer=integer_value; annotation=keyed_bbox_map

### `regular_polygon_decomposition` (4)

- `task_geometry__regular_polygon_decomposition__central_angle_value`: query_id=single_wedge_central_angle, marked_wedges_central_angle; answer=integer_value; annotation=keyed_point_map
- `task_geometry__regular_polygon_decomposition__perimeter_value`: query_id=perimeter_from_side_length, perimeter_from_total_area_and_apothem; answer=integer_value; annotation=keyed_point_map
- `task_geometry__regular_polygon_decomposition__piece_area_value`: query_id=single_wedge_area_from_total, shaded_wedges_area_from_total, wedge_area_from_side_and_apothem; answer=number_value; annotation=keyed_point_map
- `task_geometry__regular_polygon_decomposition__side_length_value`: query_id=side_length_from_perimeter, side_length_from_total_area_and_apothem, side_length_from_wedge_area_and_apothem; answer=integer_value; annotation=keyed_point_map

### `right_triangle_altitude_theorem` (2)

- `task_geometry__right_triangle_altitude_theorem__altitude_to_hypotenuse_value`: query_id=altitude_from_split_hypotenuse, missing_projection_from_altitude; answer=integer_value; annotation=keyed_point_map
- `task_geometry__right_triangle_altitude_theorem__leg_projection_length_value`: query_id=leg_from_hypotenuse_projection, projection_from_leg_and_hypotenuse; answer=integer_value; annotation=keyed_point_map

### `sector` (9)

- `task_geometry__sector__angle_from_sector_measure_angle_from_arc_length_and_radius`: query_id=angle_from_arc_length_and_radius; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__sector__angle_from_sector_measure_angle_from_area_and_radius`: query_id=angle_from_area_and_radius; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__sector__arc_length_value_arc_length_from_area_and_radius`: query_id=arc_length_from_area_and_radius; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__sector__arc_length_value_arc_length_from_radius_and_supplement_angle`: query_id=arc_length_from_radius_and_supplement_angle; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__sector__related_angle_from_sector_measure_complement_angle_from_arc_length`: query_id=complement_angle_from_arc_length; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__sector__related_angle_from_sector_measure_remaining_angle_from_sector_measure`: query_id=remaining_angle_from_sector_measure; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__sector__related_angle_from_sector_measure_supplement_angle_from_area`: query_id=supplement_angle_from_area; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__sector__sector_area_value_area_from_arc_length_and_radius`: query_id=area_from_arc_length_and_radius; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__sector__sector_area_value_area_from_radius_and_complement_angle`: query_id=area_from_radius_and_complement_angle; answer=decimal_value_1dp; annotation=bbox_set

### `shape_gallery` (5)

- `task_geometry__shape_gallery__congruent_count`: query_id=congruent_count; answer=integer_count; annotation=bbox_set
- `task_geometry__shape_gallery__reflection_match`: query_id=reflection_match; answer=option_letter; annotation=point_set
- `task_geometry__shape_gallery__rotation_match`: query_id=rotation_match; answer=option_letter; annotation=point_set
- `task_geometry__shape_gallery__similar_count`: query_id=similar_count; answer=integer_count; annotation=bbox_set
- `task_geometry__shape_gallery__translation_match`: query_id=translation_match; answer=option_letter; annotation=point_set

### `similar_figure_measure_transfer` (5)

- `task_geometry__similar_figure_measure_transfer__area_scale_side_length_value`: query_id=side_length_from_area_pair, side_length_from_area_ratio, side_length_from_area_and_known_side; answer=integer_value; annotation=keyed_point_map
- `task_geometry__similar_figure_measure_transfer__corresponding_side_value`: query_id=direct_side_transfer, two_pair_side_transfer, nested_side_transfer; answer=integer_value; annotation=keyed_point_map
- `task_geometry__similar_figure_measure_transfer__scale_factor_value`: query_id=scale_factor_from_side_pair, scale_factor_from_perimeter_pair, scale_factor_from_area_pair; answer=integer_value; annotation=keyed_point_map
- `task_geometry__similar_figure_measure_transfer__side_length_from_expression_value`: query_id=similar_triangles_target_side_from_expression, similar_polygons_target_side_from_expression; answer=decimal_value_1dp; annotation=keyed_point_map
- `task_geometry__similar_figure_measure_transfer__variable_value`: query_id=similar_triangles_side_ratio_variable, similar_polygons_side_ratio_variable, two_expression_side_ratio_variable; answer=decimal_value_1dp; annotation=keyed_point_map

### `solid_cross_section` (2)

- `task_geometry__solid_cross_section__cone_parallel_slice_area`: query_id=cone_parallel_slice_area; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__solid_cross_section__square_pyramid_parallel_slice_area`: query_id=square_pyramid_parallel_slice_area; answer=decimal_value_1dp; annotation=bbox_set

### `solid_formula` (4)

- `task_geometry__solid_formula__cylinder_cone_height_from_volume_radius`: query_id=cylinder_cone_height_from_volume_radius; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__solid_formula__cylinder_cone_radius_from_volume_heights`: query_id=cylinder_cone_radius_from_volume_heights; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__solid_formula__house_prism_length_from_volume`: query_id=house_prism_length_from_volume; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__solid_formula__prism_pyramid_height_from_volume`: query_id=prism_pyramid_height_from_volume; answer=decimal_value_1dp; annotation=bbox_set

### `solid_revolution` (4)

- `task_geometry__solid_revolution__revolution_cone_volume_value`: query_id=cone_volume_from_right_triangle; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__solid_revolution__revolution_cylinder_volume_value`: query_id=cylinder_volume_from_rectangle; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__solid_revolution__revolution_double_cone_volume_value`: query_id=double_cone_volume_from_triangle; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__solid_revolution__revolution_frustum_volume_value`: query_id=frustum_volume_from_trapezoid; answer=decimal_value_1dp; annotation=bbox_set

### `special_quadrilateral` (3)

- `task_geometry__special_quadrilateral__algebraic_angle_value`: query_id=parallelogram_opposite_angle_expression, parallelogram_consecutive_angle_expression, rhombus_diagonal_half_angle_expression, kite_opposite_angle_expression; answer=integer_value; annotation=keyed_point_map
- `task_geometry__special_quadrilateral__diagonal_angle_value`: query_id=rhombus_vertex_angle_bisected_by_diagonal, kite_vertex_angle_bisected_by_symmetry_diagonal, rhombus_diagonal_perpendicular_complement; answer=integer_value; annotation=keyed_point_map
- `task_geometry__special_quadrilateral__segment_length_value`: query_id=parallelogram_opposite_side_expression, rhombus_all_sides_expression, kite_adjacent_equal_side_expression, parallelogram_diagonal_bisection_expression; answer=integer_value; annotation=keyed_point_map

### `split_triangle_angle_chase` (1)

- `task_geometry__split_triangle_angle_chase__target_angle_value`: query_id=single_cevian_triangle_angle_sum, shared_vertex_split_angle_sum, two_step_adjacent_triangle_angle_sum; answer=integer_value; annotation=keyed_point_map

### `split_triangle_trig_chain` (1)

- `task_geometry__split_triangle_trig_chain__side_length_value`: query_id=shared_altitude_two_angles_side, shared_altitude_side_then_hypotenuse, isosceles_altitude_trig_side; answer=decimal_value_1dp; annotation=keyed_point_map

### `survey_traverse` (3)

- `task_geometry__survey_traverse__bearing_angle_value`: query_id=bearing_from_back_bearing, closed_traverse_missing_bearing; answer=integer_value; annotation=keyed_point_map
- `task_geometry__survey_traverse__station_elevation_value`: query_id=leveling_station_elevation, slope_distance_elevation_change; answer=integer_value; annotation=keyed_point_map
- `task_geometry__survey_traverse__traverse_area_value`: query_id=coordinate_traverse_area, offset_trapezoid_area; answer=integer_value; annotation=keyed_bbox_map

### `tangent_packing` (6)

- `task_geometry__tangent_packing__circle_in_square_gap_area`: query_id=circle_in_square_gap_area; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__tangent_packing__circle_in_square_radius_from_gap_area`: query_id=circle_in_square_radius_from_gap_area; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__tangent_packing__square_in_circle_gap_area`: query_id=square_in_circle_gap_area; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__tangent_packing__square_in_circle_side_from_gap_area`: query_id=square_in_circle_side_from_gap_area; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__tangent_packing__two_circles_in_rectangle_gap_area`: query_id=two_circles_in_rectangle_gap_area; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__tangent_packing__two_circles_in_rectangle_radius_from_gap_area`: query_id=two_circles_in_rectangle_radius_from_gap_area; answer=decimal_value_1dp; annotation=bbox_set

### `trapezoid_extension` (5)

- `task_geometry__trapezoid_extension__extension_from_parallelogram_area`: query_id=extension_from_parallelogram_area; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__trapezoid_extension__extension_from_parallelogram_perimeter`: query_id=extension_from_parallelogram_perimeter; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__trapezoid_extension__trapezoid_area_from_bases_and_height`: query_id=trapezoid_area_from_bases_and_height; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__trapezoid_extension__trapezoid_area_from_extension_and_height`: query_id=trapezoid_area_from_extension_and_height; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__trapezoid_extension__trapezoid_area_from_parallelogram_area`: query_id=trapezoid_area_from_parallelogram_area; answer=decimal_value_1dp; annotation=bbox_set

### `triangle_congruence_correspondence` (3)

- `task_geometry__triangle_congruence_correspondence__algebraic_side_value`: query_id=single_expression_equal_sides, two_expression_equal_sides, shared_side_congruence_expression; answer=integer_value; annotation=keyed_point_map
- `task_geometry__triangle_congruence_correspondence__corresponding_angle_value`: query_id=angle_mark_transfer, congruence_statement_angle_transfer, overlapping_triangle_angle_transfer; answer=integer_value; annotation=keyed_point_map
- `task_geometry__triangle_congruence_correspondence__corresponding_side_value`: query_id=tick_mark_side_transfer, congruence_statement_side_transfer, overlapping_triangle_side_transfer; answer=integer_value; annotation=keyed_point_map

### `triangle_relations` (19)

- `task_geometry__triangle_relations__angle_bisector_segment_value_angle_bisector_base_length`: query_id=angle_bisector_base_length; answer=integer_value; annotation=bbox_set
- `task_geometry__triangle_relations__angle_bisector_segment_value_angle_bisector_split_length`: query_id=angle_bisector_split_length; answer=integer_value; annotation=bbox_set
- `task_geometry__triangle_relations__angle_bisector_variable_value`: query_id=split_segment_ratio_variable, adjacent_side_ratio_variable; answer=integer_value; annotation=keyed_point_map
- `task_geometry__triangle_relations__angle_of_elevation_value`: query_id=angle_of_elevation_from_height_and_distance; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__triangle_relations__centroid_median_segment_value_centroid_vertex_segment_length`: query_id=centroid_vertex_segment_length; answer=integer_value; annotation=bbox_set
- `task_geometry__triangle_relations__centroid_median_segment_value_centroid_whole_median_length`: query_id=centroid_whole_median_length; answer=integer_value; annotation=bbox_set
- `task_geometry__triangle_relations__parallel_section_base_length`: query_id=parallel_section_base_length; answer=integer_value; annotation=bbox_set
- `task_geometry__triangle_relations__parallel_section_cross_length`: query_id=parallel_section_cross_length; answer=integer_value; annotation=bbox_set
- `task_geometry__triangle_relations__pythagorean_length_value_chained_rectangle_diagonal_length`: query_id=chained_rectangle_diagonal_length; answer=integer_value; annotation=bbox_set
- `task_geometry__triangle_relations__pythagorean_length_value_rectangle_triangle_shared_height_length`: query_id=rectangle_triangle_shared_height_length; answer=integer_value; annotation=bbox_set
- `task_geometry__triangle_relations__right_triangle_inverse_trig_angle_angle_from_adjacent_hypotenuse`: query_id=angle_from_adjacent_hypotenuse; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__triangle_relations__right_triangle_inverse_trig_angle_angle_from_opposite_adjacent`: query_id=angle_from_opposite_adjacent; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__triangle_relations__right_triangle_inverse_trig_angle_angle_from_opposite_hypotenuse`: query_id=angle_from_opposite_hypotenuse; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__triangle_relations__right_triangle_missing_side_value_ground_from_angle_and_height`: query_id=ground_from_angle_and_height; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__triangle_relations__right_triangle_missing_side_value_ground_from_angle_and_hypotenuse`: query_id=ground_from_angle_and_hypotenuse; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__triangle_relations__right_triangle_missing_side_value_height_from_angle_and_ground`: query_id=height_from_angle_and_ground; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__triangle_relations__right_triangle_missing_side_value_height_from_angle_and_hypotenuse`: query_id=height_from_angle_and_hypotenuse; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__triangle_relations__right_triangle_missing_side_value_hypotenuse_from_angle_and_height`: query_id=hypotenuse_from_angle_and_height; answer=decimal_value_1dp; annotation=bbox_set
- `task_geometry__triangle_relations__similar_triangles_side_length`: query_id=similar_triangles_side_length; answer=integer_value; annotation=bbox_set

### `volume_equivalence_conversion` (2)

- `task_geometry__volume_equivalence_conversion__equal_volume_option_label`: query_id=cone_matches_cylinder_option, cylinder_matches_cone_option, cuboid_matches_cylinder_option; answer=option_letter; annotation=keyed_bbox_map
- `task_geometry__volume_equivalence_conversion__missing_dimension_value`: query_id=cuboid_to_cylinder_length, cylinder_to_cone_height, cone_to_cuboid_height; answer=integer_value; annotation=keyed_bbox_map

### `wire_shape_conversion` (3)

- `task_geometry__wire_shape_conversion__frame_edge_length_value`: query_id=trapezoid_wire_to_cube_frame, parallelogram_wire_to_cuboid_frame; answer=integer_value; annotation=keyed_bbox_map
- `task_geometry__wire_shape_conversion__missing_dimension_value`: query_id=same_wire_circle_to_trapezoid_side, same_wire_polygon_to_rectangle_side; answer=integer_value; annotation=keyed_bbox_map
- `task_geometry__wire_shape_conversion__wire_length_value`: query_id=trapezoid_wire_length, parallelogram_wire_length, circle_wire_length_from_area; answer=integer_value; annotation=keyed_bbox_map
