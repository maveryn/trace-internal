"""Rendering and scene sampling for two-anchor icon scenes."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ...shared.anchor_marking import draw_anchor_marker
from ...shared.icon_assets import render_icon_rgba, resolve_icon_pool
from ...shared.icon_noise import serialize_icon_noise_edits
from ...shared.icon_scene import (
    draw_single_panel,
    max_overlap_with_existing,
    random_paste_bbox,
    resolve_single_panel_layout,
    single_panel_geometry_to_trace,
)
from ...shared.icon_style import icon_palette_meets_distance_constraints, sample_icon_palette
from ...shared.icon_task_rendering import sample_icon_instance_noise

from .spatial_primitives import (
    bbox_center,
    center_in_strip,
    center_outside_strip,
    sample_anchor_pair_bboxes,
    target_region_bbox,
)
from .state import TwoAnchorScenePayload


def _choice(rng, values: Sequence[Any]) -> Any:
    """Select one item from a non-empty sequence without coercing tuple items."""

    if not values:
        raise ValueError("cannot choose from an empty sequence")
    return values[int(rng.randrange(len(values)))]


def sample_and_render_two_anchor_scene(
    rng,
    *,
    instance_seed: int,
    strip_axis: str,
    object_count: int,
    target_count: int,
    distractor_count: int,
    pool_manifest: str,
    rotation_candidates: Tuple[int, ...],
    render_params: Mapping[str, Any],
) -> Tuple[TwoAnchorScenePayload, Image.Image]:
    """Sample and render one two-anchor strip relation scene."""

    pool = tuple(str(icon_id) for icon_id in resolve_icon_pool(str(pool_manifest)))
    if len(pool) < 2:
        raise ValueError("two-anchor strip relation pool resolved too few icons")
    anchor_icon_id = str(_choice(rng, pool))
    candidate_pool = tuple(str(icon_id) for icon_id in pool if str(icon_id) != str(anchor_icon_id))
    if not candidate_pool:
        raise ValueError("two-anchor strip relation pool resolved no non-anchor icon ids")

    palette_size = int(rng.randint(int(render_params["palette_size_min"]), int(render_params["palette_size_max"])))
    palette = tuple(
        tuple(int(channel) for channel in color)
        for color in sample_icon_palette(
            rng,
            palette_size=int(palette_size),
            channel_min=int(render_params["color_channel_min"]),
            channel_max=int(render_params["color_channel_max"]),
            anchor_colors=(
                tuple(int(v) for v in render_params["background_color_rgb"]),
                tuple(int(v) for v in render_params["panel_fill_rgb"]),
                tuple(int(v) for v in render_params["panel_border_rgb"]),
                tuple(int(v) for v in render_params["header_text_rgb"]),
            ),
            min_color_distance=float(render_params["min_color_distance"]),
            distance_space=str(render_params["color_distance_space"]),
        )
    )
    if not icon_palette_meets_distance_constraints(
        palette=palette,
        anchor_colors=(
            tuple(int(v) for v in render_params["background_color_rgb"]),
            tuple(int(v) for v in render_params["panel_fill_rgb"]),
            tuple(int(v) for v in render_params["panel_border_rgb"]),
            tuple(int(v) for v in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    ):
        raise ValueError("sampled icon palette did not satisfy strict distance constraints")

    anchor_tint_rgb = tuple(int(channel) for channel in _choice(rng, palette))
    anchor_rotation_degrees = int(_choice(rng, rotation_candidates))
    anchor_nominal_size = int(rng.randint(int(render_params["scene_icon_size_min_px"]), int(render_params["scene_icon_size_max_px"])))
    anchor_noise_edits_a, anchor_noise_seed_a = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"icons.two_anchor.{strip_axis}.anchor_a",
        render_params=render_params,
    )
    anchor_noise_edits_b, anchor_noise_seed_b = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"icons.two_anchor.{strip_axis}.anchor_b",
        render_params=render_params,
    )

    layout = resolve_single_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
        reserve_title=False,
    )
    image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
    draw_single_panel(
        image=image,
        layout=layout,
        background_rgb=tuple(int(v) for v in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(v) for v in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(v) for v in render_params["header_text_rgb"]),
        corner_radius_px=int(render_params["panel_corner_radius_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
        scene_title="",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )
    scene_content_bbox = tuple(int(value) for value in layout.scene_content_xyxy)

    anchor_sprite_a = render_icon_rgba(
        icon_id=str(anchor_icon_id),
        size_px=int(anchor_nominal_size),
        tint_rgb=tuple(int(channel) for channel in anchor_tint_rgb),
        rotation_degrees=int(anchor_rotation_degrees),
        mirror_x=False,
        noise_edits=tuple(anchor_noise_edits_a),
        noise_seed=int(anchor_noise_seed_a),
    )
    anchor_bbox_a, anchor_bbox_b = sample_anchor_pair_bboxes(
        rng,
        content_bbox=scene_content_bbox,
        sprite_size=anchor_sprite_a.size,
        strip_axis=str(strip_axis),
        span_ratio_min=float(render_params["strip_span_ratio_min"]),
        span_ratio_max=float(render_params["strip_span_ratio_max"]),
        outside_ratio_min=float(render_params["strip_outside_ratio_min"]),
        edge_padding_px=int(render_params["anchor_edge_padding_px"]),
    )
    image.alpha_composite(anchor_sprite_a, (int(anchor_bbox_a[0]), int(anchor_bbox_a[1])))
    anchor_sprite_b = render_icon_rgba(
        icon_id=str(anchor_icon_id),
        size_px=int(anchor_nominal_size),
        tint_rgb=tuple(int(channel) for channel in anchor_tint_rgb),
        rotation_degrees=int(anchor_rotation_degrees),
        mirror_x=False,
        noise_edits=tuple(anchor_noise_edits_b),
        noise_seed=int(anchor_noise_seed_b),
    )
    image.alpha_composite(anchor_sprite_b, (int(anchor_bbox_b[0]), int(anchor_bbox_b[1])))

    anchor_highlight_a = draw_anchor_marker(
        image=image,
        anchor_bbox=anchor_bbox_a,
        content_bbox=scene_content_bbox,
        highlight_padding_px=int(render_params["anchor_highlight_padding_px"]),
        highlight_radius_px=int(render_params["anchor_highlight_radius_px"]),
        outline_rgb=tuple(int(v) for v in render_params["anchor_outline_rgb"]),
        label_color_rgb=tuple(int(v) for v in render_params["anchor_label_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        label_font_size_px=int(render_params["anchor_label_font_size_px"]),
        label_text="A",
    )
    anchor_highlight_b = draw_anchor_marker(
        image=image,
        anchor_bbox=anchor_bbox_b,
        content_bbox=scene_content_bbox,
        highlight_padding_px=int(render_params["anchor_highlight_padding_px"]),
        highlight_radius_px=int(render_params["anchor_highlight_radius_px"]),
        outline_rgb=tuple(int(v) for v in render_params["anchor_outline_rgb"]),
        label_color_rgb=tuple(int(v) for v in render_params["anchor_label_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        label_font_size_px=int(render_params["anchor_label_font_size_px"]),
        label_text="B",
    )

    anchor_a_center_xy = bbox_center(anchor_bbox_a)
    anchor_b_center_xy = bbox_center(anchor_bbox_b)

    placed_bboxes: List[Tuple[int, int, int, int]] = [
        tuple(int(value) for value in anchor_highlight_a),
        tuple(int(value) for value in anchor_highlight_b),
    ]
    match_indices = set(rng.sample(list(range(int(object_count))), int(target_count)))
    matching_indices: List[int] = []
    matching_bboxes: List[Tuple[int, int, int, int]] = []
    scene_instances: List[Dict[str, Any]] = []
    scene_icon_ids: List[str] = []
    scene_tints_rgb: List[Tuple[int, int, int]] = []
    scene_rotations_degrees: List[int] = []

    min_size = max(16, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    placement_attempts = max(1, int(render_params["scene_placement_max_attempts"]))
    shrink_rounds = max(0, int(render_params["scene_size_shrink_rounds"]))
    shrink_factor = max(0.1, min(1.0, float(render_params["scene_size_shrink_factor"])))
    max_overlap_fraction = max(0.0, min(1.0, float(render_params["scene_max_overlap_fraction"])))

    for index in range(int(object_count)):
        is_target = int(index) in match_indices
        icon_id = str(_choice(rng, candidate_pool))
        tint_rgb = tuple(int(channel) for channel in _choice(rng, palette))
        rotation_degrees = int(_choice(rng, rotation_candidates))
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"icons.two_anchor.{strip_axis}.scene_icon_{int(index)}",
            render_params=render_params,
        )
        sprite = None
        paste_bbox = None
        nominal_size = None
        for shrink_round in range(int(shrink_rounds) + 1):
            round_max_size = max(int(min_size), int(round(float(max_size) * (float(shrink_factor) ** int(shrink_round)))))
            for _ in range(int(placement_attempts)):
                sampled_size = int(rng.randint(int(min_size), int(round_max_size)))
                candidate_sprite = render_icon_rgba(
                    icon_id=str(icon_id),
                    size_px=int(sampled_size),
                    tint_rgb=tuple(int(channel) for channel in tint_rgb),
                    rotation_degrees=int(rotation_degrees),
                    mirror_x=False,
                    noise_edits=tuple(noise_edits),
                    noise_seed=int(noise_seed),
                )
                region_bbox = scene_content_bbox
                if bool(is_target):
                    target_region = target_region_bbox(
                        content_bbox=scene_content_bbox,
                        anchor_a_center_xy=anchor_a_center_xy,
                        anchor_b_center_xy=anchor_b_center_xy,
                        strip_axis=str(strip_axis),
                        margin_px=int(render_params["strip_boundary_margin_px"]),
                        sprite_size=candidate_sprite.size,
                    )
                    if target_region is None:
                        continue
                    region_bbox = target_region
                try:
                    candidate_bbox = random_paste_bbox(
                        sprite_size=candidate_sprite.size,
                        content_bbox=region_bbox,
                        rng=rng,
                    )
                except ValueError:
                    continue
                if float(max_overlap_with_existing(candidate_bbox, placed_bboxes)) > float(max_overlap_fraction):
                    continue
                center_xy = bbox_center(candidate_bbox)
                if bool(is_target):
                    if not center_in_strip(
                        center_xy=center_xy,
                        anchor_a_center_xy=anchor_a_center_xy,
                        anchor_b_center_xy=anchor_b_center_xy,
                        strip_axis=str(strip_axis),
                        margin_px=int(render_params["strip_boundary_margin_px"]),
                    ):
                        continue
                else:
                    if not center_outside_strip(
                        center_xy=center_xy,
                        anchor_a_center_xy=anchor_a_center_xy,
                        anchor_b_center_xy=anchor_b_center_xy,
                        strip_axis=str(strip_axis),
                        margin_px=int(render_params["strip_boundary_margin_px"]),
                    ):
                        continue
                sprite = candidate_sprite
                paste_bbox = tuple(int(value) for value in candidate_bbox)
                nominal_size = int(sampled_size)
                break
            if sprite is not None and paste_bbox is not None and nominal_size is not None:
                break
        if sprite is None or paste_bbox is None or nominal_size is None:
            raise ValueError("failed to place icon under two-anchor strip constraints")
        image.alpha_composite(sprite, (int(paste_bbox[0]), int(paste_bbox[1])))
        placed_bboxes.append(tuple(int(value) for value in paste_bbox))
        center_xy = bbox_center(paste_bbox)
        in_strip = center_in_strip(
            center_xy=center_xy,
            anchor_a_center_xy=anchor_a_center_xy,
            anchor_b_center_xy=anchor_b_center_xy,
            strip_axis=str(strip_axis),
            margin_px=int(render_params["strip_boundary_margin_px"]),
        )
        if bool(is_target):
            matching_indices.append(int(index))
            matching_bboxes.append(tuple(int(value) for value in paste_bbox))
        scene_icon_ids.append(str(icon_id))
        scene_tints_rgb.append(tuple(int(channel) for channel in tint_rgb))
        scene_rotations_degrees.append(int(rotation_degrees))
        scene_instances.append(
            {
                "entity_kind": "scene_icon",
                "role": "candidate",
                "instance_id": f"scene_icon_{int(index)}",
                "icon_id": str(icon_id),
                "panel": "scene",
                "bbox_xyxy": [int(value) for value in paste_bbox],
                "center_xy": [float(center_xy[0]), float(center_xy[1])],
                "nominal_size_px": int(nominal_size),
                "rotation_degrees": int(rotation_degrees) % 360,
                "mirror_x": False,
                "tint_rgb": [int(channel) for channel in tint_rgb],
                "noise_edits": [dict(edit) for edit in serialize_icon_noise_edits(tuple(noise_edits))],
                "noise_seed": int(noise_seed),
                "center_in_strip": bool(in_strip),
                "is_match": bool(is_target),
            }
        )

    anchor_instances = (
        {
            "entity_kind": "anchor_icon",
            "role": "anchor_a",
            "label": "A",
            "instance_id": "anchor_a",
            "icon_id": str(anchor_icon_id),
            "panel": "scene",
            "bbox_xyxy": [int(value) for value in anchor_bbox_a],
            "center_xy": [float(anchor_a_center_xy[0]), float(anchor_a_center_xy[1])],
            "nominal_size_px": int(anchor_nominal_size),
            "rotation_degrees": int(anchor_rotation_degrees) % 360,
            "mirror_x": False,
            "tint_rgb": [int(channel) for channel in anchor_tint_rgb],
            "noise_edits": [dict(edit) for edit in serialize_icon_noise_edits(tuple(anchor_noise_edits_a))],
            "noise_seed": int(anchor_noise_seed_a),
            "highlight_bbox_xyxy": [int(value) for value in anchor_highlight_a],
        },
        {
            "entity_kind": "anchor_icon",
            "role": "anchor_b",
            "label": "B",
            "instance_id": "anchor_b",
            "icon_id": str(anchor_icon_id),
            "panel": "scene",
            "bbox_xyxy": [int(value) for value in anchor_bbox_b],
            "center_xy": [float(anchor_b_center_xy[0]), float(anchor_b_center_xy[1])],
            "nominal_size_px": int(anchor_nominal_size),
            "rotation_degrees": int(anchor_rotation_degrees) % 360,
            "mirror_x": False,
            "tint_rgb": [int(channel) for channel in anchor_tint_rgb],
            "noise_edits": [dict(edit) for edit in serialize_icon_noise_edits(tuple(anchor_noise_edits_b))],
            "noise_seed": int(anchor_noise_seed_b),
            "highlight_bbox_xyxy": [int(value) for value in anchor_highlight_b],
        },
    )

    return (
        TwoAnchorScenePayload(
            object_count=int(object_count),
            target_count=int(target_count),
            distractor_count=int(distractor_count),
            strip_axis=str(strip_axis),
            anchor_icon_id=str(anchor_icon_id),
            anchor_tint_rgb=tuple(int(channel) for channel in anchor_tint_rgb),
            anchor_rotation_degrees=int(anchor_rotation_degrees) % 360,
            anchor_a_center_xy=(float(anchor_a_center_xy[0]), float(anchor_a_center_xy[1])),
            anchor_b_center_xy=(float(anchor_b_center_xy[0]), float(anchor_b_center_xy[1])),
            strip_boundary_margin_px=int(render_params["strip_boundary_margin_px"]),
            scene_icon_ids=tuple(str(icon_id) for icon_id in scene_icon_ids),
            scene_tints_rgb=tuple(tuple(int(channel) for channel in tint) for tint in scene_tints_rgb),
            scene_rotations_degrees=tuple(int(value) for value in scene_rotations_degrees),
            matching_scene_indices=tuple(int(value) for value in matching_indices),
            matching_bboxes=tuple(tuple(int(value) for value in box) for box in matching_bboxes),
            sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in palette),
            panel_geometry=single_panel_geometry_to_trace(layout),
            scene_instances=tuple(dict(entity) for entity in scene_instances),
            anchor_instances=(dict(anchor_instances[0]), dict(anchor_instances[1])),
        ),
        image.convert("RGB"),
    )


__all__ = ["sample_and_render_two_anchor_scene"]
