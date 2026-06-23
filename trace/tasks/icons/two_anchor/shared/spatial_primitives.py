"""Spatial primitive helpers for two-anchor strip scenes."""

from __future__ import annotations

from typing import Sequence, Tuple


def bbox_center(box: Sequence[int | float]) -> Tuple[float, float]:
    """Return the geometric center of one `xyxy` box."""

    return (0.5 * (float(box[0]) + float(box[2])), 0.5 * (float(box[1]) + float(box[3])))


def center_in_strip(
    *,
    center_xy: Sequence[float],
    anchor_a_center_xy: Sequence[float],
    anchor_b_center_xy: Sequence[float],
    strip_axis: str,
    margin_px: int,
) -> bool:
    """Return whether one candidate center lies safely inside the requested strip."""

    cx, cy = float(center_xy[0]), float(center_xy[1])
    ax, ay = float(anchor_a_center_xy[0]), float(anchor_a_center_xy[1])
    bx, by = float(anchor_b_center_xy[0]), float(anchor_b_center_xy[1])
    margin = float(max(0, int(margin_px)))
    if str(strip_axis) == "vertical":
        left, right = sorted((float(ax), float(bx)))
        return float(left + margin) <= float(cx) <= float(right - margin)
    if str(strip_axis) == "horizontal":
        top, bottom = sorted((float(ay), float(by)))
        return float(top + margin) <= float(cy) <= float(bottom - margin)
    raise ValueError(f"unsupported strip_axis: {strip_axis}")


def center_outside_strip(
    *,
    center_xy: Sequence[float],
    anchor_a_center_xy: Sequence[float],
    anchor_b_center_xy: Sequence[float],
    strip_axis: str,
    margin_px: int,
) -> bool:
    """Return whether one candidate center lies safely outside the requested strip."""

    cx, cy = float(center_xy[0]), float(center_xy[1])
    ax, ay = float(anchor_a_center_xy[0]), float(anchor_a_center_xy[1])
    bx, by = float(anchor_b_center_xy[0]), float(anchor_b_center_xy[1])
    margin = float(max(0, int(margin_px)))
    if str(strip_axis) == "vertical":
        left, right = sorted((float(ax), float(bx)))
        return float(cx) <= float(left - margin) or float(cx) >= float(right + margin)
    if str(strip_axis) == "horizontal":
        top, bottom = sorted((float(ay), float(by)))
        return float(cy) <= float(top - margin) or float(cy) >= float(bottom + margin)
    raise ValueError(f"unsupported strip_axis: {strip_axis}")


def target_region_bbox(
    *,
    content_bbox: Sequence[int | float],
    anchor_a_center_xy: Sequence[float],
    anchor_b_center_xy: Sequence[float],
    strip_axis: str,
    margin_px: int,
    sprite_size: Sequence[int | float],
) -> Tuple[int, int, int, int] | None:
    """Return a content sub-rectangle that guarantees a target center falls in-strip."""

    x0, y0, x1, y1 = [float(value) for value in content_bbox]
    sprite_w, sprite_h = float(sprite_size[0]), float(sprite_size[1])
    half_w = 0.5 * float(sprite_w)
    half_h = 0.5 * float(sprite_h)
    ax, ay = float(anchor_a_center_xy[0]), float(anchor_a_center_xy[1])
    bx, by = float(anchor_b_center_xy[0]), float(anchor_b_center_xy[1])
    margin = float(max(0, int(margin_px)))
    if str(strip_axis) == "vertical":
        left, right = sorted((float(ax), float(bx)))
        region = (
            int(round(max(float(x0), float(left + margin - half_w)))),
            int(round(float(y0))),
            int(round(min(float(x1), float(right - margin + half_w)))),
            int(round(float(y1))),
        )
    elif str(strip_axis) == "horizontal":
        top, bottom = sorted((float(ay), float(by)))
        region = (
            int(round(float(x0))),
            int(round(max(float(y0), float(top + margin - half_h)))),
            int(round(float(x1))),
            int(round(min(float(y1), float(bottom - margin + half_h)))),
        )
    else:
        raise ValueError(f"unsupported strip_axis: {strip_axis}")
    if int(region[2]) - int(region[0]) <= int(sprite_w) or int(region[3]) - int(region[1]) <= int(sprite_h):
        return None
    return tuple(int(value) for value in region)


def sample_anchor_pair_bboxes(
    rng,
    *,
    content_bbox: Sequence[int | float],
    sprite_size: Tuple[int, int],
    strip_axis: str,
    span_ratio_min: float,
    span_ratio_max: float,
    outside_ratio_min: float,
    edge_padding_px: int,
) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
    """Sample one aligned anchor pair whose strip stays well inside the scene."""

    x0, y0, x1, y1 = [int(round(float(value))) for value in content_bbox]
    sprite_w, sprite_h = int(sprite_size[0]), int(sprite_size[1])
    half_w = 0.5 * float(sprite_w)
    half_h = 0.5 * float(sprite_h)
    width = max(1.0, float(x1 - x0))
    height = max(1.0, float(y1 - y0))
    outside_ratio = max(0.0, float(outside_ratio_min))
    edge_padding = max(0, int(edge_padding_px))

    if str(strip_axis) == "vertical":
        span_min = max(float(sprite_w) + 32.0, float(span_ratio_min) * float(width))
        span_max = min(float(span_ratio_max) * float(width), float(width) - 2.0 * float(outside_ratio * width))
        if span_min > span_max:
            raise ValueError("no feasible vertical strip span for aligned anchors")
        span = float(rng.uniform(float(span_min), float(span_max)))
        cx_min = float(x0) + half_w + max(float(edge_padding), float(outside_ratio * width))
        cx_max = float(x1) - half_w - max(float(edge_padding), float(outside_ratio * width)) - float(span)
        if cx_min > cx_max:
            raise ValueError("no feasible vertical anchor centers")
        left_center_x = float(rng.uniform(float(cx_min), float(cx_max)))
        right_center_x = float(left_center_x + span)
        center_y_min = float(y0) + half_h + float(edge_padding)
        center_y_max = float(y1) - half_h - float(edge_padding)
        if center_y_min > center_y_max:
            raise ValueError("no feasible vertical anchor y coordinate")
        center_y = float(rng.uniform(float(center_y_min), float(center_y_max)))
        anchor_a_center = (float(left_center_x), float(center_y))
        anchor_b_center = (float(right_center_x), float(center_y))
    elif str(strip_axis) == "horizontal":
        span_min = max(float(sprite_h) + 32.0, float(span_ratio_min) * float(height))
        span_max = min(float(span_ratio_max) * float(height), float(height) - 2.0 * float(outside_ratio * height))
        if span_min > span_max:
            raise ValueError("no feasible horizontal strip span for aligned anchors")
        span = float(rng.uniform(float(span_min), float(span_max)))
        cy_min = float(y0) + half_h + max(float(edge_padding), float(outside_ratio * height))
        cy_max = float(y1) - half_h - max(float(edge_padding), float(outside_ratio * height)) - float(span)
        if cy_min > cy_max:
            raise ValueError("no feasible horizontal anchor centers")
        top_center_y = float(rng.uniform(float(cy_min), float(cy_max)))
        bottom_center_y = float(top_center_y + span)
        center_x_min = float(x0) + half_w + float(edge_padding)
        center_x_max = float(x1) - half_w - float(edge_padding)
        if center_x_min > center_x_max:
            raise ValueError("no feasible horizontal anchor x coordinate")
        center_x = float(rng.uniform(float(center_x_min), float(center_x_max)))
        anchor_a_center = (float(center_x), float(top_center_y))
        anchor_b_center = (float(center_x), float(bottom_center_y))
    else:
        raise ValueError(f"unsupported strip_axis: {strip_axis}")

    def center_to_bbox(center_xy: Sequence[float]) -> Tuple[int, int, int, int]:
        center_x, center_y = float(center_xy[0]), float(center_xy[1])
        x_min = int(round(float(center_x) - half_w))
        y_min = int(round(float(center_y) - half_h))
        return (int(x_min), int(y_min), int(x_min + sprite_w), int(y_min + sprite_h))

    return center_to_bbox(anchor_a_center), center_to_bbox(anchor_b_center)


__all__ = [
    "bbox_center",
    "center_in_strip",
    "center_outside_strip",
    "sample_anchor_pair_bboxes",
    "target_region_bbox",
]
