"""Shared rendering helpers for GUI relation tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw, ImageFont

from ....core.task_group_config import get_task_group_defaults
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ...shared.text_rendering import draw_text_centered, fit_font_to_box, load_font


BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "office_document",
    "creative_workspace",
    "developer_ide",
    "cad_workspace",
    "scientific_plotter",
    "os_file_manager",
)
SUPPORTED_STYLE_VARIANTS: Tuple[str, ...] = ("standard", "compact", "contrast", "cool", "warm", "sage")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
)


@dataclass(frozen=True)
class _Theme:
    name: str
    app_fill: Color
    title_bar: Color
    title_text: Color
    chrome_line: Color
    panel_fill: Color
    panel_alt_fill: Color
    control_fill: Color
    control_outline: Color
    control_text: Color
    muted_text: Color
    selected_fill: Color
    accent: Color
    accent_alt: Color
    badge_fill: Color
    badge_text: Color


@dataclass(frozen=True)
class _AppProfile:
    app_title: str
    window_title: str
    primary_tab: str
    secondary_tab: str
    workspace_title: str
    status_text: str


_APP_PROFILES: Dict[str, _AppProfile] = {
    "office_document": _AppProfile("ReviewHub", "Approvals", "Inbox", "Rules", "Workflow Admin", "Live"),
    "creative_workspace": _AppProfile("AssetFlow", "Library", "Assets", "Campaigns", "Content Admin", "Synced"),
    "developer_ide": _AppProfile("OpsBoard", "Incidents", "Deploys", "Queues", "Operations Admin", "Healthy"),
    "cad_workspace": _AppProfile("InventoryGrid", "Catalog", "Items", "Rules", "Product Admin", "Updated"),
    "scientific_plotter": _AppProfile("MetricsCloud", "Experiments", "Reports", "Segments", "Analytics Admin", "2.4k rows"),
    "os_file_manager": _AppProfile("PortalDesk", "Shared Files", "Files", "Teams", "Workspace Admin", "23 items"),
}


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _bbox_list(bbox: BBox) -> List[float]:
    return [round(float(value), 3) for value in bbox]


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[float, float]:
    try:
        bbox = draw.textbbox((0, 0), str(text), font=font)
        return (float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1]))
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return (float(width), float(height))


def _draw_text_left(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    bbox: BBox,
    fill: Color,
    max_size_px: int,
    min_size_px: int = 8,
    bold: bool = False,
) -> None:
    x1, y1, x2, y2 = [float(value) for value in bbox]
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=max(1.0, float(x2 - x1)),
        max_height=max(1.0, float(y2 - y1)),
        bold=bool(bold),
        min_size_px=int(min_size_px),
        max_size_px=int(max_size_px),
        fill_ratio=0.96,
    )
    _width, height = _measure_text(draw, str(text), font)
    y = float(y1) + max(0.0, (float(y2 - y1) - float(height)) / 2.0) - 1.0
    draw.text((float(x1), float(y)), str(text), fill=fill, font=font)


def _draw_text_center_fit(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    bbox: BBox,
    fill: Color,
    max_size_px: int,
    min_size_px: int = 8,
    bold: bool = False,
) -> None:
    x1, y1, x2, y2 = [float(value) for value in bbox]
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=max(1.0, float(x2 - x1)),
        max_height=max(1.0, float(y2 - y1)),
        bold=bool(bold),
        min_size_px=int(min_size_px),
        max_size_px=int(max_size_px),
        fill_ratio=0.90,
    )
    draw_text_centered(
        draw,
        text=str(text),
        center=((float(x1) + float(x2)) / 2.0, (float(y1) + float(y2)) / 2.0),
        font=font,
        fill=fill,
        stroke_width=0,
    )


def _rounded_rect(
    draw: ImageDraw.ImageDraw,
    bbox: BBox,
    *,
    radius: int,
    fill: Color,
    outline: Color | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(
        [float(value) for value in bbox],
        radius=max(0, int(radius)),
        fill=fill,
        outline=outline,
        width=max(1, int(width)),
    )


def _theme(style_variant: str) -> _Theme:
    if str(style_variant) == "cool":
        return _Theme(
            name="cool",
            app_fill=(253, 254, 255),
            title_bar=(49, 80, 112),
            title_text=(255, 255, 255),
            chrome_line=(198, 211, 224),
            panel_fill=(244, 248, 252),
            panel_alt_fill=(235, 244, 250),
            control_fill=(255, 255, 255),
            control_outline=(177, 196, 213),
            control_text=(35, 48, 63),
            muted_text=(85, 101, 118),
            selected_fill=(225, 241, 255),
            accent=(38, 113, 171),
            accent_alt=(64, 142, 137),
            badge_fill=(35, 58, 84),
            badge_text=(255, 255, 255),
        )
    if str(style_variant) == "warm":
        return _Theme(
            name="warm",
            app_fill=(255, 254, 250),
            title_bar=(116, 77, 49),
            title_text=(255, 255, 255),
            chrome_line=(219, 207, 193),
            panel_fill=(250, 247, 241),
            panel_alt_fill=(244, 238, 228),
            control_fill=(255, 255, 252),
            control_outline=(207, 186, 164),
            control_text=(55, 44, 34),
            muted_text=(112, 93, 73),
            selected_fill=(255, 238, 219),
            accent=(159, 90, 45),
            accent_alt=(46, 126, 119),
            badge_fill=(75, 55, 41),
            badge_text=(255, 255, 255),
        )
    if str(style_variant) == "sage":
        return _Theme(
            name="sage",
            app_fill=(253, 255, 253),
            title_bar=(53, 92, 79),
            title_text=(255, 255, 255),
            chrome_line=(198, 216, 208),
            panel_fill=(244, 250, 247),
            panel_alt_fill=(234, 245, 240),
            control_fill=(255, 255, 255),
            control_outline=(174, 199, 188),
            control_text=(35, 53, 47),
            muted_text=(80, 104, 96),
            selected_fill=(222, 244, 234),
            accent=(41, 123, 100),
            accent_alt=(166, 91, 65),
            badge_fill=(35, 65, 55),
            badge_text=(255, 255, 255),
        )
    if str(style_variant) == "compact":
        return _Theme(
            name="compact",
            app_fill=(251, 252, 253),
            title_bar=(45, 53, 67),
            title_text=(250, 252, 255),
            chrome_line=(203, 209, 218),
            panel_fill=(242, 245, 248),
            panel_alt_fill=(232, 240, 240),
            control_fill=(255, 255, 255),
            control_outline=(173, 185, 195),
            control_text=(38, 44, 55),
            muted_text=(91, 99, 112),
            selected_fill=(221, 244, 242),
            accent=(0, 126, 145),
            accent_alt=(225, 90, 71),
            badge_fill=(31, 39, 51),
            badge_text=(255, 255, 255),
        )
    if str(style_variant) == "contrast":
        return _Theme(
            name="contrast",
            app_fill=(250, 250, 247),
            title_bar=(34, 34, 38),
            title_text=(255, 255, 255),
            chrome_line=(184, 184, 178),
            panel_fill=(241, 241, 236),
            panel_alt_fill=(229, 239, 246),
            control_fill=(255, 255, 252),
            control_outline=(83, 92, 103),
            control_text=(26, 28, 32),
            muted_text=(77, 81, 88),
            selected_fill=(246, 226, 230),
            accent=(184, 53, 71),
            accent_alt=(24, 121, 108),
            badge_fill=(34, 34, 38),
            badge_text=(255, 255, 255),
        )
    return _Theme(
        name="standard",
        app_fill=(255, 255, 255),
        title_bar=(63, 78, 104),
        title_text=(255, 255, 255),
        chrome_line=(205, 211, 220),
        panel_fill=(246, 248, 250),
        panel_alt_fill=(237, 243, 248),
        control_fill=(255, 255, 255),
        control_outline=(186, 196, 210),
        control_text=(40, 48, 61),
        muted_text=(91, 101, 117),
        selected_fill=(225, 239, 255),
        accent=(43, 114, 197),
        accent_alt=(213, 111, 54),
        badge_fill=(36, 47, 64),
        badge_text=(255, 255, 255),
    )


def _normalize_str_support(params: Mapping[str, Any], key: str, fallback: Sequence[str]) -> Tuple[str, ...]:
    raw_values = params.get(str(key), group_default(_GEN_DEFAULTS, str(key), fallback))
    support: List[str] = []
    for raw_value in raw_values:
        value = str(raw_value).strip()
        if value and value not in support:
            support.append(value)
    if not support:
        raise ValueError(f"{key} must not be empty for GUI relation tasks")
    return tuple(str(value) for value in support)


def _draw_app_chrome(
    draw: ImageDraw.ImageDraw,
    *,
    query: Any,
    render_params: Any,
    theme: _Theme,
) -> Tuple[BBox, _AppProfile]:
    profile = _APP_PROFILES[str(query.scene_variant)]
    m = int(render_params.window_margin_px)
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    window = (float(m), float(m - 6), float(width - m), float(height - m + 6))
    _rounded_rect(draw, window, radius=int(render_params.corner_radius_px), fill=theme.app_fill, outline=theme.chrome_line, width=2)

    header_h = max(58, int(render_params.title_bar_height_px) + 16)
    header = (window[0], window[1], window[2], window[1] + float(header_h))
    draw.rounded_rectangle(
        [header[0], header[1], header[2], header[3] + int(render_params.corner_radius_px)],
        radius=int(render_params.corner_radius_px),
        fill=theme.app_fill,
    )
    draw.rectangle([header[0], header[3] - int(render_params.corner_radius_px), header[2], header[3]], fill=theme.app_fill)
    draw.line([header[0], header[3], header[2], header[3]], fill=theme.chrome_line, width=1)

    logo = (window[0] + 22.0, header[1] + 15.0, window[0] + 52.0, header[1] + 45.0)
    _rounded_rect(draw, logo, radius=8, fill=theme.accent, outline=None)
    logo_font = load_font(int(render_params.small_font_size_px), bold=True)
    draw_text_centered(
        draw,
        text=str(profile.app_title)[:1],
        center=((logo[0] + logo[2]) / 2.0, (logo[1] + logo[3]) / 2.0),
        font=logo_font,
        fill=(255, 255, 255),
    )

    title_font = load_font(int(render_params.title_font_size_px), bold=True)
    draw.text((window[0] + 64.0, header[1] + 11.0), str(profile.app_title), fill=theme.control_text, font=title_font)
    small_font = load_font(int(render_params.small_font_size_px), bold=False)
    draw.text((window[0] + 66.0, header[1] + 39.0), str(profile.window_title), fill=theme.muted_text, font=small_font)

    nav_x = window[0] + 285.0
    for idx, nav_label in enumerate((str(profile.primary_tab), str(profile.secondary_tab), "Reports", "Settings")):
        tab_w = 92.0 if len(nav_label) <= 8 else 118.0
        tab_bbox = (nav_x, header[1] + 16.0, nav_x + tab_w, header[1] + 46.0)
        if idx == 0:
            _rounded_rect(draw, tab_bbox, radius=15, fill=theme.selected_fill, outline=theme.accent, width=1)
            _draw_text_center_fit(
                draw,
                text=nav_label,
                bbox=(tab_bbox[0] + 10.0, tab_bbox[1] + 4.0, tab_bbox[2] - 10.0, tab_bbox[3] - 4.0),
                fill=theme.control_text,
                max_size_px=int(render_params.small_font_size_px),
                bold=True,
            )
        else:
            _draw_text_center_fit(
                draw,
                text=nav_label,
                bbox=(tab_bbox[0] + 8.0, tab_bbox[1] + 5.0, tab_bbox[2] - 8.0, tab_bbox[3] - 5.0),
                fill=theme.muted_text,
                max_size_px=int(render_params.small_font_size_px),
                bold=True,
            )
        nav_x += tab_w + 8.0

    status_pill = (window[2] - 194.0, header[1] + 16.0, window[2] - 26.0, header[1] + 46.0)
    _rounded_rect(draw, status_pill, radius=15, fill=theme.panel_alt_fill, outline=theme.chrome_line, width=1)
    _draw_text_center_fit(
        draw,
        text=str(profile.status_text),
        bbox=(status_pill[0] + 10.0, status_pill[1] + 4.0, status_pill[2] - 10.0, status_pill[3] - 4.0),
        fill=theme.control_text,
        max_size_px=int(render_params.small_font_size_px),
        bold=True,
    )

    menu_y1 = header[3]
    menu_y2 = menu_y1 + max(40, int(render_params.menu_bar_height_px) + 6)
    draw.rectangle([window[0], menu_y1, window[2], menu_y2], fill=theme.panel_fill, outline=theme.chrome_line)
    tab_font = load_font(int(render_params.small_font_size_px), bold=True)
    breadcrumb_x = window[0] + 26.0
    draw.text((breadcrumb_x, menu_y1 + 12.0), "Workspace", fill=theme.muted_text, font=tab_font)
    draw.text((breadcrumb_x + 92.0, menu_y1 + 12.0), "/", fill=theme.muted_text, font=tab_font)
    draw.text((breadcrumb_x + 112.0, menu_y1 + 12.0), str(profile.window_title), fill=theme.control_text, font=tab_font)
    filter_bbox = (window[2] - 266.0, menu_y1 + 7.0, window[2] - 172.0, menu_y2 - 7.0)
    export_bbox = (window[2] - 154.0, menu_y1 + 7.0, window[2] - 26.0, menu_y2 - 7.0)
    _rounded_rect(draw, filter_bbox, radius=8, fill=theme.control_fill, outline=theme.chrome_line, width=1)
    _rounded_rect(draw, export_bbox, radius=8, fill=theme.control_fill, outline=theme.chrome_line, width=1)
    _draw_text_center_fit(
        draw,
        text="Filter",
        bbox=(filter_bbox[0] + 8.0, filter_bbox[1] + 3.0, filter_bbox[2] - 8.0, filter_bbox[3] - 3.0),
        fill=theme.muted_text,
        max_size_px=int(render_params.small_font_size_px),
        bold=True,
    )
    _draw_text_center_fit(
        draw,
        text="Export",
        bbox=(export_bbox[0] + 8.0, export_bbox[1] + 3.0, export_bbox[2] - 8.0, export_bbox[3] - 3.0),
        fill=theme.muted_text,
        max_size_px=int(render_params.small_font_size_px),
        bold=True,
    )
    return (window[0] + 22, menu_y2 + 18, window[2] - 22, window[3] - 18), profile


def _draw_badge(
    draw: ImageDraw.ImageDraw,
    *,
    control_bbox: BBox,
    label: str,
    render_params: Any,
    theme: _Theme,
) -> List[float]:
    x1, y1, x2, y2 = [float(value) for value in control_bbox]
    available_size = max(16, int(min(float(x2 - x1), float(y2 - y1)) - 8.0))
    size = max(16, min(max(20, int(render_params.badge_size_px)), int(available_size)))
    badge = (x1 + 5.0, y1 + 5.0, x1 + 5.0 + float(size), y1 + 5.0 + float(size))
    draw.ellipse([float(value) for value in badge], fill=theme.badge_fill, outline=(255, 255, 255), width=2)
    font = fit_font_to_box(
        draw,
        text=str(label),
        max_width=float(size) * 0.70,
        max_height=float(size) * 0.68,
        bold=True,
        min_size_px=8,
        max_size_px=int(render_params.label_font_size_px),
        fill_ratio=1.0,
    )
    draw_text_centered(
        draw,
        text=str(label),
        center=((badge[0] + badge[2]) / 2.0, (badge[1] + badge[3]) / 2.0),
        font=font,
        fill=theme.badge_text,
    )
    return _bbox_list(badge)


def _draw_control_button(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: BBox,
    control: Any,
    render_params: Any,
    theme: _Theme,
) -> List[float]:
    _rounded_rect(
        draw,
        bbox,
        radius=int(render_params.control_corner_radius_px),
        fill=theme.control_fill,
        outline=theme.control_outline,
        width=int(render_params.control_outline_width_px),
    )
    display_text = str(control.display_text)
    max_size_px = int(render_params.small_font_size_px)
    if str(control.role) == "panel_control":
        max_size_px = int(render_params.body_font_size_px + 2)
    _draw_text_center_fit(
        draw,
        text=display_text,
        bbox=(bbox[0] + 30.0, bbox[1] + 4.0, bbox[2] - 8.0, bbox[3] - 4.0),
        fill=theme.control_text,
        max_size_px=int(max_size_px),
        bold=True,
    )
    return _draw_badge(draw, control_bbox=bbox, label=str(control.candidate_label), render_params=render_params, theme=theme)
