"""Reusable reference-pair plus labeled scene-grid rendering for icon tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font
from .icon_assets import render_icon_transformed_rgba
from .icon_grid_scene import resolve_grid_cell_slots
from .icon_noise import NoiseEdit, serialize_icon_noise_edits
from .icon_scene import IconPanelLayout, draw_two_panel_panels, panel_geometry_to_trace, resolve_two_panel_layout


BBox = Tuple[int, int, int, int]


@dataclass(frozen=True)
class IconPairSpec:
    """One before/after icon pair to render in a labeled scene cell."""

    icon_id: str
    transform_id: str
    tint_rgb: Tuple[int, int, int]
    left_noise_edits: Tuple[NoiseEdit, ...] = ()
    left_noise_seed: int | None = None
    right_noise_edits: Tuple[NoiseEdit, ...] = ()
    right_noise_seed: int | None = None


@dataclass(frozen=True)
class RenderedReferencePair:
    """Rendered metadata for the left-panel reference pair."""

    icon_id: str
    transform_id: str
    tint_rgb: Tuple[int, int, int]
    left_bbox_xyxy: BBox
    right_bbox_xyxy: BBox
    left_noise_edits: Tuple[Dict[str, Any], ...]
    left_noise_seed: int | None
    right_noise_edits: Tuple[Dict[str, Any], ...]
    right_noise_seed: int | None


@dataclass(frozen=True)
class RenderedScenePairCell:
    """Rendered metadata for one labeled scene cell."""

    label: str
    icon_id: str
    transform_id: str
    tint_rgb: Tuple[int, int, int]
    cell_bbox_xyxy: BBox
    left_bbox_xyxy: BBox
    right_bbox_xyxy: BBox
    left_noise_edits: Tuple[Dict[str, Any], ...]
    left_noise_seed: int | None
    right_noise_edits: Tuple[Dict[str, Any], ...]
    right_noise_seed: int | None


@dataclass(frozen=True)
class RenderedIconPairGridScene:
    """Complete rendered output for one reference-pair transformation scene."""

    image: Image.Image
    layout: IconPanelLayout
    reference_pair: RenderedReferencePair
    scene_cells: Tuple[RenderedScenePairCell, ...]


def _draw_arrow(draw: ImageDraw.ImageDraw, *, left_x: float, right_x: float, center_y: float, color_rgb: Tuple[int, int, int], stroke_px: int) -> None:
    """Draw a simple rightward arrow between two icons."""

    mid_left = int(round(float(left_x)))
    mid_right = int(round(float(right_x)))
    cy = int(round(float(center_y)))
    width = max(2, int(stroke_px))
    head = max(8, width * 3)
    draw.line((mid_left, cy, mid_right - head, cy), fill=tuple(int(v) for v in color_rgb), width=width)
    draw.polygon(
        [
            (mid_right - head, cy - head // 2),
            (mid_right - head, cy + head // 2),
            (mid_right, cy),
        ],
        fill=tuple(int(v) for v in color_rgb),
    )


def _draw_pair_in_box(
    *,
    image: Image.Image,
    pair_spec: IconPairSpec,
    outer_bbox: BBox,
    icon_size_px: int,
    arrow_color_rgb: Tuple[int, int, int],
    arrow_stroke_px: int,
) -> Tuple[BBox, BBox]:
    """Draw one before/after pair inside a target box and return both icon boxes."""

    left_icon = render_icon_transformed_rgba(
        icon_id=str(pair_spec.icon_id),
        size_px=int(icon_size_px),
        tint_rgb=tuple(int(v) for v in pair_spec.tint_rgb),
        transform_id="identity",
        noise_edits=tuple(pair_spec.left_noise_edits),
        noise_seed=pair_spec.left_noise_seed,
    )
    right_icon = render_icon_transformed_rgba(
        icon_id=str(pair_spec.icon_id),
        size_px=int(icon_size_px),
        tint_rgb=tuple(int(v) for v in pair_spec.tint_rgb),
        transform_id=str(pair_spec.transform_id),
        noise_edits=tuple(pair_spec.right_noise_edits),
        noise_seed=pair_spec.right_noise_seed,
    )
    x0, y0, x1, y1 = outer_bbox
    left_w, left_h = left_icon.size
    right_w, right_h = right_icon.size
    icon_gap = max(12, int(round(0.22 * float(icon_size_px))))
    arrow_gap = max(18, int(round(0.32 * float(icon_size_px))))
    total_w = int(left_w + icon_gap + arrow_gap + right_w)
    total_h = int(max(left_h, right_h))
    if total_w > int(x1 - x0) or total_h > int(y1 - y0):
        raise ValueError("pair does not fit inside target box")
    pair_x0 = int(x0 + max(0, ((x1 - x0) - total_w) // 2))
    pair_y0 = int(y0 + max(0, ((y1 - y0) - total_h) // 2))
    left_y0 = int(pair_y0 + max(0, (total_h - left_h) // 2))
    right_y0 = int(pair_y0 + max(0, (total_h - right_h) // 2))
    left_box = (int(pair_x0), int(left_y0), int(pair_x0 + left_w), int(left_y0 + left_h))
    right_x0 = int(pair_x0 + left_w + icon_gap + arrow_gap)
    right_box = (int(right_x0), int(right_y0), int(right_x0 + right_w), int(right_y0 + right_h))
    image.alpha_composite(left_icon, (int(left_box[0]), int(left_box[1])))
    image.alpha_composite(right_icon, (int(right_box[0]), int(right_box[1])))
    draw = ImageDraw.Draw(image)
    _draw_arrow(
        draw,
        left_x=float(left_box[2] + (icon_gap // 2)),
        right_x=float(right_box[0] - (icon_gap // 2)),
        center_y=float(pair_y0 + (total_h / 2.0)),
        color_rgb=tuple(int(v) for v in arrow_color_rgb),
        stroke_px=int(arrow_stroke_px),
    )
    return left_box, right_box


def render_two_panel_icon_pair_grid_scene(
    *,
    reference_pair: IconPairSpec,
    scene_pairs: Sequence[IconPairSpec],
    scene_labels: Sequence[str],
    canvas_width: int,
    canvas_height: int,
    reference_panel_width_px: int,
    outer_margin_px: int,
    panel_gap_px: int,
    panel_padding_px: int,
    panel_corner_radius_px: int,
    cell_padding_px: int,
    scene_icon_size_min_px: int,
    scene_icon_size_max_px: int,
    reference_icon_size_px: int,
    pair_arrow_stroke_px: int,
    cell_label_font_size_px: int,
    panel_title_font_size_px: int,
    background_rgb: Tuple[int, int, int],
    panel_fill_rgb: Tuple[int, int, int],
    panel_border_rgb: Tuple[int, int, int],
    title_color_rgb: Tuple[int, int, int],
    cell_border_rgb: Tuple[int, int, int],
    cell_label_color_rgb: Tuple[int, int, int],
    arrow_color_rgb: Tuple[int, int, int],
) -> RenderedIconPairGridScene:
    """Render one reference-pair plus labeled scene-grid image."""

    if len(scene_pairs) != len(scene_labels):
        raise ValueError("scene pair specs and labels must have the same length")
    if not scene_pairs:
        raise ValueError("scene_pairs must contain at least one cell")

    layout = resolve_two_panel_layout(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        reference_panel_width_px=int(reference_panel_width_px),
        outer_margin_px=int(outer_margin_px),
        panel_gap_px=int(panel_gap_px),
        panel_padding_px=int(panel_padding_px),
        title_font_size_px=int(panel_title_font_size_px),
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
        title_font_size_px=int(panel_title_font_size_px),
        reference_title="Reference",
        scene_title="Scene",
    )

    reference_left_box, reference_right_box = _draw_pair_in_box(
        image=image,
        pair_spec=reference_pair,
        outer_bbox=tuple(int(value) for value in layout.reference_content_xyxy),
        icon_size_px=int(reference_icon_size_px),
        arrow_color_rgb=tuple(int(v) for v in arrow_color_rgb),
        arrow_stroke_px=int(pair_arrow_stroke_px),
    )

    slots = resolve_grid_cell_slots(
        tuple(int(value) for value in layout.scene_content_xyxy),
        cell_count=len(scene_pairs),
        cell_padding_px=int(cell_padding_px),
    )
    rendered_cells: List[RenderedScenePairCell] = []
    label_font = load_font(int(cell_label_font_size_px), bold=True)
    draw = ImageDraw.Draw(image)
    scene_min_size = max(20, int(scene_icon_size_min_px))
    scene_max_size = max(scene_min_size, int(scene_icon_size_max_px))
    for label, pair_spec, cell_bbox in zip(scene_labels, scene_pairs, slots):
        draw.rounded_rectangle(
            cell_bbox,
            radius=12,
            outline=tuple(int(v) for v in cell_border_rgb),
            width=2,
            fill=tuple(int(v) for v in panel_fill_rgb),
        )
        label_x = int(cell_bbox[0] + 16)
        label_y = int(cell_bbox[1] + 14)
        draw.text((label_x, label_y), str(label), font=label_font, fill=tuple(int(v) for v in cell_label_color_rgb))
        pair_bbox = (
            int(cell_bbox[0] + 12),
            int(cell_bbox[1] + 40),
            int(cell_bbox[2] - 12),
            int(cell_bbox[3] - 12),
        )
        pair_span_w = max(1, int(pair_bbox[2] - pair_bbox[0]))
        pair_span_h = max(1, int(pair_bbox[3] - pair_bbox[1]))
        icon_cap_from_width = max(20, int((pair_span_w - 46) // 2))
        icon_cap_from_height = max(20, int(pair_span_h))
        icon_size = min(scene_max_size, icon_cap_from_width, icon_cap_from_height)
        icon_size = max(scene_min_size, icon_size)
        left_box, right_box = _draw_pair_in_box(
            image=image,
            pair_spec=pair_spec,
            outer_bbox=pair_bbox,
            icon_size_px=int(icon_size),
            arrow_color_rgb=tuple(int(v) for v in arrow_color_rgb),
            arrow_stroke_px=int(pair_arrow_stroke_px),
        )
        rendered_cells.append(
            RenderedScenePairCell(
                label=str(label),
                icon_id=str(pair_spec.icon_id),
                transform_id=str(pair_spec.transform_id),
                tint_rgb=tuple(int(v) for v in pair_spec.tint_rgb),
                cell_bbox_xyxy=tuple(int(v) for v in cell_bbox),
                left_bbox_xyxy=tuple(int(v) for v in left_box),
                right_bbox_xyxy=tuple(int(v) for v in right_box),
                left_noise_edits=serialize_icon_noise_edits(pair_spec.left_noise_edits),
                left_noise_seed=None if pair_spec.left_noise_seed is None else int(pair_spec.left_noise_seed),
                right_noise_edits=serialize_icon_noise_edits(pair_spec.right_noise_edits),
                right_noise_seed=None if pair_spec.right_noise_seed is None else int(pair_spec.right_noise_seed),
            )
        )

    rendered_reference = RenderedReferencePair(
        icon_id=str(reference_pair.icon_id),
        transform_id=str(reference_pair.transform_id),
        tint_rgb=tuple(int(v) for v in reference_pair.tint_rgb),
        left_bbox_xyxy=tuple(int(v) for v in reference_left_box),
        right_bbox_xyxy=tuple(int(v) for v in reference_right_box),
        left_noise_edits=serialize_icon_noise_edits(reference_pair.left_noise_edits),
        left_noise_seed=None if reference_pair.left_noise_seed is None else int(reference_pair.left_noise_seed),
        right_noise_edits=serialize_icon_noise_edits(reference_pair.right_noise_edits),
        right_noise_seed=None if reference_pair.right_noise_seed is None else int(reference_pair.right_noise_seed),
    )
    return RenderedIconPairGridScene(
        image=image.convert("RGB"),
        layout=layout,
        reference_pair=rendered_reference,
        scene_cells=tuple(rendered_cells),
    )


__all__ = [
    "IconPairSpec",
    "RenderedIconPairGridScene",
    "RenderedReferencePair",
    "RenderedScenePairCell",
    "panel_geometry_to_trace",
    "render_two_panel_icon_pair_grid_scene",
]
