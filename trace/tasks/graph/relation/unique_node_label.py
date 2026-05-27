"""Identify the unique neighbor, successor, or predecessor of one graph node."""

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
    SUPPORTED_LAYOUT_VARIANTS,
    SUPPORTED_NODE_LINK_LABEL_VARIANTS,
    SUPPORTED_TOPOLOGY_PROFILES,
    SUPPORTED_UNIQUE_NODE_LABEL_RELATION_MODES,
    sample_unique_node_label_relation_graph,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    SUPPORTED_EDGE_ROUTING_VARIANTS,
    SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    SUPPORTED_NODE_SHAPE_VARIANTS,
    projected_node_point_evidence,
    render_graph_scene,
)
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import (
    format_graph_prompt_label,
    resolve_forced_graph_query_id,
    resolve_graph_balanced_node_color_name,
    resolve_graph_named_variant,
    resolve_graph_render_params,
)
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__node_link__unique_node_label"
SCENE_ID = "node_link"

SUPPORTED_UNIQUE_NODE_LABEL_QUERY_IDS = (
    "unique_neighbor_label",
    "unique_successor_label",
    "unique_predecessor_label",
)
RELATION_MODE_BY_QUERY_ID = {
    "unique_neighbor_label": "undirected_unique_neighbor",
    "unique_successor_label": "directed_unique_successor",
    "unique_predecessor_label": "directed_unique_predecessor",
}
GRAPH_DIRECTIONALITY_BY_QUERY_ID = {
    "unique_neighbor_label": "undirected",
    "unique_successor_label": "directed",
    "unique_predecessor_label": "directed",
}
RELATION_RULE_BY_QUERY_ID = {
    "unique_neighbor_label": "only_adjacent_node",
    "unique_successor_label": "only_outgoing_arrow_target",
    "unique_predecessor_label": "only_incoming_arrow_source",
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for unique node-label relation scenes."""

    node_count_min: int = 5
    node_count_max: int = 10
    directed_node_count_max: int = 10
    unique_neighbor_node_count_min: int = 7
    unique_neighbor_node_count_max: int = 11
    unique_directed_node_count_min: int = 4
    unique_directed_node_count_max: int = 8
    degree_sequence_max_degree: int = 5
    directed_degree_sequence_max_degree: int = 5
    unique_neighbor_degree_sequence_max_degree: int = 6
    unique_directed_degree_sequence_max_degree: int = 3
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
    """Resolved support and style axes for one unique node-label query."""

    query_id: str
    relation_mode: str
    graph_directionality: str
    node_count: int
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    query_id_probabilities: Dict[str, float]
    relation_mode_probabilities: Dict[str, float]
    graph_directionality_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
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
    """Return prompt examples that match the node-bbox evidence format."""

    example_evidence = [[280, 164, 326, 210]]
    return (
        json.dumps({"evidence": example_evidence, "answer": "B"}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps({"answer": "B"}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _query_id_from_alias(value: Any) -> str | None:
    """Return the public query id encoded by one query/task alias."""

    text = str(value or "").strip()
    aliases = {
        "unique_neighbor": "unique_neighbor_label",
        "unique_neighbor_label": "unique_neighbor_label",
        "undirected_unique_neighbor": "unique_neighbor_label",
        "undirected_unique_neighbor_label": "unique_neighbor_label",
        "unique_successor": "unique_successor_label",
        "unique_successor_label": "unique_successor_label",
        "directed_unique_successor": "unique_successor_label",
        "directed_unique_successor_label": "unique_successor_label",
        "unique_predecessor": "unique_predecessor_label",
        "unique_predecessor_label": "unique_predecessor_label",
        "directed_unique_predecessor": "unique_predecessor_label",
        "directed_unique_predecessor_label": "unique_predecessor_label",
        "unique_node_label": None,
        "default": None,
    }
    return aliases.get(text)



def _node_count_selection_index(
    instance_seed: int,
    *,
    selection_index: int,
    query_id: str,
    topology_profile: str,
) -> int:
    """Return an independent node-count index for the resolved unique-node query."""

    namespace = f"{TASK_ID}:node_count:{str(query_id)}:{str(topology_profile)}"
    return int(hash64(int(instance_seed), namespace, int(selection_index)))



def _resolve_layout_fallback_variants(
    *,
    query_id: str,
    params: Mapping[str, Any],
) -> Tuple[str, ...] | None:
    """Resolve optional branch-specific layout fallbacks."""

    key = "unique_neighbor_layout_fallback_variants" if str(query_id) == "unique_neighbor_label" else "unique_directed_layout_fallback_variants"
    raw_value = params.get(str(key), group_default(_RENDER_DEFAULTS, str(key), None))
    if raw_value is None:
        return None
    if isinstance(raw_value, str):
        candidates: Sequence[Any] = tuple(part.strip() for part in raw_value.split(","))
    elif isinstance(raw_value, Sequence):
        candidates = tuple(raw_value)
    else:
        return None
    supported = set(SUPPORTED_LAYOUT_VARIANTS)
    cleaned = tuple(str(value) for value in candidates if str(value) in supported)
    return cleaned or None


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one unique node-label relation query."""

    forced_query_id = resolve_forced_graph_query_id(params, query_id_from_alias=_query_id_from_alias)
    if forced_query_id is None:
        query_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_variant")
        query_id, query_id_probabilities = resolve_graph_named_variant(
            query_rng,
            params=params,
            gen_defaults=_GEN_DEFAULTS,
            explicit_key="query_id",
            weights_key="query_variant_weights",
            balance_flag_key="balanced_query_variant_sampling",
            supported=SUPPORTED_UNIQUE_NODE_LABEL_QUERY_IDS,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            namespace="query_variant",
        )
    else:
        query_id = str(forced_query_id)
        query_id_probabilities = {
            str(supported_query_id): (1.0 if str(supported_query_id) == str(query_id) else 0.0)
            for supported_query_id in SUPPORTED_UNIQUE_NODE_LABEL_QUERY_IDS
        }
    relation_mode = str(RELATION_MODE_BY_QUERY_ID[str(query_id)])
    graph_directionality = str(GRAPH_DIRECTIONALITY_BY_QUERY_ID[str(query_id)])

    topology_weights_key = "topology_profile_weights"
    topology_balance_flag_key = "balanced_topology_profile_sampling"
    topology_namespace = "topology_profile"
    if "topology_profile" not in params and "topology_profile_weights" not in params:
        if str(query_id) == "unique_neighbor_label" and group_default(_GEN_DEFAULTS, "unique_neighbor_topology_profile_weights", None) is not None:
            topology_weights_key = "unique_neighbor_topology_profile_weights"
            topology_balance_flag_key = "balanced_unique_neighbor_topology_profile_sampling"
            topology_namespace = "unique_neighbor_topology_profile"
        elif str(query_id) != "unique_neighbor_label" and group_default(_GEN_DEFAULTS, "unique_directed_topology_profile_weights", None) is not None:
            topology_weights_key = "unique_directed_topology_profile_weights"
            topology_balance_flag_key = "balanced_unique_directed_topology_profile_sampling"
            topology_namespace = "unique_directed_topology_profile"
    topology_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{topology_namespace}")
    topology_profile, topology_probabilities = resolve_graph_named_variant(
        topology_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="topology_profile",
        weights_key=str(topology_weights_key),
        balance_flag_key=str(topology_balance_flag_key),
        supported=SUPPORTED_TOPOLOGY_PROFILES,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace=str(topology_namespace),
    )

    if str(query_id) == "unique_neighbor_label":
        node_count_min_key = "unique_neighbor_node_count_min"
        node_count_max_key = "unique_neighbor_node_count_max"
        node_count_min_fallback = _DEFAULTS.unique_neighbor_node_count_min
        node_count_max_fallback = _DEFAULTS.unique_neighbor_node_count_max
    else:
        node_count_min_key = "unique_directed_node_count_min"
        node_count_max_key = "unique_directed_node_count_max"
        node_count_min_fallback = _DEFAULTS.unique_directed_node_count_min
        node_count_max_fallback = _DEFAULTS.unique_directed_node_count_max
    node_count_min = int(params.get(node_count_min_key, group_default(_GEN_DEFAULTS, node_count_min_key, node_count_min_fallback)))
    node_count_max = int(params.get(node_count_max_key, group_default(_GEN_DEFAULTS, node_count_max_key, node_count_max_fallback)))
    feasible_node_support = tuple(int(value) for value in range(max(3, int(node_count_min)), int(node_count_max) + 1))
    if not feasible_node_support:
        raise ValueError("no feasible node_count support exists for unique-node label relation")
    explicit_node_count = params.get("node_count")
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
        if int(node_count) not in set(feasible_node_support):
            raise ValueError("node_count is outside feasible support for unique-node label relation")
    else:
        selection_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}:node_count",
            )
        )
        if forced_query_id is None:
            selection_index = int(selection_index // max(1, len(SUPPORTED_UNIQUE_NODE_LABEL_QUERY_IDS)))
        node_index = _node_count_selection_index(
            int(instance_seed),
            selection_index=int(selection_index),
            query_id=str(query_id),
            topology_profile=str(topology_profile),
        )
        node_count = int(feasible_node_support[int(node_index % len(feasible_node_support))])

    layout_weights_key = "layout_variant_weights"
    layout_balance_flag_key = "balanced_layout_variant_sampling"
    layout_namespace = "layout_variant"
    if "layout_variant" not in params and "layout_variant_weights" not in params:
        if str(query_id) == "unique_neighbor_label" and group_default(_GEN_DEFAULTS, "unique_neighbor_layout_variant_weights", None) is not None:
            layout_weights_key = "unique_neighbor_layout_variant_weights"
            layout_balance_flag_key = "balanced_unique_neighbor_layout_variant_sampling"
            layout_namespace = "unique_neighbor_layout_variant"
        elif str(query_id) != "unique_neighbor_label" and group_default(_GEN_DEFAULTS, "unique_directed_layout_variant_weights", None) is not None:
            layout_weights_key = "unique_directed_layout_variant_weights"
            layout_balance_flag_key = "balanced_unique_directed_layout_variant_sampling"
            layout_namespace = "unique_directed_layout_variant"
    layout_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{layout_namespace}")
    layout_variant, layout_probabilities = resolve_graph_named_variant(
        layout_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="layout_variant",
        weights_key=str(layout_weights_key),
        balance_flag_key=str(layout_balance_flag_key),
        supported=SUPPORTED_LAYOUT_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace=str(layout_namespace),
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
        query_id=str(query_id),
        relation_mode=str(relation_mode),
        graph_directionality=str(graph_directionality),
        node_count=int(node_count),
        topology_profile=str(topology_profile),
        layout_variant=str(layout_variant),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        layout_transform_variant=str(layout_transform_variant),
        edge_routing_variant=str(edge_routing_variant),
        node_color_name=str(node_color_name),
        query_id_probabilities=dict(query_id_probabilities),
        relation_mode_probabilities={str(mode): (1.0 if str(mode) == str(relation_mode) else 0.0) for mode in SUPPORTED_UNIQUE_NODE_LABEL_RELATION_MODES},
        graph_directionality_probabilities={
            "undirected": 1.0 if str(graph_directionality) == "undirected" else 0.0,
            "directed": 1.0 if str(graph_directionality) == "directed" else 0.0,
        },
        node_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_node_support),
                selected=int(node_count) if explicit_node_count is not None else None,
            )
        ),
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
    relation_bonus = 1.0 if str(query.graph_directionality) == "directed" else 0.0

    components = {
        "visual_scan": (0.60 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max)))
        + (0.40 * normalize_int_with_bounds(int(edge_count), (max(1, int(node_count) - 1), max(1, int(max_edges))))),
        "topology_reasoning": (0.55 * float(relation_bonus))
        + (0.45 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0))),
        "ambiguity": 0.25 + (0.35 * float(relation_bonus)) + (0.40 * normalize_int_with_bounds(int(node_count), (3, _DEFAULTS.directed_node_count_max))),
        "clutter": (0.55 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.30 * crossing_norm)
        + (0.15 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px))),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


@register_task
class GraphRelationUniqueNodeLabelTask:
    """Identify the unique adjacent/reachable-by-one-edge node label."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic unique node-label relation instance."""

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
        layout_fallback_variants = _resolve_layout_fallback_variants(query_id=str(query.query_id), params=params)
        if str(query.query_id) == "unique_neighbor_label":
            max_degree_key = "unique_neighbor_degree_sequence_max_degree"
            max_degree_fallback = _DEFAULTS.unique_neighbor_degree_sequence_max_degree
        else:
            max_degree_key = "unique_directed_degree_sequence_max_degree"
            max_degree_fallback = _DEFAULTS.unique_directed_degree_sequence_max_degree
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
                graph_sample = sample_unique_node_label_relation_graph(
                    graph_rng,
                    relation_mode=str(query.relation_mode),
                    node_count=int(query.node_count),
                    max_degree=int(max_degree),
                    topology_profile=str(query.topology_profile),
                    label_variant=str(query.label_variant),
                )
                background, background_meta = make_background_canvas(
                    canvas_width=int(render_params.canvas_width),
                    canvas_height=int(render_params.canvas_height),
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
                )
                directed = str(query.graph_directionality) == "directed"
                query_node_style = {
                    str(graph_sample.query_label): {
                        "halo_rgb": tuple(int(value) for value in render_params.title_color_rgb),
                        "halo_pad_px": 6,
                        "halo_width_px": 3,
                    }
                }
                supporting_edge_style = {
                    (str(graph_sample.supporting_edge[0]), str(graph_sample.supporting_edge[1])): {
                        "edge_color_rgb": tuple(int(value) for value in render_params.title_color_rgb),
                        "edge_width_px": max(int(render_params.edge_width_px) + 2, 5),
                    }
                }
                rendered_scene = render_graph_scene(
                    graph_sample=graph_sample,
                    layout_variant=str(query.layout_variant),
                    layout_transform_variant=str(query.layout_transform_variant),
                    render_params=render_params,
                    layout_seed=int(instance_seed + attempt),
                    scene_title="Directed Graph" if bool(directed) else "Graph",
                    directed=bool(directed),
                    base_image=background,
                    node_style_by_label=query_node_style,
                    edge_style_by_label=supporting_edge_style,
                    layout_fallback_variants=layout_fallback_variants,
                )
                evidence_projection = projected_node_point_evidence(rendered_scene, (str(graph_sample.answer_label),))
                if not evidence_projection.get("pixel_bbox_set"):
                    raise ValueError("answer node bbox was not rendered")
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
            raise RuntimeError("failed to generate graph unique-node-label relation instance") from last_error
        if graph_sample is None or rendered_scene is None or image is None:
            raise RuntimeError("failed to generate graph unique-node-label relation instance")

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
        prompt_query_label = format_graph_prompt_label(
            str(graph_sample.query_label),
            label_variant=str(query.label_variant),
        )
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
                "query_label": str(prompt_query_label),
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

        evidence_projection = projected_node_point_evidence(rendered_scene, (str(graph_sample.answer_label),))
        evidence_bboxes = [[int(round(float(value))) for value in bbox] for bbox in evidence_projection["pixel_bbox_set"]]
        answer_gt = TypedValue(type="string", value=str(graph_sample.answer_label))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        supporting_edge = (str(graph_sample.supporting_edge[0]), str(graph_sample.supporting_edge[1]))
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
                "is_query_node": bool(str(node.label) == str(graph_sample.query_label)),
                "is_answer_node": bool(str(node.label) == str(graph_sample.answer_label)),
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
                "is_supporting_edge": bool((str(edge.node_u_label), str(edge.node_v_label)) == tuple(supporting_edge)),
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
                "scene_kind": "graph_unique_node_label_relation",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "query_variant": "default",
                    "query_id": str(query.query_id),
                    "internal_query_variant": str(query.query_id),
                    "relation_rule": str(RELATION_RULE_BY_QUERY_ID[str(query.query_id)]),
                    "relation_mode": str(graph_sample.relation_mode),
                    "graph_directionality": str(query.graph_directionality),
                    "query_label": str(graph_sample.query_label),
                    "answer_label": str(graph_sample.answer_label),
                    "target_labels": list(graph_sample.target_labels),
                    "supporting_edge": list(supporting_edge),
                    "query_variant_probabilities": dict(query.query_id_probabilities),
                    "relation_mode_probabilities": dict(query.relation_mode_probabilities),
                    "graph_directionality_probabilities": dict(query.graph_directionality_probabilities),
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
                    "query_variant_probabilities": dict(query.query_id_probabilities),
                    "relation_mode": str(query.relation_mode),
                    "relation_mode_probabilities": dict(query.relation_mode_probabilities),
                    "graph_directionality": str(query.graph_directionality),
                    "graph_directionality_probabilities": dict(query.graph_directionality_probabilities),
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "query_label": str(graph_sample.query_label),
                    "prompt_query_label": str(prompt_query_label),
                    "answer_label": str(graph_sample.answer_label),
                    "target_labels": list(graph_sample.target_labels),
                    "supporting_edge": list(supporting_edge),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "topology_profile": str(query.topology_profile),
                    "topology_profile_probabilities": dict(query.topology_profile_probabilities),
                    "layout_variant": str(query.layout_variant),
                    "layout_variant_probabilities": dict(query.layout_variant_probabilities),
                    "label_variant": str(query.label_variant),
                    "label_source_kind": str(graph_sample.label_source_kind),
                    "label_bucket": str(graph_sample.label_bucket),
                    "label_manifest": str(graph_sample.label_manifest),
                    "label_filter": dict(graph_sample.label_filter),
                    "label_bucket_probabilities": dict(graph_sample.label_bucket_probabilities),
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
                "query_variant_probabilities": dict(query.query_id_probabilities),
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": str(query.query_id),
                "relation_mode": str(graph_sample.relation_mode),
                "relation_rule": str(RELATION_RULE_BY_QUERY_ID[str(query.query_id)]),
                "graph_directionality": str(query.graph_directionality),
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "query_label": str(graph_sample.query_label),
                "prompt_query_label": str(prompt_query_label),
                "answer": str(graph_sample.answer_label),
                "answer_label": str(graph_sample.answer_label),
                "target_labels": list(graph_sample.target_labels),
                "supporting_edge": list(supporting_edge),
                "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                "in_degrees_by_label": {str(key): int(value) for key, value in graph_sample.in_degrees_by_label.items()},
                "out_degrees_by_label": {str(key): int(value) for key, value in graph_sample.out_degrees_by_label.items()},
                "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                "successors_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                "predecessors_by_label": {str(key): list(values) for key, values in graph_sample.predecessors_by_label.items()},
                "topology_profile": str(graph_sample.topology_profile),
                "topology_profile_probabilities": dict(query.topology_profile_probabilities),
                "label_variant": str(graph_sample.label_variant),
                "label_source_kind": str(graph_sample.label_source_kind),
                "label_bucket": str(graph_sample.label_bucket),
                "label_manifest": str(graph_sample.label_manifest),
                "label_filter": dict(graph_sample.label_filter),
                "label_bucket_probabilities": dict(graph_sample.label_bucket_probabilities),
                "node_shape_variant": str(render_params.node_shape_variant),
                "layout_variant_requested": str(query.layout_variant),
                "layout_variant_used": str(rendered_scene.layout_variant),
                "layout_transform_variant": str(rendered_scene.layout_transform_variant),
                "edge_routing_variant": str(rendered_scene.edge_routing_variant),
                "node_color_name": str(query.node_color_name),
                "crossing_count": int(rendered_scene.crossing_count),
            },
            "witness_symbolic": {
                "type": "unique_node_label_relation",
                "query_label": str(graph_sample.query_label),
                "answer_label": str(graph_sample.answer_label),
                "supporting_edge": list(supporting_edge),
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


__all__ = ["GraphRelationUniqueNodeLabelTask"]
