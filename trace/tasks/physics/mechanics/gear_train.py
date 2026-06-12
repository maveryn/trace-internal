"""Physics mechanics task for gear-train rotation direction."""

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
from ...shared.bbox_projection import bbox_union_many as _bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_arrow, draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import resolve_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.support_sampling import resolve_integer_support
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "task_physics__gear_train__output_direction_label"
TASK_NAMESPACE = "physics_mechanics_gear_train"
SPEED_TASK_ID = "task_physics__gear_train__output_speed_value"
SPEED_TASK_NAMESPACE = "physics_mechanics_gear_train_speed"
SCENE_ID = "gear_train"
QUERY_ID = "marked_output_direction"
SPEED_QUERY_ID = "simple_gear_ratio_output_speed"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("straight_chain", "staggered_chain", "arc_chain")
SUPPORTED_DIRECTIONS: Tuple[str, ...] = ("clockwise", "counterclockwise")
SUPPORTED_SPEED_RELATIONS: Tuple[str, ...] = ("faster", "slower")

POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="mechanics", apply_prob=0.5)
_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "mechanics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_NAMESPACE,
)
_SPEED_GEN_DEFAULTS, _SPEED_RENDER_DEFAULTS, _SPEED_PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=SPEED_TASK_NAMESPACE,
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for gear-train diagrams."""

    canvas_width: int = 1040
    canvas_height: int = 680
    panel_margin_x_px: int = 54
    panel_margin_top_px: int = 52
    panel_margin_bottom_px: int = 58
    gear_count_support: Tuple[int, ...] = (2, 3, 4, 5, 6)
    gear_radius_px_support: Tuple[int, ...] = (42, 48, 54, 60)
    label_font_size_px: int = 23
    title_font_size_px: int = 27
    tooth_count_support: Tuple[int, ...] = (12, 16, 18, 20, 24, 30, 36, 40, 48)
    input_rpm_support: Tuple[int, ...] = (30, 40, 45, 60, 72, 80, 90, 100, 120, 144, 150, 180)


@dataclass(frozen=True)
class _GearScenario:
    """Resolved symbolic gear-train scenario."""

    scene_variant: str
    gear_count: int
    input_direction: str
    output_direction: str
    radii_px: Tuple[float, ...]
    scene_variant_probabilities: Dict[str, float]
    gear_count_probabilities: Dict[str, float]
    input_direction_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _GearSpeedScenario:
    """Resolved symbolic gear-speed scenario."""

    scene_variant: str
    gear_count: int
    input_teeth: int
    output_teeth: int
    idler_teeth: Tuple[int, ...]
    input_rpm: int
    output_rpm: int
    speed_relation: str
    radii_px: Tuple[float, ...]
    scene_variant_probabilities: Dict[str, float]
    gear_count_probabilities: Dict[str, float]
    speed_relation_probabilities: Dict[str, float]
    input_rpm_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered gear-train scene and projected annotation."""

    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _clamp_bbox(bbox: Sequence[float], *, width: int, height: int) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in bbox[:4]]
    return _bbox(
        (
            max(0.0, min(float(width - 1), min(x0, x1))),
            max(0.0, min(float(height - 1), min(y0, y1))),
            max(1.0, min(float(width), max(x0, x1))),
            max(1.0, min(float(height), max(y0, y1))),
        )
    )


def _normalize_direction(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "cw": "clockwise",
        "clockwise": "clockwise",
        "counterclockwise": "counterclockwise",
        "counter_clockwise": "counterclockwise",
        "ccw": "counterclockwise",
        "anticlockwise": "counterclockwise",
        "anti_clockwise": "counterclockwise",
    }
    if text not in aliases:
        raise ValueError(f"unsupported gear rotation direction for {TASK_ID}: {value}")
    return str(aliases[text])


def _opposite_direction(direction: str) -> str:
    return "counterclockwise" if str(direction) == "clockwise" else "clockwise"


def _propagate_output_direction(input_direction: str, gear_count: int) -> str:
    return str(input_direction) if (int(gear_count) - 1) % 2 == 0 else _opposite_direction(str(input_direction))


def _probability_map(values: Sequence[str], selected: str | None = None) -> Dict[str, float]:
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in values}
    probability = 1.0 / float(len(values)) if values else 0.0
    return {str(value): float(probability) for value in values}


def _integer_probability_map(values: Sequence[int], selected: int | None = None) -> Dict[str, float]:
    if selected is not None:
        return {str(int(value)): (1.0 if int(value) == int(selected) else 0.0) for value in values}
    probability = 1.0 / float(len(values)) if values else 0.0
    return {str(int(value)): float(probability) for value in values}


def _integer_support(
    params: Mapping[str, Any],
    key: str,
    fallback: Sequence[int],
    *,
    gen_defaults: Mapping[str, Any] | None = None,
    task_id: str = TASK_ID,
) -> Tuple[int, ...]:
    support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS if gen_defaults is None else gen_defaults,
        key=str(key),
        fallback=fallback,
    )
    if not support:
        raise ValueError(f"{key} must not be empty for {task_id}")
    return tuple(int(value) for value in support)


def _resolve_scene_variant(
    instance_seed: int,
    params: Mapping[str, Any],
    *,
    task_namespace: str = TASK_NAMESPACE,
    gen_defaults: Mapping[str, Any] | None = None,
) -> Tuple[str, Dict[str, float]]:
    resolved_defaults = _GEN_DEFAULTS if gen_defaults is None else gen_defaults
    rng = spawn_rng(int(instance_seed), f"{task_namespace}.scene_variant")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=resolved_defaults,
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=resolved_defaults,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_SCENE_VARIANTS,
        balance_flag_key="balanced_scene_variant_sampling",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        sampling_namespace=f"{task_namespace}.scene_variant",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_gear_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    input_direction: str | None,
    target_answer: str | None,
) -> Tuple[int, Dict[str, float]]:
    support = _integer_support(params, "gear_count_support", _DEFAULTS.gear_count_support)
    support = tuple(int(value) for value in support if 2 <= int(value) <= 6)
    if not support:
        raise ValueError(f"gear_count_support for {TASK_ID} must include values in 2..6")
    explicit = params.get("gear_count")
    if explicit is not None:
        gear_count = int(explicit)
        if int(gear_count) not in set(support):
            raise ValueError(f"unsupported gear_count for {TASK_ID}: {gear_count}")
        return int(gear_count), _integer_probability_map(support, selected=int(gear_count))

    candidates = list(support)
    if input_direction is not None and target_answer is not None:
        candidates = [
            int(value)
            for value in candidates
            if _propagate_output_direction(str(input_direction), int(value)) == str(target_answer)
        ]
        if not candidates:
            raise ValueError("explicit input_direction and target_answer are incompatible with gear_count_support")

    if bool(params.get("balanced_gear_count_sampling", group_default(_GEN_DEFAULTS, "balanced_gear_count_sampling", True))):
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_NAMESPACE}.gear_count",
        )
        gear_count = int(candidates[int(index) % len(candidates)])
    else:
        rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.gear_count")
        gear_count = int(candidates[int(rng.randrange(len(candidates)))])
    return int(gear_count), _integer_probability_map(support)


def _resolve_scenario(instance_seed: int, params: Mapping[str, Any]) -> _GearScenario:
    query_id = str(params.get("query_id", QUERY_ID))
    if query_id != QUERY_ID:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {query_id}")

    scene_variant, scene_variant_probabilities = _resolve_scene_variant(int(instance_seed), params)
    explicit_input = _normalize_direction(params.get("input_direction"))
    explicit_target = _normalize_direction(params.get("target_answer", params.get("output_direction")))
    gear_count, gear_count_probabilities = _resolve_gear_count(
        instance_seed=int(instance_seed),
        params=params,
        input_direction=explicit_input,
        target_answer=explicit_target,
    )

    if explicit_input is not None:
        input_direction = str(explicit_input)
    elif explicit_target is not None:
        input_direction = str(explicit_target) if (int(gear_count) - 1) % 2 == 0 else _opposite_direction(str(explicit_target))
    elif bool(params.get("balanced_target_answer_sampling", group_default(_GEN_DEFAULTS, "balanced_target_answer_sampling", True))):
        answer_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_NAMESPACE}.target_answer",
        )
        selected_target = str(SUPPORTED_DIRECTIONS[int(answer_index) % len(SUPPORTED_DIRECTIONS)])
        input_direction = str(selected_target) if (int(gear_count) - 1) % 2 == 0 else _opposite_direction(str(selected_target))
    else:
        direction_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_NAMESPACE}.input_direction",
        )
        input_direction = str(SUPPORTED_DIRECTIONS[int(direction_index) % len(SUPPORTED_DIRECTIONS)])

    output_direction = _propagate_output_direction(str(input_direction), int(gear_count))
    if explicit_target is not None and str(output_direction) != str(explicit_target):
        raise ValueError("explicit gear train parameters do not produce the requested output direction")

    radius_support = _integer_support(params, "gear_radius_px_support", _DEFAULTS.gear_radius_px_support)
    radius_rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.radii")
    radii = tuple(float(radius_rng.choice(radius_support)) for _ in range(int(gear_count)))

    return _GearScenario(
        scene_variant=str(scene_variant),
        gear_count=int(gear_count),
        input_direction=str(input_direction),
        output_direction=str(output_direction),
        radii_px=tuple(float(value) for value in radii),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        gear_count_probabilities=dict(gear_count_probabilities),
        input_direction_probabilities=_probability_map(SUPPORTED_DIRECTIONS, selected=explicit_input),
        target_answer_probabilities=_probability_map(SUPPORTED_DIRECTIONS, selected=explicit_target),
    )


def _speed_relation(input_rpm: int, output_rpm: int) -> str:
    if int(output_rpm) == int(input_rpm):
        return "same"
    return "faster" if int(output_rpm) > int(input_rpm) else "slower"


def _radius_from_teeth(teeth: int) -> float:
    return float(34.0 + 0.72 * float(teeth))


def _feasible_speed_scenarios(params: Mapping[str, Any]) -> Tuple[Tuple[int, int, int, int, int, str], ...]:
    gear_counts = tuple(value for value in _integer_support(
        params,
        "gear_count_support",
        (2, 3, 4),
        gen_defaults=_SPEED_GEN_DEFAULTS,
        task_id=SPEED_TASK_ID,
    ) if 2 <= int(value) <= 4)
    if not gear_counts:
        raise ValueError(f"gear_count_support for {SPEED_TASK_ID} must include values in 2..4")
    teeth_support = _integer_support(
        params,
        "tooth_count_support",
        _DEFAULTS.tooth_count_support,
        gen_defaults=_SPEED_GEN_DEFAULTS,
        task_id=SPEED_TASK_ID,
    )
    input_rpm_support = _integer_support(
        params,
        "input_rpm_support",
        _DEFAULTS.input_rpm_support,
        gen_defaults=_SPEED_GEN_DEFAULTS,
        task_id=SPEED_TASK_ID,
    )
    min_output = int(params.get("output_rpm_min", group_default(_SPEED_GEN_DEFAULTS, "output_rpm_min", 20)))
    max_output = int(params.get("output_rpm_max", group_default(_SPEED_GEN_DEFAULTS, "output_rpm_max", 240)))
    scenarios: List[Tuple[int, int, int, int, int, str]] = []
    for gear_count in gear_counts:
        for input_teeth in teeth_support:
            for output_teeth in teeth_support:
                if int(input_teeth) == int(output_teeth):
                    continue
                for input_rpm in input_rpm_support:
                    numerator = int(input_rpm) * int(input_teeth)
                    if numerator % int(output_teeth) != 0:
                        continue
                    output_rpm = int(numerator // int(output_teeth))
                    relation = _speed_relation(int(input_rpm), int(output_rpm))
                    if relation not in SUPPORTED_SPEED_RELATIONS:
                        continue
                    if not (int(min_output) <= int(output_rpm) <= int(max_output)):
                        continue
                    scenarios.append(
                        (
                            int(gear_count),
                            int(input_teeth),
                            int(output_teeth),
                            int(input_rpm),
                            int(output_rpm),
                            str(relation),
                        )
                    )
    if not scenarios:
        raise ValueError("no feasible gear-train speed scenarios for configured supports")
    return tuple(scenarios)


def _normalize_speed_relation(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "faster": "faster",
        "speed_up": "faster",
        "higher": "faster",
        "slower": "slower",
        "speed_down": "slower",
        "lower": "slower",
    }
    if text not in aliases:
        raise ValueError(f"unsupported speed_relation for {SPEED_TASK_ID}: {value}")
    return str(aliases[text])


def _resolve_speed_scenario(instance_seed: int, params: Mapping[str, Any]) -> _GearSpeedScenario:
    query_id = str(params.get("query_id", SPEED_QUERY_ID))
    if query_id != SPEED_QUERY_ID:
        raise ValueError(f"unsupported query_id for {SPEED_TASK_ID}: {query_id}")

    scene_variant, scene_variant_probabilities = _resolve_scene_variant(
        int(instance_seed),
        params,
        task_namespace=SPEED_TASK_NAMESPACE,
        gen_defaults=_SPEED_GEN_DEFAULTS,
    )
    feasible = list(_feasible_speed_scenarios(params))
    gear_count_support = tuple(value for value in _integer_support(
        params,
        "gear_count_support",
        (2, 3, 4),
        gen_defaults=_SPEED_GEN_DEFAULTS,
        task_id=SPEED_TASK_ID,
    ) if 2 <= int(value) <= 4)
    input_rpm_support = _integer_support(
        params,
        "input_rpm_support",
        _DEFAULTS.input_rpm_support,
        gen_defaults=_SPEED_GEN_DEFAULTS,
        task_id=SPEED_TASK_ID,
    )

    explicit_gear_count = params.get("gear_count")
    explicit_input_teeth = params.get("input_teeth", params.get("input_tooth_count"))
    explicit_output_teeth = params.get("output_teeth", params.get("output_tooth_count"))
    explicit_input_rpm = params.get("input_rpm", params.get("input_speed_rpm"))
    explicit_answer = params.get("target_answer", params.get("output_rpm"))
    explicit_relation = _normalize_speed_relation(params.get("speed_relation"))

    candidates = list(feasible)
    if explicit_gear_count is not None:
        candidates = [item for item in candidates if int(item[0]) == int(explicit_gear_count)]
    if explicit_input_teeth is not None:
        candidates = [item for item in candidates if int(item[1]) == int(explicit_input_teeth)]
    if explicit_output_teeth is not None:
        candidates = [item for item in candidates if int(item[2]) == int(explicit_output_teeth)]
    if explicit_input_rpm is not None:
        candidates = [item for item in candidates if int(item[3]) == int(explicit_input_rpm)]
    if explicit_answer is not None:
        candidates = [item for item in candidates if int(item[4]) == int(explicit_answer)]
    if explicit_relation is not None:
        candidates = [item for item in candidates if str(item[5]) == str(explicit_relation)]
    if not candidates:
        raise ValueError("explicit gear-train speed parameters do not define a feasible ratio scenario")

    if explicit_relation is None and bool(
        params.get("balanced_speed_relation_sampling", group_default(_SPEED_GEN_DEFAULTS, "balanced_speed_relation_sampling", True))
    ):
        relations = [relation for relation in SUPPORTED_SPEED_RELATIONS if any(str(item[5]) == relation for item in candidates)]
        relation_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SPEED_TASK_NAMESPACE}.speed_relation",
        )
        selected_relation = str(relations[int(relation_index) % len(relations)])
        candidates = [item for item in candidates if str(item[5]) == selected_relation]

    if explicit_answer is None and bool(
        params.get("balanced_target_answer_sampling", group_default(_SPEED_GEN_DEFAULTS, "balanced_target_answer_sampling", True))
    ):
        answers = sorted({int(item[4]) for item in candidates})
        answer_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{SPEED_TASK_NAMESPACE}.target_answer",
        )
        selected_answer = int(answers[int(answer_index) % len(answers)])
        candidates = [item for item in candidates if int(item[4]) == int(selected_answer)]

    tuple_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SPEED_TASK_NAMESPACE}.scenario_tuple",
    )
    gear_count, input_teeth, output_teeth, input_rpm, output_rpm, relation = candidates[int(tuple_index) % len(candidates)]
    teeth_support = _integer_support(
        params,
        "tooth_count_support",
        _DEFAULTS.tooth_count_support,
        gen_defaults=_SPEED_GEN_DEFAULTS,
        task_id=SPEED_TASK_ID,
    )
    idler_rng = spawn_rng(int(instance_seed), f"{SPEED_TASK_NAMESPACE}.idler_teeth")
    idler_teeth = tuple(int(idler_rng.choice(teeth_support)) for _ in range(max(0, int(gear_count) - 2)))
    all_teeth = (int(input_teeth),) + idler_teeth + (int(output_teeth),)
    radii = tuple(_radius_from_teeth(value) for value in all_teeth)

    return _GearSpeedScenario(
        scene_variant=str(scene_variant),
        gear_count=int(gear_count),
        input_teeth=int(input_teeth),
        output_teeth=int(output_teeth),
        idler_teeth=tuple(int(value) for value in idler_teeth),
        input_rpm=int(input_rpm),
        output_rpm=int(output_rpm),
        speed_relation=str(relation),
        radii_px=tuple(float(value) for value in radii),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        gear_count_probabilities=_integer_probability_map(gear_count_support, selected=int(gear_count) if explicit_gear_count is not None else None),
        speed_relation_probabilities=_probability_map(SUPPORTED_SPEED_RELATIONS, selected=explicit_relation),
        input_rpm_probabilities=_integer_probability_map(input_rpm_support, selected=int(input_rpm) if explicit_input_rpm is not None else None),
        target_answer_probabilities=_integer_probability_map(
            sorted({int(item[4]) for item in feasible}),
            selected=int(output_rpm) if explicit_answer is not None else None,
        ),
    )


def _layout_centers(
    *,
    scenario: _GearScenario | _GearSpeedScenario,
    panel: Sequence[float],
    instance_seed: int,
    task_namespace: str = TASK_NAMESPACE,
) -> Tuple[Tuple[Tuple[float, float], ...], Tuple[float, ...]]:
    radii = [float(value) for value in scenario.radii_px]
    coords: List[Tuple[float, float]] = [(0.0, 0.0)]
    rng = spawn_rng(int(instance_seed), f"{task_namespace}.layout")
    if str(scenario.scene_variant) == "straight_chain":
        segment_angles = [0.0 for _ in range(max(0, int(scenario.gear_count) - 1))]
    elif str(scenario.scene_variant) == "staggered_chain":
        sign = -1.0 if int(hash64(int(instance_seed), f"{task_namespace}.stagger_sign", 0) % 2) else 1.0
        segment_angles = [math.radians(sign * (24.0 if index % 2 == 0 else -24.0)) for index in range(max(0, int(scenario.gear_count) - 1))]
    else:
        reverse = -1.0 if int(hash64(int(instance_seed), f"{task_namespace}.arc_sign", 0) % 2) else 1.0
        count = max(1, int(scenario.gear_count) - 1)
        if count == 1:
            segment_angles = [math.radians(reverse * rng.choice([-18.0, 18.0]))]
        else:
            segment_angles = [
                math.radians(reverse * (-28.0 + 56.0 * float(index) / float(count - 1)))
                for index in range(count)
            ]
    for index, angle in enumerate(segment_angles):
        distance = float(radii[index] + radii[index + 1] + 1.5)
        last_x, last_y = coords[-1]
        coords.append((float(last_x + distance * math.cos(angle)), float(last_y + distance * math.sin(angle))))

    min_x = min(x - radius for (x, _), radius in zip(coords, radii))
    max_x = max(x + radius for (x, _), radius in zip(coords, radii))
    min_y = min(y - radius for (_, y), radius in zip(coords, radii))
    max_y = max(y + radius for (_, y), radius in zip(coords, radii))
    available_w = float(panel[2] - panel[0] - 126.0)
    available_h = float(panel[3] - panel[1] - 142.0)
    raw_w = max(1.0, float(max_x - min_x))
    raw_h = max(1.0, float(max_y - min_y))
    scale = min(1.0, float(available_w / raw_w), float(available_h / raw_h))
    scaled_radii = tuple(float(radius * scale) for radius in radii)
    scaled = [(float(x * scale), float(y * scale)) for x, y in coords]
    min_x = min(x - radius for (x, _), radius in zip(scaled, scaled_radii))
    max_x = max(x + radius for (x, _), radius in zip(scaled, scaled_radii))
    min_y = min(y - radius for (_, y), radius in zip(scaled, scaled_radii))
    max_y = max(y + radius for (_, y), radius in zip(scaled, scaled_radii))
    target_cx = float((panel[0] + panel[2]) * 0.5)
    target_cy = float((panel[1] + panel[3]) * 0.54)
    shift_x = float(target_cx - 0.5 * (min_x + max_x))
    shift_y = float(target_cy - 0.5 * (min_y + max_y))
    centers = tuple((float(x + shift_x), float(y + shift_y)) for x, y in scaled)
    return centers, scaled_radii


def _gear_polygon(center: Tuple[float, float], radius: float, teeth: int) -> List[Tuple[float, float]]:
    points: List[Tuple[float, float]] = []
    cx, cy = float(center[0]), float(center[1])
    for index in range(int(teeth) * 2):
        angle = -math.pi / 2.0 + float(index) * math.pi / float(teeth)
        local_radius = float(radius * (1.12 if index % 2 == 0 else 0.94))
        points.append((float(cx + local_radius * math.cos(angle)), float(cy + local_radius * math.sin(angle))))
    return points


def _draw_gear(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    radius: float,
    fill_rgb: Tuple[int, int, int],
    style: Any,
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    teeth = max(12, min(24, int(round(float(radius) / 3.0))))
    stroke = tuple(int(v) for v in style.stroke_rgb)
    polygon = _gear_polygon(center, float(radius), int(teeth))
    draw.polygon(polygon, fill=tuple(int(v) for v in fill_rgb), outline=stroke)
    draw.line(polygon + [polygon[0]], fill=stroke, width=3)
    inner_radius = float(radius * 0.54)
    hub_radius = float(radius * 0.20)
    for angle_index in range(6):
        angle = float(angle_index) * math.tau / 6.0
        start = (float(cx + hub_radius * math.cos(angle)), float(cy + hub_radius * math.sin(angle)))
        end = (float(cx + inner_radius * math.cos(angle)), float(cy + inner_radius * math.sin(angle)))
        draw.line([start, end], fill=stroke, width=max(2, int(radius * 0.055)))
    draw.ellipse(
        (cx - inner_radius, cy - inner_radius, cx + inner_radius, cy + inner_radius),
        outline=stroke,
        width=3,
    )
    draw.ellipse(
        (cx - hub_radius, cy - hub_radius, cx + hub_radius, cy + hub_radius),
        fill=tuple(int(v) for v in style.panel_alt_fill_rgb),
        outline=stroke,
        width=3,
    )
    return _bbox((cx - radius * 1.16, cy - radius * 1.16, cx + radius * 1.16, cy + radius * 1.16))


def _draw_label_box(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font: Any,
    style: Any,
    fill_rgb: Tuple[int, int, int] | None = None,
    outline_rgb: Tuple[int, int, int] | None = None,
    text_rgb: Tuple[int, int, int] | None = None,
) -> List[float]:
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
    text_w = float(text_bbox[2] - text_bbox[0])
    text_h = float(text_bbox[3] - text_bbox[1])
    cx, cy = float(center[0]), float(center[1])
    box = _bbox((cx - text_w / 2.0 - 12.0, cy - text_h / 2.0 - 7.0, cx + text_w / 2.0 + 12.0, cy + text_h / 2.0 + 7.0))
    fill = fill_rgb if fill_rgb is not None else tuple(int(v) for v in style.label_fill_rgb)
    outline = outline_rgb if outline_rgb is not None else tuple(int(v) for v in style.label_border_rgb)
    text_fill = text_rgb if text_rgb is not None else tuple(int(v) for v in style.label_rgb)
    draw.rounded_rectangle(tuple(box), radius=9, fill=fill, outline=outline, width=2)
    text_draw_bbox = draw_centered_text(
        draw,
        text=str(text),
        center=(cx, cy),
        font=font,
        fill=text_fill,
        stroke_fill=resolve_text_stroke_fill(text_fill),
        stroke_width=1,
    )
    return _bbox(_bbox_union(box, text_draw_bbox, padding=1.0))


def _draw_rotation_arrow(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    radius: float,
    direction: str,
    fill: Tuple[int, int, int],
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    arc_radius = float(radius + 26.0)
    if str(direction) == "clockwise":
        start_angle = math.radians(-138.0)
        end_angle = math.radians(118.0)
        steps = 28
        angles = [start_angle + (end_angle - start_angle) * float(index) / float(steps - 1) for index in range(steps)]
    else:
        start_angle = math.radians(138.0)
        end_angle = math.radians(-118.0)
        steps = 28
        angles = [start_angle + (end_angle - start_angle) * float(index) / float(steps - 1) for index in range(steps)]
    points = [(float(cx + arc_radius * math.cos(angle)), float(cy + arc_radius * math.sin(angle))) for angle in angles]
    draw.line(points[:-1], fill=fill, width=7, joint="curve")
    draw_arrow(
        draw,
        start=points[-4],
        end=points[-1],
        fill=fill,
        width=7,
        head_length_px=20,
        head_width_px=19,
    )
    return _bbox((cx - arc_radius - 13.0, cy - arc_radius - 13.0, cx + arc_radius + 13.0, cy + arc_radius + 13.0))


def _render_gear_train(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scenario: _GearScenario,
) -> _RenderedScene:
    canvas_width = int(_RENDER_DEFAULTS.get("canvas_width", _DEFAULTS.canvas_width))
    canvas_height = int(_RENDER_DEFAULTS.get("canvas_height", _DEFAULTS.canvas_height))
    background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        require_grid=True,
    )
    draw = ImageDraw.Draw(background)
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_NAMESPACE}.font",
        params=params,
    )
    label_font = load_font(int(_RENDER_DEFAULTS.get("label_font_size_px", _DEFAULTS.label_font_size_px)), bold=True, font_family=str(font_family))
    title_font = load_font(int(_RENDER_DEFAULTS.get("title_font_size_px", _DEFAULTS.title_font_size_px)), bold=True, font_family=str(font_family))
    panel = (
        float(_RENDER_DEFAULTS.get("panel_margin_x_px", _DEFAULTS.panel_margin_x_px)),
        float(_RENDER_DEFAULTS.get("panel_margin_top_px", _DEFAULTS.panel_margin_top_px)),
        float(canvas_width - _RENDER_DEFAULTS.get("panel_margin_x_px", _DEFAULTS.panel_margin_x_px)),
        float(canvas_height - _RENDER_DEFAULTS.get("panel_margin_bottom_px", _DEFAULTS.panel_margin_bottom_px)),
    )
    draw.rounded_rectangle(
        panel,
        radius=18,
        fill=tuple(int(v) for v in diagram_style.panel_fill_rgb),
        outline=tuple(int(v) for v in diagram_style.panel_border_rgb),
        width=3,
    )
    _draw_label_box(
        draw,
        text="Meshed gear train",
        center=(float(canvas_width * 0.5), float(panel[1] + 40.0)),
        font=title_font,
        style=diagram_style,
    )
    centers, radii = _layout_centers(scenario=scenario, panel=panel, instance_seed=int(instance_seed))
    gear_palette = (
        (91, 145, 217),
        (221, 139, 69),
        (94, 172, 128),
        (176, 112, 204),
        (209, 91, 110),
        (78, 164, 180),
    )
    color_offset = int(hash64(int(instance_seed), f"{TASK_NAMESPACE}.color_offset", 0) % len(gear_palette))
    gear_bboxes: Dict[str, List[float]] = {}
    scene_entities: List[Dict[str, Any]] = []
    for index, (center, radius) in enumerate(zip(centers, radii)):
        gear_id = f"gear_{index + 1}"
        fill = gear_palette[(index + color_offset) % len(gear_palette)]
        bbox = _draw_gear(
            draw,
            center=center,
            radius=float(radius),
            fill_rgb=fill,
            style=diagram_style,
        )
        gear_bboxes[gear_id] = bbox
        scene_entities.append(
            {
                "id": gear_id,
                "role": "input" if index == 0 else ("output" if index == int(scenario.gear_count) - 1 else "idler"),
                "center_px": [round(float(center[0]), 3), round(float(center[1]), 3)],
                "radius_px": round(float(radius), 3),
                "bbox_px": list(bbox),
            }
        )

    input_center = centers[0]
    output_center = centers[-1]
    input_radius = float(radii[0])
    output_radius = float(radii[-1])
    accent = tuple(int(v) for v in diagram_style.accent_rgb)
    arrow_bbox = _draw_rotation_arrow(
        draw,
        center=input_center,
        radius=input_radius,
        direction=str(scenario.input_direction),
        fill=accent,
    )
    input_label = _draw_label_box(
        draw,
        text="INPUT",
        center=(float(input_center[0]), float(input_center[1] - input_radius - 58.0)),
        font=label_font,
        style=diagram_style,
    )
    target_fill = (255, 232, 232)
    target_outline = (172, 42, 42)
    target_text = (178, 38, 38)
    output_label = _draw_label_box(
        draw,
        text="OUTPUT ?",
        center=(float(output_center[0]), float(output_center[1] + output_radius + 58.0)),
        font=label_font,
        style=diagram_style,
        fill_rgb=target_fill,
        outline_rgb=target_outline,
        text_rgb=target_text,
    )
    draw.line(
        [
            (float(output_center[0]), float(output_center[1] + output_radius * 0.80)),
            (float(output_center[0]), float(output_center[1] + output_radius + 34.0)),
        ],
        fill=target_outline,
        width=3,
    )
    train_bbox = _bbox(_bbox_union(*gear_bboxes.values(), padding=8.0))
    annotation_map = {
        "input_gear": _bbox(_bbox_union(gear_bboxes["gear_1"], input_label, padding=5.0)),
        "input_rotation_arrow": _bbox(arrow_bbox),
        "output_gear": _bbox(_bbox_union(gear_bboxes[f"gear_{int(scenario.gear_count)}"], output_label, padding=5.0)),
        "gear_train": _bbox(train_bbox),
    }

    image, post_noise_meta = apply_post_image_noise(
        background,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_map = {
        str(key): _clamp_bbox(value, width=int(image.size[0]), height=int(image.size[1]))
        for key, value in annotation_map.items()
    }
    render_map = {
        "query_id": QUERY_ID,
        "scene_variant": str(scenario.scene_variant),
        "gear_count": int(scenario.gear_count),
        "input_direction": str(scenario.input_direction),
        "output_direction": str(scenario.output_direction),
        "gear_centers_px": [[round(float(x), 3), round(float(y), 3)] for x, y in centers],
        "gear_radii_px": [round(float(value), 3) for value in radii],
        "gear_bboxes_px": {str(key): list(value) for key, value in gear_bboxes.items()},
        "input_rotation_arrow_bbox_px": list(arrow_bbox),
        "technical_diagram_style": dict(diagram_style_meta),
        "background_style": background_meta,
        "post_image_noise": post_noise_meta,
    }
    return _RenderedScene(
        image=image,
        annotation_bbox_map=annotation_map,
        scene_entities=scene_entities,
        render_map=render_map,
    )


def _render_gear_train_speed(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scenario: _GearSpeedScenario,
) -> _RenderedScene:
    canvas_width = int(_SPEED_RENDER_DEFAULTS.get("canvas_width", _DEFAULTS.canvas_width))
    canvas_height = int(_SPEED_RENDER_DEFAULTS.get("canvas_height", _DEFAULTS.canvas_height))
    background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        require_grid=True,
    )
    draw = ImageDraw.Draw(background)
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{SPEED_TASK_NAMESPACE}.font",
        params=params,
    )
    label_font = load_font(int(_SPEED_RENDER_DEFAULTS.get("label_font_size_px", _DEFAULTS.label_font_size_px)), bold=True, font_family=str(font_family))
    small_font = load_font(int(_SPEED_RENDER_DEFAULTS.get("tooth_label_font_size_px", 20)), bold=True, font_family=str(font_family))
    title_font = load_font(int(_SPEED_RENDER_DEFAULTS.get("title_font_size_px", _DEFAULTS.title_font_size_px)), bold=True, font_family=str(font_family))
    panel = (
        float(_SPEED_RENDER_DEFAULTS.get("panel_margin_x_px", _DEFAULTS.panel_margin_x_px)),
        float(_SPEED_RENDER_DEFAULTS.get("panel_margin_top_px", _DEFAULTS.panel_margin_top_px)),
        float(canvas_width - _SPEED_RENDER_DEFAULTS.get("panel_margin_x_px", _DEFAULTS.panel_margin_x_px)),
        float(canvas_height - _SPEED_RENDER_DEFAULTS.get("panel_margin_bottom_px", _DEFAULTS.panel_margin_bottom_px)),
    )
    draw.rounded_rectangle(
        panel,
        radius=18,
        fill=tuple(int(v) for v in diagram_style.panel_fill_rgb),
        outline=tuple(int(v) for v in diagram_style.panel_border_rgb),
        width=3,
    )
    _draw_label_box(
        draw,
        text="Gear ratio train",
        center=(float(canvas_width * 0.5), float(panel[1] + 40.0)),
        font=title_font,
        style=diagram_style,
    )
    centers, radii = _layout_centers(
        scenario=scenario,
        panel=panel,
        instance_seed=int(instance_seed),
        task_namespace=SPEED_TASK_NAMESPACE,
    )
    gear_palette = (
        (91, 145, 217),
        (221, 139, 69),
        (94, 172, 128),
        (176, 112, 204),
        (209, 91, 110),
        (78, 164, 180),
    )
    color_offset = int(hash64(int(instance_seed), f"{SPEED_TASK_NAMESPACE}.color_offset", 0) % len(gear_palette))
    tooth_counts = (int(scenario.input_teeth),) + tuple(int(value) for value in scenario.idler_teeth) + (int(scenario.output_teeth),)
    gear_bboxes: Dict[str, List[float]] = {}
    tooth_label_bboxes: Dict[str, List[float]] = {}
    scene_entities: List[Dict[str, Any]] = []
    for index, (center, radius, tooth_count) in enumerate(zip(centers, radii, tooth_counts)):
        gear_id = f"gear_{index + 1}"
        fill = gear_palette[(index + color_offset) % len(gear_palette)]
        gear_bbox = _draw_gear(
            draw,
            center=center,
            radius=float(radius),
            fill_rgb=fill,
            style=diagram_style,
        )
        tooth_bbox = _draw_label_box(
            draw,
            text=f"T={int(tooth_count)}",
            center=(float(center[0]), float(center[1])),
            font=small_font,
            style=diagram_style,
        )
        gear_bboxes[gear_id] = _bbox(_bbox_union(gear_bbox, tooth_bbox, padding=2.0))
        tooth_label_bboxes[gear_id] = tooth_bbox
        scene_entities.append(
            {
                "id": gear_id,
                "role": "input" if index == 0 else ("output" if index == int(scenario.gear_count) - 1 else "idler"),
                "center_px": [round(float(center[0]), 3), round(float(center[1]), 3)],
                "radius_px": round(float(radius), 3),
                "tooth_count": int(tooth_count),
                "bbox_px": list(gear_bboxes[gear_id]),
            }
        )

    input_center = centers[0]
    output_center = centers[-1]
    input_radius = float(radii[0])
    output_radius = float(radii[-1])
    input_label = _draw_label_box(
        draw,
        text=f"input = {int(scenario.input_rpm)} rpm",
        center=(float(input_center[0]), float(input_center[1] - input_radius - 48.0)),
        font=label_font,
        style=diagram_style,
    )
    target_fill = (255, 232, 232)
    target_outline = (172, 42, 42)
    target_text = (178, 38, 38)
    output_label = _draw_label_box(
        draw,
        text="output = ? rpm",
        center=(float(output_center[0]), float(output_center[1] + output_radius + 48.0)),
        font=label_font,
        style=diagram_style,
        fill_rgb=target_fill,
        outline_rgb=target_outline,
        text_rgb=target_text,
    )
    draw.line(
        [
            (float(output_center[0]), float(output_center[1] + output_radius * 0.80)),
            (float(output_center[0]), float(output_center[1] + output_radius + 28.0)),
        ],
        fill=target_outline,
        width=3,
    )

    train_bbox = _bbox(_bbox_union(*gear_bboxes.values(), padding=8.0))
    annotation_map = {
        "input_gear": _bbox(_bbox_union(gear_bboxes["gear_1"], input_label, padding=5.0)),
        "output_gear": _bbox(_bbox_union(gear_bboxes[f"gear_{int(scenario.gear_count)}"], output_label, padding=5.0)),
        "gear_train": _bbox(train_bbox),
    }
    image, post_noise_meta = apply_post_image_noise(
        background,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_map = {
        str(key): _clamp_bbox(value, width=int(image.size[0]), height=int(image.size[1]))
        for key, value in annotation_map.items()
    }
    render_map = {
        "query_id": SPEED_QUERY_ID,
        "scene_variant": str(scenario.scene_variant),
        "gear_count": int(scenario.gear_count),
        "input_teeth": int(scenario.input_teeth),
        "output_teeth": int(scenario.output_teeth),
        "idler_teeth": [int(value) for value in scenario.idler_teeth],
        "input_rpm": int(scenario.input_rpm),
        "output_rpm": int(scenario.output_rpm),
        "speed_relation": str(scenario.speed_relation),
        "ratio_numerator": int(scenario.input_rpm * scenario.input_teeth),
        "ratio_denominator": int(scenario.output_teeth),
        "gear_centers_px": [[round(float(x), 3), round(float(y), 3)] for x, y in centers],
        "gear_radii_px": [round(float(value), 3) for value in radii],
        "gear_bboxes_px": {str(key): list(value) for key, value in gear_bboxes.items()},
        "tooth_label_bboxes_px": {str(key): list(value) for key, value in tooth_label_bboxes.items()},
        "technical_diagram_style": dict(diagram_style_meta),
        "background_style": background_meta,
        "post_image_noise": post_noise_meta,
    }
    return _RenderedScene(
        image=image,
        annotation_bbox_map=annotation_map,
        scene_entities=scene_entities,
        render_map=render_map,
    )


@register_task
class PhysicsGearTrainOutputDirectionLabelTask:
    """Infer the marked output gear's rotation direction."""

    domain = "physics"
    scene_id = "mechanics"
    task_id = TASK_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) + int(attempt) * 1009
            try:
                params = dict(params or {})
                scenario = _resolve_scenario(int(attempt_seed), params)
                rendered = _render_gear_train(
                    instance_seed=int(attempt_seed),
                    params=params,
                    scenario=scenario,
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
                        f"answer_hint_{QUERY_ID}",
                        f"annotation_hint_{QUERY_ID}",
                        "json_example",
                        "json_example_answer_only",
                    ),
                    context=f"prompt defaults for {TASK_ID}",
                )
                answer_gt = TypedValue(type="string", value=str(scenario.output_direction))
                annotation_gt = TypedValue(type="keyed_bbox_map", value={str(k): list(v) for k, v in rendered.annotation_bbox_map.items()})
                json_example, json_example_answer_only = resolve_prompt_json_examples(
                    prompt_defaults,
                    annotation_value=annotation_gt.value,
                    answer_type=str(answer_gt.type),
                )
                prompt_selection = render_task_prompt_variants(
                    domain=self.domain,
                    scene_id=self.scene_id,
                    bundle_id=str(prompt_defaults["bundle_id"]),
                    scene_key=str(prompt_defaults["scene_key"]),
                    task_key=str(prompt_defaults["task_key"]),
                    query_key=QUERY_ID,
                    slots={
                        "object_description": str(prompt_defaults["object_description"]),
                        "json_output_contract": str(prompt_defaults["json_output_contract"]),
                        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                        "answer_hint": str(prompt_defaults[f"answer_hint_{QUERY_ID}"]),
                        "annotation_hint": str(prompt_defaults[f"annotation_hint_{QUERY_ID}"]),
                        "json_example": str(json_example),
                        "json_example_answer_only": str(json_example_answer_only),
                    },
                    instance_seed=int(attempt_seed),
                    answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                )
                prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
                font_family = sample_font_family(
                    role="readout",
                    instance_seed=int(attempt_seed),
                    namespace=f"{TASK_NAMESPACE}.font",
                    params=params,
                )
                font_record = get_font_family_record(str(font_family))
                trace_payload = {
                    "scene_ir": {
                        "scene_kind": "physics_gear_train_direction",
                        "entities": list(rendered.scene_entities),
                        "relations": {
                            "query_id": QUERY_ID,
                            "gear_count": int(scenario.gear_count),
                            "input_direction": str(scenario.input_direction),
                            "output_direction": str(scenario.output_direction),
                            "scene_variant": str(scenario.scene_variant),
                        },
                    },
                    "query_spec": {
                        "query_id": QUERY_ID,
                        "template_id": str(prompt_defaults["bundle_id"]),
                        "prompt_variant": dict(prompt_artifacts.prompt_variant),
                        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                        "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                        "params": {
                            "query_id": QUERY_ID,
                            "scene_variant": str(scenario.scene_variant),
                            "gear_count": int(scenario.gear_count),
                            "input_direction": str(scenario.input_direction),
                            "target_answer": str(scenario.output_direction),
                            "answer_support": list(SUPPORTED_DIRECTIONS),
                            "scene_variant_probabilities": dict(scenario.scene_variant_probabilities),
                            "gear_count_probabilities": dict(scenario.gear_count_probabilities),
                            "input_direction_probabilities": dict(scenario.input_direction_probabilities),
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
                            "scope": "gear_train_diagram",
                        },
                        "technical_diagram_style": dict(rendered.render_map["technical_diagram_style"]),
                        "background_style": dict(rendered.render_map["background_style"]),
                        "post_image_noise": dict(rendered.render_map["post_image_noise"]),
                    },
                    "render_map": dict(rendered.render_map),
                    "execution_trace": {
                        "query_id": QUERY_ID,
                        "gear_count": int(scenario.gear_count),
                        "mesh_reversals": int(scenario.gear_count) - 1,
                        "input_direction": str(scenario.input_direction),
                        "output_direction": str(scenario.output_direction),
                        "annotation_entity_ids": sorted(annotation_gt.value.keys()),
                    },
                    "sampling": {
                        "scene_variant_probabilities": dict(scenario.scene_variant_probabilities),
                        "gear_count_probabilities": dict(scenario.gear_count_probabilities),
                        "input_direction_probabilities": dict(scenario.input_direction_probabilities),
                        "target_answer_probabilities": dict(scenario.target_answer_probabilities),
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
                    query_id=QUERY_ID,
                )
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"failed to generate gear-train instance after {max_attempts} attempts: {last_error}")


@register_task
class PhysicsGearTrainOutputSpeedValueTask:
    """Compute the marked output gear's rotational speed."""

    domain = "physics"
    scene_id = "mechanics"
    task_id = SPEED_TASK_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) + int(attempt) * 1009
            try:
                params = dict(params or {})
                scenario = _resolve_speed_scenario(int(attempt_seed), params)
                rendered = _render_gear_train_speed(
                    instance_seed=int(attempt_seed),
                    params=params,
                    scenario=scenario,
                )
                prompt_defaults = required_group_defaults(
                    _SPEED_PROMPT_DEFAULTS,
                    (
                        "bundle_id",
                        "scene_key",
                        "task_key",
                        "json_output_contract",
                        "json_output_contract_answer_only",
                        "object_description",
                        f"answer_hint_{SPEED_QUERY_ID}",
                        f"annotation_hint_{SPEED_QUERY_ID}",
                        "json_example",
                        "json_example_answer_only",
                    ),
                    context=f"prompt defaults for {SPEED_TASK_ID}",
                )
                answer_gt = TypedValue(type="integer", value=int(scenario.output_rpm))
                annotation_gt = TypedValue(type="keyed_bbox_map", value={str(k): list(v) for k, v in rendered.annotation_bbox_map.items()})
                json_example, json_example_answer_only = resolve_prompt_json_examples(
                    prompt_defaults,
                    annotation_value=annotation_gt.value,
                    answer_type=str(answer_gt.type),
                )
                prompt_selection = render_task_prompt_variants(
                    domain=self.domain,
                    scene_id=self.scene_id,
                    bundle_id=str(prompt_defaults["bundle_id"]),
                    scene_key=str(prompt_defaults["scene_key"]),
                    task_key=str(prompt_defaults["task_key"]),
                    query_key=SPEED_QUERY_ID,
                    slots={
                        "object_description": str(prompt_defaults["object_description"]),
                        "json_output_contract": str(prompt_defaults["json_output_contract"]),
                        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                        "answer_hint": str(prompt_defaults[f"answer_hint_{SPEED_QUERY_ID}"]),
                        "annotation_hint": str(prompt_defaults[f"annotation_hint_{SPEED_QUERY_ID}"]),
                        "json_example": str(json_example),
                        "json_example_answer_only": str(json_example_answer_only),
                    },
                    instance_seed=int(attempt_seed),
                    answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                )
                prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
                font_family = sample_font_family(
                    role="readout",
                    instance_seed=int(attempt_seed),
                    namespace=f"{SPEED_TASK_NAMESPACE}.font",
                    params=params,
                )
                font_record = get_font_family_record(str(font_family))
                trace_payload = {
                    "scene_ir": {
                        "scene_kind": "physics_gear_train_speed",
                        "entities": list(rendered.scene_entities),
                        "relations": {
                            "query_id": SPEED_QUERY_ID,
                            "gear_count": int(scenario.gear_count),
                            "input_teeth": int(scenario.input_teeth),
                            "output_teeth": int(scenario.output_teeth),
                            "input_rpm": int(scenario.input_rpm),
                            "output_rpm": int(scenario.output_rpm),
                            "speed_relation": str(scenario.speed_relation),
                            "scene_variant": str(scenario.scene_variant),
                        },
                    },
                    "query_spec": {
                        "query_id": SPEED_QUERY_ID,
                        "template_id": str(prompt_defaults["bundle_id"]),
                        "prompt_variant": dict(prompt_artifacts.prompt_variant),
                        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                        "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                        "params": {
                            "query_id": SPEED_QUERY_ID,
                            "scene_variant": str(scenario.scene_variant),
                            "gear_count": int(scenario.gear_count),
                            "input_teeth": int(scenario.input_teeth),
                            "output_teeth": int(scenario.output_teeth),
                            "idler_teeth": [int(value) for value in scenario.idler_teeth],
                            "input_rpm": int(scenario.input_rpm),
                            "target_answer": int(scenario.output_rpm),
                            "speed_relation": str(scenario.speed_relation),
                            "scene_variant_probabilities": dict(scenario.scene_variant_probabilities),
                            "gear_count_probabilities": dict(scenario.gear_count_probabilities),
                            "speed_relation_probabilities": dict(scenario.speed_relation_probabilities),
                            "input_rpm_probabilities": dict(scenario.input_rpm_probabilities),
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
                            "scope": "gear_train_speed_diagram",
                        },
                        "technical_diagram_style": dict(rendered.render_map["technical_diagram_style"]),
                        "background_style": dict(rendered.render_map["background_style"]),
                        "post_image_noise": dict(rendered.render_map["post_image_noise"]),
                    },
                    "render_map": dict(rendered.render_map),
                    "execution_trace": {
                        "query_id": SPEED_QUERY_ID,
                        "gear_count": int(scenario.gear_count),
                        "input_teeth": int(scenario.input_teeth),
                        "output_teeth": int(scenario.output_teeth),
                        "idler_teeth": [int(value) for value in scenario.idler_teeth],
                        "input_rpm": int(scenario.input_rpm),
                        "output_rpm": int(scenario.output_rpm),
                        "ratio_equation": f"{int(scenario.input_rpm)}*{int(scenario.input_teeth)}/{int(scenario.output_teeth)}",
                        "speed_relation": str(scenario.speed_relation),
                        "annotation_entity_ids": sorted(annotation_gt.value.keys()),
                    },
                    "sampling": {
                        "scene_variant_probabilities": dict(scenario.scene_variant_probabilities),
                        "gear_count_probabilities": dict(scenario.gear_count_probabilities),
                        "speed_relation_probabilities": dict(scenario.speed_relation_probabilities),
                        "input_rpm_probabilities": dict(scenario.input_rpm_probabilities),
                        "target_answer_probabilities": dict(scenario.target_answer_probabilities),
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
                ratio_gap = abs(float(scenario.output_rpm) - float(scenario.input_rpm)) / max(float(scenario.input_rpm), 1.0)
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
                    query_id=SPEED_QUERY_ID,
                )
            except Exception as exc:
                last_error = exc
                continue
        raise RuntimeError(f"failed to generate gear-train speed instance after {max_attempts} attempts: {last_error}")
