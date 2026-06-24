"""Regression tests for scene default config loading."""
from __future__ import annotations
import json
import pytest
from trace.core.scene_config import get_domain_defaults, get_scene_defaults, get_scene_defaults, resolve_scene_section_defaults
from trace.tasks.shared.config_defaults import required_group_default, required_group_defaults, resolve_optional_int_bounds, resolve_required_float_bounds, resolve_required_int_bounds, split_generation_rendering_prompt_defaults, split_scene_generation_rendering_prompt_defaults
from trace.tasks.graph.shared.graph_sample_types import SUPPORTED_LAYOUT_VARIANTS
FULL_NODE_LINK_LAYOUT_VARIANTS = set(SUPPORTED_LAYOUT_VARIANTS)

def test_graph_counting_defaults_loaded() -> None:
    cfg = get_scene_defaults('graph', 'counting')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['node_count_min']) == 5
    assert int(generation_shared['node_count_max']) == 10
    assert int(generation_shared['query_degree_min']) == 0
    assert int(generation_shared['query_degree_max']) == 4
    assert int(generation_shared['target_count_min']) == 0
    assert int(generation_shared['target_count_max']) == 5
    assert int(generation_shared['degree_sequence_max_degree']) == 5
    assert set(generation_shared['topology_profile_weights'].keys()) == {'balanced', 'hub_heavy', 'low_degree'}
    assert set(generation_shared['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(generation_shared['layout_variant_weights'].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared['node_shape_variant_weights'].keys()) == {'circle', 'rounded_square', 'hexagon'}
    assert set(generation_shared['layout_transform_variant_weights'].keys()) == {'identity', 'rotate_90', 'rotate_180', 'rotate_270', 'mirror_left_right', 'mirror_up_down'}
    assert set(generation_shared['node_color_name_weights'].keys()) == {'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'brown', 'cyan', 'magenta', 'maroon'}
    assert bool(generation_shared['balanced_topology_profile_sampling']) is True
    assert bool(generation_shared['balanced_label_variant_sampling']) is True
    assert bool(generation_shared['balanced_layout_variant_sampling']) is True
    assert bool(generation_shared['balanced_node_shape_variant_sampling']) is True
    assert bool(generation_shared['balanced_layout_transform_variant_sampling']) is True
    assert bool(generation_shared['balanced_node_color_name_sampling']) is True
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['canvas_width']) > 0
    assert int(render_shared['canvas_height']) > 0
    assert int(render_shared['node_radius_min_px']) > 0
    assert int(render_shared['node_radius_max_px']) >= int(render_shared['node_radius_min_px'])
    assert int(render_shared['edge_width_px']) > 0
    assert int(render_shared['label_font_size_px']) > 0
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip()
    assert str(prompt_shared['scene_key']).strip()
    assert str(prompt_shared['task_key']).strip()
    assert str(prompt_shared['json_output_contract']).strip()
    assert str(prompt_shared['json_output_contract_answer_only']).strip()
    assert str(prompt_shared['object_description_undirected']).strip()
    assert str(prompt_shared['object_description_directed']).strip()
    assert str(prompt_shared['question_text_degree_count']).strip()
    assert str(prompt_shared['question_text_in_degree']).strip()
    assert str(prompt_shared['question_text_out_degree']).strip()
    assert str(prompt_shared['annotation_hint_degree_count']).strip()
    assert str(prompt_shared['annotation_hint_in_degree_count']).strip()
    assert str(prompt_shared['annotation_hint_out_degree_count']).strip()
    assert str(prompt_shared['answer_hint']).strip()
    assert str(prompt_shared['json_example']).strip()
    assert str(prompt_shared['json_example_answer_only']).strip()
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__degree_value_filter_count')
    assert 'query_id_weights' not in generation_defaults
    assert sorted(generation_defaults['degree_mode_weights'].keys()) == ['in_degree', 'out_degree']
    assert set(generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert bool(generation_defaults['balanced_edge_routing_variant_sampling']) is True
    assert bool(generation_defaults['balanced_degree_mode_sampling']) is True
    assert int(generation_defaults['node_count_min']) == 5
    assert int(generation_defaults['node_count_max']) == 10
    assert int(generation_defaults['directed_node_count_max']) == 10
    assert int(generation_defaults['query_degree_min']) == 0
    assert int(generation_defaults['query_degree_max']) == 4
    assert int(generation_defaults['directed_degree_sequence_max_degree']) == 4
    assert int(rendering_defaults['canvas_width']) > 0
    assert int(rendering_defaults['node_radius_min_px']) > 0
    assert int(rendering_defaults['arrow_length_px']) > 0
    assert int(rendering_defaults['arrow_width_px']) > 0
    assert str(prompt_defaults['bundle_id']).strip() == 'graph_counting_v0'
    assert str(prompt_defaults['scene_key']).strip() == 'single_graph_counting'
    assert str(prompt_defaults['task_key']).strip() == 'degree_count_query'
    assert str(prompt_defaults['object_description_undirected']).strip()
    assert str(prompt_defaults['object_description_directed']).strip()
    assert str(prompt_defaults['question_text_degree_count']).strip()
    assert str(prompt_defaults['question_text_in_degree']).strip()
    assert str(prompt_defaults['question_text_out_degree']).strip()
    named_degree_generation_defaults, named_degree_rendering_defaults, named_degree_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__named_node_degree_value')
    assert sorted(named_degree_generation_defaults['graph_directionality_weights'].keys()) == ['directed', 'undirected']
    assert sorted(named_degree_generation_defaults['degree_mode_weights'].keys()) == ['in_degree', 'out_degree', 'total_degree']
    assert set(named_degree_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(named_degree_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert bool(named_degree_generation_defaults['balanced_graph_directionality_sampling']) is True
    assert bool(named_degree_generation_defaults['balanced_degree_mode_sampling']) is True
    assert int(named_degree_generation_defaults['node_count_min']) == 5
    assert int(named_degree_generation_defaults['node_count_max']) == 10
    assert int(named_degree_generation_defaults['directed_node_count_max']) == 10
    assert int(named_degree_generation_defaults['target_degree_min']) == 0
    assert int(named_degree_generation_defaults['target_degree_max']) == 4
    assert int(named_degree_rendering_defaults['canvas_width']) > 0
    assert int(named_degree_rendering_defaults['node_radius_min_px']) > 0
    assert str(named_degree_prompt_defaults['bundle_id']).strip() == 'graph_counting_v0'
    assert str(named_degree_prompt_defaults['scene_key']).strip() == 'single_graph_counting'
    assert str(named_degree_prompt_defaults['task_key']).strip() == 'named_node_degree_value_query'
    assert str(named_degree_prompt_defaults['object_description_undirected']).strip()
    assert str(named_degree_prompt_defaults['object_description_directed']).strip()
    assert str(named_degree_prompt_defaults['annotation_hint_named_node_degree_value']).strip()
    assert str(named_degree_prompt_defaults['annotation_hint_named_node_in_degree_value']).strip()
    assert str(named_degree_prompt_defaults['annotation_hint_named_node_out_degree_value']).strip()
    assert str(named_degree_prompt_defaults['annotation_hint_named_node_total_degree_value']).strip()
    source_sink_generation_defaults, source_sink_rendering_defaults, source_sink_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='graph_node_link_source_sink_count_internal')
    assert sorted(source_sink_generation_defaults['source_sink_mode_weights'].keys()) == ['sink', 'source']
    assert set(source_sink_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(source_sink_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert bool(source_sink_generation_defaults['balanced_source_sink_mode_sampling']) is True
    assert bool(source_sink_generation_defaults['balanced_target_count_sampling']) is True
    assert int(source_sink_generation_defaults['target_count_min']) == 0
    assert int(source_sink_generation_defaults['target_count_max']) == 4
    assert int(source_sink_generation_defaults['query_degree_min']) == 0
    assert int(source_sink_generation_defaults['query_degree_max']) == 0
    assert int(source_sink_rendering_defaults['canvas_width']) > 0
    assert str(source_sink_prompt_defaults['bundle_id']).strip() == 'graph_counting_v0'
    assert str(source_sink_prompt_defaults['scene_key']).strip() == 'single_graph_counting'
    assert str(source_sink_prompt_defaults['task_key']).strip() == 'source_sink_count_query'
    assert str(source_sink_prompt_defaults['object_description_directed']).strip()
    assert str(source_sink_prompt_defaults['annotation_hint_source_count']).strip()
    assert str(source_sink_prompt_defaults['annotation_hint_sink_count']).strip()
    node_color_generation_defaults, node_color_rendering_defaults, node_color_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__node_color_count')
    assert sorted(node_color_generation_defaults['graph_directionality_weights'].keys()) == ['directed', 'undirected']
    assert set(node_color_generation_defaults['target_color_name_weights'].keys()) == {'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'brown', 'cyan', 'magenta', 'maroon'}
    assert set(node_color_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(node_color_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert bool(node_color_generation_defaults['balanced_graph_directionality_sampling']) is True
    assert bool(node_color_generation_defaults['balanced_target_color_name_sampling']) is True
    assert bool(node_color_generation_defaults['balanced_target_count_sampling']) is True
    assert int(node_color_generation_defaults['node_count_min']) == 8
    assert int(node_color_generation_defaults['node_count_max']) == 12
    assert int(node_color_generation_defaults['directed_node_count_max']) == 12
    assert int(node_color_generation_defaults['target_count_min']) == 3
    assert int(node_color_generation_defaults['target_count_max']) == 7
    assert int(node_color_rendering_defaults['canvas_width']) > 0
    assert str(node_color_prompt_defaults['bundle_id']).strip() == 'graph_counting_v0'
    assert str(node_color_prompt_defaults['scene_key']).strip() == 'single_graph_counting'
    assert str(node_color_prompt_defaults['task_key']).strip() == 'node_color_count_query'
    assert str(node_color_prompt_defaults['object_description_undirected']).strip()
    assert str(node_color_prompt_defaults['object_description_directed']).strip()
    edge_color_generation_defaults, edge_color_rendering_defaults, edge_color_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__edge_color_count')
    assert sorted(edge_color_generation_defaults['graph_directionality_weights'].keys()) == ['directed', 'undirected']
    assert set(edge_color_generation_defaults['target_color_name_weights'].keys()) == {'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'brown', 'cyan', 'magenta', 'maroon'}
    assert set(edge_color_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(edge_color_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert bool(edge_color_generation_defaults['balanced_graph_directionality_sampling']) is True
    assert bool(edge_color_generation_defaults['balanced_target_color_name_sampling']) is True
    assert bool(edge_color_generation_defaults['balanced_target_count_sampling']) is True
    assert int(edge_color_generation_defaults['target_count_min']) == 0
    assert int(edge_color_generation_defaults['target_count_max']) == 8
    assert int(edge_color_rendering_defaults['edge_width_px']) == 5
    assert str(edge_color_prompt_defaults['bundle_id']).strip() == 'graph_counting_v0'
    assert str(edge_color_prompt_defaults['scene_key']).strip() == 'single_graph_counting'
    assert str(edge_color_prompt_defaults['task_key']).strip() == 'edge_color_count_query'
    assert str(edge_color_prompt_defaults['object_description_undirected']).strip()
    assert str(edge_color_prompt_defaults['object_description_directed']).strip()
    isolated_removal_generation_defaults, isolated_removal_rendering_defaults, isolated_removal_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__isolated_after_removal_count')
    assert sorted(isolated_removal_generation_defaults['graph_directionality_weights'].keys()) == ['directed', 'undirected']
    assert set(isolated_removal_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(isolated_removal_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert bool(isolated_removal_generation_defaults['balanced_graph_directionality_sampling']) is True
    assert bool(isolated_removal_generation_defaults['balanced_target_count_sampling']) is True
    assert int(isolated_removal_generation_defaults['target_count_min']) == 0
    assert int(isolated_removal_generation_defaults['target_count_max']) == 5
    assert int(isolated_removal_rendering_defaults['canvas_width']) > 0
    assert str(isolated_removal_prompt_defaults['bundle_id']).strip() == 'graph_counting_v0'
    assert str(isolated_removal_prompt_defaults['scene_key']).strip() == 'single_graph_counting'
    assert str(isolated_removal_prompt_defaults['task_key']).strip() == 'isolated_node_count_after_node_removal_query'
    assert str(isolated_removal_prompt_defaults['object_description_undirected']).strip()
    assert str(isolated_removal_prompt_defaults['object_description_directed']).strip()
    articulation_generation_defaults, articulation_rendering_defaults, articulation_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__articulation_point_count')
    assert 'query_id_weights' not in articulation_generation_defaults
    assert set(articulation_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(articulation_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert int(articulation_generation_defaults['node_count_min']) == 5
    assert int(articulation_generation_defaults['node_count_max']) == 10
    assert int(articulation_generation_defaults['target_count_min']) == 0
    assert int(articulation_generation_defaults['target_count_max']) == 5
    assert int(articulation_rendering_defaults['canvas_width']) > 0
    assert int(articulation_rendering_defaults['node_radius_min_px']) > 0
    assert str(articulation_prompt_defaults['bundle_id']).strip() == 'graph_counting_v0'
    assert str(articulation_prompt_defaults['scene_key']).strip() == 'single_graph_counting'
    assert str(articulation_prompt_defaults['task_key']).strip() == 'articulation_point_count_query'
    assert str(articulation_prompt_defaults['question_text_articulation_point_count']).strip()
    bridge_generation_defaults, bridge_rendering_defaults, bridge_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__bridge_count')
    assert 'query_id_weights' not in bridge_generation_defaults
    assert set(bridge_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(bridge_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert int(bridge_generation_defaults['node_count_min']) == 5
    assert int(bridge_generation_defaults['node_count_max']) == 10
    assert int(bridge_generation_defaults['target_count_min']) == 0
    assert int(bridge_generation_defaults['target_count_max']) == 5
    assert int(bridge_rendering_defaults['canvas_width']) > 0
    assert int(bridge_rendering_defaults['node_radius_min_px']) > 0
    assert str(bridge_prompt_defaults['bundle_id']).strip() == 'graph_counting_v0'
    assert str(bridge_prompt_defaults['scene_key']).strip() == 'single_graph_counting'
    assert str(bridge_prompt_defaults['task_key']).strip() == 'bridge_count_query'
    assert str(bridge_prompt_defaults['question_text_bridge_count']).strip()

def test_graph_relation_defaults_loaded() -> None:
    cfg = get_scene_defaults('graph', 'relation')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['node_count_min']) == 6
    assert int(generation_shared['node_count_max']) == 15
    assert int(generation_shared['component_count_min']) == 2
    assert int(generation_shared['component_count_max']) == 4
    assert int(generation_shared['target_component_size_min']) == 2
    assert int(generation_shared['target_component_size_max']) == 7
    assert set(generation_shared['topology_profile_weights'].keys()) == {'balanced', 'hub_heavy', 'low_degree'}
    assert set(generation_shared['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(generation_shared['layout_variant_weights'].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared['node_shape_variant_weights'].keys()) == {'circle', 'rounded_square', 'hexagon'}
    assert set(generation_shared['layout_transform_variant_weights'].keys()) == {'identity', 'rotate_90', 'rotate_180', 'rotate_270', 'mirror_left_right', 'mirror_up_down'}
    assert set(generation_shared['node_color_name_weights'].keys()) == {'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'brown', 'cyan', 'magenta', 'maroon'}
    assert bool(generation_shared['balanced_topology_profile_sampling']) is True
    assert bool(generation_shared['balanced_label_variant_sampling']) is True
    assert bool(generation_shared['balanced_layout_variant_sampling']) is True
    assert bool(generation_shared['balanced_node_shape_variant_sampling']) is True
    assert bool(generation_shared['balanced_layout_transform_variant_sampling']) is True
    assert bool(generation_shared['balanced_node_color_name_sampling']) is True
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['canvas_width']) > 0
    assert int(render_shared['canvas_height']) > 0
    assert int(render_shared['node_radius_min_px']) > 0
    assert int(render_shared['node_radius_max_px']) >= int(render_shared['node_radius_min_px'])
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip() == 'graph_relation_v0'
    assert str(prompt_shared['scene_key']).strip() == 'single_graph_relation'
    assert str(prompt_shared['task_key']).strip() == 'same_component_count_query'
    assert str(prompt_shared['object_description']).strip()
    assert str(prompt_shared['object_description_directed']).strip()
    assert str(prompt_shared['question_text_same_component_count']).strip()
    assert str(prompt_shared['annotation_hint']).strip()
    assert str(prompt_shared['answer_hint']).strip()
    assert str(prompt_shared['json_example']).strip()
    assert str(prompt_shared['json_example_answer_only']).strip()
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='graph_node_link_same_component_count_internal')
    assert 'query_id_weights' not in generation_defaults
    assert set(generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert int(generation_defaults['node_count_min']) == 6
    assert int(generation_defaults['node_count_max']) == 15
    assert int(generation_defaults['component_count_min']) == 2
    assert int(generation_defaults['component_count_max']) == 4
    assert int(generation_defaults['target_component_size_min']) == 2
    assert int(generation_defaults['target_component_size_max']) == 7
    assert int(rendering_defaults['canvas_width']) > 0
    assert int(rendering_defaults['node_radius_min_px']) > 0
    assert str(prompt_defaults['bundle_id']).strip() == 'graph_relation_v0'
    assert str(prompt_defaults['scene_key']).strip() == 'single_graph_relation'
    assert str(prompt_defaults['task_key']).strip() == 'same_component_count_query'
    assert str(prompt_defaults['question_text_same_component_count']).strip()
    reachable_generation_defaults, reachable_rendering_defaults, reachable_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__reachable_count')
    assert 'query_id_weights' not in reachable_generation_defaults
    assert set(reachable_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(reachable_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert int(reachable_generation_defaults['node_count_min']) == 5
    assert int(reachable_generation_defaults['directed_node_count_max']) == 9
    assert int(reachable_generation_defaults['target_reachable_count_min']) == 1
    assert int(reachable_generation_defaults['target_reachable_count_max']) == 6
    assert int(reachable_rendering_defaults['canvas_width']) > 0
    assert int(reachable_rendering_defaults['node_radius_min_px']) > 0
    assert str(reachable_prompt_defaults['bundle_id']).strip() == 'graph_relation_v0'
    assert str(reachable_prompt_defaults['scene_key']).strip() == 'single_graph_relation'
    assert str(reachable_prompt_defaults['task_key']).strip() == 'reachable_count_query'
    assert str(reachable_prompt_defaults['object_description_directed']).strip()
    assert str(reachable_prompt_defaults['question_text_reachable_count']).strip()
    assert str(reachable_prompt_defaults['annotation_hint_reachable_count']).strip()
    reachable_edge_edit_generation_defaults, reachable_edge_edit_rendering_defaults, reachable_edge_edit_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__reachable_count_after_edge_edit')
    assert sorted(reachable_edge_edit_generation_defaults['edge_edit_operation_weights'].keys()) == ['edge_addition', 'edge_removal']
    assert set(reachable_edge_edit_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(reachable_edge_edit_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert bool(reachable_edge_edit_generation_defaults['balanced_edge_edit_operation_sampling']) is True
    assert bool(reachable_edge_edit_generation_defaults['balanced_target_reachable_count_sampling']) is True
    assert int(reachable_edge_edit_generation_defaults['node_count_min']) == 5
    assert int(reachable_edge_edit_generation_defaults['directed_node_count_max']) == 10
    assert int(reachable_edge_edit_generation_defaults['target_reachable_count_min']) == 1
    assert int(reachable_edge_edit_generation_defaults['target_reachable_count_max']) == 8
    assert int(reachable_edge_edit_rendering_defaults['canvas_width']) > 0
    assert int(reachable_edge_edit_rendering_defaults['node_radius_min_px']) > 0
    assert str(reachable_edge_edit_prompt_defaults['bundle_id']).strip() == 'graph_relation_v0'
    assert str(reachable_edge_edit_prompt_defaults['scene_key']).strip() == 'single_graph_relation'
    assert str(reachable_edge_edit_prompt_defaults['task_key']).strip() == 'reachable_count_after_edge_edit_query'
    assert str(reachable_edge_edit_prompt_defaults['object_description_directed']).strip()
    assert str(reachable_edge_edit_prompt_defaults['annotation_hint_reachable_count_after_edge_removal']).strip()
    assert str(reachable_edge_edit_prompt_defaults['annotation_hint_reachable_count_after_edge_addition']).strip()
    common_generation_defaults, common_rendering_defaults, common_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__common_related_node_count')
    assert sorted(common_generation_defaults['common_neighbor_mode_weights'].keys()) == ['directed_common_predecessor', 'directed_common_successor', 'undirected_common_neighbor']
    assert set(common_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(common_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert bool(common_generation_defaults['balanced_common_neighbor_mode_sampling']) is True
    assert bool(common_generation_defaults['balanced_target_count_sampling']) is True
    assert int(common_generation_defaults['node_count_min']) == 6
    assert int(common_generation_defaults['node_count_max']) == 10
    assert int(common_generation_defaults['directed_node_count_max']) == 10
    assert int(common_generation_defaults['target_count_min']) == 0
    assert int(common_generation_defaults['target_count_max']) == 4
    assert int(common_rendering_defaults['canvas_width']) > 0
    assert int(common_rendering_defaults['node_radius_min_px']) > 0
    assert str(common_prompt_defaults['bundle_id']).strip() == 'graph_relation_v0'
    assert str(common_prompt_defaults['scene_key']).strip() == 'single_graph_relation'
    assert str(common_prompt_defaults['task_key']).strip() == 'common_neighbor_count_query'
    assert str(common_prompt_defaults['object_description']).strip()
    assert str(common_prompt_defaults['object_description_directed']).strip()
    assert str(common_prompt_defaults['annotation_hint_common_neighbor_count']).strip()
    assert str(common_prompt_defaults['annotation_hint_common_successor_count']).strip()
    assert str(common_prompt_defaults['annotation_hint_common_predecessor_count']).strip()
    edge_attribute_generation_defaults, edge_attribute_rendering_defaults, edge_attribute_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__edge_between_nodes_label')
    assert sorted(edge_attribute_generation_defaults['graph_directionality_weights'].keys()) == ['directed', 'undirected']
    assert int(edge_attribute_generation_defaults['edge_label_support_size']) == 16
    assert int(edge_attribute_generation_defaults['edge_label_min_chars']) == 3
    assert int(edge_attribute_generation_defaults['edge_label_max_chars']) == 5
    assert int(edge_attribute_generation_defaults['max_labeled_edge_count']) == 12
    assert 'query_id_weights' not in edge_attribute_generation_defaults
    assert set(edge_attribute_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(edge_attribute_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert 'balanced_query_id_sampling' not in edge_attribute_generation_defaults
    assert bool(edge_attribute_generation_defaults['balanced_target_edge_label_sampling']) is True
    assert int(edge_attribute_generation_defaults['node_count_min']) == 5
    assert int(edge_attribute_generation_defaults['node_count_max']) == 8
    assert int(edge_attribute_generation_defaults['directed_node_count_max']) == 8
    assert int(edge_attribute_rendering_defaults['canvas_width']) > 0
    assert int(edge_attribute_rendering_defaults['node_radius_min_px']) > 0
    assert str(edge_attribute_prompt_defaults['bundle_id']).strip() == 'graph_relation_v0'
    assert str(edge_attribute_prompt_defaults['scene_key']).strip() == 'single_graph_relation'
    assert str(edge_attribute_prompt_defaults['task_key']).strip() == 'edge_attribute_label_query'
    assert str(edge_attribute_prompt_defaults['object_description_undirected']).strip()
    assert str(edge_attribute_prompt_defaults['object_description_directed']).strip()
    assert str(edge_attribute_prompt_defaults['annotation_hint_edge_between_nodes_label']).strip()
    assert str(edge_attribute_prompt_defaults['annotation_hint_directed_edge_between_nodes_label']).strip()
    edge_edit_generation_defaults, edge_edit_rendering_defaults, edge_edit_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='graph_node_link_component_size_after_edge_edit_internal')
    assert sorted(edge_edit_generation_defaults['edge_edit_operation_weights'].keys()) == ['edge_addition', 'edge_removal']
    assert set(edge_edit_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(edge_edit_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert bool(edge_edit_generation_defaults['balanced_edge_edit_operation_sampling']) is True
    assert bool(edge_edit_generation_defaults['balanced_target_component_size_sampling']) is True
    assert int(edge_edit_generation_defaults['node_count_min']) == 5
    assert int(edge_edit_generation_defaults['node_count_max']) == 12
    assert int(edge_edit_generation_defaults['target_component_size_min']) == 1
    assert int(edge_edit_generation_defaults['target_component_size_max']) == 8
    assert int(edge_edit_rendering_defaults['canvas_width']) > 0
    assert int(edge_edit_rendering_defaults['node_radius_min_px']) > 0
    assert str(edge_edit_prompt_defaults['bundle_id']).strip() == 'graph_relation_v0'
    assert str(edge_edit_prompt_defaults['scene_key']).strip() == 'single_graph_relation'
    assert str(edge_edit_prompt_defaults['task_key']).strip() == 'component_size_after_edge_edit_query'
    assert str(edge_edit_prompt_defaults['object_description']).strip()
    assert str(edge_edit_prompt_defaults['annotation_hint_component_size_after_edge_removal']).strip()
    assert str(edge_edit_prompt_defaults['annotation_hint_component_size_after_edge_addition']).strip()
    cycle_generation_defaults, cycle_rendering_defaults, cycle_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__unique_cycle_size')
    assert 'query_id_weights' not in cycle_generation_defaults
    assert set(cycle_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(cycle_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert int(cycle_generation_defaults['node_count_min']) == 5
    assert int(cycle_generation_defaults['node_count_max']) == 10
    assert int(cycle_generation_defaults['target_cycle_size_min']) == 3
    assert int(cycle_generation_defaults['target_cycle_size_max']) == 7
    assert int(cycle_rendering_defaults['canvas_width']) > 0
    assert int(cycle_rendering_defaults['node_radius_min_px']) > 0
    assert str(cycle_prompt_defaults['bundle_id']).strip() == 'graph_relation_v0'
    assert str(cycle_prompt_defaults['scene_key']).strip() == 'single_graph_relation'
    assert str(cycle_prompt_defaults['task_key']).strip() == 'unique_cycle_size_query'
    assert str(cycle_prompt_defaults['question_text_unique_cycle_size']).strip()
    chordless_cycle_generation_defaults, chordless_cycle_rendering_defaults, chordless_cycle_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__largest_chordless_cycle_size')
    assert 'query_id_weights' not in chordless_cycle_generation_defaults
    assert set(chordless_cycle_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(chordless_cycle_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert int(chordless_cycle_generation_defaults['node_count_min']) == 8
    assert int(chordless_cycle_generation_defaults['node_count_max']) == 10
    assert int(chordless_cycle_generation_defaults['target_cycle_size_min']) == 3
    assert int(chordless_cycle_generation_defaults['target_cycle_size_max']) == 7
    assert int(chordless_cycle_rendering_defaults['canvas_width']) > 0
    assert int(chordless_cycle_rendering_defaults['node_radius_min_px']) > 0
    assert str(chordless_cycle_prompt_defaults['bundle_id']).strip() == 'graph_relation_v0'
    assert str(chordless_cycle_prompt_defaults['scene_key']).strip() == 'single_graph_relation'
    assert str(chordless_cycle_prompt_defaults['task_key']).strip() == 'largest_chordless_cycle_size_query'
    assert str(chordless_cycle_prompt_defaults['question_text_largest_chordless_cycle_size']).strip()
    hamiltonian_generation_defaults, hamiltonian_rendering_defaults, hamiltonian_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__hamiltonian_cycle_neighbor_label')
    assert 'query_id_weights' not in hamiltonian_generation_defaults
    assert set(hamiltonian_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(hamiltonian_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert int(hamiltonian_generation_defaults['node_count_min']) == 4
    assert int(hamiltonian_generation_defaults['node_count_max']) == 6
    assert int(hamiltonian_rendering_defaults['canvas_width']) > 0
    assert int(hamiltonian_rendering_defaults['node_radius_min_px']) > 0
    assert str(hamiltonian_prompt_defaults['bundle_id']).strip() == 'graph_relation_v0'
    assert str(hamiltonian_prompt_defaults['scene_key']).strip() == 'single_graph_relation'
    assert str(hamiltonian_prompt_defaults['task_key']).strip() == 'hamiltonian_cycle_neighbor_label_query'
    assert str(hamiltonian_prompt_defaults['question_text_next_in_hamiltonian_cycle_label']).strip()
    assert str(hamiltonian_prompt_defaults['question_text_previous_in_hamiltonian_cycle_label']).strip()

def test_graph_pedigree_chart_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults('graph', 'pedigree_chart')
    relationship_generation, relationship_rendering, relationship_prompt = split_scene_generation_rendering_prompt_defaults(cfg, task_id='task_graph__pedigree_chart__relationship_label')
    assert 'query_id_weights' not in relationship_generation
    assert sorted(relationship_generation['relationship_label_weights'].keys()) == ['child', 'grandchild', 'grandparent', 'parent', 'partner', 'sibling']
    assert sorted(relationship_generation['scene_variant_weights'].keys()) == ['classic_pedigree', 'paper_pedigree', 'row_guided_pedigree']
    assert int(relationship_rendering['canvas_width']) == 980
    assert int(relationship_rendering['canvas_height']) == 700
    assert str(relationship_prompt['bundle_id']) == 'graph_pedigree_chart_v1'
    assert 'scene_key' not in relationship_prompt
    assert 'task_key' not in relationship_prompt
    assert 'annotation_hint' not in relationship_prompt
    relatedness_generation, _, relatedness_prompt = split_scene_generation_rendering_prompt_defaults(cfg, task_id='task_graph__pedigree_chart__relatedness_coefficient_label')
    assert 'query_id_weights' not in relatedness_generation
    assert sorted(relatedness_generation['relatedness_label_weights'].keys()) == ['0', '1/2', '1/4', '1/8', '3/8']
    assert str(relatedness_prompt['bundle_id']) == 'graph_pedigree_chart_v1'
    assert 'scene_key' not in relatedness_prompt
    assert 'task_key' not in relatedness_prompt
    assert 'annotation_hint' not in relatedness_prompt

def test_graph_phylogeny_tree_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults('graph', 'phylogeny_tree')
    clade_generation, clade_rendering, clade_prompt = split_scene_generation_rendering_prompt_defaults(cfg, task_id='task_graph__phylogeny_tree__clade_leaf_count')
    assert 'query_id_weights' not in clade_generation
    assert sorted(clade_generation['scene_variant_weights'].keys()) == ['diagonal_cladogram', 'paper_cladogram', 'rectangular_cladogram']
    assert int(clade_generation['target_clade_leaf_count_min']) == 2
    assert int(clade_generation['target_clade_leaf_count_max']) == 6
    assert int(clade_rendering['canvas_width']) == 920
    assert int(clade_rendering['canvas_height']) == 660
    assert str(clade_prompt['bundle_id']) == 'graph_phylogeny_tree_v1'
    assert 'scene_key' not in clade_prompt
    assert 'task_key' not in clade_prompt
    assert 'annotation_hint' not in clade_prompt
    topology_generation, topology_rendering, topology_prompt = split_scene_generation_rendering_prompt_defaults(cfg, task_id='task_graph__phylogeny_tree__topology_outlier_label')
    assert 'query_id_weights' not in topology_generation
    assert int(topology_generation['option_count']) == 6
    assert int(topology_rendering['canvas_width']) == 1260
    assert int(topology_rendering['canvas_height']) == 920
    assert str(topology_prompt['bundle_id']) == 'graph_phylogeny_tree_v1'
    assert 'scene_key' not in topology_prompt
    assert 'task_key' not in topology_prompt

def test_graph_automaton_scene_defaults_loaded() -> None:
    cfg = get_scene_defaults('graph', 'automaton')
    state_generation, state_rendering, state_prompt = split_scene_generation_rendering_prompt_defaults(cfg, task_id='task_graph__automaton__state_after_input_label')
    assert 'query_id_weights' not in state_generation
    assert sorted(state_generation['layout_variant_weights'].keys()) == ['circular', 'layered', 'path_spine', 'shell', 'spring']
    assert int(state_generation['state_count_min']) == 4
    assert int(state_generation['state_count_max']) == 6
    assert int(state_rendering['canvas_width']) == 864
    assert int(state_rendering['canvas_height']) == 640
    assert str(state_prompt['bundle_id']) == 'automaton_v1'
    assert str(state_prompt['task_key']) == 'state_after_input_label_query'
    assert not any((str(key).startswith('annotation_hint') for key in state_prompt))
    dfa_generation, dfa_rendering, dfa_prompt = split_scene_generation_rendering_prompt_defaults(cfg, task_id='task_graph__automaton__dfa_accepted_string_label')
    assert 'query_id_weights' not in dfa_generation
    assert int(dfa_generation['candidate_count']) == 6
    assert int(dfa_rendering['option_panel_height_px']) == 150
    assert str(dfa_prompt['bundle_id']) == 'automaton_v1'
    assert str(dfa_prompt['task_key']) == 'accepted_string_label_query'
    nondet_generation, _, nondet_prompt = split_scene_generation_rendering_prompt_defaults(cfg, task_id='task_graph__automaton__nondeterministic_state_count')
    assert 'query_id_weights' not in nondet_generation
    assert int(nondet_generation['target_count_min']) == 0
    assert int(nondet_generation['target_count_max']) == 5
    assert str(nondet_prompt['bundle_id']) == 'automaton_v1'
    assert str(nondet_prompt['task_key']) == 'nondeterministic_state_count_query'

def test_graph_comparison_defaults_loaded() -> None:
    cfg = get_scene_defaults('graph', 'comparison')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['node_count_min']) == 6
    assert int(generation_shared['node_count_max']) == 15
    assert int(generation_shared['component_count_min']) == 2
    assert int(generation_shared['component_count_max']) == 4
    assert int(generation_shared['target_largest_component_size_min']) == 3
    assert int(generation_shared['target_largest_component_size_max']) == 9
    assert set(generation_shared['topology_profile_weights'].keys()) == {'balanced', 'hub_heavy', 'low_degree'}
    assert set(generation_shared['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(generation_shared['layout_variant_weights'].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared['node_shape_variant_weights'].keys()) == {'circle', 'rounded_square', 'hexagon'}
    assert set(generation_shared['layout_transform_variant_weights'].keys()) == {'identity', 'rotate_90', 'rotate_180', 'rotate_270', 'mirror_left_right', 'mirror_up_down'}
    assert set(generation_shared['node_color_name_weights'].keys()) == {'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'brown', 'cyan', 'magenta', 'maroon'}
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip() == 'graph_comparison_v0'
    assert str(prompt_shared['scene_key']).strip() == 'single_graph_comparison'
    assert str(prompt_shared['task_key']).strip() == 'largest_component_size_query'
    assert str(prompt_shared['object_description']).strip()
    assert str(prompt_shared['question_text_largest_component_size']).strip()
    assert str(prompt_shared['annotation_hint']).strip()
    assert str(prompt_shared['answer_hint']).strip()
    assert str(prompt_shared['json_example']).strip()
    assert str(prompt_shared['json_example_answer_only']).strip()
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='graph_node_link_largest_component_size_internal')
    assert 'query_id_weights' not in generation_defaults
    assert set(generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert int(generation_defaults['node_count_min']) == 6
    assert int(generation_defaults['node_count_max']) == 15
    assert int(generation_defaults['component_count_min']) == 2
    assert int(generation_defaults['component_count_max']) == 4
    assert int(generation_defaults['target_largest_component_size_min']) == 3
    assert int(generation_defaults['target_largest_component_size_max']) == 9
    assert int(rendering_defaults['canvas_width']) > 0
    assert int(rendering_defaults['node_radius_min_px']) > 0
    assert str(prompt_defaults['bundle_id']).strip() == 'graph_comparison_v0'
    assert str(prompt_defaults['scene_key']).strip() == 'single_graph_comparison'
    assert str(prompt_defaults['task_key']).strip() == 'largest_component_size_query'
    assert str(prompt_defaults['question_text_largest_component_size']).strip()
    extreme_generation_defaults, extreme_rendering_defaults, extreme_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__degree_extremum_value')
    assert 'query_id_weights' not in extreme_generation_defaults
    assert set(extreme_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(extreme_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert 'balanced_query_id_sampling' not in extreme_generation_defaults
    assert int(extreme_generation_defaults['node_count_min']) == 5
    assert int(extreme_generation_defaults['node_count_max']) == 10
    assert int(extreme_generation_defaults['directed_node_count_max']) == 10
    assert int(extreme_generation_defaults['target_degree_min']) == 0
    assert int(extreme_generation_defaults['target_degree_max']) == 4
    assert int(extreme_rendering_defaults['canvas_width']) > 0
    assert int(extreme_rendering_defaults['node_radius_min_px']) > 0
    assert str(extreme_prompt_defaults['bundle_id']).strip() == 'graph_comparison_v0'
    assert str(extreme_prompt_defaults['scene_key']).strip() == 'single_graph_comparison'
    assert str(extreme_prompt_defaults['task_key']).strip() == 'extreme_degree_value_query'
    assert str(extreme_prompt_defaults['object_description_undirected']).strip()
    assert str(extreme_prompt_defaults['object_description_directed']).strip()
    for key in ('annotation_hint_max_degree_value', 'annotation_hint_min_degree_value', 'annotation_hint_max_in_degree_value', 'annotation_hint_min_in_degree_value', 'annotation_hint_max_out_degree_value', 'annotation_hint_min_out_degree_value', 'annotation_hint_max_total_degree_value', 'annotation_hint_min_total_degree_value'):
        assert str(extreme_prompt_defaults[key]).strip()

def test_graph_path_defaults_loaded() -> None:
    cfg = get_scene_defaults('graph', 'path')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['node_count_min']) == 5
    assert int(generation_shared['node_count_max']) == 15
    assert int(generation_shared['directed_node_count_max']) == 15
    assert int(generation_shared['target_shortest_path_length_min']) == 3
    assert int(generation_shared['target_shortest_path_length_max']) == 7
    assert set(generation_shared['topology_profile_weights'].keys()) == {'balanced', 'hub_heavy', 'low_degree'}
    assert set(generation_shared['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(generation_shared['layout_variant_weights'].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared['node_shape_variant_weights'].keys()) == {'circle', 'rounded_square', 'hexagon'}
    assert set(generation_shared['layout_transform_variant_weights'].keys()) == {'identity', 'rotate_90', 'rotate_180', 'rotate_270', 'mirror_left_right', 'mirror_up_down'}
    assert set(generation_shared['node_color_name_weights'].keys()) == {'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'brown', 'cyan', 'magenta', 'maroon'}
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['canvas_width']) > 0
    assert int(render_shared['canvas_height']) > 0
    assert int(render_shared['node_radius_min_px']) > 0
    assert int(render_shared['node_radius_max_px']) >= int(render_shared['node_radius_min_px'])
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip() == 'graph_path_v0'
    assert str(prompt_shared['scene_key']).strip() == 'single_graph_path'
    assert str(prompt_shared['task_key']).strip() == 'shortest_path_length_query'
    assert str(prompt_shared['object_description']).strip()
    assert str(prompt_shared['object_description_directed']).strip()
    assert str(prompt_shared['question_text_shortest_path_length']).strip()
    assert str(prompt_shared['question_text_directed_shortest_path_length']).strip()
    assert str(prompt_shared['annotation_hint_shortest_path_length']).strip()
    assert str(prompt_shared['annotation_hint_directed_shortest_path_length']).strip()
    assert str(prompt_shared['answer_hint']).strip()
    assert str(prompt_shared['json_example']).strip()
    assert str(prompt_shared['json_example_answer_only']).strip()
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__shortest_path_length')
    assert 'query_id_weights' not in generation_defaults
    assert set(generation_defaults['layout_variant_weights'].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert int(generation_defaults['node_count_min']) == 5
    assert int(generation_defaults['node_count_max']) == 15
    assert int(generation_defaults['directed_node_count_max']) == 15
    assert int(generation_defaults['target_shortest_path_length_min']) == 2
    assert int(generation_defaults['target_shortest_path_length_max']) == 5
    assert int(rendering_defaults['canvas_width']) > 0
    assert int(rendering_defaults['node_radius_min_px']) > 0
    assert str(prompt_defaults['bundle_id']).strip() == 'graph_path_v0'
    assert str(prompt_defaults['scene_key']).strip() == 'single_graph_path'
    longest_generation_defaults, longest_rendering_defaults, longest_prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__longest_path_length')
    assert set(longest_generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(longest_generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert bool(longest_generation_defaults['balanced_target_longest_path_length_sampling']) is True
    assert int(longest_generation_defaults['node_count_min']) == 5
    assert int(longest_generation_defaults['directed_node_count_max']) == 10
    assert int(longest_generation_defaults['target_longest_path_length_min']) == 2
    assert int(longest_generation_defaults['target_longest_path_length_max']) == 6
    assert int(longest_rendering_defaults['canvas_width']) > 0
    assert int(longest_rendering_defaults['node_radius_min_px']) > 0
    assert str(longest_prompt_defaults['bundle_id']).strip() == 'graph_path_v0'
    assert str(longest_prompt_defaults['scene_key']).strip() == 'single_graph_path'
    assert str(longest_prompt_defaults['task_key']).strip() == 'longest_path_length_query'
    assert str(longest_prompt_defaults['object_description_directed']).strip()
    assert str(longest_prompt_defaults['annotation_hint']).strip()

def test_graph_order_defaults_loaded() -> None:
    cfg = get_scene_defaults('graph', 'order')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['node_count_min']) == 3
    assert int(generation_shared['node_count_max']) == 7
    assert int(generation_shared['target_position_min']) == 1
    assert int(generation_shared['target_position_max']) == 7
    assert set(generation_shared['topology_profile_weights'].keys()) == {'balanced', 'hub_heavy', 'low_degree'}
    assert set(generation_shared['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(generation_shared['layout_variant_weights'].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared['node_shape_variant_weights'].keys()) == {'circle', 'rounded_square', 'hexagon'}
    assert set(generation_shared['layout_transform_variant_weights'].keys()) == {'identity', 'rotate_90', 'rotate_180', 'rotate_270', 'mirror_left_right', 'mirror_up_down'}
    assert set(generation_shared['node_color_name_weights'].keys()) == {'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'brown', 'cyan', 'magenta', 'maroon'}
    render_shared = cfg['rendering']['shared']
    assert int(render_shared['canvas_width']) > 0
    assert int(render_shared['canvas_height']) > 0
    assert int(render_shared['node_radius_min_px']) > 0
    assert int(render_shared['node_radius_max_px']) >= int(render_shared['node_radius_min_px'])
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip() == 'graph_order_v0'
    assert str(prompt_shared['scene_key']).strip() == 'single_graph_order'
    assert str(prompt_shared['task_key']).strip() == 'topological_endpoint_node_label_query'
    assert str(prompt_shared['object_description']).strip()
    assert str(prompt_shared['annotation_hint']).strip()
    assert str(prompt_shared['answer_hint']).strip()
    assert str(prompt_shared['json_example']).strip()
    assert str(prompt_shared['json_example_answer_only']).strip()
    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__topological_endpoint_node_label')
    assert 'query_id_weights' not in generation_defaults
    assert set(generation_defaults['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(generation_defaults['edge_routing_variant_weights'].keys()) == {'straight', 'mixed_arc'}
    assert int(generation_defaults['node_count_min']) == 3
    assert int(generation_defaults['node_count_max']) == 7
    assert int(rendering_defaults['canvas_width']) > 0
    assert int(rendering_defaults['node_radius_min_px']) > 0
    assert str(prompt_defaults['bundle_id']).strip() == 'graph_order_v0'
    assert str(prompt_defaults['scene_key']).strip() == 'single_graph_order'

def test_graph_optimization_defaults_loaded() -> None:
    cfg = get_scene_defaults('graph', 'optimization')
    generation_shared = cfg['generation']['shared']
    assert int(generation_shared['node_count_min']) == 4
    assert int(generation_shared['node_count_max']) == 7
    assert int(generation_shared['extra_edge_count_min']) == 1
    assert int(generation_shared['extra_edge_count_max']) == 2
    assert int(generation_shared['edge_weight_min']) == 1
    assert int(generation_shared['edge_weight_max']) == 9
    assert set(generation_shared['topology_profile_weights'].keys()) == {'balanced', 'hub_heavy', 'low_degree'}
    assert set(generation_shared['label_variant_weights'].keys()) == {'letters', 'numbers', 'named'}
    assert set(generation_shared['layout_variant_weights'].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared['node_shape_variant_weights'].keys()) == {'circle', 'rounded_square', 'hexagon'}
    assert set(generation_shared['layout_transform_variant_weights'].keys()) == {'identity', 'rotate_90', 'rotate_180', 'rotate_270', 'mirror_left_right', 'mirror_up_down'}
    assert set(generation_shared['node_color_name_weights'].keys()) == {'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'brown', 'cyan', 'magenta', 'maroon'}
    rendering_shared = cfg['rendering']['shared']
    assert int(rendering_shared['canvas_width']) > 0
    assert int(rendering_shared['edge_weight_label_font_size_px']) == 22
    assert int(rendering_shared['edge_weight_label_offset_px']) == 24
    assert int(rendering_shared['edge_weight_label_padding_px']) == 7
    prompt_shared = cfg['prompt']['shared']
    assert str(prompt_shared['bundle_id']).strip() == 'graph_optimization_v0'
    assert str(prompt_shared['scene_key']).strip() == 'single_graph_optimization'
    _, _, prompt_defaults = split_generation_rendering_prompt_defaults(cfg, task_id='task_graph__node_link__mst_weight')
    assert str(prompt_defaults['bundle_id']).strip() == 'graph_optimization_v0'
    assert str(prompt_defaults['scene_key']).strip() == 'single_graph_optimization'
    assert str(prompt_defaults['object_description_undirected']).strip() == 'a labeled connected weighted graph'
    assert str(prompt_defaults['question_text_minimum_spanning_tree_weight']).strip()
    assert str(prompt_defaults['annotation_hint']).strip()
    assert str(prompt_defaults['answer_hint']).strip()
    assert str(prompt_defaults['json_example']).strip()
    assert str(prompt_defaults['json_example_answer_only']).strip()
