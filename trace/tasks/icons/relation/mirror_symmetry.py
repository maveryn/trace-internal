"""Count labeled Scene cells whose mirror symmetry matches the Reference cell."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageChops

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.counting_sampling import resolve_counting_target_and_distractor_triplet
from ...shared.labeling import LABEL_POOL_A_L, assign_shuffled_labels
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import build_icons_relation_mirror_symmetry_complexity
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_assets import render_icon_rgba, resolve_icon_pool
from ..shared.icon_labeled_grid_scene import prepare_two_panel_labeled_grid_scene
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import panel_geometry_to_trace
from ..shared.icon_style import icon_palette_meets_distance_constraints, sample_icon_palette
from ..shared.icon_task_rendering import resolve_icon_render_params, resolve_icon_rgb_param, sample_icon_instance_noise
from ..shared.evidence import matching_scene_cell_bbox_evidence
from ..shared.public_query_task import rewrite_icons_query_output


_SYMMETRY_VARIANTS: Tuple[str, ...] = (
    "mirror_vertical",
    "mirror_horizontal",
    "mirror_diagonal_main",
    "mirror_diagonal_anti",
    "mirror_both_axes",
)
_PUBLIC_QUERY_VARIANT = "mirror_symmetry_count"

_EXACT_SYMMETRY_SIGNATURES: Dict[str, Tuple[bool, bool, bool, bool]] = {
    "mirror_vertical": (True, False, False, False),
    "mirror_horizontal": (False, True, False, False),
    "mirror_diagonal_main": (False, False, True, False),
    "mirror_diagonal_anti": (False, False, False, True),
    "mirror_both_axes": (True, True, False, False),
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for mirror-symmetry relation grids."""

    object_count_min: int = 6
    object_count_max: int = 6
    target_count_min: int = 0
    target_count_max: int = 4
    distractor_count_min: int = 2
    distractor_count_max: int = 6
    distractor_margin_over_target: int = 0
    canvas_width: int = 1104
    canvas_height: int = 640
    reference_panel_width_px: int = 296
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    scene_icon_size_min_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_min_px
    scene_icon_size_max_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_max_px
    reference_icon_size_px: int = 110
    cell_padding_px: int = 10
    cell_border_rgb: Tuple[int, int, int] = (218, 223, 233)
    cell_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    cell_label_font_size_px: int = 22
    pool_manifest: str = "non_symmetry.txt"
    rotation_candidates_degrees: Tuple[int, ...] = (0, 90, 180, 270)
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: deepcopy(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )
    symmetric_icon_count_choices: Tuple[int, ...] = (2, 4, 6)
    both_axes_icon_count_choices: Tuple[int, ...] = (4,)
    nonsymmetric_icon_count_choices: Tuple[int, ...] = (2, 4, 6)
    patch_inner_margin_px: int = 8
    patch_min_gap_px: int = 6
    patch_sampling_attempts: int = 160


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one mirror-symmetry relation grid."""

    object_count: int
    target_count: int
    distractor_count: int
    query_variant: str
    cell_labels: Tuple[str, ...]
    matching_labels: Tuple[str, ...]
    scene_cell_symmetry_ids: Tuple[str, ...]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    reference_cell: Dict[str, Any]
    scene_cells: Tuple[Dict[str, Any], ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_icons__mirror_grid__mirror_symmetry_count",
)


def _resolve_fixed_grid_cardinalities(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
) -> Tuple[int, Dict[str, float], int, Dict[str, float], int, Dict[str, float]]:
    """Resolve mirror-grid counts with stable seeded selection over the small support."""

    (
        object_count,
        object_count_probabilities,
        target_count,
        target_count_probabilities,
        distractor_count,
        distractor_count_probabilities,
    ) = resolve_counting_target_and_distractor_triplet(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        fallback_total_min=_DEFAULTS.object_count_min,
        fallback_total_max=_DEFAULTS.object_count_max,
        fallback_target_min=_DEFAULTS.target_count_min,
        fallback_target_max=_DEFAULTS.target_count_max,
        fallback_distractor_min=_DEFAULTS.distractor_count_min,
        fallback_distractor_max=_DEFAULTS.distractor_count_max,
    )

    balanced_enabled = bool(params.get("balanced_sampling", group_default(_GEN_DEFAULTS, "balanced_sampling", True)))
    count_overridden = any(
        key in params and params.get(key) is not None
        for key in (
            "object_count",
            "object_count_weights",
            "target_count",
            "target_count_weights",
            "distractor_count",
            "distractor_count_weights",
        )
    )
    if (not bool(balanced_enabled)) or bool(count_overridden):
        return (
            int(object_count),
            dict(object_count_probabilities),
            int(target_count),
            dict(target_count_probabilities),
            int(distractor_count),
            dict(distractor_count_probabilities),
        )

    if len(object_count_probabilities) != 1:
        return (
            int(object_count),
            dict(object_count_probabilities),
            int(target_count),
            dict(target_count_probabilities),
            int(distractor_count),
            dict(distractor_count_probabilities),
        )

    supported_targets = sorted(int(value) for value in target_count_probabilities.keys())
    distractor_min = int(
        params.get(
            "distractor_count_min",
            group_default(_GEN_DEFAULTS, "distractor_count_min", _DEFAULTS.distractor_count_min),
        )
    )
    distractor_max = int(
        params.get(
            "distractor_count_max",
            group_default(_GEN_DEFAULTS, "distractor_count_max", _DEFAULTS.distractor_count_max),
        )
    )
    supported_distractors = {
        int(object_count) - int(value)
        for value in supported_targets
        if int(distractor_min) <= int(object_count) - int(value) <= int(distractor_max)
    }
    if not supported_targets:
        return (
            int(object_count),
            dict(object_count_probabilities),
            int(target_count),
            dict(target_count_probabilities),
            int(distractor_count),
            dict(distractor_count_probabilities),
        )

    sampling_index = abs(int(instance_seed))
    selected_target = int(supported_targets[int(sampling_index) % len(supported_targets)])
    selected_distractor = int(object_count) - int(selected_target)
    if int(selected_distractor) not in supported_distractors:
        raise ValueError("mirror symmetry task resolved an infeasible distractor count for the selected target count")

    return (
        int(object_count),
        dict(object_count_probabilities),
        int(selected_target),
        dict(target_count_probabilities),
        int(selected_distractor),
        {
            str(value): (1.0 if int(value) == int(selected_distractor) else 0.0)
            for value in sorted(supported_distractors)
        },
    )


def _resolve_mirror_signature(scene_rng, *, params: Mapping[str, Any], instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the sampled mirror signature while accepting source variant overrides."""

    signature_params = dict(params)
    if signature_params.get("mirror_signature_weights") is None and signature_params.get("variant_weights") is not None:
        signature_params["mirror_signature_weights"] = signature_params["variant_weights"]
    explicit_variant = signature_params.get("query_variant")
    if signature_params.get("mirror_signature") is None and explicit_variant is not None:
        variant = str(explicit_variant).strip()
        if variant in set(_SYMMETRY_VARIANTS):
            signature_params["mirror_signature"] = str(variant)
        elif variant == str(_PUBLIC_QUERY_VARIANT):
            signature_params.pop("query_variant", None)
    selected_signature, signature_probabilities = resolve_variant(
        scene_rng,
        params=signature_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=_SYMMETRY_VARIANTS,
        explicit_key="mirror_signature",
        weights_key="mirror_signature_weights",
    )
    selected_signature = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=signature_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected_signature),
        variant_probabilities=dict(signature_probabilities),
        supported_variants=_SYMMETRY_VARIANTS,
        balance_flag_key="balanced_variant_sampling",
        explicit_key="mirror_signature",
        weights_key="mirror_signature_weights",
    )
    return str(selected_signature), dict(signature_probabilities)


def _resolve_rotation_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve the supported icon rotations for symmetry cells."""

    raw = params.get(
        "rotation_candidates_degrees",
        group_default(_RENDER_DEFAULTS, "rotation_candidates_degrees", list(_DEFAULTS.rotation_candidates_degrees)),
    )
    if not isinstance(raw, (list, tuple)):
        raise ValueError("rotation_candidates_degrees must be a sequence")
    values = tuple(int(value) % 360 for value in raw)
    if not values:
        raise ValueError("rotation_candidates_degrees resolved no values")
    return values


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, Any]:
    """Resolve render params, including grid-cell extras for symmetry scenes."""

    render_params = resolve_icon_render_params(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        fallback_defaults=_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    render_params["cell_padding_px"] = int(
        params.get("cell_padding_px", group_default(_RENDER_DEFAULTS, "cell_padding_px", _DEFAULTS.cell_padding_px))
    )
    render_params["cell_border_rgb"] = resolve_icon_rgb_param(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        key="cell_border_rgb",
        fallback=_DEFAULTS.cell_border_rgb,
        instance_seed=int(instance_seed),
    )
    render_params["cell_label_color_rgb"] = resolve_icon_rgb_param(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        key="cell_label_color_rgb",
        fallback=_DEFAULTS.cell_label_color_rgb,
        instance_seed=int(instance_seed),
    )
    render_params["cell_label_font_size_px"] = int(
        params.get(
            "cell_label_font_size_px",
            group_default(_RENDER_DEFAULTS, "cell_label_font_size_px", _DEFAULTS.cell_label_font_size_px),
        )
    )
    render_params["rotation_candidates_degrees"] = _resolve_rotation_candidates(params)
    render_params["symmetric_icon_count_choices"] = tuple(
        int(value)
        for value in params.get(
            "symmetric_icon_count_choices",
            group_default(_RENDER_DEFAULTS, "symmetric_icon_count_choices", list(_DEFAULTS.symmetric_icon_count_choices)),
        )
    )
    render_params["both_axes_icon_count_choices"] = tuple(
        int(value)
        for value in params.get(
            "both_axes_icon_count_choices",
            group_default(_RENDER_DEFAULTS, "both_axes_icon_count_choices", list(_DEFAULTS.both_axes_icon_count_choices)),
        )
    )
    render_params["nonsymmetric_icon_count_choices"] = tuple(
        int(value)
        for value in params.get(
            "nonsymmetric_icon_count_choices",
            group_default(
                _RENDER_DEFAULTS,
                "nonsymmetric_icon_count_choices",
                list(_DEFAULTS.nonsymmetric_icon_count_choices),
            ),
        )
    )
    render_params["patch_inner_margin_px"] = int(
        params.get(
            "patch_inner_margin_px",
            group_default(_RENDER_DEFAULTS, "patch_inner_margin_px", _DEFAULTS.patch_inner_margin_px),
        )
    )
    render_params["patch_min_gap_px"] = int(
        params.get("patch_min_gap_px", group_default(_RENDER_DEFAULTS, "patch_min_gap_px", _DEFAULTS.patch_min_gap_px))
    )
    render_params["patch_sampling_attempts"] = int(
        params.get(
            "patch_sampling_attempts",
            group_default(_RENDER_DEFAULTS, "patch_sampling_attempts", _DEFAULTS.patch_sampling_attempts),
        )
    )
    return render_params


def _mirror_axis(variant: str) -> str:
    """Return the flip axis used to mirror one seed placement."""

    if str(variant) == "mirror_vertical":
        return "horizontal_flip"
    if str(variant) == "mirror_horizontal":
        return "vertical_flip"
    if str(variant) == "mirror_diagonal_main":
        return "diagonal_main_flip"
    if str(variant) == "mirror_diagonal_anti":
        return "diagonal_anti_flip"
    if str(variant) == "mirror_both_axes":
        return "both_axes_flip"
    raise ValueError(f"unsupported symmetry variant: {variant}")


def _flip_image(image: Image.Image, variant: str) -> Image.Image:
    """Return one image flipped across the requested mirror axis."""

    if str(variant) == "mirror_vertical":
        return image.transpose(Image.FLIP_LEFT_RIGHT)
    if str(variant) == "mirror_horizontal":
        return image.transpose(Image.FLIP_TOP_BOTTOM)
    if str(variant) == "mirror_diagonal_main":
        return image.transpose(Image.TRANSPOSE)
    if str(variant) == "mirror_diagonal_anti":
        return image.transpose(Image.TRANSVERSE)
    if str(variant) == "mirror_both_axes":
        return image.transpose(Image.ROTATE_180)
    raise ValueError(f"unsupported symmetry variant: {variant}")


def _has_mirror_symmetry(image: Image.Image, variant: str) -> bool:
    """Return true when the image is exactly symmetric under the requested mirror."""

    if str(variant) in {"mirror_diagonal_main", "mirror_diagonal_anti"} and int(image.size[0]) != int(image.size[1]):
        return False
    flipped = _flip_image(image, str(variant))
    return ImageChops.difference(image, flipped).getbbox() is None


def _symmetry_signature(image: Image.Image) -> Tuple[bool, bool, bool, bool]:
    """Return the exact `(vertical, horizontal, diagonal_main, diagonal_anti)` signature."""

    return (
        bool(_has_mirror_symmetry(image, "mirror_vertical")),
        bool(_has_mirror_symmetry(image, "mirror_horizontal")),
        bool(_has_mirror_symmetry(image, "mirror_diagonal_main")),
        bool(_has_mirror_symmetry(image, "mirror_diagonal_anti")),
    )


def _is_exact_symmetry_variant(image: Image.Image, variant: str) -> bool:
    """Return true when the image matches exactly the requested symmetry signature."""

    expected = _EXACT_SYMMETRY_SIGNATURES.get(str(variant))
    if expected is None:
        raise ValueError(f"unsupported symmetry variant: {variant}")
    return tuple(bool(value) for value in _symmetry_signature(image)) == tuple(bool(value) for value in expected)


def _rects_intersect(left: Tuple[int, int, int, int], right: Tuple[int, int, int, int], pad: int = 0) -> bool:
    """Return true when two `xywh` rects overlap after applying `pad`."""

    lx, ly, lw, lh = [int(value) for value in left]
    rx, ry, rw, rh = [int(value) for value in right]
    padding = int(max(0, pad))
    return not (
        lx + lw + padding <= rx
        or rx + rw + padding <= lx
        or ly + lh + padding <= ry
        or ry + rh + padding <= ly
    )


def _scale_bounds_for_count(icon_count: int) -> Tuple[float, float]:
    """Return icon-size scale bounds tuned to one cell icon count."""

    if int(icon_count) <= 4:
        return (0.22, 0.38)
    if int(icon_count) <= 6:
        return (0.18, 0.32)
    return (0.14, 0.28)


def _random_position_within_patch(
    rng,
    *,
    width: int,
    height: int,
    sprite_w: int,
    sprite_h: int,
    inner_margin_px: int,
) -> Tuple[int, int] | None:
    """Sample one random top-left position inside a patch."""

    x_min = int(inner_margin_px)
    x_max = int(width - inner_margin_px - sprite_w)
    y_min = int(inner_margin_px)
    y_max = int(height - inner_margin_px - sprite_h)
    if x_min > x_max or y_min > y_max:
        return None
    return int(rng.randint(int(x_min), int(x_max))), int(rng.randint(int(y_min), int(y_max)))


def _sample_symmetric_seed_position(
    rng,
    *,
    width: int,
    height: int,
    sprite_w: int,
    sprite_h: int,
    variant: str,
    inner_margin_px: int,
    min_gap_px: int,
) -> Tuple[int, int] | None:
    """Sample one seed placement whose mirrored pair stays within one patch."""

    margin = int(inner_margin_px)
    gap = int(min_gap_px)
    if str(variant) == "mirror_vertical":
        x_min = int(margin)
        x_max = int((int(width) - (2 * int(sprite_w)) - int(gap)) // 2)
        y_min = int(margin)
        y_max = int(height - margin - sprite_h)
    elif str(variant) == "mirror_horizontal":
        x_min = int(margin)
        x_max = int(width - margin - sprite_w)
        y_min = int(margin)
        y_max = int((int(height) - (2 * int(sprite_h)) - int(gap)) // 2)
    elif str(variant) in {"mirror_diagonal_main", "mirror_diagonal_anti"}:
        for _ in range(32):
            position = _random_position_within_patch(
                rng,
                width=int(width),
                height=int(height),
                sprite_w=int(sprite_w),
                sprite_h=int(sprite_h),
                inner_margin_px=int(inner_margin_px),
            )
            if position is None:
                return None
            x, y = int(position[0]), int(position[1])
            if str(variant) == "mirror_diagonal_main":
                if int(x + sprite_w + gap) <= int(y) or int(y + sprite_h + gap) <= int(x):
                    return int(x), int(y)
            else:
                anti_diagonal = int(width - sprite_w)
                if int(x + y) <= int(anti_diagonal - sprite_w - gap) or int(x + y) >= int(anti_diagonal + gap):
                    return int(x), int(y)
        return None
    else:
        raise ValueError(f"unsupported symmetry variant: {variant}")
    if x_min > x_max or y_min > y_max:
        return None
    return int(rng.randint(int(x_min), int(x_max))), int(rng.randint(int(y_min), int(y_max)))


def _mirrored_rect(rect_xywh: Tuple[int, int, int, int], *, width: int, height: int, variant: str) -> Tuple[int, int, int, int]:
    """Return one mirrored `xywh` rect within a patch."""

    x, y, sprite_w, sprite_h = [int(value) for value in rect_xywh]
    if str(variant) == "mirror_vertical":
        return (int(width - x - sprite_w), int(y), int(sprite_w), int(sprite_h))
    if str(variant) == "mirror_horizontal":
        return (int(x), int(height - y - sprite_h), int(sprite_w), int(sprite_h))
    if str(variant) == "mirror_diagonal_main":
        return (int(y), int(x), int(sprite_h), int(sprite_w))
    if str(variant) == "mirror_diagonal_anti":
        return (
            int(width - y - sprite_h),
            int(height - x - sprite_w),
            int(sprite_h),
            int(sprite_w),
        )
    raise ValueError(f"unsupported symmetry variant: {variant}")


def _flip_both_axes_rect(
    rect_xywh: Tuple[int, int, int, int],
    *,
    width: int,
    height: int,
) -> Tuple[int, int, int, int]:
    """Return one rect reflected across both vertical and horizontal axes."""

    x, y, sprite_w, sprite_h = [int(value) for value in rect_xywh]
    return (
        int(width - x - sprite_w),
        int(height - y - sprite_h),
        int(sprite_w),
        int(sprite_h),
    )


def _sprite_record(
    *,
    icon_id: str,
    tint_rgb: Tuple[int, int, int],
    rotation_degrees: int,
    noise_edits: Sequence[Mapping[str, Any]],
    noise_seed: int | None,
    bbox_xyxy: Sequence[int],
    relation_to_pair: str,
    mirrored_from_index: int | None,
    reflection_applied: str,
) -> Dict[str, Any]:
    """Build one trace-friendly icon-placement record."""

    return {
        "icon_id": str(icon_id),
        "tint_rgb": [int(value) for value in tint_rgb],
        "rotation_degrees": int(rotation_degrees) % 360,
        "noise_edits": [dict(edit) for edit in noise_edits],
        "noise_seed": None if noise_seed is None else int(noise_seed),
        "bbox_xyxy": [int(value) for value in bbox_xyxy],
        "relation_to_pair": str(relation_to_pair),
        "mirrored_from_index": None if mirrored_from_index is None else int(mirrored_from_index),
        "reflection_applied": str(reflection_applied),
    }


def _render_symmetric_patch(
    rng,
    *,
    instance_seed: int,
    namespace: str,
    width: int,
    height: int,
    symmetry_variant: str,
    pool: Sequence[str],
    palette: Sequence[Tuple[int, int, int]],
    rotation_candidates: Sequence[int],
    render_params: Mapping[str, Any],
) -> Tuple[Image.Image, List[Dict[str, Any]], int]:
    """Render one exact single-axis mirror-symmetric patch."""

    choices = [int(value) for value in render_params["symmetric_icon_count_choices"]]
    if not choices:
        raise ValueError("symmetric_icon_count_choices resolved no values")
    final_count = int(rng.choice(choices))
    seed_count = max(1, int(final_count // 2))
    scale_min, scale_max = _scale_bounds_for_count(int(final_count))
    patch_width = int(width)
    patch_height = int(height)
    inner_margin = int(render_params["patch_inner_margin_px"])
    min_gap = int(render_params["patch_min_gap_px"])
    max_attempts = max(1, int(render_params["patch_sampling_attempts"]))

    for _ in range(max_attempts):
        placements: List[Tuple[Tuple[int, int, int, int], Image.Image, Dict[str, Any], Image.Image]] = []
        rects_xywh: List[Tuple[int, int, int, int]] = []
        failed = False
        for seed_index in range(seed_count):
            icon_id = str(rng.choice(pool))
            tint_rgb = tuple(int(value) for value in rng.choice(palette))
            rotation_degrees = int(rng.choice(rotation_candidates))
            target_size = max(
                18,
                int(
                    round(
                        min(float(patch_width), float(patch_height))
                        * float(rng.uniform(float(scale_min), float(scale_max)))
                    )
                ),
            )
            noise_edits, noise_seed = sample_icon_instance_noise(
                instance_seed=int(instance_seed),
                namespace=f"{namespace}:seed_{int(seed_index)}",
                render_params=render_params,
            )
            sprite = render_icon_rgba(
                icon_id=str(icon_id),
                size_px=int(target_size),
                tint_rgb=tuple(int(value) for value in tint_rgb),
                rotation_degrees=int(rotation_degrees),
                mirror_x=False,
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
            sprite_w, sprite_h = sprite.size
            position = _sample_symmetric_seed_position(
                rng,
                width=int(patch_width),
                height=int(patch_height),
                sprite_w=int(sprite_w),
                sprite_h=int(sprite_h),
                variant=str(symmetry_variant),
                inner_margin_px=int(inner_margin),
                min_gap_px=int(min_gap),
            )
            if position is None:
                failed = True
                break
            rect_xywh = (int(position[0]), int(position[1]), int(sprite_w), int(sprite_h))
            mirrored_rect_xywh = _mirrored_rect(
                rect_xywh,
                width=int(patch_width),
                height=int(patch_height),
                variant=str(symmetry_variant),
            )
            if any(_rects_intersect(rect_xywh, other, pad=int(min_gap)) for other in rects_xywh):
                failed = True
                break
            if any(_rects_intersect(mirrored_rect_xywh, other, pad=int(min_gap)) for other in rects_xywh):
                failed = True
                break
            if _rects_intersect(rect_xywh, mirrored_rect_xywh, pad=int(min_gap)):
                failed = True
                break
            rects_xywh.extend((tuple(int(value) for value in rect_xywh), tuple(int(value) for value in mirrored_rect_xywh)))
            placements.append(
                (
                    tuple(int(value) for value in rect_xywh),
                    sprite,
                    {
                        "icon_id": str(icon_id),
                        "tint_rgb": tuple(int(value) for value in tint_rgb),
                        "rotation_degrees": int(rotation_degrees),
                        "noise_edits": [dict(edit) for edit in serialize_icon_noise_edits(tuple(noise_edits))],
                        "noise_seed": int(noise_seed),
                    },
                    _flip_image(sprite, str(symmetry_variant)),
                )
            )
        if failed or len(placements) != int(seed_count):
            continue

        patch = Image.new("RGBA", (int(patch_width), int(patch_height)), (255, 255, 255, 0))
        placement_records: List[Dict[str, Any]] = []
        for pair_index, (rect_xywh, sprite, sprite_meta, mirrored_sprite) in enumerate(placements):
            x, y, sprite_w, sprite_h = [int(value) for value in rect_xywh]
            patch.alpha_composite(sprite, (int(x), int(y)))
            mirrored_rect_xywh = _mirrored_rect(
                rect_xywh,
                width=int(patch_width),
                height=int(patch_height),
                variant=str(symmetry_variant),
            )
            mx, my, mw, mh = [int(value) for value in mirrored_rect_xywh]
            patch.alpha_composite(mirrored_sprite, (int(mx), int(my)))
            placement_records.append(
                _sprite_record(
                    icon_id=str(sprite_meta["icon_id"]),
                    tint_rgb=tuple(int(value) for value in sprite_meta["tint_rgb"]),
                    rotation_degrees=int(sprite_meta["rotation_degrees"]),
                    noise_edits=tuple(sprite_meta["noise_edits"]),
                    noise_seed=int(sprite_meta["noise_seed"]),
                    bbox_xyxy=(int(x), int(y), int(x + sprite_w), int(y + sprite_h)),
                    relation_to_pair="base",
                    mirrored_from_index=None,
                    reflection_applied="none",
                )
            )
            placement_records.append(
                _sprite_record(
                    icon_id=str(sprite_meta["icon_id"]),
                    tint_rgb=tuple(int(value) for value in sprite_meta["tint_rgb"]),
                    rotation_degrees=int(sprite_meta["rotation_degrees"]),
                    noise_edits=tuple(sprite_meta["noise_edits"]),
                    noise_seed=int(sprite_meta["noise_seed"]),
                    bbox_xyxy=(int(mx), int(my), int(mx + mw), int(my + mh)),
                    relation_to_pair="mirrored",
                    mirrored_from_index=int(pair_index),
                    reflection_applied=str(_mirror_axis(str(symmetry_variant))),
                )
            )
        if _is_exact_symmetry_variant(patch, str(symmetry_variant)):
            return patch, placement_records, int(final_count)
    raise ValueError("failed to sample an exact mirror-symmetric patch")


def _render_both_axes_patch(
    rng,
    *,
    instance_seed: int,
    namespace: str,
    width: int,
    height: int,
    pool: Sequence[str],
    palette: Sequence[Tuple[int, int, int]],
    rotation_candidates: Sequence[int],
    render_params: Mapping[str, Any],
) -> Tuple[Image.Image, List[Dict[str, Any]], int]:
    """Render one exact patch that is symmetric across both vertical and horizontal axes."""

    if int(width) != int(height):
        raise ValueError("mirror_both_axes requires a square patch")
    choices = [int(value) for value in render_params["both_axes_icon_count_choices"]]
    if not choices:
        raise ValueError("both_axes_icon_count_choices resolved no values")
    final_count = int(rng.choice(choices))
    if int(final_count) % 4 != 0:
        raise ValueError("both_axes icon counts must be multiples of four")
    orbit_count = max(1, int(final_count // 4))
    scale_min, scale_max = _scale_bounds_for_count(int(final_count))
    patch_width = int(width)
    patch_height = int(height)
    inner_margin = int(render_params["patch_inner_margin_px"])
    min_gap = int(render_params["patch_min_gap_px"])
    max_attempts = max(1, int(render_params["patch_sampling_attempts"]))

    for _ in range(max_attempts):
        patch = Image.new("RGBA", (int(patch_width), int(patch_height)), (255, 255, 255, 0))
        rects_xywh: List[Tuple[int, int, int, int]] = []
        placement_records: List[Dict[str, Any]] = []
        failed = False
        for orbit_index in range(int(orbit_count)):
            icon_id = str(rng.choice(pool))
            tint_rgb = tuple(int(value) for value in rng.choice(palette))
            rotation_degrees = int(rng.choice(rotation_candidates))
            target_size = max(
                18,
                int(
                    round(
                        min(float(patch_width), float(patch_height))
                        * float(rng.uniform(float(scale_min), float(scale_max)))
                    )
                ),
            )
            noise_edits, noise_seed = sample_icon_instance_noise(
                instance_seed=int(instance_seed),
                namespace=f"{namespace}:orbit_{int(orbit_index)}",
                render_params=render_params,
            )
            sprite = render_icon_rgba(
                icon_id=str(icon_id),
                size_px=int(target_size),
                tint_rgb=tuple(int(value) for value in tint_rgb),
                rotation_degrees=int(rotation_degrees),
                mirror_x=False,
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
            sprite_w, sprite_h = sprite.size
            position = _random_position_within_patch(
                rng,
                width=int(patch_width),
                height=int(patch_height),
                sprite_w=int(sprite_w),
                sprite_h=int(sprite_h),
                inner_margin_px=int(inner_margin),
            )
            if position is None:
                failed = True
                break
            base_rect = (int(position[0]), int(position[1]), int(sprite_w), int(sprite_h))
            orbit_rects = [
                base_rect,
                _mirrored_rect(base_rect, width=int(patch_width), height=int(patch_height), variant="mirror_vertical"),
                _mirrored_rect(base_rect, width=int(patch_width), height=int(patch_height), variant="mirror_horizontal"),
                _flip_both_axes_rect(base_rect, width=int(patch_width), height=int(patch_height)),
            ]
            if len({tuple(int(value) for value in rect) for rect in orbit_rects}) != 4:
                failed = True
                break
            if any(
                _rects_intersect(rect, other, pad=int(min_gap))
                for rect in orbit_rects
                for other in rects_xywh
            ):
                failed = True
                break
            for left_index, left_rect in enumerate(orbit_rects):
                for right_rect in orbit_rects[int(left_index) + 1 :]:
                    if _rects_intersect(left_rect, right_rect, pad=int(min_gap)):
                        failed = True
                        break
                if failed:
                    break
            if failed:
                break

            sprite_variants = [
                (sprite, "base", None, "none"),
                (_flip_image(sprite, "mirror_vertical"), "mirrored", int(len(placement_records)), "horizontal_flip"),
                (_flip_image(sprite, "mirror_horizontal"), "mirrored", int(len(placement_records)), "vertical_flip"),
                (_flip_image(sprite, "mirror_both_axes"), "mirrored", int(len(placement_records)), "both_axes_flip"),
            ]
            rects_xywh.extend(tuple(int(value) for value in rect) for rect in orbit_rects)
            for rect_xywh, (variant_sprite, relation_to_pair, mirrored_from_index, reflection_applied) in zip(
                orbit_rects,
                sprite_variants,
            ):
                x, y, rect_w, rect_h = [int(value) for value in rect_xywh]
                patch.alpha_composite(variant_sprite, (int(x), int(y)))
                placement_records.append(
                    _sprite_record(
                        icon_id=str(icon_id),
                        tint_rgb=tuple(int(value) for value in tint_rgb),
                        rotation_degrees=int(rotation_degrees),
                        noise_edits=tuple(dict(edit) for edit in serialize_icon_noise_edits(tuple(noise_edits))),
                        noise_seed=int(noise_seed),
                        bbox_xyxy=(int(x), int(y), int(x + rect_w), int(y + rect_h)),
                        relation_to_pair=str(relation_to_pair),
                        mirrored_from_index=int(mirrored_from_index) if mirrored_from_index is not None else None,
                        reflection_applied=str(reflection_applied),
                    )
                )
        if failed or len(placement_records) != int(final_count):
            continue
        if _is_exact_symmetry_variant(patch, "mirror_both_axes"):
            return patch, placement_records, int(final_count)
    raise ValueError("failed to sample an exact both-axes-symmetric patch")


def _render_nonsymmetric_patch(
    rng,
    *,
    instance_seed: int,
    namespace: str,
    width: int,
    height: int,
    pool: Sequence[str],
    palette: Sequence[Tuple[int, int, int]],
    rotation_candidates: Sequence[int],
    render_params: Mapping[str, Any],
) -> Tuple[Image.Image, List[Dict[str, Any]], int]:
    """Render one patch with none of the supported mirror symmetries."""

    choices = [int(value) for value in render_params["nonsymmetric_icon_count_choices"]]
    if not choices:
        raise ValueError("nonsymmetric_icon_count_choices resolved no values")
    icon_count = int(rng.choice(choices))
    scale_min, scale_max = _scale_bounds_for_count(int(icon_count))
    patch_width = int(width)
    patch_height = int(height)
    inner_margin = int(render_params["patch_inner_margin_px"])
    min_gap = int(render_params["patch_min_gap_px"])
    max_attempts = max(1, int(render_params["patch_sampling_attempts"]))

    for _ in range(max_attempts):
        patch = Image.new("RGBA", (int(patch_width), int(patch_height)), (255, 255, 255, 0))
        rects_xywh: List[Tuple[int, int, int, int]] = []
        placement_records: List[Dict[str, Any]] = []
        failed = False
        for icon_index in range(int(icon_count)):
            icon_id = str(rng.choice(pool))
            tint_rgb = tuple(int(value) for value in rng.choice(palette))
            rotation_degrees = int(rng.choice(rotation_candidates))
            target_size = max(
                18,
                int(
                    round(
                        min(float(patch_width), float(patch_height))
                        * float(rng.uniform(float(scale_min), float(scale_max)))
                    )
                ),
            )
            noise_edits, noise_seed = sample_icon_instance_noise(
                instance_seed=int(instance_seed),
                namespace=f"{namespace}:icon_{int(icon_index)}",
                render_params=render_params,
            )
            sprite = render_icon_rgba(
                icon_id=str(icon_id),
                size_px=int(target_size),
                tint_rgb=tuple(int(value) for value in tint_rgb),
                rotation_degrees=int(rotation_degrees),
                mirror_x=False,
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
            position = _random_position_within_patch(
                rng,
                width=int(patch_width),
                height=int(patch_height),
                sprite_w=int(sprite.size[0]),
                sprite_h=int(sprite.size[1]),
                inner_margin_px=int(inner_margin),
            )
            if position is None:
                failed = True
                break
            rect_xywh = (int(position[0]), int(position[1]), int(sprite.size[0]), int(sprite.size[1]))
            if any(_rects_intersect(rect_xywh, other, pad=int(min_gap)) for other in rects_xywh):
                failed = True
                break
            rects_xywh.append(tuple(int(value) for value in rect_xywh))
            x, y, sprite_w, sprite_h = rect_xywh
            patch.alpha_composite(sprite, (int(x), int(y)))
            placement_records.append(
                _sprite_record(
                    icon_id=str(icon_id),
                    tint_rgb=tuple(int(value) for value in tint_rgb),
                    rotation_degrees=int(rotation_degrees),
                    noise_edits=tuple(dict(edit) for edit in serialize_icon_noise_edits(tuple(noise_edits))),
                    noise_seed=int(noise_seed),
                    bbox_xyxy=(int(x), int(y), int(x + sprite_w), int(y + sprite_h)),
                    relation_to_pair="single",
                    mirrored_from_index=None,
                    reflection_applied="none",
                )
            )
        if failed or len(placement_records) != int(icon_count):
            continue
        if tuple(bool(value) for value in _symmetry_signature(patch)) == (False, False, False, False):
            return patch, placement_records, int(icon_count)
    raise ValueError("failed to sample a non-symmetric patch")


def _offset_patch_records(
    placements: Sequence[Mapping[str, Any]],
    *,
    offset_x: int,
    offset_y: int,
) -> List[Dict[str, Any]]:
    """Offset patch-local `bbox_xyxy` records into final image coordinates."""

    projected: List[Dict[str, Any]] = []
    for record in placements:
        bbox = record["bbox_xyxy"]
        projected.append(
            {
                **dict(record),
                "bbox_xyxy": [
                    int(bbox[0]) + int(offset_x),
                    int(bbox[1]) + int(offset_y),
                    int(bbox[2]) + int(offset_x),
                    int(bbox[3]) + int(offset_y),
                ],
            }
        )
    return projected


def _mirror_style_trace(
    *,
    render_params: Mapping[str, Any],
    sampled_palette_rgb: Sequence[Tuple[int, int, int]],
) -> Dict[str, Any]:
    """Return the canonical render-style trace block for mirror-symmetry grids."""

    return {
        "background_color_rgb": list(render_params["background_color_rgb"]),
        "panel_fill_rgb": list(render_params["panel_fill_rgb"]),
        "panel_border_rgb": list(render_params["panel_border_rgb"]),
        "header_text_rgb": list(render_params["header_text_rgb"]),
        "sampled_palette_rgb": [list(color) for color in sampled_palette_rgb],
        "color_channel_min": int(render_params["color_channel_min"]),
        "color_channel_max": int(render_params["color_channel_max"]),
        "min_color_distance": float(render_params["min_color_distance"]),
        "color_distance_space": str(render_params["color_distance_space"]),
        "rotation_candidates_degrees": [int(value) for value in render_params["rotation_candidates_degrees"]],
        "symmetric_icon_count_choices": [int(value) for value in render_params["symmetric_icon_count_choices"]],
        "both_axes_icon_count_choices": [int(value) for value in render_params["both_axes_icon_count_choices"]],
        "nonsymmetric_icon_count_choices": [int(value) for value in render_params["nonsymmetric_icon_count_choices"]],
        "patch_inner_margin_px": int(render_params["patch_inner_margin_px"]),
        "patch_min_gap_px": int(render_params["patch_min_gap_px"]),
        "patch_sampling_attempts": int(render_params["patch_sampling_attempts"]),
        "cell_padding_px": int(render_params["cell_padding_px"]),
        "cell_border_rgb": list(render_params["cell_border_rgb"]),
        "cell_label_color_rgb": list(render_params["cell_label_color_rgb"]),
        "cell_label_font_size_px": int(render_params["cell_label_font_size_px"]),
        "icon_noise_edit_types": [str(value) for value in render_params["icon_noise_edit_types"]],
        "icon_noise_edit_count_range": [
            int(render_params["icon_noise_edit_count_range"][0]),
            int(render_params["icon_noise_edit_count_range"][1]),
        ],
        "icon_noise_value_ranges": {
            str(edit_type): {
                str(param): [float(bounds[0]), float(bounds[1])]
                for param, bounds in params.items()
            }
            for edit_type, params in render_params["icon_noise_value_ranges"].items()
        },
    }


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    query_variant: str,
    object_count: int,
    target_count: int,
    render_params: Mapping[str, Any],
    pool_manifest: str,
) -> Tuple[_ScenePayload, Image.Image]:
    """Sample and render one mirror-symmetry relation scene."""

    pool = tuple(str(icon_id) for icon_id in resolve_icon_pool(str(pool_manifest)))
    if not pool:
        raise ValueError("mirror symmetry task resolved an empty icon pool")

    palette_size = int(rng.randint(int(render_params["palette_size_min"]), int(render_params["palette_size_max"])))
    sampled_palette_rgb = tuple(
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
        palette=sampled_palette_rgb,
        anchor_colors=(
            tuple(int(v) for v in render_params["background_color_rgb"]),
            tuple(int(v) for v in render_params["panel_fill_rgb"]),
            tuple(int(v) for v in render_params["panel_border_rgb"]),
            tuple(int(v) for v in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    ):
        raise ValueError("sampled mirror-symmetry palette did not satisfy strict distance constraints")

    labels = assign_shuffled_labels(rng, object_count=int(object_count), label_pool=LABEL_POOL_A_L)
    match_indices = set(rng.sample(list(range(int(object_count))), int(target_count)))
    other_symmetries = [str(value) for value in _SYMMETRY_VARIANTS if str(value) != str(query_variant)]
    distractor_variants: List[str] = []
    distractor_count = int(object_count) - int(target_count)
    if int(distractor_count) >= 1:
        distractor_variants.append(str(rng.choice(other_symmetries)))
    if int(distractor_count) >= 2:
        distractor_variants.append("none")
    while len(distractor_variants) < int(distractor_count):
        distractor_variants.append(str(rng.choice(tuple(other_symmetries) + ("none",))))
    rng.shuffle(distractor_variants)

    prepared = prepare_two_panel_labeled_grid_scene(
        scene_labels=labels,
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        reference_panel_width_px=int(render_params["reference_panel_width_px"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_gap_px=int(render_params["panel_gap_px"]),
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
        cell_label_font_size_px=int(render_params["cell_label_font_size_px"]),
        reference_square_cell=True,
        scene_square_cells=True,
    )
    image = prepared.image

    ref_content_bbox = tuple(int(value) for value in prepared.reference_cell.content_bbox_xyxy)
    ref_width = int(ref_content_bbox[2] - ref_content_bbox[0])
    ref_height = int(ref_content_bbox[3] - ref_content_bbox[1])
    if str(query_variant) == "mirror_both_axes":
        reference_patch, reference_placements, reference_icon_count = _render_both_axes_patch(
            rng,
            instance_seed=int(instance_seed),
            namespace=f"{IconsRelationMirrorSymmetryTask.task_id}:{query_variant}:reference",
            width=int(ref_width),
            height=int(ref_height),
            pool=pool,
            palette=sampled_palette_rgb,
            rotation_candidates=render_params["rotation_candidates_degrees"],
            render_params=render_params,
        )
    else:
        reference_patch, reference_placements, reference_icon_count = _render_symmetric_patch(
            rng,
            instance_seed=int(instance_seed),
            namespace=f"{IconsRelationMirrorSymmetryTask.task_id}:{query_variant}:reference",
            width=int(ref_width),
            height=int(ref_height),
            symmetry_variant=str(query_variant),
            pool=pool,
            palette=sampled_palette_rgb,
            rotation_candidates=render_params["rotation_candidates_degrees"],
            render_params=render_params,
        )
    image.alpha_composite(reference_patch, (int(ref_content_bbox[0]), int(ref_content_bbox[1])))
    reference_signature = _symmetry_signature(reference_patch)
    reference_payload = {
        "panel": "reference",
        "symmetry_id": str(query_variant),
        "cell_bbox_xyxy": list(prepared.reference_cell.cell_bbox_xyxy),
        "content_bbox_xyxy": list(prepared.reference_cell.content_bbox_xyxy),
        "icon_count": int(reference_icon_count),
        "has_vertical_symmetry": bool(reference_signature[0]),
        "has_horizontal_symmetry": bool(reference_signature[1]),
        "has_diagonal_main_symmetry": bool(reference_signature[2]),
        "has_diagonal_anti_symmetry": bool(reference_signature[3]),
        "placements": _offset_patch_records(
            reference_placements,
            offset_x=int(ref_content_bbox[0]),
            offset_y=int(ref_content_bbox[1]),
        ),
    }

    matching_labels: List[str] = []
    scene_cell_symmetry_ids: List[str] = []
    scene_cells: List[Dict[str, Any]] = []
    distractor_cursor = 0
    for index, prepared_cell in enumerate(prepared.scene_cells):
        if int(index) in match_indices:
            cell_variant = str(query_variant)
            is_match = True
            matching_labels.append(str(prepared_cell.label))
        else:
            cell_variant = str(distractor_variants[int(distractor_cursor)])
            distractor_cursor += 1
            is_match = False

        content_bbox = tuple(int(value) for value in prepared_cell.content_bbox_xyxy)
        patch_width = int(content_bbox[2] - content_bbox[0])
        patch_height = int(content_bbox[3] - content_bbox[1])
        if str(cell_variant) == "mirror_both_axes":
            patch, placements, icon_count = _render_both_axes_patch(
                rng,
                instance_seed=int(instance_seed),
                namespace=f"{IconsRelationMirrorSymmetryTask.task_id}:{query_variant}:scene_{int(index)}",
                width=int(patch_width),
                height=int(patch_height),
                pool=pool,
                palette=sampled_palette_rgb,
                rotation_candidates=render_params["rotation_candidates_degrees"],
                render_params=render_params,
            )
        elif str(cell_variant) in set(_SYMMETRY_VARIANTS):
            patch, placements, icon_count = _render_symmetric_patch(
                rng,
                instance_seed=int(instance_seed),
                namespace=f"{IconsRelationMirrorSymmetryTask.task_id}:{query_variant}:scene_{int(index)}",
                width=int(patch_width),
                height=int(patch_height),
                symmetry_variant=str(cell_variant),
                pool=pool,
                palette=sampled_palette_rgb,
                rotation_candidates=render_params["rotation_candidates_degrees"],
                render_params=render_params,
            )
        else:
            patch, placements, icon_count = _render_nonsymmetric_patch(
                rng,
                instance_seed=int(instance_seed),
                namespace=f"{IconsRelationMirrorSymmetryTask.task_id}:{query_variant}:scene_{int(index)}",
                width=int(patch_width),
                height=int(patch_height),
                pool=pool,
                palette=sampled_palette_rgb,
                rotation_candidates=render_params["rotation_candidates_degrees"],
                render_params=render_params,
            )
        image.alpha_composite(patch, (int(content_bbox[0]), int(content_bbox[1])))
        cell_signature = _symmetry_signature(patch)
        scene_cells.append(
            {
                "panel": "scene",
                "label": str(prepared_cell.label),
                "cell_bbox_xyxy": list(prepared_cell.cell_bbox_xyxy),
                "content_bbox_xyxy": list(prepared_cell.content_bbox_xyxy),
                "symmetry_id": str(cell_variant),
                "icon_count": int(icon_count),
                "has_vertical_symmetry": bool(cell_signature[0]),
                "has_horizontal_symmetry": bool(cell_signature[1]),
                "has_diagonal_main_symmetry": bool(cell_signature[2]),
                "has_diagonal_anti_symmetry": bool(cell_signature[3]),
                "is_match": bool(is_match),
                "placements": _offset_patch_records(
                    placements,
                    offset_x=int(content_bbox[0]),
                    offset_y=int(content_bbox[1]),
                ),
            }
        )
        scene_cell_symmetry_ids.append(str(cell_variant))

    return _ScenePayload(
        object_count=int(object_count),
        target_count=int(target_count),
        distractor_count=int(distractor_count),
        query_variant=str(query_variant),
        cell_labels=tuple(str(value) for value in labels),
        matching_labels=tuple(sorted(str(value) for value in matching_labels)),
        scene_cell_symmetry_ids=tuple(str(value) for value in scene_cell_symmetry_ids),
        sampled_palette_rgb=tuple(sampled_palette_rgb),
        panel_geometry=panel_geometry_to_trace(prepared.layout),
        reference_cell=dict(reference_payload),
        scene_cells=tuple(dict(item) for item in scene_cells),
    ), image.convert("RGB")


@register_task
class IconsRelationMirrorSymmetryTask:
    """Count labeled Scene cells whose mirror symmetry matches the Reference."""

    task_id = "task_icons__mirror_grid__mirror_symmetry_count"
    domain = "icons"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic mirror-symmetry relation instance."""

        scene_rng = spawn_rng(int(instance_seed), "scene")
        selected_signature, signature_probabilities = _resolve_mirror_signature(
            scene_rng,
            params=params,
            instance_seed=int(instance_seed),
        )
        cardinality_params = dict(params)
        (
            object_count,
            object_count_probabilities,
            target_count,
            target_count_probabilities,
            distractor_count,
            distractor_count_probabilities,
        ) = _resolve_fixed_grid_cardinalities(
            scene_rng,
            instance_seed=int(instance_seed),
            params=cardinality_params,
        )
        render_params = _resolve_render_params(params, instance_seed=int(instance_seed))
        pool_manifest = str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = _sample_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    query_variant=str(selected_signature),
                    object_count=int(object_count),
                    target_count=int(target_count),
                    render_params=render_params,
                    pool_manifest=str(pool_manifest),
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError("failed to generate task_icons__mirror_grid__mirror_symmetry_count instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_labels = list(scene_payload.matching_labels)
        evidence_artifacts = matching_scene_cell_bbox_evidence(
            scene_cells=scene_payload.scene_cells,
            matching_labels=evidence_labels,
        )
        answer_gt = TypedValue(type="integer", value=int(scene_payload.target_count))
        evidence_gt = TypedValue(
            type=str(evidence_artifacts["evidence_type"]),
            value=list(evidence_artifacts["evidence_value"]),
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_reference_grid_mirror_symmetry_count",
                "entities": [dict(scene_payload.reference_cell), *[dict(item) for item in scene_payload.scene_cells]],
                "relations": {
                    "counting_target": "same_mirror_symmetry_as_reference",
                    "query_variant": str(_PUBLIC_QUERY_VARIANT),
                    "reference_symmetry_id": str(scene_payload.query_variant),
                    "mirror_signature": str(scene_payload.query_variant),
                    "matching_cell_labels": list(scene_payload.matching_labels),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "query_variant": str(_PUBLIC_QUERY_VARIANT),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "object_count": int(object_count),
                    "object_count_probabilities": dict(object_count_probabilities),
                    "target_count": int(target_count),
                    "target_count_probabilities": dict(target_count_probabilities),
                    "distractor_count": int(distractor_count),
                    "distractor_count_probabilities": dict(distractor_count_probabilities),
                    "pool_manifest": str(pool_manifest),
                    "mirror_signature": str(scene_payload.query_variant),
                    "mirror_signature_probabilities": dict(signature_probabilities),
                    "internal_query_variant": str(scene_payload.query_variant),
                },
            },
            "render_spec": {
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": _mirror_style_trace(
                    render_params=render_params,
                    sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                ),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "reference_cell": dict(scene_payload.reference_cell),
                    "matching_cell_labels": list(scene_payload.matching_labels),
                    "scene_cells": [dict(item) for item in scene_payload.scene_cells],
                },
            },
            "execution_trace": {
                "scene_variant": "reference_grid",
                "query_variant": str(_PUBLIC_QUERY_VARIANT),
                "internal_query_variant": str(scene_payload.query_variant),
                "mirror_signature": str(scene_payload.query_variant),
                "object_count": int(scene_payload.object_count),
                "object_count_probabilities": dict(object_count_probabilities),
                "target_count": int(scene_payload.target_count),
                "target_count_probabilities": dict(target_count_probabilities),
                "distractor_count": int(scene_payload.distractor_count),
                "distractor_count_probabilities": dict(distractor_count_probabilities),
                "cell_labels": list(scene_payload.cell_labels),
                "matching_cell_labels": list(scene_payload.matching_labels),
                "scene_cell_symmetry_ids": list(scene_payload.scene_cell_symmetry_ids),
                "question_format": "count_scene_cells_matching_reference_mirror_symmetry",
                "mirror_signature_probabilities": dict(signature_probabilities),
            },
            "witness_symbolic": {
                "query_variant": str(_PUBLIC_QUERY_VARIANT),
                "reference_symmetry_id": str(scene_payload.query_variant),
                "mirror_signature": str(scene_payload.query_variant),
                **dict(evidence_artifacts["witness_symbolic"]),
            },
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }
        complexity = build_icons_relation_mirror_symmetry_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            query_variant=str(scene_payload.query_variant),
            object_count=int(scene_payload.object_count),
            target_count=int(scene_payload.target_count),
            scene_cells=scene_payload.scene_cells,
            render_params=render_params,
        )
        output = TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant=str(_PUBLIC_QUERY_VARIANT),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
        return rewrite_icons_query_output(
            output,
            query_id=str(scene_payload.query_variant),
            scene_id="mirror_grid",
            query_probabilities=signature_probabilities,
        )


__all__ = ["IconsRelationMirrorSymmetryTask"]
