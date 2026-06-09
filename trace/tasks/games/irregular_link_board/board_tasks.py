"""Irregular link board movement-count tasks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.complexity import build_games_complexity, normalize_linear, resolve_games_complexity_weights
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
from ..shared.visual_defaults import load_games_noise_defaults


TASK_GROUP = "irregular_link_board"
SCENE_ID = "irregular_link_board"
TASK_ID = "games_irregular_link_board_base"
MARKED_DESTINATION_TASK_ID = "task_games__irregular_link_board__marked_piece_destination_count"
CAPTURE_MOVE_TASK_ID = "task_games__irregular_link_board__capture_move_count"
MARKED_DESTINATION_QUERY_ID = "marked_piece_destination_count"
CAPTURE_MOVE_QUERY_ID = "capture_move_count"
STYLE_VARIANTS: Tuple[str, ...] = ("woodcut", "ink_diagram", "garden_cloth", "night_lines", "parchment")
SCENE_VARIANTS: Tuple[str, ...] = ("sparse_links", "mixed_links", "dense_links")
Coord = Tuple[int, int]
Edge = Tuple[Coord, Coord]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for irregular link board scenes."""

    target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8)
    board_size_support: Tuple[int, ...] = (4, 5, 6)
    capture_board_size_support: Tuple[int, ...] = (5, 6)
    min_total_piece_count: int = 4
    max_total_piece_count: int = 12
    canvas_width: int = 780
    canvas_height: int = 760
    panel_margin_px: int = 52
    max_board_size_px: int = 560
    edge_width_px: int = 5
    point_radius_px: int = 14
    piece_radius_px: int = 23
    marker_width_px: int = 5
    dynamic_canvas_size_enabled: bool = True
    canvas_min_width_px: int = 560
    canvas_min_height_px: int = 540
    canvas_side_padding_px: int = 150
    canvas_vertical_padding_px: int = 150


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved generation and style axes for one sample."""

    scene_variant: str
    style_variant: str
    board_size: int
    target_answer: int
    target_answer_support: Tuple[int, ...]
    board_size_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _Sample:
    """One symbolic variable-link board and movement-count witness."""

    board_size: int
    scene_variant: str
    style_variant: str
    marked_coord: Coord
    occupied_coords: Tuple[Coord, ...]
    edges: Tuple[Edge, ...]
    annotation_coords: Tuple[Coord, ...]
    answer: int
    construction_mode: str


@dataclass(frozen=True)
class _Theme:
    """Scene-local palette for an irregular link board."""

    board_fill_rgb: Tuple[int, int, int]
    board_border_rgb: Tuple[int, int, int]
    edge_rgb: Tuple[int, int, int]
    point_fill_rgb: Tuple[int, int, int]
    point_outline_rgb: Tuple[int, int, int]
    marked_piece_fill_rgb: Tuple[int, int, int]
    marked_piece_outline_rgb: Tuple[int, int, int]
    blocker_piece_fill_rgb: Tuple[int, int, int]
    blocker_piece_outline_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered board plus trace-friendly maps."""

    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", TASK_GROUP)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group=TASK_GROUP, apply_prob=0.5)


def _all_coords(board_size: int) -> Tuple[Coord, ...]:
    return tuple((row, col) for row in range(int(board_size)) for col in range(int(board_size)))


def _point_id(coord: Coord) -> str:
    return f"point_r{int(coord[0])}_c{int(coord[1])}"


def _piece_id(coord: Coord) -> str:
    return f"piece_r{int(coord[0])}_c{int(coord[1])}"


def _edge(a: Coord, b: Coord) -> Edge:
    ordered = tuple(sorted((tuple(a), tuple(b))))  # type: ignore[arg-type]
    return ordered  # type: ignore[return-value]


def _base_lattice_edges(board_size: int) -> Tuple[Edge, ...]:
    """Return a Fanorona-like link lattice with no non-node diagonal crossings."""

    size = int(board_size)
    seen: set[Edge] = set()
    for row in range(size):
        for col in range(size):
            if col + 1 < size:
                seen.add(_edge((row, col), (row, col + 1)))
            if row + 1 < size:
                seen.add(_edge((row, col), (row + 1, col)))

    for row in range(size - 1):
        for col in range(size - 1):
            if (row + col) % 2 == 0:
                seen.add(_edge((row, col), (row + 1, col + 1)))
            else:
                seen.add(_edge((row + 1, col), (row, col + 1)))
    return tuple(sorted(seen))


def _neighbors(coord: Coord, board_size: int) -> Tuple[Coord, ...]:
    coord = (int(coord[0]), int(coord[1]))
    out: list[Coord] = []
    for a, b in _base_lattice_edges(int(board_size)):
        if a == coord:
            out.append(b)
        elif b == coord:
            out.append(a)
    return tuple(sorted(out))


def _all_possible_edges(board_size: int) -> Tuple[Edge, ...]:
    return _base_lattice_edges(int(board_size))


def _legal_destinations(*, marked_coord: Coord, occupied_coords: Sequence[Coord], edges: Sequence[Edge], board_size: int) -> Tuple[Coord, ...]:
    occupied = {tuple(coord) for coord in occupied_coords}
    edge_set = {tuple(edge) for edge in edges}
    out: list[Coord] = []
    for neighbor in _neighbors(marked_coord, int(board_size)):
        if tuple(neighbor) in occupied:
            continue
        if _edge(marked_coord, neighbor) in edge_set:
            out.append(neighbor)
    return tuple(sorted(out))


def _capture_paths(marked_coord: Coord, board_size: int) -> Tuple[Tuple[Coord, Coord], ...]:
    base_edges = set(_all_possible_edges(int(board_size)))
    out: list[Tuple[Coord, Coord]] = []
    for captured in _neighbors(marked_coord, int(board_size)):
        dr = int(captured[0]) - int(marked_coord[0])
        dc = int(captured[1]) - int(marked_coord[1])
        destination = (int(captured[0]) + dr, int(captured[1]) + dc)
        if not (0 <= destination[0] < int(board_size) and 0 <= destination[1] < int(board_size)):
            continue
        if _edge(captured, destination) not in base_edges:
            continue
        out.append((destination, captured))
    return tuple(sorted(out))


def _capture_destinations(*, marked_coord: Coord, occupied_coords: Sequence[Coord], edges: Sequence[Edge], board_size: int) -> Tuple[Coord, ...]:
    occupied = {tuple(coord) for coord in occupied_coords}
    edge_set = {tuple(edge) for edge in edges}
    out: list[Coord] = []
    for destination, captured in _capture_paths(marked_coord, int(board_size)):
        if tuple(destination) in occupied:
            continue
        if tuple(captured) not in occupied:
            continue
        if _edge(marked_coord, captured) not in edge_set:
            continue
        if _edge(captured, destination) not in edge_set:
            continue
        out.append(destination)
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


def _resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    board_size_support_key: str = "board_size_support",
    fallback_board_size_support: Sequence[int] | None = None,
) -> _ResolvedAxes:
    scene_variant, scene_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SCENE_VARIANTS,
    )
    style_variant, style_probs = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=STYLE_VARIANTS,
    )
    board_size, board_size_probs = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(board_size_support_key),
        explicit_key="board_size",
        fallback_support=tuple(int(value) for value in (fallback_board_size_support or _DEFAULTS.board_size_support)),
        namespace=f"{TASK_ID}.board_size",
        balanced_flag_key="balanced_board_size_sampling",
        namespace_support_permutation=True,
    )
    target_answer, target_probs = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="target_answer_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.target_answer_support,
        namespace=f"{TASK_ID}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="target_answer_support",
        fallback=_DEFAULTS.target_answer_support,
    )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        board_size=int(board_size),
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_support),
        board_size_probabilities=dict(board_size_probs),
        target_answer_probabilities=dict(target_probs),
        scene_variant_probabilities=dict(scene_probs),
        style_variant_probabilities=dict(style_probs),
    )


def _link_density(scene_variant: str) -> float:
    if str(scene_variant) == "sparse_links":
        return 0.42
    if str(scene_variant) == "dense_links":
        return 0.72
    return 0.56


def _sample_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    board_size = int(axes.board_size)
    target = int(axes.target_answer)
    if target < 0 or target > 8:
        raise ValueError("irregular link board target answer must be in 0..8")
    viable = [coord for coord in _all_coords(board_size) if len(_neighbors(coord, board_size)) >= target]
    if not viable:
        raise ValueError(f"no marked point can realize target answer {target}")
    rng.shuffle(viable)
    marked_coord = viable[0]
    neighbors = list(_neighbors(marked_coord, board_size))
    rng.shuffle(neighbors)
    destinations = set(neighbors[:target])
    non_dest_neighbors = [coord for coord in neighbors if coord not in destinations]

    edges: set[Edge] = {_edge(marked_coord, coord) for coord in destinations}
    occupied: set[Coord] = {marked_coord}

    for coord in non_dest_neighbors:
        connect_and_block = bool(rng.random() < 0.58)
        if connect_and_block:
            edges.add(_edge(marked_coord, coord))
            occupied.add(coord)
        elif rng.random() < 0.38:
            occupied.add(coord)

    possible_edges = set(_all_possible_edges(board_size))
    marked_incident = {_edge(marked_coord, coord) for coord in neighbors}
    density = _link_density(str(axes.scene_variant))
    for edge in possible_edges:
        if edge in marked_incident:
            continue
        if rng.random() < float(density):
            edges.add(edge)

    min_pieces = int(group_default(_GEN_DEFAULTS, "min_total_piece_count", _DEFAULTS.min_total_piece_count))
    max_pieces = int(group_default(_GEN_DEFAULTS, "max_total_piece_count", _DEFAULTS.max_total_piece_count))
    desired_piece_count = max(len(occupied), int(rng.randint(min_pieces, max_pieces)))
    protected_empty = set(destinations)
    candidates = [coord for coord in _all_coords(board_size) if coord not in occupied and coord not in protected_empty]
    rng.shuffle(candidates)
    for coord in candidates:
        if len(occupied) >= desired_piece_count:
            break
        occupied.add(coord)

    annotation = _legal_destinations(
        marked_coord=marked_coord,
        occupied_coords=tuple(sorted(occupied)),
        edges=tuple(sorted(edges)),
        board_size=board_size,
    )
    if len(annotation) != target:
        raise ValueError("constructed legal destination count mismatch")
    return _Sample(
        board_size=int(board_size),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        marked_coord=marked_coord,
        occupied_coords=tuple(sorted(occupied)),
        edges=tuple(sorted(edges)),
        annotation_coords=tuple(annotation),
        answer=int(len(annotation)),
        construction_mode="target_conditioned_variable_link_board",
    )


def _sample_capture_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    board_size = int(axes.board_size)
    target = int(axes.target_answer)
    if target < 0 or target > 8:
        raise ValueError("irregular link capture target answer must be in 0..8")
    viable = [coord for coord in _all_coords(board_size) if len(_capture_paths(coord, board_size)) >= target]
    if not viable:
        raise ValueError(f"no marked point can realize capture target answer {target}")
    rng.shuffle(viable)
    marked_coord = viable[0]
    capture_paths = list(_capture_paths(marked_coord, board_size))
    rng.shuffle(capture_paths)
    selected_paths = tuple(capture_paths[:target])
    selected_destinations = {path[0] for path in selected_paths}
    non_selected_paths = [path for path in capture_paths if path[0] not in selected_destinations]

    edges: set[Edge] = set()
    blocked_edges: set[Edge] = set()
    occupied: set[Coord] = {marked_coord}
    protected_empty: set[Coord] = set(selected_destinations)

    for destination, captured in selected_paths:
        edges.add(_edge(marked_coord, captured))
        edges.add(_edge(captured, destination))
        occupied.add(captured)

    for destination, captured in non_selected_paths:
        if rng.random() < 0.42:
            edges.add(_edge(marked_coord, captured))
            occupied.add(captured)
            protected_empty.add(destination)
            blocked_edges.add(_edge(captured, destination))
        elif rng.random() < 0.48:
            occupied.add(destination)
            if rng.random() < 0.58:
                edges.add(_edge(marked_coord, captured))
                edges.add(_edge(captured, destination))
        else:
            occupied.add(captured)
            protected_empty.add(destination)
            blocked_edges.add(_edge(marked_coord, captured))

    possible_edges = set(_all_possible_edges(board_size))
    marked_incident = {_edge(marked_coord, coord) for coord in _neighbors(marked_coord, board_size)}
    density = _link_density(str(axes.scene_variant))
    for edge in possible_edges:
        if edge in blocked_edges:
            continue
        if edge in marked_incident and edge not in edges:
            continue
        if edge in edges:
            continue
        if rng.random() < float(density):
            edges.add(edge)

    min_pieces = int(group_default(_GEN_DEFAULTS, "min_total_piece_count", _DEFAULTS.min_total_piece_count))
    max_pieces = int(group_default(_GEN_DEFAULTS, "max_total_piece_count", _DEFAULTS.max_total_piece_count))
    desired_piece_count = max(len(occupied), int(rng.randint(min_pieces, max_pieces)))
    candidates = [coord for coord in _all_coords(board_size) if coord not in occupied and coord not in protected_empty]
    rng.shuffle(candidates)
    for coord in candidates:
        if len(occupied) >= desired_piece_count:
            break
        occupied.add(coord)

    annotation = _capture_destinations(
        marked_coord=marked_coord,
        occupied_coords=tuple(sorted(occupied)),
        edges=tuple(sorted(edges)),
        board_size=board_size,
    )
    if len(annotation) != target:
        raise ValueError("constructed capture move count mismatch")
    return _Sample(
        board_size=int(board_size),
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        marked_coord=marked_coord,
        occupied_coords=tuple(sorted(occupied)),
        edges=tuple(sorted(edges)),
        annotation_coords=tuple(annotation),
        answer=int(len(annotation)),
        construction_mode="target_conditioned_capture_move_board",
    )


def _theme_for_style(style_variant: str) -> Tuple[_Theme, Dict[str, Any]]:
    themes: dict[str, _Theme] = {
        "woodcut": _Theme(
            board_fill_rgb=(229, 200, 150),
            board_border_rgb=(103, 72, 39),
            edge_rgb=(108, 76, 45),
            point_fill_rgb=(250, 232, 188),
            point_outline_rgb=(82, 57, 34),
            marked_piece_fill_rgb=(34, 45, 65),
            marked_piece_outline_rgb=(248, 244, 232),
            blocker_piece_fill_rgb=(181, 65, 55),
            blocker_piece_outline_rgb=(88, 31, 29),
        ),
        "ink_diagram": _Theme(
            board_fill_rgb=(238, 237, 226),
            board_border_rgb=(51, 52, 56),
            edge_rgb=(58, 60, 66),
            point_fill_rgb=(253, 251, 243),
            point_outline_rgb=(44, 46, 52),
            marked_piece_fill_rgb=(29, 40, 56),
            marked_piece_outline_rgb=(250, 251, 255),
            blocker_piece_fill_rgb=(83, 107, 133),
            blocker_piece_outline_rgb=(33, 48, 64),
        ),
        "garden_cloth": _Theme(
            board_fill_rgb=(213, 233, 204),
            board_border_rgb=(63, 101, 68),
            edge_rgb=(71, 113, 76),
            point_fill_rgb=(244, 251, 235),
            point_outline_rgb=(55, 88, 58),
            marked_piece_fill_rgb=(39, 64, 50),
            marked_piece_outline_rgb=(246, 255, 240),
            blocker_piece_fill_rgb=(197, 72, 85),
            blocker_piece_outline_rgb=(94, 33, 43),
        ),
        "night_lines": _Theme(
            board_fill_rgb=(34, 42, 58),
            board_border_rgb=(174, 190, 209),
            edge_rgb=(120, 206, 232),
            point_fill_rgb=(56, 72, 96),
            point_outline_rgb=(195, 221, 236),
            marked_piece_fill_rgb=(241, 246, 255),
            marked_piece_outline_rgb=(15, 23, 42),
            blocker_piece_fill_rgb=(255, 185, 89),
            blocker_piece_outline_rgb=(87, 47, 18),
        ),
        "parchment": _Theme(
            board_fill_rgb=(239, 223, 185),
            board_border_rgb=(118, 89, 49),
            edge_rgb=(125, 92, 55),
            point_fill_rgb=(252, 240, 209),
            point_outline_rgb=(90, 67, 38),
            marked_piece_fill_rgb=(38, 55, 88),
            marked_piece_outline_rgb=(250, 247, 231),
            blocker_piece_fill_rgb=(151, 76, 52),
            blocker_piece_outline_rgb=(72, 35, 26),
        ),
    }
    resolved = str(style_variant) if str(style_variant) in themes else "woodcut"
    return themes[resolved], {
        "style_variant": str(resolved),
        "available_styles": list(STYLE_VARIANTS),
        "board_style_policy": "scene_local_irregular_link_board_palette",
    }


def _bbox(center: Sequence[float], radius: float) -> Tuple[float, float, float, float]:
    cx, cy = float(center[0]), float(center[1])
    return (
        round(cx - float(radius), 3),
        round(cy - float(radius), 3),
        round(cx + float(radius), 3),
        round(cy + float(radius), 3),
    )


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
    max_board_size_px = scale_games_px(
        group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px),
        unit_scale,
        min_px=280,
    )
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
                int(round(float(max_board_size_px) + (2.0 * float(params.get("canvas_side_padding_px", group_default(_RENDER_DEFAULTS, "canvas_side_padding_px", _DEFAULTS.canvas_side_padding_px)))))),
            ),
        )
    if dynamic_canvas_enabled and params.get("canvas_height") is None:
        canvas_height = min(
            int(base_canvas_height),
            max(
                int(params.get("canvas_min_height_px", group_default(_RENDER_DEFAULTS, "canvas_min_height_px", _DEFAULTS.canvas_min_height_px))),
                int(round(float(max_board_size_px) + (2.0 * float(params.get("canvas_vertical_padding_px", group_default(_RENDER_DEFAULTS, "canvas_vertical_padding_px", _DEFAULTS.canvas_vertical_padding_px)))))),
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

    margin = int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px)))
    board_size = int(sample.board_size)
    max_span = min(float(max_board_size_px), float(canvas_width - (2 * margin)), float(canvas_height - (2 * margin)))
    step = max(48.0, float(max_span) / float(board_size - 1))
    board_span = float(step * float(board_size - 1))
    board_bbox = (
        round(0.5 * (float(canvas_width) - board_span), 3),
        round(0.5 * (float(canvas_height) - board_span), 3),
        round(0.5 * (float(canvas_width) + board_span), 3),
        round(0.5 * (float(canvas_height) + board_span), 3),
    )
    board_bbox, _dx, _dy, resolved_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=board_bbox,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        jitter=layout_jitter,
    )
    left, top = float(board_bbox[0]), float(board_bbox[1])
    centers: Dict[Coord, Tuple[float, float]] = {
        coord: (round(left + (float(coord[1]) * step), 3), round(top + (float(coord[0]) * step), 3))
        for coord in _all_coords(board_size)
    }
    edge_width = scale_games_px(group_default(_RENDER_DEFAULTS, "edge_width_px", _DEFAULTS.edge_width_px), unit_scale, min_px=2)
    point_radius = scale_games_px(group_default(_RENDER_DEFAULTS, "point_radius_px", _DEFAULTS.point_radius_px), unit_scale, min_px=8)
    piece_radius = scale_games_px(group_default(_RENDER_DEFAULTS, "piece_radius_px", _DEFAULTS.piece_radius_px), unit_scale, min_px=14)
    marker_width = scale_games_px(group_default(_RENDER_DEFAULTS, "marker_width_px", _DEFAULTS.marker_width_px), unit_scale, min_px=3)
    board_pad = max(22, int(round(float(piece_radius) * 1.55)))
    panel_bbox = (
        max(4, int(round(float(board_bbox[0]) - board_pad))),
        max(4, int(round(float(board_bbox[1]) - board_pad))),
        min(int(canvas_width) - 4, int(round(float(board_bbox[2]) + board_pad))),
        min(int(canvas_height) - 4, int(round(float(board_bbox[3]) + board_pad))),
    )
    draw_panel_scene_chrome(
        draw,
        bbox=panel_bbox,
        style=panel_style,
        radius=24,
        border_width=max(2, int(round(float(edge_width) * 0.65))),
    )
    graph_bbox = (
        int(round(float(board_bbox[0]) - board_pad)),
        int(round(float(board_bbox[1]) - board_pad)),
        int(round(float(board_bbox[2]) + board_pad)),
        int(round(float(board_bbox[3]) + board_pad)),
    )
    draw.rounded_rectangle(
        graph_bbox,
        radius=max(16, int(round(float(board_pad) * 0.55))),
        fill=tuple(theme.board_fill_rgb) + (226,),
        outline=tuple(theme.board_border_rgb) + (255,),
        width=max(2, int(round(float(edge_width) * 0.7))),
    )

    for edge in sample.edges:
        p0 = centers[edge[0]]
        p1 = centers[edge[1]]
        draw.line([p0, p1], fill=tuple(theme.edge_rgb) + (255,), width=max(2, int(edge_width)))

    entity_bboxes: Dict[str, List[float]] = {}
    entity_points: Dict[str, List[float]] = {}
    point_centers: Dict[str, List[float]] = {}
    point_bboxes: Dict[str, List[float]] = {}
    piece_centers: Dict[str, List[float]] = {}
    piece_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    occupied = set(sample.occupied_coords)
    for coord in _all_coords(board_size):
        point_id = _point_id(coord)
        center = centers[coord]
        point_bbox = _bbox(center, float(point_radius))
        draw.ellipse(
            point_bbox,
            fill=tuple(theme.point_fill_rgb) + (255,),
            outline=tuple(theme.point_outline_rgb) + (255,),
            width=max(1, int(round(float(edge_width) * 0.45))),
        )
        point_centers[point_id] = [float(center[0]), float(center[1])]
        point_bboxes[point_id] = [float(v) for v in point_bbox]
        entity_points[point_id] = [float(center[0]), float(center[1])]
        entity_bboxes[point_id] = [float(v) for v in point_bbox]

    for coord in sorted(occupied):
        center = centers[coord]
        piece_id = "piece_marked" if coord == sample.marked_coord else _piece_id(coord)
        is_marked = bool(coord == sample.marked_coord)
        fill = theme.marked_piece_fill_rgb if is_marked else theme.blocker_piece_fill_rgb
        outline = theme.marked_piece_outline_rgb if is_marked else theme.blocker_piece_outline_rgb
        piece_bbox = _bbox(center, float(piece_radius))
        draw.ellipse(
            piece_bbox,
            fill=tuple(fill) + (255,),
            outline=tuple(outline) + (255,),
            width=max(2, int(round(float(edge_width) * 0.8))),
        )
        piece_centers[piece_id] = [float(center[0]), float(center[1])]
        piece_bboxes[piece_id] = [float(v) for v in piece_bbox]
        entity_points[piece_id] = [float(center[0]), float(center[1])]
        entity_bboxes[piece_id] = [float(v) for v in piece_bbox]

    marker_metadata: dict[str, Any] | None = None
    marked_bbox = piece_bboxes.get("piece_marked")
    if marked_bbox is not None:
        marker_pad = max(5.0, float(marker_width) * 1.45)
        marker_bbox = (
            float(marked_bbox[0]) - marker_pad,
            float(marked_bbox[1]) - marker_pad,
            float(marked_bbox[2]) + marker_pad,
            float(marked_bbox[3]) + marker_pad,
        )
        marker_style = resolve_semantic_marker_style(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.marked_piece",
            role="marked_piece",
            surface_rgbs=(
                theme.board_fill_rgb,
                theme.marked_piece_fill_rgb,
                theme.blocker_piece_fill_rgb,
                theme.edge_rgb,
            ),
            preferred_rgbs=((255, 214, 38), (255, 247, 92), (246, 80, 164), (36, 205, 228)),
        )
        marker_metadata = draw_semantic_ellipse_marker(
            draw,
            marker_bbox,
            style=marker_style,
            width=max(3, int(marker_width)),
            marker_kind="marked_piece_ring",
            extra_metadata={"piece_id": "piece_marked"},
        )
        x_metadata = draw_optional_marker_x(
            draw,
            marked_bbox,
            enabled=True,
            width=max(3, int(round(float(marker_width) * 0.75))),
            inset_fraction=0.25,
            marker_kind="marked_piece_x",
            extra_metadata={"piece_id": "piece_marked"},
        )
        if x_metadata is not None:
            marker_metadata = {**dict(marker_metadata), "overlay_x": dict(x_metadata)}

    edge_specs = [
        {
            "from": [int(edge[0][0]), int(edge[0][1])],
            "to": [int(edge[1][0]), int(edge[1][1])],
            "from_point_id": _point_id(edge[0]),
            "to_point_id": _point_id(edge[1]),
        }
        for edge in sample.edges
    ]
    for coord in _all_coords(board_size):
        point_id = _point_id(coord)
        is_marked = coord == sample.marked_coord
        piece_id = "piece_marked" if is_marked else _piece_id(coord) if coord in occupied else ""
        entities.append(
            {
                "entity_id": str(point_id),
                "entity_type": "patterned_hunt_point",
                "row": int(coord[0]),
                "col": int(coord[1]),
                "state": "marked_piece" if is_marked else "occupied" if coord in occupied else "empty",
                "center_px": list(point_centers[point_id]),
                "bbox_px": list(point_bboxes[point_id]),
                "piece_id": str(piece_id),
                "piece_bbox_px": None if not piece_id else list(piece_bboxes[str(piece_id)]),
            }
        )
    render_map = {
        "board_bbox_px": [float(v) for v in board_bbox],
        "graph_bbox_px": [float(v) for v in graph_bbox],
        "panel_bbox_px": [float(v) for v in panel_bbox],
        "point_centers_px": dict(point_centers),
        "point_bboxes_px": dict(point_bboxes),
        "piece_centers_px": dict(piece_centers),
        "piece_bboxes_px": dict(piece_bboxes),
        "entity_points_px": dict(entity_points),
        "entity_bboxes_px": dict(entity_bboxes),
        "edges": edge_specs,
        "marked_piece_marker": marker_metadata,
        "layout_jitter": dict(resolved_jitter),
        "effective_board_step_px": round(float(step), 3),
        "effective_point_radius_px": int(point_radius),
        "effective_piece_radius_px": int(piece_radius),
        "effective_edge_width_px": int(edge_width),
    }
    return _RenderedScene(
        image=image.convert("RGB"),
        entities=tuple(entities),
        render_map=render_map,
        style_meta={
            "panel_scene_style": dict(panel_style_meta),
            "irregular_link_board_style": dict(theme_meta),
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
        f"object_description_{str(sample.scene_variant)}",
        answer_hint_key,
        annotation_hint_key,
    ]
    if str(query_id) == CAPTURE_MOVE_QUERY_ID:
        required_keys.append("capture_rule_text")
    else:
        required_keys.append("movement_rule_text")
    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        tuple(required_keys),
        context=f"prompt defaults for {task_id}",
    )
    json_example, json_example_answer_only = _json_examples()
    capture_rule_text = str(prompt_defaults.get("capture_rule_text", ""))
    prompt_selection = render_task_prompt_variants(
        domain="games",
        task_group=TASK_GROUP,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults[f"object_description_{str(sample.scene_variant)}"]),
            "movement_rule_text": str(prompt_defaults.get("movement_rule_text", "")),
            "capture_rule_text": str(capture_rule_text),
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


def _build_complexity(sample: _Sample) -> Any:
    weights = resolve_games_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
    board_point_count = int(sample.board_size) * int(sample.board_size)
    link_ratio = float(len(sample.edges)) / max(1.0, float(len(_all_possible_edges(int(sample.board_size)))))
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": normalize_linear(float(board_point_count), min_value=16.0, max_value=36.0),
            "movement_reasoning": 0.42 + (0.22 * float(link_ratio)),
            "ambiguity": normalize_linear(float(sample.answer), min_value=0.0, max_value=8.0),
            "output_burden": normalize_linear(float(len(sample.annotation_coords)), min_value=0.0, max_value=8.0),
        },
    )


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
    annotation_entity_ids = tuple(_point_id(coord) for coord in sampled.annotation_coords)
    annotation_points = [list(rendered.render_map["point_centers_px"][entity_id]) for entity_id in annotation_entity_ids]
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
    annotation_trace_key = "capture_destinations" if str(query_id) == CAPTURE_MOVE_QUERY_ID else "legal_destinations"
    trace_payload = {
        "scene_ir": {
            "scene_kind": "games_irregular_link_board",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "scene_id": SCENE_ID,
                "scene_variant": str(sampled.scene_variant),
                "query_id": str(query_id),
                "style_variant": str(sampled.style_variant),
                "board_size": int(sampled.board_size),
                "target_answer": int(sampled.answer),
                "marked_piece_id": "piece_marked",
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
                "scene_variant": str(axes.scene_variant),
                "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                "style_variant": str(axes.style_variant),
                "style_variant_probabilities": dict(axes.style_variant_probabilities),
                "board_size": int(axes.board_size),
                "board_size_probabilities": dict(axes.board_size_probabilities),
                "target_answer": int(sampled.answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "target_answer_probabilities": dict(axes.target_answer_probabilities),
            },
        },
        "render_spec": {
            "scene_variant": str(sampled.scene_variant),
            "style_variant": str(sampled.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(rendered.style_meta.get("panel_scene_style", {})),
            "irregular_link_board_style": dict(rendered.style_meta.get("irregular_link_board_style", {})),
            "effective_board_step_px": float(rendered.render_map["effective_board_step_px"]),
            "effective_piece_radius_px": int(rendered.render_map["effective_piece_radius_px"]),
        },
        "render_map": dict(rendered.render_map),
        "execution_trace": {
            "scene_variant": str(sampled.scene_variant),
            "query_id": str(query_id),
            "style_variant": str(sampled.style_variant),
            "board_size": int(sampled.board_size),
            "construction_mode": str(sampled.construction_mode),
            "target_answer": int(sampled.answer),
            "target_answer_support": [int(value) for value in axes.target_answer_support],
            "marked_coord": [int(sampled.marked_coord[0]), int(sampled.marked_coord[1])],
            "occupied_coords": [[int(coord[0]), int(coord[1])] for coord in sampled.occupied_coords],
            "edge_coords": [
                [[int(edge[0][0]), int(edge[0][1])], [int(edge[1][0]), int(edge[1][1])]]
                for edge in sampled.edges
            ],
            "annotation_coords": [[int(coord[0]), int(coord[1])] for coord in sampled.annotation_coords],
            "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
            annotation_trace_key: [[int(coord[0]), int(coord[1])] for coord in sampled.annotation_coords],
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
        complexity=_build_complexity(sampled),
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(query_id),
    )


@register_task
class GamesIrregularLinkBoardMarkedPieceDestinationCountTask:
    """Count empty linked destinations for one marked piece on a variable-link board."""

    task_id = MARKED_DESTINATION_TASK_ID
    domain = "games"
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        params = dict(params or {})
        axes = _resolve_axes(int(instance_seed), params=params)
        sampled: _Sample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled = _sample_scene(rng=rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled is None:
            raise RuntimeError(f"{self.task_id} failed to generate after {max_attempts} attempts")

        return _build_task_output(
            task_id=str(self.task_id),
            query_id=MARKED_DESTINATION_QUERY_ID,
            sampled=sampled,
            axes=axes,
            instance_seed=int(instance_seed),
            params=params,
        )


@register_task
class GamesIrregularLinkBoardCaptureMoveCountTask:
    """Count legal one-step moves that would capture an opposing piece."""

    task_id = CAPTURE_MOVE_TASK_ID
    domain = "games"
    task_group = TASK_GROUP
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any] | None = None, max_attempts: int = 100) -> TaskOutput:
        params = dict(params or {})
        axes = _resolve_axes(
            int(instance_seed),
            params=params,
            board_size_support_key="capture_board_size_support",
            fallback_board_size_support=_DEFAULTS.capture_board_size_support,
        )
        sampled: _Sample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.capture.attempt.{int(attempt_index)}")
            try:
                sampled = _sample_capture_scene(rng=rng, axes=axes)
            except ValueError:
                continue
            break
        if sampled is None:
            raise RuntimeError(f"{self.task_id} failed to generate after {max_attempts} attempts")

        return _build_task_output(
            task_id=str(self.task_id),
            query_id=CAPTURE_MOVE_QUERY_ID,
            sampled=sampled,
            axes=axes,
            instance_seed=int(instance_seed),
            params=params,
        )


__all__ = [
    "GamesIrregularLinkBoardMarkedPieceDestinationCountTask",
    "GamesIrregularLinkBoardCaptureMoveCountTask",
]
