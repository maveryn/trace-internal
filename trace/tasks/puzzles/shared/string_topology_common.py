"""Shared dataset builders and defaults for topology string-component puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import spawn_rng
from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.render_variation import resolve_render_int, resolve_render_rgb
from .common import resolve_puzzle_axis_variant


SUPPORTED_PUZZLE_STRING_TOPOLOGY_SCENE_VARIANTS: Tuple[str, ...] = (
    "string_strip",
    "string_card",
    "string_outline",
)
SUPPORTED_PUZZLE_STRING_TOPOLOGY_QUERY_IDS: Tuple[str, ...] = (
    "open_rope_count",
    "closed_loop_count",
    "knotted_component_count",
)
STRING_TOPOLOGY_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (51, 86, 148),
    (169, 80, 46),
    (58, 122, 91),
    (126, 82, 157),
    (56, 119, 136),
    (151, 88, 115),
    (95, 98, 106),
    (131, 111, 48),
    (47, 128, 117),
)

@dataclass(frozen=True)
class PuzzleStringTopologyDefaults:
    """Default generation bounds for topology string-component puzzles."""

    visual_group_count_min: int = 6
    visual_group_count_max: int = 20
    target_count_min: int = 3
    target_count_max: int = 10
    distractor_count_min: int = 3
    distractor_count_max: int = 10


@dataclass(frozen=True)
class PuzzleStringTopologyRenderParams:
    """Resolved rendering params for topology string-component scenes."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    group_width_px: int
    group_height_px: int
    group_width_min_px: int
    group_width_max_px: int
    group_height_min_px: int
    group_height_max_px: int
    linked_pair_width_min_px: int
    linked_pair_width_max_px: int
    tangled_bundle_width_min_px: int
    tangled_bundle_width_max_px: int
    tangled_bundle_height_min_px: int
    tangled_bundle_height_max_px: int
    group_min_gap_px: int
    placement_attempts: int
    group_gap_px: int
    group_row_gap_px: int
    panel_corner_radius_px: int
    border_width_px: int
    rope_stroke_width_px: int
    endpoint_radius_px: int
    component_padding_px: int
    panel_fill_rgb: Tuple[int, int, int]
    card_fill_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    rope_shadow_rgb: Tuple[int, int, int]
    gap_fill_rgb: Tuple[int, int, int]


def resolve_string_topology_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the topology string scene variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_STRING_TOPOLOGY_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_string_topology_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the topology string semantic variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_STRING_TOPOLOGY_QUERY_IDS,
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def resolve_string_topology_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    instance_seed: int | None = None,
) -> PuzzleStringTopologyRenderParams:
    """Resolve rendering params for topology string-component scenes."""

    def _int(key: str, fallback: int) -> int:
        return resolve_render_int(
            params,
            render_defaults,
            str(key),
            int(fallback),
            instance_seed=instance_seed,
            namespace="puzzle_string_topology_render",
        )

    def _rgb(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_render_rgb(
            params,
            render_defaults,
            str(key),
            fallback,
            instance_seed=instance_seed,
            namespace="puzzle_string_topology_render",
        )

    return PuzzleStringTopologyRenderParams(
        canvas_width=int(_int("canvas_width", 1200)),
        canvas_height=int(_int("canvas_height", 900)),
        scene_margin_left_px=int(_int("scene_margin_left_px", 56)),
        scene_margin_right_px=int(_int("scene_margin_right_px", 56)),
        scene_margin_top_px=int(_int("scene_margin_top_px", 52)),
        scene_margin_bottom_px=int(_int("scene_margin_bottom_px", 52)),
        group_width_px=int(_int("group_width_px", 190)),
        group_height_px=int(_int("group_height_px", 128)),
        group_width_min_px=int(_int("group_width_min_px", 138)),
        group_width_max_px=int(_int("group_width_max_px", 214)),
        group_height_min_px=int(_int("group_height_min_px", 92)),
        group_height_max_px=int(_int("group_height_max_px", 146)),
        linked_pair_width_min_px=int(_int("linked_pair_width_min_px", 178)),
        linked_pair_width_max_px=int(_int("linked_pair_width_max_px", 252)),
        tangled_bundle_width_min_px=int(_int("tangled_bundle_width_min_px", 760)),
        tangled_bundle_width_max_px=int(_int("tangled_bundle_width_max_px", 1040)),
        tangled_bundle_height_min_px=int(_int("tangled_bundle_height_min_px", 420)),
        tangled_bundle_height_max_px=int(_int("tangled_bundle_height_max_px", 620)),
        group_min_gap_px=int(_int("group_min_gap_px", 18)),
        placement_attempts=int(_int("placement_attempts", 500)),
        group_gap_px=int(_int("group_gap_px", 32)),
        group_row_gap_px=int(_int("group_row_gap_px", 32)),
        panel_corner_radius_px=int(_int("panel_corner_radius_px", 16)),
        border_width_px=int(_int("border_width_px", 2)),
        rope_stroke_width_px=int(_int("rope_stroke_width_px", 9)),
        endpoint_radius_px=int(_int("endpoint_radius_px", 6)),
        component_padding_px=int(_int("component_padding_px", 14)),
        panel_fill_rgb=_rgb("panel_fill_rgb", (248, 249, 252)),
        card_fill_rgb=_rgb("card_fill_rgb", (255, 255, 255)),
        border_color_rgb=_rgb("border_color_rgb", (83, 91, 105)),
        rope_shadow_rgb=_rgb("rope_shadow_rgb", (236, 239, 244)),
        gap_fill_rgb=_rgb("gap_fill_rgb", (255, 255, 255)),
    )


def _is_uniform_probability_map(probabilities: Mapping[str, float], *, tol: float = 1e-9) -> bool:
    """Return true when all positive probabilities are approximately equal."""

    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if not positives:
        return False
    return max(positives) - min(positives) <= float(tol)


def _one_hot_probability_map(selected: int, support: Sequence[int]) -> Dict[str, float]:
    """Return a deterministic one-hot probability map over integer support."""

    return {
        str(int(value)): (1.0 if int(value) == int(selected) else 0.0)
        for value in support
    }


def _sorted_probability_map(probabilities: Mapping[str, float]) -> Dict[str, float]:
    """Return an integer-key-sorted probability map."""

    return {
        str(key): float(value)
        for key, value in sorted(probabilities.items(), key=lambda item: int(item[0]))
    }


def _balanced_axis_index(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    namespace: str,
    axis_stride: int,
) -> int:
    """Return a stable support index for one axis."""

    _ = int(axis_stride)
    return resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=str(namespace),
    )


def _resolve_count_from_support(
    rng,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    support: Sequence[int],
    explicit_key: str,
    weights_key: str,
    namespace: str,
    axis_stride: int,
) -> Tuple[int, Dict[str, float]]:
    """Resolve one count axis from an integer support."""

    supported = [int(value) for value in support]
    if not supported:
        raise ValueError(f"{explicit_key} resolved empty support")
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(supported):
            raise ValueError(f"{explicit_key} is outside configured supported range")
        return int(selected), _one_hot_probability_map(int(selected), supported)

    raw_weights = params.get(
        str(weights_key),
        gen_defaults.get(str(weights_key), {str(value): 1.0 for value in supported}),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError(f"{weights_key} must be a mapping when provided")
    supported_keys = {str(value) for value in supported}
    weights = {
        str(key): float(value)
        for key, value in raw_weights.items()
        if str(key) in supported_keys
    }
    probabilities = normalize_positive_weights(
        weights,
        default_keys=[str(value) for value in supported],
    )
    selected = int(weighted_choice(rng, probabilities, sort_keys=True))
    enabled = bool(params.get("balanced_sampling", gen_defaults.get("balanced_sampling", True)))
    overridden = str(weights_key) in params
    if bool(enabled) and (not overridden) and _is_uniform_probability_map(probabilities):
        selection_index = _balanced_axis_index(
            params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
            axis_stride=int(axis_stride),
        )
        selected = int(supported[int(selection_index) % len(supported)])
    return int(selected), _sorted_probability_map(probabilities)


def _resolve_target_and_distractor_counts(
    rng,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleStringTopologyDefaults,
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Resolve independent answer and distractor counts under total shape bounds."""

    count_params: Mapping[str, Any] = params
    if params.get("target_answer") is not None:
        if params.get("target_count") is not None and int(params["target_count"]) != int(params["target_answer"]):
            raise ValueError("target_answer and target_count must match when both are provided")
        count_params = dict(params)
        count_params["target_count"] = int(params["target_answer"])

    visual_group_count_min = int(
        count_params.get(
            "visual_group_count_min",
            count_params.get(
                "object_count_min",
                group_default(gen_defaults, "visual_group_count_min", int(defaults.visual_group_count_min)),
            ),
        )
    )
    visual_group_count_max = int(
        count_params.get(
            "visual_group_count_max",
            count_params.get(
                "object_count_max",
                group_default(gen_defaults, "visual_group_count_max", int(defaults.visual_group_count_max)),
            ),
        )
    )
    target_count_min = int(
        count_params.get(
            "target_count_min",
            group_default(gen_defaults, "target_count_min", int(defaults.target_count_min)),
        )
    )
    target_count_max = int(
        count_params.get(
            "target_count_max",
            group_default(gen_defaults, "target_count_max", int(defaults.target_count_max)),
        )
    )
    distractor_count_min = int(
        count_params.get(
            "distractor_count_min",
            group_default(gen_defaults, "distractor_count_min", int(defaults.distractor_count_min)),
        )
    )
    distractor_count_max = int(
        count_params.get(
            "distractor_count_max",
            group_default(gen_defaults, "distractor_count_max", int(defaults.distractor_count_max)),
        )
    )
    if int(visual_group_count_min) < 1 or int(visual_group_count_max) < int(visual_group_count_min):
        raise ValueError("invalid visual_group_count_min/visual_group_count_max")
    if int(target_count_min) < 1 or int(target_count_max) < int(target_count_min):
        raise ValueError("invalid target_count_min/target_count_max")
    if int(distractor_count_min) < 1 or int(distractor_count_max) < int(distractor_count_min):
        raise ValueError("invalid distractor_count_min/distractor_count_max")

    all_target_support = list(range(int(target_count_min), int(target_count_max) + 1))
    all_distractor_support = list(range(int(distractor_count_min), int(distractor_count_max) + 1))
    target_support = [
        int(target)
        for target in all_target_support
        if any(
            int(visual_group_count_min) <= int(target) + int(distractor) <= int(visual_group_count_max)
            for distractor in all_distractor_support
        )
    ]
    if not target_support:
        raise ValueError("topology string task resolved empty target support")

    target_count, target_count_probabilities = _resolve_count_from_support(
        rng,
        params=count_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        support=target_support,
        explicit_key="target_count",
        weights_key="target_count_weights",
        namespace=f"{task_id}.target_count",
        axis_stride=1,
    )
    distractor_support = [
        int(distractor)
        for distractor in all_distractor_support
        if int(visual_group_count_min) <= int(target_count) + int(distractor) <= int(visual_group_count_max)
    ]
    distractor_count, distractor_count_probabilities = _resolve_count_from_support(
        rng,
        params=count_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        support=distractor_support,
        explicit_key="distractor_count",
        weights_key="distractor_count_weights",
        namespace=f"{task_id}.distractor_count",
        axis_stride=len(target_support),
    )
    object_count = int(target_count) + int(distractor_count)
    object_count_probabilities = {
        str(int(target_count) + int(distractor)): float(probability)
        for distractor, probability in (
            (int(key), float(value))
            for key, value in distractor_count_probabilities.items()
        )
    }
    return {
        "object_count": int(object_count),
        "object_count_range": [int(visual_group_count_min), int(visual_group_count_max)],
        "object_count_probabilities": _sorted_probability_map(object_count_probabilities),
        "target_count": int(target_count),
        "target_answer": int(target_count),
        "target_count_range": [int(target_count_min), int(target_count_max)],
        "target_count_support": [int(value) for value in target_support],
        "target_count_probabilities": dict(target_count_probabilities),
        "target_answer_probabilities": dict(target_count_probabilities),
        "distractor_count": int(distractor_count),
        "distractor_count_range": [int(distractor_count_min), int(distractor_count_max)],
        "distractor_count_probabilities": dict(distractor_count_probabilities),
    }


def _component_color(index: int) -> List[int]:
    """Return a stable rope color for one component index."""

    color = STRING_TOPOLOGY_COLORS[int(index) % len(STRING_TOPOLOGY_COLORS)]
    return [int(channel) for channel in color]


def _make_component(
    *,
    component_index: int,
    component_type: str,
    visual_group_id: str,
    closed: bool,
    knotted: bool,
    knot_count: int = 0,
    linked_pair_id: str | None = None,
    pair_side: str | None = None,
) -> Dict[str, Any]:
    """Build one symbolic string component spec."""

    component_id = f"component_{int(component_index)}"
    return {
        "component_id": str(component_id),
        "component_index": int(component_index),
        "component_type": str(component_type),
        "visual_group_id": str(visual_group_id),
        "closed": bool(closed),
        "open_ended": not bool(closed),
        "knotted": bool(knotted),
        "knot_count": int(knot_count),
        "linked_pair_id": str(linked_pair_id) if linked_pair_id is not None else None,
        "pair_side": str(pair_side) if pair_side is not None else None,
        "color_rgb": _component_color(int(component_index)),
    }


def _append_single_group(
    *,
    groups: List[Dict[str, Any]],
    components: List[Dict[str, Any]],
    component_type: str,
    closed: bool,
    knotted: bool,
    knot_count: int = 0,
) -> None:
    """Append one single-component visual group."""

    group_id = f"group_{len(groups) + 1}"
    resolved_knot_count = int(knot_count if knot_count > 0 else (1 if bool(knotted) else 0))
    component = _make_component(
        component_index=len(components) + 1,
        component_type=str(component_type),
        visual_group_id=str(group_id),
        closed=bool(closed),
        knotted=bool(knotted),
        knot_count=int(resolved_knot_count),
    )
    components.append(component)
    groups.append(
        {
            "visual_group_id": str(group_id),
            "group_type": "single_component",
            "component_ids": [str(component["component_id"])],
            "linked_pair_id": None,
            "knot_count": int(resolved_knot_count),
        }
    )


def _append_tangled_rope_bundle_group(
    *,
    groups: List[Dict[str, Any]],
    components: List[Dict[str, Any]],
    rope_count: int,
) -> None:
    """Append one visual bundle containing several separate open ropes."""

    group_id = f"group_{len(groups) + 1}"
    component_ids: List[str] = []
    for _ in range(int(rope_count)):
        component = _make_component(
            component_index=len(components) + 1,
            component_type="tangled_rope",
            visual_group_id=str(group_id),
            closed=False,
            knotted=False,
            knot_count=0,
        )
        components.append(component)
        component_ids.append(str(component["component_id"]))
    groups.append(
        {
            "visual_group_id": str(group_id),
            "group_type": "tangled_rope_bundle",
            "component_ids": list(component_ids),
            "linked_pair_id": None,
            "knot_count": 0,
        }
    )


def _append_linked_pair_group(
    *,
    groups: List[Dict[str, Any]],
    components: List[Dict[str, Any]],
    pair_index: int,
) -> None:
    """Append one two-component linked-ring visual group."""

    group_id = f"group_{len(groups) + 1}"
    linked_pair_id = f"linked_pair_{int(pair_index)}"
    left = _make_component(
        component_index=len(components) + 1,
        component_type="linked_ring",
        visual_group_id=str(group_id),
        closed=True,
        knotted=False,
        knot_count=0,
        linked_pair_id=str(linked_pair_id),
        pair_side="left",
    )
    right = _make_component(
        component_index=len(components) + 2,
        component_type="linked_ring",
        visual_group_id=str(group_id),
        closed=True,
        knotted=False,
        knot_count=0,
        linked_pair_id=str(linked_pair_id),
        pair_side="right",
    )
    components.extend([left, right])
    groups.append(
        {
            "visual_group_id": str(group_id),
            "group_type": "linked_pair",
            "component_ids": [str(left["component_id"]), str(right["component_id"])],
            "linked_pair_id": str(linked_pair_id),
            "knot_count": 0,
        }
    )


def _shuffle_groups_and_renumber(
    groups: List[Dict[str, Any]],
    components: List[Dict[str, Any]],
    *,
    rng,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Shuffle visual groups while preserving per-group component order."""

    shuffled_groups = [dict(group) for group in groups]
    rng.shuffle(shuffled_groups)
    component_by_id = {str(component["component_id"]): dict(component) for component in components}
    ordered_components: List[Dict[str, Any]] = []
    for group_index, group in enumerate(shuffled_groups, start=1):
        group["visual_order"] = int(group_index)
        for component_id in group["component_ids"]:
            component = dict(component_by_id[str(component_id)])
            component["visual_order"] = int(len(ordered_components) + 1)
            ordered_components.append(component)
    return shuffled_groups, ordered_components


def _next_pair_index(groups: Sequence[Mapping[str, Any]]) -> int:
    """Return the next linked-pair index."""

    return 1 + sum(1 for group in groups if str(group.get("group_type")) == "linked_pair")


def _append_fillers(
    *,
    groups: List[Dict[str, Any]],
    components: List[Dict[str, Any]],
    target_group_count: int,
    filler_cycle: Sequence[str],
) -> None:
    """Append non-target filler groups until the visual group count is reached."""

    offset = 0
    while len(groups) < int(target_group_count):
        filler = str(filler_cycle[int(offset) % len(filler_cycle)])
        offset += 1
        if filler == "linked_pair":
            _append_linked_pair_group(
                groups=groups,
                components=components,
                pair_index=_next_pair_index(groups),
            )
        elif filler == "closed_ring":
            _append_single_group(
                groups=groups,
                components=components,
                component_type="closed_ring",
                closed=True,
                knotted=False,
            )
        elif filler == "knotted_loop":
            _append_single_group(
                groups=groups,
                components=components,
                component_type="knotted_loop",
                closed=True,
                knotted=True,
                knot_count=1,
            )
        else:
            _append_single_group(
                groups=groups,
                components=components,
                component_type="open_string",
                closed=False,
                knotted=False,
            )


def _build_component_pool(
    *,
    query_id: str,
    target_answer: int,
    visual_group_count: int,
    rng,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Build visual groups and component specs satisfying one target answer."""

    selected = str(query_id)
    groups: List[Dict[str, Any]] = []
    components: List[Dict[str, Any]] = []

    if selected == "open_rope_count":
        for _ in range(int(target_answer)):
            _append_single_group(
                groups=groups,
                components=components,
                component_type="open_string",
                closed=False,
                knotted=False,
            )
        _append_fillers(
            groups=groups,
            components=components,
            target_group_count=int(visual_group_count),
            filler_cycle=("closed_ring", "knotted_loop"),
        )
    elif selected == "closed_loop_count":
        for _ in range(int(target_answer)):
            _append_single_group(
                groups=groups,
                components=components,
                component_type="closed_ring",
                closed=True,
                knotted=False,
            )
        _append_fillers(
            groups=groups,
            components=components,
            target_group_count=int(visual_group_count),
            filler_cycle=("open_string", "open_string"),
        )
    elif selected == "knotted_component_count":
        for _ in range(int(target_answer)):
            _append_single_group(
                groups=groups,
                components=components,
                component_type="knotted_loop",
                closed=True,
                knotted=True,
                knot_count=1,
            )
        _append_fillers(
            groups=groups,
            components=components,
            target_group_count=int(visual_group_count),
            filler_cycle=("open_string", "closed_ring", "open_string"),
        )
    else:
        raise ValueError(f"unsupported topology string query_id: {query_id}")

    return _shuffle_groups_and_renumber(groups, components, rng=rng)


def _supporting_item_ids_for_variant(
    *,
    query_id: str,
    components: Sequence[Mapping[str, Any]],
    groups: Sequence[Mapping[str, Any]],
    crossings: Sequence[Mapping[str, Any]],
) -> List[str]:
    """Return ordered annotation ids for the selected query id."""

    selected = str(query_id)
    if selected == "open_rope_count":
        return [
            str(component["component_id"])
            for component in components
            if bool(component.get("open_ended", not bool(component.get("closed"))))
        ]
    if selected == "closed_loop_count":
        return [
            str(component["component_id"])
            for component in components
            if bool(component["closed"])
        ]
    if selected == "knotted_component_count":
        return [
            str(component["component_id"])
            for component in components
            if int(component.get("knot_count", 0)) > 0
        ]
    raise ValueError(f"unsupported topology string query_id: {query_id}")


def _build_crossing_specs(
    *,
    groups: Sequence[Mapping[str, Any]],
    components: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Build symbolic crossing specs for knots and linked pairs."""

    component_by_id = {str(component["component_id"]): dict(component) for component in components}
    crossings: List[Dict[str, Any]] = []
    for group in groups:
        if str(group["group_type"]) == "tangled_rope_bundle":
            continue
        if str(group["group_type"]) == "single_component":
            component_id = str(group["component_ids"][0])
            component = component_by_id[component_id]
            knot_count = int(component.get("knot_count", 0))
            for knot_index in range(1, int(knot_count) + 1):
                crossings.append(
                    {
                        "crossing_id": f"crossing_{len(crossings) + 1}",
                        "crossing_type": "self_knot",
                        "component_ids": [str(component["component_id"])],
                        "over_component_id": str(component["component_id"]),
                        "linked_pair_id": None,
                        "knot_index": int(knot_index),
                        "knot_count_on_component": int(knot_count),
                    }
                )
            continue
        if str(group["group_type"]) != "linked_pair":
            continue
        left_id, right_id = [str(value) for value in group["component_ids"]]
        pair_id = str(group["linked_pair_id"])
        for crossing_index, over_component_id in enumerate((left_id, right_id), start=1):
            crossings.append(
                {
                    "crossing_id": f"crossing_{len(crossings) + 1}",
                    "crossing_type": "inter_component_link",
                    "component_ids": [left_id, right_id],
                    "over_component_id": str(over_component_id),
                    "under_component_id": right_id if str(over_component_id) == left_id else left_id,
                    "linked_pair_id": str(pair_id),
                    "pair_crossing_index": int(crossing_index),
                    "component_sides": [
                        str(component_by_id[left_id].get("pair_side")),
                        str(component_by_id[right_id].get("pair_side")),
                    ],
                }
            )
    return crossings


def build_string_topology_dataset_for_variant(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleStringTopologyDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one deterministic topology string-component dataset."""

    selected_variant = str(query_id)
    if selected_variant not in set(SUPPORTED_PUZZLE_STRING_TOPOLOGY_QUERY_IDS):
        raise ValueError(f"unsupported topology string query_id: {query_id}")

    rng = spawn_rng(int(instance_seed), f"{task_id}.string_topology_dataset")
    count_spec = _resolve_target_and_distractor_counts(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        defaults=defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
    )
    target_answer = int(count_spec["target_count"])
    distractor_count = int(count_spec["distractor_count"])
    visual_group_count = int(count_spec["object_count"])
    visual_group_count_range = list(count_spec["object_count_range"])
    component_count_range = list(count_spec["object_count_range"])

    groups, components = _build_component_pool(
        query_id=str(selected_variant),
        target_answer=int(target_answer),
        visual_group_count=int(visual_group_count),
        rng=rng,
    )
    crossing_specs = _build_crossing_specs(groups=groups, components=components)
    component_count = len(components)
    open_rope_count = sum(1 for component in components if bool(component.get("open_ended")))
    closed_loop_count = sum(1 for component in components if bool(component["closed"]))
    knotted_component_count = sum(1 for component in components if int(component.get("knot_count", 0)) > 0)
    supporting_item_ids = _supporting_item_ids_for_variant(
        query_id=str(selected_variant),
        components=components,
        groups=groups,
        crossings=crossing_specs,
    )
    answer_value = len(supporting_item_ids)
    if int(answer_value) != int(target_answer):
        raise RuntimeError("string topology dataset target-answer construction drifted")

    return {
        "component_specs": [dict(component) for component in components],
        "visual_group_specs": [dict(group) for group in groups],
        "crossing_specs": [dict(crossing) for crossing in crossing_specs],
        "component_count": int(component_count),
        "component_count_range": list(component_count_range),
        "visual_group_count": int(len(groups)),
        "visual_group_count_range": list(visual_group_count_range),
        "object_count": int(component_count),
        "object_count_range": list(count_spec["object_count_range"]),
        "object_count_probabilities": dict(count_spec["object_count_probabilities"]),
        "target_count": int(target_answer),
        "target_answer": int(target_answer),
        "target_count_range": list(count_spec["target_count_range"]),
        "target_count_probabilities": dict(count_spec["target_count_probabilities"]),
        "distractor_count": int(distractor_count),
        "distractor_count_range": list(count_spec["distractor_count_range"]),
        "distractor_count_probabilities": dict(count_spec["distractor_count_probabilities"]),
        "open_rope_count": int(open_rope_count),
        "open_rope_count_range": list(count_spec["target_count_range"]),
        "closed_loop_count": int(closed_loop_count),
        "closed_loop_count_range": list(count_spec["target_count_range"]),
        "knotted_component_count": int(knotted_component_count),
        "knotted_component_count_range": list(count_spec["target_count_range"]),
        "target_answer_support": [int(value) for value in count_spec["target_count_support"]],
        "target_answer_probabilities": dict(count_spec["target_answer_probabilities"]),
        "answer_value": int(answer_value),
        "supporting_item_ids": [str(value) for value in supporting_item_ids],
        "question_format": "string_component_count",
        "view_family": "topology_string_component_count",
        "topology_rule": "crossings_do_not_merge_components_over_under_recorded",
        "solver_trace": {
            "query_id": str(selected_variant),
            "answer_value": int(answer_value),
            "supporting_item_ids": [str(value) for value in supporting_item_ids],
            "component_count": int(component_count),
            "visual_group_count": int(len(groups)),
            "object_count": int(component_count),
            "target_count": int(target_answer),
            "target_answer": int(target_answer),
            "distractor_count": int(distractor_count),
            "open_rope_count": int(open_rope_count),
            "closed_loop_count": int(closed_loop_count),
            "knotted_component_count": int(knotted_component_count),
            "topology_rule": "crossings_do_not_merge_components_over_under_recorded",
        },
    }


__all__ = [
    "PuzzleStringTopologyDefaults",
    "PuzzleStringTopologyRenderParams",
    "SUPPORTED_PUZZLE_STRING_TOPOLOGY_SCENE_VARIANTS",
    "SUPPORTED_PUZZLE_STRING_TOPOLOGY_QUERY_IDS",
    "build_string_topology_dataset_for_variant",
    "resolve_string_topology_render_params",
    "resolve_string_topology_scene_variant",
    "resolve_string_topology_query_id",
]
