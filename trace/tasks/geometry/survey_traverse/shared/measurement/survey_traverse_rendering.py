"""Rendering helpers for survey traverse tasks."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ......core.seed import spawn_rng
from .....shared.config_defaults import group_default
from .....shared.text_legibility import draw_text_traced
from .....shared.text_rendering import load_font
from ....shared.diagram_style import (
    geometry_diagram_style_metadata,
    prepare_geometry_diagram_style_and_background,
)
from ....shared.measurement_rendering import (
    bbox_from_points,
    bbox_to_list,
    draw_label_backplate,
    pad_bbox,
    readout_text_fill,
    readout_text_metadata,
)
from ....shared.scene_transform import LazySceneTransform
from ....shared.vector2d import point_to_list as _point_to_list

from .survey_traverse_common import (
    BBox,
    Color,
    DEGREE_SYMBOL,
    Point,
    SCENE_ID,
    SCENE_ID,
    AREA_NAMESPACE,
    BEARING_NAMESPACE,
    ELEVATION_NAMESPACE,
    _ANNOTATION_KEYS,
    _AREA_ANNOTATION_KEYS,
    _CLOSED_ANNOTATION_KEYS,
    _ELEVATION_ANNOTATION_KEYS,
    _RenderContext,
    _RenderedSurveyAreaScene,
    _RenderedSurveyScene,
    _ResolvedAreaProblem,
    _ResolvedElevationProblem,
    _ResolvedProblem,
    _bearing_to_unit_vector,
    _normalize_bearing,
)

def _make_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> tuple[_RenderContext, Dict[str, Any]]:
    width = int(render_defaults.get("canvas_width", 820))
    height = int(render_defaults.get("canvas_height", 580))
    background, background_meta, style, style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=width,
        canvas_height=height,
        allow_dark=False,
        require_grid=None,
    )
    draw = ImageDraw.Draw(background)
    line_width = int(render_defaults.get("line_width", max(2, int(style.axis_stroke_width_px))))
    label_size = int(render_defaults.get("label_font_size", 22))
    small_size = int(render_defaults.get("small_label_font_size", 18))
    tiny_size = int(render_defaults.get("tiny_label_font_size", 14))
    ctx = _RenderContext(
        image=background,
        draw=draw,
        width=width,
        height=height,
        line_color=tuple(int(v) for v in style.stroke_rgb),
        secondary_color=tuple(int(v) for v in style.secondary_stroke_rgb),
        guide_color=tuple(int(v) for v in style.guide_rgb),
        label_color=tuple(int(v) for v in style.label_rgb),
        label_stroke_color=tuple(int(v) for v in style.label_stroke_rgb),
        panel_fill=tuple(int(v) for v in style.panel_fill_rgb),
        panel_alt_fill=tuple(int(v) for v in style.panel_alt_fill_rgb),
        accent_color=tuple(int(v) for v in style.accent_rgb),
        secondary_accent_color=tuple(int(v) for v in style.secondary_accent_rgb),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(1, int(style.label_stroke_width_px)),
        font=load_font(max(12, label_size)),
        small_font=load_font(max(10, small_size)),
        tiny_font=load_font(max(8, tiny_size)),
        diagram_style_meta=dict(style_meta),
        background_meta=dict(background_meta),
    )
    return ctx, {
        "style": {
            "technical_diagram": dict(style_meta),
            "background": dict(background_meta),
        },
        "font_family": str(getattr(ctx.font, "path", "")),
    }

def _text_bbox(ctx: _RenderContext, xy: Point, text: str, *, font: Any | None = None) -> BBox:
    bbox = ctx.draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font or ctx.font)
    return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))

def _draw_label(
    ctx: _RenderContext,
    xy: Point,
    text: str,
    *,
    font: Any | None = None,
    anchor: str = "mm",
    fill: Color | None = None,
) -> BBox:
    resolved_font = font or ctx.font
    x, y = float(xy[0]), float(xy[1])
    bbox = ctx.draw.textbbox(
        (x, y),
        str(text),
        font=resolved_font,
        anchor=anchor,
        stroke_width=max(0, int(ctx.label_stroke_width)),
    )
    draw_label_backplate(ctx, bbox)
    text_fill = readout_text_fill(ctx, fill)
    draw_text_traced(
        ctx.draw,
        (x, y),
        str(text),
        font=resolved_font,
        fill=text_fill,
        anchor=anchor,
        stroke_width=ctx.label_stroke_width,
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=True,
        extra_metadata=readout_text_metadata(ctx, text_fill),
    )
    return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))

def _draw_arrow(ctx: _RenderContext, start: Point, end: Point, *, fill: Color, width: int | None = None) -> None:
    stroke = int(width or ctx.line_width)
    ctx.draw.line([start, end], fill=fill, width=stroke)
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length <= 1e-6:
        return
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    size = 12.0 + 1.5 * stroke
    tip = end
    left = (float(end[0]) - ux * size + px * size * 0.42, float(end[1]) - uy * size + py * size * 0.42)
    right = (float(end[0]) - ux * size - px * size * 0.42, float(end[1]) - uy * size - py * size * 0.42)
    ctx.draw.polygon([tip, left, right], fill=fill)

def _draw_station(ctx: _RenderContext, point: Point, label: str, *, label_offset: Point = (0.0, -24.0)) -> BBox:
    radius = 6.0
    ctx.draw.ellipse(
        [point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius],
        fill=ctx.accent_color,
        outline=ctx.line_color,
        width=max(1, ctx.line_width - 1),
    )
    return _draw_label(
        ctx,
        (float(point[0]) + float(label_offset[0]), float(point[1]) + float(label_offset[1])),
        label,
        font=ctx.font,
    )

def _draw_angle_arc(
    ctx: _RenderContext,
    *,
    center: Point,
    bearing_a: int,
    bearing_b: int,
    radius: float,
    color: Color,
) -> None:
    # PIL arc angles use x-axis degrees, increasing clockwise in image space.
    def pil_angle_from_bearing(bearing: int) -> float:
        return float(bearing) - 90.0

    start = pil_angle_from_bearing(int(bearing_a))
    end = pil_angle_from_bearing(int(bearing_b))
    ctx.draw.arc(
        [
            float(center[0]) - radius,
            float(center[1]) - radius,
            float(center[0]) + radius,
            float(center[1]) + radius,
        ],
        start=start,
        end=end,
        fill=color,
        width=max(2, ctx.line_width - 1),
    )

def _direction_endpoint(start: Point, bearing: int, length: float) -> Point:
    ux, uy = _bearing_to_unit_vector(int(bearing))
    return (float(start[0]) + ux * float(length), float(start[1]) + uy * float(length))

def _ray_length_inside_box(start: Point, bearing: int, box: BBox, *, margin: float = 0.0) -> float:
    ux, uy = _bearing_to_unit_vector(int(bearing))
    x0, y0, x1, y1 = [float(value) for value in box]
    x0 += float(margin)
    y0 += float(margin)
    x1 -= float(margin)
    y1 -= float(margin)
    candidates: list[float] = []
    if ux > 1e-6:
        candidates.append((x1 - float(start[0])) / ux)
    elif ux < -1e-6:
        candidates.append((x0 - float(start[0])) / ux)
    if uy > 1e-6:
        candidates.append((y1 - float(start[1])) / uy)
    elif uy < -1e-6:
        candidates.append((y0 - float(start[1])) / uy)
    positive = [float(value) for value in candidates if float(value) > 0.0]
    return min(positive) if positive else 120.0

def _render_back_bearing_scene(ctx: _RenderContext, problem: _ResolvedProblem, *, instance_seed: int) -> _RenderedSurveyScene:
    rng = spawn_rng(int(instance_seed), f"{BEARING_NAMESPACE}.back_bearing.layout")
    labels = problem.station_labels
    station_a = (float(ctx.width) * 0.36 + rng.uniform(-18, 18), float(ctx.height) * 0.61 + rng.uniform(-14, 14))
    station_b = _direction_endpoint(station_a, int(problem.answer), 245.0)
    station_b = (
        max(145.0, min(float(ctx.width) - 135.0, station_b[0])),
        max(130.0, min(float(ctx.height) - 120.0, station_b[1])),
    )
    station_a = _direction_endpoint(station_b, int(problem.given_bearing), 245.0)
    panel = (52.0, 48.0, float(ctx.width) - 52.0, float(ctx.height) - 48.0)
    ctx.draw.rounded_rectangle(panel, radius=10, fill=ctx.panel_fill, outline=ctx.line_color, width=ctx.line_width)

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes[labels[0]] = _draw_station(ctx, station_a, labels[0], label_offset=(-20.0, -20.0))
    label_bboxes[labels[1]] = _draw_station(ctx, station_b, labels[1], label_offset=(22.0, -18.0))
    _draw_arrow(ctx, station_a, station_b, fill=ctx.line_color, width=ctx.line_width + 1)
    _draw_arrow(ctx, station_b, station_a, fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))

    north_end = (station_a[0], station_a[1] - 78.0)
    _draw_arrow(ctx, station_a, north_end, fill=ctx.guide_color, width=max(2, ctx.line_width - 1))
    label_bboxes["north"] = _draw_label(ctx, (north_end[0], north_end[1] - 15), "N", font=ctx.small_font)
    target_end = _direction_endpoint(station_a, int(problem.answer), 92.0)
    _draw_angle_arc(ctx, center=station_a, bearing_a=0, bearing_b=int(problem.answer), radius=48.0, color=ctx.accent_color)
    label_bboxes["target"] = _draw_label(
        ctx,
        ((station_a[0] + target_end[0]) / 2.0 + 14.0, (station_a[1] + target_end[1]) / 2.0 - 8.0),
        "?",
        font=ctx.font,
        fill=ctx.accent_color,
    )

    known_mid = ((station_b[0] + station_a[0]) / 2.0, (station_b[1] + station_a[1]) / 2.0)
    segment_dx = float(station_b[0]) - float(station_a[0])
    segment_dy = float(station_b[1]) - float(station_a[1])
    segment_length = max(1.0, math.hypot(segment_dx, segment_dy))
    normal = (-segment_dy / segment_length, segment_dx / segment_length)
    label_center = (known_mid[0] + normal[0] * 48.0, known_mid[1] + normal[1] * 48.0)
    known_text = f"{labels[1]} to {labels[0]}: {problem.given_bearing}{DEGREE_SYMBOL}"
    label_bboxes["known_bearing"] = _draw_label(ctx, label_center, known_text, font=ctx.small_font)

    note_x0, note_y0 = float(ctx.width) - 310.0, float(ctx.height) - 158.0
    note_bbox = (note_x0, note_y0, float(ctx.width) - 70.0, float(ctx.height) - 68.0)
    ctx.draw.rounded_rectangle(note_bbox, radius=8, fill=ctx.panel_alt_fill, outline=ctx.secondary_color, width=2)
    note_lines = (
        "Field bearing note",
        f"{labels[1]}{labels[0]} bearing {problem.given_bearing}{DEGREE_SYMBOL}",
        f"{labels[0]}{labels[1]} bearing ?",
    )
    for row, text in enumerate(note_lines):
        y = note_y0 + 20.0 + row * 25.0
        _draw_label(ctx, (note_x0 + 16.0, y), text, font=ctx.tiny_font, anchor="lm")

    target_direction = _direction_endpoint(station_a, int(problem.answer), 72.0)
    annotation = {
        "station_a": station_a,
        "station_b": station_b,
        "reference_north": north_end,
        "target_direction": target_direction,
    }
    entities = (
        {"id": "station_a", "type": "survey_station", "label": labels[0], "point": _point_to_list(station_a)},
        {"id": "station_b", "type": "survey_station", "label": labels[1], "point": _point_to_list(station_b)},
    )
    return _RenderedSurveyScene(
        image=ctx.image,
        annotation_keyed_points=dict(annotation),
        annotation_roles=_ANNOTATION_KEYS,
        scene_entities=entities,
        label_bboxes=dict(label_bboxes),
        render_map={
            "station_points": {labels[0]: _point_to_list(station_a), labels[1]: _point_to_list(station_b)},
            "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
            "field_note_bbox": bbox_to_list(note_bbox),
            "panel_bbox": bbox_to_list(panel),
        },
        witness={
            "survey_query_family": "back_bearing",
            "station_labels": list(labels),
            "known_back_bearing": int(problem.given_bearing),
            "target_forward_bearing": int(problem.answer),
        },
    )

def _render_closed_traverse_scene(
    ctx: _RenderContext,
    problem: _ResolvedProblem,
    *,
    instance_seed: int,
) -> _RenderedSurveyScene:
    if problem.turn_angle is None or problem.turn_direction is None:
        raise ValueError("closed traverse problem requires turn angle and direction")
    rng = spawn_rng(int(instance_seed), f"{BEARING_NAMESPACE}.closed_traverse.layout")
    labels = problem.station_labels
    panel = (52.0, 48.0, float(ctx.width) - 52.0, float(ctx.height) - 48.0)
    ctx.draw.rounded_rectangle(panel, radius=10, fill=ctx.panel_fill, outline=ctx.line_color, width=ctx.line_width)
    inner_panel = (95.0, 105.0, float(ctx.width) - 95.0, float(ctx.height) - 105.0)
    station_b = (float(ctx.width) * 0.48 + rng.uniform(-16, 16), float(ctx.height) * 0.55 + rng.uniform(-10, 10))
    incoming_bearing = _normalize_bearing(int(problem.known_bearing) + 180)
    max_length = min(
        205.0,
        _ray_length_inside_box(station_b, incoming_bearing, inner_panel, margin=10.0),
        _ray_length_inside_box(station_b, int(problem.answer), inner_panel, margin=10.0),
    )
    leg_length = max(118.0, float(max_length) * 0.90)
    station_a = _direction_endpoint(station_b, incoming_bearing, leg_length)
    station_c = _direction_endpoint(station_b, int(problem.answer), leg_length)

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes[labels[0]] = _draw_station(ctx, station_a, labels[0])
    label_bboxes[labels[1]] = _draw_station(ctx, station_b, labels[1], label_offset=(22.0, -18.0))
    label_bboxes[labels[2]] = _draw_station(ctx, station_c, labels[2])
    _draw_arrow(ctx, station_a, station_b, fill=ctx.line_color, width=ctx.line_width + 1)
    _draw_arrow(ctx, station_b, station_c, fill=ctx.line_color, width=ctx.line_width + 1)

    north_end = (station_b[0], station_b[1] - 82.0)
    _draw_arrow(ctx, station_b, north_end, fill=ctx.guide_color, width=max(2, ctx.line_width - 1))
    label_bboxes["north"] = _draw_label(ctx, (north_end[0], north_end[1] - 15), "N", font=ctx.small_font)

    _draw_angle_arc(ctx, center=station_b, bearing_a=0, bearing_b=int(problem.known_bearing), radius=43.0, color=ctx.secondary_accent_color)
    _draw_angle_arc(ctx, center=station_b, bearing_a=int(problem.known_bearing), bearing_b=int(problem.answer), radius=61.0, color=ctx.accent_color)
    known_mid = _direction_endpoint(station_b, int(problem.known_bearing), 72.0)
    target_mid = _direction_endpoint(station_b, int(problem.answer), 84.0)
    label_bboxes["known_bearing"] = _draw_label(ctx, (known_mid[0] + 18.0, known_mid[1] - 6.0), f"{problem.known_bearing}{DEGREE_SYMBOL}", font=ctx.small_font)
    label_bboxes["target"] = _draw_label(ctx, (target_mid[0] + 16.0, target_mid[1] - 4.0), "?", font=ctx.font, fill=ctx.accent_color)

    turn_text = f"turn {problem.turn_angle}{DEGREE_SYMBOL} {problem.turn_direction}"
    label_bboxes["turn"] = _draw_label(ctx, (station_b[0] + 128.0, station_b[1] + 35.0), turn_text, font=ctx.small_font)

    note_x0, note_y0 = float(ctx.width) - 320.0, float(ctx.height) - 151.0
    note_bbox = (note_x0, note_y0, float(ctx.width) - 80.0, float(ctx.height) - 72.0)
    ctx.draw.rounded_rectangle(note_bbox, radius=8, fill=ctx.panel_alt_fill, outline=ctx.secondary_color, width=2)
    _draw_label(ctx, (note_x0 + 16.0, note_y0 + 20.0), "Traverse note", font=ctx.tiny_font, anchor="lm")
    _draw_label(ctx, (note_x0 + 16.0, note_y0 + 48.0), f"{labels[0]}{labels[1]} bearing {problem.known_bearing}{DEGREE_SYMBOL}", font=ctx.tiny_font, anchor="lm")
    _draw_label(ctx, (note_x0 + 16.0, note_y0 + 70.0), f"{labels[1]}{labels[2]} bearing ?", font=ctx.tiny_font, anchor="lm")

    target_direction = _direction_endpoint(station_b, int(problem.answer), 76.0)
    annotation = {
        "station_a": station_a,
        "station_b": station_b,
        "reference_north": north_end,
        "target_direction": target_direction,
        "turn_vertex": station_b,
    }
    entities = (
        {"id": "station_a", "type": "survey_station", "label": labels[0], "point": _point_to_list(station_a)},
        {"id": "station_b", "type": "survey_station", "label": labels[1], "point": _point_to_list(station_b)},
        {"id": "station_c", "type": "survey_station", "label": labels[2], "point": _point_to_list(station_c)},
    )
    return _RenderedSurveyScene(
        image=ctx.image,
        annotation_keyed_points=dict(annotation),
        annotation_roles=_CLOSED_ANNOTATION_KEYS,
        scene_entities=entities,
        label_bboxes=dict(label_bboxes),
        render_map={
            "station_points": {
                labels[0]: _point_to_list(station_a),
                labels[1]: _point_to_list(station_b),
                labels[2]: _point_to_list(station_c),
            },
            "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
            "field_note_bbox": bbox_to_list(note_bbox),
            "panel_bbox": bbox_to_list(panel),
        },
        witness={
            "survey_query_family": "closed_traverse_missing_bearing",
            "station_labels": list(labels),
            "known_bearing": int(problem.known_bearing),
            "turn_angle": int(problem.turn_angle),
            "turn_direction": str(problem.turn_direction),
            "target_bearing": int(problem.answer),
        },
    )

def _note_center(note_bbox: BBox) -> Point:
    return ((float(note_bbox[0]) + float(note_bbox[2])) / 2.0, (float(note_bbox[1]) + float(note_bbox[3])) / 2.0)

def _draw_note_box(ctx: _RenderContext, bbox: BBox, lines: Sequence[str]) -> Dict[str, BBox]:
    ctx.draw.rounded_rectangle(bbox, radius=8, fill=ctx.panel_alt_fill, outline=ctx.secondary_color, width=2)
    line_bboxes: Dict[str, BBox] = {}
    row_gap = 24.0 if len(lines) <= 4 else 21.0
    for row, text in enumerate(lines):
        y = float(bbox[1]) + 20.0 + row * row_gap
        line_bboxes[f"note_{row}"] = _draw_label(ctx, (float(bbox[0]) + 16.0, y), text, font=ctx.tiny_font, anchor="lm")
    return line_bboxes

def _draw_staff(ctx: _RenderContext, base: Point, *, height: float = 86.0) -> BBox:
    x, y = float(base[0]), float(base[1])
    ctx.draw.line([(x, y), (x, y - height)], fill=ctx.secondary_color, width=max(2, ctx.line_width - 1))
    tick_count = 5
    for tick in range(tick_count):
        ty = y - (height * tick / float(tick_count - 1))
        ctx.draw.line([(x - 8.0, ty), (x + 8.0, ty)], fill=ctx.secondary_color, width=1)
    return pad_bbox((x - 10.0, y - height, x + 10.0, y), 4.0, width=ctx.width, height=ctx.height)

def _render_leveling_station_scene(
    ctx: _RenderContext,
    problem: _ResolvedElevationProblem,
    *,
    instance_seed: int,
) -> _RenderedSurveyScene:
    if problem.backsight is None or problem.foresight is None or problem.height_of_instrument is None:
        raise ValueError("leveling station elevation query requires backsight and foresight")
    rng = spawn_rng(int(instance_seed), f"{ELEVATION_NAMESPACE}.leveling.layout")
    labels = problem.station_labels
    panel = (52.0, 48.0, float(ctx.width) - 52.0, float(ctx.height) - 48.0)
    ctx.draw.rounded_rectangle(panel, radius=10, fill=ctx.panel_fill, outline=ctx.line_color, width=ctx.line_width)

    reference_station = (
        float(ctx.width) * 0.25 + rng.uniform(-16.0, 16.0),
        float(ctx.height) * 0.68 + rng.uniform(-10.0, 10.0),
    )
    target_station = (
        float(ctx.width) * 0.66 + rng.uniform(-16.0, 16.0),
        float(ctx.height) * 0.63 + rng.uniform(-12.0, 12.0),
    )
    instrument = (
        (reference_station[0] + target_station[0]) / 2.0 + rng.uniform(-10.0, 10.0),
        min(reference_station[1], target_station[1]) - 62.0 + rng.uniform(-5.0, 5.0),
    )
    sight_y = instrument[1] - 48.0
    sight_left = (reference_station[0], sight_y)
    sight_right = (target_station[0], sight_y)

    label_bboxes: Dict[str, BBox] = {}
    terrain_points = [
        (reference_station[0] - 70.0, reference_station[1] + 12.0),
        (reference_station[0], reference_station[1]),
        (instrument[0], instrument[1] + 34.0),
        (target_station[0], target_station[1]),
        (target_station[0] + 75.0, target_station[1] + 8.0),
    ]
    ctx.draw.line(terrain_points, fill=ctx.guide_color, width=max(2, ctx.line_width - 1))
    label_bboxes[labels[0]] = _draw_station(ctx, reference_station, labels[0], label_offset=(-22.0, -18.0))
    label_bboxes[labels[1]] = _draw_station(ctx, target_station, labels[1], label_offset=(24.0, -18.0))
    _draw_staff(ctx, reference_station, height=92.0)
    _draw_staff(ctx, target_station, height=92.0)
    ctx.draw.polygon(
        [
            (instrument[0], instrument[1] - 18.0),
            (instrument[0] - 24.0, instrument[1] + 18.0),
            (instrument[0] + 24.0, instrument[1] + 18.0),
        ],
        fill=ctx.panel_alt_fill,
        outline=ctx.line_color,
    )
    ctx.draw.line([(instrument[0], instrument[1] + 18.0), (instrument[0], instrument[1] + 58.0)], fill=ctx.line_color, width=2)
    ctx.draw.line(
        [sight_left, sight_right],
        fill=ctx.secondary_accent_color,
        width=max(2, ctx.line_width - 1),
    )
    measurement_mid = ((sight_left[0] + sight_right[0]) / 2.0, sight_y)
    label_bboxes["level_line"] = _draw_label(ctx, (measurement_mid[0], measurement_mid[1] - 16.0), "level line", font=ctx.tiny_font)

    label_bboxes["known_elevation"] = _draw_label(
        ctx,
        (reference_station[0] - 22.0, reference_station[1] + 31.0),
        f"Elev {problem.reference_elevation}",
        font=ctx.tiny_font,
    )
    label_bboxes["target_unknown"] = _draw_label(
        ctx,
        (target_station[0] + 26.0, target_station[1] + 31.0),
        "Elev ?",
        font=ctx.tiny_font,
        fill=ctx.accent_color,
    )

    note_bbox = (float(ctx.width) - 315.0, 70.0, float(ctx.width) - 70.0, 190.0)
    note_bboxes = _draw_note_box(
        ctx,
        note_bbox,
        (
            "Level field note",
            f"{labels[0]} elev {problem.reference_elevation}",
            f"backsight {problem.backsight}",
            f"foresight {problem.foresight}",
            f"{labels[1]} elev ?",
        ),
    )
    label_bboxes.update(note_bboxes)

    annotation = {
        "reference_station": reference_station,
        "target_station": target_station,
        "measurement_line": measurement_mid,
        "field_note_region": _note_center(note_bbox),
    }
    entities = (
        {
            "id": "reference_station",
            "type": "survey_station",
            "label": labels[0],
            "point": _point_to_list(reference_station),
            "elevation": int(problem.reference_elevation),
        },
        {
            "id": "target_station",
            "type": "survey_station",
            "label": labels[1],
            "point": _point_to_list(target_station),
            "elevation": int(problem.target_elevation),
        },
    )
    return _RenderedSurveyScene(
        image=ctx.image,
        annotation_keyed_points=dict(annotation),
        annotation_roles=_ELEVATION_ANNOTATION_KEYS,
        scene_entities=entities,
        label_bboxes=dict(label_bboxes),
        render_map={
            "station_points": {
                labels[0]: _point_to_list(reference_station),
                labels[1]: _point_to_list(target_station),
            },
            "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
            "field_note_bbox": bbox_to_list(note_bbox),
            "measurement_line_bbox": bbox_to_list(
                bbox_from_points((sight_left, sight_right), width=ctx.width, height=ctx.height, pad=6.0)
            ),
            "panel_bbox": bbox_to_list(panel),
        },
        witness={
            "survey_query_family": "leveling_station_elevation",
            "station_labels": list(labels),
            "reference_elevation": int(problem.reference_elevation),
            "backsight": int(problem.backsight),
            "foresight": int(problem.foresight),
            "height_of_instrument": int(problem.height_of_instrument),
            "target_elevation": int(problem.target_elevation),
        },
    )

def _render_slope_elevation_scene(
    ctx: _RenderContext,
    problem: _ResolvedElevationProblem,
    *,
    instance_seed: int,
) -> _RenderedSurveyScene:
    if problem.slope_distance is None or problem.rise_per_20 is None or problem.total_rise is None:
        raise ValueError("slope elevation query requires distance and grade")
    rng = spawn_rng(int(instance_seed), f"{ELEVATION_NAMESPACE}.slope.layout")
    labels = problem.station_labels
    panel = (52.0, 48.0, float(ctx.width) - 52.0, float(ctx.height) - 48.0)
    ctx.draw.rounded_rectangle(panel, radius=10, fill=ctx.panel_fill, outline=ctx.line_color, width=ctx.line_width)

    reference_station = (
        float(ctx.width) * 0.24 + rng.uniform(-15.0, 15.0),
        float(ctx.height) * 0.68 + rng.uniform(-8.0, 8.0),
    )
    vertical_shift = -58.0 if int(problem.total_rise) >= 0 else 58.0
    target_station = (
        float(ctx.width) * 0.68 + rng.uniform(-14.0, 14.0),
        reference_station[1] + vertical_shift + rng.uniform(-6.0, 6.0),
    )
    label_bboxes: Dict[str, BBox] = {}
    terrain = [
        (reference_station[0] - 70.0, reference_station[1] + 18.0),
        reference_station,
        target_station,
        (target_station[0] + 72.0, target_station[1] + 15.0),
    ]
    ctx.draw.line(terrain, fill=ctx.guide_color, width=max(2, ctx.line_width - 1))
    label_bboxes[labels[0]] = _draw_station(ctx, reference_station, labels[0], label_offset=(-22.0, -18.0))
    label_bboxes[labels[1]] = _draw_station(ctx, target_station, labels[1], label_offset=(24.0, -18.0))
    _draw_arrow(ctx, reference_station, target_station, fill=ctx.line_color, width=ctx.line_width + 1)
    measurement_mid = ((reference_station[0] + target_station[0]) / 2.0, (reference_station[1] + target_station[1]) / 2.0)
    label_bboxes["distance"] = _draw_label(
        ctx,
        (measurement_mid[0], measurement_mid[1] - 28.0),
        f"{problem.slope_distance} units",
        font=ctx.small_font,
    )
    grade_word = "rise" if int(problem.rise_per_20) >= 0 else "fall"
    grade_value = abs(int(problem.rise_per_20))
    label_bboxes["grade"] = _draw_label(
        ctx,
        (measurement_mid[0] + 10.0, measurement_mid[1] + 33.0),
        f"{grade_word} {grade_value} per 20",
        font=ctx.small_font,
    )
    label_bboxes["known_elevation"] = _draw_label(
        ctx,
        (reference_station[0] - 24.0, reference_station[1] + 31.0),
        f"Elev {problem.reference_elevation}",
        font=ctx.tiny_font,
    )
    label_bboxes["target_unknown"] = _draw_label(
        ctx,
        (target_station[0] + 26.0, target_station[1] + 31.0),
        "Elev ?",
        font=ctx.tiny_font,
        fill=ctx.accent_color,
    )

    note_bbox = (float(ctx.width) - 318.0, 70.0, float(ctx.width) - 70.0, 176.0)
    note_bboxes = _draw_note_box(
        ctx,
        note_bbox,
        (
            "Slope field note",
            f"{labels[0]} elev {problem.reference_elevation}",
            f"{labels[0]} to {labels[1]}: {problem.slope_distance} units",
            f"{grade_word} {grade_value} per 20 units",
            f"{labels[1]} elev ?",
        ),
    )
    label_bboxes.update(note_bboxes)

    annotation = {
        "reference_station": reference_station,
        "target_station": target_station,
        "measurement_line": measurement_mid,
        "field_note_region": _note_center(note_bbox),
    }
    entities = (
        {
            "id": "reference_station",
            "type": "survey_station",
            "label": labels[0],
            "point": _point_to_list(reference_station),
            "elevation": int(problem.reference_elevation),
        },
        {
            "id": "target_station",
            "type": "survey_station",
            "label": labels[1],
            "point": _point_to_list(target_station),
            "elevation": int(problem.target_elevation),
        },
    )
    return _RenderedSurveyScene(
        image=ctx.image,
        annotation_keyed_points=dict(annotation),
        annotation_roles=_ELEVATION_ANNOTATION_KEYS,
        scene_entities=entities,
        label_bboxes=dict(label_bboxes),
        render_map={
            "station_points": {
                labels[0]: _point_to_list(reference_station),
                labels[1]: _point_to_list(target_station),
            },
            "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
            "field_note_bbox": bbox_to_list(note_bbox),
            "measurement_line_bbox": bbox_to_list(
                bbox_from_points((reference_station, target_station), width=ctx.width, height=ctx.height, pad=6.0)
            ),
            "panel_bbox": bbox_to_list(panel),
        },
        witness={
            "survey_query_family": "slope_distance_elevation_change",
            "station_labels": list(labels),
            "reference_elevation": int(problem.reference_elevation),
            "slope_distance": int(problem.slope_distance),
            "rise_per_20": int(problem.rise_per_20),
            "total_rise": int(problem.total_rise),
            "target_elevation": int(problem.target_elevation),
        },
    )

def _render_scene(ctx: _RenderContext, problem: _ResolvedProblem, *, instance_seed: int) -> _RenderedSurveyScene:
    if problem.query_id == "bearing_from_back_bearing":
        return _render_back_bearing_scene(ctx, problem, instance_seed=int(instance_seed))
    if problem.query_id == "closed_traverse_missing_bearing":
        return _render_closed_traverse_scene(ctx, problem, instance_seed=int(instance_seed))
    raise ValueError(f"unsupported survey traverse query_id: {problem.query_id}")

def _render_elevation_scene(
    ctx: _RenderContext,
    problem: _ResolvedElevationProblem,
    *,
    instance_seed: int,
) -> _RenderedSurveyScene:
    if problem.query_id == "leveling_station_elevation":
        return _render_leveling_station_scene(ctx, problem, instance_seed=int(instance_seed))
    if problem.query_id == "slope_distance_elevation_change":
        return _render_slope_elevation_scene(ctx, problem, instance_seed=int(instance_seed))
    raise ValueError(f"unsupported survey elevation query_id: {problem.query_id}")

def _map_unit_points(points: Sequence[Tuple[int, int]], box: BBox) -> Dict[Tuple[int, int], Point]:
    x0, y0, x1, y1 = [float(value) for value in box]
    xs = [int(point[0]) for point in points]
    ys = [int(point[1]) for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(1, max_x - min_x)
    span_y = max(1, max_y - min_y)
    scale = min((x1 - x0) / float(span_x + 1), (y1 - y0) / float(span_y + 1))
    used_w = float(span_x) * scale
    used_h = float(span_y) * scale
    left = x0 + ((x1 - x0) - used_w) / 2.0
    bottom = y0 + ((y1 - y0) + used_h) / 2.0
    mapped: Dict[Tuple[int, int], Point] = {}
    for unit_x, unit_y in points:
        mapped[(int(unit_x), int(unit_y))] = (
            left + (int(unit_x) - min_x) * scale,
            bottom - (int(unit_y) - min_y) * scale,
        )
    return mapped

def _draw_coordinate_grid(ctx: _RenderContext, box: BBox, *, max_x: int, max_y: int) -> BBox:
    x0, y0, x1, y1 = [float(value) for value in box]
    ctx.draw.rectangle(box, fill=ctx.panel_alt_fill, outline=ctx.secondary_color, width=2)
    grid_color = ctx.guide_color
    for col in range(max(1, int(max_x)) + 1):
        x = x0 + (x1 - x0) * col / float(max(1, int(max_x)))
        ctx.draw.line([(x, y0), (x, y1)], fill=grid_color, width=1)
    for row in range(max(1, int(max_y)) + 1):
        y = y1 - (y1 - y0) * row / float(max(1, int(max_y)))
        ctx.draw.line([(x0, y), (x1, y)], fill=grid_color, width=1)
    ctx.draw.line([(x0, y1), (x1, y1)], fill=ctx.line_color, width=max(2, ctx.line_width - 1))
    ctx.draw.line([(x0, y0), (x0, y1)], fill=ctx.line_color, width=max(2, ctx.line_width - 1))
    _draw_label(ctx, (x1 - 12.0, y1 + 20.0), "x", font=ctx.tiny_font)
    _draw_label(ctx, (x0 - 14.0, y0 + 12.0), "y", font=ctx.tiny_font)
    return pad_bbox(box, 8.0, width=ctx.width, height=ctx.height)

def _render_coordinate_traverse_area_scene(
    ctx: _RenderContext,
    problem: _ResolvedAreaProblem,
    *,
    instance_seed: int,
) -> _RenderedSurveyAreaScene:
    rng = spawn_rng(int(instance_seed), f"{AREA_NAMESPACE}.coordinate.layout")
    labels = problem.station_labels
    points = tuple(problem.coordinate_points)
    panel = (52.0, 48.0, float(ctx.width) - 52.0, float(ctx.height) - 48.0)
    ctx.draw.rounded_rectangle(panel, radius=10, fill=ctx.panel_fill, outline=ctx.line_color, width=ctx.line_width)
    grid_box = (
        86.0 + rng.uniform(-7.0, 7.0),
        102.0 + rng.uniform(-5.0, 5.0),
        502.0 + rng.uniform(-7.0, 7.0),
        455.0 + rng.uniform(-5.0, 5.0),
    )
    max_x = max(point[0] for point in points)
    max_y = max(point[1] for point in points)
    area_reference_bbox = _draw_coordinate_grid(ctx, grid_box, max_x=max_x, max_y=max_y)
    point_map = _map_unit_points(points, grid_box)
    pixel_points = [point_map[point] for point in points]

    ctx.draw.polygon(pixel_points, fill=ctx.panel_alt_fill, outline=ctx.accent_color)
    ctx.draw.line(pixel_points + [pixel_points[0]], fill=ctx.accent_color, width=ctx.line_width + 1)
    label_bboxes: Dict[str, BBox] = {}
    for idx, (label, unit_point, pixel_point) in enumerate(zip(labels, points, pixel_points)):
        label_bboxes[label] = _draw_station(
            ctx,
            pixel_point,
            label,
            label_offset=(-18.0, -18.0) if idx in {0, 3} else (20.0, -18.0),
        )
        _draw_label(
            ctx,
            (pixel_point[0] + (24.0 if idx in {1, 2} else -24.0), pixel_point[1] + 19.0),
            f"({unit_point[0]},{unit_point[1]})",
            font=ctx.tiny_font,
        )

    note_bbox = (548.0, 83.0, float(ctx.width) - 68.0, 220.0)
    note_lines = ["Coordinate field note"] + [
        f"{label}: E {point[0]}, N {point[1]}" for label, point in zip(labels, points)
    ]
    label_bboxes.update(_draw_note_box(ctx, note_bbox, note_lines))
    _draw_label(ctx, (float(note_bbox[0]) + 16.0, float(note_bbox[3]) + 30.0), "Area = ?", font=ctx.small_font, anchor="lm", fill=ctx.accent_color)

    traverse_bbox = bbox_from_points(pixel_points, width=ctx.width, height=ctx.height, pad=14.0)
    annotation_bboxes = {
        "traverse_region": traverse_bbox,
        "field_note_region": pad_bbox(note_bbox, 4.0, width=ctx.width, height=ctx.height),
        "area_reference_region": area_reference_bbox,
    }
    entities = tuple(
        {
            "id": f"station_{label.lower()}",
            "type": "survey_station",
            "label": label,
            "coordinate": [int(point[0]), int(point[1])],
            "point": _point_to_list(pixel),
        }
        for label, point, pixel in zip(labels, points, pixel_points)
    )
    return _RenderedSurveyAreaScene(
        image=ctx.image,
        annotation_bboxes=dict(annotation_bboxes),
        scene_entities=entities,
        label_bboxes=dict(label_bboxes),
        render_map={
            "station_points": {label: _point_to_list(pixel) for label, pixel in zip(labels, pixel_points)},
            "coordinate_points": {label: [int(point[0]), int(point[1])] for label, point in zip(labels, points)},
            "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
            "field_note_bbox": bbox_to_list(note_bbox),
            "traverse_bbox": bbox_to_list(traverse_bbox),
            "area_reference_bbox": bbox_to_list(area_reference_bbox),
            "panel_bbox": bbox_to_list(panel),
        },
        witness={
            "survey_query_family": "coordinate_traverse_area",
            "station_labels": list(labels),
            "coordinate_points": [[int(x), int(y)] for x, y in points],
            "area_value": int(problem.answer),
        },
    )

def _render_offset_trapezoid_area_scene(
    ctx: _RenderContext,
    problem: _ResolvedAreaProblem,
    *,
    instance_seed: int,
) -> _RenderedSurveyAreaScene:
    rng = spawn_rng(int(instance_seed), f"{AREA_NAMESPACE}.offset.layout")
    labels = problem.station_labels
    chainages = tuple(int(value) for value in problem.chainages)
    offsets = tuple(int(value) for value in problem.offsets)
    panel = (52.0, 48.0, float(ctx.width) - 52.0, float(ctx.height) - 48.0)
    ctx.draw.rounded_rectangle(panel, radius=10, fill=ctx.panel_fill, outline=ctx.line_color, width=ctx.line_width)
    map_box = (
        86.0 + rng.uniform(-6.0, 6.0),
        115.0 + rng.uniform(-5.0, 5.0),
        510.0 + rng.uniform(-6.0, 6.0),
        445.0 + rng.uniform(-5.0, 5.0),
    )
    x0, y0, x1, y1 = [float(value) for value in map_box]
    baseline_y = y1 - 44.0
    max_chain = max(chainages)
    max_offset = max(offsets)
    x_scale = (x1 - x0 - 28.0) / float(max_chain)
    y_scale = (baseline_y - y0 - 28.0) / float(max(1, max_offset))
    baseline_points = [(x0 + 14.0 + chain * x_scale, baseline_y) for chain in chainages]
    offset_points = [(base[0], baseline_y - offset * y_scale) for base, offset in zip(baseline_points, offsets)]
    shape_points = [baseline_points[0], baseline_points[-1]] + list(reversed(offset_points))

    ctx.draw.rectangle(map_box, fill=ctx.panel_alt_fill, outline=ctx.secondary_color, width=2)
    ctx.draw.line([baseline_points[0], baseline_points[-1]], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.polygon(shape_points, fill=ctx.panel_alt_fill, outline=ctx.accent_color)
    ctx.draw.line(offset_points, fill=ctx.accent_color, width=ctx.line_width + 1)
    label_bboxes: Dict[str, BBox] = {}
    for label, chain, offset, base, top in zip(labels, chainages, offsets, baseline_points, offset_points):
        ctx.draw.line([base, top], fill=ctx.secondary_accent_color, width=max(2, ctx.line_width - 1))
        ctx.draw.ellipse([top[0] - 5.0, top[1] - 5.0, top[0] + 5.0, top[1] + 5.0], fill=ctx.accent_color, outline=ctx.line_color)
        label_bboxes[label] = _draw_label(ctx, (top[0], top[1] - 18.0), label, font=ctx.small_font)
        _draw_label(ctx, (base[0], baseline_y + 17.0), str(chain), font=ctx.tiny_font)
        _draw_label(ctx, (top[0] + 22.0, (base[1] + top[1]) / 2.0), str(offset), font=ctx.tiny_font)
    label_bboxes["baseline"] = _draw_label(ctx, ((baseline_points[0][0] + baseline_points[-1][0]) / 2.0, baseline_y + 42.0), "baseline chainage", font=ctx.tiny_font)

    note_bbox = (548.0, 83.0, float(ctx.width) - 68.0, 220.0)
    note_lines = ["Offset field note"] + [
        f"{label}: ch {chain}, off {offset}" for label, chain, offset in zip(labels, chainages, offsets)
    ]
    label_bboxes.update(_draw_note_box(ctx, note_bbox, note_lines))
    _draw_label(ctx, (float(note_bbox[0]) + 16.0, float(note_bbox[3]) + 30.0), "Area = ?", font=ctx.small_font, anchor="lm", fill=ctx.accent_color)

    traverse_bbox = bbox_from_points(shape_points, width=ctx.width, height=ctx.height, pad=14.0)
    area_reference_bbox = bbox_from_points(baseline_points, width=ctx.width, height=ctx.height, pad=18.0)
    annotation_bboxes = {
        "traverse_region": traverse_bbox,
        "field_note_region": pad_bbox(note_bbox, 4.0, width=ctx.width, height=ctx.height),
        "area_reference_region": area_reference_bbox,
    }
    entities = tuple(
        {
            "id": f"offset_{label.lower()}",
            "type": "survey_offset",
            "label": label,
            "chainage": int(chain),
            "offset": int(offset),
            "point": _point_to_list(top),
        }
        for label, chain, offset, top in zip(labels, chainages, offsets, offset_points)
    )
    return _RenderedSurveyAreaScene(
        image=ctx.image,
        annotation_bboxes=dict(annotation_bboxes),
        scene_entities=entities,
        label_bboxes=dict(label_bboxes),
        render_map={
            "offset_points": {label: _point_to_list(point) for label, point in zip(labels, offset_points)},
            "baseline_points": {label: _point_to_list(point) for label, point in zip(labels, baseline_points)},
            "chainages": {label: int(value) for label, value in zip(labels, chainages)},
            "offsets": {label: int(value) for label, value in zip(labels, offsets)},
            "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
            "field_note_bbox": bbox_to_list(note_bbox),
            "traverse_bbox": bbox_to_list(traverse_bbox),
            "area_reference_bbox": bbox_to_list(area_reference_bbox),
            "panel_bbox": bbox_to_list(panel),
        },
        witness={
            "survey_query_family": "offset_trapezoid_area",
            "station_labels": list(labels),
            "chainages": [int(value) for value in chainages],
            "offsets": [int(value) for value in offsets],
            "area_value": int(problem.answer),
        },
    )

def _render_area_scene(
    ctx: _RenderContext,
    problem: _ResolvedAreaProblem,
    *,
    instance_seed: int,
) -> _RenderedSurveyAreaScene:
    if problem.query_id == "coordinate_traverse_area":
        return _render_coordinate_traverse_area_scene(ctx, problem, instance_seed=int(instance_seed))
    if problem.query_id == "offset_trapezoid_area":
        return _render_offset_trapezoid_area_scene(ctx, problem, instance_seed=int(instance_seed))
    raise ValueError(f"unsupported survey area query_id: {problem.query_id}")


__all__ = [
    '_make_context',
    '_text_bbox',
    '_draw_label',
    '_draw_arrow',
    '_draw_station',
    '_draw_angle_arc',
    '_direction_endpoint',
    '_ray_length_inside_box',
    '_render_back_bearing_scene',
    '_render_closed_traverse_scene',
    '_note_center',
    '_draw_note_box',
    '_draw_staff',
    '_render_leveling_station_scene',
    '_render_slope_elevation_scene',
    '_render_scene',
    '_render_elevation_scene',
    '_map_unit_points',
    '_draw_coordinate_grid',
    '_render_coordinate_traverse_area_scene',
    '_render_offset_trapezoid_area_scene',
    '_render_area_scene',
]
