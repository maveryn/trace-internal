"""Physics thermodynamics tasks for pressure-volume diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_many as _bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
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
from ..shared.complexity import build_physics_pv_diagram_complexity
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.fixed_query_task import FixedPhysicsQueryVariantTaskMixin
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES, build_physics_pv_diagram_theme
from ..shared.support_sampling import resolve_integer_support
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "physics_thermodynamics_pv_diagram_family"
SCENE_ID = "pv_diagram"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "clean_grid",
    "paper_grid",
    "bold_grid",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "work_value",
    "process_sign_choice",
)
SUPPORTED_WORK_MODES: Tuple[str, ...] = (
    "single_process",
    "rectangular_cycle",
)
SUPPORTED_TARGET_SIGNS: Tuple[str, ...] = ("positive", "negative", "zero")
OPTION_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H")
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "clean_grid": SUPPORTED_QUERY_IDS,
    "paper_grid": SUPPORTED_QUERY_IDS,
    "bold_grid": SUPPORTED_QUERY_IDS,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for PV-diagram scenes."""

    canvas_width: int = 1180
    canvas_height: int = 760
    plot_left_px: int = 118
    plot_top_px: int = 78
    plot_width_px: int = 760
    plot_height_px: int = 560
    mini_plot_left_px: int = 58
    mini_plot_top_px: int = 88
    mini_cell_width_px: int = 262
    mini_cell_height_px: int = 196
    mini_cell_gap_x_px: int = 18
    mini_cell_gap_y_px: int = 32
    axis_width_px: int = 5
    grid_line_width_px: int = 1
    bold_grid_line_width_px: int = 2
    process_line_width_px: int = 9
    cycle_line_width_px: int = 8
    arrow_head_length_px: int = 24
    arrow_head_width_px: int = 22
    label_font_size_px: int = 24
    tick_font_size_px: int = 18
    state_font_size_px: int = 25
    option_font_size_px: int = 26
    note_font_size_px: int = 21
    label_stroke_width_px: int = 2
    pressure_max_kpa: int = 10
    volume_max_l: int = 12
    pressure_support: Tuple[int, ...] = (2, 3, 4, 5, 6, 7, 8, 9)
    volume_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
    min_volume_delta: int = 2
    max_volume_delta: int = 9
    work_answer_support: Tuple[int, ...] = (
        -70,
        -64,
        -63,
        -60,
        -56,
        -54,
        -49,
        -48,
        -45,
        -42,
        -40,
        -36,
        -35,
        -32,
        -30,
        -28,
        -27,
        -25,
        -24,
        -21,
        -20,
        -18,
        -16,
        -15,
        -14,
        -12,
        -10,
        -9,
        -8,
        -7,
        -6,
        -5,
        -4,
        -3,
        -2,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        12,
        14,
        15,
        16,
        18,
        20,
        21,
        24,
        25,
        27,
        28,
        30,
        32,
        35,
        36,
        40,
        42,
        45,
        48,
        49,
        54,
        56,
        60,
        63,
        64,
        70,
    )


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query/color/answer axes for one PV instance."""

    scene_variant: str
    query_id: str
    work_mode: str | None
    target_sign: str | None
    correct_option_letter: str | None
    accent_color_name: str
    target_answer: int | str
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    work_mode_probabilities: Dict[str, float]
    target_sign_probabilities: Dict[str, float]
    correct_option_letter_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _WorkScenario:
    """One symbolic PV-work scenario."""

    work_mode: str
    work_value: int
    pressure: int | None
    volume_start: int | None
    volume_end: int | None
    pressure_low: int | None
    pressure_high: int | None
    volume_left: int | None
    volume_right: int | None
    cycle_direction: str | None


@dataclass(frozen=True)
class _ProcessCandidate:
    """One labeled candidate PV process for a sign-choice query."""

    letter: str
    sign: str
    pressure_start: int
    pressure_end: int
    volume_start: int
    volume_end: int


@dataclass(frozen=True)
class _SceneSpec:
    """Resolved symbolic PV scene."""

    scene_variant: str
    query_id: str
    work_mode: str | None
    target_sign: str | None
    correct_option_letter: str | None
    target_answer: int | str
    work_scenario: _WorkScenario | None
    process_candidates: Tuple[_ProcessCandidate, ...]
    annotation_entity_ids: Tuple[str, ...]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered PV diagram plus prompt-facing annotation metadata."""

    image: Image.Image
    annotation_bboxes: List[List[float]]
    annotation_entity_ids: List[str]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "thermodynamics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="thermodynamics", apply_prob=0.5)


def _with_sampling_divisor(params: Mapping[str, Any], *, divisor: int, explicit_keys: Sequence[str]) -> Mapping[str, Any]:
    """No-op hook for axis-decoupling call sites."""

    _ = int(divisor), explicit_keys
    return params


def _pressure_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return configured pressure support in kPa."""

    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="pressure_support",
        fallback=_DEFAULTS.pressure_support,
    )


def _volume_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return configured volume support in liters."""

    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="volume_support",
        fallback=_DEFAULTS.volume_support,
    )


def _work_answer_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return configured signed PV-work answer support in joules."""

    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="work_answer_support",
        fallback=_DEFAULTS.work_answer_support,
    )


def _sign_for_work(work_value: int) -> str:
    """Return positive/negative/zero for one signed work value."""

    if int(work_value) > 0:
        return "positive"
    if int(work_value) < 0:
        return "negative"
    return "zero"


def _feasible_work_scenarios(params: Mapping[str, Any], *, work_mode: str | None = None) -> Tuple[_WorkScenario, ...]:
    """Enumerate constructively feasible PV-work scenarios."""

    pressures = _pressure_support(params)
    volumes = _volume_support(params)
    configured_answers = set(_work_answer_support(params))
    min_delta = int(params.get("min_volume_delta", group_default(_GEN_DEFAULTS, "min_volume_delta", _DEFAULTS.min_volume_delta)))
    max_delta = int(params.get("max_volume_delta", group_default(_GEN_DEFAULTS, "max_volume_delta", _DEFAULTS.max_volume_delta)))
    explicit_pressure = params.get("pressure")
    explicit_volume_start = params.get("volume_start")
    explicit_volume_end = params.get("volume_end")
    explicit_pressure_low = params.get("pressure_low")
    explicit_pressure_high = params.get("pressure_high")
    explicit_volume_left = params.get("volume_left")
    explicit_volume_right = params.get("volume_right")
    explicit_cycle_direction = params.get("cycle_direction")

    modes = [str(work_mode)] if work_mode is not None else list(SUPPORTED_WORK_MODES)
    scenarios: List[_WorkScenario] = []
    if "single_process" in modes:
        for pressure in pressures:
            if explicit_pressure is not None and int(pressure) != int(explicit_pressure):
                continue
            for volume_start in volumes:
                if explicit_volume_start is not None and int(volume_start) != int(explicit_volume_start):
                    continue
                for volume_end in volumes:
                    if explicit_volume_end is not None and int(volume_end) != int(explicit_volume_end):
                        continue
                    delta_v = int(volume_end) - int(volume_start)
                    if int(delta_v) == 0:
                        continue
                    if abs(int(delta_v)) < int(min_delta) or abs(int(delta_v)) > int(max_delta):
                        continue
                    work_value = int(pressure) * int(delta_v)
                    if int(work_value) not in configured_answers:
                        continue
                    scenarios.append(
                        _WorkScenario(
                            work_mode="single_process",
                            work_value=int(work_value),
                            pressure=int(pressure),
                            volume_start=int(volume_start),
                            volume_end=int(volume_end),
                            pressure_low=None,
                            pressure_high=None,
                            volume_left=None,
                            volume_right=None,
                            cycle_direction=None,
                        )
                    )

    if "rectangular_cycle" in modes:
        directions = ("clockwise", "counterclockwise")
        if explicit_cycle_direction is not None:
            direction_text = str(explicit_cycle_direction)
            if direction_text not in set(directions):
                raise ValueError(f"unsupported cycle_direction: {explicit_cycle_direction}")
            directions = (direction_text,)
        for pressure_low in pressures:
            if explicit_pressure_low is not None and int(pressure_low) != int(explicit_pressure_low):
                continue
            for pressure_high in pressures:
                if explicit_pressure_high is not None and int(pressure_high) != int(explicit_pressure_high):
                    continue
                if int(pressure_high) <= int(pressure_low):
                    continue
                delta_p = int(pressure_high) - int(pressure_low)
                for volume_left in volumes:
                    if explicit_volume_left is not None and int(volume_left) != int(explicit_volume_left):
                        continue
                    for volume_right in volumes:
                        if explicit_volume_right is not None and int(volume_right) != int(explicit_volume_right):
                            continue
                        if int(volume_right) <= int(volume_left):
                            continue
                        delta_v = int(volume_right) - int(volume_left)
                        if int(delta_v) < int(min_delta) or int(delta_v) > int(max_delta):
                            continue
                        area = int(delta_p) * int(delta_v)
                        for direction in directions:
                            work_value = int(area) if str(direction) == "clockwise" else -int(area)
                            if int(work_value) not in configured_answers:
                                continue
                            scenarios.append(
                                _WorkScenario(
                                    work_mode="rectangular_cycle",
                                    work_value=int(work_value),
                                    pressure=None,
                                    volume_start=None,
                                    volume_end=None,
                                    pressure_low=int(pressure_low),
                                    pressure_high=int(pressure_high),
                                    volume_left=int(volume_left),
                                    volume_right=int(volume_right),
                                    cycle_direction=str(direction),
                                )
                            )

    if not scenarios:
        raise ValueError("no feasible PV-work scenarios for configured supports")
    return tuple(scenarios)


def _feasible_work_answers(params: Mapping[str, Any], *, work_mode: str) -> Tuple[int, ...]:
    """Return configured work answers that have at least one construction."""

    feasible = sorted(
        {int(scenario.work_value) for scenario in _feasible_work_scenarios(params, work_mode=str(work_mode))},
        key=lambda value: (abs(int(value)), 0 if int(value) > 0 else 1),
    )
    if not feasible:
        raise ValueError(f"no feasible PV-work answers for {work_mode}")
    return tuple(int(value) for value in feasible)


def _resolve_work_mode(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str | None, Dict[str, float]]:
    """Resolve the work-diagram construction mode for numeric work queries."""

    if str(query_id) != "work_value":
        return None, {}
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.work_mode"),
        params=_with_sampling_divisor(params, divisor=len(SUPPORTED_QUERY_IDS), explicit_keys=("work_mode",)),
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_WORK_MODES,
        explicit_key="work_mode",
        weights_key="work_mode_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=_with_sampling_divisor(params, divisor=len(SUPPORTED_QUERY_IDS), explicit_keys=("work_mode",)),
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_WORK_MODES,
        balance_flag_key="balanced_work_mode_sampling",
        explicit_key="work_mode",
        weights_key="work_mode_weights",
        sampling_namespace=f"{TASK_ID}.work_mode",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_target_sign(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str | None, Dict[str, float]]:
    """Resolve the target sign for a sign-choice query."""

    if str(query_id) != "process_sign_choice":
        return None, {}
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.target_sign"),
        params=_with_sampling_divisor(params, divisor=len(SUPPORTED_QUERY_IDS), explicit_keys=("target_sign",)),
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_TARGET_SIGNS,
        explicit_key="target_sign",
        weights_key="target_sign_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=_with_sampling_divisor(params, divisor=len(SUPPORTED_QUERY_IDS), explicit_keys=("target_sign",)),
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_TARGET_SIGNS,
        balance_flag_key="balanced_target_sign_sampling",
        explicit_key="target_sign",
        weights_key="target_sign_weights",
        sampling_namespace=f"{TASK_ID}.target_sign",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_correct_option_letter(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str | None, Dict[str, float]]:
    """Resolve which visible option letter carries the unique sign match."""

    if str(query_id) != "process_sign_choice":
        return None, {}
    option_params = dict(params)
    if option_params.get("correct_option_letter") is None and option_params.get("target_answer") is not None:
        option_params["correct_option_letter"] = str(option_params["target_answer"]).strip().upper()
    option_params = dict(_with_sampling_divisor(option_params, divisor=len(SUPPORTED_QUERY_IDS), explicit_keys=("correct_option_letter",)))
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
    if bool(balanced_enabled) and not bool(has_override) and is_uniform_probability_map(probabilities):
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
            sampling_namespace=f"{TASK_ID}.correct_option_letter",
        )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_work_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    work_mode: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve a signed integer work target from feasible configured support."""

    support = _feasible_work_answers(params, work_mode=str(work_mode))
    explicit = params.get("target_answer")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"unsupported target_answer for {work_mode}: {selected}")
        return int(selected), uniform_probability_map(support, selected=int(selected))

    adjusted_params = _with_sampling_divisor(
        params,
        divisor=len(SUPPORTED_QUERY_IDS) * len(SUPPORTED_WORK_MODES),
        explicit_keys=("target_answer",),
    )
    balanced_enabled = bool(
        adjusted_params.get(
            "balanced_target_answer_sampling",
            group_default(_GEN_DEFAULTS, "balanced_target_answer_sampling", True),
        )
    )
    if bool(balanced_enabled):
        selection_index = resolve_selection_index(
            params=adjusted_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.target_answer.{str(work_mode)}",
        )
        selected = int(support[int(selection_index) % len(support)])
    else:
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.target_answer.{str(work_mode)}")
        selected = int(support[int(rng.randrange(len(support)))])
    return int(selected), uniform_probability_map(support)


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

    work_mode, work_mode_probs = _resolve_work_mode(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    target_sign, target_sign_probs = _resolve_target_sign(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    correct_option_letter, option_probs = _resolve_correct_option_letter(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    if str(query_id) == "work_value":
        if work_mode is None:
            raise ValueError("work_value query requires a work_mode")
        target_answer, target_probs = _resolve_work_target_answer(
            instance_seed=int(instance_seed),
            params=params,
            work_mode=str(work_mode),
        )
    else:
        if correct_option_letter is None:
            raise ValueError("process_sign_choice query requires a correct option letter")
        target_answer = str(correct_option_letter)
        target_probs = dict(option_probs)

    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        work_mode=work_mode,
        target_sign=target_sign,
        correct_option_letter=correct_option_letter,
        accent_color_name=str(accent_name),
        target_answer=target_answer,
        scene_variant_probabilities={str(key): float(value) for key, value in sorted(scene_probs.items())},
        query_id_probabilities={str(key): float(value) for key, value in sorted(query_probs.items())},
        work_mode_probabilities={str(key): float(value) for key, value in sorted(work_mode_probs.items())},
        target_sign_probabilities={str(key): float(value) for key, value in sorted(target_sign_probs.items())},
        correct_option_letter_probabilities={str(key): float(value) for key, value in sorted(option_probs.items())},
        accent_color_name_probabilities={str(key): float(value) for key, value in sorted(accent_probs.items())},
        target_answer_probabilities={str(key): float(value) for key, value in sorted(target_probs.items())},
    )


def _sample_work_scenario(
    rng,
    *,
    work_mode: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> _WorkScenario:
    """Sample one symbolic PV-work scenario that realizes the target answer."""

    scenarios = [
        scenario
        for scenario in _feasible_work_scenarios(params, work_mode=str(work_mode))
        if int(scenario.work_value) == int(target_answer)
    ]
    if not scenarios:
        raise ValueError(f"no feasible PV-work scenario for {work_mode} target {target_answer}")
    return scenarios[int(rng.randrange(len(scenarios)))]


def _candidate_values_for_sign(rng, *, sign: str) -> Tuple[int, int, int, int]:
    """Return start/end pressure and volume for one sign-choice mini process."""

    if str(sign) == "positive":
        pressure = int(rng.choice((3, 4, 5, 6, 7, 8)))
        left = int(rng.choice((2, 3, 4)))
        right = int(rng.choice((8, 9, 10)))
        return pressure, pressure, left, right
    if str(sign) == "negative":
        pressure = int(rng.choice((3, 4, 5, 6, 7, 8)))
        left = int(rng.choice((2, 3, 4)))
        right = int(rng.choice((8, 9, 10)))
        return pressure, pressure, right, left
    volume = int(rng.choice((4, 5, 6, 7)))
    p0 = int(rng.choice((2, 3, 4)))
    p1 = int(rng.choice((7, 8, 9)))
    if int(rng.randrange(2)) == 0:
        return p0, p1, volume, volume
    return p1, p0, volume, volume


def _sample_process_candidates(
    rng,
    *,
    target_sign: str,
    correct_option_letter: str,
) -> Tuple[_ProcessCandidate, ...]:
    """Sample six labeled process candidates with exactly one target-sign match."""

    candidates: List[_ProcessCandidate] = []
    non_target_signs = [sign for sign in SUPPORTED_TARGET_SIGNS if str(sign) != str(target_sign)]
    for letter in OPTION_LETTERS:
        sign = str(target_sign) if str(letter) == str(correct_option_letter) else str(rng.choice(non_target_signs))
        pressure_start, pressure_end, volume_start, volume_end = _candidate_values_for_sign(rng, sign=str(sign))
        candidates.append(
            _ProcessCandidate(
                letter=str(letter),
                sign=str(sign),
                pressure_start=int(pressure_start),
                pressure_end=int(pressure_end),
                volume_start=int(volume_start),
                volume_end=int(volume_end),
            )
        )
    return tuple(candidates)


def _sample_scene_spec(
    rng,
    *,
    axes: _ResolvedAxes,
    params: Mapping[str, Any],
) -> _SceneSpec:
    """Sample one symbolic PV scene."""

    if str(axes.query_id) == "work_value":
        if axes.work_mode is None:
            raise ValueError("work_value query requires work_mode")
        scenario = _sample_work_scenario(
            rng,
            work_mode=str(axes.work_mode),
            target_answer=int(axes.target_answer),
            params=params,
        )
        return _SceneSpec(
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            work_mode=str(axes.work_mode),
            target_sign=None,
            correct_option_letter=None,
            target_answer=int(scenario.work_value),
            work_scenario=scenario,
            process_candidates=(),
            annotation_entity_ids=("work_witness_region",),
        )

    if axes.target_sign is None or axes.correct_option_letter is None:
        raise ValueError("process_sign_choice query requires target sign and correct option")
    candidates = _sample_process_candidates(
        rng,
        target_sign=str(axes.target_sign),
        correct_option_letter=str(axes.correct_option_letter),
    )
    return _SceneSpec(
        scene_variant=str(axes.scene_variant),
        query_id=str(axes.query_id),
        work_mode=None,
        target_sign=str(axes.target_sign),
        correct_option_letter=str(axes.correct_option_letter),
        target_answer=str(axes.correct_option_letter),
        work_scenario=None,
        process_candidates=tuple(candidates),
        annotation_entity_ids=(f"option_{str(axes.correct_option_letter)}_process",),
    )


def _arrow_bbox(start: Tuple[float, float], end: Tuple[float, float], *, padding_px: float) -> List[float]:
    """Return a conservative bbox for one arrow."""

    return [
        round(float(min(float(start[0]), float(end[0])) - float(padding_px)), 3),
        round(float(min(float(start[1]), float(end[1])) - float(padding_px)), 3),
        round(float(max(float(start[0]), float(end[0])) + float(padding_px)), 3),
        round(float(max(float(start[1]), float(end[1])) + float(padding_px)), 3),
    ]


def _plot_bbox(render_defaults: Mapping[str, Any]) -> List[float]:
    """Return the main plot bbox."""

    offset_x = float(render_defaults.get("layout_offset_x_px", 0))
    offset_y = float(render_defaults.get("layout_offset_y_px", 0))
    return [
        float(render_defaults["plot_left_px"]) + float(offset_x),
        float(render_defaults["plot_top_px"]) + float(offset_y),
        float(render_defaults["plot_left_px"]) + float(render_defaults["plot_width_px"]) + float(offset_x),
        float(render_defaults["plot_top_px"]) + float(render_defaults["plot_height_px"]) + float(offset_y),
    ]


def _plot_xy(
    *,
    bbox: Sequence[float],
    volume_l: float,
    pressure_kpa: float,
    volume_max_l: int,
    pressure_max_kpa: int,
) -> Tuple[float, float]:
    """Map PV coordinates to screen coordinates."""

    left, top, right, bottom = [float(value) for value in bbox[:4]]
    x = float(left + (float(volume_l) / float(volume_max_l)) * (right - left))
    y = float(bottom - (float(pressure_kpa) / float(pressure_max_kpa)) * (bottom - top))
    return float(x), float(y)


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


def _draw_axes(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    render_defaults: Mapping[str, Any],
    scene_variant: str,
    theme,
    tick_font,
    label_font,
    include_tick_numbers: bool,
) -> Dict[str, Any]:
    """Draw PV axes and return bbox metadata."""

    left, top, right, bottom = [float(value) for value in bbox[:4]]
    volume_max = int(render_defaults["volume_max_l"])
    pressure_max = int(render_defaults["pressure_max_kpa"])
    grid_width = int(render_defaults["bold_grid_line_width_px"]) if str(scene_variant) == "bold_grid" else int(render_defaults["grid_line_width_px"])
    plot_fill = tuple(int(value) for value in theme.paper_plot_fill_rgb) if str(scene_variant) == "paper_grid" else tuple(int(value) for value in theme.plot_fill_rgb)
    draw_rounded_rect(
        draw,
        tuple(float(value) for value in bbox),
        radius=0,
        fill=plot_fill,
        outline=tuple(int(value) for value in theme.plot_outline_rgb),
        width=3,
    )
    tick_bboxes: List[List[float]] = []
    for volume in range(0, int(volume_max) + 1):
        x, _ = _plot_xy(
            bbox=bbox,
            volume_l=float(volume),
            pressure_kpa=0.0,
            volume_max_l=volume_max,
            pressure_max_kpa=pressure_max,
        )
        draw.line([(float(x), float(top)), (float(x), float(bottom))], fill=tuple(int(value) for value in theme.grid_rgb), width=grid_width)
        if include_tick_numbers:
            label_bbox = draw_centered_text(
                draw,
                text=str(volume),
                center=(float(x), float(bottom + 22.0)),
                font=tick_font,
                fill=tuple(int(value) for value in theme.axis_text_rgb),
                stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.axis_text_rgb)),
                stroke_width=1,
            )
            tick_bboxes.append(list(label_bbox))
    for pressure in range(0, int(pressure_max) + 1):
        _, y = _plot_xy(
            bbox=bbox,
            volume_l=0.0,
            pressure_kpa=float(pressure),
            volume_max_l=volume_max,
            pressure_max_kpa=pressure_max,
        )
        draw.line([(float(left), float(y)), (float(right), float(y))], fill=tuple(int(value) for value in theme.grid_rgb), width=grid_width)
        if include_tick_numbers:
            label_bbox = draw_centered_text(
                draw,
                text=str(pressure),
                center=(float(left - 24.0), float(y)),
                font=tick_font,
                fill=tuple(int(value) for value in theme.axis_text_rgb),
                stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.axis_text_rgb)),
                stroke_width=1,
            )
            tick_bboxes.append(list(label_bbox))
    draw_arrow(
        draw,
        start=(float(left), float(bottom)),
        end=(float(right + 34.0), float(bottom)),
        fill=tuple(int(value) for value in theme.axis_rgb),
        width=int(render_defaults["axis_width_px"]),
        head_length_px=24.0,
        head_width_px=20.0,
    )
    draw_arrow(
        draw,
        start=(float(left), float(bottom)),
        end=(float(left), float(top - 34.0)),
        fill=tuple(int(value) for value in theme.axis_rgb),
        width=int(render_defaults["axis_width_px"]),
        head_length_px=24.0,
        head_width_px=20.0,
    )
    x_label_bbox = draw_centered_text(
        draw,
        text="V (L)",
        center=(float((left + right) / 2.0), float(bottom + 58.0)),
        font=label_font,
        fill=tuple(int(value) for value in theme.axis_text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.axis_text_rgb)),
        stroke_width=1,
    )
    y_label_bbox = draw_centered_text(
        draw,
        text="P (kPa)",
        center=(float(left - 62.0), float(top - 30.0)),
        font=label_font,
        fill=tuple(int(value) for value in theme.axis_text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.axis_text_rgb)),
        stroke_width=1,
    )
    return {
        "plot_bbox_px": [round(float(value), 3) for value in bbox],
        "tick_label_bboxes_px": [list(bbox_value) for bbox_value in tick_bboxes],
        "axis_label_bboxes_px": [list(x_label_bbox), list(y_label_bbox)],
        "axis_bbox_px": _bbox_union(bbox, x_label_bbox, y_label_bbox, *tick_bboxes),
    }


def _draw_state_label(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    theme,
) -> List[float]:
    """Draw a compact state/option label."""

    return _draw_text_tag(
        draw,
        text=str(text),
        center=(float(center[0]), float(center[1])),
        font=font,
        fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.label_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.label_text_rgb),
        stroke_width_px=2,
    )


def _draw_single_process(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    render_defaults: Mapping[str, Any],
    scenario: _WorkScenario,
    theme,
    state_font,
    note_font,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Draw one horizontal isobaric process and return entity/render metadata."""

    if scenario.pressure is None or scenario.volume_start is None or scenario.volume_end is None:
        raise ValueError("single-process scenario is missing pressure or volume")
    volume_max = int(render_defaults["volume_max_l"])
    pressure_max = int(render_defaults["pressure_max_kpa"])
    start = _plot_xy(
        bbox=bbox,
        volume_l=float(scenario.volume_start),
        pressure_kpa=float(scenario.pressure),
        volume_max_l=volume_max,
        pressure_max_kpa=pressure_max,
    )
    end = _plot_xy(
        bbox=bbox,
        volume_l=float(scenario.volume_end),
        pressure_kpa=float(scenario.pressure),
        volume_max_l=volume_max,
        pressure_max_kpa=pressure_max,
    )
    baseline_start = _plot_xy(
        bbox=bbox,
        volume_l=float(scenario.volume_start),
        pressure_kpa=0.0,
        volume_max_l=volume_max,
        pressure_max_kpa=pressure_max,
    )
    baseline_end = _plot_xy(
        bbox=bbox,
        volume_l=float(scenario.volume_end),
        pressure_kpa=0.0,
        volume_max_l=volume_max,
        pressure_max_kpa=pressure_max,
    )
    shade_poly = [baseline_start, start, end, baseline_end]
    draw.polygon(
        [(float(x), float(y)) for x, y in shade_poly],
        fill=tuple(int(value) for value in theme.work_fill_rgb),
    )
    draw.line([baseline_start, start], fill=tuple(int(value) for value in theme.guide_rgb), width=3)
    draw.line([baseline_end, end], fill=tuple(int(value) for value in theme.guide_rgb), width=3)
    draw_arrow(
        draw,
        start=start,
        end=end,
        fill=tuple(int(value) for value in theme.process_rgb),
        width=int(render_defaults["process_line_width_px"]),
        head_length_px=float(render_defaults["arrow_head_length_px"]),
        head_width_px=float(render_defaults["arrow_head_width_px"]),
    )
    process_bbox = _arrow_bbox(start, end, padding_px=float(render_defaults["arrow_head_width_px"]) + 8.0)
    shade_bbox = _bbox_union(
        [baseline_start[0], baseline_start[1], baseline_end[0], baseline_end[1]],
        [start[0], start[1], end[0], end[1]],
    )
    a_label = _draw_state_label(
        draw,
        text="A",
        center=(float(start[0]), float(start[1] - 34.0)),
        font=state_font,
        theme=theme,
    )
    b_label = _draw_state_label(
        draw,
        text="B",
        center=(float(end[0]), float(end[1] - 34.0)),
        font=state_font,
        theme=theme,
    )
    sign_label = "expansion" if int(scenario.work_value) > 0 else "compression"
    mid_x = float((start[0] + end[0]) / 2.0)
    mid_y = float(min(start[1], end[1]) - 74.0)
    if float(mid_y) < float(bbox[1] + 28.0):
        mid_y = float(max(start[1], end[1]) + 54.0)
    note_bbox = _draw_text_tag(
        draw,
        text=str(sign_label),
        center=(mid_x, mid_y),
        font=note_font,
        fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.label_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.label_text_rgb),
        stroke_width_px=2,
    )
    witness_bbox = _bbox_union(process_bbox, shade_bbox, a_label, b_label)
    entities = [
        {
            "entity_id": "work_process_arrow",
            "entity_type": "pv_process_arrow",
            "bbox_px": list(process_bbox),
            "meta": {
                "pressure_kpa": int(scenario.pressure),
                "volume_start_l": int(scenario.volume_start),
                "volume_end_l": int(scenario.volume_end),
                "delta_volume_l": int(scenario.volume_end - scenario.volume_start),
                "work_j": int(scenario.work_value),
            },
        },
        {
            "entity_id": "work_area",
            "entity_type": "pv_work_area",
            "bbox_px": list(shade_bbox),
            "meta": {"work_j": int(scenario.work_value), "sign": _sign_for_work(int(scenario.work_value))},
        },
        {
            "entity_id": "work_witness_region",
            "entity_type": "pv_work_witness",
            "bbox_px": list(witness_bbox),
            "meta": {"members": ["work_process_arrow", "work_area"], "work_j": int(scenario.work_value)},
        },
    ]
    render_map = {
        "process_start_px": [round(float(start[0]), 3), round(float(start[1]), 3)],
        "process_end_px": [round(float(end[0]), 3), round(float(end[1]), 3)],
        "process_bbox_px": list(process_bbox),
        "work_area_bbox_px": list(shade_bbox),
        "work_witness_region_bbox_px": list(witness_bbox),
        "state_label_bboxes_px": {"A": list(a_label), "B": list(b_label)},
        "process_note_bbox_px": list(note_bbox),
    }
    return entities, render_map


def _cycle_points(
    *,
    bbox: Sequence[float],
    render_defaults: Mapping[str, Any],
    scenario: _WorkScenario,
) -> Dict[str, Tuple[float, float]]:
    """Return screen points for the rectangular cycle states."""

    if (
        scenario.pressure_low is None
        or scenario.pressure_high is None
        or scenario.volume_left is None
        or scenario.volume_right is None
    ):
        raise ValueError("cycle scenario is missing rectangle bounds")
    volume_max = int(render_defaults["volume_max_l"])
    pressure_max = int(render_defaults["pressure_max_kpa"])
    return {
        "A": _plot_xy(
            bbox=bbox,
            volume_l=float(scenario.volume_left),
            pressure_kpa=float(scenario.pressure_low),
            volume_max_l=volume_max,
            pressure_max_kpa=pressure_max,
        ),
        "B": _plot_xy(
            bbox=bbox,
            volume_l=float(scenario.volume_left),
            pressure_kpa=float(scenario.pressure_high),
            volume_max_l=volume_max,
            pressure_max_kpa=pressure_max,
        ),
        "C": _plot_xy(
            bbox=bbox,
            volume_l=float(scenario.volume_right),
            pressure_kpa=float(scenario.pressure_high),
            volume_max_l=volume_max,
            pressure_max_kpa=pressure_max,
        ),
        "D": _plot_xy(
            bbox=bbox,
            volume_l=float(scenario.volume_right),
            pressure_kpa=float(scenario.pressure_low),
            volume_max_l=volume_max,
            pressure_max_kpa=pressure_max,
        ),
    }


def _draw_rectangular_cycle(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    render_defaults: Mapping[str, Any],
    scenario: _WorkScenario,
    theme,
    state_font,
    note_font,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Draw one rectangular PV cycle and return entity/render metadata."""

    points = _cycle_points(bbox=bbox, render_defaults=render_defaults, scenario=scenario)
    draw.polygon(
        [points["A"], points["B"], points["C"], points["D"]],
        fill=tuple(int(value) for value in theme.work_fill_rgb),
    )
    sequence = ("A", "B", "C", "D", "A") if str(scenario.cycle_direction) == "clockwise" else ("A", "D", "C", "B", "A")
    segment_bboxes: List[List[float]] = []
    for start_label, end_label in zip(sequence[:-1], sequence[1:]):
        start = points[str(start_label)]
        end = points[str(end_label)]
        draw_arrow(
            draw,
            start=start,
            end=end,
            fill=tuple(int(value) for value in theme.process_rgb),
            width=int(render_defaults["cycle_line_width_px"]),
            head_length_px=float(render_defaults["arrow_head_length_px"]),
            head_width_px=float(render_defaults["arrow_head_width_px"]),
        )
        segment_bboxes.append(_arrow_bbox(start, end, padding_px=float(render_defaults["arrow_head_width_px"]) + 8.0))
    label_offsets = {
        "A": (-28.0, 28.0),
        "B": (-28.0, -28.0),
        "C": (28.0, -28.0),
        "D": (28.0, 28.0),
    }
    state_label_bboxes: Dict[str, List[float]] = {}
    for label, point in points.items():
        dx, dy = label_offsets[str(label)]
        state_label_bboxes[str(label)] = _draw_state_label(
            draw,
            text=str(label),
            center=(float(point[0] + dx), float(point[1] + dy)),
            font=state_font,
            theme=theme,
        )
    direction_text = "clockwise" if int(scenario.work_value) > 0 else "counterclockwise"
    center_x = float((points["A"][0] + points["C"][0]) / 2.0)
    center_y = float((points["A"][1] + points["C"][1]) / 2.0)
    note_bbox = _draw_text_tag(
        draw,
        text=str(direction_text),
        center=(center_x, center_y),
        font=note_font,
        fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.label_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.label_text_rgb),
        stroke_width_px=2,
    )
    area_bbox = _bbox_union(points["A"] + points["C"])
    witness_bbox = _bbox_union(area_bbox, *segment_bboxes, *state_label_bboxes.values())
    entities = [
        {
            "entity_id": "work_cycle_path",
            "entity_type": "pv_cycle_path",
            "bbox_px": _bbox_union(*segment_bboxes),
            "meta": {
                "cycle_direction": str(scenario.cycle_direction),
                "work_j": int(scenario.work_value),
                "pressure_low_kpa": int(scenario.pressure_low or 0),
                "pressure_high_kpa": int(scenario.pressure_high or 0),
                "volume_left_l": int(scenario.volume_left or 0),
                "volume_right_l": int(scenario.volume_right or 0),
            },
        },
        {
            "entity_id": "work_area",
            "entity_type": "pv_net_work_area",
            "bbox_px": list(area_bbox),
            "meta": {"work_j": int(scenario.work_value), "sign": _sign_for_work(int(scenario.work_value))},
        },
        {
            "entity_id": "work_witness_region",
            "entity_type": "pv_work_witness",
            "bbox_px": list(witness_bbox),
            "meta": {"members": ["work_cycle_path", "work_area"], "work_j": int(scenario.work_value)},
        },
    ]
    render_map = {
        "cycle_state_points_px": {key: [round(float(point[0]), 3), round(float(point[1]), 3)] for key, point in points.items()},
        "cycle_segment_bboxes_px": [list(bbox_value) for bbox_value in segment_bboxes],
        "work_area_bbox_px": list(area_bbox),
        "work_witness_region_bbox_px": list(witness_bbox),
        "state_label_bboxes_px": {key: list(value) for key, value in state_label_bboxes.items()},
        "cycle_note_bbox_px": list(note_bbox),
    }
    return entities, render_map


def _draw_mini_axes(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    render_defaults: Mapping[str, Any],
    scene_variant: str,
    theme,
    tick_font,
) -> Dict[str, Any]:
    """Draw one compact PV-axis frame for a process option."""

    left, top, right, bottom = [float(value) for value in bbox[:4]]
    draw_rounded_rect(
        draw,
        tuple(float(value) for value in bbox),
        radius=8,
        fill=tuple(int(value) for value in theme.plot_fill_rgb),
        outline=tuple(int(value) for value in theme.plot_outline_rgb),
        width=2,
    )
    for volume in (0, 4, 8, 12):
        x, _ = _plot_xy(
            bbox=bbox,
            volume_l=float(volume),
            pressure_kpa=0.0,
            volume_max_l=int(render_defaults["volume_max_l"]),
            pressure_max_kpa=int(render_defaults["pressure_max_kpa"]),
        )
        draw.line([(float(x), float(top)), (float(x), float(bottom))], fill=tuple(int(value) for value in theme.grid_rgb), width=1)
    for pressure in (0, 5, 10):
        _, y = _plot_xy(
            bbox=bbox,
            volume_l=0.0,
            pressure_kpa=float(pressure),
            volume_max_l=int(render_defaults["volume_max_l"]),
            pressure_max_kpa=int(render_defaults["pressure_max_kpa"]),
        )
        draw.line([(float(left), float(y)), (float(right), float(y))], fill=tuple(int(value) for value in theme.grid_rgb), width=1)
    draw_arrow(
        draw,
        start=(float(left + 14.0), float(bottom - 12.0)),
        end=(float(right - 12.0), float(bottom - 12.0)),
        fill=tuple(int(value) for value in theme.axis_rgb),
        width=3,
        head_length_px=13.0,
        head_width_px=11.0,
    )
    draw_arrow(
        draw,
        start=(float(left + 14.0), float(bottom - 12.0)),
        end=(float(left + 14.0), float(top + 12.0)),
        fill=tuple(int(value) for value in theme.axis_rgb),
        width=3,
        head_length_px=13.0,
        head_width_px=11.0,
    )
    v_label = draw_centered_text(
        draw,
        text="V",
        center=(float(right - 14.0), float(bottom + 12.0)),
        font=tick_font,
        fill=tuple(int(value) for value in theme.axis_text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.axis_text_rgb)),
        stroke_width=1,
    )
    p_label = draw_centered_text(
        draw,
        text="P",
        center=(float(left - 10.0), float(top + 12.0)),
        font=tick_font,
        fill=tuple(int(value) for value in theme.axis_text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.axis_text_rgb)),
        stroke_width=1,
    )
    return {
        "mini_plot_bbox_px": [round(float(value), 3) for value in bbox],
        "mini_axis_bbox_px": _bbox_union(bbox, v_label, p_label),
        "scene_variant": str(scene_variant),
    }


def _draw_sign_choice_scene(
    draw: ImageDraw.ImageDraw,
    *,
    render_defaults: Mapping[str, Any],
    scene_spec: _SceneSpec,
    theme,
    tick_font,
    label_font,
    option_font,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Draw eight labeled mini-process PV diagrams."""

    entities: List[Dict[str, Any]] = []
    option_bboxes: Dict[str, List[float]] = {}
    option_process_bboxes: Dict[str, List[float]] = {}
    option_signs: Dict[str, str] = {}
    offset_x = float(render_defaults.get("layout_offset_x_px", 0))
    offset_y = float(render_defaults.get("layout_offset_y_px", 0))
    for index, candidate in enumerate(scene_spec.process_candidates):
        col = int(index % 4)
        row = int(index // 4)
        cell_left = float(render_defaults["mini_plot_left_px"]) + float(offset_x) + (float(render_defaults["mini_cell_width_px"]) + float(render_defaults["mini_cell_gap_x_px"])) * float(col)
        cell_top = float(render_defaults["mini_plot_top_px"]) + float(offset_y) + (float(render_defaults["mini_cell_height_px"]) + float(render_defaults["mini_cell_gap_y_px"])) * float(row)
        cell_bbox = [
            float(cell_left),
            float(cell_top),
            float(cell_left + float(render_defaults["mini_cell_width_px"])),
            float(cell_top + float(render_defaults["mini_cell_height_px"])),
        ]
        mini_bbox = [
            float(cell_bbox[0] + 58.0),
            float(cell_bbox[1] + 34.0),
            float(cell_bbox[2] - 18.0),
            float(cell_bbox[3] - 24.0),
        ]
        label_bbox = _draw_state_label(
            draw,
            text=str(candidate.letter),
            center=(float(cell_bbox[0] + 24.0), float(cell_bbox[1] + 16.0)),
            font=option_font,
            theme=theme,
        )
        axes_meta = _draw_mini_axes(
            draw,
            bbox=mini_bbox,
            render_defaults=render_defaults,
            scene_variant=str(scene_spec.scene_variant),
            theme=theme,
            tick_font=tick_font,
        )
        start = _plot_xy(
            bbox=mini_bbox,
            volume_l=float(candidate.volume_start),
            pressure_kpa=float(candidate.pressure_start),
            volume_max_l=int(render_defaults["volume_max_l"]),
            pressure_max_kpa=int(render_defaults["pressure_max_kpa"]),
        )
        end = _plot_xy(
            bbox=mini_bbox,
            volume_l=float(candidate.volume_end),
            pressure_kpa=float(candidate.pressure_end),
            volume_max_l=int(render_defaults["volume_max_l"]),
            pressure_max_kpa=int(render_defaults["pressure_max_kpa"]),
        )
        draw_arrow(
            draw,
            start=start,
            end=end,
            fill=tuple(int(value) for value in theme.process_rgb),
            width=max(5, int(render_defaults["process_line_width_px"]) - 2),
            head_length_px=20.0,
            head_width_px=18.0,
        )
        process_bbox = _arrow_bbox(start, end, padding_px=24.0)
        option_bbox = _bbox_union(cell_bbox, label_bbox, axes_meta["mini_axis_bbox_px"], process_bbox)
        option_bboxes[str(candidate.letter)] = list(option_bbox)
        option_process_bboxes[str(candidate.letter)] = list(process_bbox)
        option_signs[str(candidate.letter)] = str(candidate.sign)
        entities.append(
            {
                "entity_id": f"option_{str(candidate.letter)}",
                "entity_type": "candidate_pv_process",
                "bbox_px": list(option_bbox),
                "meta": {
                    "option_letter": str(candidate.letter),
                    "sign": str(candidate.sign),
                    "is_correct": str(candidate.letter) == str(scene_spec.correct_option_letter),
                    "pressure_start_kpa": int(candidate.pressure_start),
                    "pressure_end_kpa": int(candidate.pressure_end),
                    "volume_start_l": int(candidate.volume_start),
                    "volume_end_l": int(candidate.volume_end),
                    "delta_volume_l": int(candidate.volume_end - candidate.volume_start),
                },
            }
        )
        entities.append(
            {
                "entity_id": f"option_{str(candidate.letter)}_process",
                "entity_type": "candidate_pv_process_arrow",
                "bbox_px": list(process_bbox),
                "meta": {
                    "option_letter": str(candidate.letter),
                    "sign": str(candidate.sign),
                    "is_correct": str(candidate.letter) == str(scene_spec.correct_option_letter),
                    "pressure_start_kpa": int(candidate.pressure_start),
                    "pressure_end_kpa": int(candidate.pressure_end),
                    "volume_start_l": int(candidate.volume_start),
                    "volume_end_l": int(candidate.volume_end),
                    "delta_volume_l": int(candidate.volume_end - candidate.volume_start),
                },
            }
        )

    target_text = f"target: {str(scene_spec.target_sign)} work"
    target_bbox = _draw_text_tag(
        draw,
        text=target_text,
        center=(float(render_defaults["mini_plot_left_px"] + 540.0 + offset_x), float(render_defaults["canvas_height"] - 42.0 + offset_y)),
        font=label_font,
        fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.label_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.label_text_rgb),
        stroke_width_px=2,
    )
    entities.append(
        {
            "entity_id": "target_sign_label",
            "entity_type": "target_sign_label",
            "bbox_px": list(target_bbox),
            "meta": {"target_sign": str(scene_spec.target_sign)},
        }
    )
    return entities, {
        "option_bboxes_px": {key: list(value) for key, value in option_bboxes.items()},
        "option_process_bboxes_px": {key: list(value) for key, value in option_process_bboxes.items()},
        "option_signs": dict(option_signs),
        "correct_option_letter": str(scene_spec.correct_option_letter),
        "target_sign": str(scene_spec.target_sign),
        "target_sign_label_bbox_px": list(target_bbox),
    }


def _render_scene(
    *,
    background: Image.Image,
    render_defaults: Mapping[str, Any],
    accent_color_name: str,
    scene_spec: _SceneSpec,
    diagram_style: Any | None = None,
    font_family: str | None = None,
) -> _RenderedScene:
    """Render one PV diagram and return trace metadata."""

    image = background.copy()
    draw = ImageDraw.Draw(image)
    theme = build_physics_pv_diagram_theme(str(accent_color_name), diagram_style=diagram_style)
    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=True, font_family=font_family)
    tick_font = load_font(int(render_defaults["tick_font_size_px"]), bold=False, font_family=font_family)
    state_font = load_font(int(render_defaults["state_font_size_px"]), bold=True, font_family=font_family)
    option_font = load_font(int(render_defaults["option_font_size_px"]), bold=True, font_family=font_family)
    note_font = load_font(int(render_defaults["note_font_size_px"]), bold=True, font_family=font_family)

    scene_entities: List[Dict[str, Any]] = []
    render_map: Dict[str, Any] = {
        "accent_color_name": str(accent_color_name),
        "technical_diagram_frame_mode": str(getattr(diagram_style, "frame_mode", "none")),
        "scene_variant": str(scene_spec.scene_variant),
        "query_id": str(scene_spec.query_id),
    }

    if str(scene_spec.query_id) == "work_value":
        plot = _plot_bbox(render_defaults)
        axes_meta = _draw_axes(
            draw,
            bbox=plot,
            render_defaults=render_defaults,
            scene_variant=str(scene_spec.scene_variant),
            theme=theme,
            tick_font=tick_font,
            label_font=label_font,
            include_tick_numbers=True,
        )
        scene_entities.append(
            {
                "entity_id": "pv_axes",
                "entity_type": "pv_axes",
                "bbox_px": list(axes_meta["axis_bbox_px"]),
                "meta": {
                    "pressure_units": "kPa",
                    "volume_units": "L",
                    "work_unit_equivalence": "1 kPa*L = 1 J",
                },
            }
        )
        note_bbox = _draw_text_tag(
            draw,
            text="1 kPa*L = 1 J",
            center=(float(plot[2] - 120.0), float(plot[1] - 36.0)),
            font=note_font,
            fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
            outline_rgb=tuple(int(value) for value in theme.label_outline_rgb),
            text_rgb=tuple(int(value) for value in theme.label_text_rgb),
            stroke_width_px=2,
        )
        scene_entities.append(
            {
                "entity_id": "unit_equivalence_label",
                "entity_type": "unit_equivalence_label",
                "bbox_px": list(note_bbox),
                "meta": {"text": "1 kPa*L = 1 J"},
            }
        )
        if scene_spec.work_scenario is None:
            raise ValueError("work_value render requires a work scenario")
        if str(scene_spec.work_scenario.work_mode) == "single_process":
            entities, scenario_render_map = _draw_single_process(
                draw,
                bbox=plot,
                render_defaults=render_defaults,
                scenario=scene_spec.work_scenario,
                theme=theme,
                state_font=state_font,
                note_font=note_font,
            )
        else:
            entities, scenario_render_map = _draw_rectangular_cycle(
                draw,
                bbox=plot,
                render_defaults=render_defaults,
                scenario=scene_spec.work_scenario,
                theme=theme,
                state_font=state_font,
                note_font=note_font,
            )
        scene_entities.extend(entities)
        render_map.update(axes_meta)
        render_map.update(scenario_render_map)
    else:
        entities, sign_render_map = _draw_sign_choice_scene(
            draw,
            render_defaults=render_defaults,
            scene_spec=scene_spec,
            theme=theme,
            tick_font=tick_font,
            label_font=label_font,
            option_font=option_font,
        )
        scene_entities.extend(entities)
        render_map.update(sign_render_map)

    entity_bbox_map = {
        str(entity["entity_id"]): list(entity["bbox_px"])
        for entity in scene_entities
        if entity.get("bbox_px") is not None
    }
    annotation_bboxes = [
        list(entity_bbox_map[entity_id])
        for entity_id in scene_spec.annotation_entity_ids
        if str(entity_id) in entity_bbox_map
    ]
    render_map["annotation_entity_ids"] = list(scene_spec.annotation_entity_ids)
    render_map["annotation_bboxes_px"] = [list(bbox) for bbox in annotation_bboxes]
    return _RenderedScene(
        image=image,
        annotation_bboxes=[list(bbox) for bbox in annotation_bboxes],
        annotation_entity_ids=list(scene_spec.annotation_entity_ids),
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
    )


def _pv_content_bbox(
    *,
    render_defaults: Mapping[str, Any],
    scene_spec: _SceneSpec,
) -> List[float]:
    """Return a conservative bbox for the whole PV content before layout offset."""

    if str(scene_spec.query_id) == "work_value":
        left = float(render_defaults["plot_left_px"]) - 92.0
        top = float(render_defaults["plot_top_px"]) - 72.0
        right = float(render_defaults["plot_left_px"]) + float(render_defaults["plot_width_px"]) + 82.0
        bottom = float(render_defaults["plot_top_px"]) + float(render_defaults["plot_height_px"]) + 88.0
    else:
        column_count = 4
        row_count = 2
        left = float(render_defaults["mini_plot_left_px"]) - 14.0
        top = float(render_defaults["mini_plot_top_px"]) - 26.0
        right = (
            float(render_defaults["mini_plot_left_px"])
            + (float(render_defaults["mini_cell_width_px"]) * float(column_count))
            + (float(render_defaults["mini_cell_gap_x_px"]) * float(column_count - 1))
        )
        bottom = max(
            float(render_defaults["mini_plot_top_px"])
            + (float(render_defaults["mini_cell_height_px"]) * float(row_count))
            + (float(render_defaults["mini_cell_gap_y_px"]) * float(row_count - 1))
            + 12.0,
            float(render_defaults["canvas_height"]) - 16.0,
        )
    return [
        round(float(left), 3),
        round(float(top), 3),
        round(float(right), 3),
        round(float(bottom), 3),
    ]


def _resolve_pv_layout_placement(
    *,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    scene_spec: _SceneSpec,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve whole-PV-diagram placement before rendering and annotation projection."""

    canvas_width = int(render_defaults["canvas_width"])
    canvas_height = int(render_defaults["canvas_height"])
    content_bbox = _pv_content_bbox(render_defaults=render_defaults, scene_spec=scene_spec)
    content_left, content_top, content_right, content_bottom = [float(value) for value in content_bbox]
    jitter = resolve_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.pv_layout",
    )
    min_margin = int(jitter.get("min_margin_px", 8))
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
    adjusted["layout_offset_x_px"] = int(dx)
    adjusted["layout_offset_y_px"] = int(dy)

    content_width = round(float(content_right) - float(content_left), 3)
    content_height = round(float(content_bottom) - float(content_top), 3)
    final_bbox = [
        round(float(content_left) + float(dx), 3),
        round(float(content_top) + float(dy), 3),
        round(float(content_right) + float(dx), 3),
        round(float(content_bottom) + float(dy), 3),
    ]
    placement = dict(jitter)
    placement.update(
        {
            "mode": "whole_pv_diagram_offset",
            "content_bbox_px": list(content_bbox),
            "content_size_px": [float(content_width), float(content_height)],
            "final_content_bbox_px": list(final_bbox),
            "canvas_size_px": [int(canvas_width), int(canvas_height)],
            "free_space_px": [
                round(float(canvas_width) - float(content_width), 3),
                round(float(canvas_height) - float(content_height), 3),
            ],
            "available_offset_x_px": [int(min_dx), int(max_dx)],
            "available_offset_y_px": [int(min_dy), int(max_dy)],
            "sampled_offset_px": [int(requested_dx), int(requested_dy)],
            "final_offset_px": [int(dx), int(dy)],
            "default_origin_px": [round(float(content_left), 3), round(float(content_top), 3)],
            "final_origin_px": [round(float(content_left) + float(dx), 3), round(float(content_top) + float(dy), 3)],
            "dx_px": int(dx),
            "dy_px": int(dy),
        }
    )
    return adjusted, placement


def _answer_type(query_id: str) -> str:
    """Return answer type for the public query."""

    if str(query_id) == "process_sign_choice":
        return "option_letter"
    return "integer"


def _build_prompt_examples(query_id: str) -> Tuple[str, str]:
    """Return one stable prompt JSON example for the active PV query."""

    if str(query_id) == "process_sign_choice":
        return build_prompt_json_examples(
            annotation_value=[[104, 88, 430, 284]],
            answer_type="option_letter",
        )
    return build_prompt_json_examples(
        annotation_value=[[248, 188, 710, 526]],
        answer_type="integer",
    )


def _target_sign_description(target_sign: str | None) -> str:
    """Return prompt-facing target-sign wording."""

    if str(target_sign) == "positive":
        return "positive"
    if str(target_sign) == "negative":
        return "negative"
    return "zero"


class _PhysicsThermodynamicsPVDiagramBaseTask:
    """Return one pressure-volume diagram reasoning question."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "thermodynamics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        rendered_scene: _RenderedScene | None = None
        scene_spec: _SceneSpec | None = None

        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                scene_spec = _sample_scene_spec(
                    attempt_rng,
                    axes=axes,
                    params=params,
                )
            except ValueError:
                continue

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
                    "canvas_width",
                    "canvas_height",
                    "plot_left_px",
                    "plot_top_px",
                    "plot_width_px",
                    "plot_height_px",
                    "mini_plot_left_px",
                    "mini_plot_top_px",
                    "mini_cell_width_px",
                    "mini_cell_height_px",
                    "mini_cell_gap_x_px",
                    "mini_cell_gap_y_px",
                    "axis_width_px",
                    "grid_line_width_px",
                    "bold_grid_line_width_px",
                    "process_line_width_px",
                    "cycle_line_width_px",
                    "arrow_head_length_px",
                    "arrow_head_width_px",
                    "label_font_size_px",
                    "tick_font_size_px",
                    "state_font_size_px",
                    "option_font_size_px",
                    "note_font_size_px",
                    "label_stroke_width_px",
                    "pressure_max_kpa",
                    "volume_max_l",
                )
            }
            render_defaults, layout_placement_meta = _resolve_pv_layout_placement(
                render_defaults=render_defaults,
                params=params,
                instance_seed=int(instance_seed),
                scene_spec=scene_spec,
            )
            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                scene_id=SCENE_ID,
                task_group=self.task_group,
                canvas_width=int(render_defaults["canvas_width"]),
                canvas_height=int(render_defaults["canvas_height"]),
                instance_seed=int(instance_seed),
                params=params,
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.render.font_family",
                params=params,
            )
            font_record = get_font_family_record(str(font_family))
            rendered_scene = _render_scene(
                background=background,
                render_defaults=render_defaults,
                accent_color_name=str(axes.accent_color_name),
                scene_spec=scene_spec,
                diagram_style=diagram_style,
                font_family=str(font_family),
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
                    "object_description_clean_grid",
                    "object_description_paper_grid",
                    "object_description_bold_grid",
                    "answer_hint_work_value",
                    "answer_hint_process_sign_choice",
                    "annotation_hint_work_value",
                    "annotation_hint_process_sign_choice",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            json_example, json_example_answer_only = _build_prompt_examples(str(axes.query_id))
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(axes.query_id),
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                    "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                    "target_sign": _target_sign_description(axes.target_sign),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_type = _answer_type(str(axes.query_id))
            if str(axes.query_id) == "work_value":
                if scene_spec.work_scenario is None:
                    raise RuntimeError("missing work scenario after PV scene render")
                answer_value: int | str = int(scene_spec.work_scenario.work_value)
            else:
                answer_value = str(scene_spec.correct_option_letter)
            answer_gt = TypedValue(type=str(answer_type), value=answer_value)
            annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in rendered_scene.annotation_bboxes])
            complexity = build_physics_pv_diagram_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=TASK_ID,
                scene_variant=str(axes.scene_variant),
                query_id=str(axes.query_id),
                work_mode=axes.work_mode,
                target_sign=axes.target_sign,
                work_magnitude=abs(int(answer_value)) if str(answer_type) == "integer" else 0,
                option_count=len(OPTION_LETTERS) if str(axes.query_id) == "process_sign_choice" else 0,
                annotation_count=len(rendered_scene.annotation_bboxes),
            )
            scenario_payload: Dict[str, Any] = {}
            if scene_spec.work_scenario is not None:
                scenario_payload = {
                    "work_mode": str(scene_spec.work_scenario.work_mode),
                    "work_value": int(scene_spec.work_scenario.work_value),
                    "work_sign": _sign_for_work(int(scene_spec.work_scenario.work_value)),
                    "pressure_kpa": scene_spec.work_scenario.pressure,
                    "volume_start_l": scene_spec.work_scenario.volume_start,
                    "volume_end_l": scene_spec.work_scenario.volume_end,
                    "pressure_low_kpa": scene_spec.work_scenario.pressure_low,
                    "pressure_high_kpa": scene_spec.work_scenario.pressure_high,
                    "volume_left_l": scene_spec.work_scenario.volume_left,
                    "volume_right_l": scene_spec.work_scenario.volume_right,
                    "cycle_direction": scene_spec.work_scenario.cycle_direction,
                }
            candidate_payload = [
                {
                    "option_letter": str(candidate.letter),
                    "sign": str(candidate.sign),
                    "pressure_start_kpa": int(candidate.pressure_start),
                    "pressure_end_kpa": int(candidate.pressure_end),
                    "volume_start_l": int(candidate.volume_start),
                    "volume_end_l": int(candidate.volume_end),
                    "delta_volume_l": int(candidate.volume_end - candidate.volume_start),
                    "is_correct": str(candidate.letter) == str(scene_spec.correct_option_letter),
                }
                for candidate in scene_spec.process_candidates
            ]
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_pv_diagram_{str(axes.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.query_id),
                        "work_mode": axes.work_mode,
                        "target_sign": axes.target_sign,
                        "accent_color_name": str(axes.accent_color_name),
                        "target_answer": answer_value,
                        "answer_type": str(answer_type),
                        "scenario": dict(scenario_payload),
                        "process_candidates": list(candidate_payload),
                        "annotation_entity_ids": list(rendered_scene.annotation_entity_ids),
                    },
                },
                "query_spec": {
                    "query_id": str(axes.query_id),
                    "work_mode": axes.work_mode,
                    "target_sign": axes.target_sign,
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.query_id),
                        "work_mode": axes.work_mode,
                        "target_sign": axes.target_sign,
                        "accent_color_name": str(axes.accent_color_name),
                        "correct_option_letter": axes.correct_option_letter,
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_id_probabilities": dict(axes.query_id_probabilities),
                        "work_mode_probabilities": dict(axes.work_mode_probabilities),
                        "target_sign_probabilities": dict(axes.target_sign_probabilities),
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
                        "scope": "pv_diagram",
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
                    "work_mode": axes.work_mode,
                    "target_sign": axes.target_sign,
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": answer_value,
                    "answer_type": str(answer_type),
                    "work_answer_support": list(_work_answer_support(params)),
                    "pressure_support": list(_pressure_support(params)),
                    "volume_support": list(_volume_support(params)),
                    "option_letters": list(OPTION_LETTERS),
                    "scenario": dict(scenario_payload),
                    "process_candidates": list(candidate_payload),
                    "correct_option_letter": scene_spec.correct_option_letter,
                    "annotation_entity_ids": list(rendered_scene.annotation_entity_ids),
                },
                "witness_symbolic": {
                    "type": "object_set",
                    "ids": [str(item) for item in rendered_scene.annotation_entity_ids],
                },
                "projected_annotation": {
                    "type": "bbox_set",
                    "bbox_set": [list(bbox) for bbox in rendered_scene.annotation_bboxes],
                    "pixel_bbox_set": [list(bbox) for bbox in rendered_scene.annotation_bboxes],
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
                complexity=complexity,
                task_versions=default_task_versions(),
                scene_id=SCENE_ID,
                query_id=str(axes.query_id),
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")


@register_task
class PhysicsThermodynamicsPVWorkValueTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsThermodynamicsPVDiagramBaseTask,
):
    """Return signed work from a highlighted PV process or cycle."""

    task_id = "task_physics__pv_diagram__pv_work_value"
    fixed_query_id = "work_value"


@register_task
class PhysicsThermodynamicsPVProcessSignChoiceTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsThermodynamicsPVDiagramBaseTask,
):
    """Choose the labeled PV process with the requested work sign."""

    task_id = "task_physics__pv_diagram__pv_process_sign_choice"
    fixed_query_id = "process_sign_choice"
