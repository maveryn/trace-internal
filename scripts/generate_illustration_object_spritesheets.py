#!/usr/bin/env python3
"""Generate review spritesheets for illustration-domain object vocabularies."""

from __future__ import annotations

import json
from pathlib import Path
import random
import sys
import types
from typing import Any, Callable, Mapping, Sequence

from PIL import Image, ImageDraw


def _install_trace_tasks_namespace() -> None:
    """Avoid importing the repo-wide task registry for review-asset generation."""

    if "trace.tasks" in sys.modules:
        return
    repo_root = Path(__file__).resolve().parents[1]
    tasks_module = types.ModuleType("trace.tasks")
    tasks_module.__path__ = [str(repo_root / "trace" / "tasks")]  # type: ignore[attr-defined]
    sys.modules["trace.tasks"] = tasks_module


_install_trace_tasks_namespace()

from trace.tasks.shared.text_rendering import load_font
from trace.tasks.illustrations.counterfactual import visible_part_count as cf_visible
from trace.tasks.illustrations.shared import construction_site_rendering as construction
from trace.tasks.illustrations.shared import environment_object_rendering as environment
from trace.tasks.illustrations.indoor_room.shared import rendering as indoor
from trace.tasks.illustrations.shared import library_rendering as library
from trace.tasks.illustrations.shared import object_library
from trace.tasks.illustrations.shared.object_catalog import CatalogEntry, catalog_entries
from trace.tasks.illustrations.shared.object_rendering import render_vector_scene_object
from trace.tasks.illustrations.shared import park_playground_rendering as park
from trace.tasks.illustrations.shared.person_rendering import PERSON_GENDER_IDS, sample_person_gender
from trace.tasks.illustrations.shared import transit_terminal_rendering as transit


OUT_DIR = Path("review/task-reviews/assets/illustrations/object_spritesheets")
SCALE = 2
TILE_W = 238
TILE_H = 194
HEADER_H = 82
BG = (248, 247, 241)
PANEL_BG = (255, 253, 246)
TEXT = (38, 43, 50)
MUTED = (93, 101, 112)


SpriteItem = Mapping[str, Any]
DrawFn = Callable[[ImageDraw.ImageDraw, SpriteItem, tuple[float, float, float, float], random.Random], None]


def _seed(value: str) -> int:
    total = 2166136261
    for char in str(value):
        total ^= ord(char)
        total *= 16777619
        total &= 0xFFFFFFFF
    return total


def _scale_box(box: Sequence[float]) -> tuple[int, int, int, int]:
    return tuple(int(round(float(value) * SCALE)) for value in box)  # type: ignore[return-value]


def _font(size: int, *, bold: bool = False):
    return load_font(int(size) * SCALE, bold=bold)


def _draw_text(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, *, size: int = 12, fill=TEXT, bold: bool = False) -> None:
    draw.text((int(round(xy[0] * SCALE)), int(round(xy[1] * SCALE))), str(text), font=_font(size, bold=bold), fill=tuple(fill))


def _measure(draw: ImageDraw.ImageDraw, text: str, *, size: int = 12, bold: bool = False) -> tuple[float, float]:
    font = _font(size, bold=bold)
    bbox = draw.textbbox((0, 0), str(text), font=font)
    return (float(bbox[2] - bbox[0]) / SCALE, float(bbox[3] - bbox[1]) / SCALE)


def _ellipsize(draw: ImageDraw.ImageDraw, text: str, max_width: float, *, size: int, bold: bool = False) -> str:
    text = str(text)
    if _measure(draw, text, size=size, bold=bold)[0] <= float(max_width):
        return text
    suffix = "..."
    result = text
    while result and _measure(draw, result + suffix, size=size, bold=bold)[0] > float(max_width):
        result = result[:-1]
    return (result or text[:1]) + suffix


def _center_text(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    text: str,
    *,
    size: int = 12,
    fill=TEXT,
    bold: bool = False,
) -> None:
    x0, y0, x1, y1 = [float(v) for v in bbox]
    label = _ellipsize(draw, str(text), x1 - x0 - 8.0, size=size, bold=bold)
    tw, th = _measure(draw, label, size=size, bold=bold)
    _draw_text(draw, (x0 + (x1 - x0 - tw) * 0.5, y0 + (y1 - y0 - th) * 0.5), label, size=size, fill=fill, bold=bold)


def _object_box(bounds: Sequence[float], aspect: float) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = [float(v) for v in bounds]
    avail_w = max(10.0, x1 - x0)
    avail_h = max(10.0, y1 - y0)
    height = min(avail_h, avail_w / max(0.2, float(aspect)))
    width = min(avail_w, height * max(0.2, float(aspect)))
    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)
    return (cx - width * 0.5, cy - height * 0.5, cx + width * 0.5, cy + height * 0.5)


def _make_sheet(
    filename: str,
    *,
    title: str,
    subtitle: str,
    items: Sequence[SpriteItem],
    draw_item: DrawFn,
    cols: int = 4,
    tile_w: int = TILE_W,
    tile_h: int = TILE_H,
) -> dict[str, Any]:
    rows = max(1, (len(items) + int(cols) - 1) // int(cols))
    width = int(cols) * int(tile_w)
    height = HEADER_H + rows * int(tile_h)
    image = Image.new("RGB", (width * SCALE, height * SCALE), BG)
    draw = ImageDraw.Draw(image)
    _draw_text(draw, (22, 18), title, size=24, fill=TEXT, bold=True)
    _draw_text(draw, (22, 50), subtitle, size=12, fill=MUTED, bold=False)
    for index, item in enumerate(items):
        col = index % int(cols)
        row = index // int(cols)
        x = float(col * tile_w)
        y = float(HEADER_H + row * tile_h)
        panel = (x + 10.0, y + 10.0, x + tile_w - 10.0, y + tile_h - 10.0)
        draw.rounded_rectangle(_scale_box(panel), radius=10 * SCALE, fill=PANEL_BG, outline=(218, 214, 202), width=max(1, SCALE))
        group = str(item.get("group", ""))
        if group:
            badge = (panel[0] + 10.0, panel[1] + 10.0, min(panel[2] - 10.0, panel[0] + 16.0 + 7.3 * len(group)), panel[1] + 31.0)
            draw.rounded_rectangle(_scale_box(badge), radius=5 * SCALE, fill=(231, 237, 239), outline=(190, 201, 207), width=max(1, SCALE))
            _center_text(draw, badge, group, size=9, fill=(51, 69, 80), bold=True)
        object_area = (panel[0] + 16.0, panel[1] + 36.0, panel[2] - 16.0, panel[3] - 48.0)
        preview_id = str(item.get("preview_id", item.get("id", index)))
        seed_id = str(item.get("seed_id", preview_id))
        rng = random.Random(_seed(seed_id))
        draw_item(draw, item, object_area, rng)
        public_name = str(item.get("name", item.get("id", "")))
        object_id = str(item.get("display_id", item.get("preview_id", item.get("id", ""))))
        _center_text(draw, (panel[0] + 8.0, panel[3] - 42.0, panel[2] - 8.0, panel[3] - 24.0), public_name, size=12, fill=TEXT, bold=True)
        if object_id and object_id != public_name:
            _center_text(draw, (panel[0] + 8.0, panel[3] - 23.0, panel[2] - 8.0, panel[3] - 8.0), object_id, size=9, fill=MUTED, bold=False)
    output = OUT_DIR / filename
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    image.save(output)
    return {"file": str(output), "title": title, "item_count": len(items)}


def _draw_shared_object(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    object_type = str(item["id"])
    box = _object_box(bounds, object_library.aspect_ratio_for_object(object_type))
    primary, accent = object_library.choose_object_colors(rng, object_type)
    object_library.draw_illustration_object(
        draw,
        object_id=f"sheet_{object_type}",
        object_type=object_type,
        bbox_xyxy=box,
        primary_color_rgb=primary,
        accent_color_rgb=accent,
        style_id="outlined_cartoon",
        render_scale=SCALE,
        gender_id=str(item.get("gender_id", sample_person_gender(rng))) if object_library.family_for_object(object_type) == "person" else None,
    )


def _draw_market_shop(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    raise RuntimeError("urban market preview renderer is no longer active")


def _draw_market_item(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    raise RuntimeError("urban market preview renderer is no longer active")


def _draw_market_customer(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    box = _object_box(bounds, 0.62)
    primary, accent = object_library.choose_object_colors(rng, "pedestrian_with_bag")
    object_library.draw_illustration_object(
        draw,
        object_id="sheet_customer",
        object_type="pedestrian_with_bag",
        bbox_xyxy=box,
        primary_color_rgb=primary,
        accent_color_rgb=accent,
        style_id="outlined_cartoon",
        render_scale=SCALE,
        gender_id=str(item.get("gender_id", sample_person_gender(rng))),
    )


def _draw_library_section(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    spec = library.LibrarySectionSpec(section_key=str(item["id"]), book_specs=())
    library._draw_section_shell(
        draw,
        rng=rng,
        section=spec,
        bbox=(bounds[0], bounds[1] + 2.0, bounds[2], bounds[3] + 10.0),
        row_count=2,
        scale=SCALE,
        section_label_font_family="",
    )


def _draw_library_book(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    color = str(item.get("color", "blue"))
    orientation = str(item.get("orientation", "upright"))
    if orientation == "horizontal":
        box = _object_box(bounds, 2.3)
    else:
        box = _object_box(bounds, 0.36)
    spec = library.LibraryBookSpec(section_key="fiction", color_name=color, orientation=orientation)
    library._draw_book(draw, rng=rng, spec=spec, bbox=box, scale=SCALE)


def _draw_park_equipment(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    equipment_type = str(item["id"])
    render_vector_scene_object(
        draw,
        object_id=f"sheet_{equipment_type}",
        object_type="playground_equipment",
        bbox_xyxy=(bounds[0], bounds[1] + 14.0, bounds[2], bounds[3] + 8.0),
        renderer_id="park_equipment",
        renderer_variant_id=equipment_type,
        semantic_attributes={
            "decor_type": equipment_type,
            "equipment_type": equipment_type,
            "equipment_label": park.park_equipment_display_name(equipment_type),
            "zone": "playground",
        },
        visual_attributes=park._park_equipment_visual_attributes(rng, equipment_type, "outlined_cartoon"),
        role="preview",
        source_entity_type="park_decor",
        render_scale=SCALE,
        style_id="outlined_cartoon",
    )


def _draw_park_activity(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    activity = str(item["id"])
    person_box = _object_box((bounds[0] + 26.0, bounds[1] + 5.0, bounds[2] - 26.0, bounds[3] + 4.0), 0.55)
    park._draw_activity_support(draw, rng=rng, person_id=f"sheet_{activity}", activity=activity, bbox=person_box, scale=SCALE, style_id="outlined_cartoon")
    render_vector_scene_object(
        draw,
        object_id=f"sheet_{activity}",
        object_type="person",
        bbox_xyxy=person_box,
        renderer_id="park_person",
        renderer_variant_id=activity,
        semantic_attributes={"activity": activity, "activity_label": park.park_activity_display_name(activity)},
        visual_attributes={
            "primary_color_rgb": [78, 126, 178],
            "accent_color_rgb": [238, 173, 77],
            "skin_color_rgb": [178, 126, 83],
            "style_id": "outlined_cartoon",
            "gender_id": str(item.get("gender_id", "female" if activity == "sitting" else "male")),
        },
        role="preview",
        source_entity_type="park_person",
        render_scale=SCALE,
        style_id="outlined_cartoon",
    )


def _draw_zone_swatch(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    fills = {
        "playground": (235, 214, 171),
        "picnic": (213, 232, 197),
        "garden": (221, 232, 205),
        "excavation_zone": (225, 205, 167),
        "loading_zone": (222, 217, 200),
        "roadwork_zone": (212, 212, 204),
    }
    fill = fills.get(str(item["id"]), (226, 232, 220))
    draw.rounded_rectangle(_scale_box(bounds), radius=13 * SCALE, fill=fill, outline=(122, 130, 104), width=max(2, SCALE * 2))
    _center_text(draw, bounds, str(item["name"]), size=15, fill=(54, 63, 57), bold=True)


def _draw_transit_luggage(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    luggage_type = str(item["id"])
    aspect = 1.45 if luggage_type == "luggage_cart" else 0.86
    box = _object_box(bounds, aspect)
    render_vector_scene_object(
        draw,
        object_id=f"sheet_{luggage_type}",
        object_type="luggage",
        bbox_xyxy=box,
        renderer_id="transit_luggage",
        renderer_variant_id=luggage_type,
        semantic_attributes={"luggage_type": luggage_type},
        visual_attributes={"color_rgb": [93, 126, 176], "style_id": "outlined_cartoon"},
        role="preview",
        source_entity_type="transit_luggage",
        render_scale=SCALE,
        style_id="outlined_cartoon",
    )


def _draw_transit_person(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    box = _object_box(bounds, 0.54)
    pose_id = str(item["id"])
    render_vector_scene_object(
        draw,
        object_id=f"sheet_{pose_id}",
        object_type="person",
        bbox_xyxy=box,
        renderer_id="transit_person",
        renderer_variant_id=pose_id,
        semantic_attributes={"pose_id": pose_id, "area_id": "preview"},
        visual_attributes={
            "primary_color_rgb": [82, 124, 178],
            "accent_color_rgb": [235, 172, 76],
            "skin_color_rgb": [178, 126, 83],
            "gender_id": str(item.get("gender_id", "female" if pose_id == "seated" else "male")),
            "style_id": "outlined_cartoon",
        },
        role="preview",
        source_entity_type="transit_person",
        render_scale=SCALE,
        style_id="outlined_cartoon",
    )


def _draw_transit_area(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    transit._draw_area(draw, rng=rng, setting_id="rail_station", area_id=str(item["id"]), area_box=(bounds[0], bounds[1] - 4.0, bounds[2], bounds[3] + 12.0), scale=SCALE, style_id="outlined_cartoon")


def _draw_transit_service(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    service_id = str(item["id"])
    colors = {
        "security_queue": (88, 120, 170),
        "ticket_counter": (63, 143, 122),
        "gate_queue": (150, 102, 166),
    }
    label = {
        "security_queue": "SECURITY",
        "ticket_counter": "TICKETS",
        "gate_queue": "GATE",
    }[service_id]
    x0, y0, x1, y1 = [float(v) for v in bounds]
    counter = (x0 + 8.0, y0 + 8.0, x1 - 8.0, y0 + 42.0)
    sign = (counter[0] + 12.0, counter[1] + 6.0, counter[2] - 12.0, counter[3] - 6.0)
    queue = (x0 + 28.0, y0 + 54.0, x1 - 28.0, y1 - 2.0)
    transit._rect(draw, counter, fill=colors[service_id], outline=(42, 49, 58), width=2, scale=SCALE, radius=6)
    transit._draw_fit_text(draw, text=label, bbox=sign, scale=SCALE, fill=(250, 246, 232), max_size_px=18, stroke_fill=(42, 49, 58))
    for px in (queue[0] + 8.0, queue[2] - 8.0):
        transit._line(draw, [(px, queue[1] + 3.0), (px, queue[3] - 3.0)], fill=(72, 77, 84), width=3, scale=SCALE)
    transit._line(draw, [(queue[0] + 8.0, queue[1] + 12.0), (queue[2] - 8.0, queue[1] + 12.0)], fill=(162, 72, 76), width=3, scale=SCALE)
    transit._line(draw, [(queue[0] + 8.0, queue[3] - 12.0), (queue[2] - 8.0, queue[3] - 12.0)], fill=(162, 72, 76), width=3, scale=SCALE)


def _draw_construction_worker(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    hard_hat_color = str(item.get("hard_hat_color", "yellow"))
    vest_color = str(item.get("vest_color", "orange"))
    tool_type = item.get("tool_type")
    hat_rgb = construction.CONSTRUCTION_COLOR_RGB.get(hard_hat_color, (238, 194, 64))
    vest_rgb = construction.CONSTRUCTION_COLOR_RGB.get(vest_color, (232, 126, 54))
    render_vector_scene_object(
        draw,
        object_id=f"sheet_{item['id']}",
        object_type="worker",
        bbox_xyxy=_object_box(bounds, 0.55),
        renderer_id="construction_worker",
        renderer_variant_id="standing",
        semantic_attributes={
            "hard_hat_color": hard_hat_color,
            "vest_color": vest_color,
            "tool_type": str(tool_type) if tool_type else None,
        },
        visual_attributes={
            "primary_color_rgb": [84, 118, 154],
            "accent_color_rgb": [int(v) for v in vest_rgb],
            "skin_color_rgb": [178, 126, 83],
            "hard_hat_color_rgb": [int(v) for v in hat_rgb],
            "vest_color_rgb": [int(v) for v in vest_rgb],
            "style_id": "outlined_cartoon",
            "gender_id": str(item.get("gender_id", "female" if tool_type else "male")),
        },
        role="preview",
        source_entity_type="construction_worker",
        render_scale=SCALE,
        style_id="outlined_cartoon",
    )


def _draw_construction_material(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    material_type = str(item["id"])
    render_vector_scene_object(
        draw,
        object_id=f"sheet_{material_type}",
        object_type="construction_material",
        bbox_xyxy=(bounds[0] + 8.0, bounds[1] + 12.0, bounds[2] - 8.0, bounds[3] - 4.0),
        renderer_id="construction_material",
        renderer_variant_id=material_type,
        semantic_attributes={
            "material_type": material_type,
            "material_label": construction.construction_material_display_name(material_type),
        },
        visual_attributes={"style_id": "outlined_cartoon"},
        role="preview",
        source_entity_type="construction_material",
        render_scale=SCALE,
        style_id="outlined_cartoon",
    )


def _draw_construction_equipment(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    equipment_type = str(item["id"])
    render_vector_scene_object(
        draw,
        object_id=f"sheet_{equipment_type}",
        object_type="construction_equipment",
        bbox_xyxy=(bounds[0] + 3.0, bounds[1] + 4.0, bounds[2] - 3.0, bounds[3] + 10.0),
        renderer_id="construction_equipment",
        renderer_variant_id=equipment_type,
        semantic_attributes={
            "equipment_type": equipment_type,
            "equipment_label": construction.construction_equipment_display_name(equipment_type),
            "zone_id": "loading_zone",
        },
        visual_attributes={"style_id": "outlined_cartoon"},
        role="preview",
        source_entity_type="construction_equipment",
        render_scale=SCALE,
        style_id="outlined_cartoon",
    )


def _draw_indoor_surface(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    x0, y0, x1, y1 = [float(v) for v in bounds]
    surface_type = str(item["id"])
    render_vector_scene_object(
        draw,
        object_id=f"sheet_{surface_type}",
        object_type="surface",
        bbox_xyxy=(x0, y0, x1, y1),
        renderer_id="indoor_surface",
        renderer_variant_id=surface_type,
        semantic_attributes={"surface_type": surface_type, "surface_label": str(item["name"])},
        visual_attributes={"style_id": "outlined_cartoon"},
        role="preview",
        source_entity_type="indoor_surface",
        render_scale=SCALE,
        style_id="outlined_cartoon",
    )


def _draw_indoor_container(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    x0, y0, x1, y1 = [float(v) for v in _object_box(bounds, 1.45 if item["id"] != "drawer" else 2.1)]
    fill = (193, 145, 86)
    outline = (94, 69, 42)
    kind = str(item["id"])
    if kind == "basket":
        draw.rounded_rectangle(_scale_box((x0, y0 + 15.0, x1, y1)), radius=18 * SCALE, fill=fill, outline=outline, width=max(2, 2 * SCALE))
        draw.arc(_scale_box((x0 + 20, y0 - 22, x1 - 20, y0 + 58)), 180, 360, fill=outline, width=max(3, 3 * SCALE))
    elif kind == "box":
        draw.polygon([(x0 * SCALE, (y0 + 28) * SCALE), (x1 * SCALE, (y0 + 28) * SCALE), ((x1 - 16) * SCALE, y1 * SCALE), ((x0 + 16) * SCALE, y1 * SCALE)], fill=fill, outline=outline)
        draw.line(_scale_box((x0 + 16, y0 + 28, x0 + 2, y0))[:2] + _scale_box((x1 - 2, y0, x1 - 16, y0 + 28))[:2], fill=outline, width=max(2, 2 * SCALE))
    else:
        draw.rectangle(_scale_box((x0, y0 + 10.0, x1, y1 - 6.0)), fill=fill, outline=outline, width=max(2, 2 * SCALE))
        draw.line([(int((x0 + 18) * SCALE), int((y0 + 34) * SCALE)), (int((x1 - 18) * SCALE), int((y0 + 34) * SCALE))], fill=outline, width=max(2, 2 * SCALE))


def _draw_indoor_furniture(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    x0, y0, x1, y1 = [float(v) for v in bounds]
    kind = str(item["id"])
    outline = (67, 55, 46)
    if kind == "sofa":
        draw.rounded_rectangle(_scale_box((x0 + 8, y0 + 45, x1 - 8, y1 - 4)), radius=24 * SCALE, fill=(111, 142, 167), outline=outline, width=max(2, 2 * SCALE))
        draw.rounded_rectangle(_scale_box((x0 + 24, y0 + 16, x1 - 24, y0 + 78)), radius=22 * SCALE, fill=(126, 158, 183), outline=outline, width=max(2, 2 * SCALE))
    elif kind == "cabinet":
        draw.rectangle(_scale_box((x0 + 18, y0 + 10, x1 - 18, y1 - 4)), fill=(164, 122, 82), outline=outline, width=max(2, 2 * SCALE))
        draw.rectangle(_scale_box((x0 + 34, y0 + 31, (x0 + x1) / 2 - 5, y0 + 70)), fill=(187, 143, 94), outline=outline, width=max(1, SCALE))
        draw.rectangle(_scale_box(((x0 + x1) / 2 + 5, y0 + 31, x1 - 34, y0 + 70)), fill=(187, 143, 94), outline=outline, width=max(1, SCALE))
        panel_top = min(y1 - 30.0, y0 + 78.0)
        draw.rectangle(_scale_box((x0 + 34, panel_top, x1 - 34, y1 - 14)), fill=(187, 143, 94), outline=outline, width=max(1, SCALE))
    else:
        _draw_indoor_surface(draw, item, bounds, rng)
        leg_top = min(y1 - 8.0, y0 + 74.0)
        for lx in (x0 + 40, x1 - 55):
            draw.rectangle(_scale_box((lx, leg_top, lx + 18, y1 - 4)), fill=(132, 86, 55), outline=outline, width=max(1, SCALE))


def _draw_environment_feature(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    x0, y0, x1, y1 = [float(v) for v in bounds]
    kind = str(item["id"])
    if kind == "road":
        path = ((x0 - 6, y0 + 0.75 * (y1 - y0)), (x0 + 0.35 * (x1 - x0), y0 + 0.42 * (y1 - y0)), (x1 + 6, y0 + 0.50 * (y1 - y0)))
        environment._draw_road(draw, path_points=path, width_px=42.0, road_style_id="asphalt_median", scale=SCALE)
    elif kind == "river":
        path = ((x0 - 8, y0 + 0.50 * (y1 - y0)), (x0 + 0.45 * (x1 - x0), y0 + 0.28 * (y1 - y0)), (x1 + 8, y0 + 0.64 * (y1 - y0)))
        environment._draw_river(draw, path_points=path, width_px=44.0, river_style_id="blue_channel", scale=SCALE)
    elif kind == "bridge":
        path = ((x0 - 8, y0 + 0.50 * (y1 - y0)), (x0 + 0.45 * (x1 - x0), y0 + 0.28 * (y1 - y0)), (x1 + 8, y0 + 0.64 * (y1 - y0)))
        environment._draw_river(draw, path_points=path, width_px=42.0, river_style_id="blue_channel", scale=SCALE)
        environment._draw_bridge(draw, bridge_id="sheet_bridge", river_path=path, x=(x0 + x1) * 0.5, river_width=42.0, bridge_style_id="wood_plank", scale=SCALE)
    elif kind == "crosswalk":
        path = ((x0 - 8, y0 + 0.72 * (y1 - y0)), (x0 + 0.35 * (x1 - x0), y0 + 0.45 * (y1 - y0)), (x1 + 8, y0 + 0.52 * (y1 - y0)))
        environment._draw_road(draw, path_points=path, width_px=48.0, road_style_id="asphalt_median", scale=SCALE)
        environment._draw_crosswalk(draw, crosswalk_id="sheet_crosswalk", road_path=path, x=(x0 + x1) * 0.5, road_width=48.0, scale=SCALE)
    else:
        environment._draw_buildings(draw, rng=rng, width=int(x1), horizon_y=y1 - 8.0, scale=SCALE, max_buildings=3, lit_window_count_override=6)


def _draw_counterfactual_object(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    query_id = str(item["query_id"])
    style = str(item.get("style_id", item.get("id", "")))
    colors = cf_visible._sample_colors(query_id, rng)
    aspect = {
        cf_visible.BUTTERFLY_VARIANT: 1.25,
        cf_visible.BICYCLE_VARIANT: 1.60,
        cf_visible.TRAFFIC_LIGHT_VARIANT: 0.58,
        cf_visible.CLOVER_VARIANT: 1.0,
        cf_visible.STAR_VARIANT: 1.0,
        cf_visible.GLOVE_VARIANT: 0.92,
        cf_visible.FORK_VARIANT: 0.55,
        cf_visible.SNOWFLAKE_VARIANT: 1.0,
        cf_visible.CHAIR_VARIANT: 0.86,
    }.get(query_id, 1.4)
    box = _object_box(bounds, aspect)
    visible_count = int(item.get("visible_count", cf_visible.CANONICAL_BIAS_ANSWER[query_id]))
    if query_id == cf_visible.BIRD_VARIANT:
        cf_visible._draw_bird(draw, box=box, style=style, visible_count=visible_count, scale=SCALE, pad=5.0, colors=colors)
    elif query_id == cf_visible.QUADRUPED_VARIANT:
        cf_visible._draw_quadruped(draw, box=box, style=style, visible_count=visible_count, scale=SCALE, pad=5.0, colors=colors)
    elif query_id == cf_visible.AIRPLANE_VARIANT:
        cf_visible._draw_airplane(draw, box=box, style=style, visible_count=visible_count, scale=SCALE, pad=5.0, colors=colors)
    elif query_id == cf_visible.BUTTERFLY_VARIANT:
        cf_visible._draw_butterfly(draw, box=box, style=style, visible_count=visible_count, scale=SCALE, pad=5.0, colors=colors)
    elif query_id == cf_visible.BICYCLE_VARIANT:
        cf_visible._draw_bicycle(draw, box=box, style=style, visible_count=visible_count, scale=SCALE, pad=5.0, colors=colors)
    elif query_id == cf_visible.TRAFFIC_LIGHT_VARIANT:
        cf_visible._draw_traffic_light(draw, box=box, style=style, visible_count=visible_count, scale=SCALE, pad=5.0, colors=colors)
    elif query_id == cf_visible.CLOVER_VARIANT:
        cf_visible._draw_clover(draw, box=box, style=style, visible_count=visible_count, scale=SCALE, pad=5.0, colors=colors)
    elif query_id == cf_visible.STAR_VARIANT:
        cf_visible._draw_star(draw, box=box, style=style, visible_count=visible_count, scale=SCALE, pad=5.0, colors=colors)
    elif query_id == cf_visible.GLOVE_VARIANT:
        cf_visible._draw_glove(draw, box=box, style=style, visible_count=visible_count, scale=SCALE, pad=5.0, colors=colors)
    elif query_id == cf_visible.FORK_VARIANT:
        cf_visible._draw_fork(draw, box=box, style=style, visible_count=visible_count, scale=SCALE, pad=5.0, colors=colors)
    elif query_id == cf_visible.SNOWFLAKE_VARIANT:
        cf_visible._draw_snowflake(draw, box=box, style=style, visible_count=visible_count, scale=SCALE, pad=5.0, colors=colors)
    else:
        cf_visible._draw_chair(draw, box=box, style=style, visible_count=visible_count, scale=SCALE, pad=5.0, colors=colors)


def _part_phrase(part_kind: str, count: int) -> str:
    noun = str(part_kind)
    if int(count) != 1:
        noun = {"lens": "lenses", "leaf": "leaves"}.get(noun, f"{noun}s")
    return f"{int(count)} {noun}"


def _part_plural(part_kind: str) -> str:
    return {"lens": "lenses", "leaf": "leaves"}.get(str(part_kind), f"{part_kind}s")


def _make_counterfactual_count_sheet(*, manifest: list[dict[str, Any]], taxonomy: list[dict[str, Any]]) -> None:
    query_ids = [
        cf_visible.BIRD_VARIANT,
        cf_visible.QUADRUPED_VARIANT,
        cf_visible.AIRPLANE_VARIANT,
        cf_visible.BUTTERFLY_VARIANT,
        cf_visible.BICYCLE_VARIANT,
        cf_visible.TRAFFIC_LIGHT_VARIANT,
        cf_visible.CLOVER_VARIANT,
        cf_visible.STAR_VARIANT,
        cf_visible.GLOVE_VARIANT,
        cf_visible.FORK_VARIANT,
        cf_visible.SNOWFLAKE_VARIANT,
        cf_visible.CHAIR_VARIANT,
    ]
    row_specs = [(query_id, style_id) for query_id in query_ids for style_id in cf_visible.STYLE_SUPPORT[query_id]]
    label_w = 230
    tile_w = 158
    row_h = 164
    cols = 6
    width = label_w + cols * tile_w
    height = HEADER_H + len(row_specs) * row_h
    image = Image.new("RGB", (width * SCALE, height * SCALE), BG)
    draw = ImageDraw.Draw(image)
    _draw_text(draw, (22, 18), "Counterfactual Property Counts", size=24, fill=TEXT, bold=True)
    _draw_text(draw, (22, 50), "Each object style gets one row: canonical/original count first, then every noncanonical visible count.", size=12, fill=MUTED, bold=False)
    generated_items: list[dict[str, Any]] = []

    for row_index, (query_id, style_id) in enumerate(row_specs):
        row_y = HEADER_H + row_index * row_h
        part_kind = str(cf_visible.COUNTED_PART_KIND[query_id])
        canonical = int(cf_visible.CANONICAL_BIAS_ANSWER[query_id])
        support = tuple(int(value) for value in cf_visible._support_for_variant(query_id, {}))
        counts = (canonical, *(count for count in support if int(count) != canonical))
        object_name = cf_visible.OBJECT_DESCRIPTION[query_id].replace("a stylized ", "")
        label_panel = (12.0, row_y + 10.0, label_w - 14.0, row_y + row_h - 10.0)
        draw.rounded_rectangle(_scale_box(label_panel), radius=9 * SCALE, fill=(246, 247, 241), outline=(211, 214, 204), width=max(1, SCALE))
        _draw_text(draw, (label_panel[0] + 12.0, label_panel[1] + 18.0), object_name, size=14, fill=TEXT, bold=True)
        _draw_text(draw, (label_panel[0] + 12.0, label_panel[1] + 44.0), f"count visible {_part_plural(part_kind)}", size=10, fill=MUTED)
        _draw_text(draw, (label_panel[0] + 12.0, label_panel[1] + 64.0), f"style: {style_id.replace('_', ' ')}", size=9, fill=MUTED)

        for col_index, visible_count in enumerate(counts):
            x = label_w + col_index * tile_w
            panel = (x + 8.0, row_y + 10.0, x + tile_w - 8.0, row_y + row_h - 10.0)
            is_original = int(visible_count) == canonical
            draw.rounded_rectangle(_scale_box(panel), radius=9 * SCALE, fill=PANEL_BG, outline=(218, 214, 202), width=max(1, SCALE))
            badge = (panel[0] + 8.0, panel[1] + 8.0, panel[0] + (72.0 if is_original else 112.0), panel[1] + 29.0)
            draw.rounded_rectangle(_scale_box(badge), radius=5 * SCALE, fill=(229, 239, 229) if is_original else (238, 232, 231), outline=(184, 200, 184) if is_original else (207, 190, 187), width=max(1, SCALE))
            _center_text(draw, badge, "original" if is_original else "counterfactual", size=8, fill=(51, 80, 58) if is_original else (92, 60, 56), bold=True)
            item = {
                "id": f"{query_id}_{style_id}_{visible_count}",
                "name": f"{object_name}: {_part_phrase(part_kind, int(visible_count))}",
                "group": part_kind,
                "query_id": query_id,
                "style_id": style_id,
                "visible_count": int(visible_count),
                "is_original": bool(is_original),
            }
            object_area = (panel[0] + 12.0, panel[1] + 34.0, panel[2] - 12.0, panel[3] - 36.0)
            if query_id == cf_visible.TRAFFIC_LIGHT_VARIANT:
                object_area = (panel[0] + 4.0, panel[1] + 30.0, panel[2] - 4.0, panel[3] - 8.0)
            elif query_id == cf_visible.FORK_VARIANT:
                object_area = (panel[0] + 8.0, panel[1] + 28.0, panel[2] - 8.0, panel[3] - 34.0)
            elif query_id in {cf_visible.GLOVE_VARIANT, cf_visible.CHAIR_VARIANT}:
                object_area = (panel[0] + 8.0, panel[1] + 30.0, panel[2] - 8.0, panel[3] - 36.0)
            elif query_id == cf_visible.BUTTERFLY_VARIANT:
                object_area = (object_area[0] + 8.0, object_area[1] + 18.0, object_area[2] - 8.0, object_area[3] - 3.0)
            _draw_counterfactual_object(draw, item, object_area, random.Random(_seed(str(item["id"]))))
            _center_text(draw, (panel[0] + 6.0, panel[3] - 29.0, panel[2] - 6.0, panel[3] - 10.0), _part_phrase(part_kind, int(visible_count)), size=10, fill=TEXT, bold=True)
            generated_items.append(item)

    output = OUT_DIR / "05_counterfactual_property_counts.png"
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    image.save(output)
    manifest.append({"file": str(output), "title": "Counterfactual Property Counts", "item_count": len(generated_items)})
    taxonomy.extend(_taxonomy_record("counterfactual_property_counts", item) for item in generated_items)


def _taxonomy_record(category_id: str, item: SpriteItem) -> dict[str, Any]:
    return {
        "category_id": category_id,
        "catalog_id": str(item.get("catalog_id", "")),
        "object_id": str(item.get("preview_id", item.get("id", ""))),
        "display_id": str(item.get("display_id", item.get("id", ""))),
        "public_name": str(item.get("name", item.get("id", ""))),
        "group": str(item.get("group", "")),
        "family": str(item.get("family", "")),
        "render_layer": str(item.get("render_layer", "")),
        "size_class": str(item.get("size_class", "")),
        "placement_tags": list(item.get("placement_tags", ())),
        "scene_tags": list(item.get("scene_tags", ())),
        "gender_id": str(item.get("gender_id", "")),
    }


def _entry_has_tag(entry: CatalogEntry, tag: str) -> bool:
    return str(tag) in set(entry.placement_tags)


def _entry_group(entry: CatalogEntry) -> str:
    tags = set(entry.placement_tags)
    if "market_item" in tags:
        return "market item"
    if "library_book_orientation" in tags:
        return "book"
    if "transit_luggage" in tags:
        return "luggage"
    if "construction_material" in tags:
        return "material"
    if "construction_tool" in tags:
        return "tool"
    if "park_person_activity" in tags:
        return "activity"
    if "transit_person_pose" in tags:
        return "pose"
    if "construction_worker" in tags:
        return "worker"
    if "market_shop" in tags:
        return "shop"
    if "library_section" in tags:
        return "section"
    if "park_equipment" in tags or "construction_equipment" in tags:
        return "equipment"
    if "transit_service_point" in tags:
        return "service"
    if "indoor_surface" in tags:
        return "surface"
    if "indoor_container" in tags:
        return "container"
    if "indoor_furniture" in tags:
        return "furniture"
    if "environment_feature" in tags:
        return str(entry.public_name)
    if str(entry.family) == "background":
        return "background"
    if str(entry.render_layer) == "region":
        return "region"
    return str(entry.family)


def _catalog_item(entry: CatalogEntry, *, group: str | None = None, name: str | None = None) -> dict[str, Any]:
    public_name = str(name if name is not None else entry.public_name)
    item = {
        "id": str(entry.variant_id),
        "catalog_id": str(entry.catalog_id),
        "name": public_name,
        "group": str(group if group is not None else _entry_group(entry)),
        "family": str(entry.family),
        "render_layer": str(entry.render_layer),
        "size_class": str(entry.size_class),
        "placement_tags": tuple(entry.placement_tags),
        "scene_tags": tuple(entry.scene_tags),
        "renderer_id": str(entry.renderer_id),
        "object_type": str(entry.object_type),
    }
    if str(entry.renderer_id) == "library_book":
        item["orientation"] = str(entry.variant_id)
        item["color"] = "blue" if str(entry.variant_id) == "upright" else "orange"
    if str(entry.renderer_id) == "construction_worker_tool":
        item["tool_type"] = str(entry.variant_id)
        item["hard_hat_color"] = "yellow"
        item["vest_color"] = "orange"
        item["name"] = f"worker with {entry.public_name}"
    return item


def _catalog_sort_key(entry: CatalogEntry) -> tuple[str, str, str, str]:
    return (str(entry.family), _entry_group(entry), str(entry.public_name), str(entry.catalog_id))


def _person_catalog_items(entries: Sequence[CatalogEntry]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in sorted(entries, key=_catalog_sort_key):
        base = _catalog_item(entry)
        for gender_id in PERSON_GENDER_IDS:
            item = dict(base)
            item["gender_id"] = str(gender_id)
            item["preview_id"] = f"{base['catalog_id']}__{gender_id}"
            item["display_id"] = f"{base['id']}__{gender_id}"
            item["seed_id"] = str(base["id"])
            item["name"] = f"{base['name']} ({gender_id})"
            items.append(item)
    return items


def _draw_background_swatch(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    x0, y0, x1, y1 = [float(v) for v in bounds]
    scene_tag = next(iter(item.get("scene_tags", ("",))), "")
    background_id = str(item.get("id", "background"))
    palette = {
        "mixed_object_canvas": ((234, 242, 248), (225, 218, 198)),
        "environment_object_canvas": ((221, 239, 249), (177, 213, 158)),
        "indoor_room_canvas": ((232, 225, 215), (191, 166, 137)),
        "urban_market_canvas": ((229, 239, 244), (204, 190, 164)),
        "library_canvas": ((229, 222, 210), (176, 143, 108)),
        "park_playground_canvas": ((207, 229, 239), (132, 179, 113)),
        "transit_terminal_canvas": ((226, 232, 238), (190, 196, 202)),
        "construction_site_canvas": ((196, 219, 228), (180, 168, 138)),
    }
    top, bottom = palette.get(str(scene_tag), ((232, 236, 240), (209, 205, 192)))
    mid = y0 + 0.56 * (y1 - y0)
    draw.rounded_rectangle(_scale_box(bounds), radius=14 * SCALE, fill=top, outline=(118, 124, 130), width=max(2, 2 * SCALE))
    draw.rectangle(_scale_box((x0, mid, x1, y1)), fill=bottom)
    for idx in range(4):
        px = x0 + 18.0 + idx * (x1 - x0 - 36.0) / 3.0
        py = y0 + 24.0 + float(rng.randint(-6, 6))
        draw.ellipse(_scale_box((px, py, px + 26.0, py + 12.0)), fill=(246, 248, 250), outline=None)
    _center_text(draw, (x0 + 8.0, y0 + 0.58 * (y1 - y0), x1 - 8.0, y1 - 8.0), background_id.replace("_", " "), size=11, fill=(47, 55, 63), bold=True)


def _draw_catalog_entry(draw: ImageDraw.ImageDraw, item: SpriteItem, bounds: Sequence[float], rng: random.Random) -> None:
    renderer_id = str(item.get("renderer_id", ""))
    if renderer_id == "object_library":
        _draw_shared_object(draw, item, bounds, rng)
    elif renderer_id == "urban_market_shop":
        _draw_market_shop(draw, item, bounds, rng)
    elif renderer_id == "urban_market_item":
        _draw_market_item(draw, item, bounds, rng)
    elif renderer_id == "library_section":
        _draw_library_section(draw, item, bounds, rng)
    elif renderer_id == "library_book":
        _draw_library_book(draw, item, bounds, rng)
    elif renderer_id == "park_equipment":
        _draw_park_equipment(draw, item, bounds, rng)
    elif renderer_id == "park_zone":
        _draw_zone_swatch(draw, item, bounds, rng)
    elif renderer_id == "park_person":
        _draw_park_activity(draw, item, bounds, rng)
    elif renderer_id == "transit_luggage":
        _draw_transit_luggage(draw, item, bounds, rng)
    elif renderer_id == "transit_person":
        _draw_transit_person(draw, item, bounds, rng)
    elif renderer_id == "transit_area":
        _draw_transit_area(draw, item, bounds, rng)
    elif renderer_id == "transit_service_point":
        _draw_transit_service(draw, item, bounds, rng)
    elif renderer_id == "construction_worker":
        _draw_construction_worker(draw, item, bounds, rng)
    elif renderer_id == "construction_material":
        _draw_construction_material(draw, item, bounds, rng)
    elif renderer_id == "construction_equipment":
        _draw_construction_equipment(draw, item, bounds, rng)
    elif renderer_id == "construction_worker_tool":
        _draw_construction_worker(draw, item, bounds, rng)
    elif renderer_id == "construction_zone":
        _draw_zone_swatch(draw, item, bounds, rng)
    elif renderer_id == "indoor_surface":
        _draw_indoor_surface(draw, item, bounds, rng)
    elif renderer_id == "indoor_container":
        _draw_indoor_container(draw, item, bounds, rng)
    elif renderer_id == "indoor_furniture":
        _draw_indoor_furniture(draw, item, bounds, rng)
    elif renderer_id == "environment_feature":
        _draw_environment_feature(draw, item, bounds, rng)
    elif renderer_id.endswith("_background"):
        _draw_background_swatch(draw, item, bounds, rng)
    else:
        _draw_background_swatch(draw, item, bounds, rng)


def _make_catalog_sheet(
    filename: str,
    *,
    category_id: str,
    title: str,
    subtitle: str,
    entries: Sequence[CatalogEntry],
    cols: int,
    manifest: list[dict[str, Any]],
    taxonomy: list[dict[str, Any]],
) -> None:
    items = [_catalog_item(entry) for entry in sorted(entries, key=_catalog_sort_key)]
    manifest.append(
        _make_sheet(
            filename,
            title=title,
            subtitle=subtitle,
            items=items,
            draw_item=_draw_catalog_entry,
            cols=cols,
        )
    )
    taxonomy.extend(_taxonomy_record(category_id, item) for item in items)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in OUT_DIR.glob("*.png"):
        path.unlink()
    for stale in (OUT_DIR / "object_taxonomy_preview.json", OUT_DIR / "object_category_preview.json"):
        if stale.exists():
            stale.unlink()
    manifest: list[dict[str, Any]] = []
    taxonomy: list[dict[str, Any]] = []

    entries = tuple(catalog_entries())
    shared_entries = tuple(entry for entry in entries if _entry_has_tag(entry, "shared_object"))
    scene_foreground_entries = tuple(
        entry
        for entry in entries
        if str(entry.render_layer) == "foreground"
        and not _entry_has_tag(entry, "shared_object")
        and str(entry.family) not in {"person", "equipment"}
    )
    person_entries = tuple(entry for entry in entries if str(entry.family) == "person")
    fixture_entries = tuple(
        entry
        for entry in entries
        if str(entry.render_layer) == "fixture" or str(entry.family) in {"structure", "equipment"}
    )
    region_background_entries = tuple(
        entry
        for entry in entries
        if str(entry.family) == "background" or str(entry.render_layer) == "region"
    )

    _make_catalog_sheet(
        "00_foreground_shared_objects.png",
        category_id="foreground_shared_objects",
        title="Foreground Shared Objects",
        subtitle="Reusable object-library entries, grouped by public family and size class from the catalog.",
        entries=shared_entries,
        cols=6,
        manifest=manifest,
        taxonomy=taxonomy,
    )
    _make_catalog_sheet(
        "01_foreground_props_inventory_materials.png",
        category_id="foreground_props_inventory_materials",
        title="Foreground Props, Inventory, Materials",
        subtitle="Countable foreground entries outside the shared pool: inventory, books, luggage, materials, and tools.",
        entries=scene_foreground_entries,
        cols=6,
        manifest=manifest,
        taxonomy=taxonomy,
    )
    person_items = _person_catalog_items(person_entries)
    manifest.append(
        _make_sheet(
            "02_people_activity_pose_worker_variants.png",
            title="People, Activity, Pose, Worker Variants",
            subtitle="Person-family entries with render-only male/female appearance variants.",
            items=person_items,
            draw_item=_draw_catalog_entry,
            cols=4,
        )
    )
    taxonomy.extend(_taxonomy_record("people_activity_pose_worker_variants", item) for item in person_items)
    _make_catalog_sheet(
        "03_fixtures_structures_equipment.png",
        category_id="fixtures_structures_equipment",
        title="Fixtures, Structures, Equipment",
        subtitle="Large or anchored drawable entries: shops, sections, surfaces, service points, structures, and equipment.",
        entries=fixture_entries,
        cols=5,
        manifest=manifest,
        taxonomy=taxonomy,
    )
    _make_catalog_sheet(
        "04_regions_and_backgrounds.png",
        category_id="regions_and_backgrounds",
        title="Regions And Backgrounds",
        subtitle="Scene-scale backgrounds plus semantic regions such as roads, rivers, zones, and boarding areas.",
        entries=region_background_entries,
        cols=5,
        manifest=manifest,
        taxonomy=taxonomy,
    )

    _make_counterfactual_count_sheet(manifest=manifest, taxonomy=taxonomy)

    (OUT_DIR / "object_category_preview.json").write_text(json.dumps(taxonomy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    index_lines = [
        "# Illustration Object Spritesheets",
        "",
        "Generated by `scripts/generate_illustration_object_spritesheets.py`.",
        "",
        "Sheets are grouped by centralized object-catalog categories, not by scene. Scene tags remain in the machine-readable preview only as placement metadata.",
        "",
        "| File | Sheet | Items |",
        "|---|---|---:|",
    ]
    for entry in manifest:
        path = Path(str(entry["file"]))
        index_lines.append(f"| [{path.name}]({path.name}) | {entry['title']} | {entry['item_count']} |")
    index_lines.extend(
        [
            "",
            "Visual transformation scenes such as jigsaw, rotated-tile, missing-patch, object-difference, and odd-scene tasks do not introduce a separate object vocabulary; they reuse source illustration scenes or image patches.",
            "",
            "A machine-readable preview is in `object_category_preview.json`.",
        ]
    )
    (OUT_DIR / "README.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"wrote {len(manifest)} spritesheets to {OUT_DIR}")
    for entry in manifest:
        print(f"- {entry['file']} ({entry['item_count']} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
