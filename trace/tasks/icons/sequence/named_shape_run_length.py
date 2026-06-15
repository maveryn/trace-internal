"""Measure longest or shortest consecutive runs of named icons in a row."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.variant_sampling import resolve_variant
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.annotation import bbox_set_annotation
from ..shared.icon_grid_scene import resolve_horizontal_row_slots
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import (
    BBox,
    draw_single_panel,
    resolve_single_panel_layout,
    single_panel_geometry_to_trace,
    sort_bboxes_reading_order,
)
from ..shared.icon_style import sample_icon_palette
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_cell_render_params, sample_icon_instance_noise
from ..shared.procedural_named_icon_field_scene import (
    bbox_from_center_dimensions,
    render_planned_named_icon_sprite,
    resolve_named_icon_fill_style_probabilities,
)
from ..shared.procedural_named_icons import (
    PROCEDURAL_NAMED_ICON_FILL_STYLES,
    PROCEDURAL_NAMED_ICON_SHAPES,
    procedural_named_icon_display_name,
    sample_procedural_named_icon_fill_style,
    validate_procedural_named_icon_fill_style_support,
)


TASK_ID = "task_icons__named_strip__shape_run_length"
SCENE_ID = "named_strip"

QUERY_IDS: Tuple[str, ...] = (
    "longest_shape_run_length",
    "shortest_shape_run_length",
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for named-icon run rows."""

    strip_length_min: int = 12
    strip_length_max: int = 16
    longest_run_length_min: int = 2
    longest_run_length_max: int = 6
    shortest_run_length_min: int = 1
    shortest_run_length_max: int = 5
    canvas_width: int = 1280
    canvas_height: int = 320
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    reference_panel_width_px: int = ICON_SHARED_DEFAULTS.reference_panel_width_px
    reference_icon_size_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    reference_icon_size_min_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    reference_icon_size_max_px: int = ICON_SHARED_DEFAULTS.reference_icon_size_px
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    scene_icon_size_min_px: int = 42
    scene_icon_size_max_px: int = 58
    cell_box_width_min_px: int = 58
    cell_box_width_max_px: int = 72
    cell_box_height_min_px: int = 88
    cell_box_height_max_px: int = 108
    scene_max_overlap_fraction: float = 0.0
    scene_placement_max_attempts: int = ICON_SHARED_DEFAULTS.scene_placement_max_attempts
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
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
    cell_padding_px: int = 4
    cell_icon_padding_px: int = 8
    cell_corner_radius_px: int = 10
    cell_border_rgb: Tuple[int, int, int] = (218, 223, 233)
    cell_label_font_size_px: int = 0
    cell_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    missing_mark_font_size_px: int = 0
    missing_mark_color_rgb: Tuple[int, int, int] = (84, 96, 118)
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: dict(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )
    named_icon_fill_style_support: Tuple[str, ...] = PROCEDURAL_NAMED_ICON_FILL_STYLES


@dataclass(frozen=True)
class _SampleSpec:
    """Symbolic sample for one named-icon run row."""

    query_id: str
    target_shape_id: str
    target_shape_name: str
    answer: int
    strip_length: int
    shape_ids: Tuple[str, ...]
    selected_run_indices: Tuple[int, ...]
    target_runs: Tuple[Tuple[int, int], ...]
    query_probabilities: Dict[str, float]
    answer_probabilities: Dict[str, float]
    strip_length_probabilities: Dict[str, float]
    shape_probabilities: Dict[str, float]
    fill_style_support: Tuple[str, ...]
    fill_style_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _IconPlan:
    """One planned procedural named icon in the row."""

    cell_index: int
    shape_id: str
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    nominal_size_px: int
    rotation_degrees: int
    noise_edits: Tuple[Any, ...]
    noise_seed: int | None


@dataclass(frozen=True)
class _RenderedStripIcon:
    """Rendered named-strip icon metadata."""

    instance_id: str
    cell_index: int
    shape_id: str
    shape_name: str
    bbox_xyxy: Tuple[int, int, int, int]
    cell_bbox_xyxy: Tuple[int, int, int, int]
    nominal_size_px: int
    tint_rgb: Tuple[int, int, int]
    fill_style: str
    rotation_degrees: int
    is_target_shape: bool
    is_selected_run_member: bool
    noise_edits: Tuple[Dict[str, Any], ...]
    noise_seed: int | None


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready rendered scene payload."""

    image: Image.Image
    icons: Tuple[_RenderedStripIcon, ...]
    cells: Tuple[Dict[str, Any], ...]
    panel_geometry: Dict[str, Any]
    cell_box_width_px: int
    cell_box_height_px: int
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("icons", "sequence")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _shape_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("shape_id_support", group_default(_GEN_DEFAULTS, "shape_id_support", PROCEDURAL_NAMED_ICON_SHAPES))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("shape_id_support must be a sequence")
    values = tuple(dict.fromkeys(str(value).strip() for value in raw if str(value).strip()))
    unsupported = sorted(set(values) - set(PROCEDURAL_NAMED_ICON_SHAPES))
    if unsupported:
        raise ValueError(f"unsupported procedural named icon shapes: {unsupported}")
    if len(values) < 8:
        raise ValueError("named-strip run task needs at least eight supported icon shapes")
    return values


def _fill_style_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get(
        "named_icon_fill_style_support",
        group_default(_GEN_DEFAULTS, "named_icon_fill_style_support", _DEFAULTS.named_icon_fill_style_support),
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raw = _DEFAULTS.named_icon_fill_style_support
    return validate_procedural_named_icon_fill_style_support(tuple(str(value) for value in raw))


def _int_bounds(
    params: Mapping[str, Any],
    low_key: str,
    high_key: str,
    fallback_low: int,
    fallback_high: int,
) -> Tuple[int, int]:
    low = int(params.get(low_key, group_default(_GEN_DEFAULTS, low_key, fallback_low)))
    high = int(params.get(high_key, group_default(_GEN_DEFAULTS, high_key, fallback_high)))
    if low < 0 or high < low:
        raise ValueError(f"invalid {low_key}/{high_key} bounds")
    return int(low), int(high)


def _answer_support(params: Mapping[str, Any], query_id: str) -> Tuple[int, ...]:
    if str(query_id) == "longest_shape_run_length":
        low, high = _int_bounds(
            params,
            "longest_run_length_min",
            "longest_run_length_max",
            _DEFAULTS.longest_run_length_min,
            _DEFAULTS.longest_run_length_max,
        )
    elif str(query_id) == "shortest_shape_run_length":
        low, high = _int_bounds(
            params,
            "shortest_run_length_min",
            "shortest_run_length_max",
            _DEFAULTS.shortest_run_length_min,
            _DEFAULTS.shortest_run_length_max,
        )
    else:
        raise ValueError(f"unsupported query_id: {query_id}")
    if str(query_id) == "longest_shape_run_length" and low < 2:
        raise ValueError("longest run support starts at 2 so the task is not a singleton-detection branch")
    return tuple(range(int(low), int(high) + 1))


def _target_runs(shape_ids: Sequence[str], *, target_shape_id: str) -> Tuple[Tuple[int, int], ...]:
    runs: List[Tuple[int, int]] = []
    start = None
    for index, shape_id in enumerate(shape_ids):
        if str(shape_id) == str(target_shape_id):
            if start is None:
                start = int(index)
        elif start is not None:
            runs.append((int(start), int(index) - 1))
            start = None
    if start is not None:
        runs.append((int(start), len(shape_ids) - 1))
    return tuple(runs)


def _target_run_lengths(runs: Sequence[Tuple[int, int]]) -> Tuple[int, ...]:
    return tuple(int(end) - int(start) + 1 for start, end in runs)


def _build_runs_for_query(rng, *, query_id: str, answer: int, strip_length: int) -> Tuple[Tuple[int, bool], ...]:
    """Return target-run lengths, marking the run that witnesses the answer."""

    run_blocks: List[Tuple[int, bool]] = [(int(answer), True)]
    if str(query_id) == "longest_shape_run_length":
        optional_candidates = tuple(range(1, int(answer)))
        desired_optional_count = int(rng.randint(1, 4)) if optional_candidates else 0
        for _ in range(int(desired_optional_count)):
            candidate = int(rng.choice(optional_candidates))
            tentative = run_blocks + [(candidate, False)]
            min_needed = sum(length for length, _ in tentative) + max(0, len(tentative) - 1)
            if int(min_needed) <= int(strip_length):
                run_blocks.append((int(candidate), False))
    elif str(query_id) == "shortest_shape_run_length":
        max_other = min(6, int(strip_length) - int(answer) - 1)
        if max_other <= int(answer):
            raise ValueError("strip length leaves no room for a longer target-shape run")
        run_blocks.append((int(rng.randint(int(answer) + 1, int(max_other))), False))
        desired_optional_count = int(rng.randint(0, 3))
        for _ in range(int(desired_optional_count)):
            candidate = int(rng.randint(int(answer) + 1, 6))
            tentative = run_blocks + [(candidate, False)]
            min_needed = sum(length for length, _ in tentative) + max(0, len(tentative) - 1)
            if int(min_needed) <= int(strip_length):
                run_blocks.append((int(candidate), False))
    else:
        raise ValueError(f"unsupported query_id: {query_id}")
    rng.shuffle(run_blocks)
    return tuple((int(length), bool(selected)) for length, selected in run_blocks)


def _construct_shape_row(
    rng,
    *,
    support: Sequence[str],
    target_shape_id: str,
    query_id: str,
    answer: int,
    strip_length: int,
) -> Tuple[Tuple[str, ...], Tuple[int, ...], Tuple[Tuple[int, int], ...]]:
    """Construct one row with a unique target-shape extremum run."""

    run_blocks = list(
        _build_runs_for_query(
            rng,
            query_id=str(query_id),
            answer=int(answer),
            strip_length=int(strip_length),
        )
    )
    min_needed = sum(length for length, _ in run_blocks) + max(0, len(run_blocks) - 1)
    if int(min_needed) > int(strip_length):
        raise ValueError("target runs do not fit strip length")
    gaps = [0] + ([1] * max(0, len(run_blocks) - 1)) + [0]
    remaining = int(strip_length) - int(min_needed)
    for _ in range(max(0, int(remaining))):
        gaps[int(rng.randint(0, len(gaps) - 1))] += 1

    distractor_support = tuple(str(value) for value in support if str(value) != str(target_shape_id))
    if not distractor_support:
        raise ValueError("target row needs at least one distractor shape")

    row: List[str] = []
    selected_indices: List[int] = []
    for run_index, (run_length, selected) in enumerate(run_blocks):
        for _ in range(int(gaps[int(run_index)])):
            row.append(str(rng.choice(distractor_support)))
        run_start = len(row)
        for _ in range(int(run_length)):
            row.append(str(target_shape_id))
        if bool(selected):
            selected_indices.extend(range(int(run_start), int(run_start) + int(run_length)))
    for _ in range(int(gaps[-1])):
        row.append(str(rng.choice(distractor_support)))

    runs = _target_runs(row, target_shape_id=str(target_shape_id))
    lengths = _target_run_lengths(runs)
    selected_run_length = int(len(selected_indices))
    if str(query_id) == "longest_shape_run_length":
        if selected_run_length != max(lengths) or lengths.count(int(selected_run_length)) != 1:
            raise ValueError("constructed row does not have a unique longest target run")
    elif str(query_id) == "shortest_shape_run_length":
        if selected_run_length != min(lengths) or lengths.count(int(selected_run_length)) != 1:
            raise ValueError("constructed row does not have a unique shortest target run")
    return tuple(str(value) for value in row), tuple(int(index) for index in selected_indices), tuple(runs)


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample")
    query_id, query_probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    support = _shape_support(params)
    explicit_shape = params.get("shape_id", params.get("target_shape_id"))
    if explicit_shape is not None:
        target_shape_id = str(explicit_shape)
        if target_shape_id not in set(support):
            raise ValueError(f"target shape must be one of {support}")
        shape_probabilities = {str(value): (1.0 if str(value) == str(target_shape_id) else 0.0) for value in support}
    else:
        target_shape_id = str(rng.choice(support))
        probability = 1.0 / float(len(support))
        shape_probabilities = {str(value): float(probability) for value in support}

    answer_support = _answer_support(params, str(query_id))
    explicit_answer = params.get("target_run_length", params.get("answer", params.get("run_length")))
    if explicit_answer is not None:
        answer = int(explicit_answer)
        if int(answer) not in set(answer_support):
            raise ValueError("explicit run length is outside configured support")
        answer_probabilities = uniform_probability_map(answer_support, selected=int(answer))
    else:
        answer = int(rng.choice(answer_support))
        answer_probabilities = uniform_probability_map(answer_support)

    strip_min, strip_max = _int_bounds(
        params,
        "strip_length_min",
        "strip_length_max",
        _DEFAULTS.strip_length_min,
        _DEFAULTS.strip_length_max,
    )
    if int(strip_min) < int(answer):
        strip_min = int(answer)
    if str(query_id) == "shortest_shape_run_length":
        strip_min = max(int(strip_min), (2 * int(answer)) + 2)
    if int(strip_min) > int(strip_max):
        raise ValueError("strip length range cannot support the requested run-length query")
    strip_support = tuple(range(int(strip_min), int(strip_max) + 1))
    explicit_strip_length = params.get("strip_length")
    if explicit_strip_length is not None:
        strip_length = int(explicit_strip_length)
        if int(strip_length) not in set(strip_support):
            raise ValueError("explicit strip_length is outside configured support")
        strip_length_probabilities = uniform_probability_map(strip_support, selected=int(strip_length))
    else:
        strip_length = int(rng.choice(strip_support))
        strip_length_probabilities = uniform_probability_map(strip_support)

    fill_style_support = _fill_style_support(params)
    fill_style_probabilities = resolve_named_icon_fill_style_probabilities(
        params,
        _GEN_DEFAULTS,
        fill_style_support,
    )
    shape_ids, selected_indices, target_runs = _construct_shape_row(
        rng,
        support=support,
        target_shape_id=str(target_shape_id),
        query_id=str(query_id),
        answer=int(answer),
        strip_length=int(strip_length),
    )
    return _SampleSpec(
        query_id=str(query_id),
        target_shape_id=str(target_shape_id),
        target_shape_name=procedural_named_icon_display_name(str(target_shape_id)),
        answer=int(answer),
        strip_length=int(strip_length),
        shape_ids=tuple(str(value) for value in shape_ids),
        selected_run_indices=tuple(int(index) for index in selected_indices),
        target_runs=tuple((int(start), int(end)) for start, end in target_runs),
        query_probabilities=dict(query_probabilities),
        answer_probabilities=dict(answer_probabilities),
        strip_length_probabilities=dict(strip_length_probabilities),
        shape_probabilities=dict(shape_probabilities),
        fill_style_support=tuple(fill_style_support),
        fill_style_probabilities=dict(fill_style_probabilities),
    )


def _sequence_canvas_size(
    *,
    strip_length: int,
    cell_box_width_px: int,
    cell_box_height_px: int,
    render_params: Mapping[str, Any],
) -> Tuple[int, int]:
    cell_padding_px = int(render_params["cell_padding_px"])
    panel_padding_px = int(render_params["panel_padding_px"])
    outer_margin_px = int(render_params["outer_margin_px"])
    title_font_size_px = int(render_params["panel_title_font_size_px"])
    title_band_height = max(40, int(round(float(title_font_size_px) * 1.8)))
    content_width = int(strip_length) * int(int(cell_box_width_px) + (2 * cell_padding_px))
    content_height = int(int(cell_box_height_px) + (2 * cell_padding_px))
    panel_width = int(content_width + (2 * panel_padding_px))
    panel_height = int(content_height + title_band_height + panel_padding_px + (panel_padding_px // 2))
    return int(panel_width + (2 * outer_margin_px)), int(panel_height + (2 * outer_margin_px))


def _build_icon_plans(
    *,
    sample: _SampleSpec,
    instance_seed: int,
    render_params: Mapping[str, Any],
    rng,
) -> Tuple[Tuple[_IconPlan, ...], Tuple[Tuple[int, int, int], ...]]:
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
    plans: List[_IconPlan] = []
    for cell_index, shape_id in enumerate(sample.shape_ids):
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:cell_{int(cell_index)}",
            render_params=render_params,
        )
        plans.append(
            _IconPlan(
                cell_index=int(cell_index),
                shape_id=str(shape_id),
                tint_rgb=tuple(int(value) for value in rng.choice(palette)),
                fill_style=sample_procedural_named_icon_fill_style(
                    rng,
                    support=sample.fill_style_support,
                    probabilities=sample.fill_style_probabilities,
                ),
                nominal_size_px=int(rng.randint(int(min_size), int(max_size))),
                rotation_degrees=0,
                noise_edits=tuple(noise_edits),
                noise_seed=int(noise_seed),
            )
        )
    return tuple(plans), tuple(tuple(int(channel) for channel in color) for color in palette)


def _render_scene(
    *,
    sample: _SampleSpec,
    plans: Sequence[_IconPlan],
    render_params: Mapping[str, Any],
    rng,
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...],
) -> _ScenePayload:
    cell_box_width_px = int(rng.randint(int(render_params["cell_box_width_min_px"]), int(render_params["cell_box_width_max_px"])))
    cell_box_height_px = int(rng.randint(int(render_params["cell_box_height_min_px"]), int(render_params["cell_box_height_max_px"])))
    canvas_width, canvas_height = _sequence_canvas_size(
        strip_length=int(sample.strip_length),
        cell_box_width_px=int(cell_box_width_px),
        cell_box_height_px=int(cell_box_height_px),
        render_params=render_params,
    )
    layout = resolve_single_panel_layout(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
        reserve_title=False,
    )
    image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
    draw_single_panel(
        image=image,
        layout=layout,
        background_rgb=tuple(int(value) for value in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(value) for value in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(value) for value in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(value) for value in render_params["header_text_rgb"]),
        corner_radius_px=int(render_params["panel_corner_radius_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
        scene_title="",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )
    cell_slots = resolve_horizontal_row_slots(
        tuple(int(value) for value in layout.scene_content_xyxy),
        cell_count=int(sample.strip_length),
        cell_padding_px=int(render_params["cell_padding_px"]),
        target_aspect_ratio=float(cell_box_width_px) / float(max(1, cell_box_height_px)),
    )
    draw = ImageDraw.Draw(image)
    rendered_icons: List[_RenderedStripIcon] = []
    rendered_cells: List[Dict[str, Any]] = []
    selected_indices = set(int(index) for index in sample.selected_run_indices)
    for cell_index, (plan, cell_bbox) in enumerate(zip(plans, cell_slots)):
        cell_bbox = tuple(int(value) for value in cell_bbox)
        draw.rounded_rectangle(
            cell_bbox,
            radius=max(0, int(render_params["cell_corner_radius_px"])),
            outline=tuple(int(value) for value in render_params["cell_border_rgb"]),
            width=2,
            fill=tuple(int(value) for value in render_params["panel_fill_rgb"]),
        )
        sprite = render_planned_named_icon_sprite(plan)
        inner_bbox = (
            int(cell_bbox[0] + int(render_params["cell_icon_padding_px"])),
            int(cell_bbox[1] + int(render_params["cell_icon_padding_px"])),
            int(cell_bbox[2] - int(render_params["cell_icon_padding_px"])),
            int(cell_bbox[3] - int(render_params["cell_icon_padding_px"])),
        )
        if int(sprite.size[0]) > int(inner_bbox[2] - inner_bbox[0]) or int(sprite.size[1]) > int(inner_bbox[3] - inner_bbox[1]):
            raise ValueError("named icon sprite does not fit row cell")
        center = (
            0.5 * float(inner_bbox[0] + inner_bbox[2]),
            0.5 * float(inner_bbox[1] + inner_bbox[3]),
        )
        paste_bbox = bbox_from_center_dimensions(center, width=int(sprite.size[0]), height=int(sprite.size[1]))
        image.alpha_composite(sprite, (int(paste_bbox[0]), int(paste_bbox[1])))
        instance_id = f"strip_cell_{int(cell_index)}"
        rendered_icons.append(
            _RenderedStripIcon(
                instance_id=str(instance_id),
                cell_index=int(cell_index),
                shape_id=str(plan.shape_id),
                shape_name=procedural_named_icon_display_name(str(plan.shape_id)),
                bbox_xyxy=tuple(int(value) for value in paste_bbox),
                cell_bbox_xyxy=tuple(int(value) for value in cell_bbox),
                nominal_size_px=int(plan.nominal_size_px),
                tint_rgb=tuple(int(value) for value in plan.tint_rgb),
                fill_style=str(plan.fill_style),
                rotation_degrees=int(plan.rotation_degrees),
                is_target_shape=str(plan.shape_id) == str(sample.target_shape_id),
                is_selected_run_member=int(cell_index) in selected_indices,
                noise_edits=tuple(serialize_icon_noise_edits(plan.noise_edits)),
                noise_seed=None if plan.noise_seed is None else int(plan.noise_seed),
            )
        )
        rendered_cells.append(
            {
                "entity_kind": "strip_cell",
                "instance_id": f"cell_{int(cell_index)}",
                "cell_index": int(cell_index),
                "cell_bbox_xyxy": [int(value) for value in cell_bbox],
                "shape_id": str(plan.shape_id),
                "shape_name": procedural_named_icon_display_name(str(plan.shape_id)),
            }
        )
    return _ScenePayload(
        image=image.convert("RGB"),
        icons=tuple(rendered_icons),
        cells=tuple(rendered_cells),
        panel_geometry=single_panel_geometry_to_trace(layout),
        cell_box_width_px=int(cell_box_width_px),
        cell_box_height_px=int(cell_box_height_px),
        sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in sampled_palette_rgb),
    )


def _serialize_icon(icon: _RenderedStripIcon) -> Dict[str, Any]:
    return {
        "entity_kind": "named_icon",
        "instance_id": str(icon.instance_id),
        "cell_index": int(icon.cell_index),
        "shape_id": str(icon.shape_id),
        "shape_name": str(icon.shape_name),
        "bbox_xyxy": [int(value) for value in icon.bbox_xyxy],
        "cell_bbox_xyxy": [int(value) for value in icon.cell_bbox_xyxy],
        "nominal_size_px": int(icon.nominal_size_px),
        "tint_rgb": [int(value) for value in icon.tint_rgb],
        "fill_style": str(icon.fill_style),
        "rotation_degrees": int(icon.rotation_degrees),
        "is_target_shape": bool(icon.is_target_shape),
        "is_selected_run_member": bool(icon.is_selected_run_member),
        "noise_edits": [dict(value) for value in icon.noise_edits],
        "noise_seed": None if icon.noise_seed is None else int(icon.noise_seed),
    }




@register_task
class IconsSequenceNamedShapeRunLengthTask:
    """Ask for longest/shortest consecutive run length of a named icon shape."""

    task_id = TASK_ID
    domain = "icons"
    scene_id = "sequence"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        render_params = resolve_icon_cell_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            instance_seed=int(instance_seed),
        )
        if int(render_params["cell_box_width_min_px"]) > int(render_params["cell_box_width_max_px"]):
            raise ValueError("cell_box_width_min_px must be <= cell_box_width_max_px")
        if int(render_params["cell_box_height_min_px"]) > int(render_params["cell_box_height_max_px"]):
            raise ValueError("cell_box_height_min_px must be <= cell_box_height_max_px")
        last_error: Exception | None = None
        sample: _SampleSpec | None = None
        scene: _ScenePayload | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_spec(instance_seed=int(instance_seed), params=params)
                scene_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:scene", int(attempt))
                plans, sampled_palette_rgb = _build_icon_plans(
                    sample=sample,
                    instance_seed=int(instance_seed),
                    render_params=render_params,
                    rng=scene_rng,
                )
                scene = _render_scene(
                    sample=sample,
                    plans=plans,
                    render_params=render_params,
                    rng=scene_rng,
                    sampled_palette_rgb=sampled_palette_rgb,
                )
                break
            except Exception as exc:  # pragma: no cover - exercised by smoke tests.
                last_error = exc
                sample = None
                scene = None
        if sample is None or scene is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        annotation_bboxes = sort_bboxes_reading_order(
            icon.bbox_xyxy for icon in scene.icons if bool(icon.is_selected_run_member)
        )
        if len(annotation_bboxes) != int(sample.answer):
            raise RuntimeError("rendered named-strip annotation length does not match answer")
        annotation_payload = bbox_set_annotation(annotation_bboxes)
        selected_instance_ids = tuple(
            str(icon.instance_id)
            for icon in scene.icons
            if bool(icon.is_selected_run_member)
        )
        shape_counts = dict(Counter(str(icon.shape_id) for icon in scene.icons))

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text_longest_shape_run_length",
                "question_text_shortest_shape_run_length",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        question_key = f"question_text_{sample.query_id}"
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults[question_key]).format(target_shape_name=str(sample.target_shape_name)),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]).format(target_shape_name=str(sample.target_shape_name)),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        serialized_icons = [_serialize_icon(icon) for icon in scene.icons]
        target_run_lengths = _target_run_lengths(sample.target_runs)
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_named_strip_run_length",
                "scene_id": SCENE_ID,
                "entities": [
                    *[dict(cell) for cell in scene.cells],
                    *serialized_icons,
                ],
                "relations": {
                    "row_rule": "consecutive_target_shape_runs",
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "shape_counts": {str(key): int(value) for key, value in shape_counts.items()},
                    "target_runs": [
                        {"start_index": int(start), "end_index": int(end), "length": int(end) - int(start) + 1}
                        for start, end in sample.target_runs
                    ],
                    "selected_run_indices": [int(index) for index in sample.selected_run_indices],
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene.panel_geometry),
                },
            },
            "query_spec": {
                "query_id": str(sample.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_shape_id": str(sample.target_shape_id),
                    "target_shape_name": str(sample.target_shape_name),
                    "answer": int(sample.answer),
                    "strip_length": int(sample.strip_length),
                    "query_id_probabilities": dict(sample.query_probabilities),
                    "answer_probabilities": dict(sample.answer_probabilities),
                    "strip_length_probabilities": dict(sample.strip_length_probabilities),
                    "shape_id_support": list(_shape_support(params)),
                    "shape_probabilities": dict(sample.shape_probabilities),
                    "named_icon_fill_style_support": list(sample.fill_style_support),
                    "fill_style_probabilities": dict(sample.fill_style_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": list(scene.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "panel_geometry": dict(scene.panel_geometry),
                "style": {
                    **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=scene.sampled_palette_rgb),
                    "cell_box_width_px": int(scene.cell_box_width_px),
                    "cell_box_height_px": int(scene.cell_box_height_px),
                    "cell_padding_px": int(render_params["cell_padding_px"]),
                    "cell_icon_padding_px": int(render_params["cell_icon_padding_px"]),
                    "cell_corner_radius_px": int(render_params["cell_corner_radius_px"]),
                    "cell_border_rgb": list(render_params["cell_border_rgb"]),
                    "named_icon_fill_style_support": list(sample.fill_style_support),
                },
            },
            "render_map": {
                "image_id": "img0",
                "object_bboxes_px": {
                    str(icon.instance_id): [int(value) for value in icon.bbox_xyxy]
                    for icon in scene.icons
                },
                "selected_run_instance_ids": list(selected_instance_ids),
            },
            "execution_trace": {
                "scene_variant": "single_panel_named_strip_row",
                "query_id": str(sample.query_id),
                "question_format": "named_shape_run_length",
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "strip_length": int(sample.strip_length),
                "shape_ids_by_cell": [str(value) for value in sample.shape_ids],
                "target_runs": [
                    {"start_index": int(start), "end_index": int(end), "length": int(end) - int(start) + 1}
                    for start, end in sample.target_runs
                ],
                "target_run_lengths": [int(value) for value in target_run_lengths],
                "selected_run_indices": [int(index) for index in sample.selected_run_indices],
                "selected_run_instance_ids": list(selected_instance_ids),
                "answer": int(sample.answer),
            },
            "witness_symbolic": {
                "query_id": str(sample.query_id),
                "target_shape_id": str(sample.target_shape_id),
                "target_shape_name": str(sample.target_shape_name),
                "answer": int(sample.answer),
                "selected_run_indices": [int(index) for index in sample.selected_run_indices],
                "selected_run_instance_ids": list(selected_instance_ids),
            },
            "projected_annotation": dict(annotation_payload["projected_annotation"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(sample.answer)),
            annotation_gt=TypedValue(type=str(annotation_payload["annotation_type"]), value=list(annotation_payload["annotation_value"])),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
        )


__all__ = ["IconsSequenceNamedShapeRunLengthTask"]
