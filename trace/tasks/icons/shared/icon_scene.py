"""Reusable two-panel icon scene rendering for TRACE icon tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from PIL import Image, ImageColor, ImageDraw

from ...shared.text_rendering import draw_text_centered, load_font
from .icon_noise import NoiseEdit, serialize_icon_noise_edits
from .icon_assets import render_icon_rgba


BBox = Tuple[int, int, int, int]


@dataclass(frozen=True)
class IconInstanceSpec:
    """One icon instance to place into the scene panel."""

    icon_id: str
    rotation_degrees: int = 0
    mirror_x: bool = False
    tint_rgb: Tuple[int, int, int] = (33, 39, 52)
    noise_edits: Tuple[NoiseEdit, ...] = ()
    noise_seed: int | None = None


@dataclass(frozen=True)
class RenderedIconInstance:
    """Trace-ready placement metadata for one rendered icon instance."""

    instance_id: str
    icon_id: str
    panel: str
    bbox_xyxy: Tuple[int, int, int, int]
    rotation_degrees: int
    mirror_x: bool
    tint_rgb: Tuple[int, int, int]
    noise_edits: Tuple[Dict[str, Any], ...] = ()
    noise_seed: int | None = None


@dataclass(frozen=True)
class IconPanelLayout:
    """Resolved geometry for one reference+scene composite image."""

    canvas_width: int
    canvas_height: int
    reference_panel_xyxy: Tuple[int, int, int, int]
    scene_panel_xyxy: Tuple[int, int, int, int]
    reference_content_xyxy: Tuple[int, int, int, int]
    scene_content_xyxy: Tuple[int, int, int, int]


@dataclass(frozen=True)
class RenderedIconScene:
    """Full render output for one icon counting scene."""

    image: Image.Image
    layout: IconPanelLayout
    reference_instance: RenderedIconInstance
    scene_instances: Tuple[RenderedIconInstance, ...]


def _fit_header_band(panel_bbox: BBox, *, padding_px: int, title_font_size_px: int) -> Tuple[BBox, BBox]:
    """Split one panel into title and content rectangles."""

    x0, y0, x1, y1 = panel_bbox
    band_height = max(40, int(round(float(title_font_size_px) * 1.8)))
    title_bbox = (int(x0), int(y0), int(x1), int(min(y1, y0 + band_height)))
    content_bbox = (
        int(x0 + padding_px),
        int(title_bbox[3] + padding_px // 2),
        int(x1 - padding_px),
        int(y1 - padding_px),
    )
    return title_bbox, content_bbox


def resolve_two_panel_layout(
    *,
    canvas_width: int,
    canvas_height: int,
    reference_panel_width_px: int,
    outer_margin_px: int,
    panel_gap_px: int,
    panel_padding_px: int,
    title_font_size_px: int,
) -> IconPanelLayout:
    """Resolve composite-image geometry for reference and scene panels."""

    width = int(canvas_width)
    height = int(canvas_height)
    margin = int(outer_margin_px)
    gap = int(panel_gap_px)
    ref_width = int(reference_panel_width_px)
    if width <= (2 * margin) + gap + ref_width + 120:
        raise ValueError("canvas width is too small for icon two-panel layout")
    if height <= (2 * margin) + 120:
        raise ValueError("canvas height is too small for icon two-panel layout")

    outer_x0 = int(margin)
    outer_y0 = int(margin)
    outer_y1 = int(height - margin)
    ref_panel = (int(outer_x0), int(outer_y0), int(outer_x0 + ref_width), int(outer_y1))
    scene_panel = (int(ref_panel[2] + gap), int(outer_y0), int(width - margin), int(outer_y1))
    _, ref_content = _fit_header_band(ref_panel, padding_px=int(panel_padding_px), title_font_size_px=int(title_font_size_px))
    _, scene_content = _fit_header_band(scene_panel, padding_px=int(panel_padding_px), title_font_size_px=int(title_font_size_px))
    return IconPanelLayout(
        canvas_width=width,
        canvas_height=height,
        reference_panel_xyxy=ref_panel,
        scene_panel_xyxy=scene_panel,
        reference_content_xyxy=ref_content,
        scene_content_xyxy=scene_content,
    )


def _panel_title_center(panel_bbox: BBox, *, title_font_size_px: int) -> Tuple[float, float]:
    """Return the centered title anchor for one panel."""

    x0, y0, x1, _ = panel_bbox
    band_height = max(40, int(round(float(title_font_size_px) * 1.8)))
    return (0.5 * float(x0 + x1), float(y0) + (0.5 * float(band_height)))


def draw_two_panel_panels(
    *,
    image: Image.Image,
    layout: IconPanelLayout,
    background_rgb: Tuple[int, int, int],
    panel_fill_rgb: Tuple[int, int, int],
    panel_border_rgb: Tuple[int, int, int],
    title_color_rgb: Tuple[int, int, int],
    corner_radius_px: int,
    title_font_size_px: int,
    reference_title: str = "Reference",
    scene_title: str = "Scene",
) -> None:
    """Draw panel chrome and titles on one icon scene image."""

    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, image.size[0], image.size[1]), fill=tuple(int(v) for v in background_rgb))
    for panel_bbox, title in (
        (layout.reference_panel_xyxy, str(reference_title)),
        (layout.scene_panel_xyxy, str(scene_title)),
    ):
        draw.rounded_rectangle(
            panel_bbox,
            radius=max(0, int(corner_radius_px)),
            fill=tuple(int(v) for v in panel_fill_rgb),
            outline=tuple(int(v) for v in panel_border_rgb),
            width=2,
        )
        draw_text_centered(
            draw,
            text=str(title),
            center=_panel_title_center(panel_bbox, title_font_size_px=int(title_font_size_px)),
            font=load_font(int(title_font_size_px), bold=True),
            fill=tuple(int(v) for v in title_color_rgb),
            stroke_fill=tuple(int(v) for v in panel_fill_rgb),
            stroke_width=2,
        )


def _grid_slots(content_bbox: BBox, *, rows: int, cols: int, inner_padding_px: int) -> List[BBox]:
    """Return one stable grid of slot rectangles inside the scene content box."""

    x0, y0, x1, y1 = content_bbox
    width = max(1, int(x1 - x0))
    height = max(1, int(y1 - y0))
    cell_w = width / float(max(1, int(cols)))
    cell_h = height / float(max(1, int(rows)))
    slots: List[BBox] = []
    pad = max(0, int(inner_padding_px))
    for row in range(int(rows)):
        for col in range(int(cols)):
            slot_x0 = int(round(float(x0) + (float(col) * cell_w))) + pad
            slot_y0 = int(round(float(y0) + (float(row) * cell_h))) + pad
            slot_x1 = int(round(float(x0) + (float(col + 1) * cell_w))) - pad
            slot_y1 = int(round(float(y0) + (float(row + 1) * cell_h))) - pad
            slots.append((slot_x0, slot_y0, slot_x1, slot_y1))
    return slots


def _centered_paste_bbox(
    *,
    sprite_size: Tuple[int, int],
    slot_bbox: BBox,
    jitter_px: int,
    rng,
) -> Tuple[int, int, int, int]:
    """Resolve one paste bbox inside a slot with bounded center jitter."""

    slot_x0, slot_y0, slot_x1, slot_y1 = slot_bbox
    sprite_w, sprite_h = int(sprite_size[0]), int(sprite_size[1])
    slot_w = max(1, int(slot_x1 - slot_x0))
    slot_h = max(1, int(slot_y1 - slot_y0))
    if sprite_w > slot_w or sprite_h > slot_h:
        raise ValueError("sprite does not fit inside icon slot")
    slack_x = max(0, int(slot_w - sprite_w))
    slack_y = max(0, int(slot_h - sprite_h))
    jitter_x = min(int(jitter_px), slack_x // 2)
    jitter_y = min(int(jitter_px), slack_y // 2)
    cx = int(slot_x0 + (slot_w // 2))
    cy = int(slot_y0 + (slot_h // 2))
    if jitter_x > 0:
        cx += int(rng.randint(-jitter_x, jitter_x))
    if jitter_y > 0:
        cy += int(rng.randint(-jitter_y, jitter_y))
    paste_x0 = int(max(slot_x0, min(slot_x1 - sprite_w, cx - (sprite_w // 2))))
    paste_y0 = int(max(slot_y0, min(slot_y1 - sprite_h, cy - (sprite_h // 2))))
    return (paste_x0, paste_y0, int(paste_x0 + sprite_w), int(paste_y0 + sprite_h))


def _box_area(box: BBox) -> float:
    """Return the area of one `xyxy` box."""

    return max(0.0, float(box[2] - box[0])) * max(0.0, float(box[3] - box[1]))


def _intersection_area(left: BBox, right: BBox) -> float:
    """Return the intersection area between two `xyxy` boxes."""

    ix0 = max(int(left[0]), int(right[0]))
    iy0 = max(int(left[1]), int(right[1]))
    ix1 = min(int(left[2]), int(right[2]))
    iy1 = min(int(left[3]), int(right[3]))
    return max(0.0, float(ix1 - ix0)) * max(0.0, float(iy1 - iy0))


def _overlap_fraction_smaller(left: BBox, right: BBox) -> float:
    """Return overlap normalized by the smaller box area."""

    inter = _intersection_area(left, right)
    if inter <= 0.0:
        return 0.0
    return float(inter) / max(1e-9, min(_box_area(left), _box_area(right)))


def _max_overlap_with_existing(box: BBox, existing: Sequence[BBox]) -> float:
    """Return the maximum smaller-area overlap ratio against placed icons."""

    if not existing:
        return 0.0
    return max(float(_overlap_fraction_smaller(box, other)) for other in existing)


def _random_paste_bbox(
    *,
    sprite_size: Tuple[int, int],
    content_bbox: BBox,
    rng,
) -> BBox:
    """Resolve one random paste bbox fully inside the scene content rectangle."""

    x0, y0, x1, y1 = content_bbox
    sprite_w, sprite_h = int(sprite_size[0]), int(sprite_size[1])
    if int(sprite_w) > int(x1 - x0) or int(sprite_h) > int(y1 - y0):
        raise ValueError("sprite does not fit inside scene content bounds")
    paste_x0 = int(rng.randint(int(x0), int(x1 - sprite_w)))
    paste_y0 = int(rng.randint(int(y0), int(y1 - sprite_h)))
    return (int(paste_x0), int(paste_y0), int(paste_x0 + sprite_w), int(paste_y0 + sprite_h))


def sort_bboxes_reading_order(bboxes: Iterable[Sequence[int | float]]) -> List[List[int]]:
    """Return one deterministic top-to-bottom/left-to-right bbox list."""

    normalized = [
        [int(round(float(box[0]))), int(round(float(box[1]))), int(round(float(box[2]))), int(round(float(box[3])))]
        for box in bboxes
    ]
    return [
        list(box)
        for box in sorted(normalized, key=lambda item: (int(item[1]), int(item[0]), int(item[3]), int(item[2])))
    ]


def render_two_panel_icon_scene(
    *,
    rng,
    reference_icon: IconInstanceSpec,
    scene_icons: Sequence[IconInstanceSpec],
    canvas_width: int,
    canvas_height: int,
    reference_panel_width_px: int,
    outer_margin_px: int,
    panel_gap_px: int,
    panel_padding_px: int,
    panel_corner_radius_px: int,
    scene_icon_size_min_px: int,
    scene_icon_size_max_px: int,
    reference_icon_size_px: int,
    scene_max_overlap_fraction: float,
    scene_placement_max_attempts: int,
    scene_size_shrink_rounds: int,
    scene_size_shrink_factor: float,
    background_rgb: Tuple[int, int, int],
    panel_fill_rgb: Tuple[int, int, int],
    panel_border_rgb: Tuple[int, int, int],
    title_color_rgb: Tuple[int, int, int],
    title_font_size_px: int,
) -> RenderedIconScene:
    """Render one reference+scene icon image with random overlap-capped placement."""

    if not scene_icons:
        raise ValueError("scene_icons must contain at least one icon")
    layout = resolve_two_panel_layout(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        reference_panel_width_px=int(reference_panel_width_px),
        outer_margin_px=int(outer_margin_px),
        panel_gap_px=int(panel_gap_px),
        panel_padding_px=int(panel_padding_px),
        title_font_size_px=int(title_font_size_px),
    )

    image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
    draw_two_panel_panels(
        image=image,
        layout=layout,
        background_rgb=background_rgb,
        panel_fill_rgb=panel_fill_rgb,
        panel_border_rgb=panel_border_rgb,
        title_color_rgb=title_color_rgb,
        corner_radius_px=int(panel_corner_radius_px),
        title_font_size_px=int(title_font_size_px),
    )

    reference_rgba = render_icon_rgba(
        icon_id=str(reference_icon.icon_id),
        size_px=int(reference_icon_size_px),
        tint_rgb=tuple(int(value) for value in reference_icon.tint_rgb),
        rotation_degrees=int(reference_icon.rotation_degrees),
        mirror_x=bool(reference_icon.mirror_x),
        noise_edits=tuple(reference_icon.noise_edits),
        noise_seed=reference_icon.noise_seed,
    )
    ref_x0, ref_y0, ref_x1, ref_y1 = layout.reference_content_xyxy
    ref_w = int(reference_rgba.size[0])
    ref_h = int(reference_rgba.size[1])
    ref_box = (
        int(ref_x0 + max(0, (ref_x1 - ref_x0 - ref_w) // 2)),
        int(ref_y0 + max(0, (ref_y1 - ref_y0 - ref_h) // 2)),
    )
    image.alpha_composite(reference_rgba, ref_box)
    reference_instance = RenderedIconInstance(
        instance_id="reference_icon",
        icon_id=str(reference_icon.icon_id),
        panel="reference",
        bbox_xyxy=(int(ref_box[0]), int(ref_box[1]), int(ref_box[0] + ref_w), int(ref_box[1] + ref_h)),
        rotation_degrees=int(reference_icon.rotation_degrees) % 360,
        mirror_x=bool(reference_icon.mirror_x),
        tint_rgb=tuple(int(value) for value in reference_icon.tint_rgb),
        noise_edits=serialize_icon_noise_edits(reference_icon.noise_edits),
        noise_seed=None if reference_icon.noise_seed is None else int(reference_icon.noise_seed),
    )

    rendered_scene_icons: List[RenderedIconInstance] = []
    placed_bboxes: List[BBox] = []
    min_size = max(16, int(scene_icon_size_min_px))
    max_size = max(min_size, int(scene_icon_size_max_px))
    scene_content_bbox = tuple(int(value) for value in layout.scene_content_xyxy)
    max_overlap_fraction = max(0.0, min(1.0, float(scene_max_overlap_fraction)))
    placement_attempts = max(1, int(scene_placement_max_attempts))
    shrink_rounds = max(0, int(scene_size_shrink_rounds))
    shrink_factor = max(0.1, min(1.0, float(scene_size_shrink_factor)))
    for index, spec in enumerate(scene_icons):
        content_w = max(1, int(scene_content_bbox[2] - scene_content_bbox[0]))
        content_h = max(1, int(scene_content_bbox[3] - scene_content_bbox[1]))
        current_max_size = min(int(max_size), int(content_w), int(content_h))
        sprite = None
        paste_bbox = None
        for shrink_round in range(int(shrink_rounds) + 1):
            round_max_size = max(int(min_size), int(round(current_max_size * (shrink_factor**shrink_round))))
            if round_max_size < int(min_size):
                round_max_size = int(min_size)
            for _ in range(int(placement_attempts)):
                nominal_size = int(rng.randint(int(min_size), int(round_max_size)))
                candidate_sprite = render_icon_rgba(
                    icon_id=str(spec.icon_id),
                    size_px=int(nominal_size),
                    tint_rgb=tuple(int(value) for value in spec.tint_rgb),
                    rotation_degrees=int(spec.rotation_degrees),
                    mirror_x=bool(spec.mirror_x),
                    noise_edits=tuple(spec.noise_edits),
                    noise_seed=spec.noise_seed,
                )
                try:
                    candidate_bbox = _random_paste_bbox(
                        sprite_size=candidate_sprite.size,
                        content_bbox=scene_content_bbox,
                        rng=rng,
                    )
                except ValueError:
                    continue
                if float(_max_overlap_with_existing(candidate_bbox, placed_bboxes)) > float(max_overlap_fraction):
                    continue
                sprite = candidate_sprite
                paste_bbox = candidate_bbox
                break
            if sprite is not None and paste_bbox is not None:
                break
        if sprite is None or paste_bbox is None:
            raise ValueError("failed to place icon within scene content under overlap constraints")
        image.alpha_composite(sprite, (int(paste_bbox[0]), int(paste_bbox[1])))
        placed_bboxes.append(tuple(int(value) for value in paste_bbox))
        rendered_scene_icons.append(
            RenderedIconInstance(
                instance_id=f"scene_icon_{int(index)}",
                icon_id=str(spec.icon_id),
                panel="scene",
                bbox_xyxy=tuple(int(value) for value in paste_bbox),
                rotation_degrees=int(spec.rotation_degrees) % 360,
                mirror_x=bool(spec.mirror_x),
                tint_rgb=tuple(int(value) for value in spec.tint_rgb),
                noise_edits=serialize_icon_noise_edits(spec.noise_edits),
                noise_seed=None if spec.noise_seed is None else int(spec.noise_seed),
            )
        )

    return RenderedIconScene(
        image=image.convert("RGB"),
        layout=layout,
        reference_instance=reference_instance,
        scene_instances=tuple(rendered_scene_icons),
    )


def panel_geometry_to_trace(layout: IconPanelLayout) -> Dict[str, Any]:
    """Return one JSON-serializable panel-geometry payload."""

    return {
        "canvas_size": [int(layout.canvas_width), int(layout.canvas_height)],
        "reference_panel_xyxy": list(layout.reference_panel_xyxy),
        "scene_panel_xyxy": list(layout.scene_panel_xyxy),
        "reference_content_xyxy": list(layout.reference_content_xyxy),
        "scene_content_xyxy": list(layout.scene_content_xyxy),
    }


__all__ = [
    "IconInstanceSpec",
    "IconPanelLayout",
    "RenderedIconInstance",
    "RenderedIconScene",
    "draw_two_panel_panels",
    "panel_geometry_to_trace",
    "render_two_panel_icon_scene",
    "resolve_two_panel_layout",
    "sort_bboxes_reading_order",
]
