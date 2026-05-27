"""Count nodes remaining after filtering degree-one nodes from a graph."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import hash64, spawn_rng
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
    SUPPORTED_DIRECTED_DEGREE_MODES,
    SUPPORTED_LAYOUT_VARIANTS,
    SUPPORTED_NODE_LINK_LABEL_VARIANTS,
    SUPPORTED_TOPOLOGY_PROFILES,
    feasible_node_counts_for_degree_count,
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
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "graph_node_link_degree_filter_count_internal"
SCENE_ID = "node_link"
FILTER_DEGREE = 1
SUPPORTED_GRAPH_DIRECTIONALITIES: Tuple[str, ...] = ("undirected", "directed")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for degree-filter remaining-count scenes."""

    node_count_min: int = 5
    node_count_max: int = 10
    directed_node_count_max: int = 10
    target_count_min: int = 0
    target_count_max: int = 6
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
    node_color_name: str = "blue"


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved support and style axes for one degree-filter query."""

    graph_directionality: str
    degree_mode: str
    node_count: int
    target_count: int
    removed_count: int
    topology_profile: str
    layout_variant: str
    label_variant: str
    node_shape_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    graph_directionality_probabilities: Dict[str, float]
    degree_mode_probabilities: Dict[str, float]
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


def _degree_count_query_id(graph_directionality: str) -> str:
    """Return the existing degree-count sampler variant for one graph directionality."""

    return "directed_degree_count" if str(graph_directionality) == "directed" else "degree_count"


def _query_key_for_mode(graph_directionality: str, degree_mode: str) -> str:
    """Return the prompt/query key for one resolved degree-filter mode."""

    if str(graph_directionality) == "directed" and str(degree_mode) == "out_degree":
        return "directed_out_degree_one_filter_remaining_count"
    if str(graph_directionality) == "directed":
        return "directed_in_degree_one_filter_remaining_count"
    return "undirected_degree_one_filter_remaining_count"


def _feasible_node_counts_for_remaining_count(
    *,
    graph_directionality: str,
    degree_mode: str,
    target_count: int,
    node_count_min: int,
    node_count_max: int,
    max_degree: int,
    topology_profile: str,
) -> Tuple[int, ...]:
    """Return node counts that can realize exactly ``target_count`` remaining nodes."""

    feasible = []
    sampler_variant = _degree_count_query_id(str(graph_directionality))
    for node_count in range(int(node_count_min), int(node_count_max) + 1):
        removed_count = int(node_count) - int(target_count)
        if int(removed_count) < 0:
            continue
        support = feasible_node_counts_for_degree_count(
            query_id=str(sampler_variant),
            degree_mode=str(degree_mode),
            query_degree=FILTER_DEGREE,
            target_count=int(removed_count),
            node_count_min=int(node_count),
            node_count_max=int(node_count),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
        )
        if support:
            feasible.append(int(node_count))
    return tuple(int(value) for value in feasible)


def _node_count_selection_index(
    instance_seed: int,
    *,
    selection_index: int,
    graph_directionality: str,
    degree_mode: str,
    target_count: int,
    topology_profile: str,
) -> int:
    """Return an independent node-count selection index for the resolved query."""

    namespace = (
        f"{TASK_ID}:node_count:{str(graph_directionality)}:"
        f"{str(degree_mode)}:{int(target_count)}:{str(topology_profile)}"
    )
    return int(hash64(int(instance_seed), namespace, int(selection_index)))


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one degree-one filter remaining-count query."""

    direction_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.graph_directionality")
    graph_directionality, graph_directionality_probabilities = resolve_graph_named_variant(
        direction_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key="graph_directionality",
        weights_key="graph_directionality_weights",
        balance_flag_key="balanced_graph_directionality_sampling",
        supported=SUPPORTED_GRAPH_DIRECTIONALITIES,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace="graph_directionality",
    )
    if str(graph_directionality) == "directed":
        mode_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.degree_mode")
        degree_mode_params = dict(params)
        degree_mode, degree_mode_probabilities = resolve_graph_named_variant(
            mode_rng,
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
        degree_mode = "degree"
        explicit_degree_mode = params.get("degree_mode")
        if explicit_degree_mode is not None and str(explicit_degree_mode) != "degree":
            raise ValueError("degree_mode can only be degree for undirected degree-filter queries")
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
    target_count_min = int(params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min)))
    target_count_max = int(params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max)))
    max_degree_key = "directed_degree_sequence_max_degree" if str(graph_directionality) == "directed" else "degree_sequence_max_degree"
    max_degree_fallback = (
        _DEFAULTS.directed_degree_sequence_max_degree if str(graph_directionality) == "directed" else _DEFAULTS.degree_sequence_max_degree
    )
    max_degree = int(params.get(max_degree_key, group_default(_GEN_DEFAULTS, max_degree_key, max_degree_fallback)))

    target_support = tuple(range(int(target_count_min), int(target_count_max) + 1))
    if not target_support:
        raise ValueError("target_count support is empty for graph degree-filter remaining-count queries")

    feasible_targets = []
    feasible_node_support_by_target: Dict[int, Tuple[int, ...]] = {}
    for target_count in target_support:
        feasible_nodes = _feasible_node_counts_for_remaining_count(
            graph_directionality=str(graph_directionality),
            degree_mode=str(degree_mode),
            target_count=int(target_count),
            node_count_min=int(node_count_min),
            node_count_max=int(node_count_max),
            max_degree=int(max_degree),
            topology_profile=str(topology_profile),
        )
        if feasible_nodes:
            feasible_targets.append(int(target_count))
            feasible_node_support_by_target[int(target_count)] = tuple(int(value) for value in feasible_nodes)
    if not feasible_targets:
        raise ValueError("no feasible graph degree-filter remaining-count support exists")

    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:target_count",
        )
    )
    explicit_target = params.get("target_count")
    if explicit_target is not None:
        target_count = int(explicit_target)
        if int(target_count) not in set(feasible_targets):
            raise ValueError("target_count is outside feasible support for graph degree-filter remaining-count queries")
    else:
        target_count = int(feasible_targets[int(selection_index % len(feasible_targets))])

    feasible_node_support = feasible_node_support_by_target[int(target_count)]
    explicit_node_count = params.get("node_count")
    if explicit_node_count is not None:
        node_count = int(explicit_node_count)
    else:
        node_index = _node_count_selection_index(
            int(instance_seed),
            selection_index=int(selection_index),
            graph_directionality=str(graph_directionality),
            degree_mode=str(degree_mode),
            target_count=int(target_count),
            topology_profile=str(topology_profile),
        )
        node_count = int(feasible_node_support[int(node_index % len(feasible_node_support))])
    if int(node_count) not in feasible_node_support:
        raise ValueError("node_count is outside feasible support for graph degree-filter remaining-count queries")

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
        graph_directionality=str(graph_directionality),
        degree_mode=str(degree_mode),
        node_count=int(node_count),
        target_count=int(target_count),
        removed_count=int(node_count) - int(target_count),
        topology_profile=str(topology_profile),
        layout_variant=str(layout_variant),
        label_variant=str(label_variant),
        node_shape_variant=str(node_shape_variant),
        layout_transform_variant=str(layout_transform_variant),
        edge_routing_variant=str(edge_routing_variant),
        node_color_name=str(node_color_name),
        graph_directionality_probabilities=dict(graph_directionality_probabilities),
        degree_mode_probabilities=dict(degree_mode_probabilities),
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
    removed_ratio = 0.0 if int(node_count) <= 0 else float(query.removed_count) / float(node_count)
    directionality_bonus = 1.0 if str(query.graph_directionality) == "directed" else 0.0

    components = {
        "visual_scan": (0.60 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.directed_node_count_max)))
        + (0.25 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.15 * float(directionality_bonus)),
        "topology_reasoning": (0.60 * normalize_int_with_bounds(int(query.removed_count), (0, int(node_count))))
        + (0.25 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.15 * float(directionality_bonus)),
        "ambiguity": (0.65 * (1.0 - min(1.0, abs(float(removed_ratio) - 0.5) * 2.0)))
        + (0.35 * normalize_int_with_bounds(int(query.target_count), (_DEFAULTS.target_count_min, _DEFAULTS.target_count_max))),
        "clutter": (0.55 * normalize_float_with_bounds(float(edge_density), (0.0, 1.0)))
        + (0.25 * crossing_norm)
        + (0.10 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px)))
        + (0.10 * float(directionality_bonus)),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


def _sorted_remaining_labels(node_labels: Sequence[str], removed_labels: Sequence[str]) -> Tuple[str, ...]:
    """Return deterministic labels that survive the degree-one filter."""

    removed = {str(label) for label in removed_labels}
    return tuple(sorted((str(label) for label in node_labels if str(label) not in removed), key=graph_label_sort_key))


class GraphCountingNodeCountAfterDegreeFilterTask:
    """Count nodes remaining after removing degree-one nodes."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic degree-filter remaining-count instance."""

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

        graph_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.graph")
        last_error: Exception | None = None
        graph_sample = None
        rendered_scene = None
        image = None
        background_meta = {}
        post_noise_meta = {}
        for attempt in range(max(1, int(max_attempts))):
            try:
                graph_sample = sample_degree_count_graph(
                    graph_rng,
                    query_id=_degree_count_query_id(str(query.graph_directionality)),
                    degree_mode=str(query.degree_mode),
                    node_count=int(query.node_count),
                    query_degree=FILTER_DEGREE,
                    target_count=int(query.removed_count),
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
            raise RuntimeError("failed to generate graph degree-filter remaining-count instance") from last_error
        if graph_sample is None or rendered_scene is None or image is None:
            raise RuntimeError("failed to generate graph degree-filter remaining-count instance")

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
        prompt_json_example, prompt_json_example_answer_only = build_graph_prompt_json_examples(evidence_value=[[180, 220], [310, 180], [430, 260]], answer_value=3)
        query_id = _query_key_for_mode(str(query.graph_directionality), str(query.degree_mode))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(
                    prompt_defaults["object_description_directed"]
                    if str(query.graph_directionality) == "directed"
                    else prompt_defaults["object_description_undirected"]
                ),
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

        removed_labels = tuple(sorted((str(label) for label in graph_sample.target_labels), key=graph_label_sort_key))
        remaining_labels = _sorted_remaining_labels(graph_sample.node_labels, removed_labels)
        if len(remaining_labels) != int(query.target_count):
            raise RuntimeError("degree-filter sampler produced inconsistent remaining-node count")

        answer_gt = TypedValue(type="integer", value=int(len(remaining_labels)))
        evidence_projection = projected_node_point_evidence(rendered_scene, remaining_labels)
        evidence_points = [list(point) for point in evidence_projection["pixel_point_set"]]
        evidence_gt = TypedValue(type="point_set", value=list(evidence_points))
        removed_label_set = {str(label) for label in removed_labels}
        remaining_label_set = {str(label) for label in remaining_labels}
        queried_degrees_by_label = {
            str(label): int(graph_sample.degrees_by_label[str(label)])
            for label in graph_sample.node_labels
        }

        node_entities = [
            {
                "entity_id": f"node_{node.label}",
                "entity_kind": "graph_node",
                "label": str(node.label),
                "degree": int(node.degree),
                "in_degree": int(graph_sample.in_degrees_by_label[str(node.label)]),
                "out_degree": int(graph_sample.out_degrees_by_label[str(node.label)]),
                "queried_degree_value": int(queried_degrees_by_label[str(node.label)]),
                "is_removed_by_filter": bool(str(node.label) in removed_label_set),
                "is_remaining_after_filter": bool(str(node.label) in remaining_label_set),
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
                "scene_kind": "graph_degree_filter_remaining_counting",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "query_id": str(query_id),
                    "filter_rule": "remove_nodes_with_queried_degree_equal_to_filter_degree",
                    "filter_degree": int(FILTER_DEGREE),
                    "graph_directionality": str(query.graph_directionality),
                    "degree_mode": str(query.degree_mode),
                    "remaining_labels": list(remaining_labels),
                    "removed_labels": list(removed_labels),
                    "queried_degrees_by_label": dict(queried_degrees_by_label),
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
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "internal_query_id": str(query_id),
                    "query_id_probabilities": {str(query_id): 1.0},
                    "graph_directionality": str(query.graph_directionality),
                    "graph_directionality_probabilities": dict(query.graph_directionality_probabilities),
                    "degree_mode": str(query.degree_mode),
                    "degree_mode_probabilities": dict(query.degree_mode_probabilities),
                    "filter_degree": int(FILTER_DEGREE),
                    "node_count": int(query.node_count),
                    "edge_count": int(graph_sample.edge_count),
                    "target_count": int(query.target_count),
                    "removed_count": int(query.removed_count),
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
                "query_id": str(query_id),
                "internal_query_id": str(query_id),
                "query_id_probabilities": {str(query_id): 1.0},
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": str(query_id),
                "graph_directionality": str(query.graph_directionality),
                "degree_mode": str(query.degree_mode),
                "filter_degree": int(FILTER_DEGREE),
                "node_count": int(query.node_count),
                "edge_count": int(graph_sample.edge_count),
                "target_count": int(query.target_count),
                "removed_count": int(query.removed_count),
                "answer": int(len(remaining_labels)),
                "remaining_labels": list(remaining_labels),
                "removed_labels": list(removed_labels),
                "queried_degrees_by_label": dict(queried_degrees_by_label),
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
                "labels": list(remaining_labels),
                "removed_labels": list(removed_labels),
                "degree_mode": str(query.degree_mode),
                "filter_degree": int(FILTER_DEGREE),
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
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphCountingNodeCountAfterDegreeFilterTask"]
