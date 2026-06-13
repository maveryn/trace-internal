"""Reusable rendering primitives for named-field icon scenes."""

from __future__ import annotations

from typing import Any, Mapping, Sequence, Tuple

from ...shared.icon_task_rendering import sample_icon_instance_noise
from ...shared.procedural_named_icon_field_scene import (
    NamedIconFieldSpec,
    rotation_for_named_shape,
)
from ...shared.procedural_named_icons import PROCEDURAL_NAMED_ICON_SHAPES
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


__all__ = ["build_named_icon_specs_from_semantics"]
