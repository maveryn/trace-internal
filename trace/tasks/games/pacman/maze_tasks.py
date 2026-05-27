"""Games Pac-Man tasks over a visible maze route."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.complexity import build_games_pacman_maze_complexity
from ..shared.fixed_query_task import FixedQueryVariantTaskMixin, rewrite_public_query_output
from ..shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from ..shared.pacman_common import (
    PACMAN_GHOST_COLOR_KEYS,
    PACMAN_ITEM_KINDS,
    PACMAN_ITEM_LABELS,
    SUPPORTED_PACMAN_QUERY_VARIANTS,
    SUPPORTED_PACMAN_SCENE_VARIANTS,
    SUPPORTED_PACMAN_STYLE_VARIANTS,
    Coord,
    PacmanGhost,
    PacmanItem,
    PacmanSample,
    all_grid_coords,
    grid_neighbors,
    ghost_entity_id,
    item_entity_id,
    pellet_entity_id,
    sorted_coords,
    validate_pacman_sample,
    visible_ghost_trace,
    visible_pellet_trace,
)
from ..shared.pacman_scene import PacmanRenderParams, render_pacman_scene
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_variant
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_pacman_maze_base"
ROUTE_PELLET_COUNT_QUERY_VARIANTS: Tuple[str, ...] = (
    "path_pellet_count",
    "pellet_count_before_ghost",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible Pac-Man maze scenes."""

    row_count_support: Tuple[int, ...] = (7, 8, 9)
    col_count_support: Tuple[int, ...] = (9, 11, 13)
    path_pellet_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    pellet_count_before_ghost_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    next_item_label_support: Tuple[str, ...] = PACMAN_ITEM_LABELS
    item_count_support: Tuple[int, ...] = (5, 6)
    canvas_width: int = 980
    canvas_height: int = 760
    panel_margin_px: int = 38
    maze_width_px: int = 840
    maze_height_px: int = 620
    wall_gap_px: int = 2
    wall_outline_width_px: int = 1
    pellet_radius_px: int = 10
    item_radius_px: int = 19
    ghost_radius_px: int = 18
    route_width_px: int = 8
    item_label_font_size_px: int = 23


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Pac-Man instance."""

    query_variant: str
    scene_variant: str
    style_variant: str
    row_count: int
    col_count: int
    target_answer: int | None
    target_label: str | None
    item_count: int
    target_answer_support: Tuple[int, ...]
    target_label_support: Tuple[str, ...]
    query_variant_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    row_count_probabilities: Dict[str, float]
    col_count_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    target_label_probabilities: Dict[str, float]
    item_count_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "pacman")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="pacman")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="pacman", apply_prob=0.5)


def _resolve_query_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_query_variants: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced Pac-Man query variant."""

    return resolve_games_query_variant(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported_query_variants,
    )


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named Pac-Man axis."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(value) for value in supported],
    )


def _string_support(
    params: Mapping[str, Any],
    *,
    key: str,
    fallback: Sequence[str],
) -> Tuple[str, ...]:
    """Resolve a string support list from params/defaults."""

    raw = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), tuple(fallback)))
    if raw is None:
        raw = tuple(fallback)
    values = (str(raw),) if isinstance(raw, str) else tuple(str(value) for value in raw)
    values = tuple(value for value in values if value)
    if not values:
        raise ValueError(f"{key} must contain at least one label")
    return values


def _resolve_label_choice(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[str],
    namespace: str,
    balanced_flag_key: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one label-valued support choice."""

    support = _string_support(params, key=str(support_key), fallback=fallback_support)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = str(explicit)
        if value not in support:
            raise ValueError(f"{explicit_key}={value!r} is not in {support_key}")
        return value, {str(item): (1.0 if str(item) == value else 0.0) for item in support}
    probabilities = {str(item): 1.0 / float(len(support)) for item in support}
    sampling_index = params.get("_sample_cursor")
    balanced = bool(params.get(str(balanced_flag_key), group_default(_GEN_DEFAULTS, str(balanced_flag_key), True)))
    if balanced and sampling_index is not None:
        return str(support[abs(int(sampling_index)) % len(support)]), probabilities
    rng = spawn_rng(int(instance_seed), str(namespace))
    return str(rng.choice(tuple(support))), probabilities


def _uses_uniform_query_cycle(
    params: Mapping[str, Any],
    probabilities: Mapping[str, float],
    *,
    supported_query_variants: Sequence[str],
) -> bool:
    """Return true when the query axis uses the default balanced cycle."""

    if params.get("query_variant") is not None or params.get("query_variant") is not None:
        return False
    enabled = bool(params.get("balanced_query_variant_sampling", group_default(_GEN_DEFAULTS, "balanced_query_variant_sampling", True)))
    if not enabled:
        return False
    positives = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if len(positives) != len(tuple(supported_query_variants)):
        return False
    return max(positives) - min(positives) <= 1e-9


def _params_for_query_occurrence_cycle(
    params: Mapping[str, Any],
    *,
    query_variant_probabilities: Mapping[str, float],
    supported_query_variants: Sequence[str],
) -> Dict[str, Any]:
    """Use a per-query occurrence index for balanced inner axes."""

    cycle_params = dict(params)
    sampling_index = params.get("_sample_cursor")
    if sampling_index is None:
        return cycle_params
    if not _uses_uniform_query_cycle(
        params,
        query_variant_probabilities,
        supported_query_variants=supported_query_variants,
    ):
        return cycle_params
    cycle_params["_sample_cursor"] = abs(int(sampling_index)) // max(1, len(tuple(supported_query_variants)))
    return cycle_params


def _resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    supported_query_variants: Sequence[str],
) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Pac-Man instance."""

    query_variant, query_variant_probabilities = _resolve_query_variant(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_variants=supported_query_variants,
    )
    answer_cycle_params = _params_for_query_occurrence_cycle(
        params,
        query_variant_probabilities=query_variant_probabilities,
        supported_query_variants=supported_query_variants,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_PACMAN_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_PACMAN_STYLE_VARIANTS,
    )
    row_count, row_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="row_count_support",
        explicit_key="row_count",
        fallback_support=_DEFAULTS.row_count_support,
        namespace=f"{TASK_ID}.row_count",
        balanced_flag_key="balanced_row_count_sampling",
        namespace_support_permutation=True,
    )
    col_count, col_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="col_count_support",
        explicit_key="col_count",
        fallback_support=_DEFAULTS.col_count_support,
        namespace=f"{TASK_ID}.col_count",
        balanced_flag_key="balanced_col_count_sampling",
        namespace_support_permutation=True,
    )

    target_answer = None
    target_answer_probabilities: Dict[str, float] = {}
    if str(query_variant) == "path_pellet_count":
        target_answer_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="path_pellet_count_support",
            fallback=_DEFAULTS.path_pellet_count_support,
        )
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="path_pellet_count_support",
            explicit_key="target_answer",
            fallback_support=_DEFAULTS.path_pellet_count_support,
            namespace=f"{TASK_ID}.target_answer.path_pellet_count",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
    elif str(query_variant) == "pellet_count_before_ghost":
        target_answer_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key="pellet_count_before_ghost_support",
            fallback=_DEFAULTS.pellet_count_before_ghost_support,
        )
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="pellet_count_before_ghost_support",
            explicit_key="target_answer",
            fallback_support=_DEFAULTS.pellet_count_before_ghost_support,
            namespace=f"{TASK_ID}.target_answer.pellet_count_before_ghost",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
    else:
        target_answer_support = tuple(_DEFAULTS.path_pellet_count_support)

    target_label = None
    target_label_probabilities: Dict[str, float] = {}
    target_label_support = _string_support(
        params,
        key="next_item_label_support",
        fallback=_DEFAULTS.next_item_label_support,
    )
    item_count = 0
    item_count_probabilities: Dict[str, float] = {}
    if str(query_variant) == "next_item_label":
        item_count, item_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            gen_defaults=_GEN_DEFAULTS,
            support_key="item_count_support",
            explicit_key="item_count",
            fallback_support=_DEFAULTS.item_count_support,
            namespace=f"{TASK_ID}.item_count",
            balanced_flag_key="balanced_item_count_sampling",
            namespace_support_permutation=True,
        )
        target_label, target_label_probabilities = _resolve_label_choice(
            instance_seed=int(instance_seed),
            params=answer_cycle_params,
            support_key="next_item_label_support",
            explicit_key="target_label",
            fallback_support=_DEFAULTS.next_item_label_support,
            namespace=f"{TASK_ID}.target_label.next_item_label",
            balanced_flag_key="balanced_target_label_sampling",
        )
        item_count = max(int(item_count), PACMAN_ITEM_LABELS.index(str(target_label)) + 1)

    return _ResolvedAxes(
        query_variant=str(query_variant),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        row_count=int(row_count),
        col_count=int(col_count),
        target_answer=None if target_answer is None else int(target_answer),
        target_label=None if target_label is None else str(target_label),
        item_count=int(item_count),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        target_label_support=tuple(str(value) for value in target_label_support),
        query_variant_probabilities=dict(query_variant_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        row_count_probabilities=dict(row_count_probabilities),
        col_count_probabilities=dict(col_count_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        target_label_probabilities=dict(target_label_probabilities),
        item_count_probabilities=dict(item_count_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> PacmanRenderParams:
    """Resolve Pac-Man rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace="games.pacman.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.pacman.layout",
        ),
        unit_scale_meta,
    )
    return PacmanRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        maze_width_px=scale_games_px(params.get("maze_width_px", group_default(_RENDER_DEFAULTS, "maze_width_px", _DEFAULTS.maze_width_px)), unit_scale, min_px=420),
        maze_height_px=scale_games_px(params.get("maze_height_px", group_default(_RENDER_DEFAULTS, "maze_height_px", _DEFAULTS.maze_height_px)), unit_scale, min_px=310),
        wall_gap_px=scale_games_px(params.get("wall_gap_px", group_default(_RENDER_DEFAULTS, "wall_gap_px", _DEFAULTS.wall_gap_px)), unit_scale, min_px=1),
        wall_outline_width_px=scale_games_px(params.get("wall_outline_width_px", group_default(_RENDER_DEFAULTS, "wall_outline_width_px", _DEFAULTS.wall_outline_width_px)), unit_scale, min_px=1),
        pellet_radius_px=scale_games_px(params.get("pellet_radius_px", group_default(_RENDER_DEFAULTS, "pellet_radius_px", _DEFAULTS.pellet_radius_px)), unit_scale, min_px=5),
        item_radius_px=scale_games_px(params.get("item_radius_px", group_default(_RENDER_DEFAULTS, "item_radius_px", _DEFAULTS.item_radius_px)), unit_scale, min_px=9),
        ghost_radius_px=scale_games_px(params.get("ghost_radius_px", group_default(_RENDER_DEFAULTS, "ghost_radius_px", _DEFAULTS.ghost_radius_px)), unit_scale, min_px=9),
        route_width_px=scale_games_px(params.get("route_width_px", group_default(_RENDER_DEFAULTS, "route_width_px", _DEFAULTS.route_width_px)), unit_scale, min_px=4),
        item_label_font_size_px=scale_games_px(params.get("item_label_font_size_px", group_default(_RENDER_DEFAULTS, "item_label_font_size_px", _DEFAULTS.item_label_font_size_px)), unit_scale, min_px=12),
        layout_jitter_meta=layout_jitter,
    )


def _sample_route(*, rng, rows: int, cols: int, length: int) -> Tuple[Coord, ...]:
    """Sample one self-avoiding orthogonal route."""

    inner_rows = tuple(range(1, int(rows) - 1))
    inner_cols = tuple(range(1, int(cols) - 1))
    for _restart in range(96):
        start = (int(rng.choice(inner_rows)), 1)
        route = [start]
        seen = {start}
        while len(route) < int(length):
            current = route[-1]
            candidates = [coord for coord in grid_neighbors(current, rows=rows, cols=cols) if coord not in seen]
            if not candidates:
                break
            rng.shuffle(candidates)
            candidates.sort(key=lambda coord: (0 if int(coord[1]) >= int(current[1]) else 1, rng.random()))
            next_coord = tuple(candidates[0])
            route.append(next_coord)
            seen.add(next_coord)
        if len(route) >= int(length):
            return tuple(route[: int(length)])
    raise ValueError("failed to sample Pac-Man route")


def _expand_open_cells(
    *,
    rng,
    rows: int,
    cols: int,
    route_coords: Sequence[Coord],
    min_open_cells: int,
) -> Tuple[Coord, ...]:
    """Expand a connected open-cell set around the route."""

    open_set = {tuple(coord) for coord in route_coords}
    target = min(
        max(int(min_open_cells), len(open_set)),
        max(1, (int(rows) - 2) * (int(cols) - 2)),
    )
    guard = 0
    while len(open_set) < int(target) and guard < int(rows) * int(cols) * 8:
        guard += 1
        source = tuple(rng.choice(tuple(sorted(open_set))))
        candidates = [coord for coord in grid_neighbors(source, rows=rows, cols=cols) if coord not in open_set]
        if not candidates:
            continue
        open_set.add(tuple(rng.choice(candidates)))
    if len(open_set) < int(target):
        raise ValueError("failed to expand Pac-Man open cells")
    return sorted_coords(open_set)


def _wall_cells(*, rows: int, cols: int, open_cells: Sequence[Coord]) -> Tuple[Coord, ...]:
    """Return wall cells as every grid cell not marked open."""

    open_set = {tuple(coord) for coord in open_cells}
    return sorted_coords(coord for coord in all_grid_coords(rows, cols) if coord not in open_set)


def _available_open_cells(
    open_cells: Sequence[Coord],
    *,
    excluded: Sequence[Coord] = (),
) -> Tuple[Coord, ...]:
    """Return open cells excluding a set."""

    excluded_set = {tuple(coord) for coord in excluded}
    return sorted_coords(coord for coord in open_cells if tuple(coord) not in excluded_set)


def _sample_decorative_ghosts(
    *,
    rng,
    open_cells: Sequence[Coord],
    excluded: Sequence[Coord],
    start_index: int = 1,
    min_count: int = 1,
    max_count: int = 3,
) -> Tuple[PacmanGhost, ...]:
    """Sample off-query ghosts used as Pac-Man scene decoration."""

    candidates = list(_available_open_cells(open_cells, excluded=excluded))
    rng.shuffle(candidates)
    if not candidates:
        return tuple()
    count = min(len(candidates), int(rng.randint(int(min_count), int(max_count) + 1)))
    ghosts: list[PacmanGhost] = []
    for offset, coord in enumerate(candidates[:count]):
        color_key = str(PACMAN_GHOST_COLOR_KEYS[(int(start_index) + int(offset)) % len(PACMAN_GHOST_COLOR_KEYS)])
        ghosts.append(
            PacmanGhost(
                ghost_id=ghost_entity_id(int(start_index) + int(offset)),
                coord=tuple(coord),
                color_key=color_key,
                is_stop_ghost=False,
            )
        )
    return tuple(ghosts)


def _sample_path_pellet_count_scene(*, rng, axes: _ResolvedAxes) -> PacmanSample:
    """Construct a route pellet-count scene."""

    target = int(axes.target_answer or 3)
    rows, cols = int(axes.row_count), int(axes.col_count)
    route_len = min(max(target + int(rng.randint(4, 8)), target + 1), max(8, (rows - 2) * (cols - 2) - 2))
    route = _sample_route(rng=rng, rows=rows, cols=cols, length=route_len)
    min_open = len(route) + target + int(rng.randint(8, 16))
    open_cells = _expand_open_cells(rng=rng, rows=rows, cols=cols, route_coords=route, min_open_cells=min_open)
    route_candidates = list(route[1:])
    if len(route_candidates) < target:
        raise ValueError("route too short for target pellets")
    rng.shuffle(route_candidates)
    counted_pellets = sorted_coords(route_candidates[:target])
    off_route = list(_available_open_cells(open_cells, excluded=route))
    rng.shuffle(off_route)
    distractor_count = min(len(off_route), int(rng.randint(4, 8)))
    pellets = sorted_coords(tuple(counted_pellets) + tuple(off_route[:distractor_count]))
    ghosts = _sample_decorative_ghosts(
        rng=rng,
        open_cells=open_cells,
        excluded=tuple(route) + tuple(pellets),
        start_index=1,
    )
    evidence_ids = tuple(pellet_entity_id(coord) for coord in counted_pellets)
    sample = PacmanSample(
        row_count=rows,
        col_count=cols,
        query_variant=str(axes.query_variant),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        open_cells=tuple(open_cells),
        wall_cells=_wall_cells(rows=rows, cols=cols, open_cells=open_cells),
        pacman_coord=tuple(route[0]),
        route_coords=tuple(route),
        pellets=tuple(pellets),
        items=tuple(),
        ghosts=ghosts,
        answer=int(target),
        target_answer=int(target),
        evidence_entity_ids=evidence_ids,
        construction_mode="count_visible_route_pellets",
    )
    validate_pacman_sample(sample)
    return sample


def _sample_pellet_count_before_ghost_scene(*, rng, axes: _ResolvedAxes) -> PacmanSample:
    """Construct a route-count scene that stops at the first route ghost."""

    target = int(axes.target_answer or 2)
    rows, cols = int(axes.row_count), int(axes.col_count)
    route_len = min(max(target + int(rng.randint(5, 8)), target + 3), max(8, (rows - 2) * (cols - 2) - 2))
    route = _sample_route(rng=rng, rows=rows, cols=cols, length=route_len)
    min_open = len(route) + target + int(rng.randint(10, 18))
    open_cells = _expand_open_cells(rng=rng, rows=rows, cols=cols, route_coords=route, min_open_cells=min_open)
    if len(route) <= target + 1:
        raise ValueError("route too short for ghost stop query")
    counted_pellets = tuple(tuple(coord) for coord in route[1 : target + 1])
    stop_coord = tuple(route[target + 1])
    after_route = list(route[target + 2 :])
    rng.shuffle(after_route)
    after_count = min(len(after_route), int(rng.randint(2, 5)))
    off_route = list(_available_open_cells(open_cells, excluded=tuple(route)))
    rng.shuffle(off_route)
    off_route_count = min(len(off_route), int(rng.randint(3, 7)))
    pellets = sorted_coords(tuple(counted_pellets) + tuple(after_route[:after_count]) + tuple(off_route[:off_route_count]))
    stop_ghost = PacmanGhost(
        ghost_id=ghost_entity_id("route_stop"),
        coord=stop_coord,
        color_key=str(PACMAN_GHOST_COLOR_KEYS[0]),
        is_stop_ghost=True,
    )
    decorative_ghosts = _sample_decorative_ghosts(
        rng=rng,
        open_cells=open_cells,
        excluded=tuple(route) + tuple(pellets) + (stop_coord,),
        start_index=1,
        min_count=1,
        max_count=3,
    )
    ghosts = (stop_ghost,) + decorative_ghosts
    evidence_ids = tuple(pellet_entity_id(coord) for coord in counted_pellets) + (str(stop_ghost.ghost_id),)
    sample = PacmanSample(
        row_count=rows,
        col_count=cols,
        query_variant=str(axes.query_variant),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        open_cells=tuple(open_cells),
        wall_cells=_wall_cells(rows=rows, cols=cols, open_cells=open_cells),
        pacman_coord=tuple(route[0]),
        route_coords=tuple(route),
        pellets=tuple(pellets),
        items=tuple(),
        ghosts=ghosts,
        answer=int(target),
        target_answer=int(target),
        evidence_entity_ids=evidence_ids,
        construction_mode="count_route_pellets_before_first_ghost",
    )
    validate_pacman_sample(sample)
    return sample


def _sample_next_item_label_scene(*, rng, axes: _ResolvedAxes) -> PacmanSample:
    """Construct an item-order scene with exactly one first reached item."""

    target_label = str(axes.target_label or "A")
    item_count = max(int(axes.item_count or 5), PACMAN_ITEM_LABELS.index(target_label) + 1)
    rows, cols = int(axes.row_count), int(axes.col_count)
    route_len = min(max(item_count + 5, 10), max(10, (rows - 2) * (cols - 2) - 2))
    route = _sample_route(rng=rng, rows=rows, cols=cols, length=route_len)
    min_open = len(route) + item_count + int(rng.randint(10, 18))
    open_cells = _expand_open_cells(rng=rng, rows=rows, cols=cols, route_coords=route, min_open_cells=min_open)
    labels = tuple(PACMAN_ITEM_LABELS[:item_count])
    label_to_coord: Dict[str, Coord] = {}
    label_to_kind: Dict[str, str] = {}
    label_to_coord[target_label] = tuple(route[2])
    label_to_kind[target_label] = str(rng.choice(PACMAN_ITEM_KINDS))

    later_route_cells = list(route[4:])
    off_route_cells = list(_available_open_cells(open_cells, excluded=route))
    rng.shuffle(later_route_cells)
    rng.shuffle(off_route_cells)
    used = {tuple(label_to_coord[target_label])}
    later_cursor = 0
    off_cursor = 0
    for label in labels:
        label = str(label)
        if label == target_label:
            continue
        use_later_route = later_cursor < len(later_route_cells) and rng.random() < 0.48
        if use_later_route:
            coord = tuple(later_route_cells[later_cursor])
            later_cursor += 1
        else:
            if off_cursor >= len(off_route_cells):
                if later_cursor >= len(later_route_cells):
                    raise ValueError("not enough open cells for labeled items")
                coord = tuple(later_route_cells[later_cursor])
                later_cursor += 1
            else:
                coord = tuple(off_route_cells[off_cursor])
                off_cursor += 1
        if coord in used:
            raise ValueError("duplicate Pac-Man item coordinate")
        used.add(coord)
        label_to_coord[label] = coord
        label_to_kind[label] = str(PACMAN_ITEM_KINDS[(PACMAN_ITEM_LABELS.index(label) + int(rng.randrange(len(PACMAN_ITEM_KINDS)))) % len(PACMAN_ITEM_KINDS)])

    available_for_pellets = list(_available_open_cells(open_cells, excluded=tuple(route) + tuple(used)))
    rng.shuffle(available_for_pellets)
    pellet_count = min(len(available_for_pellets), int(rng.randint(5, 9)))
    pellets = sorted_coords(available_for_pellets[:pellet_count])
    items = tuple(
        PacmanItem(
            label=str(label),
            item_id=item_entity_id(str(label)),
            coord=tuple(label_to_coord[str(label)]),
            kind=str(label_to_kind[str(label)]),
            is_answer=bool(str(label) == target_label),
        )
        for label in labels
    )
    ghosts = _sample_decorative_ghosts(
        rng=rng,
        open_cells=open_cells,
        excluded=tuple(route) + tuple(pellets) + tuple(used),
        start_index=1,
    )
    sample = PacmanSample(
        row_count=rows,
        col_count=cols,
        query_variant=str(axes.query_variant),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        open_cells=tuple(open_cells),
        wall_cells=_wall_cells(rows=rows, cols=cols, open_cells=open_cells),
        pacman_coord=tuple(route[0]),
        route_coords=tuple(route),
        pellets=tuple(pellets),
        items=items,
        ghosts=ghosts,
        answer=str(target_label),
        target_answer=str(target_label),
        evidence_entity_ids=(item_entity_id(target_label),),
        construction_mode="first_labeled_bonus_on_highlighted_route",
    )
    validate_pacman_sample(sample)
    return sample


def _sample_scene(*, rng, axes: _ResolvedAxes) -> PacmanSample:
    """Construct one Pac-Man scene for the requested query."""

    query = str(axes.query_variant)
    if query == "path_pellet_count":
        return _sample_path_pellet_count_scene(rng=rng, axes=axes)
    if query == "next_item_label":
        return _sample_next_item_label_scene(rng=rng, axes=axes)
    if query == "pellet_count_before_ghost":
        return _sample_pellet_count_before_ghost_scene(rng=rng, axes=axes)
    raise ValueError(f"unsupported Pac-Man query_variant: {query}")


def _build_prompt_json_examples(query_variant: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Pac-Man JSON output."""

    if str(query_variant) == "next_item_label":
        answer_value: str | int = "D"
        evidence_value = [[490, 286, 528, 324]]
    elif str(query_variant) == "pellet_count_before_ghost":
        answer_value = 4
        evidence_value = [[350, 212, 360, 222], [410, 272, 420, 282], [530, 260, 566, 296]]
    else:
        answer_value = 5
        evidence_value = [[310, 204, 320, 214], [364, 204, 374, 214]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesPacmanMazeTask:
    """Return one grounded query over a visible Pac-Man maze."""

    task_id = TASK_ID
    domain = "games"
    task_group = "pacman"
    supported_query_variants: Tuple[str, ...] = SUPPORTED_PACMAN_QUERY_VARIANTS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(
            int(instance_seed),
            params=params,
            supported_query_variants=tuple(self.supported_query_variants),
        )
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: PacmanSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid Pac-Man maze after {max_attempts} attempts")

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_pacman_scene(
            row_count=int(sampled_scene.row_count),
            col_count=int(sampled_scene.col_count),
            open_cells=sampled_scene.open_cells,
            wall_cells=sampled_scene.wall_cells,
            pacman_coord=sampled_scene.pacman_coord,
            route_coords=sampled_scene.route_coords,
            pellets=sampled_scene.pellets,
            items=sampled_scene.items,
            ghosts=sampled_scene.ghosts,
            background=background,
            scene_variant=str(axes.scene_variant),
            style_variant=str(axes.style_variant),
            params=render_params,
        )
        evidence_bboxes = [
            list(rendered_scene.render_map["entity_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.evidence_entity_ids
        ]
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
                "object_description_compact_maze",
                "object_description_wide_maze",
                "answer_hint_path_pellet_count",
                "evidence_hint_path_pellet_count",
                "answer_hint_next_item_label",
                "evidence_hint_next_item_label",
                "answer_hint_pellet_count_before_ghost",
                "evidence_hint_pellet_count_before_ghost",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_variant))
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_variant)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_variant)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = (
            TypedValue(type="string", value=str(sampled_scene.answer))
            if str(axes.query_variant) == "next_item_label"
            else TypedValue(type="integer", value=int(sampled_scene.answer))
        )
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_pacman_maze_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            scene_variant=str(axes.scene_variant),
            query_variant=str(axes.query_variant),
            row_count=int(sampled_scene.row_count),
            col_count=int(sampled_scene.col_count),
            route_length=len(sampled_scene.route_coords),
            pellet_count=len(sampled_scene.pellets),
            item_count=len(sampled_scene.items),
            ghost_count=len(sampled_scene.ghosts),
            target_answer=sampled_scene.answer,
            evidence_count=len(sampled_scene.evidence_entity_ids),
        )
        item_trace = [
            {
                "label": str(item.label),
                "kind": str(item.kind),
                "coord": [int(item.coord[0]), int(item.coord[1])],
                "entity_id": item_entity_id(str(item.label)),
                "is_answer": bool(item.is_answer),
            }
            for item in sampled_scene.items
        ]
        ghost_trace = list(visible_ghost_trace(sampled_scene.ghosts))
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_pacman_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "query_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "row_count": int(sampled_scene.row_count),
                    "col_count": int(sampled_scene.col_count),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                },
            },
            "query_spec": {
                "query_variant": str(axes.query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "query_variant": str(axes.query_variant),
                    "style_variant": str(axes.style_variant),
                    "row_count": int(sampled_scene.row_count),
                    "col_count": int(sampled_scene.col_count),
                    "route_length": len(sampled_scene.route_coords),
                    "pellet_count": len(sampled_scene.pellets),
                    "item_count": len(sampled_scene.items),
                    "ghost_count": len(sampled_scene.ghosts),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "query_variant_probabilities": dict(axes.query_variant_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "row_count_probabilities": dict(axes.row_count_probabilities),
                    "col_count_probabilities": dict(axes.col_count_probabilities),
                    "target_answer": sampled_scene.target_answer,
                    "target_answer_support": [int(value) for value in axes.target_answer_support],
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    "target_label": axes.target_label,
                    "target_label_support": [str(value) for value in axes.target_label_support],
                    "target_label_probabilities": dict(axes.target_label_probabilities),
                    "item_count_probabilities": dict(axes.item_count_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_variant": str(axes.query_variant),
                "query_variant": str(axes.query_variant),
                "style_variant": str(axes.style_variant),
                "row_count": int(sampled_scene.row_count),
                "col_count": int(sampled_scene.col_count),
                "open_cells": [[int(row), int(col)] for row, col in sampled_scene.open_cells],
                "wall_cells": [[int(row), int(col)] for row, col in sampled_scene.wall_cells],
                "pacman_coord": [int(sampled_scene.pacman_coord[0]), int(sampled_scene.pacman_coord[1])],
                "route_coords": [[int(row), int(col)] for row, col in sampled_scene.route_coords],
                "pellets": list(visible_pellet_trace(sampled_scene.pellets)),
                "items": item_trace,
                "ghosts": ghost_trace,
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
            },
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant=str(axes.query_variant),
            scene_id="pacman",
            query_id=str(axes.query_variant),
        )


@register_task
class GamesPacmanRoutePelletCountTask(GamesPacmanMazeTask):
    """Count route pellets, with or without a first-ghost stopping condition."""

    task_id = "task_games__pacman__route_pellet_count"
    supported_query_variants = ROUTE_PELLET_COUNT_QUERY_VARIANTS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        output = super().generate(int(instance_seed), params=params, max_attempts=int(max_attempts))
        query_id = str(output.query_id)
        payload = output.trace_payload if isinstance(output.trace_payload, Mapping) else {}
        probabilities = None
        query_spec = payload.get("query_spec") if isinstance(payload, Mapping) else None
        if isinstance(query_spec, Mapping):
            spec_params = query_spec.get("params")
            if isinstance(spec_params, Mapping):
                raw_probabilities = spec_params.get("query_variant_probabilities")
                if isinstance(raw_probabilities, Mapping):
                    probabilities = {str(key): float(value) for key, value in raw_probabilities.items()}
        return rewrite_public_query_output(output, query_id=query_id, query_variant_probabilities=probabilities)


@register_task
class GamesPacmanNextItemLabelTask(FixedQueryVariantTaskMixin, GamesPacmanMazeTask):
    """Choose the first labeled bonus item reached on the highlighted route."""

    task_id = "task_games__pacman__next_item_label"
    fixed_query_variant = "next_item_label"
    supported_query_variants = ("next_item_label",)


__all__ = [
    "GamesPacmanMazeTask",
    "GamesPacmanNextItemLabelTask",
    "GamesPacmanRoutePelletCountTask",
]
