"""Physics waveform-panel task for comparing wave properties across panels."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_render_int
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_NAMESPACE = "physics_waves_waveform_panel"
SCENE_ID = "waveform_panel"
TASK_ID = "task_physics__waveform_panel__wave_property_extremum_label"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("clean_stack", "grid_stack", "lab_sheet")
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "highest_amplitude_label",
    "lowest_amplitude_label",
    "highest_frequency_label",
    "lowest_frequency_label",
    "longest_wavelength_label",
    "shortest_wavelength_label",
)
PANEL_COUNT_SUPPORT: Tuple[int, ...] = (4, 5, 6)
PANEL_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
QUERY_PROPERTY: Dict[str, str] = {
    "highest_amplitude_label": "amplitude",
    "lowest_amplitude_label": "amplitude",
    "highest_frequency_label": "frequency",
    "lowest_frequency_label": "frequency",
    "longest_wavelength_label": "wavelength",
    "shortest_wavelength_label": "wavelength",
}
QUERY_EXTREMUM: Dict[str, str] = {
    "highest_amplitude_label": "highest",
    "lowest_amplitude_label": "lowest",
    "highest_frequency_label": "highest",
    "lowest_frequency_label": "lowest",
    "longest_wavelength_label": "longest",
    "shortest_wavelength_label": "shortest",
}

_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "waves")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_NAMESPACE,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="waves", apply_prob=0.5)


@dataclass(frozen=True)
class _TaskDefaults:
    canvas_width: int = 1180
    canvas_height: int = 760
    sheet_left_px: int = 58
    sheet_top_px: int = 52
    sheet_right_margin_px: int = 58
    sheet_bottom_margin_px: int = 44
    stack_left_px: int = 96
    stack_top_px: int = 112
    stack_width_px: int = 988
    stack_height_px: int = 570
    panel_gap_px: int = 10
    label_font_size_px: int = 24
    title_font_size_px: int = 27
    wave_line_width_px: int = 4
    grid_line_width_px: int = 1
    midline_width_px: int = 2


@dataclass(frozen=True)
class _ResolvedAxes:
    scene_variant: str
    query_id: str
    panel_count: int
    correct_option_letter: str
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    panel_count_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _PanelSpec:
    label: str
    amplitude_rank: int
    cycle_count: int
    amplitude_px: float
    bbox_px: List[float]
    wave_bbox_px: List[float]
    label_bbox_px: List[float]
    is_correct: bool


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_bboxes: List[List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _uniform_probability(values: Sequence[str | int]) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if not support:
        return {}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def _scene_variant_support() -> Tuple[str, ...]:
    weights = _GEN_DEFAULTS.get("scene_variant_weights", {})
    if isinstance(weights, Mapping):
        supported = tuple(str(value) for value, weight in weights.items() if float(weight) > 0.0)
        if supported:
            return supported
    return SUPPORTED_SCENE_VARIANTS


def _panel_count_support() -> Tuple[int, ...]:
    weights = _GEN_DEFAULTS.get("panel_count_weights", {})
    if isinstance(weights, Mapping):
        supported = tuple(int(value) for value, weight in weights.items() if float(weight) > 0.0)
        supported = tuple(value for value in supported if value in PANEL_COUNT_SUPPORT)
        if supported:
            return supported
    return PANEL_COUNT_SUPPORT


def _target_answer_probabilities(*, panel_count_probs: Mapping[str, float], selected: str | None) -> Dict[str, float]:
    if selected is not None:
        return {str(selected): 1.0}
    probabilities: Dict[str, float] = {label: 0.0 for label in PANEL_LABELS}
    for raw_count, probability in panel_count_probs.items():
        count = int(raw_count)
        if count <= 0:
            continue
        active = PANEL_LABELS[:count]
        for label in active:
            probabilities[str(label)] = float(probabilities.get(str(label), 0.0)) + (float(probability) / float(count))
    return {label: float(value) for label, value in probabilities.items() if float(value) > 0.0}


def _resolve_query_id(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = str(params.get("query_id", "") or "").strip()
    if explicit:
        if explicit not in SUPPORTED_QUERY_IDS:
            raise ValueError(f"unsupported waveform-panel query_id: {explicit}")
        return explicit, {explicit: 1.0}
    index = int(instance_seed) % len(SUPPORTED_QUERY_IDS)
    return str(SUPPORTED_QUERY_IDS[index]), _uniform_probability(SUPPORTED_QUERY_IDS)


def _resolve_scene_variant(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    support = _scene_variant_support()
    explicit = str(params.get("scene_variant", "") or "").strip()
    if explicit:
        if explicit not in support:
            raise ValueError(f"unsupported waveform-panel scene_variant: {explicit}")
        return explicit, {explicit: 1.0}
    index = (int(instance_seed) // max(1, len(SUPPORTED_QUERY_IDS))) % len(support)
    return str(support[index]), _uniform_probability(support)


def _resolve_panel_count(instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    support = _panel_count_support()
    raw = params.get("panel_count")
    if raw is not None:
        count = int(raw)
        if count not in support:
            raise ValueError(f"unsupported waveform-panel panel_count: {count}")
        return int(count), {str(count): 1.0}
    index = (int(instance_seed) // max(1, len(SUPPORTED_QUERY_IDS) * len(SUPPORTED_SCENE_VARIANTS))) % len(support)
    count = int(support[index])
    return count, _uniform_probability(support)


def _resolve_target_label(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    panel_count: int,
) -> Tuple[str, Dict[str, float]]:
    raw = params.get("target_label", params.get("correct_option_letter", params.get("target_answer")))
    if raw is not None:
        label = str(raw).strip().upper()
        if label not in PANEL_LABELS[: int(panel_count)]:
            raise ValueError(f"target label {label!r} is not visible for panel_count={panel_count}")
        return label, {label: 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_NAMESPACE}.target_label.{int(panel_count)}",
    ) % int(panel_count)
    return str(PANEL_LABELS[index]), {}


def _resolve_axes(instance_seed: int, params: Mapping[str, Any]) -> _ResolvedAxes:
    query_id, query_probs = _resolve_query_id(int(instance_seed), params)
    scene_variant, scene_probs = _resolve_scene_variant(int(instance_seed), params)
    panel_count, panel_probs = _resolve_panel_count(int(instance_seed), params)
    correct_label, explicit_target_probs = _resolve_target_label(
        instance_seed=int(instance_seed),
        params=params,
        panel_count=int(panel_count),
    )
    target_probs = explicit_target_probs or _target_answer_probabilities(
        panel_count_probs=panel_probs,
        selected=None,
    )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        panel_count=int(panel_count),
        correct_option_letter=str(correct_label),
        scene_variant_probabilities={str(k): float(v) for k, v in scene_probs.items()},
        query_id_probabilities={str(k): float(v) for k, v in query_probs.items()},
        panel_count_probabilities={str(k): float(v) for k, v in panel_probs.items()},
        target_answer_probabilities={str(k): float(v) for k, v in target_probs.items()},
    )


def _shuffled_values(values: Sequence[int], *, instance_seed: int, namespace: str) -> List[int]:
    out = [int(value) for value in values]
    rng = spawn_rng(int(instance_seed), str(namespace))
    rng.shuffle(out)
    return out


def _rank_assignment(
    *,
    count: int,
    target_index: int | None,
    target_mode: str | None,
    instance_seed: int,
    namespace: str,
) -> List[int]:
    support = list(range(1, int(count) + 1))
    if target_index is None or target_mode not in {"high", "low"}:
        return _shuffled_values(support, instance_seed=int(instance_seed), namespace=str(namespace))
    target_value = int(count) if target_mode == "high" else 1
    remaining_values = [value for value in support if int(value) != int(target_value)]
    remaining_values = _shuffled_values(
        remaining_values,
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.remaining",
    )
    out: List[int] = []
    cursor = 0
    for index in range(int(count)):
        if int(index) == int(target_index):
            out.append(int(target_value))
        else:
            out.append(int(remaining_values[cursor]))
            cursor += 1
    return out


def _query_target_modes(query_id: str) -> Tuple[str | None, str | None]:
    if query_id == "highest_amplitude_label":
        return "high", None
    if query_id == "lowest_amplitude_label":
        return "low", None
    if query_id in {"highest_frequency_label", "shortest_wavelength_label"}:
        return None, "high"
    if query_id in {"lowest_frequency_label", "longest_wavelength_label"}:
        return None, "low"
    return None, None


def _build_panel_specs(
    *,
    axes: _ResolvedAxes,
    render_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    panel_count = int(axes.panel_count)
    labels = list(PANEL_LABELS[:panel_count])
    target_index = labels.index(str(axes.correct_option_letter))
    amplitude_mode, cycle_mode = _query_target_modes(str(axes.query_id))
    amplitude_ranks = _rank_assignment(
        count=panel_count,
        target_index=target_index if amplitude_mode else None,
        target_mode=amplitude_mode,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_NAMESPACE}.amplitude_ranks.{axes.query_id}",
    )
    cycle_counts = _rank_assignment(
        count=panel_count,
        target_index=target_index if cycle_mode else None,
        target_mode=cycle_mode,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_NAMESPACE}.cycle_counts.{axes.query_id}",
    )

    stack_top = float(render_defaults["stack_top_px"])
    stack_left = float(render_defaults["stack_left_px"])
    stack_width = float(render_defaults["stack_width_px"])
    stack_height = float(render_defaults["stack_height_px"])
    panel_gap = float(render_defaults["panel_gap_px"])
    panel_height = (stack_height - (panel_gap * float(panel_count - 1))) / float(panel_count)
    min_amp = max(12.0, panel_height * 0.18)
    max_amp = max(min_amp + 6.0, panel_height * 0.39)
    rank_span = max(1, panel_count - 1)

    panels: List[Dict[str, Any]] = []
    for index, label in enumerate(labels):
        top = stack_top + (float(index) * (panel_height + panel_gap))
        bottom = top + panel_height
        bbox = _bbox((stack_left, top, stack_left + stack_width, bottom))
        rank = int(amplitude_ranks[index])
        amplitude_px = min_amp + ((float(rank - 1) / float(rank_span)) * (max_amp - min_amp))
        panels.append(
            {
                "label": str(label),
                "amplitude_rank": int(rank),
                "cycle_count": int(cycle_counts[index]),
                "amplitude_px": round(float(amplitude_px), 3),
                "bbox_px": bbox,
                "is_correct": str(label) == str(axes.correct_option_letter),
            }
        )
    summary = {
        "panel_height_px": round(float(panel_height), 3),
        "amplitude_min_px": round(float(min_amp), 3),
        "amplitude_max_px": round(float(max_amp), 3),
    }
    return panels, summary


def _draw_grid(
    draw: ImageDraw.ImageDraw,
    *,
    panel_box: Sequence[float],
    scene_variant: str,
    style: Any,
    grid_width: int,
    midline_width: int,
) -> None:
    left, top, right, bottom = [float(value) for value in panel_box]
    grid_rgb = tuple(int(v) for v in style.grid_minor_rgb)
    guide_rgb = tuple(int(v) for v in style.guide_rgb)
    mid_y = (top + bottom) * 0.5
    if str(scene_variant) in {"grid_stack", "lab_sheet"}:
        for idx in range(1, 10):
            x = left + ((right - left) * (float(idx) / 10.0))
            draw.line((x, top + 4.0, x, bottom - 4.0), fill=grid_rgb, width=max(1, int(grid_width)))
        for frac in (0.25, 0.75):
            y = top + ((bottom - top) * frac)
            draw.line((left + 4.0, y, right - 4.0, y), fill=grid_rgb, width=max(1, int(grid_width)))
    draw.line((left + 6.0, mid_y, right - 6.0, mid_y), fill=guide_rgb, width=max(1, int(midline_width)))
    if str(scene_variant) == "lab_sheet":
        tick_rgb = tuple(int(v) for v in style.axis_rgb)
        for idx in range(0, 11):
            x = left + ((right - left) * (float(idx) / 10.0))
            draw.line((x, bottom - 13.0, x, bottom - 4.0), fill=tick_rgb, width=1)


def _draw_waveform(
    draw: ImageDraw.ImageDraw,
    *,
    panel_box: Sequence[float],
    amplitude_px: float,
    cycle_count: int,
    style: Any,
    line_width: int,
) -> List[float]:
    left, top, right, bottom = [float(value) for value in panel_box]
    wave_left = left + 82.0
    wave_right = right - 28.0
    mid_y = (top + bottom) * 0.5
    points: List[Tuple[float, float]] = []
    sample_count = 260
    phase = 0.0
    for idx in range(sample_count + 1):
        t = float(idx) / float(sample_count)
        x = wave_left + (t * (wave_right - wave_left))
        y = mid_y - (float(amplitude_px) * math.sin((2.0 * math.pi * float(cycle_count) * t) + phase))
        points.append((float(x), float(y)))
    shadow = tuple(int(v) for v in style.stroke_rgb)
    wave_rgb = tuple(int(v) for v in style.secondary_accent_rgb)
    draw.line(points, fill=shadow, width=max(1, int(line_width) + 2), joint="curve")
    draw.line(points, fill=wave_rgb, width=max(1, int(line_width)), joint="curve")
    return _bbox((wave_left, mid_y - float(amplitude_px), wave_right, mid_y + float(amplitude_px)))


def _render_scene(
    *,
    image: Image.Image,
    axes: _ResolvedAxes,
    render_defaults: Mapping[str, Any],
    font_family: str,
    style: Any,
    instance_seed: int,
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    canvas_width, canvas_height = image.size
    title_font = load_font(int(render_defaults["title_font_size_px"]), bold=True, font_family=font_family)
    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=True, font_family=font_family)
    text_rgb = tuple(int(value) for value in style.label_rgb)
    panel_fill = tuple(int(value) for value in style.panel_fill_rgb)
    panel_alt = tuple(int(value) for value in style.panel_alt_fill_rgb)
    panel_border = tuple(int(value) for value in style.panel_border_rgb)

    sheet_box = (
        float(render_defaults["sheet_left_px"]),
        float(render_defaults["sheet_top_px"]),
        float(canvas_width - int(render_defaults["sheet_right_margin_px"])),
        float(canvas_height - int(render_defaults["sheet_bottom_margin_px"])),
    )
    draw.rounded_rectangle(sheet_box, radius=20, fill=panel_fill, outline=panel_border, width=3)
    draw_centered_text(
        draw,
        text="Waveform comparison",
        center=((sheet_box[0] + sheet_box[2]) * 0.5, sheet_box[1] + 34.0),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )

    panel_dicts, geometry_summary = _build_panel_specs(
        axes=axes,
        render_defaults=render_defaults,
        instance_seed=int(instance_seed),
    )
    scene_entities: List[Dict[str, Any]] = []
    rendered_panels: List[_PanelSpec] = []
    for index, panel in enumerate(panel_dicts):
        box = list(panel["bbox_px"])
        fill = panel_alt if index % 2 else panel_fill
        draw.rounded_rectangle(tuple(box), radius=10, fill=fill, outline=panel_border, width=2)
        _draw_grid(
            draw,
            panel_box=box,
            scene_variant=str(axes.scene_variant),
            style=style,
            grid_width=int(render_defaults["grid_line_width_px"]),
            midline_width=int(render_defaults["midline_width_px"]),
        )
        label_bbox = draw_centered_text(
            draw,
            text=str(panel["label"]),
            center=(float(box[0]) + 36.0, (float(box[1]) + float(box[3])) * 0.5),
            font=label_font,
            fill=text_rgb,
            stroke_fill=resolve_text_stroke_fill(text_rgb),
            stroke_width=1,
        )
        wave_bbox = _draw_waveform(
            draw,
            panel_box=box,
            amplitude_px=float(panel["amplitude_px"]),
            cycle_count=int(panel["cycle_count"]),
            style=style,
            line_width=int(render_defaults["wave_line_width_px"]),
        )
        spec = _PanelSpec(
            label=str(panel["label"]),
            amplitude_rank=int(panel["amplitude_rank"]),
            cycle_count=int(panel["cycle_count"]),
            amplitude_px=float(panel["amplitude_px"]),
            bbox_px=list(box),
            wave_bbox_px=list(wave_bbox),
            label_bbox_px=list(label_bbox),
            is_correct=bool(panel["is_correct"]),
        )
        rendered_panels.append(spec)
        scene_entities.append(
            {
                "entity_id": f"panel_{spec.label}",
                "entity_type": "waveform_panel",
                "bbox_px": list(spec.bbox_px),
                "meta": {
                    "label": str(spec.label),
                    "amplitude_rank": int(spec.amplitude_rank),
                    "cycle_count": int(spec.cycle_count),
                    "is_correct": bool(spec.is_correct),
                },
            }
        )

    selected = next(panel for panel in rendered_panels if panel.is_correct)
    annotation_bboxes = [list(selected.bbox_px)]
    render_map = {
        "scene_variant": str(axes.scene_variant),
        "query_id": str(axes.query_id),
        "query_property": str(QUERY_PROPERTY[str(axes.query_id)]),
        "query_extremum": str(QUERY_EXTREMUM[str(axes.query_id)]),
        "panel_count": int(axes.panel_count),
        "active_option_labels": list(PANEL_LABELS[: int(axes.panel_count)]),
        "correct_option_letter": str(axes.correct_option_letter),
        "selected_panel_bbox_px": list(selected.bbox_px),
        "panel_geometry": dict(geometry_summary),
        "panels": [
            {
                "label": str(panel.label),
                "amplitude_rank": int(panel.amplitude_rank),
                "cycle_count": int(panel.cycle_count),
                "wavelength_relative": round(1.0 / float(panel.cycle_count), 6),
                "amplitude_px": round(float(panel.amplitude_px), 3),
                "bbox_px": list(panel.bbox_px),
                "wave_bbox_px": list(panel.wave_bbox_px),
                "label_bbox_px": list(panel.label_bbox_px),
                "is_correct": bool(panel.is_correct),
            }
            for panel in rendered_panels
        ],
    }
    return _RenderedScene(
        image=image,
        annotation_bboxes=[list(bbox) for bbox in annotation_bboxes],
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
    )




@register_task
class PhysicsWaveformPanelWavePropertyExtremumLabelTask:
    """Choose the waveform panel with the requested wave-property extremum."""

    task_id = TASK_ID
    domain = "physics"
    scene_id = "waves"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        axes = _resolve_axes(int(instance_seed), params)

        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
        background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
            instance_seed=int(instance_seed),
            params=params,
            scene_id=SCENE_ID,
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            require_grid=True,
        )
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_NAMESPACE}.font",
            params=params,
        )
        font_record = get_font_family_record(str(font_family))
        render_defaults = {
            key: resolve_render_int(
                params,
                _RENDER_DEFAULTS,
                key,
                int(getattr(_DEFAULTS, key)),
                instance_seed=int(instance_seed),
                namespace=TASK_NAMESPACE,
            )
            for key in (
                "sheet_left_px",
                "sheet_top_px",
                "sheet_right_margin_px",
                "sheet_bottom_margin_px",
                "stack_left_px",
                "stack_top_px",
                "stack_width_px",
                "stack_height_px",
                "panel_gap_px",
                "label_font_size_px",
                "title_font_size_px",
                "wave_line_width_px",
                "grid_line_width_px",
                "midline_width_px",
            )
        }
        rendered = _render_scene(
            image=background,
            axes=axes,
            render_defaults=render_defaults,
            font_family=str(font_family),
            style=diagram_style,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                f"answer_hint_{axes.query_id}",
                f"annotation_hint_{axes.query_id}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_gt = TypedValue(type="option_letter", value=str(axes.correct_option_letter))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in rendered.annotation_bboxes])
        json_example, json_example_answer_only = build_prompt_json_examples(
            annotation_value=annotation_gt.value,
            answer_type=str(answer_gt.type),
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{axes.query_id}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{axes.query_id}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        panels_payload = [dict(panel) for panel in rendered.render_map["panels"]]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"physics_waveform_panel_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "query_property": str(QUERY_PROPERTY[str(axes.query_id)]),
                    "query_extremum": str(QUERY_EXTREMUM[str(axes.query_id)]),
                    "panel_count": int(axes.panel_count),
                    "correct_option_letter": str(axes.correct_option_letter),
                    "target_answer": str(axes.correct_option_letter),
                },
            },
            "query_spec": {
                "query_id": str(axes.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "panel_count": int(axes.panel_count),
                    "correct_option_letter": str(axes.correct_option_letter),
                    "target_answer": str(axes.correct_option_letter),
                    "answer_support": list(PANEL_LABELS[: int(axes.panel_count)]),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "panel_count_probabilities": dict(axes.panel_count_probabilities),
                    "target_answer_probabilities": dict(axes.target_answer_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "waveform_panel",
                    "selection_policy": {
                        "pool": "global_approved_font_pool",
                        "include_tags": [],
                        "exclude_tags": [],
                        "exclusion_reason": "",
                    },
                },
                "technical_diagram_style": dict(diagram_style_meta),
                "background_style": background_meta,
                "post_image_noise": post_noise_meta,
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "query_property": str(QUERY_PROPERTY[str(axes.query_id)]),
                "query_extremum": str(QUERY_EXTREMUM[str(axes.query_id)]),
                "panel_count": int(axes.panel_count),
                "correct_option_letter": str(axes.correct_option_letter),
                "target_answer": str(axes.correct_option_letter),
                "answer_type": "option_letter",
                "answer_option_labels": list(PANEL_LABELS[: int(axes.panel_count)]),
                "panels": list(panels_payload),
                "annotation_entity_ids": [f"panel_{str(axes.correct_option_letter)}"],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [f"panel_{str(axes.correct_option_letter)}"],
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in rendered.annotation_bboxes],
                "pixel_bbox_set": [list(bbox) for bbox in rendered.annotation_bboxes],
            },
            "background": background_meta,
            "technical_diagram_style": dict(diagram_style_meta),
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(axes.query_id),
        )


__all__ = ["PhysicsWaveformPanelWavePropertyExtremumLabelTask"]
