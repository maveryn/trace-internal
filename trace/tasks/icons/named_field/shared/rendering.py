"""Reusable rendering primitives for named-field icon scenes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence, Tuple

from ...shared.icon_style import sample_icon_palette
from ...shared.icon_task_rendering import sample_icon_instance_noise
from ...shared.procedural_named_icon_field_scene import (
    NamedIconFieldSpec,
    rotation_for_named_shape,
)
from ...shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_SHAPES,
    sample_procedural_named_icon_fill_style,
)
from ....shared.named_colors import available_named_colors


def build_named_icon_specs_from_semantics(
    *,
    semantic_specs: Sequence[Any],
    instance_seed: int,
    render_params: Mapping[str, Any],
    rng,
    noise_namespace: str,
) -> Tuple[Tuple[NamedIconFieldSpec, ...], Tuple[Tuple[int, int, int], ...]]:
    """Convert semantic shape/color/style records into renderable icon specs."""

    color_by_name = {
        str(name): tuple(int(channel) for channel in rgb)
        for name, rgb in available_named_colors()
    }
    min_size = max(12, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    specs: list[NamedIconFieldSpec] = []
    for index, semantic_spec in enumerate(semantic_specs):
        shape_id = str(semantic_spec.shape_id)
        if shape_id not in set(PROCEDURAL_NAMED_ICON_SHAPES):
            raise ValueError(f"unsupported named icon shape: {shape_id}")
        color_name = str(semantic_spec.color_name)
        tint_rgb = tuple(int(channel) for channel in color_by_name[str(color_name)])
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{noise_namespace}:named_icon_{int(index)}",
            render_params=render_params,
        )
        specs.append(
            NamedIconFieldSpec(
                shape_id=str(shape_id),
                tint_rgb=tint_rgb,
                color_name=str(color_name),
                fill_style=str(semantic_spec.fill_style),
                nominal_size_px=int(rng.randint(int(min_size), int(max_size))),
                rotation_degrees=rotation_for_named_shape(rng, str(shape_id)),
                placement_group="",
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
        )
    sampled_palette_rgb = tuple(
        tuple(int(channel) for channel in rgb)
        for _name, rgb in available_named_colors()
    )
    return tuple(specs), sampled_palette_rgb


def build_boolean_scene_specs(
    *,
    run_namespace: str,
    sample: Any,
    instance_seed: int,
    render_params: Mapping[str, Any],
    rng,
) -> Tuple[Tuple[NamedIconFieldSpec, ...], Tuple[Tuple[int, int, int], ...]]:
    """Project Boolean symbolic icon records to renderable named-icon specs."""

    return build_named_icon_specs_from_semantics(
        semantic_specs=sample.semantic_specs,
        instance_seed=int(instance_seed),
        render_params=render_params,
        rng=rng,
        noise_namespace=str(run_namespace),
    )


def build_counterfactual_scene_specs(
    *,
    run_namespace: str,
    sample: Any,
    instance_seed: int,
    render_params: Mapping[str, Any],
    rng,
) -> Tuple[Tuple[NamedIconFieldSpec, ...], Tuple[Tuple[int, int, int], ...]]:
    """Project counterfactual symbolic icon records to renderable named-icon specs."""

    palette_size = int(rng.randint(int(render_params["palette_size_min"]), int(render_params["palette_size_max"])))
    palette = sample_icon_palette(
        rng,
        palette_size=int(palette_size),
        channel_min=int(render_params["color_channel_min"]),
        channel_max=int(render_params["color_channel_max"]),
        anchor_colors=(
            tuple(int(value) for value in render_params["background_color_rgb"]),
            tuple(int(value) for value in render_params["panel_fill_rgb"]),
            tuple(int(value) for value in render_params["panel_border_rgb"]),
            tuple(int(value) for value in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )
    min_size = max(12, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    specs: list[NamedIconFieldSpec] = []
    for index, semantic_spec in enumerate(sample.semantic_specs):
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{run_namespace}:named_icon_{int(index)}",
            render_params=render_params,
        )
        specs.append(
            NamedIconFieldSpec(
                shape_id=str(semantic_spec.shape_id),
                tint_rgb=tuple(int(value) for value in rng.choice(palette)),
                nominal_size_px=int(rng.randint(int(min_size), int(max_size))),
                fill_style=sample_procedural_named_icon_fill_style(
                    rng,
                    support=sample.fill_style_support,
                    probabilities=sample.fill_style_probabilities,
                ),
                rotation_degrees=rotation_for_named_shape(rng, str(semantic_spec.shape_id)),
                placement_group="",
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
        )
    return tuple(specs), tuple(tuple(int(channel) for channel in color) for color in palette)


def build_shape_count_scene_specs(
    *,
    run_namespace: str,
    sample: Any,
    instance_seed: int,
    render_params: Mapping[str, Any],
    rng,
) -> Tuple[Tuple[NamedIconFieldSpec, ...], Tuple[Tuple[int, int, int], ...]]:
    """Convert direct shape-count semantics into renderable icon specs."""

    palette_size = int(rng.randint(int(render_params["palette_size_min"]), int(render_params["palette_size_max"])))
    palette = sample_icon_palette(
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
    min_size = max(12, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    specs: list[NamedIconFieldSpec] = []
    group_styles: dict[str, Tuple[Tuple[int, int, int], int, str]] = {}
    stack_modes = {"shape_stacks", "target_stack_with_oddballs", "mixed_stacks"}
    for index, shape_id in enumerate(sample.shape_ids):
        placement_group = str(sample.placement_groups[int(index)] or "")
        group_key = placement_group or str(shape_id)
        if str(sample.arrangement_mode) in stack_modes and group_key not in group_styles:
            group_styles[group_key] = (
                tuple(int(value) for value in rng.choice(palette)),
                int(rng.randint(int(min_size), int(max_size))),
                sample_procedural_named_icon_fill_style(
                    rng,
                    support=sample.fill_style_support,
                    probabilities=sample.fill_style_probabilities,
                ),
            )
        if str(sample.arrangement_mode) in stack_modes:
            tint_rgb, nominal_size_px, fill_style = group_styles[str(group_key)]
        else:
            tint_rgb = tuple(int(value) for value in rng.choice(palette))
            nominal_size_px = int(rng.randint(int(min_size), int(max_size)))
            fill_style = sample_procedural_named_icon_fill_style(
                rng,
                support=sample.fill_style_support,
                probabilities=sample.fill_style_probabilities,
            )
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{run_namespace}:named_icon_{int(index)}",
            render_params=render_params,
        )
        specs.append(
            NamedIconFieldSpec(
                shape_id=str(shape_id),
                tint_rgb=tuple(int(value) for value in tint_rgb),
                nominal_size_px=int(nominal_size_px),
                fill_style=str(fill_style),
                rotation_degrees=0 if str(sample.arrangement_mode) in stack_modes else rotation_for_named_shape(rng, str(shape_id)),
                placement_group=str(placement_group),
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
        )
    return tuple(specs), tuple(tuple(int(channel) for channel in color) for color in palette)


__all__ = [
    "build_boolean_scene_specs",
    "build_counterfactual_scene_specs",
    "build_named_icon_specs_from_semantics",
    "build_shape_count_scene_specs",
]
