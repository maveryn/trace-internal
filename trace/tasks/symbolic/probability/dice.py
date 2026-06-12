"""Dice probability symbolic tasks."""

from __future__ import annotations

from collections import Counter, defaultdict
from math import gcd
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import temporary_default_font_family
from ..shared.common import (
    get_int_param as _get_int,
    get_int_range as _get_range,
    load_symbolic_task_defaults,
    projected_symbolic_keyed_bbox_annotation,
    resolve_symbolic_axis_variant,
)
from ..shared.dice_scene import (
    SUPPORTED_DICE_SCENE_VARIANTS,
    SUPPORTED_DICE_VISUAL_STYLES,
    DiceRenderParams,
    render_dice_probability_scene,
)
from ..shared.scene_style import make_symbolic_scene_background, resolve_symbolic_scene_style
from ..shared.visual_defaults import load_symbolic_background_defaults, load_symbolic_noise_defaults


SCENE_ID = "dice_probability"
SINGLE_ATTRIBUTE_TASK_ID = "task_symbolic__dice_probability__single_attribute_probability"
SINGLE_THRESHOLD_TASK_ID = "task_symbolic__dice_probability__single_threshold_probability"
PAIR_SUM_TASK_ID = "task_symbolic__dice_probability__pair_sum_probability"
PAIR_SUM_THRESHOLD_TASK_ID = "task_symbolic__dice_probability__pair_sum_threshold_probability"
PAIR_DIFFERENCE_TASK_ID = "task_symbolic__dice_probability__pair_difference_probability"
PAIR_ATTRIBUTE_COMBO_TASK_ID = "task_symbolic__dice_probability__pair_attribute_combo_probability"
CONDITIONAL_TASK_ID = "task_symbolic__dice_probability__dice_conditional_event_value"

SINGLE_QUERY_IDS: Tuple[str, ...] = (
    "single_parity_probability",
    "single_threshold_probability",
    "single_value_set_probability",
    "single_color_and_value_probability",
    "single_color_or_value_probability",
)
SINGLE_ATTRIBUTE_QUERY_IDS: Tuple[str, ...] = (
    "single_parity_probability",
    "single_value_set_probability",
    "single_color_and_value_probability",
    "single_color_or_value_probability",
)
SINGLE_THRESHOLD_QUERY_IDS: Tuple[str, ...] = ("single_threshold_probability",)
PAIR_QUERY_IDS: Tuple[str, ...] = (
    "pair_sum_probability",
    "pair_sum_threshold_probability",
    "pair_difference_probability",
    "pair_parity_combo_probability",
    "pair_color_value_combo_probability",
)
PAIR_SUM_QUERY_IDS: Tuple[str, ...] = ("pair_sum_probability",)
PAIR_SUM_THRESHOLD_QUERY_IDS: Tuple[str, ...] = ("pair_sum_threshold_probability",)
PAIR_DIFFERENCE_QUERY_IDS: Tuple[str, ...] = ("pair_difference_probability",)
PAIR_ATTRIBUTE_COMBO_QUERY_IDS: Tuple[str, ...] = (
    "pair_parity_combo_probability",
    "pair_color_value_combo_probability",
)
CONDITIONAL_QUERY_IDS: Tuple[str, ...] = (
    "conditional_value_property_given_color_probability",
    "conditional_color_given_value_property_probability",
    "conditional_color_given_value_set_probability",
)

DICE_COLOR_PALETTE: Tuple[Tuple[str, Tuple[int, int, int]], ...] = (
    ("red", (204, 67, 65)),
    ("blue", (55, 105, 190)),
    ("green", (53, 143, 91)),
    ("yellow", (235, 190, 58)),
    ("purple", (132, 89, 191)),
    ("orange", (218, 124, 53)),
)

_SCENE_LOAD = {
    "dice_tray_clean": 0.16,
    "dice_tray_felt": 0.22,
    "dice_tray_notebook": 0.24,
}
_REASONING_LOAD = {
    "single_parity_probability": 0.25,
    "single_threshold_probability": 0.30,
    "single_value_set_probability": 0.34,
    "single_color_and_value_probability": 0.43,
    "single_color_or_value_probability": 0.47,
    "pair_sum_probability": 0.45,
    "pair_sum_threshold_probability": 0.48,
    "pair_difference_probability": 0.50,
    "pair_parity_combo_probability": 0.46,
    "pair_color_value_combo_probability": 0.54,
    "conditional_value_property_given_color_probability": 0.48,
    "conditional_color_given_value_property_probability": 0.50,
    "conditional_color_given_value_set_probability": 0.52,
}

_SINGLE_COLOR_OR_ANSWER_TARGETS: Tuple[str, ...] = (
    "1/2",
    "2/3",
    "3/4",
    "3/5",
    "4/5",
    "4/7",
    "5/6",
    "5/7",
    "5/8",
    "6/7",
    "7/8",
    "7/9",
    "8/9",
    "9/10",
    "10/11",
    "11/12",
)
_CONDITIONAL_ANSWER_TARGETS: Tuple[str, ...] = (
    "1/3",
    "1/2",
    "2/5",
    "3/5",
    "3/4",
)

_TASK_GROUP_DEFAULTS = get_scene_defaults("symbolic", "probability")
POST_IMAGE_BACKGROUND_DEFAULTS = load_symbolic_background_defaults(scene_id="probability")
POST_IMAGE_NOISE_DEFAULTS = load_symbolic_noise_defaults(scene_id="probability", apply_prob=0.15)


def _sample_dice_probability_font(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> str:
    """Sample one role-aware font family for tray labels in a dice probability scene."""

    return sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.dice_probability.label_font",
        params={**dict(render_defaults), **dict(params)},
    )


def _font_trace_record(font_family: str) -> Dict[str, Any]:
    """Build trace metadata for the sampled dice scene label font."""

    return {
        "source": "global_font_pool",
        "font_family": str(font_family),
        "font_asset_version": font_asset_version(),
        "scope": "dice_probability_tray_labels",
    }


def _round_keyed_bbox_map(projected: Mapping[str, Any]) -> Dict[str, List[float]]:
    keyed = projected.get("keyed_bbox_map", {})
    if not isinstance(keyed, Mapping):
        raise ValueError("keyed bbox projection missing keyed_bbox_map")
    return {
        str(role): [round(float(value), 3) for value in bbox]
        for role, bbox in keyed.items()
    }


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_symbolic_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _resolve_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DICE_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_dice_visual_style(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DICE_VISUAL_STYLES,
        task_id=str(task_id),
        explicit_key="dice_visual_style",
        weights_key="dice_visual_style_weights",
        balance_flag_key="balanced_dice_visual_style_sampling",
        axis_namespace="dice_visual_style",
    )


def _dice_visual_style_metadata(style_id: str, probabilities: Mapping[str, float]) -> Dict[str, Any]:
    return {
        "style_id": str(style_id),
        "style_probabilities": {str(key): float(value) for key, value in probabilities.items()},
        "semantic_color_policy": {
            "die_face_colors_preserved": True,
            "pip_count_and_positions_preserved": True,
            "style_is_non_semantic": True,
        },
    }


def _resolve_query_id(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    supported_queries: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    effective_params = dict(params)
    if effective_params.get("query_id") is None and effective_params.get("query_variant") is not None:
        effective_params["query_id"] = str(effective_params["query_variant"])
    return resolve_symbolic_axis_variant(
        params=effective_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=[str(query) for query in supported_queries],
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _bbox_tuple(raw: Any, fallback: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) and len(raw) >= 4:
        return tuple(int(value) for value in raw[:4])  # type: ignore[return-value]
    return tuple(int(value) for value in fallback)


def _resolve_render_params(render_defaults: Mapping[str, Any]) -> DiceRenderParams:
    return DiceRenderParams(
        canvas_width=int(render_defaults.get("canvas_width", 1100)),
        canvas_height=int(render_defaults.get("canvas_height", 780)),
        single_tray_bbox_px=_bbox_tuple(render_defaults.get("single_tray_bbox_px"), (145, 112, 955, 650)),
        pair_left_tray_bbox_px=_bbox_tuple(render_defaults.get("pair_left_tray_bbox_px"), (68, 142, 522, 628)),
        pair_right_tray_bbox_px=_bbox_tuple(render_defaults.get("pair_right_tray_bbox_px"), (578, 142, 1032, 628)),
        die_size_px=int(render_defaults.get("die_size_px", 72)),
        die_gap_px=int(render_defaults.get("die_gap_px", 18)),
        tray_corner_radius_px=int(render_defaults.get("tray_corner_radius_px", 24)),
        tray_outline_width_px=int(render_defaults.get("tray_outline_width_px", 3)),
        die_corner_radius_px=int(render_defaults.get("die_corner_radius_px", 14)),
        die_outline_width_px=int(render_defaults.get("die_outline_width_px", 3)),
        pip_radius_px=int(render_defaults.get("pip_radius_px", 6)),
        title_font_size_px=int(render_defaults.get("title_font_size_px", 28)),
    )


def _format_fraction(numerator: int, denominator: int) -> str:
    if int(denominator) <= 0:
        raise ValueError("probability denominator must be positive")
    common = gcd(abs(int(numerator)), abs(int(denominator)))
    return f"{int(numerator) // common}/{int(denominator) // common}"


def _valid_favorable_count(count: int, total: int, *, min_count: int, max_count: int) -> bool:
    return int(min_count) <= int(count) <= min(int(total) - 1, int(max_count))


def _select_event_candidate(
    candidates: Sequence[Mapping[str, Any]],
    *,
    params: Mapping[str, Any],
    rng,
    favorable_key: str,
    denominator_key: str | None = None,
    fixed_total: int | None = None,
    answer_targets: Sequence[str] | None = None,
) -> Dict[str, Any]:
    if not candidates:
        raise RuntimeError("failed to choose a nontrivial dice probability event")

    enriched: List[Dict[str, Any]] = []
    for candidate in candidates:
        item = dict(candidate)
        favorable_count = int(len(item[str(favorable_key)]))
        total_count = int(len(item[str(denominator_key)])) if denominator_key else int(fixed_total or 0)
        item["favorable_outcome_count"] = int(favorable_count)
        item["total_outcome_count"] = int(total_count)
        item["answer_value"] = _format_fraction(int(favorable_count), int(total_count))
        enriched.append(item)

    by_answer: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in enriched:
        by_answer[str(item["answer_value"])].append(dict(item))
    if answer_targets:
        index = rng.randrange(len(answer_targets))
        target = str(list(answer_targets)[int(index) % len(answer_targets)])
        bucket = list(by_answer.get(target, []))
        if not bucket:
            raise RuntimeError(f"no candidate for balanced answer target {target}")
        rng.shuffle(bucket)
        return dict(bucket[0])
    answers = sorted(by_answer)
    index = rng.randrange(len(answers))
    bucket = list(by_answer[answers[int(index) % len(answers)]])
    rng.shuffle(bucket)
    return dict(bucket[0])


def _is_prime(value: int) -> bool:
    return int(value) in {2, 3, 5}


def _numeric_properties() -> List[Tuple[str, Callable[[int], bool], Dict[str, Any]]]:
    return [
        ("shows an even value", lambda value: int(value) % 2 == 0, {"property": "even"}),
        ("shows an odd value", lambda value: int(value) % 2 == 1, {"property": "odd"}),
        ("shows a prime value", _is_prime, {"property": "prime"}),
        ("shows a value at least 4", lambda value: int(value) >= 4, {"property": "at_least", "threshold": 4}),
        ("shows a value at most 3", lambda value: int(value) <= 3, {"property": "at_most", "threshold": 3}),
    ]


def _conditional_value_properties() -> List[Tuple[str, Callable[[int], bool], Dict[str, Any]]]:
    properties = list(_numeric_properties())
    for a in range(1, 7):
        for b in range(a + 1, 7):
            values = {int(a), int(b)}
            properties.append(
                (
                    f"shows either {a} or {b}",
                    lambda value, values=values: int(value) in values,
                    {"property": "value_set", "target_values": [int(a), int(b)]},
                )
            )
    return properties


def _sample_dice(
    *,
    tray_id: str,
    count: int,
    rng,
    color_pool_size: int,
) -> List[Dict[str, Any]]:
    color_pool = list(DICE_COLOR_PALETTE[: max(3, min(len(DICE_COLOR_PALETTE), int(color_pool_size)))])
    dice: List[Dict[str, Any]] = []
    for index in range(int(count)):
        color_name, color_rgb = color_pool[int(rng.randrange(len(color_pool)))]
        value = int(rng.randint(1, 6))
        dice.append(
            {
                "die_id": f"{tray_id}_die_{index}",
                "tray_id": str(tray_id),
                "die_index": int(index),
                "value": int(value),
                "color_name": str(color_name),
                "color_rgb": [int(channel) for channel in color_rgb],
            }
        )
    return dice


def _fraction_count_pairs(
    *,
    target: str,
    min_denominator: int,
    max_denominator: int,
    min_favorable: int,
    max_favorable: int,
) -> List[Tuple[int, int]]:
    pairs: List[Tuple[int, int]] = []
    for denominator in range(int(min_denominator), int(max_denominator) + 1):
        for favorable in range(int(min_favorable), min(int(max_favorable), int(denominator) - 1) + 1):
            if _format_fraction(int(favorable), int(denominator)) == str(target):
                pairs.append((int(favorable), int(denominator)))
    return pairs


def _sample_value_property_given_color_dice(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    count_min: int,
    count_max: int,
    color_pool_size: int,
    fixed_count: int | None,
    rng,
) -> Tuple[List[Dict[str, Any]], str]:
    min_denominator = _get_int(params, gen_defaults, "conditional_denominator_count_min", 3)
    raw_max_denominator = _get_int(params, gen_defaults, "conditional_denominator_count_max", 0)
    min_favorable = _get_int(params, gen_defaults, "conditional_favorable_count_min", 1)
    raw_max_favorable = _get_int(params, gen_defaults, "conditional_favorable_count_max", 0)
    max_total_count = int(fixed_count) if fixed_count is not None else int(count_max)
    max_denominator = int(raw_max_denominator) if int(raw_max_denominator) > 0 else int(count_max)
    max_favorable = int(raw_max_favorable) if int(raw_max_favorable) > 0 else max(1, int(max_denominator) - 1)
    feasible_targets: List[Tuple[str, List[Tuple[int, int]]]] = []
    for target in _CONDITIONAL_ANSWER_TARGETS:
        pairs = _fraction_count_pairs(
            target=str(target),
            min_denominator=int(min_denominator),
            max_denominator=min(int(max_denominator), int(max_total_count) - 1),
            min_favorable=int(min_favorable),
            max_favorable=int(max_favorable),
        )
        if pairs:
            feasible_targets.append((str(target), list(pairs)))
    if not feasible_targets:
        raise RuntimeError("no feasible conditional dice answer targets for current count constraints")

    target_answer, count_pairs = feasible_targets[int(rng.randrange(len(feasible_targets)))]
    favorable_count, denominator_count = count_pairs[int(rng.randrange(len(count_pairs)))]
    if fixed_count is not None:
        total_count = int(fixed_count)
    else:
        min_total = max(int(count_min), int(denominator_count) + 1)
        if int(min_total) > int(count_max):
            raise RuntimeError("conditional dice count range cannot fit the target color group plus distractors")
        total_count = int(rng.randint(int(min_total), int(count_max)))

    color_pool = list(DICE_COLOR_PALETTE[: max(3, min(len(DICE_COLOR_PALETTE), int(color_pool_size)))])
    target_color_name, target_color_rgb = color_pool[int(rng.randrange(len(color_pool)))]
    distractor_colors = [color for color in color_pool if str(color[0]) != str(target_color_name)]
    if not distractor_colors:
        raise RuntimeError("conditional dice construction needs at least one distractor color")

    properties = _conditional_value_properties()
    _description, predicate, _meta = properties[int(rng.randrange(len(properties)))]
    favorable_values = [value for value in range(1, 7) if predicate(int(value))]
    unfavorable_values = [value for value in range(1, 7) if not predicate(int(value))]
    if not favorable_values or not unfavorable_values:
        raise RuntimeError("conditional dice value predicate must have favorable and unfavorable values")

    raw_dice: List[Dict[str, Any]] = []
    for _ in range(int(favorable_count)):
        raw_dice.append(
            {
                "value": int(favorable_values[int(rng.randrange(len(favorable_values)))]),
                "color_name": str(target_color_name),
                "color_rgb": [int(channel) for channel in target_color_rgb],
            }
        )
    for _ in range(int(denominator_count) - int(favorable_count)):
        raw_dice.append(
            {
                "value": int(unfavorable_values[int(rng.randrange(len(unfavorable_values)))]),
                "color_name": str(target_color_name),
                "color_rgb": [int(channel) for channel in target_color_rgb],
            }
        )
    for _ in range(int(total_count) - int(denominator_count)):
        color_name, color_rgb = distractor_colors[int(rng.randrange(len(distractor_colors)))]
        raw_dice.append(
            {
                "value": int(rng.randint(1, 6)),
                "color_name": str(color_name),
                "color_rgb": [int(channel) for channel in color_rgb],
            }
        )
    rng.shuffle(raw_dice)
    dice: List[Dict[str, Any]] = []
    for index, die in enumerate(raw_dice):
        dice.append(
            {
                "die_id": f"tray_die_{index}",
                "tray_id": "tray",
                "die_index": int(index),
                "value": int(die["value"]),
                "color_name": str(die["color_name"]),
                "color_rgb": [int(channel) for channel in die["color_rgb"]],
            }
        )
    return dice, str(target_answer)


def _color_names(dice: Sequence[Mapping[str, Any]]) -> List[str]:
    return sorted({str(die["color_name"]) for die in dice})


def _choose_single_event(
    *,
    query_id: str,
    dice: Sequence[Mapping[str, Any]],
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    rng,
) -> Dict[str, Any]:
    total = len(dice)
    min_count = _get_int(params, gen_defaults, "single_favorable_count_min", 2)
    max_count = _get_int(params, gen_defaults, "single_favorable_count_max", max(2, int(total) - 2))
    candidates: List[Dict[str, Any]] = []

    if str(query_id) == "single_parity_probability":
        for description, predicate, meta in _numeric_properties()[:2]:
            favorable = [str(die["die_id"]) for die in dice if predicate(int(die["value"]))]
            if _valid_favorable_count(len(favorable), total, min_count=min_count, max_count=max_count):
                candidates.append({"event_description": str(description), "favorable_die_ids": list(favorable), **meta})
    elif str(query_id) == "single_threshold_probability":
        for description, predicate, meta in _numeric_properties()[3:]:
            favorable = [str(die["die_id"]) for die in dice if predicate(int(die["value"]))]
            if _valid_favorable_count(len(favorable), total, min_count=min_count, max_count=max_count):
                candidates.append({"event_description": str(description), "favorable_die_ids": list(favorable), **meta})
    elif str(query_id) == "single_value_set_probability":
        for a in range(1, 7):
            for b in range(a + 1, 7):
                values = {int(a), int(b)}
                favorable = [str(die["die_id"]) for die in dice if int(die["value"]) in values]
                if _valid_favorable_count(len(favorable), total, min_count=min_count, max_count=max_count):
                    candidates.append(
                        {
                            "event_description": f"shows either {a} or {b}",
                            "target_values": [int(a), int(b)],
                            "favorable_die_ids": list(favorable),
                        }
                    )
    elif str(query_id) in {"single_color_and_value_probability", "single_color_or_value_probability"}:
        for color in _color_names(dice):
            for description, predicate, meta in _numeric_properties():
                if str(query_id) == "single_color_and_value_probability":
                    favorable = [
                        str(die["die_id"])
                        for die in dice
                        if str(die["color_name"]) == str(color) and predicate(int(die["value"]))
                    ]
                    event_description = f"is {color} and {description}"
                else:
                    favorable = [
                        str(die["die_id"])
                        for die in dice
                        if str(die["color_name"]) == str(color) or predicate(int(die["value"]))
                    ]
                    event_description = f"is {color} or {description}"
                if _valid_favorable_count(len(favorable), total, min_count=min_count, max_count=max_count):
                    candidates.append(
                        {
                            "event_description": event_description,
                            "target_color": str(color),
                            "favorable_die_ids": list(favorable),
                            **meta,
                        }
                    )
    else:
        raise RuntimeError(f"unsupported single-dice probability query: {query_id}")

    return _select_event_candidate(
        candidates,
        params=params,
        rng=rng,
        favorable_key="favorable_die_ids",
        fixed_total=int(total),
        answer_targets=_SINGLE_COLOR_OR_ANSWER_TARGETS
        if str(query_id) == "single_color_or_value_probability"
        else None,
    )


def _choose_pair_event(
    *,
    query_id: str,
    dice_a: Sequence[Mapping[str, Any]],
    dice_b: Sequence[Mapping[str, Any]],
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    rng,
) -> Dict[str, Any]:
    total = int(len(dice_a) * len(dice_b))
    min_count = _get_int(params, gen_defaults, "pair_favorable_count_min", 2)
    max_count = _get_int(params, gen_defaults, "pair_favorable_count_max", max(2, int(total) - 2))
    candidates: List[Dict[str, Any]] = []

    def pair_ids(predicate: Callable[[Mapping[str, Any], Mapping[str, Any]], bool]) -> List[List[str]]:
        return [
            [str(a["die_id"]), str(b["die_id"])]
            for a in dice_a
            for b in dice_b
            if predicate(a, b)
        ]

    if str(query_id) == "pair_sum_probability":
        for target in range(3, 12):
            favorable_pairs = pair_ids(lambda a, b, target=target: int(a["value"]) + int(b["value"]) == int(target))
            if _valid_favorable_count(len(favorable_pairs), total, min_count=min_count, max_count=max_count):
                candidates.append(
                    {
                        "event_description": f"the selected values sum to {target}",
                        "target_sum": int(target),
                        "favorable_pairs": list(favorable_pairs),
                    }
                )
    elif str(query_id) == "pair_sum_threshold_probability":
        for threshold in range(5, 11):
            favorable_pairs = pair_ids(lambda a, b, threshold=threshold: int(a["value"]) + int(b["value"]) >= int(threshold))
            if _valid_favorable_count(len(favorable_pairs), total, min_count=min_count, max_count=max_count):
                candidates.append(
                    {
                        "event_description": f"the selected values sum to at least {threshold}",
                        "threshold": int(threshold),
                        "favorable_pairs": list(favorable_pairs),
                    }
                )
    elif str(query_id) == "pair_difference_probability":
        for difference in range(0, 5):
            favorable_pairs = pair_ids(lambda a, b, difference=difference: abs(int(a["value"]) - int(b["value"])) == int(difference))
            if _valid_favorable_count(len(favorable_pairs), total, min_count=min_count, max_count=max_count):
                candidates.append(
                    {
                        "event_description": f"the absolute difference between the selected values is {difference}",
                        "target_difference": int(difference),
                        "favorable_pairs": list(favorable_pairs),
                    }
                )
    elif str(query_id) == "pair_parity_combo_probability":
        for parity_a, predicate_a in (
            ("even", lambda value: int(value) % 2 == 0),
            ("odd", lambda value: int(value) % 2 == 1),
        ):
            for parity_b, predicate_b in (
                ("even", lambda value: int(value) % 2 == 0),
                ("odd", lambda value: int(value) % 2 == 1),
            ):
                favorable_pairs = pair_ids(
                    lambda a, b, predicate_a=predicate_a, predicate_b=predicate_b: predicate_a(int(a["value"]))
                    and predicate_b(int(b["value"]))
                )
                if _valid_favorable_count(len(favorable_pairs), total, min_count=min_count, max_count=max_count):
                    if str(parity_a) == str(parity_b):
                        event_description = f"both selected dice show {parity_a} values"
                    else:
                        event_description = f"the Tray A die shows an {parity_a} value and the Tray B die shows an {parity_b} value"
                    candidates.append(
                        {
                            "event_description": str(event_description),
                            "tray_a_parity": str(parity_a),
                            "tray_b_parity": str(parity_b),
                            "favorable_pairs": list(favorable_pairs),
                        }
                    )
    elif str(query_id) == "pair_color_value_combo_probability":
        for color in _color_names(dice_a):
            for description, predicate, meta in _numeric_properties():
                favorable_pairs = pair_ids(
                    lambda a, b, color=color, predicate=predicate: str(a["color_name"]) == str(color) and predicate(int(b["value"]))
                )
                if _valid_favorable_count(len(favorable_pairs), total, min_count=min_count, max_count=max_count):
                    candidates.append(
                        {
                            "event_description": f"the Tray A die is {color} and the Tray B die {description}",
                            "target_color": str(color),
                            "favorable_pairs": list(favorable_pairs),
                            **meta,
                        }
                    )
    else:
        raise RuntimeError(f"unsupported pair-dice probability query: {query_id}")

    selected = _select_event_candidate(
        candidates,
        params=params,
        rng=rng,
        favorable_key="favorable_pairs",
        fixed_total=int(total),
    )
    selected["supporting_die_ids"] = sorted({die_id for pair in selected["favorable_pairs"] for die_id in pair})
    return selected


def _choose_conditional_event(
    *,
    query_id: str,
    dice: Sequence[Mapping[str, Any]],
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    rng,
    answer_targets: Sequence[str] | None = _CONDITIONAL_ANSWER_TARGETS,
) -> Dict[str, Any]:
    min_denominator = _get_int(params, gen_defaults, "conditional_denominator_count_min", 3)
    max_denominator = _get_int(params, gen_defaults, "conditional_denominator_count_max", 0)
    min_favorable = _get_int(params, gen_defaults, "conditional_favorable_count_min", 1)
    max_favorable = _get_int(params, gen_defaults, "conditional_favorable_count_max", 0)
    candidates: List[Dict[str, Any]] = []

    def add_candidate(
        *,
        given_description: str,
        event_description: str,
        denominator_ids: Sequence[str],
        favorable_ids: Sequence[str],
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        if len(denominator_ids) < int(min_denominator):
            return
        if int(max_denominator) > 0 and len(denominator_ids) > int(max_denominator):
            return
        if not (int(min_favorable) <= len(favorable_ids) < len(denominator_ids)):
            return
        if int(max_favorable) > 0 and len(favorable_ids) > int(max_favorable):
            return
        payload: Dict[str, Any] = {
            "given_description": str(given_description),
            "event_description": str(event_description),
            "denominator_die_ids": [str(item) for item in denominator_ids],
            "favorable_die_ids": [str(item) for item in favorable_ids],
        }
        if extra:
            payload.update(dict(extra))
        candidates.append(payload)

    if str(query_id) == "conditional_value_property_given_color_probability":
        properties = _conditional_value_properties()
        for color in _color_names(dice):
            denominator = [str(die["die_id"]) for die in dice if str(die["color_name"]) == str(color)]
            color_dice = [die for die in dice if str(die["color_name"]) == str(color)]
            for description, predicate, meta in properties:
                favorable = [str(die["die_id"]) for die in color_dice if predicate(int(die["value"]))]
                add_candidate(
                    given_description=f"the selected die is {color}",
                    event_description=str(description),
                    denominator_ids=denominator,
                    favorable_ids=favorable,
                    extra={"target_color": str(color), **meta},
                )
    elif str(query_id) == "conditional_color_given_value_property_probability":
        for description, predicate, meta in _numeric_properties():
            denominator_dice = [die for die in dice if predicate(int(die["value"]))]
            denominator = [str(die["die_id"]) for die in denominator_dice]
            for color in _color_names(denominator_dice):
                favorable = [str(die["die_id"]) for die in denominator_dice if str(die["color_name"]) == str(color)]
                add_candidate(
                    given_description=f"the selected die {description}",
                    event_description=f"is {color}",
                    denominator_ids=denominator,
                    favorable_ids=favorable,
                    extra={"target_color": str(color), **meta},
                )
    elif str(query_id) == "conditional_color_given_value_set_probability":
        value_sets: List[Tuple[str, set[int], List[int]]] = []
        for a in range(1, 7):
            for b in range(a + 1, 7):
                value_sets.append((f"shows either {a} or {b}", {int(a), int(b)}, [int(a), int(b)]))
                for c in range(b + 1, 7):
                    value_sets.append((f"shows one of {a}, {b}, or {c}", {int(a), int(b), int(c)}, [int(a), int(b), int(c)]))
        for given_description, values, target_values in value_sets:
            denominator_dice = [die for die in dice if int(die["value"]) in values]
            denominator = [str(die["die_id"]) for die in denominator_dice]
            for color in _color_names(denominator_dice):
                favorable = [str(die["die_id"]) for die in denominator_dice if str(die["color_name"]) == str(color)]
                add_candidate(
                    given_description=str(given_description),
                    event_description=f"is {color}",
                    denominator_ids=denominator,
                    favorable_ids=favorable,
                    extra={"target_color": str(color), "target_values": list(target_values)},
                )
    else:
        raise RuntimeError(f"unsupported conditional-dice probability query: {query_id}")

    return _select_event_candidate(
        candidates,
        params=params,
        rng=rng,
        favorable_key="favorable_die_ids",
        denominator_key="denominator_die_ids",
        answer_targets=answer_targets,
    )


def _build_single_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.single_dataset")
    count_min, count_max = _get_range(
        params,
        gen_defaults,
        min_key="single_dice_count_min",
        max_key="single_dice_count_max",
        fallback_min=8,
        fallback_max=16,
    )
    color_pool_size = _get_int(params, gen_defaults, "dice_color_pool_size", 5)
    for _attempt in range(400):
        count = int(params.get("single_dice_count", rng.randint(int(count_min), int(count_max))))
        dice = _sample_dice(tray_id="tray", count=count, rng=rng, color_pool_size=int(color_pool_size))
        try:
            event = _choose_single_event(query_id=str(query_id), dice=dice, params=params, gen_defaults=gen_defaults, rng=rng)
            return {
                "mode": "single",
                "tray_specs": [{"tray_id": "tray", "title": "Dice tray", "dice": dice}],
                "dice_count": int(count),
                "dice_count_range": [int(count_min), int(count_max)],
                "event": dict(event),
                "answer_value": str(event["answer_value"]),
                "calculation_supporting_item_ids": list(event["favorable_die_ids"]),
                "annotation_item_ids": ["tray"],
            }
        except RuntimeError:
            continue
    raise RuntimeError("failed to build single-dice probability dataset")


def _build_pair_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.pair_dataset")
    count_min, count_max = _get_range(
        params,
        gen_defaults,
        min_key="pair_dice_count_min",
        max_key="pair_dice_count_max",
        fallback_min=4,
        fallback_max=6,
    )
    color_pool_size = _get_int(params, gen_defaults, "dice_color_pool_size", 5)
    for _attempt in range(500):
        count_a = int(params.get("pair_dice_count_a", rng.randint(int(count_min), int(count_max))))
        count_b = int(params.get("pair_dice_count_b", rng.randint(int(count_min), int(count_max))))
        dice_a = _sample_dice(tray_id="tray_a", count=count_a, rng=rng, color_pool_size=int(color_pool_size))
        dice_b = _sample_dice(tray_id="tray_b", count=count_b, rng=rng, color_pool_size=int(color_pool_size))
        try:
            event = _choose_pair_event(
                query_id=str(query_id),
                dice_a=dice_a,
                dice_b=dice_b,
                params=params,
                gen_defaults=gen_defaults,
                rng=rng,
            )
            return {
                "mode": "pair",
                "tray_specs": [
                    {"tray_id": "tray_a", "title": "Tray A", "dice": dice_a},
                    {"tray_id": "tray_b", "title": "Tray B", "dice": dice_b},
                ],
                "dice_count_a": int(count_a),
                "dice_count_b": int(count_b),
                "dice_count_range": [int(count_min), int(count_max)],
                "event": dict(event),
                "answer_value": str(event["answer_value"]),
                "calculation_supporting_item_ids": list(event["supporting_die_ids"]),
                "annotation_item_ids": ["tray_a", "tray_b"],
            }
        except RuntimeError:
            continue
    raise RuntimeError("failed to build pair-dice probability dataset")


def _build_conditional_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.conditional_dataset")
    count_min, count_max = _get_range(
        params,
        gen_defaults,
        min_key="conditional_dice_count_min",
        max_key="conditional_dice_count_max",
        fallback_min=12,
        fallback_max=18,
    )
    color_pool_size = _get_int(params, gen_defaults, "dice_color_pool_size", 5)
    for _attempt in range(600):
        fixed_count = int(params["conditional_dice_count"]) if "conditional_dice_count" in params else None
        count = int(fixed_count) if fixed_count is not None else int(rng.randint(int(count_min), int(count_max)))
        answer_targets: Sequence[str] | None = _CONDITIONAL_ANSWER_TARGETS
        if str(query_id) == "conditional_value_property_given_color_probability":
            dice, target_answer = _sample_value_property_given_color_dice(
                params=params,
                gen_defaults=gen_defaults,
                count_min=int(count_min),
                count_max=int(count_max),
                color_pool_size=int(color_pool_size),
                fixed_count=fixed_count,
                rng=rng,
            )
            count = int(len(dice))
            answer_targets = (str(target_answer),)
        else:
            dice = _sample_dice(tray_id="tray", count=count, rng=rng, color_pool_size=int(color_pool_size))
        try:
            event = _choose_conditional_event(
                query_id=str(query_id),
                dice=dice,
                params=params,
                gen_defaults=gen_defaults,
                rng=rng,
                answer_targets=answer_targets,
            )
            return {
                "mode": "conditional",
                "tray_specs": [{"tray_id": "tray", "title": "Dice tray", "dice": dice}],
                "dice_count": int(count),
                "dice_count_range": [int(count_min), int(count_max)],
                "event": dict(event),
                "answer_value": str(event["answer_value"]),
                "calculation_supporting_item_ids": list(event["favorable_die_ids"]),
                "denominator_supporting_item_ids": list(event["denominator_die_ids"]),
                "annotation_item_ids": ["tray"],
            }
        except RuntimeError:
            continue
    raise RuntimeError("failed to build conditional-dice probability dataset")


def _build_prompt(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
    event_description: str,
    given_description: str | None = None,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    required = [
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        f"object_description_{scene_variant}",
        "answer_hint",
        f"annotation_hint_{query_id}",
        f"json_example_{query_id}",
        f"json_example_answer_only_{query_id}",
    ]
    prompt_values = required_group_defaults(
        prompt_defaults,
        tuple(required),
        context=f"prompt defaults for {task_id}",
    )
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "event_description": str(event_description),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_values[f"annotation_hint_{query_id}"]),
        "answer_hint": str(prompt_values["answer_hint"]),
        "json_example": str(prompt_values[f"json_example_{query_id}"]),
        "json_example_answer_only": str(prompt_values[f"json_example_answer_only_{query_id}"]),
    }
    if given_description is not None:
        slots["given_description"] = str(given_description)
    prompt_selection = render_task_prompt_variants(
        domain="symbolic",
        scene_id="probability",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=str(query_id),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
        "bundle_id": str(prompt_values["bundle_id"]),
    }


class _DiceProbabilityBaseTask:
    """Base generator for visible-top dice probability tasks."""

    domain = "symbolic"
    scene_id = "probability"
    default_dataset_enabled = True
    supported_query_ids: Tuple[str, ...]
    dataset_family: str

    def _build_dataset(
        self,
        *,
        query_id: str,
        params: Mapping[str, Any],
        gen_defaults: Mapping[str, Any],
        instance_seed: int,
    ) -> Dict[str, Any]:
        if str(self.dataset_family) == "single":
            return _build_single_dataset(
                query_id=str(query_id),
                params=params,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                task_id=str(self.task_id),
            )
        if str(self.dataset_family) == "pair":
            return _build_pair_dataset(
                query_id=str(query_id),
                params=params,
                gen_defaults=gen_defaults,
                instance_seed=int(instance_seed),
                task_id=str(self.task_id),
            )
        if str(self.dataset_family) != "conditional":
            raise ValueError(f"unsupported dice probability dataset_family: {self.dataset_family!r}")
        return _build_conditional_dataset(
            query_id=str(query_id),
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_id_probabilities = _resolve_query_id(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
            supported_queries=self.supported_query_ids,
        )
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )
        dice_visual_style, dice_visual_style_probabilities = _resolve_dice_visual_style(
            params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(self.task_id),
        )
        dataset = self._build_dataset(
            query_id=str(query_id),
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
        )
        render_params = _resolve_render_params(render_defaults)
        font_family = _sample_dice_probability_font(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
            render_defaults=render_defaults,
        )
        scene_style, scene_style_meta = resolve_symbolic_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.dice_probability_background",
        )
        background, background_meta = make_symbolic_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        with temporary_default_font_family(str(font_family)):
            rendered_scene = render_dice_probability_scene(
                background,
                scene_variant=str(scene_variant),
                mode=str(dataset["mode"]),
                tray_specs=list(dataset["tray_specs"]),
                render_params=render_params,
                scene_style=scene_style,
                visual_style=str(dice_visual_style),
            )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        event = dict(dataset["event"])
        prompt, prompt_variants, prompt_meta = _build_prompt(
            task_id=str(self.task_id),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
            event_description=str(event["event_description"]),
            given_description=str(event["given_description"]) if "given_description" in event else None,
        )
        annotation_item_ids = [str(item_id) for item_id in dataset["annotation_item_ids"]]
        calculation_supporting_item_ids = [str(item_id) for item_id in dataset["calculation_supporting_item_ids"]]
        annotation_role_item_ids = (
            {"tray_a": "tray_a", "tray_b": "tray_b"}
            if str(dataset["mode"]) == "pair"
            else {"dice_tray": "tray"}
        )
        annotation_projection = projected_symbolic_keyed_bbox_annotation(rendered_scene.item_bbox_map, annotation_role_item_ids)
        annotation_bboxes = _round_keyed_bbox_map(annotation_projection)
        annotation_projection = {
            "type": "keyed_bbox_map",
            "keyed_bbox_map": dict(annotation_bboxes),
            "pixel_keyed_bbox_map": dict(annotation_bboxes),
            "value": dict(annotation_bboxes),
        }
        if len(annotation_bboxes) != len(annotation_role_item_ids):
            raise ValueError("dice probability annotation projection dropped tray boxes")

        answer_value = str(dataset["answer_value"])
        answer_gt = TypedValue(type="string", value=str(answer_value))
        annotation_gt = TypedValue(type="keyed_bbox_map", value=dict(annotation_bboxes))
        tray_specs = [dict(tray) for tray in dataset["tray_specs"]]
        all_dice = [dict(die) for tray in tray_specs for die in tray["dice"]]
        visual_scan_count = len(all_dice)
        mode = str(dataset["mode"])
        visual_scan_bounds = [8, 18] if mode != "pair" else [8, 12]
        outcome_count = int(event["total_outcome_count"])
        outcome_bounds = [8, 22] if mode in {"single", "conditional"} else [16, 36]
        visual_scan = normalize_int_with_bounds(int(visual_scan_count), visual_scan_bounds)
        outcome_load = normalize_int_with_bounds(int(outcome_count), outcome_bounds)
        reasoning_load = min(1.0, float(_REASONING_LOAD[str(query_id)]) + (0.12 * float(outcome_load)))

        trace_payload = {
            "scene_ir": {
                "scene_kind": "symbolic_probability_dice_panel",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "scene_id": SCENE_ID,
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_value": str(answer_value),
                    "event_description": str(event["event_description"]),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": {
                    "scene_id": SCENE_ID,
                    "query_id": str(query_id),
                    "query_id_probabilities": dict(query_id_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "dice_visual_style": str(dice_visual_style),
                    "dice_visual_style_probabilities": dict(dice_visual_style_probabilities),
                    "mode": str(mode),
                    "event_description": str(event["event_description"]),
                    "given_description": str(event.get("given_description", "")),
                    "favorable_outcome_count": int(event["favorable_outcome_count"]),
                    "total_outcome_count": int(event["total_outcome_count"]),
                },
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "dice_visual_style": _dice_visual_style_metadata(
                    str(dice_visual_style),
                    dice_visual_style_probabilities,
                ),
                "post_image_noise": dict(post_noise_meta),
                "post_image_noise_policy": {
                    "apply_prob": 0.15,
                    "reason": "dice_color_and_pip_readability",
                    "scope": "semantic die colors and visible pip counts",
                },
                "label_style": {
                    "font": _font_trace_record(str(font_family)),
                },
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "layout": str(mode),
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "die_bboxes_px": {str(key): list(value) for key, value in rendered_scene.die_bbox_map.items()},
                "tray_bboxes_px": {str(key): list(value) for key, value in rendered_scene.tray_bbox_map.items()},
                "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bbox_map.items()},
                "annotation_source": "keyed_tray_bboxes_px",
            },
            "execution_trace": {
                "query_id": str(query_id),
                "query_id_probabilities": dict(query_id_probabilities),
                "scene_id": SCENE_ID,
                "scene_variant": str(scene_variant),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
                "dice_visual_style": str(dice_visual_style),
                "dice_visual_style_probabilities": dict(dice_visual_style_probabilities),
                "mode": str(mode),
                "tray_specs": tray_specs,
                "dice_specs": all_dice,
                "dice_attribute_counts": {
                    "color": dict(Counter(str(die["color_name"]) for die in all_dice)),
                    "value": {str(key): int(value) for key, value in Counter(int(die["value"]) for die in all_dice).items()},
                },
                "event": dict(event),
                "event_description": str(event["event_description"]),
                "given_description": str(event.get("given_description", "")),
                "favorable_outcome_count": int(event["favorable_outcome_count"]),
                "total_outcome_count": int(event["total_outcome_count"]),
                "answer_value": str(answer_value),
                "annotation_item_ids": list(annotation_item_ids),
                "annotation_role_item_ids": dict(annotation_role_item_ids),
                "calculation_supporting_item_ids": list(calculation_supporting_item_ids),
                "question_format": str(query_id),
            },
            "witness_symbolic": {
                "type": "keyed_bbox_map",
                "value": dict(annotation_bboxes),
            },
            "projected_annotation": dict(annotation_projection),
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        if mode == "pair":
            trace_payload["execution_trace"]["dice_count_a"] = int(dataset["dice_count_a"])
            trace_payload["execution_trace"]["dice_count_b"] = int(dataset["dice_count_b"])
            trace_payload["execution_trace"]["dice_count_range"] = list(dataset["dice_count_range"])
        else:
            trace_payload["execution_trace"]["dice_count"] = int(dataset["dice_count"])
            trace_payload["execution_trace"]["dice_count_range"] = list(dataset["dice_count_range"])
        if mode == "conditional":
            trace_payload["execution_trace"]["denominator_supporting_item_ids"] = list(dataset["denominator_supporting_item_ids"])

        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_variants),
        )


@register_task
class SymbolicProbabilityDiceSingleAttributeProbabilityTask(_DiceProbabilityBaseTask):
    """Compute a single-tray dice probability from attribute predicates."""

    task_id = SINGLE_ATTRIBUTE_TASK_ID
    supported_query_ids = SINGLE_ATTRIBUTE_QUERY_IDS
    dataset_family = "single"


@register_task
class SymbolicProbabilityDiceSingleThresholdProbabilityTask(_DiceProbabilityBaseTask):
    """Compute a single-tray dice probability from a value threshold."""

    task_id = SINGLE_THRESHOLD_TASK_ID
    supported_query_ids = SINGLE_THRESHOLD_QUERY_IDS
    dataset_family = "single"


@register_task
class SymbolicProbabilityDicePairSumProbabilityTask(_DiceProbabilityBaseTask):
    """Compute a two-tray dice probability for an exact pair sum."""

    task_id = PAIR_SUM_TASK_ID
    supported_query_ids = PAIR_SUM_QUERY_IDS
    dataset_family = "pair"


@register_task
class SymbolicProbabilityDicePairSumThresholdProbabilityTask(_DiceProbabilityBaseTask):
    """Compute a two-tray dice probability for a pair-sum threshold."""

    task_id = PAIR_SUM_THRESHOLD_TASK_ID
    supported_query_ids = PAIR_SUM_THRESHOLD_QUERY_IDS
    dataset_family = "pair"


@register_task
class SymbolicProbabilityDicePairDifferenceProbabilityTask(_DiceProbabilityBaseTask):
    """Compute a two-tray dice probability for an absolute difference."""

    task_id = PAIR_DIFFERENCE_TASK_ID
    supported_query_ids = PAIR_DIFFERENCE_QUERY_IDS
    dataset_family = "pair"


@register_task
class SymbolicProbabilityDicePairAttributeComboProbabilityTask(_DiceProbabilityBaseTask):
    """Compute a two-tray dice probability from paired attribute predicates."""

    task_id = PAIR_ATTRIBUTE_COMBO_TASK_ID
    supported_query_ids = PAIR_ATTRIBUTE_COMBO_QUERY_IDS
    dataset_family = "pair"


@register_task
class SymbolicProbabilityDiceConditionalEventValueTask(_DiceProbabilityBaseTask):
    """Compute a visible-top conditional probability from one dice tray."""

    task_id = CONDITIONAL_TASK_ID
    supported_query_ids = CONDITIONAL_QUERY_IDS
    dataset_family = "conditional"


__all__ = [
    "CONDITIONAL_QUERY_IDS",
    "PAIR_ATTRIBUTE_COMBO_QUERY_IDS",
    "PAIR_ATTRIBUTE_COMBO_TASK_ID",
    "PAIR_DIFFERENCE_QUERY_IDS",
    "PAIR_DIFFERENCE_TASK_ID",
    "PAIR_QUERY_IDS",
    "PAIR_SUM_QUERY_IDS",
    "PAIR_SUM_TASK_ID",
    "PAIR_SUM_THRESHOLD_QUERY_IDS",
    "PAIR_SUM_THRESHOLD_TASK_ID",
    "SINGLE_ATTRIBUTE_QUERY_IDS",
    "SINGLE_ATTRIBUTE_TASK_ID",
    "SINGLE_QUERY_IDS",
    "SINGLE_THRESHOLD_QUERY_IDS",
    "SINGLE_THRESHOLD_TASK_ID",
    "SymbolicProbabilityDiceConditionalEventValueTask",
    "SymbolicProbabilityDicePairAttributeComboProbabilityTask",
    "SymbolicProbabilityDicePairDifferenceProbabilityTask",
    "SymbolicProbabilityDicePairSumProbabilityTask",
    "SymbolicProbabilityDicePairSumThresholdProbabilityTask",
    "SymbolicProbabilityDiceSingleAttributeProbabilityTask",
    "SymbolicProbabilityDiceSingleThresholdProbabilityTask",
]
