"""Select the result of applying one geometric transform to a curated icon."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
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
from ...shared.text_legibility import (
    draw_text_traced,
    resolve_readable_text_style,
    text_legibility_summary_from_records,
)
from ...shared.text_rendering import load_font
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.annotation import keyed_bbox_map_annotation
from ..shared.icon_assets import icon_transform_signature, render_icon_transformed_rgba, resolve_icon_pool
from ..shared.icon_labeled_grid_scene import prepare_two_panel_labeled_grid_scene
from ..shared.icon_noise import default_icon_noise_value_ranges, serialize_icon_noise_edits
from ..shared.icon_scene import panel_geometry_to_trace
from ..shared.icon_style import sample_single_icon_tint
from ..shared.icon_task_rendering import (
    icon_render_style_trace,
    resolve_icon_cell_render_params,
    resolve_icon_rgb_param,
    sample_icon_instance_noise,
)
from ..shared.icon_transform import IDENTITY_TRANSFORM_ID


TASK_ID = "task_icons__single_transform_options__geometric_transform_result_label"
SCENE_ID = "single_transform_options"
_QUERY_IDS: Tuple[str, ...] = (
    "rotate_90_clockwise_result_label",
    "rotate_90_counterclockwise_result_label",
    "rotate_180_result_label",
    "flip_horizontal_result_label",
    "flip_vertical_result_label",
)
_QUERY_TO_TRANSFORM: Dict[str, str] = {
    "rotate_90_clockwise_result_label": "rot270",
    "rotate_90_counterclockwise_result_label": "rot90",
    "rotate_180_result_label": "rot180",
    "flip_horizontal_result_label": "flip_h",
    "flip_vertical_result_label": "flip_v",
}
_QUERY_TO_CUE: Dict[str, str] = {
    "rotate_90_clockwise_result_label": "Rotate 90 CW",
    "rotate_90_counterclockwise_result_label": "Rotate 90 CCW",
    "rotate_180_result_label": "Rotate 180",
    "flip_horizontal_result_label": "Flip horizontal",
    "flip_vertical_result_label": "Flip vertical",
}
_ALL_OPTION_TRANSFORMS: Tuple[str, ...] = (
    IDENTITY_TRANSFORM_ID,
    "rot90",
    "rot180",
    "rot270",
    "flip_h",
    "flip_v",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for single-icon transform option scenes."""

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
    reference_icon_size_px: int = 160
    scene_max_overlap_fraction: float = 0.05
    scene_placement_max_attempts: int = ICON_SHARED_DEFAULTS.scene_placement_max_attempts
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    cell_padding_px: int = 10
    cell_border_rgb: Tuple[int, int, int] = (218, 223, 233)
    cell_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    cell_label_font_size_px: int = 22
    operation_cue_font_size_px: int = 21
    operation_cue_color_rgb: Tuple[int, int, int] = (63, 73, 94)
    pool_manifest: str = "non_symmetry.txt"
    transform_check_size_px: int = 96
    palette_size_min: int = 1
    palette_size_max: int = 1
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 42.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
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
class _ScenePayload:
    """Trace-ready payload for one transform-result option instance."""

    object_count: int
    cell_labels: Tuple[str, ...]
    query_id: str
    transform_id: str
    operation_cue: str
    answer_label: str
    icon_id: str
    option_transform_ids: Tuple[str, ...]
    tint_rgb: Tuple[int, int, int]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    reference_cell: Dict[str, Any]
    scene_cells: Tuple[Dict[str, Any], ...]


_DEFAULTS = _TaskDefaults()
_SCENE_DEFAULTS = get_scene_defaults("icons", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


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


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, Any]:
    """Resolve render params for the single-transform visual option task."""

    render_params = resolve_icon_cell_render_params(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        fallback_defaults=_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    render_params["operation_cue_font_size_px"] = int(
        params.get(
            "operation_cue_font_size_px",
            group_default(_RENDER_DEFAULTS, "operation_cue_font_size_px", _DEFAULTS.operation_cue_font_size_px),
        )
    )
    render_params["operation_cue_color_rgb"] = resolve_icon_rgb_param(
        params=params,
        render_defaults=_RENDER_DEFAULTS,
        key="operation_cue_color_rgb",
        fallback=_DEFAULTS.operation_cue_color_rgb,
        instance_seed=int(instance_seed),
    )
    render_params["reference_content_padding_px"] = int(
        params.get(
            "reference_content_padding_px",
            group_default(
                _RENDER_DEFAULTS,
                "reference_content_padding_px",
                _DEFAULTS.reference_content_padding_px,
            ),
        )
    )
    cue_style = resolve_readable_text_style(
        instance_seed=int(instance_seed),
        namespace="icons.single_transform_options.operation_cue_text",
        role="icon_operation_cue_text",
        surface_rgbs=(
            tuple(int(value) for value in render_params["panel_fill_rgb"]),
            tuple(int(value) for value in render_params["background_color_rgb"]),
        ),
        preferred_rgbs=(tuple(int(value) for value in render_params["operation_cue_color_rgb"]),),
    )
    render_params["operation_cue_color_rgb"] = tuple(int(value) for value in cue_style.fill_rgb)
    render_params["operation_cue_stroke_rgb"] = tuple(int(value) for value in render_params["panel_fill_rgb"])
    cue_record = cue_style.metadata()
    cue_record["stroke_rgb"] = list(render_params["operation_cue_stroke_rgb"])
    previous_legibility = render_params.get("text_legibility")
    previous_records = []
    if isinstance(previous_legibility, Mapping) and isinstance(previous_legibility.get("records"), list):
        previous_records = [dict(record) for record in previous_legibility["records"] if isinstance(record, Mapping)]
    render_params["text_legibility"] = text_legibility_summary_from_records([*previous_records, cue_record])
    return render_params


def _resolve_object_count(params: Mapping[str, Any]) -> int:
    raw = params.get("object_count", group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max))
    count = int(raw)
    if count != 6:
        raise ValueError("single-transform option task requires object_count=6")
    return count


def _resolve_query_id(rng, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve the operation query branch."""

    weights_raw = params.get("query_id_weights", group_default(_GEN_DEFAULTS, "query_id_weights", {key: 1.0 for key in _QUERY_IDS}))
    if not isinstance(weights_raw, Mapping):
        raise ValueError("query_id_weights must be a mapping")
    weights = {str(key): float(value) for key, value in weights_raw.items() if str(key) in set(_QUERY_IDS) and float(value) > 0.0}
    if not weights:
        weights = {key: 1.0 for key in _QUERY_IDS}
    if params.get("query_id") is not None:
        query_id = str(params["query_id"]).strip()
    elif params.get("operation_id") is not None:
        query_id = str(params["operation_id"]).strip()
    else:
        keys = list(weights.keys())
        values = [float(weights[key]) for key in keys]
        query_id = str(rng.choices(keys, weights=values, k=1)[0])
    if query_id not in set(_QUERY_IDS):
        raise ValueError(f"unsupported query_id for {TASK_ID}: {query_id}")
    total = float(sum(weights.values()))
    probabilities = {str(key): float(value) / total for key, value in weights.items()}
    return query_id, probabilities


def _resolve_answer_index(rng, *, params: Mapping[str, Any], labels: Sequence[str]) -> int:
    if params.get("answer_index") is not None:
        index = int(params["answer_index"])
        if not 0 <= index < len(labels):
            raise ValueError("answer_index out of range")
        return index
    if params.get("answer_label") is not None:
        label = str(params["answer_label"]).strip().upper()
        if label not in set(str(value) for value in labels):
            raise ValueError("answer_label is not supported by the sampled option count")
        return int(list(str(value) for value in labels).index(label))
    return int(rng.randrange(len(labels)))


def _icon_supports_all_option_transforms(icon_id: str, *, check_size_px: int) -> bool:
    signatures = [
        icon_transform_signature(str(icon_id), int(check_size_px), str(transform_id))
        for transform_id in _ALL_OPTION_TRANSFORMS
    ]
    return len(set(signatures)) == len(signatures)


def _sample_transform_distinct_icon(
    rng,
    *,
    pool_manifest: str,
    transform_check_size_px: int,
) -> str:
    pool = list(resolve_icon_pool(str(pool_manifest)))
    if not pool:
        raise ValueError("single-transform option pool resolved no icons")
    rng.shuffle(pool)
    for icon_id in pool:
        if _icon_supports_all_option_transforms(str(icon_id), check_size_px=int(transform_check_size_px)):
            return str(icon_id)
    raise ValueError("insufficient non-symmetric icons with distinct supported transforms")


def _option_transforms_for_answer(*, answer_index: int, target_transform_id: str) -> Tuple[str, ...]:
    distractors = [str(value) for value in _ALL_OPTION_TRANSFORMS if str(value) != str(target_transform_id)]
    if len(distractors) != 5:
        raise ValueError("single-transform option task requires exactly five distractor transforms")
    option_transforms: List[str] = []
    cursor = 0
    for index in range(6):
        if int(index) == int(answer_index):
            option_transforms.append(str(target_transform_id))
        else:
            option_transforms.append(str(distractors[int(cursor)]))
            cursor += 1
    return tuple(str(value) for value in option_transforms)


def _draw_centered_fit_text(
    *,
    image: Image.Image,
    text: str,
    bbox: Sequence[int | float],
    font_size_px: int,
    fill_rgb: Tuple[int, int, int],
    stroke_rgb: Tuple[int, int, int],
) -> Tuple[int, int, int, int]:
    """Draw one centered cue label, shrinking if needed."""

    draw = ImageDraw.Draw(image)
    x0, y0, x1, y1 = [int(round(float(value))) for value in bbox]
    max_w = max(1, int(x1 - x0))
    max_h = max(1, int(y1 - y0))
    font_size = max(10, int(font_size_px))
    while font_size > 10:
        font = load_font(int(font_size), bold=True)
        text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
        text_w = int(text_bbox[2] - text_bbox[0])
        text_h = int(text_bbox[3] - text_bbox[1])
        if text_w <= max_w and text_h <= max_h:
            break
        font_size -= 1
    font = load_font(int(font_size), bold=True)
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
    text_w = int(text_bbox[2] - text_bbox[0])
    text_h = int(text_bbox[3] - text_bbox[1])
    px = int(x0 + (max_w - text_w) // 2 - int(text_bbox[0]))
    py = int(y0 + (max_h - text_h) // 2 - int(text_bbox[1]))
    draw_text_traced(
        draw,
        (px, py),
        str(text),
        font=font,
        fill=tuple(int(v) for v in fill_rgb),
        stroke_fill=tuple(int(v) for v in stroke_rgb),
        stroke_width=1,
        role="icon_operation_cue_text",
        required=True,
    )
    return (int(px + text_bbox[0]), int(py + text_bbox[1]), int(px + text_bbox[2]), int(py + text_bbox[3]))


def _reference_icon_and_cue_bboxes(content_bbox: Sequence[int | float]) -> Tuple[Tuple[int, int, int, int], Tuple[int, int, int, int]]:
    x0, y0, x1, y1 = [int(round(float(value))) for value in content_bbox]
    width = max(1, int(x1 - x0))
    height = max(1, int(y1 - y0))
    cue_h = max(34, int(round(height * 0.18)))
    gap = 8
    cue_bbox = (int(x0), int(y1 - cue_h), int(x1), int(y1))
    icon_bbox = (int(x0), int(y0), int(x1), int(max(y0 + 1, cue_bbox[1] - gap)))
    square = min(int(icon_bbox[2] - icon_bbox[0]), int(icon_bbox[3] - icon_bbox[1]))
    px0 = int(icon_bbox[0] + (width - square) // 2)
    py0 = int(icon_bbox[1] + (int(icon_bbox[3] - icon_bbox[1]) - square) // 2)
    return (int(px0), int(py0), int(px0 + square), int(py0 + square)), cue_bbox


def _scene_style_trace(
    *,
    render_params: Mapping[str, Any],
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...],
) -> Dict[str, Any]:
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
            "operation_cue_font_size_px": int(render_params["operation_cue_font_size_px"]),
            "operation_cue_color_rgb": list(render_params["operation_cue_color_rgb"]),
            "operation_cue_stroke_rgb": list(render_params.get("operation_cue_stroke_rgb", render_params["panel_fill_rgb"])),
        }
    )
    return style




def _sample_scene(
    rng,
    *,
    instance_seed: int,
    render_params: Mapping[str, Any],
    pool_manifest: str,
    transform_check_size_px: int,
    params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Image.Image, Dict[str, float]]:
    """Sample and render one single-transform option-label task."""

    object_count = _resolve_object_count(params)
    labels = tuple(str(value) for value in LABEL_POOL_A_L[:object_count])
    query_id, query_probabilities = _resolve_query_id(rng, params)
    transform_id = str(_QUERY_TO_TRANSFORM[str(query_id)])
    operation_cue = str(_QUERY_TO_CUE[str(query_id)])
    answer_index = _resolve_answer_index(rng, params=params, labels=labels)
    answer_label = str(labels[int(answer_index)])
    icon_id = _sample_transform_distinct_icon(
        rng,
        pool_manifest=str(pool_manifest),
        transform_check_size_px=int(transform_check_size_px),
    )
    option_transform_ids = _option_transforms_for_answer(
        answer_index=int(answer_index),
        target_transform_id=str(transform_id),
    )
    signatures = [
        icon_transform_signature(str(icon_id), int(transform_check_size_px), str(option_transform_id))
        for option_transform_id in option_transform_ids
    ]
    if len(set(signatures)) != len(signatures):
        raise ValueError("single-transform option transforms are not visually unique")

    tint_rgb, sampled_palette_rgb = sample_single_icon_tint(
        rng,
        channel_min=int(render_params["color_channel_min"]),
        channel_max=int(render_params["color_channel_max"]),
        anchor_colors=(
            tuple(int(v) for v in render_params["background_color_rgb"]),
            tuple(int(v) for v in render_params["panel_fill_rgb"]),
            tuple(int(v) for v in render_params["panel_border_rgb"]),
            tuple(int(v) for v in render_params["header_text_rgb"]),
            tuple(int(v) for v in render_params["operation_cue_color_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    )

    reference_noise_edits, reference_noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:reference_icon",
        render_params=render_params,
    )
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
        reference_square_cell=False,
        scene_square_cells=True,
        reference_title="Reference",
        scene_title="Options",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )
    image = prepared.image
    reference_icon_slot, cue_slot = _reference_icon_and_cue_bboxes(prepared.reference_cell.content_bbox_xyxy)
    reference_sprite = render_icon_transformed_rgba(
        icon_id=str(icon_id),
        size_px=int(render_params["reference_icon_size_px"]),
        tint_rgb=tuple(int(v) for v in tint_rgb),
        transform_id=IDENTITY_TRANSFORM_ID,
        noise_edits=tuple(reference_noise_edits),
        noise_seed=int(reference_noise_seed),
    )
    reference_fitted, reference_icon_bbox = _fit_rgba_inside(reference_sprite, reference_icon_slot)
    image.alpha_composite(reference_fitted, (int(reference_icon_bbox[0]), int(reference_icon_bbox[1])))
    cue_bbox = _draw_centered_fit_text(
        image=image,
        text=str(operation_cue),
        bbox=cue_slot,
        font_size_px=int(render_params["operation_cue_font_size_px"]),
        fill_rgb=tuple(int(v) for v in render_params["operation_cue_color_rgb"]),
        stroke_rgb=tuple(int(v) for v in render_params["operation_cue_stroke_rgb"]),
    )

    scene_cells: List[Dict[str, Any]] = []
    for index, (cell, option_transform_id) in enumerate(zip(prepared.scene_cells, option_transform_ids)):
        option_noise_edits, option_noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:option_{int(index)}",
            render_params=render_params,
        )
        sprite = render_icon_transformed_rgba(
            icon_id=str(icon_id),
            size_px=int(render_params["scene_icon_size_max_px"]),
            tint_rgb=tuple(int(v) for v in tint_rgb),
            transform_id=str(option_transform_id),
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
                "transform_id": str(option_transform_id),
                "is_match": bool(int(index) == int(answer_index)),
                "tint_rgb": [int(value) for value in tint_rgb],
                "noise_edits": [dict(edit) for edit in serialize_icon_noise_edits(tuple(option_noise_edits))],
                "noise_seed": int(option_noise_seed),
                "index": int(index),
            }
        )

    if sum(1 for cell in scene_cells if bool(cell.get("is_match"))) != 1:
        raise ValueError("single-transform option scene must contain exactly one correct option")

    reference_cell = {
        "panel": "reference",
        "cell_bbox_xyxy": list(prepared.reference_cell.cell_bbox_xyxy),
        "content_bbox_xyxy": list(prepared.reference_cell.content_bbox_xyxy),
        "icon_bbox_xyxy": [int(value) for value in reference_icon_bbox],
        "operation_cue_bbox_xyxy": [int(value) for value in cue_bbox],
        "icon_id": str(icon_id),
        "transform_id": IDENTITY_TRANSFORM_ID,
        "operation_cue": str(operation_cue),
        "target_transform_id": str(transform_id),
        "tint_rgb": [int(value) for value in tint_rgb],
        "noise_edits": [dict(edit) for edit in serialize_icon_noise_edits(tuple(reference_noise_edits))],
        "noise_seed": int(reference_noise_seed),
    }

    return (
        _ScenePayload(
            object_count=int(object_count),
            cell_labels=tuple(labels),
            query_id=str(query_id),
            transform_id=str(transform_id),
            operation_cue=str(operation_cue),
            answer_label=str(answer_label),
            icon_id=str(icon_id),
            option_transform_ids=tuple(str(value) for value in option_transform_ids),
            tint_rgb=tuple(int(value) for value in tint_rgb),
            sampled_palette_rgb=tuple(sampled_palette_rgb),
            panel_geometry=panel_geometry_to_trace(prepared.layout),
            reference_cell=dict(reference_cell),
            scene_cells=tuple(dict(item) for item in scene_cells),
        ),
        image.convert("RGB"),
        dict(query_probabilities),
    )


@register_task
class IconsSingleTransformOptionsGeometricTransformResultLabelTask:
    """Select the labeled result of applying one geometric transform."""

    task_id = TASK_ID
    domain = "icons"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic transform-result option instance."""

        scene_rng = spawn_rng(int(instance_seed), "scene")
        render_params = _resolve_render_params(params, instance_seed=int(instance_seed))
        pool_manifest = str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))
        transform_check_size_px = int(
            params.get(
                "transform_check_size_px",
                group_default(_GEN_DEFAULTS, "transform_check_size_px", _DEFAULTS.transform_check_size_px),
            )
        )

        scene_payload = None
        image = None
        query_probabilities: Dict[str, float] = {}
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image, query_probabilities = _sample_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    render_params=render_params,
                    pool_manifest=str(pool_manifest),
                    transform_check_size_px=int(transform_check_size_px),
                    params=params,
                )
                break
            except Exception as exc:
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError(f"failed to generate {TASK_ID} instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_key = f"question_text_{scene_payload.query_id}"
        if question_key not in _PROMPT_DEFAULTS:
            raise ValueError(f"missing prompt default {question_key} for {self.task_id}")
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=SCENE_ID,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(_PROMPT_DEFAULTS[question_key]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        matching_cell = next(cell for cell in scene_payload.scene_cells if bool(cell.get("is_match")))
        annotation_artifacts = keyed_bbox_map_annotation(
            {
                "reference_icon": scene_payload.reference_cell["icon_bbox_xyxy"],
                "selected_option": matching_cell["cell_bbox_xyxy"],
            }
        )
        answer_gt = TypedValue(type="option_letter", value=str(scene_payload.answer_label))
        annotation_gt = TypedValue(
            type=str(annotation_artifacts["annotation_type"]),
            value=dict(annotation_artifacts["annotation_value"]),
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_single_transform_options_result_label",
                "scene_id": SCENE_ID,
                "query_id": str(scene_payload.query_id),
                "entities": [dict(scene_payload.reference_cell), *[dict(item) for item in scene_payload.scene_cells]],
                "relations": {
                    "target": "option_transform_equals_reference_after_operation",
                    "query_id": str(scene_payload.query_id),
                    "operation_cue": str(scene_payload.operation_cue),
                    "target_transform_id": str(scene_payload.transform_id),
                    "answer_label": str(scene_payload.answer_label),
                    "answer_transform_id": str(matching_cell["transform_id"]),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(scene_payload.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_id": str(self.task_id),
                    "scene_id": SCENE_ID,
                    "query_id": str(scene_payload.query_id),
                    "query_id_probabilities": dict(query_probabilities),
                    "object_count": int(scene_payload.object_count),
                    "pool_manifest": str(pool_manifest),
                    "transform_check_size_px": int(transform_check_size_px),
                    "target_transform_id": str(scene_payload.transform_id),
                    "operation_cue": str(scene_payload.operation_cue),
                    "answer_label": str(scene_payload.answer_label),
                },
            },
            "render_spec": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(scene_payload.query_id),
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
                    "reference_icon": dict(scene_payload.reference_cell),
                    "answer_label": str(scene_payload.answer_label),
                    "selected_option": dict(matching_cell),
                    "scene_cells": [dict(item) for item in scene_payload.scene_cells],
                },
            },
            "execution_trace": {
                "task_id": str(self.task_id),
                "scene_id": SCENE_ID,
                "query_id": str(scene_payload.query_id),
                "query_id_probabilities": dict(query_probabilities),
                "scene_variant": "reference_icon_with_transform_result_options",
                "question_format": "select_transformed_reference_icon_option",
                "object_count": int(scene_payload.object_count),
                "cell_labels": list(scene_payload.cell_labels),
                "answer": str(scene_payload.answer_label),
                "answer_label": str(scene_payload.answer_label),
                "icon_id": str(scene_payload.icon_id),
                "operation_cue": str(scene_payload.operation_cue),
                "target_transform_id": str(scene_payload.transform_id),
                "option_transform_ids_by_label": {
                    str(cell["label"]): str(cell["transform_id"])
                    for cell in scene_payload.scene_cells
                },
                "annotation_roles": ["reference_icon", "selected_option"],
            },
            "witness_symbolic": {
                "reference_icon_id": str(scene_payload.icon_id),
                "reference_transform_id": IDENTITY_TRANSFORM_ID,
                "target_transform_id": str(scene_payload.transform_id),
                "selected_option_label": str(scene_payload.answer_label),
                "selected_option_transform_id": str(matching_cell["transform_id"]),
                "reference_icon_bbox": list(scene_payload.reference_cell["icon_bbox_xyxy"]),
                "selected_option_bbox": list(matching_cell["cell_bbox_xyxy"]),
            },
            "projected_annotation": dict(annotation_artifacts["projected_annotation"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(scene_payload.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsSingleTransformOptionsGeometricTransformResultLabelTask", "TASK_ID"]
