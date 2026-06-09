"""Shared soroban-style abacus renderer for misc readout tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from PIL import Image, ImageDraw

from ...shared.text_rendering import load_font
from .drawing import draw_centered_text, draw_rounded_rect
from .scene_style import MiscSceneStyle


SUPPORTED_ABACUS_SCENE_VARIANTS: tuple[str, ...] = ("clean_card", "wood_frame", "worksheet")
ABACUS_COLUMN_ROLES: tuple[str, ...] = ("hundreds", "tens", "ones")
ABACUS_ANNOTATION_KEYS: tuple[str, ...] = (
    "hundreds_active_beads",
    "tens_active_beads",
    "ones_active_beads",
)


@dataclass(frozen=True)
class AbacusColumnSpec:
    item_id: str
    role: str
    place_label: str
    place_value: int
    digit: int


@dataclass(frozen=True)
class AbacusRenderParams:
    canvas_width: int = 980
    canvas_height: int = 760
    panel_width_px: int = 800
    panel_height_px: int = 540
    panel_corner_radius_px: int = 24
    frame_width_px: int = 8
    rod_width_px: int = 5
    beam_height_px: int = 22
    bead_width_px: int = 58
    bead_height_px: int = 34
    title_font_size_px: int = 25
    label_font_size_px: int = 23
    small_font_size_px: int = 16


@dataclass(frozen=True)
class AbacusMatchPanelRenderParams:
    canvas_width: int = 1200
    canvas_height: int = 760
    option_card_width_px: int = 340
    option_card_height_px: int = 280
    option_card_gap_x_px: int = 44
    option_card_gap_y_px: int = 52
    option_card_corner_radius_px: int = 18
    option_label_font_size_px: int = 26
    option_place_label_font_size_px: int = 16
    option_bead_width_px: int = 32
    option_bead_height_px: int = 20
    option_rod_width_px: int = 3
    option_beam_height_px: int = 10


@dataclass(frozen=True)
class AbacusOptionSpec:
    label: str
    value: int
    is_correct: bool


@dataclass(frozen=True)
class RenderedAbacusScene:
    image: Image.Image
    entities: tuple[dict[str, Any], ...]
    item_bboxes: dict[str, list[float]]
    bead_bboxes: dict[str, list[float]]
    active_bead_bboxes_by_column: dict[str, list[list[float]]]
    active_bead_points_by_column: dict[str, list[list[float]]]
    active_bead_ids_by_column: dict[str, list[str]]
    column_bboxes: dict[str, list[float]]
    label_bboxes: dict[str, list[float]]
    scene_bbox_px: list[float]
    style_metadata: dict[str, Any]


@dataclass(frozen=True)
class RenderedAbacusMatchPanelScene:
    image: Image.Image
    entities: tuple[dict[str, Any], ...]
    item_bboxes: dict[str, list[float]]
    option_card_bboxes: dict[str, list[float]]
    option_abacus_bboxes: dict[str, list[float]]
    option_values_by_label: dict[str, int]
    selected_option_card_bbox: list[float]
    selected_option_abacus_bbox: list[float]
    scene_bbox_px: list[float]
    style_metadata: dict[str, Any]


def _rounded_bbox(values: Sequence[float]) -> list[float]:
    return [round(float(value), 3) for value in values]


def _variant_colors(scene_variant: str, style: MiscSceneStyle) -> dict[str, tuple[int, int, int]]:
    """Return high-contrast abacus colors for one non-semantic scene variant."""

    if str(scene_variant) == "wood_frame":
        bead_fill = (202, 125, 64)
        return {
            "panel_fill": (246, 235, 212),
            "panel_outline": (116, 76, 43),
            "frame": (139, 91, 49),
            "rod": (83, 69, 57),
            "beam": (112, 72, 39),
            "active_bead": bead_fill,
            "inactive_bead": bead_fill,
            "bead_outline": (82, 58, 43),
            "label": (46, 38, 31),
            "guide": (211, 194, 161),
            "shadow": (204, 194, 178),
        }
    if str(scene_variant) == "worksheet":
        bead_fill = (71, 122, 184)
        return {
            "panel_fill": (252, 250, 242),
            "panel_outline": (128, 139, 151),
            "frame": (54, 67, 82),
            "rod": (74, 85, 99),
            "beam": (62, 73, 87),
            "active_bead": bead_fill,
            "inactive_bead": bead_fill,
            "bead_outline": (45, 57, 72),
            "label": (35, 45, 58),
            "guide": (220, 224, 230),
            "shadow": (209, 214, 220),
        }
    bead_fill = tuple(int(value) for value in style.panel_accent_rgb)
    return {
        "panel_fill": tuple(int(value) for value in style.panel_fill_rgb),
        "panel_outline": tuple(int(value) for value in style.panel_border_rgb),
        "frame": tuple(int(value) for value in style.text_rgb),
        "rod": (72, 79, 88),
        "beam": (46, 52, 60),
        "active_bead": bead_fill,
        "inactive_bead": bead_fill,
        "bead_outline": (49, 56, 66),
        "label": tuple(int(value) for value in style.text_rgb),
        "guide": tuple(int(value) for value in style.grid_rgb),
        "shadow": (208, 214, 222),
    }


def _bead_bbox(cx: float, cy: float, *, width: int, height: int) -> list[float]:
    return _rounded_bbox(
        (
            float(cx - (0.5 * int(width))),
            float(cy - (0.5 * int(height))),
            float(cx + (0.5 * int(width))),
            float(cy + (0.5 * int(height))),
        )
    )


def _bbox_center(bbox: Sequence[float]) -> list[float]:
    x0, y0, x1, y1 = (float(value) for value in bbox)
    return _rounded_bbox(((x0 + x1) * 0.5, (y0 + y1) * 0.5))


def _draw_bead(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    fill: Sequence[int],
    outline: Sequence[int],
    shadow: Sequence[int],
) -> None:
    x0, y0, x1, y1 = (float(value) for value in bbox)
    draw.ellipse((x0 + 3.0, y0 + 4.0, x1 + 3.0, y1 + 4.0), fill=tuple(int(value) for value in shadow))
    draw.ellipse((x0, y0, x1, y1), fill=tuple(int(value) for value in fill), outline=tuple(int(value) for value in outline), width=2)
    draw.arc((x0 + 8.0, y0 + 6.0, x1 - 8.0, y1 - 6.0), start=200, end=340, fill=tuple(int(value) for value in outline), width=1)


def _digit_active_counts(digit: int) -> tuple[bool, int]:
    if not 0 <= int(digit) <= 9:
        raise ValueError("abacus digit must be in 0..9")
    return bool(int(digit) >= 5), int(digit) % 5


def digits_for_abacus_value(value: int) -> tuple[int, int, int]:
    """Return hundreds/tens/ones digits for a three-column abacus value."""

    if not 0 <= int(value) <= 999:
        raise ValueError("abacus value must be in 0..999")
    text = f"{int(value):03d}"
    return int(text[0]), int(text[1]), int(text[2])


def _option_card_bboxes(
    *,
    option_labels: Sequence[str],
    params: AbacusMatchPanelRenderParams,
) -> dict[str, list[float]]:
    labels = tuple(str(label) for label in option_labels)
    if len(labels) != 6:
        raise ValueError("abacus match panel requires exactly six option labels")
    card_w = float(params.option_card_width_px)
    card_h = float(params.option_card_height_px)
    gap_x = float(params.option_card_gap_x_px)
    gap_y = float(params.option_card_gap_y_px)
    total_w = (3.0 * card_w) + (2.0 * gap_x)
    total_h = (2.0 * card_h) + gap_y
    start_x = float(round(0.5 * (float(params.canvas_width) - total_w)))
    start_y = float(round(0.5 * (float(params.canvas_height) - total_h)))
    bboxes: dict[str, list[float]] = {}
    for index, label in enumerate(labels):
        row = int(index // 3)
        col = int(index % 3)
        x0 = float(start_x + (col * (card_w + gap_x)))
        y0 = float(start_y + (row * (card_h + gap_y)))
        bboxes[str(label)] = _rounded_bbox((x0, y0, x0 + card_w, y0 + card_h))
    return bboxes


def _draw_compact_abacus_option(
    draw: ImageDraw.ImageDraw,
    *,
    card_bbox: Sequence[float],
    option: AbacusOptionSpec,
    params: AbacusMatchPanelRenderParams,
    colors: Mapping[str, tuple[int, int, int]],
) -> tuple[list[float], list[dict[str, Any]], dict[str, list[float]]]:
    label = str(option.label)
    value = int(option.value)
    x0, y0, x1, y1 = (float(value_) for value_ in card_bbox)
    card_bbox_out = _rounded_bbox((x0, y0, x1, y1))
    shadow_bbox = (x0 + 4.0, y0 + 5.0, x1 + 4.0, y1 + 5.0)
    draw_rounded_rect(
        draw,
        shadow_bbox,
        radius=int(params.option_card_corner_radius_px),
        fill=colors["shadow"],
        outline=colors["shadow"],
        width=1,
    )
    draw_rounded_rect(
        draw,
        (x0, y0, x1, y1),
        radius=int(params.option_card_corner_radius_px),
        fill=colors["panel_fill"],
        outline=colors["panel_outline"],
        width=2,
    )

    badge_bbox = (x0 + 13.0, y0 + 13.0, x0 + 49.0, y0 + 49.0)
    draw.rounded_rectangle(badge_bbox, radius=10, fill=colors["frame"], outline=colors["frame"], width=1)
    option_label_font = load_font(int(params.option_label_font_size_px), bold=True)
    badge_text_bbox = draw_centered_text(
        draw,
        text=label,
        center=(0.5 * (badge_bbox[0] + badge_bbox[2]), 0.5 * (badge_bbox[1] + badge_bbox[3])),
        font=option_label_font,
        fill=colors["panel_fill"],
        stroke_fill=colors["frame"],
        stroke_width=0,
    )

    frame_bbox = [x0 + 58.0, y0 + 58.0, x1 - 32.0, y1 - 44.0]
    frame_left, frame_top, frame_right, frame_bottom = (float(value_) for value_ in frame_bbox)
    draw_rounded_rect(
        draw,
        tuple(frame_bbox),
        radius=12,
        fill=colors["panel_fill"],
        outline=colors["frame"],
        width=4,
    )
    beam_y = float(frame_top + (0.36 * (frame_bottom - frame_top)))
    beam_bbox = (
        frame_left + 5.0,
        beam_y - (0.5 * int(params.option_beam_height_px)),
        frame_right - 5.0,
        beam_y + (0.5 * int(params.option_beam_height_px)),
    )
    draw.rounded_rectangle(beam_bbox, radius=4, fill=colors["beam"], outline=colors["frame"], width=1)

    rod_top = frame_top + 11.0
    rod_bottom = frame_bottom - 11.0
    rod_xs = (
        frame_left + 54.0,
        0.5 * (frame_left + frame_right),
        frame_right - 54.0,
    )
    upper_inactive_y = beam_y - 44.0
    upper_active_y = beam_y - 20.0
    lower_active_start_y = beam_y + 22.0
    lower_spacing = 24.0
    lower_inactive_bottom_y = rod_bottom - 6.0
    place_label_y = frame_bottom + 22.0
    place_font = load_font(int(params.option_place_label_font_size_px), bold=True)
    bead_bboxes: dict[str, list[float]] = {}
    entities: list[dict[str, Any]] = [
        {
            "item_id": f"option_{label}_card",
            "entity_type": "abacus_option_card",
            "option_label": label,
            "value": value,
            "is_correct": bool(option.is_correct),
            "bbox_px": list(card_bbox_out),
        },
        {
            "item_id": f"option_{label}_abacus_frame",
            "entity_type": "abacus_frame",
            "option_label": label,
            "value": value,
            "bbox_px": _rounded_bbox(frame_bbox),
        },
        {
            "item_id": f"option_{label}_label_badge",
            "entity_type": "option_label_badge",
            "option_label": label,
            "bbox_px": _rounded_bbox(badge_bbox),
            "text_bbox_px": list(badge_text_bbox),
        },
    ]

    for role, place_label, digit, cx in zip(ABACUS_COLUMN_ROLES, ("100", "10", "1"), digits_for_abacus_value(value), rod_xs):
        draw.line((cx, rod_top, cx, rod_bottom), fill=colors["rod"], width=int(params.option_rod_width_px))
        draw_centered_text(
            draw,
            text=str(place_label),
            center=(float(cx), float(place_label_y)),
            font=place_font,
            fill=colors["label"],
            stroke_fill=colors["panel_fill"],
            stroke_width=1,
        )
        upper_active, lower_count = _digit_active_counts(int(digit))
        upper_id = f"option_{label}_column_{role}_upper"
        upper_bbox = _bead_bbox(
            cx,
            upper_active_y if upper_active else upper_inactive_y,
            width=int(params.option_bead_width_px),
            height=int(params.option_bead_height_px),
        )
        _draw_bead(
            draw,
            bbox=upper_bbox,
            fill=colors["active_bead"],
            outline=colors["bead_outline"],
            shadow=colors["shadow"],
        )
        bead_bboxes[str(upper_id)] = list(upper_bbox)

        for bead_index in range(4):
            is_active = int(bead_index) < int(lower_count)
            if is_active:
                bead_y = float(lower_active_start_y + (bead_index * lower_spacing))
            else:
                remaining_index = int(bead_index - lower_count)
                inactive_count = int(4 - lower_count)
                bead_y = float(lower_inactive_bottom_y - ((inactive_count - remaining_index - 1) * lower_spacing))
            bead_id = f"option_{label}_column_{role}_lower_{bead_index + 1}"
            bead_bbox = _bead_bbox(
                cx,
                bead_y,
                width=int(params.option_bead_width_px),
                height=int(params.option_bead_height_px),
            )
            _draw_bead(
                draw,
                bbox=bead_bbox,
                fill=colors["active_bead"],
                outline=colors["bead_outline"],
                shadow=colors["shadow"],
            )
            bead_bboxes[str(bead_id)] = list(bead_bbox)

        entities.append(
            {
                "item_id": f"option_{label}_column_{role}",
                "entity_type": "abacus_column",
                "option_label": label,
                "place_label": str(place_label),
                "place_value": {"hundreds": 100, "tens": 10, "ones": 1}[str(role)],
                "digit": int(digit),
                "bbox_px": _rounded_bbox((cx - 8.0, rod_top, cx + 8.0, rod_bottom)),
                "active_upper_bead": bool(upper_active),
                "active_lower_bead_count": int(lower_count),
            }
        )

    for bead_id, bead_bbox in bead_bboxes.items():
        entities.append(
            {
                "item_id": str(bead_id),
                "entity_type": "abacus_bead",
                "option_label": label,
                "bbox_px": list(bead_bbox),
            }
        )
    return _rounded_bbox(frame_bbox), entities, bead_bboxes


def render_abacus_match_panel_scene(
    image: Image.Image,
    *,
    options: Sequence[AbacusOptionSpec],
    correct_label: str,
    params: AbacusMatchPanelRenderParams,
    scene_variant: str,
    style: MiscSceneStyle,
) -> RenderedAbacusMatchPanelScene:
    """Render six labeled compact abacus options for target-value matching."""

    if len(options) != 6:
        raise ValueError("abacus_match_panel requires exactly six options")
    labels = tuple(str(option.label) for option in options)
    if len(set(labels)) != len(labels):
        raise ValueError("abacus_match_panel option labels must be unique")
    if str(correct_label) not in set(labels):
        raise ValueError("abacus_match_panel correct label must be one of the visible options")

    draw = ImageDraw.Draw(image)
    colors = _variant_colors(str(scene_variant), style)
    card_bboxes = _option_card_bboxes(option_labels=labels, params=params)
    entities: list[dict[str, Any]] = []
    item_bboxes: dict[str, list[float]] = {}
    option_card_bboxes: dict[str, list[float]] = {}
    option_abacus_bboxes: dict[str, list[float]] = {}
    option_values_by_label: dict[str, int] = {}

    for option in options:
        label = str(option.label)
        option_card_bboxes[label] = list(card_bboxes[label])
        option_values_by_label[label] = int(option.value)
        abacus_bbox, option_entities, bead_bboxes = _draw_compact_abacus_option(
            draw,
            card_bbox=card_bboxes[label],
            option=option,
            params=params,
            colors=colors,
        )
        option_abacus_bboxes[label] = list(abacus_bbox)
        item_bboxes[f"option_{label}_card"] = list(card_bboxes[label])
        item_bboxes[f"option_{label}_abacus_frame"] = list(abacus_bbox)
        item_bboxes.update({str(key): list(value) for key, value in bead_bboxes.items()})
        entities.extend(option_entities)

    selected_card_bbox = list(option_card_bboxes[str(correct_label)])
    selected_abacus_bbox = list(option_abacus_bboxes[str(correct_label)])
    scene_bbox = _rounded_bbox(
        (
            min(float(bbox[0]) for bbox in option_card_bboxes.values()) - 8.0,
            min(float(bbox[1]) for bbox in option_card_bboxes.values()) - 8.0,
            max(float(bbox[2]) for bbox in option_card_bboxes.values()) + 12.0,
            max(float(bbox[3]) for bbox in option_card_bboxes.values()) + 12.0,
        )
    )
    return RenderedAbacusMatchPanelScene(
        image=image,
        entities=tuple(entities),
        item_bboxes=dict(item_bboxes),
        option_card_bboxes={str(key): list(value) for key, value in option_card_bboxes.items()},
        option_abacus_bboxes={str(key): list(value) for key, value in option_abacus_bboxes.items()},
        option_values_by_label=dict(option_values_by_label),
        selected_option_card_bbox=list(selected_card_bbox),
        selected_option_abacus_bbox=list(selected_abacus_bbox),
        scene_bbox_px=list(scene_bbox),
        style_metadata={
            "renderer": "abacus_match_panel_v0",
            "scene_variant": str(scene_variant),
            "layout": "six_option_cards_3x2",
            "option_labels": [str(label) for label in labels],
            "active_inactive_bead_color_shared": tuple(colors["active_bead"]) == tuple(colors["inactive_bead"]),
            "active_bead_rgb": [int(value) for value in colors["active_bead"]],
            "inactive_bead_rgb": [int(value) for value in colors["inactive_bead"]],
            "upper_bead_value": 5,
            "lower_bead_value": 1,
        },
    )


def render_abacus_readout_scene(
    image: Image.Image,
    *,
    columns: Sequence[AbacusColumnSpec],
    params: AbacusRenderParams,
    scene_variant: str,
    style: MiscSceneStyle,
) -> RenderedAbacusScene:
    """Render one three-column abacus readout scene."""

    if len(columns) != 3:
        raise ValueError("abacus_readout currently renders exactly three columns")
    draw = ImageDraw.Draw(image)
    colors = _variant_colors(str(scene_variant), style)
    width, height = int(params.canvas_width), int(params.canvas_height)
    panel_w = int(params.panel_width_px)
    panel_h = int(params.panel_height_px)
    panel_left = float(round(0.5 * (width - panel_w)))
    panel_top = float(round(0.5 * (height - panel_h) + 20))
    panel_bbox = [panel_left, panel_top, panel_left + panel_w, panel_top + panel_h]
    shadow_bbox = [panel_bbox[0] + 5.0, panel_bbox[1] + 7.0, panel_bbox[2] + 5.0, panel_bbox[3] + 7.0]

    draw_rounded_rect(
        draw,
        tuple(shadow_bbox),
        radius=int(params.panel_corner_radius_px),
        fill=colors["shadow"],
        outline=colors["shadow"],
        width=1,
    )
    draw_rounded_rect(
        draw,
        tuple(panel_bbox),
        radius=int(params.panel_corner_radius_px),
        fill=colors["panel_fill"],
        outline=colors["panel_outline"],
        width=2,
    )
    if str(scene_variant) == "worksheet":
        for offset in range(28, int(panel_h), 36):
            y = float(panel_top + offset)
            draw.line((panel_left + 18.0, y, panel_left + panel_w - 18.0, y), fill=colors["guide"], width=1)

    frame_pad = 48.0
    frame_bbox = [panel_left + frame_pad, panel_top + 62.0, panel_left + panel_w - frame_pad, panel_top + panel_h - 74.0]
    draw_rounded_rect(
        draw,
        tuple(frame_bbox),
        radius=16,
        fill=(0, 0, 0, 0) if image.mode == "RGBA" else colors["panel_fill"],
        outline=colors["frame"],
        width=int(params.frame_width_px),
    )

    # Keep the lower deck tall enough that active lower beads near the beam
    # are visually separated from inactive beads parked at the bottom.
    beam_y = float(panel_top + 0.42 * panel_h)
    beam_bbox = [frame_bbox[0] + 6.0, beam_y - (0.5 * int(params.beam_height_px)), frame_bbox[2] - 6.0, beam_y + (0.5 * int(params.beam_height_px))]
    draw.rounded_rectangle(tuple(beam_bbox), radius=8, fill=colors["beam"], outline=colors["frame"], width=2)

    title_font = load_font(int(params.title_font_size_px), bold=True)
    label_font = load_font(int(params.label_font_size_px), bold=True)
    label_bboxes: dict[str, list[float]] = {}
    title_bbox = draw_centered_text(
        draw,
        text="Abacus",
        center=(0.5 * width, panel_top + 34.0),
        font=title_font,
        fill=colors["label"],
        stroke_fill=colors["panel_fill"],
        stroke_width=2,
    )
    label_bboxes["title"] = list(title_bbox)

    usable_left = frame_bbox[0] + 96.0
    usable_right = frame_bbox[2] - 96.0
    rod_gap = (usable_right - usable_left) / 2.0
    rod_top = frame_bbox[1] + 14.0
    rod_bottom = frame_bbox[3] - 14.0
    upper_inactive_y = beam_y - 116.0
    upper_active_y = beam_y - 34.0
    lower_active_start_y = beam_y + 34.0
    lower_spacing = 38.0
    lower_inactive_bottom_y = rod_bottom - 10.0

    entities: list[dict[str, Any]] = []
    item_bboxes: dict[str, list[float]] = {"abacus_frame": _rounded_bbox(frame_bbox), "beam": _rounded_bbox(beam_bbox)}
    bead_bboxes: dict[str, list[float]] = {}
    column_bboxes: dict[str, list[float]] = {}
    active_bead_bboxes_by_column: dict[str, list[list[float]]] = {}
    active_bead_points_by_column: dict[str, list[list[float]]] = {}
    active_bead_ids_by_column: dict[str, list[str]] = {}

    for index, column in enumerate(columns):
        role = str(column.role)
        cx = float(usable_left + (index * rod_gap))
        rod_bbox = _rounded_bbox((cx - 12.0, rod_top, cx + 12.0, rod_bottom))
        column_bboxes[role] = list(rod_bbox)
        draw.line((cx, rod_top, cx, rod_bottom), fill=colors["rod"], width=int(params.rod_width_px))
        label_bbox = draw_centered_text(
            draw,
            text=str(column.place_label),
            center=(cx, frame_bbox[3] + 38.0),
            font=label_font,
            fill=colors["label"],
            stroke_fill=colors["panel_fill"],
            stroke_width=2,
        )
        label_bboxes[f"{role}_place_label"] = list(label_bbox)
        upper_active, lower_count = _digit_active_counts(int(column.digit))
        active_ids: list[str] = []
        active_bboxes: list[list[float]] = []
        upper_id = f"{column.item_id}_upper"
        upper_bbox = _bead_bbox(
            cx,
            upper_active_y if upper_active else upper_inactive_y,
            width=int(params.bead_width_px),
            height=int(params.bead_height_px),
        )
        _draw_bead(
            draw,
            bbox=upper_bbox,
            fill=colors["active_bead"] if upper_active else colors["inactive_bead"],
            outline=colors["bead_outline"],
            shadow=colors["shadow"],
        )
        bead_bboxes[upper_id] = list(upper_bbox)
        if upper_active:
            active_ids.append(str(upper_id))
            active_bboxes.append(list(upper_bbox))

        for bead_index in range(4):
            is_active = int(bead_index) < int(lower_count)
            if is_active:
                bead_y = float(lower_active_start_y + (bead_index * lower_spacing))
            else:
                remaining_index = int(bead_index - lower_count)
                inactive_count = int(4 - lower_count)
                bead_y = float(lower_inactive_bottom_y - ((inactive_count - remaining_index - 1) * lower_spacing))
            bead_id = f"{column.item_id}_lower_{bead_index + 1}"
            bbox = _bead_bbox(
                cx,
                bead_y,
                width=int(params.bead_width_px),
                height=int(params.bead_height_px),
            )
            _draw_bead(
                draw,
                bbox=bbox,
                fill=colors["active_bead"] if is_active else colors["inactive_bead"],
                outline=colors["bead_outline"],
                shadow=colors["shadow"],
            )
            bead_bboxes[str(bead_id)] = list(bbox)
            if is_active:
                active_ids.append(str(bead_id))
                active_bboxes.append(list(bbox))

        active_bead_ids_by_column[role] = [str(item) for item in active_ids]
        active_bead_bboxes_by_column[f"{role}_active_beads"] = [list(bbox) for bbox in active_bboxes]
        active_bead_points_by_column[f"{role}_active_beads"] = [_bbox_center(bbox) for bbox in active_bboxes]
        entities.append(
            {
                "item_id": str(column.item_id),
                "entity_type": "abacus_column",
                "role": str(role),
                "place_label": str(column.place_label),
                "place_value": int(column.place_value),
                "digit": int(column.digit),
                "bbox_px": list(rod_bbox),
                "active_upper_bead": bool(upper_active),
                "active_lower_bead_count": int(lower_count),
                "active_bead_ids": [str(item) for item in active_ids],
            }
        )

    for bead_id, bbox in bead_bboxes.items():
        item_bboxes[str(bead_id)] = list(bbox)
        role = "active_bead" if any(str(bead_id) in ids for ids in active_bead_ids_by_column.values()) else "inactive_bead"
        entities.append(
            {
                "item_id": str(bead_id),
                "entity_type": "abacus_bead",
                "role": str(role),
                "bbox_px": list(bbox),
            }
        )

    scene_bbox = _rounded_bbox((panel_bbox[0] - 8.0, panel_bbox[1] - 8.0, panel_bbox[2] + 10.0, panel_bbox[3] + 12.0))
    return RenderedAbacusScene(
        image=image,
        entities=tuple(entities),
        item_bboxes=item_bboxes,
        bead_bboxes=bead_bboxes,
        active_bead_bboxes_by_column=active_bead_bboxes_by_column,
        active_bead_points_by_column=active_bead_points_by_column,
        active_bead_ids_by_column=active_bead_ids_by_column,
        column_bboxes=column_bboxes,
        label_bboxes=label_bboxes,
        scene_bbox_px=list(scene_bbox),
        style_metadata={
            "renderer": "abacus_readout_v0",
            "scene_variant": str(scene_variant),
            "column_roles": [str(role) for role in ABACUS_COLUMN_ROLES],
            "annotation_keys": [str(key) for key in ABACUS_ANNOTATION_KEYS],
            "active_beads_touch_center_beam": True,
            "active_inactive_bead_color_shared": tuple(colors["active_bead"]) == tuple(colors["inactive_bead"]),
            "active_bead_rgb": [int(value) for value in colors["active_bead"]],
            "inactive_bead_rgb": [int(value) for value in colors["inactive_bead"]],
            "upper_bead_value": 5,
            "lower_bead_value": 1,
        },
    )


__all__ = [
    "ABACUS_COLUMN_ROLES",
    "ABACUS_ANNOTATION_KEYS",
    "SUPPORTED_ABACUS_SCENE_VARIANTS",
    "AbacusMatchPanelRenderParams",
    "AbacusColumnSpec",
    "AbacusOptionSpec",
    "AbacusRenderParams",
    "RenderedAbacusMatchPanelScene",
    "RenderedAbacusScene",
    "digits_for_abacus_value",
    "render_abacus_match_panel_scene",
    "render_abacus_readout_scene",
]
