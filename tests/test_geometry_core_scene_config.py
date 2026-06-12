"""Regression tests for scene default config loading."""
from __future__ import annotations
import json
import pytest
from trace.core.scene_config import get_domain_defaults, get_scene_defaults, resolve_scene_section_defaults
from trace.tasks import TASK_REGISTRY
from trace.tasks.shared.config_defaults import required_group_default, required_group_defaults, resolve_optional_int_bounds, resolve_required_float_bounds, resolve_required_int_bounds, split_generation_rendering_prompt_defaults
from trace.tasks.graph.shared.graph_sampling import SUPPORTED_LAYOUT_VARIANTS
FULL_NODE_LINK_LAYOUT_VARIANTS = set(SUPPORTED_LAYOUT_VARIANTS)

def test_default_geometry_tasks_declare_public_scene_metadata() -> None:
    geometry_tasks = {task_id: task_cls for task_id, task_cls in TASK_REGISTRY.items() if task_id.startswith('task_geometry__') and getattr(task_cls, 'domain', None) == 'geometry' and getattr(task_cls, 'default_dataset_enabled', False)}
    failures: list[tuple[str, str | None, str | None, str]] = []
    public_scenes: set[str] = set()
    for task_id, task_cls in sorted(geometry_tasks.items()):
        expected_scene = task_id.split('__', 2)[1]
        scene_id = getattr(task_cls, 'scene_id', None)
        public_scene_id = getattr(task_cls, 'public_scene_id', None)
        public_scenes.add(expected_scene)
        if scene_id != expected_scene or public_scene_id != expected_scene:
            failures.append((task_id, scene_id, public_scene_id, expected_scene))
    assert len(geometry_tasks) == 192
    assert len(public_scenes) == 46
    assert failures == []

def test_geometry_measurement_defaults_loaded() -> None:
    cfg = get_scene_defaults('geometry', 'measurement')
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['canvas_size_min']) > 0
    assert int(render_shared['canvas_size_max']) >= int(render_shared['canvas_size_min'])
    assert int(render_shared['graph_cells_min']) > 0
    assert int(render_shared['graph_cells_max']) >= int(render_shared['graph_cells_min'])
    assert int(render_shared['line_width_min']) >= 1
    assert int(render_shared['line_width_max']) >= int(render_shared['line_width_min'])
    assert int(render_shared['label_stroke_width_min']) >= 1
    assert int(render_shared['label_stroke_width_max']) >= int(render_shared['label_stroke_width_min'])
    scene_rotation = dict(render_shared['single_object_scene_rotation'])
    assert bool(scene_rotation['enabled']) is True
    assert float(scene_rotation['probability']) == 0.5
    assert int(scene_rotation['angle_abs_min']) == 15
    assert int(scene_rotation['angle_abs_max']) == 75
    assert int(scene_rotation['margin_px']) > 0
    assert 0.0 < float(scene_rotation['min_scale_after_fit']) <= 1.0
    generation_overrides = cfg['generation']['task_overrides']
    assert 'source_geometry_measurement_angle' in generation_overrides
    assert int(cfg['generation']['shared']['answer_min']) >= 0
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip()
    assert str(prompt_shared['scene_key']).strip()
    assert str(prompt_shared['task_key']).strip()
    assert str(prompt_shared['json_output_contract']).strip()
    assert str(prompt_shared['json_output_contract_answer_only']).strip()
    angle_generation, angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_measurement_angle')
    for key in ('min_angle', 'max_angle', 'angle_step'):
        assert key in angle_generation
    assert int(angle_generation['max_angle']) >= int(angle_generation['min_angle'])
    assert int(angle_generation['angle_step']) > 0
    assert int(angle_rendering['line_width']) > 0
    assert str(angle_prompt['annotation_hint']).strip()
    assert str(angle_prompt['answer_hint']).strip()
    assert str(angle_prompt['json_example']).strip()
    assert str(angle_prompt['json_example_answer_only']).strip()
    area_generation, area_rendering, area_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_measurement_area')
    assert sorted(area_generation['variant_weights'].keys()) == ['ellipse', 'quadrilateral', 'triangle']
    assert bool(area_generation['balanced_variant_sampling']) is True
    assert bool(area_generation['ellipse_allow_circle']) is True
    assert int(area_rendering['line_width']) > 0
    assert str(area_prompt['question_text_polygon']).strip()
    assert str(area_prompt['question_text_ellipse']).strip()
    assert str(area_prompt['annotation_hint_polygon']).strip()
    assert str(area_prompt['annotation_hint_ellipse']).strip()
    assert str(area_prompt['answer_hint_integer']).strip()
    assert str(area_prompt['answer_hint_pi']).strip()
    assert str(area_prompt['json_example_triangle']).strip()
    assert str(area_prompt['json_example_quadrilateral']).strip()
    assert str(area_prompt['json_example_ellipse']).strip()
    assert str(area_prompt['json_example_integer']).strip()
    assert str(area_prompt['json_example_pi']).strip()
    assert str(area_prompt['json_example_answer_only_integer']).strip()
    assert str(area_prompt['json_example_answer_only_pi']).strip()
    perim_generation, perim_rendering, perim_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_measurement_perimeter')
    assert sorted(perim_generation['variant_weights'].keys()) == ['circle', 'quadrilateral', 'triangle']
    assert bool(perim_generation['balanced_variant_sampling']) is True
    assert int(perim_generation['circle_radius_min']) >= 1
    assert int(perim_generation['circle_radius_max']) >= int(perim_generation['circle_radius_min'])
    assert int(perim_rendering['line_width']) > 0
    assert str(perim_prompt['question_text_polygon']).strip()
    assert str(perim_prompt['question_text_circle']).strip()
    assert str(perim_prompt['annotation_hint_polygon']).strip()
    assert str(perim_prompt['annotation_hint_circle']).strip()
    assert str(perim_prompt['answer_hint_integer']).strip()
    assert str(perim_prompt['answer_hint_pi']).strip()
    assert str(perim_prompt['json_example_triangle']).strip()
    assert str(perim_prompt['json_example_quadrilateral']).strip()
    assert str(perim_prompt['json_example_circle']).strip()
    assert str(perim_prompt['json_example_integer']).strip()
    assert str(perim_prompt['json_example_pi']).strip()
    assert str(perim_prompt['json_example_answer_only_integer']).strip()
    assert str(perim_prompt['json_example_answer_only_pi']).strip()
    length_generation, length_rendering, length_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_measurement_length')
    assert sorted(length_generation['variant_weights'].keys()) == ['circle_diameter', 'circle_radius', 'ellipse_major_axis', 'ellipse_minor_axis', 'pentagon', 'quadrilateral', 'segment', 'triangle']
    assert bool(length_generation['balanced_variant_sampling']) is True
    assert int(length_generation['answer_min']) <= int(length_generation['answer_max'])
    assert int(length_generation['segment_length_min']) >= 1
    assert int(length_generation['segment_length_max']) >= int(length_generation['segment_length_min'])
    assert int(length_rendering['line_width']) > 0
    assert str(length_prompt['question_template_segment']).strip()
    assert str(length_prompt['question_template_polygon_side']).strip()
    assert str(length_prompt['question_text_circle_radius']).strip()
    assert str(length_prompt['question_text_circle_diameter']).strip()
    assert str(length_prompt['question_text_ellipse_major_axis']).strip()
    assert str(length_prompt['question_text_ellipse_minor_axis']).strip()
    assert str(length_prompt['annotation_hint_segment']).strip()
    assert str(length_prompt['annotation_hint_polygon_side']).strip()
    assert str(length_prompt['annotation_hint_circle_center']).strip()
    assert str(length_prompt['annotation_hint_ellipse_axis']).strip()
    assert str(length_prompt['answer_hint_integer']).strip()
    assert str(length_prompt['json_example_segment_integer']).strip()
    assert str(length_prompt['json_example_polygon_side_integer']).strip()
    assert str(length_prompt['json_example_circle_radius_integer']).strip()
    assert str(length_prompt['json_example_circle_diameter_integer']).strip()
    assert str(length_prompt['json_example_ellipse_major_axis_integer']).strip()
    assert str(length_prompt['json_example_ellipse_minor_axis_integer']).strip()
    assert str(length_prompt['json_example_integer']).strip()
    assert str(length_prompt['json_example_answer_only_integer']).strip()
    slope_generation, slope_rendering, slope_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_measurement_slope')
    assert int(slope_generation['slope_tenths_min']) < 0
    assert int(slope_generation['slope_tenths_max']) > 0
    assert bool(slope_generation['balanced_sampling']) is True
    assert int(slope_rendering['line_width']) > 0
    assert str(slope_prompt['object_description']).strip()
    assert str(slope_prompt['question_text']).strip()
    assert str(slope_prompt['annotation_hint']).strip()
    assert str(slope_prompt['answer_hint']).strip()
    assert str(slope_prompt['json_example']).strip()
    assert str(slope_prompt['json_example_answer_only']).strip()

def test_geometry_circle_defaults_include_single_object_rotation() -> None:
    cfg = get_scene_defaults('geometry', 'circle')
    render_shared = cfg['rendering']['shared']
    scene_rotation = dict(render_shared['single_object_scene_rotation'])
    assert bool(scene_rotation['enabled']) is True
    assert float(scene_rotation['probability']) == 0.5
    assert int(scene_rotation['angle_abs_min']) == 15
    assert int(scene_rotation['angle_abs_max']) == 75
    assert int(scene_rotation['margin_px']) > 0
    assert 0.0 < float(scene_rotation['min_scale_after_fit']) <= 1.0

def test_geometry_comparison_defaults_loaded() -> None:
    cfg = get_scene_defaults('geometry', 'comparison')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['object_count_min']) >= 2
    assert int(generation_shared['object_count_max']) >= int(generation_shared['object_count_min'])
    assert bool(generation_shared['balanced_sampling']) is True
    assert float(generation_shared['min_normalized_gap']) > 0.0
    generation_overrides = cfg['generation']['task_overrides']
    assert 'source_geometry_comparison_angle' in generation_overrides
    assert 'source_geometry_comparison_area' in generation_overrides
    assert 'source_geometry_comparison_length' in generation_overrides
    assert 'source_geometry_comparison_perimeter' in generation_overrides
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['canvas_size_min']) > 0
    assert int(render_shared['canvas_size_max']) >= int(render_shared['canvas_size_min'])
    assert int(render_shared['graph_cells_min']) > 0
    assert int(render_shared['graph_cells_max']) >= int(render_shared['graph_cells_min'])
    assert int(render_shared['line_width_min']) >= 1
    assert int(render_shared['line_width_max']) >= int(render_shared['line_width_min'])
    assert int(render_shared['label_stroke_width_min']) >= 1
    assert int(render_shared['label_stroke_width_max']) >= int(render_shared['label_stroke_width_min'])
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip()
    assert str(prompt_shared['scene_key']).strip()
    assert str(prompt_shared['task_key']).strip()
    angle_generation, angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_comparison_angle')
    assert int(angle_generation['min_angle']) < int(angle_generation['max_angle'])
    assert int(angle_generation['angle_step']) > 0
    assert sorted(angle_generation['query_type_weights'].keys()) == ['largest', 'smallest']
    assert sorted(angle_generation['object_count_weights'].keys()) == ['4', '6', '9']
    assert float(angle_generation['min_absolute_gap_degrees']) > 0.0
    assert int(angle_rendering['line_width']) > 0
    assert str(angle_prompt['object_description']).strip()
    assert str(angle_prompt['question_text_largest']).strip()
    assert str(angle_prompt['question_text_smallest']).strip()
    assert str(angle_prompt['annotation_hint']).strip()
    assert str(angle_prompt['answer_hint']).strip()
    area_generation, area_rendering, area_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_comparison_area')
    assert int(area_generation['min_rectangle_width']) < int(area_generation['max_rectangle_width'])
    assert int(area_generation['min_rectangle_height']) < int(area_generation['max_rectangle_height'])
    assert int(area_generation['min_triangle_base']) < int(area_generation['max_triangle_base'])
    assert int(area_generation['min_triangle_height']) < int(area_generation['max_triangle_height'])
    assert sorted(area_generation['query_type_weights'].keys()) == ['largest', 'smallest']
    assert sorted(area_generation['object_count_weights'].keys()) == ['4', '6', '9']
    assert float(area_generation['min_absolute_gap_square_units']) > 0.0
    assert float(area_generation['min_absolute_triangle_area_gap_square_units']) > 0.0
    assert int(area_rendering['line_width']) > 0
    assert str(area_prompt['object_description']).strip()
    assert str(area_prompt['object_description_triangle']).strip()
    assert str(area_prompt['question_text_largest']).strip()
    assert str(area_prompt['question_text_smallest']).strip()
    assert str(area_prompt['question_text_largest_triangle']).strip()
    assert str(area_prompt['question_text_smallest_triangle']).strip()
    assert str(area_prompt['annotation_hint']).strip()
    assert str(area_prompt['annotation_hint_triangle']).strip()
    assert str(area_prompt['answer_hint']).strip()
    assert str(area_prompt['answer_hint_triangle']).strip()
    perimeter_generation, perimeter_rendering, perimeter_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_comparison_perimeter')
    assert int(perimeter_generation['min_rectangle_width']) < int(perimeter_generation['max_rectangle_width'])
    assert int(perimeter_generation['min_rectangle_height']) < int(perimeter_generation['max_rectangle_height'])
    assert int(perimeter_generation['min_triangle_base']) < int(perimeter_generation['max_triangle_base'])
    assert int(perimeter_generation['min_triangle_height']) < int(perimeter_generation['max_triangle_height'])
    assert sorted(perimeter_generation['query_type_weights'].keys()) == ['largest', 'smallest']
    assert sorted(perimeter_generation['object_count_weights'].keys()) == ['4', '6', '9']
    assert float(perimeter_generation['min_absolute_gap_units']) > 0.0
    assert float(perimeter_generation['min_absolute_triangle_perimeter_gap_units']) > 0.0
    assert int(perimeter_rendering['line_width']) > 0
    assert str(perimeter_prompt['object_description']).strip()
    assert str(perimeter_prompt['object_description_triangle']).strip()
    assert str(perimeter_prompt['question_text_largest']).strip()
    assert str(perimeter_prompt['question_text_smallest']).strip()
    assert str(perimeter_prompt['question_text_largest_triangle']).strip()
    assert str(perimeter_prompt['question_text_smallest_triangle']).strip()
    assert str(perimeter_prompt['annotation_hint']).strip()
    assert str(perimeter_prompt['annotation_hint_triangle']).strip()
    assert str(perimeter_prompt['answer_hint']).strip()
    assert str(perimeter_prompt['answer_hint_triangle']).strip()
    length_generation, length_rendering, length_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_comparison_length')
    assert int(length_generation['min_segment_length']) < int(length_generation['max_segment_length'])
    assert int(length_generation['max_abs_vector_component']) > 0
    assert sorted(length_generation['query_type_weights'].keys()) == ['largest', 'smallest']
    assert sorted(length_generation['object_count_weights'].keys()) == ['4', '6', '9']
    assert float(length_generation['min_absolute_gap_units']) > 0.0
    assert int(length_rendering['line_width']) > 0
    assert str(length_prompt['object_description']).strip()
    assert str(length_prompt['question_text_largest']).strip()
    assert str(length_prompt['question_text_smallest']).strip()
    assert str(length_prompt['annotation_hint']).strip()
    assert str(length_prompt['answer_hint']).strip()

def test_geometry_counting_defaults_loaded() -> None:
    cfg = get_scene_defaults('geometry', 'counting')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['object_count_min']) >= 2
    assert int(generation_shared['object_count_max']) >= int(generation_shared['object_count_min'])
    assert bool(generation_shared['balanced_sampling']) is True
    generation_overrides = cfg['generation']['task_overrides']
    assert 'source_geometry_counting_angle' in generation_overrides
    assert 'source_geometry_counting_triangle' in generation_overrides
    assert 'source_geometry_counting_quadrilateral' in generation_overrides
    assert 'source_geometry_counting_shape_type' in generation_overrides
    assert 'source_geometry_counting_convexity' in generation_overrides
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['canvas_size_min']) > 0
    assert int(render_shared['canvas_size_max']) >= int(render_shared['canvas_size_min'])
    assert int(render_shared['graph_cells_min']) > 0
    assert int(render_shared['graph_cells_max']) >= int(render_shared['graph_cells_min'])
    assert int(render_shared['line_width_min']) >= 1
    assert int(render_shared['line_width_max']) >= int(render_shared['line_width_min'])
    assert int(render_shared['label_stroke_width_min']) >= 1
    assert int(render_shared['label_stroke_width_max']) >= int(render_shared['label_stroke_width_min'])
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip()
    assert str(prompt_shared['scene_key']).strip()
    assert str(prompt_shared['task_key']).strip()
    angle_generation, angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_counting_angle')
    assert int(angle_generation['min_angle']) < int(angle_generation['max_angle'])
    assert int(angle_generation['angle_step']) > 0
    assert sorted(angle_generation['variant_weights'].keys()) == ['acute_angle', 'obtuse_angle', 'right_angle']
    assert bool(angle_generation['balanced_variant_sampling']) is True
    assert sorted(angle_generation['object_count_weights'].keys()) == ['10', '6', '7', '8', '9']
    assert float(angle_generation['boundary_margin_degrees']) >= 0.0
    assert int(angle_rendering['line_width']) > 0
    assert str(angle_prompt['object_description']).strip()
    assert str(angle_prompt['question_text_acute_angle']).strip()
    assert str(angle_prompt['question_text_right_angle']).strip()
    assert str(angle_prompt['question_text_obtuse_angle']).strip()
    assert str(angle_prompt['annotation_hint']).strip()
    assert str(angle_prompt['answer_hint']).strip()
    assert str(angle_prompt['json_example']).strip()
    assert str(angle_prompt['json_example_answer_only']).strip()
    triangle_generation, triangle_rendering, triangle_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_counting_triangle')
    assert float(triangle_generation['min_side_units']) < float(triangle_generation['max_side_units'])
    assert float(triangle_generation['right_angle_margin_degrees']) > 0.0
    assert float(triangle_generation['min_side_gap_units']) > 0.0
    assert sorted(triangle_generation['variant_weights'].keys()) == ['acute_triangle', 'equilateral_triangle', 'isosceles_triangle', 'obtuse_triangle', 'right_triangle', 'scalene_triangle']
    assert bool(triangle_generation['balanced_variant_sampling']) is True
    assert sorted(triangle_generation['object_count_weights'].keys()) == ['5', '6', '7', '8']
    assert int(triangle_rendering['graph_cells_min']) < int(triangle_rendering['graph_cells_max'])
    assert int(triangle_rendering['object_label_offset_px']) > 0
    assert str(triangle_prompt['object_description']).strip()
    assert str(triangle_prompt['question_text_equilateral_triangle']).strip()
    assert str(triangle_prompt['question_text_isosceles_triangle']).strip()
    assert str(triangle_prompt['question_text_scalene_triangle']).strip()
    assert str(triangle_prompt['question_text_right_triangle']).strip()
    assert str(triangle_prompt['question_text_acute_triangle']).strip()
    assert str(triangle_prompt['question_text_obtuse_triangle']).strip()
    assert str(triangle_prompt['annotation_hint']).strip()
    assert str(triangle_prompt['answer_hint']).strip()
    assert str(triangle_prompt['json_example']).strip()
    assert str(triangle_prompt['json_example_answer_only']).strip()
    quadrilateral_generation, quadrilateral_rendering, quadrilateral_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_counting_quadrilateral')
    assert float(quadrilateral_generation['min_extent_units']) < float(quadrilateral_generation['max_extent_units'])
    assert float(quadrilateral_generation['min_side_gap_units']) > 0.0
    assert float(quadrilateral_generation['min_slant_units']) > 0.0
    assert sorted(quadrilateral_generation['variant_weights'].keys()) == ['parallelogram_only', 'rectangle_non_square', 'rhombus_non_square', 'square']
    assert bool(quadrilateral_generation['balanced_variant_sampling']) is True
    assert sorted(quadrilateral_generation['object_count_weights'].keys()) == ['5', '6', '7']
    assert int(quadrilateral_rendering['graph_cells_min']) < int(quadrilateral_rendering['graph_cells_max'])
    assert int(quadrilateral_rendering['object_label_offset_px']) > 0
    assert str(quadrilateral_prompt['object_description']).strip()
    assert str(quadrilateral_prompt['question_text_square']).strip()
    assert str(quadrilateral_prompt['question_text_rectangle_non_square']).strip()
    assert str(quadrilateral_prompt['question_text_rhombus_non_square']).strip()
    assert str(quadrilateral_prompt['question_text_parallelogram_only']).strip()
    assert str(quadrilateral_prompt['annotation_hint']).strip()
    assert str(quadrilateral_prompt['answer_hint']).strip()
    assert str(quadrilateral_prompt['json_example']).strip()
    assert str(quadrilateral_prompt['json_example_answer_only']).strip()
    shape_type_generation, shape_type_rendering, shape_type_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_counting_shape_type')
    assert float(shape_type_generation['min_extent_units']) < float(shape_type_generation['max_extent_units'])
    assert float(shape_type_generation['ellipse_axis_ratio_min']) > 1.0
    assert float(shape_type_generation['min_side_gap_units']) > 0.0
    assert float(shape_type_generation['min_slant_units']) > 0.0
    assert sorted(shape_type_generation['variant_weights'].keys()) == ['circle', 'ellipse', 'hexagon', 'pentagon', 'quadrilateral', 'triangle']
    assert bool(shape_type_generation['balanced_variant_sampling']) is True
    assert sorted(shape_type_generation['object_count_weights'].keys()) == ['6', '7', '8', '9']
    assert int(shape_type_rendering['graph_cells_min']) < int(shape_type_rendering['graph_cells_max'])
    assert int(shape_type_rendering['object_label_offset_px']) > 0
    assert str(shape_type_prompt['object_description']).strip()
    assert str(shape_type_prompt['question_text_triangle']).strip()
    assert str(shape_type_prompt['question_text_quadrilateral']).strip()
    assert str(shape_type_prompt['question_text_pentagon']).strip()
    assert str(shape_type_prompt['question_text_hexagon']).strip()
    assert str(shape_type_prompt['question_text_circle']).strip()
    assert str(shape_type_prompt['question_text_ellipse']).strip()
    assert str(shape_type_prompt['annotation_hint']).strip()
    assert str(shape_type_prompt['answer_hint']).strip()
    assert str(shape_type_prompt['json_example']).strip()
    assert str(shape_type_prompt['json_example_answer_only']).strip()
    convexity_generation, convexity_rendering, convexity_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_counting_convexity')
    assert sorted(convexity_generation['variant_weights'].keys()) == ['concave_polygon', 'convex_polygon']
    assert sorted(convexity_generation['object_count_weights'].keys()) == ['6', '7', '8', '9']
    assert sorted(convexity_generation['side_count_weights'].keys()) == ['4', '5', '6']
    assert bool(convexity_generation['balanced_variant_sampling']) is True
    assert int(convexity_rendering['graph_cells_min']) < int(convexity_rendering['graph_cells_max'])
    assert int(convexity_rendering['object_label_offset_px']) > 0
    assert str(convexity_prompt['object_description']).strip()
    assert str(convexity_prompt['question_text_convex_polygon']).strip()
    assert str(convexity_prompt['question_text_concave_polygon']).strip()
    assert str(convexity_prompt['annotation_hint']).strip()
    assert str(convexity_prompt['answer_hint']).strip()
    assert str(convexity_prompt['json_example']).strip()
    assert str(convexity_prompt['json_example_answer_only']).strip()

def test_measurement_prompt_examples_are_task_valid() -> None:
    cfg = get_scene_defaults('geometry', 'measurement')
    _angle_generation, _angle_rendering, angle_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_measurement_angle')
    angle_example = json.loads(str(angle_prompt['json_example']))
    assert list(angle_example.keys()) == ['annotation', 'answer']
    assert isinstance(angle_example['annotation'], list)
    assert len(angle_example['annotation']) == 3
    assert isinstance(angle_example['answer'], int)
    angle_answer_only_example = json.loads(str(angle_prompt['json_example_answer_only']))
    assert list(angle_answer_only_example.keys()) == ['answer']
    assert isinstance(angle_answer_only_example['answer'], int)
    _slope_generation, _slope_rendering, slope_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_measurement_slope')
    slope_example = json.loads(str(slope_prompt['json_example']))
    assert list(slope_example.keys()) == ['annotation', 'answer']
    assert isinstance(slope_example['annotation'], list)
    assert len(slope_example['annotation']) == 1
    assert isinstance(slope_example['annotation'][0], list)
    assert len(slope_example['annotation'][0]) == 2
    assert isinstance(slope_example['answer'], float)
    slope_answer_only_example = json.loads(str(slope_prompt['json_example_answer_only']))
    assert list(slope_answer_only_example.keys()) == ['answer']
    assert isinstance(slope_answer_only_example['answer'], float)
    _area_generation, _area_rendering, area_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_measurement_area')
    area_example = json.loads(str(area_prompt['json_example_integer']))
    assert list(area_example.keys()) == ['annotation', 'answer']
    assert isinstance(area_example['annotation'], list)
    area_points = [[int(point[0]), int(point[1])] for point in area_example['annotation']]
    assert len(area_points) >= 3
    assert int(area_example['answer']) >= 0
    for key, expected_points in (('json_example_triangle', 3), ('json_example_quadrilateral', 4)):
        polygon_example = json.loads(str(area_prompt[key]))
        assert list(polygon_example.keys()) == ['annotation', 'answer']
        assert isinstance(polygon_example['annotation'], list)
        polygon_points = [[int(point[0]), int(point[1])] for point in polygon_example['annotation']]
        assert len(polygon_points) == int(expected_points)
        assert int(polygon_example['answer']) >= 0
    area_pi_example = json.loads(str(area_prompt['json_example_pi']))
    assert list(area_pi_example.keys()) == ['annotation', 'answer']
    assert isinstance(area_pi_example['annotation'], list) and len(area_pi_example['annotation']) == 1
    assert str(area_pi_example['answer']).endswith('π')
    area_answer_only_integer = json.loads(str(area_prompt['json_example_answer_only_integer']))
    assert list(area_answer_only_integer.keys()) == ['answer']
    assert int(area_answer_only_integer['answer']) >= 0
    area_answer_only_pi = json.loads(str(area_prompt['json_example_answer_only_pi']))
    assert list(area_answer_only_pi.keys()) == ['answer']
    assert str(area_answer_only_pi['answer']).endswith('π')
    _perim_generation, _perim_rendering, perim_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_measurement_perimeter')
    perim_example = json.loads(str(perim_prompt['json_example_integer']))
    assert list(perim_example.keys()) == ['annotation', 'answer']
    assert isinstance(perim_example['annotation'], list)
    perim_points = [[int(point[0]), int(point[1])] for point in perim_example['annotation']]
    assert len(perim_points) >= 3
    assert int(perim_example['answer']) >= 0
    for key, expected_points in (('json_example_triangle', 3), ('json_example_quadrilateral', 4)):
        polygon_example = json.loads(str(perim_prompt[key]))
        assert list(polygon_example.keys()) == ['annotation', 'answer']
        assert isinstance(polygon_example['annotation'], list)
        polygon_points = [[int(point[0]), int(point[1])] for point in polygon_example['annotation']]
        assert len(polygon_points) == int(expected_points)
        assert int(polygon_example['answer']) >= 0
    perim_pi_example = json.loads(str(perim_prompt['json_example_pi']))
    assert list(perim_pi_example.keys()) == ['annotation', 'answer']
    assert isinstance(perim_pi_example['annotation'], list) and len(perim_pi_example['annotation']) == 1
    assert str(perim_pi_example['answer']).endswith('π')
    perim_answer_only_integer = json.loads(str(perim_prompt['json_example_answer_only_integer']))
    assert list(perim_answer_only_integer.keys()) == ['answer']
    assert int(perim_answer_only_integer['answer']) >= 0
    perim_answer_only_pi = json.loads(str(perim_prompt['json_example_answer_only_pi']))
    assert list(perim_answer_only_pi.keys()) == ['answer']
    assert str(perim_answer_only_pi['answer']).endswith('π')
    _length_generation, _length_rendering, length_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='source_geometry_measurement_length')
    length_example = json.loads(str(length_prompt['json_example_integer']))
    assert list(length_example.keys()) == ['annotation', 'answer']
    assert isinstance(length_example['annotation'], list)
    length_points = [[int(point[0]), int(point[1])] for point in length_example['annotation']]
    assert len(length_points) == 2
    assert int(length_example['answer']) >= 0
    center_example = json.loads(str(length_prompt['json_example_circle_radius_integer']))
    assert list(center_example.keys()) == ['annotation', 'answer']
    assert isinstance(center_example['annotation'], list)
    assert len(center_example['annotation']) == 1
    only_point = center_example['annotation'][0]
    assert isinstance(only_point, list) and len(only_point) == 2
    length_answer_only_example = json.loads(str(length_prompt['json_example_answer_only_integer']))
    assert list(length_answer_only_example.keys()) == ['answer']
    assert int(length_answer_only_example['answer']) >= 0
