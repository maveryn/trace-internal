"""Select the Scene cell that is a requested reflection of the Reference cell."""

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
from ...shared.labeling import LABEL_POOL_A_L
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import build_icons_relation_mirror_symmetry_complexity
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.evidence import matching_scene_cell_bbox_evidence
from ..shared.icon_assets import render_icon_rgba, resolve_icon_pool
from ..shared.icon_labeled_grid_scene import prepare_two_panel_labeled_grid_scene
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import panel_geometry_to_trace
from ..shared.icon_style import icon_palette_meets_distance_constraints, sample_icon_palette
from ..shared.icon_task_rendering import resolve_icon_render_params, resolve_icon_rgb_param, sample_icon_instance_noise
from ..shared.public_query_task import rewrite_icons_query_output
from .mirror_symmetry import (
    _flip_image,
    _mirror_axis,
    _mirror_style_trace,
    _mirrored_rect,
    _offset_patch_records,
    _random_position_within_patch,
    _render_nonsymmetric_patch,
    _symmetry_signature,
)


_REFLECTION_QUERY_IDS: Tuple[str, ...] = (
    "vertical_reflection_match",
    "horizontal_reflection_match",
    "diagonal_main_reflection_match",
    "diagonal_anti_reflection_match",
)
_AXIS_BY_QUERY_ID: Dict[str, str] = {
    "vertical_reflection_match": "mirror_vertical",
    "horizontal_reflection_match": "mirror_horizontal",
    "diagonal_main_reflection_match": "mirror_diagonal_main",
    "diagonal_anti_reflection_match": "mirror_diagonal_anti",
}
_PUBLIC_QUERY_VARIANT = "reflection_match_label"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for reflection-match option grids."""

    object_count_min: int = 6
    object_count_max: int = 6
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
    nonsymmetric_icon_count_choices: Tuple[int, ...] = (3, 4, 5)
    wrong_axis_distractor_count: int = 3
    patch_inner_margin_px: int = 8
    patch_min_gap_px: int = 6
    patch_sampling_attempts: int = 180
    shuffle_scene_labels: bool = False


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one reflection-match option grid."""

    object_count: int
    query_id: str
    reflection_axis: str
    cell_labels: Tuple[str, ...]
    answer_label: str
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    reference_cell: Dict[str, Any]
    scene_cells: Tuple[Dict[str, Any], ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_icons__mirror_grid__reflection_match_label",
)


def _patch_equal(left: Image.Image, right: Image.Image) -> bool:
    """Return true when two RGBA patches are pixel-identical."""

    if left.size != right.size:
        return False
    return ImageChops.difference(left, right).getbbox() is None


def _alpha_mask(image: Image.Image) -> Image.Image:
    """Return a binary alpha mask for one RGBA patch."""

    return image.getchannel("A").point(lambda value: 255 if int(value) > 0 else 0)


def _patches_overlap(left: Image.Image, right: Image.Image) -> bool:
    """Return true when two RGBA patches have any nontransparent pixel overlap."""

    return ImageChops.multiply(_alpha_mask(left), _alpha_mask(right)).getbbox() is not None


def _patch_key(image: Image.Image) -> bytes:
    """Return a stable key for exact patch deduplication."""

    return image.convert("RGBA").tobytes()


def _resolve_reflection_query(scene_rng, *, params: Mapping[str, Any], instance_seed: int) -> Tuple[str, Dict[str, float]]:
    """Resolve the sampled reflection query id."""

    query_params = dict(params)
    explicit_variant = str(query_params.get("query_variant", "") or "").strip()
    if query_params.get("reflection_query") is None and explicit_variant in set(_REFLECTION_QUERY_IDS):
        query_params["reflection_query"] = explicit_variant
    if explicit_variant == str(_PUBLIC_QUERY_VARIANT):
        query_params.pop("query_variant", None)
    selected_query, query_probabilities = resolve_variant(
        scene_rng,
        params=query_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=_REFLECTION_QUERY_IDS,
        explicit_key="reflection_query",
        weights_key="reflection_query_weights",
    )
    selected_query = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=query_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected_query),
        variant_probabilities=dict(query_probabilities),
        supported_variants=_REFLECTION_QUERY_IDS,
        balance_flag_key="balanced_variant_sampling",
        explicit_key="reflection_query",
        weights_key="reflection_query_weights",
    )
    return str(selected_query), dict(query_probabilities)


def _resolve_rotation_candidates(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Resolve supported icon rotations for reflection cells."""

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
    """Resolve render params, including grid-cell extras."""

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
    render_params["wrong_axis_distractor_count"] = int(
        params.get(
            "wrong_axis_distractor_count",
            group_default(_RENDER_DEFAULTS, "wrong_axis_distractor_count", _DEFAULTS.wrong_axis_distractor_count),
        )
    )
    return render_params


def _reflect_patch_records(
    placements: Sequence[Mapping[str, Any]],
    *,
    width: int,
    height: int,
    axis: str,
) -> List[Dict[str, Any]]:
    """Reflect patch-local placement metadata across one axis."""

    reflected: List[Dict[str, Any]] = []
    for index, record in enumerate(placements):
        bbox = tuple(int(value) for value in record.get("bbox_xyxy", (0, 0, 0, 0)))
        rect_xywh = (bbox[0], bbox[1], max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1]))
        mirrored = _mirrored_rect(rect_xywh, width=int(width), height=int(height), variant=str(axis))
        mx, my, mw, mh = [int(value) for value in mirrored]
        reflected.append(
            {
                **dict(record),
                "bbox_xyxy": [int(mx), int(my), int(mx + mw), int(my + mh)],
                "relation_to_reference": "requested_reflection",
                "mirrored_from_index": int(index),
                "reflection_applied": str(_mirror_axis(str(axis))),
            }
        )
    return reflected


def _render_extra_icon_patch(
    rng,
    *,
    instance_seed: int,
    namespace: str,
    base_patch: Image.Image,
    pool: Sequence[str],
    palette: Sequence[Tuple[int, int, int]],
    rotation_candidates: Sequence[int],
    render_params: Mapping[str, Any],
) -> Tuple[Image.Image, List[Dict[str, Any]], int] | None:
    """Return a copy of `base_patch` with one extra unmatched icon."""

    patch_width, patch_height = [int(value) for value in base_patch.size]
    inner_margin = int(render_params["patch_inner_margin_px"])
    max_attempts = max(1, int(render_params["patch_sampling_attempts"]))
    for attempt in range(max_attempts):
        icon_id = str(rng.choice(pool))
        tint_rgb = tuple(int(value) for value in rng.choice(palette))
        rotation_degrees = int(rng.choice(rotation_candidates))
        target_size = max(16, int(round(min(float(patch_width), float(patch_height)) * float(rng.uniform(0.14, 0.24)))))
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{namespace}:extra_{int(attempt)}",
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
            continue
        extra_patch = Image.new("RGBA", (int(patch_width), int(patch_height)), (255, 255, 255, 0))
        x, y = int(position[0]), int(position[1])
        extra_patch.alpha_composite(sprite, (int(x), int(y)))
        if _patches_overlap(base_patch, extra_patch):
            continue
        altered = base_patch.copy()
        altered.alpha_composite(extra_patch)
        record = {
            "icon_id": str(icon_id),
            "tint_rgb": [int(value) for value in tint_rgb],
            "rotation_degrees": int(rotation_degrees) % 360,
            "noise_edits": [dict(edit) for edit in serialize_icon_noise_edits(tuple(noise_edits))],
            "noise_seed": int(noise_seed),
            "bbox_xyxy": [int(x), int(y), int(x + sprite.size[0]), int(y + sprite.size[1])],
            "relation_to_reference": "extra_unmatched_icon",
            "mirrored_from_index": None,
            "reflection_applied": "none",
        }
        return altered, [record], 1
    return None


def _center_origin(container_bbox: Sequence[int | float], *, patch_size: int) -> Tuple[int, int]:
    """Return a top-left origin that centers a square patch in one bbox."""

    x0, y0, x1, y1 = [int(round(float(value))) for value in container_bbox]
    return (
        int(x0 + max(0, (int(x1 - x0) - int(patch_size)) // 2)),
        int(y0 + max(0, (int(y1 - y0) - int(patch_size)) // 2)),
    )


def _resolve_correct_index(*, params: Mapping[str, Any], rng, object_count: int, instance_seed: int) -> int:
    """Resolve the unique correct option index."""

    if params.get("answer_index") is not None:
        index = int(params["answer_index"])
        if not 0 <= int(index) < int(object_count):
            raise ValueError("answer_index out of range")
        return int(index)
    _ = instance_seed
    return int(rng.randrange(int(object_count)))


def _resolve_cell_labels(
    rng,
    *,
    params: Mapping[str, Any],
    object_count: int,
    correct_index: int,
) -> Tuple[str, ...]:
    """Resolve option labels while keeping answer labels balanced for calibration exports."""

    labels = [str(value) for value in LABEL_POOL_A_L[: int(object_count)]]
    if len(labels) < int(object_count):
        raise ValueError("not enough option labels for reflection-match scene")

    if params.get("answer_label") is not None:
        answer_label = str(params["answer_label"]).strip().upper()
        if answer_label not in labels:
            raise ValueError("answer_label is not supported for the sampled option count")
    else:
        answer_label = str(labels[int(correct_index)])

    shuffle_scene_labels = bool(
        params.get(
            "shuffle_scene_labels",
            group_default(_GEN_DEFAULTS, "shuffle_scene_labels", _DEFAULTS.shuffle_scene_labels),
        )
    )
    if not bool(shuffle_scene_labels):
        fixed = list(labels)
        current_index = fixed.index(str(answer_label))
        fixed[int(current_index)], fixed[int(correct_index)] = fixed[int(correct_index)], fixed[int(current_index)]
        return tuple(str(value) for value in fixed)

    other_labels = [str(label) for label in labels if str(label) != str(answer_label)]
    rng.shuffle(other_labels)
    resolved = []
    other_cursor = 0
    for index in range(int(object_count)):
        if int(index) == int(correct_index):
            resolved.append(str(answer_label))
        else:
            resolved.append(str(other_labels[int(other_cursor)]))
            other_cursor += 1
    return tuple(str(value) for value in resolved)


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    query_id: str,
    render_params: Mapping[str, Any],
    pool_manifest: str,
    params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Image.Image]:
    """Sample and render one reflection-match option scene."""

    reflection_axis = str(_AXIS_BY_QUERY_ID[str(query_id)])
    object_count = int(params.get("object_count", group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max)))
    object_count = max(4, int(object_count))
    pool = tuple(str(icon_id) for icon_id in resolve_icon_pool(str(pool_manifest)))
    if not pool:
        raise ValueError("reflection-match task resolved an empty icon pool")

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
        raise ValueError("sampled reflection-match palette did not satisfy strict distance constraints")

    correct_index = _resolve_correct_index(params=params, rng=rng, object_count=int(object_count), instance_seed=int(instance_seed))
    labels = _resolve_cell_labels(rng, params=params, object_count=int(object_count), correct_index=int(correct_index))
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
    ref_content = tuple(int(value) for value in prepared.reference_cell.content_bbox_xyxy)
    scene_content_boxes = [tuple(int(value) for value in cell.content_bbox_xyxy) for cell in prepared.scene_cells]
    patch_size = min(
        int(ref_content[2] - ref_content[0]),
        int(ref_content[3] - ref_content[1]),
        *[int(bbox[2] - bbox[0]) for bbox in scene_content_boxes],
        *[int(bbox[3] - bbox[1]) for bbox in scene_content_boxes],
    )
    if int(patch_size) <= 0:
        raise ValueError("reflection-match scene resolved an empty patch size")

    reference_patch, reference_records, reference_icon_count = _render_nonsymmetric_patch(
        rng,
        instance_seed=int(instance_seed),
        namespace=f"{IconsRelationReflectionMatchLabelTask.task_id}:{query_id}:reference",
        width=int(patch_size),
        height=int(patch_size),
        pool=pool,
        palette=sampled_palette_rgb,
        rotation_candidates=render_params["rotation_candidates_degrees"],
        render_params=render_params,
    )
    correct_patch = _flip_image(reference_patch, str(reflection_axis))
    correct_records = _reflect_patch_records(
        reference_records,
        width=int(patch_size),
        height=int(patch_size),
        axis=str(reflection_axis),
    )
    reference_signature = _symmetry_signature(reference_patch)
    ref_origin = _center_origin(ref_content, patch_size=int(patch_size))
    image.alpha_composite(reference_patch, ref_origin)
    reference_payload = {
        "panel": "reference",
        "query_id": str(query_id),
        "reflection_axis": str(reflection_axis),
        "cell_bbox_xyxy": list(prepared.reference_cell.cell_bbox_xyxy),
        "content_bbox_xyxy": list(prepared.reference_cell.content_bbox_xyxy),
        "patch_bbox_xyxy": [
            int(ref_origin[0]),
            int(ref_origin[1]),
            int(ref_origin[0] + patch_size),
            int(ref_origin[1] + patch_size),
        ],
        "icon_count": int(reference_icon_count),
        "has_vertical_symmetry": bool(reference_signature[0]),
        "has_horizontal_symmetry": bool(reference_signature[1]),
        "has_diagonal_main_symmetry": bool(reference_signature[2]),
        "has_diagonal_anti_symmetry": bool(reference_signature[3]),
        "placements": _offset_patch_records(
            reference_records,
            offset_x=int(ref_origin[0]),
            offset_y=int(ref_origin[1]),
        ),
    }

    candidate_pool: List[Tuple[str, Image.Image, List[Dict[str, Any]], int]] = []
    wrong_axes = [axis for axis in _AXIS_BY_QUERY_ID.values() if axis != str(reflection_axis)]
    rng.shuffle(wrong_axes)
    wrong_axis_count = max(0, min(len(wrong_axes), int(render_params["wrong_axis_distractor_count"])))
    for wrong_axis in wrong_axes[: int(wrong_axis_count)]:
        patch = _flip_image(reference_patch, str(wrong_axis))
        records = _reflect_patch_records(reference_records, width=int(patch_size), height=int(patch_size), axis=str(wrong_axis))
        candidate_pool.append((f"wrong_axis_{wrong_axis}", patch, records, int(len(records))))
    candidate_pool.append(("original_reference", reference_patch.copy(), [dict(record) for record in reference_records], int(len(reference_records))))

    for attempt in range(max(12, int(object_count) * 4)):
        base_patch = correct_patch if int(attempt) % 2 == 0 else reference_patch
        extra = _render_extra_icon_patch(
            rng,
            instance_seed=int(instance_seed),
            namespace=f"{IconsRelationReflectionMatchLabelTask.task_id}:{query_id}:distractor_{int(attempt)}",
            base_patch=base_patch,
            pool=pool,
            palette=sampled_palette_rgb,
            rotation_candidates=render_params["rotation_candidates_degrees"],
            render_params=render_params,
        )
        if extra is None:
            continue
        patch, extra_records, extra_count = extra
        base_records = correct_records if base_patch is correct_patch else reference_records
        candidate_pool.append(
            (
                "altered_reflection" if base_patch is correct_patch else "altered_reference",
                patch,
                [dict(record) for record in base_records] + [dict(record) for record in extra_records],
                int(len(base_records) + extra_count),
            )
        )

    scene_cells: List[Dict[str, Any]] = []
    used_patch_keys = {_patch_key(correct_patch)}
    distractor_cursor = 0
    answer_label = str(labels[int(correct_index)])
    for index, prepared_cell in enumerate(prepared.scene_cells):
        is_match = int(index) == int(correct_index)
        if is_match:
            patch = correct_patch
            placements = [dict(record) for record in correct_records]
            reflection_id = str(query_id)
            icon_count = int(len(placements))
        else:
            selected = None
            for _ in range(max(1, len(candidate_pool) * 2)):
                if not candidate_pool:
                    break
                mode, candidate_patch, candidate_records, candidate_icon_count = candidate_pool[int(distractor_cursor) % len(candidate_pool)]
                distractor_cursor += 1
                if _patch_equal(candidate_patch, correct_patch):
                    continue
                key = _patch_key(candidate_patch)
                if key in used_patch_keys:
                    continue
                used_patch_keys.add(key)
                selected = (mode, candidate_patch, candidate_records, candidate_icon_count)
                break
            if selected is None:
                raise ValueError("failed to select enough unique reflection-match distractors")
            reflection_id, patch, placements, icon_count = selected

        content_bbox = tuple(int(value) for value in prepared_cell.content_bbox_xyxy)
        patch_origin = _center_origin(content_bbox, patch_size=int(patch_size))
        image.alpha_composite(patch, patch_origin)
        is_exact_match = bool(_patch_equal(patch, correct_patch))
        if bool(is_exact_match) != bool(is_match):
            raise ValueError("reflection-match cell exactness did not match sampled answer")
        scene_cells.append(
            {
                "panel": "scene",
                "label": str(prepared_cell.label),
                "cell_bbox_xyxy": list(prepared_cell.cell_bbox_xyxy),
                "content_bbox_xyxy": list(prepared_cell.content_bbox_xyxy),
                "patch_bbox_xyxy": [
                    int(patch_origin[0]),
                    int(patch_origin[1]),
                    int(patch_origin[0] + patch_size),
                    int(patch_origin[1] + patch_size),
                ],
                "reflection_id": str(reflection_id),
                "reflection_axis": str(reflection_axis),
                "symmetry_id": str(reflection_id),
                "icon_count": int(icon_count),
                "is_match": bool(is_match),
                "is_exact_requested_reflection": bool(is_exact_match),
                "placements": _offset_patch_records(
                    placements,
                    offset_x=int(patch_origin[0]),
                    offset_y=int(patch_origin[1]),
                ),
            }
        )

    if sum(1 for cell in scene_cells if bool(cell.get("is_match"))) != 1:
        raise ValueError("reflection-match scene must have exactly one matching cell")

    return _ScenePayload(
        object_count=int(object_count),
        query_id=str(query_id),
        reflection_axis=str(reflection_axis),
        cell_labels=tuple(str(value) for value in labels),
        answer_label=str(answer_label),
        sampled_palette_rgb=tuple(sampled_palette_rgb),
        panel_geometry=panel_geometry_to_trace(prepared.layout),
        reference_cell=dict(reference_payload),
        scene_cells=tuple(dict(item) for item in scene_cells),
    ), image.convert("RGB")


@register_task
class IconsRelationReflectionMatchLabelTask:
    """Select the Scene cell that is the requested reflection of the Reference."""

    task_id = "task_icons__mirror_grid__reflection_match_label"
    domain = "icons"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic reflection-match label instance."""

        scene_rng = spawn_rng(int(instance_seed), "scene")
        selected_query, query_probabilities = _resolve_reflection_query(
            scene_rng,
            params=params,
            instance_seed=int(instance_seed),
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
                    query_id=str(selected_query),
                    render_params=render_params,
                    pool_manifest=str(pool_manifest),
                    params=params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError("failed to generate task_icons__mirror_grid__reflection_match_label instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                f"question_text_{scene_payload.query_id}",
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
                "question_text": str(prompt_defaults[f"question_text_{scene_payload.query_id}"]),
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
        evidence_artifacts = matching_scene_cell_bbox_evidence(
            scene_cells=scene_payload.scene_cells,
            matching_labels=[str(scene_payload.answer_label)],
        )
        answer_gt = TypedValue(type="option_letter", value=str(scene_payload.answer_label))
        evidence_gt = TypedValue(
            type=str(evidence_artifacts["evidence_type"]),
            value=list(evidence_artifacts["evidence_value"]),
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_reference_grid_reflection_match_label",
                "entities": [dict(scene_payload.reference_cell), *[dict(item) for item in scene_payload.scene_cells]],
                "relations": {
                    "target": "scene_cell_is_requested_reflection_of_reference",
                    "query_variant": str(_PUBLIC_QUERY_VARIANT),
                    "query_id": str(scene_payload.query_id),
                    "reflection_axis": str(scene_payload.reflection_axis),
                    "answer_label": str(scene_payload.answer_label),
                    "matching_cell_labels": [str(scene_payload.answer_label)],
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
                    "object_count": int(scene_payload.object_count),
                    "pool_manifest": str(pool_manifest),
                    "reflection_query": str(scene_payload.query_id),
                    "reflection_query_probabilities": dict(query_probabilities),
                    "reflection_axis": str(scene_payload.reflection_axis),
                    "answer_label": str(scene_payload.answer_label),
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
                    "answer_label": str(scene_payload.answer_label),
                    "scene_cells": [dict(item) for item in scene_payload.scene_cells],
                },
            },
            "execution_trace": {
                "scene_variant": "reference_grid",
                "query_variant": str(_PUBLIC_QUERY_VARIANT),
                "query_id": str(scene_payload.query_id),
                "reflection_query": str(scene_payload.query_id),
                "reflection_query_probabilities": dict(query_probabilities),
                "reflection_axis": str(scene_payload.reflection_axis),
                "object_count": int(scene_payload.object_count),
                "cell_labels": list(scene_payload.cell_labels),
                "answer_label": str(scene_payload.answer_label),
                "matching_cell_labels": [str(scene_payload.answer_label)],
                "scene_cell_reflection_ids": [str(cell.get("reflection_id")) for cell in scene_payload.scene_cells],
                "question_format": "select_scene_cell_matching_requested_reference_reflection",
            },
            "witness_symbolic": {
                "query_variant": str(_PUBLIC_QUERY_VARIANT),
                "query_id": str(scene_payload.query_id),
                "reflection_axis": str(scene_payload.reflection_axis),
                "answer_label": str(scene_payload.answer_label),
                **dict(evidence_artifacts["witness_symbolic"]),
            },
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }
        complexity = build_icons_relation_mirror_symmetry_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            query_variant=str(scene_payload.reflection_axis),
            object_count=int(scene_payload.object_count),
            target_count=1,
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
            query_id=str(scene_payload.query_id),
            scene_id="mirror_grid",
            query_probabilities=query_probabilities,
        )


__all__ = ["IconsRelationReflectionMatchLabelTask"]
