"""Shared generation and rendering helpers for tangram-style puzzle scenes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.config_defaults import resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.mcq import option_label_for_index
from ...shared.text_rendering import load_font
from .drawing import draw_rounded_rect
from .option_layout import centered_option_grid_shape, centered_option_row_counts
from .option_panels import render_puzzle_option_panel


SUPPORTED_TANGRAM_QUERY_IDS: Tuple[str, ...] = (
    "missing_piece_label",
    "contact_count",
)
SUPPORTED_TANGRAM_SCENE_VARIANTS: Tuple[str, ...] = (
    "tangram_square",
    "tangram_diamond",
    "tangram_tilted",
)


@dataclass(frozen=True)
class TangramRenderParams:
    """Resolved visual parameters for one tangram-style scene."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    assembly_panel_width_px: int
    assembly_panel_height_px: int
    assembly_panel_padding_px: int
    assembly_to_options_gap_px: int
    option_panel_width_px: int
    option_panel_height_px: int
    option_gap_px: int
    option_row_gap_px: int
    option_shape_box_size_px: int
    option_label_gap_px: int
    panel_corner_radius_px: int
    content_corner_radius_px: int
    border_width_px: int
    seam_width_px: int
    highlight_width_px: int
    option_label_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    assembly_panel_fill_rgb: Tuple[int, int, int]
    option_panel_fill_rgb: Tuple[int, int, int]
    option_shape_fill_rgb: Tuple[int, int, int]
    missing_fill_rgb: Tuple[int, int, int]
    marked_outline_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    seam_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class RenderedTangramScene:
    """Rendered tangram scene with traceable geometry maps."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    assembly_panel_bbox_px: List[float]
    assembly_bbox_px: List[float]
    piece_bbox_map: Dict[str, List[float]]
    option_panel_bbox_map: Dict[str, List[float]]


_BASE_PIECES: Tuple[Dict[str, Any], ...] = (
    {
        "piece_id": "piece_1",
        "shape_id": "right_triangle",
        "shape_name": "triangle",
        "points": ((0.0, 0.0), (2.0, 0.0), (0.0, 2.0)),
    },
    {
        "piece_id": "piece_2",
        "shape_id": "right_triangle",
        "shape_name": "triangle",
        "points": ((2.0, 0.0), (4.0, 0.0), (4.0, 2.0)),
    },
    {
        "piece_id": "piece_3",
        "shape_id": "right_triangle",
        "shape_name": "triangle",
        "points": ((0.0, 2.0), (0.0, 4.0), (2.0, 4.0)),
    },
    {
        "piece_id": "piece_4",
        "shape_id": "right_triangle",
        "shape_name": "triangle",
        "points": ((4.0, 2.0), (4.0, 4.0), (2.0, 4.0)),
    },
    {
        "piece_id": "piece_5",
        "shape_id": "diamond",
        "shape_name": "diamond",
        "points": ((1.0, 1.0), (2.0, 0.0), (3.0, 1.0), (2.0, 2.0)),
    },
    {
        "piece_id": "piece_6",
        "shape_id": "left_notched_piece",
        "shape_name": "notched polygon",
        "points": ((0.0, 2.0), (1.0, 1.0), (2.0, 2.0), (1.0, 3.0), (0.0, 4.0)),
    },
    {
        "piece_id": "piece_7",
        "shape_id": "right_notched_piece",
        "shape_name": "mirrored notched polygon",
        "points": ((4.0, 2.0), (3.0, 1.0), (2.0, 2.0), (3.0, 3.0), (4.0, 4.0)),
    },
)

_CONTACTS: Dict[str, Tuple[str, ...]] = {
    "piece_1": ("piece_5", "piece_6"),
    "piece_2": ("piece_5", "piece_7"),
    "piece_3": ("piece_6",),
    "piece_4": ("piece_7",),
    "piece_5": ("piece_1", "piece_2", "piece_6", "piece_7"),
    "piece_6": ("piece_1", "piece_3", "piece_5"),
    "piece_7": ("piece_2", "piece_4", "piece_5"),
}

_OPTION_SHAPES: Dict[str, Tuple[Tuple[float, float], ...]] = {
    "right_triangle": ((0.0, 0.0), (2.0, 0.0), (0.0, 2.0)),
    "diamond": ((1.0, 0.0), (2.0, 1.0), (1.0, 2.0), (0.0, 1.0)),
    "left_notched_piece": ((0.0, 1.0), (1.0, 0.0), (2.0, 1.0), (1.0, 2.0), (0.0, 3.0)),
    "right_notched_piece": ((2.0, 1.0), (1.0, 0.0), (0.0, 1.0), (1.0, 2.0), (2.0, 3.0)),
    "trapezoid": ((0.2, 0.0), (1.8, 0.0), (2.2, 1.3), (0.0, 1.3)),
    "kite": ((1.0, 0.0), (2.1, 0.85), (1.0, 2.2), (0.0, 0.85)),
    "skinny_triangle": ((0.0, 0.0), (2.0, 0.0), (1.0, 1.45)),
    "parallelogram": ((0.45, 0.0), (2.0, 0.0), (1.55, 1.2), (0.0, 1.2)),
    "wide_pentagon": ((0.3, 0.0), (1.7, 0.0), (2.1, 0.85), (1.0, 1.6), (-0.1, 0.85)),
}

_MIRROR_DISTRACTOR_EXCLUSIONS: Dict[str, str] = {
    "left_notched_piece": "right_notched_piece",
    "right_notched_piece": "left_notched_piece",
}

_PIECE_FILLS: Tuple[Tuple[int, int, int], ...] = (
    (74, 122, 178),
    (219, 142, 82),
    (86, 155, 118),
    (190, 91, 105),
    (139, 104, 184),
    (214, 181, 78),
    (73, 154, 176),
)


def _int_value(mapping: Mapping[str, Any], key: str, default: int) -> int:
    return int(mapping.get(str(key), int(default)))


def resolve_tangram_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
) -> TangramRenderParams:
    """Resolve drawing parameters for one tangram scene."""

    merged = dict(render_defaults)
    merged.update(dict(params))
    return TangramRenderParams(
        canvas_width=_int_value(merged, "canvas_width", 1160),
        canvas_height=_int_value(merged, "canvas_height", 1040),
        scene_margin_left_px=_int_value(merged, "scene_margin_left_px", 58),
        scene_margin_right_px=_int_value(merged, "scene_margin_right_px", 58),
        scene_margin_top_px=_int_value(merged, "scene_margin_top_px", 52),
        scene_margin_bottom_px=_int_value(merged, "scene_margin_bottom_px", 52),
        assembly_panel_width_px=_int_value(merged, "assembly_panel_width_px", 620),
        assembly_panel_height_px=_int_value(merged, "assembly_panel_height_px", 520),
        assembly_panel_padding_px=_int_value(merged, "assembly_panel_padding_px", 52),
        assembly_to_options_gap_px=_int_value(merged, "assembly_to_options_gap_px", 34),
        option_panel_width_px=_int_value(merged, "option_panel_width_px", 150),
        option_panel_height_px=_int_value(merged, "option_panel_height_px", 178),
        option_gap_px=_int_value(merged, "option_gap_px", 20),
        option_row_gap_px=_int_value(merged, "option_row_gap_px", 18),
        option_shape_box_size_px=_int_value(merged, "option_shape_box_size_px", 108),
        option_label_gap_px=_int_value(merged, "option_label_gap_px", 10),
        panel_corner_radius_px=_int_value(merged, "panel_corner_radius_px", 26),
        content_corner_radius_px=_int_value(merged, "content_corner_radius_px", 16),
        border_width_px=_int_value(merged, "border_width_px", 3),
        seam_width_px=_int_value(merged, "seam_width_px", 3),
        highlight_width_px=_int_value(merged, "highlight_width_px", 8),
        option_label_font_size_px=_int_value(merged, "option_label_font_size_px", 29),
        panel_fill_rgb=_rgb(merged.get("panel_fill_rgb"), (248, 249, 252)),
        assembly_panel_fill_rgb=_rgb(merged.get("assembly_panel_fill_rgb"), (252, 252, 255)),
        option_panel_fill_rgb=_rgb(merged.get("option_panel_fill_rgb"), (251, 251, 255)),
        option_shape_fill_rgb=_rgb(merged.get("option_shape_fill_rgb"), (238, 243, 249)),
        missing_fill_rgb=_rgb(merged.get("missing_fill_rgb"), (18, 20, 24)),
        marked_outline_rgb=_rgb(merged.get("marked_outline_rgb"), (18, 20, 24)),
        border_color_rgb=_rgb(merged.get("border_color_rgb"), (86, 94, 108)),
        seam_color_rgb=_rgb(merged.get("seam_color_rgb"), (42, 49, 59)),
        text_color_rgb=_rgb(merged.get("text_color_rgb"), (30, 34, 40)),
        text_stroke_rgb=_rgb(merged.get("text_stroke_rgb"), (255, 255, 255)),
    )


def _bounds(points: Sequence[Tuple[float, float]]) -> Tuple[float, float, float, float]:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _round_bbox(points: Sequence[Tuple[float, float]]) -> List[float]:
    x0, y0, x1, y1 = _bounds(points)
    return [round(float(x0), 3), round(float(y0), 3), round(float(x1), 3), round(float(y1), 3)]


def _centroid(points: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    if not points:
        return 0.0, 0.0
    return (
        sum(float(point[0]) for point in points) / float(len(points)),
        sum(float(point[1]) for point in points) / float(len(points)),
    )


def _rotate_points(
    points: Sequence[Tuple[float, float]],
    *,
    degrees: float,
    center: Tuple[float, float],
) -> List[Tuple[float, float]]:
    theta = math.radians(float(degrees))
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    cx, cy = float(center[0]), float(center[1])
    out: List[Tuple[float, float]] = []
    for x, y in points:
        dx = float(x) - cx
        dy = float(y) - cy
        out.append((cx + dx * cos_t - dy * sin_t, cy + dx * sin_t + dy * cos_t))
    return out


def _scene_variant_rotation(scene_variant: str) -> float:
    angle_by_variant = {
        "tangram_square": 0.0,
        "tangram_diamond": 45.0,
        "tangram_tilted": -16.0,
    }
    return float(angle_by_variant.get(str(scene_variant), 0.0))


def _normalize_points_to_box(
    points: Sequence[Tuple[float, float]],
    box: Sequence[float],
    *,
    padding_px: float,
    rotation_degrees: float = 0.0,
) -> List[Tuple[float, float]]:
    local = [(float(x), float(y)) for x, y in points]
    cx, cy = _centroid(local)
    if abs(float(rotation_degrees)) > 1e-6:
        local = _rotate_points(local, degrees=float(rotation_degrees), center=(cx, cy))
    min_x, min_y, max_x, max_y = _bounds(local)
    width = max(1e-6, max_x - min_x)
    height = max(1e-6, max_y - min_y)
    x0, y0, x1, y1 = [float(value) for value in box]
    target_width = max(1.0, float(x1 - x0 - 2.0 * float(padding_px)))
    target_height = max(1.0, float(y1 - y0 - 2.0 * float(padding_px)))
    scale = min(target_width / width, target_height / height)
    offset_x = float(x0 + 0.5 * (x1 - x0 - width * scale) - min_x * scale)
    offset_y = float(y0 + 0.5 * (y1 - y0 - height * scale) - min_y * scale)
    return [(float(offset_x + x * scale), float(offset_y + y * scale)) for x, y in local]


def _piece_layout_points(
    *,
    scene_variant: str,
    assembly_box: Sequence[float],
    padding_px: float,
) -> Dict[str, List[Tuple[float, float]]]:
    angle = _scene_variant_rotation(str(scene_variant))
    transformed: Dict[str, List[Tuple[float, float]]] = {}
    all_points: List[Tuple[float, float]] = []
    for piece in _BASE_PIECES:
        rotated = _rotate_points(
            [(float(x), float(y)) for x, y in piece["points"]],
            degrees=angle,
            center=(2.0, 2.0),
        )
        transformed[str(piece["piece_id"])] = rotated
        all_points.extend(rotated)
    min_x, min_y, max_x, max_y = _bounds(all_points)
    width = max(1e-6, max_x - min_x)
    height = max(1e-6, max_y - min_y)
    box_x0, box_y0, box_x1, box_y1 = [float(value) for value in assembly_box]
    target_width = max(1.0, float(box_x1 - box_x0 - 2.0 * float(padding_px)))
    target_height = max(1.0, float(box_y1 - box_y0 - 2.0 * float(padding_px)))
    scale = min(target_width / width, target_height / height)
    offset_x = float(box_x0 + 0.5 * (box_x1 - box_x0 - width * scale) - min_x * scale)
    offset_y = float(box_y0 + 0.5 * (box_y1 - box_y0 - height * scale) - min_y * scale)
    return {
        piece_id: [(float(offset_x + x * scale), float(offset_y + y * scale)) for x, y in points]
        for piece_id, points in transformed.items()
    }


def _draw_polygon(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Tuple[float, float]],
    *,
    fill: Sequence[int],
    outline: Sequence[int],
    width: int,
) -> None:
    int_points = [(int(round(x)), int(round(y))) for x, y in points]
    draw.polygon(int_points, fill=tuple(int(v) for v in fill), outline=tuple(int(v) for v in outline))
    if int(width) > 1:
        draw.line(int_points + [int_points[0]], fill=tuple(int(v) for v in outline), width=int(width), joint="curve")


def _draw_target_ring(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Tuple[float, float]],
    *,
    color: Sequence[int],
    width: int,
) -> None:
    int_points = [(int(round(x)), int(round(y))) for x, y in points]
    draw.line(int_points + [int_points[0]], fill=tuple(int(v) for v in color), width=int(width), joint="curve")
    cx, cy = _centroid(points)
    radius = max(7, int(width) + 4)
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=(255, 255, 255),
        outline=tuple(int(v) for v in color),
        width=max(2, int(width // 2)),
    )


def _sample_option_count(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> Tuple[int, List[int]]:
    lower, upper = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="option_count_min",
        max_key="option_count_max",
        fallback_min=4,
        fallback_max=6,
        context="tangram option_count bounds",
    )
    return int(lower), list(range(int(lower), int(upper) + 1))


def _target_piece_for_seed(
    *,
    query_id: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> Dict[str, Any]:
    explicit = params.get("target_piece_id")
    pieces = [dict(piece) for piece in _BASE_PIECES]
    if explicit is not None:
        for piece in pieces:
            if str(piece["piece_id"]) == str(explicit):
                return dict(piece)
        raise ValueError(f"unknown target_piece_id for tangram task: {explicit}")
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"tangram:{query_id}:target_piece",
    )
    return dict(pieces[int(index) % len(pieces)])


def _contact_mark_candidates() -> Dict[int, List[Tuple[Tuple[str, ...], Tuple[str, ...]]]]:
    """Return marked-piece sets grouped by realized edge-neighbor count."""

    piece_ids = tuple(str(piece["piece_id"]) for piece in _BASE_PIECES)
    grouped: Dict[int, List[Tuple[Tuple[str, ...], Tuple[str, ...]]]] = {}
    for marked_count in (1, 2):
        for start_index, first in enumerate(piece_ids):
            if marked_count == 1:
                combinations = ((first,),)
            else:
                combinations = tuple((first, second) for second in piece_ids[start_index + 1 :])
            for marked in combinations:
                marked_set = set(marked)
                touching: set[str] = set()
                for piece_id in marked:
                    touching.update(str(item) for item in _CONTACTS.get(str(piece_id), ()))
                touching = touching.difference(marked_set)
                grouped.setdefault(len(touching) + len(marked_set), []).append(
                    (tuple(str(item) for item in marked), tuple(sorted(touching)))
                )
    return grouped


def _contact_mark_set_for_seed(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Tuple[str, ...], Tuple[str, ...], List[int]]:
    """Select one marked-piece set with balanced contact-count support."""

    grouped = _contact_mark_candidates()
    lower, upper = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="contact_count_min",
        max_key="contact_count_max",
        fallback_min=2,
        fallback_max=7,
        context="tangram contact_count bounds",
    )
    support = [count for count in range(int(lower), int(upper) + 1) if count in grouped]
    if not support:
        raise ValueError("tangram contact_count support has no feasible marked-piece sets")
    explicit_count = params.get("target_contact_count")
    if explicit_count is not None:
        selected_count = int(explicit_count)
        if selected_count not in support:
            raise ValueError(f"target_contact_count={selected_count} is not feasible for tangram contact_count")
    else:
        selected_count = support[
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace="tangram:contact_count:answer",
            )
            % len(support)
        ]
    candidates = grouped[int(selected_count)]
    candidate_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"tangram:contact_count:marked_set:{selected_count}",
    )
    marked, touching = candidates[int(candidate_index) % len(candidates)]
    return tuple(marked), tuple(touching), [int(value) for value in support]


def build_tangram_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Build symbolic tangram puzzle data before rendering."""

    if str(query_id) not in SUPPORTED_TANGRAM_QUERY_IDS:
        raise ValueError(f"unsupported tangram query_id: {query_id}")
    rng = spawn_rng(int(instance_seed), f"{task_id}.{query_id}.dataset")
    option_min, option_support = _sample_option_count(params, gen_defaults)
    option_count = int(option_support[resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"tangram:{query_id}:option_count",
    ) % len(option_support)])
    answer_option_index: int | None = None
    if str(query_id) == "missing_piece_label":
        answer_option_index = int(resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"tangram:{query_id}:answer_option_index",
        ) % int(max(option_support)))
        feasible_option_counts = [count for count in option_support if int(count) > int(answer_option_index)]
        option_count = int(feasible_option_counts[resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"tangram:{query_id}:option_count_for_answer:{answer_option_index}",
        ) % len(feasible_option_counts)])
    if str(query_id) == "contact_count":
        marked_piece_ids, contact_piece_ids, contact_count_support = _contact_mark_set_for_seed(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
        )
        target_piece_id = str(marked_piece_ids[0])
        target_piece = next(piece for piece in _BASE_PIECES if str(piece["piece_id"]) == str(target_piece_id))
    else:
        target_piece = _target_piece_for_seed(query_id=str(query_id), params=params, instance_seed=int(instance_seed))
        marked_piece_ids = (str(target_piece["piece_id"]),)
        contact_piece_ids = tuple(str(item) for item in _CONTACTS.get(str(target_piece["piece_id"]), ()))
        contact_count_support = [1, 2, 3, 4]
    target_piece_id = str(target_piece["piece_id"])
    correct_shape_id = str(target_piece["shape_id"])
    target_shape_name = str(target_piece["shape_name"])

    piece_specs = [
        {
            "piece_id": str(piece["piece_id"]),
            "shape_id": str(piece["shape_id"]),
            "shape_name": str(piece["shape_name"]),
            "base_points": [[float(x), float(y)] for x, y in piece["points"]],
            "contact_piece_ids": [str(item) for item in _CONTACTS.get(str(piece["piece_id"]), ())],
        }
        for piece in _BASE_PIECES
    ]

    option_specs: List[Dict[str, Any]] = []
    correct_option_index: int | None = None
    if str(query_id) == "missing_piece_label":
        shape_catalog = _OPTION_SHAPES
        excluded_shape_ids = {correct_shape_id}
        mirror_shape_id = _MIRROR_DISTRACTOR_EXCLUSIONS.get(correct_shape_id)
        if mirror_shape_id is not None:
            excluded_shape_ids.add(str(mirror_shape_id))
        candidate_shape_ids = [shape_id for shape_id in shape_catalog if str(shape_id) not in excluded_shape_ids]
        rng.shuffle(candidate_shape_ids)
        correct_option_shape_id = str(correct_shape_id)
        selected_shape_ids = [correct_option_shape_id] + candidate_shape_ids[: max(0, int(option_count) - 1)]
        if answer_option_index is None:
            answer_index = int(resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"tangram:{query_id}:answer_option",
            ) % int(option_count))
        else:
            answer_index = int(answer_option_index)
        ordered_shape_ids = list(selected_shape_ids)
        ordered_shape_ids.remove(correct_option_shape_id)
        ordered_shape_ids.insert(answer_index, correct_option_shape_id)
        correct_option_index = int(answer_index)
        for option_index, shape_id in enumerate(ordered_shape_ids):
            rotation = int((rng.randrange(0, 4) * 90) % 360)
            option_specs.append(
                {
                    "option_id": f"option_{option_index}",
                    "option_label": option_label_for_index(option_index),
                    "shape_id": str(shape_id),
                    "is_correct": bool(option_index == answer_index),
                    "display_rotation_degrees": int(rotation),
                    "shape_points": [[float(x), float(y)] for x, y in shape_catalog[str(shape_id)]],
                }
            )

    return {
        "query_id": str(query_id),
        "scene_variant": "",
        "piece_specs": piece_specs,
        "target_piece_id": str(target_piece_id),
        "target_piece_ids": [str(item) for item in marked_piece_ids],
        "target_shape_id": str(correct_shape_id),
        "target_shape_name": str(target_shape_name),
        "contact_piece_ids": [str(item) for item in contact_piece_ids],
        "contact_count": int(len(marked_piece_ids) + len(contact_piece_ids)),
        "contact_count_support": [int(item) for item in contact_count_support],
        "option_count": int(option_count),
        "option_count_range": [int(option_min), int(max(option_support))],
        "option_specs": option_specs,
        "correct_option_index": correct_option_index,
        "answer_option_label": (
            str(option_label_for_index(int(correct_option_index))) if correct_option_index is not None else ""
        ),
        "correct_option_panel_id": (
            f"option_{int(correct_option_index)}" if correct_option_index is not None else ""
        ),
        "solver_trace": {
            "target_piece_id": str(target_piece_id),
            "target_piece_ids": [str(item) for item in marked_piece_ids],
            "target_shape_id": str(correct_shape_id),
            "matching_rule": "rotation_allowed_no_flipping",
            "touching_rule": "count_marked_pieces_plus_unmarked_pieces_sharing_full_or_partial_edge_with_any_marked_piece",
        },
    }


def _option_layout_bboxes(
    *,
    render_params: TangramRenderParams,
    option_count: int,
    top_y: float,
) -> List[Tuple[float, float, float, float]]:
    cols, _rows = centered_option_grid_shape(int(option_count))
    row_counts = centered_option_row_counts(int(option_count), int(cols))
    total_width = float(
        int(cols) * int(render_params.option_panel_width_px)
        + (int(cols) - 1) * int(render_params.option_gap_px)
    )
    start_x = 0.5 * (float(render_params.canvas_width) - total_width)
    bboxes: List[Tuple[float, float, float, float]] = []
    current_index = 0
    for row_index, row_count in enumerate(row_counts):
        row_width = float(
            int(row_count) * int(render_params.option_panel_width_px)
            + (int(row_count) - 1) * int(render_params.option_gap_px)
        )
        row_start_x = float(start_x + 0.5 * (total_width - row_width))
        y0 = float(top_y + row_index * (int(render_params.option_panel_height_px) + int(render_params.option_row_gap_px)))
        for col in range(int(row_count)):
            x0 = float(row_start_x + col * (int(render_params.option_panel_width_px) + int(render_params.option_gap_px)))
            bboxes.append(
                (
                    x0,
                    y0,
                    x0 + float(render_params.option_panel_width_px),
                    y0 + float(render_params.option_panel_height_px),
                )
            )
            current_index += 1
    return bboxes


def render_tangram_scene(
    base_image: Image.Image,
    *,
    dataset: Mapping[str, Any],
    scene_variant: str,
    render_params: TangramRenderParams,
) -> RenderedTangramScene:
    """Render one tangram scene and return traceable bboxes."""

    image = base_image.convert("RGB")
    draw = ImageDraw.Draw(image)
    query_id = str(dataset["query_id"])
    assembly_panel_bbox = (
        float(0.5 * (render_params.canvas_width - render_params.assembly_panel_width_px)),
        float(render_params.scene_margin_top_px),
        float(0.5 * (render_params.canvas_width + render_params.assembly_panel_width_px)),
        float(render_params.scene_margin_top_px + render_params.assembly_panel_height_px),
    )
    option_top_y = float(assembly_panel_bbox[3] + render_params.assembly_to_options_gap_px)
    scene_bbox = (
        float(render_params.scene_margin_left_px),
        float(render_params.scene_margin_top_px),
        float(render_params.canvas_width - render_params.scene_margin_right_px),
        float(render_params.canvas_height - render_params.scene_margin_bottom_px),
    )
    draw_rounded_rect(
        draw,
        scene_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=render_params.panel_fill_rgb,
        outline=render_params.border_color_rgb,
        width=int(render_params.border_width_px),
    )
    draw_rounded_rect(
        draw,
        assembly_panel_bbox,
        radius=int(render_params.panel_corner_radius_px),
        fill=render_params.assembly_panel_fill_rgb,
        outline=render_params.border_color_rgb,
        width=int(render_params.border_width_px),
    )

    assembly_box = (
        float(assembly_panel_bbox[0] + render_params.assembly_panel_padding_px),
        float(assembly_panel_bbox[1] + render_params.assembly_panel_padding_px),
        float(assembly_panel_bbox[2] - render_params.assembly_panel_padding_px),
        float(assembly_panel_bbox[3] - render_params.assembly_panel_padding_px),
    )
    piece_points = _piece_layout_points(
        scene_variant=str(scene_variant),
        assembly_box=assembly_box,
        padding_px=0.0,
    )
    target_piece_ids = [str(item) for item in dataset.get("target_piece_ids", [str(dataset["target_piece_id"])])]
    target_piece_id = str(target_piece_ids[0])
    contact_piece_ids = [str(item) for item in dataset.get("contact_piece_ids", [])]
    piece_bbox_map = {piece_id: _round_bbox(points) for piece_id, points in piece_points.items()}
    assembly_bbox = _round_bbox([point for points in piece_points.values() for point in points])
    piece_fill_map = {
        str(piece["piece_id"]): _PIECE_FILLS[index % len(_PIECE_FILLS)]
        for index, piece in enumerate(_BASE_PIECES)
    }

    entities: List[Dict[str, Any]] = []
    for piece in _BASE_PIECES:
        piece_id = str(piece["piece_id"])
        points = piece_points[piece_id]
        if query_id == "missing_piece_label" and piece_id == target_piece_id:
            fill = render_params.missing_fill_rgb
            outline = render_params.marked_outline_rgb
            width = max(int(render_params.seam_width_px), int(render_params.highlight_width_px) // 2)
        else:
            fill = piece_fill_map[piece_id]
            outline = render_params.seam_color_rgb
            width = int(render_params.seam_width_px)
        _draw_polygon(draw, points, fill=fill, outline=outline, width=width)
        entities.append(
            {
                "id": piece_id,
                "type": "tangram_piece",
                "shape_id": str(piece["shape_id"]),
                "shape_name": str(piece["shape_name"]),
                "bbox_px": list(piece_bbox_map[piece_id]),
                "is_target": bool(piece_id in target_piece_ids),
                "touches_target": bool(piece_id in contact_piece_ids),
            }
        )

    if query_id == "contact_count":
        for marked_piece_id in target_piece_ids:
            _draw_target_ring(
                draw,
                piece_points[str(marked_piece_id)],
                color=render_params.marked_outline_rgb,
                width=int(render_params.highlight_width_px),
            )

    option_panel_bbox_map: Dict[str, List[float]] = {}
    if query_id == "missing_piece_label":
        label_font = load_font(int(render_params.option_label_font_size_px), bold=True)
        option_bboxes = _option_layout_bboxes(
            render_params=render_params,
            option_count=int(dataset["option_count"]),
            top_y=float(option_top_y),
        )
        for option, panel_bbox in zip(list(dataset["option_specs"]), option_bboxes):
            rendered_panel = render_puzzle_option_panel(
                draw,
                panel_bbox=panel_bbox,
                option_label=str(option["option_label"]),
                label_font=label_font,
                label_center_y_px=float(panel_bbox[1] + 25),
                content_box_size_px=float(render_params.option_shape_box_size_px),
                content_gap_px=float(render_params.option_label_gap_px),
                panel_fill_rgb=render_params.option_panel_fill_rgb,
                content_fill_rgb=(255, 255, 255),
                border_color_rgb=render_params.border_color_rgb,
                text_color_rgb=render_params.text_color_rgb,
                text_stroke_rgb=render_params.text_stroke_rgb,
                panel_corner_radius_px=int(render_params.panel_corner_radius_px),
                content_corner_radius_px=int(render_params.content_corner_radius_px),
                border_width_px=int(render_params.border_width_px),
            )
            option_id = str(option["option_id"])
            option_panel_bbox_map[option_id] = list(rendered_panel.panel_bbox)
            shape_points = [
                (float(x), float(y))
                for x, y in option["shape_points"]
            ]
            content_points = _normalize_points_to_box(
                shape_points,
                rendered_panel.content_bbox,
                padding_px=12.0,
                rotation_degrees=float(option["display_rotation_degrees"]),
            )
            _draw_polygon(
                draw,
                content_points,
                fill=render_params.option_shape_fill_rgb,
                outline=render_params.seam_color_rgb,
                width=max(2, int(render_params.seam_width_px)),
            )
            entities.append(
                {
                    "id": option_id,
                    "type": "tangram_option",
                    "option_label": str(option["option_label"]),
                    "shape_id": str(option["shape_id"]),
                    "is_correct": bool(option["is_correct"]),
                    "bbox_px": list(rendered_panel.panel_bbox),
                    "display_rotation_degrees": int(option["display_rotation_degrees"]),
                }
            )

    return RenderedTangramScene(
        image=image,
        entities=entities,
        scene_bbox_px=[round(float(value), 3) for value in scene_bbox],
        assembly_panel_bbox_px=[round(float(value), 3) for value in assembly_panel_bbox],
        assembly_bbox_px=list(assembly_bbox),
        piece_bbox_map=piece_bbox_map,
        option_panel_bbox_map=option_panel_bbox_map,
    )


__all__ = [
    "SUPPORTED_TANGRAM_QUERY_IDS",
    "SUPPORTED_TANGRAM_SCENE_VARIANTS",
    "RenderedTangramScene",
    "TangramRenderParams",
    "build_tangram_dataset",
    "render_tangram_scene",
    "resolve_tangram_render_params",
]
