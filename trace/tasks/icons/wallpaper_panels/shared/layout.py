"""Layout helpers for wallpaper-panel icon scenes."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ...shared.icon_grid_scene import resolve_fixed_grid_cell_slots
from ....shared.text_legibility import draw_centered_traced_text
from ....shared.text_rendering import load_font

from .defaults import REFERENCE_LABEL


def option_panel_geometry(
    *,
    render_params: Mapping[str, Any],
    option_labels: Sequence[str],
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Return panel geometry for six option-only wallpaper panels."""

    width = int(render_params["canvas_width"])
    height = int(render_params["canvas_height"])
    margin = max(0, int(render_params["outer_margin_px"]))
    gap = max(0, int(render_params["option_panel_gap_px"]))
    outer_bbox = (int(margin), int(margin), int(width - margin), int(height - margin))
    panel_slots = resolve_fixed_grid_cell_slots(
        outer_bbox,
        rows=2,
        cols=3,
        cell_padding_px=max(0, int(gap // 2)),
    )[: len(option_labels)]
    option_panels = _panel_payloads(
        panel_specs=tuple(zip((str(label) for label in option_labels), panel_slots)),
        render_params=render_params,
        collapse_error="wallpaper option panel content bbox collapsed",
    )
    return (
        {
            "canvas_size": [int(width), int(height)],
            "option_panel_grid": {"rows": 2, "cols": 3, "option_count": int(len(option_labels))},
            "motif_lattice": {
                "rows": int(render_params["lattice_rows"]),
                "cols": int(render_params["lattice_cols"]),
                "visible_grid": False,
            },
            "option_panels": {str(label): dict(payload) for label, payload in option_panels.items()},
        },
        option_panels,
    )


def reference_panel_geometry(
    *,
    render_params: Mapping[str, Any],
    option_labels: Sequence[str],
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    """Return panel geometry for one Reference panel plus six candidate panels."""

    width = int(render_params["canvas_width"])
    height = int(render_params["canvas_height"])
    margin = max(0, int(render_params["outer_margin_px"]))
    gap = max(0, int(render_params["option_panel_gap_px"]))
    reference_width = max(220, int(render_params["reference_panel_width_px"]))
    reference_bbox = (int(margin), int(margin), int(margin + reference_width), int(height - margin))
    options_bbox = (
        int(reference_bbox[2] + gap),
        int(margin),
        int(width - margin),
        int(height - margin),
    )
    if options_bbox[2] <= options_bbox[0]:
        raise ValueError("wallpaper reference-match option area collapsed")
    panel_slots = resolve_fixed_grid_cell_slots(
        options_bbox,
        rows=2,
        cols=3,
        cell_padding_px=max(0, int(gap // 2)),
    )[: len(option_labels)]
    panels = _panel_payloads(
        panel_specs=((REFERENCE_LABEL, reference_bbox), *tuple(zip((str(label) for label in option_labels), panel_slots))),
        render_params=render_params,
        collapse_error="wallpaper reference-match content bbox collapsed",
    )
    return (
        {
            "canvas_size": [int(width), int(height)],
            "reference_panel_label": REFERENCE_LABEL,
            "candidate_panel_grid": {"rows": 2, "cols": 3, "option_count": int(len(option_labels))},
            "motif_lattice": {
                "rows": int(render_params["lattice_rows"]),
                "cols": int(render_params["lattice_cols"]),
                "visible_grid": False,
            },
            "panels": {str(label): dict(payload) for label, payload in panels.items()},
        },
        panels,
    )


def draw_panel_label(
    draw: ImageDraw.ImageDraw,
    *,
    label: str,
    panel_bbox: Sequence[int],
    render_params: Mapping[str, Any],
) -> None:
    """Draw one centered visible panel label."""

    label_font = load_font(int(render_params["cell_label_font_size_px"]), bold=True)
    draw_centered_traced_text(
        draw,
        text=str(label),
        center=(
            0.5 * float(float(panel_bbox[0]) + float(panel_bbox[2])),
            float(panel_bbox[1]) + max(18.0, float(render_params["cell_label_font_size_px"]) * 0.95),
        ),
        font=label_font,
        fill_rgb=tuple(int(v) for v in render_params["cell_label_color_rgb"]),
        stroke_rgb=tuple(int(v) for v in render_params["cell_label_stroke_rgb"]),
        stroke_width=2,
        role="icon_wallpaper_panel_label_text",
        required=False,
    )


def _panel_payloads(
    *,
    panel_specs: Sequence[tuple[str, Sequence[int]]],
    render_params: Mapping[str, Any],
    collapse_error: str,
) -> Dict[str, Dict[str, Any]]:
    label_band_height = max(28, int(round(float(render_params["cell_label_font_size_px"]) * 1.45)))
    panel_padding = max(0, int(render_params["panel_padding_px"]))
    panels: Dict[str, Dict[str, Any]] = {}
    for label, panel_bbox in panel_specs:
        panel_x0, panel_y0, panel_x1, panel_y1 = [int(value) for value in panel_bbox]
        content_bbox = (
            int(panel_x0 + panel_padding),
            int(panel_y0 + label_band_height + max(4, panel_padding // 2)),
            int(panel_x1 - panel_padding),
            int(panel_y1 - panel_padding),
        )
        if content_bbox[2] <= content_bbox[0] or content_bbox[3] <= content_bbox[1]:
            raise ValueError(str(collapse_error))
        panels[str(label)] = {
            "label": str(label),
            "panel_bbox_xyxy": [int(value) for value in panel_bbox],
            "content_bbox_xyxy": [int(value) for value in content_bbox],
        }
    return panels


__all__ = ["draw_panel_label", "option_panel_geometry", "reference_panel_geometry"]
