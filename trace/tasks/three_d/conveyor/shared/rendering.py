"""Rendering helpers for straight 3D conveyor belt scenes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.tasks.three_d.shared.camera_projection import CameraSpec, ProjectionFrame, project_xy
from trace.tasks.three_d.shared.object_rendering import (
    ThreeDObjectSpec,
    ThreeDRenderContext,
    render_three_d_object,
)
from trace.tasks.three_d.shared.object_scene_rendering import _bbox_union, _draw_line

from .sampling import LAYOUT_HORIZONTAL, LAYOUT_VERTICAL
from .state import (
    HORIZONTAL_LANE_CENTER_BY_KEY,
    HORIZONTAL_LANE_KEYS,
    HORIZONTAL_LANE_LENGTH,
    LANE_HALF_WIDTH,
    LANE_LABELS,
    VERTICAL_LANE_CENTER_BY_KEY,
    VERTICAL_LANE_KEYS,
    VERTICAL_LANE_LENGTH,
)


FLOOR_RGB = (242, 246, 248)


@dataclass(frozen=True)
class RenderedConveyor:
    """Rendered straight conveyor scene with projected object geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    conveyor_bbox_px: List[float]
    object_bboxes_px: Dict[str, List[float]]
    object_centers_px: Dict[str, List[float]]
    target_object_bboxes_px: Dict[str, List[float]]
    target_object_centers_px: Dict[str, List[float]]
    belt_bboxes_px: Dict[str, List[float]]


def _camera_from_dataset(dataset: Mapping[str, Any]) -> CameraSpec:
    raw = dict(dataset["camera"])
    return CameraSpec(
        camera_position=tuple(float(value) for value in raw["camera_position"]),
        target=tuple(float(value) for value in raw["target"]),
        right=tuple(float(value) for value in raw["right"]),
        up=tuple(float(value) for value in raw["up"]),
        forward=tuple(float(value) for value in raw["forward"]),
        yaw_degrees=float(raw["yaw_degrees"]),
        pitch_degrees=float(raw["pitch_degrees"]),
        distance=float(raw["distance"]),
    )


def _frame_from_dataset(dataset: Mapping[str, Any]) -> ProjectionFrame:
    raw = dict(dataset["projection_frame"])
    return ProjectionFrame(
        scale=float(raw["scale"]),
        center_x=float(raw["center_x"]),
        center_y=float(raw["center_y"]),
        normalized_center_u=float(raw["normalized_center_u"]),
        normalized_center_v=float(raw["normalized_center_v"]),
    )


def _projected_bbox(points: Sequence[Sequence[float]]) -> List[float]:
    return [
        round(float(min(point[0] for point in points)), 3),
        round(float(min(point[1] for point in points)), 3),
        round(float(max(point[0] for point in points)), 3),
        round(float(max(point[1] for point in points)), 3),
    ]


def _lane_center_value(layout_orientation: str, lane_key: str) -> float:
    if str(layout_orientation) == LAYOUT_HORIZONTAL:
        return float(HORIZONTAL_LANE_CENTER_BY_KEY[str(lane_key)])
    return float(VERTICAL_LANE_CENTER_BY_KEY[str(lane_key)])


def _lane_polygon_world(layout_orientation: str, lane_key: str) -> list[tuple[float, float, float]]:
    half_width = float(LANE_HALF_WIDTH)
    if str(layout_orientation) == LAYOUT_HORIZONTAL:
        half_length = 0.5 * float(HORIZONTAL_LANE_LENGTH)
        x0, x1 = -half_length, half_length
        y = _lane_center_value(str(layout_orientation), str(lane_key))
        return [(x0, y - half_width, 0.03), (x1, y - half_width, 0.03), (x1, y + half_width, 0.03), (x0, y + half_width, 0.03)]
    half_length = 0.5 * float(VERTICAL_LANE_LENGTH)
    y0, y1 = -half_length, half_length
    x = _lane_center_value(str(layout_orientation), str(lane_key))
    return [(x - half_width, y0, 0.03), (x + half_width, y0, 0.03), (x + half_width, y1, 0.03), (x - half_width, y1, 0.03)]


def _draw_arrow(
    draw: ImageDraw.ImageDraw,
    *,
    start_xy: Sequence[float],
    end_xy: Sequence[float],
    fill: Tuple[int, int, int],
) -> None:
    sx, sy = float(start_xy[0]), float(start_xy[1])
    ex, ey = float(end_xy[0]), float(end_xy[1])
    _draw_line(draw, (sx, sy), (ex, ey), fill=fill, width=3)
    angle = math.atan2(ey - sy, ex - sx)
    length = 10.0
    spread = 0.58
    left = (
        ex - length * math.cos(angle - spread),
        ey - length * math.sin(angle - spread),
    )
    right = (
        ex - length * math.cos(angle + spread),
        ey - length * math.sin(angle + spread),
    )
    draw.polygon([(ex, ey), left, right], fill=fill)


def _draw_lane_belt(
    draw: ImageDraw.ImageDraw,
    *,
    lane_key: str,
    layout_orientation: str,
    camera: CameraSpec,
    frame: ProjectionFrame,
    fill: Tuple[int, int, int],
    outline: Tuple[int, int, int],
) -> tuple[List[float], Dict[str, Any]]:
    """Draw one lane from the same projected rectangle used for lane metadata.

    The lane bbox and entity attrs are derived from the projected belt polygon,
    keeping prompt lane positions, visual belt geometry, and trace records in
    one coordinate contract without drawing lane labels on the image.
    """

    polygon_world = _lane_polygon_world(str(layout_orientation), str(lane_key))
    polygon_screen = [project_xy(point, camera, frame) for point in polygon_world]
    draw.polygon(polygon_screen, fill=fill)
    draw.line([*polygon_screen, polygon_screen[0]], fill=outline, width=3)

    if str(layout_orientation) == LAYOUT_HORIZONTAL:
        y = _lane_center_value(str(layout_orientation), str(lane_key))
        for x in (-2.65, 0.0, 2.65):
            _draw_arrow(
                draw,
                start_xy=project_xy((x - 0.38, y, 0.065), camera, frame),
                end_xy=project_xy((x + 0.38, y, 0.065), camera, frame),
                fill=(60, 74, 88),
            )
    else:
        x = _lane_center_value(str(layout_orientation), str(lane_key))
        for y in (-2.75, 0.0, 2.75):
            _draw_arrow(
                draw,
                start_xy=project_xy((x, y - 0.34, 0.065), camera, frame),
                end_xy=project_xy((x, y + 0.34, 0.065), camera, frame),
                fill=(60, 74, 88),
            )

    bbox = _projected_bbox(polygon_screen)
    entity = {
        "entity_id": f"belt_{lane_key}",
        "entity_type": "three_d_conveyor_belt",
        "bbox_px": list(bbox),
        "attrs": {
            "belt_key": str(lane_key),
            "belt_label": str(LANE_LABELS[str(lane_key)]),
            "lane_key": str(lane_key),
            "lane_label": str(LANE_LABELS[str(lane_key)]),
            "layout_orientation": str(layout_orientation),
        },
    }
    return list(bbox), entity


def _draw_conveyor_belts(
    image: Image.Image,
    *,
    dataset: Mapping[str, Any],
    camera: CameraSpec,
    frame: ProjectionFrame,
) -> tuple[Image.Image, List[float], Dict[str, List[float]], List[Dict[str, Any]]]:
    draw = ImageDraw.Draw(image)
    layout_orientation = str(dataset["layout_orientation"])
    lane_keys = HORIZONTAL_LANE_KEYS if layout_orientation == LAYOUT_HORIZONTAL else VERTICAL_LANE_KEYS
    fill_cycle = ((194, 211, 224), (205, 219, 230), (188, 205, 219))
    outlines = (76, 92, 110)
    belt_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    for index, lane_key in enumerate(lane_keys):
        bbox, entity = _draw_lane_belt(
            draw,
            lane_key=str(lane_key),
            layout_orientation=str(layout_orientation),
            camera=camera,
            frame=frame,
            fill=fill_cycle[index % len(fill_cycle)],
            outline=outlines,
        )
        belt_bboxes[str(lane_key)] = list(bbox)
        entities.append(dict(entity))
    conveyor_bbox = _bbox_union(*belt_bboxes.values())
    return image, list(conveyor_bbox), belt_bboxes, entities


def _draw_object_shadow(draw: ImageDraw.ImageDraw, bbox: Sequence[float]) -> None:
    x0, y0, x1, y1 = (float(value) for value in bbox)
    width = max(6.0, x1 - x0)
    height = max(5.0, y1 - y0)
    shadow = [
        x0 + width * 0.10,
        y1 - height * 0.20,
        x1 - width * 0.10,
        y1 + height * 0.07,
    ]
    draw.ellipse(tuple(shadow), fill=(95, 105, 115))


def render_conveyor(
    background: Image.Image,
    *,
    dataset: Mapping[str, Any],
    render_params: Any,
) -> RenderedConveyor:
    """Render one straight conveyor scene and project object boxes."""

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, int(image.width), int(image.height)), fill=FLOOR_RGB)
    camera = _camera_from_dataset(dataset)
    frame = _frame_from_dataset(dataset)
    image, conveyor_bbox, belt_bboxes, entities = _draw_conveyor_belts(
        image,
        dataset=dataset,
        camera=camera,
        frame=frame,
    )
    draw = ImageDraw.Draw(image)
    object_specs = [dict(spec) for spec in dataset["object_specs"]]
    ordered_specs = sorted(
        object_specs,
        key=lambda item: float(item.get("camera_distance", 0.0)) + float(item.get("render_order_bias", 0.0)),
        reverse=True,
    )
    object_bboxes: Dict[str, List[float]] = {}
    object_centers: Dict[str, List[float]] = {}
    target_bboxes: Dict[str, List[float]] = {}
    target_centers: Dict[str, List[float]] = {}
    for spec in ordered_specs:
        estimated_bbox = [
            float(spec["screen_xy"][0]) - 20.0,
            float(spec["screen_xy"][1]) - 12.0,
            float(spec["screen_xy"][0]) + 20.0,
            float(spec["screen_xy"][1]) + 14.0,
        ]
        _draw_object_shadow(draw, estimated_bbox)
    for spec in ordered_specs:
        fill = tuple(int(channel) for channel in spec["fill_rgb"])
        rendered = render_three_d_object(
            ThreeDObjectSpec.from_mapping(spec, object_type_key="shape_type", default_renderer_id="object_scene_shape"),
            ThreeDRenderContext(
                draw=draw,
                camera=camera,
                frame=frame,
                render_params=render_params,
                fill_rgb=fill,
                scene_variant=str(dataset["scene_variant"]),
                floor_rgb=FLOOR_RGB,
            ),
        )
        object_id = str(spec["object_id"])
        bbox = [round(float(value), 3) for value in rendered.bbox_xyxy]
        center = [round(float(spec["screen_xy"][0]), 3), round(float(spec["screen_xy"][1]), 3)]
        object_bboxes[object_id] = list(bbox)
        object_centers[object_id] = list(center)
        entities.append(
            {
                "entity_id": object_id,
                "entity_type": "three_d_conveyor_object",
                "bbox_px": list(bbox),
                "attrs": {
                    "shape_type": str(spec["shape_type"]),
                    "object_name": str(spec["object_name"]),
                    "color_name": str(spec["color_name"]),
                    "lane_key": str(spec["lane_key"]),
                    "lane_label": str(spec["lane_label"]),
                    "belt_key": str(spec["belt_key"]),
                    "belt_label": str(spec["belt_label"]),
                    "matches_query": bool(spec.get("matches_query", False)),
                },
            }
        )
        if str(object_id) in set(str(value) for value in dataset["target_object_ids"]):
            target_bboxes[str(object_id)] = list(bbox)
            target_centers[str(object_id)] = list(center)
    scene_bbox = _bbox_union(conveyor_bbox, *object_bboxes.values()) if object_bboxes else conveyor_bbox
    return RenderedConveyor(
        image=image,
        entities=entities,
        scene_bbox_px=list(scene_bbox),
        conveyor_bbox_px=list(conveyor_bbox),
        object_bboxes_px=dict(object_bboxes),
        object_centers_px=dict(object_centers),
        target_object_bboxes_px=dict(target_bboxes),
        target_object_centers_px=dict(target_centers),
        belt_bboxes_px=dict(belt_bboxes),
    )


__all__ = ["RenderedConveyor", "render_conveyor"]
