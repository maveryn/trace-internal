"""Shared rendering helpers for two-view 3D object-scene panels."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from .....core.visual.background import make_background_canvas
from ....shared.text_legibility import draw_text_traced
from ....shared.text_rendering import load_font
from ...shared.object_scene import _RenderParams, render_object_scene_3d


REFERENCE_VIEW_KEY = "reference_view"
CANDIDATE_VIEW_KEY = "candidate_view"
MULTIVIEW_PANEL_ROOM_EXTENT = 2.55


def offset_bbox(bbox: Sequence[float], *, dx: float, dy: float) -> List[float]:
    return [
        round(float(bbox[0]) + float(dx), 3),
        round(float(bbox[1]) + float(dy), 3),
        round(float(bbox[2]) + float(dx), 3),
        round(float(bbox[3]) + float(dy), 3),
    ]


def offset_point(point: Sequence[float], *, dx: float, dy: float) -> List[float]:
    return [round(float(point[0]) + float(dx), 3), round(float(point[1]) + float(dy), 3)]


def offset_point_map(mapping: Mapping[str, Sequence[float]], *, dx: float, dy: float) -> Dict[str, List[float]]:
    return {str(key): offset_point(value, dx=dx, dy=dy) for key, value in mapping.items()}


def _offset_map(mapping: Mapping[str, Sequence[float]], *, dx: float, dy: float) -> Dict[str, List[float]]:
    return {str(key): offset_bbox(value, dx=dx, dy=dy) for key, value in mapping.items()}


def _offset_centers(mapping: Mapping[str, Sequence[float]], *, dx: float, dy: float) -> Dict[str, List[float]]:
    return {
        str(key): [round(float(value[0]) + float(dx), 3), round(float(value[1]) + float(dy), 3)]
        for key, value in mapping.items()
    }


def offset_entities(entities: Sequence[Mapping[str, Any]], *, dx: float, dy: float, view_key: str) -> List[Dict[str, Any]]:
    shifted: List[Dict[str, Any]] = []
    for entity in entities:
        updated = dict(entity)
        updated["entity_id"] = f"{view_key}:{entity['entity_id']}"
        updated["bbox_px"] = offset_bbox(entity["bbox_px"], dx=dx, dy=dy)
        attrs = dict(updated.get("attrs", {})) if isinstance(updated.get("attrs"), Mapping) else {}
        attrs["view_key"] = str(view_key)
        updated["attrs"] = attrs
        shifted.append(updated)
    return list(shifted)


def panel_layout(render_params: _RenderParams) -> Dict[str, Dict[str, int]]:
    outer_margin = max(18, min(32, int(round(render_params.canvas_width * 0.018))))
    gutter = max(24, min(42, int(round(render_params.canvas_width * 0.022))))
    label_height = 38
    panel_width = int((int(render_params.canvas_width) - (2 * outer_margin) - gutter) // 2)
    panel_height = int(int(render_params.canvas_height) - (2 * outer_margin) - label_height)
    panel_y = int(outer_margin + label_height)
    left_x = int(outer_margin)
    right_x = int(outer_margin + panel_width + gutter)
    return {
        REFERENCE_VIEW_KEY: {"x": left_x, "y": panel_y, "width": panel_width, "height": panel_height},
        CANDIDATE_VIEW_KEY: {"x": right_x, "y": panel_y, "width": panel_width, "height": panel_height},
    }


def panel_render_params(render_params: _RenderParams, panel: Mapping[str, int]) -> _RenderParams:
    return replace(
        render_params,
        canvas_width=int(panel["width"]),
        canvas_height=int(panel["height"]),
        scene_margin_left_px=32,
        scene_margin_right_px=32,
        scene_margin_top_px=28,
        scene_margin_bottom_px=32,
        room_extent=min(float(render_params.room_extent), MULTIVIEW_PANEL_ROOM_EXTENT),
        label_font_size_px=max(22, int(render_params.label_font_size_px)),
        full_bleed_floor=True,
    )


def draw_panel_label(draw: ImageDraw.ImageDraw, *, text: str, x: float, y: float) -> None:
    font = load_font(22, bold=True)
    draw_text_traced(
        draw,
        (float(x), float(y)),
        str(text),
        font=font,
        fill=(28, 34, 43),
        stroke_width=2,
        stroke_fill=(255, 255, 255),
        role="readout",
        required=False,
    )


def render_multiview_view_dataset(dataset: Mapping[str, Any], *, view_key: str) -> Dict[str, Any]:
    view = dataset["views"][str(view_key)]
    return {
        "query_id": str(dataset["query_id"]),
        "scene_variant": str(dataset["scene_variant"]),
        "point_specs": [dict(spec) for spec in view["point_specs"]],
        "context_object_specs": [dict(spec) for spec in view["context_object_specs"]],
        "answer_label": str(dataset["answer_label"]),
        "answer_point_id": str(dataset["answer_point_id"]),
        "camera": dict(view["camera"]),
        "projection_frame": dict(view["projection_frame"]),
    }


def render_multiview_scene(
    *,
    dataset: Mapping[str, Any],
    render_params: _RenderParams,
    instance_seed: int,
    params: Mapping[str, Any],
    background_defaults: Mapping[str, Any],
) -> Tuple[Image.Image, Dict[str, Any], Dict[str, Any]]:
    layout = panel_layout(render_params)
    panel_params = panel_render_params(render_params, layout[REFERENCE_VIEW_KEY])
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=background_defaults,
    )
    composite = background.convert("RGB")
    draw = ImageDraw.Draw(composite)
    rendered_by_view = {}
    view_background_meta = {}
    for view_key, seed_offset in ((REFERENCE_VIEW_KEY, 17), (CANDIDATE_VIEW_KEY, 29)):
        panel = layout[str(view_key)]
        panel_background, panel_background_meta = make_background_canvas(
            canvas_width=int(panel["width"]),
            canvas_height=int(panel["height"]),
            instance_seed=int(instance_seed) + int(seed_offset),
            params=params,
            default_config=background_defaults,
        )
        view_dataset = render_multiview_view_dataset(dataset, view_key=str(view_key))
        rendered = render_object_scene_3d(
            panel_background,
            dataset=view_dataset,
            render_params=panel_params,
            draw_candidate_labels=str(view_key) == CANDIDATE_VIEW_KEY,
            highlight_object_ids=(
                [str(dataset["target_object_id"])] if str(view_key) == REFERENCE_VIEW_KEY else []
            ),
            annotation_label=str(dataset["answer_label"]),
        )
        composite.paste(rendered.image, (int(panel["x"]), int(panel["y"])))
        draw.rectangle(
            [
                int(panel["x"]),
                int(panel["y"]),
                int(panel["x"]) + int(panel["width"]),
                int(panel["y"]) + int(panel["height"]),
            ],
            outline=(57, 67, 80),
            width=2,
        )
        rendered_by_view[str(view_key)] = rendered
        view_background_meta[str(view_key)] = dict(panel_background_meta)

    draw_panel_label(
        draw,
        text="View 1",
        x=float(layout[REFERENCE_VIEW_KEY]["x"]),
        y=float(layout[REFERENCE_VIEW_KEY]["y"] - 31),
    )
    draw_panel_label(
        draw,
        text="View 2",
        x=float(layout[CANDIDATE_VIEW_KEY]["x"]),
        y=float(layout[CANDIDATE_VIEW_KEY]["y"] - 31),
    )
    background_meta = dict(background_meta)
    background_meta["view_panels"] = dict(view_background_meta)
    return composite, dict(rendered_by_view), dict(background_meta)


def render_two_view_object_scene(
    *,
    dataset: Mapping[str, Any],
    render_params: _RenderParams,
    instance_seed: int,
    params: Mapping[str, Any],
    background_defaults: Mapping[str, Any],
    panel_params: _RenderParams,
    view_dataset_builder: Callable[[Mapping[str, Any], str], Mapping[str, Any]],
    render_view_options: Callable[[str], Mapping[str, Any]],
) -> Tuple[Image.Image, Dict[str, Any], Dict[str, Any]]:
    layout = panel_layout(render_params)
    background, background_meta = make_background_canvas(
        canvas_width=int(render_params.canvas_width),
        canvas_height=int(render_params.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=background_defaults,
    )
    composite = background.convert("RGB")
    draw = ImageDraw.Draw(composite)
    rendered_by_view = {}
    view_background_meta = {}

    for view_key, seed_offset in ((REFERENCE_VIEW_KEY, 17), (CANDIDATE_VIEW_KEY, 29)):
        panel = layout[str(view_key)]
        panel_background, panel_background_meta = make_background_canvas(
            canvas_width=int(panel["width"]),
            canvas_height=int(panel["height"]),
            instance_seed=int(instance_seed) + int(seed_offset),
            params=params,
            default_config=background_defaults,
        )
        rendered = render_object_scene_3d(
            panel_background,
            dataset=dict(view_dataset_builder(dataset, str(view_key))),
            render_params=panel_params,
            **dict(render_view_options(str(view_key))),
        )
        composite.paste(rendered.image, (int(panel["x"]), int(panel["y"])))
        draw.rectangle(
            [
                int(panel["x"]),
                int(panel["y"]),
                int(panel["x"]) + int(panel["width"]),
                int(panel["y"]) + int(panel["height"]),
            ],
            outline=(57, 67, 80),
            width=2,
        )
        rendered_by_view[str(view_key)] = rendered
        view_background_meta[str(view_key)] = dict(panel_background_meta)

    draw_panel_label(
        draw,
        text="View 1",
        x=float(layout[REFERENCE_VIEW_KEY]["x"]),
        y=float(layout[REFERENCE_VIEW_KEY]["y"] - 31),
    )
    draw_panel_label(
        draw,
        text="View 2",
        x=float(layout[CANDIDATE_VIEW_KEY]["x"]),
        y=float(layout[CANDIDATE_VIEW_KEY]["y"] - 31),
    )

    background_meta = dict(background_meta)
    background_meta["view_panels"] = dict(view_background_meta)
    return composite, dict(rendered_by_view), dict(background_meta)


def shift_render_maps(rendered_scene, *, panel: Mapping[str, int]) -> Dict[str, Any]:
    dx = float(panel["x"])
    dy = float(panel["y"])
    panel_bbox = [
        float(panel["x"]),
        float(panel["y"]),
        float(panel["x"] + panel["width"]),
        float(panel["y"] + panel["height"]),
    ]
    return {
        "panel_bbox_px": list(panel_bbox),
        "scene_bbox_px": offset_bbox(rendered_scene.scene_bbox_px, dx=dx, dy=dy),
        "room_bbox_px": offset_bbox(rendered_scene.room_bbox_px, dx=dx, dy=dy),
        "point_bboxes_px": _offset_map(rendered_scene.point_bboxes_px, dx=dx, dy=dy),
        "point_centers_px": _offset_centers(rendered_scene.point_centers_px, dx=dx, dy=dy),
        "object_bboxes_px": _offset_map(rendered_scene.object_bboxes_px, dx=dx, dy=dy),
        "object_centers_px": _offset_centers(rendered_scene.object_centers_px, dx=dx, dy=dy),
        "context_object_bboxes_px": _offset_map(rendered_scene.context_object_bboxes_px, dx=dx, dy=dy),
        "context_object_centers_px": _offset_centers(rendered_scene.context_object_centers_px, dx=dx, dy=dy),
    }


__all__ = [
    "CANDIDATE_VIEW_KEY",
    "REFERENCE_VIEW_KEY",
    "draw_panel_label",
    "offset_bbox",
    "offset_entities",
    "offset_point",
    "offset_point_map",
    "panel_layout",
    "panel_render_params",
    "render_multiview_scene",
    "render_two_view_object_scene",
    "shift_render_maps",
]
