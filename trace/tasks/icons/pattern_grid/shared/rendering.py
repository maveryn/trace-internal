"""Neutral renderer for numbered icon pattern grids."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ...shared.icon_assets import render_icon_rgba, resolve_icon_pool
from ...shared.icon_noise import serialize_icon_noise_edits
from ...shared.icon_scene import (
    IconInstanceSpec,
    RenderedIconInstance,
    centered_paste_bbox,
    serialize_rendered_icon_instance,
    single_panel_geometry_to_trace,
)
from ...shared.icon_single_panel_labeled_grid_scene import (
    prepare_single_panel_labeled_grid_scene,
    resolve_single_panel_labeled_grid_canvas_size,
)
from ...shared.icon_style import sample_single_icon_tint
from ...shared.icon_task_rendering import sample_icon_instance_noise

from .state import PatternGridSpec, RenderedPatternGridScene


def _resolve_size_level_nominal_sizes(
    rng,
    *,
    size_levels: Sequence[int],
    content_limit_px: int,
    render_params: Mapping[str, Any],
) -> Dict[int, int]:
    """Map symbolic size levels to visible nominal icon sizes."""

    ordered_levels = [int(level) for level in size_levels]
    gap_px = int(render_params["size_level_gap_px"])
    if int(gap_px) <= 0:
        raise ValueError("size_level_gap_px must be positive")
    max_nominal = min(int(render_params["size_icon_size_max_px"]), int(content_limit_px))
    min_nominal = int(render_params["size_icon_size_min_px"])
    required_top = int(min_nominal + gap_px * max(0, len(ordered_levels) - 1))
    if int(max_nominal) < int(required_top):
        raise ValueError("sampled grid cell geometry is too small for the configured size levels")
    top_size = int(rng.randint(int(required_top), int(max_nominal)))
    return {
        int(level): int(top_size - gap_px * (len(ordered_levels) - index - 1))
        for index, level in enumerate(ordered_levels)
    }


def _choose_color_nominal_size(rng, *, content_limit_px: int, render_params: Mapping[str, Any]) -> int:
    max_nominal = min(int(render_params["color_icon_size_max_px"]), int(content_limit_px))
    min_nominal = int(render_params["color_icon_size_min_px"])
    if int(max_nominal) < int(min_nominal):
        raise ValueError("sampled grid cell geometry is too small for configured color icons")
    return int(rng.randint(int(min_nominal), int(max_nominal)))


def render_pattern_grid_scene(
    rng,
    *,
    instance_seed: int,
    spec: PatternGridSpec,
    pool_manifest: str,
    render_params: Mapping[str, Any],
    noise_namespace: str,
) -> RenderedPatternGridScene:
    """Render one complete numbered pattern grid from a symbolic spec."""

    pool = list(resolve_icon_pool(str(pool_manifest)))
    if not pool:
        raise ValueError("pattern-grid icon pool resolved no icons")
    pattern_icon_id = str(rng.choice(pool))
    cell_box_width_px = int(
        rng.randint(int(render_params["cell_box_width_min_px"]), int(render_params["cell_box_width_max_px"]))
    )
    cell_box_height_px = int(
        rng.randint(int(render_params["cell_box_height_min_px"]), int(render_params["cell_box_height_max_px"]))
    )
    canvas_width, canvas_height = resolve_single_panel_labeled_grid_canvas_size(
        rows=int(spec.grid_rows),
        cols=int(spec.grid_cols),
        cell_box_width_px=int(cell_box_width_px),
        cell_box_height_px=int(cell_box_height_px),
        render_params=render_params,
    )
    labels = [str(index + 1) for index in range(int(spec.grid_rows * spec.grid_cols))]
    prepared = prepare_single_panel_labeled_grid_scene(
        scene_labels=labels,
        grid_rows=int(spec.grid_rows),
        grid_cols=int(spec.grid_cols),
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        panel_corner_radius_px=int(render_params["panel_corner_radius_px"]),
        panel_title_font_size_px=int(render_params["panel_title_font_size_px"]),
        background_rgb=tuple(int(v) for v in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(v) for v in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(v) for v in render_params["header_text_rgb"]),
        cell_padding_px=int(render_params["cell_padding_px"]),
        cell_border_rgb=tuple(int(v) for v in render_params["cell_border_rgb"]),
        cell_label_color_rgb=tuple(int(v) for v in render_params["cell_label_color_rgb"]),
        cell_label_stroke_rgb=tuple(int(v) for v in render_params["cell_label_stroke_rgb"]),
        cell_label_stroke_width_px=1,
        cell_label_font_size_px=int(render_params["cell_label_font_size_px"]),
        cell_corner_radius_px=int(render_params["cell_corner_radius_px"]),
        scene_content_side_padding_px=int(render_params["scene_content_side_padding_px"]),
        scene_content_bottom_padding_px=int(render_params["scene_content_bottom_padding_px"]),
        scene_content_top_offset_px=int(render_params["scene_content_top_offset_px"]),
        scene_square_cells=False,
        scene_title="",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )
    if not prepared.scene_cells:
        raise ValueError("prepared pattern grid produced no cells")
    first_content = tuple(int(value) for value in prepared.scene_cells[0].content_bbox_xyxy)
    content_limit = min(int(first_content[2] - first_content[0]), int(first_content[3] - first_content[1]))
    if int(content_limit) <= 0:
        raise ValueError("pattern grid content geometry is invalid")

    if str(spec.attribute_axis) == "size":
        tint_rgb, sampled_palette_rgb = sample_single_icon_tint(
            rng,
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
        size_map = _resolve_size_level_nominal_sizes(
            rng,
            size_levels=spec.level_support,
            content_limit_px=int(content_limit),
            render_params=render_params,
        )
        nominal_size = None
    else:
        sampled_palette_rgb = tuple(tuple(int(channel) for channel in color) for color in spec.color_ladder_rgb)
        tint_rgb = (0, 0, 0)
        size_map = None
        nominal_size = _choose_color_nominal_size(rng, content_limit_px=int(content_limit), render_params=render_params)

    image = prepared.image.copy()
    scene_cells: List[Dict[str, Any]] = []
    scene_icon_instances: List[Dict[str, Any]] = []
    violating_cell_bbox = None
    for cell_index, (prepared_cell, expected_level, observed_level) in enumerate(
        zip(prepared.scene_cells, spec.expected_levels, spec.observed_levels)
    ):
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{noise_namespace}:cell_{int(cell_index)}",
            render_params=render_params,
        )
        if str(spec.attribute_axis) == "size":
            observed_nominal_size = int(size_map[int(observed_level)])  # type: ignore[index]
            expected_nominal_size = int(size_map[int(expected_level)])  # type: ignore[index]
            icon_tint = tuple(int(v) for v in tint_rgb)
        else:
            observed_nominal_size = int(nominal_size or 0)
            expected_nominal_size = int(nominal_size or 0)
            icon_tint = tuple(int(v) for v in spec.color_ladder_rgb[int(observed_level)])
        icon_spec = IconInstanceSpec(
            icon_id=str(pattern_icon_id),
            rotation_degrees=int(spec.shared_rotation_degrees),
            tint_rgb=tuple(int(v) for v in icon_tint),
            noise_edits=tuple(noise_edits),
            noise_seed=int(noise_seed),
        )
        sprite = render_icon_rgba(
            icon_id=str(icon_spec.icon_id),
            size_px=int(observed_nominal_size),
            tint_rgb=tuple(int(v) for v in icon_spec.tint_rgb),
            rotation_degrees=int(icon_spec.rotation_degrees),
            mirror_x=bool(icon_spec.mirror_x),
            noise_edits=tuple(icon_spec.noise_edits),
            noise_seed=icon_spec.noise_seed,
        )
        paste_bbox = centered_paste_bbox(
            sprite_size=sprite.size,
            slot_bbox=tuple(int(value) for value in prepared_cell.content_bbox_xyxy),
            jitter_px=0,
            rng=rng,
        )
        image.alpha_composite(sprite, (int(paste_bbox[0]), int(paste_bbox[1])))
        cell_bbox = tuple(int(value) for value in prepared_cell.cell_bbox_xyxy)
        if int(cell_index) == int(spec.violation_cell_index):
            violating_cell_bbox = cell_bbox
        rendered_instance = RenderedIconInstance(
            instance_id=f"scene_icon_{int(cell_index)}",
            icon_id=str(icon_spec.icon_id),
            panel="scene",
            bbox_xyxy=tuple(int(value) for value in paste_bbox),
            nominal_size_px=int(observed_nominal_size),
            rotation_degrees=int(icon_spec.rotation_degrees) % 360,
            mirror_x=bool(icon_spec.mirror_x),
            tint_rgb=tuple(int(value) for value in icon_spec.tint_rgb),
            noise_edits=serialize_icon_noise_edits(icon_spec.noise_edits),
            noise_seed=None if icon_spec.noise_seed is None else int(icon_spec.noise_seed),
        )
        cell_payload: Dict[str, Any] = {
            "entity_kind": "pattern_cell",
            "panel": "scene",
            "cell_index": int(cell_index),
            "cell_label_text": str(prepared_cell.label),
            "cell_bbox_xyxy": list(cell_bbox),
            "grid_row": int(cell_index // int(spec.grid_cols)),
            "grid_col": int(cell_index % int(spec.grid_cols)),
            "is_violation": bool(int(cell_index) == int(spec.violation_cell_index)),
            "expected_level": int(expected_level),
            "observed_level": int(observed_level),
            "rendered_icon_count": 1,
        }
        if str(spec.attribute_axis) == "color":
            expected_rgb = tuple(int(channel) for channel in spec.color_ladder_rgb[int(expected_level)])
            observed_rgb = tuple(int(channel) for channel in spec.color_ladder_rgb[int(observed_level)])
            cell_payload.update(
                {
                    "expected_color_level": int(expected_level),
                    "observed_color_level": int(observed_level),
                    "expected_color_name": str(spec.level_names[int(expected_level)]),
                    "observed_color_name": str(spec.level_names[int(observed_level)]),
                    "expected_color_rgb": list(expected_rgb),
                    "observed_color_rgb": list(observed_rgb),
                }
            )
        else:
            cell_payload.update(
                {
                    "expected_size_level": int(expected_level),
                    "observed_size_level": int(observed_level),
                    "expected_nominal_size_px": int(expected_nominal_size),
                    "observed_nominal_size_px": int(observed_nominal_size),
                }
            )
        scene_cells.append(cell_payload)
        scene_icon_instances.append(
            serialize_rendered_icon_instance(
                rendered_instance,
                entity_kind="scene_icon",
                extra_fields={
                    "cell_index": int(cell_index),
                    "cell_label_text": str(prepared_cell.label),
                    "cell_bbox_xyxy": list(cell_bbox),
                },
            )
        )
    if violating_cell_bbox is None:
        raise ValueError("rendered pattern grid did not produce the violating cell bbox")

    return RenderedPatternGridScene(
        image=image.convert("RGB"),
        pattern_icon_id=str(pattern_icon_id),
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in sampled_palette_rgb),
        panel_geometry=single_panel_geometry_to_trace(prepared.layout),
        scene_cells=tuple(dict(cell) for cell in scene_cells),
        scene_icon_instances=tuple(dict(instance) for instance in scene_icon_instances),
        violating_cell_bbox=tuple(int(value) for value in violating_cell_bbox),
        cell_box_width_px=int(cell_box_width_px),
        cell_box_height_px=int(cell_box_height_px),
        nominal_size_px=None if nominal_size is None else int(nominal_size),
        size_level_nominal_sizes_px=None if size_map is None else {int(key): int(value) for key, value in size_map.items()},
    )


__all__ = ["render_pattern_grid_scene"]
