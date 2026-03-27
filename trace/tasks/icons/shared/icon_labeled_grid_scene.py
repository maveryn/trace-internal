"""Reusable two-panel labeled-grid chrome for icon relation tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font
from .icon_grid_scene import resolve_grid_cell_slots
from .icon_scene import IconPanelLayout, draw_two_panel_panels, resolve_two_panel_layout


BBox = Tuple[int, int, int, int]


@dataclass(frozen=True)
class PreparedReferenceGridCell:
    """Resolved reference-cell frame and content rectangles."""

    cell_bbox_xyxy: BBox
    content_bbox_xyxy: BBox


@dataclass(frozen=True)
class PreparedSceneGridCell:
    """Resolved scene-cell frame and content rectangles for one labeled cell."""

    label: str
    cell_bbox_xyxy: BBox
    content_bbox_xyxy: BBox


@dataclass(frozen=True)
class PreparedTwoPanelLabeledGridScene:
    """Prepared canvas + grid geometry for reference-vs-scene cell tasks."""

    image: Image.Image
    layout: IconPanelLayout
    reference_cell: PreparedReferenceGridCell
    scene_cells: Tuple[PreparedSceneGridCell, ...]


def _centered_square_bbox(bbox: BBox) -> BBox:
    """Return the largest centered square fully contained in `bbox`."""

    x0, y0, x1, y1 = [int(value) for value in bbox]
    width = max(1, int(x1 - x0))
    height = max(1, int(y1 - y0))
    side = int(max(1, min(width, height)))
    dx = int((width - side) // 2)
    dy = int((height - side) // 2)
    return (
        int(x0 + dx),
        int(y0 + dy),
        int(x0 + dx + side),
        int(y0 + dy + side),
    )


def prepare_two_panel_labeled_grid_scene(
    *,
    scene_labels: Sequence[str],
    canvas_width: int,
    canvas_height: int,
    reference_panel_width_px: int,
    outer_margin_px: int,
    panel_gap_px: int,
    panel_padding_px: int,
    panel_corner_radius_px: int,
    panel_title_font_size_px: int,
    background_rgb: Tuple[int, int, int],
    panel_fill_rgb: Tuple[int, int, int],
    panel_border_rgb: Tuple[int, int, int],
    title_color_rgb: Tuple[int, int, int],
    cell_padding_px: int,
    cell_border_rgb: Tuple[int, int, int],
    cell_label_color_rgb: Tuple[int, int, int],
    cell_label_font_size_px: int,
    cell_corner_radius_px: int = 12,
    reference_cell_inset_px: int = 12,
    reference_content_padding_px: int = 12,
    scene_content_side_padding_px: int = 12,
    scene_content_bottom_padding_px: int = 12,
    scene_content_top_offset_px: int = 40,
    reference_square_cell: bool = False,
    scene_square_cells: bool = False,
    reference_title: str = "Reference",
    scene_title: str = "Scene",
) -> PreparedTwoPanelLabeledGridScene:
    """Draw two-panel grid chrome and return resolved cell geometry."""

    labels = [str(value) for value in scene_labels]
    if not labels:
        raise ValueError("scene_labels must contain at least one label")

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
        background_rgb=tuple(int(v) for v in background_rgb),
        panel_fill_rgb=tuple(int(v) for v in panel_fill_rgb),
        panel_border_rgb=tuple(int(v) for v in panel_border_rgb),
        title_color_rgb=tuple(int(v) for v in title_color_rgb),
        corner_radius_px=int(panel_corner_radius_px),
        title_font_size_px=int(panel_title_font_size_px),
        reference_title=str(reference_title),
        scene_title=str(scene_title),
    )

    draw = ImageDraw.Draw(image)
    label_font = load_font(int(cell_label_font_size_px), bold=True)

    ref_x0, ref_y0, ref_x1, ref_y1 = [int(value) for value in layout.reference_content_xyxy]
    reference_cell_bbox = (
        int(ref_x0 + int(reference_cell_inset_px)),
        int(ref_y0 + int(reference_cell_inset_px)),
        int(ref_x1 - int(reference_cell_inset_px)),
        int(ref_y1 - int(reference_cell_inset_px)),
    )
    if bool(reference_square_cell):
        reference_cell_bbox = _centered_square_bbox(reference_cell_bbox)
    draw.rounded_rectangle(
        reference_cell_bbox,
        radius=max(0, int(cell_corner_radius_px)),
        outline=tuple(int(v) for v in cell_border_rgb),
        width=2,
        fill=tuple(int(v) for v in panel_fill_rgb),
    )
    reference_content_bbox = (
        int(reference_cell_bbox[0] + int(reference_content_padding_px)),
        int(reference_cell_bbox[1] + int(reference_content_padding_px)),
        int(reference_cell_bbox[2] - int(reference_content_padding_px)),
        int(reference_cell_bbox[3] - int(reference_content_padding_px)),
    )

    scene_cell_slots = resolve_grid_cell_slots(
        tuple(int(value) for value in layout.scene_content_xyxy),
        cell_count=len(labels),
        cell_padding_px=int(cell_padding_px),
    )
    scene_cells = []
    for label, cell_bbox in zip(labels, scene_cell_slots):
        resolved_cell_bbox = _centered_square_bbox(cell_bbox) if bool(scene_square_cells) else tuple(
            int(value) for value in cell_bbox
        )
        draw.rounded_rectangle(
            resolved_cell_bbox,
            radius=max(0, int(cell_corner_radius_px)),
            outline=tuple(int(v) for v in cell_border_rgb),
            width=2,
            fill=tuple(int(v) for v in panel_fill_rgb),
        )
        draw.text(
            (int(resolved_cell_bbox[0] + 16), int(resolved_cell_bbox[1] + 14)),
            str(label),
            font=label_font,
            fill=tuple(int(v) for v in cell_label_color_rgb),
        )
        scene_cells.append(
            PreparedSceneGridCell(
                label=str(label),
                cell_bbox_xyxy=tuple(int(value) for value in resolved_cell_bbox),
                content_bbox_xyxy=tuple(
                    int(value)
                    for value in (
                        _centered_square_bbox(
                            (
                                int(resolved_cell_bbox[0] + int(scene_content_side_padding_px)),
                                int(resolved_cell_bbox[1] + int(scene_content_top_offset_px)),
                                int(resolved_cell_bbox[2] - int(scene_content_side_padding_px)),
                                int(resolved_cell_bbox[3] - int(scene_content_bottom_padding_px)),
                            )
                        )
                        if bool(scene_square_cells)
                        else (
                            int(resolved_cell_bbox[0] + int(scene_content_side_padding_px)),
                            int(resolved_cell_bbox[1] + int(scene_content_top_offset_px)),
                            int(resolved_cell_bbox[2] - int(scene_content_side_padding_px)),
                            int(resolved_cell_bbox[3] - int(scene_content_bottom_padding_px)),
                        )
                    )
                ),
            )
        )

    return PreparedTwoPanelLabeledGridScene(
        image=image,
        layout=layout,
        reference_cell=PreparedReferenceGridCell(
            cell_bbox_xyxy=tuple(int(value) for value in reference_cell_bbox),
            content_bbox_xyxy=tuple(int(value) for value in reference_content_bbox),
        ),
        scene_cells=tuple(scene_cells),
    )


__all__ = [
    "PreparedReferenceGridCell",
    "PreparedSceneGridCell",
    "PreparedTwoPanelLabeledGridScene",
    "prepare_two_panel_labeled_grid_scene",
]
