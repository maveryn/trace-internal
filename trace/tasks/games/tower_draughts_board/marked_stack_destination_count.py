"""Tower draughts-style stack ownership and move-count tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_scene_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_scene_prompt_variants
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.layout import (
    apply_games_layout_jitter_to_bbox,
    attach_games_unit_size_jitter,
    resolve_games_layout_jitter,
    resolve_games_unit_size_scale,
    scale_games_px,
)
from ..shared.marking import draw_optional_marker_x, draw_semantic_ellipse_marker, resolve_semantic_marker_style
from ..shared.sampling import resolve_games_named_axis
from ..shared.scene_style import draw_panel_scene_chrome, make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "tower_draughts_board"
SCENE_ID = "tower_draughts_board"
TASK_ID = "games_tower_draughts_board_base"
CONTROLLED_STACK_TASK_ID = "task_games__tower_draughts_board__controlled_stack_count"
MARKED_DESTINATION_TASK_ID = "task_games__tower_draughts_board__marked_stack_destination_count"
MARKED_CAPTURE_TASK_ID = "task_games__tower_draughts_board__marked_stack_capture_count"
CONTROLLED_STACK_QUERY_ID = "controlled_stack_count"
MARKED_DESTINATION_QUERY_ID = "marked_stack_destination_count"
MARKED_CAPTURE_QUERY_ID = "marked_stack_capture_count"
RED = 1
BLACK = -1
PLAYER_NAMES: Dict[int, str] = {RED: "red", BLACK: "black"}
PLAYER_SUPPORT: Tuple[str, ...] = ("red", "black")
STYLE_VARIANTS: Tuple[str, ...] = ("wood_table", "ink_board", "felt_mat", "night_tokens", "parchment")
TOP_KIND_SUPPORT: Tuple[str, ...] = ("regular", "crowned")
Coord = Tuple[int, int]


@dataclass(frozen=True)
class StackSpec:
    """One stack on a playable cell, from bottom to top."""

    coord: Coord
    disks: Tuple[int, ...]
    top_crowned: bool = False

    @property
    def owner(self) -> int:
        return int(self.disks[-1])

    @property
    def height(self) -> int:
        return int(len(self.disks))


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for tower draughts board scenes."""

    board_size_support: Tuple[int, ...] = (4, 5, 6)
    controlled_stack_count_support: Tuple[int, ...] = tuple(range(0, 11))
    marked_destination_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    marked_capture_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4)
    stack_height_support: Tuple[int, ...] = (1, 2, 3, 4)
    min_occupied_fraction: float = 0.40
    max_occupied_fraction: float = 0.65
    crowned_top_probability: float = 0.25
    canvas_width: int = 760
    canvas_height: int = 740
    panel_margin_px: int = 50
    max_board_size_px: int = 520
    cell_size_min_px: int = 56
    cell_size_max_px: int = 80
    board_frame_width_px: int = 8
    marker_width_px: int = 5
    dynamic_canvas_size_enabled: bool = True
    canvas_min_width_px: int = 520
    canvas_min_height_px: int = 500
    canvas_side_padding_px: int = 136
    canvas_vertical_padding_px: int = 136


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one sample."""

    task_kind: str
    target_player: int
    marked_player: int
    top_kind: str
    style_variant: str
    board_size: int
    target_answer: int
    target_answer_support: Tuple[int, ...]
    board_size_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    target_player_probabilities: Dict[str, float]
    marked_player_probabilities: Dict[str, float]
    top_kind_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _Sample:
    """One symbolic tower draughts board and query witness."""

    query_id: str
    board_size: int
    style_variant: str
    stacks: Tuple[StackSpec, ...]
    marked_coord: Coord | None
    target_player: int
    marked_player: int
    top_kind: str
    annotation_coords: Tuple[Coord, ...]
    answer: int
    construction_mode: str


@dataclass(frozen=True)
class _Theme:
    """Scene-local palette for a tower draughts board."""

    board_fill_rgb: Tuple[int, int, int]
    board_border_rgb: Tuple[int, int, int]
    light_cell_rgb: Tuple[int, int, int]
    dark_cell_rgb: Tuple[int, int, int]
    playable_outline_rgb: Tuple[int, int, int]
    red_piece_rgb: Tuple[int, int, int]
    red_piece_outline_rgb: Tuple[int, int, int]
    black_piece_rgb: Tuple[int, int, int]
    black_piece_outline_rgb: Tuple[int, int, int]
    crown_rgb: Tuple[int, int, int]
    crown_outline_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered board plus trace-friendly maps."""

    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("games", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _player_from_name(name: str | int) -> int:
    if isinstance(name, int):
        return RED if int(name) == RED else BLACK
    normalized = str(name).strip().lower()
    if normalized == "red":
        return RED
    if normalized == "black":
        return BLACK
    raise ValueError(f"unknown tower draughts player {name!r}")


def _player_name(player: int) -> str:
    return PLAYER_NAMES[RED if int(player) == RED else BLACK]


def _opponent(player: int) -> int:
    return BLACK if int(player) == RED else RED


def _playable_coords(board_size: int) -> Tuple[Coord, ...]:
    return tuple(
        (row, col)
        for row in range(int(board_size))
        for col in range(int(board_size))
        if (int(row) + int(col)) % 2 == 1
    )


def _cell_id(coord: Coord) -> str:
    return f"cell_r{int(coord[0])}_c{int(coord[1])}"


def _stack_id(coord: Coord) -> str:
    return f"stack_r{int(coord[0])}_c{int(coord[1])}"


def _in_bounds(coord: Coord, board_size: int) -> bool:
    return 0 <= int(coord[0]) < int(board_size) and 0 <= int(coord[1]) < int(board_size)


def _movement_directions(player: int, *, crowned: bool) -> Tuple[Coord, ...]:
    if bool(crowned):
        return ((-1, -1), (-1, 1), (1, -1), (1, 1))
    row_delta = -1 if int(player) == RED else 1
    return ((row_delta, -1), (row_delta, 1))


def _destination_candidates(*, coord: Coord, owner: int, crowned: bool, board_size: int) -> Tuple[Coord, ...]:
    candidates: list[Coord] = []
    for dr, dc in _movement_directions(int(owner), crowned=bool(crowned)):
        candidate = (int(coord[0]) + int(dr), int(coord[1]) + int(dc))
        if _in_bounds(candidate, int(board_size)) and candidate in _playable_coords(int(board_size)):
            candidates.append(candidate)
    return tuple(sorted(candidates))


def _capture_paths(*, coord: Coord, owner: int, crowned: bool, board_size: int) -> Tuple[Tuple[Coord, Coord], ...]:
    paths: list[Tuple[Coord, Coord]] = []
    for dr, dc in _movement_directions(int(owner), crowned=bool(crowned)):
        captured = (int(coord[0]) + int(dr), int(coord[1]) + int(dc))
        landing = (int(coord[0]) + (2 * int(dr)), int(coord[1]) + (2 * int(dc)))
        if (
            _in_bounds(captured, int(board_size))
            and _in_bounds(landing, int(board_size))
            and captured in _playable_coords(int(board_size))
            and landing in _playable_coords(int(board_size))
        ):
            paths.append((captured, landing))
    return tuple(sorted(paths))


def _stack_owner_map(stacks: Sequence[StackSpec]) -> Dict[Coord, int]:
    return {tuple(stack.coord): int(stack.owner) for stack in stacks}


def _legal_destinations(*, stacks: Sequence[StackSpec], marked_coord: Coord, board_size: int) -> Tuple[Coord, ...]:
    stack_by_coord = {tuple(stack.coord): stack for stack in stacks}
    marked = stack_by_coord[tuple(marked_coord)]
    occupied = set(stack_by_coord)
    return tuple(
        coord
        for coord in _destination_candidates(
            coord=tuple(marked_coord),
            owner=int(marked.owner),
            crowned=bool(marked.top_crowned),
            board_size=int(board_size),
        )
        if tuple(coord) not in occupied
    )


def _capture_targets(*, stacks: Sequence[StackSpec], marked_coord: Coord, board_size: int) -> Tuple[Coord, ...]:
    stack_by_coord = {tuple(stack.coord): stack for stack in stacks}
    marked = stack_by_coord[tuple(marked_coord)]
    occupied = set(stack_by_coord)
    out: list[Coord] = []
    for captured, landing in _capture_paths(
        coord=tuple(marked_coord),
        owner=int(marked.owner),
        crowned=bool(marked.top_crowned),
        board_size=int(board_size),
    ):
        captured_stack = stack_by_coord.get(tuple(captured))
        if captured_stack is None:
            continue
        if int(captured_stack.owner) != _opponent(int(marked.owner)):
            continue
        if tuple(landing) in occupied:
            continue
        out.append(tuple(captured))
    return tuple(sorted(out))


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
    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=tuple(str(value) for value in supported),
    )


def _support_key(task_kind: str) -> str:
    return {
        CONTROLLED_STACK_QUERY_ID: "controlled_stack_count_support",
        MARKED_DESTINATION_QUERY_ID: "marked_destination_count_support",
        MARKED_CAPTURE_QUERY_ID: "marked_capture_count_support",
    }[str(task_kind)]


def _fallback_support(task_kind: str) -> Tuple[int, ...]:
    return {
        CONTROLLED_STACK_QUERY_ID: _DEFAULTS.controlled_stack_count_support,
        MARKED_DESTINATION_QUERY_ID: _DEFAULTS.marked_destination_count_support,
        MARKED_CAPTURE_QUERY_ID: _DEFAULTS.marked_capture_count_support,
    }[str(task_kind)]


def _max_count_for_board(*, task_kind: str, board_size: int) -> int:
    playable_coords = _playable_coords(int(board_size))
    playable = len(playable_coords)
    if str(task_kind) == CONTROLLED_STACK_QUERY_ID:
        return min(10, int(playable))
    max_seen = 0
    for player in (RED, BLACK):
        for coord in playable_coords:
            if str(task_kind) == MARKED_DESTINATION_QUERY_ID:
                count = len(
                    _destination_candidates(
                        coord=tuple(coord),
                        owner=int(player),
                        crowned=True,
                        board_size=int(board_size),
                    )
                )
            else:
                count = len(
                    _capture_paths(
                        coord=tuple(coord),
                        owner=int(player),
                        crowned=True,
                        board_size=int(board_size),
                    )
                )
            max_seen = max(int(max_seen), int(count))
    return min(4, int(max_seen))


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any], task_kind: str) -> _ResolvedAxes:
    style_variant, style_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=STYLE_VARIANTS,
    )
    target_player_name, target_player_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="target_player",
        explicit_key="target_player",
        weights_key="target_player_weights",
        balance_flag_key="balanced_target_player_sampling",
        supported=PLAYER_SUPPORT,
    )
    marked_player_name, marked_player_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="marked_player",
        explicit_key="marked_player",
        weights_key="marked_player_weights",
        balance_flag_key="balanced_marked_player_sampling",
        supported=PLAYER_SUPPORT,
    )
    top_kind, top_kind_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="top_kind",
        explicit_key="top_kind",
        weights_key="top_kind_weights",
        balance_flag_key="balanced_top_kind_sampling",
        supported=TOP_KIND_SUPPORT,
    )
    support_key = _support_key(str(task_kind))
    target_answer, target_probs = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=support_key,
        explicit_key="target_answer",
        fallback_support=_fallback_support(str(task_kind)),
        namespace=f"{TASK_ID}.{task_kind}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=support_key,
        fallback=_fallback_support(str(task_kind)),
    )
    board_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="board_size_support",
        fallback=_DEFAULTS.board_size_support,
    )
    feasible_board_support = tuple(
        int(size)
        for size in board_support
        if _max_count_for_board(task_kind=str(task_kind), board_size=int(size)) >= int(target_answer)
    )
    if not feasible_board_support:
        raise ValueError(f"target answer {target_answer} is infeasible for {task_kind}")
    board_params = dict(params)
    board_params["board_size_support"] = list(feasible_board_support)
    if "board_size" in params and int(params["board_size"]) not in feasible_board_support:
        raise ValueError(f"explicit board_size={params['board_size']} cannot realize target answer {target_answer}")
    board_size, board_probs = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=board_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="board_size_support",
        explicit_key="board_size",
        fallback_support=feasible_board_support,
        namespace=f"{TASK_ID}.{task_kind}.board_size",
        balanced_flag_key="balanced_board_size_sampling",
        namespace_support_permutation=True,
    )
    if str(task_kind) in {MARKED_DESTINATION_QUERY_ID, MARKED_CAPTURE_QUERY_ID} and int(target_answer) > 2:
        top_kind = "crowned"
    return _ResolvedAxes(
        task_kind=str(task_kind),
        target_player=_player_from_name(str(target_player_name)),
        marked_player=_player_from_name(str(marked_player_name)),
        top_kind=str(top_kind),
        style_variant=str(style_variant),
        board_size=int(board_size),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_support),
        board_size_probabilities=dict(board_probs),
        target_answer_probabilities=dict(target_probs),
        target_player_probabilities=dict(target_player_probs),
        marked_player_probabilities=dict(marked_player_probs),
        top_kind_probabilities=dict(top_kind_probs),
        style_variant_probabilities=dict(style_probs),
    )


def _random_height(rng: Any) -> int:
    support = resolve_integer_support(
        {},
        gen_defaults=_GEN_DEFAULTS,
        key="stack_height_support",
        fallback=_DEFAULTS.stack_height_support,
    )
    return int(rng.choice(list(support)))


def _make_stack(*, rng: Any, coord: Coord, owner: int, crowned: bool = False) -> StackSpec:
    height = _random_height(rng)
    disks = [int(owner)]
    for _ in range(max(0, int(height) - 1)):
        disks.insert(0, int(rng.choice([RED, BLACK])))
    disks[-1] = int(owner)
    return StackSpec(coord=tuple(coord), disks=tuple(int(value) for value in disks), top_crowned=bool(crowned))


def _desired_occupied_count(*, rng: Any, board_size: int, minimum: int) -> int:
    playable_count = len(_playable_coords(int(board_size)))
    min_fraction = float(group_default(_GEN_DEFAULTS, "min_occupied_fraction", _DEFAULTS.min_occupied_fraction))
    max_fraction = float(group_default(_GEN_DEFAULTS, "max_occupied_fraction", _DEFAULTS.max_occupied_fraction))
    lo = max(int(minimum), int(round(float(playable_count) * min_fraction)))
    hi = max(lo, int(round(float(playable_count) * max_fraction)))
    return min(int(playable_count), int(rng.randint(lo, hi)))


def _fill_extra_stacks(
    *,
    rng: Any,
    board_size: int,
    stacks: List[StackSpec],
    protected_empty: set[Coord],
    desired_count: int,
) -> None:
    occupied = {tuple(stack.coord) for stack in stacks}
    candidates = [
        coord
        for coord in _playable_coords(int(board_size))
        if tuple(coord) not in occupied and tuple(coord) not in protected_empty
    ]
    rng.shuffle(candidates)
    crown_prob = float(group_default(_GEN_DEFAULTS, "crowned_top_probability", _DEFAULTS.crowned_top_probability))
    for coord in candidates:
        if len(stacks) >= int(desired_count):
            break
        owner = int(rng.choice([RED, BLACK]))
        stacks.append(_make_stack(rng=rng, coord=tuple(coord), owner=owner, crowned=bool(rng.random() < crown_prob)))


def _sample_controlled_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    target = int(axes.target_answer)
    board_size = int(axes.board_size)
    playable = list(_playable_coords(board_size))
    if target > len(playable):
        raise ValueError("controlled-stack target exceeds playable cells")
    rng.shuffle(playable)
    target_coords = playable[:target]
    remaining = playable[target:]
    desired_count = _desired_occupied_count(rng=rng, board_size=board_size, minimum=max(1, target))
    desired_count = max(desired_count, target)
    stacks: list[StackSpec] = [
        _make_stack(rng=rng, coord=coord, owner=int(axes.target_player), crowned=bool(rng.random() < 0.2))
        for coord in target_coords
    ]
    opponent = _opponent(int(axes.target_player))
    for coord in remaining:
        if len(stacks) >= desired_count:
            break
        stacks.append(_make_stack(rng=rng, coord=coord, owner=opponent, crowned=bool(rng.random() < 0.2)))
    annotation = tuple(sorted(coord for coord in target_coords))
    return _Sample(
        query_id=CONTROLLED_STACK_QUERY_ID,
        board_size=int(board_size),
        style_variant=str(axes.style_variant),
        stacks=tuple(sorted(stacks, key=lambda stack: stack.coord)),
        marked_coord=None,
        target_player=int(axes.target_player),
        marked_player=int(axes.marked_player),
        top_kind=str(axes.top_kind),
        annotation_coords=tuple(annotation),
        answer=int(len(annotation)),
        construction_mode="target_conditioned_top_owner_count",
    )


def _viable_marked_coords(*, board_size: int, owner: int, crowned: bool, min_destinations: int = 0, min_captures: int = 0) -> Tuple[Coord, ...]:
    out: list[Coord] = []
    for coord in _playable_coords(int(board_size)):
        destinations = _destination_candidates(coord=coord, owner=int(owner), crowned=bool(crowned), board_size=int(board_size))
        captures = _capture_paths(coord=coord, owner=int(owner), crowned=bool(crowned), board_size=int(board_size))
        if len(destinations) >= int(min_destinations) and len(captures) >= int(min_captures):
            out.append(coord)
    return tuple(out)


def _sample_destination_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    target = int(axes.target_answer)
    board_size = int(axes.board_size)
    crowned = str(axes.top_kind) == "crowned"
    viable = list(
        _viable_marked_coords(
            board_size=board_size,
            owner=int(axes.marked_player),
            crowned=bool(crowned),
            min_destinations=target,
        )
    )
    if not viable:
        raise ValueError("no marked stack can realize destination target")
    rng.shuffle(viable)
    marked_coord = tuple(viable[0])
    candidates = list(
        _destination_candidates(
            coord=marked_coord,
            owner=int(axes.marked_player),
            crowned=bool(crowned),
            board_size=board_size,
        )
    )
    rng.shuffle(candidates)
    annotation = set(candidates[:target])
    blocked = [coord for coord in candidates if coord not in annotation]
    stacks: list[StackSpec] = [
        _make_stack(rng=rng, coord=marked_coord, owner=int(axes.marked_player), crowned=bool(crowned))
    ]
    for coord in blocked:
        stacks.append(_make_stack(rng=rng, coord=coord, owner=int(rng.choice([RED, BLACK])), crowned=bool(rng.random() < 0.2)))
    desired_count = _desired_occupied_count(rng=rng, board_size=board_size, minimum=len(stacks))
    _fill_extra_stacks(
        rng=rng,
        board_size=board_size,
        stacks=stacks,
        protected_empty={tuple(coord) for coord in annotation},
        desired_count=desired_count,
    )
    actual = _legal_destinations(stacks=tuple(stacks), marked_coord=marked_coord, board_size=board_size)
    if set(actual) != annotation:
        raise ValueError("constructed destination count mismatch")
    return _Sample(
        query_id=MARKED_DESTINATION_QUERY_ID,
        board_size=int(board_size),
        style_variant=str(axes.style_variant),
        stacks=tuple(sorted(stacks, key=lambda stack: stack.coord)),
        marked_coord=marked_coord,
        target_player=int(axes.target_player),
        marked_player=int(axes.marked_player),
        top_kind=str(axes.top_kind),
        annotation_coords=tuple(sorted(actual)),
        answer=int(len(actual)),
        construction_mode="target_conditioned_marked_stack_destinations",
    )


def _sample_capture_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    target = int(axes.target_answer)
    board_size = int(axes.board_size)
    crowned = str(axes.top_kind) == "crowned"
    viable = list(
        _viable_marked_coords(
            board_size=board_size,
            owner=int(axes.marked_player),
            crowned=bool(crowned),
            min_captures=target,
        )
    )
    if not viable:
        raise ValueError("no marked stack can realize capture target")
    rng.shuffle(viable)
    marked_coord = tuple(viable[0])
    paths = list(
        _capture_paths(
            coord=marked_coord,
            owner=int(axes.marked_player),
            crowned=bool(crowned),
            board_size=board_size,
        )
    )
    rng.shuffle(paths)
    selected = paths[:target]
    selected_captured = {tuple(captured) for captured, _landing in selected}
    selected_landings = {tuple(landing) for _captured, landing in selected}
    stacks: list[StackSpec] = [
        _make_stack(rng=rng, coord=marked_coord, owner=int(axes.marked_player), crowned=bool(crowned))
    ]
    for captured, _landing in selected:
        stacks.append(_make_stack(rng=rng, coord=tuple(captured), owner=_opponent(int(axes.marked_player)), crowned=bool(rng.random() < 0.2)))
    for captured, landing in paths[target:]:
        if tuple(captured) in selected_captured or tuple(landing) in selected_landings:
            continue
        mode = str(rng.choice(["own_piece", "blocked_landing", "empty_middle"]))
        if mode == "own_piece":
            stacks.append(_make_stack(rng=rng, coord=tuple(captured), owner=int(axes.marked_player), crowned=bool(rng.random() < 0.2)))
        elif mode == "blocked_landing":
            stacks.append(_make_stack(rng=rng, coord=tuple(captured), owner=_opponent(int(axes.marked_player)), crowned=bool(rng.random() < 0.2)))
            stacks.append(_make_stack(rng=rng, coord=tuple(landing), owner=int(rng.choice([RED, BLACK])), crowned=bool(rng.random() < 0.2)))
    unique: dict[Coord, StackSpec] = {}
    for stack in stacks:
        unique[tuple(stack.coord)] = stack
    stacks = list(unique.values())
    desired_count = _desired_occupied_count(rng=rng, board_size=board_size, minimum=len(stacks))
    _fill_extra_stacks(
        rng=rng,
        board_size=board_size,
        stacks=stacks,
        protected_empty={tuple(coord) for coord in selected_landings},
        desired_count=desired_count,
    )
    actual = _capture_targets(stacks=tuple(stacks), marked_coord=marked_coord, board_size=board_size)
    if set(actual) != selected_captured:
        raise ValueError("constructed capture count mismatch")
    return _Sample(
        query_id=MARKED_CAPTURE_QUERY_ID,
        board_size=int(board_size),
        style_variant=str(axes.style_variant),
        stacks=tuple(sorted(stacks, key=lambda stack: stack.coord)),
        marked_coord=marked_coord,
        target_player=int(axes.target_player),
        marked_player=int(axes.marked_player),
        top_kind=str(axes.top_kind),
        annotation_coords=tuple(sorted(actual)),
        answer=int(len(actual)),
        construction_mode="target_conditioned_marked_stack_captures",
    )


def _theme_for_style(style_variant: str) -> Tuple[_Theme, Dict[str, Any]]:
    themes: dict[str, _Theme] = {
        "wood_table": _Theme(
            board_fill_rgb=(206, 156, 96),
            board_border_rgb=(97, 64, 35),
            light_cell_rgb=(235, 202, 151),
            dark_cell_rgb=(122, 82, 48),
            playable_outline_rgb=(72, 48, 28),
            red_piece_rgb=(207, 54, 58),
            red_piece_outline_rgb=(86, 24, 31),
            black_piece_rgb=(38, 44, 54),
            black_piece_outline_rgb=(225, 231, 238),
            crown_rgb=(249, 218, 87),
            crown_outline_rgb=(82, 55, 16),
        ),
        "ink_board": _Theme(
            board_fill_rgb=(239, 238, 228),
            board_border_rgb=(52, 53, 58),
            light_cell_rgb=(247, 246, 237),
            dark_cell_rgb=(188, 190, 190),
            playable_outline_rgb=(58, 60, 66),
            red_piece_rgb=(180, 55, 63),
            red_piece_outline_rgb=(73, 28, 35),
            black_piece_rgb=(35, 38, 45),
            black_piece_outline_rgb=(242, 244, 247),
            crown_rgb=(250, 220, 96),
            crown_outline_rgb=(70, 52, 22),
        ),
        "felt_mat": _Theme(
            board_fill_rgb=(63, 107, 74),
            board_border_rgb=(34, 63, 42),
            light_cell_rgb=(212, 229, 201),
            dark_cell_rgb=(84, 137, 92),
            playable_outline_rgb=(34, 82, 50),
            red_piece_rgb=(214, 74, 75),
            red_piece_outline_rgb=(86, 30, 33),
            black_piece_rgb=(38, 50, 51),
            black_piece_outline_rgb=(233, 245, 236),
            crown_rgb=(255, 229, 102),
            crown_outline_rgb=(82, 65, 17),
        ),
        "night_tokens": _Theme(
            board_fill_rgb=(34, 42, 60),
            board_border_rgb=(177, 194, 212),
            light_cell_rgb=(73, 89, 117),
            dark_cell_rgb=(25, 32, 48),
            playable_outline_rgb=(164, 191, 217),
            red_piece_rgb=(239, 83, 93),
            red_piece_outline_rgb=(255, 224, 230),
            black_piece_rgb=(15, 20, 31),
            black_piece_outline_rgb=(232, 241, 255),
            crown_rgb=(255, 222, 78),
            crown_outline_rgb=(42, 31, 8),
        ),
        "parchment": _Theme(
            board_fill_rgb=(229, 208, 166),
            board_border_rgb=(118, 84, 45),
            light_cell_rgb=(248, 232, 194),
            dark_cell_rgb=(150, 101, 62),
            playable_outline_rgb=(93, 67, 39),
            red_piece_rgb=(177, 62, 50),
            red_piece_outline_rgb=(77, 32, 27),
            black_piece_rgb=(52, 48, 43),
            black_piece_outline_rgb=(246, 238, 219),
            crown_rgb=(247, 207, 72),
            crown_outline_rgb=(85, 57, 20),
        ),
    }
    resolved = str(style_variant) if str(style_variant) in themes else "wood_table"
    return themes[resolved], {
        "style_variant": str(resolved),
        "available_styles": list(STYLE_VARIANTS),
        "board_style_policy": "scene_local_tower_draughts_board_palette",
    }


def _bbox_from_center(center: Sequence[float], radius: float) -> Tuple[float, float, float, float]:
    cx, cy = float(center[0]), float(center[1])
    return (
        round(cx - float(radius), 3),
        round(cy - float(radius), 3),
        round(cx + float(radius), 3),
        round(cy + float(radius), 3),
    )


def _draw_stack(
    draw: ImageDraw.ImageDraw,
    *,
    stack: StackSpec,
    cell_bbox: Sequence[float],
    theme: _Theme,
    instance_seed: int,
    disk_radius: float,
) -> Tuple[List[float], List[float]]:
    del instance_seed
    cx = 0.5 * (float(cell_bbox[0]) + float(cell_bbox[2]))
    cy = 0.5 * (float(cell_bbox[1]) + float(cell_bbox[3]))
    layer_offset = max(3.0, min(7.0, float(disk_radius) * 0.22))
    top_center = (float(cx), float(cy) - (0.5 * (int(stack.height) - 1) * layer_offset))
    all_bboxes: list[Tuple[float, float, float, float]] = []
    for index, player in enumerate(stack.disks):
        layer_y = float(cy) + (0.5 * (int(stack.height) - 1) * layer_offset) - (float(index) * layer_offset)
        fill = theme.red_piece_rgb if int(player) == RED else theme.black_piece_rgb
        outline = theme.red_piece_outline_rgb if int(player) == RED else theme.black_piece_outline_rgb
        bbox = _bbox_from_center((cx, layer_y), float(disk_radius))
        shadow = (bbox[0] + 2.0, bbox[1] + 2.0, bbox[2] + 2.0, bbox[3] + 2.0)
        draw.ellipse(shadow, fill=(0, 0, 0, 46))
        draw.ellipse(bbox, fill=tuple(fill) + (255,), outline=tuple(outline) + (255,), width=max(2, int(round(float(disk_radius) * 0.13))))
        inner = _bbox_from_center((cx, layer_y), float(disk_radius) * 0.62)
        draw.ellipse(inner, outline=tuple(outline) + (150,), width=max(1, int(round(float(disk_radius) * 0.05))))
        all_bboxes.append(bbox)
    if bool(stack.top_crowned):
        crown_radius = float(disk_radius) * 0.38
        tx, ty = top_center
        points = (
            (tx - crown_radius * 0.95, ty + crown_radius * 0.20),
            (tx - crown_radius * 0.50, ty - crown_radius * 0.52),
            (tx, ty + crown_radius * 0.04),
            (tx + crown_radius * 0.50, ty - crown_radius * 0.52),
            (tx + crown_radius * 0.95, ty + crown_radius * 0.20),
            (tx + crown_radius * 0.72, ty + crown_radius * 0.54),
            (tx - crown_radius * 0.72, ty + crown_radius * 0.54),
        )
        draw.polygon(points, fill=tuple(theme.crown_rgb) + (245,), outline=tuple(theme.crown_outline_rgb) + (255,))
    x0 = min(bbox[0] for bbox in all_bboxes)
    y0 = min(bbox[1] for bbox in all_bboxes)
    x1 = max(bbox[2] for bbox in all_bboxes)
    y1 = max(bbox[3] for bbox in all_bboxes)
    return [round(float(cx), 3), round(float(top_center[1]), 3)], [round(x0, 3), round(y0, 3), round(x1, 3), round(y1, 3)]


def _render_scene(
    *,
    sample: _Sample,
    axes: _ResolvedAxes,
    instance_seed: int,
    params: Mapping[str, Any],
) -> _RenderedScene:
    unit_scale, unit_scale_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.layout",
        ),
        unit_scale_meta,
    )
    cell_min = int(group_default(_RENDER_DEFAULTS, "cell_size_min_px", _DEFAULTS.cell_size_min_px))
    cell_max = int(group_default(_RENDER_DEFAULTS, "cell_size_max_px", _DEFAULTS.cell_size_max_px))
    scaled_min = scale_games_px(cell_min, unit_scale, min_px=48)
    scaled_max = scale_games_px(cell_max, unit_scale, min_px=max(52, scaled_min))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.render")
    cell_size = int(rng.randint(min(scaled_min, scaled_max), max(scaled_min, scaled_max)))
    board_px = int(cell_size) * int(sample.board_size)
    base_canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
    base_canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
    dynamic_canvas_enabled = bool(params.get("dynamic_canvas_size_enabled", group_default(_RENDER_DEFAULTS, "dynamic_canvas_size_enabled", _DEFAULTS.dynamic_canvas_size_enabled)))
    canvas_width = int(base_canvas_width)
    canvas_height = int(base_canvas_height)
    if dynamic_canvas_enabled and params.get("canvas_width") is None:
        canvas_width = min(
            int(base_canvas_width),
            max(
                int(params.get("canvas_min_width_px", group_default(_RENDER_DEFAULTS, "canvas_min_width_px", _DEFAULTS.canvas_min_width_px))),
                int(round(float(board_px) + (2.0 * float(params.get("canvas_side_padding_px", group_default(_RENDER_DEFAULTS, "canvas_side_padding_px", _DEFAULTS.canvas_side_padding_px)))))),
            ),
        )
    if dynamic_canvas_enabled and params.get("canvas_height") is None:
        canvas_height = min(
            int(base_canvas_height),
            max(
                int(params.get("canvas_min_height_px", group_default(_RENDER_DEFAULTS, "canvas_min_height_px", _DEFAULTS.canvas_min_height_px))),
                int(round(float(board_px) + (2.0 * float(params.get("canvas_vertical_padding_px", group_default(_RENDER_DEFAULTS, "canvas_vertical_padding_px", _DEFAULTS.canvas_vertical_padding_px)))))),
            ),
        )
    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.panel_scene_style",
        treatment_weights=params.get("panel_scene_treatment_weights", group_default(_RENDER_DEFAULTS, "panel_scene_treatment_weights", None)),
        palette_weights=params.get("panel_scene_palette_weights", group_default(_RENDER_DEFAULTS, "panel_scene_palette_weights", None)),
    )
    image, background_meta = make_panel_scene_background(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        style=panel_style,
    )
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image, "RGBA")
    theme, theme_meta = _theme_for_style(str(axes.style_variant))
    board_bbox = (
        round(0.5 * (float(canvas_width) - float(board_px)), 3),
        round(0.5 * (float(canvas_height) - float(board_px)), 3),
        round(0.5 * (float(canvas_width) + float(board_px)), 3),
        round(0.5 * (float(canvas_height) + float(board_px)), 3),
    )
    board_bbox, _dx, _dy, resolved_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=board_bbox,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        jitter=layout_jitter,
    )
    frame_width = scale_games_px(
        group_default(_RENDER_DEFAULTS, "board_frame_width_px", _DEFAULTS.board_frame_width_px),
        unit_scale,
        min_px=3,
    )
    panel_pad = max(18, int(round(float(cell_size) * 0.26)))
    panel_bbox = (
        int(round(float(board_bbox[0]) - panel_pad)),
        int(round(float(board_bbox[1]) - panel_pad)),
        int(round(float(board_bbox[2]) + panel_pad)),
        int(round(float(board_bbox[3]) + panel_pad)),
    )
    draw_panel_scene_chrome(draw, bbox=panel_bbox, style=panel_style, radius=24, border_width=2)
    draw.rounded_rectangle(
        panel_bbox,
        radius=22,
        fill=tuple(theme.board_fill_rgb) + (230,),
        outline=tuple(theme.board_border_rgb) + (255,),
        width=max(2, int(frame_width)),
    )
    cell_bboxes: dict[str, list[float]] = {}
    cell_centers: dict[str, list[float]] = {}
    for row in range(int(sample.board_size)):
        for col in range(int(sample.board_size)):
            cell_id = _cell_id((row, col))
            x0 = float(board_bbox[0]) + (float(col) * float(cell_size))
            y0 = float(board_bbox[1]) + (float(row) * float(cell_size))
            bbox = (x0, y0, x0 + float(cell_size), y0 + float(cell_size))
            playable = (row + col) % 2 == 1
            fill = theme.dark_cell_rgb if playable else theme.light_cell_rgb
            draw.rectangle(
                bbox,
                fill=tuple(fill) + (255,),
                outline=tuple(theme.playable_outline_rgb if playable else theme.board_border_rgb) + (200,),
                width=1,
            )
            cell_bboxes[cell_id] = [round(float(value), 3) for value in bbox]
            cell_centers[cell_id] = [round(x0 + (0.5 * float(cell_size)), 3), round(y0 + (0.5 * float(cell_size)), 3)]
    stack_centers: dict[str, list[float]] = {}
    stack_bboxes: dict[str, list[float]] = {}
    entities: list[dict[str, Any]] = []
    disk_radius = max(12.0, float(cell_size) * 0.31)
    stack_by_coord = {tuple(stack.coord): stack for stack in sample.stacks}
    for coord in _playable_coords(int(sample.board_size)):
        cell_id = _cell_id(coord)
        stack = stack_by_coord.get(tuple(coord))
        entity = {
            "entity_id": str(cell_id),
            "entity_type": "tower_draughts_cell",
            "row": int(coord[0]),
            "col": int(coord[1]),
            "playable": True,
            "state": "empty" if stack is None else "occupied",
            "center_px": list(cell_centers[cell_id]),
            "bbox_px": list(cell_bboxes[cell_id]),
            "stack_id": "",
        }
        if stack is not None:
            stack_id = "stack_marked" if sample.marked_coord == tuple(coord) else _stack_id(coord)
            center, bbox = _draw_stack(
                draw,
                stack=stack,
                cell_bbox=cell_bboxes[cell_id],
                theme=theme,
                instance_seed=int(instance_seed),
                disk_radius=float(disk_radius),
            )
            stack_centers[stack_id] = list(center)
            stack_bboxes[stack_id] = list(bbox)
            entity.update(
                {
                    "stack_id": str(stack_id),
                    "stack_height": int(stack.height),
                    "stack_owner": _player_name(int(stack.owner)),
                    "top_crowned": bool(stack.top_crowned),
                    "stack_center_px": list(center),
                    "stack_bbox_px": list(bbox),
                }
            )
        entities.append(entity)
    marker_metadata: dict[str, Any] | None = None
    if sample.marked_coord is not None and "stack_marked" in stack_bboxes:
        marker_width = scale_games_px(
            group_default(_RENDER_DEFAULTS, "marker_width_px", _DEFAULTS.marker_width_px),
            unit_scale,
            min_px=3,
        )
        marked_bbox = stack_bboxes["stack_marked"]
        marker_pad = max(4.0, float(marker_width) * 1.4)
        marker_bbox = (
            float(marked_bbox[0]) - marker_pad,
            float(marked_bbox[1]) - marker_pad,
            float(marked_bbox[2]) + marker_pad,
            float(marked_bbox[3]) + marker_pad,
        )
        marker_style = resolve_semantic_marker_style(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.marked_stack",
            role="marked_stack",
            surface_rgbs=(theme.board_fill_rgb, theme.dark_cell_rgb),
            preferred_rgbs=((255, 214, 38), (255, 247, 92), (246, 80, 164), (36, 205, 228)),
        )
        marker_metadata = draw_semantic_ellipse_marker(
            draw,
            marker_bbox,
            style=marker_style,
            width=max(3, int(marker_width)),
            marker_kind="marked_stack_ring",
            extra_metadata={"stack_id": "stack_marked"},
        )
        x_metadata = draw_optional_marker_x(
            draw,
            marked_bbox,
            enabled=True,
            width=max(3, int(round(float(marker_width) * 0.72))),
            inset_fraction=0.25,
            marker_kind="marked_stack_x",
            extra_metadata={"stack_id": "stack_marked"},
        )
        if x_metadata is not None:
            marker_metadata = {**dict(marker_metadata), "overlay_x": dict(x_metadata)}
    render_map = {
        "board_bbox_px": [round(float(value), 3) for value in board_bbox],
        "panel_bbox_px": [float(value) for value in panel_bbox],
        "cell_bboxes_px": dict(cell_bboxes),
        "cell_centers_px": dict(cell_centers),
        "stack_centers_px": dict(stack_centers),
        "stack_bboxes_px": dict(stack_bboxes),
        "marked_stack_marker": marker_metadata,
        "layout_jitter": dict(resolved_jitter),
        "effective_cell_size_px": int(cell_size),
        "effective_disk_radius_px": round(float(disk_radius), 3),
    }
    return _RenderedScene(
        image=image.convert("RGB"),
        entities=tuple(entities),
        render_map=render_map,
        style_meta={
            "panel_scene_style": dict(panel_style_meta),
            "tower_draughts_board_style": dict(theme_meta),
        },
        background_meta=dict(background_meta),
    )


def _json_examples() -> Tuple[str, str]:
    annotation = [[180.0, 220.0], [268.0, 220.0]]
    return (
        json.dumps({"annotation": annotation, "answer": 2}, separators=(",", ":"), ensure_ascii=True),
        json.dumps({"answer": 2}, separators=(",", ":"), ensure_ascii=True),
    )


def _build_prompt(*, sample: _Sample, query_id: str, task_id: str, instance_seed: int) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    answer_hint_key = f"answer_hint_{str(query_id)}"
    annotation_hint_key = f"annotation_hint_{str(query_id)}"
    required_keys = [
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        "object_description",
        answer_hint_key,
        annotation_hint_key,
    ]
    if str(query_id) == CONTROLLED_STACK_QUERY_ID:
        required_keys.append("ownership_rule_text")
    elif str(query_id) == MARKED_DESTINATION_QUERY_ID:
        required_keys.extend(["ownership_rule_text", "movement_rule_text"])
    else:
        required_keys.extend(["ownership_rule_text", "capture_rule_text"])
    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        tuple(required_keys),
        context=f"prompt defaults for {task_id}",
    )
    json_example, json_example_answer_only = _json_examples()
    prompt_selection = render_scene_prompt_variants(
        domain="games",
        scene_id=SCENE_ID,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        dynamic_slots={
            "object_description": str(prompt_defaults["object_description"]),
            "target_player_name": _player_name(int(sample.target_player)),
            "marked_player_name": _player_name(int(sample.marked_player)),
            "ownership_rule_text": str(prompt_defaults.get("ownership_rule_text", "")),
            "movement_rule_text": str(prompt_defaults.get("movement_rule_text", "")),
            "capture_rule_text": str(prompt_defaults.get("capture_rule_text", "")),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults[answer_hint_key]),
            "annotation_hint": str(prompt_defaults[annotation_hint_key]),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        },
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "bundle_id": str(prompt_defaults["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
    }




def _annotation_entity_id(*, query_id: str, coord: Coord) -> str:
    if str(query_id) == MARKED_DESTINATION_QUERY_ID:
        return _cell_id(coord)
    return _stack_id(coord)


def _build_task_output(
    *,
    task_id: str,
    query_id: str,
    sampled: _Sample,
    axes: _ResolvedAxes,
    instance_seed: int,
    params: Mapping[str, Any],
) -> TaskOutput:
    rendered = _render_scene(sample=sampled, axes=axes, instance_seed=int(instance_seed), params=params)
    annotation_entity_ids = tuple(_annotation_entity_id(query_id=str(query_id), coord=coord) for coord in sampled.annotation_coords)
    annotation_points: list[list[float]] = []
    for entity_id in annotation_entity_ids:
        if str(entity_id).startswith("cell_"):
            annotation_points.append(list(rendered.render_map["cell_centers_px"][entity_id]))
        else:
            annotation_points.append(list(rendered.render_map["stack_centers_px"][entity_id]))
    image, post_noise_meta = apply_post_image_noise(
        rendered.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    prompt, prompt_variants, prompt_meta = _build_prompt(
        sample=sampled,
        query_id=str(query_id),
        task_id=str(task_id),
        instance_seed=int(instance_seed),
    )
    answer_gt = TypedValue(type="integer", value=int(sampled.answer))
    annotation_gt = TypedValue(type="point_set", value=[list(point) for point in annotation_points])
    stack_payload = [
        {
            "coord": [int(stack.coord[0]), int(stack.coord[1])],
            "height": int(stack.height),
            "disks": [_player_name(int(player)) for player in stack.disks],
            "owner": _player_name(int(stack.owner)),
            "top_crowned": bool(stack.top_crowned),
        }
        for stack in sampled.stacks
    ]
    trace_payload = {
        "scene_ir": {
            "scene_kind": "games_tower_draughts_board",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "style_variant": str(sampled.style_variant),
                "board_size": int(sampled.board_size),
                "marked_stack_id": "stack_marked" if sampled.marked_coord is not None else "",
                "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
            },
        },
        "query_spec": {
            "query_id": str(query_id),
            "template_id": str(prompt_meta["bundle_id"]),
            "prompt_variant": dict(prompt_meta["prompt_variant"]),
            "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
            "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
            "params": {
                "style_variant": str(axes.style_variant),
                "style_variant_probabilities": dict(axes.style_variant_probabilities),
                "board_size": int(axes.board_size),
                "board_size_probabilities": dict(axes.board_size_probabilities),
                "target_answer": int(sampled.answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "target_answer_probabilities": dict(axes.target_answer_probabilities),
                "target_player": _player_name(int(axes.target_player)),
                "target_player_probabilities": dict(axes.target_player_probabilities),
                "marked_player": _player_name(int(axes.marked_player)),
                "marked_player_probabilities": dict(axes.marked_player_probabilities),
                "top_kind": str(axes.top_kind),
                "top_kind_probabilities": dict(axes.top_kind_probabilities),
            },
        },
        "render_spec": {
            "style_variant": str(sampled.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(rendered.style_meta.get("panel_scene_style", {})),
            "tower_draughts_board_style": dict(rendered.style_meta.get("tower_draughts_board_style", {})),
            "effective_cell_size_px": int(rendered.render_map["effective_cell_size_px"]),
            "effective_disk_radius_px": float(rendered.render_map["effective_disk_radius_px"]),
        },
        "render_map": dict(rendered.render_map),
        "execution_trace": {
            "query_id": str(query_id),
            "style_variant": str(sampled.style_variant),
            "board_size": int(sampled.board_size),
            "construction_mode": str(sampled.construction_mode),
            "target_answer": int(sampled.answer),
            "target_answer_support": [int(value) for value in axes.target_answer_support],
            "target_player": _player_name(int(sampled.target_player)),
            "marked_player": _player_name(int(sampled.marked_player)),
            "top_kind": str(sampled.top_kind),
            "marked_coord": None if sampled.marked_coord is None else [int(sampled.marked_coord[0]), int(sampled.marked_coord[1])],
            "stacks": stack_payload,
            "annotation_coords": [[int(coord[0]), int(coord[1])] for coord in sampled.annotation_coords],
            "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
            "legal_destinations": (
                [[int(coord[0]), int(coord[1])] for coord in sampled.annotation_coords]
                if str(query_id) == MARKED_DESTINATION_QUERY_ID
                else []
            ),
            "captured_stacks": (
                [[int(coord[0]), int(coord[1])] for coord in sampled.annotation_coords]
                if str(query_id) == MARKED_CAPTURE_QUERY_ID
                else []
            ),
        },
        "witness_symbolic": {
            "type": "point_set",
            "ids": [str(entity_id) for entity_id in annotation_entity_ids],
        },
        "projected_annotation": {
            "type": "point_set",
            "point_set": [list(point) for point in annotation_points],
            "pixel_point_set": [list(point) for point in annotation_points],
        },
        "background": dict(rendered.background_meta),
        "post_image_noise": post_noise_meta,
    }
    return TaskOutput(
        prompt=str(prompt),
        prompt_variants=dict(prompt_variants),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(query_id),
    )


class _BaseTowerDraughtsTask:
    """Shared generation wrapper for tower draughts tasks."""

    task_kind: str

    def _generate_sample(self, *, rng: Any, axes: _ResolvedAxes) -> _Sample:
        if str(self.task_kind) == CONTROLLED_STACK_QUERY_ID:
            return _sample_controlled_scene(rng=rng, axes=axes)
        if str(self.task_kind) == MARKED_DESTINATION_QUERY_ID:
            return _sample_destination_scene(rng=rng, axes=axes)
        return _sample_capture_scene(rng=rng, axes=axes)

    def generate(self, instance_seed: int, *, params: Dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        params = dict(params or {})
        axes = _resolve_axes(int(instance_seed), params=params, task_kind=str(self.task_kind))
        sampled: _Sample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{self.task_kind}.attempt.{int(attempt_index)}")
            try:
                sampled = self._generate_sample(rng=rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled is None:
            raise RuntimeError(f"{self.task_id} failed to generate after {max_attempts} attempts")
        return _build_task_output(
            task_id=str(self.task_id),
            query_id=str(self.task_kind),
            sampled=sampled,
            axes=axes,
            instance_seed=int(instance_seed),
            params=params,
        )


class GamesTowerDraughtsBoardControlledStackCountTask(_BaseTowerDraughtsTask):
    """Count stacks controlled by one player, using top-disk ownership."""

    task_id = CONTROLLED_STACK_TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    task_kind = CONTROLLED_STACK_QUERY_ID


@register_task
class GamesTowerDraughtsBoardMarkedStackDestinationCountTask(_BaseTowerDraughtsTask):
    """Count empty destinations for one marked tower draughts stack."""

    task_id = MARKED_DESTINATION_TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    task_kind = MARKED_DESTINATION_QUERY_ID


class GamesTowerDraughtsBoardMarkedStackCaptureCountTask(_BaseTowerDraughtsTask):
    """Count immediate captures for one marked tower draughts stack."""

    task_id = MARKED_CAPTURE_TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    task_kind = MARKED_CAPTURE_QUERY_ID


__all__ = [
    "BLACK",
    "CONTROLLED_STACK_QUERY_ID",
    "CONTROLLED_STACK_TASK_ID",
    "GamesTowerDraughtsBoardControlledStackCountTask",
    "GamesTowerDraughtsBoardMarkedStackCaptureCountTask",
    "GamesTowerDraughtsBoardMarkedStackDestinationCountTask",
    "MARKED_CAPTURE_QUERY_ID",
    "MARKED_CAPTURE_TASK_ID",
    "MARKED_DESTINATION_QUERY_ID",
    "MARKED_DESTINATION_TASK_ID",
    "RED",
    "StackSpec",
    "_capture_targets",
    "_legal_destinations",
    "_playable_coords",
]
