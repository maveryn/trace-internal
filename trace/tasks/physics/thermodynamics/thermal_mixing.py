"""Physics thermodynamics task for equal-amount thermal mixing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_many
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_render_int
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "task_physics__thermal_mixing__final_temperature_value"
TASK_NAMESPACE = "physics_thermodynamics_thermal_mixing"
SCENE_ID = "thermal_mixing"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("equal_amount_final_temperature",)
CUP_COUNTS: Tuple[str, ...] = ("2", "3", "4")

POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="thermodynamics", apply_prob=0.5)
_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "thermodynamics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_NAMESPACE,
)


@dataclass(frozen=True)
class _TaskDefaults:
    canvas_width: int = 1180
    canvas_height: int = 760
    panel_left_px: int = 58
    panel_top_px: int = 52
    panel_right_margin_px: int = 58
    panel_bottom_margin_px: int = 56
    cup_width_px: int = 138
    cup_height_px: int = 170
    cup_top_px: int = 176
    cup_gap_px: int = 42
    mixer_width_px: int = 330
    mixer_height_px: int = 172
    mixer_top_px: int = 486
    title_font_size_px: int = 27
    label_font_size_px: int = 24
    temp_font_size_px: int = 25
    note_font_size_px: int = 20
    label_stroke_width_px: int = 2


@dataclass(frozen=True)
class _ThermalMixingScenario:
    query_id: str
    cup_count: int
    initial_temperatures_c: Tuple[int, ...]
    final_temperature_c: int
    query_id_probabilities: Dict[str, float]
    cup_count_probabilities: Dict[str, float]
    final_temperature_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_bboxes: List[List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_OFFSET_PATTERNS: Dict[int, Tuple[Tuple[int, ...], ...]] = {
    2: ((-30, 30), (-25, 25), (-20, 20), (-15, 15), (-10, 10)),
    3: ((-30, 0, 30), (-25, -5, 30), (-20, 0, 20), (-15, -5, 20), (-10, -10, 20)),
    4: ((-30, -10, 15, 25), (-25, -15, 15, 25), (-20, -10, 10, 20), (-15, -15, 10, 20), (-30, 0, 10, 20)),
}
_LIQUID_COLORS: Tuple[Tuple[int, int, int], ...] = (
    (93, 159, 224),
    (86, 180, 170),
    (218, 144, 86),
    (160, 141, 219),
    (97, 169, 113),
)


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, center: Tuple[float, float], font: Any, padding: float = 7.0) -> List[float]:
    raw = draw.textbbox((0, 0), str(text), font=font, stroke_width=0)
    width = float(raw[2] - raw[0])
    height = float(raw[3] - raw[1])
    return _bbox(
        (
            float(center[0]) - width / 2.0 - float(padding),
            float(center[1]) - height / 2.0 - float(padding),
            float(center[0]) + width / 2.0 + float(padding),
            float(center[1]) + height / 2.0 + float(padding),
        )
    )


def _draw_text_centered_traced(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font: Any,
    fill: Tuple[int, int, int],
    stroke_width: int = 0,
    required: bool = True,
) -> List[float]:
    bbox = _text_bbox(draw, str(text), center, font, padding=max(5.0, float(stroke_width) + 4.0))
    draw_text_traced(
        draw,
        (float(center[0]), float(center[1])),
        str(text),
        font=font,
        fill=fill,
        anchor="mm",
        stroke_width=int(stroke_width),
        stroke_fill=resolve_text_stroke_fill(fill),
        role="readout" if bool(required) else "decorative_label",
        required=bool(required),
    )
    return bbox


def _resolve_query_id(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.query_id"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_QUERY_IDS,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{TASK_NAMESPACE}.query_id",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_cup_count(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.cup_count"),
        params={**dict(params), "cup_count": str(params["cup_count"]) if params.get("cup_count") is not None else None},
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=CUP_COUNTS,
        explicit_key="cup_count",
        weights_key="cup_count_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=CUP_COUNTS,
        balance_flag_key="balanced_cup_count_sampling",
        explicit_key="cup_count",
        weights_key="cup_count_weights",
        sampling_namespace=f"{TASK_NAMESPACE}.cup_count",
    )
    return int(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_final_temperature(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    support = [
        int(value)
        for value in params.get(
            "final_temperature_support",
            group_default(_GEN_DEFAULTS, "final_temperature_support", [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70]),
        )
    ]
    if not support:
        raise ValueError("final_temperature_support must not be empty")
    explicit = params.get("target_answer", params.get("final_temperature_c"))
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"unsupported final_temperature_c for {TASK_ID}: {selected}")
        return selected, {str(value): (1.0 if int(value) == selected else 0.0) for value in support}
    if bool(params.get("balanced_target_answer_sampling", group_default(_GEN_DEFAULTS, "balanced_target_answer_sampling", True))):
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_NAMESPACE}.final_temperature",
        )
        selected = support[abs(int(index)) % len(support)]
    else:
        selected = int(spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.final_temperature").choice(support))
    probability = 1.0 / float(len(support))
    return int(selected), {str(value): float(probability) for value in support}


def _make_scenario(instance_seed: int, *, params: Mapping[str, Any]) -> _ThermalMixingScenario:
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.scenario")
    query_id, query_probs = _resolve_query_id(int(instance_seed), params=params)
    cup_count, cup_probs = _resolve_cup_count(int(instance_seed), params=params)
    final_temperature, final_probs = _resolve_final_temperature(int(instance_seed), params=params)
    patterns = list(_OFFSET_PATTERNS[int(cup_count)])
    rng.shuffle(patterns)
    selected_offsets: Tuple[int, ...] | None = None
    for offsets in patterns:
        temperatures = [int(final_temperature) + int(offset) for offset in offsets]
        if all(0 <= temp <= 100 for temp in temperatures):
            selected_offsets = tuple(int(offset) for offset in offsets)
            break
    if selected_offsets is None:
        raise ValueError(f"could not find bounded temperature offsets for final temperature {final_temperature}")
    temperatures = [int(final_temperature) + int(offset) for offset in selected_offsets]
    rng.shuffle(temperatures)
    if sum(temperatures) % len(temperatures) != 0:
        raise AssertionError("thermal mixing construction must produce an integer average")
    computed_final = int(sum(temperatures) // len(temperatures))
    if computed_final != int(final_temperature):
        raise AssertionError("thermal mixing construction drifted from target final temperature")
    return _ThermalMixingScenario(
        query_id=str(query_id),
        cup_count=int(cup_count),
        initial_temperatures_c=tuple(int(temp) for temp in temperatures),
        final_temperature_c=int(final_temperature),
        query_id_probabilities=dict(query_probs),
        cup_count_probabilities=dict(cup_probs),
        final_temperature_probabilities=dict(final_probs),
    )


def _resolve_render_defaults(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, int]:
    keys = (
        "panel_left_px",
        "panel_top_px",
        "panel_right_margin_px",
        "panel_bottom_margin_px",
        "cup_width_px",
        "cup_height_px",
        "cup_top_px",
        "cup_gap_px",
        "mixer_width_px",
        "mixer_height_px",
        "mixer_top_px",
        "title_font_size_px",
        "label_font_size_px",
        "temp_font_size_px",
        "note_font_size_px",
        "label_stroke_width_px",
    )
    return {
        str(key): resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            str(key),
            int(getattr(_DEFAULTS, str(key))),
            instance_seed=int(instance_seed),
            namespace=TASK_NAMESPACE,
        )
        for key in keys
    }


def _draw_cup(
    *,
    draw: ImageDraw.ImageDraw,
    center_x: float,
    top_y: float,
    cup_width: float,
    cup_height: float,
    label: str,
    temperature_c: int,
    liquid_rgb: Tuple[int, int, int],
    style: Any,
    font_family: str,
    render_defaults: Mapping[str, Any],
) -> Tuple[List[float], Dict[str, Any]]:
    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=True, font_family=font_family)
    temp_font = load_font(int(render_defaults["temp_font_size_px"]), bold=True, font_family=font_family)
    note_font = load_font(int(render_defaults["note_font_size_px"]), bold=True, font_family=font_family)
    stroke_rgb = tuple(int(v) for v in style.stroke_rgb)
    label_rgb = tuple(int(v) for v in style.label_rgb)
    text_rgb = tuple(int(v) for v in style.label_rgb)

    x0 = float(center_x - cup_width / 2.0)
    x1 = float(center_x + cup_width / 2.0)
    y0 = float(top_y)
    y1 = float(top_y + cup_height)
    rim_y = y0 + 8.0
    cup_poly = [
        (x0 + 10.0, y0),
        (x1 - 10.0, y0),
        (x1 - 24.0, y1),
        (x0 + 24.0, y1),
    ]
    draw.rounded_rectangle([x0 + 6.0, y0 - 14.0, x1 - 6.0, y0 + 12.0], radius=12, fill=tuple(style.panel_fill_rgb), outline=stroke_rgb, width=3)
    draw.polygon(cup_poly, fill=tuple(style.panel_alt_fill_rgb), outline=stroke_rgb)
    draw.line([(x0 + 10.0, y0), (x0 + 24.0, y1), (x1 - 24.0, y1), (x1 - 10.0, y0)], fill=stroke_rgb, width=3)
    liquid_top = y0 + cup_height * 0.46
    liquid_poly = [
        (x0 + 17.0, liquid_top),
        (x1 - 17.0, liquid_top),
        (x1 - 24.0, y1 - 7.0),
        (x0 + 24.0, y1 - 7.0),
    ]
    draw.polygon(liquid_poly, fill=tuple(int(v) for v in liquid_rgb), outline=tuple(int(max(0, v - 45)) for v in liquid_rgb))
    draw.line([(x0 + 18.0, liquid_top), (x1 - 18.0, liquid_top)], fill=tuple(min(255, int(v) + 35) for v in liquid_rgb), width=3)
    draw.arc([x0 + 7.0, y0 - 15.0, x1 - 7.0, y0 + 13.0], start=0, end=180, fill=stroke_rgb, width=3)
    draw.arc([x0 + 7.0, rim_y - 14.0, x1 - 7.0, rim_y + 14.0], start=0, end=180, fill=tuple(int(v) for v in style.guide_rgb), width=2)

    label_bbox = _text_bbox(draw, str(label), (center_x, y0 - 36.0), label_font, padding=8.0)
    draw.rounded_rectangle(label_bbox, radius=8, fill=tuple(style.label_fill_rgb), outline=tuple(style.label_border_rgb), width=2)
    _draw_text_centered_traced(
        draw,
        text=str(label),
        center=(center_x, y0 - 36.0),
        font=label_font,
        fill=label_rgb,
        stroke_width=int(render_defaults["label_stroke_width_px"]),
        required=False,
    )
    temp_text = f"{int(temperature_c)} C"
    temp_bbox = _text_bbox(draw, temp_text, (center_x, y0 + cup_height * 0.35), temp_font, padding=9.0)
    draw.rounded_rectangle(temp_bbox, radius=10, fill=tuple(style.label_fill_rgb), outline=tuple(style.label_border_rgb), width=2)
    _draw_text_centered_traced(
        draw,
        text=temp_text,
        center=(center_x, y0 + cup_height * 0.35),
        font=temp_font,
        fill=text_rgb,
        stroke_width=1,
        required=True,
    )
    amount_bbox = _text_bbox(draw, "equal amount", (center_x, y1 + 24.0), note_font, padding=6.0)
    _draw_text_centered_traced(
        draw,
        text="equal amount",
        center=(center_x, y1 + 24.0),
        font=note_font,
        fill=label_rgb,
        stroke_width=0,
        required=False,
    )
    cup_bbox = _bbox((x0 + 5.0, y0 - 14.0, x1 - 5.0, y1 + 3.0))
    annotation_bbox = bbox_union_many(cup_bbox, temp_bbox, padding=4.0)
    entity = {
        "entity_id": f"initial_cup_{label.lower()}",
        "entity_type": "initial_liquid_cup",
        "bbox_px": list(annotation_bbox),
        "meta": {
            "label": str(label),
            "temperature_c": int(temperature_c),
            "amount": "equal",
            "liquid": "same",
        },
    }
    return list(annotation_bbox), entity


def _draw_arrow(draw: ImageDraw.ImageDraw, *, start: Tuple[float, float], end: Tuple[float, float], fill: Tuple[int, int, int], width: int = 5) -> None:
    draw.line([start, end], fill=fill, width=int(width))
    dx = float(end[0] - start[0])
    dy = float(end[1] - start[1])
    length = max(1.0, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    head = 18.0
    wing = 10.0
    points = [
        (float(end[0]), float(end[1])),
        (float(end[0]) - ux * head + px * wing, float(end[1]) - uy * head + py * wing),
        (float(end[0]) - ux * head - px * wing, float(end[1]) - uy * head - py * wing),
    ]
    draw.polygon(points, fill=fill)


def _render_scene(
    *,
    image: Image.Image,
    scenario: _ThermalMixingScenario,
    render_defaults: Mapping[str, Any],
    font_family: str,
    style: Any,
    instance_seed: int,
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    panel_left = float(render_defaults["panel_left_px"])
    panel_top = float(render_defaults["panel_top_px"])
    panel_right = float(width - int(render_defaults["panel_right_margin_px"]))
    panel_bottom = float(height - int(render_defaults["panel_bottom_margin_px"]))
    panel_bbox = [panel_left, panel_top, panel_right, panel_bottom]
    draw.rounded_rectangle(
        panel_bbox,
        radius=22,
        fill=tuple(style.panel_fill_rgb),
        outline=tuple(style.panel_border_rgb),
        width=3,
    )

    title_font = load_font(int(render_defaults["title_font_size_px"]), bold=True, font_family=font_family)
    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=True, font_family=font_family)
    label_rgb = tuple(int(v) for v in style.label_rgb)
    _draw_text_centered_traced(
        draw,
        text="thermal mixing in an insulated container",
        center=((panel_left + panel_right) / 2.0, panel_top + 32.0),
        font=title_font,
        fill=label_rgb,
        stroke_width=1,
        required=False,
    )

    cup_count = int(scenario.cup_count)
    cup_width = float(render_defaults["cup_width_px"])
    cup_height = float(render_defaults["cup_height_px"])
    cup_gap = float(render_defaults["cup_gap_px"])
    total_width = cup_count * cup_width + max(0, cup_count - 1) * cup_gap
    start_x = float((panel_left + panel_right) / 2.0 - total_width / 2.0 + cup_width / 2.0)
    cup_top = float(render_defaults["cup_top_px"])
    liquid_rgb = _LIQUID_COLORS[abs(int(instance_seed)) % len(_LIQUID_COLORS)]
    annotation_bboxes: List[List[float]] = []
    entities: List[Dict[str, Any]] = []
    cup_centers: List[Tuple[float, float]] = []
    for index, temperature in enumerate(scenario.initial_temperatures_c):
        center_x = start_x + index * (cup_width + cup_gap)
        annotation_bbox, entity = _draw_cup(
            draw=draw,
            center_x=float(center_x),
            top_y=cup_top,
            cup_width=cup_width,
            cup_height=cup_height,
            label=chr(ord("A") + index),
            temperature_c=int(temperature),
            liquid_rgb=tuple(int(v) for v in liquid_rgb),
            style=style,
            font_family=str(font_family),
            render_defaults=render_defaults,
        )
        annotation_bboxes.append(list(annotation_bbox))
        entities.append(dict(entity))
        cup_centers.append((float(center_x), cup_top + cup_height + 48.0))

    mixer_width = float(render_defaults["mixer_width_px"])
    mixer_height = float(render_defaults["mixer_height_px"])
    mixer_top = float(render_defaults["mixer_top_px"])
    mixer_left = float((panel_left + panel_right) / 2.0 - mixer_width / 2.0)
    mixer_right = float(mixer_left + mixer_width)
    mixer_bottom = float(mixer_top + mixer_height)
    mixer_bbox = [mixer_left, mixer_top, mixer_right, mixer_bottom]
    draw.rounded_rectangle(
        mixer_bbox,
        radius=18,
        fill=tuple(style.panel_alt_fill_rgb),
        outline=tuple(style.stroke_rgb),
        width=4,
    )
    insulation_band = [mixer_left + 16.0, mixer_top + 16.0, mixer_right - 16.0, mixer_bottom - 16.0]
    draw.rounded_rectangle(insulation_band, radius=12, outline=tuple(style.guide_rgb), width=3)
    liquid_top = mixer_top + mixer_height * 0.54
    draw.rounded_rectangle(
        [mixer_left + 26.0, liquid_top, mixer_right - 26.0, mixer_bottom - 22.0],
        radius=14,
        fill=tuple(int(v) for v in liquid_rgb),
        outline=tuple(int(max(0, v - 45)) for v in liquid_rgb),
        width=2,
    )
    _draw_text_centered_traced(
        draw,
        text="insulated mixer",
        center=((mixer_left + mixer_right) / 2.0, mixer_top + 34.0),
        font=label_font,
        fill=label_rgb,
        stroke_width=1,
        required=False,
    )
    unknown_bbox = _text_bbox(draw, "? C", ((mixer_left + mixer_right) / 2.0, mixer_top + 84.0), label_font, padding=10.0)
    draw.rounded_rectangle(unknown_bbox, radius=10, fill=tuple(style.label_fill_rgb), outline=tuple(style.label_border_rgb), width=2)
    _draw_text_centered_traced(
        draw,
        text="? C",
        center=((mixer_left + mixer_right) / 2.0, mixer_top + 84.0),
        font=label_font,
        fill=label_rgb,
        stroke_width=1,
        required=False,
    )
    arrow_rgb = tuple(int(v) for v in style.accent_rgb)
    for center in cup_centers:
        _draw_arrow(
            draw,
            start=(float(center[0]), float(center[1])),
            end=((mixer_left + mixer_right) / 2.0, mixer_top - 10.0),
            fill=arrow_rgb,
            width=4,
        )

    entities.append(
        {
            "entity_id": "insulated_mixer",
            "entity_type": "final_mixing_container",
            "bbox_px": _bbox(mixer_bbox),
            "meta": {
                "final_temperature_c": int(scenario.final_temperature_c),
                "visible_answer": False,
                "system": "closed_insulated",
            },
        }
    )
    render_map = {
        "query_id": str(scenario.query_id),
        "cup_count": int(scenario.cup_count),
        "initial_temperatures_c": [int(value) for value in scenario.initial_temperatures_c],
        "final_temperature_c": int(scenario.final_temperature_c),
        "annotation_bboxes_px": [list(bbox) for bbox in annotation_bboxes],
        "mixer_bbox_px": _bbox(mixer_bbox),
    }
    return _RenderedScene(
        image=image,
        annotation_bboxes=[list(bbox) for bbox in annotation_bboxes],
        scene_entities=[dict(entity) for entity in entities],
        render_map=dict(render_map),
    )


@register_task
class PhysicsThermalMixingFinalTemperatureValueTask:
    """Compute final equilibrium temperature for equal amounts of the same liquid."""

    task_id = TASK_ID
    domain = "physics"
    scene_id = "thermodynamics"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        params = dict(params or {})
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) + attempt_index * 7919
            try:
                scenario = _make_scenario(attempt_seed, params=params)
            except Exception as exc:  # pragma: no cover - surfaced if all attempts fail.
                last_error = exc
                continue

            canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
            canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                instance_seed=attempt_seed,
                params=params,
                scene_id=SCENE_ID,
                canvas_width=int(canvas_width),
                canvas_height=int(canvas_height),
                require_grid=True,
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=attempt_seed,
                namespace=f"{TASK_NAMESPACE}.font",
                params=params,
            )
            font_record = get_font_family_record(str(font_family))
            render_defaults = _resolve_render_defaults(params, instance_seed=attempt_seed)
            rendered = _render_scene(
                image=background,
                scenario=scenario,
                render_defaults=render_defaults,
                font_family=str(font_family),
                style=diagram_style,
                instance_seed=attempt_seed,
            )
            image, post_noise_meta = apply_post_image_noise(
                rendered.image,
                instance_seed=attempt_seed,
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
                    f"answer_hint_{str(scenario.query_id)}",
                    f"annotation_hint_{str(scenario.query_id)}",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            answer_gt = TypedValue(type="integer", value=int(scenario.final_temperature_c))
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
                query_key=str(scenario.query_id),
                slots={
                    "object_description": str(prompt_defaults["object_description"]),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "answer_hint": str(prompt_defaults[f"answer_hint_{str(scenario.query_id)}"]),
                    "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(scenario.query_id)}"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=attempt_seed,
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
            trace_payload = {
                "scene_ir": {
                    "scene_kind": "physics_thermal_mixing_equal_amounts",
                    "entities": [dict(entity) for entity in rendered.scene_entities],
                    "relations": {
                        "query_id": str(scenario.query_id),
                        "cup_count": int(scenario.cup_count),
                        "same_liquid": True,
                        "equal_amounts": True,
                        "closed_insulated_system": True,
                        "final_temperature_c": int(scenario.final_temperature_c),
                    },
                },
                "query_spec": {
                    "query_id": str(scenario.query_id),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "query_id": str(scenario.query_id),
                        "target_answer": int(scenario.final_temperature_c),
                        "cup_count": int(scenario.cup_count),
                    },
                },
                "render_spec": {
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "font": {
                        "font_family": str(font_family),
                        "font_asset_version": font_asset_version(),
                        "font_asset": font_record.to_trace(),
                        "scope": "thermal_mixing_setup",
                    },
                    "technical_diagram_style": dict(diagram_style_meta),
                    "background_style": background_meta,
                    "render_defaults": dict(render_defaults),
                    "post_image_noise": post_noise_meta,
                },
                "render_map": dict(rendered.render_map),
                "execution_trace": {
                    "query_id": str(scenario.query_id),
                    "initial_temperatures_c": [int(value) for value in scenario.initial_temperatures_c],
                    "final_temperature_c": int(scenario.final_temperature_c),
                    "calculation": {
                        "operation": "average",
                        "sum_temperatures_c": int(sum(scenario.initial_temperatures_c)),
                        "cup_count": int(scenario.cup_count),
                    },
                    "annotation_entity_ids": [f"initial_cup_{chr(ord('a') + idx)}" for idx in range(int(scenario.cup_count))],
                },
                "sampling": {
                    "query_id_probabilities": dict(scenario.query_id_probabilities),
                    "cup_count_probabilities": dict(scenario.cup_count_probabilities),
                    "final_temperature_probabilities": dict(scenario.final_temperature_probabilities),
                },
                "witness_symbolic": {
                    "type": "bbox_set",
                    "count": len(annotation_gt.value),
                },
                "projected_annotation": {
                    "type": "bbox_set",
                    "bboxes": [list(bbox) for bbox in annotation_gt.value],
                    "pixel_bboxes": [list(bbox) for bbox in annotation_gt.value],
                },
                "background": background_meta,
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
                query_id=str(scenario.query_id),
            )
        raise RuntimeError(f"failed to generate thermal-mixing instance after {max_attempts} attempts: {last_error}")
