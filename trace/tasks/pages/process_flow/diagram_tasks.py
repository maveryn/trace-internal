"""Process-flow page tasks grounded in lane, status, and arrow-label semantics."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.drawing import draw_arrow, draw_centered_text, draw_dashed_line, draw_rounded_rect
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import resolve_layout_jitter, resolve_render_int
from ...shared.text_rendering import fit_font_to_box, load_font
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.diagram.common import (
    projected_diagram_bbox_annotation,
    resolve_jittered_diagram_panel_geometry,
    round_diagram_bbox,
)
from ..shared.diagram.complexity import (
    build_diagrams_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_diagrams_complexity_weights,
)
from ..shared.diagram.visual_defaults import load_diagrams_background_defaults, load_diagrams_noise_defaults
from ..shared.public_query_task import rewrite_pages_query_output


SCENE_ID = "process_flow"
FILTERED_NODE_COUNT_TASK_ID = "task_pages__process_flow__filtered_node_count"
CONDITION_PATH_ENDPOINT_TASK_ID = "task_pages__process_flow__condition_path_endpoint_label"
ALL_CROSS_LANE_HANDOFF_COUNT_TASK_ID = "task_pages__process_flow__all_cross_lane_handoff_count"
LANE_FILTERED_HANDOFF_COUNT_TASK_ID = "task_pages__process_flow__lane_filtered_handoff_count"
_HANDOFF_COUNT_TASK_IDS: Tuple[str, ...] = (
    ALL_CROSS_LANE_HANDOFF_COUNT_TASK_ID,
    LANE_FILTERED_HANDOFF_COUNT_TASK_ID,
)

_LAYOUT_VARIANTS: Tuple[str, ...] = (
    "vertical_swimlane",
    "horizontal_swimlane",
    "staggered_columns",
    "compact_rows",
)
_STYLE_VARIANTS: Tuple[str, ...] = ("blueprint", "pastel_cards", "graphite", "warm_memo")
_CONTEXT_VARIANTS: Tuple[str, ...] = (
    "incident_response",
    "editorial_review",
    "order_fulfillment",
    "model_release",
    "lab_sample",
    "support_ticket",
)
_FILTER_QUERY_IDS: Tuple[str, ...] = (
    "shape_node_count",
    "status_node_count",
    "role_node_count",
)
_HANDOFF_QUERY_IDS: Tuple[str, ...] = (
    "all_cross_lane_handoff_count",
    "lane_outgoing_handoff_count",
    "lane_involved_handoff_count",
)

_TASK_QUERY_IDS: Dict[str, Tuple[str, ...]] = {
    FILTERED_NODE_COUNT_TASK_ID: _FILTER_QUERY_IDS,
    CONDITION_PATH_ENDPOINT_TASK_ID: ("condition_path_endpoint_label",),
    ALL_CROSS_LANE_HANDOFF_COUNT_TASK_ID: ("all_cross_lane_handoff_count",),
    LANE_FILTERED_HANDOFF_COUNT_TASK_ID: ("lane_outgoing_handoff_count", "lane_involved_handoff_count"),
}
_TASK_KEYS: Dict[str, str] = {
    "shape_node_count": "shape_node_count_query",
    "status_node_count": "status_node_count_query",
    "role_node_count": "role_node_count_query",
    "condition_path_endpoint_label": "condition_path_endpoint_label_query",
    "all_cross_lane_handoff_count": "all_cross_lane_handoff_count_query",
    "lane_outgoing_handoff_count": "lane_outgoing_handoff_count_query",
    "lane_involved_handoff_count": "lane_involved_handoff_count_query",
}
_QUERY_PROBABILITY_KEYS: Dict[str, str] = {
    "shape_node_count": "query_weights",
    "status_node_count": "query_weights",
    "role_node_count": "query_weights",
    "condition_path_endpoint_label": "query_weights",
    "all_cross_lane_handoff_count": "query_weights",
    "lane_outgoing_handoff_count": "query_weights",
    "lane_involved_handoff_count": "query_weights",
}


def _is_handoff_task(task_id: str) -> bool:
    """Return whether the public task uses process-flow handoff-arrow annotation."""

    return str(task_id) in set(_HANDOFF_COUNT_TASK_IDS)

_CONDITION_POOLS: Tuple[Tuple[str, str], ...] = (
    ("yes", "no"),
    ("pass", "fail"),
    ("approve", "revise"),
    ("ready", "hold"),
    ("auto", "manual"),
    ("ship", "return"),
    ("accept", "reject"),
)
_STATUS_POOL: Tuple[str, ...] = ("Ready", "Hold", "Queued", "Review", "Done", "Retry")
_ROLE_DESCRIPTIONS: Dict[str, str] = {
    "process": "process steps",
    "decision": "decision steps",
    "review": "review steps",
    "data": "data steps",
    "output": "output steps",
}
_SHAPE_DESCRIPTIONS: Dict[str, str] = {
    "diamond": "decision diamonds",
    "rounded": "rounded process boxes",
    "parallelogram": "slanted data boxes",
    "ellipse": "terminal ovals",
}

_CONTEXTS: Dict[str, Dict[str, Any]] = {
    "incident_response": {
        "title": "Incident response flow",
        "lanes": ["Monitor", "Triage", "Security", "Ops", "Comms"],
        "steps": [
            "Alert",
            "Classify",
            "Scope",
            "Contain",
            "Patch",
            "Notify",
            "Review",
            "Close",
            "Escalate",
            "Snapshot",
            "Approve",
            "Archive",
            "Restore",
            "Report",
        ],
    },
    "editorial_review": {
        "title": "Publishing workflow",
        "lanes": ["Author", "Editor", "Legal", "Design", "Release"],
        "steps": [
            "Draft",
            "Edit",
            "Fact Check",
            "Layout",
            "Proof",
            "Revise",
            "Approve",
            "Publish",
            "Caption",
            "Archive",
            "Assign",
            "Review",
            "Upload",
            "Notify",
        ],
    },
    "order_fulfillment": {
        "title": "Order fulfillment path",
        "lanes": ["Sales", "Inventory", "Packing", "Carrier", "Billing"],
        "steps": [
            "Order",
            "Verify",
            "Reserve",
            "Pick",
            "Pack",
            "Label",
            "Dispatch",
            "Invoice",
            "Backorder",
            "Refund",
            "Inspect",
            "Confirm",
            "Ship",
            "Close",
        ],
    },
    "model_release": {
        "title": "Model release pipeline",
        "lanes": ["Data", "Training", "Eval", "Safety", "Deploy"],
        "steps": [
            "Collect",
            "Clean",
            "Train",
            "Score",
            "Audit",
            "Tune",
            "Approve",
            "Package",
            "Shadow",
            "Launch",
            "Rollback",
            "Log",
            "Monitor",
            "Signoff",
        ],
    },
    "lab_sample": {
        "title": "Lab sample workflow",
        "lanes": ["Intake", "Prep", "Assay", "Review", "Records"],
        "steps": [
            "Receive",
            "Barcode",
            "Aliquot",
            "Spin",
            "Assay",
            "Repeat",
            "Validate",
            "Record",
            "Store",
            "Reject",
            "Release",
            "Notify",
            "Archive",
            "Seal",
        ],
    },
    "support_ticket": {
        "title": "Support ticket workflow",
        "lanes": ["Customer", "Support", "Specialist", "QA", "Billing"],
        "steps": [
            "Request",
            "Triage",
            "Lookup",
            "Assign",
            "Diagnose",
            "Escalate",
            "Patch",
            "Verify",
            "Reply",
            "Credit",
            "Close",
            "Survey",
            "Reopen",
            "Document",
        ],
    },
}

_STYLE_PALETTES: Dict[str, Dict[str, Any]] = {
    "blueprint": {
        "panel_fill": (246, 250, 255),
        "panel_border": (44, 72, 102),
        "title": (25, 41, 65),
        "lane_header": (219, 234, 249),
        "lane_fills": [(237, 246, 255), (245, 251, 255), (231, 241, 251), (240, 247, 253), (235, 243, 250)],
        "node_fill": (255, 255, 255),
        "node_border": (45, 77, 112),
        "edge": (46, 78, 112),
        "text": (20, 30, 45),
        "muted": (86, 100, 116),
    },
    "pastel_cards": {
        "panel_fill": (255, 253, 248),
        "panel_border": (135, 103, 84),
        "title": (65, 43, 33),
        "lane_header": (250, 230, 207),
        "lane_fills": [(253, 244, 232), (244, 250, 236), (236, 247, 249), (249, 239, 248), (245, 242, 233)],
        "node_fill": (255, 255, 252),
        "node_border": (123, 94, 75),
        "edge": (105, 86, 76),
        "text": (42, 34, 28),
        "muted": (114, 92, 78),
    },
    "graphite": {
        "panel_fill": (244, 245, 244),
        "panel_border": (58, 64, 70),
        "title": (32, 37, 42),
        "lane_header": (226, 229, 231),
        "lane_fills": [(247, 248, 248), (238, 241, 242), (250, 250, 247), (242, 244, 246), (246, 243, 241)],
        "node_fill": (255, 255, 255),
        "node_border": (69, 74, 82),
        "edge": (63, 70, 78),
        "text": (25, 28, 31),
        "muted": (87, 93, 100),
    },
    "warm_memo": {
        "panel_fill": (255, 250, 239),
        "panel_border": (111, 83, 108),
        "title": (53, 37, 66),
        "lane_header": (239, 223, 241),
        "lane_fills": [(255, 247, 232), (247, 239, 250), (238, 247, 240), (248, 240, 232), (239, 245, 249)],
        "node_fill": (255, 255, 252),
        "node_border": (99, 75, 111),
        "edge": (88, 78, 105),
        "text": (38, 31, 48),
        "muted": (104, 89, 112),
    },
}
_BADGE_COLORS: Dict[str, Tuple[int, int, int]] = {
    "Ready": (214, 238, 222),
    "Hold": (249, 224, 196),
    "Queued": (218, 230, 249),
    "Review": (238, 224, 249),
    "Done": (206, 234, 221),
    "Retry": (247, 216, 213),
}
_ROLE_FILL_ADJUST: Dict[str, Tuple[int, int, int]] = {
    "start": (226, 242, 235),
    "process": (255, 255, 255),
    "decision": (255, 249, 217),
    "review": (239, 236, 255),
    "data": (230, 245, 252),
    "output": (230, 239, 223),
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("pages", "process_flow")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS_SHARED = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=None,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_diagrams_background_defaults(task_group="process_flow")
POST_IMAGE_NOISE_DEFAULTS = load_diagrams_noise_defaults(task_group="process_flow", apply_prob=0.5)


def _resolve_defaults_for_task(task_id: str) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )
    weights = resolve_diagrams_complexity_weights(
        _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
        task_id=str(task_id),
    )
    return gen_defaults, render_defaults, prompt_defaults, weights


def _resolve_axis(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    supported_values: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    instance_seed: int,
    task_id: str,
    namespace: str,
) -> tuple[str, Dict[str, float]]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.{namespace}")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=gen_defaults,
        supported_variants=[str(value) for value in supported_values],
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    balanced = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=[str(value) for value in supported_values],
        balance_flag_key=str(balance_flag_key),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        sampling_namespace=f"{task_id}:{namespace}",
    )
    return str(balanced), {str(key): float(value) for key, value in probabilities.items()}


def _rounded_bbox(bbox: Sequence[float]) -> list[float]:
    return [round(float(value), 3) for value in bbox]


def _rounded_point(point: Sequence[float]) -> list[float]:
    return [round(float(value), 3) for value in point[:2]]


def _union_bbox(bboxes: Iterable[Sequence[float]], *, padding: float = 0.0) -> list[float]:
    resolved = [[float(value) for value in bbox] for bbox in bboxes if len(bbox) >= 4]
    if not resolved:
        return [0.0, 0.0, 0.0, 0.0]
    return [
        round(min(bbox[0] for bbox in resolved) - float(padding), 3),
        round(min(bbox[1] for bbox in resolved) - float(padding), 3),
        round(max(bbox[2] for bbox in resolved) + float(padding), 3),
        round(max(bbox[3] for bbox in resolved) + float(padding), 3),
    ]


def _point_bbox(points: Sequence[tuple[float, float]], *, padding: float) -> list[float]:
    if not points:
        return [0.0, 0.0, 0.0, 0.0]
    return [
        round(min(float(point[0]) for point in points) - float(padding), 3),
        round(min(float(point[1]) for point in points) - float(padding), 3),
        round(max(float(point[0]) for point in points) + float(padding), 3),
        round(max(float(point[1]) for point in points) + float(padding), 3),
    ]


def _lighten(color: Sequence[int], amount: float) -> tuple[int, int, int]:
    factor = max(0.0, min(1.0, float(amount)))
    return tuple(int(round(int(channel) + ((255 - int(channel)) * factor))) for channel in color[:3])


def _draw_text_in_box(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    text: str,
    max_size_px: int,
    min_size_px: int,
    fill: Sequence[int],
    bold: bool = True,
    stroke_fill: Sequence[int] = (255, 255, 255),
    padding_px: int = 5,
) -> list[float]:
    left, top, right, bottom = [float(value) for value in bbox]
    font = fit_font_to_box(
        draw,
        text=str(text),
        max_width=max(1.0, float(right - left - (2 * int(padding_px)))),
        max_height=max(1.0, float(bottom - top - (2 * int(padding_px)))),
        bold=bool(bold),
        min_size_px=int(min_size_px),
        max_size_px=int(max_size_px),
        fill_ratio=0.94,
    )
    return draw_centered_text(
        draw,
        text=str(text),
        center=(0.5 * (float(left) + float(right)), 0.5 * (float(top) + float(bottom))),
        font=font,
        fill=tuple(int(value) for value in fill),
        stroke_fill=tuple(int(value) for value in stroke_fill),
        stroke_width=1,
    )


def _draw_badge(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    text: str,
    fill: Sequence[int],
    outline: Sequence[int],
    text_fill: Sequence[int],
    font_size_px: int,
) -> list[float]:
    draw.rounded_rectangle(
        tuple(float(value) for value in bbox),
        radius=max(4, int((float(bbox[3]) - float(bbox[1])) * 0.45)),
        fill=tuple(int(value) for value in fill),
        outline=tuple(int(value) for value in outline),
        width=1,
    )
    return _draw_text_in_box(
        draw,
        bbox=bbox,
        text=str(text),
        max_size_px=int(font_size_px),
        min_size_px=8,
        fill=text_fill,
        bold=True,
        padding_px=4,
    )


def _shape_for_role(role: str) -> str:
    return {
        "start": "ellipse",
        "decision": "diamond",
        "review": "rounded",
        "data": "parallelogram",
        "output": "ellipse",
    }.get(str(role), "rounded")


def _draw_node(
    draw: ImageDraw.ImageDraw,
    *,
    node: Mapping[str, Any],
    palette: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> tuple[list[float], list[float]]:
    bbox = [float(value) for value in node["bbox"]]
    left, top, right, bottom = bbox
    role = str(node["role"])
    shape = str(node["shape"])
    fill = tuple(_ROLE_FILL_ADJUST.get(role, tuple(palette["node_fill"])))
    fill = _lighten(fill, 0.14 if role in {"decision", "review", "data"} else 0.0)
    outline = tuple(int(value) for value in palette["node_border"])
    width = max(2, int(render_defaults.get("node_border_width_px", 3)))
    radius = max(6, int(render_defaults.get("node_corner_radius_px", 16)))
    if shape == "diamond":
        points = [
            (0.5 * (left + right), top),
            (right, 0.5 * (top + bottom)),
            (0.5 * (left + right), bottom),
            (left, 0.5 * (top + bottom)),
        ]
        draw.polygon(points, fill=fill, outline=outline)
        for offset in range(1, width):
            inset = float(offset)
            inner = [
                (0.5 * (left + right), top + inset),
                (right - inset, 0.5 * (top + bottom)),
                (0.5 * (left + right), bottom - inset),
                (left + inset, 0.5 * (top + bottom)),
            ]
            draw.line(inner + [inner[0]], fill=outline, width=1)
    elif shape == "ellipse":
        draw.ellipse(tuple(bbox), fill=fill, outline=outline, width=width)
    elif shape == "parallelogram":
        slant = min(18.0, 0.14 * float(right - left))
        points = [(left + slant, top), (right, top), (right - slant, bottom), (left, bottom)]
        draw.polygon(points, fill=fill, outline=outline)
        draw.line(points + [points[0]], fill=outline, width=width)
    else:
        draw_rounded_rect(
            draw,
            tuple(bbox),
            radius=radius,
            fill=fill,
            outline=outline,
            width=width,
        )

    status = str(node["status"])
    has_badge = role not in {"start", "output"}
    if has_badge:
        badge_h = 18.0
        badge_w = min(76.0, max(50.0, 9.0 * len(status)))
        badge_bbox = [
            0.5 * (left + right) - (0.5 * badge_w),
            bottom - badge_h - 5.0,
            0.5 * (left + right) + (0.5 * badge_w),
            bottom - 5.0,
        ]
        label_bbox = [left + 11.0, top + 6.0, right - 11.0, badge_bbox[1] - 2.0]
    else:
        badge_bbox = [0.0, 0.0, 0.0, 0.0]
        label_bbox = [left + 10.0, top + 8.0, right - 10.0, bottom - 8.0]
    label_text_bbox = _draw_text_in_box(
        draw,
        bbox=label_bbox,
        text=str(node["label"]),
        max_size_px=int(render_defaults.get("node_label_font_size_px", 17)),
        min_size_px=10,
        fill=palette["text"],
        bold=True,
        stroke_fill=(255, 255, 255),
        padding_px=2,
    )
    if has_badge:
        status_bbox = _draw_badge(
            draw,
            bbox=badge_bbox,
            text=status,
            fill=_BADGE_COLORS.get(status, (232, 232, 232)),
            outline=palette["node_border"],
            text_fill=palette["text"],
            font_size_px=int(render_defaults.get("badge_font_size_px", 12)),
        )
    else:
        status_bbox = [0.0, 0.0, 0.0, 0.0]
    return _rounded_bbox(label_text_bbox), _rounded_bbox(status_bbox)


def _draw_arrowhead(draw: ImageDraw.ImageDraw, *, start: tuple[float, float], end: tuple[float, float], fill: Sequence[int], length: float, width: float) -> None:
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    dx = ex - sx
    dy = ey - sy
    seg_len = math.hypot(dx, dy)
    if seg_len <= 1e-6:
        return
    ux = dx / seg_len
    uy = dy / seg_len
    hl = min(float(length), 0.5 * seg_len)
    base = (ex - (ux * hl), ey - (uy * hl))
    px = -uy
    py = ux
    half_w = 0.5 * float(width)
    draw.polygon(
        [
            (ex, ey),
            (base[0] + (px * half_w), base[1] + (py * half_w)),
            (base[0] - (px * half_w), base[1] - (py * half_w)),
        ],
        fill=tuple(int(value) for value in fill),
        outline=tuple(int(value) for value in fill),
    )


def _draw_polyline_arrow(
    draw: ImageDraw.ImageDraw,
    *,
    points: Sequence[tuple[float, float]],
    fill: Sequence[int],
    width: int,
    head_length_px: float,
    head_width_px: float,
    dashed: bool,
) -> list[float]:
    clean = [(float(x), float(y)) for x, y in points]
    if len(clean) < 2:
        return [0.0, 0.0, 0.0, 0.0]
    for idx, (start, end) in enumerate(zip(clean, clean[1:])):
        is_last = idx == len(clean) - 2
        if dashed:
            draw_dashed_line(
                draw,
                start=start,
                end=end,
                fill=fill,
                width=max(1, int(width)),
                dash_px=10.0,
                gap_px=7.0,
            )
            if is_last:
                _draw_arrowhead(
                    draw,
                    start=start,
                    end=end,
                    fill=fill,
                    length=float(head_length_px),
                    width=float(head_width_px),
                )
        elif is_last:
            draw_arrow(
                draw,
                start=start,
                end=end,
                fill=fill,
                width=max(1, int(width)),
                head_length_px=float(head_length_px),
                head_width_px=float(head_width_px),
            )
        else:
            draw.line([start, end], fill=tuple(int(value) for value in fill), width=max(1, int(width)))
    return _point_bbox(clean, padding=max(7.0, float(width) + 4.0))


def _edge_points(
    *,
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    layout_variant: str,
) -> list[tuple[float, float]]:
    sx, sy = [float(value) for value in source["center"]]
    tx, ty = [float(value) for value in target["center"]]
    sw, sh = float(source["width"]), float(source["height"])
    tw, th = float(target["width"]), float(target["height"])
    vertical = str(layout_variant) in {"vertical_swimlane", "staggered_columns"}
    if vertical:
        start = (sx, sy + (0.5 * sh))
        end = (tx, ty - (0.5 * th))
        if abs(start[0] - end[0]) < 18.0:
            return [start, end]
        mid_y = 0.5 * (start[1] + end[1])
        return [start, (start[0], mid_y), (end[0], mid_y), end]
    start = (sx + (0.5 * sw), sy)
    end = (tx - (0.5 * tw), ty)
    if abs(start[1] - end[1]) < 18.0:
        return [start, end]
    mid_x = 0.5 * (start[0] + end[0])
    return [start, (mid_x, start[1]), (mid_x, end[1]), end]


def _edge_label_bbox(
    *,
    points: Sequence[tuple[float, float]],
    text: str,
    layout_variant: str,
    edge_index: int,
) -> list[float]:
    if len(points) < 2:
        return [0.0, 0.0, 0.0, 0.0]
    mid_segment = max(0, min(len(points) - 2, (len(points) - 1) // 2))
    a = points[mid_segment]
    b = points[mid_segment + 1]
    cx = 0.5 * (float(a[0]) + float(b[0]))
    cy = 0.5 * (float(a[1]) + float(b[1]))
    width = min(84.0, max(46.0, 9.5 * len(str(text)) + 16.0))
    height = 24.0
    offset = 16.0 if int(edge_index) % 2 == 0 else -16.0
    if str(layout_variant) in {"vertical_swimlane", "staggered_columns"}:
        cy += offset
    else:
        cx += offset
    return [cx - (0.5 * width), cy - (0.5 * height), cx + (0.5 * width), cy + (0.5 * height)]


def _draw_edge_label(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    text: str,
    palette: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> list[float]:
    draw.rounded_rectangle(
        tuple(float(value) for value in bbox),
        radius=9,
        fill=(255, 255, 255),
        outline=tuple(int(value) for value in palette["edge"]),
        width=1,
    )
    return _draw_text_in_box(
        draw,
        bbox=bbox,
        text=str(text),
        max_size_px=int(render_defaults.get("edge_label_font_size_px", 15)),
        min_size_px=9,
        fill=palette["text"],
        bold=True,
        stroke_fill=(255, 255, 255),
        padding_px=4,
    )


def _resolve_scene_geometry(
    *,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> tuple[int, int, tuple[float, float, float, float], tuple[float, float, float, float], tuple[float, float, float, float], Dict[str, Any]]:
    canvas_width = resolve_render_int(
        params,
        render_defaults,
        "canvas_width",
        1200,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.render",
    )
    canvas_height = resolve_render_int(
        params,
        render_defaults,
        "canvas_height",
        900,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.render",
    )
    outer_margin = resolve_render_int(
        params,
        render_defaults,
        "outer_margin_px",
        46,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.render",
    )
    title_band = resolve_render_int(
        params,
        render_defaults,
        "title_band_height_px",
        68,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.render",
    )
    panel_padding = resolve_render_int(
        params,
        render_defaults,
        "panel_padding_px",
        24,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.render",
    )
    jitter = resolve_layout_jitter(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.process_flow",
    )
    panel, title_bbox, content, jitter_meta = resolve_jittered_diagram_panel_geometry(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        outer_margin_px=int(outer_margin),
        title_band_height_px=int(title_band),
        panel_padding_px=int(panel_padding),
        layout_jitter_meta=jitter,
    )
    return int(canvas_width), int(canvas_height), panel, title_bbox, content, dict(jitter_meta)


def _make_base_nodes(
    *,
    rng,
    context: Mapping[str, Any],
    lanes: Sequence[str],
    target_node_count: int,
    endpoint_first_choice: int | None,
) -> tuple[list[Dict[str, Any]], list[Dict[str, Any]], Dict[str, str]]:
    labels = list(dict.fromkeys(str(label) for label in context["steps"]))
    if len(labels) > 3:
        offset = int(rng.randrange(0, min(3, len(labels))))
        labels = labels[offset:] + labels[:offset]
    lane_count = len(lanes)
    lane_for = {
        "n0": 0,
        "n1": min(1, lane_count - 1),
        "n2": min(1, lane_count - 1),
        "n3": min(2, lane_count - 1),
        "n4": max(0, lane_count - 2),
        "n5": min(2, lane_count - 1),
        "n6": min(3, lane_count - 1),
        "n7": min(3, lane_count - 1),
        "n8": lane_count - 1,
        "n9": lane_count - 1,
    }
    roles = {
        "n0": "start",
        "n1": "process",
        "n2": "decision",
        "n3": "process",
        "n4": "review",
        "n5": "data",
        "n6": "decision",
        "n7": "process",
        "n8": "output",
        "n9": "output",
    }
    levels = {
        "n0": 0,
        "n1": 1,
        "n2": 2,
        "n3": 3,
        "n4": 3,
        "n5": 4,
        "n6": 5,
        "n7": 6,
        "n8": 6,
        "n9": 7,
    }
    nodes: list[Dict[str, Any]] = []
    for index, node_id in enumerate([f"n{item}" for item in range(10)]):
        role = roles[node_id]
        label = labels[index % len(labels)]
        if role == "start":
            label = labels[0]
        elif node_id == "n9":
            label = labels[9 % len(labels)]
        nodes.append(
            {
                "node_id": node_id,
                "bbox_id": node_id,
                "label": label,
                "lane": str(lanes[lane_for[node_id] % lane_count]),
                "lane_index": int(lane_for[node_id] % lane_count),
                "role": role,
                "shape": _shape_for_role(role),
                "status": str(rng.choice(_STATUS_POOL)),
                "level": int(levels[node_id]),
                "order": int(index),
            }
        )
    cond_pair_a = list(rng.choice(_CONDITION_POOLS))
    cond_pair_b = list(rng.choice(_CONDITION_POOLS))
    if cond_pair_b == cond_pair_a:
        cond_pair_b = list(_CONDITION_POOLS[(list(_CONDITION_POOLS).index(tuple(cond_pair_a)) + 2) % len(_CONDITION_POOLS)])
    condition_map = {
        "first_left": str(cond_pair_a[0]),
        "first_right": str(cond_pair_a[1]),
        "second_left": str(cond_pair_b[0]),
        "second_right": str(cond_pair_b[1]),
    }
    edges = [
        {"edge_id": "e0", "source": "n0", "target": "n1", "label": "", "kind": "auto"},
        {"edge_id": "e1", "source": "n1", "target": "n2", "label": "", "kind": "auto"},
        {"edge_id": "e2", "source": "n2", "target": "n3", "label": condition_map["first_left"], "kind": "decision"},
        {"edge_id": "e3", "source": "n2", "target": "n4", "label": condition_map["first_right"], "kind": "decision"},
        {"edge_id": "e4", "source": "n3", "target": "n5", "label": "", "kind": "auto"},
        {"edge_id": "e5", "source": "n4", "target": "n5", "label": "", "kind": "auto"},
        {"edge_id": "e6", "source": "n5", "target": "n6", "label": "", "kind": "auto"},
        {"edge_id": "e7", "source": "n6", "target": "n7", "label": condition_map["second_left"], "kind": "decision"},
        {"edge_id": "e8", "source": "n6", "target": "n8", "label": condition_map["second_right"], "kind": "decision"},
        {"edge_id": "e9", "source": "n7", "target": "n9", "label": "", "kind": "auto"},
        {"edge_id": "e10", "source": "n8", "target": "n9", "label": "", "kind": "auto"},
    ]

    extra_count = max(0, int(target_node_count) - len(nodes))
    route_branch = "n3" if endpoint_first_choice == 0 else "n4" if endpoint_first_choice == 1 else None
    extra_sources = ["n3", "n4", "n5"]
    if route_branch in extra_sources:
        extra_sources = [source for source in extra_sources if source != route_branch]
    extra_labels = [label for label in labels if label not in {str(node["label"]) for node in nodes}]
    extra_roles = ["process", "review", "data"]
    for extra_idx in range(extra_count):
        role = str(rng.choice(extra_roles))
        level = int(rng.choice([3, 4, 5, 6]))
        node_id = f"n{10 + extra_idx}"
        lane_index = int(rng.randrange(0, lane_count))
        label = str(extra_labels[extra_idx % len(extra_labels)] if extra_labels else f"Step {extra_idx + 1}")
        nodes.append(
            {
                "node_id": node_id,
                "bbox_id": node_id,
                "label": label,
                "lane": str(lanes[lane_index]),
                "lane_index": int(lane_index),
                "role": role,
                "shape": _shape_for_role(role),
                "status": str(rng.choice(_STATUS_POOL)),
                "level": int(level),
                "order": int(10 + extra_idx),
            }
        )
        source = str(rng.choice(extra_sources))
        target = "n5" if source in {"n3", "n4"} else "n6"
        edges.append(
            {
                "edge_id": f"e{11 + (2 * extra_idx)}",
                "source": source,
                "target": node_id,
                "label": str(rng.choice(("audit", "copy", "notify", "check"))),
                "kind": "side",
            }
        )
        edges.append(
            {
                "edge_id": f"e{12 + (2 * extra_idx)}",
                "source": node_id,
                "target": target,
                "label": "",
                "kind": "auto",
            }
        )
    return nodes, edges, condition_map


def _assign_layout(
    *,
    nodes: list[Dict[str, Any]],
    lanes: Sequence[str],
    content_bbox: Sequence[float],
    layout_variant: str,
    render_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> tuple[list[Dict[str, Any]], Dict[str, list[float]]]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.layout.{layout_variant}")
    left, top, right, bottom = [float(value) for value in content_bbox]
    configured_lane_header_h = float(render_defaults.get("lane_header_height_px", 42))
    node_w_default = float(render_defaults.get("node_width_px", 146))
    node_h_default = float(render_defaults.get("node_height_px", 64))
    lane_bboxes: Dict[str, list[float]] = {}
    vertical = str(layout_variant) in {"vertical_swimlane", "staggered_columns"}
    lane_header_h = float(configured_lane_header_h if vertical else max(88.0, configured_lane_header_h))
    max_level = max(int(node["level"]) for node in nodes)
    occupancy: Dict[tuple[int, int], int] = {}
    if vertical:
        lane_w = float(right - left) / float(len(lanes))
        flow_top = top + lane_header_h
        flow_bottom = bottom
        for idx, lane in enumerate(lanes):
            lx0 = left + (idx * lane_w)
            lx1 = left + ((idx + 1) * lane_w)
            lane_bboxes[str(lane)] = _rounded_bbox([lx0, top, lx1, bottom])
        level_gap = float(flow_bottom - flow_top) / float(max(1, max_level))
        node_w = min(node_w_default, max(104.0, lane_w - 26.0))
        node_h = node_h_default
        for node in nodes:
            lane_index = int(node["lane_index"])
            level = int(node["level"])
            key = (lane_index, level)
            slot = occupancy.get(key, 0)
            occupancy[key] = slot + 1
            lane_center = left + ((lane_index + 0.5) * lane_w)
            x_jitter = rng.uniform(-0.12, 0.12) * lane_w if str(layout_variant) == "staggered_columns" else rng.uniform(-7.0, 7.0)
            y_jitter = (slot * (node_h * 0.50)) + rng.uniform(-8.0, 8.0)
            if slot:
                x_jitter += ((-1) ** slot) * min(24.0, 0.12 * lane_w)
            cx = max(left + 0.5 * node_w + 8.0, min(right - 0.5 * node_w - 8.0, lane_center + x_jitter))
            cy = max(flow_top + 0.5 * node_h + 8.0, min(flow_bottom - 0.5 * node_h - 8.0, flow_top + (level * level_gap) + y_jitter))
            node["center"] = [round(cx, 3), round(cy, 3)]
            node["width"] = round(node_w, 3)
            node["height"] = round(node_h, 3)
            node["bbox"] = _rounded_bbox([cx - 0.5 * node_w, cy - 0.5 * node_h, cx + 0.5 * node_w, cy + 0.5 * node_h])

        for lane_index in range(len(lanes)):
            lane_nodes = sorted(
                [node for node in nodes if int(node["lane_index"]) == int(lane_index)],
                key=lambda item: (int(item["level"]), int(item["order"])),
            )
            if len(lane_nodes) <= 1:
                continue
            y_min = flow_top + (0.5 * node_h) + 10.0
            y_max = flow_bottom - (0.5 * node_h) - 10.0
            gap = float(y_max - y_min) / float(max(1, len(lane_nodes) - 1))
            if gap < node_h + 16.0:
                gap = float(y_max - y_min) / float(max(1, len(lane_nodes) - 1))
            for idx, node in enumerate(lane_nodes):
                cx = float(node["center"][0])
                cy = float(y_min + (idx * gap)) if len(lane_nodes) > 1 else float(node["center"][1])
                node["center"] = [round(cx, 3), round(cy, 3)]
                node["bbox"] = _rounded_bbox([cx - 0.5 * node_w, cy - 0.5 * node_h, cx + 0.5 * node_w, cy + 0.5 * node_h])
    else:
        lane_h = float(bottom - top) / float(len(lanes))
        flow_left = left + lane_header_h
        flow_right = right
        for idx, lane in enumerate(lanes):
            ly0 = top + (idx * lane_h)
            ly1 = top + ((idx + 1) * lane_h)
            lane_bboxes[str(lane)] = _rounded_bbox([left, ly0, right, ly1])
        level_gap = float(flow_right - flow_left) / float(max(1, max_level))
        node_w = min(node_w_default, max(118.0, level_gap * 0.78))
        node_h = min(node_h_default, max(50.0, lane_h - 22.0))
        for node in nodes:
            lane_index = int(node["lane_index"])
            level = int(node["level"])
            key = (lane_index, level)
            slot = occupancy.get(key, 0)
            occupancy[key] = slot + 1
            lane_center = top + ((lane_index + 0.5) * lane_h)
            x_jitter = (slot * (node_w * 0.26)) + rng.uniform(-7.0, 7.0)
            y_jitter = rng.uniform(-0.10, 0.10) * lane_h if str(layout_variant) == "compact_rows" else rng.uniform(-7.0, 7.0)
            cy = max(top + 0.5 * node_h + 7.0, min(bottom - 0.5 * node_h - 7.0, lane_center + y_jitter))
            cx = max(flow_left + 0.5 * node_w + 8.0, min(flow_right - 0.5 * node_w - 8.0, flow_left + (level * level_gap) + x_jitter))
            node["center"] = [round(cx, 3), round(cy, 3)]
            node["width"] = round(node_w, 3)
            node["height"] = round(node_h, 3)
            node["bbox"] = _rounded_bbox([cx - 0.5 * node_w, cy - 0.5 * node_h, cx + 0.5 * node_w, cy + 0.5 * node_h])

        for lane_index in range(len(lanes)):
            lane_nodes = sorted(
                [node for node in nodes if int(node["lane_index"]) == int(lane_index)],
                key=lambda item: (int(item["level"]), int(item["order"])),
            )
            if len(lane_nodes) <= 1:
                continue
            x_min = flow_left + (0.5 * node_w) + 10.0
            x_max = flow_right - (0.5 * node_w) - 10.0
            gap = float(x_max - x_min) / float(max(1, len(lane_nodes) - 1))
            for idx, node in enumerate(lane_nodes):
                cx = float(x_min + (idx * gap)) if len(lane_nodes) > 1 else float(node["center"][0])
                cy = float(node["center"][1])
                node["center"] = [round(cx, 3), round(cy, 3)]
                node["bbox"] = _rounded_bbox([cx - 0.5 * node_w, cy - 0.5 * node_h, cx + 0.5 * node_w, cy + 0.5 * node_h])
    return nodes, lane_bboxes


def _render_scene(
    *,
    base_image: Image.Image,
    title: str,
    nodes: list[Dict[str, Any]],
    edges: list[Dict[str, Any]],
    lanes: Sequence[str],
    lane_bboxes: Mapping[str, Sequence[float]],
    panel_bbox: Sequence[float],
    title_bbox: Sequence[float],
    content_bbox: Sequence[float],
    layout_variant: str,
    style_variant: str,
    render_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> tuple[Image.Image, Dict[str, Any]]:
    image = base_image.convert("RGB")
    draw = ImageDraw.Draw(image)
    palette = _STYLE_PALETTES[str(style_variant)]
    panel_radius = int(render_defaults.get("panel_corner_radius_px", 24))
    draw.rounded_rectangle(
        tuple(float(value) for value in panel_bbox),
        radius=panel_radius,
        fill=tuple(int(value) for value in palette["panel_fill"]),
        outline=tuple(int(value) for value in palette["panel_border"]),
        width=3,
    )
    title_font = load_font(int(render_defaults.get("title_font_size_px", 30)), bold=True)
    draw_centered_text(
        draw,
        text=str(title),
        center=(0.5 * (float(title_bbox[0]) + float(title_bbox[2])), 0.5 * (float(title_bbox[1]) + float(title_bbox[3]))),
        font=title_font,
        fill=tuple(int(value) for value in palette["title"]),
        stroke_fill=(255, 255, 255),
        stroke_width=1,
    )
    vertical = str(layout_variant) in {"vertical_swimlane", "staggered_columns"}
    lane_fills = list(palette["lane_fills"])
    lane_header_fill = tuple(int(value) for value in palette["lane_header"])
    lane_font = load_font(int(render_defaults.get("lane_font_size_px", 18)), bold=True)
    for idx, lane in enumerate(lanes):
        bbox = [float(value) for value in lane_bboxes[str(lane)]]
        fill = tuple(int(value) for value in lane_fills[idx % len(lane_fills)])
        draw.rectangle(tuple(bbox), fill=fill)
        draw.rectangle(tuple(bbox), outline=tuple(int(value) for value in palette["panel_border"]), width=1)
        if vertical:
            header_bbox = [bbox[0], bbox[1], bbox[2], bbox[1] + float(render_defaults.get("lane_header_height_px", 42))]
        else:
            header_bbox = [bbox[0], bbox[1], bbox[0] + float(render_defaults.get("lane_header_height_px", 42)), bbox[3]]
        draw.rectangle(tuple(header_bbox), fill=lane_header_fill, outline=tuple(int(value) for value in palette["panel_border"]), width=1)
        draw_centered_text(
            draw,
            text=str(lane),
            center=(0.5 * (header_bbox[0] + header_bbox[2]), 0.5 * (header_bbox[1] + header_bbox[3])),
            font=lane_font,
            fill=tuple(int(value) for value in palette["title"]),
            stroke_fill=(255, 255, 255),
            stroke_width=1,
        )

    node_by_id = {str(node["node_id"]): node for node in nodes}
    edge_bbox_map: Dict[str, list[float]] = {}
    edge_point_pair_map: Dict[str, list[list[float]]] = {}
    edge_polyline_map: Dict[str, list[list[float]]] = {}
    edge_label_bbox_map: Dict[str, list[float]] = {}
    edge_label_text_bbox_map: Dict[str, list[float]] = {}
    edge_style_rng = spawn_rng(int(instance_seed), f"{task_id}.edge_style")
    dashed_side_edges = bool(edge_style_rng.randrange(0, 2))
    for edge_idx, edge in enumerate(edges):
        source = node_by_id[str(edge["source"])]
        target = node_by_id[str(edge["target"])]
        points = _edge_points(source=source, target=target, layout_variant=str(layout_variant))
        dashed = dashed_side_edges and str(edge.get("kind", "")) == "side"
        edge_bbox_map[str(edge["edge_id"])] = _draw_polyline_arrow(
            draw,
            points=points,
            fill=palette["edge"],
            width=int(render_defaults.get("edge_width_px", 4)),
            head_length_px=float(render_defaults.get("arrow_head_length_px", 15)),
            head_width_px=float(render_defaults.get("arrow_head_width_px", 13)),
            dashed=bool(dashed),
        )
        rounded_points = [_rounded_point((x, y)) for x, y in points]
        edge_point_pair_map[str(edge["edge_id"])] = [list(rounded_points[0]), list(rounded_points[-1])]
        edge_polyline_map[str(edge["edge_id"])] = [list(point) for point in rounded_points]
        edge["points"] = [list(point) for point in rounded_points]
        edge["edge_bbox_id"] = str(edge["edge_id"])
        edge["bbox"] = list(edge_bbox_map[str(edge["edge_id"])])
        if str(edge.get("label", "")).strip():
            label_bbox = _edge_label_bbox(
                points=points,
                text=str(edge["label"]),
                layout_variant=str(layout_variant),
                edge_index=int(edge_idx),
            )
            edge_label_bbox_map[str(edge["edge_id"])] = _rounded_bbox(label_bbox)
            edge_label_text_bbox_map[str(edge["edge_id"])] = _draw_edge_label(
                draw,
                bbox=label_bbox,
                text=str(edge["label"]),
                palette=palette,
                render_defaults=render_defaults,
            )
            edge["label_bbox_id"] = str(edge["edge_id"])
            edge["label_bbox"] = list(edge_label_bbox_map[str(edge["edge_id"])])

    node_bbox_map: Dict[str, list[float]] = {}
    node_label_bbox_map: Dict[str, list[float]] = {}
    node_status_bbox_map: Dict[str, list[float]] = {}
    for node in nodes:
        label_bbox, status_bbox = _draw_node(draw, node=node, palette=palette, render_defaults=render_defaults)
        node_bbox_map[str(node["bbox_id"])] = list(node["bbox"])
        node_label_bbox_map[str(node["bbox_id"])] = list(label_bbox)
        if any(float(value) for value in status_bbox):
            node_status_bbox_map[str(node["bbox_id"])] = list(status_bbox)

    render_map = {
        "panel_bbox_px": round_diagram_bbox(panel_bbox),
        "title_bbox_px": round_diagram_bbox(title_bbox),
        "content_bbox_px": round_diagram_bbox(content_bbox),
        "lane_bboxes_px": {str(key): _rounded_bbox(value) for key, value in lane_bboxes.items()},
        "node_bboxes_px": node_bbox_map,
        "node_label_bboxes_px": node_label_bbox_map,
        "node_status_bboxes_px": node_status_bbox_map,
        "edge_bboxes_px": edge_bbox_map,
        "edge_point_pairs_px": edge_point_pair_map,
        "edge_polylines_px": edge_polyline_map,
        "edge_label_bboxes_px": edge_label_bbox_map,
        "edge_label_text_bboxes_px": edge_label_text_bbox_map,
    }
    return image, render_map


def _condition_path_query(
    *,
    rng,
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    first_choice = int(rng.randrange(0, 2))
    second_choice = int(rng.randrange(0, 2))
    first_edge_id = "e2" if first_choice == 0 else "e3"
    second_edge_id = "e7" if second_choice == 0 else "e8"
    first_target = "n3" if first_choice == 0 else "n4"
    second_target = "n7" if second_choice == 0 else "n8"
    edge_by_id = {str(edge["edge_id"]): edge for edge in edges}
    node_by_id = {str(node["node_id"]): node for node in nodes}
    path_node_ids = ["n0", "n1", "n2", first_target, "n5", "n6", second_target]
    labels = [str(edge_by_id[first_edge_id]["label"]), str(edge_by_id[second_edge_id]["label"])]
    return {
        "query_id": "condition_path_endpoint_label",
        "task_key": _TASK_KEYS["condition_path_endpoint_label"],
        "answer": str(node_by_id[second_target]["label"]),
        "answer_node_id": str(second_target),
        "annotation_roles": [
            {"key": "start_step", "kind": "node", "id": "n0"},
            {"key": "first_decision_label", "kind": "edge_label", "id": first_edge_id},
            {"key": "intermediate_step", "kind": "node", "id": first_target},
            {"key": "second_decision_label", "kind": "edge_label", "id": second_edge_id},
            {"key": "endpoint_step", "kind": "node", "id": second_target},
        ],
        "annotation_node_ids": [str(node_id) for node_id in path_node_ids],
        "annotation_edge_label_ids": [first_edge_id, second_edge_id],
        "condition_labels": labels,
        "condition_sequence_text": f"\"{labels[0]}\" then \"{labels[1]}\"",
        "start_label": str(node_by_id["n0"]["label"]),
        "path_node_labels": [str(node_by_id[node_id]["label"]) for node_id in path_node_ids],
        "answer_type": "string",
    }


def _choose_answer_balanced_candidate(
    candidates: Sequence[Mapping[str, Any]],
    *,
    rng,
    min_answer: int = 1,
) -> Dict[str, Any]:
    """Choose a candidate by answer bucket first, then by candidate.

    The scene may naturally contain many low-count candidates. Bucket-first
    selection keeps the generated calibration set from collapsing onto one
    integer answer while preserving the exact rendered scene semantics.
    """
    pool = [dict(candidate) for candidate in candidates]
    if not pool:
        raise ValueError("process-flow query selector received no candidates")
    eligible = [candidate for candidate in pool if int(candidate.get("answer", 0)) >= int(min_answer)]
    if eligible:
        pool = eligible
    by_answer: Dict[int, list[Dict[str, Any]]] = {}
    for candidate in pool:
        by_answer.setdefault(int(candidate["answer"]), []).append(candidate)
    answer_bucket = int(rng.choice(sorted(by_answer)))
    return dict(rng.choice(by_answer[answer_bucket]))


def _choose_from_answer_support(
    candidates: Sequence[Mapping[str, Any]],
    *,
    rng,
    answer_support: Sequence[int],
) -> Dict[str, Any]:
    """Choose a candidate by a seeded target answer, falling back to nearby available answers."""

    by_answer: Dict[int, list[Dict[str, Any]]] = {}
    for candidate in candidates:
        by_answer.setdefault(int(candidate["answer"]), []).append(dict(candidate))
    if not by_answer:
        raise ValueError("process-flow answer-support selector received no candidates")
    support = [int(value) for value in answer_support]
    target = int(support[int(rng.randrange(len(support)))])
    if target in by_answer:
        answer_bucket = int(target)
    else:
        available = sorted(by_answer)
        distance = min(abs(int(value) - int(target)) for value in available)
        tied = [int(value) for value in available if abs(int(value) - int(target)) == int(distance)]
        answer_bucket = int(max(tied))
    return dict(rng.choice(by_answer[int(answer_bucket)]))


def _select_filtered_query(
    *,
    query_id: str,
    nodes: Sequence[Mapping[str, Any]],
    rng,
) -> Dict[str, Any]:
    candidates_by_query: Dict[str, list[Dict[str, Any]]] = {key: [] for key in _FILTER_QUERY_IDS}
    visible_status_nodes = [node for node in nodes if str(node["role"]) not in {"start", "output"}]
    for shape, description in _SHAPE_DESCRIPTIONS.items():
        ids = [str(node["node_id"]) for node in nodes if str(node["shape"]) == str(shape)]
        if ids:
            candidates_by_query["shape_node_count"].append(
                {
                    "query_id": "shape_node_count",
                    "task_key": _TASK_KEYS["shape_node_count"],
                    "shape": str(shape),
                    "shape_description": str(description),
                    "shape_filter_description": str(description),
                    "filter_mode": "include",
                    "answer": int(len(ids)),
                    "annotation_node_ids": ids,
                    "answer_type": "integer",
                }
            )
        complement_ids = [str(node["node_id"]) for node in nodes if str(node["shape"]) != str(shape)]
        if complement_ids:
            candidates_by_query["shape_node_count"].append(
                {
                    "query_id": "shape_node_count",
                    "task_key": _TASK_KEYS["shape_node_count"],
                    "shape": str(shape),
                    "shape_description": str(description),
                    "shape_filter_description": f"not {description}",
                    "filter_mode": "exclude",
                    "answer": int(len(complement_ids)),
                    "annotation_node_ids": complement_ids,
                    "answer_type": "integer",
                }
            )
    for status in _STATUS_POOL:
        ids = [str(node["node_id"]) for node in visible_status_nodes if str(node["status"]) == str(status)]
        if ids:
            candidates_by_query["status_node_count"].append(
                {
                    "query_id": "status_node_count",
                    "task_key": _TASK_KEYS["status_node_count"],
                    "status_name": str(status),
                    "status_filter_description": f"marked {status}",
                    "filter_mode": "include",
                    "answer": int(len(ids)),
                    "annotation_node_ids": ids,
                    "answer_type": "integer",
                }
            )
        complement_ids = [str(node["node_id"]) for node in visible_status_nodes if str(node["status"]) != str(status)]
        if complement_ids:
            candidates_by_query["status_node_count"].append(
                {
                    "query_id": "status_node_count",
                    "task_key": _TASK_KEYS["status_node_count"],
                    "status_name": str(status),
                    "status_filter_description": f"not marked {status}",
                    "filter_mode": "exclude",
                    "answer": int(len(complement_ids)),
                    "annotation_node_ids": complement_ids,
                    "answer_type": "integer",
                }
            )
    for role, description in _ROLE_DESCRIPTIONS.items():
        ids = [str(node["node_id"]) for node in nodes if str(node["role"]) == str(role)]
        if ids:
            candidates_by_query["role_node_count"].append(
                {
                    "query_id": "role_node_count",
                    "task_key": _TASK_KEYS["role_node_count"],
                    "role_name": str(role),
                    "role_description": str(description),
                    "role_filter_description": str(description),
                    "filter_mode": "include",
                    "answer": int(len(ids)),
                    "annotation_node_ids": ids,
                    "answer_type": "integer",
                }
            )
        complement_ids = [str(node["node_id"]) for node in nodes if str(node["role"]) != str(role)]
        if complement_ids:
            candidates_by_query["role_node_count"].append(
                {
                    "query_id": "role_node_count",
                    "task_key": _TASK_KEYS["role_node_count"],
                    "role_name": str(role),
                    "role_description": str(description),
                    "role_filter_description": f"not {description}",
                    "filter_mode": "exclude",
                    "answer": int(len(complement_ids)),
                    "annotation_node_ids": complement_ids,
                    "answer_type": "integer",
                }
            )
    preferred = candidates_by_query.get(str(query_id), [])
    if preferred:
        return _choose_answer_balanced_candidate(preferred, rng=rng, min_answer=2)
    all_candidates = [candidate for candidates in candidates_by_query.values() for candidate in candidates]
    if not all_candidates:
        raise ValueError("process-flow filtered query could not find any count candidate")
    return _choose_answer_balanced_candidate(all_candidates, rng=rng, min_answer=2)


def _select_handoff_query(
    *,
    query_id: str,
    nodes: Sequence[Mapping[str, Any]],
    edges: Sequence[Mapping[str, Any]],
    rng,
) -> Dict[str, Any]:
    node_by_id = {str(node["node_id"]): node for node in nodes}
    cross_edges = [
        edge
        for edge in edges
        if str(node_by_id[str(edge["source"])]["lane"]) != str(node_by_id[str(edge["target"])]["lane"])
    ]
    if not cross_edges:
        raise ValueError("process-flow scene has no cross-lane handoff arrows")
    lanes = sorted({str(node["lane"]) for node in nodes})
    candidates_by_query: Dict[str, list[Dict[str, Any]]] = {
        "all_cross_lane_handoff_count": [
            {
                "query_id": "all_cross_lane_handoff_count",
                "task_key": _TASK_KEYS["all_cross_lane_handoff_count"],
                "answer": int(len(cross_edges)),
                "annotation_edge_ids": [str(edge["edge_id"]) for edge in cross_edges],
                "answer_type": "integer",
            }
        ],
        "lane_outgoing_handoff_count": [],
        "lane_involved_handoff_count": [],
    }
    for lane in lanes:
        source_edges = [
            edge
            for edge in cross_edges
            if str(node_by_id[str(edge["source"])]["lane"]) == str(lane)
        ]
        if source_edges:
            candidates_by_query["lane_outgoing_handoff_count"].append(
                {
                    "query_id": "lane_outgoing_handoff_count",
                    "task_key": _TASK_KEYS["lane_outgoing_handoff_count"],
                    "lane_name": str(lane),
                    "answer": int(len(source_edges)),
                    "annotation_edge_ids": [str(edge["edge_id"]) for edge in source_edges],
                    "answer_type": "integer",
                }
            )
        involved_edges = [
            edge
            for edge in cross_edges
            if str(node_by_id[str(edge["source"])]["lane"]) == str(lane)
            or str(node_by_id[str(edge["target"])]["lane"]) == str(lane)
        ]
        if involved_edges:
            candidates_by_query["lane_involved_handoff_count"].append(
                {
                    "query_id": "lane_involved_handoff_count",
                    "task_key": _TASK_KEYS["lane_involved_handoff_count"],
                    "lane_name": str(lane),
                    "answer": int(len(involved_edges)),
                    "annotation_edge_ids": [str(edge["edge_id"]) for edge in involved_edges],
                    "answer_type": "integer",
                }
            )
    preferred = candidates_by_query.get(str(query_id), [])
    if preferred:
        if str(query_id) == "lane_outgoing_handoff_count":
            return _choose_from_answer_support(preferred, rng=rng, answer_support=(1, 2, 3, 4, 5, 6, 7))
        return _choose_answer_balanced_candidate(preferred, rng=rng, min_answer=2)
    all_candidates = [candidate for candidates in candidates_by_query.values() for candidate in candidates]
    return _choose_answer_balanced_candidate(all_candidates, rng=rng, min_answer=2)


def _build_prompt_json_examples(*, answer_type: str, annotation_kind: str) -> tuple[str, str]:
    annotation: Any
    if str(annotation_kind) == "path":
        annotation = {
            "start_step": [126, 208, 260, 270],
            "first_decision_label": [286, 254, 340, 278],
            "intermediate_step": [360, 300, 494, 362],
            "second_decision_label": [512, 412, 570, 436],
            "endpoint_step": [630, 458, 764, 520],
        }
    elif str(annotation_kind) == "handoff":
        annotation = [
            [[272, 294], [462, 348]],
            [[526, 408], [706, 462]],
        ]
    else:
        annotation = {
            "node": [[168, 246, 302, 308], [340, 386, 474, 448]],
        }.get(str(annotation_kind), [[168, 246, 302, 308]])
    answer_value: Any = "Publish" if str(answer_type) == "string" else 3
    answer_and_annotation = {"annotation": annotation, "answer": answer_value}
    answer_only = {"answer": answer_value}
    return (
        json.dumps(answer_and_annotation, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _build_scene_and_query(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float]]:
    query_supported = _TASK_QUERY_IDS[str(task_id)]
    query_id, query_probabilities = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        supported_values=query_supported,
        explicit_key="query_id",
        weights_key="query_weights",
        balance_flag_key="balanced_query_sampling",
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        namespace="query",
    )
    context_id, context_probabilities = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        supported_values=_CONTEXT_VARIANTS,
        explicit_key="context_id",
        weights_key="context_weights",
        balance_flag_key="balanced_context_sampling",
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        namespace="context",
    )
    layout_variant, layout_probabilities = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        supported_values=_LAYOUT_VARIANTS,
        explicit_key="layout_variant",
        weights_key="layout_weights",
        balance_flag_key="balanced_layout_sampling",
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        namespace="layout",
    )
    style_variant, style_probabilities = _resolve_axis(
        params=params,
        gen_defaults=gen_defaults,
        supported_values=_STYLE_VARIANTS,
        explicit_key="style_variant",
        weights_key="style_weights",
        balance_flag_key="balanced_style_sampling",
        instance_seed=int(instance_seed),
        task_id=str(task_id),
        namespace="style",
    )
    lane_min, lane_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="lane_count_min",
        max_key="lane_count_max",
        fallback_min=3,
        fallback_max=5,
        context=str(task_id),
    )
    node_min, node_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="node_count_min",
        max_key="node_count_max",
        fallback_min=10,
        fallback_max=14,
        context=str(task_id),
    )
    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    lane_count = int(rng.randint(int(lane_min), int(lane_max)))
    node_count = int(rng.randint(int(node_min), int(node_max)))
    context = deepcopy(_CONTEXTS[str(context_id)])
    lanes = list(context["lanes"])
    rng.shuffle(lanes)
    lanes = [str(lane) for lane in lanes[:lane_count]]

    endpoint_first_choice = None
    if str(task_id) == CONDITION_PATH_ENDPOINT_TASK_ID:
        endpoint_first_choice = int(spawn_rng(int(instance_seed), f"{task_id}.endpoint_choice").randrange(0, 2))
    nodes, edges, condition_map = _make_base_nodes(
        rng=rng,
        context=context,
        lanes=lanes,
        target_node_count=node_count,
        endpoint_first_choice=endpoint_first_choice,
    )

    canvas_width, canvas_height, panel, title_bbox, content, jitter_meta = _resolve_scene_geometry(
        params=params,
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
    )
    nodes, lane_bboxes = _assign_layout(
        nodes=nodes,
        lanes=lanes,
        content_bbox=content,
        layout_variant=str(layout_variant),
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
    )

    if str(task_id) == CONDITION_PATH_ENDPOINT_TASK_ID:
        query = _condition_path_query(rng=rng, nodes=nodes, edges=edges)
    elif str(task_id) == FILTERED_NODE_COUNT_TASK_ID:
        query = _select_filtered_query(query_id=str(query_id), nodes=nodes, rng=rng)
    else:
        query = _select_handoff_query(query_id=str(query_id), nodes=nodes, edges=edges, rng=rng)

    scene = {
        "scene_id": SCENE_ID,
        "context_id": str(context_id),
        "scene_title": str(context["title"]),
        "layout_variant": str(layout_variant),
        "style_variant": str(style_variant),
        "lanes": list(lanes),
        "lane_count": int(len(lanes)),
        "node_count": int(len(nodes)),
        "edge_count": int(len(edges)),
        "decision_count": int(sum(1 for node in nodes if str(node["role"]) == "decision")),
        "condition_map": dict(condition_map),
        "nodes": [dict(node) for node in nodes],
        "edges": [dict(edge) for edge in edges],
        "canvas_width": int(canvas_width),
        "canvas_height": int(canvas_height),
        "panel_bbox": list(panel),
        "title_bbox": list(title_bbox),
        "content_bbox": list(content),
        "lane_bboxes": dict(lane_bboxes),
        "layout_jitter": dict(jitter_meta),
    }
    return scene, query, query_probabilities, context_probabilities, layout_probabilities, style_probabilities


def _build_output(
    *,
    task_id: str,
    domain: str,
    task_group: str,
    instance_seed: int,
    params: Dict[str, Any],
    max_attempts: int,
) -> TaskOutput:
    del max_attempts
    gen_defaults, render_defaults, prompt_defaults, complexity_weights = _resolve_defaults_for_task(str(task_id))
    scene, query, query_probabilities, context_probabilities, layout_probabilities, style_probabilities = _build_scene_and_query(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        render_defaults=render_defaults,
    )
    background, background_meta = make_background_canvas(
        canvas_width=int(scene["canvas_width"]),
        canvas_height=int(scene["canvas_height"]),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    rendered, render_map = _render_scene(
        base_image=background,
        title=str(scene["scene_title"]),
        nodes=list(scene["nodes"]),
        edges=list(scene["edges"]),
        lanes=list(scene["lanes"]),
        lane_bboxes=dict(scene["lane_bboxes"]),
        panel_bbox=list(scene["panel_bbox"]),
        title_bbox=list(scene["title_bbox"]),
        content_bbox=list(scene["content_bbox"]),
        layout_variant=str(scene["layout_variant"]),
        style_variant=str(scene["style_variant"]),
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
    )
    image, post_noise_meta = apply_post_image_noise(
        rendered,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )

    prompt_defaults = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "object_description",
            "json_output_contract",
            "json_output_contract_answer_only",
            "integer_answer_hint",
            "label_answer_hint",
            "annotation_hint_node_count",
            "annotation_hint_path_endpoint",
            "annotation_hint_handoff_count",
        ),
        context=f"prompt defaults for {task_id}",
    )
    annotation_kind = "node"
    if str(task_id) == CONDITION_PATH_ENDPOINT_TASK_ID:
        annotation_kind = "path"
        answer_hint = str(prompt_defaults["label_answer_hint"])
        annotation_hint = str(prompt_defaults["annotation_hint_path_endpoint"])
        answer_type = "string"
    elif _is_handoff_task(str(task_id)):
        annotation_kind = "handoff"
        answer_hint = str(prompt_defaults["integer_answer_hint"])
        annotation_hint = str(prompt_defaults["annotation_hint_handoff_count"])
        answer_type = "integer"
    else:
        answer_hint = str(prompt_defaults["integer_answer_hint"])
        annotation_hint = str(prompt_defaults["annotation_hint_node_count"])
        answer_type = "integer"
    json_example, json_example_answer_only = _build_prompt_json_examples(answer_type=str(answer_type), annotation_kind=annotation_kind)
    slots = {
        "object_description": str(prompt_defaults["object_description"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(answer_hint),
        "annotation_hint": str(annotation_hint),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
    }
    slots.update({str(key): value for key, value in query.items() if key not in {"answer", "annotation_node_ids", "annotation_edge_ids", "annotation_edge_label_ids"}})

    prompt_selection = render_task_prompt_variants(
        domain=str(domain),
        task_group=str(task_group),
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(query["task_key"]),
        query_key=str(query["query_id"]),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

    node_bbox_map = dict(render_map["node_bboxes_px"])
    edge_bbox_map = dict(render_map["edge_bboxes_px"])
    edge_point_pair_map = dict(render_map["edge_point_pairs_px"])
    edge_label_bbox_map = dict(render_map["edge_label_bboxes_px"])
    annotation_ids: list[str] = []
    annotation_key_to_bbox_id: Dict[str, str] = {}
    annotation_keyed_bboxes: Dict[str, list[float]] = {}
    annotation_point_pairs: list[list[list[float]]] = []
    bbox_source_map: Dict[str, Sequence[float]] = {}
    if str(task_id) == CONDITION_PATH_ENDPOINT_TASK_ID:
        for role in query.get("annotation_roles", []):
            annotation_key = str(role["key"])
            source_kind = str(role["kind"])
            source_id = str(role["id"])
            if source_kind == "node":
                bbox_id = f"node:{source_id}"
                bbox = node_bbox_map[str(source_id)]
            elif source_kind == "edge_label":
                bbox_id = f"edge_label:{source_id}"
                bbox = edge_label_bbox_map[str(source_id)]
            else:
                raise ValueError(f"unsupported process-flow annotation role kind: {source_kind}")
            annotation_ids.append(bbox_id)
            annotation_key_to_bbox_id[annotation_key] = bbox_id
            annotation_keyed_bboxes[annotation_key] = [round(float(value), 3) for value in bbox]
    elif _is_handoff_task(str(task_id)):
        for edge_id in [str(item) for item in query.get("annotation_edge_ids", [])]:
            annotation_ids.append(f"edge_points:{edge_id}")
            annotation_point_pairs.append(
                [
                    [round(float(value), 3) for value in point]
                    for point in edge_point_pair_map[str(edge_id)]
                ]
            )
    else:
        for node_id in [str(item) for item in query.get("annotation_node_ids", [])]:
            annotation_ids.append(f"node:{node_id}")
            bbox_source_map[f"node:{node_id}"] = node_bbox_map[str(node_id)]
    if str(task_id) == CONDITION_PATH_ENDPOINT_TASK_ID:
        annotation_bboxes = [list(bbox) for bbox in annotation_keyed_bboxes.values()]
        annotation_projection = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_keyed_bboxes),
            "pixel_keyed_bbox_map": dict(annotation_keyed_bboxes),
            "bbox_set": list(annotation_bboxes),
            "annotation_keys": list(annotation_keyed_bboxes.keys()),
            "annotation_key_to_bbox_id": dict(annotation_key_to_bbox_id),
        }
    elif _is_handoff_task(str(task_id)):
        annotation_bboxes = []
        annotation_projection = {
            "type": "point_pair_set",
            "point_pair_set": list(annotation_point_pairs),
            "pixel_point_pair_set": list(annotation_point_pairs),
            "annotation_ids": list(annotation_ids),
        }
    else:
        annotation_projection = projected_diagram_bbox_annotation(bbox_source_map, annotation_ids)
        annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in annotation_projection["bbox_set"]]
    if str(answer_type) == "string":
        answer_gt = TypedValue(type="string", value=str(query["answer"]))
    else:
        answer_gt = TypedValue(type="integer", value=int(query["answer"]))
    if str(task_id) == CONDITION_PATH_ENDPOINT_TASK_ID:
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_keyed_bboxes))
    elif _is_handoff_task(str(task_id)):
        annotation_gt = TypedValue(type="point_pair_set", value=list(annotation_point_pairs))
    else:
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))

    node_scan = normalize_int_with_bounds(int(scene["node_count"]), [10, 16])
    lane_scan = normalize_int_with_bounds(int(scene["lane_count"]), [3, 5])
    branch_scan = normalize_int_with_bounds(int(scene["decision_count"]), [2, 4])
    answer_load = normalize_int_with_bounds(
        int(len(annotation_ids)) if str(answer_type) == "string" else int(answer_gt.value),
        [1, 14],
    )
    base_reasoning = {
        FILTERED_NODE_COUNT_TASK_ID: 0.34,
        CONDITION_PATH_ENDPOINT_TASK_ID: 0.58,
        ALL_CROSS_LANE_HANDOFF_COUNT_TASK_ID: 0.46,
        LANE_FILTERED_HANDOFF_COUNT_TASK_ID: 0.52,
    }[str(task_id)]
    reasoning_load = clamp_unit_interval(float(base_reasoning) + (0.18 * answer_load) + (0.10 * branch_scan))
    complexity = build_diagrams_complexity(
        weights=complexity_weights,
        components={
            "visual_scan": float(node_scan),
            "reasoning_load": float(reasoning_load),
            "lane_count": float(lane_scan),
            "branch_count": float(branch_scan),
        },
    )

    node_specs = [
        {
            key: value
            for key, value in dict(node).items()
            if key not in {"center", "width", "height"}
        }
        for node in scene["nodes"]
    ]
    edge_specs = [
        {
            key: value
            for key, value in dict(edge).items()
            if key not in {"points", "bbox", "label_bbox"}
        }
        for edge in scene["edges"]
    ]
    trace_payload = {
        "scene_ir": {
            "scene_id": SCENE_ID,
            "scene_kind": "pages_process_flow_diagram",
            "entities": [
                {
                    "entity_id": str(node["node_id"]),
                    "entity_type": "process_step",
                    "label": str(node["label"]),
                    "lane": str(node["lane"]),
                    "role": str(node["role"]),
                    "status": str(node["status"]),
                    "shape": str(node["shape"]),
                    "bbox_id": str(node["bbox_id"]),
                }
                for node in scene["nodes"]
            ],
            "relations": {
                "query_id": str(query["query_id"]),
                "scene_variant": str(scene["layout_variant"]),
                "layout_variant": str(scene["layout_variant"]),
                "style_variant": str(scene["style_variant"]),
                "context_id": str(scene["context_id"]),
            },
        },
        "query_spec": {
            "query_id": str(query["query_id"]),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "query_id": str(query["query_id"]),
                "query_id_probabilities": dict(query_probabilities),
                "context_id": str(scene["context_id"]),
                "context_probabilities": dict(context_probabilities),
                "layout_variant": str(scene["layout_variant"]),
                "layout_probabilities": dict(layout_probabilities),
                "style_variant": str(scene["style_variant"]),
                "style_probabilities": dict(style_probabilities),
                "node_count": int(scene["node_count"]),
                "lane_count": int(scene["lane_count"]),
            },
        },
        "render_spec": {
            "scene_id": SCENE_ID,
            "query_id": str(query["query_id"]),
            "scene_variant": str(scene["layout_variant"]),
            "layout_variant": str(scene["layout_variant"]),
            "style_variant": str(scene["style_variant"]),
            "geometry_seed": int(instance_seed),
            "canvas_width": int(scene["canvas_width"]),
            "canvas_height": int(scene["canvas_height"]),
            "layout_jitter": dict(scene["layout_jitter"]),
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
        },
        "render_map": dict(render_map),
        "execution_trace": {
            "query_id": str(query["query_id"]),
            "question_format": str(query["query_id"]),
            "view_family": SCENE_ID,
            "scene_title": str(scene["scene_title"]),
            "context_id": str(scene["context_id"]),
            "layout_variant": str(scene["layout_variant"]),
            "style_variant": str(scene["style_variant"]),
            "lanes": list(scene["lanes"]),
            "node_count": int(scene["node_count"]),
            "edge_count": int(scene["edge_count"]),
            "decision_count": int(scene["decision_count"]),
            "node_specs": node_specs,
            "edge_specs": edge_specs,
            "query": {key: value for key, value in query.items() if key not in {"task_key"}},
            "answer": answer_gt.to_dict(),
            "annotation_ids": list(annotation_ids),
            "annotation_key_to_bbox_id": dict(annotation_key_to_bbox_id),
            "supporting_bbox_ids": [] if _is_handoff_task(str(task_id)) else list(annotation_ids),
            "supporting_point_pair_ids": list(annotation_ids) if _is_handoff_task(str(task_id)) else [],
        },
        "witness_symbolic": {
            "type": (
                "keyed_path_support"
                if str(task_id) == CONDITION_PATH_ENDPOINT_TASK_ID
                else "point_pair_id_set"
                if _is_handoff_task(str(task_id))
                else "bbox_id_set"
            ),
            "ids": list(annotation_ids),
            "keys": list(annotation_keyed_bboxes.keys()),
            "point_pairs": list(annotation_point_pairs),
        },
        "projected_annotation": dict(annotation_projection),
        "background": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
    }

    output = TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=image,
        image_id="img0",
        trace_payload=trace_payload,
        complexity=complexity,
        task_versions=default_task_versions(),
        query_id="default",
    )
    return rewrite_pages_query_output(
        output,
        query_id=str(query["query_id"]),
        scene_id=SCENE_ID,
        query_probabilities=query_probabilities,
    )


@register_task
class PagesProcessFlowFilteredNodeCountTask:
    """Count process-flow nodes selected by lane plus shape, status, or role."""

    task_id = FILTERED_NODE_COUNT_TASK_ID
    domain = "pages"
    task_group = "process_flow"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _build_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


@register_task
class PagesProcessFlowConditionPathEndpointLabelTask:
    """Follow visible decision-arrow labels in a process flow and return the reached step label."""

    task_id = CONDITION_PATH_ENDPOINT_TASK_ID
    domain = "pages"
    task_group = "process_flow"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _build_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


@register_task
class PagesProcessFlowAllCrossLaneHandoffCountTask:
    """Count all cross-lane handoff arrows in a process-flow diagram."""

    task_id = ALL_CROSS_LANE_HANDOFF_COUNT_TASK_ID
    domain = "pages"
    task_group = "process_flow"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _build_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


@register_task
class PagesProcessFlowLaneFilteredHandoffCountTask:
    """Count lane-filtered handoff arrows in a process-flow diagram."""

    task_id = LANE_FILTERED_HANDOFF_COUNT_TASK_ID
    domain = "pages"
    task_group = "process_flow"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _build_output(
            task_id=self.task_id,
            domain=self.domain,
            task_group=self.task_group,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


__all__ = [
    "PagesProcessFlowAllCrossLaneHandoffCountTask",
    "PagesProcessFlowConditionPathEndpointLabelTask",
    "PagesProcessFlowFilteredNodeCountTask",
    "PagesProcessFlowLaneFilteredHandoffCountTask",
]
