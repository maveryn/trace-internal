"""Shared rhythm-lane helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


SUPPORTED_RHYTHM_QUERY_IDS: Tuple[str, ...] = (
    "lane_hit_count",
    "lane_color_hit_count",
    "most_hits_lane_label",
    "earliest_hit_lane_label",
)
SUPPORTED_RHYTHM_SCENE_VARIANTS: Tuple[str, ...] = ("falling_notes",)
SUPPORTED_RHYTHM_STYLE_VARIANTS: Tuple[str, ...] = (
    "arcade",
    "neon",
    "paper",
    "dark",
    "pastel",
)
SUPPORTED_RHYTHM_COLOR_KEYS: Tuple[str, ...] = ("yellow", "cyan", "magenta", "green")


@dataclass(frozen=True)
class RhythmNote:
    """One visible falling rhythm note.

    `bottom_row` is one-indexed from the hit line upward. A note with
    `bottom_row == 1` reaches the hit line after one beat.
    """

    note_id: str
    lane_index: int
    bottom_row: int
    length: int
    color_key: str
    kind: str


@dataclass(frozen=True)
class RhythmSample:
    """Generated rhythm-lane scene state."""

    lane_count: int
    row_count: int
    beat_window: int
    mode: str
    scene_variant: str
    selected_lane_index: int | None
    selected_lane_label: str | None
    target_color_key: str | None
    answer: int
    notes: Tuple[RhythmNote, ...]
    annotation_entity_ids: Tuple[str, ...]
    construction_mode: str


def note_entity_id(index: int) -> str:
    """Return a stable note entity id."""

    return f"note_{int(index):03d}"


def lane_entity_id(lane: int) -> str:
    """Return a stable lane entity id."""

    return f"lane_{int(lane)}"


def lane_label(lane: int) -> str:
    """Return the image-facing numeric lane label."""

    return str(int(lane) + 1)


def note_hits_in_window(note: RhythmNote, beat_window: int) -> bool:
    """Return whether one note reaches the hit line within the beat window."""

    return int(note.bottom_row) <= int(beat_window)


def occupied_cells(note: RhythmNote) -> Tuple[int, ...]:
    """Return one-indexed row cells occupied by a note body."""

    return tuple(range(int(note.bottom_row), int(note.bottom_row) + max(1, int(note.length))))


def validate_rhythm_sample(sample: RhythmSample) -> None:
    """Validate generated answer/annotation against the active rhythm query."""

    if int(sample.lane_count) <= 0:
        raise ValueError("rhythm lane_count must be positive")
    if int(sample.row_count) <= 0:
        raise ValueError("rhythm row_count must be positive")
    if int(sample.beat_window) <= 0:
        raise ValueError("rhythm beat_window must be positive")
    if int(sample.beat_window) > int(sample.row_count):
        raise ValueError("rhythm beat_window cannot exceed row_count")

    note_ids = [str(note.note_id) for note in sample.notes]
    if len(note_ids) != len(set(note_ids)):
        raise ValueError("rhythm note ids must be unique")
    occupied: set[tuple[int, int]] = set()
    for note in sample.notes:
        if not (0 <= int(note.lane_index) < int(sample.lane_count)):
            raise ValueError("rhythm note lane out of range")
        if str(note.color_key) not in SUPPORTED_RHYTHM_COLOR_KEYS:
            raise ValueError("rhythm note color out of range")
        if int(note.length) <= 0:
            raise ValueError("rhythm note length must be positive")
        for row in occupied_cells(note):
            if not (1 <= int(row) <= int(sample.row_count)):
                raise ValueError("rhythm note row out of range")
            cell = (int(note.lane_index), int(row))
            if cell in occupied:
                raise ValueError("rhythm notes overlap within a lane")
            occupied.add(cell)

    known_entities = set(note_ids) | {lane_entity_id(lane) for lane in range(int(sample.lane_count))}
    if not set(sample.annotation_entity_ids) <= known_entities:
        raise ValueError("rhythm annotation references unknown entities")

    query = str(sample.mode)
    by_id = {str(note.note_id): note for note in sample.notes}
    annotation_ids = tuple(str(entity_id) for entity_id in sample.annotation_entity_ids)

    if query == "lane_hit_count":
        if sample.selected_lane_index is None:
            raise ValueError("lane_hit_count requires selected lane")
        expected_notes = tuple(
            note
            for note in sample.notes
            if int(note.lane_index) == int(sample.selected_lane_index)
            and note_hits_in_window(note, int(sample.beat_window))
        )
        expected_answer = len(expected_notes)
        expected_annotation = tuple(str(note.note_id) for note in expected_notes)
    elif query == "lane_color_hit_count":
        if sample.selected_lane_index is None or sample.target_color_key is None:
            raise ValueError("lane_color_hit_count requires selected lane and target color")
        expected_notes = tuple(
            note
            for note in sample.notes
            if int(note.lane_index) == int(sample.selected_lane_index)
            and str(note.color_key) == str(sample.target_color_key)
            and note_hits_in_window(note, int(sample.beat_window))
        )
        expected_answer = len(expected_notes)
        expected_annotation = tuple(str(note.note_id) for note in expected_notes)
    elif query == "most_hits_lane_label":
        hit_counts = []
        for lane in range(int(sample.lane_count)):
            hit_counts.append(
                sum(
                    1
                    for note in sample.notes
                    if int(note.lane_index) == int(lane) and note_hits_in_window(note, int(sample.beat_window))
                )
            )
        max_count = max(hit_counts)
        if hit_counts.count(max_count) != 1:
            raise ValueError("most_hits_lane_label requires a unique winning lane")
        winning_lane = int(hit_counts.index(max_count))
        expected_answer = int(lane_label(winning_lane))
        expected_notes = tuple(
            note
            for note in sample.notes
            if int(note.lane_index) == int(winning_lane) and note_hits_in_window(note, int(sample.beat_window))
        )
        expected_annotation = tuple(str(note.note_id) for note in expected_notes)
    elif query == "earliest_hit_lane_label":
        earliest_by_lane: list[int | None] = []
        for lane in range(int(sample.lane_count)):
            lane_times = [
                int(note.bottom_row)
                for note in sample.notes
                if int(note.lane_index) == int(lane) and note_hits_in_window(note, int(sample.beat_window))
            ]
            earliest_by_lane.append(min(lane_times) if lane_times else None)
        active_times = [time for time in earliest_by_lane if time is not None]
        if not active_times:
            raise ValueError("earliest_hit_lane_label requires at least one hitting note")
        earliest = min(int(time) for time in active_times)
        if sum(1 for time in earliest_by_lane if time == earliest) != 1:
            raise ValueError("earliest_hit_lane_label requires a unique earliest lane")
        winning_lane = next(index for index, time in enumerate(earliest_by_lane) if time == earliest)
        expected_answer = int(lane_label(winning_lane))
        earliest_notes = [
            note
            for note in sample.notes
            if int(note.lane_index) == int(winning_lane) and int(note.bottom_row) == int(earliest)
        ]
        if len(earliest_notes) != 1:
            raise ValueError("earliest_hit_lane_label requires one annotation note")
        expected_annotation = (str(earliest_notes[0].note_id),)
    else:
        raise ValueError(f"unsupported rhythm mode: {sample.mode}")

    if int(sample.answer) != int(expected_answer):
        raise ValueError("rhythm answer does not match active query")
    if set(annotation_ids) != set(expected_annotation):
        raise ValueError("rhythm annotation ids do not match active query")
    if any(entity_id not in by_id for entity_id in annotation_ids):
        raise ValueError("rhythm public annotation must reference notes")


__all__ = [
    "SUPPORTED_RHYTHM_COLOR_KEYS",
    "SUPPORTED_RHYTHM_QUERY_IDS",
    "SUPPORTED_RHYTHM_SCENE_VARIANTS",
    "SUPPORTED_RHYTHM_STYLE_VARIANTS",
    "RhythmNote",
    "RhythmSample",
    "lane_entity_id",
    "lane_label",
    "note_entity_id",
    "note_hits_in_window",
    "occupied_cells",
    "validate_rhythm_sample",
]
