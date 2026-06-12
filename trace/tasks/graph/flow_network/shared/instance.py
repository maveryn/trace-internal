"""Instance construction helpers for flow-network public tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.config_defaults import group_default
from ....shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.graph_sample_types import graph_label_sort_key
from ...shared.graph_scene import (
    SUPPORTED_EDGE_ROUTING_VARIANTS,
    SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    projected_edge_pair_annotation,
)
from ...shared.style import SUPPORTED_NODE_COLOR_NAMES
from ...shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from ...shared.visual_defaults import load_graph_scene_background_defaults, load_graph_scene_noise_defaults
from .rendering import render_flow_network_scene
from .sampling import sample_flow_network
from .state import (
    SCENE_ID,
    SUPPORTED_FLOW_LAYOUT_VARIANTS,
    FlowNetworkAxes,
    FlowNetworkDefaults,
    FlowNetworkRender,
    FlowNetworkSample,
)


@dataclass(frozen=True)
class ResolvedFlowNetwork:
    """Resolved support axes for one public flow-network objective."""

    query_id: str
    node_count: int
    target_answer: int
    target_cut_edge_count: int
    target_flow_value: int
    distractor_edge_count: int
    layout_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    query_id_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    target_cut_edge_count_probabilities: Dict[str, float]
    target_flow_value_probabilities: Dict[str, float]
    distractor_edge_count_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    edge_routing_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


@dataclass(frozen=True)
class FlowNetworkInstanceBundle:
    """Rendered flow-network instance before public output binding."""

    query: ResolvedFlowNetwork
    render_params: Any
    flow_sample: FlowNetworkSample
    render: FlowNetworkRender
    answer_value: int
    annotation_edges: Tuple[Tuple[str, str], ...]
    annotation_projection: Mapping[str, Any]
    annotation_point_pairs: Tuple[Any, ...]
    capacity_label_font_size_px: int
    capacity_label_offset_px: int
    capacity_label_padding_px: int


_DEFAULTS = FlowNetworkDefaults()
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_scene_background_defaults(scene_id=SCENE_ID)
POST_IMAGE_NOISE_DEFAULTS = load_graph_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _integer_support_probability(values: Sequence[int], *, selected: int | None = None) -> Dict[str, float]:
    return dict(uniform_probability_map(tuple(int(value) for value in values), selected=selected))


def _select_from_support(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    support: Sequence[int],
    explicit_key: str,
) -> Tuple[int, Dict[str, float]]:
    support_tuple = tuple(int(value) for value in support)
    if not support_tuple:
        raise ValueError(f"empty support for {namespace}")
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = int(explicit)
        if int(value) not in set(support_tuple):
            raise ValueError(f"{explicit_key} is outside feasible support")
        return int(value), _integer_support_probability(support_tuple, selected=int(value))
    index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))
    value = int(support_tuple[int(index % len(support_tuple))])
    return int(value), _integer_support_probability(support_tuple)


def _resolve_named_axis(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    sampling_namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Tuple[str, ...],
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_graph_named_variant(
        spawn_rng(int(instance_seed), f"{str(sampling_namespace)}.{str(namespace)}"),
        params=params,
        gen_defaults=gen_defaults,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported=tuple(str(value) for value in supported),
        instance_seed=int(instance_seed),
        task_id=str(sampling_namespace),
        namespace=str(namespace),
    )


def _resolve_flow_network(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    query_id: str,
    answer_mode: str,
    sampling_namespace: str,
) -> ResolvedFlowNetwork:
    node_count_min = int(params.get("node_count_min", group_default(gen_defaults, "node_count_min", _DEFAULTS.node_count_min)))
    node_count_max = int(params.get("node_count_max", group_default(gen_defaults, "node_count_max", _DEFAULTS.node_count_max)))
    node_support = tuple(int(value) for value in range(max(4, int(node_count_min)), int(node_count_max) + 1))
    node_count, node_count_probabilities = _select_from_support(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{str(sampling_namespace)}:node_count",
        support=node_support,
        explicit_key="node_count",
    )

    cut_count_min = int(params.get("min_cut_edge_count_min", group_default(gen_defaults, "min_cut_edge_count_min", _DEFAULTS.min_cut_edge_count_min)))
    cut_count_max = int(params.get("min_cut_edge_count_max", group_default(gen_defaults, "min_cut_edge_count_max", _DEFAULTS.min_cut_edge_count_max)))
    cut_count_support = tuple(int(value) for value in range(max(1, int(cut_count_min)), int(cut_count_max) + 1))

    if str(answer_mode) == "minimum_cut_edge_count":
        target_answer, target_answer_probabilities = _select_from_support(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{str(sampling_namespace)}:target_answer",
            support=cut_count_support,
            explicit_key="target_answer",
        )
        target_cut_edge_count = int(target_answer)
        feasible_flow = tuple(
            int(value)
            for value in range(max(4, int(target_cut_edge_count)), min(12, int(_DEFAULTS.cut_capacity_part_max) * int(target_cut_edge_count)) + 1)
        )
        target_flow_value, target_flow_value_probabilities = _select_from_support(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{str(sampling_namespace)}:target_flow_value:{target_cut_edge_count}",
            support=feasible_flow,
            explicit_key="target_flow_value",
        )
        target_cut_edge_count_probabilities = _integer_support_probability(cut_count_support, selected=int(target_cut_edge_count))
        distractor_min = int(params.get("distractor_edge_min", group_default(gen_defaults, "distractor_edge_min", _DEFAULTS.distractor_edge_min)))
        distractor_max = int(params.get("distractor_edge_max", group_default(gen_defaults, "distractor_edge_max", _DEFAULTS.distractor_edge_max)))
    else:
        flow_min = int(params.get("max_flow_value_min", group_default(gen_defaults, "max_flow_value_min", _DEFAULTS.max_flow_value_min)))
        flow_max = int(params.get("max_flow_value_max", group_default(gen_defaults, "max_flow_value_max", _DEFAULTS.max_flow_value_max)))
        flow_support = tuple(int(value) for value in range(max(1, int(flow_min)), int(flow_max) + 1))
        target_answer, target_answer_probabilities = _select_from_support(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{str(sampling_namespace)}:target_answer",
            support=flow_support,
            explicit_key="target_answer",
        )
        max_flow_cut_min = int(params.get("max_flow_cut_edge_count_min", group_default(gen_defaults, "max_flow_cut_edge_count_min", _DEFAULTS.max_flow_cut_edge_count_min)))
        max_flow_cut_max = int(params.get("max_flow_cut_edge_count_max", group_default(gen_defaults, "max_flow_cut_edge_count_max", _DEFAULTS.max_flow_cut_edge_count_max)))
        max_flow_cut_support = tuple(int(value) for value in range(max(1, int(max_flow_cut_min)), max(int(max_flow_cut_min), int(max_flow_cut_max)) + 1))
        feasible_cut_counts = tuple(
            int(value)
            for value in max_flow_cut_support
            if int(value) <= int(target_answer)
            and int(target_answer) <= int(value) * int(_DEFAULTS.cut_capacity_part_max)
        )
        target_cut_edge_count, target_cut_edge_count_probabilities = _select_from_support(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{str(sampling_namespace)}:target_cut_edge_count:{target_answer}",
            support=feasible_cut_counts,
            explicit_key="target_cut_edge_count",
        )
        target_flow_value = int(target_answer)
        target_flow_value_probabilities = {str(target_flow_value): 1.0}
        distractor_min = int(params.get("max_flow_distractor_edge_min", group_default(gen_defaults, "max_flow_distractor_edge_min", _DEFAULTS.max_flow_distractor_edge_min)))
        distractor_max = int(params.get("max_flow_distractor_edge_max", group_default(gen_defaults, "max_flow_distractor_edge_max", _DEFAULTS.max_flow_distractor_edge_max)))

    distractor_support = tuple(int(value) for value in range(max(0, int(distractor_min)), max(int(distractor_min), int(distractor_max)) + 1))
    distractor_edge_count, distractor_edge_count_probabilities = _select_from_support(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{str(sampling_namespace)}:distractor_edge_count",
        support=distractor_support,
        explicit_key="distractor_edge_count",
    )
    layout_variant, layout_variant_probabilities = _resolve_named_axis(
        int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        sampling_namespace=str(sampling_namespace),
        explicit_key="layout_variant",
        weights_key="layout_variant_weights",
        balance_flag_key="balanced_layout_variant_sampling",
        supported=SUPPORTED_FLOW_LAYOUT_VARIANTS,
        namespace="layout_variant",
    )
    layout_transform_variant, layout_transform_variant_probabilities = _resolve_named_axis(
        int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        sampling_namespace=str(sampling_namespace),
        explicit_key="layout_transform_variant",
        weights_key="layout_transform_variant_weights",
        balance_flag_key="balanced_layout_transform_variant_sampling",
        supported=SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
        namespace="layout_transform_variant",
    )
    edge_routing_variant, edge_routing_variant_probabilities = _resolve_named_axis(
        int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        sampling_namespace=str(sampling_namespace),
        explicit_key="edge_routing_variant",
        weights_key="edge_routing_variant_weights",
        balance_flag_key="balanced_edge_routing_variant_sampling",
        supported=SUPPORTED_EDGE_ROUTING_VARIANTS,
        namespace="edge_routing_variant",
    )
    node_color_name, node_color_name_probabilities = _resolve_named_axis(
        int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        sampling_namespace=str(sampling_namespace),
        explicit_key="node_color_name",
        weights_key="node_color_name_weights",
        balance_flag_key="balanced_node_color_name_sampling",
        supported=SUPPORTED_NODE_COLOR_NAMES,
        namespace="node_color_name",
    )
    return ResolvedFlowNetwork(
        query_id=str(query_id),
        node_count=int(node_count),
        target_answer=int(target_answer),
        target_cut_edge_count=int(target_cut_edge_count),
        target_flow_value=int(target_flow_value),
        distractor_edge_count=int(distractor_edge_count),
        layout_variant=str(layout_variant),
        layout_transform_variant=str(layout_transform_variant),
        edge_routing_variant=str(edge_routing_variant),
        node_color_name=str(node_color_name),
        query_id_probabilities={str(query_id): 1.0},
        node_count_probabilities=dict(node_count_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        target_cut_edge_count_probabilities=dict(target_cut_edge_count_probabilities),
        target_flow_value_probabilities=dict(target_flow_value_probabilities),
        distractor_edge_count_probabilities=dict(distractor_edge_count_probabilities),
        layout_variant_probabilities=dict(layout_variant_probabilities),
        layout_transform_variant_probabilities=dict(layout_transform_variant_probabilities),
        edge_routing_variant_probabilities=dict(edge_routing_variant_probabilities),
        node_color_name_probabilities=dict(node_color_name_probabilities),
    )


def _flow_answer_value(flow_sample: FlowNetworkSample, *, answer_mode: str) -> int:
    if str(answer_mode) == "minimum_cut_edge_count":
        return int(len(flow_sample.original_min_cut_edges))
    return int(flow_sample.original_max_flow_value)


def _capacity_trace(flow_sample: FlowNetworkSample) -> list[Dict[str, Any]]:
    return [
        {"edge": [str(left), str(right)], "capacity": int(capacity)}
        for (left, right), capacity in sorted(
            flow_sample.capacity_by_edge_label.items(),
            key=lambda item: (graph_label_sort_key(item[0][0]), graph_label_sort_key(item[0][1])),
        )
    ]


def build_flow_network_instance_bundle(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    query_id: str,
    answer_mode: str,
    sampling_namespace: str,
    max_attempts: int,
) -> FlowNetworkInstanceBundle:
    """Sample, render, and project one flow-network instance."""

    query = _resolve_flow_network(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        query_id=str(query_id),
        answer_mode=str(answer_mode),
        sampling_namespace=str(sampling_namespace),
    )
    render_params = resolve_graph_render_params(
        params,
        instance_seed=int(instance_seed),
        task_id=str(sampling_namespace),
        render_defaults=render_defaults,
        fallback_defaults=_DEFAULTS,
        node_color_name=str(query.node_color_name),
        node_shape_variant="circle",
        edge_routing_variant=str(query.edge_routing_variant),
    )
    capacity_label_font_size_px = int(params.get("capacity_label_font_size_px", group_default(render_defaults, "capacity_label_font_size_px", _DEFAULTS.capacity_label_font_size_px)))
    capacity_label_offset_px = int(params.get("capacity_label_offset_px", group_default(render_defaults, "capacity_label_offset_px", _DEFAULTS.capacity_label_offset_px)))
    capacity_label_padding_px = int(params.get("capacity_label_padding_px", group_default(render_defaults, "capacity_label_padding_px", _DEFAULTS.capacity_label_padding_px)))
    axes = FlowNetworkAxes(
        node_count=int(query.node_count),
        target_cut_edge_count=int(query.target_cut_edge_count),
        target_flow_value=int(query.target_flow_value),
        distractor_edge_count=int(query.distractor_edge_count),
    )
    graph_rng = spawn_rng(int(instance_seed), f"{str(sampling_namespace)}.graph")
    last_error: Exception | None = None
    flow_sample: FlowNetworkSample | None = None
    render: FlowNetworkRender | None = None
    for attempt in range(max(1, int(max_attempts))):
        try:
            flow_sample = sample_flow_network(graph_rng, axes=axes, defaults=_DEFAULTS)
            render = render_flow_network_scene(
                flow_sample=flow_sample,
                render_params=render_params,
                layout_variant=str(query.layout_variant),
                layout_transform_variant=str(query.layout_transform_variant),
                capacity_label_font_size_px=int(capacity_label_font_size_px),
                capacity_label_offset_px=int(capacity_label_offset_px),
                capacity_label_padding_px=int(capacity_label_padding_px),
                instance_seed=int(instance_seed),
                attempt=int(attempt),
                params=params,
                background_defaults=POST_IMAGE_BACKGROUND_DEFAULTS,
                noise_defaults=POST_IMAGE_NOISE_DEFAULTS,
            )
            break
        except Exception as exc:  # pragma: no cover - retry path depends on sampled graph geometry
            last_error = exc
            continue
    else:
        raise RuntimeError("failed to generate flow-network instance") from last_error
    if flow_sample is None or render is None:
        raise RuntimeError("failed to generate flow-network instance")

    answer_value = _flow_answer_value(flow_sample, answer_mode=str(answer_mode))
    annotation_edges = tuple(flow_sample.original_min_cut_edges)
    annotation_projection = projected_edge_pair_annotation(render.rendered_scene, annotation_edges)
    annotation_point_pairs = tuple(
        [list(point) for point in pair]
        for pair in annotation_projection["point_pair_set"]
    )
    if len(annotation_point_pairs) != len(annotation_edges):
        raise RuntimeError("flow min-cut annotation projection is incomplete")
    return FlowNetworkInstanceBundle(
        query=query,
        render_params=render_params,
        flow_sample=flow_sample,
        render=render,
        answer_value=int(answer_value),
        annotation_edges=tuple(annotation_edges),
        annotation_projection=dict(annotation_projection),
        annotation_point_pairs=tuple(annotation_point_pairs),
        capacity_label_font_size_px=int(capacity_label_font_size_px),
        capacity_label_offset_px=int(capacity_label_offset_px),
        capacity_label_padding_px=int(capacity_label_padding_px),
    )


def build_flow_network_trace_payload(
    *,
    bundle: FlowNetworkInstanceBundle,
    prompt_bundle_id: str,
    prompt_artifacts: Any,
    trace_task_id: str,
) -> Dict[str, Any]:
    """Build trace metadata for one public flow-network task."""

    query = bundle.query
    render_params = bundle.render_params
    flow_sample = bundle.flow_sample
    render = bundle.render
    annotation_edge_set = set(tuple(edge) for edge in bundle.annotation_edges)
    node_entities = [
        {
            "entity_id": f"node_{node.label}",
            "entity_kind": "graph_node",
            "label": str(node.label),
            "role": "source" if str(node.label) == "S" else ("sink" if str(node.label) == "T" else "intermediate"),
            "degree": int(node.degree),
            "neighbors": list(node.neighbors),
            "successors": list(node.successors),
            "predecessors": list(node.predecessors),
            "center_px": list(node.center_xy),
            "bbox_xyxy": list(node.bbox_xyxy),
        }
        for node in render.rendered_scene.nodes
    ]
    edge_entities = [
        {
            "entity_id": str(edge.edge_id),
            "entity_kind": "graph_edge",
            "node_u_label": str(edge.node_u_label),
            "node_v_label": str(edge.node_v_label),
            "directed": bool(edge.directed),
            "segment_px": [list(edge.segment_px[0]), list(edge.segment_px[1])],
            "route_variant": str(edge.route_variant),
            "control_px": list(edge.control_px) if edge.control_px is not None else None,
            "capacity": int(edge.weight) if edge.weight is not None else None,
            "capacity_label_bbox_xyxy": list(edge.weight_label_bbox_xyxy) if edge.weight_label_bbox_xyxy is not None else None,
            "is_min_cut_edge": bool((str(edge.node_u_label), str(edge.node_v_label)) in annotation_edge_set),
        }
        for edge in render.rendered_scene.edges
    ]
    capacities_trace = _capacity_trace(flow_sample)
    return {
        "scene_ir": {
            "task_id": str(trace_task_id),
            "scene_id": SCENE_ID,
            "scene_kind": "graph_capacity_flow_network",
            "entities": [*node_entities, *edge_entities],
            "relations": {
                "query_id": str(query.query_id),
                "graph_directionality": "directed",
                "source_label": "S",
                "sink_label": "T",
                "capacity_by_edge": list(capacities_trace),
                "max_flow_value": int(flow_sample.original_max_flow_value),
                "minimum_cut_edges": [list(edge) for edge in flow_sample.original_min_cut_edges],
            },
            "frames": {
                "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                "panels": dict(render.rendered_scene.panel_geometry),
            },
        },
        "query_spec": {
            "task_id": str(trace_task_id),
            "query_id": str(query.query_id),
            "template_id": str(prompt_bundle_id),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "node_count": int(query.node_count),
                "node_count_probabilities": dict(query.node_count_probabilities),
                "target_answer": int(query.target_answer),
                "target_answer_probabilities": dict(query.target_answer_probabilities),
                "target_cut_edge_count": int(query.target_cut_edge_count),
                "target_cut_edge_count_probabilities": dict(query.target_cut_edge_count_probabilities),
                "target_flow_value": int(query.target_flow_value),
                "target_flow_value_probabilities": dict(query.target_flow_value_probabilities),
                "distractor_edge_count": int(query.distractor_edge_count),
                "distractor_edge_count_probabilities": dict(query.distractor_edge_count_probabilities),
                "layout_variant": str(query.layout_variant),
                "layout_variant_probabilities": dict(query.layout_variant_probabilities),
                "layout_transform_variant": str(query.layout_transform_variant),
                "layout_transform_variant_probabilities": dict(query.layout_transform_variant_probabilities),
                "edge_routing_variant": str(query.edge_routing_variant),
                "edge_routing_variant_probabilities": dict(query.edge_routing_variant_probabilities),
                "node_color_name": str(query.node_color_name),
                "node_color_name_probabilities": dict(query.node_color_name_probabilities),
            },
        },
        "render_spec": {
            "canvas_size": list(render.rendered_scene.panel_geometry["canvas_size"]),
            "coord_space": "pixel",
            "panel_geometry": dict(render.rendered_scene.panel_geometry),
            "style": {
                "node_color_name": str(query.node_color_name),
                "theme_tone": str(render_params.theme_tone),
                "panel_style_variant": str(render_params.panel_style_variant),
                "background_color_rgb": list(render_params.background_color_rgb),
                "panel_fill_rgb": list(render_params.panel_fill_rgb),
                "panel_border_rgb": list(render_params.panel_border_rgb),
                "title_color_rgb": list(render_params.title_color_rgb),
                "edge_color_rgb": list(render_params.edge_color_rgb),
                "node_fill_rgb": list(render_params.node_fill_rgb),
                "node_border_rgb": list(render_params.node_border_rgb),
                "label_text_rgb": list(render_params.label_text_rgb),
                "label_stroke_rgb": list(render_params.label_stroke_rgb),
                "node_shape_variant": "circle",
                "node_radius_px": int(render_params.node_radius_px),
                "edge_width_px": int(render_params.edge_width_px),
                "edge_routing_variant": str(render.rendered_scene.edge_routing_variant),
                "arrow_length_px": int(render_params.arrow_length_px),
                "arrow_width_px": int(render_params.arrow_width_px),
                "node_border_width_px": int(render_params.node_border_width_px),
                "label_font_size_px": int(render_params.label_font_size_px),
                "resolved_label_font_size_px": int(render.rendered_scene.resolved_label_font_size_px),
                "label_stroke_width_px": int(render.rendered_scene.resolved_label_stroke_width_px),
                "capacity_label_font_size_px": int(bundle.capacity_label_font_size_px),
                "capacity_label_offset_px": int(bundle.capacity_label_offset_px),
                "capacity_label_padding_px": int(bundle.capacity_label_padding_px),
                "font_family": str(render_params.font_family or ""),
                "font_asset": dict(render_params.font_asset) if isinstance(render_params.font_asset, Mapping) else {},
                "font_asset_version": str(render_params.font_asset_version or ""),
                "font_exclusion_reason": str(render_params.font_exclusion_reason),
                "context_text_elements": list(render.rendered_scene.panel_geometry.get("context_text_elements", [])),
                "background_meta": dict(render.background_meta),
                "post_image_noise_meta": dict(render.post_noise_meta),
            },
        },
        "render_map": {"image_id": "img0", "anchors": {}},
        "execution_trace": {
            "task_id": str(trace_task_id),
            "scene_id": SCENE_ID,
            "query_id": str(query.query_id),
            "graph_directionality": "directed",
            "node_count": int(query.node_count),
            "edge_count": int(flow_sample.graph_sample.edge_count),
            "source_label": "S",
            "sink_label": "T",
            "answer": int(bundle.answer_value),
            "max_flow_value": int(flow_sample.original_max_flow_value),
            "minimum_cut_edge_count": int(len(flow_sample.original_min_cut_edges)),
            "minimum_cut_edges": [list(edge) for edge in flow_sample.original_min_cut_edges],
            "minimum_cut_partition": [list(flow_sample.original_min_cut_partition[0]), list(flow_sample.original_min_cut_partition[1])],
            "capacity_by_edge": list(capacities_trace),
            "successors_by_label": {str(key): list(values) for key, values in flow_sample.graph_sample.successors_by_label.items()},
            "predecessors_by_label": {str(key): list(values) for key, values in flow_sample.graph_sample.predecessors_by_label.items()},
            "layout_variant_requested": str(query.layout_variant),
            "layout_variant_used": str(render.rendered_scene.layout_variant),
            "layout_transform_variant": str(render.rendered_scene.layout_transform_variant),
            "edge_routing_variant": str(render.rendered_scene.edge_routing_variant),
            "node_color_name": str(query.node_color_name),
            "crossing_count": int(render.rendered_scene.crossing_count),
        },
        "witness_symbolic": {
            "type": "directed_edge_pair_set",
            "edges": [list(edge) for edge in bundle.annotation_edges],
        },
        "projected_annotation": {
            "type": "point_pair_set",
            **dict(bundle.annotation_projection),
        },
    }


__all__ = [
    "FlowNetworkInstanceBundle",
    "ResolvedFlowNetwork",
    "build_flow_network_instance_bundle",
    "build_flow_network_trace_payload",
]
