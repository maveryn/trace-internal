"""Regression tests for task-group default config loading."""

from __future__ import annotations

import json

import pytest

from trace.core.task_group_config import (
    get_domain_defaults,
    get_task_group_defaults,
    resolve_task_group_section_defaults,
)
from trace.tasks.shared.config_defaults import (
    required_group_default,
    required_group_defaults,
    resolve_optional_int_bounds,
    resolve_required_float_bounds,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from trace.tasks.graph.shared.graph_sampling import SUPPORTED_LAYOUT_VARIANTS


FULL_NODE_LINK_LAYOUT_VARIANTS = set(SUPPORTED_LAYOUT_VARIANTS)


def test_graph_counting_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "counting")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 5
    assert int(generation_shared["node_count_max"]) == 10
    assert int(generation_shared["query_degree_min"]) == 0
    assert int(generation_shared["query_degree_max"]) == 4
    assert int(generation_shared["target_count_min"]) == 0
    assert int(generation_shared["target_count_max"]) == 5
    assert int(generation_shared["degree_sequence_max_degree"]) == 5
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_shared["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared["node_shape_variant_weights"].keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(generation_shared["layout_transform_variant_weights"].keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(generation_shared["node_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }
    assert bool(generation_shared["balanced_topology_profile_sampling"]) is True
    assert bool(generation_shared["balanced_label_variant_sampling"]) is True
    assert bool(generation_shared["balanced_layout_variant_sampling"]) is True
    assert bool(generation_shared["balanced_node_shape_variant_sampling"]) is True
    assert bool(generation_shared["balanced_layout_transform_variant_sampling"]) is True
    assert bool(generation_shared["balanced_node_color_name_sampling"]) is True

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["node_radius_min_px"]) > 0
    assert int(render_shared["node_radius_max_px"]) >= int(render_shared["node_radius_min_px"])
    assert int(render_shared["edge_width_px"]) > 0
    assert int(render_shared["label_font_size_px"]) > 0

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip()
    assert str(prompt_shared["scene_key"]).strip()
    assert str(prompt_shared["task_key"]).strip()
    assert str(prompt_shared["json_output_contract"]).strip()
    assert str(prompt_shared["json_output_contract_answer_only"]).strip()
    assert str(prompt_shared["object_description_undirected"]).strip()
    assert str(prompt_shared["object_description_directed"]).strip()
    assert str(prompt_shared["question_text_degree_count"]).strip()
    assert str(prompt_shared["question_text_in_degree"]).strip()
    assert str(prompt_shared["question_text_out_degree"]).strip()
    assert str(prompt_shared["annotation_hint_degree_count"]).strip()
    assert str(prompt_shared["annotation_hint_in_degree_count"]).strip()
    assert str(prompt_shared["annotation_hint_out_degree_count"]).strip()
    assert str(prompt_shared["answer_hint"]).strip()
    assert str(prompt_shared["json_example"]).strip()
    assert str(prompt_shared["json_example_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "topology_reasoning": 0.40,
        "visual_scan": 0.30,
        "ambiguity": 0.20,
        "clutter": 0.10,
    }

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__degree_value_filter_count",
    )
    assert sorted(generation_defaults["query_id_weights"].keys()) == [
        "directed_in_degree_count",
        "directed_out_degree_count",
        "directed_sink_count",
        "directed_source_count",
        "undirected_degree_count",
    ]
    assert sorted(generation_defaults["degree_mode_weights"].keys()) == ["in_degree", "out_degree"]
    assert set(generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(generation_defaults["balanced_edge_routing_variant_sampling"]) is True
    assert bool(generation_defaults["balanced_degree_mode_sampling"]) is True
    assert int(generation_defaults["node_count_min"]) == 5
    assert int(generation_defaults["node_count_max"]) == 10
    assert int(generation_defaults["directed_node_count_max"]) == 10
    assert int(generation_defaults["query_degree_min"]) == 0
    assert int(generation_defaults["query_degree_max"]) == 4
    assert int(generation_defaults["directed_degree_sequence_max_degree"]) == 4
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert int(rendering_defaults["arrow_length_px"]) > 0
    assert int(rendering_defaults["arrow_width_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(prompt_defaults["task_key"]).strip() == "degree_count_query"
    assert str(prompt_defaults["object_description_undirected"]).strip()
    assert str(prompt_defaults["object_description_directed"]).strip()
    assert str(prompt_defaults["question_text_degree_count"]).strip()
    assert str(prompt_defaults["question_text_in_degree"]).strip()
    assert str(prompt_defaults["question_text_out_degree"]).strip()

    named_degree_generation_defaults, named_degree_rendering_defaults, named_degree_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__named_node_degree_value",
        )
    )
    assert sorted(named_degree_generation_defaults["graph_directionality_weights"].keys()) == ["directed", "undirected"]
    assert sorted(named_degree_generation_defaults["degree_mode_weights"].keys()) == [
        "in_degree",
        "out_degree",
        "total_degree",
    ]
    assert set(named_degree_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(named_degree_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(named_degree_generation_defaults["balanced_graph_directionality_sampling"]) is True
    assert bool(named_degree_generation_defaults["balanced_degree_mode_sampling"]) is True
    assert int(named_degree_generation_defaults["node_count_min"]) == 5
    assert int(named_degree_generation_defaults["node_count_max"]) == 10
    assert int(named_degree_generation_defaults["directed_node_count_max"]) == 10
    assert int(named_degree_generation_defaults["target_degree_min"]) == 0
    assert int(named_degree_generation_defaults["target_degree_max"]) == 4
    assert int(named_degree_rendering_defaults["canvas_width"]) > 0
    assert int(named_degree_rendering_defaults["node_radius_min_px"]) > 0
    assert str(named_degree_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(named_degree_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(named_degree_prompt_defaults["task_key"]).strip() == "named_node_degree_value_query"
    assert str(named_degree_prompt_defaults["object_description_undirected"]).strip()
    assert str(named_degree_prompt_defaults["object_description_directed"]).strip()
    assert str(named_degree_prompt_defaults["annotation_hint_named_node_degree_value"]).strip()
    assert str(named_degree_prompt_defaults["annotation_hint_named_node_in_degree_value"]).strip()
    assert str(named_degree_prompt_defaults["annotation_hint_named_node_out_degree_value"]).strip()
    assert str(named_degree_prompt_defaults["annotation_hint_named_node_total_degree_value"]).strip()

    source_sink_generation_defaults, source_sink_rendering_defaults, source_sink_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="graph_node_link_source_sink_count_internal",
        )
    )
    assert sorted(source_sink_generation_defaults["source_sink_mode_weights"].keys()) == ["sink", "source"]
    assert set(source_sink_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(source_sink_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(source_sink_generation_defaults["balanced_source_sink_mode_sampling"]) is True
    assert bool(source_sink_generation_defaults["balanced_target_count_sampling"]) is True
    assert int(source_sink_generation_defaults["target_count_min"]) == 0
    assert int(source_sink_generation_defaults["target_count_max"]) == 4
    assert int(source_sink_generation_defaults["query_degree_min"]) == 0
    assert int(source_sink_generation_defaults["query_degree_max"]) == 0
    assert int(source_sink_rendering_defaults["canvas_width"]) > 0
    assert str(source_sink_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(source_sink_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(source_sink_prompt_defaults["task_key"]).strip() == "source_sink_count_query"
    assert str(source_sink_prompt_defaults["object_description_directed"]).strip()
    assert str(source_sink_prompt_defaults["annotation_hint_source_count"]).strip()
    assert str(source_sink_prompt_defaults["annotation_hint_sink_count"]).strip()

    node_color_generation_defaults, node_color_rendering_defaults, node_color_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__node_color_count",
        )
    )
    assert sorted(node_color_generation_defaults["graph_directionality_weights"].keys()) == ["directed", "undirected"]
    assert set(node_color_generation_defaults["target_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }
    assert set(node_color_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(node_color_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(node_color_generation_defaults["balanced_graph_directionality_sampling"]) is True
    assert bool(node_color_generation_defaults["balanced_target_color_name_sampling"]) is True
    assert bool(node_color_generation_defaults["balanced_target_count_sampling"]) is True
    assert int(node_color_generation_defaults["node_count_min"]) == 8
    assert int(node_color_generation_defaults["node_count_max"]) == 12
    assert int(node_color_generation_defaults["directed_node_count_max"]) == 12
    assert int(node_color_generation_defaults["target_count_min"]) == 3
    assert int(node_color_generation_defaults["target_count_max"]) == 7
    assert int(node_color_rendering_defaults["canvas_width"]) > 0
    assert str(node_color_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(node_color_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(node_color_prompt_defaults["task_key"]).strip() == "node_color_count_query"
    assert str(node_color_prompt_defaults["object_description_undirected"]).strip()
    assert str(node_color_prompt_defaults["object_description_directed"]).strip()

    edge_color_generation_defaults, edge_color_rendering_defaults, edge_color_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__edge_color_count",
        )
    )
    assert sorted(edge_color_generation_defaults["graph_directionality_weights"].keys()) == ["directed", "undirected"]
    assert set(edge_color_generation_defaults["target_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }
    assert set(edge_color_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(edge_color_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(edge_color_generation_defaults["balanced_graph_directionality_sampling"]) is True
    assert bool(edge_color_generation_defaults["balanced_target_color_name_sampling"]) is True
    assert bool(edge_color_generation_defaults["balanced_target_count_sampling"]) is True
    assert int(edge_color_generation_defaults["target_count_min"]) == 0
    assert int(edge_color_generation_defaults["target_count_max"]) == 8
    assert int(edge_color_rendering_defaults["edge_width_px"]) == 5
    assert str(edge_color_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(edge_color_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(edge_color_prompt_defaults["task_key"]).strip() == "edge_color_count_query"
    assert str(edge_color_prompt_defaults["object_description_undirected"]).strip()
    assert str(edge_color_prompt_defaults["object_description_directed"]).strip()

    isolated_removal_generation_defaults, isolated_removal_rendering_defaults, isolated_removal_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__isolated_after_removal_count",
        )
    )
    assert sorted(isolated_removal_generation_defaults["graph_directionality_weights"].keys()) == ["directed", "undirected"]
    assert set(isolated_removal_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(isolated_removal_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(isolated_removal_generation_defaults["balanced_graph_directionality_sampling"]) is True
    assert bool(isolated_removal_generation_defaults["balanced_target_count_sampling"]) is True
    assert int(isolated_removal_generation_defaults["target_count_min"]) == 0
    assert int(isolated_removal_generation_defaults["target_count_max"]) == 5
    assert int(isolated_removal_rendering_defaults["canvas_width"]) > 0
    assert str(isolated_removal_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(isolated_removal_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(isolated_removal_prompt_defaults["task_key"]).strip() == "isolated_node_count_after_node_removal_query"
    assert str(isolated_removal_prompt_defaults["object_description_undirected"]).strip()
    assert str(isolated_removal_prompt_defaults["object_description_directed"]).strip()

    articulation_generation_defaults, articulation_rendering_defaults, articulation_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__articulation_point_count",
        )
    )
    assert sorted(articulation_generation_defaults["query_id_weights"].keys()) == ["articulation_point_count"]
    assert set(articulation_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(articulation_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(articulation_generation_defaults["node_count_min"]) == 5
    assert int(articulation_generation_defaults["node_count_max"]) == 10
    assert int(articulation_generation_defaults["target_count_min"]) == 0
    assert int(articulation_generation_defaults["target_count_max"]) == 5
    assert int(articulation_rendering_defaults["canvas_width"]) > 0
    assert int(articulation_rendering_defaults["node_radius_min_px"]) > 0
    assert str(articulation_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(articulation_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(articulation_prompt_defaults["task_key"]).strip() == "articulation_point_count_query"
    assert str(articulation_prompt_defaults["question_text_articulation_point_count"]).strip()

    bridge_generation_defaults, bridge_rendering_defaults, bridge_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__bridge_count",
        )
    )
    assert sorted(bridge_generation_defaults["query_id_weights"].keys()) == ["bridge_count"]
    assert set(bridge_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(bridge_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(bridge_generation_defaults["node_count_min"]) == 5
    assert int(bridge_generation_defaults["node_count_max"]) == 10
    assert int(bridge_generation_defaults["target_count_min"]) == 0
    assert int(bridge_generation_defaults["target_count_max"]) == 5
    assert int(bridge_rendering_defaults["canvas_width"]) > 0
    assert int(bridge_rendering_defaults["node_radius_min_px"]) > 0
    assert str(bridge_prompt_defaults["bundle_id"]).strip() == "graph_counting_v0"
    assert str(bridge_prompt_defaults["scene_key"]).strip() == "single_graph_counting"
    assert str(bridge_prompt_defaults["task_key"]).strip() == "bridge_count_query"
    assert str(bridge_prompt_defaults["question_text_bridge_count"]).strip()

def test_graph_relation_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "relation")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 6
    assert int(generation_shared["node_count_max"]) == 15
    assert int(generation_shared["component_count_min"]) == 2
    assert int(generation_shared["component_count_max"]) == 4
    assert int(generation_shared["target_component_size_min"]) == 2
    assert int(generation_shared["target_component_size_max"]) == 7
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_shared["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared["node_shape_variant_weights"].keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(generation_shared["layout_transform_variant_weights"].keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(generation_shared["node_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }
    assert bool(generation_shared["balanced_topology_profile_sampling"]) is True
    assert bool(generation_shared["balanced_label_variant_sampling"]) is True
    assert bool(generation_shared["balanced_layout_variant_sampling"]) is True
    assert bool(generation_shared["balanced_node_shape_variant_sampling"]) is True
    assert bool(generation_shared["balanced_layout_transform_variant_sampling"]) is True
    assert bool(generation_shared["balanced_node_color_name_sampling"]) is True

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["node_radius_min_px"]) > 0
    assert int(render_shared["node_radius_max_px"]) >= int(render_shared["node_radius_min_px"])

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "graph_relation_v0"
    assert str(prompt_shared["scene_key"]).strip() == "single_graph_relation"
    assert str(prompt_shared["task_key"]).strip() == "same_component_count_query"
    assert str(prompt_shared["object_description"]).strip()
    assert str(prompt_shared["object_description_directed"]).strip()
    assert str(prompt_shared["question_text_same_component_count"]).strip()
    assert str(prompt_shared["annotation_hint"]).strip()
    assert str(prompt_shared["answer_hint"]).strip()
    assert str(prompt_shared["json_example"]).strip()
    assert str(prompt_shared["json_example_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "topology_reasoning": 0.45,
        "visual_scan": 0.25,
        "ambiguity": 0.20,
        "clutter": 0.10,
    }

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="graph_node_link_same_component_count_internal",
    )
    assert sorted(generation_defaults["query_id_weights"].keys()) == ["same_component_count"]
    assert set(generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(generation_defaults["node_count_min"]) == 6
    assert int(generation_defaults["node_count_max"]) == 15
    assert int(generation_defaults["component_count_min"]) == 2
    assert int(generation_defaults["component_count_max"]) == 4
    assert int(generation_defaults["target_component_size_min"]) == 2
    assert int(generation_defaults["target_component_size_max"]) == 7
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(prompt_defaults["task_key"]).strip() == "same_component_count_query"
    assert str(prompt_defaults["question_text_same_component_count"]).strip()

    reachable_generation_defaults, reachable_rendering_defaults, reachable_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__reachable_count",
    )
    assert sorted(reachable_generation_defaults["query_id_weights"].keys()) == ["reachable_count"]
    assert set(reachable_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(reachable_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(reachable_generation_defaults["node_count_min"]) == 5
    assert int(reachable_generation_defaults["directed_node_count_max"]) == 9
    assert int(reachable_generation_defaults["target_reachable_count_min"]) == 1
    assert int(reachable_generation_defaults["target_reachable_count_max"]) == 7
    assert int(reachable_rendering_defaults["canvas_width"]) > 0
    assert int(reachable_rendering_defaults["node_radius_min_px"]) > 0
    assert str(reachable_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(reachable_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(reachable_prompt_defaults["task_key"]).strip() == "reachable_count_query"
    assert str(reachable_prompt_defaults["object_description_directed"]).strip()
    assert str(reachable_prompt_defaults["question_text_reachable_count"]).strip()
    assert str(reachable_prompt_defaults["annotation_hint_reachable_count"]).strip()

    reachable_edge_edit_generation_defaults, reachable_edge_edit_rendering_defaults, reachable_edge_edit_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__reachable_count_after_edge_edit",
    )
    assert sorted(reachable_edge_edit_generation_defaults["edge_edit_operation_weights"].keys()) == [
        "edge_addition",
        "edge_removal",
    ]
    assert set(reachable_edge_edit_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(reachable_edge_edit_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(reachable_edge_edit_generation_defaults["balanced_edge_edit_operation_sampling"]) is True
    assert bool(reachable_edge_edit_generation_defaults["balanced_target_reachable_count_sampling"]) is True
    assert int(reachable_edge_edit_generation_defaults["node_count_min"]) == 5
    assert int(reachable_edge_edit_generation_defaults["directed_node_count_max"]) == 10
    assert int(reachable_edge_edit_generation_defaults["target_reachable_count_min"]) == 1
    assert int(reachable_edge_edit_generation_defaults["target_reachable_count_max"]) == 8
    assert int(reachable_edge_edit_rendering_defaults["canvas_width"]) > 0
    assert int(reachable_edge_edit_rendering_defaults["node_radius_min_px"]) > 0
    assert str(reachable_edge_edit_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(reachable_edge_edit_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(reachable_edge_edit_prompt_defaults["task_key"]).strip() == "reachable_count_after_edge_edit_query"
    assert str(reachable_edge_edit_prompt_defaults["object_description_directed"]).strip()
    assert str(reachable_edge_edit_prompt_defaults["annotation_hint_reachable_count_after_edge_removal"]).strip()
    assert str(reachable_edge_edit_prompt_defaults["annotation_hint_reachable_count_after_edge_addition"]).strip()

    common_generation_defaults, common_rendering_defaults, common_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__common_related_node_count",
    )
    assert sorted(common_generation_defaults["common_neighbor_mode_weights"].keys()) == [
        "directed_common_predecessor",
        "directed_common_successor",
        "undirected_common_neighbor",
    ]
    assert set(common_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(common_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(common_generation_defaults["balanced_common_neighbor_mode_sampling"]) is True
    assert bool(common_generation_defaults["balanced_target_count_sampling"]) is True
    assert int(common_generation_defaults["node_count_min"]) == 6
    assert int(common_generation_defaults["node_count_max"]) == 10
    assert int(common_generation_defaults["directed_node_count_max"]) == 10
    assert int(common_generation_defaults["target_count_min"]) == 0
    assert int(common_generation_defaults["target_count_max"]) == 4
    assert int(common_rendering_defaults["canvas_width"]) > 0
    assert int(common_rendering_defaults["node_radius_min_px"]) > 0
    assert str(common_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(common_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(common_prompt_defaults["task_key"]).strip() == "common_neighbor_count_query"
    assert str(common_prompt_defaults["object_description"]).strip()
    assert str(common_prompt_defaults["object_description_directed"]).strip()
    assert str(common_prompt_defaults["annotation_hint_common_neighbor_count"]).strip()
    assert str(common_prompt_defaults["annotation_hint_common_successor_count"]).strip()
    assert str(common_prompt_defaults["annotation_hint_common_predecessor_count"]).strip()

    edge_attribute_generation_defaults, edge_attribute_rendering_defaults, edge_attribute_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__edge_between_nodes_label",
    )
    assert sorted(edge_attribute_generation_defaults["graph_directionality_weights"].keys()) == ["directed", "undirected"]
    assert int(edge_attribute_generation_defaults["edge_label_support_size"]) == 6
    assert set(edge_attribute_generation_defaults["query_id_weights"].keys()) == {
        "edge_between_nodes_label",
        "directed_edge_between_nodes_label",
    }
    assert set(edge_attribute_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(edge_attribute_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(edge_attribute_generation_defaults["balanced_query_id_sampling"]) is True
    assert bool(edge_attribute_generation_defaults["balanced_target_edge_label_sampling"]) is True
    assert int(edge_attribute_generation_defaults["node_count_min"]) == 5
    assert int(edge_attribute_generation_defaults["node_count_max"]) == 8
    assert int(edge_attribute_generation_defaults["directed_node_count_max"]) == 8
    assert int(edge_attribute_rendering_defaults["canvas_width"]) > 0
    assert int(edge_attribute_rendering_defaults["node_radius_min_px"]) > 0
    assert str(edge_attribute_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(edge_attribute_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(edge_attribute_prompt_defaults["task_key"]).strip() == "edge_attribute_label_query"
    assert str(edge_attribute_prompt_defaults["object_description_undirected"]).strip()
    assert str(edge_attribute_prompt_defaults["object_description_directed"]).strip()
    assert str(edge_attribute_prompt_defaults["annotation_hint_edge_between_nodes_label"]).strip()
    assert str(edge_attribute_prompt_defaults["annotation_hint_directed_edge_between_nodes_label"]).strip()
    assert str(edge_attribute_prompt_defaults["annotation_hint_shortest_path_first_edge_label"]).strip()

    shortest_edge_generation_defaults, _, shortest_edge_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__shortest_path_first_edge_label",
    )
    assert sorted(shortest_edge_generation_defaults["query_id_weights"].keys()) == [
        "shortest_path_first_edge_label"
    ]
    assert int(shortest_edge_generation_defaults["target_shortest_path_length_min"]) == 2
    assert int(shortest_edge_generation_defaults["target_shortest_path_length_max"]) == 3
    assert str(shortest_edge_prompt_defaults["task_key"]).strip() == "edge_attribute_label_query"

    edge_edit_generation_defaults, edge_edit_rendering_defaults, edge_edit_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="graph_node_link_component_size_after_edge_edit_internal",
    )
    assert sorted(edge_edit_generation_defaults["edge_edit_operation_weights"].keys()) == [
        "edge_addition",
        "edge_removal",
    ]
    assert set(edge_edit_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(edge_edit_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(edge_edit_generation_defaults["balanced_edge_edit_operation_sampling"]) is True
    assert bool(edge_edit_generation_defaults["balanced_target_component_size_sampling"]) is True
    assert int(edge_edit_generation_defaults["node_count_min"]) == 5
    assert int(edge_edit_generation_defaults["node_count_max"]) == 12
    assert int(edge_edit_generation_defaults["target_component_size_min"]) == 1
    assert int(edge_edit_generation_defaults["target_component_size_max"]) == 8
    assert int(edge_edit_rendering_defaults["canvas_width"]) > 0
    assert int(edge_edit_rendering_defaults["node_radius_min_px"]) > 0
    assert str(edge_edit_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(edge_edit_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(edge_edit_prompt_defaults["task_key"]).strip() == "component_size_after_edge_edit_query"
    assert str(edge_edit_prompt_defaults["object_description"]).strip()
    assert str(edge_edit_prompt_defaults["annotation_hint_component_size_after_edge_removal"]).strip()
    assert str(edge_edit_prompt_defaults["annotation_hint_component_size_after_edge_addition"]).strip()

    cycle_generation_defaults, cycle_rendering_defaults, cycle_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__unique_cycle_size",
    )
    assert sorted(cycle_generation_defaults["query_id_weights"].keys()) == ["unique_cycle_size"]
    assert set(cycle_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(cycle_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(cycle_generation_defaults["node_count_min"]) == 5
    assert int(cycle_generation_defaults["node_count_max"]) == 10
    assert int(cycle_generation_defaults["target_cycle_size_min"]) == 3
    assert int(cycle_generation_defaults["target_cycle_size_max"]) == 7
    assert int(cycle_rendering_defaults["canvas_width"]) > 0
    assert int(cycle_rendering_defaults["node_radius_min_px"]) > 0
    assert str(cycle_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(cycle_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(cycle_prompt_defaults["task_key"]).strip() == "unique_cycle_size_query"
    assert str(cycle_prompt_defaults["question_text_unique_cycle_size"]).strip()

    chordless_cycle_generation_defaults, chordless_cycle_rendering_defaults, chordless_cycle_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__largest_chordless_cycle_size",
    )
    assert sorted(chordless_cycle_generation_defaults["query_id_weights"].keys()) == ["largest_chordless_cycle_size"]
    assert set(chordless_cycle_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(chordless_cycle_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(chordless_cycle_generation_defaults["node_count_min"]) == 8
    assert int(chordless_cycle_generation_defaults["node_count_max"]) == 10
    assert int(chordless_cycle_generation_defaults["target_cycle_size_min"]) == 3
    assert int(chordless_cycle_generation_defaults["target_cycle_size_max"]) == 7
    assert int(chordless_cycle_rendering_defaults["canvas_width"]) > 0
    assert int(chordless_cycle_rendering_defaults["node_radius_min_px"]) > 0
    assert str(chordless_cycle_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(chordless_cycle_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(chordless_cycle_prompt_defaults["task_key"]).strip() == "largest_chordless_cycle_size_query"
    assert str(chordless_cycle_prompt_defaults["question_text_largest_chordless_cycle_size"]).strip()

    hamiltonian_generation_defaults, hamiltonian_rendering_defaults, hamiltonian_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__hamiltonian_cycle_neighbor_label",
    )
    assert sorted(hamiltonian_generation_defaults["query_id_weights"].keys()) == [
        "next_in_hamiltonian_cycle_label",
        "previous_in_hamiltonian_cycle_label",
    ]
    assert set(hamiltonian_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(hamiltonian_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(hamiltonian_generation_defaults["node_count_min"]) == 4
    assert int(hamiltonian_generation_defaults["node_count_max"]) == 6
    assert int(hamiltonian_rendering_defaults["canvas_width"]) > 0
    assert int(hamiltonian_rendering_defaults["node_radius_min_px"]) > 0
    assert str(hamiltonian_prompt_defaults["bundle_id"]).strip() == "graph_relation_v0"
    assert str(hamiltonian_prompt_defaults["scene_key"]).strip() == "single_graph_relation"
    assert str(hamiltonian_prompt_defaults["task_key"]).strip() == "hamiltonian_cycle_neighbor_label_query"
    assert str(hamiltonian_prompt_defaults["question_text_next_in_hamiltonian_cycle_label"]).strip()
    assert str(hamiltonian_prompt_defaults["question_text_previous_in_hamiltonian_cycle_label"]).strip()

def test_graph_comparison_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "comparison")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 6
    assert int(generation_shared["node_count_max"]) == 15
    assert int(generation_shared["component_count_min"]) == 2
    assert int(generation_shared["component_count_max"]) == 4
    assert int(generation_shared["target_largest_component_size_min"]) == 3
    assert int(generation_shared["target_largest_component_size_max"]) == 9
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_shared["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared["node_shape_variant_weights"].keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(generation_shared["layout_transform_variant_weights"].keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(generation_shared["node_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "graph_comparison_v0"
    assert str(prompt_shared["scene_key"]).strip() == "single_graph_comparison"
    assert str(prompt_shared["task_key"]).strip() == "largest_component_size_query"
    assert str(prompt_shared["object_description"]).strip()
    assert str(prompt_shared["question_text_largest_component_size"]).strip()
    assert str(prompt_shared["annotation_hint"]).strip()
    assert str(prompt_shared["answer_hint"]).strip()
    assert str(prompt_shared["json_example"]).strip()
    assert str(prompt_shared["json_example_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "topology_reasoning": 0.45,
        "visual_scan": 0.20,
        "ambiguity": 0.25,
        "clutter": 0.10,
    }

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="graph_node_link_largest_component_size_internal",
    )
    assert sorted(generation_defaults["query_id_weights"].keys()) == ["largest_component_size"]
    assert set(generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(generation_defaults["node_count_min"]) == 6
    assert int(generation_defaults["node_count_max"]) == 15
    assert int(generation_defaults["component_count_min"]) == 2
    assert int(generation_defaults["component_count_max"]) == 4
    assert int(generation_defaults["target_largest_component_size_min"]) == 3
    assert int(generation_defaults["target_largest_component_size_max"]) == 9
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_comparison_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "single_graph_comparison"
    assert str(prompt_defaults["task_key"]).strip() == "largest_component_size_query"
    assert str(prompt_defaults["question_text_largest_component_size"]).strip()

    extreme_generation_defaults, extreme_rendering_defaults, extreme_prompt_defaults = (
        split_generation_rendering_prompt_defaults(
            cfg,
            task_id="task_graph__node_link__degree_extremum_value",
        )
    )
    expected_extreme_query_ids = {
        "directed_max_in_degree_value",
        "directed_max_out_degree_value",
        "directed_max_total_degree_value",
        "directed_min_in_degree_value",
        "directed_min_out_degree_value",
        "directed_min_total_degree_value",
        "undirected_max_degree_value",
        "undirected_min_degree_value",
    }
    assert expected_extreme_query_ids.issubset(set(extreme_generation_defaults["query_id_weights"].keys()))
    assert all(float(extreme_generation_defaults["query_id_weights"][key]) > 0.0 for key in expected_extreme_query_ids)
    assert set(extreme_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(extreme_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(extreme_generation_defaults["balanced_query_id_sampling"]) is True
    assert int(extreme_generation_defaults["node_count_min"]) == 5
    assert int(extreme_generation_defaults["node_count_max"]) == 10
    assert int(extreme_generation_defaults["directed_node_count_max"]) == 10
    assert int(extreme_generation_defaults["target_degree_min"]) == 0
    assert int(extreme_generation_defaults["target_degree_max"]) == 4
    assert int(extreme_rendering_defaults["canvas_width"]) > 0
    assert int(extreme_rendering_defaults["node_radius_min_px"]) > 0
    assert str(extreme_prompt_defaults["bundle_id"]).strip() == "graph_comparison_v0"
    assert str(extreme_prompt_defaults["scene_key"]).strip() == "single_graph_comparison"
    assert str(extreme_prompt_defaults["task_key"]).strip() == "extreme_degree_value_query"
    assert str(extreme_prompt_defaults["object_description_undirected"]).strip()
    assert str(extreme_prompt_defaults["object_description_directed"]).strip()
    for key in (
        "annotation_hint_max_degree_value",
        "annotation_hint_min_degree_value",
        "annotation_hint_max_in_degree_value",
        "annotation_hint_min_in_degree_value",
        "annotation_hint_max_out_degree_value",
        "annotation_hint_min_out_degree_value",
        "annotation_hint_max_total_degree_value",
        "annotation_hint_min_total_degree_value",
    ):
        assert str(extreme_prompt_defaults[key]).strip()

def test_graph_path_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "path")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 5
    assert int(generation_shared["node_count_max"]) == 15
    assert int(generation_shared["directed_node_count_max"]) == 15
    assert int(generation_shared["target_shortest_path_length_min"]) == 3
    assert int(generation_shared["target_shortest_path_length_max"]) == 7
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_shared["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared["node_shape_variant_weights"].keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(generation_shared["layout_transform_variant_weights"].keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(generation_shared["node_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["node_radius_min_px"]) > 0
    assert int(render_shared["node_radius_max_px"]) >= int(render_shared["node_radius_min_px"])

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "graph_path_v0"
    assert str(prompt_shared["scene_key"]).strip() == "single_graph_path"
    assert str(prompt_shared["task_key"]).strip() == "shortest_path_length_query"
    assert str(prompt_shared["object_description"]).strip()
    assert str(prompt_shared["object_description_directed"]).strip()
    assert str(prompt_shared["question_text_shortest_path_length"]).strip()
    assert str(prompt_shared["question_text_directed_shortest_path_length"]).strip()
    assert str(prompt_shared["annotation_hint_shortest_path_length"]).strip()
    assert str(prompt_shared["annotation_hint_directed_shortest_path_length"]).strip()
    assert str(prompt_shared["answer_hint"]).strip()
    assert str(prompt_shared["json_example"]).strip()
    assert str(prompt_shared["json_example_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "topology_reasoning": 0.50,
        "visual_scan": 0.20,
        "ambiguity": 0.20,
        "clutter": 0.10,
    }

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__shortest_path_length",
    )
    assert generation_defaults["query_id_weights"] == {
        "shortest_path_length": 1.0,
        "directed_shortest_path_length": 1.0,
    }
    assert set(generation_defaults["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(generation_defaults["node_count_min"]) == 5
    assert int(generation_defaults["node_count_max"]) == 15
    assert int(generation_defaults["directed_node_count_max"]) == 15
    assert int(generation_defaults["target_shortest_path_length_min"]) == 3
    assert int(generation_defaults["target_shortest_path_length_max"]) == 7
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_path_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "single_graph_path"

    longest_generation_defaults, longest_rendering_defaults, longest_prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__longest_path_length",
    )
    assert set(longest_generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(longest_generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert bool(longest_generation_defaults["balanced_target_longest_path_length_sampling"]) is True
    assert int(longest_generation_defaults["node_count_min"]) == 5
    assert int(longest_generation_defaults["directed_node_count_max"]) == 10
    assert int(longest_generation_defaults["target_longest_path_length_min"]) == 2
    assert int(longest_generation_defaults["target_longest_path_length_max"]) == 6
    assert int(longest_rendering_defaults["canvas_width"]) > 0
    assert int(longest_rendering_defaults["node_radius_min_px"]) > 0
    assert str(longest_prompt_defaults["bundle_id"]).strip() == "graph_path_v0"
    assert str(longest_prompt_defaults["scene_key"]).strip() == "single_graph_path"
    assert str(longest_prompt_defaults["task_key"]).strip() == "longest_path_length_query"
    assert str(longest_prompt_defaults["object_description_directed"]).strip()
    assert str(longest_prompt_defaults["annotation_hint"]).strip()

def test_graph_order_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "order")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 3
    assert int(generation_shared["node_count_max"]) == 7
    assert int(generation_shared["target_position_min"]) == 1
    assert int(generation_shared["target_position_max"]) == 7
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_shared["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared["node_shape_variant_weights"].keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(generation_shared["layout_transform_variant_weights"].keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(generation_shared["node_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }

    render_shared = cfg["rendering"]["shared"]
    assert int(render_shared["canvas_width"]) > 0
    assert int(render_shared["canvas_height"]) > 0
    assert int(render_shared["node_radius_min_px"]) > 0
    assert int(render_shared["node_radius_max_px"]) >= int(render_shared["node_radius_min_px"])

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "graph_order_v0"
    assert str(prompt_shared["scene_key"]).strip() == "single_graph_order"
    assert str(prompt_shared["task_key"]).strip() == "topological_position_query"
    assert str(prompt_shared["object_description"]).strip()
    assert str(prompt_shared["question_text_topological_position"]).strip()
    assert str(prompt_shared["annotation_hint"]).strip()
    assert str(prompt_shared["answer_hint"]).strip()
    assert str(prompt_shared["json_example"]).strip()
    assert str(prompt_shared["json_example_answer_only"]).strip()

    complexity_shared = cfg["complexity"]["shared"]
    assert dict(complexity_shared["criteria_weights"]) == {
        "topology_reasoning": 0.50,
        "visual_scan": 0.20,
        "ambiguity": 0.20,
        "clutter": 0.10,
    }

    generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__topological_position_value",
    )
    assert sorted(generation_defaults["query_id_weights"].keys()) == ["topological_position"]
    assert set(generation_defaults["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_defaults["edge_routing_variant_weights"].keys()) == {"straight", "mixed_arc"}
    assert int(generation_defaults["node_count_min"]) == 3
    assert int(generation_defaults["node_count_max"]) == 7
    assert int(generation_defaults["target_position_min"]) == 1
    assert int(generation_defaults["target_position_max"]) == 7
    assert int(rendering_defaults["canvas_width"]) > 0
    assert int(rendering_defaults["node_radius_min_px"]) > 0
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_order_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "single_graph_order"

def test_graph_optimization_defaults_loaded() -> None:
    cfg = get_task_group_defaults("graph", "optimization")
    for section in ("generation", "rendering", "prompt", "visual", "complexity"):
        assert isinstance(cfg.get(section), dict)

    generation_shared = cfg["generation"]["shared"]
    assert int(generation_shared["node_count_min"]) == 4
    assert int(generation_shared["node_count_max"]) == 7
    assert int(generation_shared["extra_edge_count_min"]) == 1
    assert int(generation_shared["extra_edge_count_max"]) == 2
    assert int(generation_shared["edge_weight_min"]) == 1
    assert int(generation_shared["edge_weight_max"]) == 9
    assert set(generation_shared["topology_profile_weights"].keys()) == {"balanced", "hub_heavy", "low_degree"}
    assert set(generation_shared["label_variant_weights"].keys()) == {"letters", "numbers", "named"}
    assert set(generation_shared["layout_variant_weights"].keys()) == FULL_NODE_LINK_LAYOUT_VARIANTS
    assert set(generation_shared["node_shape_variant_weights"].keys()) == {"circle", "rounded_square", "hexagon"}
    assert set(generation_shared["layout_transform_variant_weights"].keys()) == {
        "identity",
        "rotate_90",
        "rotate_180",
        "rotate_270",
        "mirror_left_right",
        "mirror_up_down",
    }
    assert set(generation_shared["node_color_name_weights"].keys()) == {
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "brown",
        "cyan",
        "magenta",
        "maroon",
    }

    rendering_shared = cfg["rendering"]["shared"]
    assert int(rendering_shared["canvas_width"]) > 0
    assert int(rendering_shared["edge_weight_label_font_size_px"]) == 22
    assert int(rendering_shared["edge_weight_label_offset_px"]) == 24
    assert int(rendering_shared["edge_weight_label_padding_px"]) == 7

    complexity_shared = cfg["complexity"]["shared"]["criteria_weights"]
    assert set(complexity_shared.keys()) == {"topology_reasoning", "visual_scan", "ambiguity", "clutter"}

    prompt_shared = cfg["prompt"]["shared"]
    assert str(prompt_shared["bundle_id"]).strip() == "graph_optimization_v0"
    assert str(prompt_shared["scene_key"]).strip() == "single_graph_optimization"

    _, _, prompt_defaults = split_generation_rendering_prompt_defaults(
        cfg,
        task_id="task_graph__node_link__mst_weight",
    )
    assert str(prompt_defaults["bundle_id"]).strip() == "graph_optimization_v0"
    assert str(prompt_defaults["scene_key"]).strip() == "single_graph_optimization"
    assert str(prompt_defaults["object_description_undirected"]).strip() == "a labeled connected weighted graph"
    assert str(prompt_defaults["question_text_minimum_spanning_tree_weight"]).strip()
    assert str(prompt_defaults["annotation_hint"]).strip()
    assert str(prompt_defaults["answer_hint"]).strip()
    assert str(prompt_defaults["json_example"]).strip()
    assert str(prompt_defaults["json_example_answer_only"]).strip()
