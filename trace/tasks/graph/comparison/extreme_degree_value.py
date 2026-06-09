"""Report the extreme degree value in one node-link graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
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
from ..shared.fixed_query_task import rewrite_graph_query_output
from ..shared.graph_sampling import (
    SUPPORTED_EXTREME_DEGREE_DIRECTED_MODES,
    SUPPORTED_TOPOLOGY_PROFILES,
    feasible_node_counts_for_extreme_degree_value,
    graph_label_sort_key,
    sample_extreme_degree_graph,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    projected_node_point_annotation,
    render_graph_scene,
)
from ..shared.node_link_axes import resolve_node_link_visual_axes
from ..shared.prompt_examples import build_graph_prompt_json_examples
from ..shared.task_scaffolding import graph_hashed_axis_selection_index
from ..shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__node_link__degree_extremum_value"
SUPPORTED_QUERY_IDS = (
    "undirected_max_degree_value",
    "undirected_min_degree_value",
    "directed_max_in_degree_value",
    "directed_min_in_degree_value",
    "directed_max_out_degree_value",
    "directed_min_out_degree_value",
    "directed_max_total_degree_value",
    "directed_min_total_degree_value",
)
_QUERY_TO_AXES = {
    "undirected_max_degree_value": ("undirected", "degree", "max"),
    "undirected_min_degree_value": ("undirected", "degree", "min"),
    "directed_max_in_degree_value": ("directed", "in_degree", "max"),
    "directed_min_in_degree_value": ("directed", "in_degree", "min"),
    "directed_max_out_degree_value": ("directed", "out_degree", "max"),
    "directed_min_out_degree_value": ("directed", "out_degree", "min"),
    "directed_max_total_degree_value": ("directed", "total_degree", "max"),
    "directed_min_total_degree_value": ("directed", "total_degree", "min"),
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for extreme-degree comparison scenes."""

    node_count_min: int = 5
    node_count_max: int = 10
    directed_node_count_max: int = 10
    target_degree_min: int = 0
    target_degree_max: int = 4
    degree_sequence_max_degree: int = 5
    directed_degree_sequence_max_degree: int = 4
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


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved support and style axes for one extreme-degree query."""

    graph_directionality: str
    degree_mode: str
    extremum_mode: str
    node_count: int
    target_degree: int
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    graph_directionality_probabilities: Dict[str, float]
    degree_mode_probabilities: Dict[str, float]
    extremum_mode_probabilities: Dict[str, float]
    node_count_probabilities: Dict[str, float]
    target_degree_probabilities: Dict[str, float]
    topology_profile_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    label_variant_probabilities: Dict[str, float]
    node_shape_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    edge_routing_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "comparison")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="comparison")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="comparison", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return prompt examples that match the pixel-space node-annotation format."""

    return build_graph_prompt_json_examples(annotation_value=[[180, 220], [310, 180]], answer_value=3)


def _node_count_selection_index(
    instance_seed: int,
    *,
    selection_index: int,
    graph_directionality: str,
    degree_mode: str,
    extremum_mode: str,
    target_degree: int,
    topology_profile: str,
) -> int:
    """Return an independent node-count index for the resolved query support."""

    return graph_hashed_axis_selection_index(
        int(instance_seed),
        task_id=TASK_ID,
        axis_name="node_count",
        selection_index=int(selection_index),
        axis_values=(
            str(graph_directionality),
            str(degree_mode),
            str(extremum_mode),
            int(target_degree),
            str(topology_profile),
        ),
    )

def _query_id_from_axes(*, graph_directionality: str, degree_mode: str, extremum_mode: str) -> str:
    """Return the public query id for one validated extreme-degree axis tuple."""

    if str(graph_directionality) == "undirected":
        if str(degree_mode) != "degree":
            raise ValueError("undirected extreme-degree queries require degree_mode=degree")
        return f"undirected_{str(extremum_mode)}_degree_value"
    if str(degree_mode) not in SUPPORTED_EXTREME_DEGREE_DIRECTED_MODES:
        raise ValueError(f"unsupported directed degree_mode: {degree_mode}")
    return f"directed_{str(extremum_mode)}_{str(degree_mode)}_value"


def _query_id_from_explicit_axes(params: Mapping[str, Any]) -> str | None:
    """Return a query id from complete explicit axis overrides, if present."""

    has_directionality = params.get("graph_directionality") is not None
    has_degree_mode = params.get("degree_mode") is not None
    has_extremum_mode = params.get("extremum_mode") is not None
    if not any((has_directionality, has_degree_mode, has_extremum_mode)):
        return None
    if not all((has_directionality, has_degree_mode, has_extremum_mode)):
        raise ValueError(
            "degree-extremum axis overrides must provide graph_directionality, "
            "degree_mode, and extremum_mode together"
        )
    return _query_id_from_axes(
        graph_directionality=str(params["graph_directionality"]),
        degree_mode=str(params["degree_mode"]),
        extremum_mode=str(params["extremum_mode"]),
    )


def _uniform_positive_probabilities(probabilities: Mapping[str, float]) -> bool:
    """Return true when all positive probabilities are equal."""

    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if not positives:
        return False
    return max(positives) - min(positives) <= 1e-9


def _resolve_public_query_id(instance_seed: int, *, params: Mapping[str, Any]) -> tuple[str, Dict[str, float]]:
    """Resolve the public query branch as the primary sampling axis."""

    explicit_axis_query_id = _query_id_from_explicit_axes(params)
    if explicit_axis_query_id is not None:
        if params.get("query_id") is not None and str(params["query_id"]) != str(explicit_axis_query_id):
            raise ValueError("query_id conflicts with explicit degree-extremum axis overrides")
        if str(explicit_axis_query_id) not in _QUERY_TO_AXES:
            raise ValueError(f"unsupported degree-extremum axis combination: {explicit_axis_query_id}")
        return str(explicit_axis_query_id), {
            str(query_id): (1.0 if str(query_id) == str(explicit_axis_query_id) else 0.0)
            for query_id in SUPPORTED_QUERY_IDS
        }

    raw_query_weights = params.get("query_id_weights")
    if isinstance(raw_query_weights, Mapping):
        query_weights = {str(key): float(value) for key, value in raw_query_weights.items()}
    else:
        raw_default_weights = _GEN_DEFAULTS.get("query_id_weights", {})
        query_weights = (
            {str(key): float(value) for key, value in raw_default_weights.items()}
            if isinstance(raw_default_weights, Mapping)
            else {}
        )
    if not query_weights:
        query_weights = {str(query_id): 1.0 for query_id in SUPPORTED_QUERY_IDS}

    query_id, probabilities = resolve_graph_named_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.query_id"),
        params={**dict(params), "query_id_weights": query_weights},
        gen_defaults={},
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        supported=SUPPORTED_QUERY_IDS,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="query_id",
    )
    use_cursor_cycle = (
        params.get("_sample_cursor") is not None
        and params.get("query_id") is None
        and params.get("query_id_weights") is None
        and bool(params.get("balanced_query_id_sampling", group_default(_GEN_DEFAULTS, "balanced_query_id_sampling", True)))
        and _uniform_positive_probabilities(probabilities)
    )
    if bool(use_cursor_cycle):
        positive_query_ids = [
            str(query)
            for query in SUPPORTED_QUERY_IDS
            if float(probabilities.get(str(query), 0.0)) > 0.0
        ]
        if positive_query_ids:
            query_id = positive_query_ids[abs(int(params["_sample_cursor"])) % len(positive_query_ids)]
    return str(query_id), dict(probabilities)


def _validate_axis_overrides(
    *,
    query_id: str,
    graph_directionality: str,
    degree_mode: str,
    extremum_mode: str,
    params: Mapping[str, Any],
) -> None:
    """Reject explicit axis overrides that conflict with the resolved public query id."""

    explicit_directionality = params.get("graph_directionality")
    if explicit_directionality is not None and str(explicit_directionality) != str(graph_directionality):
        raise ValueError("graph_directionality conflicts with query_id")
    explicit_degree_mode = params.get("degree_mode")
    if explicit_degree_mode is not None and str(explicit_degree_mode) != str(degree_mode):
        raise ValueError("degree_mode conflicts with query_id")
    explicit_extremum_mode = params.get("extremum_mode")
    if explicit_extremum_mode is not None and str(explicit_extremum_mode) != str(extremum_mode):
        raise ValueError("extremum_mode conflicts with query_id")

    if any(key in params for key in ("graph_directionality", "degree_mode", "extremum_mode")):
        derived = _query_id_from_axes(
            graph_directionality=str(graph_directionality),
            degree_mode=str(degree_mode),
            extremum_mode=str(extremum_mode),
        )
        if str(derived) != str(query_id):
            raise ValueError("axis overrides do not map to the resolved query_id")


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one extreme-degree comparison query."""

    query_id, query_id_probabilities = _resolve_public_query_id(int(instance_seed), params=params)
    graph_directionality, degree_mode, extremum_mode = _QUERY_TO_AXES[str(query_id)]
    _validate_axis_overrides(
        query_id=str(query_id),
        graph_directionality=str(graph_directionality),
        degree_mode=str(degree_mode),
        extremum_mode=str(extremum_mode),
        params=params,
    )
    graph_directionality_probabilities = {
        "undirected": sum(
            float(prob)
            for query, prob in query_id_probabilities.items()
            if str(_QUERY_TO_AXES[str(query)][0]) == "undirected"
        ),
        "directed": sum(
            float(prob)
            for query, prob in query_id_probabilities.items()
            if str(_QUERY_TO_AXES[str(query)][0]) == "directed"
        ),
    }
    degree_mode_probabilities = {}
    for query, prob in query_id_probabilities.items():
        mode = str(_QUERY_TO_AXES[str(query)][1])
        degree_mode_probabilities[mode] = float(degree_mode_probabilities.get(mode, 0.0) + float(prob))
    extremum_mode_probabilities = {}
    for query, prob in query_id_probabilities.items():
        mode = str(_QUERY_TO_AXES[str(query)][2])
        extremum_mode_probabilities[mode] = float(extremum_mode_probabilities.get(mode, 0.0) + float(prob))

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
    target_degree_min = int(
        params.get("target_degree_min", group_default(_GEN_DEFAULTS, "target_degree_min", _DEFAULTS.target_degree_min))
    )
    target_degree_max = int(
        params.get("target_degree_max", group_default(_GEN_DEFAULTS, "target_degree_max", _DEFAULTS.target_degree_max))
    )
    max_degree_key = "directed_degree_sequence_max_degree" if str(graph_directionality) == "directed" else "degree_sequence_max_degree"
    max_degree_fallback = (
        _DEFAULTS.directed_degree_sequence_max_degree if str(graph_directionality) == "directed" else _DEFAULTS.degree_sequence_max_degree
    )
    max_degree = int(params.get(max_degree_key, group_default(_GEN_DEFAULTS, max_degree_key, max_degree_fallback)))

    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:query_support",
        )
    )

    target_support = tuple(range(int(target_degree_min), int(target_degree_max) + 1))
    if not target_support:
        raise ValueError("target_degree support is empty for extreme-degree queries")
    feasible_targets = []
    feasible_node_support_by_target: Dict[int, Tuple[int, ...]] = {}
    for target_degree in target_support:
        feasible_nodes = feasible_node_counts_for_extreme_degree_value(
            graph_directionality=str(graph_directionality),
            degree_mode=str(degree_mode),
            extremum_mode=str(extremum_mode),
            target_degree=int(target_degree),
            node_count_min=int(node_count_min),
            node_count_max=int(node_count_max),
            max_degree=int(max_degree),
        )
        if feasible_nodes:
            feasible_targets.append(int(target_degree))
            feasible_node_support_by_target[int(target_degree)] = tuple(int(value) for value in feasible_nodes)
    if not feasible_targets:
        raise ValueError("no feasible support exists for extreme-degree queries")

    explicit_target_degree = params.get("target_degree")
    if explicit_target_degree is not None:
        target_degree = int(explicit_target_degree)
        if int(target_degree) not in feasible_targets:
            raise ValueError("target_degree is outside feasible support")
    else:
        target_degree = int(feasible_targets[int(selection_index % len(feasible_targets))])

    feasible_node_support = feasible_node_support_by_target[int(target_degree)]
    explicit_node_count = params.get("node_count")
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
    else:
        node_index = _node_count_selection_index(
            int(instance_seed),
            selection_index=int(selection_index),
            graph_directionality=str(graph_directionality),
            degree_mode=str(degree_mode),
            extremum_mode=str(extremum_mode),
            target_degree=int(target_degree),
            topology_profile=str(topology_profile),
        )
        node_count = int(feasible_node_support[int(node_index % len(feasible_node_support))])
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for the requested extreme-degree query")

    visual_axes = resolve_node_link_visual_axes(
        int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        task_id=TASK_ID,
    )

    return _ResolvedQuery(
        graph_directionality=str(graph_directionality),
        degree_mode=str(degree_mode),
        extremum_mode=str(extremum_mode),
        node_count=int(node_count),
        target_degree=int(target_degree),
        topology_profile=str(topology_profile),
        layout_variant=str(visual_axes.layout_variant),
        label_variant=str(visual_axes.label_variant),
        node_shape_variant=str(visual_axes.node_shape_variant),
        layout_transform_variant=str(visual_axes.layout_transform_variant),
        edge_routing_variant=str(visual_axes.edge_routing_variant),
        node_color_name=str(visual_axes.node_color_name),
        graph_directionality_probabilities=dict(graph_directionality_probabilities),
        degree_mode_probabilities=dict(degree_mode_probabilities),
        extremum_mode_probabilities=dict(extremum_mode_probabilities),
        node_count_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_node_support),
                selected=int(node_count) if explicit_node_count is not None else None,
            )
        ),
        target_degree_probabilities=dict(
            uniform_probability_map(
                tuple(int(value) for value in feasible_targets),
                selected=int(target_degree) if explicit_target_degree is not None else None,
            )
        ),
        topology_profile_probabilities=dict(topology_probabilities),
        layout_variant_probabilities=dict(visual_axes.layout_variant_probabilities),
        label_variant_probabilities=dict(visual_axes.label_variant_probabilities),
        node_shape_variant_probabilities=dict(visual_axes.node_shape_variant_probabilities),
        layout_transform_variant_probabilities=dict(visual_axes.layout_transform_variant_probabilities),
        edge_routing_variant_probabilities=dict(visual_axes.edge_routing_variant_probabilities),
        node_color_name_probabilities=dict(visual_axes.node_color_name_probabilities),
        query_id_probabilities=dict(query_id_probabilities),
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
    crossing_norm = normalize_float_with_bounds(float(rendered_scene.crossing_count), (0.0, max(1.0, float(max_edges))))
    degree_values = [int(value) for value in graph_sample.queried_degrees_by_label.values()]
    tied_extreme_count = len(graph_sample.target_labels)
    non_extreme_values = [int(value) for value in degree_values if int(value) != int(query.target_degree)]
    if non_extreme_values:
        nearest_gap = min(abs(int(value) - int(query.target_degree)) for value in non_extreme_values)
    else:
        nearest_gap = 0
    directionality_bonus = 1.0 if str(query.graph_directionality) == "directed" else 0.0

    components = {
        "visual_scan": (0.60 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.directed_node_count_max)))
        + (0.30 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.10 * float(directionality_bonus)),
        "topology_reasoning": (0.65 * normalize_int_with_bounds(int(query.target_degree), (_DEFAULTS.target_degree_min, _DEFAULTS.target_degree_max)))
        + (0.25 * normalize_int_with_bounds(len(set(degree_values)), (1, int(node_count))))
        + (0.10 * float(directionality_bonus)),
        "ambiguity": (0.60 * (1.0 - normalize_int_with_bounds(int(nearest_gap), (0, _DEFAULTS.target_degree_max + 1))))
        + (0.40 * normalize_int_with_bounds(int(tied_extreme_count), (1, int(node_count)))),
        "clutter": (0.55 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.25 * crossing_norm)
        + (0.10 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px)))
        + (0.10 * float(directionality_bonus)),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


def _query_key_for(query: _ResolvedQuery) -> str:
    """Return the prompt query key for one resolved query."""

    prefix = "max" if str(query.extremum_mode) == "max" else "min"
    if str(query.graph_directionality) == "undirected":
        return f"{prefix}_degree_value"
    if str(query.degree_mode) == "in_degree":
        return f"{prefix}_in_degree_value"
    if str(query.degree_mode) == "out_degree":
        return f"{prefix}_out_degree_value"
    return f"{prefix}_total_degree_value"


def _public_query_id_for(query: _ResolvedQuery) -> str:
    """Return the public query id for one resolved query."""

    if str(query.graph_directionality) == "undirected":
        return f"undirected_{_query_key_for(query)}"
    return f"directed_{_query_key_for(query)}"


@register_task
class GraphComparisonExtremeDegreeValueTask:
    """Ask for the highest or lowest degree value in a graph."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "comparison"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic graph extreme-degree instance."""

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

        graph_rng = spawn_rng(int(instance_seed), "graph_structure")
        last_error: Exception | None = None
        graph_sample = None
        rendered_scene = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                graph_sample = sample_extreme_degree_graph(
                    graph_rng,
                    graph_directionality=str(query.graph_directionality),
                    degree_mode=str(query.degree_mode),
                    extremum_mode=str(query.extremum_mode),
                    node_count=int(query.node_count),
                    target_degree=int(query.target_degree),
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
            raise RuntimeError("failed to generate graph extreme-degree instance") from last_error

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
                "annotation_hint_max_degree_value",
                "annotation_hint_min_degree_value",
                "annotation_hint_max_in_degree_value",
                "annotation_hint_min_in_degree_value",
                "annotation_hint_max_out_degree_value",
                "annotation_hint_min_out_degree_value",
                "annotation_hint_max_total_degree_value",
                "annotation_hint_min_total_degree_value",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_json_example, prompt_json_example_answer_only = _build_prompt_json_examples()
        prompt_query_key = _query_key_for(query)
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
                "object_description": str(
                    prompt_defaults["object_description_directed"]
                    if str(query.graph_directionality) == "directed"
                    else prompt_defaults["object_description_undirected"]
                ),
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
        answer_gt = TypedValue(type="integer", value=int(graph_sample.target_degree))
        annotation_projection = projected_node_point_annotation(rendered_scene, annotation_labels)
        annotation_points = [list(point) for point in annotation_projection["pixel_point_set"]]
        annotation_gt = TypedValue(type="point_set", value=list(annotation_points))
        node_entities = [
            {
                "entity_id": f"node_{node.label}",
                "entity_kind": "graph_node",
                "label": str(node.label),
                "degree": int(node.degree),
                "total_degree": int(graph_sample.degrees_by_label[str(node.label)]),
                "in_degree": int(graph_sample.in_degrees_by_label[str(node.label)]),
                "out_degree": int(graph_sample.out_degrees_by_label[str(node.label)]),
                "queried_degree": int(graph_sample.queried_degrees_by_label[str(node.label)]),
                "is_extreme_degree_node": bool(str(node.label) in annotation_labels),
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
                "scene_kind": "graph_extreme_degree_comparison",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "comparison_rule": f"{str(query.extremum_mode)}_{str(query.degree_mode)}_value",
                    "graph_directionality": str(query.graph_directionality),
                    "degree_mode": str(query.degree_mode),
                    "extremum_mode": str(query.extremum_mode),
                    "target_degree": int(graph_sample.target_degree),
                    "matching_labels": list(annotation_labels),
                    "successors_by_label": {str(key): list(values) for key, values in graph_sample.successors_by_label.items()},
                    "predecessors_by_label": {str(key): list(values) for key, values in graph_sample.predecessors_by_label.items()},
                    "adjacency_by_label": {str(key): list(values) for key, values in graph_sample.adjacency_by_label.items()},
                    "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                    "in_degrees_by_label": {str(key): int(value) for key, value in graph_sample.in_degrees_by_label.items()},
                    "out_degrees_by_label": {str(key): int(value) for key, value in graph_sample.out_degrees_by_label.items()},
                    "queried_degrees_by_label": {str(key): int(value) for key, value in graph_sample.queried_degrees_by_label.items()},
                    "edge_labels": [list(edge) for edge in graph_sample.edge_labels],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(rendered_scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": "default",
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": "default",
                    "query_id_probabilities": dict(query.query_id_probabilities),
                    "graph_directionality": str(query.graph_directionality),
                    "graph_directionality_probabilities": dict(query.graph_directionality_probabilities),
                    "degree_mode": str(query.degree_mode),
                    "degree_mode_probabilities": dict(query.degree_mode_probabilities),
                    "extremum_mode": str(query.extremum_mode),
                    "extremum_mode_probabilities": dict(query.extremum_mode_probabilities),
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "target_degree": int(query.target_degree),
                    "node_count_probabilities": dict(query.node_count_probabilities),
                    "target_degree_probabilities": dict(query.target_degree_probabilities),
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
                "query_id": "default",
                "query_id_probabilities": dict(query.query_id_probabilities),
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": f"{str(query.extremum_mode)}_{str(query.degree_mode)}_value",
                "graph_directionality": str(query.graph_directionality),
                "degree_mode": str(query.degree_mode),
                "extremum_mode": str(query.extremum_mode),
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "target_degree": int(query.target_degree),
                "answer": int(graph_sample.target_degree),
                "matching_labels": list(annotation_labels),
                "degrees_by_label": {str(key): int(value) for key, value in graph_sample.degrees_by_label.items()},
                "in_degrees_by_label": {str(key): int(value) for key, value in graph_sample.in_degrees_by_label.items()},
                "out_degrees_by_label": {str(key): int(value) for key, value in graph_sample.out_degrees_by_label.items()},
                "queried_degrees_by_label": {str(key): int(value) for key, value in graph_sample.queried_degrees_by_label.items()},
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
                "labels": list(annotation_labels),
                "degree_mode": str(query.degree_mode),
                "extremum_mode": str(query.extremum_mode),
                "target_degree": int(graph_sample.target_degree),
            },
            "projected_annotation": {
                "type": "point_set",
                "point_set": list(annotation_points),
                **dict(annotation_projection),
            },
        }

        return rewrite_graph_query_output(
            TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                answer_gt=answer_gt,
                annotation_gt=annotation_gt,
                image=image,
                image_id="img0",
                trace_payload=trace_payload,
                complexity=complexity,
                task_versions=default_task_versions(),
                scene_id="node_link",
                prompt_variants=dict(prompt_artifacts.prompt_variants),
            ),
            query_id=_public_query_id_for(query),
            query_id_probabilities=dict(query.query_id_probabilities),
        )


__all__ = ["GraphComparisonExtremeDegreeValueTask"]
