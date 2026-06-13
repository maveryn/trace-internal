"""Shared dartboard renderer for games-domain tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.core.visual.noise import apply_post_image_noise

from ....shared.color_distance import color_distance
from ....shared.config_defaults import group_default
from ....shared.font_assets import get_font_family_record
from ....shared.text_rendering import load_font
from ...shared.text import draw_game_text_traced as draw_text_traced
from ...shared.scene_style import (
    GamePanelSceneStyle,
    draw_panel_scene_chrome,
    game_panel_scene_style_metadata,
    make_panel_scene_background,
    resolve_game_panel_scene_style,
)
from ...shared.visual_defaults import load_games_scene_noise_defaults

from .defaults import DARTS_NAMESPACE, SCENE_ID


STANDARD_DART_SECTORS: Tuple[int, ...] = (
    20,
    1,
    18,
    4,
    13,
    6,
    10,
    15,
    2,
    17,
    3,
    19,
    7,
    16,
    8,
    11,
    14,
    9,
    12,
    5,
)

DARTBOARD_BAND_RADII_FRACTIONS: Mapping[str, float] = {
    "inner_bull": 0.100,
    "outer_bull": 0.190,
    "inner_single": 0.390,
    "triple_outer": 0.570,
    "outer_single": 0.750,
    "double_outer": 0.940,
    "frame": 1.000,
}

DARTBOARD_SAMPLE_RADIUS_FRACTIONS: Mapping[str, Tuple[float, float]] = {
    "inner_bull": (0.000, 0.086),
    "outer_bull": (0.120, 0.172),
    "inner_single": (0.225, 0.358),
    "triple": (0.425, 0.535),
    "outer_single": (0.612, 0.710),
    "double": (0.810, 0.900),
}


@dataclass(frozen=True)
class DartInstance:
    """One visible dart marker before rendering."""

    dart_id: str
    sector_value: int | None
    ring: str
    score: int
    x_px: float
    y_px: float
    is_annotation: bool


@dataclass(frozen=True)
class DartScoreOption:
    """One visible score option for a score-choice query."""

    label: str
    score: int
    is_answer: bool


@dataclass(frozen=True)
class DartboardRenderParams:
    """Resolved render controls for one dartboard scene."""

    canvas_width: int
    canvas_height: int
    board_center_x_px: int
    board_center_y_px: int
    board_radius_px: int
    marker_radius_px: int
    number_font_size_px: int
    font_family: str = ""
    layout_jitter_meta: Dict[str, Any] | None = None


@dataclass(frozen=True)
class RenderedDartSpec:
    """One rendered dart marker with trace-friendly metadata."""

    dart_id: str
    sector_value: int | None
    ring: str
    score: int
    center_px: Tuple[float, float]
    bbox_px: Tuple[float, float, float, float]
    is_annotation: bool


@dataclass(frozen=True)
class RenderedDartsScene:
    """Rendered dartboard scene plus metadata."""

    image: Image.Image
    dart_specs: Tuple[RenderedDartSpec, ...]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


@dataclass(frozen=True)
class RenderedDartsTaskContext:
    """Rendered darts image plus scene-wide visual metadata."""

    image: Image.Image
    rendered_scene: RenderedDartsScene
    panel_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]
    post_noise_meta: Dict[str, Any]
    text_style_meta: Dict[str, Any]


POST_IMAGE_NOISE_DEFAULTS = load_games_scene_noise_defaults(scene_id=SCENE_ID, apply_prob=0.0)


_STYLE_PALETTES: Mapping[str, Mapping[str, Tuple[int, int, int]]] = {
    "classic": {
        "board_frame": (28, 31, 35),
        "light_sector": (238, 224, 194),
        "dark_sector": (33, 36, 40),
        "red": (173, 42, 44),
        "green": (42, 132, 82),
        "wire": (222, 218, 205),
        "number": (246, 246, 238),
        "dart": (244, 198, 65),
        "dart_outline": (41, 45, 52),
        "annotation": (252, 110, 74),
    },
    "soft": {
        "board_frame": (51, 61, 68),
        "light_sector": (246, 231, 197),
        "dark_sector": (63, 69, 74),
        "red": (198, 76, 74),
        "green": (62, 147, 101),
        "wire": (238, 232, 216),
        "number": (252, 249, 239),
        "dart": (102, 180, 232),
        "dart_outline": (29, 45, 58),
        "annotation": (242, 112, 96),
    },
    "outlined": {
        "board_frame": (31, 41, 48),
        "light_sector": (242, 236, 219),
        "dark_sector": (59, 66, 73),
        "red": (181, 64, 67),
        "green": (55, 137, 94),
        "wire": (32, 38, 44),
        "number": (248, 248, 240),
        "dart": (250, 218, 93),
        "dart_outline": (13, 22, 30),
        "annotation": (234, 98, 76),
    },
    "league_blue": {
        "board_frame": (24, 48, 83),
        "light_sector": (239, 231, 210),
        "dark_sector": (31, 60, 96),
        "red": (202, 58, 70),
        "green": (38, 151, 130),
        "wire": (226, 233, 240),
        "number": (250, 252, 255),
        "dart": (247, 197, 72),
        "dart_outline": (9, 24, 44),
        "annotation": (247, 126, 90),
    },
    "parchment": {
        "board_frame": (76, 55, 38),
        "light_sector": (247, 227, 184),
        "dark_sector": (78, 63, 49),
        "red": (174, 57, 55),
        "green": (75, 138, 85),
        "wire": (238, 217, 178),
        "number": (255, 244, 218),
        "dart": (73, 142, 191),
        "dart_outline": (40, 28, 21),
        "annotation": (231, 112, 76),
    },
    "neon": {
        "board_frame": (17, 24, 39),
        "light_sector": (225, 236, 230),
        "dark_sector": (24, 34, 55),
        "red": (224, 61, 104),
        "green": (34, 197, 154),
        "wire": (178, 220, 238),
        "number": (242, 250, 255),
        "dart": (250, 204, 21),
        "dart_outline": (4, 12, 24),
        "annotation": (255, 121, 91),
    },
}

_DART_COLOR_CANDIDATES: Tuple[Tuple[int, int, int], ...] = (
    (37, 99, 235),
    (147, 51, 234),
    (217, 70, 239),
    (6, 182, 212),
    (14, 165, 233),
    (244, 114, 182),
    (236, 72, 153),
    (125, 58, 237),
    (79, 70, 229),
    (56, 189, 248),
)
_DART_COLOR_ANCHOR_KEYS: Tuple[str, ...] = (
    "board_frame",
    "light_sector",
    "dark_sector",
    "red",
    "green",
    "wire",
    "number",
)
_DART_COLOR_EXTRA_ANCHORS: Tuple[Tuple[int, int, int], ...] = (
    (20, 24, 28),
    (255, 214, 72),
    (255, 246, 142),
)


def _palette(style_variant: str) -> Mapping[str, Tuple[int, int, int]]:
    """Return one safe dartboard palette."""

    return _STYLE_PALETTES.get(str(style_variant), _STYLE_PALETTES["classic"])


def dartboard_anchor_colors(style_variant: str) -> Tuple[Tuple[int, int, int], ...]:
    """Return board and highlight colors that dart markers must avoid."""

    palette = _palette(str(style_variant))
    colors = [tuple(int(v) for v in palette[key]) for key in _DART_COLOR_ANCHOR_KEYS]
    colors.extend(tuple(int(v) for v in color) for color in _DART_COLOR_EXTRA_ANCHORS)
    return tuple(colors)


def sample_dart_marker_color(
    rng,
    *,
    style_variant: str,
    min_lab_distance: float = 40.0,
) -> Tuple[Tuple[int, int, int], float]:
    """Sample a dart fill color that is Lab-separated from board colors."""

    anchors = dartboard_anchor_colors(str(style_variant))
    candidates = list(_DART_COLOR_CANDIDATES)
    rng.shuffle(candidates)
    best_color = candidates[0]
    best_min_distance = -1.0
    for candidate in candidates:
        min_distance = min(float(color_distance(candidate, anchor, distance_space="lab")) for anchor in anchors)
        if float(min_distance) > float(best_min_distance):
            best_color = candidate
            best_min_distance = float(min_distance)
        if float(min_distance) >= float(min_lab_distance):
            return tuple(int(v) for v in candidate), float(min_distance)
    return tuple(int(v) for v in best_color), float(best_min_distance)


def polar_to_xy(*, cx: float, cy: float, radius: float, angle_deg: float) -> Tuple[float, float]:
    """Convert dartboard polar coordinates to image pixel coordinates.

    Angle 0 is the top of the board and positive angles move clockwise.
    """

    theta = math.radians(float(angle_deg))
    return (
        float(cx + (float(radius) * math.sin(theta))),
        float(cy - (float(radius) * math.cos(theta))),
    )


def _ring_polygon(
    *,
    cx: float,
    cy: float,
    inner_radius: float,
    outer_radius: float,
    start_deg: float,
    end_deg: float,
    steps: int = 8,
) -> List[Tuple[float, float]]:
    """Return polygon points for one annular sector."""

    outer: List[Tuple[float, float]] = []
    inner: List[Tuple[float, float]] = []
    for index in range(int(steps) + 1):
        t = float(index) / float(max(1, steps))
        angle = float(start_deg) + (float(end_deg) - float(start_deg)) * t
        outer.append(polar_to_xy(cx=cx, cy=cy, radius=outer_radius, angle_deg=angle))
    for index in range(int(steps), -1, -1):
        t = float(index) / float(max(1, steps))
        angle = float(start_deg) + (float(end_deg) - float(start_deg)) * t
        inner.append(polar_to_xy(cx=cx, cy=cy, radius=inner_radius, angle_deg=angle))
    return outer + inner


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    *,
    font,
    fill: Tuple[int, int, int],
    stroke_fill: Tuple[int, int, int] | None = None,
    stroke_width: int = 0,
) -> None:
    """Draw text centered on one point."""

    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=int(stroke_width))
    width = float(bbox[2] - bbox[0])
    height = float(bbox[3] - bbox[1])
    draw_text_traced(draw,
        (float(xy[0]) - (0.5 * width), float(xy[1]) - (0.5 * height)),
        str(text),
        font=font,
        fill=fill,
        stroke_width=int(stroke_width),
        stroke_fill=stroke_fill,
     role="readout", required=False,)


def _draw_board(
    image: Image.Image,
    *,
    params: DartboardRenderParams,
    style_variant: str,
) -> Dict[str, Any]:
    """Draw the dartboard and return board geometry metadata."""

    draw = ImageDraw.Draw(image)
    palette = _palette(str(style_variant))
    cx = float(params.board_center_x_px)
    cy = float(params.board_center_y_px)
    radius = float(params.board_radius_px)

    radii = {key: float(value) * radius for key, value in DARTBOARD_BAND_RADII_FRACTIONS.items()}
    ring_bands = (
        ("inner_single", float(radii["outer_bull"]), float(radii["inner_single"])),
        ("triple", float(radii["inner_single"]), float(radii["triple_outer"])),
        ("outer_single", float(radii["triple_outer"]), float(radii["outer_single"])),
        ("double", float(radii["outer_single"]), float(radii["double_outer"])),
    )

    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=tuple(int(v) for v in palette["board_frame"]),
    )
    for sector_index, sector_value in enumerate(STANDARD_DART_SECTORS):
        start_deg = float((sector_index * 18.0) - 9.0)
        end_deg = float((sector_index * 18.0) + 9.0)
        alternate_fill = palette["light_sector"] if sector_index % 2 == 0 else palette["dark_sector"]
        for ring_name, inner_radius, outer_radius in ring_bands:
            if ring_name in {"double", "triple"}:
                fill = palette["red"] if sector_index % 2 == 0 else palette["green"]
            else:
                fill = alternate_fill
            draw.polygon(
                _ring_polygon(
                    cx=cx,
                    cy=cy,
                    inner_radius=float(inner_radius),
                    outer_radius=float(outer_radius),
                    start_deg=float(start_deg),
                    end_deg=float(end_deg),
                ),
                fill=tuple(int(v) for v in fill),
            )

    wire = tuple(int(v) for v in palette["wire"])
    for ring_radius in (
        radii["outer_bull"],
        radii["inner_single"],
        radii["triple_outer"],
        radii["outer_single"],
        radii["double_outer"],
    ):
        draw.ellipse(
            [cx - ring_radius, cy - ring_radius, cx + ring_radius, cy + ring_radius],
            outline=wire,
            width=3,
        )
    for sector_index in range(len(STANDARD_DART_SECTORS)):
        angle = float((sector_index * 18.0) - 9.0)
        x_outer, y_outer = polar_to_xy(cx=cx, cy=cy, radius=radii["double_outer"], angle_deg=angle)
        x_inner, y_inner = polar_to_xy(cx=cx, cy=cy, radius=radii["outer_bull"], angle_deg=angle)
        draw.line([(x_inner, y_inner), (x_outer, y_outer)], fill=wire, width=2)

    draw.ellipse(
        [cx - radii["outer_bull"], cy - radii["outer_bull"], cx + radii["outer_bull"], cy + radii["outer_bull"]],
        fill=tuple(int(v) for v in palette["green"]),
        outline=wire,
        width=3,
    )
    draw.ellipse(
        [cx - radii["inner_bull"], cy - radii["inner_bull"], cx + radii["inner_bull"], cy + radii["inner_bull"]],
        fill=tuple(int(v) for v in palette["red"]),
        outline=wire,
        width=3,
    )

    number_font = load_font(
        int(params.number_font_size_px),
        bold=True,
        font_family=str(params.font_family) or None,
    )
    for sector_index, sector_value in enumerate(STANDARD_DART_SECTORS):
        angle = float(sector_index * 18.0)
        x_text, y_text = polar_to_xy(cx=cx, cy=cy, radius=radius * 1.055, angle_deg=angle)
        _draw_centered_text(
            draw,
            (x_text, y_text),
            str(sector_value),
            font=number_font,
            fill=tuple(int(v) for v in palette["number"]),
            stroke_fill=(20, 24, 28),
            stroke_width=2,
        )

    return {
        "center_px": [round(cx, 3), round(cy, 3)],
        "radius_px": round(radius, 3),
        "radii_px": {key: round(float(value), 3) for key, value in radii.items()},
        "sector_order_clockwise_from_top": [int(value) for value in STANDARD_DART_SECTORS],
    }


def _draw_target_highlight(
    image: Image.Image,
    *,
    params: DartboardRenderParams,
    target_ring: str | None,
    target_sector_value: int | None,
) -> None:
    """Draw a non-answer target-region highlight for ring/sector count queries."""

    if target_ring is None and target_sector_value is None:
        return
    cx = float(params.board_center_x_px)
    cy = float(params.board_center_y_px)
    radius = float(params.board_radius_px)
    radii = {key: float(value) * radius for key, value in DARTBOARD_BAND_RADII_FRACTIONS.items()}
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    fill = (255, 214, 72, 118)
    outline = (255, 246, 142, 230)

    def draw_band(inner_radius: float, outer_radius: float, start_deg: float, end_deg: float) -> None:
        draw.polygon(
            _ring_polygon(
                cx=cx,
                cy=cy,
                inner_radius=float(inner_radius),
                outer_radius=float(outer_radius),
                start_deg=float(start_deg),
                end_deg=float(end_deg),
            ),
            fill=fill,
            outline=outline,
        )

    if target_sector_value is not None:
        try:
            sector_index = STANDARD_DART_SECTORS.index(int(target_sector_value))
        except ValueError:
            sector_index = 0
        draw_band(
            radii["outer_bull"],
            radii["double_outer"],
            float((sector_index * 18.0) - 9.0),
            float((sector_index * 18.0) + 9.0),
        )
    elif str(target_ring) == "bull":
        draw.ellipse(
            [cx - radii["outer_bull"], cy - radii["outer_bull"], cx + radii["outer_bull"], cy + radii["outer_bull"]],
            fill=fill,
            outline=outline,
            width=3,
        )
    else:
        ring_bands = {
            "single": (
                (radii["outer_bull"], radii["inner_single"]),
                (radii["triple_outer"], radii["outer_single"]),
            ),
            "triple": ((radii["inner_single"], radii["triple_outer"]),),
            "double": ((radii["outer_single"], radii["double_outer"]),),
        }.get(str(target_ring), ())
        for inner_radius, outer_radius in ring_bands:
            for sector_index in range(len(STANDARD_DART_SECTORS)):
                draw_band(
                    float(inner_radius),
                    float(outer_radius),
                    float((sector_index * 18.0) - 9.0),
                    float((sector_index * 18.0) + 9.0),
                )

    image.alpha_composite(overlay)


def _draw_dart(
    draw: ImageDraw.ImageDraw,
    *,
    dart: DartInstance,
    params: DartboardRenderParams,
    style_variant: str,
    dart_fill_color: Tuple[int, int, int] | None = None,
) -> Tuple[float, float, float, float]:
    """Draw one dart marker and return its bbox."""

    palette = _palette(str(style_variant))
    radius = float(params.marker_radius_px)
    x = float(dart.x_px)
    y = float(dart.y_px)
    fill = palette["dart"] if dart_fill_color is None else tuple(int(v) for v in dart_fill_color)
    outline = palette["dart_outline"]
    bbox = (
        round(x - radius, 3),
        round(y - radius, 3),
        round(x + radius, 3),
        round(y + radius, 3),
    )
    arm_radius = round(radius * 1.55)
    x_i = round(x)
    y_i = round(y)
    draw.line([(x_i - arm_radius, y_i), (x_i + arm_radius, y_i)], fill=tuple(int(v) for v in outline), width=5)
    draw.line([(x_i, y_i - arm_radius), (x_i, y_i + arm_radius)], fill=tuple(int(v) for v in outline), width=5)
    draw.line([(x_i - arm_radius, y_i), (x_i + arm_radius, y_i)], fill=tuple(int(v) for v in fill), width=3)
    draw.line([(x_i, y_i - arm_radius), (x_i, y_i + arm_radius)], fill=tuple(int(v) for v in fill), width=3)
    draw.ellipse(bbox, fill=tuple(int(v) for v in fill), outline=tuple(int(v) for v in outline), width=2)
    return bbox


def _draw_score_options(
    image: Image.Image,
    *,
    options: Sequence[DartScoreOption],
    params: DartboardRenderParams,
    style_variant: str,
) -> Dict[str, Any]:
    """Draw visible score-choice options and return option bbox metadata."""

    if not options:
        return {}
    draw = ImageDraw.Draw(image)
    palette = _palette(str(style_variant))
    option_font = load_font(30, bold=True, font_family=str(params.font_family) or None)
    panel_y0 = float(params.canvas_height - 114)
    panel_y1 = float(params.canvas_height - 34)
    left = 82.0
    gap = 18.0
    option_width = (float(params.canvas_width) - (2.0 * left) - (float(len(options) - 1) * gap)) / float(len(options))
    option_bboxes: Dict[str, List[float]] = {}
    option_scores: Dict[str, int] = {}
    for index, option in enumerate(options):
        x0 = left + float(index) * (option_width + gap)
        x1 = x0 + option_width
        bbox = [round(x0, 3), round(panel_y0, 3), round(x1, 3), round(panel_y1, 3)]
        option_bboxes[str(option.label)] = [float(v) for v in bbox]
        option_scores[str(option.label)] = int(option.score)
        draw.rounded_rectangle(
            bbox,
            radius=12,
            fill=(28, 31, 35, 235),
            outline=tuple(int(v) for v in palette["wire"]),
            width=3,
        )
        text = f"{option.label}: {int(option.score)}"
        _draw_centered_text(
            draw,
            ((x0 + x1) * 0.5, (panel_y0 + panel_y1) * 0.5),
            text,
            font=option_font,
            fill=tuple(int(v) for v in palette["number"]),
            stroke_fill=(20, 24, 28),
            stroke_width=2,
        )
    return {"score_option_bboxes_px": option_bboxes, "score_option_values": option_scores}


def _panel_bbox(
    *,
    params: DartboardRenderParams,
    has_score_options: bool,
) -> Tuple[int, int, int, int]:
    """Return a backing panel bbox that follows the jittered dartboard."""

    cx = float(params.board_center_x_px)
    cy = float(params.board_center_y_px)
    radius = float(params.board_radius_px)
    x0 = max(10, int(round(cx - radius - 62.0)))
    y0 = max(10, int(round(cy - radius - 44.0)))
    x1 = min(int(params.canvas_width) - 10, int(round(cx + radius + 62.0)))
    if has_score_options:
        y1 = int(params.canvas_height) - 18
    else:
        y1 = min(int(params.canvas_height) - 10, int(round(cy + radius + 48.0)))
    return (int(x0), int(y0), int(x1), int(max(y0 + 80, y1)))


def render_darts_scene(
    *,
    darts: Sequence[DartInstance],
    background: Image.Image,
    style_variant: str,
    params: DartboardRenderParams,
    target_ring: str | None = None,
    target_sector_value: int | None = None,
    dart_fill_color: Tuple[int, int, int] | None = None,
    dart_fill_min_lab_distance: float | None = None,
    score_options: Sequence[DartScoreOption] = (),
    panel_style: GamePanelSceneStyle | None = None,
) -> RenderedDartsScene:
    """Render the board, optional target highlight, darts, and option strip.

    The renderer only projects an already-sampled scene; scoring semantics,
    answer binding, and annotation membership are owned outside this layer.
    """

    image = background.convert("RGBA")
    panel_bbox = _panel_bbox(params=params, has_score_options=bool(score_options))
    if panel_style is not None:
        draw_panel_scene_chrome(
            ImageDraw.Draw(image),
            bbox=panel_bbox,
            style=panel_style,
            radius=24,
            border_width=3,
        )
    board_meta = _draw_board(image, params=params, style_variant=str(style_variant))
    _draw_target_highlight(
        image,
        params=params,
        target_ring=target_ring,
        target_sector_value=target_sector_value,
    )
    draw = ImageDraw.Draw(image)

    dart_specs: List[RenderedDartSpec] = []
    scene_entities: List[Dict[str, Any]] = []
    dart_bboxes: Dict[str, List[float]] = {}
    dart_centers: Dict[str, List[float]] = {}
    for dart in darts:
        bbox = _draw_dart(
            draw,
            dart=dart,
            params=params,
            style_variant=str(style_variant),
            dart_fill_color=dart_fill_color,
        )
        center = (round(float(dart.x_px), 3), round(float(dart.y_px), 3))
        dart_bboxes[str(dart.dart_id)] = [float(v) for v in bbox]
        dart_centers[str(dart.dart_id)] = [float(center[0]), float(center[1])]
        dart_specs.append(
            RenderedDartSpec(
                dart_id=str(dart.dart_id),
                sector_value=None if dart.sector_value is None else int(dart.sector_value),
                ring=str(dart.ring),
                score=int(dart.score),
                center_px=center,
                bbox_px=bbox,
                is_annotation=bool(dart.is_annotation),
            )
        )
        scene_entities.append(
            {
                "entity_id": str(dart.dart_id),
                "entity_type": "dart",
                "bbox_px": [float(v) for v in bbox],
                "attrs": {
                    "sector_value": None if dart.sector_value is None else int(dart.sector_value),
                    "ring": str(dart.ring),
                    "score": int(dart.score),
                    "is_annotation": bool(dart.is_annotation),
                },
            }
        )

    option_map = _draw_score_options(
        image,
        options=tuple(score_options),
        params=params,
        style_variant=str(style_variant),
    )
    for option in score_options:
        option_bbox = option_map.get("score_option_bboxes_px", {}).get(str(option.label))
        if option_bbox is None:
            continue
        scene_entities.append(
            {
                "entity_id": f"score_option_{str(option.label)}",
                "entity_type": "score_option",
                "bbox_px": [float(v) for v in option_bbox],
                "attrs": {
                    "label": str(option.label),
                    "score": int(option.score),
                    "is_answer": bool(option.is_answer),
                },
            }
        )

    return RenderedDartsScene(
        image=image,
        dart_specs=tuple(dart_specs),
        scene_entities=tuple(scene_entities),
        render_map={
            "board": dict(board_meta),
            "dart_bboxes_px": dict(dart_bboxes),
            "dart_centers_px": dict(dart_centers),
            "dart_fill_color": None if dart_fill_color is None else [int(v) for v in dart_fill_color],
            "dart_fill_min_lab_distance": None
            if dart_fill_min_lab_distance is None
            else round(float(dart_fill_min_lab_distance), 3),
            "layout_jitter": dict(params.layout_jitter_meta or {}),
            "scene_panel_bbox_px": [int(value) for value in panel_bbox],
            "panel_scene_style": {}
            if panel_style is None
            else game_panel_scene_style_metadata(panel_style),
            "font_family": str(params.font_family),
            **dict(option_map),
        },
    )


def _allowed_panel_treatments(params: Mapping[str, Any], render_defaults: Mapping[str, Any]) -> tuple[str, ...] | None:
    """Resolve optional panel-scene treatment filters from rendering config."""

    raw = params.get(
        "panel_scene_treatments",
        group_default(render_defaults, "panel_scene_treatments", None),
    )
    if isinstance(raw, str):
        return (str(raw),)
    if raw is None:
        return None
    return tuple(str(item) for item in raw)


def render_darts_task_scene(
    *,
    darts: Sequence[DartInstance],
    score_options: Sequence[DartScoreOption],
    target_ring: str | None,
    style_variant: str,
    render_params: DartboardRenderParams,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
) -> RenderedDartsTaskContext:
    """Render a full darts task image with shared panel style and post-noise."""

    panel_style, panel_style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{DARTS_NAMESPACE}.panel_scene_style",
        treatments=_allowed_panel_treatments(params, render_defaults),
        treatment_weights=params.get(
            "panel_scene_treatment_weights",
            group_default(render_defaults, "panel_scene_treatment_weights", None),
        ),
        palette_weights=params.get(
            "panel_scene_palette_weights",
            group_default(render_defaults, "panel_scene_palette_weights", None),
        ),
    )
    color_rng = spawn_rng(int(instance_seed), f"{DARTS_NAMESPACE}.dart_color")
    dart_fill_color, dart_fill_min_lab_distance = sample_dart_marker_color(
        color_rng,
        style_variant=str(style_variant),
        min_lab_distance=40.0,
    )
    background, background_meta = make_panel_scene_background(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        style=panel_style,
    )
    rendered_scene = render_darts_scene(
        darts=tuple(darts),
        background=background,
        style_variant=str(style_variant),
        params=render_params,
        target_ring=target_ring,
        dart_fill_color=dart_fill_color,
        dart_fill_min_lab_distance=float(dart_fill_min_lab_distance),
        score_options=tuple(score_options),
        panel_style=panel_style,
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered_scene.image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return RenderedDartsTaskContext(
        image=image,
        rendered_scene=rendered_scene,
        panel_style_meta=dict(panel_style_meta),
        background_meta=dict(background_meta),
        post_noise_meta=dict(post_noise_meta),
        text_style_meta={
            "font_family": str(render_params.font_family),
            "font_asset": get_font_family_record(str(render_params.font_family)).to_trace(),
        },
    )


__all__ = [
    "DartInstance",
    "DartScoreOption",
    "DartboardRenderParams",
    "DARTBOARD_BAND_RADII_FRACTIONS",
    "DARTBOARD_SAMPLE_RADIUS_FRACTIONS",
    "RenderedDartsTaskContext",
    "RenderedDartsScene",
    "STANDARD_DART_SECTORS",
    "dartboard_anchor_colors",
    "polar_to_xy",
    "render_darts_scene",
    "render_darts_task_scene",
    "sample_dart_marker_color",
]
