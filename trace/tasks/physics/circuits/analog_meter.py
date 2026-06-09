"""Physics circuits task for analog meter readout diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_many as _bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.drawing import draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "task_physics__analog_meter__meter_readout_value"
FAMILY_ID = "physics_circuits_analog_meter_family"
SCENE_ID = "analog_meter"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("ammeter_readout", "voltmeter_readout")

POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="circuits", apply_prob=0.5)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "circuits")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)


@dataclass(frozen=True)
class _MeterProfile:
    """One analog meter scale profile."""

    profile_id: str
    query_id: str
    meter_name: str
    unit: str
    scale_max: int
    major_step: int
    minor_step: int
    answer_support: Tuple[int, ...]


@dataclass(frozen=True)
class _MeterScenario:
    """Resolved analog meter scenario."""

    query_id: str
    profile: _MeterProfile
    readout_value: int
    query_id_probabilities: Dict[str, float]
    meter_profile_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered analog meter plus prompt-facing annotation metadata."""

    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for analog meter scenes."""

    canvas_width: int = 1120
    canvas_height: int = 720
    panel_left_px: int = 64
    panel_top_px: int = 54
    panel_right_margin_px: int = 64
    panel_bottom_margin_px: int = 56
    meter_center_x_px: int = 560
    meter_center_y_px: int = 472
    scale_radius_px: int = 270
    needle_radius_px: int = 222
    face_radius_px: int = 318
    label_font_size_px: int = 28
    tick_font_size_px: int = 20
    unit_font_size_px: int = 34
    title_font_size_px: int = 24


_DEFAULTS = _TaskDefaults()
_PROFILES: Dict[str, _MeterProfile] = {
    "ammeter_a": _MeterProfile(
        profile_id="ammeter_a",
        query_id="ammeter_readout",
        meter_name="ammeter",
        unit="A",
        scale_max=10,
        major_step=2,
        minor_step=1,
        answer_support=tuple(range(1, 10)),
    ),
    "ammeter_ma": _MeterProfile(
        profile_id="ammeter_ma",
        query_id="ammeter_readout",
        meter_name="ammeter",
        unit="mA",
        scale_max=100,
        major_step=20,
        minor_step=10,
        answer_support=tuple(range(10, 100, 10)),
    ),
    "voltmeter_v": _MeterProfile(
        profile_id="voltmeter_v",
        query_id="voltmeter_readout",
        meter_name="voltmeter",
        unit="V",
        scale_max=12,
        major_step=2,
        minor_step=1,
        answer_support=tuple(range(1, 12)),
    ),
}
_PROFILE_IDS_BY_QUERY: Dict[str, Tuple[str, ...]] = {
    "ammeter_readout": ("ammeter_a", "ammeter_ma"),
    "voltmeter_readout": ("voltmeter_v",),
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


def _support_from_defaults(key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw = group_default(_GEN_DEFAULTS, str(key), tuple(int(value) for value in fallback))
    support: List[int] = []
    for value in raw:
        selected = int(value)
        if selected not in support:
            support.append(selected)
    if not support:
        raise ValueError(f"{key} must contain at least one integer")
    return tuple(sorted(support))


def _resolve_query_id(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = str(params.get("query_id") or "").strip()
    if explicit:
        if explicit not in SUPPORTED_QUERY_IDS:
            raise ValueError(f"unsupported query_id for {TASK_ID}: {explicit}")
        return explicit, _probability_map(SUPPORTED_QUERY_IDS, selected=explicit)
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.query_id")
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
        sampling_namespace=f"{FAMILY_ID}.query_id",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_meter_profile(instance_seed: int, params: Mapping[str, Any], query_id: str) -> Tuple[_MeterProfile, Dict[str, float]]:
    supported = _PROFILE_IDS_BY_QUERY[str(query_id)]
    explicit_profile = str(params.get("meter_profile") or "").strip()
    explicit_unit = str(params.get("unit") or "").strip()
    if explicit_profile:
        if explicit_profile not in supported:
            raise ValueError(f"unsupported meter_profile for {query_id}: {explicit_profile}")
        return _PROFILES[explicit_profile], _probability_map(supported, selected=explicit_profile)
    if explicit_unit:
        matches = [profile_id for profile_id in supported if str(_PROFILES[profile_id].unit) == explicit_unit]
        if not matches:
            raise ValueError(f"unsupported unit for {query_id}: {explicit_unit}")
        return _PROFILES[matches[0]], _probability_map(supported, selected=matches[0])
    if len(supported) == 1:
        return _PROFILES[supported[0]], _probability_map(supported, selected=supported[0])

    weights = group_default(_GEN_DEFAULTS, "meter_profile_weights", {})
    enabled = bool(params.get("balanced_meter_profile_sampling", group_default(_GEN_DEFAULTS, "balanced_meter_profile_sampling", True)))
    if enabled:
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.meter_profile.{query_id}",
        )
        selected = supported[int(index) % len(supported)]
    else:
        weighted: List[str] = []
        for profile_id in supported:
            weight = float(params.get("meter_profile_weights", weights).get(profile_id, 1.0)) if isinstance(params.get("meter_profile_weights", weights), Mapping) else 1.0
            weighted.extend([profile_id] * max(0, int(round(weight))))
        if not weighted:
            weighted = list(supported)
        rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.meter_profile.{query_id}")
        selected = weighted[int(rng.randrange(len(weighted)))]
    return _PROFILES[str(selected)], _probability_map(supported)


def _resolve_readout_value(instance_seed: int, params: Mapping[str, Any], profile: _MeterProfile) -> Tuple[int, Dict[str, float]]:
    support = _support_from_defaults(f"{profile.profile_id}_answer_support", profile.answer_support)
    explicit = params.get("readout_value", params.get("target_answer"))
    if explicit is not None:
        selected = int(explicit)
        if selected not in set(support):
            raise ValueError(f"unsupported readout_value for {profile.profile_id}: {selected}")
        return int(selected), uniform_probability_map(support, selected=int(selected))
    if bool(params.get("balanced_target_answer_sampling", group_default(_GEN_DEFAULTS, "balanced_target_answer_sampling", True))):
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.target_answer.{profile.profile_id}",
        )
        selected = int(support[int(index) % len(support)])
    else:
        rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.target_answer.{profile.profile_id}")
        selected = int(support[int(rng.randrange(len(support)))])
    return int(selected), uniform_probability_map(support)


def _resolve_scenario(instance_seed: int, params: Mapping[str, Any]) -> _MeterScenario:
    query_id, query_probabilities = _resolve_query_id(int(instance_seed), params)
    profile, profile_probabilities = _resolve_meter_profile(int(instance_seed), params, query_id)
    readout_value, answer_probabilities = _resolve_readout_value(int(instance_seed), params, profile)
    return _MeterScenario(
        query_id=str(query_id),
        profile=profile,
        readout_value=int(readout_value),
        query_id_probabilities=query_probabilities,
        meter_profile_probabilities=profile_probabilities,
        target_answer_probabilities=answer_probabilities,
    )


def _angle_for_value(value: float, *, scale_max: int) -> float:
    fraction = max(0.0, min(1.0, float(value) / float(scale_max)))
    return math.radians(210.0 + (120.0 * fraction))


def _point_on_meter(center: Tuple[float, float], radius: float, angle_rad: float) -> Tuple[float, float]:
    return (
        float(center[0] + float(radius) * math.cos(float(angle_rad))),
        float(center[1] + float(radius) * math.sin(float(angle_rad))),
    )


def _draw_meter_face(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    scenario: _MeterScenario,
    style: Any,
    font_family: str,
    accent_rgb: Tuple[int, int, int],
    render_defaults: Mapping[str, Any],
) -> Tuple[Dict[str, List[float]], Dict[str, Any]]:
    profile = scenario.profile
    cx, cy = float(center[0]), float(center[1])
    face_radius = float(render_defaults.get("face_radius_px", _DEFAULTS.face_radius_px))
    scale_radius = float(render_defaults.get("scale_radius_px", _DEFAULTS.scale_radius_px))
    needle_radius = float(render_defaults.get("needle_radius_px", _DEFAULTS.needle_radius_px))
    tick_font = load_font(int(render_defaults.get("tick_font_size_px", _DEFAULTS.tick_font_size_px)), bold=True, font_family=font_family)
    unit_font = load_font(int(render_defaults.get("unit_font_size_px", _DEFAULTS.unit_font_size_px)), bold=True, font_family=font_family)
    title_font = load_font(int(render_defaults.get("title_font_size_px", _DEFAULTS.title_font_size_px)), bold=True, font_family=font_family)
    stroke = tuple(int(v) for v in style.stroke_rgb)
    guide = tuple(int(v) for v in style.guide_rgb)
    label_rgb = tuple(int(v) for v in style.label_rgb)
    casing_fill = tuple(int(v) for v in style.muted_fill_rgb)

    body_bbox = _bbox((cx - face_radius - 38.0, cy - scale_radius - 122.0, cx + face_radius + 38.0, cy + 142.0))
    draw.rounded_rectangle(tuple(body_bbox), radius=34, fill=casing_fill, outline=stroke, width=4)
    face_bbox = _bbox((cx - face_radius, cy - scale_radius - 80.0, cx + face_radius, cy + 120.0))
    draw.rounded_rectangle(
        tuple(face_bbox),
        radius=34,
        fill=tuple(int(v) for v in style.panel_alt_fill_rgb),
        outline=stroke,
        width=4,
    )

    label_bboxes: List[List[float]] = []
    tick_bboxes: List[List[float]] = []
    for value in range(0, int(profile.scale_max) + 1, int(profile.minor_step)):
        angle = _angle_for_value(float(value), scale_max=int(profile.scale_max))
        is_major = int(value) % int(profile.major_step) == 0
        outer = _point_on_meter((cx, cy), scale_radius, angle)
        inner = _point_on_meter((cx, cy), scale_radius - (30.0 if is_major else 18.0), angle)
        draw.line((inner[0], inner[1], outer[0], outer[1]), fill=stroke if is_major else guide, width=4 if is_major else 2)
        tick_bboxes.append(_bbox((min(inner[0], outer[0]) - 3.0, min(inner[1], outer[1]) - 3.0, max(inner[0], outer[0]) + 3.0, max(inner[1], outer[1]) + 3.0)))
        if is_major:
            label_center = _point_on_meter((cx, cy), scale_radius - 62.0, angle)
            label_bbox = draw_centered_text(
                draw,
                text=str(int(value)),
                center=label_center,
                font=tick_font,
                fill=label_rgb,
                stroke_fill=resolve_text_stroke_fill(label_rgb),
                stroke_width=1,
            )
            label_bboxes.append(label_bbox)

    arc_bbox = _bbox((cx - scale_radius, cy - scale_radius, cx + scale_radius, cy + scale_radius))
    arc_visual_bbox = _bbox((cx - scale_radius - 6.0, cy - scale_radius - 6.0, cx + scale_radius + 6.0, cy - (scale_radius * 0.42) + 6.0))
    draw.arc(tuple(arc_bbox), start=210, end=330, fill=stroke, width=5)
    title_bbox = draw_centered_text(
        draw,
        text=profile.meter_name.title(),
        center=(cx, cy - scale_radius - 24.0),
        font=title_font,
        fill=label_rgb,
        stroke_fill=resolve_text_stroke_fill(label_rgb),
        stroke_width=1,
    )

    unit_box = _bbox((cx - 58.0, cy + 36.0, cx + 58.0, cy + 88.0))
    draw.rounded_rectangle(tuple(unit_box), radius=13, fill=tuple(int(v) for v in style.label_fill_rgb), outline=tuple(int(v) for v in style.label_border_rgb), width=3)
    unit_text_bbox = draw_centered_text(
        draw,
        text=str(profile.unit),
        center=(cx, cy + 62.0),
        font=unit_font,
        fill=label_rgb,
        stroke_fill=resolve_text_stroke_fill(label_rgb),
        stroke_width=1,
    )
    unit_bbox = _bbox(_bbox_union(unit_box, unit_text_bbox))

    needle_angle = _angle_for_value(float(scenario.readout_value), scale_max=int(profile.scale_max))
    needle_end = _point_on_meter((cx, cy), needle_radius, needle_angle)
    tail = _point_on_meter((cx, cy), -16.0, needle_angle)
    draw.line((tail[0], tail[1], needle_end[0], needle_end[1]), fill=accent_rgb, width=8)
    draw.ellipse((cx - 16.0, cy - 16.0, cx + 16.0, cy + 16.0), fill=accent_rgb, outline=stroke, width=3)
    needle_bbox = _bbox((min(tail[0], needle_end[0], cx - 18.0) - 8.0, min(tail[1], needle_end[1], cy - 18.0) - 8.0, max(tail[0], needle_end[0], cx + 18.0) + 8.0, max(tail[1], needle_end[1], cy + 18.0) + 8.0))

    scale_region = _bbox(_bbox_union(arc_visual_bbox, title_bbox, *tick_bboxes, *label_bboxes, padding=6.0))
    annotation_map = {
        "needle": needle_bbox,
        "scale_region": scale_region,
        "unit_label": unit_bbox,
    }
    render_map = {
        "meter_profile": str(profile.profile_id),
        "meter_name": str(profile.meter_name),
        "unit": str(profile.unit),
        "scale_min": 0,
        "scale_max": int(profile.scale_max),
        "major_step": int(profile.major_step),
        "minor_step": int(profile.minor_step),
        "readout_value": int(scenario.readout_value),
        "needle_angle_deg": round(math.degrees(float(needle_angle)), 3),
        "needle_end_px": [round(float(needle_end[0]), 3), round(float(needle_end[1]), 3)],
        "face_bbox_px": face_bbox,
        "body_bbox_px": body_bbox,
    }
    return annotation_map, render_map


def _render_analog_meter(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scenario: _MeterScenario,
) -> _RenderedScene:
    canvas_width = int(_RENDER_DEFAULTS.get("canvas_width", _DEFAULTS.canvas_width))
    canvas_height = int(_RENDER_DEFAULTS.get("canvas_height", _DEFAULTS.canvas_height))
    background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        task_group="circuits",
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        require_grid=True,
    )
    draw = ImageDraw.Draw(background)
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.render")
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{FAMILY_ID}.font",
        params=params,
    )
    panel = (
        float(_RENDER_DEFAULTS.get("panel_left_px", _DEFAULTS.panel_left_px)),
        float(_RENDER_DEFAULTS.get("panel_top_px", _DEFAULTS.panel_top_px)),
        float(canvas_width - int(_RENDER_DEFAULTS.get("panel_right_margin_px", _DEFAULTS.panel_right_margin_px))),
        float(canvas_height - int(_RENDER_DEFAULTS.get("panel_bottom_margin_px", _DEFAULTS.panel_bottom_margin_px))),
    )
    draw.rounded_rectangle(
        panel,
        radius=20,
        fill=tuple(int(v) for v in diagram_style.panel_fill_rgb),
        outline=tuple(int(v) for v in diagram_style.panel_border_rgb),
        width=3,
    )
    center = (
        float(_RENDER_DEFAULTS.get("meter_center_x_px", _DEFAULTS.meter_center_x_px)) + float(rng.randint(-14, 14)),
        float(_RENDER_DEFAULTS.get("meter_center_y_px", _DEFAULTS.meter_center_y_px)) + float(rng.randint(-8, 8)),
    )
    accent_palette = (
        (190, 45, 42),
        (36, 100, 190),
        (44, 143, 91),
        (173, 94, 35),
        (132, 78, 171),
    )
    accent_rgb = accent_palette[int(hash64(int(instance_seed), f"{FAMILY_ID}.needle_color", 0) % len(accent_palette))]
    annotation_map, render_map = _draw_meter_face(
        draw,
        center=center,
        scenario=scenario,
        style=diagram_style,
        font_family=str(font_family),
        accent_rgb=accent_rgb,
        render_defaults=_RENDER_DEFAULTS,
    )
    image, post_noise_meta = apply_post_image_noise(
        background,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    render_map.update(
        {
            "center_px": [round(float(center[0]), 3), round(float(center[1]), 3)],
            "needle_rgb": list(int(v) for v in accent_rgb),
            "technical_diagram_style": dict(diagram_style_meta),
            "background_style": background_meta,
            "post_image_noise": post_noise_meta,
        }
    )
    scene_entities = [
        {"id": "needle", "bbox_px": list(annotation_map["needle"]), "readout_value": int(scenario.readout_value)},
        {"id": "scale_region", "bbox_px": list(annotation_map["scale_region"]), "scale_max": int(scenario.profile.scale_max)},
        {"id": "unit_label", "bbox_px": list(annotation_map["unit_label"]), "unit": str(scenario.profile.unit)},
    ]
    return _RenderedScene(
        image=image,
        annotation_bbox_map={str(key): list(value) for key, value in annotation_map.items()},
        scene_entities=scene_entities,
        render_map=render_map,
    )


@register_task
class PhysicsAnalogMeterReadoutValueTask:
    """Read an analog ammeter or voltmeter needle value."""

    domain = "physics"
    task_group = "circuits"
    task_id = TASK_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        scenario = _resolve_scenario(int(instance_seed), params)
        rendered = _render_analog_meter(
            instance_seed=int(instance_seed),
            params=params,
            scenario=scenario,
        )
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
        answer_gt = TypedValue(type="integer", value=int(scenario.readout_value))
        annotation_gt = TypedValue(type="keyed_bbox_map", value={str(k): list(v) for k, v in rendered.annotation_bbox_map.items()})
        json_example, json_example_answer_only = build_prompt_json_examples(
            annotation_value=annotation_gt.value,
            answer_type=str(answer_gt.type),
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
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
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.font",
            params=params,
        )
        font_record = get_font_family_record(str(font_family))
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"physics_analog_meter_{scenario.profile.profile_id}",
                "entities": list(rendered.scene_entities),
                "relations": {
                    "query_id": str(query_id),
                    "meter_profile": str(scenario.profile.profile_id),
                    "unit": str(scenario.profile.unit),
                    "readout_value": int(scenario.readout_value),
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
                    "meter_profile": str(scenario.profile.profile_id),
                    "unit": str(scenario.profile.unit),
                    "target_answer": int(scenario.readout_value),
                    "query_id_probabilities": dict(scenario.query_id_probabilities),
                    "meter_profile_probabilities": dict(scenario.meter_profile_probabilities),
                    "target_answer_probabilities": dict(scenario.target_answer_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(rendered.image.size[0]),
                "canvas_height": int(rendered.image.size[1]),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "analog_meter_diagram",
                },
                "technical_diagram_style": dict(rendered.render_map["technical_diagram_style"]),
                "background_style": dict(rendered.render_map["background_style"]),
                "post_image_noise": dict(rendered.render_map["post_image_noise"]),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "query_id": str(query_id),
                "meter_profile": str(scenario.profile.profile_id),
                "unit": str(scenario.profile.unit),
                "scale_max": int(scenario.profile.scale_max),
                "readout_value": int(scenario.readout_value),
                "target_answer": int(scenario.readout_value),
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
            complexity=TaskComplexity(
                complexity_score=0.33,
                complexity_components={
                    "visual_readout": 0.58,
                    "scale_mapping": 0.16,
                    "ambiguity": 0.12,
                    "output_burden": 0.14,
                },
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )
