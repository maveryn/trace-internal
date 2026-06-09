"""Count source or sink nodes in a directed node-link graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.prompt_examples import build_graph_prompt_json_examples
from ..shared.complexity import (
    build_graph_complexity,
    normalize_float_with_bounds,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.graph_sampling import (
    SUPPORTED_SOURCE_SINK_MODES,
    SUPPORTED_TOPOLOGY_PROFILES,
    feasible_node_counts_for_source_sink_count,
    graph_label_sort_key,
    sample_source_sink_count_graph,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    projected_node_point_annotation,
    render_graph_scene,
)
from ..shared.node_link_axes import resolve_node_link_visual_axes
from ..shared.task_scaffolding import graph_hashed_axis_selection_index
from ..shared.task_support import (
    graph_balanced_axis_count,
    graph_query_probabilities_from_alias_map,
    resolve_graph_named_variant,
    resolve_graph_render_params,
)
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "graph_node_link_source_sink_count_internal"
SCENE_ID = "node_link"
QUERY_ID_BY_MODE = {
    "source": "directed_source_count",
    "sink": "directed_sink_count",
}
DEGREE_MODE_BY_SOURCE_SINK_MODE = {
    "source": "in_degree",
    "sink": "out_degree",
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for source/sink count scenes."""

    node_count_min: int = 5
    directed_node_count_max: int = 10
    target_count_min: int = 0
    target_count_max: int = 4
    directed_degree_sequence_max_degree: int = 4
    graph_search_attempts: int = 100
    canvas_width: int = 864
    canvas_height: int = 640
    outer_margin_px: int = 28
    panel_padding_px: int = 24
    panel_corner_radius_px: int = 20
    panel_title_font_size_px: int = 24
    node_shape_variant: str = "circle"
    node_radius_min_px: int = 18
    node_radius_max_px: int = 24
    edge_width_px: int = 4
    arrow_length_px: int = 12
    arrow_width_px: int = 7
    node_border_width_px: int = 2
    label_font_size_px: int = 20
    background_color_rgb: Tuple[int, int, int] = (247, 248, 251)
    panel_fill_rgb: Tuple[int, int, int] = (255, 255, 255)
    panel_border_rgb: Tuple[int, int, int] = (205, 212, 224)
    title_color_rgb: Tuple[int, int, int] = (70, 78, 96)
    edge_color_rgb: Tuple[int, int, int] = (118, 128, 145)
    node_fill_rgb: Tuple[int, int, int] = (92, 124, 250)
    node_border_rgb: Tuple[int, int, int] = (52, 73, 144)
    label_text_rgb: Tuple[int, int, int] = (255, 255, 255)
    label_stroke_rgb: Tuple[int, int, int] = (52, 73, 144)


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved source/sink query support and style axes."""

    source_sink_mode: str
    degree_mode: str
    query_id: str
    node_count: int
    target_count: int
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    source_sink_mode_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    topology_profile_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    edge_routing_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="counting")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="counting", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _mode_from_query_alias(value: Any) -> str | None:
    """Return source/sink mode encoded by public query/task aliases."""

    text = str(value or "").strip()
    if text in {"source", "source_count", "directed_source_count"}:
        return "source"
    if text in {"sink", "sink_count", "directed_sink_count"}:
        return "sink"
    return None


def _forced_source_sink_mode(params: Mapping[str, Any]) -> str | None:
    """Return an explicitly requested source/sink mode, if present."""

    explicit = params.get("source_sink_mode")
    if explicit is not None:
        mode = _mode_from_query_alias(explicit)
        if mode is None:
            raise ValueError(f"unsupported source_sink_mode: {explicit}")
        return str(mode)
    for key in ("query_id", "query_variant"):
        mode = _mode_from_query_alias(params.get(str(key)))
        if mode is not None:
            return str(mode)
    return None




def _node_count_selection_index(
    instance_seed: int,
    *,
    selection_index: int,
    source_sink_mode: str,
    target_count: int,
    topology_profile: str,
) -> int:
    """Return an independent node-count index for the resolved query support."""

    return graph_hashed_axis_selection_index(
        int(instance_seed),
        task_id=TASK_ID,
        axis_name="node_count",
        selection_index=int(selection_index),
        axis_values=(str(source_sink_mode), int(target_count), str(topology_profile)),
    )


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one source/sink count query."""

    forced_mode = _forced_source_sink_mode(params)
    if forced_mode is None:
        mode_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.source_sink_mode")
        source_sink_mode, source_sink_probabilities = resolve_graph_named_variant(
            mode_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            explicit_key="source_sink_mode",
            weights_key="source_sink_mode_weights",
            balance_flag_key="balanced_source_sink_mode_sampling",
            supported=SUPPORTED_SOURCE_SINK_MODES,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            namespace="source_sink_mode",
        )
    else:
        source_sink_mode = str(forced_mode)
        source_sink_probabilities = {
            str(mode): (1.0 if str(mode) == str(source_sink_mode) else 0.0)
            for mode in SUPPORTED_SOURCE_SINK_MODES
        }

    topology_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.topology_profile")
    topology_profile, topology_probabilities = resolve_graph_named_variant(
        topology_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="topology_profile",
        weights_key="topology_profile_weights",
        balance_flag_key="balanced_topology_profile_sampling",
        supported=SUPPORTED_TOPOLOGY_PROFILES,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="topology_profile",
    )

    target_count_min = int(params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min)))
    target_count_max = int(params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max)))
    node_count_min = int(params.get("node_count_min", group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)))
    node_count_max = int(
        params.get(
            "directed_node_count_max",
            group_default(_GEN_DEFAULTS, "directed_node_count_max", _DEFAULTS.directed_node_count_max),
        )
    )
    max_degree = int(
        params.get(
            "directed_degree_sequence_max_degree",
            group_default(_GEN_DEFAULTS, "directed_degree_sequence_max_degree", _DEFAULTS.directed_degree_sequence_max_degree),
        )
    )

    feasible_targets = []
    feasible_node_support_by_target: Dict[int, Tuple[int, ...]] = {}
    for target_count in range(int(target_count_min), int(target_count_max) + 1):
        feasible_nodes = feasible_node_counts_for_source_sink_count(
            source_sink_mode=str(source_sink_mode),
            target_count=int(target_count),
            node_count_min=int(node_count_min),
            node_count_max=int(node_count_max),
            max_degree=int(max_degree),
        )
        if feasible_nodes:
            feasible_targets.append(int(target_count))
            feasible_node_support_by_target[int(target_count)] = tuple(int(value) for value in feasible_nodes)
    if not feasible_targets:
        raise ValueError("no feasible source/sink count support exists")

    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:target_count",
        )
    )
    source_sink_axis_count = graph_balanced_axis_count(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        probabilities=source_sink_probabilities,
        balance_flag_key="balanced_source_sink_mode_sampling",
        explicit_keys=("source_sink_mode", "query_id", "query_variant"),
        weights_key="source_sink_mode_weights",
    )

    explicit_target = params.get("target_count")
    if explicit_target is not None:
        target_count = int(explicit_target)
        if int(target_count) not in feasible_targets:
            raise ValueError("target_count is outside feasible support for source/sink count")
    else:
        target_selection_index = int(selection_index)
        if bool(
            params.get(
                "balanced_target_count_sampling",
                group_default(_GEN_DEFAULTS, "balanced_target_count_sampling", True),
            )
        ):
            target_selection_index = int(target_selection_index // int(source_sink_axis_count))
        target_count = int(feasible_targets[int(target_selection_index % len(feasible_targets))])

    feasible_node_support = feasible_node_support_by_target[int(target_count)]
    explicit_node_count = params.get("node_count")
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
    else:
        node_index = _node_count_selection_index(
            int(instance_seed),
            selection_index=int(selection_index),
            source_sink_mode=str(source_sink_mode),
            target_count=int(target_count),
            topology_profile=str(topology_profile),
        )
        node_count = int(feasible_node_support[int(node_index % len(feasible_node_support))])
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for source/sink count")

    visual_axes = resolve_node_link_visual_axes(
        int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        task_id=TASK_ID,
    )

    source_sink_probabilities = {str(key): float(value) for key, value in source_sink_probabilities.items()}
    query_probabilities = graph_query_probabilities_from_alias_map(source_sink_probabilities, QUERY_ID_BY_MODE)
    return _ResolvedQuery(
        source_sink_mode=str(source_sink_mode),
        degree_mode=str(DEGREE_MODE_BY_SOURCE_SINK_MODE[str(source_sink_mode)]),
        query_id=str(QUERY_ID_BY_MODE[str(source_sink_mode)]),
        node_count=int(node_count),
        target_count=int(target_count),
        topology_profile=str(topology_profile),
        layout_variant=str(visual_axes.layout_variant),
        label_variant=str(visual_axes.label_variant),
        node_shape_variant=str(visual_axes.node_shape_variant),
        layout_transform_variant=str(visual_axes.layout_transform_variant),
        edge_routing_variant=str(visual_axes.edge_routing_variant),
        node_color_name=str(visual_axes.node_color_name),
        source_sink_mode_probabilities=dict(source_sink_probabilities),
        query_id_probabilities=dict(query_probabilities),
        node_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_node_support),
                selected=int(node_count) if explicit_node_count is not None else None,
            )
        ),
        target_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_targets),
                selected=int(target_count) if explicit_target is not None else None,
            )
        ),
        topology_profile_probabilities=dict(topology_probabilities),
        layout_variant_probabilities=dict(visual_axes.layout_variant_probabilities),
        label_variant_probabilities=dict(visual_axes.label_variant_probabilities),
        node_shape_variant_probabilities=dict(visual_axes.node_shape_variant_probabilities),
        layout_transform_variant_probabilities=dict(visual_axes.layout_transform_variant_probabilities),
        edge_routing_variant_probabilities=dict(visual_axes.edge_routing_variant_probabilities),
        node_color_name_probabilities=dict(visual_axes.node_color_name_probabilities),
    )


def _build_complexity(
    *,
    graph_sample: Any,
    query: _ResolvedQuery,
    render_params: GraphRenderParams,
    rendered_scene: Any,
) -> Any:
    """Build one within-task normalized complexity record."""

    node_count = int(query.node_count)
    edge_count = int(graph_sample.edge_count)
    max_edges = int(node_count * (node_count - 1))
    edge_density = 0.0 if int(max_edges) <= 0 else float(edge_count) / float(max_edges)
    crossing_norm = normalize_float_with_bounds(float(rendered_scene.crossing_count), (0.0, max(1.0, float(max_edges))))
    degrees = (
        list(graph_sample.in_degrees_by_label.values())
        if str(query.source_sink_mode) == "source"
        else list(graph_sample.out_degrees_by_label.values())
    )
    near_zero_count = sum(1 for degree in degrees if int(degree) == 1)
    components = {
        "visual_scan": (0.65 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.directed_node_count_max)))
        + (0.35 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0))),
        "topology_reasoning": (0.55 * normalize_int_with_bounds(len(set(int(value) for value in degrees)), (1, int(node_count))))
        + (0.45 * normalize_int_with_bounds(int(edge_count), (0, int(max_edges)))),
        "ambiguity": (0.65 * normalize_int_with_bounds(int(near_zero_count), (0, int(node_count))))
        + (0.35 * normalize_int_with_bounds(int(query.target_count), (_DEFAULTS.target_count_min, _DEFAULTS.target_count_max))),
        "clutter": (0.60 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.25 * crossing_norm)
        + (0.15 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px))),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


class GraphCountingSourceSinkCountTask:
    """Count source or sink nodes in a directed graph."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic source/sink count instance."""

        query = _resolve_query(int(instance_seed), params=params)
        render_params = resolve_graph_render_params(
            params,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            node_color_name=str(query.node_color_name),
            node_shape_variant=str(query.node_shape_variant),
            edge_routing_variant=str(query.edge_routing_variant),
        )
        max_degree = int(
            params.get(
                "directed_degree_sequence_max_degree",
                group_default(_GEN_DEFAULTS, "directed_degree_sequence_max_degree", _DEFAULTS.directed_degree_sequence_max_degree),
            )
        )
        search_attempts = int(params.get("graph_search_attempts", group_default(_GEN_DEFAULTS, "graph_search_attempts", _DEFAULTS.graph_search_attempts)))

        graph_rng = spawn_rng(int(instance_seed), "graph_structure")
        last_error: Exception | None = None
        graph_sample = None
        rendered_scene = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                graph_sample = sample_source_sink_count_graph(
                    graph_rng,
                    source_sink_mode=str(query.source_sink_mode),
                    node_count=int(query.node_count),
                    target_count=int(query.target_count),
                    max_degree=int(max_degree),
                    topology_profile=str(query.topology_profile),
                    label_variant=str(query.label_variant),
                    search_attempts=max(1, int(search_attempts)),
                )
                background, background_meta = make_background_canvas(
                    canvas_width=int(render_params.canvas_width),
                    canvas_height=int(render_params.canvas_height),
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
                )
                rendered_scene = render_graph_scene(
                    graph_sample=graph_sample,
                    layout_variant=str(query.layout_variant),
                    layout_transform_variant=str(query.layout_transform_variant),
                    render_params=render_params,
                    layout_seed=int(instance_seed + attempt),
                    scene_title="Directed Graph",
                    directed=True,
                    base_image=background,
                )
                image, post_noise_meta = apply_post_image_noise(
                    rendered_scene.image,
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_NOISE_DEFAULTS,
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through retry loop
                last_error = exc
                continue
        else:
            raise RuntimeError("failed to generate graph source/sink count instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_directed",
                "annotation_hint_source_count",
                "annotation_hint_sink_count",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_json_example, prompt_json_example_answer_only = build_graph_prompt_json_examples(annotation_value=[[180, 220], [310, 180]], answer_value=2)
        prompt_query_key = "source_count" if str(query.source_sink_mode) == "source" else "sink_count"
        annotation_hint_key = f"annotation_hint_{prompt_query_key}"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(prompt_query_key),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_directed"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[annotation_hint_key]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_json_example),
                "json_example_answer_only": str(prompt_json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_labels = tuple(sorted((str(label) for label in graph_sample.target_labels), key=graph_label_sort_key))
        answer_gt = TypedValue(type="integer", value=int(len(annotation_labels)))
        annotation_projection = projected_node_point_annotation(rendered_scene, annotation_labels)
        annotation_points = [list(point) for point in annotation_projection["pixel_point_set"]]
        annotation_gt = TypedValue(type="point_set", value=list(annotation_points))
        node_entities = [
            {
                "entity_id": f"node_{node.label}",
                "entity_kind": "graph_node",
                "label": str(node.label),
                "degree": int(graph_sample.degrees_by_label[str(node.label)]),
                "in_degree": int(graph_sample.in_degrees_by_label[str(node.label)]),
                "out_degree": int(graph_sample.out_degrees_by_label[str(node.label)]),
                "neighbors": list(node.neighbors),
                "successors": list(node.successors),
                "predecessors": list(node.predecessors),
                "is_source_sink_node": bool(str(node.label) in set(annotation_labels)),
                "center_px": list(node.center_xy),
                "bbox_xyxy": list(node.bbox_xyxy),
            }
            for node in rendered_scene.nodes
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
            }
            for edge in rendered_scene.edges
        ]
        complexity = _build_complexity(
            graph_sample=graph_sample,
            query=query,
            render_params=render_params,
            rendered_scene=rendered_scene,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "graph_source_sink_counting",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "query_id": str(query.query_id),
                    "counting_rule": "nodes_with_zero_in_degree" if str(query.source_sink_mode) == "source" else "nodes_with_zero_out_degree",
                    "graph_directionality": "directed",
                    "source_sink_mode": str(query.source_sink_mode),
                    "degree_mode": str(query.degree_mode),
                    "query_degree": 0,
                    "matching_labels": list(annotation_labels),
                    "query_id_probabilities": dict(query.query_id_probabilities),
                    "source_sink_mode_probabilities": dict(query.source_sink_mode_probabilities),
                    "successors_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                    "predecessors_by_label": {str(key): list(values) for key, values in graph_sample.predecessors_by_label.items()},
                    "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                    "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                    "in_degrees_by_label": {str(key): int(value) for key, value in graph_sample.in_degrees_by_label.items()},
                    "out_degrees_by_label": {str(key): int(value) for key, value in graph_sample.out_degrees_by_label.items()},
                    "edge_labels": [list(edge) for edge in graph_sample.edge_labels],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered_scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query.query_id),
                    "internal_query_id": str(query.query_id),
                    "query_id_probabilities": dict(query.query_id_probabilities),
                    "source_sink_mode": str(query.source_sink_mode),
                    "source_sink_mode_probabilities": dict(query.source_sink_mode_probabilities),
                    "graph_directionality": "directed",
                    "degree_mode": str(query.degree_mode),
                    "query_degree": 0,
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "target_count": int(query.target_count),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "target_count_probabilities": dict(query.target_count_probabilities),
                    "topology_profile": str(query.topology_profile),
                    "topology_profile_probabilities": dict(query.topology_profile_probabilities),
                    "layout_variant": str(query.layout_variant),
                    "layout_variant_probabilities": dict(query.layout_variant_probabilities),
                    "label_variant": str(query.label_variant),
                    "label_variant_probabilities": dict(query.label_variant_probabilities),
                    "node_shape_variant": str(query.node_shape_variant),
                    "node_shape_variant_probabilities": dict(query.node_shape_variant_probabilities),
                    "layout_transform_variant": str(query.layout_transform_variant),
                    "layout_transform_variant_probabilities": dict(query.layout_transform_variant_probabilities),
                    "edge_routing_variant": str(query.edge_routing_variant),
                    "edge_routing_variant_probabilities": dict(query.edge_routing_variant_probabilities),
                    "node_color_name": str(query.node_color_name),
                    "node_color_name_probabilities": dict(query.node_color_name_probabilities),
                    "directed_degree_sequence_max_degree": int(max_degree),
                },
            },
            "render_spec": {
                "canvas_size": list(rendered_scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(rendered_scene.panel_geometry),
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
                    "node_shape_variant": str(render_params.node_shape_variant),
                    "node_radius_px": int(render_params.node_radius_px),
                    "edge_width_px": int(render_params.edge_width_px),
                    "edge_routing_variant": str(rendered_scene.edge_routing_variant),
                    "arrow_length_px": int(render_params.arrow_length_px),
                    "arrow_width_px": int(render_params.arrow_width_px),
                    "node_border_width_px": int(render_params.node_border_width_px),
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "resolved_label_font_size_px": int(rendered_scene.resolved_label_font_size_px),
                    "label_stroke_width_px": int(rendered_scene.resolved_label_stroke_width_px),
                    "background_meta": dict(background_meta),
                    "post_image_noise_meta": dict(post_noise_meta),
                },
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {},
            },
            "execution_trace": {
                "query_id": str(query.query_id),
                "internal_query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": str(prompt_query_key),
                "graph_directionality": "directed",
                "source_sink_mode": str(query.source_sink_mode),
                "source_sink_mode_probabilities": dict(query.source_sink_mode_probabilities),
                "degree_mode": str(query.degree_mode),
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "query_degree": 0,
                "target_count": int(query.target_count),
                "target_count_probabilities": dict(query.target_count_probabilities),
                "matching_labels": list(annotation_labels),
                "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                "in_degrees_by_label": {str(key): int(value) for key, value in graph_sample.in_degrees_by_label.items()},
                "out_degrees_by_label": {str(key): int(value) for key, value in graph_sample.out_degrees_by_label.items()},
                "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                "successors_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                "predecessors_by_label": {str(key): list(values) for key, values in graph_sample.predecessors_by_label.items()},
                "in_degree_sequence": list(graph_sample.in_degree_sequence),
                "out_degree_sequence": list(graph_sample.out_degree_sequence),
                "topology_profile": str(graph_sample.topology_profile),
                "topology_profile_probabilities": dict(query.topology_profile_probabilities),
                "label_variant": str(graph_sample.label_variant),
                "node_shape_variant": str(render_params.node_shape_variant),
                "layout_variant_requested": str(query.layout_variant),
                "layout_variant_used": str(rendered_scene.layout_variant),
                "layout_transform_variant": str(rendered_scene.layout_transform_variant),
                "edge_routing_variant": str(rendered_scene.edge_routing_variant),
                "node_color_name": str(query.node_color_name),
                "crossing_count": int(rendered_scene.crossing_count),
            },
            "witness_symbolic": {
                "type": "object_set",
                "labels": list(annotation_labels),
                "source_sink_mode": str(query.source_sink_mode),
                "degree_mode": str(query.degree_mode),
                "query_degree": 0,
            },
            "projected_annotation": {
                "type": "point_set",
                "point_set": list(annotation_points),
                **dict(annotation_projection),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphCountingSourceSinkCountTask"]
