"""Milestone-timeline temporal task with ordering and interval-count queries."""

from __future__ import annotations

import calendar
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.complexity import (
    build_temporal_complexity,
    normalize_int_with_bounds,
    resolve_temporal_complexity_weights,
)
from ..shared.style import (
    SUPPORTED_TEMPORAL_COLOR_NAMES,
    SUPPORTED_TEMPORAL_STYLE_VARIANTS,
    build_temporal_timeline_theme,
)
from ..shared.task_support import resolve_temporal_named_variant, resolve_temporal_selection_index
from ..shared.time_format import format_month_day_label, month_name
from ..shared.timeline_scene import (
    SUPPORTED_TEMPORAL_TIMELINE_SCENE_VARIANTS,
    TimelineEventSpec,
    TimelineRenderParams,
    render_timeline_scene,
    resolve_timeline_render_params,
)
from ..shared.visual_defaults import load_temporal_background_defaults, load_temporal_noise_defaults


TASK_ID = "task_temporal_timeline_milestones"
SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "before_reference_count",
    "between_reference_events_count",
    "position_of_reference",
)

_TEMPORAL_ORDER_BASE_BY_VARIANT = {
    "before_reference_count": 0.42,
    "between_reference_events_count": 0.56,
    "position_of_reference": 0.50,
}
_VISUAL_SCAN_BASE_BY_SCENE = {
    "classic": 0.40,
    "roadmap": 0.48,
    "minimal": 0.30,
}
_VISUAL_SCAN_STYLE_BONUS = {
    "studio": 0.00,
    "accented": 0.04,
    "marker": 0.06,
}
_CLUTTER_BASE_BY_SCENE = {
    "classic": 0.28,
    "roadmap": 0.34,
    "minimal": 0.20,
}
_CLUTTER_STYLE_BONUS = {
    "studio": 0.00,
    "accented": 0.04,
    "marker": 0.07,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for milestone-timeline scenes."""

    year_min: int = 2024
    year_max: int = 2030
    event_count_support: Tuple[int, ...] = (6, 7, 8, 9)
    before_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7)
    between_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    position_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8)
    event_label_pool: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H", "I")
    canvas_width: int = 1120
    canvas_height: int = 700
    outer_margin_px: int = 34
    title_height_px: int = 86
    title_gap_px: int = 18
    panel_corner_radius_px: int = 20
    panel_outline_width_px: int = 3
    axis_width_px: int = 4
    axis_tick_height_px: int = 12
    marker_radius_px: int = 10
    marker_outline_width_px: int = 3
    connector_width_px: int = 3
    card_width_px: int = 106
    card_height_px: int = 70
    card_corner_radius_px: int = 14
    card_outline_width_px: int = 3
    label_font_size_px: int = 22
    date_font_size_px: int = 16
    title_font_size_px: int = 30
    subtitle_font_size_px: int = 18
    event_vertical_gap_px: int = 16
    event_stem_length_px: int = 44


@dataclass(frozen=True)
class _RawTimelineEvent:
    """Task-internal milestone record before rendering."""

    event_id: str
    label: str
    day_of_month: int
    order_index: int
    reference_kind: str = "none"

    @property
    def date_text(self) -> str:
        """Return one placeholder date label for debugging before month binding."""

        return str(self.day_of_month)


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved semantic and visual support for one milestone-timeline query."""

    task_variant: str
    scene_variant: str
    style_variant: str
    accent_color_name: str
    year: int
    month: int
    month_name: str
    title_text: str
    subtitle_text: str
    raw_events: Tuple[_RawTimelineEvent, ...]
    answer_value: int
    answer_event_ids: Tuple[str, ...]
    reference_event_ids: Tuple[str, ...]
    event_count_support: Tuple[int, ...]
    before_count_support: Tuple[int, ...]
    between_count_support: Tuple[int, ...]
    position_support: Tuple[int, ...]
    task_variant_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("temporal", "timeline")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_temporal_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_temporal_background_defaults(task_group="timeline")
POST_IMAGE_NOISE_DEFAULTS = load_temporal_noise_defaults(task_group="timeline", apply_prob=0.0)


def _canonical_event_bbox_example() -> list[int]:
    """Return one stable event-card bbox example for prompt examples."""

    return [286, 158, 390, 228]


def _build_prompt_json_examples(*, task_variant: str) -> tuple[str, str]:
    """Return prompt JSON examples that match the active timeline query."""

    if str(task_variant) == "before_reference_count":
        answer_and_evidence = {
            "evidence": [
                [160, 158, 264, 228],
                [286, 158, 390, 228],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    elif str(task_variant) == "between_reference_events_count":
        answer_and_evidence = {
            "evidence": [
                [412, 410, 516, 480],
                [538, 158, 642, 228],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    else:
        answer_and_evidence = {
            "evidence": [
                [160, 158, 264, 228],
                [286, 158, 390, 228],
                [412, 410, 516, 480],
            ],
            "answer": 3,
        }
        answer_only = {"answer": 3}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _resolve_named_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Tuple[str, ...],
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named timeline axis."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}")
    return resolve_temporal_named_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported=supported,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace=str(namespace),
    )


def _resolve_int_support(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    """Resolve one integer support list from config or explicit params."""

    raw_values = params.get(key, group_default(_GEN_DEFAULTS, key, fallback))
    resolved: List[int] = []
    for raw_value in raw_values:
        value = int(raw_value)
        if value not in resolved:
            resolved.append(value)
    if not resolved:
        raise ValueError(f"{key} must not be empty for {TASK_ID}")
    return tuple(int(value) for value in resolved)


def _resolve_str_support(params: Mapping[str, Any], key: str, fallback: Sequence[str]) -> Tuple[str, ...]:
    """Resolve one string support list from config or explicit params."""

    raw_values = params.get(key, group_default(_GEN_DEFAULTS, key, fallback))
    resolved: List[str] = []
    for raw_value in raw_values:
        value = str(raw_value).strip()
        if value and value not in resolved:
            resolved.append(value)
    if not resolved:
        raise ValueError(f"{key} must not be empty for {TASK_ID}")
    return tuple(str(value) for value in resolved)


def _sample_month(instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, int, int]:
    """Sample one Gregorian month and return `(year, month, days_in_month)`."""

    explicit_year = params.get("year")
    explicit_month = params.get("month")
    if explicit_year is not None and explicit_month is None:
        raise ValueError("month must be provided when year is explicit for temporal timelines")
    if explicit_month is not None and explicit_year is None:
        raise ValueError("year must be provided when month is explicit for temporal timelines")

    if explicit_year is not None and explicit_month is not None:
        _, days_in_month = calendar.monthrange(int(explicit_year), int(explicit_month))
        return int(explicit_year), int(explicit_month), int(days_in_month)

    year_min = int(params.get("year_min", group_default(_GEN_DEFAULTS, "year_min", _DEFAULTS.year_min)))
    year_max = int(params.get("year_max", group_default(_GEN_DEFAULTS, "year_max", _DEFAULTS.year_max)))
    if int(year_max) < int(year_min):
        raise ValueError("year_max must be >= year_min for temporal timelines")
    year_support = tuple(range(int(year_min), int(year_max) + 1))
    year = int(
        year_support[
            int(
                resolve_temporal_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{TASK_ID}:year",
                )
                % len(year_support)
            )
        ]
    )
    month = 1 + int(
        resolve_temporal_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:month",
        )
        % 12
    )
    _, days_in_month = calendar.monthrange(int(year), int(month))
    return int(year), int(month), int(days_in_month)


def _build_raw_events(
    *,
    month: int,
    day_values: Sequence[int],
    labels: Sequence[str],
    primary_reference_index: int | None,
    secondary_reference_index: int | None,
) -> Tuple[_RawTimelineEvent, ...]:
    """Build one ordered milestone list from sampled labels and dates."""

    del month
    events: List[_RawTimelineEvent] = []
    for index, (label, day_of_month) in enumerate(zip(labels, day_values)):
        reference_kind = "none"
        if primary_reference_index is not None and int(index) == int(primary_reference_index):
            reference_kind = "primary"
        elif secondary_reference_index is not None and int(index) == int(secondary_reference_index):
            reference_kind = "secondary"
        events.append(
            _RawTimelineEvent(
                event_id=f"event_{str(label).lower()}",
                label=str(label),
                day_of_month=int(day_of_month),
                order_index=int(index),
                reference_kind=str(reference_kind),
            )
        )
    return tuple(events)


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one concrete milestone-timeline query from balanced supports."""

    task_variant, task_variant_probabilities = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        supported=SUPPORTED_TASK_VARIANTS,
        namespace="task_variant",
    )
    scene_variant, scene_variant_probabilities = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_TEMPORAL_TIMELINE_SCENE_VARIANTS,
        namespace="scene_variant",
    )
    style_variant, style_variant_probabilities = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_TEMPORAL_STYLE_VARIANTS,
        namespace="style_variant",
    )
    accent_color_name, accent_color_name_probabilities = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        balance_flag_key="balanced_accent_color_name_sampling",
        supported=SUPPORTED_TEMPORAL_COLOR_NAMES,
        namespace="accent_color_name",
    )

    year, month, days_in_month = _sample_month(int(instance_seed), params)
    event_count_support = _resolve_int_support(params, "event_count_support", _DEFAULTS.event_count_support)
    before_count_support = _resolve_int_support(params, "before_count_support", _DEFAULTS.before_count_support)
    between_count_support = _resolve_int_support(params, "between_count_support", _DEFAULTS.between_count_support)
    position_support = _resolve_int_support(params, "position_support", _DEFAULTS.position_support)
    event_label_pool = _resolve_str_support(params, "event_label_pool", _DEFAULTS.event_label_pool)

    max_event_count = min(int(days_in_month), len(event_label_pool), max(int(value) for value in event_count_support))
    if int(max_event_count) < min(int(value) for value in event_count_support):
        raise ValueError("timeline month does not have enough days for the configured event_count_support")

    if str(task_variant) == "before_reference_count":
        feasible_answers = [int(value) for value in before_count_support if 0 <= int(value) <= int(max_event_count - 1)]
        if not feasible_answers:
            raise ValueError("before_count_support has no feasible values for temporal timelines")
        answer_value = int(
            feasible_answers[
                int(
                    resolve_temporal_selection_index(
                        params=params,
                        instance_seed=int(instance_seed),
                        namespace=f"{TASK_ID}:before_answer",
                    )
                    % len(feasible_answers)
                )
            ]
        )
        feasible_event_counts = [int(value) for value in event_count_support if int(answer_value + 1) <= int(value) <= int(max_event_count)]
        event_count = int(
            feasible_event_counts[
                int(
                    resolve_temporal_selection_index(
                        params=params,
                        instance_seed=int(instance_seed),
                        namespace=f"{TASK_ID}:before_event_count",
                    )
                    % len(feasible_event_counts)
                )
            ]
        )
        primary_reference_index = int(answer_value)
        secondary_reference_index = None
        answer_slice = slice(0, int(primary_reference_index))
    elif str(task_variant) == "between_reference_events_count":
        feasible_answers = [int(value) for value in between_count_support if 0 <= int(value) <= int(max_event_count - 2)]
        if not feasible_answers:
            raise ValueError("between_count_support has no feasible values for temporal timelines")
        answer_value = int(
            feasible_answers[
                int(
                    resolve_temporal_selection_index(
                        params=params,
                        instance_seed=int(instance_seed),
                        namespace=f"{TASK_ID}:between_answer",
                    )
                    % len(feasible_answers)
                )
            ]
        )
        feasible_event_counts = [int(value) for value in event_count_support if int(answer_value + 2) <= int(value) <= int(max_event_count)]
        event_count = int(
            feasible_event_counts[
                int(
                    resolve_temporal_selection_index(
                        params=params,
                        instance_seed=int(instance_seed),
                        namespace=f"{TASK_ID}:between_event_count",
                    )
                    % len(feasible_event_counts)
                )
            ]
        )
        left_index_support = list(range(0, int(event_count - answer_value - 1)))
        primary_reference_index = int(
            left_index_support[
                int(
                    resolve_temporal_selection_index(
                        params=params,
                        instance_seed=int(instance_seed),
                        namespace=f"{TASK_ID}:between_left_index",
                    )
                    % len(left_index_support)
                )
            ]
        )
        secondary_reference_index = int(primary_reference_index + answer_value + 1)
        answer_slice = slice(int(primary_reference_index + 1), int(secondary_reference_index))
    else:
        feasible_answers = [int(value) for value in position_support if 1 <= int(value) <= int(max_event_count)]
        if not feasible_answers:
            raise ValueError("position_support has no feasible values for temporal timelines")
        answer_value = int(
            feasible_answers[
                int(
                    resolve_temporal_selection_index(
                        params=params,
                        instance_seed=int(instance_seed),
                        namespace=f"{TASK_ID}:position_answer",
                    )
                    % len(feasible_answers)
                )
            ]
        )
        feasible_event_counts = [int(value) for value in event_count_support if int(answer_value) <= int(value) <= int(max_event_count)]
        event_count = int(
            feasible_event_counts[
                int(
                    resolve_temporal_selection_index(
                        params=params,
                        instance_seed=int(instance_seed),
                        namespace=f"{TASK_ID}:position_event_count",
                    )
                    % len(feasible_event_counts)
                )
            ]
        )
        primary_reference_index = int(answer_value - 1)
        secondary_reference_index = None
        answer_slice = slice(0, int(answer_value))

    labels = tuple(str(label) for label in event_label_pool[:event_count])
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.days")
    day_values = tuple(sorted(int(value) for value in rng.sample(list(range(1, int(days_in_month) + 1)), k=int(event_count))))
    raw_events = _build_raw_events(
        month=int(month),
        day_values=tuple(day_values),
        labels=labels,
        primary_reference_index=(int(primary_reference_index) if primary_reference_index is not None else None),
        secondary_reference_index=(int(secondary_reference_index) if secondary_reference_index is not None else None),
    )
    answer_event_ids = tuple(str(event.event_id) for event in raw_events[answer_slice])
    reference_event_ids = tuple(
        str(raw_events[index].event_id)
        for index in (primary_reference_index, secondary_reference_index)
        if index is not None
    )

    return _ResolvedQuery(
        task_variant=str(task_variant),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        accent_color_name=str(accent_color_name),
        year=int(year),
        month=int(month),
        month_name=str(month_name(int(month))),
        title_text="Milestone timeline",
        subtitle_text=f"{month_name(int(month))} {int(year)}",
        raw_events=tuple(raw_events),
        answer_value=int(answer_value),
        answer_event_ids=tuple(answer_event_ids),
        reference_event_ids=tuple(reference_event_ids),
        event_count_support=tuple(int(value) for value in event_count_support),
        before_count_support=tuple(int(value) for value in before_count_support),
        between_count_support=tuple(int(value) for value in between_count_support),
        position_support=tuple(int(value) for value in position_support),
        task_variant_probabilities=dict(task_variant_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        accent_color_name_probabilities=dict(accent_color_name_probabilities),
    )


def _build_object_description(*, task_variant: str, month_name_text: str, year: int) -> str:
    """Return the prompt-facing scene description for one timeline variant."""

    if str(task_variant) == "between_reference_events_count":
        return (
            f"one labeled milestone timeline for {month_name_text} {int(year)} with dated event cards "
            "and two highlighted reference events"
        )
    return (
        f"one labeled milestone timeline for {month_name_text} {int(year)} with dated event cards "
        "and one highlighted reference event"
    )


def _build_answer_hint(*, task_variant: str) -> str:
    """Return the variant-specific answer hint text."""

    if str(task_variant) == "position_of_reference":
        return 'set "answer" to the 1-based integer position of the highlighted reference event'
    if str(task_variant) == "between_reference_events_count":
        return 'set "answer" to the integer count of events strictly between the two highlighted reference events'
    return 'set "answer" to the integer count of events before the highlighted reference event'


def _build_evidence_hint(*, task_variant: str) -> str:
    """Return the variant-specific evidence hint text."""

    if str(task_variant) == "position_of_reference":
        return (
            'set "evidence" to an array of bounding boxes [x1, y1, x2, y2] for every event card from the earliest '
            "event through the highlighted reference event, including the reference event itself"
        )
    if str(task_variant) == "between_reference_events_count":
        return (
            'set "evidence" to an array of bounding boxes [x1, y1, x2, y2] for all event cards strictly between '
            "the two highlighted reference events"
        )
    return 'set "evidence" to an array of bounding boxes [x1, y1, x2, y2] for all event cards before the highlighted reference event'


def _resolve_card_side(*, scene_variant: str, order_index: int) -> str:
    """Resolve whether one event card sits above or below the timeline axis."""

    if str(scene_variant) == "minimal":
        return "above"
    if str(scene_variant) == "roadmap":
        return "above" if (int(order_index) % 3) != 1 else "below"
    return "above" if (int(order_index) % 2) == 0 else "below"


@register_task
class TemporalTimelineMilestonesTask:
    """Reason over one milestone timeline with several numeric ordering queries."""

    task_id = TASK_ID
    domain = "temporal"
    task_group = "timeline"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query = _resolve_query(int(instance_seed), params=params)
        render_params = resolve_timeline_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_values=asdict(_DEFAULTS),
        )
        timeline_theme = build_temporal_timeline_theme(
            accent_color_name=str(query.accent_color_name),
            style_variant=str(query.style_variant),
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        image = background.copy().convert("RGB")
        rendered_events = tuple(
            TimelineEventSpec(
                event_id=str(event.event_id),
                label=str(event.label),
                date_text=str(format_month_day_label(int(query.month), int(event.day_of_month))),
                order_index=int(event.order_index),
                anchor_x_px=0.0,
                card_side=str(_resolve_card_side(scene_variant=str(query.scene_variant), order_index=int(event.order_index))),
                reference_kind=str(event.reference_kind),
            )
            for event in query.raw_events
        )
        rendered_scene = render_timeline_scene(
            image,
            title_text=str(query.title_text),
            subtitle_text=str(query.subtitle_text),
            events=rendered_events,
            scene_variant=str(query.scene_variant),
            render_params=render_params,
            visual_theme=timeline_theme,
        )
        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        evidence_bboxes = [
            [round(float(value), 3) for value in rendered_scene.event_bboxes_by_id[str(event_id)]]
            for event_id in query.answer_event_ids
        ]

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = _build_object_description(
            task_variant=str(query.task_variant),
            month_name_text=str(query.month_name),
            year=int(query.year),
        )
        evidence_hint = _build_evidence_hint(task_variant=str(query.task_variant))
        answer_hint = _build_answer_hint(task_variant=str(query.task_variant))
        json_example, json_example_answer_only = _build_prompt_json_examples(task_variant=str(query.task_variant))

        slots: Dict[str, str] = {
            "object_description": str(object_description),
            "json_output_contract": str(group_default(_PROMPT_DEFAULTS, "json_output_contract", "")),
            "json_output_contract_answer_only": str(group_default(_PROMPT_DEFAULTS, "json_output_contract_answer_only", "")),
            "evidence_hint": str(evidence_hint),
            "answer_hint": str(answer_hint),
            "json_example": str(json_example),
            "json_example_answer_only": str(json_example_answer_only),
        }

        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(query.task_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots=slots,
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(query.answer_value))
        evidence_gt = TypedValue(type="bbox_set", value=[list(box) for box in evidence_bboxes])

        event_records = [
            {
                "event_id": str(event.event_id),
                "label": str(event.label),
                "day_of_month": int(event.day_of_month),
                "date_text": str(format_month_day_label(int(query.month), int(event.day_of_month))),
                "order_index": int(event.order_index),
                "reference_kind": str(event.reference_kind),
                "card_side": str(_resolve_card_side(scene_variant=str(query.scene_variant), order_index=int(event.order_index))),
            }
            for event in query.raw_events
        ]

        trace_payload = {
            "scene_ir": {
                "scene_kind": "temporal_milestone_timeline",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(query.task_variant),
                    "scene_variant": str(query.scene_variant),
                    "style_variant": str(query.style_variant),
                    "accent_color_name": str(query.accent_color_name),
                    "year": int(query.year),
                    "month": int(query.month),
                    "month_name": str(query.month_name),
                    "reference_event_ids": [str(value) for value in query.reference_event_ids],
                },
            },
            "query_spec": {
                "task_variant": str(query.task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_variant": str(query.task_variant),
                    "scene_variant": str(query.scene_variant),
                    "style_variant": str(query.style_variant),
                    "accent_color_name": str(query.accent_color_name),
                    "year": int(query.year),
                    "month": int(query.month),
                    "month_name": str(query.month_name),
                    "event_count_support": [int(value) for value in query.event_count_support],
                    "before_count_support": [int(value) for value in query.before_count_support],
                    "between_count_support": [int(value) for value in query.between_count_support],
                    "position_support": [int(value) for value in query.position_support],
                    "task_variant_probabilities": dict(query.task_variant_probabilities),
                    "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                    "style_variant_probabilities": dict(query.style_variant_probabilities),
                    "accent_color_name_probabilities": dict(query.accent_color_name_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(query.scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
                "timeline_style": {
                    "accent_color_name": str(query.accent_color_name),
                    "style_variant": str(query.style_variant),
                    "title_text": str(query.title_text),
                    "subtitle_text": str(query.subtitle_text),
                    "resolved_colors_rgb": {
                        "panel_fill": [int(value) for value in timeline_theme.panel_fill_rgb],
                        "panel_outline": [int(value) for value in timeline_theme.panel_outline_rgb],
                        "axis_line": [int(value) for value in timeline_theme.axis_line_rgb],
                        "event_fill": [int(value) for value in timeline_theme.event_fill_rgb],
                        "event_outline": [int(value) for value in timeline_theme.event_outline_rgb],
                        "primary_reference_fill": [int(value) for value in timeline_theme.primary_reference_fill_rgb],
                        "secondary_reference_fill": [int(value) for value in timeline_theme.secondary_reference_fill_rgb],
                    },
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
                "panel_bbox_px": [round(float(value), 3) for value in rendered_scene.panel_bbox_px],
                "axis_bbox_px": [round(float(value), 3) for value in rendered_scene.axis_bbox_px],
                "title_text": str(rendered_scene.title_text),
                "subtitle_text": str(rendered_scene.subtitle_text),
                "event_bboxes_by_id": {
                    str(event_id): [round(float(value), 3) for value in bbox]
                    for event_id, bbox in rendered_scene.event_bboxes_by_id.items()
                },
                "reference_event_ids": [str(value) for value in query.reference_event_ids],
                "answer_event_ids": [str(value) for value in query.answer_event_ids],
            },
            "execution_trace": {
                "task_variant": str(query.task_variant),
                "scene_variant": str(query.scene_variant),
                "style_variant": str(query.style_variant),
                "accent_color_name": str(query.accent_color_name),
                "year": int(query.year),
                "month": int(query.month),
                "month_name": str(query.month_name),
                "event_count": len(query.raw_events),
                "answer_value": int(query.answer_value),
                "answer_event_ids": [str(value) for value in query.answer_event_ids],
                "reference_event_ids": [str(value) for value in query.reference_event_ids],
                "events": event_records,
                "task_variant_probabilities": dict(query.task_variant_probabilities),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "style_variant_probabilities": dict(query.style_variant_probabilities),
                "accent_color_name_probabilities": dict(query.accent_color_name_probabilities),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": [list(box) for box in evidence_bboxes],
            },
            "projected_evidence": {
                "bbox_set": [list(box) for box in evidence_bboxes],
            },
        }

        event_count = len(query.raw_events)
        reference_index = next(
            int(event.order_index)
            for event in query.raw_events
            if str(event.reference_kind) == "primary"
        )
        if str(query.task_variant) == "between_reference_events_count":
            secondary_index = next(
                int(event.order_index)
                for event in query.raw_events
                if str(event.reference_kind) == "secondary"
            )
            reference_span = int(secondary_index - reference_index)
        else:
            secondary_index = None
            reference_span = int(reference_index)

        complexity = build_temporal_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "temporal_order_reasoning": min(
                    1.0,
                    float(_TEMPORAL_ORDER_BASE_BY_VARIANT[str(query.task_variant)])
                    + (
                        0.18
                        * float(
                            normalize_int_with_bounds(
                                int(query.answer_value),
                                [0, 8] if str(query.task_variant) != "position_of_reference" else [1, 8],
                            )
                        )
                    )
                    + (0.08 * float(normalize_int_with_bounds(int(reference_span), [0, 7]))),
                ),
                "visual_scan": min(
                    1.0,
                    float(_VISUAL_SCAN_BASE_BY_SCENE[str(query.scene_variant)])
                    + float(_VISUAL_SCAN_STYLE_BONUS[str(query.style_variant)])
                    + (0.24 * float(normalize_int_with_bounds(int(event_count), [6, 9]))),
                ),
                "ambiguity": min(
                    1.0,
                    0.10
                    + (0.16 * float(normalize_int_with_bounds(int(event_count), [6, 9])))
                    + (
                        0.24
                        * float(
                            normalize_int_with_bounds(
                                int(min(reference_index, max(0, event_count - 1 - reference_index))),
                                [0, 4],
                            )
                        )
                    )
                    + (
                        0.12
                        * float(
                            normalize_int_with_bounds(
                                int(query.answer_value),
                                [0, 8] if str(query.task_variant) != "position_of_reference" else [1, 8],
                            )
                        )
                    ),
                ),
                "clutter": min(
                    1.0,
                    float(_CLUTTER_BASE_BY_SCENE[str(query.scene_variant)])
                    + float(_CLUTTER_STYLE_BONUS[str(query.style_variant)])
                    + (0.20 * float(normalize_int_with_bounds(int(event_count), [6, 9]))),
                ),
            },
        )

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(query.task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["TemporalTimelineMilestonesTask"]
