"""Sampling and rendering primitives for icon-field scenes."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from PIL import Image

from ...shared.icon_assets import render_icon_rgba, resolve_icon_pool
from ...shared.icon_noise import serialize_icon_noise_edits
from ...shared.icon_scene import (
    RenderedIconInstance,
    draw_single_panel,
    max_overlap_with_existing,
    random_paste_bbox,
    resolve_single_panel_layout,
    serialize_rendered_icon_instance,
    single_panel_geometry_to_trace,
)
from ...shared.icon_style import sample_icon_tints
from ...shared.icon_task_rendering import sample_icon_instance_noise

from .state import IconFieldScenePayload, TypeFrequencySpec
from .styles import sample_icon_field_palette


def sample_and_render_icon_field_scene(
    rng,
    *,
    instance_seed: int,
    frequency_spec: TypeFrequencySpec,
    pool_manifest: str,
    render_params: Mapping[str, Any],
    noise_namespace: str,
) -> Tuple[IconFieldScenePayload, Image.Image]:
    """Sample and render one single-panel icon-field scene."""

    pool = list(resolve_icon_pool(str(pool_manifest)))
    if len(pool) < int(frequency_spec.distinct_type_count):
        raise ValueError("icon pool is too small for icon-field scene")

    sampled_icon_ids = [
        str(icon_id) for icon_id in rng.sample(pool, int(frequency_spec.distinct_type_count))
    ]
    singleton_icon_ids = [str(icon_id) for icon_id in sampled_icon_ids[: int(frequency_spec.singleton_count)]]
    repeated_icon_ids = [str(icon_id) for icon_id in sampled_icon_ids[int(frequency_spec.singleton_count) :]]

    scene_icon_ids = list(singleton_icon_ids)
    type_frequencies: Dict[str, int] = {}
    for icon_id in singleton_icon_ids:
        type_frequencies[str(icon_id)] = 1
    for icon_id, multiplicity in zip(repeated_icon_ids, frequency_spec.repeated_type_multiplicities):
        type_frequencies[str(icon_id)] = int(multiplicity)
        scene_icon_ids.extend([str(icon_id)] * int(multiplicity))
    if len(scene_icon_ids) != int(frequency_spec.object_count):
        raise ValueError("icon-field scene did not realize the requested object count")
    rng.shuffle(scene_icon_ids)

    palette = sample_icon_field_palette(rng, render_params)
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
    min_size = max(16, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    max_overlap_fraction = max(0.0, min(1.0, float(render_params["scene_max_overlap_fraction"])))
    placement_attempts = max(1, int(render_params["scene_placement_max_attempts"]))
    shrink_rounds = max(0, int(render_params["scene_size_shrink_rounds"]))
    content_w = max(1, int(scene_content_bbox[2] - scene_content_bbox[0]))
    content_h = max(1, int(scene_content_bbox[3] - scene_content_bbox[1]))
    current_max_size = min(int(max_size), int(content_w), int(content_h))
    sampled_tints = list(
        sample_icon_tints(rng, palette=palette, count=int(frequency_spec.distinct_type_count))
    )
    rotation_candidates = tuple(int(value) for value in render_params["rotation_candidates_degrees"])

    type_styles: Dict[str, Dict[str, Any]] = {}
    for type_index, icon_id in enumerate(sampled_icon_ids):
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{noise_namespace}:icon_type_{int(type_index)}",
            render_params=render_params,
        )
        type_styles[str(icon_id)] = {
            "tint_rgb": tuple(int(channel) for channel in sampled_tints[int(type_index)]),
            "rotation_degrees": int(rng.choice(rotation_candidates)) % 360,
            "nominal_size_px": int(rng.randint(int(min_size), int(max(int(min_size), int(current_max_size))))),
            "noise_edits": tuple(noise_edits),
            "noise_seed": int(noise_seed),
        }

    placed_bboxes: List[Tuple[int, int, int, int]] = []
    scene_instances: List[Dict[str, Any]] = []
    singleton_indices: List[int] = []
    singleton_bboxes: List[Tuple[int, int, int, int]] = []
    repeated_indices: List[int] = []
    repeated_bboxes: List[Tuple[int, int, int, int]] = []
    scene_rotations_degrees: List[int] = []

    for index, icon_id in enumerate(scene_icon_ids):
        type_style = type_styles[str(icon_id)]
        tint_rgb = tuple(int(channel) for channel in type_style["tint_rgb"])
        rotation_degrees = int(type_style["rotation_degrees"])
        nominal_size = int(type_style["nominal_size_px"])
        noise_edits = tuple(type_style["noise_edits"])
        noise_seed = int(type_style["noise_seed"])
        sprite = render_icon_rgba(
            icon_id=str(icon_id),
            size_px=int(nominal_size),
            tint_rgb=tint_rgb,
            rotation_degrees=int(rotation_degrees),
            mirror_x=False,
            noise_edits=tuple(noise_edits),
            noise_seed=int(noise_seed),
        )
        paste_bbox = None
        for _ in range(int(placement_attempts) * (int(shrink_rounds) + 1)):
            try:
                candidate_bbox = random_paste_bbox(
                    sprite_size=sprite.size,
                    content_bbox=scene_content_bbox,
                    rng=rng,
                )
            except ValueError:
                continue
            if float(max_overlap_with_existing(candidate_bbox, placed_bboxes)) > float(max_overlap_fraction):
                continue
            paste_bbox = tuple(int(value) for value in candidate_bbox)
            break
        if paste_bbox is None:
            raise ValueError("failed to place icon-field icon within overlap constraints")

        image.alpha_composite(sprite, (int(paste_bbox[0]), int(paste_bbox[1])))
        placed_bboxes.append(tuple(int(value) for value in paste_bbox))
        is_singleton_type = int(type_frequencies[str(icon_id)]) == 1
        if bool(is_singleton_type):
            singleton_indices.append(int(index))
            singleton_bboxes.append(tuple(int(value) for value in paste_bbox))
        else:
            repeated_indices.append(int(index))
            repeated_bboxes.append(tuple(int(value) for value in paste_bbox))
        scene_rotations_degrees.append(int(rotation_degrees) % 360)
        rendered_instance = RenderedIconInstance(
            instance_id=f"scene_icon_{int(index)}",
            icon_id=str(icon_id),
            panel="scene",
            bbox_xyxy=tuple(int(value) for value in paste_bbox),
            nominal_size_px=int(nominal_size),
            rotation_degrees=int(rotation_degrees) % 360,
            mirror_x=False,
            tint_rgb=tint_rgb,
            noise_edits=serialize_icon_noise_edits(tuple(noise_edits)),
            noise_seed=int(noise_seed),
        )
        scene_instances.append(
            serialize_rendered_icon_instance(
                rendered_instance,
                entity_kind="scene_icon",
                extra_fields={
                    "index": int(index),
                    "type_frequency": int(type_frequencies[str(icon_id)]),
                    "is_singleton_type": bool(is_singleton_type),
                    "is_repeated_type": not bool(is_singleton_type),
                },
            )
        )

    return (
        IconFieldScenePayload(
            object_count=int(frequency_spec.object_count),
            singleton_count=int(frequency_spec.singleton_count),
            repeated_type_count=int(frequency_spec.repeated_type_count),
            repeated_type_multiplicities=tuple(
                int(value) for value in frequency_spec.repeated_type_multiplicities
            ),
            distinct_type_count=int(frequency_spec.distinct_type_count),
            singleton_icon_ids=tuple(str(icon_id) for icon_id in singleton_icon_ids),
            repeated_icon_ids=tuple(str(icon_id) for icon_id in repeated_icon_ids),
            scene_icon_ids=tuple(str(icon_id) for icon_id in scene_icon_ids),
            scene_rotations_degrees=tuple(int(value) for value in scene_rotations_degrees),
            singleton_indices=tuple(int(value) for value in singleton_indices),
            singleton_bboxes=tuple(tuple(int(value) for value in bbox) for bbox in singleton_bboxes),
            repeated_indices=tuple(int(value) for value in repeated_indices),
            repeated_bboxes=tuple(tuple(int(value) for value in bbox) for bbox in repeated_bboxes),
            type_frequencies={str(key): int(value) for key, value in type_frequencies.items()},
            sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in palette),
            panel_geometry=single_panel_geometry_to_trace(layout),
            scene_instances=tuple(dict(entity) for entity in scene_instances),
        ),
        image.convert("RGB"),
    )


__all__ = ["sample_and_render_icon_field_scene"]
