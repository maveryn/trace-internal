"""Physics signal-transform task for matching waveforms to spectra."""

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


TASK_NAMESPACE = "physics_waves_signal_transform"
SCENE_ID = "signal_transform"
SINUSOID_TASK_ID = "task_physics__signal_transform__sinusoid_component_spectrum_match_label"
PERIODIC_TASK_ID = "task_physics__signal_transform__periodic_harmonic_spectrum_match_label"
PULSE_TASK_ID = "task_physics__signal_transform__pulse_width_spectrum_match_label"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("clean_match", "grid_match", "lab_sheet")
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "sinusoid_component_spectrum",
    "periodic_wave_harmonic_spectrum",
    "pulse_width_spectrum",
)
QUERY_FAMILIES: Dict[str, Tuple[str, ...]] = {
    "sinusoid_component_spectrum": ("single_sinusoid", "two_tone"),
    "periodic_wave_harmonic_spectrum": ("square_wave", "triangle_wave", "sawtooth_wave"),
    "pulse_width_spectrum": ("narrow_pulse", "wide_pulse"),
}
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E")

_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "waves")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_NAMESPACE,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="waves", apply_prob=0.5)


@dataclass(frozen=True)
class _TaskDefaults:
    canvas_width: int = 1280
    canvas_height: int = 860
    sheet_left_px: int = 54
    sheet_top_px: int = 46
    sheet_right_margin_px: int = 54
    sheet_bottom_margin_px: int = 46
    input_left_px: int = 92
    input_top_px: int = 112
    input_width_px: int = 1096
    input_height_px: int = 194
    options_left_px: int = 92
    options_top_px: int = 346
    option_width_px: int = 338
    option_height_px: int = 198
    option_gap_x_px: int = 35
    option_gap_y_px: int = 34
    title_font_size_px: int = 28
    label_font_size_px: int = 24
    axis_font_size_px: int = 19
    waveform_line_width_px: int = 4
    spectrum_line_width_px: int = 4
    grid_line_width_px: int = 1


@dataclass(frozen=True)
class _ResolvedAxes:
    scene_variant: str
    query_id: str
    waveform_family: str
    correct_option_letter: str
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    waveform_family_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _SpectrumSpec:
    signature: str
    kind: str
    bins: Tuple[int, ...]
    amplitudes: Tuple[float, ...]
    lobe_width: float
    decay: str


@dataclass(frozen=True)
class _SignalScenario:
    waveform_family: str
    time_cycles: int
    tone_bins: Tuple[int, ...]
    pulse_width: float
    correct_spectrum: _SpectrumSpec
    option_specs: Dict[str, _SpectrumSpec]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _uniform_probability(values: Sequence[str]) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if not support:
        return {}
    probability = 1.0 / float(len(support))
    return {value: float(probability) for value in support}


def _weighted_support(defaults_key: str, fallback: Sequence[str]) -> Tuple[str, ...]:
    weights = _GEN_DEFAULTS.get(defaults_key, {})
    if isinstance(weights, Mapping):
        supported = tuple(str(value) for value, weight in weights.items() if float(weight) > 0.0)
        if supported:
            return supported
    return tuple(str(value) for value in fallback)


def _resolve_scene_variant(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    support = _weighted_support("scene_variant_weights", SUPPORTED_SCENE_VARIANTS)
    explicit = str(params.get("scene_variant", "") or "").strip()
    if explicit:
        if explicit not in support:
            raise ValueError(f"unsupported signal-transform scene_variant: {explicit}")
        return explicit, {explicit: 1.0}
    index = (int(instance_seed) // max(1, len(SUPPORTED_QUERY_IDS))) % len(support)
    return str(support[index]), _uniform_probability(support)


def _resolve_query_id(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    support = _weighted_support("query_id_weights", SUPPORTED_QUERY_IDS)
    explicit = str(params.get("query_id", "") or "").strip()
    if explicit:
        if explicit not in support:
            raise ValueError(f"unsupported signal-transform query_id: {explicit}")
        return explicit, {explicit: 1.0}
    index = int(instance_seed) % len(support)
    return str(support[index]), _uniform_probability(support)


def _resolve_waveform_family(
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str, Dict[str, float]]:
    supported = QUERY_FAMILIES[str(query_id)]
    explicit = str(params.get("waveform", "") or "").strip()
    if explicit:
        if explicit not in supported:
            raise ValueError(f"waveform_family {explicit!r} is not supported for {query_id}")
        return explicit, {explicit: 1.0}
    index = (int(instance_seed) // max(1, len(SUPPORTED_QUERY_IDS) * len(SUPPORTED_SCENE_VARIANTS))) % len(supported)
    return str(supported[index]), _uniform_probability(supported)


def _resolve_correct_option_letter(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    raw = params.get("correct_option_letter", params.get("target_label", params.get("target_answer")))
    if raw is not None:
        label = str(raw).strip().upper()
        if label not in OPTION_LABELS:
            raise ValueError(f"unsupported signal-transform option label: {label}")
        return label, {label: 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_NAMESPACE}.correct_option_letter",
    ) % len(OPTION_LABELS)
    return str(OPTION_LABELS[index]), _uniform_probability(OPTION_LABELS)


def _resolve_axes(instance_seed: int, params: Mapping[str, Any]) -> _ResolvedAxes:
    query_id, query_probs = _resolve_query_id(int(instance_seed), params)
    scene_variant, scene_probs = _resolve_scene_variant(int(instance_seed), params)
    waveform_family, waveform_probs = _resolve_waveform_family(int(instance_seed), params, str(query_id))
    correct_label, target_probs = _resolve_correct_option_letter(int(instance_seed), params)
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        waveform_family=str(waveform_family),
        correct_option_letter=str(correct_label),
        scene_variant_probabilities=dict(scene_probs),
        query_id_probabilities=dict(query_probs),
        waveform_family_probabilities=dict(waveform_probs),
        target_answer_probabilities=dict(target_probs),
    )


def _spikes(signature: str, bins: Sequence[int], amplitudes: Sequence[float], *, decay: str = "custom") -> _SpectrumSpec:
    return _SpectrumSpec(
        signature=str(signature),
        kind="spikes",
        bins=tuple(int(value) for value in bins),
        amplitudes=tuple(float(value) for value in amplitudes),
        lobe_width=0.0,
        decay=str(decay),
    )


def _sinc(signature: str, *, lobe_width: float) -> _SpectrumSpec:
    return _SpectrumSpec(
        signature=str(signature),
        kind="sinc",
        bins=(),
        amplitudes=(),
        lobe_width=float(lobe_width),
        decay="sinc_envelope",
    )


def _bell(signature: str) -> _SpectrumSpec:
    return _SpectrumSpec(
        signature=str(signature),
        kind="bell",
        bins=(),
        amplitudes=(),
        lobe_width=1.0,
        decay="smooth_bell",
    )


def _spectrum_payload(spec: _SpectrumSpec) -> Dict[str, Any]:
    return {
        "signature": str(spec.signature),
        "kind": str(spec.kind),
        "bins": list(spec.bins),
        "amplitudes": [round(float(value), 4) for value in spec.amplitudes],
        "lobe_width": round(float(spec.lobe_width), 4),
        "decay": str(spec.decay),
    }


def _unique_specs(specs: Sequence[_SpectrumSpec], *, exclude_signature: str) -> List[_SpectrumSpec]:
    out: List[_SpectrumSpec] = []
    seen = {str(exclude_signature)}
    for spec in specs:
        if str(spec.signature) in seen:
            continue
        seen.add(str(spec.signature))
        out.append(spec)
    return out


def _scenario_for_family(family: str, instance_seed: int) -> Tuple[int, Tuple[int, ...], float, _SpectrumSpec, List[_SpectrumSpec]]:
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.scenario.{family}")
    if family == "single_sinusoid":
        freq = int(rng.choice([2, 3, 4, 5]))
        correct = _spikes(f"single_spike_f{freq}", [freq], [1.0])
        distractors = [
            _spikes(f"single_spike_f{freq + 1 if freq < 5 else 2}", [freq + 1 if freq < 5 else 2], [1.0]),
            _spikes(f"two_spikes_f{freq}_{min(6, freq + 2)}", [freq, min(6, freq + 2)], [1.0, 0.62]),
            _spikes("odd_harmonics_slow", [1, 3, 5, 7], [1.0, 0.35, 0.22, 0.16], decay="odd_slow"),
            _sinc("wide_sinc_envelope", lobe_width=2.9),
            _bell("smooth_bell_spectrum"),
        ]
        return freq, (freq,), 0.0, correct, distractors
    if family == "two_tone":
        choices = [(2, 5), (3, 6), (2, 4), (3, 5)]
        bins = tuple(int(value) for value in rng.choice(choices))
        correct = _spikes(f"two_spikes_f{bins[0]}_{bins[1]}", bins, [1.0, 0.66])
        distractors = [
            _spikes(f"single_spike_f{bins[0]}", [bins[0]], [1.0]),
            _spikes(f"two_spikes_f{bins[0]}_{max(1, bins[1] - 1)}", [bins[0], max(1, bins[1] - 1)], [1.0, 0.66]),
            _spikes(f"three_spikes_f{bins[0]}_{bins[1]}_7", [bins[0], bins[1], 7], [1.0, 0.66, 0.38]),
            _spikes("all_harmonics_slow", [1, 2, 3, 4, 5, 6], [1.0, 0.5, 0.33, 0.25, 0.2, 0.17], decay="all_slow"),
            _sinc("narrow_sinc_envelope", lobe_width=1.45),
        ]
        return 4, bins, 0.0, correct, distractors
    if family == "square_wave":
        correct = _spikes("odd_harmonics_slow", [1, 3, 5, 7], [1.0, 0.35, 0.22, 0.16], decay="odd_slow")
        distractors = [
            _spikes("all_harmonics_slow", [1, 2, 3, 4, 5, 6], [1.0, 0.5, 0.33, 0.25, 0.2, 0.17], decay="all_slow"),
            _spikes("odd_harmonics_fast", [1, 3, 5, 7], [1.0, 0.18, 0.09, 0.05], decay="odd_fast"),
            _spikes("even_harmonics_slow", [2, 4, 6, 8], [1.0, 0.5, 0.33, 0.25], decay="even_slow"),
            _spikes("odd_harmonics_flat", [1, 3, 5, 7], [1.0, 0.9, 0.82, 0.74], decay="odd_flat"),
            _sinc("wide_sinc_envelope", lobe_width=2.9),
        ]
        return 3, (1, 3, 5, 7), 0.0, correct, distractors
    if family == "triangle_wave":
        correct = _spikes("odd_harmonics_fast", [1, 3, 5, 7], [1.0, 0.18, 0.09, 0.05], decay="odd_fast")
        distractors = [
            _spikes("odd_harmonics_slow", [1, 3, 5, 7], [1.0, 0.35, 0.22, 0.16], decay="odd_slow"),
            _spikes("all_harmonics_fast", [1, 2, 3, 4, 5, 6], [1.0, 0.25, 0.12, 0.07, 0.05, 0.04], decay="all_fast"),
            _spikes("even_harmonics_slow", [2, 4, 6, 8], [1.0, 0.5, 0.33, 0.25], decay="even_slow"),
            _spikes("single_spike_f3", [3], [1.0]),
            _sinc("narrow_sinc_envelope", lobe_width=1.45),
        ]
        return 3, (1, 3, 5, 7), 0.0, correct, distractors
    if family == "sawtooth_wave":
        correct = _spikes("all_harmonics_slow", [1, 2, 3, 4, 5, 6], [1.0, 0.5, 0.33, 0.25, 0.2, 0.17], decay="all_slow")
        distractors = [
            _spikes("odd_harmonics_slow", [1, 3, 5, 7], [1.0, 0.35, 0.22, 0.16], decay="odd_slow"),
            _spikes("all_harmonics_flat", [1, 2, 3, 4, 5, 6], [1.0, 0.92, 0.84, 0.76, 0.68, 0.6], decay="all_flat"),
            _spikes("even_harmonics_slow", [2, 4, 6, 8], [1.0, 0.5, 0.33, 0.25], decay="even_slow"),
            _spikes("two_spikes_f2_5", [2, 5], [1.0, 0.65]),
            _bell("smooth_bell_spectrum"),
        ]
        return 3, (1, 2, 3, 4, 5, 6), 0.0, correct, distractors
    if family == "narrow_pulse":
        correct = _sinc("wide_sinc_envelope", lobe_width=2.9)
        distractors = [
            _sinc("narrow_sinc_envelope", lobe_width=1.45),
            _spikes("single_spike_f2", [2], [1.0]),
            _spikes("odd_harmonics_slow", [1, 3, 5, 7], [1.0, 0.35, 0.22, 0.16], decay="odd_slow"),
            _bell("smooth_bell_spectrum"),
            _spikes("all_harmonics_flat", [1, 2, 3, 4, 5, 6], [1.0, 0.92, 0.84, 0.76, 0.68, 0.6], decay="all_flat"),
        ]
        return 1, (), 0.22, correct, distractors
    if family == "wide_pulse":
        correct = _sinc("narrow_sinc_envelope", lobe_width=1.45)
        distractors = [
            _sinc("wide_sinc_envelope", lobe_width=2.9),
            _spikes("single_spike_f2", [2], [1.0]),
            _spikes("all_harmonics_slow", [1, 2, 3, 4, 5, 6], [1.0, 0.5, 0.33, 0.25, 0.2, 0.17], decay="all_slow"),
            _bell("smooth_bell_spectrum"),
            _spikes("odd_harmonics_flat", [1, 3, 5, 7], [1.0, 0.9, 0.82, 0.74], decay="odd_flat"),
        ]
        return 1, (), 0.44, correct, distractors
    raise ValueError(f"unsupported waveform family: {family}")


def _build_scenario(axes: _ResolvedAxes, instance_seed: int) -> _SignalScenario:
    time_cycles, tone_bins, pulse_width, correct, distractors = _scenario_for_family(
        str(axes.waveform_family),
        int(instance_seed),
    )
    distractor_specs = _unique_specs(distractors, exclude_signature=str(correct.signature))
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.option_order.{axes.waveform_family}")
    rng.shuffle(distractor_specs)
    option_specs: Dict[str, _SpectrumSpec] = {}
    cursor = 0
    for label in OPTION_LABELS:
        if str(label) == str(axes.correct_option_letter):
            option_specs[str(label)] = correct
        else:
            option_specs[str(label)] = distractor_specs[cursor]
            cursor += 1
    return _SignalScenario(
        waveform_family=str(axes.waveform_family),
        time_cycles=int(time_cycles),
        tone_bins=tuple(int(value) for value in tone_bins),
        pulse_width=float(pulse_width),
        correct_spectrum=correct,
        option_specs=dict(option_specs),
    )


def _draw_panel_frame(
    draw: ImageDraw.ImageDraw,
    *,
    box: Sequence[float],
    label: str,
    label_font: Any,
    axis_font: Any,
    style: Any,
    scene_variant: str,
) -> None:
    left, top, right, bottom = [float(value) for value in box]
    panel_fill = tuple(int(value) for value in style.panel_alt_fill_rgb)
    panel_border = tuple(int(value) for value in style.panel_border_rgb)
    text_rgb = tuple(int(value) for value in style.label_rgb)
    grid_rgb = tuple(int(value) for value in style.grid_minor_rgb)
    axis_rgb = tuple(int(value) for value in style.axis_rgb)
    draw.rounded_rectangle((left, top, right, bottom), radius=12, fill=panel_fill, outline=panel_border, width=2)
    if str(scene_variant) in {"grid_match", "lab_sheet"}:
        for idx in range(1, 6):
            x = left + (idx * (right - left) / 6.0)
            draw.line((x, top + 12.0, x, bottom - 12.0), fill=grid_rgb, width=1)
        for idx in range(1, 4):
            y = top + (idx * (bottom - top) / 4.0)
            draw.line((left + 12.0, y, right - 12.0, y), fill=grid_rgb, width=1)
    draw.line((left + 42.0, bottom - 34.0, right - 24.0, bottom - 34.0), fill=axis_rgb, width=2)
    draw.line((left + 42.0, top + 24.0, left + 42.0, bottom - 34.0), fill=axis_rgb, width=2)
    label_center_x = left + (52.0 if str(label).lower().startswith("input") else 23.0)
    draw_centered_text(
        draw,
        text=str(label),
        center=(label_center_x, top + 24.0),
        font=label_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )
    x_axis = "t" if str(label).lower().startswith("input") else "f"
    draw_centered_text(
        draw,
        text=x_axis,
        center=(right - 20.0, bottom - 22.0),
        font=axis_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )


def _draw_time_waveform(
    draw: ImageDraw.ImageDraw,
    *,
    box: Sequence[float],
    scenario: _SignalScenario,
    style: Any,
    line_width: int,
) -> List[float]:
    left, top, right, bottom = [float(value) for value in box]
    wave_left = left + 58.0
    wave_right = right - 34.0
    mid_y = top + ((bottom - top) * 0.52)
    amp = (bottom - top) * 0.28
    points: List[Tuple[float, float]] = []
    sample_count = 420
    family = str(scenario.waveform_family)
    if family in {"narrow_pulse", "wide_pulse"}:
        high_y = mid_y - amp * 0.72
        low_y = mid_y + amp * 0.42
        center = 0.5
        half_width = float(scenario.pulse_width) * 0.5
        left_edge = center - half_width
        right_edge = center + half_width
        coords = [
            (0.0, low_y),
            (left_edge, low_y),
            (left_edge, high_y),
            (right_edge, high_y),
            (right_edge, low_y),
            (1.0, low_y),
        ]
        points = [(wave_left + (t * (wave_right - wave_left)), y) for t, y in coords]
    else:
        for idx in range(sample_count + 1):
            t = float(idx) / float(sample_count)
            if family == "single_sinusoid":
                y_unit = math.sin(2.0 * math.pi * float(scenario.time_cycles) * t)
            elif family == "two_tone":
                first, second = scenario.tone_bins
                y_unit = (math.sin(2.0 * math.pi * float(first) * t) + 0.62 * math.sin(2.0 * math.pi * float(second) * t)) / 1.62
            elif family == "square_wave":
                y_unit = 1.0 if math.sin(2.0 * math.pi * float(scenario.time_cycles) * t) >= 0.0 else -1.0
            elif family == "triangle_wave":
                phase = (float(scenario.time_cycles) * t) % 1.0
                y_unit = 1.0 - (4.0 * abs(phase - 0.5))
            elif family == "sawtooth_wave":
                phase = (float(scenario.time_cycles) * t) % 1.0
                y_unit = (2.0 * phase) - 1.0
            else:
                y_unit = 0.0
            points.append((wave_left + (t * (wave_right - wave_left)), mid_y - (amp * y_unit)))
    shadow = tuple(int(value) for value in style.stroke_rgb)
    wave_rgb = tuple(int(value) for value in style.secondary_accent_rgb)
    draw.line(points, fill=shadow, width=max(1, int(line_width) + 2), joint="curve")
    draw.line(points, fill=wave_rgb, width=max(1, int(line_width)), joint="curve")
    ys = [point[1] for point in points]
    return _bbox((wave_left, min(ys), wave_right, max(ys)))


def _draw_spectrum(
    draw: ImageDraw.ImageDraw,
    *,
    box: Sequence[float],
    spec: _SpectrumSpec,
    style: Any,
    line_width: int,
) -> List[float]:
    left, top, right, bottom = [float(value) for value in box]
    plot_left = left + 50.0
    plot_right = right - 28.0
    baseline = bottom - 34.0
    plot_top = top + 34.0
    plot_height = baseline - plot_top
    stroke = tuple(int(value) for value in style.stroke_rgb)
    spectrum_rgb = tuple(int(value) for value in style.accent_rgb)
    max_bin = 8.0
    used_points: List[Tuple[float, float]] = []
    if spec.kind == "spikes":
        for bin_value, amplitude in zip(spec.bins, spec.amplitudes):
            x = plot_left + ((float(bin_value) / max_bin) * (plot_right - plot_left))
            y = baseline - (float(amplitude) * plot_height * 0.86)
            draw.line((x, baseline, x, y), fill=stroke, width=max(1, int(line_width) + 2))
            draw.line((x, baseline, x, y), fill=spectrum_rgb, width=max(1, int(line_width)))
            draw.ellipse((x - 5.0, y - 5.0, x + 5.0, y + 5.0), fill=spectrum_rgb, outline=stroke, width=1)
            used_points.append((x, y))
    elif spec.kind == "sinc":
        points: List[Tuple[float, float]] = []
        for idx in range(260):
            u = float(idx) / 259.0
            f = u * max_bin
            z = (math.pi * f) / max(0.25, float(spec.lobe_width))
            mag = 1.0 if abs(z) < 1e-6 else abs(math.sin(z) / z)
            x = plot_left + (u * (plot_right - plot_left))
            y = baseline - (mag * plot_height * 0.9)
            points.append((x, y))
        draw.line(points, fill=stroke, width=max(1, int(line_width) + 2), joint="curve")
        draw.line(points, fill=spectrum_rgb, width=max(1, int(line_width)), joint="curve")
        used_points = points
    elif spec.kind == "bell":
        points = []
        for idx in range(220):
            u = float(idx) / 219.0
            mag = math.exp(-((u - 0.36) ** 2) / 0.045)
            x = plot_left + (u * (plot_right - plot_left))
            y = baseline - (mag * plot_height * 0.82)
            points.append((x, y))
        draw.line(points, fill=stroke, width=max(1, int(line_width) + 2), joint="curve")
        draw.line(points, fill=spectrum_rgb, width=max(1, int(line_width)), joint="curve")
        used_points = points
    if not used_points:
        return _bbox((plot_left, baseline, plot_right, baseline))
    xs = [point[0] for point in used_points]
    ys = [point[1] for point in used_points]
    return _bbox((min(xs) - 6.0, min(ys) - 6.0, max(xs) + 6.0, baseline + 6.0))


def _option_box(index: int, render_defaults: Mapping[str, int]) -> Tuple[float, float, float, float]:
    col = int(index) % 3
    row = int(index) // 3
    left = float(render_defaults["options_left_px"]) + float(col) * (
        float(render_defaults["option_width_px"]) + float(render_defaults["option_gap_x_px"])
    )
    top = float(render_defaults["options_top_px"]) + float(row) * (
        float(render_defaults["option_height_px"]) + float(render_defaults["option_gap_y_px"])
    )
    return (
        left,
        top,
        left + float(render_defaults["option_width_px"]),
        top + float(render_defaults["option_height_px"]),
    )


def _render_scene(
    *,
    image: Image.Image,
    axes: _ResolvedAxes,
    scenario: _SignalScenario,
    render_defaults: Mapping[str, int],
    font_family: str,
    style: Any,
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    canvas_width, canvas_height = image.size
    title_font = load_font(int(render_defaults["title_font_size_px"]), bold=True, font_family=font_family)
    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=True, font_family=font_family)
    axis_font = load_font(int(render_defaults["axis_font_size_px"]), bold=False, font_family=font_family)
    text_rgb = tuple(int(value) for value in style.label_rgb)
    panel_fill = tuple(int(value) for value in style.panel_fill_rgb)
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
        text="Signal spectrum match",
        center=((sheet_box[0] + sheet_box[2]) * 0.5, sheet_box[1] + 34.0),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )

    input_box = (
        float(render_defaults["input_left_px"]),
        float(render_defaults["input_top_px"]),
        float(render_defaults["input_left_px"] + render_defaults["input_width_px"]),
        float(render_defaults["input_top_px"] + render_defaults["input_height_px"]),
    )
    _draw_panel_frame(
        draw,
        box=input_box,
        label="input",
        label_font=label_font,
        axis_font=axis_font,
        style=style,
        scene_variant=str(axes.scene_variant),
    )
    input_wave_bbox = _draw_time_waveform(
        draw,
        box=input_box,
        scenario=scenario,
        style=style,
        line_width=int(render_defaults["waveform_line_width_px"]),
    )

    option_bboxes: Dict[str, List[float]] = {}
    spectrum_bboxes: Dict[str, List[float]] = {}
    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": "input_waveform",
            "entity_type": "time_domain_waveform",
            "bbox_px": _bbox(input_box),
            "meta": {
                "waveform_family": str(scenario.waveform_family),
                "tone_bins": list(scenario.tone_bins),
                "pulse_width": round(float(scenario.pulse_width), 4),
            },
        }
    ]
    for index, label in enumerate(OPTION_LABELS):
        box = _option_box(index, render_defaults)
        _draw_panel_frame(
            draw,
            box=box,
            label=str(label),
            label_font=label_font,
            axis_font=axis_font,
            style=style,
            scene_variant=str(axes.scene_variant),
        )
        spec = scenario.option_specs[str(label)]
        spectrum_bbox = _draw_spectrum(
            draw,
            box=box,
            spec=spec,
            style=style,
            line_width=int(render_defaults["spectrum_line_width_px"]),
        )
        option_bboxes[str(label)] = _bbox(box)
        spectrum_bboxes[str(label)] = list(spectrum_bbox)
        scene_entities.append(
            {
                "entity_id": f"spectrum_{label}",
                "entity_type": "spectrum_option",
                "bbox_px": _bbox(box),
                "meta": {
                    "label": str(label),
                    "is_correct": str(label) == str(axes.correct_option_letter),
                    "spectrum": _spectrum_payload(spec),
                },
            }
        )

    selected_box = option_bboxes[str(axes.correct_option_letter)]
    annotation_bbox_map = {
        "input_waveform": _bbox(input_box),
        "selected_spectrum": list(selected_box),
    }
    render_map = {
        "scene_variant": str(axes.scene_variant),
        "query_id": str(axes.query_id),
        "waveform_family": str(scenario.waveform_family),
        "time_cycles": int(scenario.time_cycles),
        "tone_bins": list(scenario.tone_bins),
        "pulse_width": round(float(scenario.pulse_width), 4),
        "correct_option_letter": str(axes.correct_option_letter),
        "input_panel_bbox_px": _bbox(input_box),
        "input_wave_bbox_px": list(input_wave_bbox),
        "option_bboxes": dict(option_bboxes),
        "spectrum_bboxes": dict(spectrum_bboxes),
        "option_map": {str(label): _spectrum_payload(spec) for label, spec in scenario.option_specs.items()},
        "correct_spectrum": _spectrum_payload(scenario.correct_spectrum),
    }
    return _RenderedScene(
        image=image,
        annotation_bbox_map={str(key): list(value) for key, value in annotation_bbox_map.items()},
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
    )




class _PhysicsSignalTransformSpectrumMatchTaskBase:
    """Choose the spectrum option that matches the shown time-domain signal."""

    task_id = ""
    domain = "physics"
    scene_id = "waves"
    default_dataset_enabled = True
    forced_query_id = ""

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        forced_query_id = str(getattr(self, "forced_query_id", "") or "")
        if forced_query_id:
            explicit_query_id = params.get("query_id")
            if explicit_query_id is not None and str(explicit_query_id) != forced_query_id:
                raise ValueError(f"{self.task_id} only supports query_id={forced_query_id!r}")
            params["query_id"] = forced_query_id
        axes = _resolve_axes(int(instance_seed), params)
        scenario = _build_scenario(axes, int(instance_seed))

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
                "input_left_px",
                "input_top_px",
                "input_width_px",
                "input_height_px",
                "options_left_px",
                "options_top_px",
                "option_width_px",
                "option_height_px",
                "option_gap_x_px",
                "option_gap_y_px",
                "title_font_size_px",
                "label_font_size_px",
                "axis_font_size_px",
                "waveform_line_width_px",
                "spectrum_line_width_px",
                "grid_line_width_px",
            )
        }
        rendered = _render_scene(
            image=background,
            axes=axes,
            scenario=scenario,
            render_defaults=render_defaults,
            font_family=str(font_family),
            style=diagram_style,
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
        annotation_gt = TypedValue(
            type="keyed_bbox_map",
            value={str(key): list(value) for key, value in rendered.annotation_bbox_map.items()},
        )
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
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"physics_signal_transform_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "waveform_family": str(scenario.waveform_family),
                    "correct_option_letter": str(axes.correct_option_letter),
                    "target_answer": str(axes.correct_option_letter),
                    "correct_spectrum_signature": str(scenario.correct_spectrum.signature),
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
                    "waveform_family": str(scenario.waveform_family),
                    "correct_option_letter": str(axes.correct_option_letter),
                    "target_answer": str(axes.correct_option_letter),
                    "answer_support": list(OPTION_LABELS),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "waveform_family_probabilities": dict(axes.waveform_family_probabilities),
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
                    "scope": "signal_transform",
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
                "waveform_family": str(scenario.waveform_family),
                "time_cycles": int(scenario.time_cycles),
                "tone_bins": list(scenario.tone_bins),
                "pulse_width": round(float(scenario.pulse_width), 4),
                "correct_option_letter": str(axes.correct_option_letter),
                "target_answer": str(axes.correct_option_letter),
                "answer_type": "option_letter",
                "answer_option_labels": list(OPTION_LABELS),
                "correct_spectrum": _spectrum_payload(scenario.correct_spectrum),
                "option_map": {str(label): _spectrum_payload(spec) for label, spec in scenario.option_specs.items()},
                "annotation_entity_ids": ["input_waveform", f"spectrum_{str(axes.correct_option_letter)}"],
            },
            "witness_symbolic": {
                "type": "object_map",
                "ids": ["input_waveform", f"spectrum_{str(axes.correct_option_letter)}"],
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_gt.value),
                "pixel_keyed_bbox_map": dict(annotation_gt.value),
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


@register_task
class PhysicsSignalTransformSinusoidComponentSpectrumMatchLabelTask(_PhysicsSignalTransformSpectrumMatchTaskBase):
    """Choose the spectrum option matching sinusoid frequency components."""

    task_id = SINUSOID_TASK_ID
    forced_query_id = "sinusoid_component_spectrum"


@register_task
class PhysicsSignalTransformPeriodicHarmonicSpectrumMatchLabelTask(_PhysicsSignalTransformSpectrumMatchTaskBase):
    """Choose the spectrum option matching periodic-wave harmonic support and decay."""

    task_id = PERIODIC_TASK_ID
    forced_query_id = "periodic_wave_harmonic_spectrum"


@register_task
class PhysicsSignalTransformPulseWidthSpectrumMatchLabelTask(_PhysicsSignalTransformSpectrumMatchTaskBase):
    """Choose the spectrum option matching the pulse-width frequency lobe."""

    task_id = PULSE_TASK_ID
    forced_query_id = "pulse_width_spectrum"


__all__ = [
    "PhysicsSignalTransformPeriodicHarmonicSpectrumMatchLabelTask",
    "PhysicsSignalTransformPulseWidthSpectrumMatchLabelTask",
    "PhysicsSignalTransformSinusoidComponentSpectrumMatchLabelTask",
]
