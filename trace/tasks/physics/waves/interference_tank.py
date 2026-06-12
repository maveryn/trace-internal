"""Physics wave-interference tasks for two-source ripple-tank diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_many as _bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.drawing import draw_centered_text, draw_dashed_line, draw_rounded_rect
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
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES, build_physics_waves_theme
from ..shared.support_sampling import resolve_integer_support
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "physics_waves_interference_tank"
SCENE_ID = "wave_interference"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "clean_tank",
    "grid_tank",
    "lab_sheet",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "interference_point_choice",
    "path_difference_value",
)
SUPPORTED_PHASE_RELATIONS: Tuple[str, ...] = ("in_phase", "opposite_phase")
SUPPORTED_TARGET_CONDITIONS: Tuple[str, ...] = ("constructive", "destructive")
OPTION_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D", "E")
SOURCE_SEPARATION_STEPS = 8
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "clean_tank": SUPPORTED_QUERY_IDS,
    "grid_tank": SUPPORTED_QUERY_IDS,
    "lab_sheet": SUPPORTED_QUERY_IDS,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for wave-interference scenes."""

    canvas_width: int = 1180
    canvas_height: int = 760
    board_left_px: int = 70
    board_top_px: int = 50
    board_width_px: int = 980
    board_height_px: int = 620
    half_wavelength_px: int = 50
    ring_count: int = 10
    grid_line_width_px: int = 1
    source_radius_px: int = 24
    candidate_radius_px: int = 15
    point_radius_px: int = 18
    wavefront_width_px: int = 2
    guide_width_px: int = 4
    label_font_size_px: int = 22
    source_font_size_px: int = 21
    candidate_font_size_px: int = 23
    note_font_size_px: int = 20
    path_difference_step_support: Tuple[int, ...] = (1, 2, 3, 4, 5)


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query axes for one instance."""

    scene_variant: str
    query_id: str
    phase_relation: str
    target_condition: str | None
    correct_option_letter: str | None
    path_difference_steps: int | None
    accent_color_name: str
    target_answer: int | str
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    phase_relation_probabilities: Dict[str, float]
    target_condition_probabilities: Dict[str, float]
    correct_option_letter_probabilities: Dict[str, float]
    path_difference_steps_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _PointTemplate:
    """One exact point described by half-wavelength source distances."""

    r1_steps: int
    r2_steps: int
    sign_y: int
    x_steps: float
    y_steps: float


@dataclass(frozen=True)
class _CandidatePoint:
    """One labeled interference candidate point."""

    letter: str
    x_steps: float
    y_steps: float
    r1_steps: int
    r2_steps: int
    condition: str
    is_correct: bool


@dataclass(frozen=True)
class _ChoiceScenario:
    """One two-source interference point-choice scenario."""

    phase_relation: str
    target_condition: str
    candidates: Tuple[_CandidatePoint, ...]
    correct_option_letter: str


@dataclass(frozen=True)
class _PathScenario:
    """One two-source path-difference value scenario."""

    phase_relation: str
    point_x_steps: float
    point_y_steps: float
    r1_steps: int
    r2_steps: int
    path_difference_steps: int


@dataclass(frozen=True)
class _SceneSpec:
    """Resolved symbolic wave-interference scene."""

    scene_variant: str
    query_id: str
    phase_relation: str
    choice_scenario: _ChoiceScenario | None
    path_scenario: _PathScenario | None
    target_answer: int | str
    annotation_entity_ids: Tuple[str, ...]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered wave scene plus prompt-facing annotation metadata."""

    image: Image.Image
    annotation_type: str
    annotation_bboxes: List[List[float]]
    annotation_bbox_map: Dict[str, List[float]]
    annotation_points: List[List[float]]
    annotation_key_by_entity_id: Dict[str, str]
    annotation_entity_ids: List[str]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "waves")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="waves", apply_prob=0.5)


def _with_sampling_divisor(params: Mapping[str, Any], *, divisor: int, explicit_keys: Sequence[str]) -> Mapping[str, Any]:
    """No-op hook for axis-decoupling call sites."""

    _ = int(divisor), explicit_keys
    return params


def _uniform_string_probability_map(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    """Return a deterministic uniform probability map over a finite string support."""

    support = tuple(str(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(selected): 1.0}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def _path_difference_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return configured half-wavelength path-difference support."""

    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="path_difference_step_support",
        fallback=_DEFAULTS.path_difference_step_support,
    )


def _resolve_scene_query(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float], str, Dict[str, float]]:
    """Resolve the public scene/query axes."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.scene_query")
    return resolve_compatible_scene_query_ids(
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


def _resolve_phase_relation(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    """Resolve whether the two sources are in phase or opposite phase."""

    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.phase_relation"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PHASE_RELATIONS,
        explicit_key="phase_relation",
        weights_key="phase_relation_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_PHASE_RELATIONS,
        balance_flag_key="balanced_phase_relation_sampling",
        explicit_key="phase_relation",
        weights_key="phase_relation_weights",
        sampling_namespace=f"{TASK_ID}.phase_relation",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_target_condition(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str | None, Dict[str, float]]:
    """Resolve the requested interference condition for choice tasks."""

    if str(query_id) != "interference_point_choice":
        return None, {}
    adjusted_params = _with_sampling_divisor(params, divisor=len(SUPPORTED_QUERY_IDS), explicit_keys=("target_condition",))
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.target_condition"),
        params=adjusted_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_TARGET_CONDITIONS,
        explicit_key="target_condition",
        weights_key="target_condition_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=adjusted_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_TARGET_CONDITIONS,
        balance_flag_key="balanced_target_condition_sampling",
        explicit_key="target_condition",
        weights_key="target_condition_weights",
        sampling_namespace=f"{TASK_ID}.target_condition",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_correct_option_letter(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str | None, Dict[str, float]]:
    """Resolve the correct candidate label for point-choice scenes."""

    if str(query_id) != "interference_point_choice":
        return None, {}
    adjusted_params = dict(_with_sampling_divisor(params, divisor=1, explicit_keys=("correct_option_letter",)))
    if adjusted_params.get("correct_option_letter") is None and adjusted_params.get("target_answer") is not None:
        adjusted_params["correct_option_letter"] = str(adjusted_params["target_answer"]).strip().upper()
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.correct_option_letter"),
        params=adjusted_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=OPTION_LETTERS,
        explicit_key="correct_option_letter",
        weights_key="option_letter_weights",
    )
    balanced_enabled = bool(adjusted_params.get("balanced_option_letter_sampling", group_default(_GEN_DEFAULTS, "balanced_option_letter_sampling", True)))
    has_override = any(adjusted_params.get(str(key)) is not None for key in ("correct_option_letter", "option_letter_weights"))
    if bool(balanced_enabled) and not bool(has_override) and is_uniform_probability_map(probabilities):
        selected = str(OPTION_LETTERS[abs(int(instance_seed)) % len(OPTION_LETTERS)])
    else:
        selected = apply_balanced_variant_sampling(
            instance_seed=int(instance_seed),
            params=adjusted_params,
            gen_defaults=_GEN_DEFAULTS,
            selected_variant=str(selected),
            variant_probabilities=probabilities,
            supported_variants=OPTION_LETTERS,
            balance_flag_key="balanced_option_letter_sampling",
            explicit_key="correct_option_letter",
            weights_key="option_letter_weights",
            sampling_namespace=f"{TASK_ID}.correct_option_letter",
        )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_path_difference_steps(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[int | None, Dict[str, float]]:
    """Resolve the integer path difference in half-wavelength steps."""

    if str(query_id) != "path_difference_value":
        return None, {}
    support = tuple(int(value) for value in _path_difference_support(params) if int(value) > 0)
    if not support:
        raise ValueError("path_difference_value requires positive path-difference support")
    explicit = params.get("target_answer", params.get("path_difference_steps"))
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"unsupported path_difference target_answer: {selected}")
        return int(selected), uniform_probability_map(support, selected=int(selected))

    adjusted_params = _with_sampling_divisor(params, divisor=1, explicit_keys=("target_answer", "path_difference_steps"))
    balanced_enabled = bool(adjusted_params.get("balanced_target_answer_sampling", group_default(_GEN_DEFAULTS, "balanced_target_answer_sampling", True)))
    if bool(balanced_enabled):
        selection_index = resolve_selection_index(
            params=adjusted_params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}.target_answer.path_difference_value",
        )
        selected = int(support[int(selection_index) % len(support)])
    else:
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.path_difference_steps")
        selected = int(support[int(rng.randrange(len(support)))])
    return int(selected), uniform_probability_map(support)


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve scene/query/color/answer axes for one instance."""

    scene_variant, scene_probs, query_id, query_probs = _resolve_scene_query(int(instance_seed), params=params)
    phase_relation, phase_probs = _resolve_phase_relation(int(instance_seed), params=params)
    target_condition, condition_probs = _resolve_target_condition(int(instance_seed), params=params, query_id=str(query_id))
    correct_option_letter, option_probs = _resolve_correct_option_letter(int(instance_seed), params=params, query_id=str(query_id))
    path_difference_steps, path_probs = _resolve_path_difference_steps(int(instance_seed), params=params, query_id=str(query_id))

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.accent")
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

    if str(query_id) == "interference_point_choice":
        if correct_option_letter is None or target_condition is None:
            raise ValueError("interference_point_choice requires target condition and correct option")
        target_answer: int | str = str(correct_option_letter)
        target_probs = dict(option_probs)
    else:
        if path_difference_steps is None:
            raise ValueError("path_difference_value requires an integer target answer")
        target_answer = int(path_difference_steps)
        target_probs = dict(path_probs)

    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        phase_relation=str(phase_relation),
        target_condition=target_condition,
        correct_option_letter=correct_option_letter,
        path_difference_steps=path_difference_steps,
        accent_color_name=str(accent_name),
        target_answer=target_answer,
        scene_variant_probabilities={str(key): float(value) for key, value in sorted(scene_probs.items())},
        query_id_probabilities={str(key): float(value) for key, value in sorted(query_probs.items())},
        phase_relation_probabilities=dict(phase_probs),
        target_condition_probabilities=dict(condition_probs),
        correct_option_letter_probabilities=dict(option_probs),
        path_difference_steps_probabilities=dict(path_probs),
        accent_color_name_probabilities={str(key): float(value) for key, value in sorted(accent_probs.items())},
        target_answer_probabilities={str(key): float(value) for key, value in sorted(target_probs.items())},
    )


def _point_templates() -> Tuple[_PointTemplate, ...]:
    """Return feasible candidate points with exact half-wavelength distances."""

    templates: List[_PointTemplate] = []
    source_separation = float(SOURCE_SEPARATION_STEPS)
    for r1_steps in range(3, 11):
        for r2_steps in range(3, 11):
            x_from_s1 = ((r1_steps * r1_steps) - (r2_steps * r2_steps) + (SOURCE_SEPARATION_STEPS * SOURCE_SEPARATION_STEPS)) / (2.0 * source_separation)
            y_squared = float((r1_steps * r1_steps) - (x_from_s1 * x_from_s1))
            if float(y_squared) <= 1e-6:
                continue
            y_steps = math.sqrt(float(y_squared))
            x_steps = float(x_from_s1 - (source_separation / 2.0))
            if abs(float(x_steps)) > 5.9 or float(y_steps) > 4.9:
                continue
            for sign_y in (1, -1):
                templates.append(
                    _PointTemplate(
                        r1_steps=int(r1_steps),
                        r2_steps=int(r2_steps),
                        sign_y=int(sign_y),
                        x_steps=round(float(x_steps), 6),
                        y_steps=round(float(sign_y) * float(y_steps), 6),
                    )
                )
    return tuple(templates)


def _classify_condition(*, r1_steps: int, r2_steps: int, phase_relation: str) -> str:
    """Classify a point as constructive or destructive from phase parity."""

    source_2_offset = 0 if str(phase_relation) == "in_phase" else 1
    phase_1 = int(r1_steps) % 2
    phase_2 = (int(r2_steps) + int(source_2_offset)) % 2
    return "constructive" if int(phase_1) == int(phase_2) else "destructive"


def _template_distance(a: _PointTemplate, b: _PointTemplate) -> float:
    """Return distance between two point templates in half-wavelength coordinates."""

    return math.hypot(float(a.x_steps) - float(b.x_steps), float(a.y_steps) - float(b.y_steps))


def _select_spaced_templates(rng, *, pool: Sequence[_PointTemplate], count: int, existing: Sequence[_PointTemplate]) -> Tuple[_PointTemplate, ...]:
    """Select visually separated candidate templates."""

    shuffled = list(pool)
    rng.shuffle(shuffled)
    selected: List[_PointTemplate] = []
    for template in shuffled:
        if any(_template_distance(template, other) < 1.0 for other in tuple(existing) + tuple(selected)):
            continue
        selected.append(template)
        if len(selected) >= int(count):
            return tuple(selected)
    for template in shuffled:
        if template in selected or template in existing:
            continue
        selected.append(template)
        if len(selected) >= int(count):
            return tuple(selected)
    if len(selected) < int(count):
        raise ValueError("not enough spaced wave-interference candidate points")
    return tuple(selected)


def _sample_choice_scenario(rng, *, axes: _ResolvedAxes) -> _ChoiceScenario:
    """Build an interference point-choice scenario with one correct candidate."""

    if axes.target_condition is None or axes.correct_option_letter is None:
        raise ValueError("choice scenario requires target condition and correct option")
    templates = _point_templates()
    target_pool = [
        template
        for template in templates
        if _classify_condition(r1_steps=template.r1_steps, r2_steps=template.r2_steps, phase_relation=str(axes.phase_relation)) == str(axes.target_condition)
    ]
    distractor_pool = [
        template
        for template in templates
        if _classify_condition(r1_steps=template.r1_steps, r2_steps=template.r2_steps, phase_relation=str(axes.phase_relation)) != str(axes.target_condition)
    ]
    if not target_pool or len(distractor_pool) < len(OPTION_LETTERS) - 1:
        raise ValueError("not enough feasible wave-interference candidates")
    correct_template = target_pool[int(rng.randrange(len(target_pool)))]
    distractors = _select_spaced_templates(rng, pool=distractor_pool, count=len(OPTION_LETTERS) - 1, existing=(correct_template,))
    distractor_iter = iter(distractors)
    candidates: List[_CandidatePoint] = []
    for letter in OPTION_LETTERS:
        template = correct_template if str(letter) == str(axes.correct_option_letter) else next(distractor_iter)
        condition = _classify_condition(
            r1_steps=int(template.r1_steps),
            r2_steps=int(template.r2_steps),
            phase_relation=str(axes.phase_relation),
        )
        candidates.append(
            _CandidatePoint(
                letter=str(letter),
                x_steps=float(template.x_steps),
                y_steps=float(template.y_steps),
                r1_steps=int(template.r1_steps),
                r2_steps=int(template.r2_steps),
                condition=str(condition),
                is_correct=str(letter) == str(axes.correct_option_letter),
            )
        )
    return _ChoiceScenario(
        phase_relation=str(axes.phase_relation),
        target_condition=str(axes.target_condition),
        candidates=tuple(candidates),
        correct_option_letter=str(axes.correct_option_letter),
    )


def _sample_path_scenario(rng, *, axes: _ResolvedAxes) -> _PathScenario:
    """Build a path-difference value scenario."""

    if axes.path_difference_steps is None:
        raise ValueError("path-difference scenario requires target answer")
    templates = [
        template
        for template in _point_templates()
        if abs(int(template.r1_steps) - int(template.r2_steps)) == int(axes.path_difference_steps)
    ]
    if not templates:
        raise ValueError(f"no wave-interference path scenario for answer {axes.path_difference_steps}")
    template = templates[int(rng.randrange(len(templates)))]
    return _PathScenario(
        phase_relation=str(axes.phase_relation),
        point_x_steps=float(template.x_steps),
        point_y_steps=float(template.y_steps),
        r1_steps=int(template.r1_steps),
        r2_steps=int(template.r2_steps),
        path_difference_steps=abs(int(template.r1_steps) - int(template.r2_steps)),
    )


def _sample_scene_spec(rng, *, axes: _ResolvedAxes) -> _SceneSpec:
    """Sample one symbolic wave-interference scene."""

    if str(axes.query_id) == "interference_point_choice":
        scenario = _sample_choice_scenario(rng, axes=axes)
        return _SceneSpec(
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            phase_relation=str(axes.phase_relation),
            choice_scenario=scenario,
            path_scenario=None,
            target_answer=str(scenario.correct_option_letter),
            annotation_entity_ids=(f"candidate_{str(scenario.correct_option_letter)}",),
        )
    if str(axes.query_id) == "path_difference_value":
        scenario = _sample_path_scenario(rng, axes=axes)
        return _SceneSpec(
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            phase_relation=str(axes.phase_relation),
            choice_scenario=None,
            path_scenario=scenario,
            target_answer=int(scenario.path_difference_steps),
            annotation_entity_ids=("path_S1P", "path_S2P"),
        )
    raise ValueError(f"unsupported waves query id: {axes.query_id}")


def _line_bbox(start: Tuple[float, float], end: Tuple[float, float], *, padding_px: float) -> List[float]:
    """Return a conservative bbox for one line segment."""

    return [
        round(float(min(start[0], end[0]) - padding_px), 3),
        round(float(min(start[1], end[1]) - padding_px), 3),
        round(float(max(start[0], end[0]) + padding_px), 3),
        round(float(max(start[1], end[1]) + padding_px), 3),
    ]


def _board_bbox(render_defaults: Mapping[str, Any]) -> List[float]:
    """Return board bbox in pixels."""

    return [
        float(render_defaults["board_left_px"]),
        float(render_defaults["board_top_px"]),
        float(render_defaults["board_left_px"]) + float(render_defaults["board_width_px"]),
        float(render_defaults["board_top_px"]) + float(render_defaults["board_height_px"]),
    ]


def _wave_content_bbox(render_defaults: Mapping[str, Any]) -> List[float]:
    """Return a conservative bbox for the whole wave tank before placement."""

    board = _board_bbox(render_defaults)
    return [
        round(float(board[0]) - 8.0, 3),
        round(float(board[1]) - 8.0, 3),
        round(float(board[2]) + 8.0, 3),
        round(float(board[3]) + 8.0, 3),
    ]


def _resolve_wave_layout_placement(
    *,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve whole-tank placement before rendering and annotation projection."""

    canvas_width = int(render_defaults["canvas_width"])
    canvas_height = int(render_defaults["canvas_height"])
    content_bbox = _wave_content_bbox(render_defaults)
    content_left, content_top, content_right, content_bottom = [float(value) for value in content_bbox]
    jitter = resolve_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.wave_layout",
    )
    min_margin = int(jitter.get("min_margin_px", 18))
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
    adjusted["board_left_px"] = int(adjusted["board_left_px"]) + int(dx)
    adjusted["board_top_px"] = int(adjusted["board_top_px"]) + int(dy)

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
            "mode": "whole_wave_tank_offset",
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
            "dx_px": int(dx),
            "dy_px": int(dy),
        }
    )
    return adjusted, placement


def _source_positions(board: Sequence[float], *, unit_px: float) -> Dict[str, Tuple[float, float]]:
    """Return the two source centers in pixels."""

    cx = (float(board[0]) + float(board[2])) / 2.0
    cy = (float(board[1]) + float(board[3])) / 2.0
    half_sep = 0.5 * float(SOURCE_SEPARATION_STEPS) * float(unit_px)
    return {"S1": (float(cx - half_sep), float(cy)), "S2": (float(cx + half_sep), float(cy))}


def _point_to_px(board: Sequence[float], *, unit_px: float, x_steps: float, y_steps: float) -> Tuple[float, float]:
    """Project half-wavelength coordinates into pixels."""

    cx = (float(board[0]) + float(board[2])) / 2.0
    cy = (float(board[1]) + float(board[3])) / 2.0
    return (float(cx + (float(x_steps) * float(unit_px))), float(cy - (float(y_steps) * float(unit_px))))


def _draw_text_tag(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    fill_rgb: Sequence[int],
    outline_rgb: Sequence[int],
    text_rgb: Sequence[int],
    pad_x: float = 11.0,
    pad_y: float = 7.0,
) -> List[float]:
    """Draw a small rounded label and return its bbox."""

    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
    width = float(text_bbox[2] - text_bbox[0])
    height = float(text_bbox[3] - text_bbox[1])
    cx, cy = float(center[0]), float(center[1])
    bbox = [
        round(float(cx - (width / 2.0) - float(pad_x)), 3),
        round(float(cy - (height / 2.0) - float(pad_y)), 3),
        round(float(cx + (width / 2.0) + float(pad_x)), 3),
        round(float(cy + (height / 2.0) + float(pad_y)), 3),
    ]
    draw_rounded_rect(draw, tuple(float(value) for value in bbox), radius=9, fill=fill_rgb, outline=outline_rgb, width=2)
    text_draw_bbox = draw_centered_text(
        draw,
        text=str(text),
        center=(cx, cy),
        font=font,
        fill=text_rgb,
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(text_rgb)),
        stroke_width=1,
    )
    return _bbox_union(bbox, text_draw_bbox)


def _draw_tank(draw: ImageDraw.ImageDraw, *, board: Sequence[float], scene_variant: str, theme, render_defaults: Mapping[str, Any]) -> None:
    """Draw the ripple-tank panel and optional grid."""

    fill_rgb = theme.tank_alt_fill_rgb if str(scene_variant) == "lab_sheet" else theme.tank_fill_rgb
    draw_rounded_rect(draw, tuple(float(value) for value in board), radius=12, fill=fill_rgb, outline=theme.tank_outline_rgb, width=3)
    left, top, right, bottom = [float(value) for value in board[:4]]
    if str(scene_variant) in {"grid_tank", "lab_sheet"}:
        unit_px = float(render_defaults["half_wavelength_px"])
        x = left + unit_px
        while float(x) < float(right):
            draw.line([(x, top), (x, bottom)], fill=theme.grid_rgb, width=max(1, int(render_defaults["grid_line_width_px"])))
            x += unit_px
        y = top + unit_px
        while float(y) < float(bottom):
            draw.line([(left, y), (right, y)], fill=theme.grid_rgb, width=max(1, int(render_defaults["grid_line_width_px"])))
            y += unit_px
    if str(scene_variant) == "lab_sheet":
        for offset in range(0, int(bottom - top), 34):
            y = top + float(offset)
            draw.line([(left, y), (right, y)], fill=(236, 240, 245), width=1)


def _draw_dashed_ellipse(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    *,
    fill: Sequence[int],
    width: int,
    dash_degrees: int = 11,
    gap_degrees: int = 9,
) -> None:
    """Draw a dashed ellipse using short arc segments."""

    angle = 0
    while angle < 360:
        draw.arc(tuple(float(value) for value in bbox), start=int(angle), end=int(min(360, angle + dash_degrees)), fill=tuple(int(value) for value in fill), width=max(1, int(width)))
        angle += int(dash_degrees + gap_degrees)


def _draw_wavefronts(image: Image.Image, *, board: Sequence[float], source_positions: Mapping[str, Tuple[float, float]], phase_relation: str, theme, render_defaults: Mapping[str, Any]) -> Image.Image:
    """Draw clipped crest/trough rings for the two wave sources."""

    unit_px = float(render_defaults["half_wavelength_px"])
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer)
    ring_count = int(render_defaults["ring_count"])
    width = max(1, int(render_defaults["wavefront_width_px"]))
    offsets = {"S1": 0, "S2": 0 if str(phase_relation) == "in_phase" else 1}
    for source_id, center in source_positions.items():
        offset = int(offsets[str(source_id)])
        for step in range(1, ring_count + 1):
            radius = float(step) * unit_px
            bbox = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
            if (int(step) + int(offset)) % 2 == 0:
                layer_draw.ellipse(tuple(bbox), outline=tuple(int(value) for value in theme.crest_rgb) + (112,), width=width)
            else:
                _draw_dashed_ellipse(layer_draw, bbox, fill=tuple(int(value) for value in theme.trough_rgb) + (92,), width=max(1, width - 1))

    mask = Image.new("L", image.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(tuple(float(value) for value in board), radius=12, fill=255)
    alpha = ImageChops.multiply(layer.getchannel("A"), mask)
    layer.putalpha(alpha)
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def _draw_source(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    source_id: str,
    theme,
    render_defaults: Mapping[str, Any],
    font,
) -> List[float]:
    """Draw one source marker and return its bbox."""

    radius = float(render_defaults["source_radius_px"])
    bbox = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
    draw.ellipse(tuple(bbox), fill=theme.source_fill_rgb, outline=theme.source_outline_rgb, width=3)
    text_bbox = draw_centered_text(
        draw,
        text=str(source_id),
        center=center,
        font=font,
        fill=theme.source_text_rgb,
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.source_text_rgb)),
        stroke_width=1,
    )
    return _bbox_union(bbox, text_bbox)


def _draw_candidate(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    letter: str,
    theme,
    render_defaults: Mapping[str, Any],
    font,
) -> List[float]:
    """Draw one labeled candidate point and return its bbox."""

    radius = float(render_defaults["candidate_radius_px"])
    bbox = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
    halo = [center[0] - radius - 5.0, center[1] - radius - 5.0, center[0] + radius + 5.0, center[1] + radius + 5.0]
    draw.ellipse(tuple(halo), fill=theme.label_fill_rgb, outline=theme.candidate_outline_rgb, width=1)
    draw.ellipse(tuple(bbox), fill=theme.candidate_fill_rgb, outline=theme.candidate_outline_rgb, width=3)
    text_bbox = draw_centered_text(
        draw,
        text=str(letter),
        center=center,
        font=font,
        fill=theme.candidate_text_rgb,
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.candidate_text_rgb)),
        stroke_width=1,
    )
    return _bbox_union(bbox, text_bbox)


def _draw_point_p(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    theme,
    render_defaults: Mapping[str, Any],
    font,
) -> List[float]:
    """Draw highlighted point P and return its bbox."""

    radius = float(render_defaults["point_radius_px"])
    bbox = [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]
    halo = [center[0] - radius - 5.0, center[1] - radius - 5.0, center[0] + radius + 5.0, center[1] + radius + 5.0]
    draw.ellipse(tuple(halo), fill=theme.label_fill_rgb, outline=theme.point_outline_rgb, width=1)
    draw.ellipse(tuple(bbox), fill=theme.point_fill_rgb, outline=theme.point_outline_rgb, width=3)
    text_bbox = draw_centered_text(
        draw,
        text="P",
        center=center,
        font=font,
        fill=theme.candidate_text_rgb,
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.candidate_text_rgb)),
        stroke_width=1,
    )
    return _bbox_union(bbox, text_bbox)


def _phase_label(phase_relation: str) -> str:
    """Return a short source-phase label."""

    return "sources in phase" if str(phase_relation) == "in_phase" else "S2 opposite phase"


def _condition_phrase(target_condition: str | None) -> str:
    """Return prompt-facing condition phrase."""

    if str(target_condition) == "constructive":
        return "constructive interference"
    if str(target_condition) == "destructive":
        return "destructive interference"
    return "the requested interference condition"


def _object_description_for_query(prompt_defaults: Mapping[str, Any], *, scene_variant: str, query_id: str) -> str:
    """Return the most specific prompt-facing scene description available."""

    query_specific_key = f"object_description_{str(scene_variant)}_{str(query_id)}"
    if query_specific_key in prompt_defaults:
        return str(prompt_defaults[query_specific_key])
    return str(prompt_defaults[f"object_description_{str(scene_variant)}"])


def _render_scene(
    *,
    background: Image.Image,
    render_defaults: Mapping[str, Any],
    accent_color_name: str,
    scene_spec: _SceneSpec,
    diagram_style: Any | None = None,
    font_family: str | None = None,
) -> _RenderedScene:
    """Render one wave-interference scene."""

    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    theme = build_physics_waves_theme(str(accent_color_name), diagram_style=diagram_style)
    resolved_font_family = None if font_family is None else str(font_family)
    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=False, font_family=resolved_font_family)
    source_font = load_font(int(render_defaults["source_font_size_px"]), bold=True, font_family=resolved_font_family)
    candidate_font = load_font(int(render_defaults["candidate_font_size_px"]), bold=True, font_family=resolved_font_family)
    note_font = load_font(int(render_defaults["note_font_size_px"]), bold=False, font_family=resolved_font_family)
    board = _board_bbox(render_defaults)
    _draw_tank(draw, board=board, scene_variant=str(scene_spec.scene_variant), theme=theme, render_defaults=render_defaults)
    source_positions = _source_positions(board, unit_px=float(render_defaults["half_wavelength_px"]))
    image = _draw_wavefronts(
        image,
        board=board,
        source_positions=source_positions,
        phase_relation=str(scene_spec.phase_relation),
        theme=theme,
        render_defaults=render_defaults,
    )
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(tuple(float(value) for value in board), radius=12, outline=theme.tank_outline_rgb, width=3)
    scene_entities: List[Dict[str, Any]] = []
    render_map: Dict[str, Any] = {
        "technical_diagram_frame_mode": str(getattr(diagram_style, "frame_mode", "none")),
        "board_bbox_px": list(board),
    }

    source_bboxes: Dict[str, List[float]] = {}
    for source_id, center in source_positions.items():
        bbox = _draw_source(draw, center=center, source_id=str(source_id), theme=theme, render_defaults=render_defaults, font=source_font)
        source_bboxes[str(source_id)] = list(bbox)
        scene_entities.append(
            {
                "entity_id": str(source_id),
                "entity_type": "wave_source",
                "bbox": list(bbox),
                "meta": {"source_id": str(source_id), "phase_relation": str(scene_spec.phase_relation)},
            }
        )
    phase_bbox = _draw_text_tag(
        draw,
        text=_phase_label(str(scene_spec.phase_relation)),
        center=(board[0] + 150.0, board[1] + 34.0),
        font=label_font,
        fill_rgb=theme.label_fill_rgb,
        outline_rgb=theme.label_outline_rgb,
        text_rgb=theme.label_text_rgb,
    )
    legend_bbox = _draw_text_tag(
        draw,
        text="ring gap = lambda/2",
        center=(board[2] - 170.0, board[3] - 34.0),
        font=note_font,
        fill_rgb=theme.label_fill_rgb,
        outline_rgb=theme.label_outline_rgb,
        text_rgb=theme.label_text_rgb,
    )
    scene_entities.append({"entity_id": "phase_relation_label", "entity_type": "phase_label", "bbox": list(phase_bbox), "meta": {"phase_relation": str(scene_spec.phase_relation)}})
    scene_entities.append({"entity_id": "ring_spacing_label", "entity_type": "scale_label", "bbox": list(legend_bbox), "meta": {"spacing": "lambda/2"}})

    annotation_type: str
    annotation_bboxes: List[List[float]]
    annotation_bbox_map: Dict[str, List[float]]
    annotation_points: List[List[float]]
    annotation_key_by_entity_id: Dict[str, str]
    annotation_ids: List[str] = [str(entity_id) for entity_id in scene_spec.annotation_entity_ids]
    unit_px = float(render_defaults["half_wavelength_px"])

    if scene_spec.choice_scenario is not None:
        candidate_bboxes: Dict[str, List[float]] = {}
        candidate_centers: Dict[str, List[float]] = {}
        for candidate in scene_spec.choice_scenario.candidates:
            center = _point_to_px(board, unit_px=unit_px, x_steps=float(candidate.x_steps), y_steps=float(candidate.y_steps))
            bbox = _draw_candidate(
                draw,
                center=center,
                letter=str(candidate.letter),
                theme=theme,
                render_defaults=render_defaults,
                font=candidate_font,
            )
            candidate_bboxes[str(candidate.letter)] = list(bbox)
            candidate_centers[str(candidate.letter)] = [round(float(center[0]), 3), round(float(center[1]), 3)]
            scene_entities.append(
                {
                    "entity_id": f"candidate_{str(candidate.letter)}",
                    "entity_type": "interference_candidate_point",
                    "bbox": list(bbox),
                    "meta": {
                        "option_letter": str(candidate.letter),
                        "x_steps": float(candidate.x_steps),
                        "y_steps": float(candidate.y_steps),
                        "s1_distance_steps": int(candidate.r1_steps),
                        "s2_distance_steps": int(candidate.r2_steps),
                        "condition": str(candidate.condition),
                        "is_correct": bool(candidate.is_correct),
                    },
                }
            )
        correct_letter = str(scene_spec.choice_scenario.correct_option_letter)
        annotation_type = "point_set"
        annotation_points = [list(candidate_centers[correct_letter])]
        annotation_bboxes = []
        annotation_bbox_map = {}
        annotation_key_by_entity_id = {}
        render_map.update(
            {
                "source_bboxes_px": dict(source_bboxes),
                "candidate_bboxes_px": dict(candidate_bboxes),
                "candidate_centers_px": dict(candidate_centers),
                "annotation_point_set_px": [list(point) for point in annotation_points],
            }
        )

    elif scene_spec.path_scenario is not None:
        scenario = scene_spec.path_scenario
        point_center = _point_to_px(board, unit_px=unit_px, x_steps=float(scenario.point_x_steps), y_steps=float(scenario.point_y_steps))
        s1_center = source_positions["S1"]
        s2_center = source_positions["S2"]
        draw_dashed_line(
            draw,
            start=s1_center,
            end=point_center,
            fill=theme.guide_rgb,
            width=max(1, int(render_defaults["guide_width_px"])),
            dash_px=16.0,
            gap_px=9.0,
        )
        draw_dashed_line(
            draw,
            start=s2_center,
            end=point_center,
            fill=theme.guide_rgb,
            width=max(1, int(render_defaults["guide_width_px"])),
            dash_px=16.0,
            gap_px=9.0,
        )
        line_1_bbox = _line_bbox(s1_center, point_center, padding_px=18.0)
        line_2_bbox = _line_bbox(s2_center, point_center, padding_px=18.0)
        point_bbox = _draw_point_p(draw, center=point_center, theme=theme, render_defaults=render_defaults, font=candidate_font)
        tag_1_bbox = _draw_text_tag(
            draw,
            text="S1P",
            center=((s1_center[0] + point_center[0]) / 2.0, (s1_center[1] + point_center[1]) / 2.0 - 20.0),
            font=note_font,
            fill_rgb=theme.label_fill_rgb,
            outline_rgb=theme.label_outline_rgb,
            text_rgb=theme.label_text_rgb,
        )
        tag_2_bbox = _draw_text_tag(
            draw,
            text="S2P",
            center=((s2_center[0] + point_center[0]) / 2.0, (s2_center[1] + point_center[1]) / 2.0 + 20.0),
            font=note_font,
            fill_rgb=theme.label_fill_rgb,
            outline_rgb=theme.label_outline_rgb,
            text_rgb=theme.label_text_rgb,
        )
        path_s1p_bbox = _bbox_union(line_1_bbox, tag_1_bbox, point_bbox)
        path_s2p_bbox = _bbox_union(line_2_bbox, tag_2_bbox, point_bbox)
        witness_bbox = _bbox_union(source_bboxes["S1"], source_bboxes["S2"], path_s1p_bbox, path_s2p_bbox)
        scene_entities.append(
            {
                "entity_id": "point_P",
                "entity_type": "path_difference_point",
                "bbox": list(point_bbox),
                "meta": {
                    "x_steps": float(scenario.point_x_steps),
                    "y_steps": float(scenario.point_y_steps),
                    "s1_distance_steps": int(scenario.r1_steps),
                    "s2_distance_steps": int(scenario.r2_steps),
                },
            }
        )
        scene_entities.append(
            {
                "entity_id": "path_S1P",
                "entity_type": "path_difference_guide",
                "bbox": list(path_s1p_bbox),
                "meta": {
                    "path_key": "S1P",
                    "source_id": "S1",
                    "target_id": "P",
                    "distance_steps": int(scenario.r1_steps),
                },
            }
        )
        scene_entities.append(
            {
                "entity_id": "path_S2P",
                "entity_type": "path_difference_guide",
                "bbox": list(path_s2p_bbox),
                "meta": {
                    "path_key": "S2P",
                    "source_id": "S2",
                    "target_id": "P",
                    "distance_steps": int(scenario.r2_steps),
                },
            }
        )
        scene_entities.append(
            {
                "entity_id": "path_difference_witness_region",
                "entity_type": "path_difference_witness_region",
                "bbox": list(witness_bbox),
                "meta": {"path_difference_steps": int(scenario.path_difference_steps)},
            }
        )
        annotation_type = "keyed_bbox_map"
        annotation_bbox_map = {
            "S1P": list(path_s1p_bbox),
            "S2P": list(path_s2p_bbox),
        }
        annotation_key_by_entity_id = {"path_S1P": "S1P", "path_S2P": "S2P"}
        annotation_bboxes = []
        annotation_points = []
        render_map.update(
            {
                "source_bboxes_px": dict(source_bboxes),
                "point_p_bbox_px": list(point_bbox),
                "path_s1_bbox_px": list(line_1_bbox),
                "path_s2_bbox_px": list(line_2_bbox),
                "path_s1_label_bbox_px": list(tag_1_bbox),
                "path_s2_label_bbox_px": list(tag_2_bbox),
                "path_s1p_bbox_px": list(path_s1p_bbox),
                "path_s2p_bbox_px": list(path_s2p_bbox),
                "path_difference_witness_region_bbox_px": list(witness_bbox),
                "annotation_bbox_map_px": {str(key): list(value) for key, value in annotation_bbox_map.items()},
            }
        )
    else:
        raise ValueError("wave scene requires a choice or path-difference scenario")

    return _RenderedScene(
        image=image,
        annotation_type=str(annotation_type),
        annotation_bboxes=[list(bbox) for bbox in annotation_bboxes],
        annotation_bbox_map={str(key): list(value) for key, value in annotation_bbox_map.items()},
        annotation_points=[list(point) for point in annotation_points],
        annotation_key_by_entity_id={str(key): str(value) for key, value in annotation_key_by_entity_id.items()},
        annotation_entity_ids=list(annotation_ids),
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
    )


def _answer_type(query_id: str) -> str:
    """Return answer type for one query."""

    if str(query_id) == "interference_point_choice":
        return "option_letter"
    if str(query_id) == "path_difference_value":
        return "integer"
    raise ValueError(f"unsupported waves query id: {query_id}")


def _build_prompt_examples(query_id: str) -> Tuple[str, str]:
    """Build deterministic JSON examples for one query."""

    if str(query_id) == "interference_point_choice":
        return build_prompt_json_examples(annotation_value=[[247, 225]], answer_type="option_letter")
    if str(query_id) == "path_difference_value":
        return build_prompt_json_examples(
            annotation_value={"S1P": [212, 164, 486, 356], "S2P": [446, 184, 754, 474]},
            answer_type="integer",
        )
    raise ValueError(f"unsupported waves query id: {query_id}")


class _PhysicsWavesInterferenceTankBaseTask:
    """Return one wave-interference reasoning question."""

    task_id = TASK_ID
    domain = "physics"
    scene_id = "waves"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        rendered_scene: _RenderedScene | None = None
        scene_spec: _SceneSpec | None = None

        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                scene_spec = _sample_scene_spec(attempt_rng, axes=axes)
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
                    "board_left_px",
                    "board_top_px",
                    "board_width_px",
                    "board_height_px",
                    "half_wavelength_px",
                    "ring_count",
                    "grid_line_width_px",
                    "source_radius_px",
                    "candidate_radius_px",
                    "point_radius_px",
                    "wavefront_width_px",
                    "guide_width_px",
                    "label_font_size_px",
                    "source_font_size_px",
                    "candidate_font_size_px",
                    "note_font_size_px",
                )
            }
            render_defaults, layout_placement_meta = _resolve_wave_layout_placement(
                render_defaults=render_defaults,
                params=params,
                instance_seed=int(instance_seed),
            )
            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                scene_id=SCENE_ID,
                canvas_width=int(render_defaults["canvas_width"]),
                canvas_height=int(render_defaults["canvas_height"]),
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
                    "object_description_clean_tank",
                    "object_description_grid_tank",
                    "object_description_lab_sheet",
                    "object_description_clean_tank_interference_point_choice",
                    "object_description_grid_tank_interference_point_choice",
                    "object_description_lab_sheet_interference_point_choice",
                    "object_description_clean_tank_path_difference_value",
                    "object_description_grid_tank_path_difference_value",
                    "object_description_lab_sheet_path_difference_value",
                    "answer_hint_interference_point_choice",
                    "answer_hint_path_difference_value",
                    "annotation_hint_interference_point_choice",
                    "annotation_hint_path_difference_value",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            json_example, json_example_answer_only = _build_prompt_examples(str(axes.query_id))
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                scene_id=self.scene_id,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(axes.query_id),
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": _object_description_for_query(
                        prompt_defaults,
                        scene_variant=str(axes.scene_variant),
                        query_id=str(axes.query_id),
                    ),
                    "target_condition_phrase": _condition_phrase(axes.target_condition),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                    "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_type = _answer_type(str(axes.query_id))
            answer_value: int | str = scene_spec.target_answer
            answer_gt = TypedValue(type=str(answer_type), value=answer_value)
            if str(rendered_scene.annotation_type) == "point_set":
                annotation_value = [list(point) for point in rendered_scene.annotation_points]
            elif str(rendered_scene.annotation_type) == "keyed_bbox_map":
                annotation_value = {str(key): list(value) for key, value in rendered_scene.annotation_bbox_map.items()}
            else:
                annotation_value = [list(bbox) for bbox in rendered_scene.annotation_bboxes]
            annotation_gt = TypedValue(type=str(rendered_scene.annotation_type), value=annotation_value)

            choice_payload: Dict[str, Any] = {}
            if scene_spec.choice_scenario is not None:
                scenario = scene_spec.choice_scenario
                choice_payload = {
                    "phase_relation": str(scenario.phase_relation),
                    "target_condition": str(scenario.target_condition),
                    "correct_option_letter": str(scenario.correct_option_letter),
                    "candidates": [
                        {
                            "option_letter": str(candidate.letter),
                            "x_steps": float(candidate.x_steps),
                            "y_steps": float(candidate.y_steps),
                            "s1_distance_steps": int(candidate.r1_steps),
                            "s2_distance_steps": int(candidate.r2_steps),
                            "condition": str(candidate.condition),
                            "is_correct": bool(candidate.is_correct),
                        }
                        for candidate in scenario.candidates
                    ],
                }
            path_payload: Dict[str, Any] = {}
            if scene_spec.path_scenario is not None:
                scenario = scene_spec.path_scenario
                path_payload = {
                    "phase_relation": str(scenario.phase_relation),
                    "point_x_steps": float(scenario.point_x_steps),
                    "point_y_steps": float(scenario.point_y_steps),
                    "s1_distance_steps": int(scenario.r1_steps),
                    "s2_distance_steps": int(scenario.r2_steps),
                    "path_difference_steps": int(scenario.path_difference_steps),
                    "unit": "lambda/2",
                }

            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_waves_interference_{str(axes.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.query_id),
                        "phase_relation": str(axes.phase_relation),
                        "target_condition": axes.target_condition,
                        "target_answer": answer_value,
                        "answer_type": str(answer_type),
                        "choice_scenario": dict(choice_payload),
                        "path_difference_scenario": dict(path_payload),
                        "annotation_entity_ids": list(rendered_scene.annotation_entity_ids),
                        "annotation_key_by_entity_id": dict(rendered_scene.annotation_key_by_entity_id),
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
                        "phase_relation": str(axes.phase_relation),
                        "target_condition": axes.target_condition,
                        "correct_option_letter": axes.correct_option_letter,
                        "path_difference_steps": axes.path_difference_steps,
                        "accent_color_name": str(axes.accent_color_name),
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_id_probabilities": dict(axes.query_id_probabilities),
                        "phase_relation_probabilities": dict(axes.phase_relation_probabilities),
                        "target_condition_probabilities": dict(axes.target_condition_probabilities),
                        "correct_option_letter_probabilities": dict(axes.correct_option_letter_probabilities),
                        "path_difference_steps_probabilities": dict(axes.path_difference_steps_probabilities),
                        "accent_color_name_probabilities": dict(axes.accent_color_name_probabilities),
                        "target_answer": answer_value,
                        "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    },
                },
                "render_spec": {
                    "scene_variant": str(axes.scene_variant),
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "accent_color_name": str(axes.accent_color_name),
                    "half_wavelength_px": int(render_defaults["half_wavelength_px"]),
                    "font": {
                        "font_family": str(font_family),
                        "font_asset_version": font_asset_version(),
                        "font_asset": font_record.to_trace(),
                        "scope": "wave_interference_tank",
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
                    "phase_relation": str(axes.phase_relation),
                    "target_condition": axes.target_condition,
                    "correct_option_letter": axes.correct_option_letter,
                    "path_difference_steps": axes.path_difference_steps,
                    "path_difference_step_support": list(_path_difference_support(params)),
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": answer_value,
                    "answer_type": str(answer_type),
                    "option_letters": list(OPTION_LETTERS),
                    "choice_scenario": dict(choice_payload),
                    "path_difference_scenario": dict(path_payload),
                    "annotation_entity_ids": list(rendered_scene.annotation_entity_ids),
                    "annotation_key_by_entity_id": dict(rendered_scene.annotation_key_by_entity_id),
                },
                "witness_symbolic": {
                    "type": "object_key_map" if str(rendered_scene.annotation_type) == "keyed_bbox_map" else "object_set",
                    "ids": [str(item) for item in rendered_scene.annotation_entity_ids],
                    **(
                        {"keys": dict(rendered_scene.annotation_key_by_entity_id)}
                        if str(rendered_scene.annotation_type) == "keyed_bbox_map"
                        else {}
                    ),
                },
                "projected_annotation": {
                    "type": str(rendered_scene.annotation_type),
                    **(
                        {
                            "point_set": [list(point) for point in rendered_scene.annotation_points],
                            "pixel_point_set": [list(point) for point in rendered_scene.annotation_points],
                        }
                        if str(rendered_scene.annotation_type) == "point_set"
                        else {
                            "keyed_bbox_map": {
                                str(key): list(value) for key, value in rendered_scene.annotation_bbox_map.items()
                            },
                            "pixel_keyed_bbox_map": {
                                str(key): list(value) for key, value in rendered_scene.annotation_bbox_map.items()
                            },
                        }
                        if str(rendered_scene.annotation_type) == "keyed_bbox_map"
                        else {
                            "bbox_set": [list(bbox) for bbox in rendered_scene.annotation_bboxes],
                            "pixel_bbox_set": [list(bbox) for bbox in rendered_scene.annotation_bboxes],
                        }
                    ),
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

        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")


@register_task
class PhysicsWavesInterferencePointChoiceTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsWavesInterferenceTankBaseTask,
):
    """Choose a point where two-source wave interference has the requested condition."""

    task_id = "task_physics__wave_interference__interference_point_choice"
    fixed_query_id = "interference_point_choice"


@register_task
class PhysicsWavesPathDifferenceValueTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsWavesInterferenceTankBaseTask,
):
    """Compute the source-to-point path difference in half-wavelength steps."""

    task_id = "task_physics__wave_interference__path_difference_value"
    fixed_query_id = "path_difference_value"
