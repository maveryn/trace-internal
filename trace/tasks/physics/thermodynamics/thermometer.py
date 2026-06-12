"""Physics thermodynamics task for thermometer temperature conversion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
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
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "task_physics__thermometer__temperature_conversion_value"
TASK_NAMESPACE = "physics_thermodynamics_thermometer"
SCENE_ID = "thermometer"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("celsius_to_fahrenheit_value", "fahrenheit_to_celsius_value")

POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="thermodynamics", apply_prob=0.5)
_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "thermodynamics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_NAMESPACE,
)


@dataclass(frozen=True)
class _ThermometerProfile:
    """One visible thermometer scale profile."""

    profile_id: str
    query_id: str
    source_unit: str
    target_unit: str
    scale_min: int
    scale_max: int
    major_step: int
    minor_step: int
    source_support: Tuple[int, ...]


@dataclass(frozen=True)
class _ThermometerScenario:
    """Resolved thermometer conversion scenario."""

    query_id: str
    profile: _ThermometerProfile
    source_temperature: int
    target_temperature: int
    query_id_probabilities: Dict[str, float]
    scale_profile_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _ThermometerGeometry:
    """Pixel geometry for one vertical thermometer."""

    center_x: float
    scale_top: float
    scale_bottom: float
    tube_width: float
    bulb_radius: float
    scale_left: bool


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered thermometer and prompt-facing annotation metadata."""

    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for thermometer conversion scenes."""

    canvas_width: int = 1100
    canvas_height: int = 720
    panel_left_px: int = 58
    panel_top_px: int = 52
    panel_right_margin_px: int = 58
    panel_bottom_margin_px: int = 56
    thermometer_center_x_px: int = 550
    thermometer_scale_top_px: int = 120
    thermometer_scale_bottom_px: int = 562
    tube_width_px: int = 46
    bulb_radius_px: int = 58
    title_font_size_px: int = 28
    tick_font_size_px: int = 22
    unit_font_size_px: int = 34


_DEFAULTS = _TaskDefaults()
_PROFILES: Dict[str, _ThermometerProfile] = {
    "celsius_weather": _ThermometerProfile(
        profile_id="celsius_weather",
        query_id="celsius_to_fahrenheit_value",
        source_unit="C",
        target_unit="F",
        scale_min=-20,
        scale_max=50,
        major_step=10,
        minor_step=5,
        source_support=tuple(range(-15, 50, 5)),
    ),
    "celsius_lab": _ThermometerProfile(
        profile_id="celsius_lab",
        query_id="celsius_to_fahrenheit_value",
        source_unit="C",
        target_unit="F",
        scale_min=0,
        scale_max=100,
        major_step=20,
        minor_step=5,
        source_support=tuple(range(5, 100, 5)),
    ),
    "fahrenheit_weather": _ThermometerProfile(
        profile_id="fahrenheit_weather",
        query_id="fahrenheit_to_celsius_value",
        source_unit="F",
        target_unit="C",
        scale_min=20,
        scale_max=120,
        major_step=20,
        minor_step=2,
        source_support=(32, 50, 68, 86, 104),
    ),
    "fahrenheit_compact": _ThermometerProfile(
        profile_id="fahrenheit_compact",
        query_id="fahrenheit_to_celsius_value",
        source_unit="F",
        target_unit="C",
        scale_min=30,
        scale_max=110,
        major_step=10,
        minor_step=2,
        source_support=(32, 50, 68, 86, 104),
    ),
}
_PROFILE_IDS_BY_QUERY: Dict[str, Tuple[str, ...]] = {
    "celsius_to_fahrenheit_value": ("celsius_weather", "celsius_lab"),
    "fahrenheit_to_celsius_value": ("fahrenheit_weather", "fahrenheit_compact"),
}


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _probability_map(values: Sequence[str], selected: str | None = None) -> Dict[str, float]:
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in values}
    if not values:
        return {}
    probability = 1.0 / float(len(values))
    return {str(value): float(probability) for value in values}


def _bbox_union(boxes: Sequence[Sequence[float]]) -> List[float]:
    if not boxes:
        raise ValueError("cannot union an empty bbox sequence")
    return _bbox(
        (
            min(float(box[0]) for box in boxes),
            min(float(box[1]) for box in boxes),
            max(float(box[2]) for box in boxes),
            max(float(box[3]) for box in boxes),
        )
    )


def _draw_label(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    fill: Tuple[int, int, int],
    *,
    anchor: str | None = None,
) -> List[float]:
    kwargs: Dict[str, Any] = {}
    if anchor is not None:
        kwargs["anchor"] = str(anchor)
    record = draw_text_traced(
        draw,
        (float(xy[0]), float(xy[1])),
        str(text),
        font=font,
        fill=fill,
        stroke_width=0,
        stroke_fill=resolve_text_stroke_fill(fill),
        role="readout",
        required=True,
        **kwargs,
    )
    bbox = tuple(float(value) for value in record["bbox_px"])
    return _bbox((bbox[0], bbox[1], bbox[2], bbox[3]))


def _convert_temperature(query_id: str, source_temperature: int) -> int:
    source = int(source_temperature)
    if query_id == "celsius_to_fahrenheit_value":
        if source % 5 != 0:
            raise ValueError("Celsius source temperature must be a multiple of 5 for integer Fahrenheit answers")
        return int(source * 9 // 5 + 32)
    if query_id == "fahrenheit_to_celsius_value":
        numerator = int(source - 32) * 5
        if numerator % 9 != 0:
            raise ValueError("Fahrenheit source temperature must convert to an integer Celsius answer")
        return int(numerator // 9)
    raise ValueError(f"unsupported query_id for {TASK_ID}: {query_id}")


def _source_from_target(query_id: str, target_temperature: int) -> int:
    target = int(target_temperature)
    if query_id == "celsius_to_fahrenheit_value":
        numerator = int(target - 32) * 5
        if numerator % 9 != 0:
            raise ValueError("target Fahrenheit answer does not map to an integer Celsius source")
        return int(numerator // 9)
    if query_id == "fahrenheit_to_celsius_value":
        if target % 5 != 0:
            raise ValueError("target Celsius answer must be a multiple of 5 for supported Fahrenheit sources")
        return int(target * 9 // 5 + 32)
    raise ValueError(f"unsupported query_id for {TASK_ID}: {query_id}")


def _resolve_query_id(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = str(params.get("query_id") or "").strip()
    if explicit:
        if explicit not in SUPPORTED_QUERY_IDS:
            raise ValueError(f"unsupported query_id for {TASK_ID}: {explicit}")
        return explicit, _probability_map(SUPPORTED_QUERY_IDS, selected=explicit)
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.query_id")
    selected, probabilities = resolve_variant(
        rng,
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


def _resolve_profile(instance_seed: int, params: Mapping[str, Any], query_id: str) -> Tuple[_ThermometerProfile, Dict[str, float]]:
    supported = _PROFILE_IDS_BY_QUERY[str(query_id)]
    explicit = str(params.get("scale_profile") or params.get("thermometer_profile") or "").strip()
    if explicit:
        if explicit not in supported:
            raise ValueError(f"unsupported scale_profile for {query_id}: {explicit}")
        return _PROFILES[explicit], _probability_map(supported, selected=explicit)
    balanced = bool(params.get("balanced_scale_profile_sampling", group_default(_GEN_DEFAULTS, "balanced_scale_profile_sampling", True)))
    if balanced:
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_NAMESPACE}.scale_profile.{query_id}",
        )
        selected = supported[int(index) % len(supported)]
    else:
        rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.scale_profile.{query_id}")
        weights = group_default(_GEN_DEFAULTS, "scale_profile_weights", {})
        weighted = [max(0.0, float(weights.get(profile_id, 1.0))) for profile_id in supported]
        total = sum(weighted) or float(len(supported))
        threshold = rng.random() * total
        cumulative = 0.0
        selected = supported[-1]
        for profile_id, weight in zip(supported, weighted):
            cumulative += weight if total != float(len(supported)) else 1.0
            if threshold <= cumulative:
                selected = profile_id
                break
    return _PROFILES[str(selected)], _probability_map(supported, selected=str(selected))


def _resolve_source_temperature(
    instance_seed: int,
    params: Mapping[str, Any],
    *,
    query_id: str,
    profile: _ThermometerProfile,
) -> Tuple[int, int, Dict[str, float]]:
    support = tuple(int(value) for value in profile.source_support)
    target_support = tuple(_convert_temperature(str(query_id), value) for value in support)
    explicit_source_raw = params.get("source_temperature", params.get("source_value"))
    explicit_target_raw = params.get("target_answer")
    if explicit_source_raw is not None:
        source = int(explicit_source_raw)
        if source not in support:
            raise ValueError(f"unsupported source_temperature for {profile.profile_id}: {source}")
        target = _convert_temperature(str(query_id), source)
        return source, target, _probability_map([str(value) for value in target_support], selected=str(target))
    if explicit_target_raw is not None:
        target = int(explicit_target_raw)
        source = _source_from_target(str(query_id), target)
        if source not in support:
            raise ValueError(f"unsupported target_answer for {profile.profile_id}: {target}")
        return source, target, _probability_map([str(value) for value in target_support], selected=str(target))

    balanced = bool(params.get("balanced_target_answer_sampling", group_default(_GEN_DEFAULTS, "balanced_target_answer_sampling", True)))
    if balanced:
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_NAMESPACE}.target_answer.{profile.profile_id}",
        )
        source = support[int(index) % len(support)]
    else:
        source = support[int(hash64(int(instance_seed), f"{TASK_NAMESPACE}.source_temperature.{profile.profile_id}", 0) % len(support))]
    target = _convert_temperature(str(query_id), source)
    return int(source), int(target), _probability_map([str(value) for value in target_support], selected=str(target))


def _resolve_scenario(instance_seed: int, params: Mapping[str, Any]) -> _ThermometerScenario:
    query_id, query_probabilities = _resolve_query_id(int(instance_seed), params)
    profile, profile_probabilities = _resolve_profile(int(instance_seed), params, str(query_id))
    source_temperature, target_temperature, target_probabilities = _resolve_source_temperature(
        int(instance_seed),
        params,
        query_id=str(query_id),
        profile=profile,
    )
    return _ThermometerScenario(
        query_id=str(query_id),
        profile=profile,
        source_temperature=int(source_temperature),
        target_temperature=int(target_temperature),
        query_id_probabilities=dict(query_probabilities),
        scale_profile_probabilities=dict(profile_probabilities),
        target_answer_probabilities=dict(target_probabilities),
    )


def _temperature_to_y(geometry: _ThermometerGeometry, profile: _ThermometerProfile, temperature: int) -> float:
    frac = (float(temperature) - float(profile.scale_min)) / float(profile.scale_max - profile.scale_min)
    frac = max(0.0, min(1.0, frac))
    return float(geometry.scale_bottom - frac * (geometry.scale_bottom - geometry.scale_top))


def _draw_thermometer(
    draw: ImageDraw.ImageDraw,
    *,
    geometry: _ThermometerGeometry,
    scenario: _ThermometerScenario,
    font_family: str,
    style: Any,
    liquid_rgb: Tuple[int, int, int],
) -> Dict[str, Any]:
    profile = scenario.profile
    tick_font = load_font(int(_RENDER_DEFAULTS.get("tick_font_size_px", _DEFAULTS.tick_font_size_px)), bold=True, font_family=font_family)
    unit_font = load_font(int(_RENDER_DEFAULTS.get("unit_font_size_px", _DEFAULTS.unit_font_size_px)), bold=True, font_family=font_family)
    title_font = load_font(int(_RENDER_DEFAULTS.get("title_font_size_px", _DEFAULTS.title_font_size_px)), bold=True, font_family=font_family)
    outline = tuple(int(value) for value in style.stroke_rgb)
    guide = tuple(int(value) for value in style.guide_rgb)
    text_rgb = (14, 20, 32)
    glass_fill = (239, 248, 252)
    tube_left = float(geometry.center_x - geometry.tube_width * 0.5)
    tube_right = float(geometry.center_x + geometry.tube_width * 0.5)
    tube_top = float(geometry.scale_top - 8)
    tube_bottom = float(geometry.scale_bottom + 20)
    bulb_cy = float(geometry.scale_bottom + geometry.bulb_radius * 0.66)
    bulb_bbox = (
        float(geometry.center_x - geometry.bulb_radius),
        float(bulb_cy - geometry.bulb_radius),
        float(geometry.center_x + geometry.bulb_radius),
        float(bulb_cy + geometry.bulb_radius),
    )

    draw.rounded_rectangle((tube_left, tube_top, tube_right, tube_bottom), radius=22, fill=glass_fill, outline=outline, width=4)
    draw.ellipse(bulb_bbox, fill=glass_fill, outline=outline, width=4)

    level_y = _temperature_to_y(geometry, profile, int(scenario.source_temperature))
    liquid_left = float(tube_left + 9)
    liquid_right = float(tube_right - 9)
    draw.rounded_rectangle(
        (liquid_left, float(level_y), liquid_right, float(tube_bottom + 3)),
        radius=10,
        fill=tuple(int(value) for value in liquid_rgb),
    )
    draw.ellipse(
        (
            float(geometry.center_x - geometry.bulb_radius + 12),
            float(bulb_cy - geometry.bulb_radius + 12),
            float(geometry.center_x + geometry.bulb_radius - 12),
            float(bulb_cy + geometry.bulb_radius - 12),
        ),
        fill=tuple(int(value) for value in liquid_rgb),
        outline=tuple(max(0, int(value) - 45) for value in liquid_rgb),
        width=3,
    )
    draw.line((liquid_left, level_y, liquid_right, level_y), fill=tuple(max(0, int(value) - 55) for value in liquid_rgb), width=4)

    scale_x = float(geometry.center_x - 96 if geometry.scale_left else geometry.center_x + 96)
    tick_dir = 1 if geometry.scale_left else -1
    label_anchor = "rm" if geometry.scale_left else "lm"
    label_x = float(scale_x - 12 if geometry.scale_left else scale_x + 12)
    tick_bboxes: List[List[float]] = []
    label_bboxes: List[List[float]] = []
    for tick_value in range(int(profile.scale_min), int(profile.scale_max) + 1, int(profile.minor_step)):
        y = _temperature_to_y(geometry, profile, int(tick_value))
        is_major = (tick_value - int(profile.scale_min)) % int(profile.major_step) == 0
        tick_len = 28 if is_major else 14
        x1 = float(scale_x)
        x2 = float(scale_x + tick_dir * tick_len)
        draw.line((x1, y, x2, y), fill=outline if is_major else guide, width=3 if is_major else 1)
        tick_bboxes.append(_bbox((min(x1, x2), y - 2, max(x1, x2), y + 2)))
        if is_major:
            label_bboxes.append(_draw_label(draw, (label_x, y), str(tick_value), tick_font, text_rgb, anchor=label_anchor))

    unit_y = float(geometry.scale_top - 42)
    unit_bbox = _draw_label(draw, (scale_x, unit_y), str(profile.source_unit), unit_font, text_rgb, anchor="mm")
    title_center_x = float(geometry.center_x)
    draw_centered_text(
        draw,
        text="Thermometer",
        center=(title_center_x, float(geometry.scale_top - 78)),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )
    scale_region = _bbox_union([*tick_bboxes, *label_bboxes, unit_bbox])
    liquid_level = _bbox((liquid_left - 5, float(level_y - 10), liquid_right + 5, float(level_y + 10)))
    return {
        "liquid_level": liquid_level,
        "scale_region": scale_region,
        "source_unit_label": unit_bbox,
        "thermometer_body": _bbox((min(tube_left, bulb_bbox[0]), tube_top, max(tube_right, bulb_bbox[2]), bulb_bbox[3])),
        "level_y_px": round(float(level_y), 3),
    }


def _render_thermometer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scenario: _ThermometerScenario,
) -> _RenderedScene:
    canvas_width = int(_RENDER_DEFAULTS.get("canvas_width", _DEFAULTS.canvas_width))
    canvas_height = int(_RENDER_DEFAULTS.get("canvas_height", _DEFAULTS.canvas_height))
    background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        require_grid=True,
    )
    draw = ImageDraw.Draw(background)
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.layout")
    panel_left = int(_RENDER_DEFAULTS.get("panel_left_px", _DEFAULTS.panel_left_px))
    panel_top = int(_RENDER_DEFAULTS.get("panel_top_px", _DEFAULTS.panel_top_px))
    panel_right = int(canvas_width - int(_RENDER_DEFAULTS.get("panel_right_margin_px", _DEFAULTS.panel_right_margin_px)))
    panel_bottom = int(canvas_height - int(_RENDER_DEFAULTS.get("panel_bottom_margin_px", _DEFAULTS.panel_bottom_margin_px)))
    draw.rounded_rectangle(
        (panel_left, panel_top, panel_right, panel_bottom),
        radius=18,
        fill=tuple(int(value) for value in diagram_style.panel_fill_rgb),
        outline=tuple(int(value) for value in diagram_style.panel_border_rgb),
        width=3,
    )

    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_NAMESPACE}.font",
        params=params,
    )
    font_record = get_font_family_record(str(font_family))
    palette = ((218, 64, 80), (224, 92, 48), (198, 54, 92), (230, 116, 58))
    liquid_rgb = palette[int(hash64(int(instance_seed), f"{TASK_NAMESPACE}.liquid", 0) % len(palette))]
    geometry = _ThermometerGeometry(
        center_x=float(int(_RENDER_DEFAULTS.get("thermometer_center_x_px", _DEFAULTS.thermometer_center_x_px)) + rng.randint(-16, 16)),
        scale_top=float(int(_RENDER_DEFAULTS.get("thermometer_scale_top_px", _DEFAULTS.thermometer_scale_top_px)) + rng.randint(-8, 8)),
        scale_bottom=float(int(_RENDER_DEFAULTS.get("thermometer_scale_bottom_px", _DEFAULTS.thermometer_scale_bottom_px)) + rng.randint(-6, 8)),
        tube_width=float(int(_RENDER_DEFAULTS.get("tube_width_px", _DEFAULTS.tube_width_px))),
        bulb_radius=float(int(_RENDER_DEFAULTS.get("bulb_radius_px", _DEFAULTS.bulb_radius_px))),
        scale_left=bool(hash64(int(instance_seed), f"{TASK_NAMESPACE}.scale_side", 0) % 2),
    )
    rendered = _draw_thermometer(
        draw,
        geometry=geometry,
        scenario=scenario,
        font_family=str(font_family),
        style=diagram_style,
        liquid_rgb=tuple(int(value) for value in liquid_rgb),
    )
    image, post_noise_meta = apply_post_image_noise(
        background,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_map = {
        "liquid_level": list(rendered["liquid_level"]),
        "scale_region": list(rendered["scale_region"]),
        "source_unit_label": list(rendered["source_unit_label"]),
    }
    scene_entities = [
        {
            "id": "liquid_level",
            "bbox_px": list(annotation_map["liquid_level"]),
            "source_temperature": int(scenario.source_temperature),
            "source_unit": str(scenario.profile.source_unit),
        },
        {
            "id": "scale_region",
            "bbox_px": list(annotation_map["scale_region"]),
            "scale_min": int(scenario.profile.scale_min),
            "scale_max": int(scenario.profile.scale_max),
            "source_unit": str(scenario.profile.source_unit),
        },
        {"id": "source_unit_label", "bbox_px": list(annotation_map["source_unit_label"]), "unit": str(scenario.profile.source_unit)},
    ]
    render_map = {
        "thermometer": dict(rendered),
        "source_temperature": int(scenario.source_temperature),
        "source_unit": str(scenario.profile.source_unit),
        "target_temperature": int(scenario.target_temperature),
        "target_unit": str(scenario.profile.target_unit),
        "scale_profile": {
            "profile_id": str(scenario.profile.profile_id),
            "scale_min": int(scenario.profile.scale_min),
            "scale_max": int(scenario.profile.scale_max),
            "major_step": int(scenario.profile.major_step),
            "minor_step": int(scenario.profile.minor_step),
        },
        "font": {
            "font_family": str(font_family),
            "font_asset_version": font_asset_version(),
            "font_asset": font_record.to_trace(),
        },
        "technical_diagram_style": dict(diagram_style_meta),
        "background_style": dict(background_meta),
        "post_image_noise": dict(post_noise_meta),
    }
    return _RenderedScene(
        image=image,
        annotation_bbox_map={str(key): list(value) for key, value in annotation_map.items()},
        scene_entities=scene_entities,
        render_map=render_map,
    )


@register_task
class PhysicsThermometerTemperatureConversionValueTask:
    """Read a thermometer and convert the source temperature to the other unit."""

    domain = "physics"
    scene_id = "thermodynamics"
    task_id = TASK_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        scenario = _resolve_scenario(int(instance_seed), params)
        rendered = _render_thermometer(instance_seed=int(instance_seed), params=params, scenario=scenario)
        query_id = str(scenario.query_id)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                f"answer_hint_{query_id}",
                f"annotation_hint_{query_id}",
            ),
            context=f"prompt defaults for {TASK_ID}",
        )
        answer_gt = TypedValue(type="integer", value=int(scenario.target_temperature))
        annotation_gt = TypedValue(type="keyed_bbox_map", value={str(key): list(value) for key, value in rendered.annotation_bbox_map.items()})
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
            query_key=str(query_id),
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{query_id}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{query_id}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"physics_thermometer_{scenario.profile.profile_id}",
                "entities": list(rendered.scene_entities),
                "relations": {
                    "query_id": str(query_id),
                    "scale_profile": str(scenario.profile.profile_id),
                    "source_temperature": int(scenario.source_temperature),
                    "source_unit": str(scenario.profile.source_unit),
                    "target_temperature": int(scenario.target_temperature),
                    "target_unit": str(scenario.profile.target_unit),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "scale_profile": str(scenario.profile.profile_id),
                    "source_temperature": int(scenario.source_temperature),
                    "source_unit": str(scenario.profile.source_unit),
                    "target_answer": int(scenario.target_temperature),
                    "target_unit": str(scenario.profile.target_unit),
                    "query_id_probabilities": dict(scenario.query_id_probabilities),
                    "scale_profile_probabilities": dict(scenario.scale_profile_probabilities),
                    "target_answer_probabilities": dict(scenario.target_answer_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(rendered.image.size[0]),
                "canvas_height": int(rendered.image.size[1]),
                "font": {
                    "font_family": str(rendered.render_map["font"]["font"]),
                    "font_asset_version": str(rendered.render_map["font"]["font_asset_version"]),
                    "font_asset": dict(rendered.render_map["font"]["font_asset"]),
                    "scope": "thermometer_diagram",
                },
                "technical_diagram_style": dict(rendered.render_map["technical_diagram_style"]),
                "background_style": dict(rendered.render_map["background_style"]),
                "post_image_noise": dict(rendered.render_map["post_image_noise"]),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "query_id": str(query_id),
                "scale_profile": str(scenario.profile.profile_id),
                "source_temperature": int(scenario.source_temperature),
                "source_unit": str(scenario.profile.source_unit),
                "target_temperature": int(scenario.target_temperature),
                "target_unit": str(scenario.profile.target_unit),
                "target_answer": int(scenario.target_temperature),
                "annotation_entity_ids": sorted(annotation_gt.value.keys()),
            },
            "witness_symbolic": {
                "type": "object_map",
                "ids": sorted(annotation_gt.value.keys()),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_gt.value),
                "pixel_keyed_bbox_map": dict(annotation_gt.value),
            },
            "background": dict(rendered.render_map["background_style"]),
            "post_image_noise": dict(rendered.render_map["post_image_noise"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )
