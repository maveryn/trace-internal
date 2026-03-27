"""Reusable reference-plus-sequence scene rendering for icon sequence tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import draw_text_centered, load_font
from .icon_assets import render_icon_rgba
from .icon_grid_scene import resolve_horizontal_row_slots
from .icon_noise import NoiseEdit, serialize_icon_noise_edits
from .icon_scene import (
    IconInstanceSpec,
    IconPanelLayout,
    RenderedIconInstance,
    draw_two_panel_panels,
    max_overlap_with_existing,
    random_paste_bbox,
    resolve_two_panel_layout,
)


BBox = Tuple[int, int, int, int]


@dataclass(frozen=True)
class IconSequenceCellSpec:
    """One sequence cell containing zero or more icon instances."""

    icon_instances: Tuple[IconInstanceSpec, ...] = ()
    is_missing: bool = False


@dataclass(frozen=True)
class RenderedSequenceCell:
    """Rendered metadata for one scene sequence cell."""

    cell_index: int
    cell_bbox_xyxy: BBox
    is_missing: bool
    icon_instances: Tuple[RenderedIconInstance, ...]


@dataclass(frozen=True)
class RenderedIconSequenceScene:
    """Complete rendered output for one reference-plus-sequence icon scene."""

    image: Image.Image
    layout: IconPanelLayout
    reference_instance: RenderedIconInstance
    scene_cells: Tuple[RenderedSequenceCell, ...]


def _render_reference_icon(
    *,
    image: Image.Image,
    reference_icon: IconInstanceSpec,
    content_bbox: BBox,
    nominal_size_px: int,
) -> RenderedIconInstance:
    """Render the left-panel reference icon and return its trace metadata."""

    sprite = render_icon_rgba(
        icon_id=str(reference_icon.icon_id),
        size_px=int(reference_icon.nominal_size_px if reference_icon.nominal_size_px is not None else nominal_size_px),
        tint_rgb=tuple(int(value) for value in reference_icon.tint_rgb),
        rotation_degrees=int(reference_icon.rotation_degrees),
        mirror_x=bool(reference_icon.mirror_x),
        noise_edits=tuple(reference_icon.noise_edits),
        noise_seed=reference_icon.noise_seed,
    )
    x0, y0, x1, y1 = content_bbox
    sprite_w, sprite_h = sprite.size
    paste_x0 = int(x0 + max(0, ((x1 - x0) - sprite_w) // 2))
    paste_y0 = int(y0 + max(0, ((y1 - y0) - sprite_h) // 2))
    image.alpha_composite(sprite, (int(paste_x0), int(paste_y0)))
    return RenderedIconInstance(
        instance_id="reference_icon",
        icon_id=str(reference_icon.icon_id),
        panel="reference",
        bbox_xyxy=(int(paste_x0), int(paste_y0), int(paste_x0 + sprite_w), int(paste_y0 + sprite_h)),
        nominal_size_px=int(reference_icon.nominal_size_px if reference_icon.nominal_size_px is not None else nominal_size_px),
        rotation_degrees=int(reference_icon.rotation_degrees) % 360,
        mirror_x=bool(reference_icon.mirror_x),
        tint_rgb=tuple(int(value) for value in reference_icon.tint_rgb),
        noise_edits=serialize_icon_noise_edits(reference_icon.noise_edits),
        noise_seed=None if reference_icon.noise_seed is None else int(reference_icon.noise_seed),
    )


def render_two_panel_icon_sequence_scene(
    *,
    rng,
    reference_icon: IconInstanceSpec,
    scene_cells: Sequence[IconSequenceCellSpec],
    canvas_width: int,
    canvas_height: int,
    reference_panel_width_px: int,
    outer_margin_px: int,
    panel_gap_px: int,
    panel_padding_px: int,
    panel_corner_radius_px: int,
    cell_padding_px: int,
    cell_icon_padding_px: int,
    cell_corner_radius_px: int,
    scene_icon_size_min_px: int,
    scene_icon_size_max_px: int,
    reference_icon_size_px: int,
    scene_max_overlap_fraction: float,
    scene_placement_max_attempts: int,
    scene_size_shrink_rounds: int,
    scene_size_shrink_factor: float,
    panel_title_font_size_px: int,
    missing_mark_font_size_px: int,
    background_rgb: Tuple[int, int, int],
    panel_fill_rgb: Tuple[int, int, int],
    panel_border_rgb: Tuple[int, int, int],
    title_color_rgb: Tuple[int, int, int],
    cell_border_rgb: Tuple[int, int, int],
    missing_mark_color_rgb: Tuple[int, int, int],
    scene_title: str = "Sequence",
) -> RenderedIconSequenceScene:
    """Render one reference icon plus a horizontal sequence of scene cells."""

    if not scene_cells:
        raise ValueError("scene_cells must contain at least one cell")

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
        scene_title=str(scene_title),
    )

    reference_instance = _render_reference_icon(
        image=image,
        reference_icon=reference_icon,
        content_bbox=tuple(int(value) for value in layout.reference_content_xyxy),
        nominal_size_px=int(reference_icon_size_px),
    )

    cell_slots = resolve_horizontal_row_slots(
        tuple(int(value) for value in layout.scene_content_xyxy),
        cell_count=len(scene_cells),
        cell_padding_px=int(cell_padding_px),
    )
    draw = ImageDraw.Draw(image)
    missing_font = load_font(int(missing_mark_font_size_px), bold=True)
    min_size = max(16, int(scene_icon_size_min_px))
    max_size = max(min_size, int(scene_icon_size_max_px))
    max_overlap_fraction = max(0.0, min(1.0, float(scene_max_overlap_fraction)))
    placement_attempts = max(1, int(scene_placement_max_attempts))
    shrink_rounds = max(0, int(scene_size_shrink_rounds))
    shrink_factor = max(0.1, min(1.0, float(scene_size_shrink_factor)))
    inner_padding = max(0, int(cell_icon_padding_px))
    rendered_cells: List[RenderedSequenceCell] = []

    for cell_index, (cell_spec, cell_bbox) in enumerate(zip(scene_cells, cell_slots)):
        draw.rounded_rectangle(
            cell_bbox,
            radius=max(0, int(cell_corner_radius_px)),
            outline=tuple(int(v) for v in cell_border_rgb),
            width=2,
            fill=tuple(int(v) for v in panel_fill_rgb),
        )
        if bool(cell_spec.is_missing):
            draw_text_centered(
                draw,
                text="?",
                center=(0.5 * float(cell_bbox[0] + cell_bbox[2]), 0.5 * float(cell_bbox[1] + cell_bbox[3])),
                font=missing_font,
                fill=tuple(int(v) for v in missing_mark_color_rgb),
                stroke_fill=tuple(int(v) for v in panel_fill_rgb),
                stroke_width=2,
            )
            rendered_cells.append(
                RenderedSequenceCell(
                    cell_index=int(cell_index),
                    cell_bbox_xyxy=tuple(int(v) for v in cell_bbox),
                    is_missing=True,
                    icon_instances=(),
                )
            )
            continue

        icon_content_bbox = (
            int(cell_bbox[0] + inner_padding),
            int(cell_bbox[1] + inner_padding),
            int(cell_bbox[2] - inner_padding),
            int(cell_bbox[3] - inner_padding),
        )
        content_w = max(1, int(icon_content_bbox[2] - icon_content_bbox[0]))
        content_h = max(1, int(icon_content_bbox[3] - icon_content_bbox[1]))
        current_max_size = min(int(max_size), int(content_w), int(content_h))
        placed_bboxes: List[BBox] = []
        rendered_instances: List[RenderedIconInstance] = []
        for icon_index, icon_spec in enumerate(cell_spec.icon_instances):
            sprite = None
            paste_bbox = None
            resolved_nominal_size = None
            for shrink_round in range(int(shrink_rounds) + 1):
                round_max_size = max(int(min_size), int(round(current_max_size * (shrink_factor**shrink_round))))
                if round_max_size < int(min_size):
                    round_max_size = int(min_size)
                for _ in range(int(placement_attempts)):
                    nominal_size = int(
                        icon_spec.nominal_size_px
                        if icon_spec.nominal_size_px is not None
                        else rng.randint(int(min_size), int(round_max_size))
                    )
                    if icon_spec.nominal_size_px is not None and nominal_size > int(round_max_size):
                        continue
                    candidate_sprite = render_icon_rgba(
                        icon_id=str(icon_spec.icon_id),
                        size_px=int(nominal_size),
                        tint_rgb=tuple(int(value) for value in icon_spec.tint_rgb),
                        rotation_degrees=int(icon_spec.rotation_degrees),
                        mirror_x=bool(icon_spec.mirror_x),
                        noise_edits=tuple(icon_spec.noise_edits),
                        noise_seed=icon_spec.noise_seed,
                    )
                    try:
                        candidate_bbox = random_paste_bbox(
                            sprite_size=candidate_sprite.size,
                            content_bbox=icon_content_bbox,
                            rng=rng,
                        )
                    except ValueError:
                        continue
                    if float(max_overlap_with_existing(candidate_bbox, placed_bboxes)) > float(max_overlap_fraction):
                        continue
                    sprite = candidate_sprite
                    paste_bbox = candidate_bbox
                    resolved_nominal_size = int(nominal_size)
                    break
                if sprite is not None and paste_bbox is not None:
                    break
            if sprite is None or paste_bbox is None or resolved_nominal_size is None:
                raise ValueError("failed to place icon inside sequence cell under overlap constraints")
            image.alpha_composite(sprite, (int(paste_bbox[0]), int(paste_bbox[1])))
            placed_bboxes.append(tuple(int(value) for value in paste_bbox))
            rendered_instances.append(
                RenderedIconInstance(
                    instance_id=f"scene_cell_{int(cell_index)}_icon_{int(icon_index)}",
                    icon_id=str(icon_spec.icon_id),
                    panel="scene",
                    bbox_xyxy=tuple(int(value) for value in paste_bbox),
                    nominal_size_px=int(resolved_nominal_size),
                    rotation_degrees=int(icon_spec.rotation_degrees) % 360,
                    mirror_x=bool(icon_spec.mirror_x),
                    tint_rgb=tuple(int(value) for value in icon_spec.tint_rgb),
                    noise_edits=serialize_icon_noise_edits(icon_spec.noise_edits),
                    noise_seed=None if icon_spec.noise_seed is None else int(icon_spec.noise_seed),
                )
            )
        rendered_cells.append(
            RenderedSequenceCell(
                cell_index=int(cell_index),
                cell_bbox_xyxy=tuple(int(v) for v in cell_bbox),
                is_missing=False,
                icon_instances=tuple(rendered_instances),
            )
        )

    return RenderedIconSequenceScene(
        image=image.convert("RGB"),
        layout=layout,
        reference_instance=reference_instance,
        scene_cells=tuple(rendered_cells),
    )


__all__ = [
    "IconSequenceCellSpec",
    "RenderedIconSequenceScene",
    "RenderedSequenceCell",
    "render_two_panel_icon_sequence_scene",
]
