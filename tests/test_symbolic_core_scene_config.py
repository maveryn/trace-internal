"""Regression tests for symbolic scene default config loading."""
from __future__ import annotations
from trace.core.scene_config import get_scene_defaults
from trace.tasks.shared.config_defaults import split_generation_rendering_prompt_defaults

def test_symbolic_abacus_defaults_loaded() -> None:
    cfg = get_scene_defaults('symbolic', 'abacus')
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_symbolic__abacus_readout__displayed_value_readout')
    assert sorted(generation_defaults['query_id_weights'].keys()) == ['displayed_value_readout']
    assert sorted(generation_defaults['scene_variant_weights'].keys()) == ['clean_card', 'wood_frame', 'worksheet']
    assert bool(generation_defaults['balanced_query_id_sampling']) is True
    assert bool(generation_defaults['balanced_scene_variant_sampling']) is True
    assert int(generation_defaults['target_answer_min']) == 0
    assert int(generation_defaults['target_answer_max']) == 999
    assert int(rendering_defaults['canvas_width']) == 980
    assert int(rendering_defaults['canvas_height']) == 760
    assert int(rendering_defaults['panel_width_px']) == 800
    assert int(rendering_defaults['panel_height_px']) == 540
    assert int(rendering_defaults['bead_width_px']) > int(rendering_defaults['bead_height_px'])
    assert str(prompt_defaults['bundle_id']).strip() == 'symbolic_abacus_v0'
    assert str(prompt_defaults['scene_key']).strip() == 'abacus_readout'
    assert str(prompt_defaults['task_key']).strip() == 'abacus_displayed_value_query'
    assert str(prompt_defaults['object_description_clean_card']).strip()
    assert str(prompt_defaults['annotation_hint']).strip()
    assert str(prompt_defaults['answer_hint']).strip()

def test_symbolic_abacus_match_panel_defaults_loaded() -> None:
    cfg = get_scene_defaults('symbolic', 'abacus')
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_symbolic__abacus_match_panel__target_value_match_label')
    assert sorted(generation_defaults['query_id_weights'].keys()) == ['target_value_match_label']
    assert sorted(generation_defaults['scene_variant_weights'].keys()) == ['clean_card', 'wood_frame', 'worksheet']
    assert list(generation_defaults['option_label_support']) == ['A', 'B', 'C', 'D', 'E', 'F']
    assert int(generation_defaults['option_count']) == 6
    assert bool(generation_defaults['balanced_correct_option_label_sampling']) is True
    assert sorted(generation_defaults['correct_option_label_weights'].keys()) == ['A', 'B', 'C', 'D', 'E', 'F']
    assert int(generation_defaults['target_value_min']) == 0
    assert int(generation_defaults['target_value_max']) == 999
    assert int(rendering_defaults['canvas_width']) == 1200
    assert int(rendering_defaults['canvas_height']) == 760
    assert int(rendering_defaults['option_card_width_px']) == 340
    assert int(rendering_defaults['option_card_height_px']) == 280
    assert int(rendering_defaults['option_bead_width_px']) > int(rendering_defaults['option_bead_height_px'])
    assert str(prompt_defaults['bundle_id']).strip() == 'symbolic_abacus_v0'
    assert str(prompt_defaults['scene_key']).strip() == 'abacus_match_panel'
    assert str(prompt_defaults['task_key']).strip() == 'abacus_target_value_match_query'
    assert str(prompt_defaults['object_description_clean_card']).strip()
    assert str(prompt_defaults['annotation_hint']).strip()
    assert str(prompt_defaults['answer_hint']).strip()

def test_symbolic_clock_defaults_loaded() -> None:
    cfg = get_scene_defaults('symbolic', 'clock')
    generation_shared = cfg['generation']['shared']
    assert sorted(generation_shared['scene_variant_weights'].keys()) == ['classic', 'minimal', 'outline']
    assert sorted(generation_shared['style_variant_weights'].keys()) == ['accented', 'marker', 'studio']
    assert sorted(generation_shared['accent_color_name_weights'].keys()) == ['blue', 'brown', 'cyan', 'green', 'magenta', 'maroon', 'orange', 'purple', 'red', 'yellow']
    assert bool(generation_shared['balanced_scene_variant_sampling']) is True
    assert bool(generation_shared['balanced_style_variant_sampling']) is True
    assert bool(generation_shared['balanced_accent_color_name_sampling']) is True
    assert int(generation_shared['hour_min']) == 1
    assert int(generation_shared['hour_max']) == 12
    assert int(generation_shared['minute_step']) == 5
    assert int(generation_shared['second_step']) == 5
    assert float(generation_shared['min_hand_angle_gap_deg']) == 10.0
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['canvas_width']) == 640
    assert int(render_shared['canvas_height']) == 640
    assert int(render_shared['face_radius_px']) > 0
    assert int(render_shared['hour_hand_width_px']) > int(render_shared['minute_hand_width_px'])
    assert int(render_shared['minute_hand_width_px']) > int(render_shared['second_hand_width_px'])
    assert int(render_shared['minor_tick_dot_radius_px']) >= 2
    assert int(render_shared['inner_ring_inset_px']) > 0
    assert int(render_shared['inner_ring_width_px']) > 0
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip() == 'symbolic_clock_v0'
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='symbolic_clock_readout_base')
    assert int(generation_defaults['hour_min']) == 1
    assert int(generation_defaults['hour_max']) == 12
    assert int(generation_defaults['minute_step']) == 5
    assert int(generation_defaults['second_step']) == 5
    assert dict(generation_defaults['delta_minutes_support']) == {'min': 5, 'max': 600, 'step': 5}
    assert dict(generation_defaults['delta_seconds_support']) == {'min': 5, 'max': 36000, 'step': 5}
    assert sorted(generation_defaults['query_id_weights'].keys()) == ['offset_time']
    assert sorted(generation_defaults['offset_unit_weights'].keys()) == ['minutes', 'seconds']
    assert sorted(generation_defaults['offset_direction_weights'].keys()) == ['after', 'before']
    assert bool(generation_defaults['balanced_query_id_sampling']) is True
    assert int(rendering_defaults['canvas_width']) == 640
    assert str(prompt_defaults['bundle_id']).strip() == 'symbolic_clock_v0'
    assert str(prompt_defaults['scene_key']).strip() == 'analog_clock'
    assert str(prompt_defaults['task_key']).strip() == 'clock_readout_query'
    assert str(prompt_defaults['object_description_classic']).strip()
    assert str(prompt_defaults['annotation_hint']).strip()
    assert str(prompt_defaults['answer_hint']).strip()

def test_symbolic_clock_compare_defaults_loaded() -> None:
    cfg = get_scene_defaults('symbolic', 'clock')
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_symbolic__clock_collection__compare')
    assert sorted(generation_defaults['query_id_weights'].keys()) == ['time_extremum_label']
    assert sorted(generation_defaults['extremum_direction_weights'].keys()) == ['earliest', 'latest']
    assert bool(generation_defaults['balanced_query_id_sampling']) is True
    assert list(generation_defaults['clock_label_support']) == ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
    assert list(generation_defaults['clock_count_support']) == [6, 7, 8, 9, 10, 11, 12]
    assert int(generation_defaults['min_compare_gap_minutes']) == 15
    assert int(rendering_defaults['canvas_width']) == 960
    assert int(rendering_defaults['canvas_height']) == 760
    assert int(rendering_defaults['face_radius_px']) == 84
    assert int(rendering_defaults['label_font_size_px']) == 28
    assert str(prompt_defaults['bundle_id']).strip() == 'symbolic_clock_v0'
    assert str(prompt_defaults['scene_key']).strip() == 'multi_analog_clock'
    assert str(prompt_defaults['task_key']).strip() == 'clock_compare_query'
    assert str(prompt_defaults['object_description_classic']).strip()
    assert str(prompt_defaults['annotation_hint']).strip()
    assert str(prompt_defaults['answer_hint']).strip()

def test_symbolic_clock_match_panel_defaults_loaded() -> None:
    cfg = get_scene_defaults('symbolic', 'clock')
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_symbolic__clock_match_panel__equivalent_time_label')
    assert sorted(generation_defaults['query_id_weights'].keys()) == ['analog_reference_digital_options', 'digital_reference_analog_options']
    assert sorted(generation_defaults['digital_display_palette_weights'].keys()) == ['blue_lcd', 'charcoal_mint', 'cream_ink', 'forest_lime', 'graphite_amber', 'navy_cyan', 'plum_ice', 'wine_rose']
    assert bool(generation_defaults['balanced_query_id_sampling']) is True
    assert bool(generation_defaults['balanced_digital_display_palette_sampling']) is True
    assert list(generation_defaults['option_label_support']) == ['A', 'B', 'C', 'D', 'E', 'F']
    assert int(generation_defaults['option_count']) == 6
    assert int(generation_defaults['min_option_gap_minutes']) == 10
    assert int(rendering_defaults['canvas_width']) == 980
    assert int(rendering_defaults['canvas_height']) == 760
    assert int(rendering_defaults['reference_clock_radius_px']) == 136
    assert int(rendering_defaults['option_clock_radius_px']) == 76
    assert int(rendering_defaults['digital_font_size_px']) == 58
    assert int(rendering_defaults['option_digital_font_size_px']) == 42
    assert str(prompt_defaults['bundle_id']).strip() == 'symbolic_clock_v0'
    assert str(prompt_defaults['scene_key']).strip() == 'clock_match_panel'
    assert str(prompt_defaults['task_key']).strip() == 'clock_match_query'
    assert str(prompt_defaults['object_description_analog_reference_digital_options']).strip()
    assert str(prompt_defaults['object_description_digital_reference_analog_options']).strip()
    assert str(prompt_defaults['annotation_hint']).strip()
    assert str(prompt_defaults['answer_hint']).strip()
