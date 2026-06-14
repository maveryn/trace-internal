"""Regression tests for scene default config loading."""
from __future__ import annotations
import json
import pytest
from trace.core.scene_config import get_domain_defaults, get_scene_defaults, get_scene_defaults, resolve_scene_section_defaults, resolve_scene_section_defaults
from trace.core.prompts import load_scene_prompt_bundle
from trace.tasks.shared.config_defaults import required_group_default, required_group_defaults, resolve_optional_int_bounds, resolve_required_float_bounds, resolve_required_int_bounds, split_generation_rendering_prompt_defaults
from trace.tasks.graph.shared.graph_sample_types import SUPPORTED_LAYOUT_VARIANTS
FULL_NODE_LINK_LAYOUT_VARIANTS = set(SUPPORTED_LAYOUT_VARIANTS)

def test_icons_single_transform_options_scene_defaults_loaded() -> None:
    task_id = 'task_icons__single_transform_options__geometric_transform_result_label'
    cfg = get_scene_defaults('icons', 'single_transform_options')
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(cfg, task_id=task_id)
    assert str(generation['pool_manifest']) == 'non_symmetry.txt'
    assert int(generation['object_count_min']) == 6
    assert int(generation['object_count_max']) == 6
    assert sorted(generation['query_id_weights'].keys()) == ['flip_horizontal_result_label', 'flip_vertical_result_label', 'rotate_180_result_label', 'rotate_90_clockwise_result_label', 'rotate_90_counterclockwise_result_label']
    assert int(rendering['scene_icon_size_min_px']) == 96
    assert int(rendering['scene_icon_size_max_px']) == 112
    assert str(prompt['bundle_id']) == 'icons_single_transform_options_v0'
    assert str(prompt['scene_key']) == 'single_transform_options_transformation'
    assert str(prompt['task_key']) == 'transformation_query'
    assert resolve_scene_section_defaults(cfg, 'prompt', task_id=task_id) == prompt
    bundle = load_scene_prompt_bundle('icons', 'single_transform_options', 'icons_single_transform_options_v0')
    assert bundle.bundle_id == 'icons_single_transform_options_v0'
    assert set(bundle.scene_templates.keys()) == {'single_transform_options_transformation'}

def test_icons_reference_canvas_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults('icons', 'reference_canvas')
    attribute_task_id = 'task_icons__reference_canvas__reference_attribute_match_count'
    attribute_generation, attribute_rendering, attribute_prompt = split_generation_rendering_prompt_defaults(cfg, task_id=attribute_task_id)
    assert set(attribute_generation['query_id_weights'].keys()) == {'match_type', 'match_color', 'match_rotation', 'match_type_color_rotation'}
    assert str(attribute_generation['variant_generation_params']['match_type']['pool_manifest']).strip() == 'all_icons.txt'
    assert str(attribute_generation['variant_generation_params']['match_color']['pool_manifest']).strip() == 'all_icons.txt'
    assert str(attribute_generation['variant_generation_params']['match_rotation']['pool_manifest']).strip() == 'non_symmetry.txt'
    assert list(attribute_generation['variant_generation_params']['match_rotation']['rotation_candidates_degrees']) == [0, 90, 180, 270]
    assert float(attribute_rendering['variant_render_params']['match_color']['min_color_distance']) == 60.0
    assert int(attribute_rendering['variant_render_params']['match_color']['palette_size_min']) == 3
    assert int(attribute_rendering['variant_render_params']['match_color']['palette_size_max']) == 4
    assert str(attribute_prompt['bundle_id']) == 'icons_reference_canvas_v0'
    assert str(attribute_prompt['scene_key']) == 'reference_canvas_counting'
    assert set(attribute_prompt['question_text_by_variant'].keys()) == {'match_type', 'match_color', 'match_rotation', 'match_type_color_rotation'}
    assert str(attribute_prompt['annotation_hint']).strip()
    assert str(attribute_prompt['answer_hint']).strip()
    metric_task_id = 'task_icons__reference_canvas__reference_metric_relation_count'
    metric_generation, metric_rendering, metric_prompt = split_generation_rendering_prompt_defaults(cfg, task_id=metric_task_id)
    assert set(metric_generation['query_id_weights'].keys()) == {'size_smaller', 'size_larger'}
    assert set(metric_prompt['question_text_by_variant'].keys()) == {'size_smaller', 'size_larger'}
    metric_generation_smaller = metric_generation['variant_generation_params']['size_smaller']
    assert str(metric_generation_smaller['pool_manifest']).strip() == 'all_icons.txt'
    assert list(metric_generation_smaller['rotation_candidates_degrees']) == [0, 90, 180, 270]
    assert list(metric_generation_smaller['size_relation_candidates']) == ['smaller', 'larger']
    assert int(metric_generation_smaller['size_relation_min_delta_px']) == 18
    assert int(metric_generation_smaller['object_count_max']) == 14
    assert int(metric_generation_smaller['target_count_max']) == 5
    assert int(metric_generation_smaller['distractor_count_max']) == 6
    assert int(metric_rendering['variant_render_params']['size_smaller']['scene_icon_size_max_px']) == 120
    assert int(metric_rendering['variant_render_params']['size_smaller']['reference_icon_size_min_px']) == 64
    assert int(metric_rendering['variant_render_params']['size_smaller']['reference_icon_size_max_px']) == 96
    anchor_task_id = 'task_icons__reference_canvas__anchor_position_count'
    anchor_generation, anchor_rendering, anchor_prompt = split_generation_rendering_prompt_defaults(cfg, task_id=anchor_task_id)
    assert str(anchor_generation['pool_manifest']).strip() == 'all_icons.txt'
    assert dict(anchor_generation['direction_weights']) == {'left': 1.0, 'right': 1.0, 'above': 1.0, 'below': 1.0}
    assert float(anchor_rendering['scene_max_overlap_fraction']) == 0.05
    assert int(anchor_rendering['anchor_gap_px_directional']) == 8
    assert str(anchor_prompt['scene_key']) == 'reference_canvas_anchor'
    assert str(anchor_prompt['question_text_left']).strip()
    assert str(anchor_prompt['question_text_right']).strip()
    assert str(anchor_prompt['question_text_above']).strip()
    assert str(anchor_prompt['question_text_below']).strip()
    bundle = load_scene_prompt_bundle('icons', 'reference_canvas', 'icons_reference_canvas_v0')
    assert bundle.bundle_id == 'icons_reference_canvas_v0'
    assert set(bundle.scene_templates.keys()) == {'reference_canvas_anchor', 'reference_canvas_counting'}

def test_icons_icon_field_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults('icons', 'icon_field')
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id='task_icons__icon_field__type_frequency_count',
    )
    assert str(generation['pool_manifest']).strip() == 'all_icons.txt'
    singleton_params = generation['variant_generation_params']['singleton_type_count']
    assert int(singleton_params['object_count_min']) == 5
    assert int(singleton_params['object_count_max']) == 10
    assert int(singleton_params['target_count_min']) == 0
    assert int(singleton_params['target_count_max']) == 4
    assert int(singleton_params['repeated_type_count_min']) == 1
    assert int(singleton_params['repeated_type_count_max']) == 4
    assert int(singleton_params['repeated_type_multiplicity_min']) == 2
    assert int(singleton_params['repeated_type_multiplicity_max']) == 4
    most_frequent_params = generation['variant_generation_params']['most_frequent_type_count']
    assert str(most_frequent_params['pool_manifest']).strip() == 'all_icons.txt'
    assert int(most_frequent_params['object_count_min']) == 7
    assert int(most_frequent_params['object_count_max']) == 12
    assert int(most_frequent_params['target_count_min']) == 2
    assert int(most_frequent_params['target_count_max']) == 6
    assert int(most_frequent_params['other_repeated_type_count_max']) == 3
    assert int(rendering['canvas_width']) == 960
    assert int(rendering['canvas_height']) == 544
    assert int(rendering['scene_icon_size_min_px']) == 64
    assert int(rendering['scene_icon_size_max_px']) == 96
    assert list(rendering['rotation_candidates_degrees']) == [0, 90, 180, 270]
    assert str(prompt['bundle_id']) == 'icons_icon_field_v1'
    assert str(prompt['scene_key']) == 'single_scene_counting'
    assert str(prompt['task_key']) == 'type_frequency_query'
    bundle = load_scene_prompt_bundle('icons', 'icon_field', 'icons_icon_field_v1')
    assert bundle.bundle_id == 'icons_icon_field_v1'
    assert set(bundle.scene_templates.keys()) == {'single_scene_counting'}
    assert set(bundle.query_templates.keys()) == {'most_frequent_type_count', 'singleton_type_count'}

def test_icons_counting_defaults_loaded() -> None:
    cfg = get_scene_defaults('icons', 'counting')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['object_count_min']) >= 1
    assert int(generation_shared['object_count_max']) >= int(generation_shared['object_count_min'])
    assert int(generation_shared['target_count_min']) == 0
    assert int(generation_shared['target_count_max']) == 10
    assert int(generation_shared['distractor_count_min']) == 1
    assert int(generation_shared['distractor_count_max']) == 10
    assert bool(generation_shared['balanced_sampling']) is True
    assert 'task_icons__named_field__count_arithmetic' not in cfg['generation']['task_overrides']
    assert 'task_icons__named_field__closer_to_reference_count' not in cfg['generation']['task_overrides']
    assert 'task_icons__named_grid__scoped_attribute_count' not in cfg['generation'].get('task_overrides', {})
    assert 'task_icons__named_grid__row_column_shape_extreme_number' not in cfg['generation'].get('task_overrides', {})
    assert 'task_icons__named_grid__group_predicate_count' not in cfg['generation'].get('task_overrides', {})
    assert 'task_icons__named_ring__scoped_attribute_count' not in cfg['generation']['task_overrides']
    assert 'task_icons__venn_field__scoped_attribute_count' in cfg['generation']['task_overrides']
    named_cfg = get_scene_defaults('icons', 'named_field')
    named_grid_cfg = get_scene_defaults('icons', 'named_grid')
    named_ring_cfg = get_scene_defaults('icons', 'named_ring')
    assert 'task_icons__named_field__count_arithmetic' in named_cfg['generation']['task_overrides']
    assert 'task_icons__named_field__closer_to_reference_count' in named_cfg['generation']['task_overrides']
    assert 'task_icons__named_grid__scoped_attribute_count' in named_grid_cfg['generation']['task_overrides']
    assert 'task_icons__named_grid__row_column_shape_extreme_number' in named_grid_cfg['generation']['task_overrides']
    assert 'task_icons__named_grid__group_predicate_count' in named_grid_cfg['generation']['task_overrides']
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['canvas_width']) > 0
    assert int(render_shared['canvas_height']) > 0
    assert int(render_shared['reference_panel_width_px']) > 0
    assert int(render_shared['scene_icon_size_min_px']) > 0
    assert int(render_shared['scene_icon_size_max_px']) >= int(render_shared['scene_icon_size_min_px'])
    assert 0.0 <= float(render_shared['scene_max_overlap_fraction']) <= 1.0
    assert int(render_shared['scene_placement_max_attempts']) > 0
    assert 1 <= int(render_shared['palette_size_min']) <= int(render_shared['palette_size_max'])
    assert float(render_shared['min_color_distance']) > 0.0
    assert str(render_shared['color_distance_space']).strip() in {'lab', 'rgb'}
    assert 'icon_tint_rgb' not in render_shared
    assert list(render_shared['icon_noise_edit_types']) == ['blur', 'downsample', 'jpeg', 'noise']
    assert list(render_shared['icon_noise_edit_count_range']) == [0, 2]
    assert 'noise' in render_shared['icon_noise_value_ranges']
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip()
    assert str(prompt_shared['scene_key']).strip()
    assert str(prompt_shared['task_key']).strip()
    assert str(prompt_shared['json_output_contract']).strip()
    assert str(prompt_shared['json_output_contract_answer_only']).strip()
    pair_generation, pair_rendering, pair_prompt = split_generation_rendering_prompt_defaults(named_cfg, task_id='task_icons__named_field__count_arithmetic')
    assert int(pair_generation['operand_count_min']) == 1
    assert int(pair_generation['operand_count_max']) == 6
    assert int(pair_generation['total_answer_min']) == 2
    assert int(pair_generation['total_answer_max']) == 10
    assert int(pair_generation['difference_answer_min']) == 0
    assert int(pair_generation['difference_answer_max']) == 5
    assert sorted(pair_generation['query_weights'].keys()) == ['two_bound_color_difference_count', 'two_bound_color_total_count', 'two_shape_difference_count', 'two_shape_total_count']
    assert int(pair_rendering['canvas_width']) > 0
    assert int(pair_rendering['canvas_height']) > 0
    assert str(pair_prompt['scene_key']).strip() == 'single_scene_counting'
    assert str(pair_prompt['question_text_two_shape_total_count']).strip()
    assert str(pair_prompt['question_text_two_bound_color_total_count']).strip()
    assert str(pair_prompt['question_text_two_shape_difference_count']).strip()
    assert str(pair_prompt['question_text_two_bound_color_difference_count']).strip()
    assert str(pair_prompt['annotation_hint']).strip()
    assert str(pair_prompt['answer_hint']).strip()
    assert str(pair_prompt['json_example']).strip()
    assert str(pair_prompt['json_example_answer_only']).strip()
    grid_generation, grid_rendering, grid_prompt = split_generation_rendering_prompt_defaults(named_grid_cfg, task_id='task_icons__named_grid__scoped_attribute_count')
    assert int(grid_generation['target_count_min']) == 1
    assert int(grid_generation['target_count_max']) == 5
    assert sorted(grid_generation['query_id_weights'].keys()) == ['column_shape_count', 'row_shape_count']
    assert [list(value) for value in grid_generation['grid_size_support']] == [[4, 4], [4, 5], [4, 6], [5, 4], [5, 5], [5, 6], [6, 4], [6, 5], [6, 6]]
    assert int(grid_rendering['canvas_width']) == 880
    assert int(grid_rendering['canvas_height']) == 680
    assert int(grid_rendering['grid_cell_max_size_px']) == 104
    assert int(grid_rendering['axis_label_font_size_px']) == 24
    assert str(grid_prompt['scene_key']).strip() == 'single_scene_counting'
    assert str(grid_prompt['question_text_row_shape_count']).strip()
    assert str(grid_prompt['question_text_column_shape_count']).strip()
    assert str(grid_prompt['annotation_hint']).strip()
    assert str(grid_prompt['answer_hint']).strip()
    assert str(grid_prompt['json_example']).strip()
    assert str(grid_prompt['json_example_answer_only']).strip()
    grid_extreme_generation, grid_extreme_rendering, grid_extreme_prompt = split_generation_rendering_prompt_defaults(named_grid_cfg, task_id='task_icons__named_grid__row_column_shape_extreme_number')
    assert int(grid_extreme_generation['answer_line_number_min']) == 1
    assert int(grid_extreme_generation['answer_line_number_max']) == 6
    assert sorted(grid_extreme_generation['query_id_weights'].keys()) == ['column_fewest_shape_number', 'column_most_shape_number', 'row_fewest_shape_number', 'row_most_shape_number']
    assert [list(value) for value in grid_extreme_generation['grid_size_support']] == [[4, 4], [4, 5], [4, 6], [5, 4], [5, 5], [5, 6], [6, 4], [6, 5], [6, 6]]
    assert int(grid_extreme_rendering['canvas_width']) == 880
    assert int(grid_extreme_rendering['canvas_height']) == 680
    assert str(grid_extreme_prompt['scene_key']).strip() == 'single_scene_counting'
    assert str(grid_extreme_prompt['question_text_row_most_shape_number']).strip()
    assert str(grid_extreme_prompt['question_text_row_fewest_shape_number']).strip()
    assert str(grid_extreme_prompt['question_text_column_most_shape_number']).strip()
    assert str(grid_extreme_prompt['question_text_column_fewest_shape_number']).strip()
    assert str(grid_extreme_prompt['annotation_hint']).strip()
    assert str(grid_extreme_prompt['answer_hint']).strip()
    assert str(grid_extreme_prompt['json_example']).strip()
    assert str(grid_extreme_prompt['json_example_answer_only']).strip()
    grid_line_generation, grid_line_rendering, grid_line_prompt = split_generation_rendering_prompt_defaults(named_grid_cfg, task_id='task_icons__named_grid__group_predicate_count')
    assert int(grid_line_generation['answer_count_min']) == 0
    assert int(grid_line_generation['answer_count_max']) == 5
    assert int(grid_line_generation['at_least_threshold_min']) == 2
    assert int(grid_line_generation['at_least_threshold_max']) == 3
    assert int(grid_line_generation['exactly_threshold_min']) == 1
    assert int(grid_line_generation['exactly_threshold_max']) == 3
    assert sorted(grid_line_generation['query_id_weights'].keys()) == ['column_at_least_shape_count', 'column_exactly_shape_count', 'column_no_shape_count', 'row_at_least_shape_count', 'row_exactly_shape_count', 'row_no_shape_count']
    assert [list(value) for value in grid_line_generation['grid_size_support']] == [[4, 4], [4, 5], [4, 6], [5, 4], [5, 5], [5, 6], [6, 4], [6, 5], [6, 6]]
    assert int(grid_line_rendering['canvas_width']) == 880
    assert int(grid_line_rendering['canvas_height']) == 680
    assert str(grid_line_prompt['scene_key']).strip() == 'single_scene_counting'
    assert str(grid_line_prompt['question_text_row_at_least_shape_count']).strip()
    assert str(grid_line_prompt['question_text_column_at_least_shape_count']).strip()
    assert str(grid_line_prompt['question_text_row_exactly_shape_count']).strip()
    assert str(grid_line_prompt['question_text_column_exactly_shape_count']).strip()
    assert str(grid_line_prompt['question_text_row_no_shape_count']).strip()
    assert str(grid_line_prompt['question_text_column_no_shape_count']).strip()
    assert str(grid_line_prompt['annotation_hint']).strip()
    assert str(grid_line_prompt['answer_hint']).strip()
    assert str(grid_line_prompt['json_example']).strip()
    assert str(grid_line_prompt['json_example_answer_only']).strip()
    ring_generation, ring_rendering, ring_prompt = split_generation_rendering_prompt_defaults(
        named_ring_cfg,
        task_id='task_icons__named_ring__scoped_attribute_count',
    )
    assert int(ring_generation['ring_icon_count_min']) == 12
    assert int(ring_generation['ring_icon_count_max']) == 22
    assert int(ring_generation['answer_count_min']) == 0
    assert int(ring_generation['answer_count_max']) == 6
    assert int(ring_generation['arc_span_min']) == 3
    assert int(ring_generation['arc_span_max']) == 12
    assert int(ring_rendering['canvas_width']) == 880
    assert int(ring_rendering['canvas_height']) == 680
    assert int(ring_rendering['ring_margin_px']) == 86
    assert int(ring_rendering['marker_label_radius_px']) == 18
    assert str(ring_prompt['bundle_id']).strip() == 'icons_named_ring_v1'
    assert str(ring_prompt['scene_key']).strip() == 'single_scene_counting'
    assert str(ring_prompt['task_key']).strip() == 'counting_query'
    ring_prompt_defaults = required_group_defaults(
        ring_prompt,
        (
            'object_description',
            'question_text_clockwise_arc_shape_count',
            'question_text_counterclockwise_arc_shape_count',
            'annotation_hint',
            'answer_hint',
            'json_example',
            'json_example_answer_only',
        ),
        context='named_ring prompt defaults',
    )
    assert str(ring_prompt_defaults['question_text_clockwise_arc_shape_count']).strip()
    assert str(ring_prompt_defaults['question_text_counterclockwise_arc_shape_count']).strip()
    assert str(ring_prompt_defaults['annotation_hint']).strip()
    assert str(ring_prompt_defaults['answer_hint']).strip()
    assert str(ring_prompt_defaults['json_example']).strip()
    assert str(ring_prompt_defaults['json_example_answer_only']).strip()
    closer_generation, closer_rendering, closer_prompt = split_generation_rendering_prompt_defaults(named_cfg, task_id='task_icons__named_field__closer_to_reference_count')
    assert int(closer_generation['target_icon_count_min']) == 4
    assert int(closer_generation['target_icon_count_max']) == 8
    assert int(closer_generation['target_answer_min']) == 0
    assert int(closer_generation['target_answer_max']) == 4
    assert dict(closer_generation['queried_reference_label_weights']) == {'A': 1.0, 'B': 1.0}
    assert list(closer_generation['reference_axis_degrees']) == [0, 35, 90, 145]
    assert int(closer_rendering['canvas_width']) > 0
    assert int(closer_rendering['canvas_height']) > 0
    assert int(closer_rendering['distance_margin_px']) == 42
    assert str(closer_prompt['scene_key']).strip() == 'single_scene_counting'
    assert str(closer_prompt['question_text_closer_to_reference_count']).strip()
    assert str(closer_prompt['annotation_hint']).strip()
    assert str(closer_prompt['answer_hint']).strip()
    assert str(closer_prompt['json_example']).strip()
    assert str(closer_prompt['json_example_answer_only']).strip()
    venn_generation, venn_rendering, venn_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='task_icons__venn_field__scoped_attribute_count')
    assert int(venn_generation['object_count_min']) == 8
    assert int(venn_generation['object_count_max']) == 16
    assert int(venn_generation['target_count_min']) == 1
    assert int(venn_generation['target_count_max']) == 5
    assert sorted(venn_generation['named_venn_query_ids']) == ['inside_both_circles_count', 'inside_either_circle_count', 'inside_exactly_one_circle_count', 'outside_both_circles_count']
    assert sorted(venn_generation['target_attribute_mode_weights'].keys()) == ['color_shape', 'fill_style_shape', 'shape_only']
    assert int(venn_rendering['canvas_width']) > 0
    assert int(venn_rendering['canvas_height']) > 0
    assert int(venn_rendering['venn_boundary_margin_px']) == 12
    assert str(venn_prompt['scene_key']).strip() == 'single_scene_counting'
    assert str(venn_prompt['question_text_inside_both_circles_count']).strip()
    assert str(venn_prompt['question_text_inside_either_circle_count']).strip()
    assert str(venn_prompt['question_text_inside_exactly_one_circle_count']).strip()
    assert str(venn_prompt['question_text_outside_both_circles_count']).strip()
    assert str(venn_prompt['annotation_hint']).strip()
    assert str(venn_prompt['answer_hint']).strip()
    assert str(venn_prompt['json_example']).strip()
    assert str(venn_prompt['json_example_answer_only']).strip()

def test_icons_pair_grid_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults('icons', 'pair_grid')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['object_count_min']) == 4
    assert int(generation_shared['object_count_max']) == 9
    assert int(generation_shared['target_count_min']) == 0
    assert int(generation_shared['target_count_max']) == 4
    assert int(generation_shared['distractor_count_min']) == 1
    assert int(generation_shared['distractor_count_max']) == 9
    assert bool(generation_shared['balanced_sampling']) is True
    assert 'task_icons__pair_grid__attribute_delta_pair_count' in cfg['generation']['task_overrides']
    assert 'task_icons__pair_grid__reference_transform_match_count' in cfg['generation']['task_overrides']
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['canvas_width']) > 0
    assert int(render_shared['canvas_height']) > 0
    assert int(render_shared['reference_panel_width_px']) > 0
    assert int(render_shared['scene_icon_size_min_px']) > 0
    assert int(render_shared['scene_icon_size_max_px']) >= int(render_shared['scene_icon_size_min_px'])
    assert int(render_shared['cell_padding_px']) > 0
    assert int(render_shared['cell_label_font_size_px']) > 0
    assert int(render_shared['pair_arrow_stroke_px']) > 0
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']) == 'icons_pair_grid_v1'
    assert str(prompt_shared['scene_key']) == 'reference_pair_grid'
    assert str(prompt_shared['task_key']) == 'relation_match_count_query'
    assert str(prompt_shared['json_output_contract']).strip()
    assert str(prompt_shared['json_output_contract_answer_only']).strip()
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(cfg, task_id='task_icons__pair_grid__reference_transform_match_count')
    assert str(generation['pool_manifest']).strip() == 'non_symmetry.txt'
    assert int(generation['object_count_min']) == 6
    assert int(generation['object_count_max']) == 6
    assert list(generation['transform_ids']) == ['rot90', 'rot180', 'rot270', 'flip_h', 'flip_v', 'flip_diag_main', 'flip_diag_anti']
    assert int(generation['transform_check_size_px']) > 0
    assert int(rendering['canvas_width']) > 0
    assert int(rendering['reference_panel_width_px']) > 0
    prompt_defaults = required_group_defaults(
        prompt,
        (
            'object_description',
            'question_text',
            'annotation_hint',
            'answer_hint',
            'json_example',
            'json_example_answer_only',
        ),
        context='pair_grid reference-transform prompt defaults',
    )
    assert str(prompt_defaults['object_description']).strip()
    assert str(prompt_defaults['question_text']).strip()
    assert str(prompt_defaults['annotation_hint']).strip()
    assert str(prompt_defaults['answer_hint']).strip()
    assert str(prompt_defaults['json_example']).strip()
    assert str(prompt_defaults['json_example_answer_only']).strip()
    attribute_generation, attribute_rendering, attribute_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='task_icons__pair_grid__attribute_delta_pair_count')
    assert sorted(attribute_generation['attribute_rule_weights'].keys()) == ['color_and_size_change', 'color_only_change', 'size_only_change']
    assert bool(attribute_generation['balanced_attribute_rule_sampling']) is True
    assert float(attribute_generation['size_scale_small']) < 1.0 < float(attribute_generation['size_scale_large'])
    assert int(attribute_rendering['reference_icon_size_px']) > 0
    assert int(attribute_rendering['palette_size_min']) >= 2
    assert int(attribute_rendering['palette_size_max']) >= int(attribute_rendering['palette_size_min'])
    attribute_prompt_defaults = required_group_defaults(
        attribute_prompt,
        (
            'object_description',
            'question_text',
            'annotation_hint',
            'answer_hint',
            'json_example',
            'json_example_answer_only',
        ),
        context='pair_grid attribute-delta prompt defaults',
    )
    assert str(attribute_prompt_defaults['object_description']).strip()
    assert str(attribute_prompt_defaults['question_text']).strip()
    assert str(attribute_prompt_defaults['annotation_hint']).strip()
    assert str(attribute_prompt_defaults['answer_hint']).strip()
    assert str(attribute_prompt_defaults['json_example']).strip()
    assert str(attribute_prompt_defaults['json_example_answer_only']).strip()
    bundle = load_scene_prompt_bundle('icons', 'pair_grid', 'icons_pair_grid_v1')
    assert bundle.bundle_id == 'icons_pair_grid_v1'
    assert set(bundle.scene_templates.keys()) == {'reference_pair_grid'}
    assert set(bundle.task_templates.keys()) == {'relation_match_count_query'}

def test_icons_paired_canvas_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults('icons', 'paired_canvas')
    assert sorted(cfg['generation']['task_overrides'].keys()) == ['task_icons__paired_canvas__original_attribute_label', 'task_icons__paired_canvas__panel_attribute_change_count', 'task_icons__paired_canvas__panel_movement_direction_count', 'task_icons__paired_canvas__panel_set_relation_count']
    assert sorted(cfg['rendering']['task_overrides'].keys()) == ['task_icons__paired_canvas__original_attribute_label']
    assert sorted(cfg['prompt']['task_overrides'].keys()) == ['task_icons__paired_canvas__original_attribute_label', 'task_icons__paired_canvas__panel_attribute_change_count', 'task_icons__paired_canvas__panel_movement_direction_count', 'task_icons__paired_canvas__panel_set_relation_count']
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']) == 'icons_paired_canvas_v0'
    assert str(prompt_shared['scene_key']) == 'paired_canvas_set_relation'
    assert str(prompt_shared['task_key']) == 'paired_canvas_query'
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(cfg, task_id='task_icons__paired_canvas__panel_attribute_change_count')
    assert int(generation['object_count_min']) == 5
    assert int(generation['object_count_max']) == 10
    assert int(rendering['reference_panel_width_px']) == 516
    assert str(prompt['scene_key']) == 'paired_canvas_attribute_change'
    assert str(prompt['question_text_color_changed_count']).strip()
    assert str(prompt['question_text_size_changed_count']).strip()
    assert str(prompt['question_text_rotation_changed_count']).strip()
    bundle = load_scene_prompt_bundle('icons', 'paired_canvas', 'icons_paired_canvas_v0')
    assert bundle.bundle_id == 'icons_paired_canvas_v0'
    assert set(bundle.scene_templates.keys()) == {'paired_canvas_attribute_change', 'paired_canvas_movement_direction', 'paired_canvas_original_attribute', 'paired_canvas_set_relation'}


def test_icons_mirror_grid_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults('icons', 'mirror_grid')
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id='task_icons__mirror_grid__mirror_symmetry_match_label',
    )
    assert str(generation['pool_manifest']).strip() == 'non_symmetry.txt'
    assert list(generation['option_count_choices']) == [4, 6]
    assert int(rendering['canvas_width']) == 1104
    assert int(rendering['canvas_height']) == 640
    assert int(rendering['reference_panel_width_px']) == 296
    assert list(rendering['symmetric_icon_count_choices']) == [2, 4, 6]
    assert list(rendering['both_axes_icon_count_choices']) == [4]
    assert list(rendering['nonsymmetric_icon_count_choices']) == [2, 4, 6]
    assert int(rendering['patch_inner_margin_px']) == 8
    assert int(rendering['patch_min_gap_px']) == 6
    assert str(prompt['bundle_id']) == 'icons_mirror_grid_v1'
    assert str(prompt['scene_key']).strip() == 'reference_mirror_grid'
    assert str(prompt['task_key']).strip() == 'mirror_symmetry_match_label'


def test_icons_relation_defaults_loaded() -> None:
    cfg = get_scene_defaults('icons', 'relation')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['object_count_min']) >= 1
    assert int(generation_shared['object_count_max']) >= int(generation_shared['object_count_min'])
    assert int(generation_shared['target_count_min']) == 0
    assert int(generation_shared['target_count_max']) == 5
    assert int(generation_shared['distractor_count_min']) == 1
    assert int(generation_shared['distractor_count_max']) == 10
    assert int(generation_shared['distractor_margin_over_target']) == 1
    assert bool(generation_shared['balanced_sampling']) is True
    assert bool(generation_shared['balanced_variant_sampling']) is True
    assert 'task_icons__two_anchor__between_anchors_count' in cfg['generation']['task_overrides']
    assert 'task_icons__overlap_grid__occlusion_order_count' in cfg['generation']['task_overrides']
    assert 'task_icons__named_field__reference_distance_rank_label' not in cfg['generation']['task_overrides']
    assert 'task_icons__named_path__path_neighbor_label' not in cfg['generation']['task_overrides']
    named_cfg = get_scene_defaults('icons', 'named_field')
    assert 'task_icons__named_field__reference_distance_rank_label' in named_cfg['generation']['task_overrides']
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['canvas_width']) > 0
    assert int(render_shared['canvas_height']) > 0
    assert int(render_shared['reference_panel_width_px']) > 0
    assert int(render_shared['scene_icon_size_min_px']) > 0
    assert int(render_shared['scene_icon_size_max_px']) >= int(render_shared['scene_icon_size_min_px'])
    assert 0.0 <= float(render_shared['scene_max_overlap_fraction']) <= 1.0
    assert int(render_shared['anchor_gap_px_directional']) > 0
    assert float(render_shared['anchor_target_area_ratio_min']) > 0.0
    assert float(render_shared['anchor_target_area_ratio_max']) >= float(render_shared['anchor_target_area_ratio_min'])
    assert float(render_shared['anchor_opposite_area_ratio_min']) > 0.0
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip()
    assert str(prompt_shared['scene_key']).strip()
    assert str(prompt_shared['task_key']).strip()
    assert str(prompt_shared['json_output_contract']).strip()
    assert str(prompt_shared['json_output_contract_answer_only']).strip()
    strip_generation, strip_rendering, strip_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='task_icons__two_anchor__between_anchors_count')
    assert str(strip_generation['pool_manifest']).strip() == 'all_icons.txt'
    assert int(strip_generation['target_count_max']) == 5
    assert int(strip_generation['distractor_count_max']) == 10
    assert dict(strip_generation['strip_axis_weights']) == {'vertical': 1.0, 'horizontal': 1.0}
    assert float(strip_rendering['scene_max_overlap_fraction']) == 0.08
    assert int(strip_rendering['strip_boundary_margin_px']) == 14
    assert float(strip_rendering['strip_span_ratio_min']) == 0.32
    assert float(strip_rendering['strip_span_ratio_max']) == 0.6
    assert str(strip_prompt['scene_key']).strip() == 'scene_two_anchor_relation'
    assert str(strip_prompt['object_description']).strip()
    assert str(strip_prompt['question_text_vertical_strip']).strip()
    assert str(strip_prompt['question_text_horizontal_strip']).strip()
    assert str(strip_prompt['annotation_hint']).strip()
    assert str(strip_prompt['answer_hint']).strip()
    assert str(strip_prompt['json_example']).strip()
    assert str(strip_prompt['json_example_answer_only']).strip()
    occlusion_generation, occlusion_rendering, occlusion_prompt = split_generation_rendering_prompt_defaults(cfg, task_id='task_icons__overlap_grid__occlusion_order_count')
    assert str(occlusion_generation['pool_manifest']).strip() == 'all_icons.txt'
    assert int(occlusion_generation['object_count_min']) == 2
    assert int(occlusion_generation['object_count_max']) == 8
    assert int(occlusion_generation['target_count_max']) == 4
    assert int(occlusion_generation['distractor_count_max']) == 5
    assert int(occlusion_generation['distractor_margin_over_target']) == 0
    assert int(occlusion_rendering['canvas_width']) == 1104
    assert int(occlusion_rendering['reference_panel_width_px']) == 296
    assert float(occlusion_rendering['min_color_distance']) == 40.0
    assert float(occlusion_rendering['pair_min_color_distance']) == 80.0
    assert list(occlusion_rendering['overlap_ratio_range']) == [0.4, 0.6]
    assert str(occlusion_prompt['scene_key']).strip() == 'reference_grid_occlusion_relation'
    assert str(occlusion_prompt['object_description']).strip()
    assert str(occlusion_prompt['question_text']).strip()
    assert str(occlusion_prompt['annotation_hint']).strip()
    assert str(occlusion_prompt['answer_hint']).strip()
    assert str(occlusion_prompt['json_example']).strip()
    assert str(occlusion_prompt['json_example_answer_only']).strip()
    distance_generation, distance_rendering, distance_prompt = split_generation_rendering_prompt_defaults(named_cfg, task_id='task_icons__named_field__reference_distance_rank_label')
    assert int(distance_generation['candidate_count']) == 6
    assert int(distance_generation['distractor_count_min']) == 4
    assert int(distance_generation['distractor_count_max']) == 8
    assert dict(distance_generation['distance_rank_query_weights']) == {'closest_to_named_reference_label': 1.0, 'second_closest_to_named_reference_label': 1.0, 'farthest_from_named_reference_label': 1.0}
    assert list(distance_generation['named_icon_fill_style_support']) == ['solid', 'striped', 'dotted', 'half_filled']
    assert int(distance_rendering['canvas_width']) == 960
    assert int(distance_rendering['canvas_height']) == 560
    assert int(distance_rendering['scene_icon_size_min_px']) == 50
    assert int(distance_rendering['scene_icon_size_max_px']) == 72
    assert int(distance_rendering['distance_rank_margin_px']) == 24
    assert int(distance_rendering['candidate_label_font_size_px']) == 24
    assert str(distance_prompt['scene_key']).strip() == 'single_scene_counting'
    assert str(distance_prompt['object_description']).strip()
    assert str(distance_prompt['question_text_closest_to_named_reference_label']).strip()
    assert str(distance_prompt['question_text_second_closest_to_named_reference_label']).strip()
    assert str(distance_prompt['question_text_farthest_from_named_reference_label']).strip()
    assert str(distance_prompt['annotation_hint']).strip()
    assert str(distance_prompt['answer_hint']).strip()
    assert str(distance_prompt['json_example']).strip()
    assert str(distance_prompt['json_example_answer_only']).strip()
def test_icons_named_path_defaults_loaded() -> None:
    cfg = get_scene_defaults('icons', 'named_path')
    path_generation, path_rendering, path_prompt = split_generation_rendering_prompt_defaults(
        cfg,
        task_id='task_icons__named_path__path_neighbor_label',
    )
    assert int(path_generation['candidate_count']) == 6
    assert int(path_generation['distractor_count_min']) == 4
    assert int(path_generation['distractor_count_max']) == 8
    assert int(path_generation['target_occurrence_count_min']) == 2
    assert int(path_generation['target_occurrence_count_max']) == 4
    assert list(path_generation['named_icon_fill_style_support']) == ['solid', 'striped', 'dotted', 'half_filled']
    assert int(path_rendering['canvas_width']) == 1280
    assert int(path_rendering['canvas_height']) == 720
    assert int(path_rendering['scene_icon_size_min_px']) == 44
    assert int(path_rendering['scene_icon_size_max_px']) == 60
    assert int(path_rendering['path_stroke_width_px']) == 7
    assert int(path_rendering['candidate_label_font_size_px']) == 24
    assert str(path_prompt['bundle_id']).strip() == 'icons_named_path_v1'
    assert str(path_prompt['scene_key']).strip() == 'named_path_relation'
    assert str(path_prompt['task_key']).strip() == 'path_neighbor_query'
    prompt_defaults = required_group_defaults(
        path_prompt,
        (
            'object_description',
            'question_text_after_first_shape_label',
            'question_text_before_first_shape_label',
            'question_text_after_last_shape_label',
            'question_text_before_last_shape_label',
            'question_text_after_second_shape_label',
            'question_text_before_second_shape_label',
            'annotation_hint',
            'answer_hint',
            'json_example',
            'json_example_answer_only',
        ),
        context='named_path prompt defaults',
    )
    assert str(prompt_defaults['object_description']).strip()
    for suffix in ('after_first_shape_label', 'before_first_shape_label', 'after_last_shape_label', 'before_last_shape_label', 'after_second_shape_label', 'before_second_shape_label'):
        assert str(prompt_defaults[f'question_text_{suffix}']).strip()
    assert str(prompt_defaults['annotation_hint']).strip()
    assert str(prompt_defaults['answer_hint']).strip()
    assert str(prompt_defaults['json_example']).strip()
    assert str(prompt_defaults['json_example_answer_only']).strip()

def test_icons_sequence_defaults_loaded() -> None:
    cfg = get_scene_defaults('icons', 'sequence')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['sequence_length_min']) == 4
    assert int(generation_shared['sequence_length_max']) == 6
    assert int(generation_shared['target_count_min']) == 0
    assert int(generation_shared['target_count_max']) == 10
    assert int(generation_shared['step_abs_min']) == 1
    assert int(generation_shared['step_abs_max']) == 3
    assert bool(generation_shared['balanced_sampling']) is True
    assert 'task_icons__sequence_strip__missing_count_value' in cfg['generation']['task_overrides']
    assert 'task_icons__named_strip__shape_run_length' in cfg['generation']['task_overrides']
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['scene_icon_size_min_px']) == 24
    assert int(render_shared['scene_icon_size_max_px']) == 40
    assert float(render_shared['scene_max_overlap_fraction']) == pytest.approx(0.2, rel=1e-09)
    assert int(render_shared['cell_padding_px']) > 0
    assert int(render_shared['cell_icon_padding_px']) >= 0
    assert int(render_shared['cell_box_width_min_px']) == 112
    assert int(render_shared['cell_box_width_max_px']) == 160
    assert int(render_shared['cell_box_height_min_px']) == 96
    assert int(render_shared['cell_box_height_max_px']) == 144
    assert int(render_shared['cell_label_font_size_px']) > 0
    assert int(render_shared['missing_mark_font_size_px']) > 0
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip()
    assert str(prompt_shared['scene_key']).strip()
    assert str(prompt_shared['task_key']).strip()
    assert str(prompt_shared['json_output_contract']).strip()
    assert str(prompt_shared['json_output_contract_answer_only']).strip()
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(cfg, task_id='task_icons__sequence_strip__missing_count_value')
    assert str(generation['pool_manifest']).strip() == 'all_icons.txt'
    assert list(generation['rotation_candidates_degrees']) == [0, 90, 180, 270]
    assert int(rendering['scene_icon_size_min_px']) == 24
    assert int(rendering['scene_icon_size_max_px']) == 40
    assert str(prompt['object_description']).strip()
    assert str(prompt['question_text']).strip()
    assert str(prompt['annotation_hint']).strip()
    assert str(prompt['answer_hint']).strip()
    assert str(prompt['json_example']).strip()
    assert str(prompt['json_example_answer_only']).strip()
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(cfg, task_id='task_icons__named_strip__shape_run_length')
    assert sorted(generation['query_id_weights'].keys()) == ['longest_shape_run_length', 'shortest_shape_run_length']
    assert int(generation['strip_length_min']) == 12
    assert int(generation['strip_length_max']) == 16
    assert int(generation['longest_run_length_min']) == 2
    assert int(generation['longest_run_length_max']) == 6
    assert int(generation['shortest_run_length_min']) == 1
    assert int(generation['shortest_run_length_max']) == 5
    assert int(rendering['scene_icon_size_min_px']) == 42
    assert int(rendering['scene_icon_size_max_px']) == 58
    assert int(rendering['cell_padding_px']) == 4
    assert str(prompt['scene_key']).strip() == 'named_strip_run_length'
    assert str(prompt['task_key']).strip() == 'run_length_query'
    assert str(prompt['question_text_longest_shape_run_length']).strip()
    assert str(prompt['question_text_shortest_shape_run_length']).strip()
    assert str(prompt['annotation_hint']).strip()
    assert str(prompt['answer_hint']).strip()
    assert str(prompt['json_example']).strip()
    assert str(prompt['json_example_answer_only']).strip()

def test_icons_pattern_defaults_loaded() -> None:
    cfg = get_scene_defaults('icons', 'pattern')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['grid_rows']) == 3
    assert int(generation_shared['grid_cols']) == 3
    assert int(generation_shared['answer_index_min']) == 1
    assert int(generation_shared['answer_index_max']) == 9
    assert bool(generation_shared['balanced_sampling']) is True
    assert 'task_icons__pattern_grid__attribute_pattern_violation_index' in cfg['generation']['task_overrides']
    assert 'task_icons__sequence_strip__rotation_sequence_violation_index' in cfg['generation']['task_overrides']
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['scene_icon_size_min_px']) == 48
    assert int(render_shared['scene_icon_size_max_px']) == 72
    assert int(render_shared['cell_box_width_min_px']) == 104
    assert int(render_shared['cell_box_width_max_px']) == 140
    assert int(render_shared['cell_box_height_min_px']) == 104
    assert int(render_shared['cell_box_height_max_px']) == 140
    assert int(render_shared['scene_content_side_padding_px']) == 10
    assert int(render_shared['scene_content_bottom_padding_px']) == 10
    assert int(render_shared['scene_content_top_offset_px']) == 40
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip() == 'icons_pattern_v0'
    assert str(prompt_shared['scene_key']).strip() == 'structured_violation_scene'
    assert str(prompt_shared['task_key']).strip() == 'structured_violation_query'
    assert str(prompt_shared['json_output_contract']).strip()
    assert str(prompt_shared['json_output_contract_answer_only']).strip()
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(cfg, task_id='task_icons__sequence_strip__rotation_sequence_violation_index')
    assert str(generation['pool_manifest']).strip() == 'non_symmetry.txt'
    assert list(generation['step_candidates_degrees']) == [90, 180]
    assert int(generation['sequence_length_min']) == 10
    assert int(generation['sequence_length_max']) == 10
    assert int(generation['answer_index_max']) == 6
    assert int(rendering['scene_icon_size_min_px']) == 72
    assert int(rendering['scene_icon_size_max_px']) == 92
    assert str(prompt['object_description']).strip()
    assert str(prompt['question_text']).strip()
    generation, rendering, prompt = split_generation_rendering_prompt_defaults(cfg, task_id='task_icons__pattern_grid__attribute_pattern_violation_index')
    assert sorted(generation['query_id_weights'].keys()) == ['grid_color_violation', 'grid_size_violation']
    color_generation = generation['variant_generation_params']['grid_color_violation']
    assert str(color_generation['pool_manifest']).strip() == 'all_icons.txt'
    assert list(color_generation['color_levels']) == [0, 1, 2, 3, 4, 5, 6, 7]
    assert list(color_generation['base_color_level_candidates']) == [0, 1, 2, 3, 4, 5, 6, 7]
    assert list(color_generation['row_step_color_candidates']) == [-2, -1, 0, 1, 2]
    assert list(color_generation['col_step_color_candidates']) == [-2, -1, 0, 1, 2]
    assert list(color_generation['shared_rotation_candidates_degrees']) == [0, 90, 180, 270]
    color_rendering = rendering['variant_render_params']['grid_color_violation']
    assert int(color_rendering['scene_icon_size_min_px']) == 66
    assert int(color_rendering['scene_icon_size_max_px']) == 84
    assert int(color_rendering['palette_size_min']) == 8
    assert int(color_rendering['palette_size_max']) == 8
    assert list(color_rendering['icon_noise_edit_count_range']) == [0, 0]
    size_generation = generation['variant_generation_params']['grid_size_violation']
    assert str(size_generation['pool_manifest']).strip() == 'all_icons.txt'
    assert list(size_generation['size_levels']) == [1, 2, 3, 4, 5]
    assert list(size_generation['base_level_candidates']) == [1, 2, 3, 4, 5]
    assert list(size_generation['row_step_candidates']) == [-1, 0, 1]
    assert list(size_generation['col_step_candidates']) == [-1, 0, 1]
    assert list(size_generation['shared_rotation_candidates_degrees']) == [0, 90, 180, 270]
    size_rendering = rendering['variant_render_params']['grid_size_violation']
    assert int(size_rendering['scene_icon_size_min_px']) == 34
    assert int(size_rendering['scene_icon_size_max_px']) == 82
    assert int(size_rendering['cell_box_width_min_px']) == 116
    assert int(size_rendering['cell_box_width_max_px']) == 152
    assert int(size_rendering['cell_box_height_min_px']) == 116
    assert int(size_rendering['cell_box_height_max_px']) == 152
    assert int(size_rendering['size_level_gap_px']) == 10
    assert list(size_rendering['icon_noise_edit_count_range']) == [0, 0]
    assert str(prompt['object_description']).strip()
    assert str(prompt['question_text']).strip()
    assert str(prompt['annotation_hint']).strip()
    assert str(prompt['answer_hint']).strip()
    assert str(prompt['json_example']).strip()
    assert str(prompt['json_example_answer_only']).strip()
