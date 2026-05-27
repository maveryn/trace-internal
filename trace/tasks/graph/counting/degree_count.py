"""Count labeled graph nodes with a specified degree."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

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
from ...shared.variant_sampling import has_non_null_param, is_uniform_probability_map
from ..shared.complexity import (
    build_graph_complexity,
    normalize_float_with_bounds,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.graph_sampling import (
    SUPPORTED_DEGREE_QUERY_VARIANTS,
    SUPPORTED_DIRECTED_DEGREE_MODES,
    SUPPORTED_NODE_LINK_LABEL_VARIANTS,
    SUPPORTED_LAYOUT_VARIANTS,
    SUPPORTED_TOPOLOGY_PROFILES,
    feasible_node_counts_for_degree_count,
    graph_degree_mode_for_query_variant,
    graph_directionality_for_query_variant,
    graph_label_sort_key,
    sample_degree_count_graph,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    SUPPORTED_EDGE_ROUTING_VARIANTS,
    SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    SUPPORTED_NODE_SHAPE_VARIANTS,
    projected_node_point_evidence,
    render_graph_scene,
)
from ..shared.fixed_query_task import (
    decoupled_merged_branch_params,
    rewrite_graph_public_task_output,
    rewrite_graph_query_output,
    select_merged_graph_query_id,
)
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES, build_graph_named_color_theme
from ..shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__node_link__degree_predicate_count"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for graph degree-count scenes."""

    node_count_min: int = 5
    node_count_max: int = 10
    directed_node_count_max: int = 10
    query_degree_min: int = 0
    query_degree_max: int = 4
    target_count_min: int = 0
    target_count_max: int = 5
    degree_sequence_max_degree: int = 5
    directed_degree_sequence_max_degree: int = 4
    graph_search_attempts: int = 600
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
    label_variant: str = "letters"
    layout_transform_variant: str = "identity"
    node_color_name: str = "blue"
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
    """Resolved graph-query support for one degree-count instance."""

    query_variant: str
    graph_directionality: str
    degree_mode: str
    node_count: int
    query_degree: int
    target_count: int
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    query_variant_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    query_degree_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    topology_profile_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    edge_routing_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]
    degree_mode_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="counting")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="counting", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _build_prompt_json_examples(*, label_variant: str) -> Tuple[str, str]:
    """Return prompt examples that match the pixel-space evidence format."""

    example_evidence = [[180, 220], [310, 180]]
    return (
        json.dumps({"evidence": example_evidence, "answer": 2}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps({"answer": 2}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _query_support_selection_index(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    query_variant_probabilities: Mapping[str, float],
    degree_mode_probabilities: Mapping[str, float],
) -> int:
    """Return a query-support index decorrelated from balanced query variants."""

    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:query_support",
        )
    )
    balanced_query_variants = bool(
        params.get(
            "balanced_query_variant_sampling",
            group_default(_GEN_DEFAULTS, "balanced_query_variant_sampling", True),
        )
    )
    query_variant_overridden = any(
        has_non_null_param(params, key)
        for key in ("query_variant", "query_variant_weights")
    )
    divisor = 1
    if (
        bool(balanced_query_variants)
        and not bool(query_variant_overridden)
        and is_uniform_probability_map(query_variant_probabilities)
    ):
        active_variant_count = sum(
            1 for value in query_variant_probabilities.values() if float(value) > 0.0
        )
        if int(active_variant_count) > 1:
            divisor *= int(active_variant_count)

    balanced_degree_modes = bool(
        params.get(
            "balanced_degree_mode_sampling",
            group_default(_GEN_DEFAULTS, "balanced_degree_mode_sampling", True),
        )
    )
    degree_mode_overridden = any(
        has_non_null_param(params, key)
        for key in ("degree_mode", "degree_mode_weights")
    )
    if (
        bool(balanced_degree_modes)
        and not bool(degree_mode_overridden)
        and is_uniform_probability_map(degree_mode_probabilities)
    ):
        active_mode_count = sum(
            1 for value in degree_mode_probabilities.values() if float(value) > 0.0
        )
        if int(active_mode_count) > 1:
            divisor *= int(active_mode_count)
    if int(divisor) > 1:
        return int(selection_index // int(divisor))
    return int(selection_index)


def _degree_mode_params_for_sampling(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_variant_probabilities: Mapping[str, float],
) -> Mapping[str, Any]:
    """Return params with degree-mode cycling decoupled from query-variant cycling."""

    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:degree_mode",
        )
    )
    balanced_query_variants = bool(
        params.get(
            "balanced_query_variant_sampling",
            group_default(_GEN_DEFAULTS, "balanced_query_variant_sampling", True),
        )
    )
    query_variant_overridden = any(
        has_non_null_param(params, key)
        for key in ("query_variant", "query_variant_weights")
    )
    _ = selection_index, balanced_query_variants, query_variant_overridden, query_variant_probabilities
    return params


def _node_count_selection_index(
    instance_seed: int,
    *,
    query_selection_index: int,
    query_variant: str,
    query_degree: int,
    target_count: int,
    topology_profile: str,
) -> int:
    """Return an independent index for node-count support selection."""

    namespace = (
        f"{TASK_ID}:node_count:"
        f"{str(query_variant)}:{int(query_degree)}:{int(target_count)}:{str(topology_profile)}"
    )
    return int(hash64(int(instance_seed), namespace, int(query_selection_index)))


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve balanced node-count / degree-query support for one instance."""

    variant_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.query_variant")
    query_variant, query_variant_probabilities = resolve_graph_named_variant(
        variant_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        supported=SUPPORTED_DEGREE_QUERY_VARIANTS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="query_variant",
    )
    graph_directionality = str(graph_directionality_for_query_variant(str(query_variant)))
    if str(graph_directionality) == "directed":
        degree_mode_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.degree_mode")
        degree_mode_params = _degree_mode_params_for_sampling(
            instance_seed=int(instance_seed),
            params=params,
            query_variant_probabilities=query_variant_probabilities,
        )
        degree_mode, degree_mode_probabilities = resolve_graph_named_variant(
            degree_mode_rng,
            params=degree_mode_params,
            gen_defaults=_GEN_DEFAULTS,
            explicit_key="degree_mode",
            weights_key="degree_mode_weights",
            balance_flag_key="balanced_degree_mode_sampling",
            supported=SUPPORTED_DIRECTED_DEGREE_MODES,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            namespace="degree_mode",
        )
    else:
        degree_mode = str(graph_degree_mode_for_query_variant(str(query_variant)))
        explicit_degree_mode = params.get("degree_mode")
        if explicit_degree_mode is not None and str(explicit_degree_mode) != str(degree_mode):
            raise ValueError("degree_mode can only be set to degree for the undirected degree-count variant")
        degree_mode_probabilities = {"degree": 1.0}
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

    node_count_min = int(params.get("node_count_min", group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)))
    node_count_max_key = "directed_node_count_max" if str(graph_directionality) == "directed" else "node_count_max"
    node_count_max_fallback = _DEFAULTS.directed_node_count_max if str(graph_directionality) == "directed" else _DEFAULTS.node_count_max
    node_count_max = int(params.get(node_count_max_key, group_default(_GEN_DEFAULTS, node_count_max_key, node_count_max_fallback)))
    query_degree_min = int(
        params.get("query_degree_min", group_default(_GEN_DEFAULTS, "query_degree_min", _DEFAULTS.query_degree_min))
    )
    query_degree_max = int(
        params.get("query_degree_max", group_default(_GEN_DEFAULTS, "query_degree_max", _DEFAULTS.query_degree_max))
    )
    target_count_min = int(
        params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min))
    )
    target_count_max = int(
        params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max))
    )
    max_degree_key = "directed_degree_sequence_max_degree" if str(graph_directionality) == "directed" else "degree_sequence_max_degree"
    max_degree_fallback = (
        _DEFAULTS.directed_degree_sequence_max_degree if str(graph_directionality) == "directed" else _DEFAULTS.degree_sequence_max_degree
    )
    max_degree = int(params.get(max_degree_key, group_default(_GEN_DEFAULTS, max_degree_key, max_degree_fallback)))

    target_support = tuple(range(int(target_count_min), int(target_count_max) + 1))
    degree_support = tuple(range(int(query_degree_min), int(query_degree_max) + 1))
    if not target_support:
        raise ValueError("target_count support is empty for graph degree counting")
    if not degree_support:
        raise ValueError("query_degree support is empty for graph degree counting")

    selection_index = _query_support_selection_index(
        int(instance_seed),
        params=params,
        query_variant_probabilities=query_variant_probabilities,
        degree_mode_probabilities=degree_mode_probabilities,
    )

    feasible_pairs = []
    feasible_node_support_by_pair: Dict[Tuple[int, int], Tuple[int, ...]] = {}
    for supported_degree in degree_support:
        for supported_target in target_support:
            feasible_nodes = feasible_node_counts_for_degree_count(
                query_variant=str(query_variant),
                degree_mode=str(degree_mode),
                query_degree=int(supported_degree),
                target_count=int(supported_target),
                node_count_min=int(node_count_min),
                node_count_max=int(node_count_max),
                max_degree=int(max_degree),
                topology_profile=str(topology_profile),
            )
            if feasible_nodes:
                pair = (int(supported_degree), int(supported_target))
                feasible_pairs.append(pair)
                feasible_node_support_by_pair[pair] = tuple(int(value) for value in feasible_nodes)
    if not feasible_pairs:
        raise ValueError("no feasible graph degree-count support exists for the configured query variant")

    explicit_target = params.get("target_count")
    explicit_query_degree = params.get("query_degree")
    if explicit_target is not None:
        target_count = int(explicit_target)
        if target_count not in target_support:
            raise ValueError("target_count is outside configured support")
    else:
        target_count = None
    if explicit_query_degree is not None:
        query_degree = int(explicit_query_degree)
        if query_degree not in degree_support:
            raise ValueError("query_degree is outside configured support")
    else:
        query_degree = None

    filtered_pairs = [
        pair
        for pair in feasible_pairs
        if (query_degree is None or int(pair[0]) == int(query_degree))
        and (target_count is None or int(pair[1]) == int(target_count))
    ]
    if not filtered_pairs:
        raise ValueError("no feasible node counts exist for the configured graph degree-count support")

    if query_degree is None and target_count is None:
        query_degree, target_count = filtered_pairs[int(selection_index % len(filtered_pairs))]
    elif query_degree is None:
        degree_candidates = tuple(sorted({int(pair[0]) for pair in filtered_pairs}))
        query_degree = int(degree_candidates[int(selection_index % len(degree_candidates))])
    elif target_count is None:
        target_candidates = tuple(sorted({int(pair[1]) for pair in filtered_pairs}))
        target_count = int(target_candidates[int(selection_index % len(target_candidates))])

    feasible_node_support = feasible_node_support_by_pair[(int(query_degree), int(target_count))]
    explicit_node_count = params.get("node_count")
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
    else:
        node_index = _node_count_selection_index(
            int(instance_seed),
            query_selection_index=int(selection_index),
            query_variant=str(query_variant),
            query_degree=int(query_degree),
            target_count=int(target_count),
            topology_profile=str(topology_profile),
        )
        node_count = int(feasible_node_support[int(node_index % len(feasible_node_support))])
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested graph degree-count query")

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
    color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.node_color_name")
    node_color_name, node_color_name_probabilities = resolve_graph_named_variant(
        color_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="node_color_name",
        weights_key="node_color_name_weights",
        balance_flag_key="balanced_node_color_name_sampling",
        supported=SUPPORTED_NODE_COLOR_NAMES,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="node_color_name",
    )

    return _ResolvedQuery(
        query_variant=str(query_variant),
        graph_directionality=str(graph_directionality),
        degree_mode=str(degree_mode),
        node_count=int(node_count),
        query_degree=int(query_degree),
        target_count=int(target_count),
        topology_profile=str(topology_profile),
        layout_variant=str(layout_variant),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        layout_transform_variant=str(layout_transform_variant),
        edge_routing_variant=str(edge_routing_variant),
        node_color_name=str(node_color_name),
        query_variant_probabilities=dict(query_variant_probabilities),
        node_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_node_support),
                selected=int(node_count) if explicit_node_count is not None else None,
            )
        ),
        query_degree_probabilities=dict(
            uniform_probability_map(
                tuple(sorted({int(pair[0]) for pair in filtered_pairs})),
                selected=int(query_degree) if explicit_query_degree is not None else None,
            )
        ),
        target_count_probabilities=dict(
            uniform_probability_map(
                tuple(sorted({int(pair[1]) for pair in filtered_pairs})),
                selected=int(target_count) if explicit_target is not None else None,
            )
        ),
        topology_profile_probabilities=dict(topology_probabilities),
        layout_variant_probabilities=dict(layout_probabilities),
        label_variant_probabilities=dict(label_variant_probabilities),
        node_shape_variant_probabilities=dict(node_shape_variant_probabilities),
        layout_transform_variant_probabilities=dict(layout_transform_variant_probabilities),
        edge_routing_variant_probabilities=dict(edge_routing_variant_probabilities),
        node_color_name_probabilities=dict(node_color_name_probabilities),
        degree_mode_probabilities=dict(degree_mode_probabilities),
    )


def _build_complexity(
    *,
    graph_sample,
    query: _ResolvedQuery,
    render_params: GraphRenderParams,
    rendered_scene,
) -> Any:
    """Build one within-task normalized complexity record."""

    node_count = int(query.node_count)
    edge_count = int(graph_sample.edge_count)
    max_edges = int(node_count * (node_count - 1))
    if str(query.graph_directionality) == "undirected":
        max_edges = int(max_edges // 2)
    degree_support = (group_default(_GEN_DEFAULTS, "query_degree_min", _DEFAULTS.query_degree_min), group_default(_GEN_DEFAULTS, "query_degree_max", _DEFAULTS.query_degree_max))
    degree_values = list(int(value) for value in graph_sample.degrees_by_label.values())
    near_miss_count = sum(1 for degree in degree_values if abs(int(degree) - int(query.query_degree)) == 1)
    edge_density = 0.0 if int(max_edges) <= 0 else float(edge_count) / float(max_edges)
    crossing_norm = normalize_float_with_bounds(float(rendered_scene.crossing_count), (0.0, max(1.0, float(max_edges))))
    directionality_bonus = 1.0 if str(query.graph_directionality) == "directed" else 0.0

    components = {
        "visual_scan": (0.6 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.directed_node_count_max if str(query.graph_directionality) == "directed" else _DEFAULTS.node_count_max)))
        + (0.3 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.1 * float(directionality_bonus)),
        "topology_reasoning": (0.7 * normalize_int_with_bounds(int(query.query_degree), degree_support))
        + (0.2 * normalize_int_with_bounds(len(set(degree_values)), (1, min(node_count, _DEFAULTS.degree_sequence_max_degree + 1))))
        + (0.1 * float(directionality_bonus)),
        "ambiguity": (0.6 * normalize_int_with_bounds(int(near_miss_count), (0, int(node_count))))
        + (0.4 * normalize_int_with_bounds(int(query.target_count), (_DEFAULTS.target_count_min, _DEFAULTS.target_count_max))),
        "clutter": (0.55 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.25 * crossing_norm)
        + (0.10 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px)))
        + (0.10 * float(directionality_bonus)),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


class _GraphCountingDegreeCountBaseTask:
    """Count graph nodes that have one specified degree."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic graph degree-count instance."""

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
        search_attempts = int(params.get("graph_search_attempts", group_default(_GEN_DEFAULTS, "graph_search_attempts", _DEFAULTS.graph_search_attempts)))

        graph_rng = spawn_rng(int(instance_seed), "graph_structure")
        last_error: Exception | None = None
        graph_sample = None
        rendered_scene = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                graph_sample = sample_degree_count_graph(
                    graph_rng,
                    query_variant=str(query.query_variant),
                    degree_mode=str(query.degree_mode),
                    node_count=int(query.node_count),
                    query_degree=int(query.query_degree),
                    target_count=int(query.target_count),
                    max_degree=int(max_degree),
                    topology_profile=str(query.topology_profile),
                    label_variant=str(query.label_variant),
                    search_attempts=max(100, int(search_attempts)),
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
                    scene_title="Directed Graph" if str(query.graph_directionality) == "directed" else "Graph",
                    directed=bool(query.graph_directionality == "directed"),
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
            raise RuntimeError("failed to generate graph degree-count instance") from last_error

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
        prompt_json_example, prompt_json_example_answer_only = _build_prompt_json_examples(
            label_variant=str(query.label_variant)
        )
        prompt_query_key = {
            "degree": "degree_count",
            "in_degree": "in_degree_count",
            "out_degree": "out_degree_count",
        }[str(query.degree_mode)]

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(prompt_query_key),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(
                    prompt_defaults["object_description_directed"]
                    if str(query.graph_directionality) == "directed"
                    else prompt_defaults["object_description_undirected"]
                ),
                "query_degree": int(query.query_degree),
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

        evidence_labels = tuple(sorted((str(label) for label in graph_sample.target_labels), key=graph_label_sort_key))
        answer_gt = TypedValue(type="integer", value=int(len(evidence_labels)))
        evidence_projection = projected_node_point_evidence(rendered_scene, evidence_labels)
        evidence_points = [list(point) for point in evidence_projection["pixel_point_set"]]
        evidence_gt = TypedValue(type="point_set", value=list(evidence_points))
        node_entities = [
            {
                "entity_id": f"node_{node.label}",
                "entity_kind": "graph_node",
                "label": str(node.label),
                "degree": int(node.degree),
                "neighbors": list(node.neighbors),
                "successors": list(node.successors),
                "predecessors": list(node.predecessors),
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
                "scene_kind": "graph_degree_counting",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "counting_rule": f"node_{str(query.degree_mode)}_equals_query_degree",
                    "graph_directionality": str(query.graph_directionality),
                    "degree_mode": str(query.degree_mode),
                    "query_degree": int(query.query_degree),
                    "matching_labels": list(evidence_labels),
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
                "query_variant": str(query.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "graph_directionality": str(query.graph_directionality),
                    "degree_mode": str(query.degree_mode),
                    "degree_mode_probabilities": dict(query.degree_mode_probabilities),
                    "query_variant_probabilities": dict(query.query_variant_probabilities),
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "query_degree": int(query.query_degree),
                    "target_count": int(query.target_count),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "query_degree_probabilities": dict(query.query_degree_probabilities),
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
                    str(max_degree_key): int(max_degree),
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
                "query_variant": str(query.query_variant),
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": f"count_nodes_with_{str(query.degree_mode)}",
                "graph_directionality": str(query.graph_directionality),
                "degree_mode": str(query.degree_mode),
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "query_degree": int(query.query_degree),
                "target_count": int(query.target_count),
                "matching_labels": list(evidence_labels),
                "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                "in_degrees_by_label": {str(key): int(value) for key, value in graph_sample.in_degrees_by_label.items()},
                "out_degrees_by_label": {str(key): int(value) for key, value in graph_sample.out_degrees_by_label.items()},
                "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                "successors_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                "predecessors_by_label": {str(key): list(values) for key, values in graph_sample.predecessors_by_label.items()},
                "degree_sequence": list(graph_sample.degree_sequence),
                "in_degree_sequence": list(graph_sample.in_degree_sequence),
                "out_degree_sequence": list(graph_sample.out_degree_sequence),
                "topology_profile": str(graph_sample.topology_profile),
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
                "labels": list(evidence_labels),
                "degree_mode": str(query.degree_mode),
                "query_degree": int(query.query_degree),
            },
            "projected_evidence": {
                "type": "point_set",
                "point_set": list(evidence_points),
                **dict(evidence_projection),
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
            query_variant=str(query.query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


_MERGED_QUERY_IDS: Tuple[str, ...] = (
    "undirected_degree_count",
    "directed_in_degree_count",
    "directed_out_degree_count",
    "undirected_degree_one_filter_remaining_count",
    "directed_in_degree_one_filter_remaining_count",
    "directed_out_degree_one_filter_remaining_count",
    "directed_source_count",
    "directed_sink_count",
)

_MERGED_QUERY_ALIASES: Dict[str, str] = {
    "degree_count": "undirected_degree_count",
    "in_degree_count": "directed_in_degree_count",
    "out_degree_count": "directed_out_degree_count",
    "source_count": "directed_source_count",
    "sink_count": "directed_sink_count",
    "source": "directed_source_count",
    "sink": "directed_sink_count",
    "undirected_degree_filter_remaining_count": "undirected_degree_one_filter_remaining_count",
    "directed_in_degree_filter_remaining_count": "directed_in_degree_one_filter_remaining_count",
    "directed_out_degree_filter_remaining_count": "directed_out_degree_one_filter_remaining_count",
}


def _normalize_merged_degree_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Translate source degree query-variant params into public query ids."""

    normalized = dict(params)
    query_variant = params.get("query_variant")
    if str(query_variant or "").strip() == "directed_degree_count":
        degree_mode = str(params.get("degree_mode", "")).strip()
        if degree_mode == "out_degree":
            normalized["query_id"] = "directed_out_degree_count"
        elif degree_mode == "in_degree":
            normalized["query_id"] = "directed_in_degree_count"
    return normalized


def _degree_branch_params(params: Mapping[str, Any], query_id: str) -> Dict[str, Any]:
    """Return params forcing one absorbed degree-style branch."""

    forced = dict(params)
    forced.pop("query_id", None)
    forced.pop("query_variant", None)
    if str(query_id) == "undirected_degree_count":
        forced["query_variant"] = "degree_count"
        forced["degree_mode"] = "degree"
    elif str(query_id) == "directed_in_degree_count":
        forced["query_variant"] = "directed_degree_count"
        forced["degree_mode"] = "in_degree"
    elif str(query_id) == "directed_out_degree_count":
        forced["query_variant"] = "directed_degree_count"
        forced["degree_mode"] = "out_degree"
    else:
        raise ValueError(f"unsupported degree branch query id: {query_id}")
    return forced


def _degree_filter_branch_params(params: Mapping[str, Any], query_id: str) -> Dict[str, Any]:
    """Return params forcing one absorbed degree-filter branch."""

    forced = dict(params)
    forced.pop("query_id", None)
    forced.pop("query_variant", None)
    forced.pop("query_variant", None)
    if str(query_id) == "undirected_degree_one_filter_remaining_count":
        forced["graph_directionality"] = "undirected"
        forced["degree_mode"] = "degree"
    elif str(query_id) == "directed_in_degree_one_filter_remaining_count":
        forced["graph_directionality"] = "directed"
        forced["degree_mode"] = "in_degree"
    elif str(query_id) == "directed_out_degree_one_filter_remaining_count":
        forced["graph_directionality"] = "directed"
        forced["degree_mode"] = "out_degree"
    else:
        raise ValueError(f"unsupported degree-filter branch query id: {query_id}")
    return forced


def _source_sink_branch_params(params: Mapping[str, Any], query_id: str) -> Dict[str, Any]:
    """Return params forcing one absorbed source/sink branch."""

    forced = dict(params)
    forced["query_id"] = str(query_id)
    forced["source_sink_mode"] = "source" if str(query_id) == "directed_source_count" else "sink"
    return forced


@register_task
class GraphCountingDegreeCountTask(_GraphCountingDegreeCountBaseTask):
    """Count graph nodes satisfying a degree-style predicate."""

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        public_params = _normalize_merged_degree_params(params)
        branch_base_params = decoupled_merged_branch_params(
            public_params,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            supported_query_ids=_MERGED_QUERY_IDS,
            aliases=_MERGED_QUERY_ALIASES,
        )
        query_id = select_merged_graph_query_id(
            params=public_params,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            supported_query_ids=_MERGED_QUERY_IDS,
            aliases=_MERGED_QUERY_ALIASES,
        )
        if str(query_id) in {
            "undirected_degree_count",
            "directed_in_degree_count",
            "directed_out_degree_count",
        }:
            output = super().generate(
                int(instance_seed),
                params=_degree_branch_params(branch_base_params, str(query_id)),
                max_attempts=int(max_attempts),
            )
            execution_trace = output.trace_payload.get("execution_trace") if isinstance(output.trace_payload, Mapping) else None
            degree_mode = None
            if isinstance(execution_trace, Mapping):
                degree_mode = execution_trace.get("degree_mode")
            if str(degree_mode) == "out_degree":
                output = rewrite_graph_query_output(output, query_id="directed_out_degree_count")
            elif str(degree_mode) == "in_degree":
                output = rewrite_graph_query_output(output, query_id="directed_in_degree_count")
            else:
                output = rewrite_graph_query_output(output, query_id="undirected_degree_count")
        elif str(query_id) in {
            "undirected_degree_one_filter_remaining_count",
            "directed_in_degree_one_filter_remaining_count",
            "directed_out_degree_one_filter_remaining_count",
        }:
            from .node_count_after_degree_filter import GraphCountingNodeCountAfterDegreeFilterTask

            output = GraphCountingNodeCountAfterDegreeFilterTask().generate(
                int(instance_seed),
                params=_degree_filter_branch_params(branch_base_params, str(query_id)),
                max_attempts=int(max_attempts),
            )
        else:
            from .source_sink_count import GraphCountingSourceSinkCountTask

            output = GraphCountingSourceSinkCountTask().generate(
                int(instance_seed),
                params=_source_sink_branch_params(branch_base_params, str(query_id)),
                max_attempts=int(max_attempts),
            )
        return rewrite_graph_public_task_output(output, task_id=TASK_ID, query_id=output.query_id)


__all__ = [
    "GraphCountingDegreeCountTask",
]
