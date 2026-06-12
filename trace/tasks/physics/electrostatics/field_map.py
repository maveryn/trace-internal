"""Physics electrostatics tasks for field-map diagrams."""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import product
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.bbox_projection import bbox_union_many as _bbox_union
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.drawing import draw_arrow, draw_centered_text, draw_dashed_line, draw_rounded_rect
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
from ..shared.diagram_style import (
    PHYSICS_ELECTROSTATICS_SEMANTIC_COLORS,
    PhysicsDiagramStyle,
    make_physics_diagram_background,
    physics_electrostatics_theme_from_diagram_style,
    resolve_physics_diagram_style,
)
from trace.tasks.shared.fixed_query import FixedPhysicsQueryVariantTaskMixin
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES
from ..shared.support_sampling import resolve_integer_support
from ..shared.vector_arrows import SEMANTIC_DIRECTION_VECTORS, arrow_bbox, centered_arrow_endpoints, draw_arrow_with_bbox
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "physics_electrostatics_field_map"
SCENE_ID = "electrostatic_field"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "clean_grid",
    "paper_grid",
    "dense_grid",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (
    "field_direction_choice",
    "zero_field_point_label",
    "potential_value",
)
SUPPORTED_DIRECTION_MODES: Tuple[str, ...] = (
    "electric_field_direction",
    "force_on_positive_charge",
    "force_on_negative_charge",
)
SUPPORTED_DIRECTIONS: Tuple[str, ...] = (
    "east",
    "northeast",
    "north",
    "northwest",
    "west",
    "southwest",
    "south",
    "southeast",
)
DIRECTION_VECTORS: Dict[str, Tuple[int, int]] = dict(SEMANTIC_DIRECTION_VECTORS)
OPTION_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H")
POINT_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
POTENTIAL_DISTANCE_UNITS: Tuple[int, ...] = (2, 3, 4)
POTENTIAL_CHARGE_COORDS: Tuple[Tuple[int, int], ...] = ((2, 0), (0, 3), (-4, 0))
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "clean_grid": SUPPORTED_QUERY_IDS,
    "paper_grid": SUPPORTED_QUERY_IDS,
    "dense_grid": SUPPORTED_QUERY_IDS,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for electrostatics field-map scenes."""

    canvas_width: int = 1180
    canvas_height: int = 760
    board_left_px: int = 58
    board_top_px: int = 58
    board_width_px: int = 760
    board_height_px: int = 560
    coord_extent: int = 5
    grid_line_width_px: int = 1
    dense_grid_line_width_px: int = 2
    axis_width_px: int = 4
    charge_radius_px: int = 30
    point_radius_px: int = 14
    label_font_size_px: int = 22
    option_font_size_px: int = 25
    note_font_size_px: int = 21
    charge_font_size_px: int = 25
    option_panel_left_px: int = 850
    option_panel_top_px: int = 82
    option_cell_width_px: int = 140
    option_cell_height_px: int = 118
    option_cell_gap_x_px: int = 22
    option_cell_gap_y_px: int = 22
    option_arrow_length_px: int = 64
    option_arrow_width_px: int = 7
    option_arrow_head_length_px: int = 20
    option_arrow_head_width_px: int = 18
    potential_answer_support: Tuple[int, ...] = tuple(range(-9, 10))
    potential_contribution_support: Tuple[int, ...] = (-3, -2, -1, 1, 2, 3)


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query axes and answer support for one instance."""

    scene_variant: str
    query_id: str
    direction_mode: str | None
    target_direction: str | None
    correct_option_letter: str | None
    accent_color_name: str
    target_answer: int | str
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    direction_mode_probabilities: Dict[str, float]
    target_direction_probabilities: Dict[str, float]
    correct_option_letter_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _Charge:
    """One fixed point charge in grid coordinates."""

    charge_id: str
    charge_value: int
    x: int
    y: int


@dataclass(frozen=True)
class _CandidatePoint:
    """One labeled candidate point in grid coordinates."""

    letter: str
    x: int
    y: int
    is_correct: bool


@dataclass(frozen=True)
class _PotentialCharge:
    """One visible charge with an exact displayed distance to the query point."""

    charge_id: str
    charge_value: int
    contribution: int
    distance_units: int
    x: int
    y: int


@dataclass(frozen=True)
class _DirectionScenario:
    """One symbolic field-direction scenario."""

    charges: Tuple[_Charge, ...]
    point_x: int
    point_y: int
    field_direction: str
    requested_direction: str
    option_directions: Dict[str, str]


@dataclass(frozen=True)
class _ZeroFieldScenario:
    """One symbolic zero-field candidate-point scenario."""

    charges: Tuple[_Charge, ...]
    candidate_points: Tuple[_CandidatePoint, ...]
    correct_option_letter: str
    symmetry_axis: str


@dataclass(frozen=True)
class _PotentialScenario:
    """One symbolic electric-potential scenario."""

    charges: Tuple[_PotentialCharge, ...]
    point_x: int
    point_y: int
    potential_value: int


@dataclass(frozen=True)
class _SceneSpec:
    """Resolved symbolic electrostatics scene."""

    scene_variant: str
    query_id: str
    direction_mode: str | None
    target_direction: str | None
    correct_option_letter: str | None
    target_answer: int | str
    direction_scenario: _DirectionScenario | None
    zero_field_scenario: _ZeroFieldScenario | None
    potential_scenario: _PotentialScenario | None
    annotation_entity_ids: Tuple[str, ...]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered electrostatics scene plus prompt-facing annotation metadata."""

    image: Image.Image
    annotation_bboxes: List[List[float]]
    annotation_points: List[List[float]]
    annotation_point_map: Dict[str, List[float]]
    annotation_entity_ids: List[str]
    annotation_key_by_entity_id: Dict[str, str]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "electrostatics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="electrostatics", apply_prob=0.5)


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


def _potential_answer_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return configured signed electric-potential answer support."""

    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="potential_answer_support",
        fallback=_DEFAULTS.potential_answer_support,
    )


def _potential_contribution_support(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return configured per-charge contribution support for potential scenes."""

    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="potential_contribution_support",
        fallback=_DEFAULTS.potential_contribution_support,
    )


def _opposite_direction(direction: str) -> str:
    """Return the opposite named compass direction."""

    dx, dy = DIRECTION_VECTORS[str(direction)]
    for name, vector in DIRECTION_VECTORS.items():
        if vector == (-int(dx), -int(dy)):
            return str(name)
    raise ValueError(f"unsupported direction: {direction}")


def _resolve_direction_mode(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str | None, Dict[str, float]]:
    """Resolve the field/force direction wording branch."""

    if str(query_id) != "field_direction_choice":
        return None, {}
    adjusted_params = _with_sampling_divisor(params, divisor=len(SUPPORTED_QUERY_IDS), explicit_keys=("direction_mode",))
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.direction_mode"),
        params=adjusted_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_DIRECTION_MODES,
        explicit_key="direction_mode",
        weights_key="direction_mode_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=adjusted_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_DIRECTION_MODES,
        balance_flag_key="balanced_direction_mode_sampling",
        explicit_key="direction_mode",
        weights_key="direction_mode_weights",
        sampling_namespace=f"{TASK_ID}.direction_mode",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_target_direction(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str | None, Dict[str, float]]:
    """Resolve the requested vector direction for direction-choice scenes."""

    if str(query_id) != "field_direction_choice":
        return None, {}
    adjusted_params = _with_sampling_divisor(
        params,
        divisor=len(SUPPORTED_QUERY_IDS) * len(SUPPORTED_DIRECTION_MODES),
        explicit_keys=("target_direction",),
    )
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.target_direction"),
        params=adjusted_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_DIRECTIONS,
        explicit_key="target_direction",
        weights_key="target_direction_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=adjusted_params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_DIRECTIONS,
        balance_flag_key="balanced_target_direction_sampling",
        explicit_key="target_direction",
        weights_key="target_direction_weights",
        sampling_namespace=f"{TASK_ID}.target_direction",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_correct_option_letter(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[str | None, Dict[str, float]]:
    """Resolve the correct visible option/candidate letter for option tasks."""

    if str(query_id) not in {"field_direction_choice", "zero_field_point_label"}:
        return None, {}
    supported = OPTION_LETTERS if str(query_id) == "field_direction_choice" else POINT_LETTERS
    weights_key = "direction_option_letter_weights" if str(query_id) == "field_direction_choice" else "point_option_letter_weights"
    balance_key = (
        "balanced_direction_option_letter_sampling"
        if str(query_id) == "field_direction_choice"
        else "balanced_point_option_letter_sampling"
    )
    option_params = dict(params)
    if option_params.get("correct_option_letter") is None and option_params.get("target_answer") is not None:
        option_params["correct_option_letter"] = str(option_params["target_answer"]).strip().upper()
    option_params = dict(
        _with_sampling_divisor(
            option_params,
            divisor=len(SUPPORTED_QUERY_IDS),
            explicit_keys=("correct_option_letter",),
        )
    )
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.correct_option_letter.{str(query_id)}"),
        params=option_params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported,
        explicit_key="correct_option_letter",
        weights_key=weights_key,
    )
    balanced_enabled = bool(
        option_params.get(
            balance_key,
            group_default(_GEN_DEFAULTS, balance_key, True),
        )
    )
    has_override = any(
        option_params.get(str(key)) is not None
        for key in ("correct_option_letter", weights_key)
    )
    if bool(balanced_enabled) and not bool(has_override) and is_uniform_probability_map(probabilities):
        selected = str(supported[abs(int(instance_seed)) % len(supported)])
    else:
        selected = apply_balanced_variant_sampling(
            instance_seed=int(instance_seed),
            params=option_params,
            gen_defaults=_GEN_DEFAULTS,
            selected_variant=str(selected),
            variant_probabilities=probabilities,
            supported_variants=supported,
            balance_flag_key=balance_key,
            explicit_key="correct_option_letter",
            weights_key=weights_key,
            sampling_namespace=f"{TASK_ID}.correct_option_letter.{str(query_id)}",
        )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _feasible_potential_scenarios(params: Mapping[str, Any]) -> Tuple[_PotentialScenario, ...]:
    """Enumerate exact integer potential scenarios."""

    answer_support = set(int(value) for value in _potential_answer_support(params))
    contribution_support = tuple(int(value) for value in _potential_contribution_support(params) if int(value) != 0)
    explicit_answer = params.get("target_answer")
    explicit_contributions = params.get("potential_contributions")
    distance_units = POTENTIAL_DISTANCE_UNITS
    coords = POTENTIAL_CHARGE_COORDS
    scenarios: List[_PotentialScenario] = []

    if explicit_contributions is not None:
        if not isinstance(explicit_contributions, Sequence) or isinstance(explicit_contributions, (str, bytes)):
            raise ValueError(f"potential_contributions must be a sequence of {len(distance_units)} integers")
        contribution_rows = [tuple(int(value) for value in explicit_contributions)]
    else:
        contribution_rows = product(contribution_support, repeat=len(distance_units))

    for contributions in contribution_rows:
        if len(tuple(contributions)) != len(distance_units):
            raise ValueError(f"potential_contributions must contain exactly {len(distance_units)} integers")
        contribution_values = tuple(int(value) for value in contributions)
        answer = int(sum(contribution_values))
        if explicit_answer is not None and int(answer) != int(explicit_answer):
            continue
        if int(answer) not in answer_support:
            continue
        charges = []
        for index, (contribution, distance, coord) in enumerate(zip(contribution_values, distance_units, coords), start=1):
            charges.append(
                _PotentialCharge(
                    charge_id=f"charge_{index}",
                    charge_value=int(contribution) * int(distance),
                    contribution=int(contribution),
                    distance_units=int(distance),
                    x=int(coord[0]),
                    y=int(coord[1]),
                )
            )
        scenarios.append(
            _PotentialScenario(
                charges=tuple(charges),
                point_x=0,
                point_y=0,
                potential_value=int(answer),
            )
        )
    if not scenarios:
        raise ValueError("no feasible electrostatic-potential scenarios for configured supports")
    return tuple(scenarios)


def _feasible_potential_answers(params: Mapping[str, Any]) -> Tuple[int, ...]:
    """Return configured potential answers that have at least one construction."""

    feasible = sorted({int(scenario.potential_value) for scenario in _feasible_potential_scenarios(params)})
    if not feasible:
        raise ValueError("no feasible potential answers")
    return tuple(int(value) for value in feasible)


def _resolve_potential_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    query_id: str,
) -> Tuple[int | None, Dict[str, float]]:
    """Resolve an exact integer potential target."""

    if str(query_id) != "potential_value":
        return None, {}
    support = _feasible_potential_answers(params)
    explicit = params.get("target_answer")
    if explicit is not None:
        selected = int(explicit)
        if int(selected) not in set(support):
            raise ValueError(f"unsupported electrostatic potential target_answer: {selected}")
        return int(selected), uniform_probability_map(support, selected=int(selected))

    adjusted_params = _with_sampling_divisor(params, divisor=len(SUPPORTED_QUERY_IDS), explicit_keys=("target_answer",))
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
            namespace=f"{TASK_ID}.target_answer.potential_value",
        )
        selected = int(support[int(selection_index) % len(support)])
    else:
        rng = spawn_rng(int(instance_seed), f"{TASK_ID}.target_answer.potential_value")
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
    direction_mode, direction_mode_probs = _resolve_direction_mode(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    target_direction, target_direction_probs = _resolve_target_direction(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    correct_option_letter, option_probs = _resolve_correct_option_letter(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )
    potential_answer, potential_probs = _resolve_potential_target_answer(
        instance_seed=int(instance_seed),
        params=params,
        query_id=str(query_id),
    )

    if str(query_id) == "potential_value":
        if potential_answer is None:
            raise ValueError("potential_value query requires a numeric target answer")
        target_answer: int | str = int(potential_answer)
        target_probs: Dict[str, float] = dict(potential_probs)
    else:
        if correct_option_letter is None:
            raise ValueError(f"{query_id} query requires a correct option letter")
        target_answer = str(correct_option_letter)
        target_probs = dict(option_probs)

    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        direction_mode=direction_mode,
        target_direction=target_direction,
        correct_option_letter=correct_option_letter,
        accent_color_name=str(accent_name),
        target_answer=target_answer,
        scene_variant_probabilities={str(key): float(value) for key, value in sorted(scene_probs.items())},
        query_id_probabilities={str(key): float(value) for key, value in sorted(query_probs.items())},
        direction_mode_probabilities={str(key): float(value) for key, value in sorted(direction_mode_probs.items())},
        target_direction_probabilities={str(key): float(value) for key, value in sorted(target_direction_probs.items())},
        correct_option_letter_probabilities={str(key): float(value) for key, value in sorted(option_probs.items())},
        accent_color_name_probabilities={str(key): float(value) for key, value in sorted(accent_probs.items())},
        target_answer_probabilities={str(key): float(value) for key, value in sorted(target_probs.items())},
    )


def _direction_options(
    rng,
    *,
    requested_direction: str,
    correct_option_letter: str,
) -> Dict[str, str]:
    """Assign every option letter to a unique compass direction."""

    remaining = [direction for direction in SUPPORTED_DIRECTIONS if str(direction) != str(requested_direction)]
    rng.shuffle(remaining)
    option_directions: Dict[str, str] = {}
    for letter in OPTION_LETTERS:
        if str(letter) == str(correct_option_letter):
            option_directions[str(letter)] = str(requested_direction)
        else:
            option_directions[str(letter)] = str(remaining.pop())
    return option_directions


def _sample_direction_scenario(rng, *, axes: _ResolvedAxes) -> _DirectionScenario:
    """Build a field-direction scene with a known exact compass direction."""

    if axes.direction_mode is None or axes.target_direction is None or axes.correct_option_letter is None:
        raise ValueError("direction scenario requires mode, target direction, and correct option")
    requested_direction = str(axes.target_direction)
    field_direction = (
        _opposite_direction(requested_direction)
        if str(axes.direction_mode) == "force_on_negative_charge"
        else requested_direction
    )
    field_dx, field_dy = DIRECTION_VECTORS[str(field_direction)]
    perp_dx, perp_dy = -int(field_dy), int(field_dx)
    if int(perp_dx) == 0 and int(perp_dy) == 0:
        perp_dx, perp_dy = 0, 1
    use_negative_source = int(rng.randrange(2)) == 0
    if use_negative_source:
        main_charge = _Charge(
            charge_id="charge_main",
            charge_value=-4,
            x=int(2 * field_dx),
            y=int(2 * field_dy),
        )
    else:
        main_charge = _Charge(
            charge_id="charge_main",
            charge_value=4,
            x=int(-2 * field_dx),
            y=int(-2 * field_dy),
        )
    charges = (
        main_charge,
        _Charge(charge_id="charge_cancel_a", charge_value=1, x=int(2 * perp_dx), y=int(2 * perp_dy)),
        _Charge(charge_id="charge_cancel_b", charge_value=1, x=int(-2 * perp_dx), y=int(-2 * perp_dy)),
    )
    return _DirectionScenario(
        charges=charges,
        point_x=0,
        point_y=0,
        field_direction=str(field_direction),
        requested_direction=str(requested_direction),
        option_directions=_direction_options(
            rng,
            requested_direction=str(requested_direction),
            correct_option_letter=str(axes.correct_option_letter),
        ),
    )


def _inside_candidate_bounds(x: int, y: int) -> bool:
    """Return whether a candidate point is comfortably inside the board."""

    return -4 <= int(x) <= 4 and -4 <= int(y) <= 4


def _sample_zero_field_scenario(rng, *, axes: _ResolvedAxes) -> _ZeroFieldScenario:
    """Build an unequal-charge zero-field candidate scene."""

    if axes.correct_option_letter is None:
        raise ValueError("zero-field scenario requires a correct option letter")
    symmetry_axis = "horizontal" if int(rng.randrange(2)) == 0 else "vertical"
    charge_sign = 1 if int(rng.randrange(2)) == 0 else -1
    small_charge_first = int(rng.randrange(2)) == 0
    if str(symmetry_axis) == "horizontal":
        axis_dx, axis_dy = 1, 0
        point_x = int((-1, 0, 1)[int(rng.randrange(3))])
        point_y = int((-2, -1, 0, 1, 2)[int(rng.randrange(5))])
    else:
        axis_dx, axis_dy = 0, 1
        point_x = int((-2, -1, 0, 1, 2)[int(rng.randrange(5))])
        point_y = int((-1, 0, 1)[int(rng.randrange(3))])

    if bool(small_charge_first):
        first_distance, second_distance = 1, 2
        first_magnitude, second_magnitude = 1, 4
    else:
        first_distance, second_distance = 2, 1
        first_magnitude, second_magnitude = 4, 1

    first_x = int(point_x - first_distance * axis_dx)
    first_y = int(point_y - first_distance * axis_dy)
    second_x = int(point_x + second_distance * axis_dx)
    second_y = int(point_y + second_distance * axis_dy)
    if str(symmetry_axis) == "horizontal":
        charges = (
            _Charge(charge_id="charge_left", charge_value=int(first_magnitude * charge_sign), x=first_x, y=first_y),
            _Charge(charge_id="charge_right", charge_value=int(second_magnitude * charge_sign), x=second_x, y=second_y),
        )
    else:
        charges = (
            _Charge(charge_id="charge_bottom", charge_value=int(first_magnitude * charge_sign), x=first_x, y=first_y),
            _Charge(charge_id="charge_top", charge_value=int(second_magnitude * charge_sign), x=second_x, y=second_y),
        )

    charge_coords = {(int(charge.x), int(charge.y)) for charge in charges}
    distractor_coords: List[Tuple[int, int]] = []

    def add_candidate(x: int, y: int) -> None:
        coord = (int(x), int(y))
        if coord == (int(point_x), int(point_y)):
            return
        if coord in charge_coords:
            return
        if coord in distractor_coords:
            return
        if not _inside_candidate_bounds(int(x), int(y)):
            return
        distractor_coords.append(coord)

    perp_dx, perp_dy = -int(axis_dy), int(axis_dx)
    for offset in (-3, -2, -1, 1, 2, 3):
        add_candidate(int(point_x + offset * axis_dx), int(point_y + offset * axis_dy))
    for offset in (-2, -1, 1, 2):
        add_candidate(int(point_x + offset * perp_dx), int(point_y + offset * perp_dy))
    for axis_offset, perp_offset in ((-1, -1), (-1, 1), (1, -1), (1, 1), (-2, 1), (2, -1)):
        add_candidate(
            int(point_x + axis_offset * axis_dx + perp_offset * perp_dx),
            int(point_y + axis_offset * axis_dy + perp_offset * perp_dy),
        )
    if len(distractor_coords) < len(POINT_LETTERS) - 1:
        raise RuntimeError("not enough electrostatics zero-field distractor candidates")

    rng.shuffle(distractor_coords)
    candidates: List[_CandidatePoint] = []
    distractor_index = 0
    for letter in POINT_LETTERS:
        if str(letter) == str(axes.correct_option_letter):
            x, y = int(point_x), int(point_y)
            is_correct = True
        else:
            x, y = distractor_coords[int(distractor_index)]
            distractor_index += 1
            is_correct = False
        candidates.append(
            _CandidatePoint(
                letter=str(letter),
                x=int(x),
                y=int(y),
                is_correct=bool(is_correct),
            )
        )
    return _ZeroFieldScenario(
        charges=charges,
        candidate_points=tuple(candidates),
        correct_option_letter=str(axes.correct_option_letter),
        symmetry_axis=str(symmetry_axis),
    )


def _sample_potential_scenario(rng, *, target_answer: int, params: Mapping[str, Any]) -> _PotentialScenario:
    """Sample one exact electric-potential scenario for the target answer."""

    scenarios = [
        scenario
        for scenario in _feasible_potential_scenarios(params)
        if int(scenario.potential_value) == int(target_answer)
    ]
    if not scenarios:
        raise ValueError(f"no electrostatic-potential scenario for target {target_answer}")
    return scenarios[int(rng.randrange(len(scenarios)))]


def _sample_scene_spec(rng, *, axes: _ResolvedAxes, params: Mapping[str, Any]) -> _SceneSpec:
    """Sample one symbolic electrostatics scene."""

    if str(axes.query_id) == "field_direction_choice":
        scenario = _sample_direction_scenario(rng, axes=axes)
        return _SceneSpec(
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            direction_mode=str(axes.direction_mode),
            target_direction=str(axes.target_direction),
            correct_option_letter=str(axes.correct_option_letter),
            target_answer=str(axes.correct_option_letter),
            direction_scenario=scenario,
            zero_field_scenario=None,
            potential_scenario=None,
            annotation_entity_ids=("charge_main", "charge_cancel_a", "charge_cancel_b", "query_point"),
        )
    if str(axes.query_id) == "zero_field_point_label":
        scenario = _sample_zero_field_scenario(rng, axes=axes)
        return _SceneSpec(
            scene_variant=str(axes.scene_variant),
            query_id=str(axes.query_id),
            direction_mode=None,
            target_direction=None,
            correct_option_letter=str(axes.correct_option_letter),
            target_answer=str(axes.correct_option_letter),
            direction_scenario=None,
            zero_field_scenario=scenario,
            potential_scenario=None,
            annotation_entity_ids=tuple(str(charge.charge_id) for charge in scenario.charges),
        )
    scenario = _sample_potential_scenario(rng, target_answer=int(axes.target_answer), params=params)
    return _SceneSpec(
        scene_variant=str(axes.scene_variant),
        query_id=str(axes.query_id),
        direction_mode=None,
        target_direction=None,
        correct_option_letter=None,
        target_answer=int(scenario.potential_value),
        direction_scenario=None,
        zero_field_scenario=None,
        potential_scenario=scenario,
        annotation_entity_ids=tuple(
            [str(charge.charge_id) for charge in scenario.charges]
            + ["query_point"]
        ),
    )


def _annotation_entity_key_map(scene_spec: _SceneSpec) -> Dict[str, str]:
    """Return neutral visible annotation keys by rendered entity id."""

    key_by_entity_id: Dict[str, str] = {}
    charge_index = 1
    for entity_id in scene_spec.annotation_entity_ids:
        if str(entity_id) == "query_point":
            key_by_entity_id[str(entity_id)] = "P"
        else:
            key_by_entity_id[str(entity_id)] = f"Q{int(charge_index)}"
            charge_index += 1
    return key_by_entity_id


def _board_bbox(render_defaults: Mapping[str, Any]) -> List[float]:
    """Return the main coordinate board bbox."""

    return [
        float(render_defaults["board_left_px"]),
        float(render_defaults["board_top_px"]),
        float(render_defaults["board_left_px"]) + float(render_defaults["board_width_px"]),
        float(render_defaults["board_top_px"]) + float(render_defaults["board_height_px"]),
    ]


def _electrostatics_content_bbox(render_defaults: Mapping[str, Any], *, query_id: str) -> List[float]:
    """Return a conservative bbox for the whole rendered electrostatics diagram."""

    board = _board_bbox(render_defaults)
    left = float(board[0]) - 46.0
    top = float(board[1]) - 50.0
    right = float(board[2]) + 58.0
    bottom = float(board[3]) + 50.0
    if str(query_id) == "field_direction_choice":
        option_left = float(render_defaults["option_panel_left_px"])
        option_top = float(render_defaults["option_panel_top_px"])
        option_right = option_left + (2.0 * float(render_defaults["option_cell_width_px"])) + float(render_defaults["option_cell_gap_x_px"])
        option_bottom = option_top + (4.0 * float(render_defaults["option_cell_height_px"])) + (3.0 * float(render_defaults["option_cell_gap_y_px"]))
        left = min(left, option_left)
        top = min(top, option_top)
        right = max(right, option_right)
        bottom = max(bottom, option_bottom)
    return [round(left, 3), round(top, 3), round(right, 3), round(bottom, 3)]


def _resolve_electrostatics_layout_placement(
    *,
    render_defaults: Mapping[str, Any],
    params: Mapping[str, Any],
    instance_seed: int,
    query_id: str,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve a whole-diagram offset before rendering and annotation projection."""

    canvas_width = int(render_defaults["canvas_width"])
    canvas_height = int(render_defaults["canvas_height"])
    content_bbox = _electrostatics_content_bbox(render_defaults, query_id=str(query_id))
    content_left, content_top, content_right, content_bottom = [float(value) for value in content_bbox]
    jitter = resolve_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}.electrostatics_layout",
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
    for key in ("board_left_px", "option_panel_left_px"):
        adjusted[key] = int(adjusted[key]) + int(dx)
    for key in ("board_top_px", "option_panel_top_px"):
        adjusted[key] = int(adjusted[key]) + int(dy)

    final_bbox = [
        round(float(content_left) + float(dx), 3),
        round(float(content_top) + float(dy), 3),
        round(float(content_right) + float(dx), 3),
        round(float(content_bottom) + float(dy), 3),
    ]
    content_width = round(float(content_right) - float(content_left), 3)
    content_height = round(float(content_bottom) - float(content_top), 3)
    placement = dict(jitter)
    placement.update(
        {
            "mode": "whole_electrostatics_diagram_offset",
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


def _coord_to_px(*, bbox: Sequence[float], x: float, y: float, coord_extent: int) -> Tuple[float, float]:
    """Map board coordinates to pixel coordinates."""

    left, top, right, bottom = [float(value) for value in bbox[:4]]
    extent = max(1, int(coord_extent))
    px = float(left + ((float(x) + float(extent)) / float(2 * extent)) * (right - left))
    py = float(bottom - ((float(y) + float(extent)) / float(2 * extent)) * (bottom - top))
    return px, py


def _point_bbox(center: Tuple[float, float], *, radius_px: float, padding_px: float = 0.0) -> List[float]:
    """Return a bbox around one rendered circular marker."""

    cx, cy = float(center[0]), float(center[1])
    radius = float(radius_px) + float(padding_px)
    return [
        round(float(cx - radius), 3),
        round(float(cy - radius), 3),
        round(float(cx + radius), 3),
        round(float(cy + radius), 3),
    ]


def _expand_bbox(bbox: Sequence[float], padding_px: float) -> List[float]:
    """Return one bbox expanded by a constant pixel margin."""

    return [
        round(float(bbox[0]) - float(padding_px), 3),
        round(float(bbox[1]) - float(padding_px), 3),
        round(float(bbox[2]) + float(padding_px), 3),
        round(float(bbox[3]) + float(padding_px), 3),
    ]


def _bbox_overlaps(left: Sequence[float], right: Sequence[float]) -> bool:
    """Return whether two axis-aligned bboxes overlap."""

    return not (
        float(left[2]) <= float(right[0])
        or float(left[0]) >= float(right[2])
        or float(left[3]) <= float(right[1])
        or float(left[1]) >= float(right[3])
    )


def _bbox_intersection_area(left: Sequence[float], right: Sequence[float]) -> float:
    """Return the positive intersection area between two bboxes."""

    x0 = max(float(left[0]), float(right[0]))
    y0 = max(float(left[1]), float(right[1]))
    x1 = min(float(left[2]), float(right[2]))
    y1 = min(float(left[3]), float(right[3]))
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return float((x1 - x0) * (y1 - y0))


def _bbox_inside(inner: Sequence[float], outer: Sequence[float], padding_px: float = 0.0) -> bool:
    """Return whether one bbox stays inside another with optional margin."""

    return (
        float(inner[0]) >= float(outer[0]) + float(padding_px)
        and float(inner[1]) >= float(outer[1]) + float(padding_px)
        and float(inner[2]) <= float(outer[2]) - float(padding_px)
        and float(inner[3]) <= float(outer[3]) - float(padding_px)
    )


def _text_tag_bbox(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font,
    stroke_width_px: int,
) -> List[float]:
    """Return the outer bbox for one rounded text tag before drawing it."""

    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width_px)))
    text_width = float(text_bbox[2] - text_bbox[0])
    text_height = float(text_bbox[3] - text_bbox[1])
    pad_x = 11.0
    pad_y = 7.0
    center_x, center_y = float(center[0]), float(center[1])
    return [
        round(float(center_x - (0.5 * text_width) - pad_x), 3),
        round(float(center_y - (0.5 * text_height) - pad_y), 3),
        round(float(center_x + (0.5 * text_width) + pad_x), 3),
        round(float(center_y + (0.5 * text_height) + pad_y), 3),
    ]


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

    center_x, center_y = float(center[0]), float(center[1])
    tag_bbox = _text_tag_bbox(draw, text=str(text), center=(center_x, center_y), font=font, stroke_width_px=int(stroke_width_px))
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


def _draw_board(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    render_defaults: Mapping[str, Any],
    scene_variant: str,
    theme,
    diagram_style: PhysicsDiagramStyle,
    label_font,
) -> Dict[str, Any]:
    """Draw the coordinate board and return bbox metadata."""

    left, top, right, bottom = [float(value) for value in bbox[:4]]
    extent = int(render_defaults["coord_extent"])
    grid_width = int(render_defaults["dense_grid_line_width_px"]) if str(scene_variant) == "dense_grid" else int(render_defaults["grid_line_width_px"])
    board_fill = tuple(int(value) for value in theme.board_alt_fill_rgb) if str(scene_variant) == "paper_grid" else tuple(int(value) for value in theme.board_fill_rgb)
    draw.rectangle(tuple(float(value) for value in bbox), fill=board_fill)
    frame_mode = str(diagram_style.frame_mode)
    if frame_mode == "plain_outline":
        draw.rectangle(
            tuple(float(value) for value in bbox),
            outline=tuple(int(value) for value in theme.board_outline_rgb),
            width=max(1, int(diagram_style.panel_border_width_px)),
        )
    elif frame_mode == "matching_outline":
        draw.rectangle(
            tuple(float(value) for value in bbox),
            outline=tuple(int(value) for value in theme.board_outline_rgb),
            width=max(2, int(diagram_style.panel_border_width_px)),
        )
        inset = 7.0
        draw.rectangle(
            (left + inset, top + inset, right - inset, bottom - inset),
            outline=tuple(int(value) for value in diagram_style.canvas_accent_rgb),
            width=1,
        )
    tick_bboxes: List[List[float]] = []
    for coord in range(-extent, extent + 1):
        x, _ = _coord_to_px(bbox=bbox, x=coord, y=0, coord_extent=extent)
        _, y = _coord_to_px(bbox=bbox, x=0, y=coord, coord_extent=extent)
        draw.line([(float(x), float(top)), (float(x), float(bottom))], fill=tuple(int(value) for value in theme.grid_rgb), width=grid_width)
        draw.line([(float(left), float(y)), (float(right), float(y))], fill=tuple(int(value) for value in theme.grid_rgb), width=grid_width)
        if coord in {-4, -2, 0, 2, 4}:
            xb = draw_centered_text(
                draw,
                text=str(coord),
                center=(float(x), float(bottom + 22.0)),
                font=label_font,
                fill=tuple(int(value) for value in theme.axis_text_rgb),
                stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.axis_text_rgb)),
                stroke_width=1,
            )
            yb = draw_centered_text(
                draw,
                text=str(coord),
                center=(float(left - 24.0), float(y)),
                font=label_font,
                fill=tuple(int(value) for value in theme.axis_text_rgb),
                stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.axis_text_rgb)),
                stroke_width=1,
            )
            tick_bboxes.extend([list(xb), list(yb)])
    origin = _coord_to_px(bbox=bbox, x=0, y=0, coord_extent=extent)
    x_end = _coord_to_px(bbox=bbox, x=extent, y=0, coord_extent=extent)
    y_end = _coord_to_px(bbox=bbox, x=0, y=extent, coord_extent=extent)
    draw_arrow(
        draw,
        start=(float(left), float(origin[1])),
        end=(float(x_end[0] + 30.0), float(origin[1])),
        fill=tuple(int(value) for value in theme.axis_rgb),
        width=int(render_defaults["axis_width_px"]),
        head_length_px=22.0,
        head_width_px=18.0,
    )
    draw_arrow(
        draw,
        start=(float(origin[0]), float(bottom)),
        end=(float(origin[0]), float(y_end[1] - 30.0)),
        fill=tuple(int(value) for value in theme.axis_rgb),
        width=int(render_defaults["axis_width_px"]),
        head_length_px=22.0,
        head_width_px=18.0,
    )
    x_label = draw_centered_text(
        draw,
        text="+x",
        center=(float(right + 22.0), float(origin[1] + 26.0)),
        font=label_font,
        fill=tuple(int(value) for value in theme.axis_text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.axis_text_rgb)),
        stroke_width=1,
    )
    y_label = draw_centered_text(
        draw,
        text="+y",
        center=(float(origin[0] - 28.0), float(top - 20.0)),
        font=label_font,
        fill=tuple(int(value) for value in theme.axis_text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.axis_text_rgb)),
        stroke_width=1,
    )
    return {
        "board_bbox_px": [round(float(value), 3) for value in bbox],
        "axis_bbox_px": _bbox_union(bbox, x_label, y_label, *tick_bboxes),
        "tick_label_bboxes_px": [list(bbox_value) for bbox_value in tick_bboxes],
    }


def _charge_key_value_text(display_label: str, charge_value: int) -> str:
    """Return one compact visible label binding charge key to charge value."""

    return f"{str(display_label)}={int(charge_value):+d}"


def _draw_charge(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    coord_extent: int,
    charge: _Charge | _PotentialCharge,
    display_label: str,
    render_defaults: Mapping[str, Any],
    theme,
    charge_font,
    label_font,
) -> Tuple[Dict[str, Any], List[float]]:
    """Draw one point charge and return entity/render bbox."""

    center = _coord_to_px(bbox=bbox, x=int(charge.x), y=int(charge.y), coord_extent=int(coord_extent))
    radius = float(render_defaults["charge_radius_px"])
    is_positive = int(charge.charge_value) > 0
    fill_rgb = theme.positive_fill_rgb if is_positive else theme.negative_fill_rgb
    outline_rgb = theme.positive_outline_rgb if is_positive else theme.negative_outline_rgb
    text_rgb = theme.positive_text_rgb if is_positive else theme.negative_text_rgb
    circle_bbox = _point_bbox(center, radius_px=radius)
    draw.ellipse(
        tuple(float(value) for value in circle_bbox),
        fill=tuple(int(value) for value in fill_rgb),
        outline=tuple(int(value) for value in outline_rgb),
        width=4,
    )
    sign_bbox = draw_centered_text(
        draw,
        text="+" if is_positive else "-",
        center=(float(center[0]), float(center[1] - 2.0)),
        font=charge_font,
        fill=tuple(int(value) for value in text_rgb),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(text_rgb)),
        stroke_width=1,
    )
    label_y = float(center[1] + radius + 24.0)
    if float(label_y) > float(bbox[3] - 16.0):
        label_y = float(center[1] - radius - 22.0)
    charge_label_text = _charge_key_value_text(str(display_label), int(charge.charge_value))
    label_bbox = _draw_text_tag(
        draw,
        text=str(charge_label_text),
        center=(float(center[0]), label_y),
        font=label_font,
        fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in outline_rgb),
        text_rgb=tuple(int(value) for value in theme.label_text_rgb),
        stroke_width_px=2,
    )
    marker_bbox = _bbox_union(circle_bbox, sign_bbox)
    entity_bbox = _bbox_union(marker_bbox, label_bbox)
    entity = {
        "entity_id": str(charge.charge_id),
        "entity_type": "point_charge",
        "bbox_px": list(entity_bbox),
        "meta": {
            "charge_value": int(charge.charge_value),
            "display_label": str(display_label),
            "x": int(charge.x),
            "y": int(charge.y),
            "center_px": [round(float(center[0]), 3), round(float(center[1]), 3)],
            "charge_marker_bbox_px": list(marker_bbox),
            "charge_id_label_bbox_px": list(label_bbox),
            "charge_label_bbox_px": list(label_bbox),
            "charge_label_text": str(charge_label_text),
        },
    }
    if isinstance(charge, _PotentialCharge):
        entity["meta"]["distance_units"] = int(charge.distance_units)
        entity["meta"]["potential_contribution"] = int(charge.contribution)
    return entity, list(entity_bbox)


def _choose_point_label_center(
    draw: ImageDraw.ImageDraw,
    *,
    marker_center: Tuple[float, float],
    label: str,
    font,
    board_bbox: Sequence[float],
    avoid_bboxes: Sequence[Sequence[float]],
    stroke_width_px: int,
) -> Tuple[Tuple[float, float], List[float]]:
    """Choose a point-label location that avoids nearby charge/candidate labels."""

    offsets = (
        (24.0, -22.0),
        (-24.0, -22.0),
        (24.0, 24.0),
        (-24.0, 24.0),
        (0.0, -38.0),
        (0.0, 38.0),
        (40.0, 0.0),
        (-40.0, 0.0),
        (0.0, -64.0),
        (0.0, 64.0),
        (62.0, -42.0),
        (-62.0, -42.0),
        (62.0, 42.0),
        (-62.0, 42.0),
        (88.0, 0.0),
        (-88.0, 0.0),
        (120.0, 0.0),
        (-120.0, 0.0),
        (120.0, -42.0),
        (-120.0, -42.0),
        (120.0, 42.0),
        (-120.0, 42.0),
    )
    expanded_avoid = [_expand_bbox(bbox, 8.0) for bbox in avoid_bboxes]
    fallback_center = (float(marker_center[0] + offsets[0][0]), float(marker_center[1] + offsets[0][1]))
    fallback_bbox = _text_tag_bbox(draw, text=str(label), center=fallback_center, font=font, stroke_width_px=int(stroke_width_px))
    best_score = float("inf")
    for dx, dy in offsets:
        center = (float(marker_center[0] + float(dx)), float(marker_center[1] + float(dy)))
        label_bbox = _text_tag_bbox(draw, text=str(label), center=center, font=font, stroke_width_px=int(stroke_width_px))
        if not _bbox_inside(label_bbox, board_bbox, padding_px=4.0):
            continue
        expanded_label = _expand_bbox(label_bbox, 2.0)
        overlap_score = sum(_bbox_intersection_area(expanded_label, avoid) for avoid in expanded_avoid)
        if overlap_score < best_score:
            best_score = float(overlap_score)
            fallback_center = center
            fallback_bbox = list(label_bbox)
        if any(_bbox_overlaps(expanded_label, avoid) for avoid in expanded_avoid):
            continue
        return center, label_bbox
    return fallback_center, fallback_bbox


def _draw_point_marker_with_label_bbox(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    coord_extent: int,
    x: int,
    y: int,
    label: str,
    render_defaults: Mapping[str, Any],
    theme,
    point_font,
    target: bool,
    avoid_bboxes: Sequence[Sequence[float]] = (),
) -> Tuple[List[float], List[float]]:
    """Draw a labeled point marker and return full and label bboxes."""

    center = _coord_to_px(bbox=bbox, x=int(x), y=int(y), coord_extent=int(coord_extent))
    radius = float(render_defaults["point_radius_px"]) + (4.0 if bool(target) else 0.0)
    fill_rgb = theme.target_fill_rgb if bool(target) else theme.point_fill_rgb
    outline_rgb = theme.target_outline_rgb if bool(target) else theme.point_outline_rgb
    circle_bbox = _point_bbox(center, radius_px=radius)
    draw.ellipse(
        tuple(float(value) for value in circle_bbox),
        fill=tuple(int(value) for value in fill_rgb),
        outline=tuple(int(value) for value in outline_rgb),
        width=3,
    )
    label_center, _ = _choose_point_label_center(
        draw,
        marker_center=center,
        label=str(label),
        font=point_font,
        board_bbox=bbox,
        avoid_bboxes=avoid_bboxes,
        stroke_width_px=2,
    )
    label_bbox = _draw_text_tag(
        draw,
        text=str(label),
        center=label_center,
        font=point_font,
        fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in outline_rgb),
        text_rgb=tuple(int(value) for value in theme.point_text_rgb),
        stroke_width_px=2,
    )
    return list(_bbox_union(circle_bbox, label_bbox)), list(label_bbox)


def _draw_point_marker(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Sequence[float],
    coord_extent: int,
    x: int,
    y: int,
    label: str,
    render_defaults: Mapping[str, Any],
    theme,
    point_font,
    target: bool,
) -> List[float]:
    """Draw a labeled point marker and return its bbox."""

    point_bbox, _ = _draw_point_marker_with_label_bbox(
        draw,
        bbox=bbox,
        coord_extent=int(coord_extent),
        x=int(x),
        y=int(y),
        label=str(label),
        render_defaults=render_defaults,
        theme=theme,
        point_font=point_font,
        target=bool(target),
    )
    return list(point_bbox)


def _draw_direction_options(
    draw: ImageDraw.ImageDraw,
    *,
    render_defaults: Mapping[str, Any],
    scenario: _DirectionScenario,
    theme,
    option_font,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Draw candidate direction arrows."""

    entities: List[Dict[str, Any]] = []
    option_bboxes: Dict[str, List[float]] = {}
    option_directions: Dict[str, str] = {}
    for index, letter in enumerate(OPTION_LETTERS):
        col = int(index % 2)
        row = int(index // 2)
        cell_left = float(render_defaults["option_panel_left_px"]) + float(col) * (
            float(render_defaults["option_cell_width_px"]) + float(render_defaults["option_cell_gap_x_px"])
        )
        cell_top = float(render_defaults["option_panel_top_px"]) + float(row) * (
            float(render_defaults["option_cell_height_px"]) + float(render_defaults["option_cell_gap_y_px"])
        )
        cell_bbox = [
            float(cell_left),
            float(cell_top),
            float(cell_left + float(render_defaults["option_cell_width_px"])),
            float(cell_top + float(render_defaults["option_cell_height_px"])),
        ]
        draw_rounded_rect(
            draw,
            tuple(float(value) for value in cell_bbox),
            radius=8,
            fill=tuple(int(value) for value in theme.label_fill_rgb),
            outline=tuple(int(value) for value in theme.option_outline_rgb),
            width=2,
        )
        direction = str(scenario.option_directions[str(letter)])
        length = float(render_defaults["option_arrow_length_px"])
        cx = float((cell_bbox[0] + cell_bbox[2]) / 2.0 + 14.0)
        cy = float((cell_bbox[1] + cell_bbox[3]) / 2.0 + 8.0)
        start, end = centered_arrow_endpoints(
            (cx, cy),
            direction=direction,
            length_px=length,
            direction_vectors=DIRECTION_VECTORS,
            half_fraction=0.42,
        )
        arrow_bbox_value = draw_arrow_with_bbox(
            draw,
            start=start,
            end=end,
            fill=tuple(int(value) for value in theme.option_arrow_rgb),
            width=int(render_defaults["option_arrow_width_px"]),
            head_length_px=float(render_defaults["option_arrow_head_length_px"]),
            head_width_px=float(render_defaults["option_arrow_head_width_px"]),
            padding_px=22.0,
        )
        label_bbox = draw_centered_text(
            draw,
            text=str(letter),
            center=(float(cell_bbox[0] + 24.0), float(cell_bbox[1] + 22.0)),
            font=option_font,
            fill=tuple(int(value) for value in theme.axis_text_rgb),
            stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(theme.axis_text_rgb)),
            stroke_width=1,
        )
        option_bbox = _bbox_union(cell_bbox, label_bbox, arrow_bbox_value)
        option_bboxes[str(letter)] = list(option_bbox)
        option_directions[str(letter)] = str(direction)
        entities.append(
            {
                "entity_id": f"option_{str(letter)}",
                "entity_type": "candidate_direction_arrow",
                "bbox_px": list(option_bbox),
                "meta": {
                    "option_letter": str(letter),
                    "direction": str(direction),
                    "is_correct": str(direction) == str(scenario.requested_direction),
                },
            }
        )
    return entities, {
        "option_bboxes_px": {key: list(value) for key, value in option_bboxes.items()},
        "option_directions": dict(option_directions),
    }


def _draw_distance_label(
    draw: ImageDraw.ImageDraw,
    *,
    start: Tuple[float, float],
    end: Tuple[float, float],
    text: str,
    theme,
    label_font,
) -> List[float]:
    """Draw one dashed distance guide and label."""

    draw_dashed_line(
        draw,
        start=start,
        end=end,
        fill=tuple(int(value) for value in theme.guide_rgb),
        width=3,
        dash_px=10.0,
        gap_px=6.0,
    )
    guide_bbox = arrow_bbox(start, end, padding_px=6.0)
    mid = (float((start[0] + end[0]) / 2.0), float((start[1] + end[1]) / 2.0))
    dx = float(end[0] - start[0])
    dy = float(end[1] - start[1])
    if abs(dx) < abs(dy):
        label_center = (float(mid[0] + 58.0), float(mid[1]))
    else:
        label_center = (float(mid[0]), float(mid[1] - 28.0))
    label_bbox = _draw_text_tag(
        draw,
        text=str(text),
        center=label_center,
        font=label_font,
        fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
        outline_rgb=tuple(int(value) for value in theme.label_outline_rgb),
        text_rgb=tuple(int(value) for value in theme.label_text_rgb),
        stroke_width_px=2,
    )
    return list(_bbox_union(guide_bbox, label_bbox))


def _render_scene(
    *,
    background: Image.Image,
    render_defaults: Mapping[str, Any],
    accent_color_name: str,
    diagram_style: PhysicsDiagramStyle,
    scene_spec: _SceneSpec,
    font_family: str,
) -> _RenderedScene:
    """Render one electrostatics field map and return trace metadata."""

    image = background.copy()
    draw = ImageDraw.Draw(image)
    theme = physics_electrostatics_theme_from_diagram_style(
        diagram_style,
        accent_color_name=str(accent_color_name),
    )
    resolved_font_family = str(font_family)
    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=False, font_family=resolved_font_family)
    option_font = load_font(int(render_defaults["option_font_size_px"]), bold=True, font_family=resolved_font_family)
    note_font = load_font(int(render_defaults["note_font_size_px"]), bold=True, font_family=resolved_font_family)
    charge_font = load_font(int(render_defaults["charge_font_size_px"]), bold=True, font_family=resolved_font_family)
    board = _board_bbox(render_defaults)
    board_meta = _draw_board(
        draw,
        bbox=board,
        render_defaults=render_defaults,
        scene_variant=str(scene_spec.scene_variant),
        theme=theme,
        diagram_style=diagram_style,
        label_font=label_font,
    )
    scene_entities: List[Dict[str, Any]] = [
        {
            "entity_id": "coordinate_board",
            "entity_type": "electrostatics_coordinate_board",
            "bbox_px": list(board_meta["axis_bbox_px"]),
            "meta": {"coord_extent": int(render_defaults["coord_extent"])},
        }
    ]
    render_map: Dict[str, Any] = {
        "accent_color_name": str(accent_color_name),
        "scene_variant": str(scene_spec.scene_variant),
        "query_id": str(scene_spec.query_id),
        "technical_diagram_frame_mode": str(diagram_style.frame_mode),
    }
    coord_extent = int(render_defaults["coord_extent"])
    annotation_key_by_entity_id = _annotation_entity_key_map(scene_spec)

    if str(scene_spec.query_id) == "field_direction_choice":
        if scene_spec.direction_scenario is None:
            raise ValueError("field_direction_choice render requires a direction scenario")
        scenario = scene_spec.direction_scenario
        charge_bboxes: List[List[float]] = []
        for charge in scenario.charges:
            entity, charge_bbox = _draw_charge(
                draw,
                bbox=board,
                coord_extent=coord_extent,
                charge=charge,
                display_label=str(annotation_key_by_entity_id[str(charge.charge_id)]),
                render_defaults=render_defaults,
                theme=theme,
                charge_font=charge_font,
                label_font=label_font,
            )
            scene_entities.append(entity)
            charge_bboxes.append(list(charge_bbox))
        point_center = _coord_to_px(bbox=board, x=int(scenario.point_x), y=int(scenario.point_y), coord_extent=coord_extent)
        point_bbox = _draw_point_marker(
            draw,
            bbox=board,
            coord_extent=coord_extent,
            x=int(scenario.point_x),
            y=int(scenario.point_y),
            label="P",
            render_defaults=render_defaults,
            theme=theme,
            point_font=option_font,
            target=True,
        )
        scene_entities.append(
            {
                "entity_id": "query_point",
                "entity_type": "query_point",
                "bbox_px": list(point_bbox),
                "meta": {
                    "x": int(scenario.point_x),
                    "y": int(scenario.point_y),
                    "label": "P",
                    "center_px": [round(float(point_center[0]), 3), round(float(point_center[1]), 3)],
                },
            }
        )
        option_entities, option_map = _draw_direction_options(
            draw,
            render_defaults=render_defaults,
            scenario=scenario,
            theme=theme,
            option_font=option_font,
        )
        scene_entities.extend(option_entities)
        render_map.update(board_meta)
        render_map.update(option_map)
        render_map["query_point_bbox_px"] = list(point_bbox)
        render_map["charge_bboxes_px"] = [list(bbox) for bbox in charge_bboxes]
    elif str(scene_spec.query_id) == "zero_field_point_label":
        if scene_spec.zero_field_scenario is None:
            raise ValueError("zero_field_point_label render requires a zero-field scenario")
        scenario = scene_spec.zero_field_scenario
        charge_bboxes = []
        avoid_bboxes: List[List[float]] = []
        charge_label_bboxes: List[List[float]] = []
        for charge in scenario.charges:
            entity, charge_bbox = _draw_charge(
                draw,
                bbox=board,
                coord_extent=coord_extent,
                charge=charge,
                display_label=str(annotation_key_by_entity_id[str(charge.charge_id)]),
                render_defaults=render_defaults,
                theme=theme,
                charge_font=charge_font,
                label_font=label_font,
            )
            scene_entities.append(entity)
            charge_bboxes.append(list(charge_bbox))
            avoid_bboxes.append(list(charge_bbox))
            label_bbox = entity.get("meta", {}).get("charge_label_bbox_px", [])
            if isinstance(label_bbox, Sequence) and len(label_bbox) == 4:
                charge_label_bboxes.append([float(value) for value in label_bbox])
        candidate_bboxes: Dict[str, List[float]] = {}
        candidate_label_bboxes: Dict[str, List[float]] = {}
        for point in scenario.candidate_points:
            point_center = _coord_to_px(bbox=board, x=int(point.x), y=int(point.y), coord_extent=coord_extent)
            point_bbox, point_label_bbox = _draw_point_marker_with_label_bbox(
                draw,
                bbox=board,
                coord_extent=coord_extent,
                x=int(point.x),
                y=int(point.y),
                label=str(point.letter),
                render_defaults=render_defaults,
                theme=theme,
                point_font=option_font,
                target=False,
                avoid_bboxes=avoid_bboxes,
            )
            candidate_bboxes[str(point.letter)] = list(point_bbox)
            candidate_label_bboxes[str(point.letter)] = list(point_label_bbox)
            avoid_bboxes.append(list(point_bbox))
            scene_entities.append(
                {
                    "entity_id": f"candidate_{str(point.letter)}",
                    "entity_type": "candidate_zero_field_point",
                    "bbox_px": list(point_bbox),
                    "meta": {
                        "option_letter": str(point.letter),
                        "x": int(point.x),
                        "y": int(point.y),
                        "is_correct": bool(point.is_correct),
                        "center_px": [round(float(point_center[0]), 3), round(float(point_center[1]), 3)],
                    },
                }
            )
        render_map.update(board_meta)
        render_map["charge_bboxes_px"] = [list(bbox) for bbox in charge_bboxes]
        render_map["charge_label_bboxes_px"] = [list(bbox) for bbox in charge_label_bboxes]
        render_map["candidate_point_bboxes_px"] = {key: list(value) for key, value in candidate_bboxes.items()}
        render_map["candidate_label_bboxes_px"] = {key: list(value) for key, value in candidate_label_bboxes.items()}
    else:
        if scene_spec.potential_scenario is None:
            raise ValueError("potential_value render requires a potential scenario")
        scenario = scene_spec.potential_scenario
        note_bbox = _draw_text_tag(
            draw,
            text="Use k=1 and V=sum(q/r)",
            center=(float(board[2] - 150.0), float(board[1] - 34.0)),
            font=note_font,
            fill_rgb=tuple(int(value) for value in theme.label_fill_rgb),
            outline_rgb=tuple(int(value) for value in theme.label_outline_rgb),
            text_rgb=tuple(int(value) for value in theme.label_text_rgb),
            stroke_width_px=2,
        )
        scene_entities.append(
            {
                "entity_id": "potential_formula_label",
                "entity_type": "formula_label",
                "bbox_px": list(note_bbox),
                "meta": {"text": "Use k=1 and V=sum(q/r)"},
            }
        )
        point_center = _coord_to_px(bbox=board, x=int(scenario.point_x), y=int(scenario.point_y), coord_extent=coord_extent)
        point_bbox = _draw_point_marker(
            draw,
            bbox=board,
            coord_extent=coord_extent,
            x=int(scenario.point_x),
            y=int(scenario.point_y),
            label="P",
            render_defaults=render_defaults,
            theme=theme,
            point_font=option_font,
            target=True,
        )
        scene_entities.append(
            {
                "entity_id": "query_point",
                "entity_type": "query_point",
                "bbox_px": list(point_bbox),
                "meta": {
                    "x": int(scenario.point_x),
                    "y": int(scenario.point_y),
                    "label": "P",
                    "center_px": [round(float(point_center[0]), 3), round(float(point_center[1]), 3)],
                },
            }
        )
        charge_bboxes = []
        distance_bboxes = []
        for charge in scenario.charges:
            entity, charge_bbox = _draw_charge(
                draw,
                bbox=board,
                coord_extent=coord_extent,
                charge=charge,
                display_label=str(annotation_key_by_entity_id[str(charge.charge_id)]),
                render_defaults=render_defaults,
                theme=theme,
                charge_font=charge_font,
                label_font=label_font,
            )
            scene_entities.append(entity)
            charge_bboxes.append(list(charge_bbox))
            charge_center = _coord_to_px(bbox=board, x=int(charge.x), y=int(charge.y), coord_extent=coord_extent)
            distance_bbox = _draw_distance_label(
                draw,
                start=charge_center,
                end=point_center,
                text=f"r={int(charge.distance_units)}",
                theme=theme,
                label_font=label_font,
            )
            distance_bboxes.append(list(distance_bbox))
            scene_entities.append(
                {
                    "entity_id": f"distance_guide_{str(charge.charge_id)}",
                    "entity_type": "charge_to_point_distance_guide",
                    "bbox_px": list(distance_bbox),
                    "meta": {
                        "charge_id": str(charge.charge_id),
                        "point_id": "query_point",
                        "distance_units": int(charge.distance_units),
                    },
                }
            )
        witness_bbox = _bbox_union(point_bbox, note_bbox, *charge_bboxes, *distance_bboxes)
        scene_entities.append(
            {
                "entity_id": "potential_witness_region",
                "entity_type": "potential_witness_region",
                "bbox_px": list(witness_bbox),
                "meta": {
                    "members": ["query_point"] + [str(charge.charge_id) for charge in scenario.charges],
                    "potential_value": int(scenario.potential_value),
                },
            }
        )
        render_map.update(board_meta)
        render_map["query_point_bbox_px"] = list(point_bbox)
        render_map["charge_bboxes_px"] = [list(bbox) for bbox in charge_bboxes]
        render_map["distance_guide_bboxes_px"] = [list(bbox) for bbox in distance_bboxes]
        render_map["potential_witness_region_bbox_px"] = list(witness_bbox)

    entity_bbox_map = {
        str(entity["entity_id"]): list(entity["bbox_px"])
        for entity in scene_entities
        if entity.get("bbox_px") is not None
    }
    entity_point_map = {
        str(entity["entity_id"]): list(entity.get("meta", {}).get("center_px", []))
        for entity in scene_entities
        if "center_px" in entity.get("meta", {})
    }
    annotation_bboxes: List[List[float]] = []
    annotation_points: List[List[float]] = []
    annotation_point_map: Dict[str, List[float]] = {}
    for entity_id in scene_spec.annotation_entity_ids:
        entity_key = str(entity_id)
        if entity_key not in entity_bbox_map or entity_key not in entity_point_map:
            raise ValueError(f"missing electrostatics annotation projection for entity {entity_key!r}")
        annotation_key = str(annotation_key_by_entity_id[entity_key])
        annotation_bboxes.append(list(entity_bbox_map[entity_key]))
        annotation_points.append(list(entity_point_map[entity_key]))
        annotation_point_map[annotation_key] = list(entity_point_map[entity_key])
    render_map["annotation_entity_ids"] = list(scene_spec.annotation_entity_ids)
    render_map["annotation_key_by_entity_id"] = dict(annotation_key_by_entity_id)
    render_map["annotation_points_px"] = [list(point) for point in annotation_points]
    render_map["annotation_keyed_points_px"] = {str(key): list(point) for key, point in annotation_point_map.items()}
    return _RenderedScene(
        image=image,
        annotation_bboxes=[list(bbox) for bbox in annotation_bboxes],
        annotation_points=[list(point) for point in annotation_points],
        annotation_point_map={str(key): list(point) for key, point in annotation_point_map.items()},
        annotation_entity_ids=list(scene_spec.annotation_entity_ids),
        annotation_key_by_entity_id={str(key): str(value) for key, value in annotation_key_by_entity_id.items()},
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
    )


def _answer_type(query_id: str) -> str:
    """Return answer type for the public query."""

    if str(query_id) in {"field_direction_choice", "zero_field_point_label"}:
        return "option_letter"
    return "integer"


def _build_prompt_examples(query_id: str) -> Tuple[str, str]:
    """Return one stable prompt JSON example for the active electrostatics query."""

    if str(query_id) == "field_direction_choice":
        return build_prompt_json_examples(
            annotation_value={
                "Q1": [210, 308],
                "Q2": [496, 194],
                "Q3": [496, 446],
                "P": [444, 304],
            },
            answer_type="option_letter",
        )
    if str(query_id) == "zero_field_point_label":
        return build_prompt_json_examples(
            annotation_value={
                "Q1": [270, 330],
                "Q2": [540, 330],
            },
            answer_type="option_letter",
        )
    return build_prompt_json_examples(
        annotation_value={
            "Q1": [592, 330],
            "Q2": [428, 164],
            "Q3": [126, 330],
            "P": [444, 304],
        },
        answer_type="integer",
    )


def _direction_mode_phrase(direction_mode: str | None) -> str:
    """Return prompt-facing wording for the selected direction branch."""

    if str(direction_mode) == "force_on_positive_charge":
        return "the force on a positive test charge at P, which points in the same direction as the electric field"
    if str(direction_mode) == "force_on_negative_charge":
        return "the force on a negative test charge at P, which points opposite the electric field"
    return "the net electric field at P"


def _object_description_for_query(prompt_defaults: Dict[str, Any], *, scene_variant: str, query_id: str) -> str:
    """Return the most specific prompt-facing scene description available."""

    query_specific_key = f"object_description_{str(scene_variant)}_{str(query_id)}"
    if query_specific_key in prompt_defaults:
        return str(prompt_defaults[query_specific_key])
    return str(prompt_defaults[f"object_description_{str(scene_variant)}"])


class _PhysicsElectrostaticsFieldMapBaseTask:
    """Return one electrostatics field-map reasoning question."""

    task_id = TASK_ID
    domain = "physics"
    scene_id = "electrostatics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        rendered_scene: _RenderedScene | None = None
        scene_spec: _SceneSpec | None = None

        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                scene_spec = _sample_scene_spec(attempt_rng, axes=axes, params=params)
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
                    "coord_extent",
                    "grid_line_width_px",
                    "dense_grid_line_width_px",
                    "axis_width_px",
                    "charge_radius_px",
                    "point_radius_px",
                    "label_font_size_px",
                    "option_font_size_px",
                    "note_font_size_px",
                    "charge_font_size_px",
                    "option_panel_left_px",
                    "option_panel_top_px",
                    "option_cell_width_px",
                    "option_cell_height_px",
                    "option_cell_gap_x_px",
                    "option_cell_gap_y_px",
                    "option_arrow_length_px",
                    "option_arrow_width_px",
                    "option_arrow_head_length_px",
                    "option_arrow_head_width_px",
                )
            }
            diagram_style, diagram_style_meta = resolve_physics_diagram_style(
                instance_seed=int(instance_seed),
                params=params,
                scene_id=SCENE_ID,
                protected_colors=PHYSICS_ELECTROSTATICS_SEMANTIC_COLORS,
                allow_dark=False,
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.render.font",
                params=params,
            )
            font_record = get_font_family_record(str(font_family))
            styled_render_defaults = dict(render_defaults)
            styled_render_defaults["grid_line_width_px"] = max(1, int(diagram_style.grid_minor_width_px))
            styled_render_defaults["dense_grid_line_width_px"] = max(
                int(styled_render_defaults["grid_line_width_px"]),
                int(diagram_style.grid_major_width_px),
            )
            styled_render_defaults["axis_width_px"] = max(3, int(diagram_style.axis_stroke_width_px))
            styled_render_defaults, layout_placement_meta = _resolve_electrostatics_layout_placement(
                render_defaults=styled_render_defaults,
                params=params,
                instance_seed=int(instance_seed),
                query_id=str(axes.query_id),
            )
            background, background_meta = make_physics_diagram_background(
                canvas_width=int(styled_render_defaults["canvas_width"]),
                canvas_height=int(styled_render_defaults["canvas_height"]),
                style=diagram_style,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}.technical_diagram_background",
            )
            rendered_scene = _render_scene(
                background=background,
                render_defaults=styled_render_defaults,
                accent_color_name=str(axes.accent_color_name),
                diagram_style=diagram_style,
                scene_spec=scene_spec,
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
                    "object_description_dense_grid",
                    "object_description_clean_grid_field_direction_choice",
                    "object_description_paper_grid_field_direction_choice",
                    "object_description_dense_grid_field_direction_choice",
                    "object_description_clean_grid_zero_field_point_label",
                    "object_description_paper_grid_zero_field_point_label",
                    "object_description_dense_grid_zero_field_point_label",
                    "object_description_clean_grid_potential_value",
                    "object_description_paper_grid_potential_value",
                    "object_description_dense_grid_potential_value",
                    "answer_hint_field_direction_choice",
                    "answer_hint_zero_field_point_label",
                    "answer_hint_potential_value",
                    "annotation_hint_field_direction_choice",
                    "annotation_hint_zero_field_point_label",
                    "annotation_hint_potential_value",
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
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                    "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(axes.query_id)}"]),
                    "direction_mode_phrase": _direction_mode_phrase(axes.direction_mode),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_type = _answer_type(str(axes.query_id))
            if str(axes.query_id) == "potential_value":
                if scene_spec.potential_scenario is None:
                    raise RuntimeError("missing potential scenario after electrostatics scene render")
                answer_value: int | str = int(scene_spec.potential_scenario.potential_value)
            else:
                answer_value = str(scene_spec.correct_option_letter)
            answer_gt = TypedValue(type=str(answer_type), value=answer_value)
            annotation_gt = TypedValue(
                type="keyed_point_map",
                value={str(key): list(point) for key, point in rendered_scene.annotation_point_map.items()},
            )

            charge_count = 0
            option_count = 0
            answer_magnitude = abs(int(answer_value)) if str(answer_type) == "integer" else 0
            if scene_spec.direction_scenario is not None:
                charge_count = len(scene_spec.direction_scenario.charges)
                option_count = len(OPTION_LETTERS)
            elif scene_spec.zero_field_scenario is not None:
                charge_count = len(scene_spec.zero_field_scenario.charges)
                option_count = len(POINT_LETTERS)
            elif scene_spec.potential_scenario is not None:
                charge_count = len(scene_spec.potential_scenario.charges)


            direction_payload: Dict[str, Any] = {}
            if scene_spec.direction_scenario is not None:
                direction_payload = {
                    "charges": [
                        {
                            "charge_id": str(charge.charge_id),
                            "display_label": str(rendered_scene.annotation_key_by_entity_id.get(str(charge.charge_id), "")),
                            "charge_value": int(charge.charge_value),
                            "x": int(charge.x),
                            "y": int(charge.y),
                        }
                        for charge in scene_spec.direction_scenario.charges
                    ],
                    "point": {"label": "P", "x": int(scene_spec.direction_scenario.point_x), "y": int(scene_spec.direction_scenario.point_y)},
                    "field_direction": str(scene_spec.direction_scenario.field_direction),
                    "requested_direction": str(scene_spec.direction_scenario.requested_direction),
                    "option_directions": dict(scene_spec.direction_scenario.option_directions),
                }
            zero_payload: Dict[str, Any] = {}
            if scene_spec.zero_field_scenario is not None:
                zero_payload = {
                    "charges": [
                        {
                            "charge_id": str(charge.charge_id),
                            "display_label": str(rendered_scene.annotation_key_by_entity_id.get(str(charge.charge_id), "")),
                            "charge_value": int(charge.charge_value),
                            "x": int(charge.x),
                            "y": int(charge.y),
                        }
                        for charge in scene_spec.zero_field_scenario.charges
                    ],
                    "candidate_points": [
                        {
                            "option_letter": str(point.letter),
                            "x": int(point.x),
                            "y": int(point.y),
                            "is_correct": bool(point.is_correct),
                        }
                        for point in scene_spec.zero_field_scenario.candidate_points
                    ],
                    "charge_axis": str(scene_spec.zero_field_scenario.symmetry_axis),
                    "symmetry_axis": str(scene_spec.zero_field_scenario.symmetry_axis),
                    "correct_option_letter": str(scene_spec.zero_field_scenario.correct_option_letter),
                }
            potential_payload: Dict[str, Any] = {}
            if scene_spec.potential_scenario is not None:
                potential_payload = {
                    "charges": [
                        {
                            "charge_id": str(charge.charge_id),
                            "display_label": str(rendered_scene.annotation_key_by_entity_id.get(str(charge.charge_id), "")),
                            "charge_value": int(charge.charge_value),
                            "distance_units": int(charge.distance_units),
                            "potential_contribution": int(charge.contribution),
                            "x": int(charge.x),
                            "y": int(charge.y),
                        }
                        for charge in scene_spec.potential_scenario.charges
                    ],
                    "point": {"label": "P", "x": int(scene_spec.potential_scenario.point_x), "y": int(scene_spec.potential_scenario.point_y)},
                    "potential_value": int(scene_spec.potential_scenario.potential_value),
                    "formula": "V=sum(q/r), k=1",
                }

            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_electrostatics_field_map_{str(axes.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.query_id),
                        "direction_mode": axes.direction_mode,
                        "target_direction": axes.target_direction,
                        "accent_color_name": str(axes.accent_color_name),
                        "target_answer": answer_value,
                        "answer_type": str(answer_type),
                        "direction_scenario": dict(direction_payload),
                        "zero_field_scenario": dict(zero_payload),
                        "potential_scenario": dict(potential_payload),
                        "annotation_entity_ids": list(rendered_scene.annotation_entity_ids),
                        "annotation_key_by_entity_id": dict(rendered_scene.annotation_key_by_entity_id),
                    },
                },
                "query_spec": {
                    "query_id": str(axes.query_id),
                    "direction_mode": axes.direction_mode,
                    "target_direction": axes.target_direction,
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(axes.scene_variant),
                        "query_id": str(axes.query_id),
                        "direction_mode": axes.direction_mode,
                        "target_direction": axes.target_direction,
                        "accent_color_name": str(axes.accent_color_name),
                        "correct_option_letter": axes.correct_option_letter,
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_id_probabilities": dict(axes.query_id_probabilities),
                        "direction_mode_probabilities": dict(axes.direction_mode_probabilities),
                        "target_direction_probabilities": dict(axes.target_direction_probabilities),
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
                        "scope": "electrostatics_field_map",
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
                    "direction_mode": axes.direction_mode,
                    "target_direction": axes.target_direction,
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": answer_value,
                    "answer_type": str(answer_type),
                    "potential_answer_support": list(_potential_answer_support(params)),
                    "potential_contribution_support": list(_potential_contribution_support(params)),
                    "option_letters": list(OPTION_LETTERS) if str(axes.query_id) == "field_direction_choice" else list(POINT_LETTERS),
                    "direction_scenario": dict(direction_payload),
                    "zero_field_scenario": dict(zero_payload),
                    "potential_scenario": dict(potential_payload),
                    "correct_option_letter": scene_spec.correct_option_letter,
                    "annotation_entity_ids": list(rendered_scene.annotation_entity_ids),
                    "annotation_key_by_entity_id": dict(rendered_scene.annotation_key_by_entity_id),
                },
                "witness_symbolic": {
                    "type": "object_key_map",
                    "ids": [str(item) for item in rendered_scene.annotation_entity_ids],
                    "keys": dict(rendered_scene.annotation_key_by_entity_id),
                },
                "projected_annotation": {
                    "type": "keyed_point_map",
                    "keyed_point_map": {str(key): list(point) for key, point in rendered_scene.annotation_point_map.items()},
                    "pixel_keyed_point_map": {
                        str(key): list(point) for key, point in rendered_scene.annotation_point_map.items()
                    },
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
class PhysicsElectrostaticsFieldDirectionChoiceTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsElectrostaticsFieldMapBaseTask,
):
    """Choose the labeled arrow matching an electric-field or test-charge force direction."""

    task_id = "task_physics__electrostatic_field__field_direction_choice"
    fixed_query_id = "field_direction_choice"


@register_task
class PhysicsElectrostaticsZeroFieldPointLabelTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsElectrostaticsFieldMapBaseTask,
):
    """Choose the labeled point where unequal same-sign charges produce zero net field."""

    task_id = "task_physics__electrostatic_field__zero_field_point_label"
    fixed_query_id = "zero_field_point_label"


@register_task
class PhysicsElectrostaticsPotentialValueTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsElectrostaticsFieldMapBaseTask,
):
    """Compute signed electric potential at a marked point from shown charges and distances."""

    task_id = "task_physics__electrostatic_field__potential_value"
    fixed_query_id = "potential_value"
