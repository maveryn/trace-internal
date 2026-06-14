"""Spatial placement and rendering primitives for named-field icon scenes."""

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw

from ...shared.icon_noise import serialize_icon_noise_edits
from ...shared.icon_scene import BBox, draw_single_panel, resolve_single_panel_layout, single_panel_geometry_to_trace
from ...shared.procedural_named_icon_field_scene import (
    bbox_center_float,
    bbox_from_center_and_size,
    bbox_from_center_dimensions,
    bbox_inside,
    boxes_overlap,
    label_bbox_for_icon,
    render_planned_named_icon_sprite,
    union_bbox,
)
from ...shared.procedural_named_icons import procedural_named_icon_display_name
from ....shared.text_rendering import draw_text_centered, load_font

from .metrics import trace_key
from .state import (
    CloserReferenceRenderedIcon,
    CloserReferenceSampleSpec,
    CloserReferenceScenePayload,
    DistanceRankIconPlan,
    DistanceRankRenderedIcon,
    DistanceRankScenePayload,
    RegionSpec,
    RenderedRegionIcon,
)


def _axis_radius(center: Tuple[float, float], axis: Tuple[float, float], content_bbox: BBox) -> float:
    cx, cy = float(center[0]), float(center[1])
    dx, dy = float(axis[0]), float(axis[1])
    x0, y0, x1, y1 = tuple(float(value) for value in content_bbox)

    def forward_limit(sign: float) -> float:
        limits = []
        if abs(dx) > 1e-9:
            limits.append(((x1 if sign * dx > 0 else x0) - cx) / (sign * dx))
        if abs(dy) > 1e-9:
            limits.append(((y1 if sign * dy > 0 else y0) - cy) / (sign * dy))
        positives = [float(value) for value in limits if float(value) > 0.0]
        return min(positives) if positives else 0.0

    return float(min(forward_limit(1.0), forward_limit(-1.0)))


def serialize_closer_reference_icon(icon: CloserReferenceRenderedIcon) -> Dict[str, Any]:
    """Serialize one closer-reference icon for trace payloads."""

    return {
        "entity_kind": "procedural_named_icon",
        "instance_id": str(icon.instance_id),
        "role": str(icon.role),
        "label": str(icon.label),
        "shape_id": str(icon.shape_id),
        "shape_name": str(icon.shape_name),
        "color_name": str(icon.color_name),
        "tint_rgb": [int(value) for value in icon.tint_rgb],
        "fill_style": str(icon.fill_style),
        "bbox_xyxy": [int(value) for value in icon.bbox_xyxy],
        "center_xy": [float(icon.center_xy[0]), float(icon.center_xy[1])],
        "nominal_size_px": int(icon.nominal_size_px),
        "rotation_degrees": int(icon.rotation_degrees),
        "distance_to_reference_a_px": None if icon.distance_to_reference_a_px is None else float(icon.distance_to_reference_a_px),
        "distance_to_reference_b_px": None if icon.distance_to_reference_b_px is None else float(icon.distance_to_reference_b_px),
        "closer_reference_label": str(icon.closer_reference_label),
        "counted": bool(icon.counted),
        "label_bbox_xyxy": None if icon.label_bbox_xyxy is None else [int(value) for value in icon.label_bbox_xyxy],
        "noise_edits": [dict(edit) for edit in icon.noise_edits],
        "noise_seed": None if icon.noise_seed is None else int(icon.noise_seed),
    }


def render_closer_reference_scene(
    *,
    rng,
    sample: CloserReferenceSampleSpec,
    render_params: Mapping[str, Any],
) -> CloserReferenceScenePayload:
    """Render named-field references and targets while preserving distance margins."""

    layout = resolve_single_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    content_bbox = tuple(int(value) for value in layout.scene_content_xyxy)
    plans = tuple(sample.plans)
    sprites = [render_planned_named_icon_sprite(plan) for plan in plans]
    axes = tuple(int(value) for value in sample.reference_axis_probabilities)
    axis_degrees = int(rng.choice(axes)) if axes else 0
    if any(abs(float(value) - 1.0) < 1e-9 for value in sample.reference_axis_probabilities.values()):
        axis_degrees = int(next(int(key) for key, value in sample.reference_axis_probabilities.items() if abs(float(value) - 1.0) < 1e-9))

    angle = math.radians(float(axis_degrees))
    axis = (float(math.cos(angle)), float(math.sin(angle)))
    perp = (-float(axis[1]), float(axis[0]))
    center = (
        0.5 * float(content_bbox[0] + content_bbox[2]),
        0.5 * float(content_bbox[1] + content_bbox[3]),
    )
    radius = _axis_radius(center, axis, content_bbox)
    max_ref_size = max(int(sprites[0].size[0]), int(sprites[0].size[1]), int(sprites[1].size[0]), int(sprites[1].size[1]))
    half_sep = max(96.0, min(190.0, float(radius) - 0.85 * float(max_ref_size)))
    if half_sep < 90.0:
        raise ValueError("content bbox too small for reference placement")
    ref_centers = {
        "A": (float(center[0]) - float(axis[0]) * half_sep, float(center[1]) - float(axis[1]) * half_sep),
        "B": (float(center[0]) + float(axis[0]) * half_sep, float(center[1]) + float(axis[1]) * half_sep),
    }
    max_proj = max(float(render_params["distance_margin_px"]) + 8.0, float(radius) - 42.0)
    perp_span = max(38.0, min(132.0, 0.42 * float(radius)))
    collision_gap = int(render_params["icon_collision_gap_px"])

    max_attempts = max(1, int(render_params["scene_placement_max_attempts"]))
    last_error: Exception | None = None
    for _attempt in range(max_attempts):
        try:
            occupancy: list[BBox] = []
            rendered: list[CloserReferenceRenderedIcon] = []
            reference_centers_actual: Dict[str, Tuple[float, float]] = {}

            for index, label in enumerate(("A", "B")):
                plan = plans[int(index)]
                sprite = sprites[int(index)]
                bbox = bbox_from_center_dimensions(ref_centers[str(label)], width=int(sprite.size[0]), height=int(sprite.size[1]))
                if not bbox_inside(bbox, content_bbox):
                    raise ValueError("reference outside content")
                if any(boxes_overlap(bbox, other, gap_px=collision_gap) for other in occupancy):
                    raise ValueError("reference overlap")
                occupancy.append(bbox)
                reference_centers_actual[str(label)] = bbox_center_float(bbox)
                rendered.append(
                    CloserReferenceRenderedIcon(
                        instance_id=f"reference_{str(label).lower()}",
                        role="reference",
                        label=str(label),
                        shape_id=str(plan.shape_id),
                        shape_name=procedural_named_icon_display_name(str(plan.shape_id)),
                        color_name=str(plan.color_name),
                        tint_rgb=tuple(int(value) for value in plan.tint_rgb),
                        fill_style=str(plan.fill_style),
                        bbox_xyxy=tuple(int(value) for value in bbox),
                        center_xy=bbox_center_float(bbox),
                        nominal_size_px=int(plan.nominal_size_px),
                        rotation_degrees=int(plan.rotation_degrees),
                        distance_to_reference_a_px=None,
                        distance_to_reference_b_px=None,
                        closer_reference_label="",
                        counted=False,
                        label_bbox_xyxy=None,
                        noise_edits=tuple(serialize_icon_noise_edits(plan.noise_edits)),
                        noise_seed=plan.noise_seed,
                    )
                )

            for target_index, (plan, sprite) in enumerate(zip(plans[2:], sprites[2:])):
                desired_label = str(plan.desired_closer_label)
                sign = -1.0 if desired_label == "A" else 1.0
                placed = False
                for _placement_attempt in range(180):
                    projection = sign * float(rng.uniform(float(render_params["distance_margin_px"]), max_proj))
                    offset = float(rng.uniform(-perp_span, perp_span))
                    candidate_center = (
                        float(center[0]) + float(axis[0]) * projection + float(perp[0]) * offset,
                        float(center[1]) + float(axis[1]) * projection + float(perp[1]) * offset,
                    )
                    bbox = bbox_from_center_dimensions(candidate_center, width=int(sprite.size[0]), height=int(sprite.size[1]))
                    if not bbox_inside(bbox, content_bbox):
                        continue
                    if any(boxes_overlap(bbox, other, gap_px=collision_gap) for other in occupancy):
                        continue
                    distance_a = math.hypot(candidate_center[0] - reference_centers_actual["A"][0], candidate_center[1] - reference_centers_actual["A"][1])
                    distance_b = math.hypot(candidate_center[0] - reference_centers_actual["B"][0], candidate_center[1] - reference_centers_actual["B"][1])
                    closer = "A" if float(distance_a) < float(distance_b) else "B"
                    if str(closer) != desired_label:
                        continue
                    if abs(float(distance_a) - float(distance_b)) < float(render_params["distance_margin_px"]):
                        continue
                    occupancy.append(bbox)
                    rendered.append(
                        CloserReferenceRenderedIcon(
                            instance_id=f"target_{int(target_index):02d}",
                            role="target",
                            label="",
                            shape_id=str(plan.shape_id),
                            shape_name=procedural_named_icon_display_name(str(plan.shape_id)),
                            color_name=str(plan.color_name),
                            tint_rgb=tuple(int(value) for value in plan.tint_rgb),
                            fill_style=str(plan.fill_style),
                            bbox_xyxy=tuple(int(value) for value in bbox),
                            center_xy=bbox_center_float(bbox),
                            nominal_size_px=int(plan.nominal_size_px),
                            rotation_degrees=int(plan.rotation_degrees),
                            distance_to_reference_a_px=float(distance_a),
                            distance_to_reference_b_px=float(distance_b),
                            closer_reference_label=str(closer),
                            counted=str(closer) == str(sample.queried_reference_label),
                            label_bbox_xyxy=None,
                            noise_edits=tuple(serialize_icon_noise_edits(plan.noise_edits)),
                            noise_seed=plan.noise_seed,
                        )
                    )
                    placed = True
                    break
                if not placed:
                    raise ValueError("failed to place target icon with requested closer reference")

            image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
            draw_single_panel(
                image=image,
                layout=layout,
                background_rgb=tuple(int(value) for value in render_params["background_color_rgb"]),
                panel_fill_rgb=tuple(int(value) for value in render_params["panel_fill_rgb"]),
                panel_border_rgb=tuple(int(value) for value in render_params["panel_border_rgb"]),
                title_color_rgb=tuple(int(value) for value in render_params["header_text_rgb"]),
                corner_radius_px=int(render_params["panel_corner_radius_px"]),
                title_font_size_px=int(render_params["panel_title_font_size_px"]),
                scene_title="Scene",
                icon_canvas_style=render_params.get("_icon_canvas_style_object"),
            )
            for record, sprite in zip(rendered, sprites):
                image.alpha_composite(sprite, (int(record.bbox_xyxy[0]), int(record.bbox_xyxy[1])))
            return CloserReferenceScenePayload(
                image=image.convert("RGB"),
                icons=tuple(rendered),
                panel_geometry=single_panel_geometry_to_trace(layout),
                reference_axis_degrees=int(axis_degrees),
            )
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError("failed to render closer-reference icon scene") from last_error


def _occupancy_bbox_for_icon(
    *,
    icon_bbox: BBox,
    label: str,
    content_bbox: BBox,
    label_font,
    render_params: Mapping[str, Any],
) -> BBox:
    if not str(label):
        return tuple(int(value) for value in icon_bbox)
    label_bbox = label_bbox_for_icon(
        icon_bbox=tuple(int(value) for value in icon_bbox),
        label=str(label),
        content_bbox=tuple(int(value) for value in content_bbox),
        font=label_font,
        padding_px=int(render_params["candidate_label_padding_px"]),
        gap_px=int(render_params["candidate_label_gap_px"]),
    )
    return union_bbox(tuple(int(value) for value in icon_bbox), label_bbox)


def _candidate_distances(rng, *, render_params: Mapping[str, Any], option_count: int) -> Tuple[float, ...]:
    margin = max(10, int(render_params["distance_rank_margin_px"]))
    min_distance = max(74, int(render_params["center_distance_min_px"]))
    jitter = max(0, int(render_params["center_distance_gap_jitter_px"]))
    values: list[float] = [float(min_distance + int(rng.randint(0, max(1, margin // 2))))]
    for _ in range(1, int(option_count)):
        values.append(float(values[-1] + margin + (int(rng.randint(0, jitter)) if jitter > 0 else 0)))
    return tuple(float(value) for value in values)


def _draw_candidate_label(
    *,
    image: Image.Image,
    icon_bbox: BBox,
    label: str,
    content_bbox: BBox,
    label_font,
    render_params: Mapping[str, Any],
) -> BBox:
    label_bbox = label_bbox_for_icon(
        icon_bbox=tuple(int(value) for value in icon_bbox),
        label=str(label),
        content_bbox=tuple(int(value) for value in content_bbox),
        font=label_font,
        padding_px=int(render_params["candidate_label_padding_px"]),
        gap_px=int(render_params["candidate_label_gap_px"]),
    )
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        label_bbox,
        radius=max(4, int(round(0.28 * float(label_bbox[3] - label_bbox[1])))),
        fill=tuple(int(value) for value in render_params["candidate_label_background_rgb"]) + (238,),
        outline=tuple(int(value) for value in render_params["candidate_label_border_rgb"]) + (255,),
        width=1,
    )
    draw_text_centered(
        draw,
        text=str(label),
        center=bbox_center_float(label_bbox),
        font=label_font,
        fill=tuple(int(value) for value in render_params["candidate_label_color_rgb"]),
        stroke_fill=tuple(
            int(value)
            for value in render_params.get("candidate_label_stroke_rgb", render_params["candidate_label_background_rgb"])
        ),
        stroke_width=1,
    )
    return tuple(int(value) for value in label_bbox)


def render_distance_rank_scene(
    *,
    rng,
    query_name: str,
    answer_label: str,
    answer_rank: int,
    plans: Sequence[DistanceRankIconPlan],
    reference_description: str,
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...],
    distractor_count: int,
    render_params: Mapping[str, Any],
    option_labels: Sequence[str],
    angle_pool_degrees: Sequence[int],
) -> Tuple[DistanceRankScenePayload, Image.Image]:
    """Place and render distance-rank icons, labels, and annotation geometry."""

    layout = resolve_single_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    content_bbox = tuple(int(value) for value in layout.scene_content_xyxy)
    label_font = load_font(int(render_params["candidate_label_font_size_px"]), bold=True)
    sprites = [render_planned_named_icon_sprite(plan) for plan in plans]
    reference_plan = plans[0]
    reference_sprite = sprites[0]
    candidate_plans = [plan for plan in plans if str(plan.role) == "candidate"]
    candidate_sprites = [sprites[index] for index, plan in enumerate(plans) if str(plan.role) == "candidate"]
    distractor_pairs = [(plan, sprites[index]) for index, plan in enumerate(plans) if str(plan.role) == "distractor"]

    collision_gap = int(render_params["icon_collision_gap_px"])
    max_attempts = max(1, int(render_params["scene_placement_max_attempts"]))
    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            occupancy: list[BBox] = []

            rx0 = int(content_bbox[0] + int(max(reference_sprite.size)) + 36)
            rx1 = int(content_bbox[2] - int(max(reference_sprite.size)) - 36)
            ry0 = int(content_bbox[1] + int(max(reference_sprite.size)) + 40)
            ry1 = int(content_bbox[3] - int(max(reference_sprite.size)) - 40)
            if rx1 <= rx0 or ry1 <= ry0:
                raise ValueError("content bbox too small for reference icon")
            reference_center = (float(rng.randint(rx0, rx1)), float(rng.randint(ry0, ry1)))
            reference_bbox = bbox_from_center_dimensions(
                reference_center,
                width=int(reference_sprite.size[0]),
                height=int(reference_sprite.size[1]),
            )
            if not bbox_inside(reference_bbox, content_bbox):
                raise ValueError("reference icon outside content")
            occupancy.append(reference_bbox)

            labels_by_rank = [str(plan.label) for plan in candidate_plans]
            plans_by_label = {str(plan.label): plan for plan in candidate_plans}
            sprites_by_label = {str(plan.label): sprite for plan, sprite in zip(candidate_plans, candidate_sprites)}
            distances = _candidate_distances(rng, render_params=render_params, option_count=len(tuple(option_labels)))
            angle_values = list(int(value) for value in angle_pool_degrees)
            rng.shuffle(angle_values)
            candidate_records: list[DistanceRankRenderedIcon] = []
            for rank, label in enumerate(labels_by_rank):
                plan = plans_by_label[str(label)]
                sprite = sprites_by_label[str(label)]
                distance = float(distances[int(rank)])
                placed = False
                for angle_attempt in range(len(angle_values)):
                    angle_degrees = float(angle_values[(int(rank) + int(angle_attempt)) % len(angle_values)])
                    angle = math.radians(angle_degrees)
                    center = (
                        float(reference_center[0]) + distance * math.cos(angle),
                        float(reference_center[1]) + distance * math.sin(angle),
                    )
                    bbox = bbox_from_center_dimensions(center, width=int(sprite.size[0]), height=int(sprite.size[1]))
                    occupancy_bbox = _occupancy_bbox_for_icon(
                        icon_bbox=bbox,
                        label=str(label),
                        content_bbox=content_bbox,
                        label_font=label_font,
                        render_params=render_params,
                    )
                    if not bbox_inside(occupancy_bbox, content_bbox):
                        continue
                    if any(boxes_overlap(occupancy_bbox, other, gap_px=collision_gap) for other in occupancy):
                        continue
                    occupancy.append(occupancy_bbox)
                    candidate_records.append(
                        DistanceRankRenderedIcon(
                            instance_id=f"candidate_{str(label)}",
                            role="candidate",
                            label=str(label),
                            shape_id=str(plan.shape_id),
                            shape_name=procedural_named_icon_display_name(str(plan.shape_id)),
                            color_name=str(plan.color_name),
                            tint_rgb=tuple(int(value) for value in plan.tint_rgb),
                            fill_style=str(plan.fill_style),
                            bbox_xyxy=tuple(int(value) for value in bbox),
                            center_xy=bbox_center_float(bbox),
                            nominal_size_px=int(plan.nominal_size_px),
                            rotation_degrees=int(plan.rotation_degrees),
                            distance_to_reference_px=float(distance),
                            distance_rank=int(rank),
                            noise_edits=tuple(serialize_icon_noise_edits(plan.noise_edits)),
                            noise_seed=plan.noise_seed,
                        )
                    )
                    placed = True
                    break
                if not placed:
                    raise ValueError("failed to place distance-ranked candidate")

            distractor_records: list[DistanceRankRenderedIcon] = []
            for index, (plan, sprite) in enumerate(distractor_pairs):
                placed = False
                for _placement_attempt in range(80):
                    cx = float(rng.randint(int(content_bbox[0] + sprite.size[0] // 2), int(content_bbox[2] - sprite.size[0] // 2)))
                    cy = float(rng.randint(int(content_bbox[1] + sprite.size[1] // 2), int(content_bbox[3] - sprite.size[1] // 2)))
                    bbox = bbox_from_center_dimensions((cx, cy), width=int(sprite.size[0]), height=int(sprite.size[1]))
                    if not bbox_inside(bbox, content_bbox):
                        continue
                    if any(boxes_overlap(bbox, other, gap_px=collision_gap) for other in occupancy):
                        continue
                    occupancy.append(bbox)
                    distance = math.hypot(float(cx) - float(reference_center[0]), float(cy) - float(reference_center[1]))
                    distractor_records.append(
                        DistanceRankRenderedIcon(
                            instance_id=f"distractor_{int(index):02d}",
                            role="distractor",
                            label="",
                            shape_id=str(plan.shape_id),
                            shape_name=procedural_named_icon_display_name(str(plan.shape_id)),
                            color_name=str(plan.color_name),
                            tint_rgb=tuple(int(value) for value in plan.tint_rgb),
                            fill_style=str(plan.fill_style),
                            bbox_xyxy=tuple(int(value) for value in bbox),
                            center_xy=(float(cx), float(cy)),
                            nominal_size_px=int(plan.nominal_size_px),
                            rotation_degrees=int(plan.rotation_degrees),
                            distance_to_reference_px=float(distance),
                            distance_rank=None,
                            noise_edits=tuple(serialize_icon_noise_edits(plan.noise_edits)),
                            noise_seed=plan.noise_seed,
                        )
                    )
                    placed = True
                    break
                if not placed:
                    raise ValueError("failed to place distractor icon")

            sorted_candidates = tuple(
                sorted(candidate_records, key=lambda item: (float(item.distance_to_reference_px or 0.0), str(item.label)))
            )
            sorted_labels = tuple(str(item.label) for item in sorted_candidates)
            if sorted_labels[int(answer_rank)] != str(answer_label):
                raise ValueError("constructed candidate distances did not preserve answer rank")
            adjacent_gaps = [
                float(sorted_candidates[index + 1].distance_to_reference_px or 0.0)
                - float(sorted_candidates[index].distance_to_reference_px or 0.0)
                for index in range(len(sorted_candidates) - 1)
            ]
            if int(answer_rank) > 0 and adjacent_gaps[int(answer_rank) - 1] < float(render_params["distance_rank_margin_px"]):
                raise ValueError("distance gap before answer is too small")
            if int(answer_rank) < len(sorted_candidates) - 1 and adjacent_gaps[int(answer_rank)] < float(render_params["distance_rank_margin_px"]):
                raise ValueError("distance gap after answer is too small")

            image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
            draw_single_panel(
                image=image,
                layout=layout,
                background_rgb=tuple(int(value) for value in render_params["background_color_rgb"]),
                panel_fill_rgb=tuple(int(value) for value in render_params["panel_fill_rgb"]),
                panel_border_rgb=tuple(int(value) for value in render_params["panel_border_rgb"]),
                title_color_rgb=tuple(int(value) for value in render_params["header_text_rgb"]),
                corner_radius_px=int(render_params["panel_corner_radius_px"]),
                title_font_size_px=int(render_params["panel_title_font_size_px"]),
                scene_title="Scene",
                icon_canvas_style=render_params.get("_icon_canvas_style_object"),
            )
            image.alpha_composite(reference_sprite, (int(reference_bbox[0]), int(reference_bbox[1])))
            for record in candidate_records:
                sprite = sprites_by_label[str(record.label)]
                image.alpha_composite(sprite, (int(record.bbox_xyxy[0]), int(record.bbox_xyxy[1])))
            for record, (_plan, sprite) in zip(distractor_records, distractor_pairs):
                image.alpha_composite(sprite, (int(record.bbox_xyxy[0]), int(record.bbox_xyxy[1])))
            for record in candidate_records:
                _draw_candidate_label(
                    image=image,
                    icon_bbox=tuple(int(value) for value in record.bbox_xyxy),
                    label=str(record.label),
                    content_bbox=content_bbox,
                    label_font=label_font,
                    render_params=render_params,
                )

            reference_record = DistanceRankRenderedIcon(
                instance_id="reference",
                role="reference",
                label="",
                shape_id=str(reference_plan.shape_id),
                shape_name=procedural_named_icon_display_name(str(reference_plan.shape_id)),
                color_name=str(reference_plan.color_name),
                tint_rgb=tuple(int(value) for value in reference_plan.tint_rgb),
                fill_style=str(reference_plan.fill_style),
                bbox_xyxy=tuple(int(value) for value in reference_bbox),
                center_xy=bbox_center_float(reference_bbox),
                nominal_size_px=int(reference_plan.nominal_size_px),
                rotation_degrees=int(reference_plan.rotation_degrees),
                distance_to_reference_px=None,
                distance_rank=None,
                noise_edits=tuple(serialize_icon_noise_edits(reference_plan.noise_edits)),
                noise_seed=reference_plan.noise_seed,
            )
            distance_by_label = {
                str(record.label): float(record.distance_to_reference_px or 0.0)
                for record in candidate_records
            }
            return (
                DistanceRankScenePayload(
                    query_key=str(query_name),
                    answer_label=str(answer_label),
                    answer_rank=int(answer_rank),
                    reference_description=str(reference_description),
                    reference_icon=reference_record,
                    candidate_icons=tuple(sorted(candidate_records, key=lambda item: str(item.label))),
                    distractor_icons=tuple(distractor_records),
                    distance_by_label=distance_by_label,
                    sorted_candidate_labels_by_distance=tuple(sorted_labels),
                    panel_geometry=single_panel_geometry_to_trace(layout),
                    sampled_palette_rgb=tuple(sampled_palette_rgb),
                    distractor_count=int(distractor_count),
                ),
                image.convert("RGB"),
            )
        except Exception as exc:
            last_error = exc
            continue
    raise RuntimeError("failed to render named-reference distance-rank scene") from last_error


def serialize_distance_rank_icon(icon: DistanceRankRenderedIcon) -> Dict[str, Any]:
    """Serialize one distance-rank icon for trace payloads."""

    return {
        "entity_kind": "procedural_named_icon",
        "instance_id": str(icon.instance_id),
        "role": str(icon.role),
        "label": str(icon.label),
        "shape_id": str(icon.shape_id),
        "shape_name": str(icon.shape_name),
        "color_name": str(icon.color_name),
        "tint_rgb": [int(value) for value in icon.tint_rgb],
        "fill_style": str(icon.fill_style),
        "bbox_xyxy": [int(value) for value in icon.bbox_xyxy],
        "center_xy": [float(icon.center_xy[0]), float(icon.center_xy[1])],
        "nominal_size_px": int(icon.nominal_size_px),
        "rotation_degrees": int(icon.rotation_degrees),
        "distance_to_reference_px": None if icon.distance_to_reference_px is None else float(icon.distance_to_reference_px),
        "distance_rank": None if icon.distance_rank is None else int(icon.distance_rank),
        "noise_edits": [dict(edit) for edit in icon.noise_edits],
        "noise_seed": None if icon.noise_seed is None else int(icon.noise_seed),
    }


def region_to_trace(region: RegionSpec) -> Dict[str, Any]:
    """Serialize a visible region without hardcoding public identity keys."""

    payload: Dict[str, Any] = {
        trace_key("query", "id"): str(region.query_key),
        "region_kind": str(region.region_kind),
        "counts_inside": bool(region.counts_inside),
        "shape_kind": str(region.shape_kind),
        "band_kind": str(region.band_kind),
        "quadrant_id": str(region.quadrant_id),
        "shelf_index": int(region.shelf_index),
        "shelf_count": int(region.shelf_count),
    }
    if region.bbox_xyxy is not None:
        payload["bbox_xyxy"] = [int(value) for value in region.bbox_xyxy]
    if region.ellipse_center_xy is not None:
        payload["ellipse_center_xy"] = [float(value) for value in region.ellipse_center_xy]
    if region.ellipse_radii_xy is not None:
        payload["ellipse_radii_xy"] = [float(value) for value in region.ellipse_radii_xy]
    if region.band_normal_xy is not None:
        payload["band_normal_xy"] = [float(value) for value in region.band_normal_xy]
    if region.band_center_distance is not None:
        payload["band_center_distance"] = float(region.band_center_distance)
    if region.band_half_width_px is not None:
        payload["band_half_width_px"] = float(region.band_half_width_px)
    if region.band_polygon_xy:
        payload["band_polygon_xy"] = [[float(x), float(y)] for x, y in region.band_polygon_xy]
    return payload


def point_inside_region(region: RegionSpec, center_xy: Sequence[float]) -> bool:
    """Return whether a point lies inside a visible scoped-count region."""

    cx, cy = float(center_xy[0]), float(center_xy[1])
    if region.region_kind in {"shape", "quadrant", "shelf"}:
        if region.shape_kind == "ellipse":
            if region.ellipse_center_xy is None or region.ellipse_radii_xy is None:
                raise ValueError("ellipse region is missing center/radii")
            ex, ey = region.ellipse_center_xy
            rx, ry = region.ellipse_radii_xy
            return ((cx - float(ex)) / max(1e-6, float(rx))) ** 2 + ((cy - float(ey)) / max(1e-6, float(ry))) ** 2 <= 1.0
        if region.bbox_xyxy is None:
            raise ValueError("box-like region is missing bbox")
        x0, y0, x1, y1 = [float(value) for value in region.bbox_xyxy]
        return x0 <= cx <= x1 and y0 <= cy <= y1
    if region.region_kind == "band":
        if region.band_normal_xy is None or region.band_center_distance is None or region.band_half_width_px is None:
            raise ValueError("band region is missing normal/center/width")
        nx, ny = region.band_normal_xy
        distance = abs((float(cx) * float(nx)) + (float(cy) * float(ny)) - float(region.band_center_distance))
        return distance <= float(region.band_half_width_px)
    raise ValueError(f"unsupported region kind: {region.region_kind}")


def _bbox_corners(box: Sequence[int | float]) -> Tuple[Tuple[float, float], ...]:
    x0, y0, x1, y1 = [float(value) for value in box]
    return ((x0, y0), (x1, y0), (x1, y1), (x0, y1))


def bbox_safely_matches_region(
    region: RegionSpec,
    bbox_xyxy: Sequence[int | float],
    *,
    desired_inside: bool,
    margin_px: int,
) -> bool:
    """Evaluate region membership with boundary clearance for stable annotations."""

    x0, y0, x1, y1 = [float(value) for value in bbox_xyxy]
    margin = float(max(0, int(margin_px)))
    if region.region_kind in {"shape", "quadrant", "shelf"}:
        if region.shape_kind == "ellipse":
            if region.ellipse_center_xy is None or region.ellipse_radii_xy is None:
                raise ValueError("ellipse region is missing center/radii")
            ex, ey = region.ellipse_center_xy
            rx, ry = region.ellipse_radii_xy
            scale_margin = margin / max(1.0, min(float(rx), float(ry)))
            if bool(desired_inside):
                threshold = max(0.0, (1.0 - scale_margin) ** 2)
                return all(
                    ((float(cx) - float(ex)) / max(1e-6, float(rx))) ** 2
                    + ((float(cy) - float(ey)) / max(1e-6, float(ry))) ** 2
                    <= threshold
                    for cx, cy in _bbox_corners(bbox_xyxy)
                )
            nearest_x = min(max(float(ex), float(x0)), float(x1))
            nearest_y = min(max(float(ey), float(y0)), float(y1))
            value = ((float(nearest_x) - float(ex)) / max(1e-6, float(rx))) ** 2 + (
                (float(nearest_y) - float(ey)) / max(1e-6, float(ry))
            ) ** 2
            return value >= (1.0 + scale_margin) ** 2
        if region.bbox_xyxy is None:
            raise ValueError("box-like region is missing bbox")
        rx0, ry0, rx1, ry1 = [float(value) for value in region.bbox_xyxy]
        if bool(desired_inside):
            return rx0 + margin <= x0 and x1 <= rx1 - margin and ry0 + margin <= y0 and y1 <= ry1 - margin
        return x1 <= rx0 - margin or x0 >= rx1 + margin or y1 <= ry0 - margin or y0 >= ry1 + margin
    if region.region_kind == "band":
        if region.band_normal_xy is None or region.band_center_distance is None or region.band_half_width_px is None:
            raise ValueError("band region is missing normal/center/width")
        nx, ny = region.band_normal_xy
        signed_distances = [
            (float(cx) * float(nx)) + (float(cy) * float(ny)) - float(region.band_center_distance)
            for cx, cy in _bbox_corners(bbox_xyxy)
        ]
        lower = min(float(value) for value in signed_distances)
        upper = max(float(value) for value in signed_distances)
        half_width = float(region.band_half_width_px)
        if bool(desired_inside):
            return lower >= -half_width + margin and upper <= half_width - margin
        return lower >= half_width + margin or upper <= -half_width - margin
    raise ValueError(f"unsupported region kind: {region.region_kind}")


def sample_box_region(
    rng,
    *,
    query_key: str,
    counts_inside: bool,
    content_bbox: BBox,
    shape_kind: str,
) -> RegionSpec:
    """Sample a rectangular or elliptical region."""

    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    width = int(x1 - x0)
    height = int(y1 - y0)
    box_w = int(round(float(width) * float(rng.uniform(0.36, 0.56))))
    box_h = int(round(float(height) * float(rng.uniform(0.38, 0.62))))
    box_x0 = int(rng.randint(int(x0 + 18), int(max(x0 + 18, x1 - box_w - 18))))
    box_y0 = int(rng.randint(int(y0 + 16), int(max(y0 + 16, y1 - box_h - 16))))
    bbox = (int(box_x0), int(box_y0), int(box_x0 + box_w), int(box_y0 + box_h))
    center = bbox_center_float(bbox)
    return RegionSpec(
        query_key=str(query_key),
        region_kind="shape",
        counts_inside=bool(counts_inside),
        shape_kind=str(shape_kind),
        bbox_xyxy=bbox,
        ellipse_center_xy=center if str(shape_kind) == "ellipse" else None,
        ellipse_radii_xy=(0.5 * float(box_w), 0.5 * float(box_h)) if str(shape_kind) == "ellipse" else None,
    )


def band_normal(kind: str) -> Tuple[float, float]:
    """Return a normal vector for a visible band orientation."""

    if str(kind) == "vertical":
        return (1.0, 0.0)
    if str(kind) == "horizontal":
        return (0.0, 1.0)
    if str(kind) == "slanted_positive":
        return (math.sqrt(0.5), -math.sqrt(0.5))
    if str(kind) == "slanted_negative":
        return (math.sqrt(0.5), math.sqrt(0.5))
    raise ValueError(f"unsupported band kind: {kind}")


def sample_band_region(
    rng,
    *,
    query_key: str,
    counts_inside: bool,
    content_bbox: BBox,
    band_kind: str,
) -> RegionSpec:
    """Sample a visible band region with clear interior/exterior separation."""

    x0, y0, x1, y1 = [float(value) for value in content_bbox]
    width = float(x1 - x0)
    height = float(y1 - y0)
    nx, ny = band_normal(str(band_kind))
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    values = [(float(x) * float(nx)) + (float(y) * float(ny)) for x, y in corners]
    min_value = min(values)
    max_value = max(values)
    span = max(1.0, float(max_value - min_value))
    half_width = float(rng.uniform(0.13, 0.20)) * min(width, height)
    center_min = min_value + (0.32 * span)
    center_max = max_value - (0.32 * span)
    center_distance = float(rng.uniform(center_min, center_max)) if center_min < center_max else 0.5 * (min_value + max_value)
    tx, ty = -float(ny), float(nx)
    base_x = float(nx) * float(center_distance)
    base_y = float(ny) * float(center_distance)
    line_half_len = 2.0 * math.hypot(width, height)
    polygon = (
        (base_x - float(nx) * half_width - tx * line_half_len, base_y - float(ny) * half_width - ty * line_half_len),
        (base_x - float(nx) * half_width + tx * line_half_len, base_y - float(ny) * half_width + ty * line_half_len),
        (base_x + float(nx) * half_width + tx * line_half_len, base_y + float(ny) * half_width + ty * line_half_len),
        (base_x + float(nx) * half_width - tx * line_half_len, base_y + float(ny) * half_width - ty * line_half_len),
    )
    return RegionSpec(
        query_key=str(query_key),
        region_kind="band",
        counts_inside=bool(counts_inside),
        band_kind=str(band_kind),
        band_normal_xy=(float(nx), float(ny)),
        band_center_distance=float(center_distance),
        band_half_width_px=float(half_width),
        band_polygon_xy=tuple((float(x), float(y)) for x, y in polygon),
    )


def sample_quadrant_region(rng, *, query_key: str, content_bbox: BBox, quadrant_id: str) -> RegionSpec:
    """Sample one quadrant region from the content area."""

    del rng
    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    xm = int(round(0.5 * float(x0 + x1)))
    ym = int(round(0.5 * float(y0 + y1)))
    quadrant_to_bbox = {
        "top_left": (x0, y0, xm, ym),
        "top_right": (xm, y0, x1, ym),
        "bottom_left": (x0, ym, xm, y1),
        "bottom_right": (xm, ym, x1, y1),
    }
    bbox = quadrant_to_bbox[str(quadrant_id)]
    return RegionSpec(
        query_key=str(query_key),
        region_kind="quadrant",
        counts_inside=True,
        shape_kind="rectangle",
        quadrant_id=str(quadrant_id),
        bbox_xyxy=tuple(int(value) for value in bbox),
    )


def sample_shelf_region(
    rng,
    *,
    query_key: str,
    content_bbox: BBox,
    shelf_count_min: int,
    shelf_count_max: int,
) -> RegionSpec:
    """Sample one shelf-row region from the content area."""

    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    shelf_count = int(rng.randint(int(shelf_count_min), int(shelf_count_max)))
    shelf_index = int(rng.randrange(0, int(shelf_count)))
    shelf_h = float(y1 - y0) / float(max(1, int(shelf_count)))
    sy0 = int(round(float(y0) + float(shelf_index) * shelf_h))
    sy1 = int(round(float(y0) + float(shelf_index + 1) * shelf_h))
    return RegionSpec(
        query_key=str(query_key),
        region_kind="shelf",
        counts_inside=True,
        shape_kind="rectangle",
        shelf_index=int(shelf_index),
        shelf_count=int(shelf_count),
        bbox_xyxy=(int(x0), int(sy0), int(x1), int(sy1)),
    )


def sample_region_icon_center(
    rng,
    *,
    content_bbox: BBox,
    sprite_size: Tuple[int, int],
    region: RegionSpec,
    desired_inside: bool,
    margin_px: int,
) -> Tuple[float, float]:
    """Sample an icon center whose full bbox is safely inside/outside a region."""

    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    half_w = 0.5 * float(sprite_size[0])
    half_h = 0.5 * float(sprite_size[1])
    min_x = float(x0) + half_w
    max_x = float(x1) - half_w
    min_y = float(y0) + half_h
    max_y = float(y1) - half_h
    if min_x >= max_x or min_y >= max_y:
        raise ValueError("sprite does not fit content bbox")
    for _ in range(900):
        cx = float(rng.uniform(min_x, max_x))
        cy = float(rng.uniform(min_y, max_y))
        bbox = bbox_from_center_and_size((cx, cy), sprite_size)
        if bbox_safely_matches_region(region, bbox, desired_inside=bool(desired_inside), margin_px=int(margin_px)):
            return (float(cx), float(cy))
    raise ValueError("could not sample center with requested region membership")


def _draw_clipped_polygon(
    image: Image.Image,
    *,
    content_bbox: BBox,
    polygon: Sequence[Sequence[float]],
    fill_rgba: Tuple[int, int, int, int],
    outline_rgba: Tuple[int, int, int, int] | None,
    width: int,
) -> None:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    points = [(float(x), float(y)) for x, y in polygon]
    draw.polygon(points, fill=tuple(int(value) for value in fill_rgba))
    if outline_rgba is not None:
        draw.line(points + [points[0]], fill=tuple(int(value) for value in outline_rgba), width=max(1, int(width)))
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rectangle(tuple(int(value) for value in content_bbox), fill=255)
    alpha = ImageChops.multiply(overlay.getchannel("A"), mask)
    overlay.putalpha(alpha)
    image.alpha_composite(overlay)


def draw_region_underlay(image: Image.Image, *, region: RegionSpec, content_bbox: BBox, render_params: Mapping[str, Any]) -> None:
    """Draw the translucent fill for a visible scoped-count region."""

    fill = tuple(int(value) for value in render_params["region_fill_rgb"]) + (int(render_params["region_fill_alpha"]),)
    guide = tuple(int(value) for value in render_params["region_guide_rgb"]) + (150,)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if region.region_kind in {"shape", "quadrant", "shelf"}:
        if region.bbox_xyxy is None:
            raise ValueError("box-like region is missing bbox")
        if region.shape_kind == "ellipse":
            draw.ellipse(tuple(int(value) for value in region.bbox_xyxy), fill=fill)
        else:
            draw.rectangle(tuple(int(value) for value in region.bbox_xyxy), fill=fill)
        if region.region_kind == "quadrant":
            x0, y0, x1, y1 = [int(value) for value in content_bbox]
            xm = int(round(0.5 * float(x0 + x1)))
            ym = int(round(0.5 * float(y0 + y1)))
            draw.line((xm, y0, xm, y1), fill=guide, width=2)
            draw.line((x0, ym, x1, ym), fill=guide, width=2)
        if region.region_kind == "shelf":
            x0, y0, x1, y1 = [int(value) for value in content_bbox]
            for row in range(1, int(region.shelf_count)):
                y = int(round(float(y0) + (float(row) * float(y1 - y0) / float(max(1, int(region.shelf_count))))))
                draw.line((x0, y, x1, y), fill=guide, width=2)
        image.alpha_composite(overlay)
        return
    if region.region_kind == "band":
        _draw_clipped_polygon(
            image,
            content_bbox=content_bbox,
            polygon=region.band_polygon_xy,
            fill_rgba=fill,
            outline_rgba=None,
            width=int(render_params["region_outline_width_px"]),
        )
        return
    raise ValueError(f"unsupported region kind: {region.region_kind}")


def draw_region_outline(image: Image.Image, *, region: RegionSpec, content_bbox: BBox, render_params: Mapping[str, Any]) -> None:
    """Draw the visible boundary for a scoped-count region."""

    outline = tuple(int(value) for value in render_params["region_outline_rgb"]) + (230,)
    guide = tuple(int(value) for value in render_params["region_guide_rgb"]) + (170,)
    width = max(1, int(render_params["region_outline_width_px"]))
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if region.region_kind in {"shape", "quadrant", "shelf"}:
        if region.bbox_xyxy is None:
            raise ValueError("box-like region is missing bbox")
        if region.region_kind == "quadrant":
            x0, y0, x1, y1 = [int(value) for value in content_bbox]
            xm = int(round(0.5 * float(x0 + x1)))
            ym = int(round(0.5 * float(y0 + y1)))
            draw.line((xm, y0, xm, y1), fill=guide, width=2)
            draw.line((x0, ym, x1, ym), fill=guide, width=2)
        if region.region_kind == "shelf":
            x0, y0, x1, y1 = [int(value) for value in content_bbox]
            for row in range(1, int(region.shelf_count)):
                y = int(round(float(y0) + (float(row) * float(y1 - y0) / float(max(1, int(region.shelf_count))))))
                draw.line((x0, y, x1, y), fill=guide, width=2)
        if region.shape_kind == "ellipse":
            draw.ellipse(tuple(int(value) for value in region.bbox_xyxy), outline=outline, width=width)
        else:
            draw.rectangle(tuple(int(value) for value in region.bbox_xyxy), outline=outline, width=width)
        image.alpha_composite(overlay)
        return
    if region.region_kind == "band":
        _draw_clipped_polygon(
            image,
            content_bbox=content_bbox,
            polygon=region.band_polygon_xy,
            fill_rgba=(0, 0, 0, 0),
            outline_rgba=outline,
            width=width,
        )
        return
    raise ValueError(f"unsupported region kind: {region.region_kind}")


def serialize_region_icon(instance: RenderedRegionIcon) -> Dict[str, Any]:
    """Serialize one scoped-region icon for trace payloads."""

    return {
        "entity_kind": "procedural_named_icon",
        "instance_id": str(instance.instance_id),
        "shape_id": str(instance.shape_id),
        "shape_name": str(instance.shape_name),
        "bbox_xyxy": [int(value) for value in instance.bbox_xyxy],
        "center_xy": [float(value) for value in instance.center_xy],
        "nominal_size_px": int(instance.nominal_size_px),
        "rotation_degrees": int(instance.rotation_degrees),
        "tint_rgb": [int(value) for value in instance.tint_rgb],
        "fill_style": str(instance.fill_style),
        "inside_region": bool(instance.inside_region),
        "counted": bool(instance.counted),
        "noise_edits": [dict(edit) for edit in instance.noise_edits],
        "noise_seed": None if instance.noise_seed is None else int(instance.noise_seed),
    }


__all__ = [
    "band_normal",
    "bbox_safely_matches_region",
    "draw_region_outline",
    "draw_region_underlay",
    "point_inside_region",
    "render_closer_reference_scene",
    "render_distance_rank_scene",
    "region_to_trace",
    "sample_band_region",
    "sample_box_region",
    "sample_quadrant_region",
    "sample_region_icon_center",
    "sample_shelf_region",
    "serialize_closer_reference_icon",
    "serialize_distance_rank_icon",
    "serialize_region_icon",
]
