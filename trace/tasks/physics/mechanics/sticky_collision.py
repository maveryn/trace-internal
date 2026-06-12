"""Physics mechanics tasks for perpendicular sticky-collision diagrams."""

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
from ...shared.bbox_projection import bbox_union_many as _bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_arrow, draw_centered_text, draw_rounded_rect
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_layout_jitter, resolve_render_int
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import (
    apply_balanced_variant_sampling,
    is_uniform_probability_map,
    resolve_compatible_scene_query_ids,
    resolve_variant,
)
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from trace.tasks.shared.fixed_query import FixedPhysicsQueryVariantTaskMixin
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES, build_physics_collision_theme
from ..shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "physics_mechanics_sticky_collision"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "wide_table",
    "compact_table",
    "gridded_table",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "direction_choice",
    "velocity_component",
)
SUPPORTED_COMPONENT_AXES: Tuple[str, ...] = ("x", "y")
OPTION_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "wide_table": SUPPORTED_QUERY_IDS,
    "compact_table": SUPPORTED_QUERY_IDS,
    "gridded_table": SUPPORTED_QUERY_IDS,
}
ANNOTATION_ENTITY_KEY_BY_ID: Dict[str, str] = {
    "horizontal_puck": "A",
    "vertical_puck": "B",
    "stuck_pucks": "A+B",
}
ANNOTATION_ENTITY_IDS: Tuple[str, ...] = tuple(ANNOTATION_ENTITY_KEY_BY_ID.keys())


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for sticky-collision scenes."""

    canvas_width: int = 1180
    canvas_height: int = 760
    table_left_px: int = 52
    table_top_px: int = 48
    table_width_px: int = 1076
    table_height_px: int = 506
    table_corner_radius_px: int = 22
    collision_center_x_px: int = 436
    collision_center_y_px: int = 304
    compact_collision_center_x_px: int = 420
    compact_collision_center_y_px: int = 292
    horizontal_start_distance_px: int = 300
    vertical_start_distance_px: int = 200
    compact_start_distance_delta_px: int = -20
    puck_radius_px: int = 42
    stuck_radius_px: int = 50
    motion_arrow_width_px: int = 8
    final_arrow_width_px: int = 8
    arrow_head_length_px: int = 24
    arrow_head_width_px: int = 22
    label_font_size_px: int = 23
    puck_font_size_px: int = 30
    option_font_size_px: int = 24
    label_stroke_width_px: int = 2
    option_panel_top_px: int = 584
    option_cell_left_px: int = 82
    option_cell_width_px: int = 164
    option_arrow_length_px: int = 74
    option_arrow_width_px: int = 7
    option_arrow_head_length_px: int = 20
    option_arrow_head_width_px: int = 18
    grid_spacing_px: int = 44
    mass_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    speed_support: Tuple[int, ...] = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
    component_answer_support: Tuple[int, ...] = (-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6)


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query axes and answer support for one instance."""

    scene_variant: str
    query_id: str
    component_axis: str | None
    accent_color_name: str
    target_answer: int | str
    correct_option_letter: str
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    component_axis_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]
    correct_option_letter_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _CollisionScenario:
    """One symbolic perpendicular sticky-collision setup."""

    horizontal_mass: int
    vertical_mass: int
    horizontal_speed: int
    vertical_speed: int
    horizontal_sign: int
    vertical_sign: int
    final_vx: int
    final_vy: int
    total_mass: int


@dataclass(frozen=True)
class _SceneSpec:
    """Resolved symbolic sticky-collision scene."""

    scene_variant: str
    query_id: str
    component_axis: str | None
    scenario: _CollisionScenario
    correct_option_letter: str
    option_angles_degrees: Dict[str, float]
    direction_label: str
    target_answer: int | str
    annotation_entity_ids: Tuple[str, ...]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered sticky-collision scene plus prompt-facing annotation metadata."""

    image: Image.Image
    annotation_points: List[List[float]]
    annotation_point_map: Dict[str, List[float]]
    annotation_entity_ids: List[str]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "mechanics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="mechanics", apply_prob=0.5)


def _with_sampling_divisor(params: Mapping[str, Any], *, divisor: int, explicit_keys: Sequence[str]) -> Mapping[str, Any]:
    """No-op hook for axis-decoupling call sites."""

    _ = int(divisor), explicit_keys
    return params


def _component_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return configured signed final-component answer support."""

    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="component_answer_support",
        fallback=_DEFAULTS.component_answer_support,
    )


def _mass_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return configured puck mass support."""

    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="mass_support",
        fallback=_DEFAULTS.mass_support,
    )


def _speed_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return configured input speed support."""

    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="speed_support",
        fallback=_DEFAULTS.speed_support,
    )


def _direction_sign(value: Any, *, axis: str) -> int:
    """Resolve one named cardinal direction into a signed component."""

    text = str(value).strip().lower()
    if str(axis) == "horizontal":
        mapping = {"right": 1, "+x": 1, "east": 1, "left": -1, "-x": -1, "west": -1}
    else:
        mapping = {"up": 1, "+y": 1, "north": 1, "down": -1, "-y": -1, "south": -1}
    if text not in mapping:
        raise ValueError(f"unsupported {axis} direction: {value}")
    return int(mapping[text])


def _feasible_collision_scenarios(params: Mapping[str, Any]) -> Tuple[_CollisionScenario, ...]:
    """Enumerate constructively feasible integer-component sticky collisions."""

    masses = _mass_support(params)
    speeds = _speed_support(params)
    component_values = set(int(value) for value in _component_support(params))
    component_magnitudes = {abs(int(value)) for value in component_values}
    explicit_horizontal_mass = params.get("horizontal_mass")
    explicit_vertical_mass = params.get("vertical_mass")
    explicit_horizontal_speed = params.get("horizontal_speed")
    explicit_vertical_speed = params.get("vertical_speed")
    explicit_horizontal_direction = params.get("horizontal_direction")
    explicit_vertical_direction = params.get("vertical_direction")
    horizontal_signs = (
        (_direction_sign(explicit_horizontal_direction, axis="horizontal"),)
        if explicit_horizontal_direction is not None
        else (-1, 1)
    )
    vertical_signs = (
        (_direction_sign(explicit_vertical_direction, axis="vertical"),)
        if explicit_vertical_direction is not None
        else (-1, 1)
    )

    scenarios: List[_CollisionScenario] = []
    for horizontal_mass in masses:
        if explicit_horizontal_mass is not None and int(horizontal_mass) != int(explicit_horizontal_mass):
            continue
        for vertical_mass in masses:
            if explicit_vertical_mass is not None and int(vertical_mass) != int(explicit_vertical_mass):
                continue
            total_mass = int(horizontal_mass) + int(vertical_mass)
            if int(total_mass) <= 0:
                continue
            for horizontal_speed in speeds:
                if explicit_horizontal_speed is not None and int(horizontal_speed) != int(explicit_horizontal_speed):
                    continue
                horizontal_momentum = int(horizontal_mass) * int(horizontal_speed)
                if int(horizontal_momentum) % int(total_mass) != 0:
                    continue
                final_vx_magnitude = int(horizontal_momentum) // int(total_mass)
                if int(final_vx_magnitude) not in component_magnitudes:
                    continue
                for vertical_speed in speeds:
                    if explicit_vertical_speed is not None and int(vertical_speed) != int(explicit_vertical_speed):
                        continue
                    vertical_momentum = int(vertical_mass) * int(vertical_speed)
                    if int(vertical_momentum) % int(total_mass) != 0:
                        continue
                    final_vy_magnitude = int(vertical_momentum) // int(total_mass)
                    if int(final_vy_magnitude) not in component_magnitudes:
                        continue
                    for horizontal_sign in horizontal_signs:
                        final_vx = int(horizontal_sign) * int(final_vx_magnitude)
                        if int(final_vx) not in component_values:
                            continue
                        for vertical_sign in vertical_signs:
                            final_vy = int(vertical_sign) * int(final_vy_magnitude)
                            if int(final_vy) not in component_values:
                                continue
                            scenarios.append(
                                _CollisionScenario(
                                    horizontal_mass=int(horizontal_mass),
                                    vertical_mass=int(vertical_mass),
                                    horizontal_speed=int(horizontal_speed),
                                    vertical_speed=int(vertical_speed),
                                    horizontal_sign=int(horizontal_sign),
                                    vertical_sign=int(vertical_sign),
                                    final_vx=int(final_vx),
                                    final_vy=int(final_vy),
                                    total_mass=int(total_mass),
                                )
                            )
    if not scenarios:
        raise ValueError("no feasible sticky-collision scenarios for configured supports")
    return tuple(scenarios)


def _resolve_component_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve a signed integer target answer for a component query."""

    support = _component_support(params)
    explicit_key = "target_answer"
    adjusted_params = _with_sampling_divisor(
        params,
        divisor=len(SUPPORTED_QUERY_IDS) * len(SUPPORTED_COMPONENT_AXES),
        explicit_keys=(explicit_key,),
    )
    selected, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=adjusted_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="component_answer_support",
        explicit_key=explicit_key,
        fallback_support=support,
        namespace=f"{TASK_ID}.target_answer.{str(query_id)}",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    return int(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_component_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str | None, Dict[str, float]]:
    """Resolve which velocity component a component query asks for."""

    if str(query_id) != "velocity_component":
        return None, {}
    adjusted_params = _with_sampling_divisor(
        params,
        divisor=len(SUPPORTED_QUERY_IDS),
        explicit_keys=("component_axis",),
    )
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.component_axis")
    selected, probabilities = resolve_variant(
        rng,
        params=adjusted_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_COMPONENT_AXES,
        explicit_key="component_axis",
        weights_key="component_axis_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=adjusted_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_COMPONENT_AXES,
        balance_flag_key="balanced_component_axis_sampling",
        explicit_key="component_axis",
        weights_key="component_axis_weights",
        sampling_namespace=f"{TASK_ID}.component_axis",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_correct_option_letter(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve which visible option letter carries the correct resultant arrow."""

    option_params = dict(params)
    if str(query_id) == "direction_choice" and option_params.get("correct_option_letter") is None:
        raw_target = option_params.get("target_answer")
        if raw_target is not None:
            option_params["correct_option_letter"] = str(raw_target).strip().upper()
    option_params = dict(
        _with_sampling_divisor(
            option_params,
            divisor=len(SUPPORTED_QUERY_IDS),
            explicit_keys=("correct_option_letter",),
        )
    )
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.correct_option_letter"),
        params=option_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=OPTION_LETTERS,
        explicit_key="correct_option_letter",
        weights_key="correct_option_letter_weights",
    )
    balanced_enabled = bool(
        option_params.get(
            "balanced_correct_option_letter_sampling",
            group_default(_GEN_DEFAULTS, "balanced_correct_option_letter_sampling", True),
        )
    )
    has_override = any(
        option_params.get(str(key)) is not None
        for key in ("correct_option_letter", "correct_option_letter_weights")
    )
    if (
        bool(balanced_enabled)
        and not bool(has_override)
        and is_uniform_probability_map(probabilities)
    ):
        selected = str(OPTION_LETTERS[abs(int(instance_seed)) % len(OPTION_LETTERS)])
    else:
        selected = apply_balanced_variant_sampling(
            instance_seed=int(instance_seed),
            params=option_params,
            gen_defaults=_GEN_DEFAULTS,
            selected_variant=str(selected),
            variant_probabilities=probabilities,
            supported_variants=OPTION_LETTERS,
            balance_flag_key="balanced_correct_option_letter_sampling",
            explicit_key="correct_option_letter",
            weights_key="correct_option_letter_weights",
            sampling_namespace=f"{TASK_ID}.correct_option_letter.{str(query_id)}",
        )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve scene/query/color/answer axes for one instance."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    scene_variant, scene_probs, query_id, query_probs = resolve_compatible_scene_query_ids(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_scene_variants=SUPPORTED_SCENE_VARIANTS,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        compatibility=COMPATIBILITY,
        scene_sampling_namespace=f"{TASK_ID}.scene_variant",
        query_sampling_namespace=f"{TASK_ID}.query_id",
        decouple_scene_sampling=True,
    )
    accent_name, accent_probs = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
    )
    accent_name = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(accent_name),
        variant_probabilities=accent_probs,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        balance_flag_key="balanced_accent_color_name_sampling",
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        sampling_namespace=f"{TASK_ID}.accent_color_name",
    )
    correct_option_letter, option_probs = _resolve_correct_option_letter(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    component_axis, component_axis_probs = _resolve_component_axis(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    if str(query_id) == "direction_choice":
        target_answer: int | str = str(correct_option_letter)
        target_probs = dict(option_probs)
    else:
        target_answer, target_probs = _resolve_component_target_answer(
            instance_seed=int(instance_seed),
            params=params,
            query_id=str(query_id),
        )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        component_axis=component_axis,
        accent_color_name=str(accent_name),
        target_answer=target_answer,
        correct_option_letter=str(correct_option_letter),
        scene_variant_probabilities={str(key): float(value) for key, value in sorted(scene_probs.items())},
        query_id_probabilities={str(key): float(value) for key, value in sorted(query_probs.items())},
        component_axis_probabilities={str(key): float(value) for key, value in sorted(component_axis_probs.items())},
        accent_color_name_probabilities={str(key): float(value) for key, value in sorted(accent_probs.items())},
        target_answer_probabilities={str(key): float(value) for key, value in sorted(target_probs.items())},
        correct_option_letter_probabilities=dict(option_probs),
    )


def _angle_degrees(vx: float, vy: float) -> float:
    """Return physics-plane angle in degrees in [0, 360)."""

    return float((math.degrees(math.atan2(float(vy), float(vx))) + 360.0) % 360.0)


def _angular_distance(a: float, b: float) -> float:
    """Return the smaller absolute angle difference in degrees."""

    delta = abs((float(a) - float(b) + 180.0) % 360.0 - 180.0)
    return float(delta)


def _direction_label(angle_degrees: float) -> str:
    """Return the nearest eight-way direction label for one vector angle."""

    labels = (
        ("east", 0.0),
        ("northeast", 45.0),
        ("north", 90.0),
        ("northwest", 135.0),
        ("west", 180.0),
        ("southwest", 225.0),
        ("south", 270.0),
        ("southeast", 315.0),
    )
    return min(labels, key=lambda item: _angular_distance(float(angle_degrees), float(item[1])))[0]


def _candidate_distractor_angles(correct_angle_degrees: float) -> Tuple[float, ...]:
    """Return a stable set of separated distractor angles around the correct arrow."""

    correct_angle = float(correct_angle_degrees) % 360.0
    candidates = [
        0.0,
        45.0,
        90.0,
        135.0,
        180.0,
        225.0,
        270.0,
        315.0,
        (correct_angle + 90.0) % 360.0,
        (correct_angle + 180.0) % 360.0,
        (correct_angle + 270.0) % 360.0,
        (360.0 - correct_angle) % 360.0,
        (180.0 - correct_angle) % 360.0,
    ]
    selected: List[float] = []
    for candidate in candidates:
        angle = round(float(candidate) % 360.0, 3)
        if _angular_distance(angle, correct_angle) < 22.0:
            continue
        if any(_angular_distance(angle, existing) < 18.0 for existing in selected):
            continue
        selected.append(float(angle))
        if len(selected) >= len(OPTION_LETTERS) - 1:
            return tuple(selected)
    offset = 36.0
    while len(selected) < len(OPTION_LETTERS) - 1:
        angle = round(float(correct_angle + offset) % 360.0, 3)
        if _angular_distance(angle, correct_angle) >= 22.0 and all(
            _angular_distance(angle, existing) >= 18.0 for existing in selected
        ):
            selected.append(float(angle))
        offset += 37.0
    return tuple(selected[: len(OPTION_LETTERS) - 1])


def _component_axis_label(component_axis: str | None) -> str:
    """Return the prompt-facing axis label for a component query."""

    return "horizontal" if str(component_axis) == "x" else "vertical"


def _sample_scene_spec(
    rng,
    *,
    scene_variant: str,
    query_id: str,
    component_axis: str | None,
    target_answer: int | str,
    correct_option_letter: str,
    params: Mapping[str, Any],
) -> _SceneSpec:
    """Sample one symbolic sticky-collision scene that realizes the target answer."""

    scenarios = list(_feasible_collision_scenarios(params))
    if str(query_id) == "velocity_component" and str(component_axis) == "x":
        scenarios = [scenario for scenario in scenarios if int(scenario.final_vx) == int(target_answer)]
    elif str(query_id) == "velocity_component" and str(component_axis) == "y":
        scenarios = [scenario for scenario in scenarios if int(scenario.final_vy) == int(target_answer)]
    if not scenarios:
        raise ValueError(
            f"no feasible sticky-collision scenario for {query_id} axis {component_axis} target {target_answer}"
        )

    scenario = scenarios[int(rng.randrange(len(scenarios)))]
    correct_angle = _angle_degrees(float(scenario.final_vx), float(scenario.final_vy))
    distractors = list(_candidate_distractor_angles(correct_angle))
    rng.shuffle(distractors)
    option_angles: Dict[str, float] = {}
    for letter in OPTION_LETTERS:
        if str(letter) == str(correct_option_letter):
            option_angles[str(letter)] = round(float(correct_angle), 3)
        else:
            option_angles[str(letter)] = round(float(distractors.pop()), 3)

    return _SceneSpec(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        component_axis=component_axis,
        scenario=scenario,
        correct_option_letter=str(correct_option_letter),
        option_angles_degrees=dict(option_angles),
        direction_label=str(_direction_label(correct_angle)),
        target_answer=target_answer,
        annotation_entity_ids=tuple(ANNOTATION_ENTITY_IDS),
    )


def _arrow_bbox(start: Tuple[float, float], end: Tuple[float, float], *, padding_px: float) -> List[float]:
    """Return a conservative bbox for one arrow."""

    return [
        round(float(min(float(start[0]), float(end[0])) - float(padding_px)), 3),
        round(float(min(float(start[1]), float(end[1])) - float(padding_px)), 3),
        round(float(max(float(start[0]), float(end[0])) + float(padding_px)), 3),
        round(float(max(float(start[1]), float(end[1])) + float(padding_px)), 3),
    ]


def _screen_unit_from_physics_angle(angle_degrees: float) -> Tuple[float, float]:
    """Map a physics-plane angle to a screen-space unit vector."""

    radians = math.radians(float(angle_degrees))
    return (float(math.cos(radians)), float(-math.sin(radians)))


def _draw_text_tag(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
    text_rgb: Tuple[int, int, int],
    stroke_width_px: int,
) -> List[float]:
    """Draw one rounded text tag and return its outer bbox."""

    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width_px)))
    text_width = float(text_bbox[2] - text_bbox[0])
    text_height = float(text_bbox[3] - text_bbox[1])
    pad_x = 12.0
    pad_y = 7.0
    center_x, center_y = float(center[0]), float(center[1])
    tag_bbox = [
        round(float(center_x - (0.5 * text_width) - pad_x), 3),
        round(float(center_y - (0.5 * text_height) - pad_y), 3),
        round(float(center_x + (0.5 * text_width) + pad_x), 3),
        round(float(center_y + (0.5 * text_height) + pad_y), 3),
    ]
    draw_rounded_rect(
        draw,
        tuple(float(value) for value in tag_bbox),
        radius=9,
        fill=tuple(int(value) for value in fill_rgb),
        outline=tuple(int(value) for value in outline_rgb),
        width=max(1, int(stroke_width_px)),
    )
    text_draw_bbox = draw_centered_text(
        draw,
        text=str(text),
        center=(float(center_x), float(center_y)),
        font=font,
        fill=tuple(int(value) for value in text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(text_rgb)),
        stroke_width=1,
    )
    return _bbox_union(tag_bbox, text_draw_bbox)


def _draw_grid(
    draw: ImageDraw.ImageDraw,
    *,
    table_bbox: Sequence[float],
    spacing_px: int,
    fill_rgb: Tuple[int, int, int],
) -> None:
    """Draw a light deterministic grid inside the collision table."""

    left, top, right, bottom = [float(value) for value in table_bbox]
    spacing = max(16, int(spacing_px))
    x = float(left + spacing)
    while x < float(right):
        draw.line([(float(x), float(top)), (float(x), float(bottom))], fill=tuple(int(value) for value in fill_rgb), width=1)
        x += float(spacing)
    y = float(top + spacing)
    while y < float(bottom):
        draw.line([(float(left), float(y)), (float(right), float(y))], fill=tuple(int(value) for value in fill_rgb), width=1)
        y += float(spacing)


def _puck_bbox(center: Tuple[float, float], *, radius_px: float) -> List[float]:
    """Return the bbox for one circular puck."""

    cx, cy = float(center[0]), float(center[1])
    radius = float(radius_px)
    return [
        round(float(cx - radius), 3),
        round(float(cy - radius), 3),
        round(float(cx + radius), 3),
        round(float(cy + radius), 3),
    ]


def _draw_puck(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    radius_px: int,
    label: str,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
    text_rgb: Tuple[int, int, int],
    font,
) -> Tuple[List[float], List[float]]:
    """Draw one labeled puck and return puck/text bboxes."""

    bbox = _puck_bbox(center, radius_px=float(radius_px))
    draw.ellipse(
        tuple(float(value) for value in bbox),
        fill=tuple(int(value) for value in fill_rgb),
        outline=tuple(int(value) for value in outline_rgb),
        width=4,
    )
    text_bbox = draw_centered_text(
        draw,
        text=str(label),
        center=(float(center[0]), float(center[1])),
        font=font,
        fill=tuple(int(value) for value in text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(text_rgb)),
        stroke_width=1,
    )
    return list(bbox), list(text_bbox)


def _render_scene(
    *,
    background: Image.Image,
    render_defaults: Mapping[str, Any],
    accent_color_name: str,
    scene_spec: _SceneSpec,
    font_family: str,
    diagram_style: Any | None = None,
) -> _RenderedScene:
    """Render one sticky-collision diagram and return trace metadata."""

    image = background.copy()
    draw = ImageDraw.Draw(image)
    theme = build_physics_collision_theme(str(accent_color_name), diagram_style=diagram_style)
    resolved_font_family = str(font_family)
    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=True, font_family=resolved_font_family)
    small_font = load_font(max(14, int(render_defaults["label_font_size_px"]) - 3), bold=False, font_family=resolved_font_family)
    puck_font = load_font(int(render_defaults["puck_font_size_px"]), bold=True, font_family=resolved_font_family)
    option_font = load_font(int(render_defaults["option_font_size_px"]), bold=True, font_family=resolved_font_family)

    table_bbox = [
        float(render_defaults["table_left_px"]),
        float(render_defaults["table_top_px"]),
        float(render_defaults["table_left_px"]) + float(render_defaults["table_width_px"]),
        float(render_defaults["table_top_px"]) + float(render_defaults["table_height_px"]),
    ]
    draw_rounded_rect(
        draw,
        tuple(float(value) for value in table_bbox),
        radius=int(render_defaults["table_corner_radius_px"]),
        fill=tuple(int(value) for value in theme.table_fill_rgb),
        outline=tuple(int(value) for value in theme.table_outline_rgb),
        width=4,
    )
    if str(scene_spec.scene_variant) == "gridded_table":
        _draw_grid(
            draw,
            table_bbox=table_bbox,
            spacing_px=int(render_defaults["grid_spacing_px"]),
            fill_rgb=tuple(int(value) for value in theme.grid_rgb),
        )

    if str(scene_spec.scene_variant) == "compact_table":
        center_x = float(render_defaults["compact_collision_center_x_px"])
        center_y = float(render_defaults["compact_collision_center_y_px"])
        distance_delta = float(render_defaults["compact_start_distance_delta_px"])
    else:
        center_x = float(render_defaults["collision_center_x_px"])
        center_y = float(render_defaults["collision_center_y_px"])
        distance_delta = 0.0

    puck_radius = int(render_defaults["puck_radius_px"])
    stuck_radius = int(render_defaults["stuck_radius_px"])
    horizontal_distance = float(render_defaults["horizontal_start_distance_px"]) + float(distance_delta)
    vertical_distance = float(render_defaults["vertical_start_distance_px"]) + float(distance_delta)
    scenario = scene_spec.scenario
    horizontal_screen_unit = (float(scenario.horizontal_sign), 0.0)
    vertical_screen_unit = (0.0, float(-scenario.vertical_sign))
    horizontal_center = (
        float(center_x - (horizontal_screen_unit[0] * horizontal_distance)),
        float(center_y - (horizontal_screen_unit[1] * horizontal_distance)),
    )
    vertical_center = (
        float(center_x - (vertical_screen_unit[0] * vertical_distance)),
        float(center_y - (vertical_screen_unit[1] * vertical_distance)),
    )
    collision_center = (float(center_x), float(center_y))

    # Draw approach tracks first so pucks and arrows remain visually dominant.
    draw.line(
        [horizontal_center, collision_center],
        fill=tuple(int(value) for value in theme.grid_rgb),
        width=3,
    )
    draw.line(
        [vertical_center, collision_center],
        fill=tuple(int(value) for value in theme.grid_rgb),
        width=3,
    )

    horizontal_arrow_start = (
        float(horizontal_center[0] + (horizontal_screen_unit[0] * (puck_radius + 12))),
        float(horizontal_center[1] + (horizontal_screen_unit[1] * (puck_radius + 12))),
    )
    horizontal_arrow_end = (
        float(center_x - (horizontal_screen_unit[0] * (stuck_radius + 20))),
        float(center_y - (horizontal_screen_unit[1] * (stuck_radius + 20))),
    )
    vertical_arrow_start = (
        float(vertical_center[0] + (vertical_screen_unit[0] * (puck_radius + 12))),
        float(vertical_center[1] + (vertical_screen_unit[1] * (puck_radius + 12))),
    )
    vertical_arrow_end = (
        float(center_x - (vertical_screen_unit[0] * (stuck_radius + 20))),
        float(center_y - (vertical_screen_unit[1] * (stuck_radius + 20))),
    )
    draw_arrow(
        draw,
        start=horizontal_arrow_start,
        end=horizontal_arrow_end,
        fill=tuple(int(value) for value in theme.motion_arrow_rgb),
        width=int(render_defaults["motion_arrow_width_px"]),
        head_length_px=float(render_defaults["arrow_head_length_px"]),
        head_width_px=float(render_defaults["arrow_head_width_px"]),
    )
    draw_arrow(
        draw,
        start=vertical_arrow_start,
        end=vertical_arrow_end,
        fill=tuple(int(value) for value in theme.motion_arrow_rgb),
        width=int(render_defaults["motion_arrow_width_px"]),
        head_length_px=float(render_defaults["arrow_head_length_px"]),
        head_width_px=float(render_defaults["arrow_head_width_px"]),
    )
    horizontal_arrow_bbox = _arrow_bbox(
        horizontal_arrow_start,
        horizontal_arrow_end,
        padding_px=float(render_defaults["arrow_head_width_px"]),
    )
    vertical_arrow_bbox = _arrow_bbox(
        vertical_arrow_start,
        vertical_arrow_end,
        padding_px=float(render_defaults["arrow_head_width_px"]),
    )

    horizontal_puck_bbox, _ = _draw_puck(
        draw,
        center=horizontal_center,
        radius_px=puck_radius,
        label="A",
        fill_rgb=tuple(int(value) for value in theme.puck_a_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.puck_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.puck_text_rgb),
        font=puck_font,
    )
    vertical_puck_bbox, _ = _draw_puck(
        draw,
        center=vertical_center,
        radius_px=puck_radius,
        label="B",
        fill_rgb=tuple(int(value) for value in theme.puck_b_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.puck_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.puck_text_rgb),
        font=puck_font,
    )
    stuck_bbox, _ = _draw_puck(
        draw,
        center=collision_center,
        radius_px=stuck_radius,
        label="A+B",
        fill_rgb=tuple(int(value) for value in theme.collision_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.collision_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.puck_text_rgb),
        font=load_font(max(18, int(render_defaults["puck_font_size_px"]) - 8), bold=True, font_family=resolved_font_family),
    )

    final_angle = _angle_degrees(float(scenario.final_vx), float(scenario.final_vy))

    # Quantity tags near the pucks keep the arithmetic grounded in the image.
    horizontal_label_x = float(horizontal_center[0])
    horizontal_label_y = float(horizontal_center[1] - 78.0)
    if horizontal_label_y < float(table_bbox[1] + 34.0):
        horizontal_label_y = float(horizontal_center[1] + 78.0)
    horizontal_mass_bbox = _draw_text_tag(
        draw,
        text=f"mA={int(scenario.horizontal_mass)} kg",
        center=(horizontal_label_x, horizontal_label_y),
        font=label_font,
        fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.label_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.label_text_rgb),
        stroke_width_px=int(render_defaults["label_stroke_width_px"]),
    )
    horizontal_speed_bbox = _draw_text_tag(
        draw,
        text=f"vA={int(scenario.horizontal_speed)} m/s",
        center=(float((horizontal_arrow_start[0] + horizontal_arrow_end[0]) / 2.0), float(center_y + 44.0)),
        font=label_font,
        fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.label_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.label_text_rgb),
        stroke_width_px=int(render_defaults["label_stroke_width_px"]),
    )
    vertical_label_x = float(vertical_center[0] + 96.0)
    if vertical_label_x > float(table_bbox[2] - 95.0):
        vertical_label_x = float(vertical_center[0] - 96.0)
    if float(vertical_center[1]) > float(center_y):
        vertical_mass_y = float(vertical_center[1] - 62.0)
        vertical_speed_y = float(vertical_center[1] - 8.0)
    else:
        vertical_mass_y = float(vertical_center[1] + 8.0)
        vertical_speed_y = float(vertical_center[1] + 62.0)
    vertical_mass_bbox = _draw_text_tag(
        draw,
        text=f"mB={int(scenario.vertical_mass)} kg",
        center=(vertical_label_x, vertical_mass_y),
        font=label_font,
        fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.label_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.label_text_rgb),
        stroke_width_px=int(render_defaults["label_stroke_width_px"]),
    )
    vertical_speed_bbox = _draw_text_tag(
        draw,
        text=f"vB={int(scenario.vertical_speed)} m/s",
        center=(vertical_label_x, vertical_speed_y),
        font=label_font,
        fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.label_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.label_text_rgb),
        stroke_width_px=int(render_defaults["label_stroke_width_px"]),
    )
    combined_mass_bbox = _draw_text_tag(
        draw,
        text=f"M={int(scenario.total_mass)} kg",
        center=(float(center_x + 140.0), float(center_y - 72.0)),
        font=label_font,
        fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.label_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.label_text_rgb),
        stroke_width_px=int(render_defaults["label_stroke_width_px"]),
    )

    # Small axis cue for signed-component tasks.
    axis_origin = (float(table_bbox[0] + 86.0), float(table_bbox[1] + 94.0))
    draw_arrow(
        draw,
        start=axis_origin,
        end=(float(axis_origin[0] + 64.0), float(axis_origin[1])),
        fill=tuple(int(value) for value in theme.option_arrow_rgb),
        width=4,
        head_length_px=14.0,
        head_width_px=12.0,
    )
    draw_arrow(
        draw,
        start=axis_origin,
        end=(float(axis_origin[0]), float(axis_origin[1] - 64.0)),
        fill=tuple(int(value) for value in theme.option_arrow_rgb),
        width=4,
        head_length_px=14.0,
        head_width_px=12.0,
    )
    x_axis_label_bbox = draw_centered_text(
        draw,
        text="+x",
        center=(float(axis_origin[0] + 82.0), float(axis_origin[1])),
        font=small_font,
        fill=tuple(int(value) for value in theme.label_text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.label_text_rgb)),
        stroke_width=1,
    )
    y_axis_label_bbox = draw_centered_text(
        draw,
        text="+y",
        center=(float(axis_origin[0]), float(axis_origin[1] - 82.0)),
        font=small_font,
        fill=tuple(int(value) for value in theme.label_text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.label_text_rgb)),
        stroke_width=1,
    )
    axis_bbox = _bbox_union(
        [axis_origin[0], axis_origin[1] - 76.0, axis_origin[0] + 76.0, axis_origin[1]],
        x_axis_label_bbox,
        y_axis_label_bbox,
    )

    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": "collision_table",
            "entity_type": "collision_table",
            "bbox_px": [round(float(value), 3) for value in table_bbox],
            "meta": {"scene_variant": str(scene_spec.scene_variant)},
        },
        {
            "entity_id": "axis_cue",
            "entity_type": "signed_axis_cue",
            "bbox_px": list(axis_bbox),
            "meta": {"positive_x": "right", "positive_y": "up"},
        },
        {
            "entity_id": "horizontal_puck",
            "entity_type": "puck",
            "bbox_px": list(horizontal_puck_bbox),
            "point_px": [round(float(horizontal_center[0]), 3), round(float(horizontal_center[1]), 3)],
            "meta": {
                "label": "A",
                "mass": int(scenario.horizontal_mass),
                "speed": int(scenario.horizontal_speed),
                "direction": "right" if int(scenario.horizontal_sign) > 0 else "left",
            },
        },
        {
            "entity_id": "vertical_puck",
            "entity_type": "puck",
            "bbox_px": list(vertical_puck_bbox),
            "point_px": [round(float(vertical_center[0]), 3), round(float(vertical_center[1]), 3)],
            "meta": {
                "label": "B",
                "mass": int(scenario.vertical_mass),
                "speed": int(scenario.vertical_speed),
                "direction": "up" if int(scenario.vertical_sign) > 0 else "down",
            },
        },
        {
            "entity_id": "stuck_pucks",
            "entity_type": "stuck_puck_pair",
            "bbox_px": list(stuck_bbox),
            "point_px": [round(float(collision_center[0]), 3), round(float(collision_center[1]), 3)],
            "meta": {"total_mass": int(scenario.total_mass)},
        },
        {
            "entity_id": "horizontal_motion_arrow",
            "entity_type": "input_velocity_arrow",
            "bbox_px": list(horizontal_arrow_bbox),
            "meta": {"puck": "A", "axis": "x", "sign": int(scenario.horizontal_sign)},
        },
        {
            "entity_id": "vertical_motion_arrow",
            "entity_type": "input_velocity_arrow",
            "bbox_px": list(vertical_arrow_bbox),
            "meta": {"puck": "B", "axis": "y", "sign": int(scenario.vertical_sign)},
        },
        {
            "entity_id": "horizontal_mass_label",
            "entity_type": "mass_label",
            "bbox_px": list(horizontal_mass_bbox),
            "meta": {"puck": "A", "value": int(scenario.horizontal_mass)},
        },
        {
            "entity_id": "horizontal_speed_label",
            "entity_type": "speed_label",
            "bbox_px": list(horizontal_speed_bbox),
            "meta": {"puck": "A", "value": int(scenario.horizontal_speed)},
        },
        {
            "entity_id": "vertical_mass_label",
            "entity_type": "mass_label",
            "bbox_px": list(vertical_mass_bbox),
            "meta": {"puck": "B", "value": int(scenario.vertical_mass)},
        },
        {
            "entity_id": "vertical_speed_label",
            "entity_type": "speed_label",
            "bbox_px": list(vertical_speed_bbox),
            "meta": {"puck": "B", "value": int(scenario.vertical_speed)},
        },
        {
            "entity_id": "combined_mass_label",
            "entity_type": "combined_mass_label",
            "bbox_px": list(combined_mass_bbox),
            "meta": {"value": int(scenario.total_mass)},
        },
    ]
    horizontal_component_witness_bbox = _bbox_union(
        horizontal_puck_bbox,
        horizontal_arrow_bbox,
        horizontal_mass_bbox,
        horizontal_speed_bbox,
        combined_mass_bbox,
    )
    vertical_component_witness_bbox = _bbox_union(
        vertical_puck_bbox,
        vertical_arrow_bbox,
        vertical_mass_bbox,
        vertical_speed_bbox,
        combined_mass_bbox,
    )
    scene_entities.extend(
        [
            {
                "entity_id": "horizontal_component_witness",
                "entity_type": "component_momentum_witness",
                "bbox_px": list(horizontal_component_witness_bbox),
                "meta": {
                    "axis": "x",
                    "puck": "A",
                    "members": [
                        "horizontal_puck",
                        "horizontal_motion_arrow",
                        "horizontal_mass_label",
                        "horizontal_speed_label",
                        "combined_mass_label",
                    ],
                },
            },
            {
                "entity_id": "vertical_component_witness",
                "entity_type": "component_momentum_witness",
                "bbox_px": list(vertical_component_witness_bbox),
                "meta": {
                    "axis": "y",
                    "puck": "B",
                    "members": [
                        "vertical_puck",
                        "vertical_motion_arrow",
                        "vertical_mass_label",
                        "vertical_speed_label",
                        "combined_mass_label",
                    ],
                },
            },
        ]
    )

    option_bboxes: Dict[str, List[float]] = {}
    option_top = float(render_defaults["option_panel_top_px"])
    option_left = float(render_defaults["option_cell_left_px"])
    option_width = float(render_defaults["option_cell_width_px"])
    option_arrow_length = float(render_defaults["option_arrow_length_px"])
    for option_index, letter in enumerate(OPTION_LETTERS):
        cell_center_x = float(option_left + (option_index * option_width) + (0.5 * option_width))
        cell_center_y = float(option_top + 76.0)
        letter_bbox = _draw_text_tag(
            draw,
            text=str(letter),
            center=(float(cell_center_x), float(option_top + 24.0)),
            font=option_font,
            fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
            outline_rgb=tuple(int(value) for value in theme.option_outline_rgb),
            text_rgb=tuple(int(value) for value in theme.label_text_rgb),
            stroke_width_px=int(render_defaults["label_stroke_width_px"]),
        )
        unit = _screen_unit_from_physics_angle(float(scene_spec.option_angles_degrees[str(letter)]))
        arrow_start = (
            float(cell_center_x - (unit[0] * option_arrow_length * 0.5)),
            float(cell_center_y - (unit[1] * option_arrow_length * 0.5)),
        )
        arrow_end = (
            float(cell_center_x + (unit[0] * option_arrow_length * 0.5)),
            float(cell_center_y + (unit[1] * option_arrow_length * 0.5)),
        )
        draw_arrow(
            draw,
            start=arrow_start,
            end=arrow_end,
            fill=tuple(int(value) for value in theme.option_arrow_rgb),
            width=int(render_defaults["option_arrow_width_px"]),
            head_length_px=float(render_defaults["option_arrow_head_length_px"]),
            head_width_px=float(render_defaults["option_arrow_head_width_px"]),
        )
        arrow_bbox = _arrow_bbox(
            arrow_start,
            arrow_end,
            padding_px=float(render_defaults["option_arrow_head_width_px"]),
        )
        option_bbox = _bbox_union(letter_bbox, arrow_bbox)
        option_bboxes[str(letter)] = list(option_bbox)
        scene_entities.append(
            {
                "entity_id": f"option_{str(letter)}",
                "entity_type": "candidate_resultant_arrow",
                "bbox_px": list(option_bbox),
                "meta": {
                    "option_letter": str(letter),
                    "angle_degrees": float(scene_spec.option_angles_degrees[str(letter)]),
                    "is_correct": str(letter) == str(scene_spec.correct_option_letter),
                },
            }
        )

    entity_bbox_map = {
        str(entity["entity_id"]): list(entity["bbox_px"])
        for entity in scene_entities
        if entity.get("bbox_px") is not None
    }
    entity_point_map = {
        str(entity["entity_id"]): list(entity["point_px"])
        for entity in scene_entities
        if entity.get("point_px") is not None
    }
    annotation_points = [
        list(entity_point_map[entity_id])
        for entity_id in scene_spec.annotation_entity_ids
        if str(entity_id) in entity_point_map
    ]
    annotation_point_map = {
        ANNOTATION_ENTITY_KEY_BY_ID[str(entity_id)]: list(entity_point_map[str(entity_id)])
        for entity_id in scene_spec.annotation_entity_ids
        if str(entity_id) in entity_point_map
    }
    render_map = {
        "accent_color_name": str(accent_color_name),
        "technical_diagram_frame_mode": str(getattr(diagram_style, "frame_mode", "none")),
        "table_bbox_px": [round(float(value), 3) for value in table_bbox],
        "collision_center_px": [round(float(center_x), 3), round(float(center_y), 3)],
        "horizontal_puck_bbox_px": list(horizontal_puck_bbox),
        "horizontal_puck_center_px": [round(float(horizontal_center[0]), 3), round(float(horizontal_center[1]), 3)],
        "vertical_puck_bbox_px": list(vertical_puck_bbox),
        "vertical_puck_center_px": [round(float(vertical_center[0]), 3), round(float(vertical_center[1]), 3)],
        "stuck_pucks_bbox_px": list(stuck_bbox),
        "stuck_pucks_center_px": [round(float(collision_center[0]), 3), round(float(collision_center[1]), 3)],
        "horizontal_motion_arrow_bbox_px": list(horizontal_arrow_bbox),
        "vertical_motion_arrow_bbox_px": list(vertical_arrow_bbox),
        "horizontal_component_witness_bbox_px": list(horizontal_component_witness_bbox),
        "vertical_component_witness_bbox_px": list(vertical_component_witness_bbox),
        "direction_angle_degrees": round(float(final_angle), 3),
        "direction_label": str(scene_spec.direction_label),
        "option_bboxes_px": {str(letter): list(bbox) for letter, bbox in option_bboxes.items()},
        "option_angles_degrees": dict(scene_spec.option_angles_degrees),
        "correct_option_letter": str(scene_spec.correct_option_letter),
        "annotation_entity_ids": list(scene_spec.annotation_entity_ids),
        "annotation_key_by_entity_id": dict(ANNOTATION_ENTITY_KEY_BY_ID),
        "entity_points_px": {str(key): list(value) for key, value in entity_point_map.items()},
        "annotation_points_px": [list(point) for point in annotation_points],
        "annotation_keyed_points_px": {str(key): list(value) for key, value in annotation_point_map.items()},
    }
    return _RenderedScene(
        image=image,
        annotation_points=[list(point) for point in annotation_points],
        annotation_point_map={str(key): list(value) for key, value in annotation_point_map.items()},
        annotation_entity_ids=list(scene_spec.annotation_entity_ids),
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
    )


def _resolve_collision_layout_placement(
    *,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    canvas_width: int,
    canvas_height: int,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve a whole-diagram offset before rendering and annotation projection."""

    content_left = min(float(render_defaults["table_left_px"]), float(render_defaults["option_cell_left_px"]))
    content_top = min(float(render_defaults["table_top_px"]), float(render_defaults["option_panel_top_px"]))
    content_right = max(
        float(render_defaults["table_left_px"]) + float(render_defaults["table_width_px"]),
        float(render_defaults["option_cell_left_px"]) + (float(render_defaults["option_cell_width_px"]) * len(OPTION_LETTERS)),
    )
    content_bottom = max(
        float(render_defaults["table_top_px"]) + float(render_defaults["table_height_px"]),
        float(render_defaults["option_panel_top_px"]) + 144.0,
    )
    base_bbox = [round(content_left, 3), round(content_top, 3), round(content_right, 3), round(content_bottom, 3)]
    jitter = resolve_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.collision_layout",
    )
    min_margin = int(jitter.get("min_margin_px", 24))
    requested_dx = int(jitter.get("requested_dx_px", 0))
    requested_dy = int(jitter.get("requested_dy_px", 0))
    min_dx = int(math.ceil(float(min_margin) - float(content_left)))
    max_dx = int(math.floor(float(canvas_width) - float(min_margin) - float(content_right)))
    min_dy = int(math.ceil(float(min_margin) - float(content_top)))
    max_dy = int(math.floor(float(canvas_height) - float(min_margin) - float(content_bottom)))
    if int(min_dx) > int(max_dx):
        min_dx = 0
        max_dx = 0
    if int(min_dy) > int(max_dy):
        min_dy = 0
        max_dy = 0
    if not bool(jitter.get("enabled", False)):
        requested_dx = 0
        requested_dy = 0
    dx = max(int(min_dx), min(int(max_dx), int(requested_dx)))
    dy = max(int(min_dy), min(int(max_dy), int(requested_dy)))

    adjusted = dict(render_defaults)
    for key in ("table_left_px", "collision_center_x_px", "compact_collision_center_x_px", "option_cell_left_px"):
        adjusted[key] = int(adjusted[key]) + int(dx)
    for key in ("table_top_px", "collision_center_y_px", "compact_collision_center_y_px", "option_panel_top_px"):
        adjusted[key] = int(adjusted[key]) + int(dy)

    final_bbox = [
        round(float(content_left) + float(dx), 3),
        round(float(content_top) + float(dy), 3),
        round(float(content_right) + float(dx), 3),
        round(float(content_bottom) + float(dy), 3),
    ]
    placement = dict(jitter)
    placement.update(
        {
            "mode": "whole_collision_diagram_offset",
            "content_bbox_px": base_bbox,
            "final_content_bbox_px": final_bbox,
            "canvas_size_px": [int(canvas_width), int(canvas_height)],
            "available_offset_x_px": [int(min_dx), int(max_dx)],
            "available_offset_y_px": [int(min_dy), int(max_dy)],
            "sampled_offset_px": [int(requested_dx), int(requested_dy)],
            "final_offset_px": [int(dx), int(dy)],
            "dx_px": int(dx),
            "dy_px": int(dy),
        }
    )
    return adjusted, placement


def _answer_type(query_id: str) -> str:
    """Return answer type for the public query."""

    if str(query_id) == "direction_choice":
        return "option_letter"
    return "integer"


def _build_prompt_examples(query_id: str) -> Tuple[str, str]:
    """Return one stable prompt JSON example for the active collision query."""

    if str(query_id) == "direction_choice":
        return build_prompt_json_examples(
            annotation_value={
                "A": [170, 304],
                "B": [436, 152],
                "A+B": [436, 304],
            },
            answer_type="option_letter",
        )
    return build_prompt_json_examples(
        annotation_value={
            "A": [170, 304],
            "B": [436, 152],
            "A+B": [436, 304],
        },
        answer_type="integer",
    )


class _PhysicsMechanicsStickyCollisionBaseTask:
    """Return one perpendicular sticky-collision question."""

    task_id = TASK_ID
    domain = "physics"
    scene_id = "mechanics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        rendered_scene: _RenderedScene | None = None
        scene_spec: _SceneSpec | None = None

        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                scene_spec = _sample_scene_spec(
                    attempt_rng,
                    scene_variant=str(axes.scene_variant),
                    query_id=str(axes.query_id),
                    component_axis=axes.component_axis,
                    target_answer=axes.target_answer,
                    correct_option_letter=str(axes.correct_option_letter),
                    params=params,
                )
            except ValueError:
                continue

            canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
            canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                scene_id="collision",
                canvas_width=int(canvas_width),
                canvas_height=int(canvas_height),
                instance_seed=int(instance_seed),
                params=params,
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.render.font",
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
                    namespace=TASK_ID,
                )
                for key in (
                    "table_left_px",
                    "table_top_px",
                    "table_width_px",
                    "table_height_px",
                    "table_corner_radius_px",
                    "collision_center_x_px",
                    "collision_center_y_px",
                    "compact_collision_center_x_px",
                    "compact_collision_center_y_px",
                    "horizontal_start_distance_px",
                    "vertical_start_distance_px",
                    "compact_start_distance_delta_px",
                    "puck_radius_px",
                    "stuck_radius_px",
                    "motion_arrow_width_px",
                    "final_arrow_width_px",
                    "arrow_head_length_px",
                    "arrow_head_width_px",
                    "label_font_size_px",
                    "puck_font_size_px",
                    "option_font_size_px",
                    "label_stroke_width_px",
                    "option_panel_top_px",
                    "option_cell_left_px",
                    "option_cell_width_px",
                    "option_arrow_length_px",
                    "option_arrow_width_px",
                    "option_arrow_head_length_px",
                    "option_arrow_head_width_px",
                    "grid_spacing_px",
                )
            }
            render_defaults, layout_placement_meta = _resolve_collision_layout_placement(
                render_defaults=render_defaults,
                params=params,
                instance_seed=int(instance_seed),
                canvas_width=int(canvas_width),
                canvas_height=int(canvas_height),
            )
            rendered_scene = _render_scene(
                background=background,
                render_defaults=render_defaults,
                accent_color_name=str(axes.accent_color_name),
                scene_spec=scene_spec,
                font_family=str(font_family),
                diagram_style=diagram_style,
            )
            image, post_noise_meta = apply_post_image_noise(
                rendered_scene.image,
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
                    "object_description_wide_table",
                    "object_description_compact_table",
                    "object_description_gridded_table",
                    "answer_hint_direction_choice",
                    "answer_hint_component",
                    "annotation_hint_direction_choice",
                    "annotation_hint_velocity_component",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            json_example, json_example_answer_only = _build_prompt_examples(str(axes.query_id))
            answer_hint_key = (
                "answer_hint_direction_choice"
                if str(axes.query_id) == "direction_choice"
                else "answer_hint_component"
            )
            component_axis_label = _component_axis_label(axes.component_axis)
            positive_direction = "right" if str(axes.component_axis) == "x" else "up"
            negative_direction = "left" if str(axes.component_axis) == "x" else "down"
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                scene_id=self.scene_id,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(axes.query_id),
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "answer_hint": str(prompt_defaults[answer_hint_key]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                    "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                    "component_axis": str(component_axis_label),
                    "positive_direction": str(positive_direction),
                    "negative_direction": str(negative_direction),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_type = _answer_type(str(axes.query_id))
            answer_value: int | str
            if str(axes.query_id) == "direction_choice":
                answer_value = str(scene_spec.correct_option_letter)
            elif str(axes.component_axis) == "x":
                answer_value = int(scene_spec.scenario.final_vx)
            else:
                answer_value = int(scene_spec.scenario.final_vy)
            answer_gt = TypedValue(type=str(answer_type), value=answer_value)
            annotation_gt = TypedValue(
                type="keyed_point_map",
                value={str(key): list(point) for key, point in rendered_scene.annotation_point_map.items()},
            )
            scenario_payload = {
                "horizontal_mass": int(scene_spec.scenario.horizontal_mass),
                "vertical_mass": int(scene_spec.scenario.vertical_mass),
                "horizontal_speed": int(scene_spec.scenario.horizontal_speed),
                "vertical_speed": int(scene_spec.scenario.vertical_speed),
                "horizontal_direction": "right" if int(scene_spec.scenario.horizontal_sign) > 0 else "left",
                "vertical_direction": "up" if int(scene_spec.scenario.vertical_sign) > 0 else "down",
                "horizontal_momentum": int(scene_spec.scenario.horizontal_mass * scene_spec.scenario.horizontal_speed * scene_spec.scenario.horizontal_sign),
                "vertical_momentum": int(scene_spec.scenario.vertical_mass * scene_spec.scenario.vertical_speed * scene_spec.scenario.vertical_sign),
                "total_mass": int(scene_spec.scenario.total_mass),
                "final_vx": int(scene_spec.scenario.final_vx),
                "final_vy": int(scene_spec.scenario.final_vy),
                "direction_angle_degrees": float(rendered_scene.render_map["option_angles_degrees"][str(scene_spec.correct_option_letter)]),
                "direction_label": str(scene_spec.direction_label),
                "correct_option_letter": str(scene_spec.correct_option_letter),
                "option_angles_degrees": dict(scene_spec.option_angles_degrees),
                "component_axis": axes.component_axis,
                "component_axis_label": str(component_axis_label) if str(axes.query_id) == "velocity_component" else None,
            }
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_sticky_collision_{str(axes.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.query_id),
                        "component_axis": axes.component_axis,
                        "accent_color_name": str(axes.accent_color_name),
                        "target_answer": answer_value,
                        "answer_type": str(answer_type),
                        "scenario": dict(scenario_payload),
                        "annotation_entity_ids": list(rendered_scene.annotation_entity_ids),
                        "annotation_key_by_entity_id": dict(ANNOTATION_ENTITY_KEY_BY_ID),
                    },
                },
                "query_spec": {
                    "query_id": str(axes.query_id),
                    "component_axis": axes.component_axis,
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.query_id),
                        "component_axis": axes.component_axis,
                        "accent_color_name": str(axes.accent_color_name),
                        "correct_option_letter": str(axes.correct_option_letter),
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_id_probabilities": dict(axes.query_id_probabilities),
                        "component_axis_probabilities": dict(axes.component_axis_probabilities),
                        "accent_color_name_probabilities": dict(axes.accent_color_name_probabilities),
                        "target_answer": answer_value,
                        "target_answer_probabilities": dict(axes.target_answer_probabilities),
                        "correct_option_letter_probabilities": dict(axes.correct_option_letter_probabilities),
                    },
                },
                "render_spec": {
                    "scene_variant": str(axes.scene_variant),
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "accent_color_name": str(axes.accent_color_name),
                    "font": {
                        "font_family": str(font_family),
                        "font_asset_version": font_asset_version(),
                        "font_asset": font_record.to_trace(),
                        "scope": "collision_diagram",
                        "selection_policy": {
                            "pool": "global_approved_font_pool",
                            "include_tags": [],
                            "exclude_tags": [],
                            "exclusion_reason": "",
                        },
                    },
                    "technical_diagram_style": dict(diagram_style_meta),
                    "background_style": background_meta,
                    "layout_placement": dict(layout_placement_meta),
                    "post_image_noise": post_noise_meta,
                },
                "render_map": dict(rendered_scene.render_map),
                "execution_trace": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "component_axis": axes.component_axis,
                    "component_axis_probabilities": dict(axes.component_axis_probabilities),
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": answer_value,
                    "answer_type": str(answer_type),
                    "component_answer_support": list(_component_support(params)),
                    "mass_support": list(_mass_support(params)),
                    "speed_support": list(_speed_support(params)),
                    "option_letters": list(OPTION_LETTERS),
                    "scenario": dict(scenario_payload),
                    "horizontal_mass": int(scene_spec.scenario.horizontal_mass),
                    "vertical_mass": int(scene_spec.scenario.vertical_mass),
                    "horizontal_speed": int(scene_spec.scenario.horizontal_speed),
                    "vertical_speed": int(scene_spec.scenario.vertical_speed),
                    "total_mass": int(scene_spec.scenario.total_mass),
                    "final_vx": int(scene_spec.scenario.final_vx),
                    "final_vy": int(scene_spec.scenario.final_vy),
                    "correct_option_letter": str(scene_spec.correct_option_letter),
                    "direction_label": str(scene_spec.direction_label),
                    "annotation_entity_ids": list(rendered_scene.annotation_entity_ids),
                    "annotation_key_by_entity_id": dict(ANNOTATION_ENTITY_KEY_BY_ID),
                },
                "witness_symbolic": {
                    "type": "object_key_map",
                    "ids": [str(item) for item in rendered_scene.annotation_entity_ids],
                    "keys": dict(ANNOTATION_ENTITY_KEY_BY_ID),
                },
                "projected_annotation": {
                    "type": "keyed_point_map",
                    "keyed_point_map": {
                        str(key): list(point) for key, point in rendered_scene.annotation_point_map.items()
                    },
                    "pixel_keyed_point_map": {
                        str(key): list(point) for key, point in rendered_scene.annotation_point_map.items()
                    },
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
                query_id=str(axes.query_id),
                scene_id="collision",
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")


@register_task
class PhysicsMechanicsStickyCollisionDirectionChoiceTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsMechanicsStickyCollisionBaseTask,
):
    """Choose the candidate arrow showing the post-collision direction."""

    task_id = "task_physics__collision__sticky_collision_direction_choice"
    fixed_query_id = "direction_choice"


@register_task
class PhysicsMechanicsStickyCollisionVelocityComponentValueTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsMechanicsStickyCollisionBaseTask,
):
    """Return one signed final velocity component after sticking."""

    task_id = "task_physics__collision__sticky_collision_velocity_component_value"
    fixed_query_id = "velocity_component"


__all__ = [
    "PhysicsMechanicsStickyCollisionDirectionChoiceTask",
    "PhysicsMechanicsStickyCollisionVelocityComponentValueTask",
]
