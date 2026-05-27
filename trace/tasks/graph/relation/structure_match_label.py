"""Labeled graph structure matching option task."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import round_bbox as _round_bbox
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.mcq import option_label_for_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import fit_font_to_box, load_font
from ..shared.complexity import (
    build_graph_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.style import build_graph_named_color_theme, apply_graph_panel_style
from ..shared.task_support import resolve_graph_named_variant
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults
from ....core.visual.background import make_background_canvas


TASK_ID = "task_graph__graph_options__structure_match_label"
SCENE_ID = "graph_options"

SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "same_structure_label",
    "contained_subgraph_label",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "clean_graph_options",
    "colored_node_graph_options",
    "notebook_graph_options",
)
SUPPORTED_EDGE_MODES: Tuple[str, ...] = ("undirected", "directed")
_QUERY_LOAD = {
    "same_structure_label": 0.50,
    "contained_subgraph_label": 0.64,
}
_SCENE_LOAD = {
    "clean_graph_options": 0.18,
    "colored_node_graph_options": 0.22,
    "notebook_graph_options": 0.28,
}
_LABEL_POOL: Tuple[str, ...] = tuple("ABCDEFGHJKLMNPQRSTUVXYZ")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for graph structure matching."""

    option_count: int = 6
    same_structure_node_count_min: int = 4
    same_structure_node_count_max: int = 6
    node_count_min: int = 5
    node_count_max: int = 7
    extra_edge_min: int = 1
    extra_edge_max: int = 3
    subgraph_node_count_min: int = 3
    subgraph_node_count_max: int = 4


@dataclass(frozen=True)
class _RenderParams:
    """Resolved render constants for the structure-diagram scene."""

    canvas_width: int = 1260
    canvas_height: int = 920
    margin_x_px: int = 66
    margin_top_px: int = 46
    reference_panel_height_px: int = 300
    reference_to_options_gap_px: int = 34
    option_gap_px: int = 26
    option_row_gap_px: int = 24
    panel_padding_px: int = 24
    panel_corner_radius_px: int = 24
    border_width_px: int = 3
    title_font_size_px: int = 28
    option_label_font_size_px: int = 30
    node_radius_px: int = 22
    edge_width_px: int = 5
    panel_fill_rgb: Tuple[int, int, int] = (250, 251, 254)
    option_fill_rgb: Tuple[int, int, int] = (255, 255, 255)
    border_rgb: Tuple[int, int, int] = (86, 96, 112)
    edge_rgb: Tuple[int, int, int] = (72, 82, 98)
    node_fill_rgb: Tuple[int, int, int] = (246, 248, 252)
    node_outline_rgb: Tuple[int, int, int] = (63, 76, 94)
    text_rgb: Tuple[int, int, int] = (30, 34, 42)
    text_stroke_rgb: Tuple[int, int, int] = (255, 255, 255)
    notebook_line_rgb: Tuple[int, int, int] = (218, 225, 235)


_DEFAULTS = _TaskDefaults()
_RENDER_FALLBACKS = _RenderParams()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="relation", apply_prob=0.5)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="relation")


def _project_bbox_evidence(bbox_map: Mapping[str, Sequence[float]], entity_ids: Sequence[str]) -> Dict[str, Any]:
    bbox_set = []
    for entity_id in entity_ids:
        if str(entity_id) not in bbox_map:
            raise ValueError(f"missing bbox for evidence entity {entity_id}")
        bbox_set.append([round(float(value), 3) for value in bbox_map[str(entity_id)]])
    return {"bbox_set": bbox_set, "pixel_bbox_set": [list(bbox) for bbox in bbox_set]}


def _edge_key(u_label: str, v_label: str, *, directed: bool = False) -> Tuple[str, str]:
    u, v = str(u_label), str(v_label)
    if u == v:
        raise ValueError("self edges are not supported")
    if directed:
        return (u, v)
    a, b = sorted((u, v))
    return (a, b)


def _is_directed(spec: Mapping[str, Any]) -> bool:
    return bool(spec.get("directed", False))


def _canonical_spec(spec: Mapping[str, Any]) -> str:
    labels = tuple(sorted(str(label) for label in spec["labels"]))
    directed = _is_directed(spec)
    edges = tuple(sorted(_edge_key(str(edge[0]), str(edge[1]), directed=directed) for edge in spec["edges"]))
    return json.dumps({"directed": directed, "labels": labels, "edges": edges}, sort_keys=True, separators=(",", ":"))


def _edge_set(spec: Mapping[str, Any]) -> set[Tuple[str, str]]:
    directed = _is_directed(spec)
    return {_edge_key(str(edge[0]), str(edge[1]), directed=directed) for edge in spec["edges"]}


def _spec_from(labels: Sequence[str], edges: Sequence[Sequence[str]], *, directed: bool = False) -> Dict[str, Any]:
    label_list = [str(label) for label in labels]
    edge_spec = {"labels": label_list, "edges": edges, "directed": bool(directed)}
    return {
        "labels": list(label_list),
        "edges": [list(edge) for edge in sorted(_edge_set(edge_spec))],
        "directed": bool(directed),
    }


def _all_label_pairs(labels: Sequence[str], *, directed: bool = False) -> List[Tuple[str, str]]:
    label_list = [str(label) for label in labels]
    if directed:
        return [
            _edge_key(source, target, directed=True)
            for source in label_list
            for target in label_list
            if source != target
        ]
    return [
        _edge_key(label_list[i], label_list[j])
        for i in range(len(label_list))
        for j in range(i + 1, len(label_list))
    ]


def _is_connected(labels: Sequence[str], edges: Sequence[Sequence[str]]) -> bool:
    label_list = [str(label) for label in labels]
    if not label_list:
        return False
    adjacency = {label: set() for label in label_list}
    for u_label, v_label in edges:
        u, v = str(u_label), str(v_label)
        if u in adjacency and v in adjacency:
            adjacency[u].add(v)
            adjacency[v].add(u)
    seen = {label_list[0]}
    stack = [label_list[0]]
    while stack:
        current = stack.pop()
        for neighbor in sorted(adjacency[current]):
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return len(seen) == len(label_list)


def _make_connected_spec(
    rng,
    *,
    node_count: int,
    extra_edge_min: int,
    extra_edge_max: int,
    directed: bool,
) -> Dict[str, Any]:
    labels = list(_LABEL_POOL[:])
    rng.shuffle(labels)
    labels = sorted(labels[: int(node_count)])
    path_order = list(labels)
    rng.shuffle(path_order)
    edges: set[Tuple[str, str]] = set()
    for index in range(len(path_order) - 1):
        source, target = path_order[index], path_order[index + 1]
        if bool(directed) and bool(rng.randrange(2)):
            source, target = target, source
        edges.add(_edge_key(source, target, directed=bool(directed)))

    available = [pair for pair in _all_label_pairs(labels, directed=bool(directed)) if pair not in edges]
    rng.shuffle(available)
    max_extra = min(int(extra_edge_max), len(available))
    min_extra = min(int(extra_edge_min), max_extra)
    extra_count = int(rng.randint(int(min_extra), int(max_extra))) if max_extra >= min_extra else 0
    for pair in available[:extra_count]:
        edges.add(pair)
    return _spec_from(labels, sorted(edges), directed=bool(directed))


def _mutate_edges(
    rng,
    spec: Mapping[str, Any],
    *,
    toggle_count: int,
    require_connected: bool = True,
) -> Dict[str, Any]:
    labels = [str(label) for label in spec["labels"]]
    directed = _is_directed(spec)
    base_edges = _edge_set(spec)
    for _ in range(160):
        edges = set(base_edges)
        candidates = list(_all_label_pairs(labels, directed=directed))
        rng.shuffle(candidates)
        toggled = 0
        for pair in candidates:
            if toggled >= int(toggle_count):
                break
            if pair in edges:
                if len(edges) <= len(labels) - 1:
                    continue
                edges.remove(pair)
                if require_connected and not _is_connected(labels, sorted(edges)):
                    edges.add(pair)
                    continue
            else:
                edges.add(pair)
            toggled += 1
        if toggled == int(toggle_count):
            candidate = _spec_from(labels, sorted(edges), directed=directed)
            if _canonical_spec(candidate) != _canonical_spec(spec):
                return candidate
    raise ValueError("failed to mutate structure edges")


def _swap_two_labels(rng, spec: Mapping[str, Any]) -> Dict[str, Any]:
    labels = [str(label) for label in spec["labels"]]
    directed = _is_directed(spec)
    if len(labels) < 2:
        raise ValueError("need at least two labels to swap")
    a_idx, b_idx = rng.sample(range(len(labels)), 2)
    swapped = list(labels)
    swapped[a_idx], swapped[b_idx] = swapped[b_idx], swapped[a_idx]
    mapping = {old: new for old, new in zip(labels, swapped)}
    edges = [_edge_key(mapping[str(edge[0])], mapping[str(edge[1])], directed=directed) for edge in spec["edges"]]
    return _spec_from(sorted(swapped), edges, directed=directed)


def _edge_symmetric_difference_count(left: Mapping[str, Any], right: Mapping[str, Any]) -> int:
    if set(str(label) for label in left["labels"]) != set(str(label) for label in right["labels"]):
        return 10_000
    return len(_edge_set(left).symmetric_difference(_edge_set(right)))


def _contains_pattern(pattern: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    if _is_directed(pattern) != _is_directed(candidate):
        return False
    pattern_labels = set(str(label) for label in pattern["labels"])
    candidate_labels = set(str(label) for label in candidate["labels"])
    if not pattern_labels.issubset(candidate_labels):
        return False
    return _edge_set(pattern).issubset(_edge_set(candidate))


def _sample_connected_label_subset(rng, spec: Mapping[str, Any], *, subset_size: int) -> List[str]:
    labels = [str(label) for label in spec["labels"]]
    adjacency = {label: set() for label in labels}
    for u_label, v_label in spec["edges"]:
        adjacency[str(u_label)].add(str(v_label))
        adjacency[str(v_label)].add(str(u_label))
    for _ in range(100):
        start = str(rng.choice(labels))
        subset = [start]
        frontier = list(adjacency[start])
        while len(subset) < int(subset_size) and frontier:
            rng.shuffle(frontier)
            candidate = str(frontier.pop())
            if candidate in subset:
                continue
            subset.append(candidate)
            frontier.extend(sorted(adjacency[candidate] - set(subset)))
        if len(subset) == int(subset_size):
            return sorted(subset)
    return sorted(labels[: int(subset_size)])


def _subspec_from_labels(spec: Mapping[str, Any], labels: Sequence[str]) -> Dict[str, Any]:
    subset = set(str(label) for label in labels)
    edges = [
        _edge_key(str(edge[0]), str(edge[1]), directed=_is_directed(spec))
        for edge in spec["edges"]
        if str(edge[0]) in subset and str(edge[1]) in subset
    ]
    if not edges:
        raise ValueError("pattern must include at least one edge")
    return _spec_from(sorted(subset), edges, directed=_is_directed(spec))


def _replacement_label(existing: Sequence[str]) -> str:
    taken = set(str(label) for label in existing)
    for label in _LABEL_POOL:
        if label not in taken:
            return str(label)
    raise ValueError("no replacement labels left")


def _resolve_int_range(
    params: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    namespace: str,
    instance_seed: int,
) -> Tuple[int, Tuple[int, int], Dict[str, float]]:
    lower = int(params.get(str(min_key), group_default(_GEN_DEFAULTS, str(min_key), int(fallback_min))))
    upper = int(params.get(str(max_key), group_default(_GEN_DEFAULTS, str(max_key), int(fallback_max))))
    if int(lower) > int(upper):
        raise ValueError(f"{min_key} must be <= {max_key}")
    explicit_key = str(min_key).removesuffix("_min")
    explicit = params.get(explicit_key)
    if explicit is not None:
        value = int(explicit)
        if not int(lower) <= value <= int(upper):
            raise ValueError(f"{explicit_key} must fall in [{lower}, {upper}]")
        return int(value), (int(lower), int(upper)), dict(uniform_probability_map(tuple(range(lower, upper + 1)), selected=value))
    selection = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))
    value = int(lower + (selection % (int(upper) - int(lower) + 1)))
    return int(value), (int(lower), int(upper)), dict(uniform_probability_map(tuple(range(lower, upper + 1))))


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_graph_named_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.query_id"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_QUERY_IDS,
        task_id=TASK_ID,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        namespace="query_id",
    )


def _resolve_scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_graph_named_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.scene_variant"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        namespace="scene_variant",
    )


def _resolve_edge_mode(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_graph_named_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.edge_mode"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_EDGE_MODES,
        task_id=TASK_ID,
        explicit_key="edge_mode",
        weights_key="edge_mode_weights",
        balance_flag_key="balanced_edge_mode_sampling",
        namespace="edge_mode",
    )


def _resolve_correct_option_index(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    option_count: int,
    query_id: str,
) -> int:
    explicit = params.get("correct_option_index")
    if explicit is not None:
        index = int(explicit)
        if not 0 <= int(index) < int(option_count):
            raise ValueError("correct_option_index must fall inside option count")
        return int(index)
    selection = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:{str(query_id)}:correct_option_index",
        )
    )
    return int(selection % int(option_count))


def _build_options(
    *,
    correct_spec: Mapping[str, Any],
    distractors: Sequence[Mapping[str, Any]],
    correct_option_index: int,
    option_count: int,
) -> List[Dict[str, Any]]:
    seen = {_canonical_spec(correct_spec)}
    unique_distractors: List[Dict[str, Any]] = []
    for spec in distractors:
        signature = _canonical_spec(spec)
        if signature in seen:
            continue
        seen.add(signature)
        unique_distractors.append(dict(spec))
    if len(unique_distractors) < int(option_count) - 1:
        raise ValueError("not enough unique structure distractors")
    ordered = unique_distractors[: int(option_count) - 1]
    ordered.insert(int(correct_option_index), dict(correct_spec))
    options: List[Dict[str, Any]] = []
    for index, spec in enumerate(ordered):
        label = str(option_label_for_index(int(index)))
        options.append(
            {
                "option_panel_id": f"option_{label}",
                "option_index": int(index),
                "option_label": str(label),
                "structure_spec": dict(spec),
                "structure_signature": _canonical_spec(spec),
                "is_correct": bool(index == int(correct_option_index)),
            }
        )
    return options


def _build_same_structure_dataset(
    *,
    rng,
    params: Mapping[str, Any],
    instance_seed: int,
    option_count: int,
    correct_option_index: int,
    edge_mode: str,
) -> Dict[str, Any]:
    directed = str(edge_mode) == "directed"
    node_count, node_count_range, node_count_probs = _resolve_int_range(
        params,
        min_key="same_structure_node_count_min",
        max_key="same_structure_node_count_max",
        fallback_min=_DEFAULTS.same_structure_node_count_min,
        fallback_max=_DEFAULTS.same_structure_node_count_max,
        namespace=f"{TASK_ID}:same_structure:node_count",
        instance_seed=int(instance_seed),
    )
    base = _make_connected_spec(
        rng,
        node_count=int(node_count),
        extra_edge_min=int(params.get("extra_edge_min", group_default(_GEN_DEFAULTS, "extra_edge_min", _DEFAULTS.extra_edge_min))),
        extra_edge_max=int(params.get("extra_edge_max", group_default(_GEN_DEFAULTS, "extra_edge_max", _DEFAULTS.extra_edge_max))),
        directed=bool(directed),
    )
    distractors: List[Dict[str, Any]] = []
    for delta in (1, 2, 1, 2, 3, 1, 2, 3, 1):
        try:
            distractors.append(_mutate_edges(rng, base, toggle_count=int(delta), require_connected=True))
        except ValueError:
            continue
    while len({_canonical_spec(item) for item in distractors}) < int(option_count) - 1:
        distractors.append(_swap_two_labels(rng, _mutate_edges(rng, base, toggle_count=1, require_connected=True)))
    options = _build_options(
        correct_spec=base,
        distractors=distractors,
        correct_option_index=int(correct_option_index),
        option_count=int(option_count),
    )
    return {
        "query_id": "same_structure_label",
        "query_panel_title": "Reference",
        "query_structure_spec": dict(base),
        "answer_structure_spec": dict(base),
        "option_specs": options,
        "answer_option_label": str(option_label_for_index(int(correct_option_index))),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": f"option_{option_label_for_index(int(correct_option_index))}",
        "node_count": int(node_count),
        "node_count_range": list(node_count_range),
        "node_count_probabilities": dict(node_count_probs),
        "pattern_node_count": None,
        "edge_mode": str(edge_mode),
        "solver_trace": {"rule": "same labeled graph structure, layout ignored", "edge_mode": str(edge_mode)},
    }


def _build_contained_subgraph_dataset(
    *,
    rng,
    params: Mapping[str, Any],
    instance_seed: int,
    option_count: int,
    correct_option_index: int,
    edge_mode: str,
) -> Dict[str, Any]:
    directed = str(edge_mode) == "directed"
    node_count, node_count_range, node_count_probs = _resolve_int_range(
        params,
        min_key="node_count_min",
        max_key="node_count_max",
        fallback_min=_DEFAULTS.node_count_min,
        fallback_max=_DEFAULTS.node_count_max,
        namespace=f"{TASK_ID}:contained_subgraph:node_count",
        instance_seed=int(instance_seed),
    )
    subgraph_count, subgraph_count_range, subgraph_count_probs = _resolve_int_range(
        params,
        min_key="subgraph_node_count_min",
        max_key="subgraph_node_count_max",
        fallback_min=_DEFAULTS.subgraph_node_count_min,
        fallback_max=_DEFAULTS.subgraph_node_count_max,
        namespace=f"{TASK_ID}:contained_subgraph:subgraph_node_count",
        instance_seed=int(instance_seed),
    )
    subgraph_count = min(int(subgraph_count), int(node_count) - 1)
    base = _make_connected_spec(
        rng,
        node_count=int(node_count),
        extra_edge_min=int(params.get("extra_edge_min", group_default(_GEN_DEFAULTS, "extra_edge_min", _DEFAULTS.extra_edge_min))),
        extra_edge_max=int(params.get("extra_edge_max", group_default(_GEN_DEFAULTS, "extra_edge_max", _DEFAULTS.extra_edge_max))),
        directed=bool(directed),
    )
    pattern_labels = _sample_connected_label_subset(rng, base, subset_size=int(subgraph_count))
    pattern = _subspec_from_labels(base, pattern_labels)
    distractors: List[Dict[str, Any]] = []
    for _ in range(120):
        candidate_labels = _sample_connected_label_subset(rng, base, subset_size=int(subgraph_count))
        candidate = _subspec_from_labels(base, candidate_labels)
        if _contains_pattern(candidate, base):
            candidate_edges = set(_edge_set(candidate))
            all_pairs = [pair for pair in _all_label_pairs(candidate["labels"], directed=directed) if pair not in candidate_edges]
            rng.shuffle(all_pairs)
            if all_pairs:
                candidate_edges.add(all_pairs[0])
                candidate = _spec_from(candidate["labels"], sorted(candidate_edges), directed=directed)
        if _contains_pattern(candidate, base):
            pattern_edges = list(_edge_set(pattern))
            if pattern_edges:
                labels = [str(label) for label in candidate["labels"]]
                replace_label = str(rng.choice(labels))
                replacement = _replacement_label(base["labels"])
                mapped = {label: (replacement if label == replace_label else label) for label in labels}
                candidate = _spec_from(sorted(mapped.values()), [_edge_key(mapped[str(edge[0])], mapped[str(edge[1])], directed=directed) for edge in candidate["edges"]], directed=directed)
        if not _contains_pattern(candidate, base):
            distractors.append(candidate)
        if len({_canonical_spec(item) for item in distractors}) >= int(option_count) - 1:
            break
    if len({_canonical_spec(item) for item in distractors}) < int(option_count) - 1:
        for _ in range(60):
            candidate = dict(base)
            labels = [str(label) for label in candidate["labels"]]
            replace_label = str(rng.choice(pattern_labels))
            replacement = _replacement_label(base["labels"])
            mapped = {label: (replacement if label == replace_label else label) for label in labels}
            candidate = _spec_from(sorted(mapped.values()), [_edge_key(mapped[str(edge[0])], mapped[str(edge[1])], directed=directed) for edge in pattern["edges"]], directed=directed)
            if not _contains_pattern(candidate, base):
                distractors.append(candidate)
            if len({_canonical_spec(item) for item in distractors}) >= int(option_count) - 1:
                break
    options = _build_options(
        correct_spec=pattern,
        distractors=distractors,
        correct_option_index=int(correct_option_index),
        option_count=int(option_count),
    )
    return {
        "query_id": "contained_subgraph_label",
        "query_panel_title": "Target Graph",
        "query_structure_spec": dict(base),
        "answer_structure_spec": dict(pattern),
        "option_specs": options,
        "answer_option_label": str(option_label_for_index(int(correct_option_index))),
        "correct_option_index": int(correct_option_index),
        "correct_option_panel_id": f"option_{option_label_for_index(int(correct_option_index))}",
        "node_count": int(node_count),
        "node_count_range": list(node_count_range),
        "node_count_probabilities": dict(node_count_probs),
        "subgraph_node_count": int(subgraph_count),
        "subgraph_node_count_range": list(subgraph_count_range),
        "subgraph_node_count_probability_map": dict(subgraph_count_probs),
        "pattern_node_count": int(subgraph_count),
        "pattern_node_count_range": list(subgraph_count_range),
        "pattern_node_count_probability_map": dict(subgraph_count_probs),
        "edge_mode": str(edge_mode),
        "solver_trace": {"rule": "selected option is contained in the larger graph", "edge_mode": str(edge_mode)},
    }


def _build_dataset_for_variant(
    *,
    query_id: str,
    edge_mode: str,
    params: Mapping[str, Any],
    instance_seed: int,
    attempt: int,
) -> Dict[str, Any]:
    option_count = int(params.get("option_count", group_default(_GEN_DEFAULTS, "option_count", _DEFAULTS.option_count)))
    correct_option_index = _resolve_correct_option_index(
        params,
        instance_seed=int(instance_seed),
        option_count=int(option_count),
        query_id=str(query_id),
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset.{str(query_id)}", int(attempt))
    if str(query_id) == "same_structure_label":
        dataset = _build_same_structure_dataset(
            rng=rng,
            params=params,
            instance_seed=int(instance_seed),
            option_count=int(option_count),
            correct_option_index=int(correct_option_index),
            edge_mode=str(edge_mode),
        )
    elif str(query_id) == "contained_subgraph_label":
        dataset = _build_contained_subgraph_dataset(
            rng=rng,
            params=params,
            instance_seed=int(instance_seed),
            option_count=int(option_count),
            correct_option_index=int(correct_option_index),
            edge_mode=str(edge_mode),
        )
    else:
        raise ValueError(f"unsupported query_id: {query_id}")
    dataset["option_count"] = int(option_count)
    dataset["edge_mode"] = str(edge_mode)
    return dataset


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    namespace = f"{TASK_ID}.render"
    return _RenderParams(
        canvas_width=resolve_render_int(params, _RENDER_DEFAULTS, "canvas_width", _RENDER_FALLBACKS.canvas_width, instance_seed=instance_seed, namespace=namespace),
        canvas_height=resolve_render_int(params, _RENDER_DEFAULTS, "canvas_height", _RENDER_FALLBACKS.canvas_height, instance_seed=instance_seed, namespace=namespace),
        margin_x_px=resolve_render_int(params, _RENDER_DEFAULTS, "margin_x_px", _RENDER_FALLBACKS.margin_x_px, instance_seed=instance_seed, namespace=namespace),
        margin_top_px=resolve_render_int(params, _RENDER_DEFAULTS, "margin_top_px", _RENDER_FALLBACKS.margin_top_px, instance_seed=instance_seed, namespace=namespace),
        reference_panel_height_px=resolve_render_int(params, _RENDER_DEFAULTS, "reference_panel_height_px", _RENDER_FALLBACKS.reference_panel_height_px, instance_seed=instance_seed, namespace=namespace),
        reference_to_options_gap_px=resolve_render_int(params, _RENDER_DEFAULTS, "reference_to_options_gap_px", _RENDER_FALLBACKS.reference_to_options_gap_px, instance_seed=instance_seed, namespace=namespace),
        option_gap_px=resolve_render_int(params, _RENDER_DEFAULTS, "option_gap_px", _RENDER_FALLBACKS.option_gap_px, instance_seed=instance_seed, namespace=namespace),
        option_row_gap_px=resolve_render_int(params, _RENDER_DEFAULTS, "option_row_gap_px", _RENDER_FALLBACKS.option_row_gap_px, instance_seed=instance_seed, namespace=namespace),
        panel_padding_px=resolve_render_int(params, _RENDER_DEFAULTS, "panel_padding_px", _RENDER_FALLBACKS.panel_padding_px, instance_seed=instance_seed, namespace=namespace),
        panel_corner_radius_px=resolve_render_int(params, _RENDER_DEFAULTS, "panel_corner_radius_px", _RENDER_FALLBACKS.panel_corner_radius_px, instance_seed=instance_seed, namespace=namespace),
        border_width_px=resolve_render_int(params, _RENDER_DEFAULTS, "border_width_px", _RENDER_FALLBACKS.border_width_px, instance_seed=instance_seed, namespace=namespace),
        title_font_size_px=resolve_render_int(params, _RENDER_DEFAULTS, "title_font_size_px", _RENDER_FALLBACKS.title_font_size_px, instance_seed=instance_seed, namespace=namespace),
        option_label_font_size_px=resolve_render_int(params, _RENDER_DEFAULTS, "option_label_font_size_px", _RENDER_FALLBACKS.option_label_font_size_px, instance_seed=instance_seed, namespace=namespace),
        node_radius_px=resolve_render_int(params, _RENDER_DEFAULTS, "node_radius_px", _RENDER_FALLBACKS.node_radius_px, instance_seed=instance_seed, namespace=namespace),
        edge_width_px=resolve_render_int(params, _RENDER_DEFAULTS, "edge_width_px", _RENDER_FALLBACKS.edge_width_px, instance_seed=instance_seed, namespace=namespace),
        panel_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "panel_fill_rgb", _RENDER_FALLBACKS.panel_fill_rgb, instance_seed=instance_seed, namespace=namespace),
        option_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "option_fill_rgb", _RENDER_FALLBACKS.option_fill_rgb, instance_seed=instance_seed, namespace=namespace),
        border_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "border_rgb", _RENDER_FALLBACKS.border_rgb, instance_seed=instance_seed, namespace=namespace),
        edge_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "edge_rgb", _RENDER_FALLBACKS.edge_rgb, instance_seed=instance_seed, namespace=namespace),
        node_fill_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "node_fill_rgb", _RENDER_FALLBACKS.node_fill_rgb, instance_seed=instance_seed, namespace=namespace),
        node_outline_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "node_outline_rgb", _RENDER_FALLBACKS.node_outline_rgb, instance_seed=instance_seed, namespace=namespace),
        text_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_rgb", _RENDER_FALLBACKS.text_rgb, instance_seed=instance_seed, namespace=namespace),
        text_stroke_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "text_stroke_rgb", _RENDER_FALLBACKS.text_stroke_rgb, instance_seed=instance_seed, namespace=namespace),
        notebook_line_rgb=resolve_render_rgb(params, _RENDER_DEFAULTS, "notebook_line_rgb", _RENDER_FALLBACKS.notebook_line_rgb, instance_seed=instance_seed, namespace=namespace),
    )


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    fill: Sequence[int],
    stroke_fill: Sequence[int],
    stroke_width: int = 1,
) -> List[float]:
    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=int(stroke_width))
    width = float(bbox[2] - bbox[0])
    height = float(bbox[3] - bbox[1])
    x = float(center[0]) - (0.5 * width) - float(bbox[0])
    y = float(center[1]) - (0.5 * height) - float(bbox[1])
    draw.text(
        (x, y),
        str(text),
        font=font,
        fill=tuple(int(value) for value in fill),
        stroke_fill=tuple(int(value) for value in stroke_fill),
        stroke_width=int(stroke_width),
    )
    return _round_bbox((x + bbox[0], y + bbox[1], x + bbox[2], y + bbox[3]))


def _draw_notebook_lines(
    draw: ImageDraw.ImageDraw,
    *,
    content_bbox: Sequence[float],
    color: Sequence[int],
) -> None:
    left, top, right, bottom = [float(value) for value in content_bbox]
    step = 24.0
    y = top + step
    while y < bottom - 4:
        draw.line((left + 8, y, right - 8, y), fill=tuple(int(value) for value in color), width=1)
        y += step
    x = left + step
    while x < right - 4:
        draw.line((x, top + 8, x, bottom - 8), fill=tuple(int(value) for value in color), width=1)
        x += step


def _panel_content_bbox(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Sequence[float],
    title: str,
    render_params: _RenderParams,
    title_font,
    panel_fill_rgb: Sequence[int],
    border_rgb: Sequence[int],
    text_rgb: Sequence[int],
    text_stroke_rgb: Sequence[int],
) -> List[float]:
    left, top, right, bottom = [float(value) for value in panel_bbox]
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=int(render_params.panel_corner_radius_px),
        fill=tuple(int(value) for value in panel_fill_rgb),
        outline=tuple(int(value) for value in border_rgb),
        width=int(render_params.border_width_px),
    )
    title_band = max(50.0, float(render_params.panel_padding_px) + 24.0)
    title_center_y = top + 0.46 * float(title_band)
    _draw_centered_text(
        draw,
        text=str(title),
        center=(0.5 * (left + right), title_center_y),
        font=title_font,
        fill=text_rgb,
        stroke_fill=text_stroke_rgb,
        stroke_width=1,
    )
    pad = float(render_params.panel_padding_px)
    return _round_bbox((left + pad, top + title_band, right - pad, bottom - pad))


def _layout_structure_positions(
    *,
    labels: Sequence[str],
    content_bbox: Sequence[float],
    layout_variant: str,
    rng,
) -> Dict[str, Tuple[float, float]]:
    label_list = [str(label) for label in labels]
    left, top, right, bottom = [float(value) for value in content_bbox]
    width = max(1.0, right - left)
    height = max(1.0, bottom - top)
    cx = left + 0.5 * width
    cy = top + 0.5 * height
    rx = max(28.0, 0.40 * width)
    ry = max(28.0, 0.36 * height)
    order = list(label_list)
    rng.shuffle(order)
    positions: Dict[str, Tuple[float, float]] = {}
    if str(layout_variant) == "chain":
        if len(order) == 1:
            positions[order[0]] = (cx, cy)
        else:
            for index, label in enumerate(order):
                t = float(index) / float(len(order) - 1)
                x = left + 0.14 * width + (0.72 * width * t)
                y = cy + (0.22 * height * math.sin((t * math.pi * 2.0) + rng.uniform(-0.3, 0.3)))
                positions[str(label)] = (float(x), float(y))
    elif str(layout_variant) == "branch":
        if order:
            positions[order[0]] = (cx, cy)
        for index, label in enumerate(order[1:], start=1):
            angle = (2.0 * math.pi * float(index - 1) / max(1.0, float(len(order) - 1))) + rng.uniform(-0.22, 0.22)
            radius_scale = 0.58 + (0.18 * (index % 2))
            positions[str(label)] = (
                float(cx + (radius_scale * rx * math.cos(angle))),
                float(cy + (radius_scale * ry * math.sin(angle))),
            )
    else:
        offset = rng.uniform(-0.25, 0.25)
        for index, label in enumerate(order):
            angle = (2.0 * math.pi * float(index) / max(1.0, float(len(order)))) + offset
            positions[str(label)] = (float(cx + rx * math.cos(angle)), float(cy + ry * math.sin(angle)))
    jitter_x = 0.035 * width
    jitter_y = 0.035 * height
    resolved = {
        str(label): (
            max(left + 24.0, min(right - 24.0, float(x + rng.uniform(-jitter_x, jitter_x)))),
            max(top + 24.0, min(bottom - 24.0, float(y + rng.uniform(-jitter_y, jitter_y)))),
        )
        for label, (x, y) in positions.items()
    }
    min_sep = min(54.0, max(40.0, 0.30 * min(width, height)))
    for _ in range(48):
        moved = False
        for i, left_label in enumerate(label_list):
            for right_label in label_list[i + 1:]:
                lx, ly = resolved[str(left_label)]
                rx2, ry2 = resolved[str(right_label)]
                dx = float(rx2 - lx)
                dy = float(ry2 - ly)
                dist = max(1e-6, math.hypot(dx, dy))
                if dist >= min_sep:
                    continue
                push = 0.5 * (min_sep - dist)
                ux = dx / dist
                uy = dy / dist
                resolved[str(left_label)] = (
                    max(left + 24.0, min(right - 24.0, lx - (push * ux))),
                    max(top + 24.0, min(bottom - 24.0, ly - (push * uy))),
                )
                resolved[str(right_label)] = (
                    max(left + 24.0, min(right - 24.0, rx2 + (push * ux))),
                    max(top + 24.0, min(bottom - 24.0, ry2 + (push * uy))),
                )
                moved = True
        if not moved:
            break
    return resolved


def _draw_structure(
    draw: ImageDraw.ImageDraw,
    *,
    spec: Mapping[str, Any],
    content_bbox: Sequence[float],
    panel_id: str,
    scene_variant: str,
    render_params: _RenderParams,
    palette_colors: Sequence[Sequence[int]],
    rng,
) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]]]:
    layout_variant = str(rng.choice(["circle", "chain", "branch"]))
    labels = [str(label) for label in spec["labels"]]
    directed = _is_directed(spec)
    positions = _layout_structure_positions(labels=labels, content_bbox=content_bbox, layout_variant=layout_variant, rng=rng)
    atom_palette = [tuple(int(channel) for channel in color) for color in palette_colors] or [(84, 118, 194)]
    if str(scene_variant) == "notebook_graph_options":
        _draw_notebook_lines(draw, content_bbox=content_bbox, color=render_params.notebook_line_rgb)

    edge_rgb = tuple(int(value) for value in render_params.edge_rgb)
    for u_label, v_label in spec["edges"]:
        ux, uy = positions[str(u_label)]
        vx, vy = positions[str(v_label)]
        if directed:
            dx = float(vx - ux)
            dy = float(vy - uy)
            distance = max(1e-6, math.hypot(dx, dy))
            shrink = float(render_params.node_radius_px) + 3.0
            start = (ux + (dx / distance) * shrink, uy + (dy / distance) * shrink)
            end = (vx - (dx / distance) * shrink, vy - (dy / distance) * shrink)
        else:
            start = (ux, uy)
            end = (vx, vy)
        draw.line(
            (start[0], start[1], end[0], end[1]),
            fill=edge_rgb,
            width=int(render_params.edge_width_px),
            joint="curve",
        )
        if directed:
            angle = math.atan2(end[1] - start[1], end[0] - start[0])
            arrow_len = max(12.0, float(render_params.edge_width_px) * 3.1)
            arrow_w = max(8.0, float(render_params.edge_width_px) * 2.0)
            tip = end
            left = (
                tip[0] - arrow_len * math.cos(angle) + arrow_w * math.cos(angle + math.pi / 2.0),
                tip[1] - arrow_len * math.sin(angle) + arrow_w * math.sin(angle + math.pi / 2.0),
            )
            right = (
                tip[0] - arrow_len * math.cos(angle) + arrow_w * math.cos(angle - math.pi / 2.0),
                tip[1] - arrow_len * math.sin(angle) + arrow_w * math.sin(angle - math.pi / 2.0),
            )
            draw.polygon((tip, left, right), fill=edge_rgb)

    entities: List[Dict[str, Any]] = []
    bbox_map: Dict[str, List[float]] = {}
    radius = float(render_params.node_radius_px)
    for index, label in enumerate(labels):
        cx, cy = positions[str(label)]
        if str(scene_variant) == "colored_node_graph_options":
            node_fill = atom_palette[index % len(atom_palette)]
            label_fill = (255, 255, 255)
            label_stroke = tuple(int(value) for value in render_params.node_outline_rgb)
        else:
            node_fill = tuple(int(value) for value in render_params.node_fill_rgb)
            label_fill = tuple(int(value) for value in render_params.text_rgb)
            label_stroke = tuple(int(value) for value in render_params.text_stroke_rgb)
        outline = tuple(int(value) for value in render_params.node_outline_rgb)
        node_bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
        draw.ellipse(tuple(node_bbox), fill=node_fill, outline=outline, width=max(2, int(render_params.border_width_px)))
        label_font = fit_font_to_box(
            draw,
            text=str(label),
            max_width=1.35 * radius,
            max_height=1.15 * radius,
            bold=True,
            min_size_px=12,
            max_size_px=24,
            fill_ratio=0.95,
        )
        _draw_centered_text(
            draw,
            text=str(label),
            center=(cx, cy),
            font=label_font,
            fill=label_fill,
            stroke_fill=label_stroke,
            stroke_width=1,
        )
        entity_id = f"{panel_id}_node_{label}"
        rounded_bbox = _round_bbox(node_bbox)
        bbox_map[entity_id] = rounded_bbox
        entities.append(
            {
                "entity_id": entity_id,
                "entity_kind": "structure_node",
                "panel_id": str(panel_id),
                "label": str(label),
                "center_px": [round(float(cx), 3), round(float(cy), 3)],
                "bbox_xyxy": list(rounded_bbox),
            }
        )
    for edge_index, (u_label, v_label) in enumerate(sorted(_edge_set(spec))):
        ux, uy = positions[str(u_label)]
        vx, vy = positions[str(v_label)]
        entities.append(
            {
                "entity_id": f"{panel_id}_edge_{edge_index}",
                "entity_kind": "structure_edge",
                "panel_id": str(panel_id),
                "node_u_label": str(u_label),
                "node_v_label": str(v_label),
                "segment_px": [[round(float(ux), 3), round(float(uy), 3)], [round(float(vx), 3), round(float(vy), 3)]],
            }
        )
    entities.append(
        {
            "entity_id": f"{panel_id}_structure",
                "entity_kind": "structure_diagram",
                "panel_id": str(panel_id),
                "labels": list(labels),
                "edges": [list(edge) for edge in sorted(_edge_set(spec))],
                "directed": bool(directed),
                "layout_variant": str(layout_variant),
            }
    )
    return entities, bbox_map


@dataclass(frozen=True)
class _RenderedStructureGraphScene:
    """Rendered image and projected geometry for one graph-structure task."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    bbox_map: Dict[str, List[float]]
    option_panel_bbox_map: Dict[str, List[float]]


def _render_scene(
    *,
    dataset: Mapping[str, Any],
    scene_variant: str,
    render_params: _RenderParams,
    instance_seed: int,
    background: Image.Image,
    palette_colors: Sequence[Sequence[int]],
) -> _RenderedStructureGraphScene:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    option_font = load_font(int(render_params.option_label_font_size_px), bold=True)
    entities: List[Dict[str, Any]] = []
    bbox_map: Dict[str, List[float]] = {}
    option_panel_bbox_map: Dict[str, List[float]] = {}

    ref_left = float(render_params.margin_x_px)
    ref_top = float(render_params.margin_top_px)
    ref_right = float(render_params.canvas_width - render_params.margin_x_px)
    ref_bottom = ref_top + float(render_params.reference_panel_height_px)
    reference_bbox = _round_bbox((ref_left, ref_top, ref_right, ref_bottom))
    reference_content = _panel_content_bbox(
        draw,
        panel_bbox=reference_bbox,
        title=str(dataset["query_panel_title"]),
        render_params=render_params,
        title_font=title_font,
        panel_fill_rgb=render_params.panel_fill_rgb,
        border_rgb=render_params.border_rgb,
        text_rgb=render_params.text_rgb,
        text_stroke_rgb=render_params.text_stroke_rgb,
    )
    ref_entities, ref_bboxes = _draw_structure(
        draw,
        spec=dataset["query_structure_spec"],
        content_bbox=reference_content,
        panel_id="query_panel",
        scene_variant=str(scene_variant),
        render_params=render_params,
        palette_colors=palette_colors,
        rng=spawn_rng(int(instance_seed), f"{TASK_ID}.render.query_structure"),
    )
    entities.extend(ref_entities)
    bbox_map.update(ref_bboxes)
    bbox_map["query_panel"] = list(reference_bbox)
    entities.append(
        {
            "entity_id": "query_panel",
            "entity_kind": "query_panel",
            "title": str(dataset["query_panel_title"]),
            "bbox_xyxy": list(reference_bbox),
            "content_bbox_xyxy": list(reference_content),
        }
    )

    option_count = int(dataset["option_count"])
    cols = 3
    rows = int(math.ceil(float(option_count) / float(cols)))
    options_top = ref_bottom + float(render_params.reference_to_options_gap_px)
    usable_width = float(render_params.canvas_width - (2 * render_params.margin_x_px))
    option_w = (usable_width - (float(cols - 1) * float(render_params.option_gap_px))) / float(cols)
    remaining_height = float(render_params.canvas_height) - options_top - float(render_params.margin_top_px)
    option_h = (remaining_height - (float(rows - 1) * float(render_params.option_row_gap_px))) / float(rows)

    for option_index, option_spec in enumerate(dataset["option_specs"]):
        row = int(option_index // cols)
        col = int(option_index % cols)
        left = ref_left + (float(col) * (option_w + float(render_params.option_gap_px)))
        top = options_top + (float(row) * (option_h + float(render_params.option_row_gap_px)))
        panel_bbox = _round_bbox((left, top, left + option_w, top + option_h))
        option_panel_id = str(option_spec["option_panel_id"])
        option_panel_bbox_map[option_panel_id] = list(panel_bbox)
        bbox_map[option_panel_id] = list(panel_bbox)
        content_bbox = _panel_content_bbox(
            draw,
            panel_bbox=panel_bbox,
            title=str(option_spec["option_label"]),
            render_params=render_params,
            title_font=option_font,
            panel_fill_rgb=render_params.option_fill_rgb,
            border_rgb=render_params.border_rgb,
            text_rgb=render_params.text_rgb,
            text_stroke_rgb=render_params.text_stroke_rgb,
        )
        option_entities, option_bboxes = _draw_structure(
            draw,
            spec=option_spec["structure_spec"],
            content_bbox=content_bbox,
            panel_id=option_panel_id,
            scene_variant=str(scene_variant),
            render_params=render_params,
            palette_colors=palette_colors,
            rng=spawn_rng(int(instance_seed), f"{TASK_ID}.render.{option_panel_id}", int(option_index)),
        )
        entities.extend(option_entities)
        bbox_map.update(option_bboxes)
        entities.append(
            {
                "entity_id": option_panel_id,
                "entity_kind": "option_panel",
                "option_label": str(option_spec["option_label"]),
                "is_correct": bool(option_spec["is_correct"]),
                "bbox_xyxy": list(panel_bbox),
                "content_bbox_xyxy": list(content_bbox),
            }
        )

    scene_bbox = _round_bbox((ref_left, ref_top, ref_right, float(render_params.canvas_height - render_params.margin_top_px)))
    return _RenderedStructureGraphScene(
        image=image,
        entities=entities,
        scene_bbox_px=scene_bbox,
        bbox_map=bbox_map,
        option_panel_bbox_map=option_panel_bbox_map,
    )


def _build_complexity(dataset: Mapping[str, Any], *, query_id: str, scene_variant: str) -> Any:
    option_count = int(dataset.get("option_count", 6))
    node_count = int(dataset.get("node_count", 5))
    edge_count = len(_edge_set(dataset["answer_structure_spec"]))
    visual_scan = clamp_unit_interval(
        0.45 * normalize_int_with_bounds(option_count, (4, 6))
        + 0.35 * normalize_int_with_bounds(node_count, (4, 8))
        + 0.20 * normalize_int_with_bounds(edge_count, (3, 12))
    )
    clutter = clamp_unit_interval(0.65 * normalize_int_with_bounds(edge_count, (4, 14)) + 0.35 * normalize_int_with_bounds(option_count, (4, 6)))
    return build_graph_complexity(
        weights=_COMPLEXITY_WEIGHTS,
        components={
            "topology_reasoning": float(_QUERY_LOAD[str(query_id)]),
            "visual_scan": float(visual_scan),
            "ambiguity": 0.36 if str(query_id) == "same_structure_label" else 0.46,
            "clutter": float(clutter + (0.08 * _SCENE_LOAD[str(scene_variant)])),
        },
    )


@register_task
class GraphRelationStructureMatchLabelTask:
    """Choose a matching labeled graph option."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, instance_seed=int(instance_seed))
        edge_mode, edge_mode_probabilities = _resolve_edge_mode(params, instance_seed=int(instance_seed))
        last_error: Exception | None = None
        dataset: Dict[str, Any] | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                dataset = _build_dataset_for_variant(
                    query_id=str(query_id),
                    edge_mode=str(edge_mode),
                    params=params,
                    instance_seed=int(hash64(int(instance_seed), f"{TASK_ID}.dataset_seed", int(attempt))),
                    attempt=int(attempt),
                )
                break
            except Exception as exc:  # pragma: no cover - retry path
                last_error = exc
                continue
        if dataset is None:
            raise RuntimeError(f"failed to generate {self.task_id}") from last_error

        base_render_params = _resolve_render_params(params, instance_seed=int(instance_seed))
        color_names = ("blue", "green", "orange", "purple", "cyan", "magenta", "maroon")
        color_selection = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}:node_color_name",
            )
        )
        node_color_name = color_names[color_selection % len(color_names)]
        panel_style_variants = ("default", "cool", "warm", "mint", "paper")
        panel_style = panel_style_variants[
            int(
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{TASK_ID}:panel_style_variant",
                )
            )
            % len(panel_style_variants)
        ]
        graph_theme = apply_graph_panel_style(
            build_graph_named_color_theme(str(node_color_name)),
            panel_style_variant=str(panel_style),
        )
        palette_colors = (
            graph_theme.node_fill_rgb,
            (217, 119, 6),
            (22, 163, 74),
            (147, 51, 234),
            (8, 145, 178),
            (220, 38, 38),
        )
        scene_style_meta = {
            "node_color_name": str(node_color_name),
            "panel_style_variant": str(panel_style),
        }
        render_params = _RenderParams(
            **{
                **base_render_params.__dict__,
                "panel_fill_rgb": tuple(int(value) for value in graph_theme.panel_fill_rgb),
                "option_fill_rgb": (255, 255, 255),
                "border_rgb": tuple(int(value) for value in graph_theme.panel_border_rgb),
                "edge_rgb": tuple(int(value) for value in graph_theme.edge_color_rgb),
                "node_fill_rgb": tuple(int(value) for value in graph_theme.node_fill_rgb),
                "node_outline_rgb": tuple(int(value) for value in graph_theme.node_border_rgb),
                "text_rgb": tuple(int(value) for value in graph_theme.title_color_rgb),
                "text_stroke_rgb": (255, 255, 255),
                "notebook_line_rgb": tuple(int(value) for value in graph_theme.panel_border_rgb),
            }
        )
        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            fallback_color=tuple(int(value) for value in graph_theme.background_color_rgb),
        )
        rendered_scene = _render_scene(
            dataset=dataset,
            scene_variant=str(scene_variant),
            render_params=render_params,
            instance_seed=int(instance_seed),
            background=background,
            palette_colors=palette_colors,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_undirected",
                "object_description_directed",
                "evidence_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
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
                    prompt_defaults[
                        "object_description_directed" if str(edge_mode) == "directed" else "object_description_undirected"
                    ]
                ),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        correct_option_panel_id = str(dataset["correct_option_panel_id"])
        evidence_projection = _project_bbox_evidence(rendered_scene.bbox_map, [correct_option_panel_id])
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_value = str(dataset["answer_option_label"])
        answer_gt = TypedValue(type="option_letter", value=str(answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        trace_payload = {
            "scene_ir": {
                "scene_kind": "graph_structure_options",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(query_id),
                    "edge_mode": str(edge_mode),
                    "answer_option_label": str(answer_value),
                    "correct_option_panel_id": str(correct_option_panel_id),
                    "query_structure_signature": _canonical_spec(dataset["query_structure_spec"]),
                    "answer_structure_signature": _canonical_spec(dataset["answer_structure_spec"]),
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
                    "query_id_probabilities": dict(query_id_probabilities),
                    "edge_mode": str(edge_mode),
                    "edge_mode_probabilities": dict(edge_mode_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "option_count": int(dataset["option_count"]),
                    "node_count": int(dataset["node_count"]),
                    "node_count_range": list(dataset["node_count_range"]),
                    "node_count_probabilities": dict(dataset["node_count_probabilities"]),
                    "pattern_node_count": dataset.get("pattern_node_count"),
                    "pattern_node_count_range": list(dataset.get("pattern_node_count_range", [])),
                    "pattern_node_count_probability_map": dict(dataset.get("pattern_node_count_probability_map", {})),
                    "subgraph_node_count": dataset.get("subgraph_node_count"),
                    "subgraph_node_count_range": list(dataset.get("subgraph_node_count_range", [])),
                    "subgraph_node_count_probability_map": dict(dataset.get("subgraph_node_count_probability_map", {})),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "style": {
                    "panel_fill_rgb": list(render_params.panel_fill_rgb),
                    "option_fill_rgb": list(render_params.option_fill_rgb),
                    "border_rgb": list(render_params.border_rgb),
                    "edge_rgb": list(render_params.edge_rgb),
                    "node_fill_rgb": list(render_params.node_fill_rgb),
                    "node_outline_rgb": list(render_params.node_outline_rgb),
                    "text_rgb": list(render_params.text_rgb),
                    "text_stroke_rgb": list(render_params.text_stroke_rgb),
                    "node_radius_px": int(render_params.node_radius_px),
                    "edge_width_px": int(render_params.edge_width_px),
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.bbox_map.items()},
                "option_panel_bboxes_px": {
                    str(key): list(value) for key, value in rendered_scene.option_panel_bbox_map.items()
                },
            },
            "execution_trace": {
                "query_id": str(query_id),
                "query_id_probabilities": dict(query_id_probabilities),
                "edge_mode": str(edge_mode),
                "edge_mode_probabilities": dict(edge_mode_probabilities),
                "scene_variant": str(scene_variant),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "question_format": str(query_id),
                "query_panel_title": str(dataset["query_panel_title"]),
                "query_structure_spec": dict(dataset["query_structure_spec"]),
                "answer_structure_spec": dict(dataset["answer_structure_spec"]),
                "answer_option_label": str(answer_value),
                "correct_option_index": int(dataset["correct_option_index"]),
                "correct_option_panel_id": str(correct_option_panel_id),
                "option_count": int(dataset["option_count"]),
                "option_specs": [dict(option) for option in dataset["option_specs"]],
                "node_count": int(dataset["node_count"]),
                "node_count_range": list(dataset["node_count_range"]),
                "node_count_probabilities": dict(dataset["node_count_probabilities"]),
                "pattern_node_count": dataset.get("pattern_node_count"),
                "pattern_node_count_range": list(dataset.get("pattern_node_count_range", [])),
                "pattern_node_count_probability_map": dict(dataset.get("pattern_node_count_probability_map", {})),
                "subgraph_node_count": dataset.get("subgraph_node_count"),
                "subgraph_node_count_range": list(dataset.get("subgraph_node_count_range", [])),
                "subgraph_node_count_probability_map": dict(dataset.get("subgraph_node_count_probability_map", {})),
                "solver_trace": dict(dataset["solver_trace"]),
                "supporting_option_panel_ids": [str(correct_option_panel_id)],
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
                "correct_option_panel_id": str(correct_option_panel_id),
            },
            "projected_evidence": {
                "type": "bbox_set",
                "bbox_set": list(evidence_bboxes),
                "pixel_bbox_set": list(evidence_bboxes),
            },
        }
        complexity = _build_complexity(dataset, query_id=str(query_id), scene_variant=str(scene_variant))
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


__all__ = ["GraphRelationStructureMatchLabelTask"]
