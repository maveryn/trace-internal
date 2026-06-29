"""Rendering helpers for voxel-ladder puzzle scenes."""

from __future__ import annotations

from typing import Any, Iterable

from PIL import Image, ImageDraw

from trace.tasks.shared.named_colors import named_color
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import draw_text_centered, load_font

from .rules import checkpoint_item_id
from .state import (
    BBox,
    Color,
    Node,
    RenderParams,
    RenderedVoxelLadder,
    VoxelLadderDataset,
)


def blend(color: Color, target: Color, amount: float) -> Color:
    """Blend an RGB color toward another RGB color."""

    return tuple(
        int(round((float(channel) * (1.0 - amount)) + (float(target_channel) * amount)))
        for channel, target_channel in zip(color, target)
    )


def inflate_bbox(bbox: BBox, pad: float) -> BBox:
    """Pad one bbox in every direction."""

    return (
        float(bbox[0]) - float(pad),
        float(bbox[1]) - float(pad),
        float(bbox[2]) + float(pad),
        float(bbox[3]) + float(pad),
    )


def union_bboxes(bboxes: Iterable[BBox]) -> BBox:
    """Return a bbox containing all input bboxes."""

    items = list(bboxes)
    return (
        min(b[0] for b in items),
        min(b[1] for b in items),
        max(b[2] for b in items),
        max(b[3] for b in items),
    )


def cube_polygons(
    node: Node,
    *,
    origin_x: float,
    origin_y: float,
    params: RenderParams,
) -> tuple[
    list[tuple[float, float]],
    list[tuple[float, float]],
    list[tuple[float, float]],
    BBox,
]:
    """Project one voxel cube to top/left/right isometric polygons."""

    x, y, z = node
    w = float(params.cube_width_px)
    h = float(params.cube_height_px)
    d = float(params.cube_depth_px)
    cx = float(origin_x) + ((float(x) - float(y)) * w * 0.5)
    cy = float(origin_y) + ((float(x) + float(y)) * h * 0.5) - (float(z) * d)
    top = [
        (cx, cy - h * 0.5),
        (cx + w * 0.5, cy),
        (cx, cy + h * 0.5),
        (cx - w * 0.5, cy),
    ]
    left = [
        (cx - w * 0.5, cy),
        (cx, cy + h * 0.5),
        (cx, cy + h * 0.5 + d),
        (cx - w * 0.5, cy + d),
    ]
    right = [
        (cx + w * 0.5, cy),
        (cx, cy + h * 0.5),
        (cx, cy + h * 0.5 + d),
        (cx + w * 0.5, cy + d),
    ]
    points = top + left + right
    bbox = (
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )
    return top, left, right, bbox


def node_top_center(
    node: Node,
    *,
    origin_x: float,
    origin_y: float,
    params: RenderParams,
) -> tuple[float, float]:
    """Return the projected center of one cube top face."""

    x, y, z = node
    return (
        float(origin_x) + ((float(x) - float(y)) * float(params.cube_width_px) * 0.5),
        float(origin_y)
        + ((float(x) + float(y)) * float(params.cube_height_px) * 0.5)
        - (float(z) * float(params.cube_depth_px)),
    )


def cube_colors(
    kind: str,
    params: RenderParams,
    *,
    top_override: Color | None = None,
) -> tuple[Color, Color, Color]:
    """Return top/left/right colors for one cube kind."""

    if kind == "start":
        top = params.start_top_rgb
    elif kind == "goal":
        top = params.goal_top_rgb
    elif kind == "checkpoint":
        top = tuple(int(v) for v in (top_override or params.checkpoint_top_rgb))
    else:
        top = params.neutral_top_rgb
    return top, blend(top, (30, 36, 46), 0.28), blend(top, (30, 36, 46), 0.16)


def render_voxel_ladder_scene(
    background: Image.Image,
    *,
    dataset: VoxelLadderDataset,
    render_params: RenderParams,
) -> RenderedVoxelLadder:
    """Render the voxel-ladder maze and every answerable item bbox."""

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    raw_bboxes = [
        cube_polygons(node, origin_x=0, origin_y=0, params=render_params)[3]
        for node in dataset.cubes
    ]
    raw_bbox = union_bboxes(raw_bboxes)
    board_right = float(render_params.board_left_px + render_params.board_width_px)
    if dataset.option_specs:
        board_right = float(
            render_params.canvas_width - render_params.option_panel_width_px - 44
        )
    board_center_x = float(render_params.board_left_px + board_right) * 0.5
    board_center_y = float(
        render_params.board_top_px + (0.52 * render_params.board_height_px)
    )
    origin_x = board_center_x - ((raw_bbox[0] + raw_bbox[2]) * 0.5)
    origin_y = board_center_y - ((raw_bbox[1] + raw_bbox[3]) * 0.5)
    cube_bboxes = {
        node: cube_polygons(
            node, origin_x=origin_x, origin_y=origin_y, params=render_params
        )[3]
        for node in dataset.cubes
    }
    scene_bbox = inflate_bbox(union_bboxes(cube_bboxes.values()), 24.0)
    floor = [
        (scene_bbox[0] - 18, scene_bbox[3] - 34),
        (scene_bbox[0] + 0.5 * (scene_bbox[2] - scene_bbox[0]), scene_bbox[3] - 110),
        (scene_bbox[2] + 24, scene_bbox[3] - 34),
        (scene_bbox[0] + 0.5 * (scene_bbox[2] - scene_bbox[0]), scene_bbox[3] + 42),
    ]
    draw.polygon(floor, fill=tuple(int(v) for v in render_params.shadow_rgb))

    item_bbox_map: dict[str, BBox] = {}
    entities: list[dict[str, Any]] = []
    checkpoint_by_node = {
        checkpoint.node: checkpoint for checkpoint in dataset.checkpoints
    }
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    small_font = load_font(
        max(13, int(render_params.label_font_size_px * 0.62)), bold=True
    )
    for node in sorted(dataset.cubes, key=lambda n: (n[0] + n[1], n[2], n[0])):
        checkpoint = checkpoint_by_node.get(node)
        kind = "neutral"
        item_id = f"cube_{node[0]}_{node[1]}_{node[2]}"
        label_text = ""
        text_fill = render_params.text_rgb
        if node == dataset.start_node:
            kind = "start"
            item_id = "cube_start"
            label_text = "START"
            text_fill = (255, 255, 255)
        elif node == dataset.goal_node:
            kind = "goal"
            item_id = "cube_goal"
            label_text = "GOAL"
            text_fill = (255, 255, 255)
        elif checkpoint is not None:
            kind = "checkpoint"
            item_id = checkpoint_item_id(checkpoint.color_name)
        top, left, right, bbox = cube_polygons(
            node,
            origin_x=origin_x,
            origin_y=origin_y,
            params=render_params,
        )
        top_color, left_color, right_color = cube_colors(
            kind,
            render_params,
            top_override=checkpoint.color_rgb if checkpoint is not None else None,
        )
        outline = blend(render_params.panel_border_rgb, (0, 0, 0), 0.08)
        draw.polygon(left, fill=left_color, outline=outline)
        draw.polygon(right, fill=right_color, outline=outline)
        draw.polygon(top, fill=top_color, outline=outline)
        cx, cy = node_top_center(
            node, origin_x=origin_x, origin_y=origin_y, params=render_params
        )
        if checkpoint is not None:
            _draw_checkpoint_marker(draw, cx, cy, top_color, render_params)
        item_bbox_map[item_id] = inflate_bbox(bbox, 3.0)
        entities.append(
            {
                "item_id": item_id,
                "entity_type": "voxel_ladder_cube",
                "node": [int(node[0]), int(node[1]), int(node[2])],
                "cube_kind": kind,
                "label": label_text,
                "checkpoint_color_name": (
                    str(checkpoint.color_name) if checkpoint is not None else None
                ),
                "checkpoint_color_rgb": (
                    list(checkpoint.color_rgb) if checkpoint is not None else None
                ),
                "bbox_px": [round(float(v), 3) for v in item_bbox_map[item_id]],
            }
        )
        if label_text:
            font = small_font if label_text in {"START", "GOAL"} else label_font
            draw_text_centered(
                draw,
                text=label_text,
                center=(cx, cy + (0.05 * render_params.cube_height_px)),
                font=font,
                fill=text_fill,
                stroke_fill=(
                    render_params.text_stroke_rgb
                    if text_fill != (255, 255, 255)
                    else (28, 32, 38)
                ),
                stroke_width=2,
            )

    _draw_ladders(
        draw,
        dataset=dataset,
        render_params=render_params,
        origin_x=origin_x,
        origin_y=origin_y,
        item_bbox_map=item_bbox_map,
        entities=entities,
    )
    _draw_option_panel(
        draw,
        dataset=dataset,
        render_params=render_params,
        item_bbox_map=item_bbox_map,
        entities=entities,
    )

    return RenderedVoxelLadder(
        image=image,
        entities=tuple(entities),
        item_bbox_map={
            key: tuple(round(float(v), 3) for v in value)
            for key, value in item_bbox_map.items()
        },
        scene_bbox_px=tuple(round(float(v), 3) for v in scene_bbox),  # type: ignore[arg-type]
    )


def _draw_checkpoint_marker(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    top_color: Color,
    render_params: RenderParams,
) -> None:
    """Draw the ring marker used to distinguish checkpoint cube tops."""

    marker_radius = max(8.0, 0.16 * float(render_params.cube_width_px))
    marker_bbox = (
        cx - marker_radius,
        cy - (0.58 * marker_radius),
        cx + marker_radius,
        cy + (0.58 * marker_radius),
    )
    draw.ellipse(
        marker_bbox,
        outline=(255, 255, 255),
        width=max(3, int(round(0.055 * render_params.cube_width_px))),
    )
    draw.ellipse(
        (
            cx - (0.43 * marker_radius),
            cy - (0.25 * marker_radius),
            cx + (0.43 * marker_radius),
            cy + (0.25 * marker_radius),
        ),
        fill=blend(top_color, (255, 255, 255), 0.18),
        outline=blend(top_color, (0, 0, 0), 0.25),
        width=1,
    )


def _draw_ladders(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: VoxelLadderDataset,
    render_params: RenderParams,
    origin_x: float,
    origin_y: float,
    item_bbox_map: dict[str, BBox],
    entities: list[dict[str, Any]],
) -> None:
    """Draw ladder rails/rungs and record ladder bboxes."""

    ladder_pad = float(max(6, int(0.12 * render_params.cube_width_px)))
    for ladder in dataset.ladders:
        lx, ly = node_top_center(
            ladder.lower, origin_x=origin_x, origin_y=origin_y, params=render_params
        )
        ux, uy = node_top_center(
            ladder.upper, origin_x=origin_x, origin_y=origin_y, params=render_params
        )
        x_offset = 0.20 * float(render_params.cube_width_px)
        p0 = (lx + x_offset, ly + 0.32 * float(render_params.cube_height_px))
        p1 = (ux + x_offset, uy + 0.32 * float(render_params.cube_height_px))
        rail_gap = max(6.0, 0.07 * float(render_params.cube_width_px))
        width = max(3, int(round(0.055 * render_params.cube_width_px)))
        for delta in (-rail_gap, rail_gap):
            draw.line(
                (p0[0] + delta, p0[1], p1[0] + delta, p1[1]),
                fill=render_params.ladder_rgb,
                width=width,
            )
        rung_count = max(
            2,
            int(abs(p0[1] - p1[1]) // max(18, render_params.cube_depth_px * 0.36)),
        )
        for rung_index in range(1, rung_count + 1):
            t = rung_index / float(rung_count + 1)
            ry = p0[1] + ((p1[1] - p0[1]) * t)
            rx = p0[0] + ((p1[0] - p0[0]) * t)
            draw.line(
                (rx - rail_gap, ry, rx + rail_gap, ry),
                fill=render_params.ladder_rgb,
                width=max(2, width - 1),
            )
        bbox = (
            min(p0[0], p1[0]) - ladder_pad,
            min(p0[1], p1[1]) - ladder_pad,
            max(p0[0], p1[0]) + ladder_pad,
            max(p0[1], p1[1]) + ladder_pad,
        )
        item_bbox_map[ladder.ladder_id] = bbox
        entities.append(
            {
                "item_id": ladder.ladder_id,
                "entity_type": "voxel_ladder_ladder",
                "lower_node": [int(v) for v in ladder.lower],
                "upper_node": [int(v) for v in ladder.upper],
                "on_goal_route": bool(ladder.on_goal_route),
                "bbox_px": [round(float(v), 3) for v in bbox],
            }
        )


def _draw_option_panel(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: VoxelLadderDataset,
    render_params: RenderParams,
    item_bbox_map: dict[str, BBox],
    entities: list[dict[str, Any]],
) -> None:
    """Draw route-sequence option cards when a task needs visual options."""

    if not dataset.option_specs:
        return
    panel_x0 = float(
        render_params.canvas_width - render_params.option_panel_width_px - 34
    )
    panel_y0 = 86.0
    panel_x1 = float(render_params.canvas_width - 34)
    panel_y1 = panel_y0 + 30.0 + (float(len(dataset.option_specs)) * 54.0)
    draw.rounded_rectangle(
        (panel_x0, panel_y0, panel_x1, panel_y1),
        radius=18,
        fill=render_params.panel_fill_rgb,
        outline=render_params.panel_border_rgb,
        width=2,
    )
    option_font = load_font(int(render_params.option_font_size_px), bold=True)
    for index, option in enumerate(dataset.option_specs):
        y0 = panel_y0 + 16 + (index * 54)
        card_bbox = (panel_x0 + 18, y0, panel_x1 - 18, y0 + 42)
        draw.rounded_rectangle(
            card_bbox,
            radius=10,
            fill=(255, 255, 255),
            outline=blend(render_params.panel_border_rgb, (255, 255, 255), 0.18),
            width=2,
        )
        draw_text_traced(
            draw,
            (card_bbox[0] + 14, card_bbox[1] + 8),
            f"{option.option_label}.",
            fill=render_params.text_rgb,
            font=option_font,
            role="readout",
            required=False,
        )
        _draw_option_sequence(draw, option.sequence_items, card_bbox, render_params)
        item_bbox_map[f"option_{option.option_label}"] = card_bbox
        entities.append(
            {
                "item_id": f"option_{option.option_label}",
                "entity_type": "voxel_ladder_route_option",
                "option_label": str(option.option_label),
                "sequence_text": str(option.sequence_text),
                "sequence_items": list(option.sequence_items),
                "sequence_rgb": [
                    list(named_color(str(color_name)))
                    for color_name in option.sequence_items
                ],
                "is_correct": bool(option.is_correct),
                "bbox_px": [round(float(v), 3) for v in card_bbox],
            }
        )


def _draw_option_sequence(
    draw: ImageDraw.ImageDraw,
    sequence_items: tuple[str, ...],
    card_bbox: BBox,
    render_params: RenderParams,
) -> None:
    """Draw colored dots and arrows inside one route option card."""

    dot_radius = 10.0
    dot_step = 34.0
    dot_x = float(card_bbox[0] + 60)
    dot_y = float(card_bbox[1] + 21)
    for item_index, color_name in enumerate(sequence_items):
        center_x = dot_x + (float(item_index) * dot_step)
        color_rgb = tuple(int(v) for v in named_color(str(color_name)))
        draw.ellipse(
            (
                center_x - dot_radius,
                dot_y - dot_radius,
                center_x + dot_radius,
                dot_y + dot_radius,
            ),
            fill=color_rgb,
            outline=blend(color_rgb, (0, 0, 0), 0.35),
            width=2,
        )
        if item_index < len(sequence_items) - 1:
            x0 = center_x + dot_radius + 4
            x1 = center_x + dot_step - dot_radius - 4
            draw.line((x0, dot_y, x1, dot_y), fill=render_params.text_rgb, width=2)
            draw.polygon(
                [(x1, dot_y), (x1 - 5, dot_y - 4), (x1 - 5, dot_y + 4)],
                fill=render_params.text_rgb,
            )
