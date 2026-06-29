"""Shared rendering helpers for topology string-component puzzle scenes."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.shared.bbox_projection import round_bbox as _round_bbox

from .sampling import PuzzleStringTopologyRenderParams


@dataclass(frozen=True)
class RenderedStringTopologyScene:
    """Rendered topology string scene plus traced geometry."""

    image: Image.Image
    scene_bbox_px: List[float]
    visual_group_bbox_map: Dict[str, List[float]]
    component_bbox_map: Dict[str, List[float]]
    linked_pair_bbox_map: Dict[str, List[float]]
    crossing_bbox_map: Dict[str, List[float]]
    entities: List[Dict[str, Any]]


def _expand_bbox(bbox: Sequence[float], amount: float) -> List[float]:
    """Expand one bbox by a fixed pixel amount."""

    left, top, right, bottom = [float(value) for value in bbox]
    return _round_bbox([left - float(amount), top - float(amount), right + float(amount), bottom + float(amount)])


def _union_bbox(bboxes: Sequence[Sequence[float]], padding: float = 0.0) -> List[float]:
    """Return the union of one or more bboxes."""

    if not bboxes:
        return [0.0, 0.0, 0.0, 0.0]
    left = min(float(bbox[0]) for bbox in bboxes)
    top = min(float(bbox[1]) for bbox in bboxes)
    right = max(float(bbox[2]) for bbox in bboxes)
    bottom = max(float(bbox[3]) for bbox in bboxes)
    return _round_bbox([left - float(padding), top - float(padding), right + float(padding), bottom + float(padding)])


def _line(draw: ImageDraw.ImageDraw, points: Sequence[Tuple[float, float]], *, fill: Sequence[int], width: int) -> None:
    """Draw one rounded-enough polyline for rope paths."""

    if len(points) < 2:
        return
    draw.line([(float(x), float(y)) for x, y in points], fill=tuple(int(v) for v in fill), width=int(width), joint="curve")


def _open_string_points(bbox: Sequence[float], *, phase: float = 0.35) -> List[Tuple[float, float]]:
    """Return a deterministic wavy open-rope path inside one bbox."""

    left, top, right, bottom = [float(value) for value in bbox]
    mid_y = (top + bottom) * 0.5
    amp = (bottom - top) * 0.18
    points: List[Tuple[float, float]] = []
    for step in range(64):
        t = float(step) / 63.0
        x = left + (right - left) * t
        y = mid_y + amp * math.sin((2.0 * math.pi * t) + phase) + (amp * 0.45 * math.sin(5.0 * math.pi * t))
        points.append((x, y))
    return points


def _cubic_bezier_points(
    p0: Tuple[float, float],
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    *,
    steps: int = 96,
) -> List[Tuple[float, float]]:
    """Sample one cubic Bezier curve."""

    points: List[Tuple[float, float]] = []
    for step in range(int(steps)):
        t = float(step) / float(int(steps) - 1)
        inv = 1.0 - t
        x = (
            (inv ** 3) * float(p0[0])
            + (3.0 * (inv ** 2) * t * float(p1[0]))
            + (3.0 * inv * (t ** 2) * float(p2[0]))
            + ((t ** 3) * float(p3[0]))
        )
        y = (
            (inv ** 3) * float(p0[1])
            + (3.0 * (inv ** 2) * t * float(p1[1]))
            + (3.0 * inv * (t ** 2) * float(p2[1]))
            + ((t ** 3) * float(p3[1]))
        )
        points.append((x, y))
    return points


def _tangled_rope_points(bbox: Sequence[float], *, rope_index: int, rope_count: int) -> List[Tuple[float, float]]:
    """Return one crossing-rich open rope path inside a shared bundle bbox."""

    left, top, right, bottom = [float(value) for value in bbox]
    width = right - left
    height = bottom - top
    count = max(1, int(rope_count))
    slot = (float(rope_index) + 0.5) / float(count)
    mirror_slot = 1.0 - slot
    pattern = int(rope_index) % 4

    if pattern == 0:
        p0 = (left, top + height * (0.15 + 0.70 * slot))
        p3 = (right, top + height * (0.15 + 0.70 * mirror_slot))
        p1 = (left + width * 0.30, top + height * (0.88 - 0.35 * slot))
        p2 = (left + width * 0.70, top + height * (0.12 + 0.35 * slot))
    elif pattern == 1:
        p0 = (left + width * (0.12 + 0.76 * slot), top)
        p3 = (left + width * (0.12 + 0.76 * mirror_slot), bottom)
        p1 = (left + width * (0.82 - 0.28 * slot), top + height * 0.34)
        p2 = (left + width * (0.18 + 0.28 * slot), top + height * 0.66)
    elif pattern == 2:
        p0 = (left, top + height * (0.82 - 0.58 * slot))
        p3 = (right, top + height * (0.20 + 0.58 * slot))
        p1 = (left + width * 0.42, top + height * (0.12 + 0.55 * mirror_slot))
        p2 = (left + width * 0.58, top + height * (0.88 - 0.55 * mirror_slot))
    else:
        p0 = (left + width * (0.15 + 0.70 * slot), bottom)
        p3 = (left + width * (0.85 - 0.70 * slot), top)
        p1 = (left + width * (0.20 + 0.35 * mirror_slot), top + height * 0.62)
        p2 = (left + width * (0.80 - 0.35 * mirror_slot), top + height * 0.38)

    points = _cubic_bezier_points(p0, p1, p2, p3, steps=104)
    wiggle_amp = height * 0.018
    return [
        (
            float(x),
            float(y) + wiggle_amp * math.sin((float(step) / 103.0) * math.pi * 6.0 + float(rope_index)),
        )
        for step, (x, y) in enumerate(points)
    ]


def _draw_endpoints(
    draw: ImageDraw.ImageDraw,
    points: Sequence[Tuple[float, float]],
    *,
    color: Sequence[int],
    render_params: PuzzleStringTopologyRenderParams,
) -> None:
    """Draw visible rope endpoints."""

    radius = float(render_params.endpoint_radius_px)
    for center in (points[0], points[-1]):
        cx, cy = center
        draw.ellipse(
            [cx - radius, cy - radius, cx + radius, cy + radius],
            fill=tuple(int(v) for v in color),
            outline=tuple(int(v) for v in render_params.rope_shadow_rgb),
            width=2,
        )


def _draw_open_string(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    *,
    color: Sequence[int],
    render_params: PuzzleStringTopologyRenderParams,
) -> List[float]:
    """Draw one open string with two visible endpoints."""

    width = int(render_params.rope_stroke_width_px)
    points = _open_string_points(bbox)
    _line(draw, points, fill=render_params.rope_shadow_rgb, width=width + 4)
    _line(draw, points, fill=color, width=width)
    _draw_endpoints(draw, points, color=color, render_params=render_params)
    return _expand_bbox(bbox, amount=0.5 * width)


def _draw_closed_ring(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    *,
    color: Sequence[int],
    render_params: PuzzleStringTopologyRenderParams,
) -> List[float]:
    """Draw one closed ring."""

    width = int(render_params.rope_stroke_width_px)
    draw.ellipse(
        [float(v) for v in bbox],
        outline=tuple(int(v) for v in render_params.rope_shadow_rgb),
        width=width + 4,
    )
    draw.ellipse(
        [float(v) for v in bbox],
        outline=tuple(int(v) for v in color),
        width=width,
    )
    return _expand_bbox(bbox, amount=0.5 * width)


def _draw_knot_mark(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    color: Sequence[int],
    render_params: PuzzleStringTopologyRenderParams,
    scale: float = 1.0,
) -> List[float]:
    """Draw one visible over-under knot marker and return its bbox."""

    cx, cy = [float(value) for value in center]
    width = int(render_params.rope_stroke_width_px)
    gap = float(width + 6) * float(scale)
    radius_x = gap * 0.95
    radius_y = gap * 0.68
    draw.ellipse(
        [cx - radius_x, cy - radius_y, cx + radius_x, cy + radius_y],
        outline=tuple(int(v) for v in render_params.rope_shadow_rgb),
        width=max(2, width - 2),
    )
    draw.ellipse(
        [cx - radius_x, cy - radius_y, cx + radius_x, cy + radius_y],
        outline=tuple(int(v) for v in color),
        width=max(2, width - 4),
    )
    draw.line(
        [(cx - gap, cy), (cx + gap, cy)],
        fill=tuple(int(v) for v in render_params.gap_fill_rgb),
        width=width + 6,
    )
    draw.line(
        [(cx - gap * 0.72, cy - gap * 0.45), (cx + gap * 0.72, cy + gap * 0.45)],
        fill=tuple(int(v) for v in color),
        width=width,
    )
    return _round_bbox([cx - gap * 1.25, cy - gap * 1.05, cx + gap * 1.25, cy + gap * 1.05])


def _draw_knotted_loop(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    *,
    color: Sequence[int],
    render_params: PuzzleStringTopologyRenderParams,
) -> tuple[List[float], List[float]]:
    """Draw one closed loop with a visible self-crossing."""

    left, top, right, bottom = [float(value) for value in bbox]
    cx = (left + right) * 0.5
    cy = (top + bottom) * 0.5
    rx = (right - left) * 0.34
    ry = (bottom - top) * 0.30
    points: List[Tuple[float, float]] = []
    for step in range(121):
        t = (2.0 * math.pi * float(step)) / 120.0
        x = cx + rx * math.sin(t)
        y = cy + ry * math.sin(2.0 * t)
        points.append((x, y))
    width = int(render_params.rope_stroke_width_px)
    _line(draw, points, fill=render_params.rope_shadow_rgb, width=width + 4)
    _line(draw, points, fill=color, width=width)
    crossing_bbox = _draw_knot_mark(
        draw,
        center=(cx, cy),
        color=color,
        render_params=render_params,
        scale=0.95,
    )
    component_bbox = _expand_bbox([cx - rx, cy - ry, cx + rx, cy + ry], amount=0.5 * width)
    return component_bbox, crossing_bbox


def _draw_tangled_rope_bundle(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    *,
    components: Sequence[Mapping[str, Any]],
    render_params: PuzzleStringTopologyRenderParams,
) -> Dict[str, List[float]]:
    """Draw several separate ropes inside one tangled bundle."""

    width = int(render_params.rope_stroke_width_px)
    paths_by_id: Dict[str, List[Tuple[float, float]]] = {}
    component_bbox_map: Dict[str, List[float]] = {}
    count = len(components)
    for rope_index, component in enumerate(components):
        component_id = str(component["component_id"])
        paths_by_id[component_id] = _tangled_rope_points(
            bbox,
            rope_index=int(rope_index),
            rope_count=int(count),
        )

    for points in paths_by_id.values():
        _line(draw, points, fill=render_params.rope_shadow_rgb, width=width + 5)
    for component in components:
        component_id = str(component["component_id"])
        points = paths_by_id[component_id]
        color = component["color_rgb"]
        _line(draw, points, fill=color, width=width)
        _draw_endpoints(draw, points, color=color, render_params=render_params)
        point_bbox = _union_bbox(
            [[float(x), float(y), float(x), float(y)] for x, y in points],
            padding=(0.5 * float(width)) + float(render_params.endpoint_radius_px),
        )
        component_bbox_map[component_id] = list(point_bbox)
    return component_bbox_map


def _draw_linked_pair(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    *,
    left_color: Sequence[int],
    right_color: Sequence[int],
    render_params: PuzzleStringTopologyRenderParams,
) -> tuple[List[float], List[float], List[float], List[List[float]]]:
    """Draw two linked rings and return pair/component/crossing bboxes."""

    left, top, right, bottom = [float(value) for value in bbox]
    width = int(render_params.rope_stroke_width_px)
    ring_w = (right - left) * 0.52
    ring_h = (bottom - top) * 0.68
    center_y = (top + bottom) * 0.5
    left_cx = left + (right - left) * 0.39
    right_cx = left + (right - left) * 0.61
    left_ring = [left_cx - ring_w * 0.5, center_y - ring_h * 0.5, left_cx + ring_w * 0.5, center_y + ring_h * 0.5]
    right_ring = [right_cx - ring_w * 0.5, center_y - ring_h * 0.5, right_cx + ring_w * 0.5, center_y + ring_h * 0.5]

    _draw_closed_ring(draw, left_ring, color=left_color, render_params=render_params)
    _draw_closed_ring(draw, right_ring, color=right_color, render_params=render_params)

    cross_x = (left_cx + right_cx) * 0.5
    cross_top_y = center_y - ring_h * 0.27
    cross_bottom_y = center_y + ring_h * 0.27
    gap = float(width + 8)
    for cx, cy, color in (
        (cross_x, cross_top_y, left_color),
        (cross_x, cross_bottom_y, right_color),
    ):
        draw.ellipse(
            [cx - gap, cy - gap, cx + gap, cy + gap],
            fill=tuple(int(v) for v in render_params.gap_fill_rgb),
        )
        draw.line(
            [(cx - gap * 0.55, cy - gap * 0.55), (cx + gap * 0.55, cy + gap * 0.55)],
            fill=tuple(int(v) for v in color),
            width=width,
        )

    left_component_bbox = _expand_bbox(left_ring, amount=0.5 * width)
    right_component_bbox = _expand_bbox(right_ring, amount=0.5 * width)
    pair_bbox = _union_bbox([left_component_bbox, right_component_bbox], padding=4.0)
    crossing_bboxes = [
        _round_bbox([cross_x - gap, cross_top_y - gap, cross_x + gap, cross_top_y + gap]),
        _round_bbox([cross_x - gap, cross_bottom_y - gap, cross_x + gap, cross_bottom_y + gap]),
    ]
    return pair_bbox, left_component_bbox, right_component_bbox, crossing_bboxes


def _overlaps_with_gap(candidate: Sequence[float], existing: Sequence[float], gap: float) -> bool:
    """Return true if candidate violates the configured rectangle gap."""

    left, top, right, bottom = [float(value) for value in candidate]
    other_left, other_top, other_right, other_bottom = [float(value) for value in existing]
    return not (
        right + float(gap) <= other_left
        or other_right + float(gap) <= left
        or bottom + float(gap) <= other_top
        or other_bottom + float(gap) <= top
    )


def _group_size(
    group: Mapping[str, Any],
    *,
    rng,
    render_params: PuzzleStringTopologyRenderParams,
) -> tuple[float, float]:
    """Sample a deterministic group bbox size for one visual group."""

    group_type = str(group["group_type"])
    if group_type == "linked_pair":
        width_min = int(render_params.linked_pair_width_min_px)
        width_max = int(render_params.linked_pair_width_max_px)
    elif group_type == "tangled_rope_bundle":
        width_min = int(render_params.tangled_bundle_width_min_px)
        width_max = int(render_params.tangled_bundle_width_max_px)
        height_min = int(render_params.tangled_bundle_height_min_px)
        height_max = int(render_params.tangled_bundle_height_max_px)
        return float(rng.randint(width_min, width_max)), float(rng.randint(height_min, height_max))
    else:
        width_min = int(render_params.group_width_min_px)
        width_max = int(render_params.group_width_max_px)
    height_min = int(render_params.group_height_min_px)
    height_max = int(render_params.group_height_max_px)
    return float(rng.randint(width_min, width_max)), float(rng.randint(height_min, height_max))


def _fallback_group_bboxes(
    visual_group_specs: Sequence[Mapping[str, Any]],
    *,
    render_params: PuzzleStringTopologyRenderParams,
    rng,
) -> List[List[float]]:
    """Build a non-overlapping jittered grid fallback when rejection placement is full."""

    count = len(visual_group_specs)
    canvas_width = float(render_params.canvas_width)
    canvas_height = float(render_params.canvas_height)
    left_margin = float(render_params.scene_margin_left_px)
    right_margin = float(render_params.scene_margin_right_px)
    top_margin = float(render_params.scene_margin_top_px)
    bottom_margin = float(render_params.scene_margin_bottom_px)
    interior_w = canvas_width - left_margin - right_margin
    interior_h = canvas_height - top_margin - bottom_margin
    cols = max(1, int(math.ceil(math.sqrt(float(count) * interior_w / max(1.0, interior_h)))))
    rows = max(1, int(math.ceil(float(count) / float(cols))))
    cell_w = interior_w / float(cols)
    cell_h = interior_h / float(rows)
    gap = float(render_params.group_min_gap_px)
    bboxes: List[List[float]] = []
    for index, group in enumerate(visual_group_specs):
        row = int(index) // int(cols)
        col = int(index) % int(cols)
        desired_w, desired_h = _group_size(group, rng=rng, render_params=render_params)
        width = min(float(desired_w), max(80.0, cell_w - gap))
        height = min(float(desired_h), max(70.0, cell_h - gap))
        cell_left = left_margin + (float(col) * cell_w)
        cell_top = top_margin + (float(row) * cell_h)
        slack_x = max(0.0, cell_w - width - gap)
        slack_y = max(0.0, cell_h - height - gap)
        x1 = cell_left + (gap * 0.5) + (rng.random() * slack_x)
        y1 = cell_top + (gap * 0.5) + (rng.random() * slack_y)
        bboxes.append(_round_bbox([x1, y1, x1 + width, y1 + height]))
    return bboxes


def _layout_group_bboxes(
    visual_group_specs: Sequence[Mapping[str, Any]],
    *,
    render_params: PuzzleStringTopologyRenderParams,
    instance_seed: int,
) -> tuple[List[float], List[List[float]]]:
    """Return scene bbox and random non-overlapping visual group bboxes."""

    rng = spawn_rng(int(instance_seed), "puzzle_string_topology.open_canvas_layout")
    canvas_width = float(render_params.canvas_width)
    canvas_height = float(render_params.canvas_height)
    left_margin = float(render_params.scene_margin_left_px)
    right_margin = float(render_params.scene_margin_right_px)
    top_margin = float(render_params.scene_margin_top_px)
    bottom_margin = float(render_params.scene_margin_bottom_px)
    gap = float(render_params.group_min_gap_px)
    bboxes: List[List[float]] = []

    if (
        len(visual_group_specs) == 1
        and str(visual_group_specs[0].get("group_type")) == "tangled_rope_bundle"
    ):
        width, height = _group_size(visual_group_specs[0], rng=rng, render_params=render_params)
        interior_w = canvas_width - left_margin - right_margin
        interior_h = canvas_height - top_margin - bottom_margin
        centered_x = left_margin + ((interior_w - width) * 0.5)
        centered_y = top_margin + ((interior_h - height) * 0.5)
        jitter_x = (rng.random() - 0.5) * min(120.0, max(0.0, interior_w - width))
        jitter_y = (rng.random() - 0.5) * min(120.0, max(0.0, interior_h - height))
        x1 = min(max(left_margin, centered_x + jitter_x), canvas_width - right_margin - width)
        y1 = min(max(top_margin, centered_y + jitter_y), canvas_height - bottom_margin - height)
        single_bbox = _round_bbox([x1, y1, x1 + width, y1 + height])
        scene_bbox = _union_bbox([single_bbox], padding=18.0)
        return scene_bbox, [single_bbox]

    sorted_groups = sorted(
        enumerate(visual_group_specs),
        key=lambda item: 0 if str(item[1]["group_type"]) == "tangled_rope_bundle" else 1,
    )
    pending_by_index: Dict[int, List[float]] = {}
    for original_index, group in sorted_groups:
        placed = False
        for _ in range(int(render_params.placement_attempts)):
            width, height = _group_size(group, rng=rng, render_params=render_params)
            max_x = max(left_margin, canvas_width - right_margin - width)
            max_y = max(top_margin, canvas_height - bottom_margin - height)
            x1 = rng.uniform(left_margin, max_x)
            y1 = rng.uniform(top_margin, max_y)
            candidate = _round_bbox([x1, y1, x1 + width, y1 + height])
            if any(_overlaps_with_gap(candidate, bbox, gap) for bbox in pending_by_index.values()):
                continue
            pending_by_index[int(original_index)] = candidate
            placed = True
            break
        if not placed:
            fallback = _fallback_group_bboxes(visual_group_specs, render_params=render_params, rng=rng)
            scene_bbox = _union_bbox(fallback, padding=18.0)
            return scene_bbox, fallback

    bboxes = [pending_by_index[index] for index in range(len(visual_group_specs))]
    scene_bbox = _union_bbox(bboxes, padding=18.0)
    return scene_bbox, bboxes


def render_puzzle_string_topology_scene(
    image: Image.Image,
    *,
    scene_variant: str,
    component_specs: Sequence[Mapping[str, Any]],
    visual_group_specs: Sequence[Mapping[str, Any]],
    crossing_specs: Sequence[Mapping[str, Any]],
    render_params: PuzzleStringTopologyRenderParams,
    instance_seed: int,
) -> RenderedStringTopologyScene:
    """Render the complete string-topology scene and collect geometry metadata."""

    selected_variant = str(scene_variant)
    if selected_variant not in {"string_strip", "string_card", "string_outline"}:
        raise ValueError(f"unsupported topology string scene_variant: {scene_variant}")

    draw = ImageDraw.Draw(image)
    entities: List[Dict[str, Any]] = []
    component_by_id = {str(component["component_id"]): dict(component) for component in component_specs}
    link_crossings_by_pair: Dict[str, List[Mapping[str, Any]]] = {}
    self_crossings_by_component: Dict[str, List[Mapping[str, Any]]] = {}
    for crossing in crossing_specs:
        crossing_type = str(crossing["crossing_type"])
        if crossing_type == "inter_component_link":
            link_crossings_by_pair.setdefault(str(crossing["linked_pair_id"]), []).append(crossing)
        elif crossing_type == "self_knot":
            component_ids = [str(value) for value in crossing.get("component_ids", [])]
            if component_ids:
                self_crossings_by_component.setdefault(component_ids[0], []).append(crossing)

    scene_bbox, group_bboxes = _layout_group_bboxes(
        visual_group_specs,
        render_params=render_params,
        instance_seed=int(instance_seed),
    )
    entities.append(
        {
            "entity_id": "string_topology_scene_panel",
            "entity_type": "puzzle_topology_string_scene_panel",
            "bbox_px": list(scene_bbox),
            "attributes": {
                "scene_variant": str(selected_variant),
                "layout": "random_open_canvas",
                "minimum_group_gap_px": int(render_params.group_min_gap_px),
            },
        }
    )

    visual_group_bbox_map: Dict[str, List[float]] = {}
    component_bbox_map: Dict[str, List[float]] = {}
    linked_pair_bbox_map: Dict[str, List[float]] = {}
    crossing_bbox_map: Dict[str, List[float]] = {}
    crossing_fallback_cursor = 0
    for group, group_bbox in zip(visual_group_specs, group_bboxes, strict=True):
        group_id = str(group["visual_group_id"])
        visual_group_bbox_map[group_id] = list(group_bbox)
        entities.append(
            {
                "entity_id": str(group_id),
                "entity_type": "puzzle_topology_string_visual_group",
                "bbox_px": list(group_bbox),
                "attributes": {
                    "group_type": str(group["group_type"]),
                    "component_ids": [str(value) for value in group["component_ids"]],
                    "linked_pair_id": group.get("linked_pair_id"),
                    "knot_count": int(group.get("knot_count", 0)),
                },
            }
        )

        pad = float(render_params.component_padding_px)
        inner = _round_bbox([group_bbox[0] + pad, group_bbox[1] + pad, group_bbox[2] - pad, group_bbox[3] - pad])
        if str(group["group_type"]) == "linked_pair":
            left_id, right_id = [str(value) for value in group["component_ids"]]
            left_component = component_by_id[left_id]
            right_component = component_by_id[right_id]
            pair_bbox, left_bbox, right_bbox, crossing_bboxes = _draw_linked_pair(
                draw,
                inner,
                left_color=left_component["color_rgb"],
                right_color=right_component["color_rgb"],
                render_params=render_params,
            )
            pair_id = str(group["linked_pair_id"])
            linked_pair_bbox_map[pair_id] = list(pair_bbox)
            component_bbox_map[left_id] = list(left_bbox)
            component_bbox_map[right_id] = list(right_bbox)
            entities.append(
                {
                    "entity_id": str(pair_id),
                    "entity_type": "puzzle_topology_string_linked_pair",
                    "bbox_px": list(pair_bbox),
                    "attributes": {"component_ids": [left_id, right_id]},
                }
            )
            for component_id, component_bbox, component in (
                (left_id, left_bbox, left_component),
                (right_id, right_bbox, right_component),
            ):
                entities.append(
                    {
                        "entity_id": str(component_id),
                        "entity_type": "puzzle_topology_string_component",
                        "bbox_px": list(component_bbox),
                        "attributes": {
                            "component_type": str(component["component_type"]),
                            "closed": bool(component["closed"]),
                            "open_ended": bool(component.get("open_ended")),
                            "knotted": bool(component["knotted"]),
                            "knot_count": int(component.get("knot_count", 0)),
                            "linked_pair_id": str(pair_id),
                            "pair_side": str(component.get("pair_side")),
                        },
                    }
                )
            expected_crossings = list(link_crossings_by_pair.get(str(pair_id), []))
            for crossing_index, crossing_bbox in enumerate(crossing_bboxes):
                crossing_fallback_cursor += 1
                crossing = dict(expected_crossings[crossing_index]) if crossing_index < len(expected_crossings) else {}
                crossing_id = str(crossing.get("crossing_id", f"crossing_{int(crossing_fallback_cursor)}"))
                crossing_bbox_map[crossing_id] = list(crossing_bbox)
                entities.append(
                    {
                        "entity_id": str(crossing_id),
                        "entity_type": "puzzle_topology_string_crossing",
                        "bbox_px": list(crossing_bbox),
                        "attributes": {
                            "crossing_type": "inter_component_link",
                            "linked_pair_id": str(pair_id),
                            "component_ids": [left_id, right_id],
                            "over_component_id": crossing.get("over_component_id"),
                        },
                    }
                )
            continue

        if str(group["group_type"]) == "tangled_rope_bundle":
            bundle_components = [component_by_id[str(component_id)] for component_id in group["component_ids"]]
            bundle_component_bboxes = _draw_tangled_rope_bundle(
                draw,
                inner,
                components=bundle_components,
                render_params=render_params,
            )
            for component in bundle_components:
                component_id = str(component["component_id"])
                component_bbox = list(bundle_component_bboxes[component_id])
                component_bbox_map[component_id] = list(component_bbox)
                entities.append(
                    {
                        "entity_id": str(component_id),
                        "entity_type": "puzzle_topology_string_component",
                        "bbox_px": list(component_bbox),
                        "attributes": {
                            "component_type": str(component["component_type"]),
                            "closed": bool(component["closed"]),
                            "open_ended": bool(component.get("open_ended")),
                            "knotted": bool(component["knotted"]),
                            "knot_count": int(component.get("knot_count", 0)),
                            "linked_pair_id": component.get("linked_pair_id"),
                        },
                    }
                )
            continue

        component_id = str(group["component_ids"][0])
        component = component_by_id[component_id]
        component_type = str(component["component_type"])
        if component_type == "open_string":
            component_bbox = _draw_open_string(
                draw,
                inner,
                color=component["color_rgb"],
                render_params=render_params,
            )
        elif component_type == "knotted_loop":
            component_bbox, crossing_bbox = _draw_knotted_loop(
                draw,
                inner,
                color=component["color_rgb"],
                render_params=render_params,
            )
            crossing_fallback_cursor += 1
            expected_crossings = list(self_crossings_by_component.get(str(component_id), []))
            crossing = dict(expected_crossings[0]) if expected_crossings else {}
            crossing_id = str(crossing.get("crossing_id", f"crossing_{int(crossing_fallback_cursor)}"))
            crossing_bbox_map[crossing_id] = list(crossing_bbox)
            entities.append(
                {
                    "entity_id": str(crossing_id),
                    "entity_type": "puzzle_topology_string_crossing",
                    "bbox_px": list(crossing_bbox),
                    "attributes": {
                        "crossing_type": "self_knot",
                        "component_ids": [str(component_id)],
                        "over_component_id": crossing.get("over_component_id", str(component_id)),
                        "knot_index": int(crossing.get("knot_index", 1)),
                    },
                }
            )
        else:
            ring_bbox = _round_bbox([
                inner[0] + 14.0,
                inner[1] + 6.0,
                inner[2] - 14.0,
                inner[3] - 6.0,
            ])
            component_bbox = _draw_closed_ring(
                draw,
                ring_bbox,
                color=component["color_rgb"],
                render_params=render_params,
            )
        component_bbox_map[component_id] = list(component_bbox)
        entities.append(
            {
                "entity_id": str(component_id),
                "entity_type": "puzzle_topology_string_component",
                "bbox_px": list(component_bbox),
                "attributes": {
                    "component_type": str(component_type),
                    "closed": bool(component["closed"]),
                    "open_ended": bool(component.get("open_ended")),
                    "knotted": bool(component["knotted"]),
                    "knot_count": int(component.get("knot_count", 0)),
                    "linked_pair_id": component.get("linked_pair_id"),
                },
            }
        )

    return RenderedStringTopologyScene(
        image=image,
        scene_bbox_px=list(scene_bbox),
        visual_group_bbox_map={str(key): list(value) for key, value in visual_group_bbox_map.items()},
        component_bbox_map={str(key): list(value) for key, value in component_bbox_map.items()},
        linked_pair_bbox_map={str(key): list(value) for key, value in linked_pair_bbox_map.items()},
        crossing_bbox_map={str(key): list(value) for key, value in crossing_bbox_map.items()},
        entities=entities,
    )


__all__ = ["RenderedStringTopologyScene", "render_puzzle_string_topology_scene"]
