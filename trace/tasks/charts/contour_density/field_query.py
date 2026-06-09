"""Contour-density field reasoning tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    resolve_required_int_bounds,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import load_font, temporary_default_font_family
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin
from ..shared.label_assets import resolve_chart_entity_labels
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import (
    chart_font_asset_metadata,
    load_chart_background_defaults,
    load_chart_noise_defaults,
    sample_chart_font_family,
)


TASK_ID = "charts_contour_density_field_query_base"
SCENE_ID = "contour_density"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "nearest_region_option_label",
    "density_extremum_region_label",
    "reference_distance_extremum_label",
    "density_threshold_region_count",
    "spread_extremum_region_label",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "contour_rings",
    "filled_density",
    "scatter_contour",
)
SUPPORTED_DENSITY_EXTREMA: Tuple[str, ...] = ("highest", "lowest")
SUPPORTED_DISTANCE_EXTREMA: Tuple[str, ...] = ("nearest", "farthest")
SUPPORTED_REFERENCE_KINDS: Tuple[str, ...] = ("point", "vertical_line", "horizontal_line")
SUPPORTED_DENSITY_THRESHOLD_DIRECTIONS: Tuple[str, ...] = ("at_least", "below")
SUPPORTED_SPREAD_EXTREMA: Tuple[str, ...] = ("widest", "narrowest")
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "contour_density")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="contour_density")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="contour_density", apply_prob=0.0)

_REASONING_LOAD_BY_QUERY: Dict[str, float] = {
    "nearest_region_option_label": 0.70,
    "density_extremum_region_label": 0.62,
    "reference_distance_extremum_label": 0.76,
    "density_threshold_region_count": 0.66,
    "spread_extremum_region_label": 0.64,
}
_SCENE_LOAD_BY_VARIANT: Dict[str, float] = {
    "contour_rings": 0.64,
    "filled_density": 0.68,
    "scatter_contour": 0.72,
}

RGB = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]


@dataclass(frozen=True)
class _Region:
    region_id: str
    label: str
    option_label: str
    center_x: float
    center_y: float
    radius_x: float
    radius_y: float
    density: float
    density_level: int
    color_rgb: RGB


@dataclass(frozen=True)
class _Reference:
    kind: str
    x_value: float
    y_value: float


@dataclass(frozen=True)
class _Query:
    query_id: str
    answer: Any
    answer_type: str
    annotation_type: str
    annotation_roles: Dict[str, str]
    annotation_region_ids: Tuple[str, ...]
    density_extremum: str
    distance_extremum: str
    reference_kind: str
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    scene_variant: str
    regions: Tuple[_Region, ...]
    query: _Query
    reference: _Reference | None


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    margin_left: int
    margin_right: int
    margin_top: int
    margin_bottom: int
    grid_line_width: int
    axis_line_width: int
    tick_font_size: int
    label_font_size: int
    title_font_size: int
    marker_radius: int
    text_rgb: RGB
    muted_rgb: RGB
    axis_rgb: RGB
    grid_rgb: RGB
    plot_fill_rgb: RGB
    reference_rgb: RGB
    text_stroke_rgb: RGB
    layout_jitter: Dict[str, Any]


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    plot_bbox_px: List[float]
    region_bboxes: Dict[str, List[float]]
    option_bboxes: Dict[str, List[float]]
    reference_bboxes: Dict[str, List[float]]
    render_meta: Dict[str, Any]


def _as_rgb(value: Any, fallback: RGB) -> RGB:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
        return tuple(int(channel) for channel in fallback)
    return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[index]


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(
        resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            str(key),
            int(fallback),
            instance_seed=_render_style_seed(params),
            namespace=TASK_ID,
        )
    )


def _resolve_rgb(params: Mapping[str, Any], key: str, fallback: RGB) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _gen_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _gen_float(params: Mapping[str, Any], key: str, fallback: float) -> float:
    return float(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), float(fallback))))


def _without_sample_cursor(params: Mapping[str, Any]) -> Dict[str, Any]:
    copied = dict(params)
    copied.pop("_sample_cursor", None)
    return copied


def _resolve_axis(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    supported: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_key: str,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=tuple(str(value) for value in supported),
        task_id=TASK_ID,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_key),
        axis_namespace=str(namespace),
    )


def _resolve_query_id(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis(
        params,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_key="balanced_query_id_sampling",
        namespace="query_id",
    )


def _choice_index(params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> int:
    return int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace)))


def _balanced_choice(values: Sequence[Any], params: Mapping[str, Any], *, instance_seed: int, namespace: str) -> Any:
    support = list(values)
    if not support:
        raise ValueError(f"empty support for {namespace}")
    return support[_choice_index(params, instance_seed=int(instance_seed), namespace=str(namespace)) % len(support)]


def _option_count_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    explicit = params.get("option_count")
    raw_support = params.get("option_count_support", group_default(_GEN_DEFAULTS, "option_count_support", (4, 6)))
    if explicit is not None:
        count = int(explicit)
        if count not in {4, 6}:
            raise ValueError("option_count must be either 4 or 6 for contour-density option tasks")
        return (int(count),)
    if isinstance(raw_support, Sequence) and not isinstance(raw_support, (str, bytes)):
        support = sorted({int(value) for value in raw_support if int(value) in {4, 6}})
    else:
        support = []
    if not support:
        raise ValueError("option_count_support must contain 4 and/or 6")
    return tuple(support)


def _option_labels_for_count(option_count: int) -> Tuple[str, ...]:
    if int(option_count) not in {4, 6}:
        raise ValueError("option_count must be either 4 or 6")
    return tuple(OPTION_LABELS[: int(option_count)])


def _palette(params: Mapping[str, Any]) -> Tuple[RGB, ...]:
    raw = params.get("region_palette_rgb", _RENDER_DEFAULTS.get("region_palette_rgb", ()))
    colors: List[RGB] = []
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        for item in raw:
            if isinstance(item, Sequence) and not isinstance(item, (str, bytes)) and len(item) >= 3:
                colors.append(_as_rgb(item, (0, 0, 0)))
    return tuple(colors) if colors else (
        (37, 99, 180),
        (210, 83, 73),
        (59, 145, 99),
        (143, 91, 184),
        (216, 145, 48),
        (65, 157, 183),
        (188, 88, 135),
    )


def _region_labels(count: int, *, instance_seed: int) -> Tuple[str, ...]:
    labels = resolve_chart_entity_labels(
        spawn_rng(int(instance_seed), f"{TASK_ID}.labels"),
        count=int(count),
        min_chars=2,
        max_chars=8,
        allow_spaces=False,
    ).labels
    return tuple(str(label) for label in labels)


def _density_level_from_density(density: float) -> int:
    return max(1, min(5, int(round(float(density) * 5.0))))


def _density_from_level(level: int) -> float:
    return 0.20 + (0.15 * max(1, min(5, int(level))))


def _region_count(params: Mapping[str, Any], *, instance_seed: int) -> int:
    low, high = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="region_count_min",
        max_key="region_count_max",
        fallback_min=5,
        fallback_max=7,
        context=f"generation defaults for {TASK_ID}",
    )
    return int(
        _balanced_choice(
            list(range(int(low), int(high) + 1)),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.region_count",
        )
    )


def _scene_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return _resolve_axis(
        params,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_key="balanced_scene_variant_sampling",
        namespace="scene_variant",
    )


def _base_centers(count: int, *, rng: Any) -> List[Tuple[float, float]]:
    candidates = [
        (18.0, 24.0),
        (50.0, 18.0),
        (80.0, 28.0),
        (24.0, 72.0),
        (58.0, 56.0),
        (82.0, 76.0),
        (42.0, 84.0),
    ]
    rng.shuffle(candidates)
    centers: List[Tuple[float, float]] = []
    for x_value, y_value in candidates[: int(count)]:
        centers.append((float(x_value) + rng.uniform(-4.0, 4.0), float(y_value) + rng.uniform(-4.0, 4.0)))
    return centers


def _build_regions(
    *,
    count: int,
    labels: Sequence[str],
    option_labels: Sequence[str],
    densities: Sequence[float],
    density_levels: Sequence[int] | None = None,
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> Tuple[_Region, ...]:
    rng = spawn_rng(int(instance_seed), str(namespace))
    centers = _base_centers(int(count), rng=rng)
    colors = _palette(params)
    regions: List[_Region] = []
    for index in range(int(count)):
        density = float(densities[int(index)])
        density_level = (
            max(1, min(5, int(density_levels[int(index)])))
            if density_levels is not None and int(index) < len(density_levels)
            else _density_level_from_density(float(density))
        )
        regions.append(
            _Region(
                region_id=f"region_{index}",
                label=str(labels[int(index)]),
                option_label=str(option_labels[int(index)]) if int(index) < len(option_labels) else "",
                center_x=float(centers[int(index)][0]),
                center_y=float(centers[int(index)][1]),
                radius_x=float(rng.uniform(7.5, 12.0)),
                radius_y=float(rng.uniform(6.5, 11.5)),
                density=float(density),
                density_level=int(density_level),
                color_rgb=tuple(colors[int(index) % len(colors)]),
            )
        )
    return tuple(regions)


def _distance_to_reference(region: _Region, reference: _Reference) -> float:
    if str(reference.kind) == "point":
        return math.hypot(float(region.center_x) - float(reference.x_value), float(region.center_y) - float(reference.y_value))
    if str(reference.kind) == "vertical_line":
        return abs(float(region.center_x) - float(reference.x_value))
    if str(reference.kind) == "horizontal_line":
        return abs(float(region.center_y) - float(reference.y_value))
    raise ValueError(f"unsupported reference kind: {reference.kind}")


def _build_nearest_option_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    scene_variant, scene_probabilities = _scene_variant(params, instance_seed=int(instance_seed))
    option_count = int(
        _balanced_choice(
            _option_count_support(params),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.nearest_option.option_count",
        )
    )
    option_labels = _option_labels_for_count(int(option_count))
    answer_option = str(
        _balanced_choice(
            option_labels,
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.nearest_option.answer",
        )
    )
    answer_index = option_labels.index(str(answer_option))
    labels = tuple(option_labels)
    densities = [
        0.55 + (0.28 * float(index) / float(max(1, int(option_count) - 1)))
        for index in range(int(option_count))
    ]
    regions = list(
        _build_regions(
            count=int(option_count),
            labels=labels,
            option_labels=option_labels,
            densities=densities,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.nearest_option.regions",
        )
    )
    answer_region = regions[int(answer_index)]
    reference = _Reference(
        kind="point",
        x_value=max(5.0, min(95.0, float(answer_region.center_x) + 2.0)),
        y_value=max(5.0, min(95.0, float(answer_region.center_y) - 2.0)),
    )
    distances = {str(region.option_label): _distance_to_reference(region, reference) for region in regions}
    if min(distances, key=lambda label: (distances[label], label)) != str(answer_option):
        raise RuntimeError("nearest-option construction lost unique answer")
    query = _Query(
        query_id="nearest_region_option_label",
        answer=str(answer_option),
        answer_type="option_letter",
        annotation_type="keyed_bbox_map",
        annotation_roles={"reference_point": "reference", "selected_option_region": str(answer_region.region_id)},
        annotation_region_ids=(),
        density_extremum="",
        distance_extremum="nearest",
        reference_kind="point",
        trace={
            "option_count": int(option_count),
            "option_count_support": list(_option_count_support(params)),
            "option_region_labels": list(option_labels),
            "reference_kind": "point",
            "reference_value": {"x": round(float(reference.x_value), 3), "y": round(float(reference.y_value), 3)},
            "distance_extremum": "nearest",
            "distances_by_option": {key: round(float(value), 3) for key, value in distances.items()},
            "scene_variant_probabilities": dict(scene_probabilities),
        },
    )
    return _Dataset(scene_variant=str(scene_variant), regions=tuple(regions), query=query, reference=reference)


def _build_density_extremum_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    scene_variant, scene_probabilities = _scene_variant(params, instance_seed=int(instance_seed))
    extremum, extremum_probabilities = _resolve_axis(
        params,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_DENSITY_EXTREMA,
        explicit_key="density_extremum",
        weights_key="density_extremum_weights",
        balance_key="balanced_density_extremum_sampling",
        namespace="density_extremum",
    )
    count = _region_count(params, instance_seed=int(instance_seed))
    labels = _region_labels(int(count), instance_seed=int(instance_seed))
    answer_index = int(
        _balanced_choice(
            list(range(int(count))),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.density_extremum.answer",
        )
    )
    densities = [0.42 + (0.05 * index) for index in range(int(count))]
    if str(extremum) == "highest":
        densities[int(answer_index)] = 0.98
        for index in range(int(count)):
            if int(index) != int(answer_index):
                densities[int(index)] = min(0.78, densities[int(index)])
    else:
        densities[int(answer_index)] = 0.28
        for index in range(int(count)):
            if int(index) != int(answer_index):
                densities[int(index)] = max(0.48, densities[int(index)])
    regions = _build_regions(
        count=int(count),
        labels=labels,
        option_labels=(),
        densities=densities,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.density_extremum.regions",
    )
    density_by_label = {str(region.label): float(region.density) for region in regions}
    if str(extremum) == "highest":
        answer_label = max(density_by_label, key=lambda label: (density_by_label[label], label))
    else:
        answer_label = min(density_by_label, key=lambda label: (density_by_label[label], label))
    answer_region = next(region for region in regions if str(region.label) == str(answer_label))
    query = _Query(
        query_id="density_extremum_region_label",
        answer=str(answer_label),
        answer_type="string",
        annotation_type="keyed_bbox_map",
        annotation_roles={"answer_region": str(answer_region.region_id)},
        annotation_region_ids=(),
        density_extremum=str(extremum),
        distance_extremum="",
        reference_kind="",
        trace={
            "density_extremum": str(extremum),
            "density_extremum_phrase": "highest" if str(extremum) == "highest" else "lowest",
            "density_by_region_label": {key: round(float(value), 3) for key, value in density_by_label.items()},
            "density_extremum_probabilities": dict(extremum_probabilities),
            "scene_variant_probabilities": dict(scene_probabilities),
        },
    )
    return _Dataset(scene_variant=str(scene_variant), regions=tuple(regions), query=query, reference=None)


def _reference_for_answer(region: _Region, *, kind: str, distance_extremum: str) -> _Reference:
    if str(kind) == "point":
        if str(distance_extremum) == "nearest":
            return _Reference(kind="point", x_value=max(4.0, min(96.0, region.center_x + 2.0)), y_value=max(4.0, min(96.0, region.center_y + 2.0)))
        return _Reference(kind="point", x_value=100.0 - float(region.center_x), y_value=100.0 - float(region.center_y))
    if str(kind) == "vertical_line":
        if str(distance_extremum) == "nearest":
            return _Reference(kind="vertical_line", x_value=float(region.center_x) + 1.5, y_value=50.0)
        return _Reference(kind="vertical_line", x_value=5.0 if float(region.center_x) > 50.0 else 95.0, y_value=50.0)
    if str(kind) == "horizontal_line":
        if str(distance_extremum) == "nearest":
            return _Reference(kind="horizontal_line", x_value=50.0, y_value=float(region.center_y) + 1.5)
        return _Reference(kind="horizontal_line", x_value=50.0, y_value=5.0 if float(region.center_y) > 50.0 else 95.0)
    raise ValueError(f"unsupported reference kind: {kind}")


def _build_reference_distance_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    scene_variant, scene_probabilities = _scene_variant(params, instance_seed=int(instance_seed))
    distance_extremum, distance_probabilities = _resolve_axis(
        params,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_DISTANCE_EXTREMA,
        explicit_key="distance_extremum",
        weights_key="distance_extremum_weights",
        balance_key="balanced_distance_extremum_sampling",
        namespace="distance_extremum",
    )
    reference_kind, reference_kind_probabilities = _resolve_axis(
        params,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_REFERENCE_KINDS,
        explicit_key="reference_kind",
        weights_key="reference_kind_weights",
        balance_key="balanced_reference_kind_sampling",
        namespace="reference_kind",
    )
    count = _region_count(params, instance_seed=int(instance_seed))
    labels = _region_labels(int(count), instance_seed=int(instance_seed))
    answer_index = int(
        _balanced_choice(
            list(range(int(count))),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.reference_distance.answer",
        )
    )
    densities = [0.48 + (0.05 * (index % 5)) for index in range(int(count))]
    regions = list(
        _build_regions(
            count=int(count),
            labels=labels,
            option_labels=(),
            densities=densities,
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.reference_distance.regions",
        )
    )
    answer_region = regions[int(answer_index)]
    reference = _reference_for_answer(answer_region, kind=str(reference_kind), distance_extremum=str(distance_extremum))
    distances = {str(region.label): _distance_to_reference(region, reference) for region in regions}
    if str(distance_extremum) == "nearest":
        answer_label = min(distances, key=lambda label: (distances[label], label))
    else:
        answer_label = max(distances, key=lambda label: (distances[label], label))
    if str(answer_label) != str(answer_region.label):
        raise RuntimeError("reference-distance construction lost unique answer")
    query = _Query(
        query_id="reference_distance_extremum_label",
        answer=str(answer_label),
        answer_type="string",
        annotation_type="keyed_bbox_map",
        annotation_roles={"reference_mark": "reference", "answer_region": str(answer_region.region_id)},
        annotation_region_ids=(),
        density_extremum="",
        distance_extremum=str(distance_extremum),
        reference_kind=str(reference_kind),
        trace={
            "distance_extremum": str(distance_extremum),
            "distance_extremum_phrase": "nearest to" if str(distance_extremum) == "nearest" else "farthest from",
            "reference_kind": str(reference_kind),
            "reference_kind_phrase": {
                "point": "reference point",
                "vertical_line": "vertical reference line",
                "horizontal_line": "horizontal reference line",
            }[str(reference_kind)],
            "reference_value": {"x": round(float(reference.x_value), 3), "y": round(float(reference.y_value), 3)},
            "distances_by_region_label": {key: round(float(value), 3) for key, value in distances.items()},
            "distance_extremum_probabilities": dict(distance_probabilities),
            "reference_kind_probabilities": dict(reference_kind_probabilities),
            "scene_variant_probabilities": dict(scene_probabilities),
        },
    )
    return _Dataset(scene_variant=str(scene_variant), regions=tuple(regions), query=query, reference=reference)


def _threshold_count_support(params: Mapping[str, Any], *, region_count: int) -> Tuple[int, ...]:
    raw_support = params.get(
        "threshold_count_answer_support",
        group_default(_GEN_DEFAULTS, "threshold_count_answer_support", list(range(1, 6))),
    )
    support: List[int] = []
    if isinstance(raw_support, Sequence) and not isinstance(raw_support, (str, bytes)):
        for value in raw_support:
            try:
                support.append(int(value))
            except Exception:
                continue
    if not support:
        support = list(range(1, 6))
    filtered = sorted({int(value) for value in support if 1 <= int(value) < int(region_count)})
    if not filtered:
        filtered = list(range(1, max(2, min(5, int(region_count)))))
    return tuple(filtered)


def _build_density_threshold_count_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    scene_variant, scene_probabilities = _scene_variant(params, instance_seed=int(instance_seed))
    direction, direction_probabilities = _resolve_axis(
        params,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_DENSITY_THRESHOLD_DIRECTIONS,
        explicit_key="density_threshold_direction",
        weights_key="density_threshold_direction_weights",
        balance_key="balanced_density_threshold_direction_sampling",
        namespace="density_threshold_direction",
    )
    threshold_min, threshold_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="density_threshold_level_min",
        max_key="density_threshold_level_max",
        fallback_min=2,
        fallback_max=5,
        context=f"density threshold levels for {TASK_ID}",
    )
    level_support = list(range(max(2, int(threshold_min)), min(5, int(threshold_max)) + 1))
    if not level_support:
        level_support = [3, 4]
    threshold_level = int(
        _balanced_choice(
            level_support,
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.density_threshold.level",
        )
    )
    count = _region_count(params, instance_seed=int(instance_seed))
    answer_support = _threshold_count_support(params, region_count=int(count))
    target_count = int(
        _balanced_choice(
            answer_support,
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.density_threshold.answer_count",
        )
    )
    labels = _region_labels(int(count), instance_seed=int(instance_seed))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.density_threshold.levels")
    candidate_indices = list(range(int(count)))
    rng.shuffle(candidate_indices)
    matching_indices = set(candidate_indices[: int(target_count)])
    density_levels: List[int] = []
    for index in range(int(count)):
        if str(direction) == "at_least":
            level_choices = list(range(int(threshold_level), 6)) if index in matching_indices else list(range(1, int(threshold_level)))
        else:
            level_choices = list(range(1, int(threshold_level))) if index in matching_indices else list(range(int(threshold_level), 6))
        if not level_choices:
            raise RuntimeError("invalid threshold-level construction")
        density_levels.append(int(level_choices[rng.randrange(len(level_choices))]))
    densities = [_density_from_level(level) for level in density_levels]
    regions = _build_regions(
        count=int(count),
        labels=labels,
        option_labels=(),
        densities=densities,
        density_levels=density_levels,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.density_threshold.regions",
    )
    if str(direction) == "at_least":
        annotation_regions = tuple(region for region in regions if int(region.density_level) >= int(threshold_level))
        phrase = "at least"
        operator = ">="
    else:
        annotation_regions = tuple(region for region in regions if int(region.density_level) < int(threshold_level))
        phrase = "below"
        operator = "<"
    if len(annotation_regions) != int(target_count):
        raise RuntimeError("density-threshold construction lost target count")
    query = _Query(
        query_id="density_threshold_region_count",
        answer=int(target_count),
        answer_type="integer",
        annotation_type="bbox_set",
        annotation_roles={},
        annotation_region_ids=tuple(str(region.region_id) for region in annotation_regions),
        density_extremum="",
        distance_extremum="",
        reference_kind="",
        trace={
            "density_threshold_direction": str(direction),
            "density_threshold_phrase": str(phrase),
            "density_threshold_operator": str(operator),
            "density_threshold_level": int(threshold_level),
            "density_level_by_region_label": {str(region.label): int(region.density_level) for region in regions},
            "matching_region_labels": [str(region.label) for region in annotation_regions],
            "density_threshold_direction_probabilities": dict(direction_probabilities),
            "scene_variant_probabilities": dict(scene_probabilities),
        },
    )
    return _Dataset(scene_variant=str(scene_variant), regions=tuple(regions), query=query, reference=None)


def _build_spread_extremum_dataset(params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    scene_variant, scene_probabilities = _scene_variant(params, instance_seed=int(instance_seed))
    spread_extremum, spread_probabilities = _resolve_axis(
        params,
        instance_seed=int(instance_seed),
        supported=SUPPORTED_SPREAD_EXTREMA,
        explicit_key="spread_extremum",
        weights_key="spread_extremum_weights",
        balance_key="balanced_spread_extremum_sampling",
        namespace="spread_extremum",
    )
    count = _region_count(params, instance_seed=int(instance_seed))
    labels = _region_labels(int(count), instance_seed=int(instance_seed))
    answer_index = int(
        _balanced_choice(
            list(range(int(count))),
            params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.spread_extremum.answer",
        )
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.spread_extremum.regions")
    density_levels = [1 + ((index + rng.randrange(5)) % 5) for index in range(int(count))]
    densities = [_density_from_level(level) for level in density_levels]
    base_regions = _build_regions(
        count=int(count),
        labels=labels,
        option_labels=(),
        densities=densities,
        density_levels=density_levels,
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.spread_extremum.base_regions",
    )
    regions: List[_Region] = []
    for index, region in enumerate(base_regions):
        if str(spread_extremum) == "widest":
            radius_x = rng.uniform(13.5, 15.0) if int(index) == int(answer_index) else rng.uniform(6.0, 9.5)
            radius_y = rng.uniform(12.0, 13.8) if int(index) == int(answer_index) else rng.uniform(5.4, 8.4)
        else:
            radius_x = rng.uniform(5.1, 6.2) if int(index) == int(answer_index) else rng.uniform(8.4, 12.0)
            radius_y = rng.uniform(4.8, 5.8) if int(index) == int(answer_index) else rng.uniform(7.2, 11.2)
        regions.append(replace(region, radius_x=float(radius_x), radius_y=float(radius_y)))
    spread_by_label = {str(region.label): float(region.radius_x) * float(region.radius_y) for region in regions}
    if str(spread_extremum) == "widest":
        answer_label = max(spread_by_label, key=lambda label: (spread_by_label[label], label))
        phrase = "widest"
    else:
        answer_label = min(spread_by_label, key=lambda label: (spread_by_label[label], label))
        phrase = "narrowest"
    answer_region = next(region for region in regions if str(region.label) == str(answer_label))
    if str(answer_region.region_id) != f"region_{int(answer_index)}":
        raise RuntimeError("spread-extremum construction lost unique answer")
    query = _Query(
        query_id="spread_extremum_region_label",
        answer=str(answer_label),
        answer_type="string",
        annotation_type="keyed_bbox_map",
        annotation_roles={"answer_region": str(answer_region.region_id)},
        annotation_region_ids=(),
        density_extremum="",
        distance_extremum="",
        reference_kind="",
        trace={
            "spread_extremum": str(spread_extremum),
            "spread_extremum_phrase": str(phrase),
            "footprint_area_by_region_label": {key: round(float(value), 3) for key, value in spread_by_label.items()},
            "spread_extremum_probabilities": dict(spread_probabilities),
            "scene_variant_probabilities": dict(scene_probabilities),
        },
    )
    return _Dataset(scene_variant=str(scene_variant), regions=tuple(regions), query=query, reference=None)


def _build_dataset(query_id: str, params: Mapping[str, Any], *, instance_seed: int) -> _Dataset:
    if str(query_id) == "nearest_region_option_label":
        return _build_nearest_option_dataset(params, instance_seed=int(instance_seed))
    if str(query_id) == "density_extremum_region_label":
        return _build_density_extremum_dataset(params, instance_seed=int(instance_seed))
    if str(query_id) == "reference_distance_extremum_label":
        return _build_reference_distance_dataset(params, instance_seed=int(instance_seed))
    if str(query_id) == "density_threshold_region_count":
        return _build_density_threshold_count_dataset(params, instance_seed=int(instance_seed))
    if str(query_id) == "spread_extremum_region_label":
        return _build_spread_extremum_dataset(params, instance_seed=int(instance_seed))
    raise ValueError(f"unsupported query id: {query_id}")


def _resolve_render_params(params: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    params = {**dict(params), "_render_style_seed": int(instance_seed)}
    outer = _resolve_int(params, "outer_margin_px", 48)
    left, right, top, bottom, jitter = apply_layout_jitter_to_margins(
        left_px=_resolve_int(params, "plot_margin_left_px", 92),
        right_px=_resolve_int(params, "plot_margin_right_px", 72),
        top_px=_resolve_int(params, "plot_margin_top_px", 82),
        bottom_px=_resolve_int(params, "plot_margin_bottom_px", 86),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.layout",
    )
    if outer:
        left = max(int(left), int(outer))
        right = max(int(right), int(outer))
    return _RenderParams(
        canvas_width=_resolve_int(params, "canvas_width", 1280),
        canvas_height=_resolve_int(params, "canvas_height", 820),
        margin_left=int(left),
        margin_right=int(right),
        margin_top=int(top),
        margin_bottom=int(bottom),
        grid_line_width=_resolve_int(params, "grid_line_width_px", 1),
        axis_line_width=_resolve_int(params, "axis_line_width_px", 2),
        tick_font_size=_resolve_int(params, "tick_font_size_px", 15),
        label_font_size=_resolve_int(params, "label_font_size_px", 18),
        title_font_size=_resolve_int(params, "title_font_size_px", 26),
        marker_radius=_resolve_int(params, "reference_marker_radius_px", 8),
        text_rgb=_resolve_rgb(params, "text_color_rgb", (35, 40, 52)),
        muted_rgb=_resolve_rgb(params, "muted_text_rgb", (83, 91, 105)),
        axis_rgb=_resolve_rgb(params, "axis_color_rgb", (55, 60, 70)),
        grid_rgb=_resolve_rgb(params, "grid_color_rgb", (223, 227, 235)),
        plot_fill_rgb=_resolve_rgb(params, "plot_fill_rgb", (255, 255, 255)),
        reference_rgb=_resolve_rgb(params, "reference_rgb", (24, 26, 30)),
        text_stroke_rgb=_resolve_rgb(params, "text_stroke_rgb", (255, 255, 255)),
        layout_jitter=dict(jitter),
    )


def _plot_bbox(rp: _RenderParams) -> BBox:
    return (
        float(rp.margin_left),
        float(rp.margin_top),
        float(rp.canvas_width - rp.margin_right),
        float(rp.canvas_height - rp.margin_bottom),
    )


def _scale_point(x_value: float, y_value: float, *, plot_bbox: BBox) -> Tuple[float, float]:
    x0, y0, x1, y1 = (float(value) for value in plot_bbox)
    return (
        x0 + (float(x_value) / 100.0) * (x1 - x0),
        y1 - (float(y_value) / 100.0) * (y1 - y0),
    )


def _region_bbox(region: _Region, *, plot_bbox: BBox, scale: float = 1.0) -> List[float]:
    cx, cy = _scale_point(region.center_x, region.center_y, plot_bbox=plot_bbox)
    x0, y0, x1, y1 = (float(value) for value in plot_bbox)
    rx = (float(region.radius_x) * float(scale) / 100.0) * (x1 - x0)
    ry = (float(region.radius_y) * float(scale) / 100.0) * (y1 - y0)
    return _bbox([cx - rx, cy - ry, cx + rx, cy + ry])


def _draw_axes(draw: ImageDraw.ImageDraw, *, plot_bbox: BBox, rp: _RenderParams) -> None:
    x0, y0, x1, y1 = (float(value) for value in plot_bbox)
    draw.rectangle([x0, y0, x1, y1], fill=rp.plot_fill_rgb, outline=rp.grid_rgb, width=1)
    tick_font = load_font(int(rp.tick_font_size), bold=False)
    for tick in (0, 25, 50, 75, 100):
        sx, _ = _scale_point(float(tick), 0.0, plot_bbox=plot_bbox)
        _, sy = _scale_point(0.0, float(tick), plot_bbox=plot_bbox)
        draw.line([sx, y0, sx, y1], fill=rp.grid_rgb, width=max(1, int(rp.grid_line_width)))
        draw.line([x0, sy, x1, sy], fill=rp.grid_rgb, width=max(1, int(rp.grid_line_width)))
        draw_text_traced(draw, (sx - 8.0, y1 + 10.0), str(tick), font=tick_font, fill=rp.muted_rgb, role="readout", required=False)
        draw_text_traced(draw, (x0 - 36.0, sy - 8.0), str(tick), font=tick_font, fill=rp.muted_rgb, role="readout", required=False)
    draw.line([x0, y1, x1, y1], fill=rp.axis_rgb, width=max(1, int(rp.axis_line_width)))
    draw.line([x0, y0, x0, y1], fill=rp.axis_rgb, width=max(1, int(rp.axis_line_width)))


def _lighten(color: RGB, amount: float) -> RGB:
    return tuple(int(round(float(channel) + ((255.0 - float(channel)) * float(amount)))) for channel in color)


def _draw_region(
    draw: ImageDraw.ImageDraw,
    *,
    region: _Region,
    dataset: _Dataset,
    plot_bbox: BBox,
    rp: _RenderParams,
) -> List[float]:
    outer_bbox = _region_bbox(region, plot_bbox=plot_bbox, scale=1.9)
    density_level = max(1, min(5, int(region.density_level)))
    ring_count = int(density_level)
    if str(dataset.scene_variant) == "filled_density":
        fill = _lighten(region.color_rgb, max(0.16, 0.82 - (0.12 * float(density_level))))
        draw.ellipse(outer_bbox, fill=fill, outline=region.color_rgb, width=2)
    for ring_index in range(ring_count, 0, -1):
        scale = 0.42 + ((1.45 / float(max(1, ring_count))) * float(ring_index))
        bbox = _region_bbox(region, plot_bbox=plot_bbox, scale=scale)
        width = 1 + (1 if ring_index <= 2 or ring_index == ring_count else 0)
        draw.ellipse(bbox, outline=region.color_rgb, width=width)
    if str(dataset.scene_variant) == "scatter_contour":
        rng = spawn_rng(int(round(region.center_x * 1000 + region.center_y * 37)), f"{TASK_ID}.scatter_points.{region.region_id}")
        point_count = 5 + (3 * int(density_level))
        x0, y0, x1, y1 = (float(value) for value in plot_bbox)
        for _ in range(point_count):
            x_value = region.center_x + rng.uniform(-0.8 * region.radius_x, 0.8 * region.radius_x)
            y_value = region.center_y + rng.uniform(-0.8 * region.radius_y, 0.8 * region.radius_y)
            px, py = _scale_point(x_value, y_value, plot_bbox=plot_bbox)
            pr = 2.8
            draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=region.color_rgb, outline=(255, 255, 255), width=1)
        _ = (x0, y0, x1, y1)
    label_font = load_font(int(rp.label_font_size), bold=True)
    label = str(region.option_label or region.label)
    cx, cy = _scale_point(region.center_x, region.center_y, plot_bbox=plot_bbox)
    draw_text_traced(
        draw,
        (cx + 7.0, cy - 8.0),
        label,
        font=label_font,
        fill=rp.text_rgb,
        stroke_fill=rp.text_stroke_rgb,
        stroke_width=2,
        role="readout",
        required=False,
    )
    return outer_bbox


def _draw_density_threshold_guide(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: _Dataset,
    plot_bbox: BBox,
    rp: _RenderParams,
) -> Dict[str, Any]:
    if str(dataset.query.query_id) != "density_threshold_region_count":
        return {}
    threshold_level = int(dataset.query.trace["density_threshold_level"])
    operator = str(dataset.query.trace["density_threshold_operator"])
    label = f"Density level {operator} {threshold_level}"
    font = load_font(int(rp.tick_font_size), bold=True)
    x0, y0, x1, _ = (float(value) for value in plot_bbox)
    text_bbox = draw.textbbox((0, 0), label, font=font)
    width = float(text_bbox[2] - text_bbox[0]) + 22.0
    height = float(text_bbox[3] - text_bbox[1]) + 14.0
    bx1 = x1 - 8.0
    bx0 = max(x0 + 8.0, bx1 - width)
    by0 = max(8.0, y0 - height - 12.0)
    by1 = by0 + height
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=8, fill=(255, 255, 255), outline=rp.grid_rgb, width=1)
    draw_text_traced(
        draw,
        (bx0 + 11.0, by0 + 6.0),
        label,
        font=font,
        fill=rp.text_rgb,
        role="readout",
        required=False,
    )
    return {"density_threshold_guide_bbox_px": _bbox([bx0, by0, bx1, by1]), "density_threshold_guide_text": label}


def _draw_reference(
    draw: ImageDraw.ImageDraw,
    *,
    reference: _Reference | None,
    plot_bbox: BBox,
    rp: _RenderParams,
) -> Dict[str, List[float]]:
    if reference is None:
        return {}
    x0, y0, x1, y1 = (float(value) for value in plot_bbox)
    if str(reference.kind) == "point":
        cx, cy = _scale_point(reference.x_value, reference.y_value, plot_bbox=plot_bbox)
        radius = float(rp.marker_radius)
        bbox = _bbox([cx - radius, cy - radius, cx + radius, cy + radius])
        draw.ellipse(bbox, fill=rp.reference_rgb, outline=(255, 255, 255), width=2)
        draw.line([cx - radius * 1.6, cy, cx + radius * 1.6, cy], fill=(255, 255, 255), width=1)
        draw.line([cx, cy - radius * 1.6, cx, cy + radius * 1.6], fill=(255, 255, 255), width=1)
        return {"reference": list(bbox)}
    if str(reference.kind) == "vertical_line":
        sx, _ = _scale_point(reference.x_value, 0.0, plot_bbox=plot_bbox)
        draw.line([sx, y0, sx, y1], fill=rp.reference_rgb, width=3)
        return {"reference": _bbox([sx - 2.0, y0, sx + 2.0, y1])}
    if str(reference.kind) == "horizontal_line":
        _, sy = _scale_point(0.0, reference.y_value, plot_bbox=plot_bbox)
        draw.line([x0, sy, x1, sy], fill=rp.reference_rgb, width=3)
        return {"reference": _bbox([x0, sy - 2.0, x1, sy + 2.0])}
    raise ValueError(f"unsupported reference kind: {reference.kind}")


def _render_dataset(dataset: _Dataset, *, params: Mapping[str, Any], instance_seed: int) -> _Rendered:
    params = {**dict(params), "_render_style_seed": int(instance_seed)}
    rp = _resolve_render_params(params, instance_seed=int(instance_seed))
    background, background_meta = make_background_canvas(
        canvas_width=int(rp.canvas_width),
        canvas_height=int(rp.canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    plot_bbox = _plot_bbox(rp)
    title_font = load_font(int(rp.title_font_size), bold=True)
    draw_text_traced(
        draw,
        (float(rp.margin_left), 26.0),
        "Contour density field",
        font=title_font,
        fill=rp.text_rgb,
        role="readout",
        required=False,
    )
    _draw_axes(draw, plot_bbox=plot_bbox, rp=rp)
    threshold_guide_meta = _draw_density_threshold_guide(draw, dataset=dataset, plot_bbox=plot_bbox, rp=rp)

    entities: List[Dict[str, Any]] = []
    region_bboxes: Dict[str, List[float]] = {}
    option_bboxes: Dict[str, List[float]] = {}
    for region in dataset.regions:
        bbox = _draw_region(draw, region=region, dataset=dataset, plot_bbox=plot_bbox, rp=rp)
        region_bboxes[str(region.region_id)] = list(bbox)
        if str(region.option_label):
            option_bboxes[str(region.option_label)] = list(bbox)
        entities.append(
            {
                "entity_id": str(region.region_id),
                "entity_type": "contour_density_region",
                "bbox_px": list(bbox),
                "attrs": {
                    "label": str(region.label),
                    "option_label": str(region.option_label),
                    "center": [round(float(region.center_x), 3), round(float(region.center_y), 3)],
                    "density": round(float(region.density), 3),
                    "density_level": int(region.density_level),
                    "radius": [round(float(region.radius_x), 3), round(float(region.radius_y), 3)],
                },
            }
        )
    reference_bboxes = _draw_reference(draw, reference=dataset.reference, plot_bbox=plot_bbox, rp=rp)
    if reference_bboxes:
        entities.append(
            {
                "entity_id": "reference",
                "entity_type": "contour_density_reference",
                "bbox_px": list(reference_bboxes["reference"]),
                "attrs": {
                    "kind": str(dataset.reference.kind if dataset.reference else ""),
                    "x_value": round(float(dataset.reference.x_value if dataset.reference else 0), 3),
                    "y_value": round(float(dataset.reference.y_value if dataset.reference else 0), 3),
                },
            }
        )
    image, post_noise_meta = apply_post_image_noise(
        image,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    return _Rendered(
        image=image,
        entities=tuple(entities),
        plot_bbox_px=_bbox(plot_bbox),
        region_bboxes=dict(region_bboxes),
        option_bboxes=dict(option_bboxes),
        reference_bboxes=dict(reference_bboxes),
        render_meta={
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "layout_jitter": dict(rp.layout_jitter),
            **dict(threshold_guide_meta),
        },
    )


def _annotation_map(dataset: _Dataset, rendered: _Rendered) -> Dict[str, List[float]]:
    annotation: Dict[str, List[float]] = {}
    for role, entity_id in dataset.query.annotation_roles.items():
        if str(entity_id) == "reference":
            box = rendered.reference_bboxes.get("reference")
        else:
            box = rendered.region_bboxes.get(str(entity_id))
        if box is None:
            raise RuntimeError(f"missing annotation bbox for role {role}: {entity_id}")
        annotation[str(role)] = list(box)
    return annotation


def _annotation_bbox_set(dataset: _Dataset, rendered: _Rendered) -> List[List[float]]:
    bboxes: List[List[float]] = []
    for region_id in dataset.query.annotation_region_ids:
        box = rendered.region_bboxes.get(str(region_id))
        if box is None:
            raise RuntimeError(f"missing bbox-set annotation for region: {region_id}")
        bboxes.append(list(box))
    return bboxes


def _projected_annotation_payload(annotation_type: str, annotation: Any, dataset: _Dataset) -> Dict[str, Any]:
    if str(annotation_type) == "bbox_set":
        return {
            "type": "bbox_set",
            "bbox_set": [list(value) for value in annotation],
            "pixel_bbox_set": [list(value) for value in annotation],
            "annotation_region_ids": list(dataset.query.annotation_region_ids),
        }
    if str(annotation_type) == "keyed_bbox_map":
        return {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": {key: list(value) for key, value in annotation.items()},
            "pixel_keyed_bbox_map": {key: list(value) for key, value in annotation.items()},
            "annotation_roles": dict(dataset.query.annotation_roles),
        }
    raise ValueError(f"unsupported annotation type: {annotation_type}")


def _regions_trace(dataset: _Dataset) -> Dict[str, Dict[str, Any]]:
    return {
        str(region.label): {
            "region_id": str(region.region_id),
            "option_label": str(region.option_label),
            "center": [round(float(region.center_x), 3), round(float(region.center_y), 3)],
            "density": round(float(region.density), 3),
            "density_level": int(region.density_level),
            "radius": [round(float(region.radius_x), 3), round(float(region.radius_y), 3)],
        }
        for region in dataset.regions
    }


class ChartsContourDensityFieldQueryTask:
    """Answer contour-density field questions from synthetic scientific plots."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "contour_density"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities = _resolve_query_id(params, instance_seed=int(instance_seed))
        dataset: _Dataset | None = None
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                attempt_params = {**dict(params), "_attempt_index": int(attempt_index)}
                dataset = _build_dataset(str(query_id), attempt_params, instance_seed=int(instance_seed) + int(attempt_index))
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        chart_font_family = sample_chart_font_family(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.chart_font",
            params=params,
        )
        with temporary_default_font_family(str(chart_font_family)):
            rendered = _render_dataset(dataset, params=params, instance_seed=int(instance_seed))
        if str(dataset.query.annotation_type) == "bbox_set":
            annotation = _annotation_bbox_set(dataset, rendered)
        else:
            annotation = _annotation_map(dataset, rendered)

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "answer_hint_label",
                "answer_hint_option",
                "answer_hint_count",
                "annotation_hint_nearest_region_option_label",
                "annotation_hint_density_extremum_region_label",
                "annotation_hint_reference_distance_extremum_label",
                "annotation_hint_density_threshold_region_count",
                "annotation_hint_spread_extremum_region_label",
                "json_example_nearest_region_option_label",
                "json_example_density_extremum_region_label",
                "json_example_reference_distance_extremum_label",
                "json_example_density_threshold_region_count",
                "json_example_spread_extremum_region_label",
                "json_example_answer_only_nearest_region_option_label",
                "json_example_answer_only_density_extremum_region_label",
                "json_example_answer_only_reference_distance_extremum_label",
                "json_example_answer_only_density_threshold_region_count",
                "json_example_answer_only_spread_extremum_region_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        if str(dataset.query.answer_type) == "option_letter":
            answer_hint_key = "answer_hint_option"
        elif str(dataset.query.answer_type) == "integer":
            answer_hint_key = "answer_hint_count"
        else:
            answer_hint_key = "answer_hint_label"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(dataset.query.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "density_extremum_phrase": str(dataset.query.trace.get("density_extremum_phrase", "")),
                "density_threshold_phrase": str(dataset.query.trace.get("density_threshold_phrase", "")),
                "density_threshold_operator": str(dataset.query.trace.get("density_threshold_operator", "")),
                "density_threshold_level": str(dataset.query.trace.get("density_threshold_level", "")),
                "distance_extremum_phrase": str(dataset.query.trace.get("distance_extremum_phrase", "")),
                "reference_kind_phrase": str(dataset.query.trace.get("reference_kind_phrase", "")),
                "spread_extremum_phrase": str(dataset.query.trace.get("spread_extremum_phrase", "")),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{dataset.query.query_id}"]),
                "answer_hint": str(prompt_defaults[answer_hint_key]),
                "json_example": str(prompt_defaults[f"json_example_{dataset.query.query_id}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{dataset.query.query_id}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_value = int(dataset.query.answer) if str(dataset.query.answer_type) == "integer" else str(dataset.query.answer)
        answer_gt = TypedValue(type=str(dataset.query.answer_type), value=answer_value)
        if str(dataset.query.annotation_type) == "bbox_set":
            annotation_gt = TypedValue(type="bbox_set", value=[list(value) for value in annotation])
        else:
            annotation_gt = TypedValue(type="keyed_bbox_map", value={key: list(value) for key, value in annotation.items()})
        region_trace = _regions_trace(dataset)
        projected_annotation = _projected_annotation_payload(str(dataset.query.annotation_type), annotation, dataset)
        trace_payload = {
            "scene_ir": {
                "scene_kind": "chart_contour_density",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_id": str(dataset.query.query_id),
                    "scene_variant": str(dataset.scene_variant),
                    "answer": answer_value,
                    "annotation_roles": dict(dataset.query.annotation_roles),
                    "annotation_region_ids": list(dataset.query.annotation_region_ids),
                },
            },
            "query_spec": {
                "query_id": str(dataset.query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(dataset.query.query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(dataset.scene_variant),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "region_count": int(len(dataset.regions)),
                    **dict(dataset.query.trace),
                },
            },
            "render_spec": {
                "canvas_width": int(rendered.image.size[0]),
                "canvas_height": int(rendered.image.size[1]),
                "coord_space": "pixel",
                "scene_variant": str(dataset.scene_variant),
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "font_assets": chart_font_asset_metadata(str(chart_font_family)),
                **dict(rendered.render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "region_bboxes_px": dict(rendered.region_bboxes),
                "option_bboxes_px": dict(rendered.option_bboxes),
                "reference_bboxes_px": dict(rendered.reference_bboxes),
            },
            "execution_trace": {
                "query_id": str(dataset.query.query_id),
                "scene_id": SCENE_ID,
                "scene_variant": str(dataset.scene_variant),
                "question_format": "contour_density_field_query",
                "answer": answer_value,
                "answer_type": str(dataset.query.answer_type),
                "annotation_type": str(dataset.query.annotation_type),
                "region_count": int(len(dataset.regions)),
                "region_labels": [str(region.label) for region in dataset.regions],
                "regions": dict(region_trace),
                "annotation_roles": dict(dataset.query.annotation_roles),
                "annotation_region_ids": list(dataset.query.annotation_region_ids),
                "query_id_probabilities": dict(query_id_probabilities),
                **dict(dataset.query.trace),
            },
            "witness_symbolic": {
                "type": "contour_density_witness",
                "annotation_type": str(dataset.query.annotation_type),
                "annotation_roles": dict(dataset.query.annotation_roles),
                "annotation_region_ids": list(dataset.query.annotation_region_ids),
                "answer": answer_value,
            },
            "projected_annotation": dict(projected_annotation),
        }
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(len(dataset.regions)), [5, 7]),
                "reasoning_load": clamp_unit_interval(float(_REASONING_LOAD_BY_QUERY[str(dataset.query.query_id)])),
                "scene_variant_load": float(_SCENE_LOAD_BY_VARIANT[str(dataset.scene_variant)]),
            },
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsContourDensityNearestRegionOptionLabelTask(FixedChartQueryVariantTaskMixin, ChartsContourDensityFieldQueryTask):
    """Choose the option region nearest to a marked reference point."""

    task_id = "task_charts__contour_density__nearest_region_option_label"
    fixed_query_id = "nearest_region_option_label"


@register_task
class ChartsContourDensityDensityExtremumRegionLabelTask(FixedChartQueryVariantTaskMixin, ChartsContourDensityFieldQueryTask):
    """Return the region label with the highest or lowest density."""

    task_id = "task_charts__contour_density__density_extremum_region_label"
    fixed_query_id = "density_extremum_region_label"


@register_task
class ChartsContourDensityReferenceDistanceExtremumLabelTask(FixedChartQueryVariantTaskMixin, ChartsContourDensityFieldQueryTask):
    """Return the region label nearest to or farthest from a reference mark."""

    task_id = "task_charts__contour_density__reference_distance_extremum_label"
    fixed_query_id = "reference_distance_extremum_label"


@register_task
class ChartsContourDensityDensityThresholdRegionCountTask(FixedChartQueryVariantTaskMixin, ChartsContourDensityFieldQueryTask):
    """Count regions whose visible density level satisfies a threshold."""

    task_id = "task_charts__contour_density__density_threshold_region_count"
    fixed_query_id = "density_threshold_region_count"


@register_task
class ChartsContourDensitySpreadExtremumRegionLabelTask(FixedChartQueryVariantTaskMixin, ChartsContourDensityFieldQueryTask):
    """Return the region label with the widest or narrowest visible footprint."""

    task_id = "task_charts__contour_density__spread_extremum_region_label"
    fixed_query_id = "spread_extremum_region_label"


__all__ = [
    "ChartsContourDensityDensityExtremumRegionLabelTask",
    "ChartsContourDensityDensityThresholdRegionCountTask",
    "ChartsContourDensityFieldQueryTask",
    "ChartsContourDensityNearestRegionOptionLabelTask",
    "ChartsContourDensityReferenceDistanceExtremumLabelTask",
    "ChartsContourDensitySpreadExtremumRegionLabelTask",
    "SUPPORTED_DENSITY_THRESHOLD_DIRECTIONS",
    "SUPPORTED_QUERY_IDS",
    "SUPPORTED_SCENE_VARIANTS",
    "SUPPORTED_SPREAD_EXTREMA",
]
