"""Illustration object review inventory and preview rendering."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import random
import re
import sys
import types
from typing import Any, Mapping

from PIL import Image, ImageDraw


def _install_trace_tasks_namespace() -> None:
    """Avoid importing the repo-wide task registry for object previews."""

    if "trace.tasks" in sys.modules:
        return
    repo_root = Path(__file__).resolve().parents[2]
    tasks_module = types.ModuleType("trace.tasks")
    tasks_module.__path__ = [str(repo_root / "trace" / "tasks")]  # type: ignore[attr-defined]
    sys.modules["trace.tasks"] = tasks_module
    trace_module = sys.modules.get("trace")
    if trace_module is not None:
        setattr(trace_module, "tasks", tasks_module)


_install_trace_tasks_namespace()

from trace.tasks.illustrations.shared.object_catalog import CATALOG_ENTRIES, CatalogEntry
from trace.tasks.illustrations.shared.object_library import (
    OBJECT_TEMPLATES,
    aspect_ratio_for_object,
    choose_object_colors,
    display_name_for_object_type,
)
from trace.tasks.illustrations.shared.object_rendering import (
    PIXEL_RPG_SHARED_OBJECT_TYPES,
    IllustrationObjectSpec,
    RenderContext,
    render_illustration_object,
)
from trace.tasks.illustrations.shared.object_variants import (
    PERSON_VARIANT_IDS,
    RENDERER_STYLE_ISOMETRIC_PIXEL_RPG,
    RENDERER_STYLE_TOP_DOWN_PIXEL_RPG,
    RENDERER_STYLE_VECTOR,
    TREE_VARIANT_IDS,
)
from trace.tasks.illustrations.shared.pixel_world_objects import (
    PIXEL_DOMESTIC_ANIMALS,
    PIXEL_PRODUCE_GOODS,
    PIXEL_SHELF_GOODS,
    PIXEL_VEGETABLE_STYLES,
)


RENDERER_LABELS: Mapping[str, str] = {
    RENDERER_STYLE_VECTOR: "Vector",
    RENDERER_STYLE_TOP_DOWN_PIXEL_RPG: "Top-down RPG",
    RENDERER_STYLE_ISOMETRIC_PIXEL_RPG: "Isometric RPG",
}
VALID_REVIEW_DECISIONS = ("approve", "remove", "improve")

_PREVIEW_SIZE = (260, 210)
_PIXEL_FOOTPRINTS: Mapping[str, tuple[int, int]] = {
    "archway": (2, 1),
    "barn": (4, 3),
    "basket": (1, 1),
    "bed": (2, 3),
    "bench": (2, 1),
    "boulder": (1, 1),
    "brazier": (1, 1),
    "broken_wall": (2, 1),
    "cart": (2, 1),
    "castle": (5, 4),
    "cave_entrance": (4, 3),
    "cemetery_gate": (3, 1),
    "candle": (1, 1),
    "chair": (1, 1),
    "chest": (2, 1),
    "chicken_coop": (2, 2),
    "church": (4, 4),
    "coop": (2, 2),
    "counter": (3, 1),
    "crystal_cluster": (1, 1),
    "crop_row": (4, 1),
    "dead_tree": (1, 2),
    "domestic_animal": (2, 1),
    "farm_gate": (3, 1),
    "fireplace": (2, 1),
    "floor_switch": (1, 1),
    "fountain": (2, 2),
    "gazebo": (3, 3),
    "grave_marker": (1, 1),
    "house": (4, 3),
    "inn": (4, 3),
    "iron_fence": (3, 1),
    "jar": (1, 1),
    "lamp_post": (1, 2),
    "ladder": (1, 1),
    "magic_circle": (2, 2),
    "market_stall": (3, 2),
    "mine_cart": (2, 1),
    "notice_board": (2, 1),
    "ore_vein": (1, 1),
    "plate": (1, 1),
    "pond": (3, 2),
    "pot": (1, 1),
    "produce_bin": (2, 1),
    "rail_track": (1, 1),
    "rubble": (1, 1),
    "room_divider": (3, 1),
    "rug": (3, 2),
    "sack": (1, 1),
    "scarecrow": (1, 2),
    "sealed_door": (2, 1),
    "shelf": (3, 1),
    "shop": (4, 3),
    "stairs": (2, 2),
    "stalagmite": (1, 1),
    "statue": (2, 2),
    "stone_column": (1, 1),
    "stool": (1, 1),
    "table": (2, 2),
    "tower": (3, 4),
    "torch": (1, 1),
    "tree": (1, 2),
    "trough": (2, 1),
    "vegetable_patch": (1, 1),
    "wagon": (3, 2),
    "well": (2, 2),
    "windmill": (3, 4),
    "woodpile": (2, 1),
    "wood_support": (2, 2),
}
_VECTOR_CATALOG_RENDERERS = {
    "construction_equipment",
    "construction_material",
    "construction_worker",
    "fixture_bench",
    "indoor_container",
    "indoor_furniture",
    "indoor_surface",
    "park_equipment",
    "park_person",
}


@dataclass(frozen=True)
class IllustrationObjectReviewItem:
    """One renderable object/style row in the illustration review page."""

    item_id: str
    renderer_style: str
    renderer_label: str
    category: str
    category_label: str
    object_type: str
    public_name: str
    family: str
    source: str
    size_class: str = ""
    render_layer: str = ""
    variant_id: str = ""
    variant_label: str = ""
    renderer_id: str = ""
    renderer_variant_id: str = ""
    semantic_attributes: Mapping[str, Any] | None = None
    visual_attributes: Mapping[str, Any] | None = None

    @property
    def display_label(self) -> str:
        if self.variant_label and self.variant_label != self.public_name:
            return f"{self.public_name} · {self.variant_label}"
        return self.public_name


@lru_cache(maxsize=1)
def illustration_object_review_items() -> tuple[IllustrationObjectReviewItem, ...]:
    """Return the current reviewable illustration object/style inventory."""

    items: list[IllustrationObjectReviewItem] = []
    items.extend(_vector_library_items())
    items.extend(_vector_catalog_items())
    items.extend(_pixel_items(RENDERER_STYLE_TOP_DOWN_PIXEL_RPG))
    items.extend(_pixel_items(RENDERER_STYLE_ISOMETRIC_PIXEL_RPG))
    return tuple(sorted(items, key=lambda item: (item.renderer_style, item.category, item.public_name, item.variant_label, item.item_id)))


def illustration_object_review_item(item_id: str) -> IllustrationObjectReviewItem | None:
    """Return a review item by id."""

    key = str(item_id)
    for item in illustration_object_review_items():
        if item.item_id == key:
            return item
    return None


def render_illustration_object_review_image(item_id: str) -> Image.Image:
    """Render one object/style preview image for the review app."""

    item = illustration_object_review_item(item_id)
    if item is None:
        return _placeholder_image("Unknown object", str(item_id))
    try:
        if item.renderer_style == RENDERER_STYLE_VECTOR:
            return _render_vector_preview(item)
        if item.renderer_style == RENDERER_STYLE_TOP_DOWN_PIXEL_RPG:
            return _render_top_down_pixel_preview(item)
        if item.renderer_style == RENDERER_STYLE_ISOMETRIC_PIXEL_RPG:
            return _render_isometric_pixel_preview(item)
    except Exception as exc:  # pragma: no cover - defensive preview fallback
        return _placeholder_image("Render error", f"{item.display_label}: {exc}")
    return _placeholder_image("Unsupported renderer", item.renderer_style)


def filtered_illustration_object_items(
    *,
    renderer_style: str,
    category: str,
) -> tuple[IllustrationObjectReviewItem, ...]:
    """Return items filtered by renderer and category tab selections."""

    renderer = str(renderer_style or RENDERER_STYLE_VECTOR)
    category_key = str(category or "all")
    items = [item for item in illustration_object_review_items() if item.renderer_style == renderer]
    if category_key != "all":
        items = [item for item in items if item.category == category_key]
    return tuple(items)


def illustration_object_renderer_tabs(selected_renderer: str) -> tuple[dict[str, Any], ...]:
    """Return renderer tabs with counts."""

    items = illustration_object_review_items()
    selected = str(selected_renderer or RENDERER_STYLE_VECTOR)
    tabs = []
    for renderer_style, label in RENDERER_LABELS.items():
        tabs.append(
            {
                "renderer_style": renderer_style,
                "label": label,
                "count": sum(1 for item in items if item.renderer_style == renderer_style),
                "active": selected == renderer_style,
            }
        )
    return tuple(tabs)


def illustration_object_category_tabs(
    *,
    renderer_style: str,
    selected_category: str,
) -> tuple[dict[str, Any], ...]:
    """Return category tabs for the selected renderer."""

    renderer = str(renderer_style or RENDERER_STYLE_VECTOR)
    selected = str(selected_category or "all")
    items = [item for item in illustration_object_review_items() if item.renderer_style == renderer]
    labels: dict[str, str] = {}
    counts: dict[str, int] = {}
    for item in items:
        labels[item.category] = item.category_label
        counts[item.category] = counts.get(item.category, 0) + 1
    tabs = [
        {
            "category": "all",
            "label": "All",
            "count": len(items),
            "active": selected == "all",
        }
    ]
    for category in sorted(counts, key=lambda value: (labels.get(value, value), value)):
        tabs.append(
            {
                "category": category,
                "label": labels.get(category, category.replace("_", " ")),
                "count": counts[category],
                "active": selected == category,
            }
        )
    return tuple(tabs)


def illustration_object_review_progress(
    items: tuple[IllustrationObjectReviewItem, ...],
    reviews_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, int]:
    """Return compact decision counts for the current page."""

    counts = {"total": len(items), "pending": 0, "approve": 0, "remove": 0, "improve": 0}
    for item in items:
        decision = str((reviews_by_id.get(item.item_id) or {}).get("decision", ""))
        if decision in VALID_REVIEW_DECISIONS:
            counts[decision] += 1
        else:
            counts["pending"] += 1
    return counts


def _vector_library_items() -> list[IllustrationObjectReviewItem]:
    items: list[IllustrationObjectReviewItem] = []
    for object_type, template in sorted(OBJECT_TEMPLATES.items()):
        variants = _vector_library_variants(str(object_type))
        for variant_id, variant_label in variants:
            category, category_label = _category(str(template.family))
            suffix = variant_id or "default"
            items.append(
                IllustrationObjectReviewItem(
                    item_id=_make_item_id(RENDERER_STYLE_VECTOR, "library", object_type, suffix),
                    renderer_style=RENDERER_STYLE_VECTOR,
                    renderer_label=RENDERER_LABELS[RENDERER_STYLE_VECTOR],
                    category=category,
                    category_label=category_label,
                    object_type=str(object_type),
                    public_name=display_name_for_object_type(str(object_type)),
                    family=str(template.family),
                    source="object_library",
                    size_class="",
                    render_layer="foreground",
                    variant_id=variant_id,
                    variant_label=variant_label,
                    visual_attributes=_vector_visual_attributes(str(object_type), variant_id),
                )
            )
    return items


def _vector_catalog_items() -> list[IllustrationObjectReviewItem]:
    items: list[IllustrationObjectReviewItem] = []
    for entry in CATALOG_ENTRIES:
        if entry.renderer_id not in _VECTOR_CATALOG_RENDERERS:
            continue
        category, category_label = _category(entry.family)
        items.append(
            IllustrationObjectReviewItem(
                item_id=_make_item_id(RENDERER_STYLE_VECTOR, "catalog", entry.catalog_id),
                renderer_style=RENDERER_STYLE_VECTOR,
                renderer_label=RENDERER_LABELS[RENDERER_STYLE_VECTOR],
                category=category,
                category_label=category_label,
                object_type=entry.object_type,
                public_name=entry.public_name,
                family=entry.family,
                source=f"catalog:{entry.scene_tags[0] if entry.scene_tags else 'shared'}",
                size_class=entry.size_class,
                render_layer=entry.render_layer,
                renderer_id=entry.renderer_id,
                renderer_variant_id=entry.variant_id,
                variant_id="",
                variant_label=entry.variant_id.replace("_", " "),
                semantic_attributes=_catalog_semantic_attributes(entry),
                visual_attributes=_catalog_visual_attributes(entry),
            )
        )
    return items


def _pixel_items(renderer_style: str) -> list[IllustrationObjectReviewItem]:
    items: list[IllustrationObjectReviewItem] = []
    for object_type in PIXEL_RPG_SHARED_OBJECT_TYPES:
        for variant_id, variant_label, semantic, visual in _pixel_variants(str(object_type), renderer_style):
            family = _pixel_family(str(object_type))
            category, category_label = _category(family)
            suffix = variant_id or "default"
            items.append(
                IllustrationObjectReviewItem(
                    item_id=_make_item_id(renderer_style, "pixel_rpg", object_type, suffix),
                    renderer_style=renderer_style,
                    renderer_label=RENDERER_LABELS[renderer_style],
                    category=category,
                    category_label=category_label,
                    object_type=str(object_type),
                    public_name=_pixel_public_name(str(object_type), variant_label),
                    family=family,
                    source="pixel_rpg_shared",
                    size_class="",
                    render_layer="foreground",
                    variant_id=variant_id if object_type in {"person", "tree", "vegetable_patch"} else "",
                    variant_label=variant_label,
                    semantic_attributes=semantic,
                    visual_attributes=visual,
                )
            )
    return items


def _vector_library_variants(object_type: str) -> tuple[tuple[str, str], ...]:
    if object_type == "tree":
        return tuple((variant_id, variant_id.replace("_", " ")) for variant_id in TREE_VARIANT_IDS)
    if object_type in {"person", "pedestrian_with_bag"}:
        return tuple((variant_id, variant_id.replace("_", " ")) for variant_id in PERSON_VARIANT_IDS)
    return (("", ""),)


def _pixel_variants(
    object_type: str,
    renderer_style: str,
) -> tuple[tuple[str, str, Mapping[str, Any], Mapping[str, Any]], ...]:
    if object_type == "tree":
        return tuple(
            (
                variant_id,
                variant_id.replace("_", " "),
                {},
                {"tree_style": variant_id, "leaf_rgb": _tree_rgb(variant_id)},
            )
            for variant_id in TREE_VARIANT_IDS
        )
    if object_type == "person":
        return tuple(
            (
                variant_id,
                variant_id.replace("_", " "),
                {},
                {
                    "person_variant_id": variant_id,
                    "gender_id": "female" if variant_id in {"vendor", "soldier"} else "male",
                    "facing": "down" if renderer_style == RENDERER_STYLE_TOP_DOWN_PIXEL_RPG else "right",
                },
            )
            for variant_id in PERSON_VARIANT_IDS
        )
    if object_type == "domestic_animal":
        return tuple(
            (
                animal_type,
                animal_type.replace("_", " "),
                {"animal_type": animal_type},
                {"animal_type": animal_type, "facing": "right"},
            )
            for animal_type in PIXEL_DOMESTIC_ANIMALS
        )
    if object_type == "vegetable_patch":
        return tuple(
            (
                vegetable_style,
                vegetable_style.replace("_", " "),
                {},
                {"vegetable_style": vegetable_style},
            )
            for vegetable_style in PIXEL_VEGETABLE_STYLES
        )
    if object_type == "shelf":
        return tuple(
            (
                goods_type,
                goods_type.replace("_", " "),
                {},
                {"goods_type": goods_type},
            )
            for goods_type in PIXEL_SHELF_GOODS
        )
    if object_type == "produce_bin":
        return tuple(
            (
                goods_type,
                goods_type.replace("_", " "),
                {},
                {"goods_type": goods_type},
            )
            for goods_type in PIXEL_PRODUCE_GOODS
        )
    if object_type == "table":
        return (
            ("square", "square", {}, {"table_shape": "square"}),
            ("round", "round", {}, {"table_shape": "round"}),
            ("long", "long", {}, {"table_shape": "long"}),
        )
    if object_type == "chair":
        return tuple(
            (
                facing,
                facing,
                {},
                {"facing": facing},
            )
            for facing in ("down", "left", "right")
        )
    if object_type == "bed":
        return (
            ("single", "single", {}, {"bed_size": "single"}),
            ("double", "double", {}, {"bed_size": "double"}),
        )
    if object_type == "fireplace":
        return (
            ("lit", "lit", {}, {"fire_state": "lit"}),
            ("unlit", "unlit", {}, {"fire_state": "unlit"}),
        )
    if object_type == "brazier":
        return (
            ("lit", "lit", {}, {"fire_state": "lit"}),
            ("unlit", "unlit", {}, {"fire_state": "unlit"}),
        )
    if object_type == "candle":
        return (
            ("lit", "lit", {}, {"flame_state": "lit"}),
            ("unlit", "unlit", {}, {"flame_state": "unlit"}),
        )
    if object_type == "room_divider":
        return (
            ("screen", "screen", {}, {"divider_style": "screen"}),
            ("curtain", "curtain", {}, {"divider_style": "curtain"}),
        )
    if object_type == "rail_track":
        return tuple(
            (
                track_shape,
                track_shape.replace("_", " "),
                {},
                {"track_shape": track_shape},
            )
            for track_shape in ("horizontal", "vertical", "corner", "crossing")
        )
    if object_type == "ladder":
        return (
            ("vertical", "vertical", {}, {"orientation": "vertical"}),
            ("horizontal", "horizontal", {}, {"orientation": "horizontal"}),
        )
    if object_type == "stairs":
        return (
            ("down", "down", {}, {"stair_direction": "down"}),
            ("up", "up", {}, {"stair_direction": "up"}),
            ("left", "left", {}, {"stair_direction": "left"}),
            ("right", "right", {}, {"stair_direction": "right"}),
        )
    if object_type == "floor_switch":
        return (
            ("raised", "raised", {}, {"switch_state": "raised"}),
            ("pressed", "pressed", {}, {"switch_state": "pressed"}),
        )
    if object_type == "broken_wall":
        return (
            ("cracked", "cracked", {}, {"break_style": "cracked"}),
            ("gap", "gap", {}, {"break_style": "gap"}),
        )
    if object_type == "sealed_door":
        return (
            ("horizontal", "horizontal", {}, {"door_orientation": "horizontal"}),
            ("vertical", "vertical", {}, {"door_orientation": "vertical"}),
        )
    return (("", "", {}, _default_pixel_visuals(object_type)),)


def _render_vector_preview(item: IllustrationObjectReviewItem) -> Image.Image:
    image = _base_preview_image()
    draw = ImageDraw.Draw(image, "RGBA")
    _draw_vector_preview_frame(draw, _PREVIEW_SIZE)
    bbox = _vector_bbox(item.object_type, item.renderer_id)
    primary, accent = _object_colors(item.object_type, item.item_id)
    visual = dict(item.visual_attributes or {})
    visual.setdefault("primary_color_rgb", primary)
    visual.setdefault("accent_color_rgb", accent)
    spec = IllustrationObjectSpec(
        object_id="preview_object",
        object_type=item.object_type,
        public_name=item.public_name,
        bbox_xyxy=bbox,
        variant_id=item.variant_id,
        renderer_id=item.renderer_id,
        renderer_variant_id=item.renderer_variant_id,
        semantic_attributes=dict(item.semantic_attributes or {}),
        visual_attributes=visual,
        source_entity_type="illustration_object_review",
    )
    render_illustration_object(
        spec,
        RenderContext(
            renderer_style=RENDERER_STYLE_VECTOR,
            draw=draw,
            render_scale=1,
            style_id=str(visual.get("style_id", "flat_vector")),
            primary_color_rgb=primary,
            accent_color_rgb=accent,
        ),
    )
    return image


def _render_top_down_pixel_preview(item: IllustrationObjectReviewItem) -> Image.Image:
    tile_w, tile_h = _pixel_footprint_for_item(item)
    margin = 2
    base_w = (tile_w + margin * 2) * 16
    base_h = (tile_h + margin * 2) * 16
    sprite = Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sprite, "RGBA")
    _draw_top_down_ground(draw, margin, margin, tile_w, tile_h)
    spec = _pixel_spec(item, tile_xywh=(margin, margin, tile_w, tile_h))
    render_illustration_object(
        spec,
        RenderContext(
            renderer_style=RENDERER_STYLE_TOP_DOWN_PIXEL_RPG,
            draw=draw,
        ),
    )
    scaled = _scale_pixel_sprite(sprite)
    image = _base_preview_image()
    _paste_center(image, scaled)
    return image


def _render_isometric_pixel_preview(item: IllustrationObjectReviewItem) -> Image.Image:
    tile_w, tile_h = _pixel_footprint_for_item(item)
    sprite = Image.new("RGBA", (220, 170), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sprite, "RGBA")

    target_x = sprite.width * 0.5
    target_y = sprite.height * 0.66
    center_x = (tile_w - 1) * 0.5
    center_y = (tile_h - 1) * 0.5
    origin_x = target_x - (center_x - center_y) * 16.0
    origin_y = target_y - (center_x + center_y) * 8.0

    def project_tile_center(tile_xywh: tuple[int, int, int, int], level: int) -> tuple[float, float]:
        x, y, w, h = tile_xywh
        local_x = float(x) + (float(w) - 1.0) * 0.5
        local_y = float(y) + (float(h) - 1.0) * 0.5
        return (
            origin_x + (local_x - local_y) * 16.0,
            origin_y + (local_x + local_y) * 8.0 - float(level) * 12.0,
        )

    for y in range(tile_h):
        for x in range(tile_w):
            cx, cy = project_tile_center((x, y, 1, 1), 0)
            diamond = [(cx, cy - 8), (cx + 16, cy), (cx, cy + 8), (cx - 16, cy)]
            draw.polygon(diamond, fill=(107, 159, 82, 255), outline=(73, 117, 62, 255))
    spec = _pixel_spec(item, tile_xywh=(0, 0, tile_w, tile_h))
    render_illustration_object(
        spec,
        RenderContext(
            renderer_style=RENDERER_STYLE_ISOMETRIC_PIXEL_RPG,
            image=sprite,
            project_tile_center=project_tile_center,
        ),
    )
    image = _base_preview_image()
    cropped = _crop_nonempty(sprite)
    scaled = _scale_pixel_sprite(cropped)
    _paste_center(image, scaled)
    return image


def _pixel_spec(item: IllustrationObjectReviewItem, *, tile_xywh: tuple[int, int, int, int]) -> IllustrationObjectSpec:
    return IllustrationObjectSpec(
        object_id="preview_object",
        object_type=item.object_type,
        public_name=item.public_name,
        tile_xywh=tile_xywh,
        variant_id=item.variant_id,
        semantic_attributes=dict(item.semantic_attributes or {}),
        visual_attributes=dict(item.visual_attributes or {}),
        source_entity_type="illustration_object_review",
    )


def _vector_bbox(object_type: str, renderer_id: str) -> tuple[float, float, float, float]:
    width, height = _PREVIEW_SIZE
    if renderer_id:
        aspect = {
            "construction_equipment": 1.55,
            "construction_material": 1.45,
            "fixture_bench": 1.9,
            "indoor_container": 1.0,
            "indoor_furniture": 1.45,
            "indoor_surface": 1.75,
            "park_equipment": 1.55,
        }.get(renderer_id, 0.62 if "person" in renderer_id or renderer_id == "construction_worker" else 1.2)
    else:
        aspect = aspect_ratio_for_object(object_type)
    max_w = 202.0
    max_h = 150.0
    if aspect >= max_w / max_h:
        obj_w = max_w
        obj_h = max_w / max(0.1, float(aspect))
    else:
        obj_h = max_h
        obj_w = max_h * max(0.1, float(aspect))
    cx = width * 0.5
    cy = height * 0.52
    return (cx - obj_w * 0.5, cy - obj_h * 0.5, cx + obj_w * 0.5, cy + obj_h * 0.5)


def _draw_vector_preview_frame(draw: ImageDraw.ImageDraw, size: tuple[int, int]) -> None:
    w, h = size
    draw.rounded_rectangle((16, 16, w - 16, h - 16), radius=10, fill=(255, 255, 255, 210), outline=(212, 219, 225, 255), width=1)
    draw.ellipse((56, h - 42, w - 56, h - 20), fill=(195, 202, 194, 75))


def _draw_top_down_ground(draw: ImageDraw.ImageDraw, x0: int, y0: int, tile_w: int, tile_h: int) -> None:
    for y in range(tile_h):
        for x in range(tile_w):
            px0 = (x0 + x) * 16
            py0 = (y0 + y) * 16
            fill = (99, 157, 79, 255) if (x + y) % 2 == 0 else (109, 169, 88, 255)
            draw.rectangle((px0, py0, px0 + 15, py0 + 15), fill=fill, outline=(75, 126, 63, 255))


def _scale_pixel_sprite(sprite: Image.Image) -> Image.Image:
    max_w = _PREVIEW_SIZE[0] - 28
    max_h = _PREVIEW_SIZE[1] - 28
    scale = max(1, min(5, max_w // max(1, sprite.width), max_h // max(1, sprite.height)))
    return sprite.resize((sprite.width * scale, sprite.height * scale), Image.Resampling.NEAREST)


def _crop_nonempty(image: Image.Image, pad: int = 6) -> Image.Image:
    bbox = image.getbbox()
    if bbox is None:
        return image
    x0, y0, x1, y1 = bbox
    return image.crop(
        (
            max(0, x0 - int(pad)),
            max(0, y0 - int(pad)),
            min(image.width, x1 + int(pad)),
            min(image.height, y1 + int(pad)),
        )
    )


def _paste_center(background: Image.Image, foreground: Image.Image) -> None:
    x = int(round((background.width - foreground.width) * 0.5))
    y = int(round((background.height - foreground.height) * 0.5))
    background.alpha_composite(foreground, dest=(x, y))


def _base_preview_image() -> Image.Image:
    image = Image.new("RGBA", _PREVIEW_SIZE, (238, 241, 233, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((0, 0, _PREVIEW_SIZE[0], _PREVIEW_SIZE[1]), fill=(238, 241, 233, 255))
    for x in range(0, _PREVIEW_SIZE[0], 26):
        draw.line((x, 0, x, _PREVIEW_SIZE[1]), fill=(220, 226, 217, 110))
    for y in range(0, _PREVIEW_SIZE[1], 26):
        draw.line((0, y, _PREVIEW_SIZE[0], y), fill=(220, 226, 217, 110))
    return image


def _placeholder_image(title: str, detail: str) -> Image.Image:
    image = Image.new("RGBA", _PREVIEW_SIZE, (246, 239, 235, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((18, 18, _PREVIEW_SIZE[0] - 18, _PREVIEW_SIZE[1] - 18), outline=(173, 92, 78, 255), width=2)
    draw.text((30, 48), str(title), fill=(124, 54, 45, 255))
    draw.text((30, 76), _clip_text(str(detail), 38), fill=(124, 54, 45, 255))
    return image


def _catalog_semantic_attributes(entry: CatalogEntry) -> Mapping[str, Any]:
    variant = str(entry.variant_id)
    renderer_id = str(entry.renderer_id)
    attrs: dict[str, Any] = {"family": str(entry.family)}
    if renderer_id == "fixture_bench":
        attrs["fixture_type"] = variant
    elif renderer_id == "park_equipment":
        attrs["equipment_type"] = variant
    elif renderer_id == "construction_material":
        attrs["material_type"] = variant
    elif renderer_id == "construction_equipment":
        attrs["equipment_type"] = variant
    elif renderer_id == "park_person":
        attrs["activity"] = variant
    elif renderer_id == "construction_worker":
        attrs["tool_type"] = "hammer"
    elif renderer_id == "indoor_furniture":
        attrs["furniture_type"] = variant
    elif renderer_id == "indoor_surface":
        attrs["surface_type"] = variant
    elif renderer_id == "indoor_container":
        attrs["container_type"] = variant
    return attrs


def _catalog_visual_attributes(entry: CatalogEntry) -> Mapping[str, Any]:
    renderer_id = str(entry.renderer_id)
    variant = str(entry.variant_id)
    attrs: dict[str, Any] = {"style_id": "flat_vector"}
    if renderer_id == "construction_worker":
        attrs.update(
            {
                "person_variant_id": "worker",
                "hard_hat_color_rgb": (238, 194, 64),
                "vest_color_rgb": (229, 128, 57),
                "primary_color_rgb": (66, 113, 163),
                "accent_color_rgb": (238, 194, 64),
            }
        )
    elif renderer_id == "park_person":
        attrs.update({"person_variant_id": "adult", "primary_color_rgb": (75, 124, 174), "accent_color_rgb": (229, 169, 72)})
    elif renderer_id == "indoor_surface":
        attrs.update(_indoor_surface_visuals(variant))
    elif renderer_id == "indoor_furniture":
        attrs.update(_indoor_furniture_visuals(variant))
    elif renderer_id == "indoor_container":
        attrs.update({"container_style": "woven" if variant == "basket" else "slatted"})
    return attrs


def _indoor_surface_visuals(variant: str) -> Mapping[str, Any]:
    if variant == "shelf":
        return {
            "board_bbox": (50, 52, 210, 70),
            "shelf_style": "brackets",
            "top_fill_rgb": (176, 133, 84),
            "lip_fill_rgb": (116, 82, 54),
        }
    if variant == "counter":
        return {
            "top_fill_rgb": (202, 180, 151),
            "lip_fill_rgb": (129, 105, 80),
            "lip_bottom_y": 122,
        }
    return {"top_fill_rgb": (190, 143, 88), "lip_fill_rgb": (118, 79, 48)}


def _indoor_furniture_visuals(variant: str) -> Mapping[str, Any]:
    if variant == "table":
        return {
            "draw_phase": "all",
            "surface_bbox": (60, 76, 200, 108),
            "rug_bbox": (42, 128, 218, 182),
            "leg_width": 26,
            "table_style": "tapered_legs",
        }
    if variant == "sofa":
        return {"sofa_style": "split_cushions", "fill_rgb": (109, 143, 173), "back_fill_rgb": (129, 164, 191)}
    if variant == "cabinet":
        return {"cabinet_style": "mixed_drawers"}
    return {}


def _vector_visual_attributes(object_type: str, variant_id: str) -> Mapping[str, Any]:
    attrs: dict[str, Any] = {"style_id": "flat_vector"}
    if object_type in {"person", "pedestrian_with_bag"}:
        attrs["gender_id"] = "female" if variant_id in {"vendor", "soldier"} else "male"
        attrs["person_variant_id"] = variant_id or "adult"
    if object_type == "tree" and variant_id:
        attrs["tree_style"] = variant_id
    return attrs


def _default_pixel_visuals(object_type: str) -> Mapping[str, Any]:
    if object_type in {"bridge", "cemetery_gate", "farm_gate", "fence", "iron_fence"}:
        return {"orientation": "horizontal"}
    if object_type == "crop_row":
        return {"crop_style": "wheat"}
    if object_type == "vegetable_patch":
        return {"vegetable_style": "carrot"}
    if object_type == "shelf":
        return {"goods_type": "mixed"}
    if object_type == "produce_bin":
        return {"goods_type": "fruit"}
    if object_type == "table":
        return {"table_shape": "square"}
    if object_type == "chair":
        return {"facing": "down"}
    if object_type == "bed":
        return {"bed_size": "single"}
    if object_type == "fireplace":
        return {"fire_state": "lit"}
    if object_type == "candle":
        return {"flame_state": "lit"}
    if object_type == "room_divider":
        return {"divider_style": "screen"}
    if object_type == "grave_marker":
        return {"marker_style": "rounded"}
    if object_type == "pond":
        return {"pond_shape": "round"}
    if object_type == "ladder":
        return {"orientation": "vertical"}
    if object_type == "mine_cart":
        return {"orientation": "horizontal"}
    if object_type == "rail_track":
        return {"track_shape": "horizontal"}
    if object_type == "stairs":
        return {"stair_direction": "down"}
    if object_type == "floor_switch":
        return {"switch_state": "raised"}
    if object_type == "broken_wall":
        return {"break_style": "cracked"}
    if object_type == "sealed_door":
        return {"door_orientation": "horizontal"}
    if object_type == "brazier":
        return {"fire_state": "lit"}
    return {}


def _object_colors(object_type: str, salt: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    seed = sum((index + 1) * ord(char) for index, char in enumerate(f"{object_type}:{salt}"))
    return choose_object_colors(random.Random(seed), object_type if object_type in OBJECT_TEMPLATES else "apple")


def _pixel_footprint(object_type: str) -> tuple[int, int]:
    return _PIXEL_FOOTPRINTS.get(str(object_type), (1, 1))


def _pixel_footprint_for_item(item: IllustrationObjectReviewItem) -> tuple[int, int]:
    if item.object_type == "domestic_animal":
        animal_type = str(
            (item.semantic_attributes or {}).get(
                "animal_type",
                (item.visual_attributes or {}).get("animal_type", item.variant_label or item.public_name),
            )
        )
        return (2, 1) if animal_type == "cow" else (1, 1)
    if item.object_type == "table":
        return (3, 2) if str((item.visual_attributes or {}).get("table_shape", "")) == "long" else (2, 2)
    if item.object_type == "bed":
        return (3, 3) if str((item.visual_attributes or {}).get("bed_size", "")) == "double" else (2, 3)
    if item.object_type == "sealed_door":
        return (1, 2) if str((item.visual_attributes or {}).get("door_orientation", "")) == "vertical" else (2, 1)
    return _pixel_footprint(item.object_type)


def _pixel_family(object_type: str) -> str:
    if object_type in {"tree", "dead_tree", "flower", "crop_row"}:
        return "plant"
    if object_type == "vegetable_patch":
        return "vegetable"
    if object_type in {"basket", "chest", "jar", "pot", "sack"}:
        return "container"
    if object_type == "domestic_animal":
        return "animal"
    if object_type == "person":
        return "person"
    if object_type in {"archway", "barn", "broken_wall", "castle", "chicken_coop", "church", "coop", "gazebo", "house", "inn", "sealed_door", "shop", "stone_column", "tower", "well", "windmill", "wood_support"}:
        return "structure"
    if object_type == "cave_entrance":
        return "terrain_feature"
    if object_type in {"boulder", "rubble", "stalagmite"}:
        return "obstacle"
    if object_type in {"ore_vein", "crystal_cluster"}:
        return "resource"
    if object_type in {"ladder", "rail_track", "stairs"}:
        return "route_feature"
    if object_type == "mine_cart":
        return "vehicle"
    if object_type in {
        "bed",
        "bench",
        "brazier",
        "bridge",
        "candle",
        "chair",
        "cemetery_gate",
        "counter",
        "farm_gate",
        "fence",
        "fireplace",
        "floor_switch",
        "fountain",
        "grave_marker",
        "iron_fence",
        "lamp_post",
        "market_stall",
        "magic_circle",
        "notice_board",
        "pond",
        "produce_bin",
        "room_divider",
        "rug",
        "scarecrow",
        "shelf",
        "sign",
        "statue",
        "stool",
        "table",
        "torch",
        "trough",
    }:
        return "fixture"
    return "object"


def _pixel_public_name(object_type: str, variant_label: str) -> str:
    if object_type == "domestic_animal" and variant_label:
        return variant_label
    if object_type == "vegetable_patch" and variant_label:
        return variant_label
    return object_type.replace("_", " ")


def _category(family: str) -> tuple[str, str]:
    key = _slug(family or "other")
    labels = {
        "animal": "Animals",
        "container": "Containers",
        "equipment": "Equipment",
        "fixture": "Fixtures",
        "material": "Materials",
        "object": "Objects",
        "obstacle": "Obstacles",
        "person": "People",
        "plant": "Plants",
        "resource": "Resources",
        "route_feature": "Route Features",
        "sky": "Sky",
        "structure": "Structures",
        "terrain_feature": "Terrain Features",
        "vehicle": "Vehicles",
        "vegetable": "Vegetables",
    }
    return key, labels.get(key, key.replace("_", " ").title())


def _tree_rgb(variant_id: str) -> tuple[int, int, int]:
    return {
        "oak": (38, 144, 78),
        "pine": (35, 121, 91),
        "maple": (185, 111, 61),
        "fruit_tree": (51, 142, 82),
    }.get(str(variant_id), (38, 144, 78))


def _make_item_id(*parts: str) -> str:
    return "__".join(_slug(part) for part in parts if str(part))


def _slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip().lower()).strip("_")
    return text or "item"


def _clip_text(value: str, limit: int) -> str:
    text = " ".join(str(value).split())
    if len(text) <= int(limit):
        return text
    return text[: max(0, int(limit) - 3)].rstrip() + "..."


__all__ = [
    "RENDERER_LABELS",
    "VALID_REVIEW_DECISIONS",
    "IllustrationObjectReviewItem",
    "filtered_illustration_object_items",
    "illustration_object_category_tabs",
    "illustration_object_renderer_tabs",
    "illustration_object_review_item",
    "illustration_object_review_items",
    "illustration_object_review_progress",
    "render_illustration_object_review_image",
]
