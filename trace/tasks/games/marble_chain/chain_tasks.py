"""Games marble-chain shot-direction tasks."""

from __future__ import annotations

import json
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
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.font_assets import get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.text_legibility import draw_text_traced
from ..shared.complexity import build_games_complexity, normalize_linear, resolve_games_complexity_weights
from ..shared.layout import (
    apply_games_layout_jitter_to_bbox,
    attach_games_unit_size_jitter,
    resolve_games_layout_jitter,
    resolve_games_unit_size_scale,
    scale_games_px,
)
from ..shared.sampling import resolve_games_named_axis
from ..shared.scene_style import draw_panel_scene_chrome, make_panel_scene_background, resolve_game_panel_scene_style
from ..shared.visual_defaults import load_games_noise_defaults


TASK_GROUP = "marble_chain"
SCENE_ID = "marble_chain"
QUERY_MAX_POP_DIRECTION = "max_pop_direction_label"
QUERY_TARGET_POP_DIRECTION = "target_pop_direction_label"
QUERY_POP_COUNT = "pop_count_after_marked_shot"
SUPPORTED_DIRECTION_LABEL_QUERIES: Tuple[str, ...] = (QUERY_MAX_POP_DIRECTION, QUERY_TARGET_POP_DIRECTION)
SUPPORTED_EFFECT_VALUE_QUERIES: Tuple[str, ...] = (QUERY_POP_COUNT,)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("semicircle_track", "spiral_track", "double_arc_track")
SUPPORTED_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic_track",
    "arcade_track",
    "neon_track",
    "chalk_track",
    "copper_track",
)
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G")
COLOR_KEYS: Tuple[str, ...] = ("red", "blue", "green", "yellow", "purple", "orange")
COLOR_RGB: Dict[str, Tuple[int, int, int]] = {
    "red": (216, 57, 64),
    "blue": (58, 118, 218),
    "green": (54, 158, 99),
    "yellow": (238, 190, 52),
    "purple": (144, 92, 205),
    "orange": (230, 126, 51),
}

MARBLE_CHAIN_STYLE_RGB: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    "classic_track": {
        "track": (177, 181, 184),
        "rail": (83, 91, 101),
        "arrow": (36, 99, 164),
        "shooter_body": (242, 244, 248),
    },
    "arcade_track": {
        "track": (75, 91, 125),
        "rail": (21, 31, 54),
        "arrow": (242, 198, 56),
        "shooter_body": (31, 43, 70),
    },
    "neon_track": {
        "track": (64, 53, 102),
        "rail": (21, 19, 42),
        "arrow": (71, 215, 205),
        "shooter_body": (42, 37, 73),
    },
    "chalk_track": {
        "track": (191, 196, 182),
        "rail": (78, 90, 76),
        "arrow": (188, 83, 69),
        "shooter_body": (235, 232, 214),
    },
    "copper_track": {
        "track": (174, 122, 82),
        "rail": (93, 57, 38),
        "arrow": (37, 112, 124),
        "shooter_body": (236, 210, 171),
    },
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for marble-chain tasks."""

    chain_length_support: Tuple[int, ...] = (18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28)
    color_count_support: Tuple[int, ...] = (4, 5, 6)
    option_count_support: Tuple[int, ...] = (5, 6, 7)
    target_pop_count_support: Tuple[int, ...] = (0, 2, 3, 4, 5)
    canvas_width: int = 900
    canvas_height: int = 760
    panel_margin_px: int = 36
    track_panel_top_px: int = 36
    track_panel_height_px: int = 688
    option_panel_top_px: int = 0
    marble_radius_px: int = 28
    slot_radius_px: int = 13
    track_width_px: int = 26
    label_font_size_px: int = 19
    title_font_size_px: int = 24


@dataclass(frozen=True)
class _Outcome:
    """Single-step insertion outcome for one slot."""

    slot_index: int
    pop_count: int
    popped_indices: Tuple[int, ...]
    affected_indices: Tuple[int, ...]
    remaining_count: int


@dataclass(frozen=True)
class _SlotOption:
    """One labeled shot-direction option."""

    label: str
    slot_index: int
    outcome: _Outcome
    is_answer: bool

    @property
    def entity_id(self) -> str:
        return f"shot_option_{str(self.label).lower()}"


@dataclass(frozen=True)
class _Sample:
    """Constructed marble-chain scene and query witness."""

    query_id: str
    scene_variant: str
    chain_colors: Tuple[str, ...]
    shooter_color: str
    answer: int | str
    answer_type: str
    option_specs: Tuple[_SlotOption, ...]
    marked_slot_index: int | None
    marked_outcome: _Outcome | None
    target_pop_count: int | None
    evidence_entity_ids: Tuple[str, ...]
    metadata: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered marble-chain scene and trace maps."""

    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]
    style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", TASK_GROUP)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="games_marble_chain_base",
)
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group=TASK_GROUP, apply_prob=0.5)


def _int_default(params: Mapping[str, Any], key: str, fallback: int) -> int:
    if str(key) in params:
        return int(params[str(key)])
    return int(group_default(_RENDER_DEFAULTS, str(key), int(fallback)))


def _draw_text_center(
    draw: ImageDraw.ImageDraw,
    bbox: Tuple[float, float, float, float],
    text: str,
    *,
    font,
    fill: Tuple[int, int, int],
    stroke_width: int = 1,
) -> None:
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=int(stroke_width))
    width = float(text_bbox[2] - text_bbox[0])
    height = float(text_bbox[3] - text_bbox[1])
    x0, y0, x1, y1 = bbox
    origin = (float(x0 + ((x1 - x0) - width) / 2.0), float(y0 + ((y1 - y0) - height) / 2.0))
    draw_text_traced(draw,
        origin,
        str(text),
        font=font,
        fill=tuple(int(value) for value in fill),
        stroke_width=int(stroke_width),
        stroke_fill=tuple(int(value) for value in resolve_text_stroke_fill(fill)),
     role="readout", required=False,)


def _sample_integer_axis(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[int],
    namespace: str,
    balanced_flag_key: str,
) -> Tuple[int, Dict[str, float]]:
    value, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key=str(explicit_key),
        fallback_support=tuple(int(item) for item in fallback_support),
        namespace=f"{str(task_id)}.{str(namespace)}",
        balanced_flag_key=str(balanced_flag_key),
        namespace_support_permutation=True,
    )
    return int(value), dict(probabilities)


def _sample_scene_variant(*, task_id: str, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported_variants=SUPPORTED_SCENE_VARIANTS,
    )


def _sample_style_variant(*, task_id: str, instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported_variants=SUPPORTED_STYLE_VARIANTS,
    )


def _sample_query_id(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    supported: Sequence[str],
    weights_key: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="query_id",
        explicit_key="query_id",
        weights_key=str(weights_key),
        balance_flag_key="balanced_query_id_sampling",
        supported_variants=tuple(str(value) for value in supported),
    )


def _sample_color_keys(rng, *, color_count: int) -> Tuple[str, ...]:
    colors = list(COLOR_KEYS)
    rng.shuffle(colors)
    return tuple(colors[: int(color_count)])


def _sample_chain(rng, *, length: int, color_keys: Sequence[str], shooter_color: str) -> Tuple[str, ...]:
    chain: List[str] = []
    while len(chain) < int(length):
        allowed = [str(color) for color in color_keys if not chain or str(color) != str(chain[-1])]
        color = str(allowed[int(rng.randrange(len(allowed)))])
        if color == str(shooter_color):
            run_len = int(rng.choice((1, 1, 2, 2, 3, 4, 5)))
        else:
            run_len = int(rng.choice((1, 1, 2, 2, 3)))
        remaining = int(length) - len(chain)
        run_len = min(int(run_len), int(remaining))
        chain.extend([str(color)] * int(run_len))
    return tuple(chain[: int(length)])


def _compute_outcome(chain_colors: Sequence[str], *, shooter_color: str, slot_index: int) -> _Outcome:
    chain = tuple(str(color) for color in chain_colors)
    slot = max(0, min(int(slot_index), len(chain)))
    inserted_color = str(shooter_color)
    new_chain = list(chain[:slot]) + [inserted_color] + list(chain[slot:])
    inserted_index = int(slot)
    left = inserted_index
    while left - 1 >= 0 and str(new_chain[left - 1]) == inserted_color:
        left -= 1
    right = inserted_index
    while right + 1 < len(new_chain) and str(new_chain[right + 1]) == inserted_color:
        right += 1
    run_len = int(right - left + 1)
    affected_indices: List[int] = []
    popped_indices: List[int] = []
    if run_len >= 3:
        for new_index in range(left, right + 1):
            if new_index == inserted_index:
                continue
            original_index = int(new_index if new_index < inserted_index else new_index - 1)
            popped_indices.append(original_index)
            affected_indices.append(original_index)
        remaining_count = int(len(chain) - len(popped_indices))
    else:
        for original_index in (slot - 1, slot):
            if 0 <= int(original_index) < len(chain):
                affected_indices.append(int(original_index))
        remaining_count = int(len(chain) + 1)
    return _Outcome(
        slot_index=int(slot),
        pop_count=int(len(popped_indices)),
        popped_indices=tuple(sorted(set(int(index) for index in popped_indices))),
        affected_indices=tuple(sorted(set(int(index) for index in affected_indices))),
        remaining_count=int(remaining_count),
    )


def _all_outcomes(chain_colors: Sequence[str], *, shooter_color: str) -> Dict[int, _Outcome]:
    return {
        int(slot): _compute_outcome(chain_colors, shooter_color=str(shooter_color), slot_index=int(slot))
        for slot in range(len(chain_colors) + 1)
    }


def _marble_entity_id(index: int) -> str:
    return f"marble_{int(index):02d}"


def _neighbor_entity_ids(chain_colors: Sequence[str], slot_index: int) -> Tuple[str, ...]:
    ids: List[str] = []
    for index in (int(slot_index) - 1, int(slot_index)):
        if 0 <= int(index) < len(chain_colors):
            ids.append(_marble_entity_id(int(index)))
    return tuple(ids)


def _evidence_ids_for_outcome(
    *,
    slot_entity_id: str,
    chain_colors: Sequence[str],
    outcome: _Outcome,
) -> Tuple[str, ...]:
    del chain_colors
    del outcome
    return (str(slot_entity_id),)


def _popped_marble_evidence_ids(outcome: _Outcome) -> Tuple[str, ...]:
    """Return public evidence ids for the existing marbles removed by one shot."""

    return tuple(_marble_entity_id(int(index)) for index in outcome.popped_indices)


def _answer_label(instance_seed: int, *, params: Mapping[str, Any], option_count: int) -> str:
    labels = OPTION_LABELS[: int(option_count)]
    raw = params.get("answer_option_label")
    if raw is not None:
        value = str(raw).strip().upper()
        if value not in labels:
            raise ValueError(f"answer_option_label={value!r} is not available for {option_count} options")
        return str(value)
    cursor = params.get("_sample_cursor")
    if cursor is not None:
        return str(labels[abs(int(cursor)) % len(labels)])
    rng = spawn_rng(int(instance_seed), "games.marble_chain.answer_label")
    return str(labels[int(rng.randrange(len(labels)))])


def _pick_slots_with_spacing(
    rng,
    candidates: Sequence[int],
    *,
    count: int,
    blocked: Sequence[int] = (),
    min_gap: int = 2,
) -> List[int]:
    blocked_set = {int(value) for value in blocked}
    pool = [int(value) for value in candidates if int(value) not in blocked_set]
    rng.shuffle(pool)
    selected: List[int] = []
    for slot in pool:
        if all(abs(int(slot) - int(existing)) >= int(min_gap) for existing in selected) and all(
            abs(int(slot) - int(existing)) >= int(min_gap) for existing in blocked_set
        ):
            selected.append(int(slot))
            if len(selected) == int(count):
                return selected
    for slot in pool:
        if int(slot) not in selected:
            selected.append(int(slot))
            if len(selected) == int(count):
                return selected
    return selected


def _sample_direction_label(
    rng,
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
    query_id: str,
) -> _Sample:
    chain_length, chain_length_probs = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="chain_length_support",
        explicit_key="chain_length",
        fallback_support=_DEFAULTS.chain_length_support,
        namespace="chain_length",
        balanced_flag_key="balanced_chain_length_sampling",
    )
    color_count, color_count_probs = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="color_count_support",
        explicit_key="color_count",
        fallback_support=_DEFAULTS.color_count_support,
        namespace="color_count",
        balanced_flag_key="balanced_color_count_sampling",
    )
    option_count, option_count_probs = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="option_count_support",
        explicit_key="option_count",
        fallback_support=_DEFAULTS.option_count_support,
        namespace="option_count",
        balanced_flag_key="balanced_option_count_sampling",
    )
    target_pop_count = None
    target_pop_probs: Dict[str, float] = {}
    if str(query_id) == QUERY_TARGET_POP_DIRECTION:
        target_pop_count, target_pop_probs = _sample_integer_axis(
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            support_key="target_pop_count_support",
            explicit_key="target_pop_count",
            fallback_support=_DEFAULTS.target_pop_count_support,
            namespace="target_pop_count",
            balanced_flag_key="balanced_target_answer_sampling",
        )
    answer_label = _answer_label(int(instance_seed), params=params, option_count=int(option_count))
    labels = OPTION_LABELS[: int(option_count)]
    for _attempt in range(800):
        color_keys = _sample_color_keys(rng, color_count=int(color_count))
        shooter_color = str(color_keys[int(rng.randrange(len(color_keys)))])
        chain_colors = _sample_chain(rng, length=int(chain_length), color_keys=color_keys, shooter_color=str(shooter_color))
        outcomes = _all_outcomes(chain_colors, shooter_color=str(shooter_color))
        if str(query_id) == QUERY_MAX_POP_DIRECTION:
            max_pop = max(int(outcome.pop_count) for outcome in outcomes.values())
            if int(max_pop) <= 0:
                continue
            answer_candidates = [slot for slot, outcome in outcomes.items() if int(outcome.pop_count) == int(max_pop)]
            distractor_candidates = [slot for slot, outcome in outcomes.items() if int(outcome.pop_count) < int(max_pop)]
        else:
            answer_candidates = [slot for slot, outcome in outcomes.items() if int(outcome.pop_count) == int(target_pop_count or 0)]
            if int(target_pop_count or 0) == 0:
                distractor_candidates = [slot for slot, outcome in outcomes.items() if int(outcome.pop_count) > 0]
            else:
                distractor_candidates = [slot for slot, outcome in outcomes.items() if int(outcome.pop_count) != int(target_pop_count or 0)]
        if not answer_candidates or len(distractor_candidates) < int(option_count) - 1:
            continue
        answer_slot = int(answer_candidates[int(rng.randrange(len(answer_candidates)))])
        distractor_slots = _pick_slots_with_spacing(
            rng,
            distractor_candidates,
            count=int(option_count) - 1,
            blocked=(answer_slot,),
            min_gap=3,
        )
        if len(distractor_slots) < int(option_count) - 1:
            continue
        specs: List[_SlotOption] = []
        distractor_cursor = 0
        for label in labels:
            if str(label) == str(answer_label):
                slot = int(answer_slot)
            else:
                slot = int(distractor_slots[distractor_cursor])
                distractor_cursor += 1
            specs.append(
                _SlotOption(
                    label=str(label),
                    slot_index=int(slot),
                    outcome=outcomes[int(slot)],
                    is_answer=str(label) == str(answer_label),
                )
            )
        # Re-check uniqueness within displayed options.
        if str(query_id) == QUERY_MAX_POP_DIRECTION:
            displayed_max = max(int(spec.outcome.pop_count) for spec in specs)
            if sum(1 for spec in specs if int(spec.outcome.pop_count) == int(displayed_max)) != 1:
                continue
        else:
            if sum(1 for spec in specs if int(spec.outcome.pop_count) == int(target_pop_count or 0)) != 1:
                continue
        answer_spec = next(spec for spec in specs if bool(spec.is_answer))
        evidence_ids = _evidence_ids_for_outcome(
            slot_entity_id=str(answer_spec.entity_id),
            chain_colors=chain_colors,
            outcome=answer_spec.outcome,
        )
        return _Sample(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            chain_colors=tuple(chain_colors),
            shooter_color=str(shooter_color),
            answer=str(answer_label),
            answer_type="string",
            option_specs=tuple(specs),
            marked_slot_index=None,
            marked_outcome=None,
            target_pop_count=None if target_pop_count is None else int(target_pop_count),
            evidence_entity_ids=tuple(evidence_ids),
            metadata={
                "chain_length": int(chain_length),
                "chain_length_probabilities": dict(chain_length_probs),
                "color_count": int(color_count),
                "color_count_probabilities": dict(color_count_probs),
                "option_count": int(option_count),
                "option_count_probabilities": dict(option_count_probs),
                "target_pop_count": None if target_pop_count is None else int(target_pop_count),
                "target_pop_count_probabilities": dict(target_pop_probs),
                "answer_option_label": str(answer_label),
            },
        )
    raise ValueError("failed to sample marble-chain shot-direction scene")


def _sample_effect_value(
    rng,
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
    query_id: str,
) -> _Sample:
    color_count, color_count_probs = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="color_count_support",
        explicit_key="color_count",
        fallback_support=_DEFAULTS.color_count_support,
        namespace="color_count",
        balanced_flag_key="balanced_color_count_sampling",
    )
    target_pop_count = None
    target_probs: Dict[str, float] = {}
    if str(query_id) != QUERY_POP_COUNT:
        raise ValueError(f"unsupported marble-chain effect query: {query_id}")
    target_pop_count, target_probs = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="target_pop_count_support",
        explicit_key="target_answer",
        fallback_support=_DEFAULTS.target_pop_count_support,
        namespace="target_pop_count",
        balanced_flag_key="balanced_target_answer_sampling",
    )
    chain_length, chain_length_probs = _sample_integer_axis(
        task_id=str(task_id),
        instance_seed=int(instance_seed),
        params=params,
        support_key="chain_length_support",
        explicit_key="chain_length",
        fallback_support=_DEFAULTS.chain_length_support,
        namespace="chain_length",
        balanced_flag_key="balanced_chain_length_sampling",
    )
    desired_pop_count = int(target_pop_count)

    for _attempt in range(800):
        color_keys = _sample_color_keys(rng, color_count=int(color_count))
        shooter_color = str(color_keys[int(rng.randrange(len(color_keys)))])
        chain_colors = _sample_chain(rng, length=int(chain_length), color_keys=color_keys, shooter_color=str(shooter_color))
        outcomes = _all_outcomes(chain_colors, shooter_color=str(shooter_color))
        candidate_slots = [slot for slot, outcome in outcomes.items() if int(outcome.pop_count) == int(desired_pop_count or 0)]
        if not candidate_slots:
            continue
        marked_slot = int(candidate_slots[int(rng.randrange(len(candidate_slots)))])
        outcome = outcomes[int(marked_slot)]
        answer = int(outcome.pop_count)
        evidence_ids = _popped_marble_evidence_ids(outcome)
        return _Sample(
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            chain_colors=tuple(chain_colors),
            shooter_color=str(shooter_color),
            answer=int(answer),
            answer_type="integer",
            option_specs=(),
            marked_slot_index=int(marked_slot),
            marked_outcome=outcome,
            target_pop_count=None if target_pop_count is None else int(target_pop_count),
            evidence_entity_ids=tuple(evidence_ids),
            metadata={
                "chain_length": int(chain_length),
                "chain_length_probabilities": dict(chain_length_probs),
                "color_count": int(color_count),
                "color_count_probabilities": dict(color_count_probs),
                "target_answer": int(answer),
                "target_answer_probabilities": dict(target_probs),
                "target_pop_count": None if target_pop_count is None else int(target_pop_count),
                "desired_pop_count": int(desired_pop_count or 0),
            },
        )
    raise ValueError("failed to sample marble-chain effect-value scene")


def _track_point(t: float, *, variant: str, bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0 + 18.0
    base_radius = min(x1 - x0, y1 - y0) * 0.40
    if str(variant) == "spiral_track":
        theta = math.radians(145.0 + 610.0 * float(t))
        radius = base_radius * (0.36 + 0.64 * float(t))
    elif str(variant) == "double_arc_track":
        theta = math.radians(140.0 + 430.0 * float(t))
        radius = base_radius * (0.78 + 0.24 * math.sin(2.0 * math.pi * float(t)))
    else:
        theta = math.radians(155.0 + 250.0 * float(t))
        radius = base_radius
    x = cx + radius * math.cos(theta)
    y = cy + radius * math.sin(theta)
    return float(x), float(y)


def _chain_centers(count: int, *, variant: str, bbox: Tuple[float, float, float, float]) -> Tuple[Tuple[float, float], ...]:
    if int(count) <= 1:
        return (_track_point(0.5, variant=str(variant), bbox=bbox),)
    return tuple(
        _track_point(float(index) / float(int(count) - 1), variant=str(variant), bbox=bbox)
        for index in range(int(count))
    )


def _slot_center(slot_index: int, centers: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    slot = int(slot_index)
    if not centers:
        return 0.0, 0.0
    if slot <= 0:
        x0, y0 = centers[0]
        x1, y1 = centers[1] if len(centers) > 1 else (x0 + 42.0, y0)
        return float(x0 - 0.5 * (x1 - x0)), float(y0 - 0.5 * (y1 - y0))
    if slot >= len(centers):
        x0, y0 = centers[-2] if len(centers) > 1 else (centers[-1][0] - 42.0, centers[-1][1])
        x1, y1 = centers[-1]
        return float(x1 + 0.5 * (x1 - x0)), float(y1 + 0.5 * (y1 - y0))
    x0, y0 = centers[slot - 1]
    x1, y1 = centers[slot]
    return float((x0 + x1) / 2.0), float((y0 + y1) / 2.0)


def _circle_bbox(center: Tuple[float, float], radius: float) -> List[float]:
    x, y = center
    r = float(radius)
    return [round(float(x - r), 3), round(float(y - r), 3), round(float(x + r), 3), round(float(y + r), 3)]


def _draw_marble(
    draw: ImageDraw.ImageDraw,
    bbox: Sequence[float],
    *,
    fill_rgb: Tuple[int, int, int],
    outline_rgb: Tuple[int, int, int],
    highlight_rgb: Tuple[int, int, int],
    width: int,
) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    draw.ellipse((x0, y0, x1, y1), fill=tuple(fill_rgb), outline=tuple(outline_rgb), width=int(width))
    inset = max(4.0, (x1 - x0) * 0.18)
    draw.ellipse(
        (x0 + inset, y0 + inset, x0 + inset * 1.75, y0 + inset * 1.75),
        fill=tuple(highlight_rgb),
    )


def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: Tuple[float, float],
    end: Tuple[float, float],
    *,
    fill: Tuple[int, int, int],
    width: int,
    dash_px: float = 12.0,
    gap_px: float = 9.0,
) -> None:
    x0, y0 = start
    x1, y1 = end
    length = math.hypot(float(x1 - x0), float(y1 - y0))
    if length <= 0:
        return
    ux = float(x1 - x0) / length
    uy = float(y1 - y0) / length
    cursor = 0.0
    while cursor < length:
        seg_end = min(length, cursor + float(dash_px))
        draw.line(
            (
                x0 + ux * cursor,
                y0 + uy * cursor,
                x0 + ux * seg_end,
                y0 + uy * seg_end,
            ),
            fill=tuple(fill),
            width=int(width),
        )
        cursor += float(dash_px) + float(gap_px)


def _arrow_bbox(start: Tuple[float, float], end: Tuple[float, float], *, pad: float) -> List[float]:
    x0, y0 = start
    x1, y1 = end
    return [
        round(min(float(x0), float(x1)) - float(pad), 3),
        round(min(float(y0), float(y1)) - float(pad), 3),
        round(max(float(x0), float(x1)) + float(pad), 3),
        round(max(float(y0), float(y1)) + float(pad), 3),
    ]


def _draw_shot_arrow(
    draw: ImageDraw.ImageDraw,
    start: Tuple[float, float],
    end: Tuple[float, float],
    *,
    line_rgb: Tuple[int, int, int],
    label: str | None,
    label_font,
    text_rgb: Tuple[int, int, int],
    label_fill_rgb: Tuple[int, int, int],
    label_outline_rgb: Tuple[int, int, int],
    width: int,
    emphasize: bool,
) -> List[float]:
    x0, y0 = start
    x1, y1 = end
    length = max(1.0, math.hypot(float(x1 - x0), float(y1 - y0)))
    ux = float(x1 - x0) / length
    uy = float(y1 - y0) / length
    shaft_start = (float(x0 + ux * 34.0), float(y0 + uy * 34.0))
    shaft_end = (float(x1 - ux * 18.0), float(y1 - uy * 18.0))
    line_width = int(width + (2 if bool(emphasize) else 0))
    draw.line((shaft_start[0], shaft_start[1], shaft_end[0], shaft_end[1]), fill=tuple(line_rgb), width=line_width)
    head_len = 20.0 + (4.0 if bool(emphasize) else 0.0)
    head_w = 12.0 + (3.0 if bool(emphasize) else 0.0)
    tip = (float(x1 - ux * 8.0), float(y1 - uy * 8.0))
    base = (float(tip[0] - ux * head_len), float(tip[1] - uy * head_len))
    px = -uy
    py = ux
    draw.polygon(
        (
            tip,
            (base[0] + px * head_w, base[1] + py * head_w),
            (base[0] - px * head_w, base[1] - py * head_w),
        ),
        fill=tuple(line_rgb),
    )
    bbox = _arrow_bbox(shaft_start, tip, pad=max(18.0, float(line_width) * 2.0))
    if label:
        label_cx = float(x1 + px * 23.0 - ux * 6.0)
        label_cy = float(y1 + py * 23.0 - uy * 6.0)
        label_radius = 17.0
        label_bbox = (
            label_cx - label_radius,
            label_cy - label_radius,
            label_cx + label_radius,
            label_cy + label_radius,
        )
        draw.ellipse(label_bbox, fill=tuple(label_fill_rgb), outline=tuple(label_outline_rgb), width=2)
        _draw_text_center(draw, label_bbox, str(label), font=label_font, fill=text_rgb, stroke_width=0)
        bbox = [
            min(float(bbox[0]), float(label_bbox[0])),
            min(float(bbox[1]), float(label_bbox[1])),
            max(float(bbox[2]), float(label_bbox[2])),
            max(float(bbox[3]), float(label_bbox[3])),
        ]
    return [round(float(value), 3) for value in bbox]


def _render_scene(
    *,
    sample: _Sample,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any],
    style_variant: str,
) -> _RenderedScene:
    canvas_width = _int_default(params, "canvas_width", _DEFAULTS.canvas_width)
    canvas_height = _int_default(params, "canvas_height", _DEFAULTS.canvas_height)
    margin = _int_default(params, "panel_margin_px", _DEFAULTS.panel_margin_px)
    style, style_meta = resolve_game_panel_scene_style(
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.marble_chain_panel_style",
        treatment_weights=group_default(_GEN_DEFAULTS, "panel_treatment_weights", {}),
        palette_weights=group_default(_GEN_DEFAULTS, "panel_palette_weights", {}),
    )
    image, background_meta = make_panel_scene_background(
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        style=style,
    )
    image = image.convert("RGBA")
    draw = ImageDraw.Draw(image)
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.marble_chain.label_font",
        params=params,
    )
    marble_style = MARBLE_CHAIN_STYLE_RGB.get(
        str(style_variant),
        MARBLE_CHAIN_STYLE_RGB["classic_track"],
    )
    layout_jitter = resolve_games_layout_jitter(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.marble_chain.layout",
    )
    unit_scale, unit_meta = resolve_games_unit_size_scale(
        params,
        _RENDER_DEFAULTS,
        instance_seed=int(instance_seed),
        namespace=f"{str(task_id)}.marble_chain.unit_size",
    )
    base_track_bbox = (
        float(margin),
        float(_int_default(params, "track_panel_top_px", _DEFAULTS.track_panel_top_px)),
        float(canvas_width - margin),
        float(_int_default(params, "track_panel_top_px", _DEFAULTS.track_panel_top_px) + _int_default(params, "track_panel_height_px", _DEFAULTS.track_panel_height_px)),
    )
    track_bbox, dx, dy, resolved_jitter = apply_games_layout_jitter_to_bbox(
        bbox_px=base_track_bbox,
        canvas_width=int(canvas_width),
        canvas_height=int(canvas_height),
        jitter=layout_jitter,
    )
    track_bbox_i = tuple(int(round(value)) for value in track_bbox)
    draw_panel_scene_chrome(draw, bbox=track_bbox_i, style=style, radius=22, border_width=3)

    label_font = load_font(
        _int_default(params, "label_font_size_px", _DEFAULTS.label_font_size_px),
        bold=True,
        font_family=str(font_family),
    )
    text_rgb = tuple(int(value) for value in style.text_rgb)
    border_rgb = tuple(int(value) for value in marble_style["rail"])
    accent_rgb = tuple(int(value) for value in marble_style["arrow"])
    track_rgb = tuple(int(value) for value in marble_style["track"])
    shooter_body_rgb = tuple(int(value) for value in marble_style["shooter_body"])
    guide_rgb = tuple(int(max(80, min(210, value))) for value in style.grid_rgb)

    radius_base = _int_default(params, "marble_radius_px", _DEFAULTS.marble_radius_px)
    radius = float(scale_games_px(radius_base, float(unit_scale), min_px=14))
    centers = _chain_centers(len(sample.chain_colors), variant=str(sample.scene_variant), bbox=track_bbox)
    if len(centers) >= 2:
        min_spacing = min(
            math.hypot(float(centers[index + 1][0] - centers[index][0]), float(centers[index + 1][1] - centers[index][1]))
            for index in range(len(centers) - 1)
        )
        radius = min(float(radius), max(14.0, (float(min_spacing) - 5.0) / 2.0))
    track_width = scale_games_px(_int_default(params, "track_width_px", _DEFAULTS.track_width_px), float(unit_scale), min_px=4)

    track_points = [
        _track_point(float(i) / 180.0, variant=str(sample.scene_variant), bbox=track_bbox)
        for i in range(181)
    ]
    draw.line(track_points, fill=tuple(border_rgb), width=int(track_width + 5), joint="curve")
    draw.line(track_points, fill=track_rgb, width=int(track_width), joint="curve")

    entities: List[Dict[str, Any]] = []
    entity_bboxes: Dict[str, List[float]] = {}
    entity_points: Dict[str, List[float]] = {}
    chain_specs: List[Dict[str, Any]] = []
    shot_specs: List[Dict[str, Any]] = []

    shooter_center = (float((track_bbox[0] + track_bbox[2]) / 2.0), float((track_bbox[1] + track_bbox[3]) / 2.0 + 18.0))
    guide_radius = min(float(track_bbox[2] - track_bbox[0]), float(track_bbox[3] - track_bbox[1])) * 0.46
    for angle_deg in range(0, 360, 45):
        theta = math.radians(float(angle_deg))
        end = (shooter_center[0] + guide_radius * math.cos(theta), shooter_center[1] + guide_radius * math.sin(theta))
        _draw_dashed_line(draw, shooter_center, end, fill=guide_rgb, width=1, dash_px=9.0, gap_px=10.0)

    hole_center = track_points[-1]
    hole_radius = max(20.0, float(radius) * 1.05)
    hole_bbox = _circle_bbox(hole_center, hole_radius)
    draw.ellipse(tuple(hole_bbox), fill=(8, 8, 8), outline=tuple(border_rgb), width=2)
    entity_bboxes["track_black_hole"] = [float(value) for value in hole_bbox]
    entities.append(
        {
            "entity_id": "track_black_hole",
            "entity_type": "track_black_hole",
            "bbox_px": [float(value) for value in hole_bbox],
        }
    )

    for index, (color_key, center) in enumerate(zip(sample.chain_colors, centers)):
        entity_id = _marble_entity_id(int(index))
        bbox = _circle_bbox(center, radius)
        fill = tuple(int(value) for value in COLOR_RGB[str(color_key)])
        _draw_marble(
            draw,
            bbox,
            fill_rgb=fill,
            outline_rgb=border_rgb,
            highlight_rgb=(255, 255, 255),
            width=2,
        )
        entity_bboxes[str(entity_id)] = [float(value) for value in bbox]
        entity_points[str(entity_id)] = [round(float(center[0]), 3), round(float(center[1]), 3)]
        spec = {
            "entity_id": str(entity_id),
            "entity_type": "chain_marble",
            "index": int(index),
            "color_key": str(color_key),
            "bbox_px": [float(value) for value in bbox],
            "center_px": [round(float(center[0]), 3), round(float(center[1]), 3)],
        }
        chain_specs.append(dict(spec))
        entities.append(dict(spec))

    shooter_body_radius = max(44.0, float(radius) * 2.0)
    shooter_body = (
        (shooter_center[0], shooter_center[1] - shooter_body_radius * 0.96),
        (shooter_center[0] - shooter_body_radius * 0.88, shooter_center[1] + shooter_body_radius * 0.66),
        (shooter_center[0] + shooter_body_radius * 0.88, shooter_center[1] + shooter_body_radius * 0.66),
    )
    draw.polygon(shooter_body, fill=tuple(shooter_body_rgb), outline=tuple(border_rgb))
    shooter_bbox = _circle_bbox(shooter_center, max(13.0, float(radius) * 0.72))
    _draw_marble(
        draw,
        shooter_bbox,
        fill_rgb=tuple(int(value) for value in COLOR_RGB[str(sample.shooter_color)]),
        outline_rgb=border_rgb,
        highlight_rgb=(255, 255, 255),
        width=3,
    )
    entity_bboxes["shooter_marble"] = [float(value) for value in shooter_bbox]
    entity_points["shooter_marble"] = [round(float(shooter_center[0]), 3), round(float(shooter_center[1]), 3)]
    entities.append(
        {
            "entity_id": "shooter_marble",
            "entity_type": "shooter_marble",
            "color_key": str(sample.shooter_color),
            "bbox_px": [float(value) for value in shooter_bbox],
            "center_px": [round(float(shooter_center[0]), 3), round(float(shooter_center[1]), 3)],
        }
    )

    for option in sample.option_specs:
        arrow_end = _slot_center(int(option.slot_index), centers)
        bbox = _draw_shot_arrow(
            draw,
            shooter_center,
            arrow_end,
            line_rgb=accent_rgb,
            label=str(option.label),
            label_font=label_font,
            text_rgb=text_rgb,
            label_fill_rgb=tuple(style.option_fill_rgb),
            label_outline_rgb=accent_rgb,
            width=4,
            emphasize=False,
        )
        entity_bboxes[str(option.entity_id)] = [float(value) for value in bbox]
        entity_points[str(option.entity_id)] = [round(float(arrow_end[0]), 3), round(float(arrow_end[1]), 3)]
        spec = {
            "entity_id": str(option.entity_id),
            "entity_type": "shot_direction_arrow",
            "label": str(option.label),
            "slot_index": int(option.slot_index),
            "pop_count": int(option.outcome.pop_count),
            "remaining_count": int(option.outcome.remaining_count),
            "popped_indices": [int(index) for index in option.outcome.popped_indices],
            "is_answer": bool(option.is_answer),
            "bbox_px": [float(value) for value in bbox],
            "insertion_point_px": [round(float(arrow_end[0]), 3), round(float(arrow_end[1]), 3)],
        }
        shot_specs.append(dict(spec))
        entities.append(dict(spec))

    marked_shot_spec = None
    if sample.marked_slot_index is not None:
        arrow_end = _slot_center(int(sample.marked_slot_index), centers)
        bbox = _draw_shot_arrow(
            draw,
            shooter_center,
            arrow_end,
            line_rgb=accent_rgb,
            label=None,
            label_font=label_font,
            text_rgb=text_rgb,
            label_fill_rgb=tuple(style.option_fill_rgb),
            label_outline_rgb=accent_rgb,
            width=7,
            emphasize=True,
        )
        entity_bboxes["marked_shot_arrow"] = [float(value) for value in bbox]
        entity_points["marked_shot_arrow"] = [round(float(arrow_end[0]), 3), round(float(arrow_end[1]), 3)]
        marked_shot_spec = {
            "entity_id": "marked_shot_arrow",
            "entity_type": "marked_shot_arrow",
            "slot_index": int(sample.marked_slot_index),
            "pop_count": int(sample.marked_outcome.pop_count if sample.marked_outcome else 0),
            "remaining_count": int(sample.marked_outcome.remaining_count if sample.marked_outcome else len(sample.chain_colors)),
            "popped_indices": [int(index) for index in (sample.marked_outcome.popped_indices if sample.marked_outcome else ())],
            "bbox_px": [float(value) for value in bbox],
            "insertion_point_px": [round(float(arrow_end[0]), 3), round(float(arrow_end[1]), 3)],
        }
        entities.append(dict(marked_shot_spec))

    render_map = {
        "entity_bboxes_px": dict(entity_bboxes),
        "entity_points_px": dict(entity_points),
        "chain_marble_bboxes_px": {
            str(spec["entity_id"]): [float(value) for value in spec["bbox_px"]]
            for spec in chain_specs
        },
        "chain_marble_centers_px": {
            str(spec["entity_id"]): [float(value) for value in spec["center_px"]]
            for spec in chain_specs
        },
        "shot_arrow_bboxes_px": {
            str(spec["entity_id"]): [float(value) for value in spec["bbox_px"]]
            for spec in shot_specs
        },
        "shot_arrow_insertion_points_px": {
            str(spec["entity_id"]): [float(value) for value in spec["insertion_point_px"]]
            for spec in shot_specs
        },
        "marked_shot_arrow_bbox_px": None if marked_shot_spec is None else [float(value) for value in marked_shot_spec["bbox_px"]],
        "marked_shot_arrow_insertion_point_px": None
        if marked_shot_spec is None
        else [float(value) for value in marked_shot_spec["insertion_point_px"]],
        "scene_variant": str(sample.scene_variant),
        "panel_scene_style": {key: value for key, value in dict(style_meta).items() if key not in {"text_legibility", "text_color_policy"}},
        "marble_chain_style": {
            "style_variant": str(style_variant),
            **{str(key): [int(value) for value in rgb] for key, rgb in marble_style.items()},
        },
        "text_style": {
            "font_family": str(font_family),
            "font_asset": get_font_family_record(str(font_family)).to_trace(),
        },
        "layout_jitter": attach_games_unit_size_jitter(resolved_jitter, unit_meta),
    }
    return _RenderedScene(
        image=image.convert("RGB"),
        entities=tuple(entities),
        render_map=dict(render_map),
        style_meta={key: value for key, value in dict(style_meta).items() if key not in {"text_legibility", "text_color_policy"}},
        background_meta=dict(background_meta),
    )


def _json_examples(query_id: str) -> Tuple[str, str]:
    if str(query_id) in SUPPORTED_DIRECTION_LABEL_QUERIES:
        answer_and_evidence = {"evidence": [[465, 286]], "answer": "C"}
        answer_only = {"answer": "C"}
    else:
        answer_and_evidence = {"evidence": [[448, 224], [502, 242], [551, 276], [590, 322]], "answer": 4}
        answer_only = {"answer": 4}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=True, allow_nan=False, separators=(",", ":")),
    )


def _build_prompt(sample: _Sample, *, instance_seed: int) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    prompt_defaults = required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description_marble_chain_board",
            f"answer_hint_{str(sample.query_id)}",
            f"evidence_hint_{str(sample.query_id)}",
            "marble_chain_rule_text",
        ),
        context=f"prompt defaults for {str(sample.query_id)}",
    )
    json_example, json_example_answer_only = _json_examples(str(sample.query_id))
    slots = {
        "object_description": str(prompt_defaults["object_description_marble_chain_board"]),
        "json_output_contract": str(prompt_defaults["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
        "answer_hint": str(prompt_defaults[f"answer_hint_{str(sample.query_id)}"]),
        "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(sample.query_id)}"]),
        "json_example": str(json_example),
        "json_example_answer_only": str(json_example_answer_only),
        "marble_chain_rule_text": str(prompt_defaults["marble_chain_rule_text"]),
        "target_pop_count": "" if sample.target_pop_count is None else str(int(sample.target_pop_count)),
    }
    prompt_selection = render_task_prompt_variants(
        domain="games",
        task_group=TASK_GROUP,
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        query_key=str(sample.query_id),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
        slots=slots,
        instance_seed=int(instance_seed),
    )
    prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
    return str(prompt_artifacts.prompt), dict(prompt_artifacts.prompt_variants), {
        "bundle_id": str(prompt_defaults["bundle_id"]),
        "prompt_variant": dict(prompt_artifacts.prompt_variant),
        "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
        "prompt_variants_for_trace": dict(prompt_artifacts.prompt_variants_for_trace),
    }


def _build_complexity(*, task_id: str, sample: _Sample, evidence_count: int) -> Any:
    weights = resolve_games_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=str(task_id))
    query_reasoning = {
        QUERY_MAX_POP_DIRECTION: 0.62,
        QUERY_TARGET_POP_DIRECTION: 0.66,
        QUERY_POP_COUNT: 0.44,
    }[str(sample.query_id)]
    option_load = len(sample.option_specs) if sample.option_specs else 1
    return build_games_complexity(
        weights=weights,
        components={
            "visual_scan": normalize_linear(float(len(sample.chain_colors)), min_value=12.0, max_value=18.0),
            "state_reasoning": float(query_reasoning),
            "ambiguity": normalize_linear(float(option_load), min_value=1.0, max_value=7.0),
            "output_burden": normalize_linear(float(evidence_count), min_value=1.0, max_value=9.0),
        },
    )


class _MarbleChainTask:
    """Shared generator for public marble-chain tasks."""

    domain = "games"
    task_group = TASK_GROUP
    default_dataset_enabled = True
    supported_queries: Tuple[str, ...]
    query_weights_key: str

    def _sample(self, rng, *, task_id: str, instance_seed: int, params: Mapping[str, Any], scene_variant: str, query_id: str) -> _Sample:
        if str(query_id) in SUPPORTED_DIRECTION_LABEL_QUERIES:
            return _sample_direction_label(
                rng,
                task_id=str(task_id),
                instance_seed=int(instance_seed),
                params=params,
                scene_variant=str(scene_variant),
                query_id=str(query_id),
            )
        return _sample_effect_value(
            rng,
            task_id=str(task_id),
            instance_seed=int(instance_seed),
            params=params,
            scene_variant=str(scene_variant),
            query_id=str(query_id),
        )

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        scene_variant, scene_variant_probabilities = _sample_scene_variant(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
        )
        style_variant, style_variant_probabilities = _sample_style_variant(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
        )
        query_id, query_probabilities = _sample_query_id(
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
            supported=tuple(self.supported_queries),
            weights_key=str(self.query_weights_key),
        )
        sample: _Sample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{str(self.task_id)}.attempt.{int(attempt_index)}")
            try:
                sample = self._sample(
                    rng,
                    task_id=str(self.task_id),
                    instance_seed=int(instance_seed),
                    params=params,
                    scene_variant=str(scene_variant),
                    query_id=str(query_id),
                )
                break
            except ValueError:
                continue
        if sample is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid marble-chain scene after {max_attempts} attempts")

        rendered = _render_scene(
            sample=sample,
            task_id=str(self.task_id),
            instance_seed=int(instance_seed),
            params=params,
            style_variant=str(style_variant),
        )
        evidence_points = [
            list(rendered.render_map["entity_points_px"][str(entity_id)])
            for entity_id in sample.evidence_entity_ids
            if str(entity_id) in rendered.render_map["entity_points_px"]
        ]
        prompt, prompt_variants, prompt_meta = _build_prompt(sample, instance_seed=int(instance_seed))
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        answer_gt = TypedValue(type=str(sample.answer_type), value=sample.answer)
        evidence_gt = TypedValue(type="point_set", value=[list(point) for point in evidence_points])
        complexity = _build_complexity(task_id=str(self.task_id), sample=sample, evidence_count=len(evidence_points))
        option_trace = [
            {
                "label": str(option.label),
                "entity_id": str(option.entity_id),
                "slot_index": int(option.slot_index),
                "pop_count": int(option.outcome.pop_count),
                "remaining_count": int(option.outcome.remaining_count),
                "popped_indices": [int(index) for index in option.outcome.popped_indices],
                "is_answer": bool(option.is_answer),
            }
            for option in sample.option_specs
        ]
        marked_trace = None
        if sample.marked_outcome is not None:
            marked_trace = {
                "slot_index": int(sample.marked_outcome.slot_index),
                "pop_count": int(sample.marked_outcome.pop_count),
                "remaining_count": int(sample.marked_outcome.remaining_count),
                "popped_indices": [int(index) for index in sample.marked_outcome.popped_indices],
                "affected_indices": [int(index) for index in sample.marked_outcome.affected_indices],
            }
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_marble_chain_{str(sample.scene_variant)}",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_variant": str(sample.scene_variant),
                    "query_id": str(sample.query_id),
                    "style_variant": str(style_variant),
                    "chain_length": int(len(sample.chain_colors)),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sample.evidence_entity_ids],
                },
            },
            "query_spec": {
                "query_id": str(sample.query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": {
                    "scene_variant": str(sample.scene_variant),
                    "query_id": str(sample.query_id),
                    "style_variant": str(style_variant),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                    "query_id_probabilities": dict(query_probabilities),
                    "style_variant_probabilities": dict(style_variant_probabilities),
                    **dict(sample.metadata),
                },
            },
            "render_spec": {
                "scene_variant": str(sample.scene_variant),
                "style_variant": str(style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered.render_map.get("layout_jitter", {})),
                "panel_scene_style": dict(rendered.style_meta),
                "marble_chain_style": dict(rendered.render_map.get("marble_chain_style", {})),
                "text_style": dict(rendered.render_map.get("text_style", {})),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "scene_variant": str(sample.scene_variant),
                "query_id": str(sample.query_id),
                "style_variant": str(style_variant),
                "chain_colors": list(sample.chain_colors),
                "shooter_color": str(sample.shooter_color),
                "shot_options": option_trace,
                "marked_outcome": marked_trace,
                "target_pop_count": None if sample.target_pop_count is None else int(sample.target_pop_count),
                "answer": sample.answer,
                "evidence_entity_ids": [str(entity_id) for entity_id in sample.evidence_entity_ids],
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sample.evidence_entity_ids],
            },
            "projected_evidence": {
                "type": "point_set",
                "point_set": [list(point) for point in evidence_points],
                "pixel_point_set": [list(point) for point in evidence_points],
            },
            "background": dict(rendered.background_meta),
            "post_image_noise": dict(post_noise_meta),
        }
        return TaskOutput(
            prompt=str(prompt),
            prompt_variants=dict(prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.query_id),
        )


@register_task
class GamesMarbleChainShotDirectionLabelTask(_MarbleChainTask):
    """Choose a labeled shot direction by simulated pop effect."""

    task_id = "task_games__marble_chain__shot_direction_label"
    supported_queries = SUPPORTED_DIRECTION_LABEL_QUERIES
    query_weights_key = "direction_label_query_id_weights"


@register_task
class GamesMarbleChainShotEffectValueTask(_MarbleChainTask):
    """Compute a numeric effect of the marked marble-chain shot."""

    task_id = "task_games__marble_chain__shot_effect_value"
    supported_queries = SUPPORTED_EFFECT_VALUE_QUERIES
    query_weights_key = "effect_value_query_id_weights"


__all__ = [
    "GamesMarbleChainShotDirectionLabelTask",
    "GamesMarbleChainShotEffectValueTask",
]
