"""Single-day schedule temporal task with overlap, duration, and optimization queries."""

from __future__ import annotations

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
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.complexity import build_temporal_complexity, normalize_int_with_bounds, resolve_temporal_complexity_weights
from ..shared.schedule_scene import (
    SUPPORTED_TEMPORAL_SCHEDULE_SCENE_VARIANTS,
    RenderedScheduleScene,
    ScheduledEventSpec,
    ScheduleRenderParams,
    render_day_schedule_scene,
    resolve_schedule_render_params,
)
from ..shared.style import (
    SUPPORTED_TEMPORAL_COLOR_NAMES,
    SUPPORTED_TEMPORAL_STYLE_VARIANTS,
    build_temporal_schedule_theme,
)
from ..shared.task_support import resolve_temporal_named_variant
from ..shared.time_format import format_day_time_hhmm
from ..shared.visual_defaults import load_temporal_background_defaults, load_temporal_noise_defaults


TASK_ID = "task_temporal_schedule_day_planner"
SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "overlap_count",
    "longer_than_reference_count",
    "maximum_non_overlapping_count",
)
_INTERVAL_REASONING_BASE_BY_VARIANT = {
    "overlap_count": 0.40,
    "longer_than_reference_count": 0.46,
    "maximum_non_overlapping_count": 0.66,
}
_VISUAL_SCAN_BASE_BY_SCENE = {
    "classic": 0.42,
    "minimal": 0.30,
    "outline": 0.36,
}
_VISUAL_SCAN_STYLE_BONUS = {
    "studio": 0.00,
    "accented": 0.04,
    "marker": 0.06,
}
_CLUTTER_BASE_BY_SCENE = {
    "classic": 0.34,
    "minimal": 0.18,
    "outline": 0.24,
}
_CLUTTER_STYLE_BONUS = {
    "studio": 0.00,
    "accented": 0.04,
    "marker": 0.08,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for single-day planner scenes."""

    start_hour: int = 8
    end_hour: int = 18
    slot_minutes: int = 30
    max_lane_count: int = 5
    event_count_support: Tuple[int, ...] = (7, 8, 9, 10)
    overlap_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    longer_than_count_support: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
    maximum_non_overlapping_support: Tuple[int, ...] = (2, 3, 4, 5, 6, 7)
    reference_duration_slots_support: Tuple[int, ...] = (2, 3, 4)
    duration_slots_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    day_label_support: Tuple[str, ...] = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
    event_label_pool: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M")
    canvas_width: int = 920
    canvas_height: int = 820
    outer_margin_px: int = 36
    header_height_px: int = 92
    panel_corner_radius_px: int = 20
    panel_outline_width_px: int = 3
    time_axis_width_px: int = 94
    planner_top_gap_px: int = 18
    planner_bottom_gap_px: int = 24
    lane_gap_px: int = 8
    grid_line_width_px: int = 2
    minor_grid_line_width_px: int = 1
    hour_label_font_size_px: int = 16
    title_font_size_px: int = 28
    event_label_font_size_px: int = 18
    event_corner_radius_px: int = 12
    event_text_padding_px: int = 8


@dataclass(frozen=True)
class _RawEvent:
    """Task-internal event interval before lane assignment and rendering."""

    event_id: str
    label: str
    start_slot: int
    end_slot: int
    is_reference: bool = False

    @property
    def duration_slots(self) -> int:
        """Return the interval duration in discrete schedule slots."""

        return int(self.end_slot) - int(self.start_slot)


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved semantic and visual support for one single-day schedule query."""

    task_variant: str
    scene_variant: str
    style_variant: str
    accent_color_name: str
    day_label: str
    title_text: str
    start_hour: int
    end_hour: int
    slot_minutes: int
    max_lane_count: int
    event_count_support: Tuple[int, ...]
    overlap_count_support: Tuple[int, ...]
    longer_than_count_support: Tuple[int, ...]
    maximum_non_overlapping_support: Tuple[int, ...]
    raw_events: Tuple[_RawEvent, ...]
    rendered_events: Tuple[ScheduledEventSpec, ...]
    event_count: int
    lane_count: int
    answer_value: int
    answer_event_ids: Tuple[str, ...]
    reference_event_id: str | None
    task_variant_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("temporal", "schedule")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_temporal_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_temporal_background_defaults(task_group="schedule")
POST_IMAGE_NOISE_DEFAULTS = load_temporal_noise_defaults(task_group="schedule", apply_prob=0.0)


def _canonical_event_bbox_example() -> list[int]:
    """Return one stable event-block bbox example for prompt examples."""

    return [250, 276, 396, 366]


def _build_prompt_json_examples(*, task_variant: str) -> tuple[str, str]:
    """Return prompt JSON examples that match the active schedule query."""

    if str(task_variant) == "overlap_count":
        answer_and_evidence = {
            "evidence": [
                [250, 276, 396, 366],
                [404, 318, 550, 438],
            ],
            "answer": 2,
        }
        answer_only = {"answer": 2}
    elif str(task_variant) == "longer_than_reference_count":
        answer_and_evidence = {
            "evidence": [
                [250, 240, 396, 408],
                [404, 430, 550, 634],
                [558, 352, 704, 568],
            ],
            "answer": 3,
        }
        answer_only = {"answer": 3}
    else:
        answer_and_evidence = {
            "evidence": [
                [250, 220, 396, 316],
                [404, 316, 550, 412],
                [558, 412, 704, 508],
                [250, 508, 396, 604],
            ],
            "answer": 4,
        }
        answer_only = {"answer": 4}
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
    """Resolve one balanced named schedule-task axis."""

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


def _selection_index(*, params: Mapping[str, Any], instance_seed: int, namespace: str) -> int:
    """Resolve one stable selection index, favoring `_sampling_index` when present."""

    if "_sampling_index" in params:
        return int(params["_sampling_index"])
    return int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
    )


def _resolve_str_support(params: Mapping[str, Any], key: str, fallback: Sequence[str]) -> Tuple[str, ...]:
    """Resolve one string support list from config or explicit params."""

    raw_values = params.get(key, group_default(_GEN_DEFAULTS, key, fallback))
    resolved: List[str] = []
    for raw_value in raw_values:
        value = str(raw_value)
        if value and value not in resolved:
            resolved.append(value)
    if not resolved:
        raise ValueError(f"{key} must not be empty for {TASK_ID}")
    return tuple(str(value) for value in resolved)


def _intervals_overlap(left: Tuple[int, int], right: Tuple[int, int]) -> bool:
    """Return whether two half-open slot intervals overlap."""

    return bool(int(left[0]) < int(right[1]) and int(right[0]) < int(left[1]))


def _slots_to_total_minutes(slot_index: int, *, start_hour: int, slot_minutes: int) -> int:
    """Convert one schedule slot index into absolute day minutes."""

    return int((int(start_hour) * 60) + (int(slot_index) * int(slot_minutes)))


def _build_raw_event(label: str, start_slot: int, end_slot: int, *, is_reference: bool = False) -> _RawEvent:
    """Build one task-internal raw event record."""

    return _RawEvent(
        event_id=f"event_{str(label).lower()}",
        label=str(label),
        start_slot=int(start_slot),
        end_slot=int(end_slot),
        is_reference=bool(is_reference),
    )


def _assign_lanes(raw_events: Sequence[_RawEvent]) -> Tuple[Tuple[ScheduledEventSpec, ...], int]:
    """Assign non-overlapping lane indices to one set of schedule events."""

    lane_end_slots: List[int] = []
    scheduled: List[ScheduledEventSpec] = []
    for raw_event in sorted(raw_events, key=lambda event: (int(event.start_slot), int(event.end_slot), str(event.label))):
        lane_index: int | None = None
        for candidate_lane, lane_end in enumerate(lane_end_slots):
            if int(lane_end) <= int(raw_event.start_slot):
                lane_index = int(candidate_lane)
                lane_end_slots[int(candidate_lane)] = int(raw_event.end_slot)
                break
        if lane_index is None:
            lane_index = len(lane_end_slots)
            lane_end_slots.append(int(raw_event.end_slot))
        scheduled.append(
            ScheduledEventSpec(
                event_id=str(raw_event.event_id),
                label=str(raw_event.label),
                start_total_minutes=0,
                end_total_minutes=0,
                lane_index=int(lane_index),
                is_reference=bool(raw_event.is_reference),
            )
        )
    lane_count = max(1, len(lane_end_slots))
    return tuple(scheduled), int(lane_count)


def _hydrate_event_minutes(
    scheduled_events: Sequence[ScheduledEventSpec],
    raw_events_by_id: Mapping[str, _RawEvent],
    *,
    start_hour: int,
    slot_minutes: int,
) -> Tuple[ScheduledEventSpec, ...]:
    """Fill rendered schedule events with day-minute coordinates."""

    hydrated: List[ScheduledEventSpec] = []
    for scheduled_event in scheduled_events:
        raw_event = raw_events_by_id[str(scheduled_event.event_id)]
        hydrated.append(
            ScheduledEventSpec(
                event_id=str(raw_event.event_id),
                label=str(raw_event.label),
                start_total_minutes=_slots_to_total_minutes(
                    int(raw_event.start_slot),
                    start_hour=int(start_hour),
                    slot_minutes=int(slot_minutes),
                ),
                end_total_minutes=_slots_to_total_minutes(
                    int(raw_event.end_slot),
                    start_hour=int(start_hour),
                    slot_minutes=int(slot_minutes),
                ),
                lane_index=int(scheduled_event.lane_index),
                is_reference=bool(raw_event.is_reference),
            )
        )
    return tuple(hydrated)


def _random_interval(
    rng,
    *,
    total_slots: int,
    duration_support: Sequence[int],
) -> Tuple[int, int]:
    """Sample one random slot interval from the provided duration support."""

    duration = int(rng.choice([int(value) for value in duration_support]))
    duration = max(1, min(int(duration), int(total_slots)))
    start_slot = int(rng.randint(0, int(total_slots - duration)))
    return int(start_slot), int(start_slot + duration)


def _sample_overlap_variant(
    *,
    instance_seed: int,
    total_slots: int,
    params: Mapping[str, Any],
    event_labels: Sequence[str],
    event_count_support: Sequence[int],
    overlap_count_support: Sequence[int],
    reference_duration_slots_support: Sequence[int],
    duration_slots_support: Sequence[int],
    max_lane_count: int,
) -> Tuple[Tuple[_RawEvent, ...], Tuple[str, ...], str]:
    """Sample one overlap-count schedule with a highlighted reference event."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.overlap_count")
    feasible_event_counts = [int(value) for value in event_count_support if 2 <= int(value) <= len(event_labels)]
    if not feasible_event_counts:
        raise ValueError("no feasible event_count_support exists for overlap_count")
    event_count = int(
        feasible_event_counts[
            int(_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:overlap_event_count") % len(feasible_event_counts))
        ]
    )
    feasible_answer_support = [int(value) for value in overlap_count_support if 0 <= int(value) <= int(event_count - 1)]
    if not feasible_answer_support:
        raise ValueError("no feasible overlap_count_support exists for overlap_count")
    total_support = [int(value) for value in duration_slots_support if 1 <= int(value) < int(total_slots)]
    if not total_support:
        raise ValueError("duration_slots_support must contain values inside the schedule horizon")

    for _ in range(600):
        answer_count = int(
            feasible_answer_support[
                int(_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:overlap_answer_count") % len(feasible_answer_support))
            ]
        )
        reference_support = [int(value) for value in reference_duration_slots_support if 1 <= int(value) < int(total_slots)]
        ref_duration = int(
            reference_support[
                int(_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:overlap_reference_duration") % len(reference_support))
            ]
        )
        ref_start = int(rng.randint(0, int(total_slots - ref_duration)))
        ref_interval = (int(ref_start), int(ref_start + ref_duration))

        used_intervals = {tuple(ref_interval)}
        overlap_intervals: List[Tuple[int, int]] = []
        distractor_intervals: List[Tuple[int, int]] = []

        inner_guard = 0
        while len(overlap_intervals) < int(answer_count) and inner_guard < 600:
            inner_guard += 1
            candidate = _random_interval(rng, total_slots=int(total_slots), duration_support=total_support)
            if candidate in used_intervals or candidate == tuple(ref_interval):
                continue
            if not _intervals_overlap(candidate, ref_interval):
                continue
            overlap_intervals.append(tuple(candidate))
            used_intervals.add(tuple(candidate))

        inner_guard = 0
        while len(distractor_intervals) < int(event_count - 1 - answer_count) and inner_guard < 800:
            inner_guard += 1
            if float(rng.random()) < 0.35:
                if float(rng.random()) < 0.5 and int(ref_start) > 0:
                    end_slot = int(ref_start)
                    duration = int(rng.choice(total_support))
                    start_slot = max(0, int(end_slot - duration))
                    candidate = (int(start_slot), int(end_slot))
                else:
                    start_slot = int(ref_interval[1])
                    if int(start_slot) >= int(total_slots):
                        continue
                    duration = int(rng.choice(total_support))
                    candidate = (int(start_slot), min(int(total_slots), int(start_slot + duration)))
                if int(candidate[1]) <= int(candidate[0]):
                    continue
            else:
                candidate = _random_interval(rng, total_slots=int(total_slots), duration_support=total_support)
            if candidate in used_intervals or candidate == tuple(ref_interval):
                continue
            if _intervals_overlap(candidate, ref_interval):
                continue
            distractor_intervals.append(tuple(candidate))
            used_intervals.add(tuple(candidate))

        if len(overlap_intervals) != int(answer_count) or len(distractor_intervals) != int(event_count - 1 - answer_count):
            continue

        raw_events = [
            _build_raw_event(str(event_labels[0]), int(ref_interval[0]), int(ref_interval[1]), is_reference=True),
        ]
        raw_events.extend(
            _build_raw_event(str(event_labels[index + 1]), int(interval[0]), int(interval[1]))
            for index, interval in enumerate(overlap_intervals)
        )
        raw_events.extend(
            _build_raw_event(str(event_labels[1 + len(overlap_intervals) + index]), int(interval[0]), int(interval[1]))
            for index, interval in enumerate(distractor_intervals)
        )
        _, lane_count = _assign_lanes(raw_events)
        if int(lane_count) > int(max_lane_count):
            continue
        answer_event_ids = tuple(event.event_id for event in raw_events if not event.is_reference and _intervals_overlap((event.start_slot, event.end_slot), ref_interval))
        return tuple(raw_events), tuple(answer_event_ids), str(raw_events[0].event_id)

    raise ValueError("failed to sample a readable overlap-count schedule")


def _sample_longer_variant(
    *,
    instance_seed: int,
    total_slots: int,
    params: Mapping[str, Any],
    event_labels: Sequence[str],
    event_count_support: Sequence[int],
    longer_than_count_support: Sequence[int],
    reference_duration_slots_support: Sequence[int],
    duration_slots_support: Sequence[int],
    max_lane_count: int,
) -> Tuple[Tuple[_RawEvent, ...], Tuple[str, ...], str]:
    """Sample one duration-comparison schedule with a highlighted reference event."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.longer_than_reference_count")
    feasible_event_counts = [int(value) for value in event_count_support if 2 <= int(value) <= len(event_labels)]
    if not feasible_event_counts:
        raise ValueError("no feasible event_count_support exists for longer_than_reference_count")
    durations = [int(value) for value in duration_slots_support if 1 <= int(value) < int(total_slots)]
    if not durations:
        raise ValueError("duration_slots_support must contain values inside the schedule horizon")

    for _ in range(600):
        event_count = int(
            feasible_event_counts[
                int(_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:longer_event_count") % len(feasible_event_counts))
            ]
        )
        reference_support = [int(value) for value in reference_duration_slots_support if 1 <= int(value) < int(total_slots)]
        ref_duration = int(
            reference_support[
                int(_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:longer_reference_duration") % len(reference_support))
            ]
        )
        reference_interval = _random_interval(rng, total_slots=int(total_slots), duration_support=(int(ref_duration),))
        feasible_answer_support = [int(value) for value in longer_than_count_support if 0 <= int(value) <= int(event_count - 1)]
        if not feasible_answer_support:
            raise ValueError("no feasible longer_than_count_support exists for longer_than_reference_count")
        answer_count = int(
            feasible_answer_support[
                int(_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:longer_answer_count") % len(feasible_answer_support))
            ]
        )

        longer_durations = [int(value) for value in durations if int(value) > int(ref_duration)]
        not_longer_durations = [int(value) for value in durations if int(value) <= int(ref_duration)]
        if answer_count > 0 and not longer_durations:
            continue
        if int(event_count - 1 - answer_count) > 0 and not not_longer_durations:
            continue

        used_intervals = {tuple(reference_interval)}
        longer_intervals: List[Tuple[int, int]] = []
        other_intervals: List[Tuple[int, int]] = []

        inner_guard = 0
        while len(longer_intervals) < int(answer_count) and inner_guard < 600:
            inner_guard += 1
            candidate = _random_interval(rng, total_slots=int(total_slots), duration_support=tuple(longer_durations))
            if candidate in used_intervals or candidate == tuple(reference_interval):
                continue
            longer_intervals.append(tuple(candidate))
            used_intervals.add(tuple(candidate))

        inner_guard = 0
        while len(other_intervals) < int(event_count - 1 - answer_count) and inner_guard < 800:
            inner_guard += 1
            candidate = _random_interval(rng, total_slots=int(total_slots), duration_support=tuple(not_longer_durations))
            if candidate in used_intervals or candidate == tuple(reference_interval):
                continue
            other_intervals.append(tuple(candidate))
            used_intervals.add(tuple(candidate))

        if len(longer_intervals) != int(answer_count) or len(other_intervals) != int(event_count - 1 - answer_count):
            continue

        raw_events = [
            _build_raw_event(str(event_labels[0]), int(reference_interval[0]), int(reference_interval[1]), is_reference=True),
        ]
        raw_events.extend(
            _build_raw_event(str(event_labels[index + 1]), int(interval[0]), int(interval[1]))
            for index, interval in enumerate(longer_intervals)
        )
        raw_events.extend(
            _build_raw_event(str(event_labels[1 + len(longer_intervals) + index]), int(interval[0]), int(interval[1]))
            for index, interval in enumerate(other_intervals)
        )
        _, lane_count = _assign_lanes(raw_events)
        if int(lane_count) > int(max_lane_count):
            continue
        answer_event_ids = tuple(
            event.event_id
            for event in raw_events
            if not event.is_reference and int(event.duration_slots) > int(ref_duration)
        )
        return tuple(raw_events), tuple(answer_event_ids), str(raw_events[0].event_id)

    raise ValueError("failed to sample a readable longer-than-reference schedule")


def _sample_unique_optimal_variant(
    *,
    instance_seed: int,
    total_slots: int,
    params: Mapping[str, Any],
    event_labels: Sequence[str],
    maximum_non_overlapping_support: Sequence[int],
) -> Tuple[Tuple[_RawEvent, ...], Tuple[str, ...]]:
    """Sample one schedule with a unique maximum-size non-overlapping subset."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.maximum_non_overlapping_count")
    feasible_support = [
        int(value)
        for value in maximum_non_overlapping_support
        if 2 <= int(value) and ((2 * int(value)) - 1) <= len(event_labels)
    ]
    if not feasible_support:
        raise ValueError("maximum_non_overlapping_support must contain feasible values whose witness set fits the label pool")
    answer_value = int(
        feasible_support[
            int(_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:maximum_non_overlapping_count") % len(feasible_support))
        ]
    )

    for _ in range(400):
        backbone_durations = [int(rng.choice((1, 2, 2, 3))) for _ in range(int(answer_value))]
        chain_length = int(sum(backbone_durations))
        if int(chain_length) >= int(total_slots):
            continue
        start_slot = int(rng.randint(0, int(total_slots - chain_length)))
        raw_events: List[_RawEvent] = []
        backbone_event_ids: List[str] = []
        cursor = int(start_slot)
        for index, duration in enumerate(backbone_durations):
            event = _build_raw_event(str(event_labels[index]), int(cursor), int(cursor + duration))
            raw_events.append(event)
            backbone_event_ids.append(str(event.event_id))
            cursor += int(duration)

        distractor_offset = int(answer_value)
        for boundary_index in range(int(answer_value - 1)):
            left_event = raw_events[int(boundary_index)]
            right_event = raw_events[int(boundary_index + 1)]
            start_candidate = int(max(int(left_event.start_slot), int(left_event.end_slot) - 1))
            end_candidate = int(min(int(total_slots), max(int(right_event.start_slot) + 1, int(right_event.end_slot))))
            if int(end_candidate) <= int(start_candidate):
                end_candidate = int(start_candidate + 2)
            distractor = _build_raw_event(
                str(event_labels[distractor_offset + boundary_index]),
                int(start_candidate),
                int(min(int(total_slots), int(end_candidate))),
            )
            raw_events.append(distractor)

        return tuple(raw_events), tuple(backbone_event_ids)

    raise ValueError("failed to sample a unique-optimal non-overlapping schedule")


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one concrete single-day planner query from balanced supports."""

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
        supported=SUPPORTED_TEMPORAL_SCHEDULE_SCENE_VARIANTS,
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

    start_hour = int(params.get("start_hour", group_default(_GEN_DEFAULTS, "start_hour", _DEFAULTS.start_hour)))
    end_hour = int(params.get("end_hour", group_default(_GEN_DEFAULTS, "end_hour", _DEFAULTS.end_hour)))
    slot_minutes = int(params.get("slot_minutes", group_default(_GEN_DEFAULTS, "slot_minutes", _DEFAULTS.slot_minutes)))
    if int(end_hour) <= int(start_hour):
        raise ValueError("end_hour must be greater than start_hour for schedule tasks")
    if int(slot_minutes) <= 0 or (60 % int(slot_minutes)) != 0:
        raise ValueError("slot_minutes must be a positive divisor of 60 for schedule tasks")
    total_slots = int(((int(end_hour) - int(start_hour)) * 60) // int(slot_minutes))
    max_lane_count = int(params.get("max_lane_count", group_default(_GEN_DEFAULTS, "max_lane_count", _DEFAULTS.max_lane_count)))
    if int(max_lane_count) <= 0:
        raise ValueError("max_lane_count must be positive for schedule tasks")

    event_count_support = _resolve_int_support(params, "event_count_support", _DEFAULTS.event_count_support)
    overlap_count_support = _resolve_int_support(params, "overlap_count_support", _DEFAULTS.overlap_count_support)
    longer_than_count_support = _resolve_int_support(params, "longer_than_count_support", _DEFAULTS.longer_than_count_support)
    maximum_non_overlapping_support = _resolve_int_support(
        params,
        "maximum_non_overlapping_support",
        _DEFAULTS.maximum_non_overlapping_support,
    )
    reference_duration_slots_support = _resolve_int_support(
        params,
        "reference_duration_slots_support",
        _DEFAULTS.reference_duration_slots_support,
    )
    duration_slots_support = _resolve_int_support(params, "duration_slots_support", _DEFAULTS.duration_slots_support)
    day_label_support = _resolve_str_support(params, "day_label_support", _DEFAULTS.day_label_support)
    event_label_pool = _resolve_str_support(params, "event_label_pool", _DEFAULTS.event_label_pool)
    day_label = str(
        day_label_support[
            int(_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:day_label") % len(day_label_support))
        ]
    )

    if str(task_variant) == "overlap_count":
        raw_events, answer_event_ids, reference_event_id = _sample_overlap_variant(
            instance_seed=int(instance_seed),
            total_slots=int(total_slots),
            params=params,
            event_labels=tuple(event_label_pool),
            event_count_support=tuple(event_count_support),
            overlap_count_support=tuple(overlap_count_support),
            reference_duration_slots_support=tuple(reference_duration_slots_support),
            duration_slots_support=tuple(duration_slots_support),
            max_lane_count=int(max_lane_count),
        )
    elif str(task_variant) == "longer_than_reference_count":
        raw_events, answer_event_ids, reference_event_id = _sample_longer_variant(
            instance_seed=int(instance_seed),
            total_slots=int(total_slots),
            params=params,
            event_labels=tuple(event_label_pool),
            event_count_support=tuple(event_count_support),
            longer_than_count_support=tuple(longer_than_count_support),
            reference_duration_slots_support=tuple(reference_duration_slots_support),
            duration_slots_support=tuple(duration_slots_support),
            max_lane_count=int(max_lane_count),
        )
    else:
        raw_events, answer_event_ids = _sample_unique_optimal_variant(
            instance_seed=int(instance_seed),
            total_slots=int(total_slots),
            params=params,
            event_labels=tuple(event_label_pool),
            maximum_non_overlapping_support=tuple(maximum_non_overlapping_support),
        )
        reference_event_id = None

    scheduled_placeholder, lane_count = _assign_lanes(raw_events)
    if int(lane_count) > int(max_lane_count):
        raise ValueError("sampled schedule exceeds configured max_lane_count")
    rendered_events = _hydrate_event_minutes(
        scheduled_placeholder,
        {str(event.event_id): event for event in raw_events},
        start_hour=int(start_hour),
        slot_minutes=int(slot_minutes),
    )

    return _ResolvedQuery(
        task_variant=str(task_variant),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        accent_color_name=str(accent_color_name),
        day_label=str(day_label),
        title_text="Day Planner",
        start_hour=int(start_hour),
        end_hour=int(end_hour),
        slot_minutes=int(slot_minutes),
        max_lane_count=int(max_lane_count),
        event_count_support=tuple(int(value) for value in event_count_support),
        overlap_count_support=tuple(int(value) for value in overlap_count_support),
        longer_than_count_support=tuple(int(value) for value in longer_than_count_support),
        maximum_non_overlapping_support=tuple(int(value) for value in maximum_non_overlapping_support),
        raw_events=tuple(raw_events),
        rendered_events=tuple(rendered_events),
        event_count=len(raw_events),
        lane_count=int(lane_count),
        answer_value=len(answer_event_ids),
        answer_event_ids=tuple(str(value) for value in answer_event_ids),
        reference_event_id=(str(reference_event_id) if reference_event_id is not None else None),
        task_variant_probabilities=dict(task_variant_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        accent_color_name_probabilities=dict(accent_color_name_probabilities),
    )


def _build_object_description(*, task_variant: str, event_count: int) -> str:
    """Return the prompt-facing scene description for one schedule variant."""

    if str(task_variant) == "maximum_non_overlapping_count":
        return f"one single-day schedule with time labels and {int(event_count)} scheduled event blocks"
    return f"one single-day schedule with time labels, {int(event_count)} scheduled event blocks, and one highlighted reference event"


def _build_answer_hint(*, task_variant: str) -> str:
    """Return the variant-specific answer hint text."""

    if str(task_variant) == "overlap_count":
        return 'set "answer" to the integer count of events that overlap the reference event'
    if str(task_variant) == "longer_than_reference_count":
        return 'set "answer" to the integer count of events that are longer than the reference event'
    return 'set "answer" to the maximum number of non-overlapping events as an integer'


def _build_evidence_hint(*, task_variant: str) -> str:
    """Return the variant-specific evidence hint text."""

    if str(task_variant) == "maximum_non_overlapping_count":
        return 'set "evidence" to an array of bounding boxes [x1, y1, x2, y2] for the unique maximum-size non-overlapping event set'
    return 'set "evidence" to an array of bounding boxes [x1, y1, x2, y2] for all event blocks that satisfy the query'


@register_task
class TemporalScheduleDayPlannerTask:
    """Reason over one single-day planner with numeric overlap, duration, and optimization queries."""

    task_id = TASK_ID
    domain = "temporal"
    task_group = "schedule"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query = _resolve_query(int(instance_seed), params=params)
        render_params = resolve_schedule_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_values=asdict(_DEFAULTS),
        )
        schedule_theme = build_temporal_schedule_theme(
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
        rendered_scene: RenderedScheduleScene = render_day_schedule_scene(
            image,
            title_text=str(query.title_text),
            day_label_text=str(query.day_label),
            start_total_minutes=int(query.start_hour * 60),
            end_total_minutes=int(query.end_hour * 60),
            slot_minutes=int(query.slot_minutes),
            lane_count=int(query.lane_count),
            events=tuple(query.rendered_events),
            scene_variant=str(query.scene_variant),
            render_params=render_params,
            visual_theme=schedule_theme,
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
        raw_events_by_id = {str(event.event_id): event for event in query.raw_events}
        rendered_events_by_id = {str(event.event_id): event for event in query.rendered_events}

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            ("bundle_id", "task_family_key", "task_key"),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = _build_object_description(
            task_variant=str(query.task_variant),
            event_count=int(query.event_count),
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

        query_params: Dict[str, Any] = {
            "task_variant": str(query.task_variant),
            "scene_variant": str(query.scene_variant),
            "style_variant": str(query.style_variant),
            "accent_color_name": str(query.accent_color_name),
            "day_label": str(query.day_label),
            "start_hour": int(query.start_hour),
            "end_hour": int(query.end_hour),
            "slot_minutes": int(query.slot_minutes),
            "event_count": int(query.event_count),
            "lane_count": int(query.lane_count),
            "max_lane_count": int(query.max_lane_count),
            "event_count_support": [int(value) for value in query.event_count_support],
            "overlap_count_support": [int(value) for value in query.overlap_count_support],
            "longer_than_count_support": [int(value) for value in query.longer_than_count_support],
            "maximum_non_overlapping_support": [int(value) for value in query.maximum_non_overlapping_support],
            "answer_event_ids": [str(value) for value in query.answer_event_ids],
            "reference_event_id": str(query.reference_event_id) if query.reference_event_id is not None else None,
            "task_variant_probabilities": dict(query.task_variant_probabilities),
            "scene_variant_probabilities": dict(query.scene_variant_probabilities),
            "style_variant_probabilities": dict(query.style_variant_probabilities),
            "accent_color_name_probabilities": dict(query.accent_color_name_probabilities),
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "temporal_day_schedule",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(query.task_variant),
                    "scene_variant": str(query.scene_variant),
                    "style_variant": str(query.style_variant),
                    "accent_color_name": str(query.accent_color_name),
                    "day_label": str(query.day_label),
                    "reference_event_id": str(query.reference_event_id) if query.reference_event_id is not None else None,
                },
            },
            "query_spec": {
                "task_variant": str(query.task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": dict(query_params),
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(query.scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
                "schedule_style": {
                    "accent_color_name": str(query.accent_color_name),
                    "style_variant": str(query.style_variant),
                    "resolved_colors_rgb": {
                        "panel_fill": [int(value) for value in schedule_theme.panel_fill_rgb],
                        "panel_outline": [int(value) for value in schedule_theme.panel_outline_rgb],
                        "header_fill": [int(value) for value in schedule_theme.header_fill_rgb],
                        "header_text": [int(value) for value in schedule_theme.header_text_rgb],
                        "grid_line": [int(value) for value in schedule_theme.grid_line_rgb],
                        "minor_grid_line": [int(value) for value in schedule_theme.minor_grid_line_rgb],
                        "event_fill": [int(value) for value in schedule_theme.event_fill_rgb],
                        "event_outline": [int(value) for value in schedule_theme.event_outline_rgb],
                        "reference_fill": [int(value) for value in schedule_theme.reference_fill_rgb],
                        "reference_outline": [int(value) for value in schedule_theme.reference_outline_rgb],
                    },
                    "header_kind": str(schedule_theme.header_kind),
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
                "panel_bbox_px": [round(float(value), 3) for value in rendered_scene.panel_bbox_px],
                "title_text": str(rendered_scene.title_text),
                "day_label": str(query.day_label),
                "event_bboxes_by_id": {
                    str(event_id): [round(float(value), 3) for value in bbox]
                    for event_id, bbox in rendered_scene.event_bboxes_by_id.items()
                },
                "answer_event_ids": [str(value) for value in query.answer_event_ids],
                "reference_event_id": str(query.reference_event_id) if query.reference_event_id is not None else None,
            },
            "execution_trace": {
                "task_variant": str(query.task_variant),
                "scene_variant": str(query.scene_variant),
                "style_variant": str(query.style_variant),
                "accent_color_name": str(query.accent_color_name),
                "day_label": str(query.day_label),
                "start_hour": int(query.start_hour),
                "end_hour": int(query.end_hour),
                "slot_minutes": int(query.slot_minutes),
                "event_count": int(query.event_count),
                "lane_count": int(query.lane_count),
                "answer_value": int(query.answer_value),
                "answer_event_ids": [str(value) for value in query.answer_event_ids],
                "reference_event_id": str(query.reference_event_id) if query.reference_event_id is not None else None,
                "events": [
                    {
                        "event_id": str(raw_event.event_id),
                        "label": str(raw_event.label),
                        "start_slot": int(raw_event.start_slot),
                        "end_slot": int(raw_event.end_slot),
                        "duration_slots": int(raw_event.duration_slots),
                        "start_time": str(format_day_time_hhmm(int(rendered_events_by_id[str(raw_event.event_id)].start_total_minutes))),
                        "end_time": str(format_day_time_hhmm(int(rendered_events_by_id[str(raw_event.event_id)].end_total_minutes))),
                        "lane_index": int(rendered_events_by_id[str(raw_event.event_id)].lane_index),
                        "is_reference": bool(raw_event.is_reference),
                    }
                    for raw_event in query.raw_events
                ],
                "event_count_support": [int(value) for value in query.event_count_support],
                "overlap_count_support": [int(value) for value in query.overlap_count_support],
                "longer_than_count_support": [int(value) for value in query.longer_than_count_support],
                "maximum_non_overlapping_support": [int(value) for value in query.maximum_non_overlapping_support],
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

        reference_duration_slots = 0
        if query.reference_event_id is not None:
            reference_duration_slots = int(raw_events_by_id[str(query.reference_event_id)].duration_slots)
        event_count = int(query.event_count)
        lane_count = int(query.lane_count)
        touching_reference_count = 0
        if query.reference_event_id is not None:
            reference_interval = (
                int(raw_events_by_id[str(query.reference_event_id)].start_slot),
                int(raw_events_by_id[str(query.reference_event_id)].end_slot),
            )
            for raw_event in query.raw_events:
                if str(raw_event.event_id) == str(query.reference_event_id):
                    continue
                if int(raw_event.end_slot) == int(reference_interval[0]) or int(raw_event.start_slot) == int(reference_interval[1]):
                    touching_reference_count += 1
        close_duration_count = 0
        if query.reference_event_id is not None:
            for raw_event in query.raw_events:
                if str(raw_event.event_id) == str(query.reference_event_id):
                    continue
                if abs(int(raw_event.duration_slots) - int(reference_duration_slots)) <= 1:
                    close_duration_count += 1

        complexity = build_temporal_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "interval_reasoning": min(
                    1.0,
                    float(_INTERVAL_REASONING_BASE_BY_VARIANT[str(query.task_variant)])
                    + (0.14 * float(normalize_int_with_bounds(int(query.answer_value), [0, 5])))
                    + (0.12 * float(normalize_int_with_bounds(int(event_count), [3, 10]))),
                ),
                "visual_scan": min(
                    1.0,
                    float(_VISUAL_SCAN_BASE_BY_SCENE[str(query.scene_variant)])
                    + float(_VISUAL_SCAN_STYLE_BONUS[str(query.style_variant)])
                    + (0.18 * float(normalize_int_with_bounds(int(event_count), [3, 10])))
                    + (0.14 * float(normalize_int_with_bounds(int(lane_count), [1, int(query.max_lane_count)]))),
                ),
                "ambiguity": min(
                    1.0,
                    (
                        0.24
                        * float(
                            normalize_int_with_bounds(
                                int(
                                    touching_reference_count
                                    if str(query.task_variant) == "overlap_count"
                                    else close_duration_count if str(query.task_variant) == "longer_than_reference_count" else max(0, int(query.event_count - query.answer_value))
                                ),
                                [0, 5],
                            )
                        )
                    )
                    + (0.18 * float(normalize_int_with_bounds(int(query.answer_value), [0, 5])))
                    + (0.10 * float(normalize_int_with_bounds(int(lane_count), [1, int(query.max_lane_count)])))
                    + 0.08,
                ),
                "clutter": min(
                    1.0,
                    float(_CLUTTER_BASE_BY_SCENE[str(query.scene_variant)])
                    + float(_CLUTTER_STYLE_BONUS[str(query.style_variant)])
                    + (0.20 * float(normalize_int_with_bounds(int(event_count), [3, 10])))
                    + (0.16 * float(normalize_int_with_bounds(int(lane_count), [1, int(query.max_lane_count)]))),
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


__all__ = ["TemporalScheduleDayPlannerTask"]
