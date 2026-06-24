"""Warehouse shelf-level scene rendering helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

from PIL import Image, ImageDraw

from ....shared.color_distance import coerce_rgb as _rgb
from ...shared.object_rendering import ThreeDObjectSpec, ThreeDRenderContext, render_three_d_object
from ...shared.object_scene import (
    _CameraSpec,
    _ProjectionFrame,
    _canvas_floor_polygon_xy,
    _grid_values_for_range,
    _polygon_axis_line_segment,
    _project_xy,
)
from ...shared.object_scene_rendering import _draw_line
from ...shared.warehouse_object_rendering import _draw_ground_shadow, _fill_for_object
from .state import (
    _WarehouseRenderParams,
    _camera_from_dataset,
    _frame_from_dataset,
    _projected_bbox,
    _scene_palette,
)
from .components import _draw_shelf_rack_object


@dataclass(frozen=True)
class _RenderedShelfScene:
    image: Image.Image
    entities: List[Dict[str, Any]]
    scene_bbox_px: List[float]
    warehouse_bbox_px: List[float]
    object_bboxes_px: Dict[str, List[float]]
    object_centers_px: Dict[str, List[float]]
    rack_bboxes_px: Dict[str, List[float]]
    rack_centers_px: Dict[str, List[float]]
    shelf_item_bboxes_px: Dict[str, List[float]]
    shelf_item_centers_px: Dict[str, List[float]]
    target_item_bboxes_px: Dict[str, List[float]]
    target_item_centers_px: Dict[str, List[float]]
    annotation_bboxes: List[List[float]]
    annotation_entity_ids: List[str]


def _draw_shelf_floor(
    image: Image.Image,
    *,
    camera: _CameraSpec,
    frame: _ProjectionFrame,
    render_params: _WarehouseRenderParams,
    scene_variant: str,
    dataset: Mapping[str, Any],
) -> Tuple[Image.Image, List[float], List[Dict[str, Any]]]:
    """Draw the shelf-count floor, aisle, and context polygons."""
    draw = ImageDraw.Draw(image)
    floor_rgb, grid_rgb, aisle_rgb, shelf_zone_rgb = _scene_palette(str(scene_variant), render_params)
    draw.rectangle((0, 0, int(render_params.canvas_width), int(render_params.canvas_height)), fill=floor_rgb)
    floor_polygon_xy = _canvas_floor_polygon_xy(camera=camera, frame=frame, render_params=render_params)
    grid_world_bbox = None
    if floor_polygon_xy:
        min_x = min(float(point[0]) for point in floor_polygon_xy)
        max_x = max(float(point[0]) for point in floor_polygon_xy)
        min_y = min(float(point[1]) for point in floor_polygon_xy)
        max_y = max(float(point[1]) for point in floor_polygon_xy)
        grid_world_bbox = [round(min_x, 4), round(min_y, 4), round(max_x, 4), round(max_y, 4)]
        for value in _grid_values_for_range(min_y, max_y, float(render_params.grid_step)):
            segment = _polygon_axis_line_segment(floor_polygon_xy, axis="y", value=float(value))
            if segment is None:
                continue
            _draw_line(
                draw,
                _project_xy((segment[0][0], segment[0][1], 0.0), camera, frame),
                _project_xy((segment[1][0], segment[1][1], 0.0), camera, frame),
                fill=grid_rgb,
                width=render_params.line_width_px,
            )
        for value in _grid_values_for_range(min_x, max_x, float(render_params.grid_step)):
            segment = _polygon_axis_line_segment(floor_polygon_xy, axis="x", value=float(value))
            if segment is None:
                continue
            _draw_line(
                draw,
                _project_xy((segment[0][0], segment[0][1], 0.0), camera, frame),
                _project_xy((segment[1][0], segment[1][1], 0.0), camera, frame),
                fill=grid_rgb,
                width=render_params.line_width_px,
            )
    for polygon_world in dataset["rack_zone_polygons_world"]:
        draw.polygon([_project_xy(point, camera, frame) for point in polygon_world], fill=shelf_zone_rgb)
    draw.polygon([_project_xy(point, camera, frame) for point in dataset["main_aisle_polygon_world"]], fill=aisle_rgb)
    stage_bbox = [0.0, 0.0, float(render_params.canvas_width), float(render_params.canvas_height)]
    return image, list(stage_bbox), [
        {
            "entity_id": "warehouse_floor",
            "entity_type": "three_d_warehouse_floor",
            "bbox_px": list(stage_bbox),
            "attrs": {
                "scene_variant": str(scene_variant),
                "full_bleed_floor": True,
                "grid_mode": "screen_ray_floor_plane",
                "grid_world_bbox": list(grid_world_bbox) if grid_world_bbox is not None else None,
                "floor_rgb": list(floor_rgb),
            },
        },
        {
            "entity_id": "warehouse_main_aisle",
            "entity_type": "three_d_warehouse_main_aisle",
            "bbox_px": _projected_bbox([_project_xy(point, camera, frame) for point in dataset["main_aisle_polygon_world"]]),
            "attrs": {"aisle_heading": str(dataset["aisle_heading"])},
        },
    ]


def render_warehouse_shelf_level_count_scene_3d(
    background: Image.Image,
    *,
    dataset: Mapping[str, Any],
    render_params: _WarehouseRenderParams,
) -> _RenderedShelfScene:
    """Render colored racks and project shelf-item annotations."""
    image = background.convert("RGB")
    camera = _camera_from_dataset(dataset)
    frame = _frame_from_dataset(dataset)
    scene_variant = str(dataset["scene_variant"])
    image, warehouse_bbox, entities = _draw_shelf_floor(
        image,
        camera=camera,
        frame=frame,
        render_params=render_params,
        scene_variant=scene_variant,
        dataset=dataset,
    )
    draw = ImageDraw.Draw(image)
    rack_specs = [dict(spec) for spec in dataset["rack_specs"]]
    item_specs = [dict(spec) for spec in dataset["shelf_item_specs"]]
    items_by_rack: Dict[str, List[Dict[str, Any]]] = {str(spec["object_id"]): [] for spec in rack_specs}
    for item in item_specs:
        items_by_rack.setdefault(str(item["rack_id"]), []).append(item)

    for rack in sorted(rack_specs, key=lambda item: float(item["camera_distance"]), reverse=True):
        _draw_ground_shadow(draw, rack, camera=camera, frame=frame)

    object_bboxes: Dict[str, List[float]] = {}
    object_centers: Dict[str, List[float]] = {}
    rack_bboxes: Dict[str, List[float]] = {}
    rack_centers: Dict[str, List[float]] = {}
    shelf_item_bboxes: Dict[str, List[float]] = {}
    shelf_item_centers: Dict[str, List[float]] = {}
    target_item_bboxes: Dict[str, List[float]] = {}
    target_item_centers: Dict[str, List[float]] = {}

    for rack in sorted(rack_specs, key=lambda item: float(item["camera_distance"]), reverse=True):
        rack_fill = _fill_for_object(rack, scene_variant=scene_variant)
        rack_bbox = _draw_shelf_rack_object(draw, rack, camera=camera, frame=frame, fill=rack_fill)
        rack_center = [round(float(rack["screen_xy"][0]), 3), round(float(rack["screen_xy"][1]), 3)]
        rack_bboxes[str(rack["object_id"])] = list(rack_bbox)
        rack_centers[str(rack["object_id"])] = list(rack_center)
        object_bboxes[str(rack["object_id"])] = list(rack_bbox)
        object_centers[str(rack["object_id"])] = list(rack_center)
        entities.append(
            {
                "entity_id": str(rack["object_id"]),
                "entity_type": "three_d_warehouse_shelf_rack",
                "bbox_px": list(rack_bbox),
                "attrs": {
                    "object_type": "shelf_rack",
                    "object_name": "shelf rack",
                    "object_role": str(rack["object_role"]),
                    "rack_index": int(rack["rack_index"]),
                    "rack_color_name": str(rack["rack_color_name"]),
                    "rack_color_label": str(rack["rack_color_label"]),
                    "shelf_frame_rgb": list(rack["shelf_frame_rgb"]),
                    "is_target_rack": bool(rack["is_target_rack"]),
                    "shelf_style": str(rack["shelf_style"]),
                    "shelf_levels": int(rack["shelf_levels"]),
                    "shelf_level_names": list(rack["shelf_level_names"]),
                    "shelf_load_count": 0,
                    "fill_rgb": [int(channel) for channel in rack_fill],
                    "world_xyz": list(rack["world_xyz"]),
                    "base_xyz": list(rack["base_xyz"]),
                    "dimensions_xyz": list(rack["dimensions_xyz"]),
                    "screen_xy": list(rack_center),
                    "camera_distance": float(rack["camera_distance"]),
                },
            }
        )
        for item in sorted(items_by_rack.get(str(rack["object_id"]), []), key=lambda spec: float(spec["camera_distance"]), reverse=True):
            item_fill = _rgb(item.get("fill_rgb"), _fill_for_object(item, scene_variant=scene_variant))
            rendered_item = render_three_d_object(
                ThreeDObjectSpec.from_mapping(
                    item,
                    object_type_key="object_type",
                    default_renderer_id="warehouse_object",
                    role=str(item.get("object_role", "warehouse_shelf_item")),
                    source_entity_type="three_d_warehouse_shelf_item",
                ),
                ThreeDRenderContext(
                    draw=draw,
                    camera=camera,
                    frame=frame,
                    render_params=render_params,
                    fill_rgb=item_fill,
                    scene_variant=str(scene_variant),
                ),
            )
            item_bbox = list(rendered_item.bbox_xyxy)
            item_center = [round(float(item["screen_xy"][0]), 3), round(float(item["screen_xy"][1]), 3)]
            object_bboxes[str(item["object_id"])] = list(item_bbox)
            object_centers[str(item["object_id"])] = list(item_center)
            shelf_item_bboxes[str(item["object_id"])] = list(item_bbox)
            shelf_item_centers[str(item["object_id"])] = list(item_center)
            if bool(item.get("matches_query", False)):
                target_item_bboxes[str(item["object_id"])] = list(item_bbox)
                target_item_centers[str(item["object_id"])] = list(item_center)
            entities.append(
                {
                    "entity_id": str(item["object_id"]),
                    "entity_type": "three_d_warehouse_shelf_item",
                    "bbox_px": list(item_bbox),
                    "attrs": {
                        "object_type": str(item["object_type"]),
                        "object_name": str(item["object_name"]),
                        "object_role": str(item["object_role"]),
                        "rack_id": str(item["rack_id"]),
                        "rack_color_name": str(item["rack_color_name"]),
                        "rack_color_label": str(item["rack_color_label"]),
                        "shelf_level": str(item["shelf_level"]),
                        "shelf_level_index": int(item["shelf_level_index"]),
                        "is_countable_object": bool(item["is_countable_object"]),
                        "matches_query": bool(item["matches_query"]),
                        "count_role": str(item["count_role"]),
                        "fill_rgb": [int(channel) for channel in item_fill],
                        "world_xyz": list(item["world_xyz"]),
                        "base_xyz": list(item["base_xyz"]),
                        "dimensions_xyz": list(item["dimensions_xyz"]),
                        "screen_xy": list(item_center),
                        "camera_distance": float(item["camera_distance"]),
                        "object_record": dict(rendered_item.object_record),
                    },
                }
            )

    target_ids = [str(value) for value in dataset["target_item_ids"]]
    annotation_bboxes = [list(target_item_bboxes[object_id]) for object_id in target_ids]
    scene_bboxes = [list(warehouse_bbox)] + [list(bbox) for bbox in object_bboxes.values()]
    scene_bbox = [
        round(float(min(bbox[0] for bbox in scene_bboxes)), 3),
        round(float(min(bbox[1] for bbox in scene_bboxes)), 3),
        round(float(max(bbox[2] for bbox in scene_bboxes)), 3),
        round(float(max(bbox[3] for bbox in scene_bboxes)), 3),
    ]
    return _RenderedShelfScene(
        image=image,
        entities=list(entities),
        scene_bbox_px=list(scene_bbox),
        warehouse_bbox_px=list(warehouse_bbox),
        object_bboxes_px=dict(object_bboxes),
        object_centers_px=dict(object_centers),
        rack_bboxes_px=dict(rack_bboxes),
        rack_centers_px=dict(rack_centers),
        shelf_item_bboxes_px=dict(shelf_item_bboxes),
        shelf_item_centers_px=dict(shelf_item_centers),
        target_item_bboxes_px=dict(target_item_bboxes),
        target_item_centers_px=dict(target_item_centers),
        annotation_bboxes=list(annotation_bboxes),
        annotation_entity_ids=list(target_ids),
    )
