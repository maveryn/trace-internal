"""Shared helpers for scene-agnostic illustration visual tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageStat

from ....core.sampling import normalize_positive_weights
from ....core.seed import spawn_rng
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.text_rendering import fit_font_to_box, load_font
from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.text_legibility import draw_text_traced
from .mixed_object_scene import (
    ObjectPlacementSpec,
    RenderedMixedObjectScene,
    choose_background_id,
    render_mixed_object_scene,
    resolve_content_bbox,
    sample_background_layout,
    sample_placements,
)
from .mixed_task_common import MIXED_QUERY_OBJECT_TYPES, positive_background_weights, positive_style_weights, serialize_mixed_scene
from .object_library import choose_object_colors


SOURCE_TASK_IDS: Tuple[str, ...] = (
    "task_illustrations__environment__on_feature_object_count",
    "task_illustrations__indoor_room__surface_object_count",
    "task_illustrations__library__books_in_section_count",
    "task_illustrations__park_playground__activity_person_count",
    "task_illustrations__transit_terminal__person_in_boarding_area_count",
    "task_illustrations__construction_site__worker_attribute_count",
)

SOURCE_SCENE_BY_TASK: Dict[str, str] = {
    "task_illustrations__environment__on_feature_object_count": "environment",
    "task_illustrations__indoor_room__surface_object_count": "indoor_room",
    "task_illustrations__library__books_in_section_count": "library",
    "task_illustrations__park_playground__activity_person_count": "park_playground",
    "task_illustrations__transit_terminal__person_in_boarding_area_count": "transit_terminal",
    "task_illustrations__construction_site__worker_attribute_count": "construction_site",
}


@dataclass(frozen=True)
class SourceIllustration:
    """One rendered source illustration used by a shared visual task."""

    image: Image.Image
    source_task_id: str
    source_scene_id: str
    source_trace: Mapping[str, Any]
    source_probabilities: Dict[str, float]


@dataclass(frozen=True)
class MixedVisualScene:
    """A mixed-object source scene with serialized object metadata."""

    scene: RenderedMixedObjectScene
    serialized_objects: Tuple[Dict[str, Any], ...]
    object_bboxes: Dict[str, list[float]]


def bbox_list(box: Sequence[float], *, dx: float = 0.0, dy: float = 0.0) -> list[float]:
    """Return a rounded pixel bbox list with an optional offset."""

    return [
        round(float(box[0]) + float(dx), 3),
        round(float(box[1]) + float(dy), 3),
        round(float(box[2]) + float(dx), 3),
        round(float(box[3]) + float(dy), 3),
    ]


def sort_bboxes_by_position(boxes: Sequence[Sequence[float]]) -> list[list[float]]:
    """Sort bboxes top-to-bottom, left-to-right."""

    return [bbox_list(box) for box in sorted(boxes, key=lambda box: (float(box[1]), float(box[0]), float(box[3]), float(box[2])))]


def default_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    """Load the active shared font for compact illustration labels."""

    return load_font(int(size), bold=bool(bold))


def draw_panel_label(
    draw: ImageDraw.ImageDraw,
    label: str,
    xy: Tuple[int, int],
    *,
    size: int = 24,
    font_family: str | None = None,
) -> None:
    """Draw a compact panel label."""

    x, y = int(xy[0]), int(xy[1])
    font = load_font(int(size), bold=True, font_family=str(font_family or "")) if font_family else default_font(int(size), bold=True)
    text = str(label)
    bbox = draw.textbbox((x, y), text, font=font)
    pad_x = 8
    pad_y = 5
    draw.rounded_rectangle(
        (bbox[0] - pad_x, bbox[1] - pad_y, bbox[2] + pad_x, bbox[3] + pad_y),
        radius=6,
        fill=(255, 255, 255),
        outline=(42, 49, 58),
        width=2,
    )
    draw_text_traced(draw,(x, y), text, fill=(22, 28, 36), font=font, role="readout", required=False)


def sample_visual_label_font_trace(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace_suffix: str,
    explicit_key: str,
    weights_key: str,
) -> Dict[str, Any]:
    """Sample one approved font family for a visual-task label role."""

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{task_id}:{namespace_suffix}",
        params=params,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
    )
    record = get_font_family_record(str(font_family))
    return {
        "font_asset_version": font_asset_version(),
        "pool": "global_approved_font_pool",
        **record.to_trace(),
    }


def draw_label_badge(
    draw: ImageDraw.ImageDraw,
    label: str,
    bbox_xyxy: Sequence[float],
    *,
    font_family: str | None = None,
    fill: Tuple[int, int, int] = (255, 255, 255),
    outline: Tuple[int, int, int] = (44, 52, 65),
    text_fill: Tuple[int, int, int] = (18, 25, 35),
    radius: int = 5,
    width: int = 2,
) -> None:
    """Draw a fitted compact label badge."""

    x0, y0, x1, y1 = [float(value) for value in bbox_xyxy]
    draw.rounded_rectangle((x0, y0, x1, y1), radius=int(radius), fill=fill, outline=outline, width=int(width))
    text = str(label)
    font = fit_font_to_box(
        draw,
        text=text,
        max_width=max(1.0, (x1 - x0) - 8.0),
        max_height=max(1.0, (y1 - y0) - 6.0),
        bold=True,
        font_family=font_family,
        min_size_px=8,
        max_size_px=int(max(8.0, (y1 - y0) - 4.0)),
        fill_ratio=1.0,
    )
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w = float(text_bbox[2] - text_bbox[0])
    text_h = float(text_bbox[3] - text_bbox[1])
    text_x = float(x0 + ((x1 - x0) - text_w) * 0.5 - float(text_bbox[0]))
    text_y = float(y0 + ((y1 - y0) - text_h) * 0.5 - float(text_bbox[1]))
    draw_text_traced(draw,(text_x, text_y), text, fill=text_fill, font=font, role="readout", required=False)


def fit_source_image(image: Image.Image, *, width: int, height: int) -> Image.Image:
    """Pad/resize a source illustration to a fixed panel."""

    return ImageOps.pad(image.convert("RGB"), (int(width), int(height)), method=Image.Resampling.LANCZOS, color=(246, 248, 250))


def image_detail_score(image: Image.Image) -> float:
    """Cheap crop-detail score used to avoid blank missing-patch crops."""

    gray = image.convert("L")
    stat = ImageStat.Stat(gray)
    variance = float(stat.var[0]) if stat.var else 0.0
    extrema = gray.getextrema()
    contrast = float(extrema[1] - extrema[0]) if extrema else 0.0
    return variance + 2.0 * contrast


def resolve_source_task(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the underlying illustration source task for visual shared tasks."""

    raw = params.get("source_task_id_support", group_default(gen_defaults, "source_task_id_support", SOURCE_TASK_IDS))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("source_task_id_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(SOURCE_TASK_IDS))
    if not support:
        raise ValueError("source_task_id_support resolved no supported tasks")
    explicit = params.get("source_task_id")
    if explicit is not None:
        selected = str(explicit)
        if selected not in set(support):
            raise ValueError(f"source_task_id must be one of {support}")
        return selected, {selected: 1.0}
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}:source_task")
    selected = str(support[int(index) % len(support)])
    probability = 1.0 / float(len(support))
    return selected, {str(value): probability for value in support}


def render_source_illustration(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    max_attempts: int,
) -> SourceIllustration:
    """Render a source illustration through one existing accepted illustration task."""

    from ...registry import create_task

    source_task_id, probabilities = resolve_source_task(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
    )
    source_params: Dict[str, Any] = {}
    source_seed = int(spawn_rng(int(instance_seed), f"{task_id}:source_seed").randint(0, 2**63 - 1))
    out = create_task(source_task_id).generate(source_seed, params=source_params, max_attempts=max(20, int(max_attempts)))
    return SourceIllustration(
        image=out.image.convert("RGB"),
        source_task_id=str(source_task_id),
        source_scene_id=str(SOURCE_SCENE_BY_TASK.get(str(source_task_id), out.scene_id)),
        source_trace=dict(out.trace_payload),
        source_probabilities=dict(probabilities),
    )


def _range_from_params(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    low_key: str,
    high_key: str,
    fallback_low: int,
    fallback_high: int,
) -> Tuple[int, int]:
    low = int(params.get(low_key, group_default(defaults, low_key, fallback_low)))
    high = int(params.get(high_key, group_default(defaults, high_key, fallback_high)))
    if low < 1 or high < low:
        raise ValueError(f"invalid {low_key}/{high_key}")
    return int(low), int(high)


def sample_count_axis(
    *,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    task_id: str,
    namespace: str,
    low_key: str,
    high_key: str,
    explicit_key: str,
    fallback_low: int,
    fallback_high: int,
    instance_seed: int,
    sampling_divisor: int = 1,
) -> Tuple[int, Dict[str, float]]:
    """Sample an integer support with deterministic seeded handling."""

    low, high = _range_from_params(params, defaults, low_key, high_key, fallback_low, fallback_high)
    support = tuple(range(int(low), int(high) + 1))
    explicit = params.get(explicit_key)
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError(f"{explicit_key} is outside configured support")
        return value, dict(uniform_probability_map(support, selected=value))
    _ = int(sampling_divisor)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{task_id}:{namespace}")
    value = int(support[int(index) % len(support)])
    return value, dict(uniform_probability_map(support))


def render_mixed_visual_scene(
    *,
    task_id: str,
    instance_seed: int,
    attempt_index: int,
    object_types_for_scene: Sequence[str],
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    fallback: Mapping[str, Any],
) -> MixedVisualScene:
    """Render a mixed-object scene and expose placements for paired visual tasks."""

    rng = spawn_rng(int(instance_seed), f"{task_id}:mixed_scene", int(attempt_index))
    canvas_width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", int(fallback["canvas_width"]))))
    canvas_height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", int(fallback["canvas_height"]))))
    margin = int(params.get("outer_margin_px", group_default(render_defaults, "outer_margin_px", int(fallback["outer_margin_px"]))))
    render_scale = int(params.get("render_scale", group_default(render_defaults, "render_scale", int(fallback["render_scale"]))))
    content_bbox = resolve_content_bbox(canvas_width=canvas_width, canvas_height=canvas_height, margin_px=margin)
    background_weights = positive_background_weights(params, render_defaults)
    background_id = choose_background_id(rng, background_weights, object_types=object_types_for_scene)
    background_layout = sample_background_layout(rng, background_id=background_id, canvas_width=canvas_width, canvas_height=canvas_height)
    placements = sample_placements(
        object_types=tuple(str(value) for value in object_types_for_scene),
        rng=rng,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        content_bbox=content_bbox,
        object_size_min_px=int(params.get("object_size_min_px", group_default(render_defaults, "object_size_min_px", int(fallback["object_size_min_px"])))),
        object_size_max_px=int(params.get("object_size_max_px", group_default(render_defaults, "object_size_max_px", int(fallback["object_size_max_px"])))),
        min_gap_px=int(params.get("object_min_gap_px", group_default(render_defaults, "object_min_gap_px", int(fallback["object_min_gap_px"])))),
        max_overlap_fraction=float(params.get("max_overlap_fraction", group_default(render_defaults, "max_overlap_fraction", float(fallback["max_overlap_fraction"])))),
        placement_max_attempts=int(params.get("placement_max_attempts", group_default(render_defaults, "placement_max_attempts", int(fallback["placement_max_attempts"])))),
        style_weights=positive_style_weights(params, render_defaults),
        background_id=str(background_id),
        background_layout=background_layout,
    )
    scene = render_mixed_object_scene(
        placements=placements,
        rng=rng,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        background_weights=background_weights,
        render_scale=render_scale,
        content_bbox=content_bbox,
        background_id=str(background_id),
        background_layout=background_layout,
    )
    serialized, object_bboxes, _part_bboxes = serialize_mixed_scene(scene)
    return MixedVisualScene(scene=scene, serialized_objects=tuple(serialized), object_bboxes=object_bboxes)


def rerender_mixed_visual_scene(
    *,
    base_scene: RenderedMixedObjectScene,
    placements: Sequence[ObjectPlacementSpec],
    task_id: str,
    instance_seed: int,
    attempt_index: int,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
) -> MixedVisualScene:
    """Render modified placements against a base scene background."""

    rng = spawn_rng(int(instance_seed), f"{task_id}:rerender", int(attempt_index))
    scene = render_mixed_object_scene(
        placements=tuple(placements),
        rng=rng,
        canvas_width=int(base_scene.canvas_width),
        canvas_height=int(base_scene.canvas_height),
        background_weights=positive_background_weights(params, render_defaults),
        render_scale=int(base_scene.render_scale),
        content_bbox=base_scene.content_bbox,
        background_id=str(base_scene.background_id),
        background_layout=dict(base_scene.background_layout),
    )
    serialized, object_bboxes, _part_bboxes = serialize_mixed_scene(scene)
    return MixedVisualScene(scene=scene, serialized_objects=tuple(serialized), object_bboxes=object_bboxes)


def sample_object_types(
    *,
    rng,
    count: int,
    support: Sequence[str] = MIXED_QUERY_OBJECT_TYPES,
) -> Tuple[str, ...]:
    """Sample object types for visual mixed-object scenes."""

    cleaned = tuple(str(value) for value in support if str(value) in set(MIXED_QUERY_OBJECT_TYPES))
    if not cleaned:
        raise ValueError("no supported illustration object types")
    return tuple(str(rng.choice(cleaned)) for _ in range(int(count)))


def normalized_variant_weights(raw: Mapping[str, Any] | None, supported: Sequence[str]) -> Dict[str, float]:
    """Normalize variant weights with a supported-key fallback."""

    if isinstance(raw, Mapping):
        weights = {str(value): float(raw.get(str(value), 0.0)) for value in supported}
    else:
        weights = {str(value): 1.0 for value in supported}
    return normalize_positive_weights(weights, default_keys=tuple(str(value) for value in supported))


__all__ = [
    "SOURCE_TASK_IDS",
    "MixedVisualScene",
    "SourceIllustration",
    "bbox_list",
    "default_font",
    "draw_label_badge",
    "draw_panel_label",
    "fit_source_image",
    "image_detail_score",
    "normalized_variant_weights",
    "render_mixed_visual_scene",
    "render_source_illustration",
    "rerender_mixed_visual_scene",
    "resolve_source_task",
    "sample_visual_label_font_trace",
    "sample_count_axis",
    "sample_object_types",
    "sort_bboxes_by_position",
]
