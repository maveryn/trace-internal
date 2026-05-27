"""Size-encoded chart comparison task."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

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
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.render_variation import apply_layout_jitter_to_margins, resolve_render_rgb
from ...shared.text_rendering import fit_font_to_box, load_font, resolve_text_stroke_fill
from ..shared.complexity import (
    build_chart_complexity,
    clamp_unit_interval,
    normalize_int_with_bounds,
    resolve_chart_complexity_weights,
)
from ..shared.fixed_query_task import FixedChartQueryVariantTaskMixin
from ..shared.labeled_chart_common import resolve_chart_axis_variant
from ..shared.visual_defaults import load_chart_background_defaults, load_chart_noise_defaults


TASK_ID = "charts_size_encoding_comparison_label_base"
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "filtered_item_extremum_label",
    "reference_size_neighbor_label",
    "category_total_extremum_label",
)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "rect_word_cloud",
    "circle_word_cloud",
    "packed_bubble_cloud",
    "small_multiple_bubble_cloud",
)
SUPPORTED_EXTREMUM_DIRECTIONS: Tuple[str, ...] = ("largest", "smallest")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("charts", "size_encoding")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_chart_background_defaults(task_group="size_encoding")
POST_IMAGE_NOISE_DEFAULTS = load_chart_noise_defaults(task_group="size_encoding", apply_prob=0.0)
_COMPLEXITY_WEIGHTS = resolve_chart_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)

_REASONING_LOAD_BY_VARIANT: Dict[str, float] = {
    "filtered_item_extremum_label": 0.44,
    "reference_size_neighbor_label": 0.72,
    "category_total_extremum_label": 0.86,
}
_SCENE_VARIANT_LOADS: Dict[str, float] = {
    "rect_word_cloud": 0.22,
    "circle_word_cloud": 0.34,
    "packed_bubble_cloud": 0.40,
    "small_multiple_bubble_cloud": 0.72,
}

_CATEGORY_POOL: Tuple[str, ...] = (
    "Coastal",
    "Metro",
    "Highland",
    "Campus",
    "Market",
    "Harbor",
    "Forest",
    "Desert",
)
_ITEM_LABEL_POOL: Tuple[str, ...] = (
    "Aero",
    "Bela",
    "Cair",
    "Dove",
    "Eden",
    "Fenn",
    "Gala",
    "Holt",
    "Ibis",
    "Juno",
    "Kora",
    "Luma",
    "Mica",
    "Nori",
    "Opal",
    "Pine",
    "Quay",
    "Rune",
    "Sage",
    "Tide",
    "Vale",
    "Wisp",
    "Xeno",
    "Yara",
    "Zest",
    "Argo",
    "Brio",
    "Cove",
    "Dusk",
    "Echo",
    "Flux",
    "Glen",
    "Haze",
    "Isle",
    "Jade",
    "Kite",
    "Lark",
    "Muse",
    "Nova",
    "Oren",
)

BBox = Tuple[float, float, float, float]
RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class _Item:
    item_id: str
    label: str
    category: str
    panel: str
    value: int


@dataclass(frozen=True)
class _Query:
    query_variant: str
    answer: str
    evidence_item_ids: Tuple[str, ...]
    evidence_panel_labels: Tuple[str, ...]
    evidence_category_labels: Tuple[str, ...]
    category_label: str
    panel_label: str
    reference_label: str
    extremum_direction: str
    trace: Dict[str, Any]


@dataclass(frozen=True)
class _Dataset:
    items: Tuple[_Item, ...]
    categories: Tuple[str, ...]
    panels: Tuple[str, ...]
    query: _Query


@dataclass(frozen=True)
class _Rendered:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    item_bboxes: Dict[str, List[float]]
    panel_title_bboxes: Dict[str, List[float]]
    category_legend_bboxes: Dict[str, List[float]]
    plot_bbox_px: List[float]
    render_meta: Dict[str, Any]


def _resolve_query_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_QUERY_VARIANTS,
        task_id=TASK_ID,
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
    )


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    query_variant: str,
    instance_seed: int,
) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        task_id=TASK_ID,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_extremum_direction(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_chart_axis_variant(
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_EXTREMUM_DIRECTIONS,
        task_id=TASK_ID,
        explicit_key="extremum_direction",
        weights_key="extremum_direction_weights",
        balance_flag_key="balanced_extremum_direction_sampling",
        axis_namespace="extremum_direction",
    )


def _resolve_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _render_style_seed(params: Mapping[str, Any]) -> int:
    try:
        return int(params.get("_render_style_seed", params.get("_sample_cursor", 0)) or 0)
    except Exception:
        return 0


def _resolve_rgb(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> RGB:
    return resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        str(key),
        fallback,
        instance_seed=_render_style_seed(params),
        namespace=TASK_ID,
    )


def _category_palette(params: Mapping[str, Any], category_count: int) -> Tuple[RGB, ...]:
    raw = params.get("category_palette_rgb", group_default(_RENDER_DEFAULTS, "category_palette_rgb", []))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) < int(category_count):
        raise ValueError("category_palette_rgb must contain enough RGB colors")
    colors: List[RGB] = []
    for value in raw[: int(category_count)]:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 3:
            raise ValueError("category_palette_rgb entries must be RGB sequences")
        colors.append((int(value[0]), int(value[1]), int(value[2])))
    return tuple(colors)


def _lighten(color: RGB, factor: float) -> RGB:
    factor = max(0.0, min(1.0, float(factor)))
    return tuple(int(round(int(channel) + ((255 - int(channel)) * factor))) for channel in color)  # type: ignore[return-value]


def _darken(color: RGB, factor: float) -> RGB:
    factor = max(0.0, min(1.0, float(factor)))
    return tuple(int(round(int(channel) * factor)) for channel in color)  # type: ignore[return-value]


def _text_bbox(draw: ImageDraw.ImageDraw, xy: Tuple[float, float], text: str, font: ImageFont.ImageFont, *, stroke_width: int = 0) -> BBox:
    try:
        bbox = draw.textbbox(xy, str(text), font=font, stroke_width=max(0, int(stroke_width)))
        return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        x, y = float(xy[0]), float(xy[1])
        return (x, y, x + float(width), y + float(height))


def _center_text(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    fill: RGB,
    stroke_width: int = 0,
    stroke_fill: RGB | None = None,
) -> List[float]:
    bbox0 = _text_bbox(draw, (0.0, 0.0), str(text), font, stroke_width=stroke_width)
    width = float(bbox0[2] - bbox0[0])
    height = float(bbox0[3] - bbox0[1])
    x = float(center[0]) - (width / 2.0) - float(bbox0[0])
    y = float(center[1]) - (height / 2.0) - float(bbox0[1])
    draw.text(
        (x, y),
        str(text),
        font=font,
        fill=tuple(int(channel) for channel in fill),
        stroke_width=max(0, int(stroke_width)),
        stroke_fill=tuple(int(channel) for channel in (stroke_fill or resolve_text_stroke_fill(fill))),
    )
    return [float(value) for value in _text_bbox(draw, (x, y), str(text), font, stroke_width=stroke_width)]


def _format_bbox(bbox: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in bbox[:4]]


def _items_by_category(items: Sequence[_Item]) -> Dict[str, List[_Item]]:
    grouped: Dict[str, List[_Item]] = {}
    for item in items:
        grouped.setdefault(str(item.category), []).append(item)
    return grouped


def _choose_index(length: int, *, params: Mapping[str, Any], instance_seed: int, namespace: str) -> int:
    if int(length) <= 0:
        raise ValueError(f"empty support for {namespace}")
    if params.get("_sample_cursor") is not None:
        return abs(int(params["_sample_cursor"])) % int(length)
    rng = spawn_rng(int(instance_seed), str(namespace))
    return int(rng.randrange(0, int(length)))


def _extreme(items: Sequence[_Item], direction: str) -> Tuple[_Item, int]:
    ordered = sorted(items, key=lambda item: (int(item.value), str(item.label)))
    if str(direction) == "largest":
        winner = ordered[-1]
        runner_up = ordered[-2]
    elif str(direction) == "smallest":
        winner = ordered[0]
        runner_up = ordered[1]
    else:
        raise ValueError(f"unsupported extremum direction: {direction}")
    return winner, abs(int(winner.value) - int(runner_up.value))


def _outside_extreme_count(*, items: Sequence[_Item], winner: _Item, direction: str) -> int:
    if str(direction) == "largest":
        return sum(1 for item in items if str(item.category) != str(winner.category) and int(item.value) > int(winner.value))
    if str(direction) == "smallest":
        return sum(1 for item in items if str(item.category) != str(winner.category) and int(item.value) < int(winner.value))
    raise ValueError(f"unsupported extremum direction: {direction}")


def _sample_categories(*, count: int, instance_seed: int) -> Tuple[str, ...]:
    values = list(_CATEGORY_POOL)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.categories")
    rng.shuffle(values)
    return tuple(str(value) for value in values[: int(count)])


def _sample_labels(*, count: int, instance_seed: int) -> Tuple[str, ...]:
    values = list(_ITEM_LABEL_POOL)
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.item_labels")
    rng.shuffle(values)
    if int(count) > len(values):
        raise ValueError("item label pool is too small for requested count")
    return tuple(str(value) for value in values[: int(count)])


def _panel_labels(panel_count: int, *, instance_seed: int) -> Tuple[str, ...]:
    if int(panel_count) <= 1:
        return ("Overall",)
    base_year = 2018 + (abs(int(instance_seed)) % 4)
    return tuple(str(int(base_year) + int(index)) for index in range(int(panel_count)))


def _sample_items(
    *,
    categories: Sequence[str],
    panels: Sequence[str],
    item_count_by_panel: Mapping[str, int],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[_Item, ...]:
    value_min, value_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="value_min",
        max_key="value_max",
        fallback_min=12,
        fallback_max=99,
        context=f"generation defaults for {TASK_ID}",
    )
    total_items = int(sum(int(value) for value in item_count_by_panel.values()))
    labels = _sample_labels(count=int(total_items), instance_seed=int(instance_seed))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.items")
    items: List[_Item] = []
    label_index = 0
    for panel_index, panel in enumerate(panels):
        count = int(item_count_by_panel[str(panel)])
        panel_categories = list(categories)
        rng.shuffle(panel_categories)
        assigned_categories = [panel_categories[index % len(panel_categories)] for index in range(count)]
        rng.shuffle(assigned_categories)
        for local_index in range(count):
            items.append(
                _Item(
                    item_id=f"item_{len(items):02d}",
                    label=str(labels[label_index]),
                    category=str(assigned_categories[local_index]),
                    panel=str(panel),
                    value=int(rng.randint(int(value_min), int(value_max))),
                )
            )
            label_index += 1
        # Nudge one item per category in each panel so small groups are less likely to tie.
        del panel_index
    return tuple(items)


def _build_query(
    *,
    items: Sequence[_Item],
    categories: Sequence[str],
    panels: Sequence[str],
    query_variant: str,
    extremum_direction: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Query:
    winner_gap_min = _resolve_int(params, "winner_gap_min", 8)
    neighbor_gap_min = _resolve_int(params, "neighbor_gap_min", 5)
    category_total_gap_min = _resolve_int(params, "category_total_gap_min", 18)

    if str(query_variant) == "filtered_item_extremum_label":
        filtered_gap_min = _resolve_int(params, "filtered_item_winner_gap_min", int(winner_gap_min))
        filtered_gap_max = _resolve_int(params, "filtered_item_winner_gap_max", 10_000)
        outside_extreme_min = _resolve_int(params, "filtered_item_outside_extreme_min", 0)
        feasible: List[Tuple[str, List[_Item], _Item, int, int]] = []
        for category, group in sorted(_items_by_category(items).items()):
            if len(group) < 2:
                continue
            candidate_winner, candidate_gap = _extreme(group, str(extremum_direction))
            if int(candidate_gap) < int(filtered_gap_min) or int(candidate_gap) > int(filtered_gap_max):
                continue
            candidate_outside_extreme_count = _outside_extreme_count(
                items=items,
                winner=candidate_winner,
                direction=str(extremum_direction),
            )
            if int(candidate_outside_extreme_count) < int(outside_extreme_min):
                continue
            feasible.append(
                (
                    str(category),
                    list(group),
                    candidate_winner,
                    int(candidate_gap),
                    int(candidate_outside_extreme_count),
                )
            )
        if not feasible:
            raise ValueError("no feasible filtered extremum category")
        category, group, winner, gap, outside_extreme_count = feasible[
            _choose_index(
                len(feasible),
                params=params,
                instance_seed=instance_seed,
                namespace=f"{TASK_ID}.filtered_category",
            )
        ]
        return _Query(
            query_variant=str(query_variant),
            answer=str(winner.label),
            evidence_item_ids=(str(winner.item_id),),
            evidence_panel_labels=(),
            evidence_category_labels=(),
            category_label=str(category),
            panel_label="",
            reference_label="",
            extremum_direction=str(extremum_direction),
            trace={
                "winner_gap": int(gap),
                "candidate_count": int(len(group)),
                "outside_extreme_count": int(outside_extreme_count),
            },
        )

    if str(query_variant) == "reference_size_neighbor_label":
        feasible_categories: List[Tuple[str, List[Tuple[_Item, List[Tuple[int, str, _Item]]]]]] = []
        for category, group in sorted(_items_by_category(items).items()):
            if len(group) < 3:
                continue
            feasible_references: List[Tuple[_Item, List[Tuple[int, str, _Item]]]] = []
            for reference in group:
                candidates = [item for item in group if str(item.item_id) != str(reference.item_id)]
                distances = sorted(
                    ((abs(int(item.value) - int(reference.value)), str(item.label), item) for item in candidates),
                    key=lambda row: (int(row[0]), str(row[1])),
                )
                if len(distances) >= 2 and int(distances[1][0]) - int(distances[0][0]) >= int(neighbor_gap_min):
                    feasible_references.append((reference, distances))
            if feasible_references:
                feasible_categories.append((str(category), feasible_references))
        if not feasible_categories:
            raise ValueError("reference-neighbor gap too small")
        category, feasible_references = feasible_categories[
            _choose_index(
                len(feasible_categories),
                params=params,
                instance_seed=instance_seed,
                namespace=f"{TASK_ID}.neighbor_category",
            )
        ]
        reference, distances = feasible_references[
            _choose_index(
                len(feasible_references),
                params=params,
                instance_seed=instance_seed,
                namespace=f"{TASK_ID}.neighbor_reference",
            )
        ]
        answer_item = distances[0][2]
        return _Query(
            query_variant=str(query_variant),
            answer=str(answer_item.label),
            evidence_item_ids=(str(reference.item_id), str(answer_item.item_id)),
            evidence_panel_labels=(),
            evidence_category_labels=(),
            category_label=str(category),
            panel_label="",
            reference_label=str(reference.label),
            extremum_direction="closest",
            trace={
                "reference_label": str(reference.label),
                "reference_value": int(reference.value),
                "nearest_distance": int(distances[0][0]),
                "nearest_gap": int(distances[1][0]) - int(distances[0][0]),
                "candidate_count": int(len(distances)),
            },
        )
    if str(query_variant) == "category_total_extremum_label":
        totals = {
            str(category): int(sum(int(item.value) for item in items if str(item.category) == str(category)))
            for category in categories
        }
        ordered = sorted(totals.items(), key=lambda row: (int(row[1]), str(row[0])))
        if str(extremum_direction) == "largest":
            answer_category, answer_total = ordered[-1]
            runner_total = ordered[-2][1]
        elif str(extremum_direction) == "smallest":
            answer_category, answer_total = ordered[0]
            runner_total = ordered[1][1]
        else:
            raise ValueError(f"unsupported extremum direction: {extremum_direction}")
        gap = abs(int(answer_total) - int(runner_total))
        if int(gap) < int(category_total_gap_min):
            raise ValueError("category-total gap too small")
        evidence_ids = tuple(str(item.item_id) for item in items if str(item.category) == str(answer_category))
        return _Query(
            query_variant=str(query_variant),
            answer=str(answer_category),
            evidence_item_ids=evidence_ids,
            evidence_panel_labels=(),
            evidence_category_labels=(str(answer_category),),
            category_label=str(answer_category),
            panel_label="",
            reference_label="",
            extremum_direction=str(extremum_direction),
            trace={"category_totals": dict(totals), "winner_gap": int(gap), "winner_total": int(answer_total)},
        )

    raise ValueError(f"unsupported query variant: {query_variant}")


def _build_dataset(
    *,
    query_variant: str,
    scene_variant: str,
    extremum_direction: str,
    params: Mapping[str, Any],
    instance_seed: int,
    attempt_index: int,
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.dataset.{int(attempt_index)}")
    cat_min, cat_max = resolve_required_int_bounds(
        params,
        _GEN_DEFAULTS,
        min_key="category_count_min",
        max_key="category_count_max",
        fallback_min=3,
        fallback_max=5,
        context=f"generation defaults for {TASK_ID}",
    )
    category_count = int(rng.randint(int(cat_min), int(cat_max)))
    categories = _sample_categories(count=int(category_count), instance_seed=int(instance_seed) + int(attempt_index))

    if str(scene_variant) == "small_multiple_bubble_cloud":
        panel_min, panel_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="panel_count_min",
            max_key="panel_count_max",
            fallback_min=2,
            fallback_max=4,
            context=f"generation defaults for {TASK_ID}",
        )
        item_min, item_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="panel_item_count_min",
            max_key="panel_item_count_max",
            fallback_min=7,
            fallback_max=10,
            context=f"generation defaults for {TASK_ID}",
        )
        panel_count = int(rng.randint(int(panel_min), int(panel_max)))
        panels = _panel_labels(int(panel_count), instance_seed=int(instance_seed))
        item_count_by_panel = {str(panel): int(rng.randint(int(item_min), int(item_max))) for panel in panels}
    else:
        item_min, item_max = resolve_required_int_bounds(
            params,
            _GEN_DEFAULTS,
            min_key="item_count_min",
            max_key="item_count_max",
            fallback_min=18,
            fallback_max=30,
            context=f"generation defaults for {TASK_ID}",
        )
        panels = ("Overall",)
        item_count_by_panel = {"Overall": int(rng.randint(int(item_min), int(item_max)))}

    total_item_count_min = _resolve_int(params, "total_item_count_min", 1)
    total_item_count_max = _resolve_int(params, "total_item_count_max", 10_000)
    total_item_count = int(sum(int(value) for value in item_count_by_panel.values()))
    if int(total_item_count) < int(total_item_count_min):
        raise ValueError("total item count below minimum")
    if int(total_item_count) > int(total_item_count_max):
        raise ValueError("total item count above maximum")

    items = _sample_items(
        categories=categories,
        panels=panels,
        item_count_by_panel=item_count_by_panel,
        params=params,
        instance_seed=int(instance_seed) + (997 * int(attempt_index)),
    )
    query = _build_query(
        items=items,
        categories=categories,
        panels=panels,
        query_variant=str(query_variant),
        extremum_direction=str(extremum_direction),
        params=params,
        instance_seed=int(instance_seed) + (131 * int(attempt_index)),
    )
    return _Dataset(items=tuple(items), categories=tuple(categories), panels=tuple(panels), query=query)


def _cell_centers(
    bbox: BBox,
    *,
    count: int,
    instance_seed: int,
    namespace: str,
    circular: bool = False,
) -> List[Tuple[float, float, float, float]]:
    x1, y1, x2, y2 = (float(value) for value in bbox)
    width = max(1.0, x2 - x1)
    height = max(1.0, y2 - y1)
    cols = max(1, int(math.ceil(math.sqrt(float(count) * 1.35))))
    rows = max(1, int(math.ceil(float(count) / float(cols))))
    cells: List[Tuple[float, float, float, float]] = []
    while True:
        cells.clear()
        cell_w = width / float(cols)
        cell_h = height / float(rows)
        cx0 = (x1 + x2) / 2.0
        cy0 = (y1 + y2) / 2.0
        rx = width * 0.48
        ry = height * 0.48
        for row in range(rows):
            for col in range(cols):
                cx = x1 + (float(col) + 0.5) * cell_w
                cy = y1 + (float(row) + 0.5) * cell_h
                if circular:
                    norm = ((cx - cx0) / max(1.0, rx)) ** 2 + ((cy - cy0) / max(1.0, ry)) ** 2
                    if norm > 0.90:
                        continue
                cells.append((cx, cy, cell_w, cell_h))
        if len(cells) >= int(count) or not circular:
            break
        cols += 1
        rows += 1
    rng = spawn_rng(int(instance_seed), str(namespace))
    rng.shuffle(cells)
    return cells[: int(count)]


def _value_scale(items: Sequence[_Item]) -> Tuple[int, int]:
    values = [int(item.value) for item in items]
    return min(values), max(values)


def _value_fraction(value: int, *, value_min: int, value_max: int) -> float:
    if int(value_max) <= int(value_min):
        return 0.5
    return (float(value) - float(value_min)) / (float(value_max) - float(value_min))


def _draw_legend(
    draw: ImageDraw.ImageDraw,
    *,
    categories: Sequence[str],
    colors: Mapping[str, RGB],
    bbox: BBox,
    params: Mapping[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]]]:
    x1, y1, x2, y2 = (float(value) for value in bbox)
    font = load_font(_resolve_int(params, "legend_font_size_px", 18), bold=False)
    entities: List[Dict[str, Any]] = []
    bboxes: Dict[str, List[float]] = {}
    column_w = max(80.0, (x2 - x1) / max(1, len(categories)))
    for index, category in enumerate(categories):
        left = x1 + (index * column_w) + 4
        cy = (y1 + y2) / 2.0
        color = colors[str(category)]
        swatch = [left, cy - 8, left + 18, cy + 10]
        draw.rounded_rectangle(swatch, radius=4, fill=color, outline=_darken(color, 0.62), width=1)
        text_xy = (left + 26, cy - 12)
        draw.text(text_xy, str(category), font=font, fill=(52, 60, 76))
        text_box = _text_bbox(draw, text_xy, str(category), font)
        full_box = [
            float(min(swatch[0], text_box[0])),
            float(min(swatch[1], text_box[1])),
            float(max(swatch[2], text_box[2])),
            float(max(swatch[3], text_box[3])),
        ]
        bboxes[str(category)] = _format_bbox(full_box)
        entities.append(
            {
                "entity_id": f"legend_{str(category).lower()}",
                "entity_type": "chart_size_category_legend",
                "bbox_px": _format_bbox(full_box),
                "attrs": {"category": str(category), "fill_rgb": list(color)},
            }
        )
    return entities, bboxes


def _draw_word_cloud(
    draw: ImageDraw.ImageDraw,
    *,
    items: Sequence[_Item],
    bbox: BBox,
    category_colors: Mapping[str, RGB],
    params: Mapping[str, Any],
    instance_seed: int,
    circular: bool,
) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]]]:
    item_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    value_min, value_max = _value_scale(items)
    min_font = _resolve_int(params, "min_word_font_size_px", 18)
    max_font = _resolve_int(params, "max_word_font_size_px", 52)
    stroke_width = _resolve_int(params, "word_text_stroke_width_px", 1)
    if circular:
        draw.ellipse(bbox, outline=(210, 216, 226), width=2)
    cells = _cell_centers(
        bbox,
        count=len(items),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.word_cells.{int(circular)}",
        circular=bool(circular),
    )
    for item, (cx, cy, cell_w, cell_h) in zip(items, cells):
        frac = _value_fraction(int(item.value), value_min=int(value_min), value_max=int(value_max))
        target_font = int(round(float(min_font) + (float(max_font - min_font) * math.sqrt(float(frac)))))
        font = fit_font_to_box(
            draw,
            text=str(item.label),
            max_width=float(cell_w) * 0.96,
            max_height=float(cell_h) * 0.90,
            bold=True,
            min_size_px=max(8, int(min_font) - 6),
            max_size_px=max(int(min_font), int(target_font)),
            fill_ratio=0.95,
        )
        color = _darken(category_colors[str(item.category)], 0.78)
        bbox_px = _center_text(
            draw,
            center=(float(cx), float(cy)),
            text=str(item.label),
            font=font,
            fill=color,
            stroke_width=stroke_width,
            stroke_fill=(255, 255, 255),
        )
        padded = [bbox_px[0] - 3, bbox_px[1] - 3, bbox_px[2] + 3, bbox_px[3] + 3]
        item_bboxes[str(item.item_id)] = _format_bbox(padded)
        entities.append(
            {
                "entity_id": str(item.item_id),
                "entity_type": "chart_size_word_item",
                "bbox_px": _format_bbox(padded),
                "attrs": {
                    "label": str(item.label),
                    "category": str(item.category),
                    "panel": str(item.panel),
                    "value": int(item.value),
                    "font_size_px": int(getattr(font, "size", target_font)),
                },
            }
        )
    return entities, item_bboxes


def _draw_bubbles(
    draw: ImageDraw.ImageDraw,
    *,
    items: Sequence[_Item],
    bbox: BBox,
    category_colors: Mapping[str, RGB],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, List[float]]]:
    item_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    value_min, value_max = _value_scale(items)
    stroke_width = _resolve_int(params, "bubble_label_stroke_width_px", 1)
    cells = _cell_centers(
        bbox,
        count=len(items),
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.bubble_cells",
        circular=False,
    )
    for item, (cx, cy, cell_w, cell_h) in zip(items, cells):
        frac = _value_fraction(int(item.value), value_min=int(value_min), value_max=int(value_max))
        max_r = max(10.0, min(float(cell_w), float(cell_h)) * 0.43)
        min_r = max(10.0, max_r * 0.42)
        radius = min_r + ((max_r - min_r) * math.sqrt(float(frac)))
        color = category_colors[str(item.category)]
        fill = _lighten(color, 0.12)
        outline = _darken(color, 0.55)
        circle = [float(cx - radius), float(cy - radius), float(cx + radius), float(cy + radius)]
        draw.ellipse(circle, fill=fill, outline=outline, width=2)
        font = fit_font_to_box(
            draw,
            text=str(item.label),
            max_width=float(radius) * 1.65,
            max_height=float(radius) * 0.80,
            bold=True,
            min_size_px=9,
            max_size_px=_resolve_int(params, "bubble_label_font_size_px", 19),
            fill_ratio=0.92,
        )
        _center_text(
            draw,
            center=(float(cx), float(cy)),
            text=str(item.label),
            font=font,
            fill=(38, 44, 58),
            stroke_width=stroke_width,
            stroke_fill=(255, 255, 255),
        )
        item_bboxes[str(item.item_id)] = _format_bbox(circle)
        entities.append(
            {
                "entity_id": str(item.item_id),
                "entity_type": "chart_size_bubble_item",
                "bbox_px": _format_bbox(circle),
                "attrs": {
                    "label": str(item.label),
                    "category": str(item.category),
                    "panel": str(item.panel),
                    "value": int(item.value),
                    "radius_px": round(float(radius), 3),
                },
            }
        )
    return entities, item_bboxes


def _panel_layout(plot_bbox: BBox, panel_count: int, gap: float) -> List[BBox]:
    x1, y1, x2, y2 = (float(value) for value in plot_bbox)
    if int(panel_count) <= 1:
        return [(x1, y1, x2, y2)]
    cols = 2 if int(panel_count) <= 4 else 3
    rows = int(math.ceil(float(panel_count) / float(cols)))
    cell_w = (x2 - x1 - (float(cols - 1) * gap)) / float(cols)
    cell_h = (y2 - y1 - (float(rows - 1) * gap)) / float(rows)
    bboxes: List[BBox] = []
    for index in range(int(panel_count)):
        row = index // cols
        col = index % cols
        px1 = x1 + (col * (cell_w + gap))
        py1 = y1 + (row * (cell_h + gap))
        bboxes.append((px1, py1, px1 + cell_w, py1 + cell_h))
    return bboxes


def _render_dataset(
    dataset: _Dataset,
    *,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Rendered:
    params = {**dict(params), "_render_style_seed": int(instance_seed)}
    canvas_width = _resolve_int(params, "canvas_width", 1320)
    canvas_height = _resolve_int(params, "canvas_height", 900)
    background, background_meta = make_background_canvas(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
    )
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    outer = _resolve_int(params, "outer_margin_px", 44)
    margin_left, margin_right, margin_top, margin_bottom, layout_jitter_meta = apply_layout_jitter_to_margins(
        left_px=int(outer),
        right_px=int(outer),
        top_px=int(outer),
        bottom_px=int(outer),
        params=params,
        defaults=_RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.layout",
    )
    title_band = _resolve_int(params, "title_band_height_px", 74)
    legend_height = _resolve_int(params, "legend_height_px", 58)
    panel_gap = _resolve_int(params, "panel_gap_px", 28)
    panel_padding = _resolve_int(params, "panel_padding_px", 18)
    title_rgb = _resolve_rgb(params, "title_rgb", (42, 50, 66))
    subtitle_rgb = _resolve_rgb(params, "subtitle_rgb", (88, 96, 112))
    panel_fill = _resolve_rgb(params, "panel_fill_rgb", (255, 255, 255))
    panel_border = _resolve_rgb(params, "panel_border_rgb", (196, 204, 216))
    category_palette = _category_palette(params, len(dataset.categories))
    category_colors = {str(category): category_palette[index] for index, category in enumerate(dataset.categories)}

    title_font = load_font(_resolve_int(params, "title_font_size_px", 28), bold=True)
    subtitle_font = load_font(_resolve_int(params, "subtitle_font_size_px", 18), bold=False)
    draw.text((margin_left, 24 + int(layout_jitter_meta.get("dy_px", 0))), "Size-Encoded Category Chart", font=title_font, fill=title_rgb)
    draw.text((margin_left, 58 + int(layout_jitter_meta.get("dy_px", 0))), "Relative size shows value; colors show category.", font=subtitle_font, fill=subtitle_rgb)

    legend_bbox = (float(margin_left), float(title_band + int(layout_jitter_meta.get("dy_px", 0))), float(canvas_width - margin_right), float(title_band + legend_height + int(layout_jitter_meta.get("dy_px", 0))))
    legend_entities, legend_bboxes = _draw_legend(
        draw,
        categories=dataset.categories,
        colors=category_colors,
        bbox=legend_bbox,
        params=params,
    )
    plot_bbox = [
        float(margin_left),
        float(title_band + legend_height + 16 + int(layout_jitter_meta.get("dy_px", 0))),
        float(canvas_width - margin_right),
        float(canvas_height - margin_bottom),
    ]

    entities: List[Dict[str, Any]] = list(legend_entities)
    item_bboxes: Dict[str, List[float]] = {}
    panel_title_bboxes: Dict[str, List[float]] = {}
    panel_bboxes = _panel_layout(tuple(plot_bbox), panel_count=len(dataset.panels), gap=float(panel_gap))
    panel_title_font = load_font(_resolve_int(params, "panel_title_font_size_px", 20), bold=True)

    for panel_index, (panel, panel_bbox) in enumerate(zip(dataset.panels, panel_bboxes)):
        px1, py1, px2, py2 = (float(value) for value in panel_bbox)
        draw.rounded_rectangle(
            [px1, py1, px2, py2],
            radius=_resolve_int(params, "panel_corner_radius_px", 10),
            fill=panel_fill,
            outline=panel_border,
            width=_resolve_int(params, "panel_border_width_px", 2),
        )
        if len(dataset.panels) > 1:
            title_xy = (px1 + 14, py1 + 10)
            draw.text(title_xy, str(panel), font=panel_title_font, fill=(50, 58, 74))
            title_bbox = _format_bbox(_text_bbox(draw, title_xy, str(panel), panel_title_font))
            panel_title_bboxes[str(panel)] = title_bbox
            content_top = py1 + 40
        else:
            panel_title_bboxes[str(panel)] = _format_bbox([px1, py1, px2, min(py2, py1 + 1)])
            content_top = py1 + panel_padding
        content_bbox: BBox = (
            px1 + panel_padding,
            content_top + panel_padding,
            px2 - panel_padding,
            py2 - panel_padding,
        )
        panel_items = [item for item in dataset.items if str(item.panel) == str(panel)]
        if str(scene_variant) == "packed_bubble_cloud" or str(scene_variant) == "small_multiple_bubble_cloud":
            rendered_entities, rendered_bboxes = _draw_bubbles(
                draw,
                items=panel_items,
                bbox=content_bbox,
                category_colors=category_colors,
                params=params,
                instance_seed=int(instance_seed) + int(panel_index),
            )
        else:
            rendered_entities, rendered_bboxes = _draw_word_cloud(
                draw,
                items=panel_items,
                bbox=content_bbox,
                category_colors=category_colors,
                params=params,
                instance_seed=int(instance_seed) + int(panel_index),
                circular=str(scene_variant) == "circle_word_cloud",
            )
        entities.extend(rendered_entities)
        item_bboxes.update(rendered_bboxes)
        entities.append(
            {
                "entity_id": f"panel_{str(panel)}",
                "entity_type": "chart_size_panel",
                "bbox_px": _format_bbox([px1, py1, px2, py2]),
                "attrs": {"panel": str(panel), "scene_variant": str(scene_variant), "item_count": int(len(panel_items))},
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
        item_bboxes=dict(item_bboxes),
        panel_title_bboxes=dict(panel_title_bboxes),
        category_legend_bboxes=dict(legend_bboxes),
        plot_bbox_px=_format_bbox(plot_bbox),
        render_meta={
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
            "layout_jitter": dict(layout_jitter_meta),
            "category_colors_rgb": {str(key): list(value) for key, value in category_colors.items()},
            "panel_bboxes_px": {str(panel): _format_bbox(bbox) for panel, bbox in zip(dataset.panels, panel_bboxes)},
        },
    )


def _evidence_bboxes(dataset: _Dataset, rendered: _Rendered) -> List[List[float]]:
    boxes: List[List[float]] = []
    for panel_label in dataset.query.evidence_panel_labels:
        bbox = rendered.panel_title_bboxes.get(str(panel_label))
        if bbox is not None:
            boxes.append(list(bbox))
    for category_label in dataset.query.evidence_category_labels:
        if dataset.query.query_variant != "category_total_extremum_label":
            bbox = rendered.category_legend_bboxes.get(str(category_label))
            if bbox is not None:
                boxes.append(list(bbox))
    for item_id in dataset.query.evidence_item_ids:
        bbox = rendered.item_bboxes.get(str(item_id))
        if bbox is not None:
            boxes.append(list(bbox))
    return boxes


class ChartsSizeEncodingComparisonLabelTask:
    """Answer comparative label queries on size-encoded charts."""

    task_id = TASK_ID
    domain = "charts"
    task_group = "size_encoding"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_variant, query_variant_probabilities = _resolve_query_variant(params, instance_seed=int(instance_seed))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            query_variant=str(query_variant),
            instance_seed=int(instance_seed),
        )
        extremum_direction, extremum_direction_probabilities = _resolve_extremum_direction(
            params,
            instance_seed=int(instance_seed),
        )

        last_error: Exception | None = None
        dataset: _Dataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_dataset(
                    query_variant=str(query_variant),
                    scene_variant=str(scene_variant),
                    extremum_direction=str(extremum_direction),
                    params=params,
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt_index),
                )
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        rendered = _render_dataset(
            dataset,
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
        )
        evidence_boxes = _evidence_bboxes(dataset, rendered)
        if not evidence_boxes:
            raise RuntimeError(f"{self.task_id} produced empty evidence")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint",
                "object_description_rect_word_cloud",
                "object_description_circle_word_cloud",
                "object_description_packed_bubble_cloud",
                "object_description_small_multiple_bubble_cloud",
                "evidence_hint_filtered_item_extremum_label",
                "evidence_hint_reference_size_neighbor_label",
                "evidence_hint_category_total_extremum_label",
                "json_example_filtered_item_extremum_label",
                "json_example_reference_size_neighbor_label",
                "json_example_category_total_extremum_label",
                "json_example_answer_only_filtered_item_extremum_label",
                "json_example_answer_only_reference_size_neighbor_label",
                "json_example_answer_only_category_total_extremum_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults[f"object_description_{str(scene_variant)}"]),
                "category_label": str(dataset.query.category_label),
                "panel_label": str(dataset.query.panel_label),
                "reference_label": str(dataset.query.reference_label),
                "extremum_phrase": "largest" if str(extremum_direction) == "largest" else "smallest",
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(query_variant)}"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults[f"json_example_{str(query_variant)}"]),
                "json_example_answer_only": str(prompt_defaults[f"json_example_answer_only_{str(query_variant)}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        items_by_id = {str(item.item_id): item for item in dataset.items}
        values_by_label = {str(item.label): int(item.value) for item in dataset.items}
        category_by_label = {str(item.label): str(item.category) for item in dataset.items}
        panel_by_label = {str(item.label): str(item.panel) for item in dataset.items}
        evidence_labels = [str(items_by_id[item_id].label) for item_id in dataset.query.evidence_item_ids if item_id in items_by_id]
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_boxes])
        answer_gt = TypedValue(type="string", value=str(dataset.query.answer))

        trace_payload = {
            "scene_ir": {
                "scene_kind": f"chart_size_encoding_{str(scene_variant)}",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "query_variant": str(query_variant),
                    "scene_variant": str(scene_variant),
                    "extremum_direction": str(extremum_direction),
                    "answer_label": str(dataset.query.answer),
                    "evidence_labels": list(evidence_labels),
                    "category_label": str(dataset.query.category_label),
                    "panel_label": str(dataset.query.panel_label),
                    "reference_label": str(dataset.query.reference_label),
                },
            },
            "query_spec": {
                "query_variant": str(query_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": str(query_variant),
                    "scene_variant": str(scene_variant),
                    "extremum_direction": str(extremum_direction),
                    "query_variant_probabilities": dict(query_variant_probabilities),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "extremum_direction_probabilities": dict(extremum_direction_probabilities),
                    "item_count": int(len(dataset.items)),
                    "category_count": int(len(dataset.categories)),
                    "panel_count": int(len(dataset.panels)),
                    "category_label": str(dataset.query.category_label),
                    "panel_label": str(dataset.query.panel_label),
                    "reference_label": str(dataset.query.reference_label),
                    "question_format": "size_encoded_label_comparison",
                },
            },
            "render_spec": {
                "canvas_width": _resolve_int(params, "canvas_width", 1320),
                "canvas_height": _resolve_int(params, "canvas_height", 900),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "plot_bbox_px": list(rendered.plot_bbox_px),
                **dict(rendered.render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "plot_bbox_px": list(rendered.plot_bbox_px),
                "item_bboxes_px": dict(rendered.item_bboxes),
                "panel_title_bboxes_px": dict(rendered.panel_title_bboxes),
                "category_legend_bboxes_px": dict(rendered.category_legend_bboxes),
            },
            "execution_trace": {
                "query_variant": str(query_variant),
                "scene_variant": str(scene_variant),
                "extremum_direction": str(extremum_direction),
                "answer_label": str(dataset.query.answer),
                "answer_value_hidden": int(values_by_label[str(dataset.query.answer)])
                if str(dataset.query.answer) in values_by_label
                else None,
                "evidence_labels": list(evidence_labels),
                "item_count": int(len(dataset.items)),
                "category_count": int(len(dataset.categories)),
                "panel_count": int(len(dataset.panels)),
                "categories": list(dataset.categories),
                "panels": list(dataset.panels),
                "values_by_label": dict(values_by_label),
                "category_by_label": dict(category_by_label),
                "panel_by_label": dict(panel_by_label),
                "query_variant_probabilities": dict(query_variant_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "extremum_direction_probabilities": dict(extremum_direction_probabilities),
                "question_format": "size_encoded_label_comparison",
                **dict(dataset.query.trace),
            },
            "witness_symbolic": {
                "type": "object_set",
                "labels": list(evidence_labels),
                "answer": str(dataset.query.answer),
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_boxes],
                "evidence_item_ids": list(dataset.query.evidence_item_ids),
                "evidence_panel_labels": list(dataset.query.evidence_panel_labels),
                "evidence_category_labels": list(dataset.query.evidence_category_labels),
            },
        }

        single_item_min = _resolve_int(params, "item_count_min", 18)
        panel_max = _resolve_int(params, "panel_count_max", 4)
        panel_item_max = _resolve_int(params, "panel_item_count_max", 10)
        visual_scan_max = max(int(single_item_min) + 1, int(panel_max) * int(panel_item_max))
        complexity = build_chart_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": normalize_int_with_bounds(int(len(dataset.items)), [int(single_item_min), int(visual_scan_max)]),
                "reasoning_load": float(_REASONING_LOAD_BY_VARIANT[str(query_variant)]),
                "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
            },
        )
        if str(query_variant) == "category_total_extremum_label":
            complexity = build_chart_complexity(
                weights=_COMPLEXITY_WEIGHTS,
                components={
                    "visual_scan": normalize_int_with_bounds(int(len(dataset.items)), [int(single_item_min), int(visual_scan_max)]),
                    "reasoning_load": clamp_unit_interval(float(_REASONING_LOAD_BY_VARIANT[str(query_variant)]) + (0.04 * max(0, len(evidence_boxes) - 4))),
                    "scene_variant_load": float(_SCENE_VARIANT_LOADS[str(scene_variant)]),
                },
            )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant=str(query_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class ChartsSizeEncodingFilteredItemExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsSizeEncodingComparisonLabelTask,
):
    """Return the size-encoded item label with an extremal value inside a filter."""

    task_id = "task_charts__size_encoding__filtered_item_extremum_label"
    fixed_query_variant = "filtered_item_extremum_label"


@register_task
class ChartsSizeEncodingReferenceSizeNeighborLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsSizeEncodingComparisonLabelTask,
):
    """Return the size neighbor of a reference item."""

    task_id = "task_charts__size_encoding__reference_size_neighbor_label"
    fixed_query_variant = "reference_size_neighbor_label"


@register_task
class ChartsSizeEncodingCategoryTotalExtremumLabelTask(
    FixedChartQueryVariantTaskMixin,
    ChartsSizeEncodingComparisonLabelTask,
):
    """Return the category label with an extremal total encoded size."""

    task_id = "task_charts__size_encoding__category_total_extremum_label"
    fixed_query_variant = "category_total_extremum_label"


__all__ = [
    "ChartsSizeEncodingCategoryTotalExtremumLabelTask",
    "ChartsSizeEncodingComparisonLabelTask",
    "ChartsSizeEncodingFilteredItemExtremumLabelTask",
    "ChartsSizeEncodingReferenceSizeNeighborLabelTask",
]
