"""Physics circuits task for equivalent-resistance reasoning from resistor diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import (
    apply_balanced_variant_sampling,
    resolve_compatible_scene_query_variants,
    resolve_variant,
)
from ..shared.circuit_scene import RenderedCircuitScene, render_resistor_network_scene
from ..shared.complexity import build_physics_circuit_resistance_complexity
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES
from ..shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.visual_defaults import load_physics_background_defaults, load_physics_noise_defaults


TASK_ID = "task_physics_circuits_equivalent_resistance"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "parallel",
    "simple_series_parallel",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "total_resistance",
    "missing_resistor_value",
)
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "parallel": SUPPORTED_QUERY_VARIANTS,
    "simple_series_parallel": SUPPORTED_QUERY_VARIANTS,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for resistor-network scenes."""

    canvas_width: int = 940
    canvas_height: int = 560
    terminal_left_x_px: int = 104
    terminal_radius_px: int = 12
    terminal_font_size_px: int = 24
    wire_width_px: int = 5
    resistor_box_width_px: int = 96
    resistor_box_height_px: int = 46
    resistor_font_size_px: int = 24
    label_stroke_width_px: int = 3
    parallel_rail_left_x_px: int = 268
    parallel_branch_top_y_px: int = 190
    parallel_branch_bottom_y_px: int = 430
    series_parallel_branch_left_x_px: int = 360
    resistor_value_min: int = 1
    resistor_value_max: int = 12
    parallel_target_answer_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    simple_series_parallel_target_answer_support: Tuple[int, ...] = tuple(range(2, 19))
    missing_resistor_value_support: Tuple[int, ...] = tuple(range(1, 13))
    pair_scene_width_px: int = 400
    pair_scene_height_px: int = 420
    pair_origin_top_y_px: int = 70
    pair_left_origin_x_px: int = 24
    pair_right_origin_x_px: int = 516
    pair_terminal_left_x_px: int = 54
    pair_parallel_rail_left_x_px: int = 132
    pair_parallel_branch_top_y_px: int = 146
    pair_parallel_branch_bottom_y_px: int = 306
    pair_series_parallel_branch_left_x_px: int = 152
    pair_equals_font_size_px: int = 48


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query axes and answer support for one instance."""

    scene_variant: str
    query_variant: str
    accent_color_name: str
    target_answer: int
    scene_variant_probabilities: Dict[str, float]
    query_variant_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _CircuitLayout:
    """One sampled resistor network satisfying the requested total."""

    scene_variant: str
    series_values: Tuple[int, ...]
    parallel_values: Tuple[int, ...]
    target_answer: int
    series_parallel_orientation: str | None


@dataclass(frozen=True)
class _MissingCircuitPairLayout:
    """One paired-circuit scene with a missing resistor on the left circuit."""

    scene_variant: str
    left_series_values: Tuple[int, ...]
    left_parallel_values: Tuple[int, ...]
    left_orientation: str | None
    right_series_values: Tuple[int, ...]
    right_parallel_values: Tuple[int, ...]
    right_orientation: str | None
    missing_resistor_index: int
    missing_component_group: str
    target_answer: int
    paired_total_resistance: int


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "circuits")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_physics_background_defaults(task_group="circuits")
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="circuits", apply_prob=0.0)


def _target_support_key(*, scene_variant: str, query_variant: str) -> str:
    """Return the config support key for one scene variant."""

    if str(query_variant) == "missing_resistor_value":
        return "missing_resistor_value_support"
    return {
        "parallel": "parallel_target_answer_support",
        "simple_series_parallel": "simple_series_parallel_target_answer_support",
    }[str(scene_variant)]


def _resolve_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
    query_variant: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve the sampled target resistance support for one scene family."""

    support_key = _target_support_key(scene_variant=str(scene_variant), query_variant=str(query_variant))
    fallback = getattr(_DEFAULTS, support_key)
    return resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=fallback,
        namespace=f"{TASK_ID}.target_answer.{str(scene_variant)}",
        balanced_flag_key="balanced_target_answer_sampling",
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve one compatible scene/query pair plus answer support."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    scene_variant, scene_probs, query_variant, query_probs = resolve_compatible_scene_query_variants(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_scene_variants=SUPPORTED_SCENE_VARIANTS,
        supported_query_variants=SUPPORTED_QUERY_VARIANTS,
        compatibility=COMPATIBILITY,
        scene_sampling_namespace=f"{TASK_ID}.scene_variant",
        query_sampling_namespace=f"{TASK_ID}.query_variant",
    )
    target_answer, target_answer_probabilities = _resolve_target_answer(
        instance_seed=int(instance_seed),
        params=params,
        scene_variant=str(scene_variant),
        query_variant=str(query_variant),
    )
    color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.accent_color_name")
    accent_color_name, accent_color_name_probabilities = resolve_variant(
        color_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
    )
    accent_color_name = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(accent_color_name),
        variant_probabilities=accent_color_name_probabilities,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        balance_flag_key="balanced_accent_color_name_sampling",
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        sampling_namespace=f"{TASK_ID}.accent_color_name",
    )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_variant=str(query_variant),
        accent_color_name=str(accent_color_name),
        target_answer=int(target_answer),
        scene_variant_probabilities=dict(scene_probs),
        query_variant_probabilities=dict(query_probs),
        accent_color_name_probabilities=dict(accent_color_name_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _sorted_int_tuple(*values: int) -> Tuple[int, ...]:
    """Return a canonical sorted integer tuple."""

    return tuple(sorted(int(value) for value in values))


def _parallel_equivalent_fraction(values: Sequence[int]) -> Fraction:
    """Return the exact equivalent resistance of one parallel resistor bank."""

    if not values:
        raise ValueError("parallel equivalent requires at least one resistor")
    reciprocal_sum = sum(Fraction(1, int(value)) for value in values)
    if reciprocal_sum <= 0:
        raise ValueError("parallel equivalent requires a positive reciprocal sum")
    return Fraction(1, 1) / reciprocal_sum


def _equivalent_resistance_fraction(
    *,
    scene_variant: str,
    series_values: Sequence[int],
    parallel_values: Sequence[int],
) -> Fraction:
    """Return the exact equivalent resistance for one supported circuit layout."""

    if str(scene_variant) == "parallel":
        return _parallel_equivalent_fraction(parallel_values)
    return Fraction(sum(int(value) for value in series_values), 1) + _parallel_equivalent_fraction(parallel_values)


def _series_chain_candidates_for_total(
    *,
    target_total: int,
    resistor_count: int,
    resistor_value_min: int,
    resistor_value_max: int,
) -> List[Tuple[int, ...]]:
    """Enumerate feasible fixed-length series chains for one target total."""

    candidates: List[Tuple[int, ...]] = []
    if int(resistor_count) == 1:
        if int(resistor_value_min) <= int(target_total) <= int(resistor_value_max):
            return [(int(target_total),)]
        return []
    if int(resistor_count) == 2:
        for first in range(int(resistor_value_min), int(resistor_value_max) + 1):
            second = int(target_total) - int(first)
            if int(first) <= int(second) <= int(resistor_value_max):
                candidates.append(_sorted_int_tuple(int(first), int(second)))
        return candidates
    if int(resistor_count) != 3:
        raise ValueError("series-chain candidates only support counts 1..3")
    for first in range(int(resistor_value_min), int(resistor_value_max) + 1):
        for second in range(int(first), int(resistor_value_max) + 1):
            third = int(target_total) - int(first) - int(second)
            if int(second) <= int(third) <= int(resistor_value_max):
                candidates.append(_sorted_int_tuple(int(first), int(second), int(third)))
    deduped: List[Tuple[int, ...]] = []
    seen: set[Tuple[int, ...]] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def _parallel_bank_candidates_for_total(
    *,
    target_answer: int,
    resistor_count: int,
    resistor_value_min: int,
    resistor_value_max: int,
) -> List[Tuple[int, ...]]:
    """Enumerate feasible fixed-length parallel resistor banks for one target total."""

    from fractions import Fraction

    if int(resistor_count) < 2:
        raise ValueError("parallel banks require at least two resistors")
    values = range(int(resistor_value_min), int(resistor_value_max) + 1)
    candidates: List[Tuple[int, ...]] = []

    def search(prefix: Tuple[int, ...], start_value: int) -> None:
        if len(prefix) == int(resistor_count):
            reciprocal_sum = sum(Fraction(1, int(value)) for value in prefix)
            if reciprocal_sum == Fraction(1, int(target_answer)):
                candidates.append(tuple(int(value) for value in prefix))
            return
        for value in range(int(start_value), int(resistor_value_max) + 1):
            search(prefix + (int(value),), int(value))

    search(tuple(), int(resistor_value_min))
    deduped: List[Tuple[int, ...]] = []
    seen: set[Tuple[int, ...]] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        deduped.append(candidate)
    return deduped


def _series_parallel_candidates_for_total(
    *,
    target_answer: int,
    resistor_value_min: int,
    resistor_value_max: int,
    allowed_count_pairs: Sequence[Tuple[int, int]] = ((1, 3), (2, 2), (2, 3)),
) -> List[Tuple[Tuple[int, ...], Tuple[int, ...]]]:
    """Enumerate feasible series-plus-parallel layouts with at least four resistors."""

    candidates: List[Tuple[Tuple[int, ...], Tuple[int, ...]]] = []
    for series_count, parallel_count in allowed_count_pairs:
        min_series_total = int(series_count) * int(resistor_value_min)
        max_series_total = int(series_count) * int(resistor_value_max)
        for series_total in range(int(min_series_total), int(max_series_total) + 1):
            parallel_target = int(target_answer) - int(series_total)
            if int(parallel_target) < 1:
                continue
            series_candidates = _series_chain_candidates_for_total(
                target_total=int(series_total),
                resistor_count=int(series_count),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
            )
            if not series_candidates:
                continue
            parallel_candidates = _parallel_bank_candidates_for_total(
                target_answer=int(parallel_target),
                resistor_count=int(parallel_count),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
            )
            if not parallel_candidates:
                continue
            for series_values in series_candidates:
                for parallel_values in parallel_candidates:
                    candidates.append(
                        (
                            tuple(int(value) for value in series_values),
                            tuple(int(value) for value in parallel_values),
                        )
                    )
    return candidates


def _sample_layout(
    rng,
    *,
    scene_variant: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> _CircuitLayout:
    """Sample one resistor network that realizes the requested total."""

    resistor_value_min = int(
        params.get("resistor_value_min", group_default(_GEN_DEFAULTS, "resistor_value_min", _DEFAULTS.resistor_value_min))
    )
    resistor_value_max = int(
        params.get("resistor_value_max", group_default(_GEN_DEFAULTS, "resistor_value_max", _DEFAULTS.resistor_value_max))
    )
    if str(scene_variant) == "parallel":
        branch_counts = [3, 4]
        rng.shuffle(branch_counts)
        candidates: List[Tuple[int, ...]] = []
        for branch_count in branch_counts:
            candidates = _parallel_bank_candidates_for_total(
                target_answer=int(target_answer),
                resistor_count=int(branch_count),
                resistor_value_min=int(resistor_value_min),
                resistor_value_max=int(resistor_value_max),
            )
            if candidates:
                break
        if not candidates:
            raise ValueError(f"no parallel candidates for target {target_answer}")
        chosen = list(candidates[int(rng.randrange(len(candidates)))])
        rng.shuffle(chosen)
        return _CircuitLayout(
            scene_variant=str(scene_variant),
            series_values=tuple(),
            parallel_values=tuple(int(value) for value in chosen),
            target_answer=int(target_answer),
            series_parallel_orientation=None,
        )
    candidates = _series_parallel_candidates_for_total(
        target_answer=int(target_answer),
        resistor_value_min=int(resistor_value_min),
        resistor_value_max=int(resistor_value_max),
    )
    if not candidates:
        raise ValueError(f"no series_parallel candidates for target {target_answer}")
    chosen = list(candidates[int(rng.randrange(len(candidates)))])
    series_values = list(chosen[0])
    branch_values = list(chosen[1])
    rng.shuffle(series_values)
    rng.shuffle(branch_values)
    orientation = "series_then_parallel" if rng.random() < 0.5 else "parallel_then_series"
    return _CircuitLayout(
        scene_variant=str(scene_variant),
        series_values=tuple(int(value) for value in series_values),
        parallel_values=tuple(int(value) for value in branch_values),
        target_answer=int(target_answer),
        series_parallel_orientation=str(orientation),
    )


def _parallel_missing_pair_candidates(
    *,
    target_answer: int,
    resistor_value_min: int,
    resistor_value_max: int,
) -> List[Tuple[Tuple[int, ...], Tuple[int, ...]]]:
    """Enumerate feasible paired parallel circuits for the missing-resistor query."""

    candidates: List[Tuple[Tuple[int, ...], Tuple[int, ...]]] = []

    def enumerate_known_values(count: int, start_value: int, prefix: Tuple[int, ...]) -> List[Tuple[int, ...]]:
        if int(count) == 0:
            return [tuple(int(value) for value in prefix)]
        out: List[Tuple[int, ...]] = []
        for value in range(int(start_value), int(resistor_value_max) + 1):
            out.extend(enumerate_known_values(int(count) - 1, int(value), prefix + (int(value),)))
        return out

    for left_branch_count in (2, 3):
        known_count = int(left_branch_count) - 1
        known_candidates = enumerate_known_values(int(known_count), int(resistor_value_min), tuple())
        for known_values in known_candidates:
            total_fraction = Fraction(1, 1) / (
                Fraction(1, int(target_answer)) + sum(Fraction(1, int(value)) for value in known_values)
            )
            if int(total_fraction.denominator) != 1:
                continue
            total_equivalent = int(total_fraction.numerator)
            for right_branch_count in (2, 3):
                right_candidates = _parallel_bank_candidates_for_total(
                    target_answer=int(total_equivalent),
                    resistor_count=int(right_branch_count),
                    resistor_value_min=int(resistor_value_min),
                    resistor_value_max=int(resistor_value_max),
                )
                for right_values in right_candidates:
                    full_left = tuple(sorted(tuple(int(value) for value in known_values) + (int(target_answer),)))
                    if tuple(int(value) for value in right_values) == full_left:
                        continue
                    candidates.append((tuple(int(value) for value in known_values), tuple(int(value) for value in right_values)))
    return candidates


def _simple_series_parallel_missing_pair_candidates(
    *,
    target_answer: int,
    resistor_value_min: int,
    resistor_value_max: int,
) -> List[Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], int]]:
    """Enumerate feasible paired mixed circuits with one missing left-series resistor."""

    candidates: List[Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], int]] = []
    for parallel_total in range(1, int(resistor_value_max) + 1):
        left_parallel_candidates = _parallel_bank_candidates_for_total(
            target_answer=int(parallel_total),
            resistor_count=2,
            resistor_value_min=int(resistor_value_min),
            resistor_value_max=int(resistor_value_max),
        )
        if not left_parallel_candidates:
            continue
        paired_total = int(target_answer) + int(parallel_total)
        right_candidates = _series_parallel_candidates_for_total(
            target_answer=int(paired_total),
            resistor_value_min=int(resistor_value_min),
            resistor_value_max=int(resistor_value_max),
            allowed_count_pairs=((1, 2),),
        )
        if not right_candidates:
            continue
        for left_parallel in left_parallel_candidates:
            for right_series, right_parallel in right_candidates:
                if tuple(int(value) for value in right_series) == (int(target_answer),) and tuple(
                    int(value) for value in right_parallel
                ) == tuple(int(value) for value in left_parallel):
                    continue
                candidates.append(
                    (
                        (int(target_answer),),
                        tuple(int(value) for value in left_parallel),
                        tuple(int(value) for value in right_series),
                        tuple(int(value) for value in right_parallel),
                        int(paired_total),
                    )
                )
    return candidates


def _sample_missing_pair_layout(
    rng,
    *,
    scene_variant: str,
    target_answer: int,
    params: Mapping[str, Any],
) -> _MissingCircuitPairLayout:
    """Sample one paired-circuit layout with a single missing left resistor."""

    resistor_value_min = int(
        params.get("resistor_value_min", group_default(_GEN_DEFAULTS, "resistor_value_min", _DEFAULTS.resistor_value_min))
    )
    resistor_value_max = int(
        params.get("resistor_value_max", group_default(_GEN_DEFAULTS, "resistor_value_max", _DEFAULTS.resistor_value_max))
    )
    if str(scene_variant) == "parallel":
        candidates = _parallel_missing_pair_candidates(
            target_answer=int(target_answer),
            resistor_value_min=int(resistor_value_min),
            resistor_value_max=int(resistor_value_max),
        )
        if not candidates:
            raise ValueError(f"no paired parallel candidates for missing resistor {target_answer}")
        left_known_values, right_values = candidates[int(rng.randrange(len(candidates)))]
        left_entries = [(int(value), False) for value in left_known_values] + [(int(target_answer), True)]
        rng.shuffle(left_entries)
        left_values = [int(value) for value, _ in left_entries]
        right_values_list = list(right_values)
        rng.shuffle(right_values_list)
        missing_index = next(index for index, (_, is_missing) in enumerate(left_entries, start=1) if bool(is_missing))
        paired_total = _equivalent_resistance_fraction(
            scene_variant="parallel",
            series_values=tuple(),
            parallel_values=tuple(int(value) for value in left_values),
        )
        if int(paired_total.denominator) != 1:
            raise ValueError("paired parallel missing layout must have an integral equivalent resistance")
        return _MissingCircuitPairLayout(
            scene_variant=str(scene_variant),
            left_series_values=tuple(),
            left_parallel_values=tuple(int(value) for value in left_values),
            left_orientation=None,
            right_series_values=tuple(),
            right_parallel_values=tuple(int(value) for value in right_values_list),
            right_orientation=None,
            missing_resistor_index=int(missing_index),
            missing_component_group="parallel",
            target_answer=int(target_answer),
            paired_total_resistance=int(paired_total.numerator),
        )

    candidates = _simple_series_parallel_missing_pair_candidates(
        target_answer=int(target_answer),
        resistor_value_min=int(resistor_value_min),
        resistor_value_max=int(resistor_value_max),
    )
    if not candidates:
        raise ValueError(f"no paired series-parallel candidates for missing resistor {target_answer}")
    left_series, left_parallel, right_series, right_parallel, paired_total = candidates[int(rng.randrange(len(candidates)))]
    left_orientation = "series_then_parallel" if rng.random() < 0.5 else "parallel_then_series"
    right_orientation = "series_then_parallel" if rng.random() < 0.5 else "parallel_then_series"
    right_series_list = list(right_series)
    right_parallel_list = list(right_parallel)
    rng.shuffle(right_series_list)
    rng.shuffle(right_parallel_list)
    missing_resistor_index = 1 if str(left_orientation) == "series_then_parallel" else int(len(left_parallel) + 1)
    return _MissingCircuitPairLayout(
        scene_variant=str(scene_variant),
        left_series_values=tuple(int(value) for value in left_series),
        left_parallel_values=tuple(int(value) for value in left_parallel),
        left_orientation=str(left_orientation),
        right_series_values=tuple(int(value) for value in right_series_list),
        right_parallel_values=tuple(int(value) for value in right_parallel_list),
        right_orientation=str(right_orientation),
        missing_resistor_index=int(missing_resistor_index),
        missing_component_group="series",
        target_answer=int(target_answer),
        paired_total_resistance=int(paired_total),
    )


def _build_prompt_json_examples(query_variant: str) -> Tuple[str, str]:
    """Return prompt JSON examples tailored to the active query variant."""

    evidence_value: List[List[int]]
    if str(query_variant) == "missing_resistor_value":
        evidence_value = [[174, 214, 270, 260]]
    else:
        evidence_value = [
            [322, 167, 418, 213],
            [322, 257, 418, 303],
            [322, 347, 418, 393],
        ]
    return build_prompt_json_examples(evidence_value=evidence_value, answer_type="integer")


def _pair_render_defaults(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Return local render defaults for one sub-circuit in the paired missing-resistor scene."""

    return {
        "canvas_width": int(
            params.get("pair_scene_width_px", group_default(_RENDER_DEFAULTS, "pair_scene_width_px", _DEFAULTS.pair_scene_width_px))
        ),
        "canvas_height": int(
            params.get("pair_scene_height_px", group_default(_RENDER_DEFAULTS, "pair_scene_height_px", _DEFAULTS.pair_scene_height_px))
        ),
        "terminal_left_x_px": int(
            params.get(
                "pair_terminal_left_x_px",
                group_default(_RENDER_DEFAULTS, "pair_terminal_left_x_px", _DEFAULTS.pair_terminal_left_x_px),
            )
        ),
        "terminal_radius_px": int(params.get("terminal_radius_px", group_default(_RENDER_DEFAULTS, "terminal_radius_px", _DEFAULTS.terminal_radius_px))),
        "terminal_font_size_px": int(
            params.get("terminal_font_size_px", group_default(_RENDER_DEFAULTS, "terminal_font_size_px", _DEFAULTS.terminal_font_size_px))
        ),
        "wire_width_px": int(params.get("wire_width_px", group_default(_RENDER_DEFAULTS, "wire_width_px", _DEFAULTS.wire_width_px))),
        "resistor_box_width_px": int(
            params.get("resistor_box_width_px", group_default(_RENDER_DEFAULTS, "resistor_box_width_px", _DEFAULTS.resistor_box_width_px))
        ),
        "resistor_box_height_px": int(
            params.get("resistor_box_height_px", group_default(_RENDER_DEFAULTS, "resistor_box_height_px", _DEFAULTS.resistor_box_height_px))
        ),
        "resistor_font_size_px": int(
            params.get("resistor_font_size_px", group_default(_RENDER_DEFAULTS, "resistor_font_size_px", _DEFAULTS.resistor_font_size_px))
        ),
        "label_stroke_width_px": int(
            params.get("label_stroke_width_px", group_default(_RENDER_DEFAULTS, "label_stroke_width_px", _DEFAULTS.label_stroke_width_px))
        ),
        "parallel_rail_left_x_px": int(
            params.get(
                "pair_parallel_rail_left_x_px",
                group_default(_RENDER_DEFAULTS, "pair_parallel_rail_left_x_px", _DEFAULTS.pair_parallel_rail_left_x_px),
            )
        ),
        "parallel_branch_top_y_px": int(
            params.get(
                "pair_parallel_branch_top_y_px",
                group_default(_RENDER_DEFAULTS, "pair_parallel_branch_top_y_px", _DEFAULTS.pair_parallel_branch_top_y_px),
            )
        ),
        "parallel_branch_bottom_y_px": int(
            params.get(
                "pair_parallel_branch_bottom_y_px",
                group_default(_RENDER_DEFAULTS, "pair_parallel_branch_bottom_y_px", _DEFAULTS.pair_parallel_branch_bottom_y_px),
            )
        ),
        "series_parallel_branch_left_x_px": int(
            params.get(
                "pair_series_parallel_branch_left_x_px",
                group_default(
                    _RENDER_DEFAULTS,
                    "pair_series_parallel_branch_left_x_px",
                    _DEFAULTS.pair_series_parallel_branch_left_x_px,
                ),
            )
        ),
    }


def _draw_equals_sign(image, *, center_xy: Tuple[float, float], font_size_px: int) -> List[float]:
    """Draw one centered equality sign and return its bbox."""

    draw = ImageDraw.Draw(image)
    font = load_font(int(font_size_px), bold=True)
    text = "="
    stroke_fill = resolve_text_stroke_fill((72, 76, 82))
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=3)
    left, top, right, bottom = [float(value) for value in bbox]
    origin = (
        float(center_xy[0] - (0.5 * (left + right))),
        float(center_xy[1] - (0.5 * (top + bottom))),
    )
    draw.text(origin, text, font=font, fill=(72, 76, 82), stroke_width=3, stroke_fill=tuple(int(v) for v in stroke_fill))
    return [
        round(float(origin[0] + left), 3),
        round(float(origin[1] + top), 3),
        round(float(origin[0] + right), 3),
        round(float(origin[1] + bottom), 3),
    ]


@register_task
class PhysicsCircuitsEquivalentResistanceTask:
    """Return one simple equivalent-resistance question from a resistor diagram."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "circuits"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        rendered_scene: RenderedCircuitScene | None = None
        layout: _CircuitLayout | None = None
        pair_layout: _MissingCircuitPairLayout | None = None

        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                if str(axes.query_variant) == "missing_resistor_value":
                    pair_layout = _sample_missing_pair_layout(
                        attempt_rng,
                        scene_variant=str(axes.scene_variant),
                        target_answer=int(axes.target_answer),
                        params=params,
                    )
                    layout = None
                else:
                    layout = _sample_layout(
                        attempt_rng,
                        scene_variant=str(axes.scene_variant),
                        target_answer=int(axes.target_answer),
                        params=params,
                    )
                    pair_layout = None
            except ValueError:
                continue

            background, background_meta = make_background_canvas(
                canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
                canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
            )
            if str(axes.query_variant) == "missing_resistor_value":
                pair_defaults = _pair_render_defaults(params)
                left_origin = (
                    float(
                        params.get(
                            "pair_left_origin_x_px",
                            group_default(_RENDER_DEFAULTS, "pair_left_origin_x_px", _DEFAULTS.pair_left_origin_x_px),
                        )
                    ),
                    float(
                        params.get(
                            "pair_origin_top_y_px",
                            group_default(_RENDER_DEFAULTS, "pair_origin_top_y_px", _DEFAULTS.pair_origin_top_y_px),
                        )
                    ),
                )
                right_origin = (
                    float(
                        params.get(
                            "pair_right_origin_x_px",
                            group_default(_RENDER_DEFAULTS, "pair_right_origin_x_px", _DEFAULTS.pair_right_origin_x_px),
                        )
                    ),
                    float(
                        params.get(
                            "pair_origin_top_y_px",
                            group_default(_RENDER_DEFAULTS, "pair_origin_top_y_px", _DEFAULTS.pair_origin_top_y_px),
                        )
                    ),
                )
                left_scene = render_resistor_network_scene(
                    scene_variant=str(pair_layout.scene_variant),
                    series_values=list(pair_layout.left_series_values),
                    parallel_values=list(pair_layout.left_parallel_values),
                    background=background,
                    render_defaults=pair_defaults,
                    accent_color_name=str(axes.accent_color_name),
                    series_parallel_orientation=str(pair_layout.left_orientation or "series_then_parallel"),
                    missing_resistor_indices=[int(pair_layout.missing_resistor_index)],
                    origin_offset_px=left_origin,
                    entity_id_prefix="left_",
                )
                rendered_scene = render_resistor_network_scene(
                    scene_variant=str(pair_layout.scene_variant),
                    series_values=list(pair_layout.right_series_values),
                    parallel_values=list(pair_layout.right_parallel_values),
                    background=left_scene.image,
                    render_defaults=pair_defaults,
                    accent_color_name=str(axes.accent_color_name),
                    series_parallel_orientation=str(pair_layout.right_orientation or "series_then_parallel"),
                    origin_offset_px=right_origin,
                    entity_id_prefix="right_",
                )
                equals_bbox = _draw_equals_sign(
                    rendered_scene.image,
                    center_xy=(
                        float(0.5 * ((left_origin[0] + pair_defaults["canvas_width"]) + right_origin[0])),
                        float(left_origin[1] + (0.5 * pair_defaults["canvas_height"])),
                    ),
                    font_size_px=int(
                        params.get(
                            "pair_equals_font_size_px",
                            group_default(_RENDER_DEFAULTS, "pair_equals_font_size_px", _DEFAULTS.pair_equals_font_size_px),
                        )
                    ),
                )
                missing_specs = [spec for spec in left_scene.resistor_specs if bool(spec.missing)]
                if len(missing_specs) != 1:
                    continue
                missing_spec = missing_specs[0]
                combined_entities = list(left_scene.scene_entities) + list(rendered_scene.scene_entities)
                resistor_specs = list(left_scene.resistor_specs) + list(rendered_scene.resistor_specs)
                render_map = {
                    "accent_color_name": str(axes.accent_color_name),
                    "left_scene": dict(left_scene.render_map),
                    "right_scene": dict(rendered_scene.render_map),
                    "resistor_bboxes_px": {
                        **{spec.resistor_id: list(spec.bbox_px) for spec in resistor_specs},
                    },
                    "wire_segments_px": list(left_scene.render_map["wire_segments_px"]) + list(rendered_scene.render_map["wire_segments_px"]),
                    "terminal_bboxes_px": {
                        "left_A": list(left_scene.render_map["terminal_bboxes_px"]["A"]),
                        "left_B": list(left_scene.render_map["terminal_bboxes_px"]["B"]),
                        "right_A": list(rendered_scene.render_map["terminal_bboxes_px"]["A"]),
                        "right_B": list(rendered_scene.render_map["terminal_bboxes_px"]["B"]),
                    },
                    "terminal_label_bboxes_px": {
                        "left_A": list(left_scene.render_map["terminal_label_bboxes_px"]["A"]),
                        "left_B": list(left_scene.render_map["terminal_label_bboxes_px"]["B"]),
                        "right_A": list(rendered_scene.render_map["terminal_label_bboxes_px"]["A"]),
                        "right_B": list(rendered_scene.render_map["terminal_label_bboxes_px"]["B"]),
                    },
                    "missing_resistor_entity_ids": [str(missing_spec.resistor_id)],
                    "evidence_entity_ids": [str(missing_spec.resistor_id)],
                    "equals_sign_bbox_px": list(equals_bbox),
                }
                rendered_scene = RenderedCircuitScene(
                    image=rendered_scene.image,
                    resistor_specs=resistor_specs,
                    evidence_bboxes=[list(missing_spec.bbox_px)],
                    evidence_entity_ids=[str(missing_spec.resistor_id)],
                    render_map=render_map,
                    scene_entities=combined_entities,
                )
            else:
                rendered_scene = render_resistor_network_scene(
                    scene_variant=str(layout.scene_variant),
                    series_values=list(layout.series_values),
                    parallel_values=list(layout.parallel_values),
                    background=background,
                    render_defaults={
                        key: params.get(key, group_default(_RENDER_DEFAULTS, key, getattr(_DEFAULTS, key)))
                        for key in (
                            "canvas_width",
                            "canvas_height",
                            "terminal_left_x_px",
                            "terminal_radius_px",
                            "terminal_font_size_px",
                            "wire_width_px",
                            "resistor_box_width_px",
                            "resistor_box_height_px",
                            "resistor_font_size_px",
                            "label_stroke_width_px",
                            "parallel_rail_left_x_px",
                            "parallel_branch_top_y_px",
                            "parallel_branch_bottom_y_px",
                            "series_parallel_branch_left_x_px",
                        )
                    },
                    accent_color_name=str(axes.accent_color_name),
                    series_parallel_orientation=(
                        str(layout.series_parallel_orientation)
                        if layout.series_parallel_orientation is not None
                        else "series_then_parallel"
                    ),
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
                    "task_family_key",
                    "task_key",
                    "json_output_contract",
                    "json_output_contract_answer_only",
                    "answer_hint_total_resistance",
                    "answer_hint_missing_resistor_value",
                    "evidence_hint_total_resistance",
                    "evidence_hint_missing_resistor_value",
                    "object_description_parallel_total_resistance",
                    "object_description_simple_series_parallel_total_resistance",
                    "object_description_parallel_missing_resistor_value",
                    "object_description_simple_series_parallel_missing_resistor_value",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_variant))
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                task_family_key=str(prompt_defaults["task_family_key"]),
                task_key=str(prompt_defaults["task_key"]),
                task_variant_key=str(axes.query_variant),
                answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(
                        prompt_defaults[f"object_description_{str(axes.scene_variant)}_{str(axes.query_variant)}"]
                    ),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_variant)}"]),
                    "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_variant)}"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
            evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in rendered_scene.evidence_bboxes])
            complexity = build_physics_circuit_resistance_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=self.task_id,
                scene_variant=str(axes.scene_variant),
                query_variant=str(axes.query_variant),
                resistor_count=len(rendered_scene.resistor_specs),
                target_answer=int(axes.target_answer),
            )
            support_key = _target_support_key(scene_variant=str(axes.scene_variant), query_variant=str(axes.query_variant))
            trace_payload = {
                "scene_ir": {
                    "scene_kind": (
                        f"physics_resistor_network_pair_{str(axes.scene_variant)}"
                        if str(axes.query_variant) == "missing_resistor_value"
                        else f"physics_resistor_network_{str(axes.scene_variant)}"
                    ),
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_variant": str(axes.query_variant),
                        "task_variant": str(axes.query_variant),
                        "target_answer": int(axes.target_answer),
                        "accent_color_name": str(axes.accent_color_name),
                        "evidence_entity_ids": list(rendered_scene.evidence_entity_ids),
                        "paired_total_resistance": (
                            None if pair_layout is None else int(pair_layout.paired_total_resistance)
                        ),
                    },
                },
                "query_spec": {
                    "task_variant": str(axes.query_variant),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(axes.scene_variant),
                        "query_variant": str(axes.query_variant),
                        "task_variant": str(axes.query_variant),
                        "accent_color_name": str(axes.accent_color_name),
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_variant_probabilities": dict(axes.query_variant_probabilities),
                        "task_variant_probabilities": dict(axes.query_variant_probabilities),
                        "accent_color_name_probabilities": dict(axes.accent_color_name_probabilities),
                        "target_answer": int(axes.target_answer),
                        "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    },
                },
                "render_spec": {
                    "scene_variant": str(axes.scene_variant),
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "accent_color_name": str(axes.accent_color_name),
                },
                "render_map": dict(rendered_scene.render_map),
                "execution_trace": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "task_variant": str(axes.query_variant),
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": list(
                        resolve_integer_support(
                            params,
                            gen_defaults=_GEN_DEFAULTS,
                            key=str(support_key),
                            fallback=getattr(_DEFAULTS, support_key),
                        )
                    ),
                    "series_parallel_orientation": None if layout is None else layout.series_parallel_orientation,
                    "series_values": [] if layout is None else [int(value) for value in layout.series_values],
                    "parallel_values": [] if layout is None else [int(value) for value in layout.parallel_values],
                    "paired_total_resistance": None if pair_layout is None else int(pair_layout.paired_total_resistance),
                    "missing_resistor_index": None if pair_layout is None else int(pair_layout.missing_resistor_index),
                    "missing_component_group": None if pair_layout is None else str(pair_layout.missing_component_group),
                    "left_series_values": [] if pair_layout is None else [int(value) for value in pair_layout.left_series_values],
                    "left_parallel_values": [] if pair_layout is None else [int(value) for value in pair_layout.left_parallel_values],
                    "right_series_values": [] if pair_layout is None else [int(value) for value in pair_layout.right_series_values],
                    "right_parallel_values": [] if pair_layout is None else [int(value) for value in pair_layout.right_parallel_values],
                    "left_orientation": None if pair_layout is None else pair_layout.left_orientation,
                    "right_orientation": None if pair_layout is None else pair_layout.right_orientation,
                    "resistor_specs": [
                        {
                            "resistor_id": str(spec.resistor_id),
                            "value": None if spec.value is None else int(spec.value),
                            "missing": bool(spec.missing),
                        }
                        for spec in rendered_scene.resistor_specs
                    ],
                    "evidence_entity_ids": list(rendered_scene.evidence_entity_ids),
                },
                "witness_symbolic": {
                    "type": "id_set",
                    "ids": [str(item) for item in rendered_scene.evidence_entity_ids],
                },
                "projected_evidence": {
                    "bbox_set": [list(bbox) for bbox in rendered_scene.evidence_bboxes],
                },
                "background": background_meta,
                "post_image_noise": post_noise_meta,
            }
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=answer_gt,
                evidence_gt=evidence_gt,
                image=image,
                image_id="img0",
                trace_payload=trace_payload,
                complexity=complexity,
                task_versions=default_task_versions(),
                task_variant=str(axes.query_variant),
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")


__all__ = ["PhysicsCircuitsEquivalentResistanceTask"]
