"""Simulate a deterministic state-transition diagram for a short input string."""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

import networkx as nx
from PIL import ImageDraw

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
from ...shared.text_rendering import load_font
from ..shared.complexity import (
    build_graph_complexity,
    normalize_float_with_bounds,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.graph_sampling import (
    SUPPORTED_LAYOUT_VARIANTS,
    GraphTopologySample,
    graph_label_sort_key,
)
from ..shared.graph_scene import (
    GraphRenderParams,
    RenderedGraphScene,
    projected_edge_label_bbox_evidence,
    projected_node_point_evidence,
    render_graph_scene,
)
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import resolve_forced_graph_query_id, resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults


TASK_ID = "task_graph__automaton__state_after_input_label"
SCENE_ID = "automaton"

FINAL_STATE_QUERY_ID = "final_state_label"
STEP_STATE_QUERY_ID = "transition_step_state_label"
SUPPORTED_AUTOMATON_QUERY_IDS = (FINAL_STATE_QUERY_ID, STEP_STATE_QUERY_ID)
SUPPORTED_AUTOMATON_LAYOUT_VARIANTS = ("circular", "shell", "layered", "path_spine", "spring")
AUTOMATON_SYMBOLS = ("0", "1")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for automaton state-transition scenes."""

    state_count_min: int = 4
    state_count_max: int = 6
    input_length_min: int = 3
    input_length_max: int = 6
    transition_step_min: int = 2
    transition_step_max: int = 5
    distractor_edge_min: int = 2
    distractor_edge_max: int = 5
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
    arrow_length_px: int = 12
    arrow_width_px: int = 7
    node_border_width_px: int = 2
    label_font_size_px: int = 20
    node_color_name: str = "blue"


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved support and visual axes for one automaton simulation query."""

    query_id: str
    state_count: int
    input_length: int
    transition_step_count: int | None
    target_state_index: int
    distractor_edge_count: int
    layout_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    query_id_probabilities: Dict[str, float]
    state_count_probabilities: Dict[str, float]
    input_length_probabilities: Dict[str, float]
    transition_step_count_probabilities: Dict[str, float]
    target_state_index_probabilities: Dict[str, float]
    distractor_edge_count_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    edge_routing_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _AutomatonSample:
    """One trace-ready automaton and simulation path."""

    graph_sample: GraphTopologySample
    start_label: str
    accepting_labels: Tuple[str, ...]
    input_string: str
    query_step_count: int
    answer_label: str
    full_state_path_labels: Tuple[str, ...]
    evidence_state_labels: Tuple[str, ...]
    transition_labels_by_edge: Dict[Tuple[str, str], str]
    transition_function: Dict[str, Dict[str, str]]
    used_transition_edges: Tuple[Tuple[str, str], ...]


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
    """Return prompt examples that match ordered state-center evidence."""

    example_evidence = [[150, 250], [310, 190], [480, 230]]
    return (
        json.dumps({"evidence": example_evidence, "answer": "C"}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps({"answer": "C"}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _query_id_from_alias(value: Any) -> str | None:
    """Return the public query id encoded by one query/task alias."""

    text = str(value or "").strip()
    aliases = {
        "final_state": FINAL_STATE_QUERY_ID,
        "final_state_label": FINAL_STATE_QUERY_ID,
        "transition_step_state": STEP_STATE_QUERY_ID,
        "transition_step_state_label": STEP_STATE_QUERY_ID,
        "step_state_label": STEP_STATE_QUERY_ID,
        "automaton_state_simulation": None,
        "default": None,
    }
    return aliases.get(text)



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
    """Resolve one balanced automaton visual/query axis."""

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


def _uniform_probability(values: Sequence[int], *, selected: int | None = None) -> Dict[str, float]:
    """Return a uniform probability map over integer support."""

    return dict(uniform_probability_map(tuple(int(value) for value in values), selected=selected))


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one automaton simulation query."""

    forced_query_id = resolve_forced_graph_query_id(params, query_id_from_alias=_query_id_from_alias)
    if forced_query_id is None:
        query_id, query_id_probabilities = _resolve_named_variant(
            int(instance_seed),
            params=params,
            explicit_key="query_id",
            weights_key="query_id_weights",
            balance_flag_key="balanced_query_id_sampling",
            supported=SUPPORTED_AUTOMATON_QUERY_IDS,
            namespace="query_id",
        )
    else:
        query_id = str(forced_query_id)
        query_id_probabilities = {
            str(supported_query_id): (1.0 if str(supported_query_id) == str(query_id) else 0.0)
            for supported_query_id in SUPPORTED_AUTOMATON_QUERY_IDS
        }

    state_count_min = int(params.get("state_count_min", group_default(_GEN_DEFAULTS, "state_count_min", _DEFAULTS.state_count_min)))
    state_count_max = int(params.get("state_count_max", group_default(_GEN_DEFAULTS, "state_count_max", _DEFAULTS.state_count_max)))
    state_count_support = tuple(int(value) for value in range(max(3, int(state_count_min)), int(state_count_max) + 1))
    if not state_count_support:
        raise ValueError("no feasible state_count support exists for automaton simulation")
    explicit_state_count = params.get("state_count")
    if explicit_state_count is not None:
        state_count = int(explicit_state_count)
        if int(state_count) not in set(state_count_support):
            raise ValueError("state_count is outside feasible support")
    else:
        state_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:state_count"))
        state_count = int(state_count_support[int(state_index % len(state_count_support))])

    input_length_min = int(params.get("input_length_min", group_default(_GEN_DEFAULTS, "input_length_min", _DEFAULTS.input_length_min)))
    input_length_max = int(params.get("input_length_max", group_default(_GEN_DEFAULTS, "input_length_max", _DEFAULTS.input_length_max)))
    input_length_support = tuple(int(value) for value in range(max(1, int(input_length_min)), int(input_length_max) + 1))
    if not input_length_support:
        raise ValueError("no feasible input_length support exists for automaton simulation")
    explicit_input_length = params.get("input_length")
    if explicit_input_length is not None:
        input_length = int(explicit_input_length)
        if int(input_length) not in set(input_length_support):
            raise ValueError("input_length is outside feasible support")
    else:
        length_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:input_length"))
        input_length = int(input_length_support[int(length_index % len(input_length_support))])

    transition_step_count: int | None = None
    transition_step_probabilities: Dict[str, float] = {}
    if str(query_id) == STEP_STATE_QUERY_ID:
        step_min = int(params.get("transition_step_min", group_default(_GEN_DEFAULTS, "transition_step_min", _DEFAULTS.transition_step_min)))
        step_max = int(params.get("transition_step_max", group_default(_GEN_DEFAULTS, "transition_step_max", _DEFAULTS.transition_step_max)))
        step_support = tuple(int(value) for value in range(max(1, int(step_min)), min(int(step_max), int(input_length)) + 1))
        if not step_support:
            raise ValueError("no feasible transition_step support exists for automaton simulation")
        explicit_step = params.get("transition_step_count")
        if explicit_step is not None:
            transition_step_count = int(explicit_step)
            if int(transition_step_count) not in set(step_support):
                raise ValueError("transition_step_count is outside feasible support")
        else:
            step_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:transition_step"))
            transition_step_count = int(step_support[int(step_index % len(step_support))])
        transition_step_probabilities = _uniform_probability(
            tuple(int(value) for value in step_support),
            selected=int(transition_step_count) if explicit_step is not None else None,
        )

    target_support = tuple(int(value) for value in range(int(state_count)))
    explicit_target = params.get("target_state_index")
    if explicit_target is not None:
        target_state_index = int(explicit_target)
        if int(target_state_index) not in set(target_support):
            raise ValueError("target_state_index is outside feasible support")
    else:
        target_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:target_state_index"))
        # Offset the hash by query branch so both branches do not land on the
        # same state support cycle for the same seed.
        query_offset = SUPPORTED_AUTOMATON_QUERY_IDS.index(str(query_id))
        target_state_index = int((int(target_index) + int(query_offset)) % int(state_count))

    distractor_min = int(params.get("distractor_edge_min", group_default(_GEN_DEFAULTS, "distractor_edge_min", _DEFAULTS.distractor_edge_min)))
    distractor_max = int(params.get("distractor_edge_max", group_default(_GEN_DEFAULTS, "distractor_edge_max", _DEFAULTS.distractor_edge_max)))
    distractor_support = tuple(int(value) for value in range(max(0, int(distractor_min)), max(int(distractor_min), int(distractor_max)) + 1))
    explicit_distractors = params.get("distractor_edge_count")
    if explicit_distractors is not None:
        distractor_edge_count = int(explicit_distractors)
        if int(distractor_edge_count) not in set(distractor_support):
            raise ValueError("distractor_edge_count is outside feasible support")
    else:
        distractor_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:distractor_edge_count"))
        distractor_edge_count = int(distractor_support[int(distractor_index % len(distractor_support))])

    layout_variant, layout_variant_probabilities = _resolve_named_variant(
        int(instance_seed),
        params=params,
        explicit_key="layout_variant",
        weights_key="layout_variant_weights",
        balance_flag_key="balanced_layout_variant_sampling",
        supported=SUPPORTED_AUTOMATON_LAYOUT_VARIANTS,
        namespace="layout_variant",
    )
    layout_transform_variant, layout_transform_variant_probabilities = _resolve_named_variant(
        int(instance_seed),
        params=params,
        explicit_key="layout_transform_variant",
        weights_key="layout_transform_variant_weights",
        balance_flag_key="balanced_layout_transform_variant_sampling",
        supported=("identity", "mirror_left_right", "mirror_up_down"),
        namespace="layout_transform_variant",
    )
    edge_routing_variant, edge_routing_variant_probabilities = _resolve_named_variant(
        int(instance_seed),
        params=params,
        explicit_key="edge_routing_variant",
        weights_key="edge_routing_variant_weights",
        balance_flag_key="balanced_edge_routing_variant_sampling",
        supported=("straight", "mixed_arc"),
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
        state_count=int(state_count),
        input_length=int(input_length),
        transition_step_count=int(transition_step_count) if transition_step_count is not None else None,
        target_state_index=int(target_state_index),
        distractor_edge_count=int(distractor_edge_count),
        layout_variant=str(layout_variant),
        layout_transform_variant=str(layout_transform_variant),
        edge_routing_variant=str(edge_routing_variant),
        node_color_name=str(node_color_name),
        query_id_probabilities=dict(query_id_probabilities),
        state_count_probabilities=_uniform_probability(
            state_count_support,
            selected=int(state_count) if explicit_state_count is not None else None,
        ),
        input_length_probabilities=_uniform_probability(
            input_length_support,
            selected=int(input_length) if explicit_input_length is not None else None,
        ),
        transition_step_count_probabilities=dict(transition_step_probabilities),
        target_state_index_probabilities=_uniform_probability(
            target_support,
            selected=int(target_state_index) if explicit_target is not None else None,
        ),
        distractor_edge_count_probabilities=_uniform_probability(
            distractor_support,
            selected=int(distractor_edge_count) if explicit_distractors is not None else None,
        ),
        layout_variant_probabilities=dict(layout_variant_probabilities),
        layout_transform_variant_probabilities=dict(layout_transform_variant_probabilities),
        edge_routing_variant_probabilities=dict(edge_routing_variant_probabilities),
        node_color_name_probabilities=dict(node_color_name_probabilities),
    )


def _state_labels(state_count: int) -> Tuple[str, ...]:
    """Return compact automaton state labels."""

    return tuple(chr(ord("A") + int(index)) for index in range(int(state_count)))


def _sorted_label_tuple(values: Sequence[str]) -> Tuple[str, ...]:
    """Sort state labels with graph label ordering."""

    return tuple(sorted((str(value) for value in values), key=graph_label_sort_key))


def _build_topology_sample(
    *,
    graph: nx.DiGraph,
    labels: Sequence[str],
    transition_labels_by_edge: Mapping[Tuple[str, str], str],
) -> GraphTopologySample:
    """Build the generic graph topology record for one automaton diagram."""

    label_by_node = {int(node): str(labels[int(node)]) for node in graph.nodes()}
    edge_labels = tuple(
        sorted(
            ((str(label_by_node[int(left)]), str(label_by_node[int(right)])) for left, right in graph.edges()),
            key=lambda pair: (graph_label_sort_key(pair[0]), graph_label_sort_key(pair[1])),
        )
    )
    adjacency_by_label = {
        str(label_by_node[int(node)]): _sorted_label_tuple(
            {
                *[str(label_by_node[int(neighbor)]) for neighbor in graph.predecessors(int(node))],
                *[str(label_by_node[int(neighbor)]) for neighbor in graph.successors(int(node))],
            }
        )
        for node in graph.nodes()
    }
    successors_by_label = {
        str(label_by_node[int(node)]): _sorted_label_tuple(str(label_by_node[int(neighbor)]) for neighbor in graph.successors(int(node)))
        for node in graph.nodes()
    }
    predecessors_by_label = {
        str(label_by_node[int(node)]): _sorted_label_tuple(str(label_by_node[int(neighbor)]) for neighbor in graph.predecessors(int(node)))
        for node in graph.nodes()
    }
    degrees_by_label = {
        str(label_by_node[int(node)]): int(graph.in_degree(int(node)) + graph.out_degree(int(node)))
        for node in graph.nodes()
    }
    return GraphTopologySample(
        graph=graph,
        directed=True,
        node_labels=tuple(str(label_by_node[int(node)]) for node in graph.nodes()),
        edge_labels=tuple((str(left), str(right)) for left, right in edge_labels),
        degrees_by_label={str(key): int(value) for key, value in degrees_by_label.items()},
        in_degrees_by_label={str(label_by_node[int(node)]): int(graph.in_degree(int(node))) for node in graph.nodes()},
        out_degrees_by_label={str(label_by_node[int(node)]): int(graph.out_degree(int(node))) for node in graph.nodes()},
        adjacency_by_label={str(key): tuple(str(value) for value in values) for key, values in adjacency_by_label.items()},
        successors_by_label={str(key): tuple(str(value) for value in values) for key, values in successors_by_label.items()},
        predecessors_by_label={str(key): tuple(str(value) for value in values) for key, values in predecessors_by_label.items()},
        edge_count=int(graph.number_of_edges()),
        topology_profile="automaton_partial_dfa",
        label_variant="automaton_state",
    )


def _path_is_consistent(path: Sequence[int], input_symbols: Sequence[str]) -> bool:
    """Return whether a path can be represented by a deterministic transition table."""

    transition_by_key: Dict[Tuple[int, str], int] = {}
    target_by_state: Dict[int, set[int]] = {}
    for source, symbol, target in zip(path[:-1], input_symbols, path[1:]):
        source_i = int(source)
        target_i = int(target)
        if int(source_i) == int(target_i):
            return False
        key = (int(source_i), str(symbol))
        existing = transition_by_key.get(key)
        if existing is not None and int(existing) != int(target_i):
            return False
        target_set = target_by_state.setdefault(int(source_i), set())
        if int(target_i) in target_set and key not in transition_by_key:
            return False
        transition_by_key[key] = int(target_i)
        target_set.add(int(target_i))
    return True


def _sample_state_path(
    rng: random.Random,
    *,
    state_count: int,
    input_symbols: Sequence[str],
    answer_position: int,
    target_state_index: int,
) -> Tuple[int, ...]:
    """Sample a state path whose queried position is the requested answer state."""

    length = len(tuple(input_symbols))
    for _ in range(1000):
        path = [0]
        for position in range(1, int(length) + 1):
            if int(position) == int(answer_position):
                next_state = int(target_state_index)
            else:
                candidates = [int(value) for value in range(int(state_count)) if int(value) != int(path[-1])]
                next_state = int(rng.choice(candidates))
            path.append(int(next_state))
        if _path_is_consistent(path, input_symbols):
            return tuple(int(value) for value in path)
    raise ValueError("failed to sample a deterministic automaton path")


def _sample_transitions(
    rng: random.Random,
    *,
    state_count: int,
    input_symbols: Sequence[str],
    path: Sequence[int],
    distractor_edge_count: int,
) -> Dict[Tuple[int, str], int]:
    """Build required path transitions plus deterministic distractor transitions."""

    transitions: Dict[Tuple[int, str], int] = {}
    targets_by_state: Dict[int, set[int]] = {int(state): set() for state in range(int(state_count))}
    for source, symbol, target in zip(path[:-1], input_symbols, path[1:]):
        source_i = int(source)
        target_i = int(target)
        key = (int(source_i), str(symbol))
        existing = transitions.get(key)
        if existing is not None and int(existing) != int(target_i):
            raise ValueError("path transition conflict")
        transitions[key] = int(target_i)
        targets_by_state.setdefault(int(source_i), set()).add(int(target_i))

    candidates: list[Tuple[int, str]] = [
        (int(state), str(symbol))
        for state in range(int(state_count))
        for symbol in AUTOMATON_SYMBOLS
        if (int(state), str(symbol)) not in transitions
    ]
    rng.shuffle(candidates)
    added = 0
    for state, symbol in candidates:
        if int(added) >= int(distractor_edge_count):
            break
        used_targets = targets_by_state.setdefault(int(state), set())
        target_candidates = [
            int(value)
            for value in range(int(state_count))
            if int(value) != int(state) and int(value) not in used_targets
        ]
        if not target_candidates:
            continue
        target = int(rng.choice(target_candidates))
        transitions[(int(state), str(symbol))] = int(target)
        used_targets.add(int(target))
        added += 1
    return dict(transitions)


def _sample_automaton(
    rng: random.Random,
    *,
    query: _ResolvedQuery,
) -> _AutomatonSample:
    """Construct one deterministic state-transition diagram and simulation trace."""

    labels = _state_labels(int(query.state_count))
    answer_position = int(query.input_length if str(query.query_id) == FINAL_STATE_QUERY_ID else int(query.transition_step_count or 1))
    input_symbols = tuple(str(rng.choice(AUTOMATON_SYMBOLS)) for _ in range(int(query.input_length)))
    path = _sample_state_path(
        rng,
        state_count=int(query.state_count),
        input_symbols=input_symbols,
        answer_position=int(answer_position),
        target_state_index=int(query.target_state_index),
    )
    transitions = _sample_transitions(
        rng,
        state_count=int(query.state_count),
        input_symbols=input_symbols,
        path=path,
        distractor_edge_count=int(query.distractor_edge_count),
    )
    graph = nx.DiGraph()
    graph.add_nodes_from(range(int(query.state_count)))
    for (source, _symbol), target in sorted(transitions.items()):
        graph.add_edge(int(source), int(target))

    transition_labels_by_edge: Dict[Tuple[str, str], str] = {}
    transition_function: Dict[str, Dict[str, str]] = {str(label): {} for label in labels}
    for (source, symbol), target in sorted(transitions.items()):
        source_label = str(labels[int(source)])
        target_label = str(labels[int(target)])
        transition_labels_by_edge[(source_label, target_label)] = str(symbol)
        transition_function[str(source_label)][str(symbol)] = str(target_label)

    accepting_count = int(rng.randint(1, min(2, int(query.state_count))))
    accepting_indices = set(rng.sample(range(int(query.state_count)), k=int(accepting_count)))
    if rng.random() < 0.50:
        accepting_indices.add(int(path[-1]))
    accepting_labels = _sorted_label_tuple(str(labels[int(index)]) for index in accepting_indices)
    graph_sample = _build_topology_sample(
        graph=graph,
        labels=labels,
        transition_labels_by_edge=transition_labels_by_edge,
    )
    full_path_labels = tuple(str(labels[int(index)]) for index in path)
    evidence_labels = tuple(str(label) for label in full_path_labels[: int(answer_position) + 1])
    used_edges = tuple(
        (str(labels[int(source)]), str(labels[int(target)]))
        for source, target in zip(path[:-1], path[1:])
    )
    return _AutomatonSample(
        graph_sample=graph_sample,
        start_label=str(labels[0]),
        accepting_labels=tuple(str(label) for label in accepting_labels),
        input_string="".join(str(symbol) for symbol in input_symbols),
        query_step_count=int(answer_position),
        answer_label=str(full_path_labels[int(answer_position)]),
        full_state_path_labels=tuple(str(label) for label in full_path_labels),
        evidence_state_labels=tuple(str(label) for label in evidence_labels),
        transition_labels_by_edge={(str(left), str(right)): str(symbol) for (left, right), symbol in transition_labels_by_edge.items()},
        transition_function={str(key): {str(symbol): str(target) for symbol, target in value.items()} for key, value in transition_function.items()},
        used_transition_edges=tuple((str(left), str(right)) for left, right in used_edges[: int(answer_position)]),
    )


def _draw_arrowhead(draw: ImageDraw.ImageDraw, *, start: Tuple[int, int], end: Tuple[int, int], color: Tuple[int, int, int]) -> None:
    """Draw a compact triangular arrowhead at ``end`` pointing from ``start``."""

    dx = float(end[0] - start[0])
    dy = float(end[1] - start[1])
    length = max(1.0, math.hypot(dx, dy))
    ux = dx / length
    uy = dy / length
    px = -uy
    py = ux
    size = 11.0
    back_x = float(end[0]) - (ux * size)
    back_y = float(end[1]) - (uy * size)
    points = [
        (int(round(end[0])), int(round(end[1]))),
        (int(round(back_x + px * size * 0.48)), int(round(back_y + py * size * 0.48))),
        (int(round(back_x - px * size * 0.48)), int(round(back_y - py * size * 0.48))),
    ]
    draw.polygon(points, fill=tuple(int(value) for value in color))


def _decorate_automaton_scene(
    rendered_scene: RenderedGraphScene,
    *,
    start_label: str,
    accepting_labels: Sequence[str],
    render_params: GraphRenderParams,
) -> None:
    """Add automaton-specific start and accepting-state glyphs to a rendered graph."""

    draw = ImageDraw.Draw(rendered_scene.image)
    node_by_label = {str(node.label): node for node in rendered_scene.nodes}
    ink = tuple(int(value) for value in render_params.title_color_rgb)
    radius = int(render_params.node_radius_px)
    for label in accepting_labels:
        node = node_by_label.get(str(label))
        if node is None:
            continue
        x0, y0, x1, y1 = (int(value) for value in node.bbox_xyxy)
        inset = max(4, int(round(float(radius) * 0.22)))
        draw.ellipse((x0 + inset, y0 + inset, x1 - inset, y1 - inset), outline=ink, width=2)

    start_node = node_by_label.get(str(start_label))
    if start_node is None:
        return
    cx, cy = (int(value) for value in start_node.center_xy)
    content = tuple(int(value) for value in rendered_scene.panel_geometry.get("scene_content_xyxy", (0, 0, rendered_scene.image.width, rendered_scene.image.height)))
    if cx - content[0] >= 92:
        start = (int(max(content[0] + 12, cx - 82)), int(cy))
        end = (int(cx - radius - 6), int(cy))
        text_xy = (int(start[0]), int(cy - 26))
    else:
        start = (int(cx), int(max(content[1] + 12, cy - 82)))
        end = (int(cx), int(cy - radius - 6))
        text_xy = (int(cx + 12), int(start[1]))
    draw.line((start, end), fill=ink, width=3)
    _draw_arrowhead(draw, start=start, end=end, color=ink)
    font = load_font(14, bold=True)
    draw.text(text_xy, "start", fill=ink, font=font)


def _edge_label_bbox_entries(rendered_scene: RenderedGraphScene, edges: Sequence[Tuple[str, str]]) -> Tuple[list[list[int]], Dict[str, list[list[int]]]]:
    """Return transition-label bboxes for each used edge and all used-edge occurrences."""

    all_by_edge: Dict[str, list[list[int]]] = {}
    occurrence_bboxes: list[list[int]] = []
    for left, right in edges:
        projection = projected_edge_label_bbox_evidence(rendered_scene, (str(left), str(right)))
        boxes = [[int(round(float(value))) for value in bbox] for bbox in projection.get("bbox_set", [])]
        all_by_edge[f"{str(left)}->{str(right)}"] = list(boxes)
        if boxes:
            occurrence_bboxes.append(list(boxes[0]))
    return occurrence_bboxes, dict(all_by_edge)


def _build_complexity(
    *,
    query: _ResolvedQuery,
    automaton: _AutomatonSample,
    render_params: GraphRenderParams,
    rendered_scene: RenderedGraphScene,
) -> Any:
    """Build one within-task normalized complexity record."""

    state_count = int(query.state_count)
    edge_count = int(automaton.graph_sample.edge_count)
    path_steps = int(automaton.query_step_count)
    crossing_norm = normalize_float_with_bounds(float(rendered_scene.crossing_count), (0.0, max(1.0, float(edge_count))))
    components = {
        "visual_scan": (0.45 * normalize_int_with_bounds(int(edge_count), (max(2, state_count - 1), max(3, state_count * 2))))
        + (0.35 * normalize_int_with_bounds(int(state_count), (_DEFAULTS.state_count_min, _DEFAULTS.state_count_max)))
        + (0.20 * normalize_int_with_bounds(int(path_steps), (_DEFAULTS.transition_step_min, _DEFAULTS.input_length_max))),
        "topology_reasoning": 0.25
        + (0.55 * normalize_int_with_bounds(int(path_steps), (1, _DEFAULTS.input_length_max)))
        + (0.20 if str(query.query_id) == STEP_STATE_QUERY_ID else 0.0),
        "ambiguity": (0.45 * normalize_int_with_bounds(int(edge_count), (3, max(4, state_count * 2))))
        + (0.35 * normalize_int_with_bounds(int(len(automaton.accepting_labels)), (1, 3)))
        + (0.20 * normalize_int_with_bounds(int(state_count), (_DEFAULTS.state_count_min, _DEFAULTS.state_count_max))),
        "clutter": (0.60 * normalize_int_with_bounds(int(edge_count), (3, max(4, state_count * 2))))
        + (0.25 * crossing_norm)
        + (0.15 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px))),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


@register_task
class GraphRelationAutomatonStateSimulationLabelTask:
    """Simulate a state-transition diagram and answer the reached state label."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic automaton simulation instance."""

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
        graph_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.graph")
        last_error: Exception | None = None
        automaton = None
        rendered_scene = None
        image = None
        background_meta = {}
        post_noise_meta = {}
        transition_bbox_entries: list[list[int]] = []
        used_transition_bbox_by_edge: Dict[str, list[list[int]]] = {}
        for attempt in range(max(1, int(max_attempts))):
            try:
                automaton = _sample_automaton(graph_rng, query=query)
                background, background_meta = make_background_canvas(
                    canvas_width=int(render_params.canvas_width),
                    canvas_height=int(render_params.canvas_height),
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
                )
                node_style_by_label = {
                    str(automaton.start_label): {
                        "halo_rgb": tuple(int(value) for value in render_params.title_color_rgb),
                        "halo_width_px": 3,
                        "halo_pad_px": 6,
                    }
                }
                rendered_scene = render_graph_scene(
                    graph_sample=automaton.graph_sample,
                    layout_variant=str(query.layout_variant),
                    layout_transform_variant=str(query.layout_transform_variant),
                    render_params=render_params,
                    layout_seed=int(instance_seed + attempt),
                    scene_title="State Transition Diagram",
                    directed=True,
                    base_image=background,
                    edge_text_labels_by_label=automaton.transition_labels_by_edge,
                    edge_text_label_font_size_px=max(15, int(render_params.label_font_size_px) - 3),
                    node_style_by_label=node_style_by_label,
                    layout_fallback_variants=("circular", "shell", "layered", "spring"),
                )
                _decorate_automaton_scene(
                    rendered_scene,
                    start_label=str(automaton.start_label),
                    accepting_labels=tuple(str(label) for label in automaton.accepting_labels),
                    render_params=render_params,
                )
                transition_bbox_entries, used_transition_bbox_by_edge = _edge_label_bbox_entries(
                    rendered_scene,
                    automaton.used_transition_edges,
                )
                if len(transition_bbox_entries) != len(automaton.used_transition_edges):
                    raise ValueError("not all used transition-label bboxes were rendered")
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
            raise RuntimeError("failed to generate automaton state-simulation instance") from last_error
        if automaton is None or rendered_scene is None or image is None:
            raise RuntimeError("failed to generate automaton state-simulation instance")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_json_example, prompt_json_example_answer_only = _build_prompt_json_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "input_string": str(automaton.input_string),
                "transition_step_count": str(automaton.query_step_count),
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

        evidence_projection = projected_node_point_evidence(rendered_scene, automaton.evidence_state_labels)
        evidence_path = [[int(round(float(point[0]))), int(round(float(point[1])))] for point in evidence_projection["pixel_point_sequence"]]
        if len(evidence_path) != len(automaton.evidence_state_labels):
            raise RuntimeError("automaton evidence path projection is incomplete")
        answer_gt = TypedValue(type="string", value=str(automaton.answer_label))
        evidence_gt = TypedValue(type="point_sequence", value=list(evidence_path))
        answer_label = str(automaton.answer_label)
        path_label_set = set(str(label) for label in automaton.evidence_state_labels)
        edge_usage_counts: Dict[str, int] = {}
        for left, right in automaton.used_transition_edges:
            key = f"{str(left)}->{str(right)}"
            edge_usage_counts[key] = int(edge_usage_counts.get(key, 0)) + 1

        node_entities = [
            {
                "entity_id": f"state_{node.label}",
                "entity_kind": "automaton_state",
                "label": str(node.label),
                "is_start_state": bool(str(node.label) == str(automaton.start_label)),
                "is_accepting_state": bool(str(node.label) in set(automaton.accepting_labels)),
                "is_answer_state": bool(str(node.label) == str(answer_label)),
                "is_in_evidence_path": bool(str(node.label) in path_label_set),
                "path_positions": [int(index) for index, label in enumerate(automaton.evidence_state_labels) if str(label) == str(node.label)],
                "center_px": list(node.center_xy),
                "bbox_xyxy": list(node.bbox_xyxy),
                "successors": list(automaton.graph_sample.successors_by_label[str(node.label)]),
                "predecessors": list(automaton.graph_sample.predecessors_by_label[str(node.label)]),
            }
            for node in rendered_scene.nodes
        ]
        edge_entities = [
            {
                "entity_id": str(edge.edge_id),
                "entity_kind": "automaton_transition",
                "source_state_label": str(edge.node_u_label),
                "target_state_label": str(edge.node_v_label),
                "transition_symbol": str(automaton.transition_labels_by_edge[(str(edge.node_u_label), str(edge.node_v_label))]),
                "is_used_transition": bool(edge_usage_counts.get(f"{str(edge.node_u_label)}->{str(edge.node_v_label)}", 0) > 0),
                "used_transition_count": int(edge_usage_counts.get(f"{str(edge.node_u_label)}->{str(edge.node_v_label)}", 0)),
                "segment_px": [list(edge.segment_px[0]), list(edge.segment_px[1])],
                "route_variant": str(edge.route_variant),
                "control_px": list(edge.control_px) if edge.control_px is not None else None,
                "edge_label_bbox_xyxy": list(edge.edge_label_bbox_xyxy) if edge.edge_label_bbox_xyxy is not None else None,
            }
            for edge in rendered_scene.edges
        ]
        transition_entries = [
            {
                "source_state": str(left),
                "target_state": str(right),
                "symbol": str(symbol),
            }
            for (left, right), symbol in automaton.transition_labels_by_edge.items()
        ]
        complexity = _build_complexity(
            query=query,
            automaton=automaton,
            render_params=render_params,
            rendered_scene=rendered_scene,
        )

        trace_payload = {
            "scene_ir": {
                "scene_kind": "automaton_state_transition_simulation",
                "entities": [*node_entities, *edge_entities],
                "relations": {
                    "query_id": str(query.query_id),
                    "simulation_rule": "start_at_start_state_and_follow_one_visible_transition_label_per_input_symbol",
                    "input_string": str(automaton.input_string),
                    "start_state_label": str(automaton.start_label),
                    "accepting_state_labels": list(automaton.accepting_labels),
                    "answer_state_label": str(automaton.answer_label),
                    "query_step_count": int(automaton.query_step_count),
                    "full_state_path_labels": list(automaton.full_state_path_labels),
                    "evidence_state_path_labels": list(automaton.evidence_state_labels),
                    "used_transition_edges": [list(edge) for edge in automaton.used_transition_edges],
                    "transition_function": dict(automaton.transition_function),
                    "transition_labels_by_edge": list(transition_entries),
                    "query_id_probabilities": dict(query.query_id_probabilities),
                    "state_count_probabilities": dict(query.state_count_probabilities),
                    "input_length_probabilities": dict(query.input_length_probabilities),
                    "transition_step_count_probabilities": dict(query.transition_step_count_probabilities),
                    "target_state_index_probabilities": dict(query.target_state_index_probabilities),
                    "distractor_edge_count_probabilities": dict(query.distractor_edge_count_probabilities),
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
                    "state_count": int(query.state_count),
                    "state_count_probabilities": dict(query.state_count_probabilities),
                    "input_length": int(query.input_length),
                    "input_length_probabilities": dict(query.input_length_probabilities),
                    "transition_step_count": int(automaton.query_step_count),
                    "transition_step_count_probabilities": dict(query.transition_step_count_probabilities),
                    "target_state_index": int(query.target_state_index),
                    "target_state_index_probabilities": dict(query.target_state_index_probabilities),
                    "distractor_edge_count": int(query.distractor_edge_count),
                    "distractor_edge_count_probabilities": dict(query.distractor_edge_count_probabilities),
                    "input_string": str(automaton.input_string),
                    "answer_state_label": str(automaton.answer_label),
                    "start_state_label": str(automaton.start_label),
                    "accepting_state_labels": list(automaton.accepting_labels),
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
                    "automaton_accepting_state_glyph": "double_inner_ring",
                    "automaton_start_state_glyph": "incoming_start_arrow",
                    "transition_labels_by_edge": list(transition_entries),
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
                "question_format": str(query.query_id),
                "state_count": int(query.state_count),
                "edge_count": int(automaton.graph_sample.edge_count),
                "input_length": int(query.input_length),
                "input_string": str(automaton.input_string),
                "transition_step_count": int(automaton.query_step_count),
                "answer": str(automaton.answer_label),
                "answer_state_label": str(automaton.answer_label),
                "start_state_label": str(automaton.start_label),
                "accepting_state_labels": list(automaton.accepting_labels),
                "full_state_path_labels": list(automaton.full_state_path_labels),
                "evidence_state_path_labels": list(automaton.evidence_state_labels),
                "used_transition_edges": [list(edge) for edge in automaton.used_transition_edges],
                "transition_function": dict(automaton.transition_function),
                "transition_labels_by_edge": list(transition_entries),
                "used_transition_label_bboxes": list(transition_bbox_entries),
                "used_transition_bbox_by_edge": dict(used_transition_bbox_by_edge),
                "target_state_index": int(query.target_state_index),
                "target_state_index_probabilities": dict(query.target_state_index_probabilities),
                "state_count_probabilities": dict(query.state_count_probabilities),
                "input_length_probabilities": dict(query.input_length_probabilities),
                "transition_step_count_probabilities": dict(query.transition_step_count_probabilities),
                "distractor_edge_count": int(query.distractor_edge_count),
                "distractor_edge_count_probabilities": dict(query.distractor_edge_count_probabilities),
                "layout_variant_requested": str(query.layout_variant),
                "layout_variant_used": str(rendered_scene.layout_variant),
                "layout_transform_variant": str(rendered_scene.layout_transform_variant),
                "edge_routing_variant": str(rendered_scene.edge_routing_variant),
                "node_color_name": str(query.node_color_name),
                "crossing_count": int(rendered_scene.crossing_count),
            },
            "witness_symbolic": {
                "type": "state_path",
                "state_path_labels": list(automaton.evidence_state_labels),
                "answer_state_label": str(automaton.answer_label),
            },
            "projected_evidence": {
                "type": "point_sequence",
                "point_sequence": list(evidence_path),
                "pixel_point_sequence": list(evidence_path),
                "pixel_bbox_set": list(evidence_projection["pixel_bbox_set"]),
                "used_transition_label_bboxes": list(transition_bbox_entries),
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


__all__ = ["GraphRelationAutomatonStateSimulationLabelTask"]
