"""Pretwa-inspired radial hunt board movement and capture tasks."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.core.visual.noise import apply_post_image_noise
from trace.tasks.shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults, required_group_defaults
from trace.tasks.shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_query_spec,
    build_prompt_trace_artifacts,
    render_scene_prompt_variants,
)
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support
from trace.tasks.games.shared.layout import (
    apply_games_layout_jitter_to_bbox,
    attach_games_unit_size_jitter,
    resolve_games_layout_jitter,
    resolve_games_unit_size_scale,
    scale_games_px,
)
from trace.tasks.games.shared.marking import draw_optional_marker_x, draw_semantic_ellipse_marker, resolve_semantic_marker_style
from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.games.shared.scene_style import draw_panel_scene_chrome, make_panel_scene_background, resolve_game_panel_scene_style
from trace.tasks.games.shared.visual_defaults import load_games_scene_noise_defaults


SCENE_ID = "radial_hunt_board"
SCENE_NAMESPACE = "games.radial_hunt_board"
MARKED_DESTINATION_QUERY_ID = "marked_piece_destination_count"
CAPTURE_MOVE_QUERY_ID = "capture_move_count"
STYLE_VARIANTS: Tuple[str, ...] = ("ink_rings", "carved_wood", "temple_cloth", "night_gold", "chalk_circle")
SCENE_VARIANTS: Tuple[str, ...] = ("open_position", "mixed_position", "crowded_position")
CENTER: Tuple[int, int] = (0, 0)
Coord = Tuple[int, int]
Edge = Tuple[Coord, Coord]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for radial hunt board scenes."""

    target_answer_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)
    min_total_piece_count: int = 5
    max_total_piece_count: int = 14
    canvas_width: int = 780
    canvas_height: int = 760
    panel_margin_px: int = 52
    max_board_size_px: int = 560
    edge_width_px: int = 5
    point_radius_px: int = 13
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
    target_answer: int
    target_answer_support: Tuple[int, ...]
    target_answer_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _Sample:
    """One symbolic radial hunt board sample and witness."""

    scene_variant: str
    style_variant: str
    marked_coord: Coord
    occupied_coords: Tuple[Coord, ...]
    annotation_coords: Tuple[Coord, ...]
    answer: int
    construction_mode: str


@dataclass(frozen=True)
class _Theme:
    """Scene-local palette for a radial hunt board."""

    board_fill_rgb: Tuple[int, int, int]
    board_border_rgb: Tuple[int, int, int]
    edge_rgb: Tuple[int, int, int]
    point_fill_rgb: Tuple[int, int, int]
    point_outline_rgb: Tuple[int, int, int]
    marked_piece_fill_rgb: Tuple[int, int, int]
    marked_piece_outline_rgb: Tuple[int, int, int]
    opponent_piece_fill_rgb: Tuple[int, int, int]
    opponent_piece_outline_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered board plus trace-friendly maps."""

    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


@dataclass(frozen=True)
class RadialHuntBoardOutputParts:
    """Prompt, image, annotation, and trace payload for one generated board."""

    prompt: str
    prompt_variants: Dict[str, str]
    answer_gt: TypedValue
    annotation_gt: TypedValue
    image: Image.Image
    trace_payload: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.5)


def _all_coords() -> Tuple[Coord, ...]:
    return (CENTER,) + tuple((ring, spoke) for ring in range(1, 4) for spoke in range(6))


def _circle_lines() -> Tuple[Tuple[Coord, ...], ...]:
    return tuple(tuple((ring, spoke) for spoke in range(6)) for ring in range(1, 4))


def _diameter_lines() -> Tuple[Tuple[Coord, ...], ...]:
    return tuple(
        (
            (3, (axis + 3) % 6),
            (2, (axis + 3) % 6),
            (1, (axis + 3) % 6),
            CENTER,
            (1, axis),
            (2, axis),
            (3, axis),
        )
        for axis in range(3)
    )


def _all_lines() -> Tuple[Tuple[Coord, ...], ...]:
    return _circle_lines() + _diameter_lines()


def _point_id(coord: Coord) -> str:
    if tuple(coord) == CENTER:
        return "point_center"
    return f"point_ring{int(coord[0])}_spoke{int(coord[1])}"


def _piece_id(coord: Coord) -> str:
    if tuple(coord) == CENTER:
        return "piece_center"
    return f"piece_ring{int(coord[0])}_spoke{int(coord[1])}"


def _edge(a: Coord, b: Coord) -> Edge:
    ordered = tuple(sorted((tuple(a), tuple(b))))  # type: ignore[arg-type]
    return ordered  # type: ignore[return-value]


def _all_possible_edges() -> Tuple[Edge, ...]:
    seen: set[Edge] = set()
    for line in _circle_lines():
        for index, coord in enumerate(line):
            seen.add(_edge(coord, line[(index + 1) % len(line)]))
    for line in _diameter_lines():
        for index in range(len(line) - 1):
            seen.add(_edge(line[index], line[index + 1]))
    return tuple(sorted(seen))


def _neighbors(coord: Coord) -> Tuple[Coord, ...]:
    coord = tuple(coord)
    out: set[Coord] = set()
    for edge in _all_possible_edges():
        if edge[0] == coord:
            out.add(edge[1])
        elif edge[1] == coord:
            out.add(edge[0])
    return tuple(sorted(out))


def _legal_destinations(*, marked_coord: Coord, occupied_coords: Sequence[Coord]) -> Tuple[Coord, ...]:
    occupied = {tuple(coord) for coord in occupied_coords}
    return tuple(sorted(coord for coord in _neighbors(marked_coord) if coord not in occupied))


def _capture_paths(marked_coord: Coord) -> Tuple[Tuple[Coord, Coord], ...]:
    marked_coord = tuple(marked_coord)
    out: set[Tuple[Coord, Coord]] = set()
    for line in _circle_lines():
        if marked_coord not in line:
            continue
        index = line.index(marked_coord)
        for direction in (-1, 1):
            captured = line[(index + direction) % len(line)]
            destination = line[(index + (2 * direction)) % len(line)]
            out.add((destination, captured))
    for line in _diameter_lines():
        if marked_coord not in line:
            continue
        index = line.index(marked_coord)
        for direction in (-1, 1):
            captured_index = index + direction
            destination_index = index + (2 * direction)
            if 0 <= captured_index < len(line) and 0 <= destination_index < len(line):
                out.add((line[destination_index], line[captured_index]))
    return tuple(sorted(out))


def _capture_destinations(*, marked_coord: Coord, occupied_coords: Sequence[Coord]) -> Tuple[Coord, ...]:
    occupied = {tuple(coord) for coord in occupied_coords}
    out: list[Coord] = []
    for destination, captured in _capture_paths(marked_coord):
        if tuple(captured) in occupied and tuple(destination) not in occupied:
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
        task_id=SCENE_NAMESPACE,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=tuple(str(value) for value in supported),
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
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
    target_answer, target_probs = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="target_answer_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.target_answer_support,
        namespace=f"{SCENE_NAMESPACE}.target_answer",
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
        target_answer=int(target_answer),
        target_answer_support=tuple(int(value) for value in target_support),
        target_answer_probabilities=dict(target_probs),
        scene_variant_probabilities=dict(scene_probs),
        style_variant_probabilities=dict(style_probs),
    )


def _piece_count_bounds(scene_variant: str) -> Tuple[int, int]:
    if str(scene_variant) == "open_position":
        return (5, 8)
    if str(scene_variant) == "crowded_position":
        return (11, 16)
    return (8, 12)


def _sample_destination_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    target = int(axes.target_answer)
    if target < 0 or target > 6:
        raise ValueError("radial hunt destination target answer must be in 0..6")
    viable = [coord for coord in _all_coords() if len(_neighbors(coord)) >= target]
    rng.shuffle(viable)
    marked_coord = viable[0]
    neighbors = list(_neighbors(marked_coord))
    rng.shuffle(neighbors)
    destinations = set(neighbors[:target])
    occupied: set[Coord] = {marked_coord}
    for coord in neighbors:
        if coord not in destinations:
            occupied.add(coord)

    min_pieces, max_pieces = _piece_count_bounds(str(axes.scene_variant))
    min_pieces = int(group_default(_GEN_DEFAULTS, "min_total_piece_count", min_pieces))
    max_pieces = int(group_default(_GEN_DEFAULTS, "max_total_piece_count", max_pieces))
    desired_piece_count = max(len(occupied), int(rng.randint(min_pieces, max_pieces)))
    candidates = [coord for coord in _all_coords() if coord not in occupied and coord not in destinations]
    rng.shuffle(candidates)
    for coord in candidates:
        if len(occupied) >= desired_piece_count:
            break
        occupied.add(coord)

    annotation = _legal_destinations(marked_coord=marked_coord, occupied_coords=tuple(sorted(occupied)))
    if len(annotation) != target:
        raise ValueError("constructed radial destination count mismatch")
    return _Sample(
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        marked_coord=marked_coord,
        occupied_coords=tuple(sorted(occupied)),
        annotation_coords=tuple(annotation),
        answer=int(len(annotation)),
        construction_mode="target_conditioned_radial_destination_board",
    )


def _sample_capture_scene(*, rng: Any, axes: _ResolvedAxes) -> _Sample:
    target = int(axes.target_answer)
    if target < 0 or target > 6:
        raise ValueError("radial hunt capture target answer must be in 0..6")
    viable = [coord for coord in _all_coords() if len(_capture_paths(coord)) >= target]
    rng.shuffle(viable)
    marked_coord = viable[0]
    capture_paths = list(_capture_paths(marked_coord))
    rng.shuffle(capture_paths)
    selected_paths = tuple(capture_paths[:target])
    selected_destinations = {path[0] for path in selected_paths}
    selected_captured = {path[1] for path in selected_paths}
    if selected_destinations & selected_captured:
        raise ValueError("selected radial capture paths have conflicting occupied and empty points")

    occupied: set[Coord] = {marked_coord, *selected_captured}
    protected_empty: set[Coord] = set(selected_destinations)
    for destination, captured in capture_paths:
        if destination in selected_destinations and (destination, captured) not in selected_paths:
            if captured in selected_captured:
                raise ValueError("selected radial capture paths create an accidental extra capture")
            protected_empty.add(captured)
    for destination, captured in capture_paths:
        if destination in selected_destinations:
            continue
        if captured in selected_captured:
            occupied.add(destination)
        elif rng.random() < 0.62:
            occupied.add(destination)
        else:
            protected_empty.add(captured)

    min_pieces, max_pieces = _piece_count_bounds(str(axes.scene_variant))
    min_pieces = int(group_default(_GEN_DEFAULTS, "min_total_piece_count", min_pieces))
    max_pieces = int(group_default(_GEN_DEFAULTS, "max_total_piece_count", max_pieces))
    desired_piece_count = max(len(occupied), int(rng.randint(min_pieces, max_pieces)))
    candidates = [coord for coord in _all_coords() if coord not in occupied and coord not in protected_empty]
    rng.shuffle(candidates)
    for coord in candidates:
        if len(occupied) >= desired_piece_count:
            break
        occupied.add(coord)

    annotation = _capture_destinations(marked_coord=marked_coord, occupied_coords=tuple(sorted(occupied)))
    if len(annotation) != target:
        raise ValueError("constructed radial capture count mismatch")
    return _Sample(
        scene_variant=str(axes.scene_variant),
        style_variant=str(axes.style_variant),
        marked_coord=marked_coord,
        occupied_coords=tuple(sorted(occupied)),
        annotation_coords=tuple(annotation),
        answer=int(len(annotation)),
        construction_mode="target_conditioned_radial_capture_board",
    )


def _theme_for_style(style_variant: str) -> Tuple[_Theme, Dict[str, Any]]:
    themes: dict[str, _Theme] = {
        "ink_rings": _Theme(
            board_fill_rgb=(236, 235, 221),
            board_border_rgb=(52, 55, 59),
            edge_rgb=(45, 48, 52),
            point_fill_rgb=(252, 249, 237),
            point_outline_rgb=(43, 45, 49),
            marked_piece_fill_rgb=(28, 40, 61),
            marked_piece_outline_rgb=(250, 250, 245),
            opponent_piece_fill_rgb=(184, 72, 58),
            opponent_piece_outline_rgb=(80, 32, 28),
        ),
        "carved_wood": _Theme(
            board_fill_rgb=(226, 188, 126),
            board_border_rgb=(94, 63, 36),
            edge_rgb=(110, 74, 42),
            point_fill_rgb=(250, 228, 177),
            point_outline_rgb=(83, 55, 33),
            marked_piece_fill_rgb=(38, 52, 80),
            marked_piece_outline_rgb=(247, 240, 220),
            opponent_piece_fill_rgb=(166, 75, 47),
            opponent_piece_outline_rgb=(76, 35, 24),
        ),
        "temple_cloth": _Theme(
            board_fill_rgb=(211, 228, 202),
            board_border_rgb=(63, 95, 67),
            edge_rgb=(67, 103, 71),
            point_fill_rgb=(242, 249, 229),
            point_outline_rgb=(54, 82, 55),
            marked_piece_fill_rgb=(40, 62, 47),
            marked_piece_outline_rgb=(247, 255, 239),
            opponent_piece_fill_rgb=(191, 67, 89),
            opponent_piece_outline_rgb=(83, 30, 42),
        ),
        "night_gold": _Theme(
            board_fill_rgb=(35, 43, 58),
            board_border_rgb=(210, 185, 116),
            edge_rgb=(236, 198, 101),
            point_fill_rgb=(58, 71, 95),
            point_outline_rgb=(242, 221, 156),
            marked_piece_fill_rgb=(241, 246, 255),
            marked_piece_outline_rgb=(12, 20, 36),
            opponent_piece_fill_rgb=(255, 177, 84),
            opponent_piece_outline_rgb=(86, 48, 18),
        ),
        "chalk_circle": _Theme(
            board_fill_rgb=(70, 91, 82),
            board_border_rgb=(220, 230, 216),
            edge_rgb=(224, 232, 221),
            point_fill_rgb=(90, 113, 103),
            point_outline_rgb=(238, 243, 232),
            marked_piece_fill_rgb=(247, 249, 236),
            marked_piece_outline_rgb=(28, 45, 39),
            opponent_piece_fill_rgb=(236, 104, 89),
            opponent_piece_outline_rgb=(92, 40, 35),
        ),
    }
    resolved = str(style_variant) if str(style_variant) in themes else "ink_rings"
    return themes[resolved], {
        "style_variant": str(resolved),
        "available_styles": list(STYLE_VARIANTS),
        "board_style_policy": "scene_local_radial_hunt_board_palette",
    }


def _bbox(center: Sequence[float], radius: float) -> Tuple[float, float, float, float]:
    cx, cy = float(center[0]), float(center[1])
    return (
        round(cx - float(radius), 3),
        round(cy - float(radius), 3),
        round(cx + float(radius), 3),
        round(cy + float(radius), 3),
    )


def _coord_angle(spoke: int) -> float:
    return math.radians(-90.0 + (60.0 * float(spoke)))


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
        namespace=f"{SCENE_NAMESPACE}.unit_size",
    )
    layout_jitter = attach_games_unit_size_jitter(
        resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace=f"{SCENE_NAMESPACE}.layout",
        ),
        unit_scale_meta,
    )
    max_board_size_px = scale_games_px(
        group_default(_RENDER_DEFAULTS, "max_board_size_px", _DEFAULTS.max_board_size_px),
        unit_scale,
        min_px=300,
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
        namespace=f"{SCENE_NAMESPACE}.panel_scene_style",
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
    max_span = min(float(max_board_size_px), float(canvas_width - (2 * margin)), float(canvas_height - (2 * margin)))
    outer_radius = float(max_span) * 0.5
    board_bbox = (
        round(0.5 * (float(canvas_width) - (2.0 * outer_radius)), 3),
        round(0.5 * (float(canvas_height) - (2.0 * outer_radius)), 3),
        round(0.5 * (float(canvas_width) + (2.0 * outer_radius)), 3),
        round(0.5 * (float(canvas_height) + (2.0 * outer_radius)), 3),
    )
    board_bbox, _dx, _dy, resolved_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=board_bbox,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        jitter=layout_jitter,
    )
    center_xy = (
        round(0.5 * (float(board_bbox[0]) + float(board_bbox[2])), 3),
        round(0.5 * (float(board_bbox[1]) + float(board_bbox[3])), 3),
    )
    outer_radius = 0.5 * min(float(board_bbox[2]) - float(board_bbox[0]), float(board_bbox[3]) - float(board_bbox[1]))
    ring_radii = {1: outer_radius / 3.0, 2: (2.0 * outer_radius) / 3.0, 3: outer_radius}
    centers: Dict[Coord, Tuple[float, float]] = {CENTER: center_xy}
    for ring in range(1, 4):
        for spoke in range(6):
            angle = _coord_angle(spoke)
            radius = ring_radii[ring]
            centers[(ring, spoke)] = (
                round(float(center_xy[0]) + (float(radius) * math.cos(angle)), 3),
                round(float(center_xy[1]) + (float(radius) * math.sin(angle)), 3),
            )

    edge_width = scale_games_px(group_default(_RENDER_DEFAULTS, "edge_width_px", _DEFAULTS.edge_width_px), unit_scale, min_px=2)
    point_radius = scale_games_px(group_default(_RENDER_DEFAULTS, "point_radius_px", _DEFAULTS.point_radius_px), unit_scale, min_px=8)
    piece_radius = scale_games_px(group_default(_RENDER_DEFAULTS, "piece_radius_px", _DEFAULTS.piece_radius_px), unit_scale, min_px=14)
    marker_width = scale_games_px(group_default(_RENDER_DEFAULTS, "marker_width_px", _DEFAULTS.marker_width_px), unit_scale, min_px=3)
    board_pad = max(24, int(round(float(piece_radius) * 1.6)))
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
        radius=28,
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
        radius=max(20, int(round(float(board_pad) * 0.6))),
        fill=tuple(theme.board_fill_rgb) + (226,),
        outline=tuple(theme.board_border_rgb) + (255,),
        width=max(2, int(round(float(edge_width) * 0.7))),
    )

    for ring in range(1, 4):
        radius = ring_radii[ring]
        circle_bbox = (
            float(center_xy[0]) - radius,
            float(center_xy[1]) - radius,
            float(center_xy[0]) + radius,
            float(center_xy[1]) + radius,
        )
        draw.ellipse(circle_bbox, outline=tuple(theme.edge_rgb) + (255,), width=max(2, int(edge_width)))
    for axis in range(3):
        p0 = centers[(3, axis)]
        p1 = centers[(3, (axis + 3) % 6)]
        draw.line([p0, p1], fill=tuple(theme.edge_rgb) + (255,), width=max(2, int(edge_width)))

    entity_bboxes: Dict[str, List[float]] = {}
    entity_points: Dict[str, List[float]] = {}
    point_centers: Dict[str, List[float]] = {}
    point_bboxes: Dict[str, List[float]] = {}
    piece_centers: Dict[str, List[float]] = {}
    piece_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    occupied = set(sample.occupied_coords)
    for coord in _all_coords():
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
        fill = theme.marked_piece_fill_rgb if is_marked else theme.opponent_piece_fill_rgb
        outline = theme.marked_piece_outline_rgb if is_marked else theme.opponent_piece_outline_rgb
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
            namespace=f"{SCENE_NAMESPACE}.marked_piece",
            role="marked_piece",
            surface_rgbs=(theme.board_fill_rgb,),
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
        for edge in _all_possible_edges()
    ]
    for coord in _all_coords():
        point_id = _point_id(coord)
        is_marked = coord == sample.marked_coord
        piece_id = "piece_marked" if is_marked else _piece_id(coord) if coord in occupied else ""
        entities.append(
            {
                "entity_id": str(point_id),
                "entity_type": "radial_hunt_point",
                "ring": int(coord[0]),
                "spoke": int(coord[1]),
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
        "effective_outer_radius_px": round(float(outer_radius), 3),
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
            "radial_hunt_board_style": dict(theme_meta),
        },
        background_meta=dict(background_meta),
    )


def _json_examples() -> Tuple[str, str]:
    annotation = [[180.0, 220.0], [268.0, 220.0]]
    return (
        json.dumps({"annotation": annotation, "answer": 2}, separators=(",", ":"), ensure_ascii=True),
        json.dumps({"answer": 2}, separators=(",", ":"), ensure_ascii=True),
    )


def _build_prompt(*, sample: _Sample, query_id: str, instance_seed: int) -> Tuple[str, Dict[str, str], Any]:
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
        context=f"prompt defaults for {SCENE_ID}",
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
            "object_description": str(prompt_defaults[f"object_description_{str(sample.scene_variant)}"]),
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
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), prompt_artifacts


def build_radial_hunt_board_output_parts(
    *,
    query_id: str,
    sampled: _Sample,
    axes: _ResolvedAxes,
    instance_seed: int,
    params: Mapping[str, Any],
) -> RadialHuntBoardOutputParts:
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
        instance_seed=int(instance_seed),
    )
    answer_gt = TypedValue(type="integer", value=int(sampled.answer))
    annotation_gt = TypedValue(type="point_set", value=[list(point) for point in annotation_points])
    annotation_trace_key = "capture_destinations" if str(query_id) == CAPTURE_MOVE_QUERY_ID else "legal_destinations"
    trace_payload = {
        "scene_ir": {
            "scene_kind": "games_radial_hunt_board",
            "entities": [dict(entity) for entity in rendered.entities],
            "relations": {
                "scene_id": SCENE_ID,
                "scene_variant": str(sampled.scene_variant),
                "query_id": str(query_id),
                "style_variant": str(sampled.style_variant),
                "target_answer": int(sampled.answer),
                "marked_piece_id": "piece_marked",
                "annotation_entity_ids": [str(entity_id) for entity_id in annotation_entity_ids],
            },
        },
        "query_spec": build_prompt_query_spec(
            prompt_artifacts=prompt_meta,
            query_id=str(query_id),
            params={
                "scene_variant": str(axes.scene_variant),
                "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                "style_variant": str(axes.style_variant),
                "style_variant_probabilities": dict(axes.style_variant_probabilities),
                "target_answer": int(sampled.answer),
                "target_answer_support": [int(value) for value in axes.target_answer_support],
                "target_answer_probabilities": dict(axes.target_answer_probabilities),
            },
        ),
        "render_spec": {
            "scene_variant": str(sampled.scene_variant),
            "style_variant": str(sampled.style_variant),
            "canvas_width": int(image.size[0]),
            "canvas_height": int(image.size[1]),
            "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
            "panel_scene_style": dict(rendered.style_meta.get("panel_scene_style", {})),
            "radial_hunt_board_style": dict(rendered.style_meta.get("radial_hunt_board_style", {})),
            "effective_outer_radius_px": float(rendered.render_map["effective_outer_radius_px"]),
            "effective_piece_radius_px": int(rendered.render_map["effective_piece_radius_px"]),
        },
        "render_map": dict(rendered.render_map),
        "execution_trace": {
            "scene_variant": str(sampled.scene_variant),
            "query_id": str(query_id),
            "style_variant": str(sampled.style_variant),
            "construction_mode": str(sampled.construction_mode),
            "target_answer": int(sampled.answer),
            "target_answer_support": [int(value) for value in axes.target_answer_support],
            "marked_coord": [int(sampled.marked_coord[0]), int(sampled.marked_coord[1])],
            "occupied_coords": [[int(coord[0]), int(coord[1])] for coord in sampled.occupied_coords],
            "edge_coords": [
                [[int(edge[0][0]), int(edge[0][1])], [int(edge[1][0]), int(edge[1][1])]]
                for edge in _all_possible_edges()
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
    return RadialHuntBoardOutputParts(
        prompt=str(prompt),
        prompt_variants=dict(prompt_variants),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        trace_payload=trace_payload,
    )


resolve_radial_hunt_board_axes = _resolve_axes
sample_radial_hunt_board_destination_scene = _sample_destination_scene
sample_radial_hunt_board_capture_scene = _sample_capture_scene


__all__ = [
    "CAPTURE_MOVE_QUERY_ID",
    "MARKED_DESTINATION_QUERY_ID",
    "RadialHuntBoardOutputParts",
    "SCENE_ID",
    "build_radial_hunt_board_output_parts",
    "resolve_radial_hunt_board_axes",
    "sample_radial_hunt_board_capture_scene",
    "sample_radial_hunt_board_destination_scene",
]
