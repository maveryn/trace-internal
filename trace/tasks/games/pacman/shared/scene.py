"""Scene-local primitives for Pac-Man maze tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import group_default, required_group_defaults
from trace.tasks.shared.font_assets import get_font_family_record, sample_font_family
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support
from trace.tasks.games.shared.layout import attach_games_unit_size_jitter, resolve_games_layout_jitter, resolve_games_unit_size_scale, scale_games_px
from .common import (
    PACMAN_GHOST_COLOR_KEYS,
    PACMAN_ITEM_KINDS,
    PACMAN_ITEM_LABELS,
    SUPPORTED_PACMAN_QUERY_IDS,
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
    visible_item_trace,
    visible_pellet_trace,
)
from .rendering import PacmanRenderParams, render_pacman_scene
from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.games.shared.scene_style import make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "pacman"
ROUTE_PELLET_COUNT_QUERY_IDS: Tuple[str, ...] = (
    "path_pellet_count",
    "pellet_count_before_ghost",
)
ROUTE_SCORE_BONUS_VALUE_SUPPORT: Tuple[int, ...] = (2, 3, 5, 10)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable scene/render fallback defaults for visible Pac-Man maze scenes."""

    row_count_support: Tuple[int, ...] = (7, 8, 9)
    col_count_support: Tuple[int, ...] = (9, 11, 13)
    path_pellet_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    pellet_count_before_ghost_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    route_score_on_route_pellet_count_support: Tuple[int, ...] = (1, 2, 3, 4)
    route_score_on_route_bonus_count_support: Tuple[int, ...] = (1, 2, 3)
    route_score_off_route_bonus_count_support: Tuple[int, ...] = (1, 2, 3)
    route_score_bonus_value_support: Tuple[int, ...] = ROUTE_SCORE_BONUS_VALUE_SUPPORT
    next_item_label_support: Tuple[str, ...] = PACMAN_ITEM_LABELS
    item_count_support: Tuple[int, ...] = (4, 5, 6)
    canvas_width: int = 980
    canvas_height: int = 760
    panel_margin_px: int = 38
    maze_width_px: int = 840
    maze_height_px: int = 620
    wall_gap_px: int = 2
    wall_outline_width_px: int = 1
    pellet_radius_px: int = 13
    item_radius_px: int = 19
    ghost_radius_px: int = 18
    route_width_px: int = 8
    item_label_font_size_px: int = 23


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one Pac-Man instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    row_count: int
    col_count: int
    target_answer: int | None
    target_label: str | None
    item_count: int
    target_answer_support: Tuple[int, ...]
    target_label_support: Tuple[str, ...]
    route_score_on_route_pellet_count_support: Tuple[int, ...]
    route_score_on_route_bonus_count_support: Tuple[int, ...]
    route_score_off_route_bonus_count_support: Tuple[int, ...]
    route_score_bonus_value_support: Tuple[int, ...]
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    row_count_probabilities: Dict[str, float]
    col_count_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    target_label_probabilities: Dict[str, float]
    item_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class GeneratedComponents:
    """Rendered and prompted scene components before public output wrapping."""

    prompt: str
    prompt_variants: Dict[str, str]
    answer_gt: TypedValue
    annotation_gt: TypedValue
    image: Any
    trace_payload: Dict[str, Any]
    query_id: str


_DEFAULTS = _TaskDefaults()
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id="pacman", apply_prob=0.5)


def _resolve_named_axis(
    *,
    gen_defaults: Mapping[str, Any],
    namespace_root: str,
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
        task_id=str(namespace_root),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        namespace=f"{namespace_root}.{namespace}",
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(value) for value in supported],
    )


def _string_support(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    key: str,
    fallback: Sequence[str],
) -> Tuple[str, ...]:
    """Resolve a string support list from params/defaults."""

    raw = params.get(str(key), group_default(gen_defaults, str(key), tuple(fallback)))
    if raw is None:
        raw = tuple(fallback)
    values = (str(raw),) if isinstance(raw, str) else tuple(str(value) for value in raw)
    values = tuple(value for value in values if value)
    if not values:
        raise ValueError(f"{key} must contain at least one label")
    return values


def _resolve_label_choice(
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[str],
    namespace: str,
    balanced_flag_key: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one label-valued support choice."""

    support = _string_support(params, gen_defaults=gen_defaults, key=str(support_key), fallback=fallback_support)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = str(explicit)
        if value not in support:
            raise ValueError(f"{explicit_key}={value!r} is not in {support_key}")
        return value, {str(item): (1.0 if str(item) == value else 0.0) for item in support}
    probabilities = {str(item): 1.0 / float(len(support)) for item in support}
    sampling_index = params.get("_sample_cursor")
    balanced = bool(params.get(str(balanced_flag_key), group_default(gen_defaults, str(balanced_flag_key), True)))
    if balanced and sampling_index is not None:
        return str(support[abs(int(sampling_index)) % len(support)]), probabilities
    rng = spawn_rng(int(instance_seed), str(namespace))
    return str(rng.choice(tuple(support))), probabilities


def resolve_axes(
    instance_seed: int,
    *,
    gen_defaults: Mapping[str, Any],
    namespace: str,
    params: Mapping[str, Any],
    query_id: str,
    query_id_probabilities: Mapping[str, float],
) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one Pac-Man instance."""

    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_PACMAN_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        gen_defaults=gen_defaults,
        namespace_root=str(namespace),
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
        gen_defaults=gen_defaults,
        support_key="row_count_support",
        explicit_key="row_count",
        fallback_support=_DEFAULTS.row_count_support,
        namespace=f"{namespace}.row_count",
        balanced_flag_key="balanced_row_count_sampling",
        namespace_support_permutation=True,
    )
    col_count, col_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        support_key="col_count_support",
        explicit_key="col_count",
        fallback_support=_DEFAULTS.col_count_support,
        namespace=f"{namespace}.col_count",
        balanced_flag_key="balanced_col_count_sampling",
        namespace_support_permutation=True,
    )

    target_answer = None
    target_answer_probabilities: Dict[str, float] = {}
    if str(query_id) == "path_pellet_count":
        target_answer_support = resolve_integer_support(
            params,
            gen_defaults=gen_defaults,
            key="path_pellet_count_support",
            fallback=_DEFAULTS.path_pellet_count_support,
        )
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            support_key="path_pellet_count_support",
            explicit_key="target_answer",
            fallback_support=_DEFAULTS.path_pellet_count_support,
            namespace=f"{namespace}.target_answer.path_pellet_count",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
    elif str(query_id) == "pellet_count_before_ghost":
        target_answer_support = resolve_integer_support(
            params,
            gen_defaults=gen_defaults,
            key="pellet_count_before_ghost_support",
            fallback=_DEFAULTS.pellet_count_before_ghost_support,
        )
        target_answer, target_answer_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            support_key="pellet_count_before_ghost_support",
            explicit_key="target_answer",
            fallback_support=_DEFAULTS.pellet_count_before_ghost_support,
            namespace=f"{namespace}.target_answer.pellet_count_before_ghost",
            balanced_flag_key="balanced_target_answer_sampling",
            namespace_support_permutation=True,
        )
    elif str(query_id) == "route_score_value":
        target_answer_support = tuple()
    else:
        target_answer_support = tuple(_DEFAULTS.path_pellet_count_support)

    route_score_on_route_pellet_count_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="route_score_on_route_pellet_count_support",
        fallback=_DEFAULTS.route_score_on_route_pellet_count_support,
    )
    route_score_on_route_bonus_count_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="route_score_on_route_bonus_count_support",
        fallback=_DEFAULTS.route_score_on_route_bonus_count_support,
    )
    route_score_off_route_bonus_count_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="route_score_off_route_bonus_count_support",
        fallback=_DEFAULTS.route_score_off_route_bonus_count_support,
    )
    route_score_bonus_value_support = resolve_integer_support(
        params,
        gen_defaults=gen_defaults,
        key="route_score_bonus_value_support",
        fallback=_DEFAULTS.route_score_bonus_value_support,
    )

    target_label = None
    target_label_probabilities: Dict[str, float] = {}
    target_label_support = _string_support(
        params,
        gen_defaults=gen_defaults,
        key="next_item_label_support",
        fallback=_DEFAULTS.next_item_label_support,
    )
    item_count = 0
    item_count_probabilities: Dict[str, float] = {}
    if str(query_id) == "next_item_label":
        item_count, item_count_probabilities = resolve_integer_choice(
            instance_seed=int(instance_seed),
            params=params,
            gen_defaults=gen_defaults,
            support_key="item_count_support",
            explicit_key="item_count",
            fallback_support=_DEFAULTS.item_count_support,
            namespace=f"{namespace}.item_count",
            balanced_flag_key="balanced_item_count_sampling",
            namespace_support_permutation=True,
        )
        target_label, target_label_probabilities = _resolve_label_choice(
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            params=params,
            support_key="next_item_label_support",
            explicit_key="target_label",
            fallback_support=_DEFAULTS.next_item_label_support,
            namespace=f"{namespace}.target_label.next_item_label",
            balanced_flag_key="balanced_target_label_sampling",
        )
        item_count = max(int(item_count), PACMAN_ITEM_LABELS.index(str(target_label)) + 1)

    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        row_count=int(row_count),
        col_count=int(col_count),
        target_answer=None if target_answer is None else int(target_answer),
        target_label=None if target_label is None else str(target_label),
        item_count=int(item_count),
        target_answer_support=tuple(int(value) for value in target_answer_support),
        target_label_support=tuple(str(value) for value in target_label_support),
        route_score_on_route_pellet_count_support=tuple(int(value) for value in route_score_on_route_pellet_count_support),
        route_score_on_route_bonus_count_support=tuple(int(value) for value in route_score_on_route_bonus_count_support),
        route_score_off_route_bonus_count_support=tuple(int(value) for value in route_score_off_route_bonus_count_support),
        route_score_bonus_value_support=tuple(int(value) for value in route_score_bonus_value_support),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        row_count_probabilities=dict(row_count_probabilities),
        col_count_probabilities=dict(col_count_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
        target_label_probabilities=dict(target_label_probabilities),
        item_count_probabilities=dict(item_count_probabilities),
    )


def _render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    namespace: str,
    instance_seed: int,
) -> PacmanRenderParams:
    """Resolve Pac-Man rendering parameters from config/defaults."""

    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            render_defaults,
            instance_seed=int(instance_seed),
            namespace=f"{namespace}.layout",
        ),
        unit_scale_meta,
    )
    maze_width_px = scale_games_px(
        params.get("maze_width_px", group_default(render_defaults, "maze_width_px", _DEFAULTS.maze_width_px)),
        unit_scale,
        min_px=420,
    )
    maze_height_px = scale_games_px(
        params.get("maze_height_px", group_default(render_defaults, "maze_height_px", _DEFAULTS.maze_height_px)),
        unit_scale,
        min_px=310,
    )
    default_canvas_width = int(group_default(render_defaults, "canvas_width", _DEFAULTS.canvas_width))
    default_canvas_height = int(group_default(render_defaults, "canvas_height", _DEFAULTS.canvas_height))
    canvas_width = int(max(620, min(default_canvas_width, int(maze_width_px) + 220)))
    canvas_height = int(max(500, min(default_canvas_height, int(maze_height_px) + 180)))
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.font_family",
        params=params,
    )
    return PacmanRenderParams(
        canvas_width=int(params.get("canvas_width", canvas_width)),
        canvas_height=int(params.get("canvas_height", canvas_height)),
        panel_margin_px=scale_games_px(
            params.get("panel_margin_px", group_default(render_defaults, "panel_margin_px", _DEFAULTS.panel_margin_px)),
            unit_scale,
            min_px=18,
        ),
        maze_width_px=int(maze_width_px),
        maze_height_px=int(maze_height_px),
        wall_gap_px=scale_games_px(params.get("wall_gap_px", group_default(render_defaults, "wall_gap_px", _DEFAULTS.wall_gap_px)), unit_scale, min_px=1),
        wall_outline_width_px=scale_games_px(params.get("wall_outline_width_px", group_default(render_defaults, "wall_outline_width_px", _DEFAULTS.wall_outline_width_px)), unit_scale, min_px=1),
        pellet_radius_px=scale_games_px(params.get("pellet_radius_px", group_default(render_defaults, "pellet_radius_px", _DEFAULTS.pellet_radius_px)), unit_scale, min_px=7),
        item_radius_px=scale_games_px(params.get("item_radius_px", group_default(render_defaults, "item_radius_px", _DEFAULTS.item_radius_px)), unit_scale, min_px=9),
        ghost_radius_px=scale_games_px(params.get("ghost_radius_px", group_default(render_defaults, "ghost_radius_px", _DEFAULTS.ghost_radius_px)), unit_scale, min_px=9),
        route_width_px=scale_games_px(params.get("route_width_px", group_default(render_defaults, "route_width_px", _DEFAULTS.route_width_px)), unit_scale, min_px=4),
        item_label_font_size_px=scale_games_px(params.get("item_label_font_size_px", group_default(render_defaults, "item_label_font_size_px", _DEFAULTS.item_label_font_size_px)), unit_scale, min_px=12),
        font_family=str(font_family),
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
    annotation_ids = tuple(pellet_entity_id(coord) for coord in counted_pellets)
    sample = PacmanSample(
        row_count=rows,
        col_count=cols,
        mode=str(axes.query_id),
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
        annotation_entity_ids=annotation_ids,
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
    annotation_ids = tuple(pellet_entity_id(coord) for coord in counted_pellets) + (str(stop_ghost.ghost_id),)
    sample = PacmanSample(
        row_count=rows,
        col_count=cols,
        mode=str(axes.query_id),
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
        annotation_entity_ids=annotation_ids,
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
        mode=str(axes.query_id),
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
        annotation_entity_ids=(item_entity_id(target_label),),
        construction_mode="first_labeled_bonus_on_highlighted_route",
    )
    validate_pacman_sample(sample)
    return sample


def _sample_route_score_value_scene(*, rng, axes: _ResolvedAxes) -> PacmanSample:
    """Construct a route score scene with normal pellets and scored bonus items."""

    rows, cols = int(axes.row_count), int(axes.col_count)
    on_route_pellet_count = int(rng.choice(tuple(axes.route_score_on_route_pellet_count_support)))
    on_route_bonus_count = int(rng.choice(tuple(axes.route_score_on_route_bonus_count_support)))
    max_bonus_count = len(PACMAN_ITEM_LABELS)
    on_route_bonus_count = min(on_route_bonus_count, max_bonus_count)
    off_route_bonus_count = int(rng.choice(tuple(axes.route_score_off_route_bonus_count_support)))
    off_route_bonus_count = max(1, min(off_route_bonus_count, max_bonus_count - on_route_bonus_count))

    route_collectible_count = int(on_route_pellet_count + on_route_bonus_count)
    route_len = min(
        max(route_collectible_count + int(rng.randint(5, 9)), 10),
        max(10, (rows - 2) * (cols - 2) - 2),
    )
    route = _sample_route(rng=rng, rows=rows, cols=cols, length=route_len)
    min_open = len(route) + on_route_pellet_count + on_route_bonus_count + off_route_bonus_count + int(rng.randint(12, 20))
    open_cells = _expand_open_cells(rng=rng, rows=rows, cols=cols, route_coords=route, min_open_cells=min_open)

    route_candidates = list(route[1:])
    if len(route_candidates) < route_collectible_count:
        raise ValueError("route too short for route score collectibles")
    rng.shuffle(route_candidates)
    on_route_bonus_coords = tuple(tuple(coord) for coord in route_candidates[:on_route_bonus_count])
    on_route_pellet_coords = tuple(tuple(coord) for coord in route_candidates[on_route_bonus_count : route_collectible_count])

    off_route_cells = list(_available_open_cells(open_cells, excluded=tuple(route)))
    rng.shuffle(off_route_cells)
    if len(off_route_cells) < off_route_bonus_count:
        raise ValueError("not enough off-route cells for route score bonus distractors")
    off_route_bonus_coords = tuple(tuple(coord) for coord in off_route_cells[:off_route_bonus_count])

    used_item_coords = tuple(on_route_bonus_coords) + tuple(off_route_bonus_coords)
    available_for_pellets = list(_available_open_cells(open_cells, excluded=tuple(route) + tuple(used_item_coords)))
    rng.shuffle(available_for_pellets)
    off_route_pellet_count = min(len(available_for_pellets), int(rng.randint(4, 9)))
    pellets = sorted_coords(tuple(on_route_pellet_coords) + tuple(available_for_pellets[:off_route_pellet_count]))

    labels = tuple(PACMAN_ITEM_LABELS[: int(on_route_bonus_count + off_route_bonus_count)])
    bonus_coords = tuple(on_route_bonus_coords) + tuple(off_route_bonus_coords)
    bonus_values = tuple(int(rng.choice(tuple(axes.route_score_bonus_value_support))) for _ in labels)
    route_coord_set = {tuple(coord) for coord in route}
    items = tuple(
        PacmanItem(
            label=str(label),
            item_id=item_entity_id(str(label)),
            coord=tuple(coord),
            kind=str(PACMAN_ITEM_KINDS[index % len(PACMAN_ITEM_KINDS)]),
            is_answer=tuple(coord) in route_coord_set,
            score_value=int(bonus_values[index]),
        )
        for index, (label, coord) in enumerate(zip(labels, bonus_coords))
    )
    route_order = {tuple(coord): index for index, coord in enumerate(route)}
    scored_entries = [
        (int(route_order[tuple(coord)]), pellet_entity_id(tuple(coord)))
        for coord in on_route_pellet_coords
    ]
    scored_entries.extend(
        (int(route_order[tuple(item.coord)]), item_entity_id(str(item.label)))
        for item in items
        if tuple(item.coord) in route_coord_set
    )
    annotation_ids = tuple(str(entity_id) for _index, entity_id in sorted(scored_entries, key=lambda pair: pair[0]))
    score_by_item_id = {item_entity_id(str(item.label)): int(item.score_value or 0) for item in items}
    answer = sum(1 for entity_id in annotation_ids if str(entity_id).startswith("pellet_r")) + sum(
        int(score_by_item_id[str(entity_id)])
        for entity_id in annotation_ids
        if str(entity_id).startswith("item_")
    )
    ghosts = _sample_decorative_ghosts(
        rng=rng,
        open_cells=open_cells,
        excluded=tuple(route) + tuple(pellets) + tuple(used_item_coords),
        start_index=1,
        min_count=1,
        max_count=2,
    )
    sample = PacmanSample(
        row_count=rows,
        col_count=cols,
        mode=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        open_cells=tuple(open_cells),
        wall_cells=_wall_cells(rows=rows, cols=cols, open_cells=open_cells),
        pacman_coord=tuple(route[0]),
        route_coords=tuple(route),
        pellets=tuple(pellets),
        items=items,
        ghosts=ghosts,
        answer=int(answer),
        target_answer=int(answer),
        annotation_entity_ids=tuple(annotation_ids),
        construction_mode="sum_route_collectible_scores",
    )
    validate_pacman_sample(sample)
    return sample


def sample_scene(*, rng, axes: _ResolvedAxes) -> PacmanSample:
    """Construct one Pac-Man scene for the requested query."""

    query = str(axes.query_id)
    if query == "path_pellet_count":
        return _sample_path_pellet_count_scene(rng=rng, axes=axes)
    if query == "next_item_label":
        return _sample_next_item_label_scene(rng=rng, axes=axes)
    if query == "pellet_count_before_ghost":
        return _sample_pellet_count_before_ghost_scene(rng=rng, axes=axes)
    if query == "route_score_value":
        return _sample_route_score_value_scene(rng=rng, axes=axes)
    raise ValueError(f"unsupported Pac-Man query_id: {query}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for Pac-Man JSON output."""

    if str(query_id) == "next_item_label":
        answer_value: str | int = "D"
        annotation_value = [[509, 305]]
    elif str(query_id) == "pellet_count_before_ghost":
        answer_value = 4
        annotation_value = [[355, 217], [415, 277], [548, 278]]
    elif str(query_id) == "route_score_value":
        answer_value = 12
        annotation_value = [[315, 209], [369, 209], [424, 264]]
    else:
        answer_value = 5
        annotation_value = [[315, 209], [369, 209]]
    return (
        json.dumps({"annotation": annotation_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


def build_components(
    *,
    sampled_scene: PacmanSample,
    axes: _ResolvedAxes,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    prompt_defaults: Mapping[str, Any],
    namespace: str,
) -> GeneratedComponents:
    """Render, prompt, annotate, and trace one Pac-Man sample."""

    render_params = _render_params(
        params,
        render_defaults=render_defaults,
        namespace=str(namespace),
        instance_seed=int(instance_seed),
    )
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.panel_scene_style",
        treatment_weights=params.get("panel_scene_treatment_weights", group_default(render_defaults, "panel_scene_treatment_weights", None)),
        palette_weights=params.get("panel_scene_palette_weights", group_default(render_defaults, "panel_scene_palette_weights", None)),
    )
    background, background_meta = make_panel_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=panel_style,
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
        panel_style=panel_style,
    )
    annotation_points = [
        list(rendered_scene.render_map["entity_points_px"][str(entity_id)])
        for entity_id in sampled_scene.annotation_entity_ids
    ]
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )

    resolved_prompt_defaults = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_compact_maze",
            "object_description_wide_maze",
            "answer_hint_path_pellet_count",
            "annotation_hint_path_pellet_count",
            "answer_hint_next_item_label",
            "annotation_hint_next_item_label",
            "answer_hint_pellet_count_before_ghost",
            "annotation_hint_pellet_count_before_ghost",
            "answer_hint_route_score_value",
            "annotation_hint_route_score_value",
            "score_rule_text",
        ),
        context=f"prompt defaults for {namespace}",
    )
    json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
    prompt_selection = render_scene_prompt_variants(
        domain="games",
        scene_id=SCENE_ID,
        bundle_id=str(resolved_prompt_defaults["bundle_id"]),
        scene_key=str(resolved_prompt_defaults["scene_key"]),
        task_key=str(resolved_prompt_defaults["task_key"]),
        query_key=str(axes.query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "object_description": str(resolved_prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
            "json_output_contract": str(resolved_prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(resolved_prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(resolved_prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
            "annotation_hint": str(resolved_prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
            "score_rule_text": str(resolved_prompt_defaults["score_rule_text"]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    answer_gt = (
        TypedValue(type="string", value=str(sampled_scene.answer))
        if str(axes.query_id) == "next_item_label"
        else TypedValue(type="integer", value=int(sampled_scene.answer))
    )
    annotation_gt = TypedValue(type="point_set", value=[list(point) for point in annotation_points])
    text_style_meta = {
        "font_family": str(render_params.font_family),
        "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
    }
    item_trace = list(visible_item_trace(sampled_scene.items))
    ghost_trace = list(visible_ghost_trace(sampled_scene.ghosts))
    trace_payload = {
        "scene_ir": {
            "scene_kind": f"games_pacman_{str(axes.scene_variant)}",
            "entities": [dict(entity) for entity in rendered_scene.scene_entities],
            "relations": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "row_count": int(sampled_scene.row_count),
                "col_count": int(sampled_scene.col_count),
                "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
            },
        },
        "query_spec": {
            "query_id": str(axes.query_id),
            "template_id": str(resolved_prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "row_count": int(sampled_scene.row_count),
                "col_count": int(sampled_scene.col_count),
                "route_length": len(sampled_scene.route_coords),
                "pellet_count": len(sampled_scene.pellets),
                "item_count": len(sampled_scene.items),
                "ghost_count": len(sampled_scene.ghosts),
                "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                "query_id_probabilities": dict(axes.query_id_probabilities),
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
                "route_score_on_route_pellet_count_support": [int(value) for value in axes.route_score_on_route_pellet_count_support],
                "route_score_on_route_bonus_count_support": [int(value) for value in axes.route_score_on_route_bonus_count_support],
                "route_score_off_route_bonus_count_support": [int(value) for value in axes.route_score_off_route_bonus_count_support],
                "route_score_bonus_value_support": [int(value) for value in axes.route_score_bonus_value_support],
            },
        },
        "render_spec": {
            "scene_variant": str(axes.scene_variant),
            "style_variant": str(axes.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(panel_style_meta),
            "text_style": dict(text_style_meta),
        },
        "render_map": dict(rendered_scene.render_map),
        "execution_trace": {
            "scene_variant": str(axes.scene_variant),
            "query_id": str(axes.query_id),
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
            "annotation_entity_ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
            "construction_mode": str(sampled_scene.construction_mode),
        },
        "witness_symbolic": {
            "type": "object_set",
            "ids": [str(entity_id) for entity_id in sampled_scene.annotation_entity_ids],
        },
        "projected_annotation": {
            "type": "point_set",
            "point_set": [list(point) for point in annotation_points],
            "pixel_point_set": [list(point) for point in annotation_points],
        },
        "background": background_meta,
        "post_image_noise": post_noise_meta,
    }
    return GeneratedComponents(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        trace_payload=trace_payload,
        query_id=str(axes.query_id),
    )


__all__ = [
    "GeneratedComponents",
    "POST_IMAGE_NOISE_DEFAULTS",
    "ROUTE_PELLET_COUNT_QUERY_IDS",
    "ROUTE_SCORE_BONUS_VALUE_SUPPORT",
    "SCENE_ID",
    "SUPPORTED_PACMAN_QUERY_IDS",
    "build_components",
    "resolve_axes",
    "sample_scene",
]
