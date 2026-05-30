"""Match a partial curated-icon fragment to the full labeled icon option."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
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
from ..shared.complexity import build_icon_task_complexity, icon_scene_clutter_score, icon_visual_scan_score
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.evidence import keyed_bbox_map_evidence
from ..shared.icon_assets import icon_transform_signature, render_icon_rgba, resolve_icon_pool
from ..shared.icon_labeled_grid_scene import prepare_two_panel_labeled_grid_scene
from ..shared.icon_noise import default_icon_noise_value_ranges, serialize_icon_noise_edits
from ..shared.icon_scene import panel_geometry_to_trace
from ..shared.icon_style import icon_palette_meets_distance_constraints, sample_icon_palette
from ..shared.icon_task_rendering import (
    icon_render_style_trace,
    resolve_icon_cell_render_params,
    resolve_icon_rgb_param,
    sample_icon_instance_noise,
)


_QUERY_ID = "partial_icon_match_label"
_FRAGMENT_WINDOW_STYLES: Tuple[str, ...] = ("rectangle", "rounded", "ellipse")
_WINDOW_STYLE_DIFFICULTY: Dict[str, float] = {
    "rectangle": 0.25,
    "rounded": 0.40,
    "ellipse": 0.55,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for partial-icon matching scenes."""

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
    scene_icon_size_min_px: int = 96
    scene_icon_size_max_px: int = 112
    reference_icon_size_px: int = 224
    scene_max_overlap_fraction: float = 0.05
    scene_placement_max_attempts: int = ICON_SHARED_DEFAULTS.scene_placement_max_attempts
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    cell_padding_px: int = 10
    cell_border_rgb: Tuple[int, int, int] = (218, 223, 233)
    cell_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    cell_label_font_size_px: int = 22
    fragment_frame_rgb: Tuple[int, int, int] = (78, 91, 116)
    fragment_frame_width_px: int = 3
    pool_manifest: str = "all_icons.txt"
    rotation_candidates_degrees: Tuple[int, ...] = (0,)
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 190
    min_color_distance: float = 46.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    fragment_window_styles: Tuple[str, ...] = _FRAGMENT_WINDOW_STYLES
    fragment_window_width_fraction_range: Tuple[float, float] = (0.44, 0.70)
    fragment_window_height_fraction_range: Tuple[float, float] = (0.44, 0.70)
    fragment_visible_alpha_ratio_range: Tuple[float, float] = (0.34, 0.64)
    fragment_alpha_density_min: float = 0.08
    fragment_sampling_attempts: int = 240
    reference_content_padding_px: int = 18
    scene_content_side_padding_px: int = 14
    scene_content_bottom_padding_px: int = 14
    scene_content_top_offset_px: int = 42
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=default_icon_noise_value_ranges
    )


@dataclass(frozen=True)
class _FragmentPayload:
    """One sampled partial-fragment crop and metadata."""

    image: Image.Image
    crop_xyxy: Tuple[int, int, int, int]
    window_style: str
    visible_alpha_ratio: float
    alpha_density: float


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one icon-cutout option instance."""

    object_count: int
    cell_labels: Tuple[str, ...]
    answer_label: str
    correct_icon_id: str
    option_icon_ids: Tuple[str, ...]
    tint_rgb: Tuple[int, int, int]
    rotation_degrees: int
    fragment_window_style: str
    fragment_visible_alpha_ratio: float
    fragment_alpha_density: float
    fragment_crop_xyxy: Tuple[int, int, int, int]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    reference_cell: Dict[str, Any]
    scene_cells: Tuple[Dict[str, Any], ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_icons__icon_cutout__partial_match_label",
)


def _clip01(value: float) -> float:
    """Clamp a float into [0, 1]."""

    return max(0.0, min(1.0, float(value)))


def _normalize_linear(value: float, *, min_value: float, max_value: float) -> float:
    """Normalize a value into [0, 1]."""

    lo = float(min_value)
    hi = float(max_value)
    if hi <= lo:
        return 0.0
    return _clip01((float(value) - lo) / (hi - lo))


def _alpha_pixel_count(image: Image.Image) -> int:
    """Return the number of visibly nontransparent pixels in an RGBA image."""

    alpha = image.convert("RGBA").getchannel("A")
    return int(sum(1 for value in alpha.getdata() if int(value) > 8))


def _apply_window_mask(image: Image.Image, *, style: str) -> Image.Image:
    """Apply the sampled fragment-window shape to one crop."""

    crop = image.convert("RGBA")
    if str(style) == "rectangle":
        return crop

    mask = Image.new("L", crop.size, 0)
    draw = ImageDraw.Draw(mask)
    bbox = (0, 0, max(1, int(crop.size[0]) - 1), max(1, int(crop.size[1]) - 1))
    if str(style) == "ellipse":
        draw.ellipse(bbox, fill=255)
    elif str(style) == "rounded":
        radius = max(4, int(round(min(crop.size) * 0.18)))
        draw.rounded_rectangle(bbox, radius=int(radius), fill=255)
    else:
        raise ValueError(f"unsupported fragment window style: {style}")

    existing_alpha = crop.getchannel("A")
    masked_alpha = ImageChops.multiply(existing_alpha, mask)
    crop.putalpha(masked_alpha)
    return crop


def _resolve_range(raw: Any, fallback: Sequence[float], *, key: str) -> Tuple[float, float]:
    """Resolve a two-value numeric range."""

    value = raw if raw is not None else fallback
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        raise ValueError(f"{key} must contain two numeric bounds")
    lo = float(value[0])
    hi = float(value[1])
    return min(lo, hi), max(lo, hi)


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, Any]:
    """Resolve render params for the icon-cutout task."""

    render_params = resolve_icon_cell_render_params(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        fallback_defaults=_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    render_params["fragment_frame_rgb"] = resolve_icon_rgb_param(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        key="fragment_frame_rgb",
        fallback=_DEFAULTS.fragment_frame_rgb,
        instance_seed=int(instance_seed),
    )
    render_params["fragment_frame_width_px"] = int(
        params.get(
            "fragment_frame_width_px",
            group_default(_RENDER_DEFAULTS, "fragment_frame_width_px", _DEFAULTS.fragment_frame_width_px),
        )
    )
    raw_styles = params.get(
        "fragment_window_styles",
        group_default(_RENDER_DEFAULTS, "fragment_window_styles", list(_DEFAULTS.fragment_window_styles)),
    )
    if not isinstance(raw_styles, (list, tuple)):
        raise ValueError("fragment_window_styles must be a sequence")
    styles = tuple(str(value) for value in raw_styles if str(value) in set(_FRAGMENT_WINDOW_STYLES))
    if not styles:
        raise ValueError("fragment_window_styles resolved no supported styles")
    render_params["fragment_window_styles"] = styles
    render_params["fragment_window_width_fraction_range"] = _resolve_range(
        params.get(
            "fragment_window_width_fraction_range",
            group_default(
                _RENDER_DEFAULTS,
                "fragment_window_width_fraction_range",
                list(_DEFAULTS.fragment_window_width_fraction_range),
            ),
        ),
        _DEFAULTS.fragment_window_width_fraction_range,
        key="fragment_window_width_fraction_range",
    )
    render_params["fragment_window_height_fraction_range"] = _resolve_range(
        params.get(
            "fragment_window_height_fraction_range",
            group_default(
                _RENDER_DEFAULTS,
                "fragment_window_height_fraction_range",
                list(_DEFAULTS.fragment_window_height_fraction_range),
            ),
        ),
        _DEFAULTS.fragment_window_height_fraction_range,
        key="fragment_window_height_fraction_range",
    )
    render_params["fragment_visible_alpha_ratio_range"] = _resolve_range(
        params.get(
            "fragment_visible_alpha_ratio_range",
            group_default(
                _RENDER_DEFAULTS,
                "fragment_visible_alpha_ratio_range",
                list(_DEFAULTS.fragment_visible_alpha_ratio_range),
            ),
        ),
        _DEFAULTS.fragment_visible_alpha_ratio_range,
        key="fragment_visible_alpha_ratio_range",
    )
    render_params["fragment_alpha_density_min"] = float(
        params.get(
            "fragment_alpha_density_min",
            group_default(_RENDER_DEFAULTS, "fragment_alpha_density_min", _DEFAULTS.fragment_alpha_density_min),
        )
    )
    render_params["fragment_sampling_attempts"] = int(
        params.get(
            "fragment_sampling_attempts",
            group_default(_RENDER_DEFAULTS, "fragment_sampling_attempts", _DEFAULTS.fragment_sampling_attempts),
        )
    )
    render_params["reference_content_padding_px"] = int(
        params.get(
            "reference_content_padding_px",
            group_default(_RENDER_DEFAULTS, "reference_content_padding_px", _DEFAULTS.reference_content_padding_px),
        )
    )
    render_params["rotation_candidates_degrees"] = tuple(
        int(value) % 360
        for value in params.get(
            "rotation_candidates_degrees",
            group_default(_RENDER_DEFAULTS, "rotation_candidates_degrees", list(_DEFAULTS.rotation_candidates_degrees)),
        )
    )
    if not render_params["rotation_candidates_degrees"]:
        raise ValueError("rotation_candidates_degrees resolved no values")
    return render_params


def _sample_palette(rng, render_params: Mapping[str, Any]) -> Tuple[Tuple[int, int, int], ...]:
    """Sample a palette separated from icon chrome colors."""

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
                tuple(int(v) for v in render_params["fragment_frame_rgb"]),
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
            tuple(int(v) for v in render_params["fragment_frame_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    ):
        raise ValueError("sampled icon-cutout palette did not satisfy distance constraints")
    return palette


def _fit_rgba_inside(image: Image.Image, bbox: Sequence[int | float]) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    """Resize an RGBA image to fit inside a bbox and return placed bbox."""

    x0, y0, x1, y1 = [int(round(float(value))) for value in bbox]
    max_w = max(1, int(x1 - x0))
    max_h = max(1, int(y1 - y0))
    source = image.convert("RGBA")
    scale = min(float(max_w) / float(max(1, source.size[0])), float(max_h) / float(max(1, source.size[1])))
    new_w = max(1, int(round(float(source.size[0]) * float(scale))))
    new_h = max(1, int(round(float(source.size[1]) * float(scale))))
    resized = source.resize((int(new_w), int(new_h)), resample=Image.Resampling.LANCZOS)
    px0 = int(x0 + (max_w - new_w) // 2)
    py0 = int(y0 + (max_h - new_h) // 2)
    return resized, (int(px0), int(py0), int(px0 + new_w), int(py0 + new_h))


def _sample_fragment(rng, *, sprite: Image.Image, render_params: Mapping[str, Any]) -> _FragmentPayload:
    """Sample one visible partial crop from the correct full icon sprite."""

    total_alpha = max(1, _alpha_pixel_count(sprite))
    width_min, width_max = [float(value) for value in render_params["fragment_window_width_fraction_range"]]
    height_min, height_max = [float(value) for value in render_params["fragment_window_height_fraction_range"]]
    visible_min, visible_max = [float(value) for value in render_params["fragment_visible_alpha_ratio_range"]]
    density_min = float(render_params["fragment_alpha_density_min"])
    styles = tuple(str(value) for value in render_params["fragment_window_styles"])
    sprite_w, sprite_h = [int(value) for value in sprite.size]

    for _ in range(max(1, int(render_params["fragment_sampling_attempts"]))):
        crop_w = max(10, min(sprite_w - 1, int(round(float(sprite_w) * float(rng.uniform(width_min, width_max))))))
        crop_h = max(10, min(sprite_h - 1, int(round(float(sprite_h) * float(rng.uniform(height_min, height_max))))))
        if crop_w >= sprite_w and crop_h >= sprite_h:
            continue
        x0 = int(rng.randint(0, max(0, sprite_w - crop_w)))
        y0 = int(rng.randint(0, max(0, sprite_h - crop_h)))
        raw_crop = sprite.crop((int(x0), int(y0), int(x0 + crop_w), int(y0 + crop_h)))
        style = str(rng.choice(styles))
        crop = _apply_window_mask(raw_crop, style=str(style))
        crop_alpha = _alpha_pixel_count(crop)
        visible_ratio = float(crop_alpha) / float(total_alpha)
        density = float(crop_alpha) / float(max(1, crop.size[0] * crop.size[1]))
        if density <= 0.0:
            continue
        payload = _FragmentPayload(
            image=crop,
            crop_xyxy=(int(x0), int(y0), int(x0 + crop_w), int(y0 + crop_h)),
            window_style=str(style),
            visible_alpha_ratio=float(visible_ratio),
            alpha_density=float(density),
        )
        if float(visible_min) <= float(visible_ratio) <= float(visible_max) and float(density) >= float(density_min):
            return payload

    raise ValueError("failed to sample a visible partial icon fragment")


def _draw_fragment_frame(
    *,
    image: Image.Image,
    bbox: Sequence[int | float],
    style: str,
    frame_rgb: Tuple[int, int, int],
    frame_width_px: int,
) -> None:
    """Draw the visible partial-fragment window frame."""

    draw = ImageDraw.Draw(image)
    x0, y0, x1, y1 = [int(round(float(value))) for value in bbox]
    width = max(1, int(frame_width_px))
    frame_bbox = (int(x0), int(y0), int(x1 - 1), int(y1 - 1))
    if str(style) == "ellipse":
        draw.ellipse(frame_bbox, outline=tuple(int(v) for v in frame_rgb), width=int(width))
    elif str(style) == "rounded":
        radius = max(8, int(round(min(max(1, x1 - x0), max(1, y1 - y0)) * 0.10)))
        draw.rounded_rectangle(frame_bbox, radius=int(radius), outline=tuple(int(v) for v in frame_rgb), width=int(width))
    else:
        draw.rectangle(frame_bbox, outline=tuple(int(v) for v in frame_rgb), width=int(width))


def _resolve_object_count(params: Mapping[str, Any]) -> int:
    """Resolve the number of labeled full-icon options."""

    raw = params.get("object_count", group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max))
    count = int(raw)
    if count < 4 or count > len(LABEL_POOL_A_L):
        raise ValueError("object_count must be between 4 and the supported label-pool size")
    return int(count)


def _resolve_answer_index(rng, *, params: Mapping[str, Any], labels: Sequence[str]) -> int:
    """Resolve which labeled option is correct."""

    if params.get("answer_index") is not None:
        index = int(params["answer_index"])
        if not 0 <= int(index) < len(labels):
            raise ValueError("answer_index out of range")
        return int(index)
    if params.get("answer_label") is not None:
        label = str(params["answer_label"]).strip().upper()
        if label not in set(str(value) for value in labels):
            raise ValueError("answer_label is not supported by the sampled option count")
        return int(list(str(value) for value in labels).index(label))
    return int(rng.randrange(len(labels)))


def _sample_option_icon_ids(
    rng,
    *,
    pool: Sequence[str],
    correct_icon_id: str,
    correct_index: int,
    object_count: int,
    signature_size_px: int,
    rotation_degrees: int,
) -> Tuple[str, ...]:
    """Sample option icon ids with the correct id at the resolved index."""

    correct_signature = icon_transform_signature(
        str(correct_icon_id),
        int(signature_size_px),
        transform_id="identity",
    )
    candidates = [str(icon_id) for icon_id in pool if str(icon_id) != str(correct_icon_id)]
    rng.shuffle(candidates)
    distractors: List[str] = []
    seen_signatures = {correct_signature}
    for icon_id in candidates:
        signature = icon_transform_signature(str(icon_id), int(signature_size_px), transform_id="identity")
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        distractors.append(str(icon_id))
        if len(distractors) >= int(object_count) - 1:
            break
    if len(distractors) < int(object_count) - 1:
        raise ValueError("icon-cutout task resolved too few visually distinct distractors")

    option_ids: List[str] = []
    cursor = 0
    for index in range(int(object_count)):
        if int(index) == int(correct_index):
            option_ids.append(str(correct_icon_id))
        else:
            option_ids.append(str(distractors[int(cursor)]))
            cursor += 1
    _ = rotation_degrees
    return tuple(str(value) for value in option_ids)


def _scene_style_trace(
    *,
    render_params: Mapping[str, Any],
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...],
) -> Dict[str, Any]:
    """Return trace metadata for rendered icon-cutout style choices."""

    style = icon_render_style_trace(
        render_params=render_params,
        sampled_palette_rgb=sampled_palette_rgb,
    )
    style.update(
        {
            "cell_padding_px": int(render_params["cell_padding_px"]),
            "cell_border_rgb": list(render_params["cell_border_rgb"]),
            "cell_label_color_rgb": list(render_params["cell_label_color_rgb"]),
            "cell_label_stroke_rgb": list(render_params.get("cell_label_stroke_rgb", render_params["panel_fill_rgb"])),
            "cell_label_font_size_px": int(render_params["cell_label_font_size_px"]),
            "fragment_frame_rgb": list(render_params["fragment_frame_rgb"]),
            "fragment_frame_width_px": int(render_params["fragment_frame_width_px"]),
            "fragment_window_styles": [str(value) for value in render_params["fragment_window_styles"]],
            "fragment_window_width_fraction_range": [
                float(render_params["fragment_window_width_fraction_range"][0]),
                float(render_params["fragment_window_width_fraction_range"][1]),
            ],
            "fragment_window_height_fraction_range": [
                float(render_params["fragment_window_height_fraction_range"][0]),
                float(render_params["fragment_window_height_fraction_range"][1]),
            ],
            "fragment_visible_alpha_ratio_range": [
                float(render_params["fragment_visible_alpha_ratio_range"][0]),
                float(render_params["fragment_visible_alpha_ratio_range"][1]),
            ],
            "fragment_alpha_density_min": float(render_params["fragment_alpha_density_min"]),
            "fragment_sampling_attempts": int(render_params["fragment_sampling_attempts"]),
        }
    )
    return style


def _build_complexity(
    *,
    scene_payload: _ScenePayload,
    render_params: Mapping[str, Any],
) -> TaskComplexity:
    """Build relation-task complexity for partial icon matching."""

    object_count_min = int(group_default(_GEN_DEFAULTS, "object_count_min", _DEFAULTS.object_count_min))
    object_count_max = int(group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max))
    visible_min, visible_max = [float(value) for value in render_params["fragment_visible_alpha_ratio_range"]]
    crop_difficulty = 1.0 - _normalize_linear(
        float(scene_payload.fragment_visible_alpha_ratio),
        min_value=float(visible_min),
        max_value=float(visible_max),
    )
    style_difficulty = float(_WINDOW_STYLE_DIFFICULTY.get(str(scene_payload.fragment_window_style), 0.40))
    visual_scan = icon_visual_scan_score(
        object_count=int(scene_payload.object_count),
        object_count_min=int(object_count_min),
        object_count_max=max(int(object_count_min) + 1, int(object_count_max)),
    )
    spatial_reasoning = _clip01((0.70 * float(crop_difficulty)) + (0.30 * float(style_difficulty)))
    ambiguity = _clip01((0.60 * float(crop_difficulty)) + (0.25 * float(style_difficulty)) + (0.15 * float(visual_scan)))
    option_instances = [
        {
            "bbox_xyxy": list(cell.get("icon_bbox_xyxy", ())),
            "noise_edits": list(cell.get("noise_edits", ())),
        }
        for cell in scene_payload.scene_cells
    ]
    clutter = icon_scene_clutter_score(
        scene_instances=option_instances,
        scene_icon_size_min_px=int(render_params["scene_icon_size_min_px"]),
        scene_icon_size_max_px=int(render_params["scene_icon_size_max_px"]),
        scene_max_overlap_fraction=0.05,
        noise_edit_count_range=render_params["icon_noise_edit_count_range"],
    )
    return build_icon_task_complexity(
        task_group_defaults=_TASK_GROUP_DEFAULTS,
        task_id=IconsRelationPartialMatchLabelTask.task_id,
        criterion_values={
            "visual_scan": float(visual_scan),
            "spatial_reasoning": float(spatial_reasoning),
            "ambiguity": float(ambiguity),
            "clutter": float(clutter),
        },
    )


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    render_params: Mapping[str, Any],
    pool_manifest: str,
    params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Image.Image]:
    """Sample and render one partial-fragment option task."""

    object_count = _resolve_object_count(params)
    labels = tuple(str(value) for value in LABEL_POOL_A_L[: int(object_count)])
    answer_index = _resolve_answer_index(rng, params=params, labels=labels)
    answer_label = str(labels[int(answer_index)])

    pool = tuple(str(icon_id) for icon_id in resolve_icon_pool(str(pool_manifest)))
    if len(pool) < int(object_count):
        raise ValueError("icon-cutout pool resolved too few icons")
    correct_icon_id = str(rng.choice(pool))
    rotation_degrees = int(rng.choice(tuple(int(value) for value in render_params["rotation_candidates_degrees"])))
    option_icon_ids = _sample_option_icon_ids(
        rng,
        pool=pool,
        correct_icon_id=str(correct_icon_id),
        correct_index=int(answer_index),
        object_count=int(object_count),
        signature_size_px=int(render_params["scene_icon_size_max_px"]),
        rotation_degrees=int(rotation_degrees),
    )

    sampled_palette_rgb = _sample_palette(rng, render_params)
    tint_rgb = tuple(int(channel) for channel in rng.choice(sampled_palette_rgb))
    source_noise_edits, source_noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"{IconsRelationPartialMatchLabelTask.task_id}:source_icon",
        render_params=render_params,
    )
    source_sprite = render_icon_rgba(
        icon_id=str(correct_icon_id),
        size_px=int(render_params["reference_icon_size_px"]),
        tint_rgb=tuple(int(channel) for channel in tint_rgb),
        rotation_degrees=int(rotation_degrees),
        mirror_x=False,
        noise_edits=tuple(source_noise_edits),
        noise_seed=int(source_noise_seed),
    )
    fragment = _sample_fragment(rng, sprite=source_sprite, render_params=render_params)

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
        cell_label_stroke_rgb=tuple(int(v) for v in render_params["cell_label_stroke_rgb"]),
        cell_label_stroke_width_px=1,
        cell_label_font_size_px=int(render_params["cell_label_font_size_px"]),
        reference_content_padding_px=int(render_params["reference_content_padding_px"]),
        scene_content_side_padding_px=int(render_params["scene_content_side_padding_px"]),
        scene_content_bottom_padding_px=int(render_params["scene_content_bottom_padding_px"]),
        scene_content_top_offset_px=int(render_params["scene_content_top_offset_px"]),
        reference_square_cell=True,
        scene_square_cells=True,
        reference_title="Fragment",
        scene_title="Full icons",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )
    image = prepared.image
    fragment_image, fragment_bbox = _fit_rgba_inside(fragment.image, prepared.reference_cell.content_bbox_xyxy)
    image.alpha_composite(fragment_image, (int(fragment_bbox[0]), int(fragment_bbox[1])))
    _draw_fragment_frame(
        image=image,
        bbox=fragment_bbox,
        style=str(fragment.window_style),
        frame_rgb=tuple(int(v) for v in render_params["fragment_frame_rgb"]),
        frame_width_px=int(render_params["fragment_frame_width_px"]),
    )

    reference_cell = {
        "panel": "reference",
        "cell_bbox_xyxy": list(prepared.reference_cell.cell_bbox_xyxy),
        "content_bbox_xyxy": list(prepared.reference_cell.content_bbox_xyxy),
        "fragment_bbox_xyxy": [int(value) for value in fragment_bbox],
        "source_icon_id": str(correct_icon_id),
        "source_icon_size_px": int(render_params["reference_icon_size_px"]),
        "source_icon_crop_xyxy": [int(value) for value in fragment.crop_xyxy],
        "fragment_window_style": str(fragment.window_style),
        "fragment_visible_alpha_ratio": float(fragment.visible_alpha_ratio),
        "fragment_alpha_density": float(fragment.alpha_density),
        "rotation_degrees": int(rotation_degrees),
        "tint_rgb": [int(value) for value in tint_rgb],
        "noise_edits": [dict(edit) for edit in serialize_icon_noise_edits(tuple(source_noise_edits))],
        "noise_seed": int(source_noise_seed),
    }

    scene_cells: List[Dict[str, Any]] = []
    for index, (cell, icon_id) in enumerate(zip(prepared.scene_cells, option_icon_ids)):
        if int(index) == int(answer_index):
            option_noise_edits = tuple(source_noise_edits)
            option_noise_seed = int(source_noise_seed)
        else:
            option_noise_edits, option_noise_seed = sample_icon_instance_noise(
                instance_seed=int(instance_seed),
                namespace=f"{IconsRelationPartialMatchLabelTask.task_id}:option_{int(index)}",
                render_params=render_params,
            )
        sprite = render_icon_rgba(
            icon_id=str(icon_id),
            size_px=int(render_params["scene_icon_size_max_px"]),
            tint_rgb=tuple(int(channel) for channel in tint_rgb),
            rotation_degrees=int(rotation_degrees),
            mirror_x=False,
            noise_edits=tuple(option_noise_edits),
            noise_seed=int(option_noise_seed),
        )
        fitted, icon_bbox = _fit_rgba_inside(sprite, cell.content_bbox_xyxy)
        image.alpha_composite(fitted, (int(icon_bbox[0]), int(icon_bbox[1])))
        scene_cells.append(
            {
                "panel": "scene",
                "label": str(cell.label),
                "cell_bbox_xyxy": list(cell.cell_bbox_xyxy),
                "content_bbox_xyxy": list(cell.content_bbox_xyxy),
                "icon_bbox_xyxy": [int(value) for value in icon_bbox],
                "icon_id": str(icon_id),
                "is_match": bool(int(index) == int(answer_index)),
                "rotation_degrees": int(rotation_degrees),
                "tint_rgb": [int(value) for value in tint_rgb],
                "noise_edits": [dict(edit) for edit in serialize_icon_noise_edits(tuple(option_noise_edits))],
                "noise_seed": int(option_noise_seed),
            }
        )

    if sum(1 for cell in scene_cells if bool(cell.get("is_match"))) != 1:
        raise ValueError("icon-cutout scene must contain exactly one matching full-icon option")

    return _ScenePayload(
        object_count=int(object_count),
        cell_labels=tuple(labels),
        answer_label=str(answer_label),
        correct_icon_id=str(correct_icon_id),
        option_icon_ids=tuple(str(value) for value in option_icon_ids),
        tint_rgb=tuple(int(value) for value in tint_rgb),
        rotation_degrees=int(rotation_degrees),
        fragment_window_style=str(fragment.window_style),
        fragment_visible_alpha_ratio=float(fragment.visible_alpha_ratio),
        fragment_alpha_density=float(fragment.alpha_density),
        fragment_crop_xyxy=tuple(int(value) for value in fragment.crop_xyxy),
        sampled_palette_rgb=tuple(sampled_palette_rgb),
        panel_geometry=panel_geometry_to_trace(prepared.layout),
        reference_cell=dict(reference_cell),
        scene_cells=tuple(dict(item) for item in scene_cells),
    ), image.convert("RGB")


@register_task
class IconsRelationPartialMatchLabelTask:
    """Select which full curated icon generated the partial fragment."""

    task_id = "task_icons__icon_cutout__partial_match_label"
    domain = "icons"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic partial-icon matching instance."""

        scene_rng = spawn_rng(int(instance_seed), "scene")
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
                    render_params=render_params,
                    pool_manifest=str(pool_manifest),
                    params=params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError("failed to generate task_icons__icon_cutout__partial_match_label instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text_partial_icon_match_label",
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
                "question_text": str(prompt_defaults["question_text_partial_icon_match_label"]),
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

        matching_cell = next(cell for cell in scene_payload.scene_cells if bool(cell.get("is_match")))
        evidence_artifacts = keyed_bbox_map_evidence(
            {
                "source_fragment": scene_payload.reference_cell["fragment_bbox_xyxy"],
                "selected_option": matching_cell["cell_bbox_xyxy"],
            }
        )
        answer_gt = TypedValue(type="option_letter", value=str(scene_payload.answer_label))
        evidence_gt = TypedValue(
            type=str(evidence_artifacts["evidence_type"]),
            value=dict(evidence_artifacts["evidence_value"]),
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_icon_cutout_partial_match_label",
                "scene_id": "icon_cutout",
                "query_id": str(_QUERY_ID),
                "entities": [dict(scene_payload.reference_cell), *[dict(item) for item in scene_payload.scene_cells]],
                "relations": {
                    "target": "full_icon_option_matches_partial_source_fragment",
                    "query_id": str(_QUERY_ID),
                    "answer_label": str(scene_payload.answer_label),
                    "answer_icon_id": str(scene_payload.correct_icon_id),
                    "matching_cell_label": str(scene_payload.answer_label),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "task_id": str(self.task_id),
                "scene_id": "icon_cutout",
                "query_id": str(_QUERY_ID),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_id": str(self.task_id),
                    "scene_id": "icon_cutout",
                    "query_id": str(_QUERY_ID),
                    "query_id_probabilities": {str(_QUERY_ID): 1.0},
                    "object_count": int(scene_payload.object_count),
                    "pool_manifest": str(pool_manifest),
                    "answer_label": str(scene_payload.answer_label),
                    "fragment_window_style": str(scene_payload.fragment_window_style),
                    "fragment_visible_alpha_ratio": float(scene_payload.fragment_visible_alpha_ratio),
                    "fragment_alpha_density": float(scene_payload.fragment_alpha_density),
                },
            },
            "render_spec": {
                "task_id": str(self.task_id),
                "scene_id": "icon_cutout",
                "query_id": str(_QUERY_ID),
                "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": _scene_style_trace(
                    render_params=render_params,
                    sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                ),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "source_fragment": dict(scene_payload.reference_cell),
                    "answer_label": str(scene_payload.answer_label),
                    "selected_option": dict(matching_cell),
                    "scene_cells": [dict(item) for item in scene_payload.scene_cells],
                },
            },
            "execution_trace": {
                "task_id": str(self.task_id),
                "scene_id": "icon_cutout",
                "query_id": str(_QUERY_ID),
                "query_id_probabilities": {str(_QUERY_ID): 1.0},
                "scene_variant": "partial_fragment_with_full_icon_options",
                "question_format": "select_full_icon_option_matching_partial_source_fragment",
                "object_count": int(scene_payload.object_count),
                "cell_labels": list(scene_payload.cell_labels),
                "answer": str(scene_payload.answer_label),
                "answer_label": str(scene_payload.answer_label),
                "correct_icon_id": str(scene_payload.correct_icon_id),
                "option_icon_ids_by_label": {
                    str(cell["label"]): str(cell["icon_id"])
                    for cell in scene_payload.scene_cells
                },
                "fragment_window_style": str(scene_payload.fragment_window_style),
                "fragment_visible_alpha_ratio": float(scene_payload.fragment_visible_alpha_ratio),
                "fragment_alpha_density": float(scene_payload.fragment_alpha_density),
                "evidence_roles": ["source_fragment", "selected_option"],
            },
            "witness_symbolic": {
                "source_fragment_icon_id": str(scene_payload.correct_icon_id),
                "selected_option_label": str(scene_payload.answer_label),
                "selected_option_icon_id": str(matching_cell["icon_id"]),
                "source_fragment_bbox": list(scene_payload.reference_cell["fragment_bbox_xyxy"]),
                "selected_option_bbox": list(matching_cell["cell_bbox_xyxy"]),
            },
            "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(scene_payload=scene_payload, render_params=render_params),
            task_versions=default_task_versions(),
            scene_id="icon_cutout",
            query_id=str(_QUERY_ID),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsRelationPartialMatchLabelTask"]
