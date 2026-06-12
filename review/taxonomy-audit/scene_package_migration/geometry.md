# Geometry Scene-Package Migration

Geometry is migrated from legacy group routing to scene-package routing. Public task files are under `trace/tasks/geometry/<scene_id>/<objective_contract>.py`; scene-local helpers are under each scene package `shared/` directory.

| Scene | Tasks | Status | Source package |
|---|---:|---|---|
| `angle_relations` | 3 | `source_audited_required_gate_blocked` | `trace/tasks/geometry/angle_relations/` |
| `area_partition` | 1 | `objective_ownership_complete` | `trace/tasks/geometry/area_partition/` |
| `bearing_route` | 2 | `objective_ownership_complete` | `trace/tasks/geometry/bearing_route/` |
| `circle_centerline_overlap` | 1 | `objective_ownership_complete` | `trace/tasks/geometry/circle_centerline_overlap/` |
| `circle_pair_tangents` | 2 | `objective_ownership_complete` | `trace/tasks/geometry/circle_pair_tangents/` |
| `circle_polygon_composite` | 2 | `objective_ownership_complete` | `trace/tasks/geometry/circle_polygon_composite/` |
| `circle_theorem` | 14 | `objective_ownership_complete` | `trace/tasks/geometry/circle_theorem/` |
| `composite_shape` | 13 | `objective_ownership_complete` | `trace/tasks/geometry/composite_shape/` |
| `concentric_chord` | 2 | `objective_ownership_complete` | `trace/tasks/geometry/concentric_chord/` |
| `cone_net` | 2 | `objective_ownership_complete` | `trace/tasks/geometry/cone_net/` |
| `container_volume_transfer` | 4 | `objective_ownership_complete` | `trace/tasks/geometry/container_volume_transfer/` |
| `coordinate_composite` | 1 | `objective_ownership_complete` | `trace/tasks/geometry/coordinate_composite/` |
| `coordinate_panels` | 1 | `objective_ownership_complete` | `trace/tasks/geometry/coordinate_panels/` |
| `coordinate_plane` | 12 | `objective_ownership_complete` | `trace/tasks/geometry/coordinate_plane/` |
| `cuboid_views` | 1 | `objective_ownership_complete` | `trace/tasks/geometry/cuboid_views/` |
| `cylinder_wrap` | 2 | `objective_ownership_complete` | `trace/tasks/geometry/cylinder_wrap/` |
| `function_graph` | 4 | `objective_ownership_complete` | `trace/tasks/geometry/function_graph/` |
| `function_panels` | 6 | `objective_ownership_complete` | `trace/tasks/geometry/function_panels/` |
| `graph_paper` | 15 | `objective_ownership_complete` | `trace/tasks/geometry/graph_paper/` |
| `incircle_tangents` | 2 | `objective_ownership_complete` | `trace/tasks/geometry/incircle_tangents/` |
| `marked_polygon_equation` | 4 | `objective_ownership_complete` | `trace/tasks/geometry/marked_polygon_equation/` |
| `measuring_tools` | 4 | `objective_ownership_complete` | `trace/tasks/geometry/measuring_tools/` |
| `paper_fold` | 1 | `objective_ownership_complete` | `trace/tasks/geometry/paper_fold/` |
| `parallel_segment_proportion` | 2 | `objective_ownership_complete` | `trace/tasks/geometry/parallel_segment_proportion/` |
| `polygon_angle_chase` | 3 | `objective_ownership_complete` | `trace/tasks/geometry/polygon_angle_chase/` |
| `pythagorean_dissection` | 1 | `objective_ownership_complete` | `trace/tasks/geometry/pythagorean_dissection/` |
| `pythagorean_tree` | 1 | `objective_ownership_complete` | `trace/tasks/geometry/pythagorean_tree/` |
| `rectangular_solid` | 4 | `objective_ownership_complete` | `trace/tasks/geometry/rectangular_solid/` |
| `regular_polygon_decomposition` | 4 | `objective_ownership_complete` | `trace/tasks/geometry/regular_polygon_decomposition/` |
| `right_triangle_altitude_theorem` | 2 | `objective_ownership_complete` | `trace/tasks/geometry/right_triangle_altitude_theorem/` |
| `sector` | 9 | `objective_ownership_complete` | `trace/tasks/geometry/sector/` |
| `shape_gallery` | 5 | `objective_ownership_complete` | `trace/tasks/geometry/shape_gallery/` |
| `similar_figure_measure_transfer` | 5 | `objective_ownership_complete` | `trace/tasks/geometry/similar_figure_measure_transfer/` |
| `solid_cross_section` | 2 | `objective_ownership_complete` | `trace/tasks/geometry/solid_cross_section/` |
| `solid_formula` | 4 | `objective_ownership_complete` | `trace/tasks/geometry/solid_formula/` |
| `solid_revolution` | 4 | `objective_ownership_complete` | `trace/tasks/geometry/solid_revolution/` |
| `special_quadrilateral` | 3 | `objective_ownership_complete` | `trace/tasks/geometry/special_quadrilateral/` |
| `split_triangle_angle_chase` | 1 | `objective_ownership_complete` | `trace/tasks/geometry/split_triangle_angle_chase/` |
| `split_triangle_trig_chain` | 1 | `objective_ownership_complete` | `trace/tasks/geometry/split_triangle_trig_chain/` |
| `survey_traverse` | 3 | `objective_ownership_complete` | `trace/tasks/geometry/survey_traverse/` |
| `tangent_packing` | 6 | `objective_ownership_complete` | `trace/tasks/geometry/tangent_packing/` |
| `trapezoid_extension` | 5 | `objective_ownership_complete` | `trace/tasks/geometry/trapezoid_extension/` |
| `triangle_congruence_correspondence` | 3 | `objective_ownership_complete` | `trace/tasks/geometry/triangle_congruence_correspondence/` |
| `triangle_relations` | 19 | `objective_ownership_complete` | `trace/tasks/geometry/triangle_relations/` |
| `volume_equivalence_conversion` | 2 | `objective_ownership_complete` | `trace/tasks/geometry/volume_equivalence_conversion/` |
| `wire_shape_conversion` | 3 | `objective_ownership_complete` | `trace/tasks/geometry/wire_shape_conversion/` |
