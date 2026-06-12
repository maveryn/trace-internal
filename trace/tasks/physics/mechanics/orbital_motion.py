"""Physics orbital-motion tasks for Kepler-style ellipse diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_NAMESPACE = "physics_mechanics_orbital_motion"
SCENE_ID = "orbital_motion"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "sun_focus_label",
    "greatest_speed_position_label",
    "least_speed_position_label",
)
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")

_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "mechanics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_NAMESPACE,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="mechanics", apply_prob=0.5)


@dataclass(frozen=True)
class _OrbitSpec:
    query_id: str
    center: Tuple[float, float]
    semi_major: float
    semi_minor: float
    rotation_rad: float
    focus_side: int
    candidate_points: Dict[str, Tuple[float, float]]
    selected_label: str
    selected_point: Tuple[float, float]
    sun_point: Tuple[float, float] | None
    major_axis_endpoints: Tuple[Tuple[float, float], Tuple[float, float]]
    eccentricity: float


def _bbox_from_center(center: Tuple[float, float], half_w: float, half_h: float) -> List[float]:
    return [
        round(float(center[0] - half_w), 3),
        round(float(center[1] - half_h), 3),
        round(float(center[0] + half_w), 3),
        round(float(center[1] + half_h), 3),
    ]


def _rotated_point(center: Tuple[float, float], x: float, y: float, theta: float) -> Tuple[float, float]:
    cos_t = math.cos(float(theta))
    sin_t = math.sin(float(theta))
    return (
        float(center[0] + x * cos_t - y * sin_t),
        float(center[1] + x * sin_t + y * cos_t),
    )


def _major_axis_unit(theta: float) -> Tuple[float, float]:
    return (float(math.cos(theta)), float(math.sin(theta)))


def _point_on_orbit(spec: _OrbitSpec, angle_rad: float) -> Tuple[float, float]:
    return _rotated_point(
        spec.center,
        float(spec.semi_major * math.cos(angle_rad)),
        float(spec.semi_minor * math.sin(angle_rad)),
        spec.rotation_rad,
    )


def _choice(values: Sequence[str], instance_seed: int, namespace: str, params: Mapping[str, Any], explicit_key: str) -> str:
    explicit = params.get(str(explicit_key))
    if explicit is not None and str(explicit) in set(values):
        return str(explicit)
    index = int(hash64(int(instance_seed), str(namespace), 0) % max(1, len(values)))
    return str(values[index])


def _make_orbit_spec(instance_seed: int, *, params: Mapping[str, Any], query_id: str) -> _OrbitSpec:
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.orbit")
    canvas_width = int(_RENDER_DEFAULTS.get("canvas_width", 1040))
    canvas_height = int(_RENDER_DEFAULTS.get("canvas_height", 720))
    center = (
        float(canvas_width * 0.50 + rng.randint(-28, 28)),
        float(canvas_height * 0.52 + rng.randint(-18, 20)),
    )
    semi_major = float(rng.choice([270, 290, 310]))
    semi_minor = float(rng.choice([176, 192, 208]))
    if semi_minor >= semi_major:
        semi_minor = float(semi_major * 0.55)
    rotation_deg = float(rng.choice([-24, -14, 0, 16, 26]))
    rotation_rad = math.radians(rotation_deg)
    focus_distance = math.sqrt(float(semi_major * semi_major - semi_minor * semi_minor))
    axis_unit = _major_axis_unit(rotation_rad)
    focus_side = 1 if int(hash64(int(instance_seed), f"{TASK_NAMESPACE}.focus_side", 0) % 2) == 0 else -1
    focus = (
        float(center[0] + focus_side * focus_distance * axis_unit[0]),
        float(center[1] + focus_side * focus_distance * axis_unit[1]),
    )
    opposite_focus = (
        float(center[0] - focus_side * focus_distance * axis_unit[0]),
        float(center[1] - focus_side * focus_distance * axis_unit[1]),
    )
    major_end_1 = (
        float(center[0] + semi_major * axis_unit[0]),
        float(center[1] + semi_major * axis_unit[1]),
    )
    major_end_2 = (
        float(center[0] - semi_major * axis_unit[0]),
        float(center[1] - semi_major * axis_unit[1]),
    )

    labels = list(OPTION_LABELS)
    rng.shuffle(labels)

    if str(query_id) == "sun_focus_label":
        selected_point = focus
        raw_points = [
            ("selected_focus", focus),
            ("center", center),
            ("on_orbit_1", _rotated_point(center, 0.0, semi_minor, rotation_rad)),
            ("on_orbit_2", _rotated_point(center, -0.88 * semi_major, 0.32 * semi_minor, rotation_rad)),
            ("inside_not_focus", _rotated_point(center, 0.35 * semi_major, -0.32 * semi_minor, rotation_rad)),
            ("near_other_focus", _rotated_point(center, -focus_side * 0.72 * focus_distance, 0.20 * semi_minor, rotation_rad)),
        ]
        selected_label = labels[0]
        candidate_points = {selected_label: selected_point}
        for label, (_, point) in zip(labels[1:], raw_points[1:]):
            candidate_points[str(label)] = point
        sun_point = None
    else:
        sun_point = focus

        def _distance_to_sun(point: Tuple[float, float]) -> float:
            return math.hypot(float(point[0] - focus[0]), float(point[1] - focus[1]))

        endpoints = (major_end_1, major_end_2)
        perihelion = min(endpoints, key=_distance_to_sun)
        aphelion = max(endpoints, key=_distance_to_sun)
        selected_point = perihelion if str(query_id) == "greatest_speed_position_label" else aphelion
        selected_label = labels[0]
        candidate_points = {selected_label: selected_point}
        distractor_angles = [math.radians(v) for v in (58, 126, 218, 302, 20)]
        for label, angle in zip(labels[1:], distractor_angles):
            point = _point_on_orbit(
                _OrbitSpec(
                    query_id=str(query_id),
                    center=center,
                    semi_major=semi_major,
                    semi_minor=semi_minor,
                    rotation_rad=rotation_rad,
                    focus_side=focus_side,
                    candidate_points={},
                    selected_label=selected_label,
                    selected_point=selected_point,
                    sun_point=sun_point,
                    major_axis_endpoints=(major_end_1, major_end_2),
                    eccentricity=float(focus_distance / semi_major),
                ),
                angle,
            )
            candidate_points[str(label)] = point
        if aphelion != selected_point and str(query_id) == "greatest_speed_position_label":
            candidate_points[labels[-1]] = aphelion
        if perihelion != selected_point and str(query_id) == "least_speed_position_label":
            candidate_points[labels[-1]] = perihelion

    return _OrbitSpec(
        query_id=str(query_id),
        center=center,
        semi_major=semi_major,
        semi_minor=semi_minor,
        rotation_rad=rotation_rad,
        focus_side=int(focus_side),
        candidate_points={str(k): tuple(v) for k, v in candidate_points.items()},
        selected_label=str(selected_label),
        selected_point=tuple(selected_point),
        sun_point=sun_point,
        major_axis_endpoints=(major_end_1, major_end_2),
        eccentricity=float(focus_distance / semi_major),
    )


def _draw_orbit_scene(
    *,
    image: Image.Image,
    spec: _OrbitSpec,
    font_family: str,
    style: Any,
) -> Tuple[Image.Image, Dict[str, Any], Dict[str, Any], List[Dict[str, Any]]]:
    draw = ImageDraw.Draw(image)
    label_font = load_font(30, bold=True, font_family=font_family)
    small_font = load_font(23, bold=True, font_family=font_family)
    title_font = load_font(26, bold=True, font_family=font_family)
    stroke = tuple(int(v) for v in style.stroke_rgb)
    muted = tuple(int(v) for v in style.secondary_stroke_rgb)
    guide = tuple(int(v) for v in style.guide_rgb)
    accent = tuple(int(v) for v in style.accent_rgb)
    label_fill = tuple(int(v) for v in style.label_fill_rgb)
    label_outline = tuple(int(v) for v in style.label_border_rgb)
    label_text = tuple(int(v) for v in style.label_rgb)

    panel = [54, 52, image.size[0] - 54, image.size[1] - 58]
    draw.rounded_rectangle(panel, radius=18, fill=tuple(style.panel_fill_rgb), outline=tuple(style.panel_border_rgb), width=3)

    points = [_rotated_point(spec.center, spec.semi_major * math.cos(t), spec.semi_minor * math.sin(t), spec.rotation_rad) for t in [i * 2 * math.pi / 240 for i in range(241)]]
    draw.line(points, fill=stroke, width=5, joint="curve")
    draw.line([spec.major_axis_endpoints[0], spec.major_axis_endpoints[1]], fill=guide, width=2)
    minor_1 = _rotated_point(spec.center, 0.0, spec.semi_minor, spec.rotation_rad)
    minor_2 = _rotated_point(spec.center, 0.0, -spec.semi_minor, spec.rotation_rad)
    draw.line([minor_1, minor_2], fill=guide, width=2)
    draw.ellipse(_bbox_from_center(spec.center, 6, 6), fill=muted, outline=stroke, width=2)
    draw_centered_text(draw, text="center", center=(spec.center[0], spec.center[1] + 28), font=small_font, fill=muted, stroke_fill=resolve_text_stroke_fill(muted), stroke_width=1)

    if spec.sun_point is not None:
        sx, sy = spec.sun_point
        draw.ellipse(_bbox_from_center((sx, sy), 20, 20), fill=(255, 205, 68), outline=(164, 96, 22), width=3)
        draw_centered_text(draw, text="Sun", center=(sx, sy + 42), font=small_font, fill=(120, 72, 20), stroke_fill=(255, 248, 210), stroke_width=2)

    candidate_bboxes: Dict[str, List[float]] = {}
    entities: List[Dict[str, Any]] = []
    for label, point in sorted(spec.candidate_points.items()):
        x, y = point
        draw.ellipse(_bbox_from_center((x, y), 13, 13), fill=accent, outline=stroke, width=3)
        label_center = (float(x + 29), float(y - 28))
        label_bbox = _bbox_from_center(label_center, 19, 18)
        draw.rounded_rectangle(label_bbox, radius=8, fill=label_fill, outline=label_outline, width=2)
        draw_centered_text(draw, text=str(label), center=label_center, font=label_font, fill=label_text, stroke_fill=resolve_text_stroke_fill(label_text), stroke_width=1)
        candidate_bboxes[str(label)] = _bbox_from_center((x, y), 18, 18)
        entities.append({"id": f"candidate_{label}", "label": str(label), "center": [round(x, 3), round(y, 3)]})

    draw_centered_text(
        draw,
        text="elliptical orbit",
        center=(image.size[0] * 0.5, panel[1] + 28),
        font=title_font,
        fill=tuple(style.label_rgb),
        stroke_fill=resolve_text_stroke_fill(tuple(style.label_rgb)),
        stroke_width=1,
    )

    keyed_points: Dict[str, List[float]] = {
        "selected_focus" if spec.query_id == "sun_focus_label" else "selected_position": [
            round(float(spec.selected_point[0]), 3),
            round(float(spec.selected_point[1]), 3),
        ],
    }
    if spec.query_id == "sun_focus_label":
        keyed_points["center"] = [round(float(spec.center[0]), 3), round(float(spec.center[1]), 3)]
        keyed_points["major_axis_endpoint_1"] = [
            round(float(spec.major_axis_endpoints[0][0]), 3),
            round(float(spec.major_axis_endpoints[0][1]), 3),
        ]
        keyed_points["major_axis_endpoint_2"] = [
            round(float(spec.major_axis_endpoints[1][0]), 3),
            round(float(spec.major_axis_endpoints[1][1]), 3),
        ]
    else:
        assert spec.sun_point is not None
        keyed_points["sun"] = [round(float(spec.sun_point[0]), 3), round(float(spec.sun_point[1]), 3)]

    render_map = {
        "candidate_bboxes": candidate_bboxes,
        "candidate_points": {str(k): [round(float(v[0]), 3), round(float(v[1]), 3)] for k, v in spec.candidate_points.items()},
        "selected_label": str(spec.selected_label),
        "keyed_points": keyed_points,
    }
    return image, keyed_points, render_map, entities


class _PhysicsOrbitalMotionBaseTask:
    domain = "physics"
    scene_id = "mechanics"
    default_dataset_enabled = True
    fixed_query_id: str | None = None

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        supported = (str(self.fixed_query_id),) if self.fixed_query_id else (
            "greatest_speed_position_label",
            "least_speed_position_label",
        )
        query_id = _choice(supported, int(instance_seed), f"{TASK_NAMESPACE}.query_id", params, "query_id")
        spec = _make_orbit_spec(int(instance_seed), params=params, query_id=query_id)
        canvas_width = int(_RENDER_DEFAULTS.get("canvas_width", 1040))
        canvas_height = int(_RENDER_DEFAULTS.get("canvas_height", 720))
        background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
            instance_seed=int(instance_seed),
            params=params,
            scene_id=SCENE_ID,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            require_grid=True,
        )
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_NAMESPACE}.font",
            params=params,
        )
        font_record = get_font_family_record(str(font_family))
        image, annotation_points, render_map, entities = _draw_orbit_scene(
            image=background,
            spec=spec,
            font_family=str(font_family),
            style=diagram_style,
        )
        image, post_noise_meta = apply_post_image_noise(
            image,
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
                f"answer_hint_{query_id}",
                f"annotation_hint_{query_id}",
                "object_description",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_gt = TypedValue(type="option_letter", value=str(spec.selected_label))
        annotation_gt = TypedValue(type="keyed_point_map", value=dict(annotation_points))
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
                "scene_kind": "physics_orbital_motion_ellipse",
                "entities": entities,
                "relations": {
                    "query_id": str(query_id),
                    "selected_label": str(spec.selected_label),
                    "selected_point": list(annotation_points[next(iter(annotation_points))]),
                    "eccentricity": round(float(spec.eccentricity), 4),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {"query_id": str(query_id), "target_answer": str(spec.selected_label)},
            },
            "render_spec": {
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "orbital_motion_diagram",
                },
                "technical_diagram_style": dict(diagram_style_meta),
                "background_style": background_meta,
                "post_image_noise": post_noise_meta,
            },
            "render_map": dict(render_map),
            "execution_trace": {
                "query_id": str(query_id),
                "target_answer": str(spec.selected_label),
                "candidate_points": dict(render_map["candidate_points"]),
                "focus_side": int(spec.focus_side),
            },
            "witness_symbolic": {
                "type": "point_map",
                "keys": sorted(annotation_gt.value.keys()),
            },
            "projected_annotation": {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_gt.value),
                "pixel_keyed_point_map": dict(annotation_gt.value),
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
            query_id=str(query_id),
        )


@register_task
class PhysicsOrbitalMotionFocusLocationLabelTask(_PhysicsOrbitalMotionBaseTask):
    """Choose the labeled point that can be the Sun/focus of an elliptical orbit."""

    task_id = "task_physics__orbital_motion__focus_location_label"
    fixed_query_id = "sun_focus_label"


@register_task
class PhysicsOrbitalMotionSpeedExtremumLabelTask(_PhysicsOrbitalMotionBaseTask):
    """Choose the labeled planet position with greatest or least orbital speed."""

    task_id = "task_physics__orbital_motion__orbital_speed_extremum_label"
    fixed_query_id = None
