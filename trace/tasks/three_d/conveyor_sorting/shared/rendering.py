"""Rendering helpers for synthetic 3D conveyor sorting scenes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.tasks.shared.text_rendering import load_font
from trace.tasks.three_d.shared.camera_projection import (
    CameraSpec,
    ProjectionFrame,
    project_xy,
)
from trace.tasks.three_d.shared.object_rendering import (
    ThreeDObjectSpec,
    ThreeDRenderContext,
    render_three_d_object,
)
from trace.tasks.three_d.shared.object_scene_rendering import _bbox_union, _draw_line

from .state import SEGMENT_KEYS, SEGMENT_LABELS


@dataclass(frozen=True)
class RenderedConveyorSorting:
    """Rendered conveyor sorting scene with projected object geometry."""

    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    conveyor_bbox_px: List[float]
    object_bboxes_px: Dict[str, List[float]]
    object_centers_px: Dict[str, List[float]]
    target_object_bboxes_px: Dict[str, List[float]]
    target_object_centers_px: Dict[str, List[float]]
    lane_bboxes_px: Dict[str, List[float]]
    segment_bboxes_px: Dict[str, List[float]]


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


def _segment_polygon_world(record: Mapping[str, Any]) -> list[tuple[float, float, float]]:
    x0, y0, x1, y1 = (float(value) for value in record["world_bbox_xy"])
    z = 0.035
    return [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]


def _draw_segment_label(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center_xy: Sequence[float],
    fill: Tuple[int, int, int],
) -> List[float]:
    font = load_font(18, bold=True)
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
    text_w = int(text_bbox[2] - text_bbox[0])
    text_h = int(text_bbox[3] - text_bbox[1])
    x = float(center_xy[0]) - text_w * 0.5
    y = float(center_xy[1]) - text_h * 0.5
    draw.text((x, y), str(text), font=font, fill=fill, stroke_width=2, stroke_fill=(248, 250, 252))
    return [round(x, 3), round(y, 3), round(x + text_w, 3), round(y + text_h, 3)]


def _draw_conveyor_belts(
    image: Image.Image,
    *,
    dataset: Mapping[str, Any],
    camera: CameraSpec,
    frame: ProjectionFrame,
) -> tuple[Image.Image, List[float], Dict[str, List[float]], Dict[str, List[float]], List[Dict[str, Any]]]:
    """Draw belt lanes, segment boxes, labels, and scanner context.

    Conveyor segment polygons are projected from world-space lane records so the
    visible labels and the object placement metadata share one geometric frame.
    """

    draw = ImageDraw.Draw(image)
    lane_bboxes: Dict[str, List[float]] = {}
    segment_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    conveyor_bboxes: list[list[float]] = []
    segment_fill = {
        "input": (203, 217, 226),
        "scan": (211, 225, 235),
        "output": (199, 214, 223),
    }
    segment_outline = (88, 104, 120)
    label_fill = (48, 58, 70)
    for record in dataset["segment_records"]:
        lane_label = str(record["lane_label"])
        segment_key = str(record["segment_key"])
        segment_label = str(record["segment_label"])
        polygon_world = _segment_polygon_world(record)
        polygon_screen = [project_xy(point, camera, frame) for point in polygon_world]
        draw.polygon(polygon_screen, fill=segment_fill.get(segment_key, (205, 218, 228)))
        draw.line([*polygon_screen, polygon_screen[0]], fill=segment_outline, width=2)
        segment_bbox = _projected_bbox(polygon_screen)
        segment_id = f"lane_{lane_label}_{segment_key}"
        segment_bboxes[str(segment_id)] = list(segment_bbox)
        conveyor_bboxes.append(segment_bbox)
        center_world = (
            (float(record["world_bbox_xy"][0]) + float(record["world_bbox_xy"][2])) * 0.5,
            (float(record["world_bbox_xy"][1]) + float(record["world_bbox_xy"][3])) * 0.5,
            0.055,
        )
        center = project_xy(center_world, camera, frame)
        text_bbox = _draw_segment_label(draw, text=str(segment_label), center_xy=center, fill=label_fill)
        entities.append(
            {
                "entity_id": str(segment_id),
                "entity_type": "three_d_conveyor_segment",
                "bbox_px": list(segment_bbox),
                "attrs": {
                    "lane_label": str(lane_label),
                    "segment_key": str(segment_key),
                    "segment_label": str(segment_label),
                    "label_bbox_px": list(text_bbox),
                    "world_bbox_xy": list(record["world_bbox_xy"]),
                },
            }
        )
    for lane in dataset["lane_records"]:
        lane_label = str(lane["lane_label"])
        lane_segments = [
            segment_bboxes[f"lane_{lane_label}_{segment_key}"]
            for segment_key in SEGMENT_KEYS
        ]
        lane_bbox = _bbox_union(*lane_segments)
        lane_bboxes[str(lane_label)] = list(lane_bbox)
        x0, y0, x1, y1 = lane_bbox
        badge = [x0 - 26.0, y0 + 8.0, x0 + 18.0, y0 + 48.0]
        draw.rounded_rectangle(tuple(badge), radius=7, fill=(35, 46, 60), outline=(255, 255, 255), width=2)
        font = load_font(22, bold=True)
        draw.text((badge[0] + 11.0, badge[1] + 6.0), lane_label, font=font, fill=(255, 255, 255))
        entities.append(
            {
                "entity_id": f"lane_{lane_label}",
                "entity_type": "three_d_conveyor_lane",
                "bbox_px": list(lane_bbox),
                "attrs": {"lane_label": str(lane_label), "badge_bbox_px": list(badge)},
            }
        )
    conveyor_bbox = _bbox_union(*conveyor_bboxes) if conveyor_bboxes else [0.0, 0.0, float(image.width), float(image.height)]
    scan_boxes = [bbox for key, bbox in segment_bboxes.items() if key.endswith("_scan")]
    if scan_boxes:
        scanner_bbox = _bbox_union(*scan_boxes)
        sx0, sy0, sx1, sy1 = scanner_bbox
        _draw_line(draw, (sx0, sy0 - 18.0), (sx0, sy1 + 18.0), fill=(66, 115, 165), width=4)
        _draw_line(draw, (sx1, sy0 - 18.0), (sx1, sy1 + 18.0), fill=(66, 115, 165), width=4)
        _draw_line(draw, (sx0, sy0 - 18.0), (sx1, sy0 - 18.0), fill=(66, 115, 165), width=4)
        entities.append(
            {
                "entity_id": "scanner_frame",
                "entity_type": "three_d_conveyor_scanner_frame",
                "bbox_px": [round(sx0, 3), round(sy0 - 18.0, 3), round(sx1, 3), round(sy1 + 18.0, 3)],
                "attrs": {"segment_key": "scan"},
            }
        )
    return image, list(conveyor_bbox), lane_bboxes, segment_bboxes, entities


def _draw_object_shadow(draw: ImageDraw.ImageDraw, bbox: Sequence[float]) -> None:
    x0, y0, x1, y1 = (float(value) for value in bbox)
    width = max(6.0, x1 - x0)
    height = max(5.0, y1 - y0)
    shadow = [
        x0 + width * 0.12,
        y1 - height * 0.18,
        x1 - width * 0.12,
        y1 + height * 0.08,
    ]
    draw.ellipse(tuple(shadow), fill=(92, 102, 112))


def render_conveyor_sorting(
    background: Image.Image,
    *,
    dataset: Mapping[str, Any],
    render_params: Any,
) -> RenderedConveyorSorting:
    """Render one conveyor sorting scene and project object boxes."""

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, int(image.width), int(image.height)), fill=(244, 247, 249))
    camera = _camera_from_dataset(dataset)
    frame = _frame_from_dataset(dataset)
    image, conveyor_bbox, lane_bboxes, segment_bboxes, entities = _draw_conveyor_belts(
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
                floor_rgb=(244, 247, 249),
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
                    "lane_label": str(spec["lane_label"]),
                    "segment_key": str(spec["segment_key"]),
                    "segment_label": str(spec["segment_label"]),
                    "matches_query": bool(spec.get("matches_query", False)),
                },
            }
        )
        if str(object_id) in set(str(value) for value in dataset["target_object_ids"]):
            target_bboxes[str(object_id)] = list(bbox)
            target_centers[str(object_id)] = list(center)
    scene_bbox = _bbox_union(conveyor_bbox, *object_bboxes.values()) if object_bboxes else conveyor_bbox
    return RenderedConveyorSorting(
        image=image,
        entities=entities,
        scene_bbox_px=list(scene_bbox),
        conveyor_bbox_px=list(conveyor_bbox),
        object_bboxes_px=dict(object_bboxes),
        object_centers_px=dict(object_centers),
        target_object_bboxes_px=dict(target_bboxes),
        target_object_centers_px=dict(target_centers),
        lane_bboxes_px=dict(lane_bboxes),
        segment_bboxes_px=dict(segment_bboxes),
    )


__all__ = ["RenderedConveyorSorting", "render_conveyor_sorting"]
