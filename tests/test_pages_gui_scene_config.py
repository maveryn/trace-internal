"""Regression tests for scene default config loading."""
from __future__ import annotations
import json
import pytest
from trace.core.scene_config import get_domain_defaults, get_scene_defaults, resolve_scene_section_defaults
from trace.tasks.shared.config_defaults import required_group_default, required_group_defaults, resolve_optional_int_bounds, resolve_required_float_bounds, resolve_required_int_bounds, split_generation_rendering_prompt_defaults
from trace.tasks.graph.shared.graph_sampling import SUPPORTED_LAYOUT_VARIANTS
FULL_NODE_LINK_LAYOUT_VARIANTS = set(SUPPORTED_LAYOUT_VARIANTS)

def test_gui_counting_defaults_loaded() -> None:
    cfg = get_scene_defaults('pages', 'counting')
    control_generation_defaults, rendering_defaults, control_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_pages__control_board__disabled_controls_in_group_count')
    row_generation_defaults, _row_rendering_defaults, row_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_pages__record_table__enabled_action_for_type_count')
    assert sorted(control_generation_defaults['query_id_weights'].keys()) == ['disabled_controls_in_group_count']
    assert sorted(row_generation_defaults['query_id_weights'].keys()) == ['enabled_action_for_type_count']
    assert bool(control_generation_defaults['balanced_query_id_sampling']) is True
    assert bool(control_generation_defaults['balanced_scene_variant_sampling']) is True
    assert bool(control_generation_defaults['balanced_style_variant_sampling']) is True
    assert bool(row_generation_defaults['balanced_query_id_sampling']) is True
    assert bool(row_generation_defaults['balanced_scene_variant_sampling']) is True
    assert bool(row_generation_defaults['balanced_style_variant_sampling']) is True
    assert list(row_generation_defaults['row_count_support']) == [9, 10, 11, 12, 13, 14, 15]
    assert list(row_generation_defaults['section_count_support']) == [2, 3]
    assert list(control_generation_defaults['answer_count_support']) == [2, 3, 4, 5, 6, 7]
    assert list(row_generation_defaults['enabled_action_for_type_count_row_count_support']) == [9, 10, 11, 12]
    assert list(row_generation_defaults['enabled_action_for_type_count_answer_count_support']) == [2, 3, 4, 5, 6]
    assert list(row_generation_defaults['size_threshold_support']) == [25, 35, 45, 55, 65]
    assert len(control_generation_defaults['candidate_label_pool']) == 26
    assert int(rendering_defaults['canvas_width']) == 1280
    assert int(rendering_defaults['canvas_height']) == 800
    assert int(rendering_defaults['badge_size_px']) == 28
    assert int(rendering_defaults['row_height_px']) == 28
    assert str(control_prompt_defaults['bundle_id']).strip() == 'pages_counting_v0'
    assert str(control_prompt_defaults['scene_key']).strip() == 'gui_control_board'
    assert str(control_prompt_defaults['task_key']).strip() == 'control_filter_count_query'
    assert str(control_prompt_defaults['answer_hint']).strip()
    assert str(control_prompt_defaults['annotation_hint']).strip()
    assert str(row_prompt_defaults['scene_key']).strip() == 'gui_table'
    assert str(row_prompt_defaults['task_key']).strip() == 'table_row_filter_count_query'
    assert str(row_prompt_defaults['answer_hint']).strip()
    assert str(row_prompt_defaults['annotation_hint']).strip()

def test_gui_relation_defaults_loaded() -> None:
    cfg = get_scene_defaults('pages', 'relation')
    nav_generation_defaults, nav_rendering_defaults, nav_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='pages_navigation_flow_path_target_source')
    assert sorted(nav_generation_defaults['query_id_weights'].keys()) == ['menu_path_target_label', 'ribbon_group_command_label']
    assert int(nav_generation_defaults['menu_command_count_min']) == 3
    assert int(nav_generation_defaults['menu_command_count_max']) == 4
    assert int(nav_generation_defaults['ribbon_tab_count_min']) == 3
    assert int(nav_generation_defaults['ribbon_tab_count_max']) == 5
    assert int(nav_generation_defaults['ribbon_group_count_min']) == 2
    assert int(nav_generation_defaults['ribbon_group_count_max']) == 3
    assert int(nav_generation_defaults['ribbon_command_count_min']) == 3
    assert int(nav_generation_defaults['ribbon_command_count_max']) == 4
    assert list(nav_generation_defaults['nav_menu_pool']) == ['File', 'Edit', 'View']
    assert list(nav_generation_defaults['nav_submenu_pool']) == ['Arrange', 'Inspect']
    assert list(nav_generation_defaults['nav_menu_group_pool']) == ['Primary', 'Advanced']
    assert list(nav_generation_defaults['nav_command_pool']) == ['Align', 'Duplicate', 'Export', 'Preview']
    assert list(nav_generation_defaults['nav_sidebar_section_pool']) == ['Workspace', 'Assets', 'Settings', 'Reports']
    assert list(nav_generation_defaults['nav_sidebar_item_pool']) == ['Overview', 'Timeline', 'Details']
    assert list(nav_generation_defaults['nav_ribbon_tab_pool']) == ['Home', 'Insert', 'Review', 'Analyze', 'Share']
    assert int(nav_rendering_defaults['canvas_width']) == 1280
    assert int(nav_rendering_defaults['canvas_height']) == 800
    assert int(nav_rendering_defaults['badge_size_px']) == 30
    assert str(nav_prompt_defaults['bundle_id']).strip() == 'pages_relation_v0'
    assert str(nav_prompt_defaults['scene_key']).strip() == 'gui_navigation_paths'
    assert str(nav_prompt_defaults['task_key']).strip() == 'navigation_path_query'
    assert str(nav_prompt_defaults['answer_hint']).strip()
    assert str(nav_prompt_defaults['annotation_hint_menu_path_target_label']).strip()
    assert str(nav_prompt_defaults['annotation_hint_sidebar_tree_target_label']).strip()
    assert str(nav_prompt_defaults['annotation_hint_ribbon_group_command_label']).strip()
    intent_generation_defaults, intent_rendering_defaults, intent_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_pages__command_matrix__command_intent_target_label')
    assert sorted(intent_generation_defaults['query_id_weights'].keys()) == ['command_intent_target_label', 'dual_guide_command_label']
    assert sorted(intent_generation_defaults['intent_category_weights'].keys()) == ['create_insert', 'edit_transform', 'format_style', 'select_choose', 'view_toggle']
    assert list(intent_generation_defaults['intent_object_pool']) == ['Document', 'Chart', 'Layer', 'File', 'Project']
    assert list(intent_generation_defaults['intent_create_insert_action_pool']) == ['Create', 'Insert', 'Import', 'Add', 'Upload']
    assert list(intent_generation_defaults['intent_select_choose_action_pool']) == ['Select', 'Choose', 'Check', 'Pick', 'Highlight']
    assert list(intent_generation_defaults['intent_view_toggle_action_pool']) == ['Show', 'Hide', 'Zoom', 'Preview', 'Expand']
    assert list(intent_generation_defaults['intent_edit_transform_action_pool']) == ['Copy', 'Delete', 'Move', 'Rotate', 'Resize']
    assert list(intent_generation_defaults['intent_format_style_action_pool']) == ['Format', 'Align', 'Color', 'Size', 'Style']
    assert int(intent_rendering_defaults['canvas_width']) == 1280
    assert int(intent_rendering_defaults['canvas_height']) == 800
    assert str(intent_prompt_defaults['bundle_id']).strip() == 'pages_relation_v0'
    assert str(intent_prompt_defaults['scene_key']).strip() == 'gui_command_intents'
    assert str(intent_prompt_defaults['task_key']).strip() == 'command_intent_query'
    assert str(intent_prompt_defaults['answer_hint']).strip()
    assert str(intent_prompt_defaults['annotation_hint_command_intent_target_label']).strip()
    assert str(intent_prompt_defaults['annotation_hint_dual_guide_command_label']).strip()
    professional_generation_defaults, professional_rendering_defaults, professional_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='pages_workspace_professional_target_source')
    assert sorted(professional_generation_defaults['query_id_weights'].keys()) == ['canvas_workspace_control_label', 'code_workspace_control_label', 'file_dialog_control_label', 'property_panel_control_label', 'toolbar_palette_control_label']
    assert int(professional_generation_defaults['context_count_min']) == 3
    assert int(professional_generation_defaults['context_count_max']) == 5
    assert int(professional_rendering_defaults['canvas_width']) == 1280
    assert int(professional_rendering_defaults['canvas_height']) == 800
    assert int(professional_rendering_defaults['badge_size_px']) == 30
    assert str(professional_prompt_defaults['bundle_id']).strip() == 'pages_relation_v0'
    assert str(professional_prompt_defaults['scene_key']).strip() == 'gui_professional_target_controls'
    assert str(professional_prompt_defaults['task_key']).strip() == 'professional_target_query'
    assert str(professional_prompt_defaults['answer_hint']).strip()
    assert str(professional_prompt_defaults['annotation_hint_toolbar_palette_control_label']).strip()
    assert str(professional_prompt_defaults['annotation_hint_property_panel_control_label']).strip()
    assert str(professional_prompt_defaults['annotation_hint_canvas_workspace_control_label']).strip()
    assert str(professional_prompt_defaults['annotation_hint_code_workspace_control_label']).strip()
    assert str(professional_prompt_defaults['annotation_hint_file_dialog_control_label']).strip()
    web_generation_defaults, web_rendering_defaults, web_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='pages_web_action_target_source')
    assert sorted(web_generation_defaults['query_id_weights'].keys()) == ['click_target_label', 'select_option_label', 'type_field_label']
    assert {'content_cms', 'finance_portal', 'learning_portal', 'shop_catalog', 'support_center', 'travel_booking'}.issubset(set(web_generation_defaults['scene_variant_weights'].keys()))
    assert int(web_generation_defaults['web_click_item_count_min']) == 4
    assert int(web_generation_defaults['web_click_item_count_max']) == 6
    assert int(web_generation_defaults['web_type_section_count_min']) == 3
    assert int(web_generation_defaults['web_select_option_count_max']) == 4
    assert list(web_generation_defaults['web_click_action_pool']) == ['Details', 'Compare', 'Save', 'Open']
    assert int(web_rendering_defaults['canvas_width']) == 1280
    assert int(web_rendering_defaults['canvas_height']) == 800
    assert int(web_rendering_defaults['browser_margin_px']) == 34
    assert int(web_rendering_defaults['instruction_height_px']) == 60
    assert str(web_prompt_defaults['bundle_id']).strip() == 'pages_relation_v0'
    assert str(web_prompt_defaults['scene_key']).strip() == 'gui_web_action_targets'
    assert str(web_prompt_defaults['task_key']).strip() == 'web_action_query'
    assert str(web_prompt_defaults['answer_hint']).strip()
    assert str(web_prompt_defaults['annotation_hint_click_target_label']).strip()
    assert str(web_prompt_defaults['annotation_hint_type_field_label']).strip()
    assert str(web_prompt_defaults['annotation_hint_select_option_label']).strip()
