"""Solve max-flow and minimum-cut questions on a directed capacity network."""

from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Dict, Mapping, Sequence, Tuple

import networkx as nx

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
    GraphTopologySample,
    canonicalize_graph_edge_label,
    graph_label_sort_key,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    SUPPORTED_EDGE_ROUTING_VARIANTS,
    SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
    RenderedGraphScene,
    projected_edge_pair_evidence,
    render_graph_scene,
)
from ..shared.fixed_query_task import forced_query_id_params, rewrite_graph_public_task_output
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__flow_network__max_flow_value"
MIN_CUT_TASK_ID = "task_graph__flow_network__min_cut_edge_count"
SCENE_ID = "flow_network"

MAX_FLOW_QUERY_ID = "max_flow_value"
MIN_CUT_EDGE_COUNT_QUERY_ID = "minimum_cut_edge_count"
SUPPORTED_MAX_FLOW_QUERY_IDS = (
    MAX_FLOW_QUERY_ID,
    MIN_CUT_EDGE_COUNT_QUERY_ID,
)
SUPPORTED_FLOW_LAYOUT_VARIANTS = ("layered",)
FLOW_INTERNAL_LABELS = ("A", "B", "C", "D", "E")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for flow-network optimization scenes."""

    node_count_min: int = 5
    node_count_max: int = 6
    max_flow_value_min: int = 2
    max_flow_value_max: int = 6
    max_flow_cut_edge_count_min: int = 1
    max_flow_cut_edge_count_max: int = 2
    min_cut_edge_count_min: int = 1
    min_cut_edge_count_max: int = 5
    cut_capacity_part_max: int = 9
    distractor_edge_min: int = 1
    distractor_edge_max: int = 2
    max_flow_distractor_edge_min: int = 0
    max_flow_distractor_edge_max: int = 1
    canvas_width: int = 864
    canvas_height: int = 640
    outer_margin_px: int = 28
    panel_padding_px: int = 24
    panel_corner_radius_px: int = 20
    panel_title_font_size_px: int = 24
    node_shape_variant: str = "circle"
    node_radius_min_px: int = 20
    node_radius_max_px: int = 25
    edge_width_px: int = 4
    arrow_length_px: int = 14
    arrow_width_px: int = 9
    node_border_width_px: int = 2
    label_font_size_px: int = 20
    capacity_label_font_size_px: int = 20
    capacity_label_offset_px: int = 22
    capacity_label_padding_px: int = 6
    node_color_name: str = "blue"


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved support and visual axes for one flow-network query."""

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
class _CutResult:
    """One verified source-sink cut."""

    value: int
    source_side: Tuple[int, ...]
    sink_side: Tuple[int, ...]
    edges: Tuple[Tuple[int, int], ...]


@dataclass(frozen=True)
class _FlowNetworkSample:
    """Trace-ready flow network plus query answer/evidence."""

    graph_sample: GraphTopologySample
    source_label: str
    sink_label: str
    capacity_by_edge_label: Dict[Tuple[str, str], int]
    original_max_flow_value: int
    original_min_cut_edges: Tuple[Tuple[str, str], ...]
    original_min_cut_partition: Tuple[Tuple[str, ...], Tuple[str, ...]]
    answer_value: int
    evidence_edges: Tuple[Tuple[str, str], ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "optimization")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="optimization")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="optimization", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _query_id_from_alias(value: Any) -> str | None:
    """Return the public query id encoded by one query/task alias."""

    text = str(value or "").strip()
    aliases = {
        "max_flow": MAX_FLOW_QUERY_ID,
        "max_flow_value": MAX_FLOW_QUERY_ID,
        "minimum_cut_edge_count": MIN_CUT_EDGE_COUNT_QUERY_ID,
        "min_cut_edge_count": MIN_CUT_EDGE_COUNT_QUERY_ID,
        "default": None,
    }
    return aliases.get(text)


def _forced_query_id(params: Mapping[str, Any]) -> str | None:
    """Resolve an explicitly requested query id, if present."""

    for key in ("query_id", "query_id", "query_id"):
        raw_value = params.get(str(key))
        if raw_value is None:
            continue
        query_id = _query_id_from_alias(raw_value)
        if query_id is not None:
            return str(query_id)
        if str(raw_value).strip() not in {"", "default"}:
            raise ValueError(f"unsupported max-flow query id: {raw_value}")
    return None


def _resolve_named_variant(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Tuple[str, ...],
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced flow-network axis."""

    return resolve_graph_named_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.{str(namespace)}"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported=tuple(str(value) for value in supported),
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace=str(namespace),
    )


def _integer_support_probability(values: Sequence[int], *, selected: int | None = None) -> Dict[str, float]:
    """Return a uniform probability map over integer support."""

    return dict(uniform_probability_map(tuple(int(value) for value in values), selected=selected))


def _select_from_support(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    support: Sequence[int],
    explicit_key: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve one integer support value with optional explicit override."""

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


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one flow-network optimization query."""

    forced_query_id = _forced_query_id(params)
    if forced_query_id is None:
        query_id, query_id_probabilities = _resolve_named_variant(
            int(instance_seed),
            params=params,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            supported=SUPPORTED_MAX_FLOW_QUERY_IDS,
            namespace="query_id",
        )
    else:
        query_id = str(forced_query_id)
        query_id_probabilities = {
            str(supported_query_id): (1.0 if str(supported_query_id) == str(query_id) else 0.0)
            for supported_query_id in SUPPORTED_MAX_FLOW_QUERY_IDS
        }

    node_count_min = int(params.get("node_count_min", group_default(_GEN_DEFAULTS, "node_count_min", _DEFAULTS.node_count_min)))
    node_count_max = int(params.get("node_count_max", group_default(_GEN_DEFAULTS, "node_count_max", _DEFAULTS.node_count_max)))
    node_support = tuple(int(value) for value in range(max(4, int(node_count_min)), int(node_count_max) + 1))
    node_count, node_count_probabilities = _select_from_support(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:node_count",
        support=node_support,
        explicit_key="node_count",
    )

    cut_count_min = int(
        params.get("min_cut_edge_count_min", group_default(_GEN_DEFAULTS, "min_cut_edge_count_min", _DEFAULTS.min_cut_edge_count_min))
    )
    cut_count_max = int(
        params.get("min_cut_edge_count_max", group_default(_GEN_DEFAULTS, "min_cut_edge_count_max", _DEFAULTS.min_cut_edge_count_max))
    )
    cut_count_support = tuple(int(value) for value in range(max(1, int(cut_count_min)), int(cut_count_max) + 1))

    if str(query_id) == MIN_CUT_EDGE_COUNT_QUERY_ID:
        target_answer, target_answer_probabilities = _select_from_support(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:target_answer:{query_id}",
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
            namespace=f"{TASK_ID}:target_flow_value:{query_id}:{target_cut_edge_count}",
            support=feasible_flow,
            explicit_key="target_flow_value",
        )
    else:
        flow_min = int(params.get("max_flow_value_min", group_default(_GEN_DEFAULTS, "max_flow_value_min", _DEFAULTS.max_flow_value_min)))
        flow_max = int(params.get("max_flow_value_max", group_default(_GEN_DEFAULTS, "max_flow_value_max", _DEFAULTS.max_flow_value_max)))
        flow_support = tuple(int(value) for value in range(max(1, int(flow_min)), int(flow_max) + 1))
        target_answer, target_answer_probabilities = _select_from_support(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:target_answer:{query_id}",
            support=flow_support,
            explicit_key="target_answer",
        )
        max_flow_cut_min = int(
            params.get(
                "max_flow_cut_edge_count_min",
                group_default(_GEN_DEFAULTS, "max_flow_cut_edge_count_min", _DEFAULTS.max_flow_cut_edge_count_min),
            )
        )
        max_flow_cut_max = int(
            params.get(
                "max_flow_cut_edge_count_max",
                group_default(_GEN_DEFAULTS, "max_flow_cut_edge_count_max", _DEFAULTS.max_flow_cut_edge_count_max),
            )
        )
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
            namespace=f"{TASK_ID}:target_cut_edge_count:{query_id}:{target_answer}",
            support=feasible_cut_counts,
            explicit_key="target_cut_edge_count",
        )
        target_flow_value = int(target_answer)
        target_flow_value_probabilities = {str(target_flow_value): 1.0}

    if str(query_id) == MIN_CUT_EDGE_COUNT_QUERY_ID:
        target_cut_edge_count_probabilities = _integer_support_probability(cut_count_support, selected=int(target_cut_edge_count))

    if str(query_id) == MAX_FLOW_QUERY_ID:
        distractor_min = int(
            params.get(
                "max_flow_distractor_edge_min",
                group_default(_GEN_DEFAULTS, "max_flow_distractor_edge_min", _DEFAULTS.max_flow_distractor_edge_min),
            )
        )
        distractor_max = int(
            params.get(
                "max_flow_distractor_edge_max",
                group_default(_GEN_DEFAULTS, "max_flow_distractor_edge_max", _DEFAULTS.max_flow_distractor_edge_max),
            )
        )
    else:
        distractor_min = int(params.get("distractor_edge_min", group_default(_GEN_DEFAULTS, "distractor_edge_min", _DEFAULTS.distractor_edge_min)))
        distractor_max = int(params.get("distractor_edge_max", group_default(_GEN_DEFAULTS, "distractor_edge_max", _DEFAULTS.distractor_edge_max)))
    distractor_support = tuple(int(value) for value in range(max(0, int(distractor_min)), max(int(distractor_min), int(distractor_max)) + 1))
    distractor_edge_count, distractor_edge_count_probabilities = _select_from_support(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:distractor_edge_count",
        support=distractor_support,
        explicit_key="distractor_edge_count",
    )

    layout_variant, layout_variant_probabilities = _resolve_named_variant(
        int(instance_seed),
        params=params,
        explicit_key="layout_variant",
        weights_key="layout_variant_weights",
        balance_flag_key="balanced_layout_variant_sampling",
        supported=SUPPORTED_FLOW_LAYOUT_VARIANTS,
        namespace="layout_variant",
    )
    layout_transform_variant, layout_transform_variant_probabilities = _resolve_named_variant(
        int(instance_seed),
        params=params,
        explicit_key="layout_transform_variant",
        weights_key="layout_transform_variant_weights",
        balance_flag_key="balanced_layout_transform_variant_sampling",
        supported=SUPPORTED_LAYOUT_TRANSFORM_VARIANTS,
        namespace="layout_transform_variant",
    )
    edge_routing_variant, edge_routing_variant_probabilities = _resolve_named_variant(
        int(instance_seed),
        params=params,
        explicit_key="edge_routing_variant",
        weights_key="edge_routing_variant_weights",
        balance_flag_key="balanced_edge_routing_variant_sampling",
        supported=SUPPORTED_EDGE_ROUTING_VARIANTS,
        namespace="edge_routing_variant",
    )
    node_color_name, node_color_name_probabilities = _resolve_named_variant(
        int(instance_seed),
        params=params,
        explicit_key="node_color_name",
        weights_key="node_color_name_weights",
        balance_flag_key="balanced_node_color_name_sampling",
        supported=SUPPORTED_NODE_COLOR_NAMES,
        namespace="node_color_name",
    )

    return _ResolvedQuery(
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
        query_id_probabilities=dict(query_id_probabilities),
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


def _node_labels(node_count: int) -> Tuple[str, ...]:
    """Return conventional source/sink labels plus compact internal labels."""

    internal_count = max(0, int(node_count) - 2)
    if int(internal_count) > len(FLOW_INTERNAL_LABELS):
        raise ValueError("flow network node_count exceeds available internal labels")
    return ("S", *tuple(FLOW_INTERNAL_LABELS[: int(internal_count)]), "T")


def _positive_capacity_parts(
    rng: random.Random,
    *,
    total: int,
    count: int,
    max_part: int,
) -> Tuple[int, ...]:
    """Sample positive integer capacities with a fixed sum and per-edge cap."""

    total_int = int(total)
    count_int = int(count)
    max_part_int = int(max_part)
    if count_int <= 0 or total_int < count_int or total_int > count_int * max_part_int:
        raise ValueError("infeasible capacity composition")
    candidates: list[Tuple[int, ...]] = []

    def _recurse(prefix: Tuple[int, ...], remaining: int, slots: int) -> None:
        if int(slots) == 0:
            if int(remaining) == 0:
                candidates.append(tuple(int(value) for value in prefix))
            return
        low = max(1, int(remaining) - ((int(slots) - 1) * int(max_part_int)))
        high = min(int(max_part_int), int(remaining) - (int(slots) - 1))
        for value in range(int(low), int(high) + 1):
            _recurse((*prefix, int(value)), int(remaining) - int(value), int(slots) - 1)

    _recurse((), int(total_int), int(count_int))
    if not candidates:
        raise ValueError("no capacity composition candidates")
    return tuple(int(value) for value in rng.choice(candidates))


def _all_st_cuts(
    graph: nx.DiGraph,
    *,
    source: int,
    sink: int,
    capacity_by_edge: Mapping[Tuple[int, int], int],
) -> Tuple[_CutResult, ...]:
    """Enumerate all source-sink cuts for a small directed network."""

    nodes = tuple(sorted(int(node) for node in graph.nodes()))
    internal_nodes = tuple(int(node) for node in nodes if int(node) not in {int(source), int(sink)})
    active_edges = tuple((int(left), int(right)) for left, right in graph.edges())
    cuts: list[_CutResult] = []
    for subset_size in range(0, len(internal_nodes) + 1):
        for subset in combinations(internal_nodes, subset_size):
            source_side = tuple(sorted((int(source), *tuple(int(value) for value in subset))))
            source_set = set(source_side)
            sink_side = tuple(sorted(int(node) for node in nodes if int(node) not in source_set))
            cut_edges = tuple(
                sorted(
                    ((int(left), int(right)) for left, right in active_edges if int(left) in source_set and int(right) not in source_set),
                    key=lambda edge: (int(edge[0]), int(edge[1])),
                )
            )
            value = sum(int(capacity_by_edge[(int(left), int(right))]) for left, right in cut_edges)
            cuts.append(
                _CutResult(
                    value=int(value),
                    source_side=tuple(int(node) for node in source_side),
                    sink_side=tuple(int(node) for node in sink_side),
                    edges=tuple((int(left), int(right)) for left, right in cut_edges),
                )
            )
    return tuple(cuts)


def _unique_min_cut(
    graph: nx.DiGraph,
    *,
    source: int,
    sink: int,
    capacity_by_edge: Mapping[Tuple[int, int], int],
) -> _CutResult:
    """Return the unique minimum source-sink cut or raise."""

    cuts = _all_st_cuts(
        graph,
        source=int(source),
        sink=int(sink),
        capacity_by_edge=capacity_by_edge,
    )
    if not cuts:
        raise ValueError("no source-sink cuts found")
    min_value = min(int(cut.value) for cut in cuts)
    min_cuts = tuple(cut for cut in cuts if int(cut.value) == int(min_value))
    unique_edge_sets = {tuple(cut.edges) for cut in min_cuts}
    if len(min_cuts) != 1 or len(unique_edge_sets) != 1:
        raise ValueError("minimum source-sink cut is not unique")
    return min_cuts[0]


def _build_topology_sample(
    *,
    graph: nx.DiGraph,
    labels: Sequence[str],
) -> GraphTopologySample:
    """Build a generic graph topology record for one directed flow network."""

    label_by_node = {int(node): str(labels[int(node)]) for node in graph.nodes()}
    edge_labels = tuple(
        sorted(
            ((str(label_by_node[int(left)]), str(label_by_node[int(right)])) for left, right in graph.edges()),
            key=lambda pair: (graph_label_sort_key(pair[0]), graph_label_sort_key(pair[1])),
        )
    )
    adjacency_by_label = {
        str(label_by_node[int(node)]): tuple(
            sorted(
                {
                    *[str(label_by_node[int(neighbor)]) for neighbor in graph.predecessors(int(node))],
                    *[str(label_by_node[int(neighbor)]) for neighbor in graph.successors(int(node))],
                },
                key=graph_label_sort_key,
            )
        )
        for node in graph.nodes()
    }
    successors_by_label = {
        str(label_by_node[int(node)]): tuple(
            sorted((str(label_by_node[int(neighbor)]) for neighbor in graph.successors(int(node))), key=graph_label_sort_key)
        )
        for node in graph.nodes()
    }
    predecessors_by_label = {
        str(label_by_node[int(node)]): tuple(
            sorted((str(label_by_node[int(neighbor)]) for neighbor in graph.predecessors(int(node))), key=graph_label_sort_key)
        )
        for node in graph.nodes()
    }
    return GraphTopologySample(
        graph=graph,
        directed=True,
        node_labels=tuple(str(label_by_node[int(node)]) for node in graph.nodes()),
        edge_labels=tuple((str(left), str(right)) for left, right in edge_labels),
        degrees_by_label={
            str(label_by_node[int(node)]): int(graph.in_degree(int(node)) + graph.out_degree(int(node)))
            for node in graph.nodes()
        },
        in_degrees_by_label={str(label_by_node[int(node)]): int(graph.in_degree(int(node))) for node in graph.nodes()},
        out_degrees_by_label={str(label_by_node[int(node)]): int(graph.out_degree(int(node))) for node in graph.nodes()},
        adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in adjacency_by_label.items()},
        successors_by_label={str(key): tuple(str(value) for value in values) for key, values in successors_by_label.items()},
        predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in predecessors_by_label.items()},
        edge_count=int(graph.number_of_edges()),
        topology_profile="layered_capacity_network",
        label_variant="source_sink_letters",
    )


def _sample_flow_network(rng: random.Random, *, query: _ResolvedQuery) -> _FlowNetworkSample:
    """Construct one capacitated directed graph with a unique source-sink cut."""

    node_count = int(query.node_count)
    labels = _node_labels(node_count)
    source = 0
    sink = int(node_count) - 1
    internal_nodes = tuple(int(node) for node in range(1, int(node_count) - 1))
    if len(internal_nodes) < 2:
        raise ValueError("flow network requires at least two internal nodes")
    source_side_count = int(rng.randint(1, len(internal_nodes) - 1))
    # Keep the source-side states earlier in the label order so most layouts read
    # like a left-to-right flow network rather than a scrambled arbitrary DAG.
    source_internal = tuple(int(node) for node in internal_nodes[: int(source_side_count)])
    sink_internal = tuple(int(node) for node in internal_nodes[int(source_side_count) :])
    source_side_nodes = (int(source), *tuple(int(node) for node in source_internal))
    sink_side_nodes = (*tuple(int(node) for node in sink_internal), int(sink))

    candidate_cut_edges = [
        (int(left), int(right))
        for left in source_side_nodes
        for right in sink_side_nodes
        if int(left) != int(right) and not (int(left) == int(source) and int(right) == int(sink))
    ]
    if len(candidate_cut_edges) < int(query.target_cut_edge_count):
        raise ValueError("not enough candidate cut edges")
    rng.shuffle(candidate_cut_edges)
    cut_edges = tuple(sorted(candidate_cut_edges[: int(query.target_cut_edge_count)], key=lambda edge: (int(edge[0]), int(edge[1]))))

    graph = nx.DiGraph()
    graph.add_nodes_from(range(int(node_count)))
    capacity_by_edge: Dict[Tuple[int, int], int] = {}
    high_capacity = int(query.target_flow_value) + int(rng.randint(5, 9))

    def _add_edge(left: int, right: int, capacity: int) -> None:
        if int(left) == int(right):
            return
        graph.add_edge(int(left), int(right))
        graph[int(left)][int(right)]["capacity"] = int(capacity)
        capacity_by_edge[(int(left), int(right))] = int(capacity)

    for node in source_internal:
        _add_edge(int(source), int(node), int(high_capacity + rng.randint(0, 3)))
    for node in sink_internal:
        _add_edge(int(node), int(sink), int(high_capacity + rng.randint(0, 3)))

    possible_internal = [
        (int(left), int(right))
        for left in source_internal
        for right in source_internal
        if int(left) < int(right)
    ] + [
        (int(left), int(right))
        for left in sink_internal
        for right in sink_internal
        if int(left) < int(right)
    ]
    rng.shuffle(possible_internal)
    for left, right in possible_internal[: int(query.distractor_edge_count)]:
        _add_edge(int(left), int(right), int(high_capacity + rng.randint(0, 3)))

    parts = _positive_capacity_parts(
        rng,
        total=int(query.target_flow_value),
        count=len(cut_edges),
        max_part=int(_DEFAULTS.cut_capacity_part_max),
    )
    cut_capacities = {tuple(edge): int(capacity) for edge, capacity in zip(cut_edges, parts)}

    for edge in cut_edges:
        _add_edge(int(edge[0]), int(edge[1]), int(cut_capacities[tuple(edge)]))

    original_cut = _unique_min_cut(
        graph,
        source=int(source),
        sink=int(sink),
        capacity_by_edge=capacity_by_edge,
    )
    original_flow = int(nx.maximum_flow_value(graph, int(source), int(sink), capacity="capacity"))
    if int(original_flow) != int(query.target_flow_value):
        raise ValueError("constructed flow network has wrong max-flow value")

    topology_sample = _build_topology_sample(graph=graph, labels=labels)
    capacity_by_label = {
        canonicalize_graph_edge_label(str(labels[int(left)]), str(labels[int(right)]), directed=True): int(capacity)
        for (left, right), capacity in capacity_by_edge.items()
    }

    def _label_edges(edges: Sequence[Tuple[int, int]]) -> Tuple[Tuple[str, str], ...]:
        return tuple(
            sorted(
                (
                    canonicalize_graph_edge_label(str(labels[int(left)]), str(labels[int(right)]), directed=True)
                    for left, right in edges
                ),
                key=lambda edge: (graph_label_sort_key(edge[0]), graph_label_sort_key(edge[1])),
            )
        )

    original_cut_labels = _label_edges(original_cut.edges)
    if str(query.query_id) == MIN_CUT_EDGE_COUNT_QUERY_ID:
        answer_value = int(len(original_cut_labels))
        evidence_edges = tuple(original_cut_labels)
    else:
        answer_value = int(original_flow)
        evidence_edges = tuple(original_cut_labels)

    original_source_side_labels = tuple(sorted((str(labels[int(node)]) for node in original_cut.source_side), key=graph_label_sort_key))
    original_sink_side_labels = tuple(sorted((str(labels[int(node)]) for node in original_cut.sink_side), key=graph_label_sort_key))
    return _FlowNetworkSample(
        graph_sample=topology_sample,
        source_label="S",
        sink_label="T",
        capacity_by_edge_label=dict(capacity_by_label),
        original_max_flow_value=int(original_flow),
        original_min_cut_edges=tuple(original_cut_labels),
        original_min_cut_partition=(tuple(original_source_side_labels), tuple(original_sink_side_labels)),
        answer_value=int(answer_value),
        evidence_edges=tuple(evidence_edges),
    )


def _build_complexity(
    *,
    query: _ResolvedQuery,
    flow_sample: _FlowNetworkSample,
    render_params: GraphRenderParams,
    rendered_scene: RenderedGraphScene,
) -> Any:
    """Build one within-task normalized complexity record."""

    node_count = int(query.node_count)
    edge_count = int(flow_sample.graph_sample.edge_count)
    cut_count = len(flow_sample.evidence_edges)
    crossing_norm = normalize_float_with_bounds(float(rendered_scene.crossing_count), (0.0, max(1.0, float(edge_count))))
    capacity_span = max(flow_sample.capacity_by_edge_label.values()) - min(flow_sample.capacity_by_edge_label.values())
    components = {
        "visual_scan": (0.45 * normalize_int_with_bounds(int(edge_count), (5, 13)))
        + (0.35 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max)))
        + (0.20 * normalize_int_with_bounds(int(cut_count), (_DEFAULTS.min_cut_edge_count_min, _DEFAULTS.min_cut_edge_count_max))),
        "topology_reasoning": 0.35
        + (0.35 * normalize_int_with_bounds(int(node_count), (_DEFAULTS.node_count_min, _DEFAULTS.node_count_max)))
        + (0.12 if str(query.query_id) == MAX_FLOW_QUERY_ID else 0.0),
        "ambiguity": (0.50 * normalize_int_with_bounds(int(capacity_span), (4, 20)))
        + (0.25 * normalize_int_with_bounds(int(cut_count), (_DEFAULTS.min_cut_edge_count_min, _DEFAULTS.min_cut_edge_count_max))),
        "clutter": (0.60 * normalize_int_with_bounds(int(edge_count), (5, 13)))
        + (0.25 * crossing_norm)
        + (0.15 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px))),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


class _GraphOptimizationFlowNetworkTask:
    """Answer max-flow and min-cut questions on a directed capacity graph."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "optimization"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic max-flow/min-cut task instance."""

        query = _resolve_query(int(instance_seed), params=params)
        render_params = resolve_graph_render_params(
            params,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            node_color_name=str(query.node_color_name),
            node_shape_variant="circle",
            edge_routing_variant=str(query.edge_routing_variant),
        )
        capacity_label_font_size_px = int(
            params.get(
                "capacity_label_font_size_px",
                group_default(_RENDER_DEFAULTS, "capacity_label_font_size_px", _DEFAULTS.capacity_label_font_size_px),
            )
        )
        capacity_label_offset_px = int(
            params.get(
                "capacity_label_offset_px",
                group_default(_RENDER_DEFAULTS, "capacity_label_offset_px", _DEFAULTS.capacity_label_offset_px),
            )
        )
        capacity_label_padding_px = int(
            params.get(
                "capacity_label_padding_px",
                group_default(_RENDER_DEFAULTS, "capacity_label_padding_px", _DEFAULTS.capacity_label_padding_px),
            )
        )
        graph_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.graph")
        last_error: Exception | None = None
        flow_sample = None
        rendered_scene = None
        image = None
        background_meta: Dict[str, Any] = {}
        post_noise_meta: Dict[str, Any] = {}
        for attempt in range(max(1, int(max_attempts))):
            try:
                flow_sample = _sample_flow_network(graph_rng, query=query)
                background, background_meta = make_background_canvas(
                    canvas_width=int(render_params.canvas_width),
                    canvas_height=int(render_params.canvas_height),
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
                )
                node_style_by_label = {
                    "S": {
                        "fill_rgb": (42, 157, 88),
                        "border_rgb": (20, 100, 58),
                        "label_text_rgb": (255, 255, 255),
                        "label_stroke_rgb": (20, 100, 58),
                        "halo_rgb": (20, 100, 58),
                        "halo_width_px": 3,
                        "halo_pad_px": 6,
                    },
                    "T": {
                        "fill_rgb": (126, 87, 194),
                        "border_rgb": (80, 48, 140),
                        "label_text_rgb": (255, 255, 255),
                        "label_stroke_rgb": (80, 48, 140),
                        "halo_rgb": (80, 48, 140),
                        "halo_width_px": 3,
                        "halo_pad_px": 6,
                    },
                }
                rendered_scene = render_graph_scene(
                    graph_sample=flow_sample.graph_sample,
                    layout_variant=str(query.layout_variant),
                    layout_transform_variant=str(query.layout_transform_variant),
                    render_params=render_params,
                    layout_seed=int(instance_seed + attempt),
                    scene_title="Capacity Network",
                    directed=True,
                    base_image=background,
                    edge_weights_by_label=dict(flow_sample.capacity_by_edge_label),
                    edge_weight_label_font_size_px=int(capacity_label_font_size_px),
                    edge_weight_label_offset_px=int(capacity_label_offset_px),
                    edge_weight_label_padding_px=int(capacity_label_padding_px),
                    node_style_by_label=node_style_by_label,
                    edge_style_by_label={},
                    layout_fallback_variants=("layered",),
                )
                if any(edge.weight_label_bbox_xyxy is None for edge in rendered_scene.edges):
                    raise ValueError("not all capacity labels were rendered")
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
            raise RuntimeError("failed to generate max-flow optimization instance") from last_error
        if flow_sample is None or rendered_scene is None or image is None:
            raise RuntimeError("failed to generate max-flow optimization instance")

        answer_hint_key = f"answer_hint_{query.query_id}"
        json_example_key = f"json_example_{query.query_id}"
        json_example_answer_only_key = f"json_example_answer_only_{query.query_id}"
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_directed",
                answer_hint_key,
                "evidence_hint_minimum_cut_edges",
                json_example_key,
                json_example_answer_only_key,
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_directed"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint_minimum_cut_edges"]),
                "answer_hint": str(prompt_defaults[answer_hint_key]),
                "json_example": str(prompt_defaults[json_example_key]),
                "json_example_answer_only": str(prompt_defaults[json_example_answer_only_key]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_projection = projected_edge_pair_evidence(rendered_scene, flow_sample.evidence_edges)
        evidence_point_pairs = [[list(point) for point in pair] for pair in evidence_projection["point_pair_set"]]
        if len(evidence_point_pairs) != len(flow_sample.evidence_edges):
            raise RuntimeError("flow min-cut evidence projection is incomplete")
        answer_gt = TypedValue(type="integer", value=int(flow_sample.answer_value))
        evidence_gt = TypedValue(type="point_pair_set", value=list(evidence_point_pairs))
        evidence_edge_set = set(tuple(edge) for edge in flow_sample.evidence_edges)
        original_min_cut_set = set(tuple(edge) for edge in flow_sample.original_min_cut_edges)

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
                "capacity": int(edge.weight) if edge.weight is not None else None,
                "capacity_label_bbox_xyxy": list(edge.weight_label_bbox_xyxy) if edge.weight_label_bbox_xyxy is not None else None,
                "is_original_min_cut_edge": bool((str(edge.node_u_label), str(edge.node_v_label)) in original_min_cut_set),
                "is_evidence_edge": bool((str(edge.node_u_label), str(edge.node_v_label)) in evidence_edge_set),
            }
            for edge in rendered_scene.edges
        ]
        capacities_trace = [
            {"edge": [str(left), str(right)], "capacity": int(capacity)}
            for (left, right), capacity in sorted(
                flow_sample.capacity_by_edge_label.items(),
                key=lambda item: (graph_label_sort_key(item[0][0]), graph_label_sort_key(item[0][1])),
            )
        ]
        complexity = _build_complexity(
            query=query,
            flow_sample=flow_sample,
            render_params=render_params,
            rendered_scene=rendered_scene,
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "graph_capacity_flow_network",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "query_id": str(query.query_id),
                    "graph_directionality": "directed",
                    "source_label": "S",
                    "sink_label": "T",
                    "capacity_by_edge": list(capacities_trace),
                    "original_max_flow_value": int(flow_sample.original_max_flow_value),
                    "original_min_cut_edges": [list(edge) for edge in flow_sample.original_min_cut_edges],
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
                    "node_shape_variant": "circle",
                    "node_radius_px": int(render_params.node_radius_px),
                    "edge_width_px": int(render_params.edge_width_px),
                    "edge_routing_variant": str(rendered_scene.edge_routing_variant),
                    "arrow_length_px": int(render_params.arrow_length_px),
                    "arrow_width_px": int(render_params.arrow_width_px),
                    "node_border_width_px": int(render_params.node_border_width_px),
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "resolved_label_font_size_px": int(rendered_scene.resolved_label_font_size_px),
                    "label_stroke_width_px": int(rendered_scene.resolved_label_stroke_width_px),
                    "capacity_label_font_size_px": int(capacity_label_font_size_px),
                    "capacity_label_offset_px": int(capacity_label_offset_px),
                    "capacity_label_padding_px": int(capacity_label_padding_px),
                    "font_family": str(render_params.font_family or ""),
                    "font_asset": dict(render_params.font_asset) if isinstance(render_params.font_asset, Mapping) else {},
                    "font_asset_version": str(render_params.font_asset_version or ""),
                    "font_exclusion_reason": str(render_params.font_exclusion_reason),
                    "context_text_elements": list(rendered_scene.panel_geometry.get("context_text_elements", [])),
                    "background_meta": dict(background_meta),
                    "post_image_noise_meta": dict(post_noise_meta),
                },
            },
            "render_map": {"image_id": "img0", "anchors": {}},
            "execution_trace": {
                "query_id": str(query.query_id),
                "internal_query_id": str(query.query_id),
                "query_id_probabilities": dict(query.query_id_probabilities),
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": str(query.query_id),
                "graph_directionality": "directed",
                "node_count": int(query.node_count),
                "edge_count": int(flow_sample.graph_sample.edge_count),
                "source_label": "S",
                "sink_label": "T",
                "answer": int(flow_sample.answer_value),
                "original_max_flow_value": int(flow_sample.original_max_flow_value),
                "original_min_cut_edge_count": int(len(flow_sample.original_min_cut_edges)),
                "original_min_cut_edges": [list(edge) for edge in flow_sample.original_min_cut_edges],
                "original_min_cut_partition": [list(flow_sample.original_min_cut_partition[0]), list(flow_sample.original_min_cut_partition[1])],
                "evidence_edges": [list(edge) for edge in flow_sample.evidence_edges],
                "capacity_by_edge": list(capacities_trace),
                "successors_by_label": {str(key): list(values) for key, values in flow_sample.graph_sample.successors_by_label.items()},
                "predecessors_by_label": {str(key): list(values) for key, values in flow_sample.graph_sample.predecessors_by_label.items()},
                "layout_variant_requested": str(query.layout_variant),
                "layout_variant_used": str(rendered_scene.layout_variant),
                "layout_transform_variant": str(rendered_scene.layout_transform_variant),
                "edge_routing_variant": str(rendered_scene.edge_routing_variant),
                "node_color_name": str(query.node_color_name),
                "crossing_count": int(rendered_scene.crossing_count),
            },
            "witness_symbolic": {
                "type": "directed_edge_pair_set",
                "edges": [list(edge) for edge in flow_sample.evidence_edges],
            },
            "projected_evidence": {
                "type": "point_pair_set",
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
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GraphOptimizationMaxFlowValueTask(_GraphOptimizationFlowNetworkTask):
    """Answer maximum-flow value questions on a directed capacity graph."""

    task_id = TASK_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        forced_params = forced_query_id_params(params, query_id=MAX_FLOW_QUERY_ID)
        output = super().generate(int(instance_seed), params=forced_params, max_attempts=int(max_attempts))
        return rewrite_graph_public_task_output(output, task_id=self.task_id, query_id=MAX_FLOW_QUERY_ID)


@register_task
class GraphOptimizationMinCutEdgeCountTask(_GraphOptimizationFlowNetworkTask):
    """Answer minimum-cut edge-count questions on a directed capacity graph."""

    task_id = MIN_CUT_TASK_ID

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        forced_params = forced_query_id_params(params, query_id=MIN_CUT_EDGE_COUNT_QUERY_ID)
        output = super().generate(int(instance_seed), params=forced_params, max_attempts=int(max_attempts))
        return rewrite_graph_public_task_output(output, task_id=self.task_id, query_id=MIN_CUT_EDGE_COUNT_QUERY_ID)


__all__ = ["GraphOptimizationMaxFlowValueTask", "GraphOptimizationMinCutEdgeCountTask"]
