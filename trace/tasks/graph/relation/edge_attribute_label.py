"""Read the visible text label bound to one queried graph edge."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.complexity import (
    build_graph_complexity,
    normalize_float_with_bounds,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.graph_sampling import (
    SUPPORTED_EDGE_ATTRIBUTE_LABEL_DIRECTIONS,
    SUPPORTED_LAYOUT_VARIANTS,
    SUPPORTED_NODE_LINK_LABEL_VARIANTS,
    SUPPORTED_TOPOLOGY_PROFILES,
    feasible_node_counts_for_shortest_path_length,
    sample_edge_attribute_label_graph,
    sample_edge_attribute_path_label_graph,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    SUPPORTED_EDGE_ROUTING_VARIANTS,
    SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    SUPPORTED_NODE_SHAPE_VARIANTS,
    projected_edge_label_bbox_evidence,
    render_graph_scene,
)
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import (
    format_graph_prompt_label,
    graph_edge_label_entries,
    graph_uniform_label_probability_map,
    resolve_graph_balanced_node_color_name,
    resolve_graph_edge_label_support_from_params,
    resolve_graph_named_variant,
    resolve_graph_render_params,
)
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__node_link__edge_attribute_label"
SCENE_ID = "node_link"

PATH_FIRST_EDGE_QUERY_ID = "shortest_path_first_edge_label"
SUPPORTED_EDGE_ATTRIBUTE_QUERY_IDS = (
    "edge_between_nodes_label",
    "directed_edge_between_nodes_label",
    PATH_FIRST_EDGE_QUERY_ID,
)
FIXED_DIRECTIONALITY_BY_QUERY_ID = {
    "edge_between_nodes_label": "undirected",
    "directed_edge_between_nodes_label": "directed",
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for edge-label relation scenes."""

    node_count_min: int = 5
    node_count_max: int = 8
    directed_node_count_max: int = 8
    target_shortest_path_length_min: int = 2
    target_shortest_path_length_max: int = 3
    degree_sequence_max_degree: int = 4
    directed_degree_sequence_max_degree: int = 4
    edge_label_support_size: int = 6
    edge_label_min_chars: int = 3
    edge_label_max_chars: int = 12
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
    """Resolved support and style axes for one labeled-edge query."""

    graph_directionality: str
    query_id: str
    node_count: int
    target_shortest_path_length: int | None
    target_edge_label: str
    edge_label_support: Tuple[str, ...]
    edge_label_source_kind: str
    edge_label_bucket: str
    edge_label_manifest: str
    edge_label_filter: Mapping[str, Any]
    edge_label_bucket_probabilities: Dict[str, float]
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    query_id_probabilities: Dict[str, float]
    graph_directionality_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    target_shortest_path_length_probabilities: Dict[str, float]
    target_edge_label_probabilities: Dict[str, float]
    topology_profile_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    edge_routing_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="relation")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="relation", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return prompt examples that match the edge-label bbox evidence format."""

    example_evidence = [[240, 190, 308, 214]]
    return (
        json.dumps({"evidence": example_evidence, "answer": "feeds"}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps({"answer": "feeds"}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )




def _query_id_from_alias(value: Any) -> str | None:
    """Return the public query id encoded by one query/task alias."""

    text = str(value or "").strip()
    aliases = {
        "edge_between_nodes_label": "edge_between_nodes_label",
        "undirected_edge_between_nodes_label": "edge_between_nodes_label",
        "directed_edge_between_nodes_label": "directed_edge_between_nodes_label",
        "shortest_path_first_edge_label": PATH_FIRST_EDGE_QUERY_ID,
        "path_first_edge_label": PATH_FIRST_EDGE_QUERY_ID,
        "edge_attribute_label": None,
        "default": None,
    }
    return aliases.get(text)


def _forced_query_id(params: Mapping[str, Any]) -> str | None:
    """Resolve an explicit public query id, if present."""

    for key in ("query_id", "query_variant", "query_variant"):
        query_id = _query_id_from_alias(params.get(str(key)))
        if query_id is not None:
            return str(query_id)
    explicit_directionality = params.get("graph_directionality")
    if explicit_directionality is not None:
        directionality = str(explicit_directionality).strip()
        if directionality == "undirected":
            return "edge_between_nodes_label"
        if directionality == "directed":
            return "directed_edge_between_nodes_label"
    return None


def _forced_graph_directionality(params: Mapping[str, Any], *, query_id: str) -> str | None:
    """Resolve an explicit or query-implied graph directionality, if present."""

    query_directionality = FIXED_DIRECTIONALITY_BY_QUERY_ID.get(str(query_id))

    explicit = params.get("graph_directionality")
    if explicit is None:
        return query_directionality
    explicit_directionality = str(explicit).strip()
    if explicit_directionality not in set(SUPPORTED_EDGE_ATTRIBUTE_LABEL_DIRECTIONS):
        raise ValueError(f"unsupported graph_directionality: {explicit}")
    if query_directionality is not None and str(query_directionality) != str(explicit_directionality):
        raise ValueError("query_id is incompatible with graph_directionality")
    return str(explicit_directionality)


def _node_count_selection_index(
    instance_seed: int,
    *,
    selection_index: int,
    graph_directionality: str,
    target_edge_label: str,
    topology_profile: str,
) -> int:
    """Return an independent node-count index for the resolved labeled-edge query."""

    namespace = (
        f"{TASK_ID}:node_count:"
        f"{str(graph_directionality)}:{str(target_edge_label)}:{str(topology_profile)}"
    )
    return int(hash64(int(instance_seed), namespace, int(selection_index)))


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one edge-attribute lookup query."""

    forced_query_id = _forced_query_id(params)
    if forced_query_id is None:
        query_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_variant")
        query_id, query_id_probabilities = resolve_graph_named_variant(
            query_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            explicit_key="query_id",
            weights_key="query_variant_weights",
            balance_flag_key="balanced_query_variant_sampling",
            supported=SUPPORTED_EDGE_ATTRIBUTE_QUERY_IDS,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            namespace="query_variant",
        )
    else:
        query_id = str(forced_query_id)
        query_id_probabilities = {
            str(supported_query_id): (1.0 if str(supported_query_id) == str(query_id) else 0.0)
            for supported_query_id in SUPPORTED_EDGE_ATTRIBUTE_QUERY_IDS
        }

    forced_directionality = _forced_graph_directionality(params, query_id=str(query_id))
    if forced_directionality is None:
        direction_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.graph_directionality")
        graph_directionality, graph_directionality_probabilities = resolve_graph_named_variant(
            direction_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            explicit_key="graph_directionality",
            weights_key="graph_directionality_weights",
            balance_flag_key="balanced_graph_directionality_sampling",
            supported=SUPPORTED_EDGE_ATTRIBUTE_LABEL_DIRECTIONS,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            namespace="graph_directionality",
        )
    else:
        graph_directionality = str(forced_directionality)
        graph_directionality_probabilities = {
            str(directionality): (1.0 if str(directionality) == str(graph_directionality) else 0.0)
            for directionality in SUPPORTED_EDGE_ATTRIBUTE_LABEL_DIRECTIONS
        }

    edge_label_support, edge_label_metadata = resolve_graph_edge_label_support_from_params(
        int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        task_id=TASK_ID,
        default_support_size=_DEFAULTS.edge_label_support_size,
        default_min_chars=_DEFAULTS.edge_label_min_chars,
        default_max_chars=_DEFAULTS.edge_label_max_chars,
    )
    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:target_edge_label",
        )
    )
    target_label_index = int(selection_index)
    if forced_query_id is None:
        target_label_index = int(selection_index // max(1, len(SUPPORTED_EDGE_ATTRIBUTE_QUERY_IDS)))
    explicit_target_label = params.get("target_edge_label")
    if explicit_target_label is not None:
        target_edge_label = str(explicit_target_label).strip().lower()
        if str(target_edge_label) not in set(edge_label_support):
            raise ValueError("target_edge_label is outside edge_label_support")
    else:
        if bool(params.get("balanced_target_edge_label_sampling", group_default(_GEN_DEFAULTS, "balanced_target_edge_label_sampling", True))):
            target_edge_label = str(edge_label_support[int(target_label_index % len(edge_label_support))])
        else:
            label_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.target_edge_label")
            target_edge_label = str(edge_label_support[int(label_rng.randrange(len(edge_label_support)))])

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

    target_shortest_path_length: int | None = None
    target_shortest_path_length_probabilities: Dict[str, float] = {}
    if str(query_id) == PATH_FIRST_EDGE_QUERY_ID:
        length_min = int(
            params.get(
                "target_shortest_path_length_min",
                group_default(_GEN_DEFAULTS, "target_shortest_path_length_min", _DEFAULTS.target_shortest_path_length_min),
            )
        )
        length_max = int(
            params.get(
                "target_shortest_path_length_max",
                group_default(_GEN_DEFAULTS, "target_shortest_path_length_max", _DEFAULTS.target_shortest_path_length_max),
            )
        )
        length_support = tuple(int(value) for value in range(max(1, int(length_min)), int(length_max) + 1))
        if not length_support:
            raise ValueError("target_shortest_path_length support is empty")
        explicit_path_length = params.get("target_shortest_path_length")
        if explicit_path_length is not None:
            target_shortest_path_length = int(explicit_path_length)
            if int(target_shortest_path_length) not in set(length_support):
                raise ValueError("target_shortest_path_length is outside configured support")
        else:
            length_index = int(target_label_index // max(1, len(edge_label_support)))
            target_shortest_path_length = int(length_support[int(length_index % len(length_support))])
        target_shortest_path_length_probabilities = dict(
            uniform_probability_map(
                tuple(int(value) for value in length_support),
                selected=int(target_shortest_path_length) if explicit_path_length is not None else None,
            )
        )

    node_count_min = int(params.get("node_count_min", group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)))
    node_count_max_key = "directed_node_count_max" if str(graph_directionality) == "directed" else "node_count_max"
    node_count_max_fallback = _DEFAULTS.directed_node_count_max if str(graph_directionality) == "directed" else _DEFAULTS.node_count_max
    node_count_max = int(params.get(node_count_max_key, group_default(_GEN_DEFAULTS, node_count_max_key, node_count_max_fallback)))
    if str(query_id) == PATH_FIRST_EDGE_QUERY_ID:
        feasible_node_support = feasible_node_counts_for_shortest_path_length(
            target_shortest_path_length=int(target_shortest_path_length or 1),
            node_count_min=int(node_count_min),
            node_count_max=int(node_count_max),
        )
    else:
        feasible_node_support = tuple(int(value) for value in range(max(2, int(node_count_min)), int(node_count_max) + 1))
    if not feasible_node_support:
        raise ValueError("no feasible node_count support exists for edge-attribute label")
    explicit_node_count = params.get("node_count")
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
        if int(node_count) not in set(feasible_node_support):
            raise ValueError("node_count is outside feasible support for edge-attribute label")
    else:
        node_index = _node_count_selection_index(
            int(instance_seed),
            selection_index=int(selection_index),
            graph_directionality=str(graph_directionality),
            target_edge_label=str(target_edge_label),
            topology_profile=str(topology_profile),
        )
        node_count = int(feasible_node_support[int(node_index % len(feasible_node_support))])

    layout_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.layout_variant")
    layout_variant, layout_probabilities = resolve_graph_named_variant(
        layout_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="layout_variant",
        weights_key="layout_variant_weights",
        balance_flag_key="balanced_layout_variant_sampling",
        supported=SUPPORTED_LAYOUT_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="layout_variant",
    )
    label_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.label_variant")
    label_variant, label_variant_probabilities = resolve_graph_named_variant(
        label_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="label_variant",
        weights_key="label_variant_weights",
        balance_flag_key="balanced_label_variant_sampling",
        supported=SUPPORTED_NODE_LINK_LABEL_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="label_variant",
    )
    shape_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.node_shape_variant")
    node_shape_variant, node_shape_variant_probabilities = resolve_graph_named_variant(
        shape_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="node_shape_variant",
        weights_key="node_shape_variant_weights",
        balance_flag_key="balanced_node_shape_variant_sampling",
        supported=SUPPORTED_NODE_SHAPE_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="node_shape_variant",
    )
    transform_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.layout_transform_variant")
    layout_transform_variant, layout_transform_variant_probabilities = resolve_graph_named_variant(
        transform_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="layout_transform_variant",
        weights_key="layout_transform_variant_weights",
        balance_flag_key="balanced_layout_transform_variant_sampling",
        supported=SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="layout_transform_variant",
    )
    edge_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.edge_routing_variant")
    edge_routing_variant, edge_routing_variant_probabilities = resolve_graph_named_variant(
        edge_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="edge_routing_variant",
        weights_key="edge_routing_variant_weights",
        balance_flag_key="balanced_edge_routing_variant_sampling",
        supported=SUPPORTED_EDGE_ROUTING_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="edge_routing_variant",
    )
    node_color_name, node_color_name_probabilities = resolve_graph_balanced_node_color_name(
        int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        task_id=TASK_ID,
        supported=SUPPORTED_NODE_COLOR_NAMES,
    )

    return _ResolvedQuery(
        graph_directionality=str(graph_directionality),
        query_id=str(query_id),
        node_count=int(node_count),
        target_shortest_path_length=int(target_shortest_path_length) if target_shortest_path_length is not None else None,
        target_edge_label=str(target_edge_label),
        edge_label_support=tuple(str(label) for label in edge_label_support),
        edge_label_source_kind=str(edge_label_metadata["edge_label_source_kind"]),
        edge_label_bucket=str(edge_label_metadata["edge_label_bucket"]),
        edge_label_manifest=str(edge_label_metadata["edge_label_manifest"]),
        edge_label_filter=dict(edge_label_metadata["edge_label_filter"]),
        edge_label_bucket_probabilities=dict(edge_label_metadata["edge_label_bucket_probabilities"]),
        topology_profile=str(topology_profile),
        layout_variant=str(layout_variant),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        layout_transform_variant=str(layout_transform_variant),
        edge_routing_variant=str(edge_routing_variant),
        node_color_name=str(node_color_name),
        query_id_probabilities=dict(query_id_probabilities),
        graph_directionality_probabilities=dict(graph_directionality_probabilities),
        node_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_node_support),
                selected=int(node_count) if explicit_node_count is not None else None,
            )
        ),
        target_edge_label_probabilities=dict(
            graph_uniform_label_probability_map(
                edge_label_support,
                selected=str(target_edge_label) if explicit_target_label is not None else None,
            )
        ),
        target_shortest_path_length_probabilities=dict(target_shortest_path_length_probabilities),
        topology_profile_probabilities=dict(topology_probabilities),
        layout_variant_probabilities=dict(layout_probabilities),
        label_variant_probabilities=dict(label_variant_probabilities),
        node_shape_variant_probabilities=dict(node_shape_variant_probabilities),
        layout_transform_variant_probabilities=dict(layout_transform_variant_probabilities),
        edge_routing_variant_probabilities=dict(edge_routing_variant_probabilities),
        node_color_name_probabilities=dict(node_color_name_probabilities),
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
    if str(query.graph_directionality) == "undirected":
        max_edges = int(max_edges // 2)
    edge_density = 0.0 if int(max_edges) <= 0 else float(edge_count) / float(max_edges)
    crossing_norm = normalize_float_with_bounds(float(rendered_scene.crossing_count), (0.0, max(1.0, float(edge_count))))
    target_label_frequency = int(graph_sample.edge_label_counts_by_value[str(query.target_edge_label)])
    repeated_label_norm = 0.0 if int(edge_count) <= 1 else normalize_int_with_bounds(int(target_label_frequency), (1, int(edge_count)))
    directionality_bonus = 1.0 if str(query.graph_directionality) == "directed" else 0.0

    components = {
        "visual_scan": (0.45 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max)))
        + (0.35 * normalize_int_with_bounds(int(edge_count), (max(1, int(node_count) - 1), max(1, int(max_edges)))))
        + (
            0.20
            * normalize_int_with_bounds(
                len(query.edge_label_support),
                (2, max(2, int(_DEFAULTS.edge_label_support_size))),
            )
        ),
        "topology_reasoning": (0.50 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.30 * float(directionality_bonus))
        + (0.20 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.directed_node_count_max))),
        "ambiguity": (0.65 * float(repeated_label_norm)) + (0.35 * float(directionality_bonus)),
        "clutter": (0.50 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.30 * crossing_norm)
        + (0.20 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px))),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


@register_task
class GraphRelationEdgeAttributeLabelTask:
    """Read the visible text label attached to a queried edge."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic labeled-edge lookup instance."""

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
        max_degree_key = "directed_degree_sequence_max_degree" if str(query.graph_directionality) == "directed" else "degree_sequence_max_degree"
        max_degree_fallback = (
            _DEFAULTS.directed_degree_sequence_max_degree if str(query.graph_directionality) == "directed" else _DEFAULTS.degree_sequence_max_degree
        )
        max_degree = int(params.get(max_degree_key, group_default(_GEN_DEFAULTS, max_degree_key, max_degree_fallback)))

        graph_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.graph")
        last_error: Exception | None = None
        graph_sample = None
        rendered_scene = None
        image = None
        background_meta = {}
        post_noise_meta = {}
        for attempt in range(max(1, int(max_attempts))):
            try:
                if str(query.query_id) == PATH_FIRST_EDGE_QUERY_ID:
                    graph_sample = sample_edge_attribute_path_label_graph(
                        graph_rng,
                        graph_directionality=str(query.graph_directionality),
                        node_count=int(query.node_count),
                        target_shortest_path_length=int(query.target_shortest_path_length or 2),
                        target_edge_label=str(query.target_edge_label),
                        edge_label_support=tuple(str(label) for label in query.edge_label_support),
                        topology_profile=str(query.topology_profile),
                        label_variant=str(query.label_variant),
                    )
                else:
                    graph_sample = sample_edge_attribute_label_graph(
                        graph_rng,
                        graph_directionality=str(query.graph_directionality),
                        node_count=int(query.node_count),
                        target_edge_label=str(query.target_edge_label),
                        edge_label_support=tuple(str(label) for label in query.edge_label_support),
                        topology_profile=str(query.topology_profile),
                        label_variant=str(query.label_variant),
                        max_degree=int(max_degree),
                    )
                background, background_meta = make_background_canvas(
                    canvas_width=int(render_params.canvas_width),
                    canvas_height=int(render_params.canvas_height),
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
                )
                directed = str(query.graph_directionality) == "directed"
                rendered_scene = render_graph_scene(
                    graph_sample=graph_sample,
                    layout_variant=str(query.layout_variant),
                    layout_transform_variant=str(query.layout_transform_variant),
                    render_params=render_params,
                    layout_seed=int(instance_seed + attempt),
                    scene_title="Directed Graph" if bool(directed) else "Graph",
                    directed=bool(directed),
                    base_image=background,
                    edge_text_labels_by_label=graph_sample.edge_attribute_labels_by_label,
                    edge_text_label_font_size_px=max(13, int(render_params.label_font_size_px) - 4),
                )
                evidence_projection = projected_edge_label_bbox_evidence(rendered_scene, graph_sample.query_edge)
                if not evidence_projection.get("bbox_set"):
                    raise ValueError("queried edge label bbox was not rendered")
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
            raise RuntimeError("failed to generate graph edge-attribute label instance") from last_error
        if graph_sample is None or rendered_scene is None or image is None:
            raise RuntimeError("failed to generate graph edge-attribute label instance")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_undirected",
                "object_description_directed",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_json_example, prompt_json_example_answer_only = _build_prompt_json_examples()
        prompt_source_raw = str(graph_sample.query_edge[0])
        prompt_target_raw = str(graph_sample.query_edge[1])
        if str(query.query_id) == PATH_FIRST_EDGE_QUERY_ID:
            path_labels = tuple(str(label) for label in graph_sample.query_path_labels)
            if len(path_labels) < 2:
                raise ValueError("path-label query is missing shortest-path endpoints")
            prompt_source_raw = str(path_labels[0])
            prompt_target_raw = str(path_labels[-1])
        source_label = format_graph_prompt_label(
            str(prompt_source_raw),
            label_variant=str(query.label_variant),
        )
        target_label = format_graph_prompt_label(
            str(prompt_target_raw),
            label_variant=str(query.label_variant),
        )
        path_edge_term = "arrow" if str(query.graph_directionality) == "directed" else "edge"
        path_follow_clause = ", using arrow directions" if str(query.graph_directionality) == "directed" else " in the graph"
        object_description_key = "object_description_directed" if str(query.graph_directionality) == "directed" else "object_description_undirected"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[object_description_key]),
                "source_label": str(source_label),
                "target_label": str(target_label),
                "path_edge_term": str(path_edge_term),
                "path_follow_clause": str(path_follow_clause),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_json_example),
                "json_example_answer_only": str(prompt_json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_projection = projected_edge_label_bbox_evidence(rendered_scene, graph_sample.query_edge)
        evidence_bboxes = [[int(round(float(value))) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_gt = TypedValue(type="string", value=str(graph_sample.target_edge_label))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        query_edge = (str(graph_sample.query_edge[0]), str(graph_sample.query_edge[1]))
        edge_label_entries = graph_edge_label_entries(graph_sample.edge_attribute_labels_by_label)
        node_entities = [
            {
                "entity_id": f"node_{node.label}",
                "entity_kind": "graph_node",
                "label": str(node.label),
                "degree": int(node.degree),
                "in_degree": int(graph_sample.in_degrees_by_label[str(node.label)]),
                "out_degree": int(graph_sample.out_degrees_by_label[str(node.label)]),
                "neighbors": list(node.neighbors),
                "successors": list(node.successors),
                "predecessors": list(node.predecessors),
                "is_query_source_node": bool(str(node.label) == str(query_edge[0])),
                "is_query_target_node": bool(str(node.label) == str(query_edge[1])),
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
                "edge_attribute_label": str(graph_sample.edge_attribute_labels_by_label[(str(edge.node_u_label), str(edge.node_v_label))]),
                "edge_label_bbox_xyxy": list(edge.edge_label_bbox_xyxy) if edge.edge_label_bbox_xyxy is not None else None,
                "is_query_edge": bool((str(edge.node_u_label), str(edge.node_v_label)) == tuple(query_edge)),
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

        query_variant_probabilities = dict(query.query_id_probabilities)
        trace_payload = {
            "scene_ir": {
                "scene_kind": "graph_edge_attribute_relation",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "query_variant": "default",
                    "query_id": str(query.query_id),
                    "internal_query_variant": str(query.query_id),
                    "relation_rule": "visible_text_label_on_queried_edge",
                    "graph_directionality": str(query.graph_directionality),
                    "query_variant_probabilities": dict(query_variant_probabilities),
                    "query_edge": list(query_edge),
                    "query_path_labels": list(graph_sample.query_path_labels),
                    "query_path_edge_index": graph_sample.query_path_edge_index,
                    "query_path_edge_position": graph_sample.query_path_edge_position,
                    "target_edge_label": str(graph_sample.target_edge_label),
                    "edge_label_support": list(query.edge_label_support),
                    "edge_label_source_kind": str(query.edge_label_source_kind),
                    "edge_label_bucket": str(query.edge_label_bucket),
                    "edge_label_manifest": str(query.edge_label_manifest),
                    "edge_label_filter": dict(query.edge_label_filter),
                    "edge_label_bucket_probabilities": dict(query.edge_label_bucket_probabilities),
                    "edge_attribute_labels_by_label_pair": list(edge_label_entries),
                    "edge_label_counts_by_value": dict(graph_sample.edge_label_counts_by_value),
                    "graph_directionality_probabilities": dict(query.graph_directionality_probabilities),
                    "target_edge_label_probabilities": dict(query.target_edge_label_probabilities),
                    "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                    "successors_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                    "predecessors_by_label": {str(key): list(values) for key, values in graph_sample.predecessors_by_label.items()},
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
                "query_variant": "default",
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": "default",
                    "query_id": str(query.query_id),
                    "internal_query_variant": str(query.query_id),
                    "query_variant_probabilities": dict(query_variant_probabilities),
                    "graph_directionality": str(query.graph_directionality),
                    "graph_directionality_probabilities": dict(query.graph_directionality_probabilities),
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "query_edge": list(query_edge),
                    "query_path_labels": list(graph_sample.query_path_labels),
                    "query_path_edge_index": graph_sample.query_path_edge_index,
                    "query_path_edge_position": graph_sample.query_path_edge_position,
                    "target_edge_label": str(graph_sample.target_edge_label),
                    "edge_label_support": list(query.edge_label_support),
                    "edge_label_source_kind": str(query.edge_label_source_kind),
                    "edge_label_bucket": str(query.edge_label_bucket),
                    "edge_label_manifest": str(query.edge_label_manifest),
                    "edge_label_filter": dict(query.edge_label_filter),
                    "edge_label_bucket_probabilities": dict(query.edge_label_bucket_probabilities),
                    "target_edge_label_probabilities": dict(query.target_edge_label_probabilities),
                    "target_shortest_path_length": query.target_shortest_path_length,
                    "target_shortest_path_length_probabilities": dict(query.target_shortest_path_length_probabilities),
                    "node_count_probabilities": dict(query.node_count_probabilities),
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
                    "query_variant_probabilities": {"default": 1.0},
                    max_degree_key: int(max_degree),
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
                    "semantic_edge_text_labels_by_label_pair": list(edge_label_entries),
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
                "query_variant": "default",
                "query_id": str(query.query_id),
                "internal_query_variant": str(query.query_id),
                "query_variant_probabilities": dict(query_variant_probabilities),
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": str(query.query_id),
                "graph_directionality": str(query.graph_directionality),
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "query_edge": list(query_edge),
                "query_path_labels": list(graph_sample.query_path_labels),
                "query_path_edge_index": graph_sample.query_path_edge_index,
                "query_path_edge_position": graph_sample.query_path_edge_position,
                "source_label": str(prompt_source_raw),
                "target_label": str(prompt_target_raw),
                "query_edge_source_label": str(query_edge[0]),
                "query_edge_target_label": str(query_edge[1]),
                "prompt_source_label": str(source_label),
                "prompt_target_label": str(target_label),
                "answer": str(graph_sample.target_edge_label),
                "target_edge_label": str(graph_sample.target_edge_label),
                "edge_label_support": list(query.edge_label_support),
                "edge_label_source_kind": str(query.edge_label_source_kind),
                "edge_label_bucket": str(query.edge_label_bucket),
                "edge_label_manifest": str(query.edge_label_manifest),
                "edge_label_filter": dict(query.edge_label_filter),
                "edge_label_bucket_probabilities": dict(query.edge_label_bucket_probabilities),
                "target_edge_label_probabilities": dict(query.target_edge_label_probabilities),
                "target_shortest_path_length": query.target_shortest_path_length,
                "target_shortest_path_length_probabilities": dict(query.target_shortest_path_length_probabilities),
                "edge_attribute_labels_by_label_pair": list(edge_label_entries),
                "edge_label_counts_by_value": dict(graph_sample.edge_label_counts_by_value),
                "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                "in_degrees_by_label": {str(key): int(value) for key, value in graph_sample.in_degrees_by_label.items()},
                "out_degrees_by_label": {str(key): int(value) for key, value in graph_sample.out_degrees_by_label.items()},
                "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                "successors_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                "predecessors_by_label": {str(key): list(values) for key, values in graph_sample.predecessors_by_label.items()},
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
                "type": "edge_attribute_label",
                "edge": list(query_edge),
                "edge_label": str(graph_sample.target_edge_label),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_bboxes),
                "pixel_bbox_set": list(evidence_bboxes),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphRelationEdgeAttributeLabelTask"]
