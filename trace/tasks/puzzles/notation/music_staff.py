"""Music-staff notation puzzle tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults
from ...shared.mcq import option_label_for_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.common import load_puzzle_task_defaults, projected_puzzle_bbox_evidence, resolve_puzzle_axis_variant
from ..shared.complexity import build_puzzle_complexity, clamp_unit_interval
from ..shared.music_notation_scene import (
    DEGREE_NAMES,
    LETTERS,
    MusicSceneSpec,
    OptionCard,
    Pitch,
    StaffBarline,
    StaffChord,
    StaffNote,
    StaffRange,
    StaffSymbol,
    StaffSystem,
    StaffText,
    build_interval_pitch,
    format_key_signature,
    format_pitch,
    interval_name,
    major_scale_pitch,
    pitch_from_staff_step,
    pitch_midi,
    render_music_scene,
    resolve_music_render_params,
)
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults


SCENE_ID = "music_staff"
PITCH_INTERVAL_TASK_ID = "task_puzzles__music_staff__pitch_interval_label"
KEY_SCALE_TASK_ID = "task_puzzles__music_staff__key_scale_label"
CHORD_HARMONY_TASK_ID = "task_puzzles__music_staff__chord_harmony_label"
DOMINANT_CHORD_COUNT_TASK_ID = "task_puzzles__music_staff__dominant_chord_count"
METER_RHYTHM_TASK_ID = "task_puzzles__music_staff__meter_rhythm_label"
DURATION_EQUIVALENCE_TASK_ID = "task_puzzles__music_staff__duration_equivalence_label"
BAR_COUNT_TASK_ID = "task_puzzles__music_staff__bar_count_value"

PITCH_INTERVAL_QUERY_IDS: Tuple[str, ...] = (
    "note_name_label",
    "interval_name_label",
    "same_pitch_truth_label",
    "transposed_pitch_truth_label",
)
KEY_SCALE_QUERY_IDS: Tuple[str, ...] = (
    "key_signature_label",
    "scale_validation_truth_label",
    "scale_degree_function_label",
)
CHORD_HARMONY_QUERY_IDS: Tuple[str, ...] = (
    "chord_quality_label",
    "roman_numeral_label",
    "chord_inversion_label",
)
DOMINANT_CHORD_COUNT_QUERY_IDS: Tuple[str, ...] = (
    "dominant_count_value",
)
METER_RHYTHM_QUERY_IDS: Tuple[str, ...] = (
    "time_signature_label",
    "meter_type_label",
    "articulation_symbol_label",
)
DURATION_EQUIVALENCE_QUERY_IDS: Tuple[str, ...] = ("duration_equivalence_label",)
BAR_COUNT_QUERY_IDS: Tuple[str, ...] = ("bar_count_value",)

SCENE_VARIANTS: Tuple[str, ...] = (
    "engraved_sheet",
    "exam_scan",
    "notebook_staff",
)
ANSWER_TRUE_FALSE: Tuple[str, str] = ("True", "False")
KEY_SIGNATURES: Dict[str, Tuple[Pitch, Tuple[str, ...]]] = {
    "C major": (Pitch("C", 4, 0), ()),
    "G major": (Pitch("G", 4, 0), ("#",)),
    "D major": (Pitch("D", 4, 0), ("#", "#")),
    "F major": (Pitch("F", 4, 0), ("b",)),
    "Bb major": (Pitch("B", 3, -1), ("b", "b")),
    "Eb major": (Pitch("E", 4, -1), ("b", "b", "b")),
}
DURATION_UNITS: Dict[str, int] = {
    "eighth note": 1,
    "quarter note": 2,
    "dotted quarter note": 3,
    "half note": 4,
    "dotted half note": 6,
    "whole note": 8,
}
TIME_SIGNATURE_UNITS: Dict[str, int] = {
    "2/4": 4,
    "3/4": 6,
    "4/4": 8,
}
METER_TYPE_SIGNATURES: Dict[str, str] = {
    "2/4": "simple",
    "3/4": "simple",
    "4/4": "simple",
    "6/8": "compound",
    "9/8": "compound",
}
CHORD_QUALITY_INTERVALS: Dict[str, Tuple[int, ...]] = {
    "major triad": (0, 4, 7),
    "minor triad": (0, 3, 7),
    "diminished triad": (0, 3, 6),
    "augmented triad": (0, 4, 8),
    "dominant seventh": (0, 4, 7, 10),
    "major seventh": (0, 4, 7, 11),
    "minor seventh": (0, 3, 7, 10),
    "half-diminished seventh": (0, 3, 6, 10),
}
CHORD_QUALITY_DEGREES: Dict[str, Tuple[int, ...]] = {
    "major triad": (1, 3, 5),
    "minor triad": (1, 3, 5),
    "diminished triad": (1, 3, 5),
    "augmented triad": (1, 3, 5),
    "dominant seventh": (1, 3, 5, 7),
    "major seventh": (1, 3, 5, 7),
    "minor seventh": (1, 3, 5, 7),
    "half-diminished seventh": (1, 3, 5, 7),
}
ROMAN_BY_DEGREE: Tuple[str, ...] = ("I", "ii", "iii", "IV", "V", "vi", "vii diminished")
QUALITY_BY_MAJOR_DEGREE: Tuple[str, ...] = (
    "major triad",
    "minor triad",
    "minor triad",
    "major triad",
    "major triad",
    "minor triad",
    "diminished triad",
)
INVERSION_NAMES: Tuple[str, ...] = ("root position", "first inversion", "second inversion", "third inversion")
ARTICULATION_SYMBOLS: Tuple[str, ...] = ("staccato", "tenuto", "accent", "fermata")


@dataclass(frozen=True)
class _Dataset:
    task_id: str
    query_id: str
    answer_type: str
    answer_value: int | str
    evidence_item_ids: Tuple[str, ...]
    spec: MusicSceneSpec
    scene_variant: str
    query_slots: Dict[str, str]
    metadata: Dict[str, Any]
    target_answer_support: Tuple[int | str, ...]


_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "notation")
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="notation", apply_prob=0.5)


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_puzzle_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _supported_queries(task_id: str) -> Tuple[str, ...]:
    if str(task_id) == PITCH_INTERVAL_TASK_ID:
        return PITCH_INTERVAL_QUERY_IDS
    if str(task_id) == KEY_SCALE_TASK_ID:
        return KEY_SCALE_QUERY_IDS
    if str(task_id) == CHORD_HARMONY_TASK_ID:
        return CHORD_HARMONY_QUERY_IDS
    if str(task_id) == DOMINANT_CHORD_COUNT_TASK_ID:
        return DOMINANT_CHORD_COUNT_QUERY_IDS
    if str(task_id) == METER_RHYTHM_TASK_ID:
        return METER_RHYTHM_QUERY_IDS
    if str(task_id) == DURATION_EQUIVALENCE_TASK_ID:
        return DURATION_EQUIVALENCE_QUERY_IDS
    if str(task_id) == BAR_COUNT_TASK_ID:
        return BAR_COUNT_QUERY_IDS
    raise ValueError(f"unsupported music-notation task_id: {task_id}")


def _resolve_scene_variant(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], *, instance_seed: int, task_id: str) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def _resolve_query_id(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], *, instance_seed: int, task_id: str) -> Tuple[str, Dict[str, float]]:
    effective_params = dict(params)
    if effective_params.get("query_id") is None:
        if effective_params.get("query_id") is not None:
            effective_params["query_id"] = str(effective_params["query_id"])
        elif effective_params.get("query_id") is not None:
            effective_params["query_id"] = str(effective_params["query_id"])
    return resolve_puzzle_axis_variant(
        params=effective_params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=_supported_queries(str(task_id)),
        task_id=str(task_id),
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        axis_namespace="query_id",
    )


def _title_for(scene_variant: str, text: str) -> str:
    prefix = {
        "engraved_sheet": "Staff Notation",
        "exam_scan": "Music Theory Item",
        "notebook_staff": "Notation Notes",
    }.get(str(scene_variant), "Staff Notation")
    return f"{prefix}: {text}"


def _key_signature_text(key_label: str) -> str:
    return format_key_signature(KEY_SIGNATURES[str(key_label)][1]) or "natural"


def _random_staff_pitch(rng, *, clef: str = "treble", low_step: int = -1, high_step: int = 9, allow_accidental: bool = True) -> Pitch:
    step = rng.randrange(int(low_step), int(high_step) + 1)
    accidental = rng.choice([-1, 0, 1]) if allow_accidental and rng.random() < 0.28 else 0
    return pitch_from_staff_step(str(clef), int(step), accidental=int(accidental))


def _build_chord(root: Pitch, quality: str, *, octave_shift: int = 0) -> Tuple[Pitch, ...]:
    intervals = CHORD_QUALITY_INTERVALS[str(quality)]
    degrees = CHORD_QUALITY_DEGREES[str(quality)]
    pitches = []
    for semitone, degree in zip(intervals, degrees):
        target_index = int(root.octave + int(octave_shift)) * 7 + LETTERS.index(str(root.letter)) + int(degree) - 1
        natural = Pitch(str(LETTERS[target_index % 7]), int(target_index // 7), 0)
        wanted = pitch_midi(root) + int(semitone)
        accidental = int(wanted - pitch_midi(natural))
        if accidental not in (-1, 0, 1):
            accidental = 0
        pitches.append(Pitch(str(natural.letter), int(natural.octave), int(accidental)))
    return tuple(pitches)


def _normalize_chord_for_staff(root: Pitch, quality: str) -> Tuple[Pitch, ...]:
    for octave in (3, 4):
        candidate_root = Pitch(str(root.letter), int(octave), int(root.accidental))
        pitches = _build_chord(candidate_root, str(quality))
        steps = [p.octave * 7 + LETTERS.index(p.letter) for p in pitches]
        if max(steps) - min(steps) <= 6:
            return pitches
    return _build_chord(Pitch(str(root.letter), 3, int(root.accidental)), str(quality))


def _invert_chord(pitches: Tuple[Pitch, ...], inversion_index: int) -> Tuple[Pitch, ...]:
    ordered = list(sorted(pitches, key=pitch_midi))
    for _ in range(int(inversion_index)):
        p = ordered.pop(0)
        ordered.append(Pitch(str(p.letter), int(p.octave) + 1, int(p.accidental)))
        ordered = list(sorted(ordered, key=pitch_midi))
    return tuple(ordered)


def _duration_partition(total_units: int, rng) -> Tuple[int, ...]:
    remaining = int(total_units)
    parts = []
    choices = (1, 2, 3, 4)
    while remaining > 0:
        valid = [value for value in choices if value <= remaining]
        if remaining in (1, 2, 3, 4):
            value = remaining if rng.random() < 0.55 else rng.choice(valid)
        else:
            value = rng.choice(valid)
        parts.append(int(value))
        remaining -= int(value)
    return tuple(parts)


def _duration_name(units: int) -> str:
    for name, value in DURATION_UNITS.items():
        if int(value) == int(units):
            return str(name)
    return f"{int(units)} units"


def _pitch_interval_dataset(query_id: str, *, instance_seed: int, scene_variant: str, params: Mapping[str, Any]) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{PITCH_INTERVAL_TASK_ID}.{query_id}.dataset")
    if str(query_id) == "note_name_label":
        pitch = _random_staff_pitch(rng, allow_accidental=True)
        note = StaffNote("target_note", 0, 2.0, pitch, accidental_visible=True, marker="A")
        answer = format_pitch(pitch, include_octave=False)
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "marked note"),
            systems=(StaffSystem(clef="treble", slot_count=5, notes=(note,)),),
        )
        return _Dataset(PITCH_INTERVAL_TASK_ID, str(query_id), "string", answer, ("target_note",), spec, str(scene_variant), {"target_marker": "A"}, {"target_pitch": format_pitch(pitch, include_octave=True)}, tuple())

    if str(query_id) == "interval_name_label":
        qualities = ("major", "minor", "perfect", "augmented", "diminished")
        for _ in range(80):
            root = _random_staff_pitch(rng, low_step=0, high_step=4, allow_accidental=False)
            number = rng.choice((2, 3, 4, 5, 6, 7, 8))
            quality = rng.choice(qualities)
            target = build_interval_pitch(root, int(number), str(quality))
            if target is None:
                continue
            if -2 <= (target.octave * 7 + LETTERS.index(target.letter)) - (Pitch("E", 4).octave * 7 + 2) <= 10:
                lower, upper = root, target
                break
        else:
            lower, upper = Pitch("C", 4), Pitch("E", 4)
        answer = interval_name(lower, upper)
        notes = (
            StaffNote("interval_note_1", 0, 1.8, lower, accidental_visible=True, marker="1"),
            StaffNote("interval_note_2", 0, 3.2, upper, accidental_visible=True, marker="2"),
        )
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "marked interval"),
            systems=(StaffSystem(clef="treble", slot_count=6, notes=notes),),
        )
        return _Dataset(PITCH_INTERVAL_TASK_ID, str(query_id), "string", answer, ("interval_note_1", "interval_note_2"), spec, str(scene_variant), {}, {"interval_answer": answer}, tuple())

    if str(query_id) == "same_pitch_truth_label":
        pitch_a = _random_staff_pitch(rng, low_step=0, high_step=8, allow_accidental=True)
        is_same = bool(rng.randrange(2))
        pitch_b = pitch_a if is_same else _random_staff_pitch(rng, low_step=0, high_step=8, allow_accidental=True)
        if not is_same and pitch_midi(pitch_a) == pitch_midi(pitch_b):
            pitch_b = Pitch("D", pitch_a.octave, 0)
        notes = (
            StaffNote("pitch_a", 0, 1.7, pitch_a, accidental_visible=True, marker="A"),
            StaffNote("pitch_b", 0, 3.4, pitch_b, accidental_visible=True, marker="B"),
        )
        answer = "True" if pitch_midi(pitch_a) == pitch_midi(pitch_b) else "False"
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "same pitch check"),
            systems=(StaffSystem(clef="treble", slot_count=6, notes=notes),),
        )
        return _Dataset(PITCH_INTERVAL_TASK_ID, str(query_id), "string", answer, ("pitch_a", "pitch_b"), spec, str(scene_variant), {}, {"pitch_a": format_pitch(pitch_a, include_octave=True), "pitch_b": format_pitch(pitch_b, include_octave=True)}, ANSWER_TRUE_FALSE)

    interval = rng.choice((3, 4, 5))
    lower = _random_staff_pitch(rng, low_step=0, high_step=4, allow_accidental=False)
    expected = build_interval_pitch(lower, int(interval), "perfect" if interval in (4, 5) else "major") or Pitch("E", 4)
    shown = expected if bool(rng.randrange(2)) else Pitch(str(expected.letter), int(expected.octave), int(expected.accidental) + (1 if expected.accidental <= 0 else -1))
    answer = "True" if pitch_midi(shown) == pitch_midi(expected) else "False"
    notes = (
        StaffNote("source_note", 0, 1.7, lower, accidental_visible=True, marker="A"),
        StaffNote("transposed_note", 0, 3.5, shown, accidental_visible=True, marker="B"),
    )
    spec = MusicSceneSpec(
        title=_title_for(scene_variant, "transposition check"),
        systems=(StaffSystem(clef="treble", slot_count=6, notes=notes),),
    )
    return _Dataset(PITCH_INTERVAL_TASK_ID, str(query_id), "string", answer, ("source_note", "transposed_note"), spec, str(scene_variant), {"interval_name": interval_name(lower, expected)}, {"expected_pitch": format_pitch(expected, include_octave=True), "shown_pitch": format_pitch(shown, include_octave=True)}, ANSWER_TRUE_FALSE)


def _key_scale_dataset(query_id: str, *, instance_seed: int, scene_variant: str, params: Mapping[str, Any]) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{KEY_SCALE_TASK_ID}.{query_id}.dataset")
    visible_key_labels = tuple(key for key in KEY_SIGNATURES if key != "C major")
    key_label = rng.choice(visible_key_labels)
    root = KEY_SIGNATURES[key_label][0]
    key_text = _key_signature_text(key_label)
    if str(query_id) == "key_signature_label":
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "key signature"),
            systems=(StaffSystem(clef="treble", slot_count=3, key_signature=key_text, key_signature_id="key_signature"),),
        )
        return _Dataset(KEY_SCALE_TASK_ID, str(query_id), "string", key_label, ("key_signature",), spec, str(scene_variant), {}, {"key_label": key_label}, tuple(KEY_SIGNATURES.keys()))

    if str(query_id) == "scale_validation_truth_label":
        correct = rng.random() < 0.68
        notes = []
        altered_index = rng.randrange(1, 7)
        for degree in range(1, 8):
            pitch = major_scale_pitch(root, degree)
            if not correct and degree == altered_index:
                pitch = Pitch(str(pitch.letter), int(pitch.octave), int(pitch.accidental) + (1 if pitch.accidental <= 0 else -1))
            notes.append(StaffNote(f"scale_note_{degree}", 0, 0.9 + degree * 0.75, pitch, accidental_visible=True))
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "major scale check"),
            systems=(StaffSystem(clef="treble", slot_count=8, key_signature=key_text, key_signature_id="key_signature", notes=tuple(notes)),),
        )
        answer = "True" if correct else "False"
        return _Dataset(
            KEY_SCALE_TASK_ID,
            str(query_id),
            "string",
            answer,
            tuple(["key_signature", *[n.item_id for n in notes]]),
            spec,
            str(scene_variant),
            {"target_key": key_label},
            {
                "is_correct_scale": bool(correct),
                "correct_scale_probability": 0.68,
                "altered_index": int(altered_index) if not correct else None,
            },
            ANSWER_TRUE_FALSE,
        )

    degree = rng.randrange(1, 8)
    pitch = major_scale_pitch(root, degree)
    note = StaffNote("degree_note", 0, 2.5, pitch, accidental_visible=True, marker="A")
    spec = MusicSceneSpec(
        title=_title_for(scene_variant, "scale degree"),
        systems=(StaffSystem(clef="treble", slot_count=5, key_signature=key_text, key_signature_id="key_signature", notes=(note,)),),
    )
    answer = DEGREE_NAMES[int(degree) - 1]
    return _Dataset(KEY_SCALE_TASK_ID, str(query_id), "string", answer, ("key_signature", "degree_note"), spec, str(scene_variant), {"target_key": key_label, "target_marker": "A"}, {"degree_1based": int(degree), "note": format_pitch(pitch, include_octave=True)}, DEGREE_NAMES)


def _chord_harmony_dataset(query_id: str, *, instance_seed: int, scene_variant: str, params: Mapping[str, Any]) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{CHORD_HARMONY_TASK_ID}.{query_id}.dataset")
    root = rng.choice((Pitch("C", 4), Pitch("D", 4), Pitch("E", 4), Pitch("F", 4), Pitch("G", 4), Pitch("A", 4)))
    if str(query_id) == "chord_quality_label":
        quality = rng.choice(tuple(CHORD_QUALITY_INTERVALS.keys()))
        chord = StaffChord("target_chord", 0, 2.4, _normalize_chord_for_staff(root, quality), marker="A", accidental_visible=True)
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "chord quality"),
            systems=(StaffSystem(clef="treble", slot_count=5, chords=(chord,)),),
        )
        return _Dataset(CHORD_HARMONY_TASK_ID, str(query_id), "string", quality, ("target_chord",), spec, str(scene_variant), {"target_marker": "A"}, {"root": format_pitch(root), "quality": quality}, tuple(CHORD_QUALITY_INTERVALS.keys()))

    if str(query_id) == "roman_numeral_label":
        key_label = rng.choice(("G major", "F major"))
        key_root = KEY_SIGNATURES[key_label][0]
        degree = rng.randrange(1, 8)
        chord_root = major_scale_pitch(key_root, degree)
        quality = QUALITY_BY_MAJOR_DEGREE[degree - 1]
        chord = StaffChord("target_chord", 0, 2.5, _normalize_chord_for_staff(chord_root, quality), marker="A", accidental_visible=True)
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "roman numeral"),
            systems=(StaffSystem(clef="treble", slot_count=5, key_signature=_key_signature_text(key_label), key_signature_id="key_signature", chords=(chord,)),),
        )
        answer = ROMAN_BY_DEGREE[degree - 1]
        return _Dataset(CHORD_HARMONY_TASK_ID, str(query_id), "string", answer, ("key_signature", "target_chord"), spec, str(scene_variant), {"target_key": key_label, "target_marker": "A"}, {"degree_1based": int(degree), "quality": quality}, ROMAN_BY_DEGREE)

    if str(query_id) == "chord_inversion_label":
        quality = rng.choice(("major triad", "minor triad", "dominant seventh", "major seventh"))
        base = _normalize_chord_for_staff(root, quality)
        max_inv = min(len(base) - 1, 3)
        inversion = rng.randrange(0, max_inv + 1)
        chord = StaffChord("target_chord", 0, 2.5, _invert_chord(base, inversion), marker="A", accidental_visible=True)
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "chord inversion"),
            systems=(StaffSystem(clef="treble", slot_count=5, chords=(chord,)),),
        )
        answer = INVERSION_NAMES[inversion]
        return _Dataset(CHORD_HARMONY_TASK_ID, str(query_id), "string", answer, ("target_chord",), spec, str(scene_variant), {"target_marker": "A"}, {"quality": quality, "inversion_index": int(inversion)}, INVERSION_NAMES[: max_inv + 1])

    key_label = rng.choice(("G major", "F major"))
    key_root = KEY_SIGNATURES[key_label][0]
    chord_count = 6
    dominant_positions = set(rng.sample(range(chord_count), rng.randrange(1, 4)))
    chords = []
    evidence = ["key_signature"]
    for idx in range(chord_count):
        degree = 5 if idx in dominant_positions else rng.choice((1, 2, 3, 4, 6))
        chord_root = major_scale_pitch(key_root, degree)
        quality = QUALITY_BY_MAJOR_DEGREE[degree - 1]
        item_id = f"chord_{idx + 1}"
        chords.append(StaffChord(item_id, 0, 1.0 + idx * 0.9, _normalize_chord_for_staff(chord_root, quality), marker=str(idx + 1), accidental_visible=True))
        if degree == 5:
            evidence.append(item_id)
    spec = MusicSceneSpec(
        title=_title_for(scene_variant, "dominant count"),
        systems=(StaffSystem(clef="treble", slot_count=8, key_signature=_key_signature_text(key_label), key_signature_id="key_signature", chords=tuple(chords)),),
    )
    answer = len(dominant_positions)
    return _Dataset(CHORD_HARMONY_TASK_ID, str(query_id), "integer", int(answer), tuple(evidence), spec, str(scene_variant), {"target_key": key_label}, {"dominant_positions": sorted(int(v) + 1 for v in dominant_positions)}, tuple(range(1, 5)))


def _meter_rhythm_dataset(query_id: str, *, instance_seed: int, scene_variant: str, params: Mapping[str, Any]) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{METER_RHYTHM_TASK_ID}.{query_id}.dataset")
    if str(query_id) == "time_signature_label":
        sig = rng.choice(tuple(TIME_SIGNATURE_UNITS.keys()))
        units = TIME_SIGNATURE_UNITS[sig]
        parts = _duration_partition(units, rng)
        notes = [StaffNote(f"rhythm_note_{idx}", 0, 1.0 + idx * 0.82, Pitch("B", 4), duration_units=part, filled=part <= 3, dotted=part in (3, 6)) for idx, part in enumerate(parts, start=1)]
        bar_range = StaffRange("target_bar", 0, 0.6, 1.0 + len(parts) * 0.82, "one bar")
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "time signature"),
            systems=(StaffSystem(clef="treble", slot_count=7, notes=tuple(notes), ranges=(bar_range,)),),
        )
        return _Dataset(METER_RHYTHM_TASK_ID, str(query_id), "string", sig, tuple(["target_bar", *[n.item_id for n in notes]]), spec, str(scene_variant), {}, {"duration_units": int(units), "parts": list(parts)}, tuple(TIME_SIGNATURE_UNITS.keys()))

    if str(query_id) == "bar_count_value":
        sig = rng.choice(("2/4", "3/4", "4/4"))
        bar_count = rng.randrange(3, 8)
        notes = []
        barlines = [StaffBarline("barline_0", 0, 0.6)]
        ranges = []
        slot = 0.9
        for bar_index in range(bar_count):
            parts = _duration_partition(TIME_SIGNATURE_UNITS[sig], rng)
            start_slot = slot - 0.25
            for part in parts:
                notes.append(StaffNote(f"bar_{bar_index + 1}_note_{len(notes) + 1}", 0, slot, Pitch("B", 4), duration_units=part, filled=part <= 3, dotted=part in (3, 6)))
                slot += 0.45
            ranges.append(StaffRange(f"bar_{bar_index + 1}", 0, start_slot, slot - 0.18, str(bar_index + 1)))
            barlines.append(StaffBarline(f"barline_{bar_index + 1}", 0, slot))
            slot += 0.22
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "bar count"),
            systems=(StaffSystem(clef="treble", slot_count=max(9, int(slot) + 1), time_signature=sig, time_signature_id="time_signature", notes=tuple(notes), barlines=tuple(barlines), ranges=tuple(ranges)),),
        )
        return _Dataset(METER_RHYTHM_TASK_ID, str(query_id), "integer", int(bar_count), tuple(r.item_id for r in ranges), spec, str(scene_variant), {}, {"time_signature": sig}, tuple(range(3, 8)))

    if str(query_id) == "duration_equivalence_label":
        target_units = rng.choice((1, 2, 3, 4, 6, 8))
        option_units = [target_units]
        for value in (1, 2, 3, 4, 6, 8):
            if value != target_units:
                option_units.append(value)
            if len(option_units) == 4:
                break
        rng.shuffle(option_units)
        options = []
        answer_label = ""
        for idx, units in enumerate(option_units):
            label = option_label_for_index(idx)
            is_correct = int(units) == int(target_units)
            if is_correct:
                answer_label = label
            options.append(OptionCard(f"option_{label}", label, text=_duration_name(units), duration_units=int(units), is_correct=is_correct))
        target_note = StaffNote("target_duration", 0, 2.0, Pitch("B", 4), duration_units=target_units, filled=target_units <= 3, dotted=target_units in (3, 6), marker="A")
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "duration match"),
            systems=(StaffSystem(clef="treble", slot_count=4, notes=(target_note,)),),
            option_cards=tuple(options),
        )
        return _Dataset(METER_RHYTHM_TASK_ID, str(query_id), "string", answer_label, ("target_duration", f"option_{answer_label}"), spec, str(scene_variant), {"target_marker": "A"}, {"target_duration_units": int(target_units), "option_units": list(option_units)}, tuple(option_label_for_index(i) for i in range(len(options))))

    if str(query_id) == "meter_type_label":
        sig = rng.choice(tuple(METER_TYPE_SIGNATURES.keys()))
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "meter type"),
            systems=(StaffSystem(clef="treble", slot_count=4, time_signature=sig, time_signature_id="time_signature", notes=(StaffNote("sample_note", 0, 2.0, Pitch("B", 4)),)),),
        )
        answer = METER_TYPE_SIGNATURES[sig]
        return _Dataset(METER_RHYTHM_TASK_ID, str(query_id), "string", answer, ("time_signature",), spec, str(scene_variant), {}, {"time_signature": sig}, ("simple", "compound"))

    symbol = rng.choice(ARTICULATION_SYMBOLS)
    pitch = Pitch("B", 4)
    note = StaffNote("symbol_note", 0, 2.2, pitch, marker="A")
    spec = MusicSceneSpec(
        title=_title_for(scene_variant, "articulation"),
        systems=(StaffSystem(clef="treble", slot_count=5, notes=(note,), symbols=(StaffSymbol("target_symbol", 0, 2.2, pitch, symbol),)),),
    )
    return _Dataset(METER_RHYTHM_TASK_ID, str(query_id), "string", symbol, ("symbol_note", "target_symbol"), spec, str(scene_variant), {"target_marker": "A"}, {"symbol": symbol}, ARTICULATION_SYMBOLS)


def _build_dataset(task_id: str, query_id: str, *, instance_seed: int, scene_variant: str, params: Mapping[str, Any]) -> _Dataset:
    if str(task_id) == PITCH_INTERVAL_TASK_ID:
        return _pitch_interval_dataset(str(query_id), instance_seed=int(instance_seed), scene_variant=str(scene_variant), params=params)
    if str(task_id) == KEY_SCALE_TASK_ID:
        return _key_scale_dataset(str(query_id), instance_seed=int(instance_seed), scene_variant=str(scene_variant), params=params)
    if str(task_id) == CHORD_HARMONY_TASK_ID:
        return replace(
            _chord_harmony_dataset(str(query_id), instance_seed=int(instance_seed), scene_variant=str(scene_variant), params=params),
            task_id=str(task_id),
        )
    if str(task_id) == DOMINANT_CHORD_COUNT_TASK_ID:
        return replace(
            _chord_harmony_dataset(str(query_id), instance_seed=int(instance_seed), scene_variant=str(scene_variant), params=params),
            task_id=str(task_id),
        )
    if str(task_id) == METER_RHYTHM_TASK_ID:
        return replace(
            _meter_rhythm_dataset(str(query_id), instance_seed=int(instance_seed), scene_variant=str(scene_variant), params=params),
            task_id=str(task_id),
        )
    if str(task_id) == DURATION_EQUIVALENCE_TASK_ID:
        return replace(
            _meter_rhythm_dataset(str(query_id), instance_seed=int(instance_seed), scene_variant=str(scene_variant), params=params),
            task_id=str(task_id),
        )
    if str(task_id) == BAR_COUNT_TASK_ID:
        return replace(
            _meter_rhythm_dataset(str(query_id), instance_seed=int(instance_seed), scene_variant=str(scene_variant), params=params),
            task_id=str(task_id),
        )
    raise ValueError(f"unsupported music-notation task_id: {task_id}")


def _build_prompt(
    *,
    task_id: str,
    dataset: _Dataset,
    prompt_defaults: Mapping[str, Any],
    instance_seed: int,
) -> Tuple[str, Dict[str, str], Dict[str, Any]]:
    query_id = str(dataset.query_id)
    scene_variant = str(dataset.scene_variant)
    required_keys = (
        "bundle_id",
        "scene_key",
        "task_key",
        "json_output_contract",
        "json_output_contract_answer_only",
        f"object_description_{scene_variant}",
        f"answer_hint_{query_id}",
        f"evidence_hint_{query_id}",
        f"json_example_{query_id}",
        f"json_example_answer_only_{query_id}",
    )
    prompt_values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {task_id}")
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "evidence_hint": str(prompt_values[f"evidence_hint_{query_id}"]),
        "answer_hint": str(prompt_values[f"answer_hint_{query_id}"]),
        "json_example": str(prompt_values[f"json_example_{query_id}"]),
        "json_example_answer_only": str(prompt_values[f"json_example_answer_only_{query_id}"]),
        "target_key": str(dataset.query_slots.get("target_key", "")),
        "target_marker": str(dataset.query_slots.get("target_marker", "A")),
        "interval_name": str(dataset.query_slots.get("interval_name", "")),
    }
    prompt_selection = render_task_prompt_variants(
        domain="puzzles",
        task_group="notation",
        bundle_id=str(prompt_values["bundle_id"]),
        scene_key=str(prompt_values["scene_key"]),
        task_key=str(prompt_values["task_key"]),
        query_key=str(query_id),
        answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
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


class _PuzzlesNotationBaseTask:
    domain = "puzzles"
    task_group = "notation"
    default_dataset_enabled = True
    task_id: str

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        gen_defaults, render_defaults, prompt_defaults, complexity_weights = _load_defaults(str(self.task_id))
        query_id, query_probabilities = _resolve_query_id(params, gen_defaults, instance_seed=int(instance_seed), task_id=str(self.task_id))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, gen_defaults, instance_seed=int(instance_seed), task_id=str(self.task_id))
        last_error: Exception | None = None
        dataset: _Dataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_dataset(
                    str(self.task_id),
                    str(query_id),
                    instance_seed=int(instance_seed) + int(attempt_index),
                    scene_variant=str(scene_variant),
                    params=params,
                )
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate music-notation puzzle instance") from last_error

        render_params = resolve_music_render_params(params, render_defaults, instance_seed=int(instance_seed))
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.music_notation_background",
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered_scene = render_music_scene(
            background,
            spec=dataset.spec,
            render_params=render_params,
            scene_style=scene_style,
            instance_seed=int(instance_seed),
        )
        image, post_noise_meta = apply_post_image_noise(rendered_scene.image, instance_seed=int(instance_seed), params=params, default_config=POST_IMAGE_NOISE_DEFAULTS)
        prompt, prompt_variants, prompt_meta = _build_prompt(
            task_id=str(self.task_id),
            dataset=dataset,
            prompt_defaults=prompt_defaults,
            instance_seed=int(instance_seed),
        )
        evidence_projection = projected_puzzle_bbox_evidence(rendered_scene.item_bboxes, list(dataset.evidence_item_ids))
        evidence_bboxes = [[round(float(value), 3) for value in bbox] for bbox in evidence_projection["bbox_set"]]
        answer_gt = TypedValue(
            type=str(dataset.answer_type),
            value=int(dataset.answer_value) if str(dataset.answer_type) == "integer" else str(dataset.answer_value),
        )
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        query_params = {
            "query_id": str(dataset.query_id),
            "internal_query_id": str(dataset.query_id),
            "query_id_probabilities": {"default": 1.0},
            "internal_query_id_probabilities": dict(query_probabilities),
            "scene_id": SCENE_ID,
            "scene_variant": str(scene_variant),
            "scene_variant_probabilities": dict(scene_variant_probabilities),
            "target_answer_support": list(dataset.target_answer_support),
        }
        answer_value = int(dataset.answer_value) if str(dataset.answer_type) == "integer" else str(dataset.answer_value)
        trace_payload = {
            "scene_ir": {
                "scene_kind": SCENE_ID,
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "query_id": str(dataset.query_id),
                    "internal_query_id": str(dataset.query_id),
                    "scene_id": SCENE_ID,
                    "scene_variant": str(scene_variant),
                    "answer_value": answer_value,
                },
            },
            "query_spec": {
                "query_id": str(dataset.query_id),
                "internal_query_id": str(dataset.query_id),
                "template_id": str(prompt_meta["bundle_id"]),
                "prompt_variant": dict(prompt_meta["prompt_variant"]),
                "prompt_variant_active_key": str(prompt_meta["prompt_variant_active_key"]),
                "prompt_variants": dict(prompt_meta["prompt_variants_for_trace"]),
                "params": dict(query_params),
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "scene_style": dict(scene_style_meta),
                "music_style": dict(rendered_scene.style_metadata),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "unit_size_jitter": dict(render_params.unit_size_jitter),
                "layout_jitter": dict(rendered_scene.layout_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bboxes.items()},
                "evidence_source": "item_bboxes_px",
                "layout_jitter": dict(rendered_scene.layout_jitter),
            }, render_params.unit_size_jitter),
            "execution_trace": {
                **dict(query_params),
                "answer_value": answer_value,
                "answer_type": str(dataset.answer_type),
                "evidence_item_ids": [str(item) for item in dataset.evidence_item_ids],
                "notation_metadata": dict(dataset.metadata),
                "question_format": str(dataset.query_id),
            },
            "witness_symbolic": {"type": "bbox_set", "value": list(evidence_bboxes)},
            "projected_evidence": {"type": "bbox_set", "bbox_set": list(evidence_bboxes), "value": list(evidence_bboxes)},
            "answer_gt": answer_gt.to_dict(),
            "evidence_gt": evidence_gt.to_dict(),
        }
        complexity = build_puzzle_complexity(
            weights=complexity_weights,
            components={
                "visual_scan": clamp_unit_interval(len(rendered_scene.entities) / 18.0),
                "reasoning_load": _reasoning_load(str(dataset.query_id)),
                "scene_variant_load": {"engraved_sheet": 0.18, "exam_scan": 0.28, "notebook_staff": 0.24}.get(str(scene_variant), 0.2),
            },
        )
        trace_payload["complexity"] = complexity.to_dict()
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query_id),
            prompt_variants=dict(prompt_variants),
        )


def _reasoning_load(query_id: str) -> float:
    return {
        "note_name_label": 0.22,
        "interval_name_label": 0.48,
        "same_pitch_truth_label": 0.34,
        "transposed_pitch_truth_label": 0.52,
        "key_signature_label": 0.28,
        "scale_validation_truth_label": 0.56,
        "scale_degree_function_label": 0.42,
        "chord_quality_label": 0.50,
        "roman_numeral_label": 0.62,
        "chord_inversion_label": 0.58,
        "dominant_count_value": 0.70,
        "time_signature_label": 0.42,
        "bar_count_value": 0.30,
        "duration_equivalence_label": 0.38,
        "meter_type_label": 0.26,
        "articulation_symbol_label": 0.24,
    }.get(str(query_id), 0.4)


@register_task
class PuzzlesNotationPitchIntervalLabelTask(_PuzzlesNotationBaseTask):
    """Read pitches, intervals, and transposition relationships on a staff."""

    task_id = PITCH_INTERVAL_TASK_ID


@register_task
class PuzzlesNotationKeyScaleLabelTask(_PuzzlesNotationBaseTask):
    """Read key signatures, scales, and scale-degree functions."""

    task_id = KEY_SCALE_TASK_ID


@register_task
class PuzzlesNotationChordHarmonyLabelTask(_PuzzlesNotationBaseTask):
    """Read chord quality, inversion, and roman-numeral harmony cues."""

    task_id = CHORD_HARMONY_TASK_ID


@register_task
class PuzzlesNotationDominantChordCountTask(_PuzzlesNotationBaseTask):
    """Count dominant chords in a visible harmonic context."""

    task_id = DOMINANT_CHORD_COUNT_TASK_ID


@register_task
class PuzzlesNotationMeterRhythmLabelTask(_PuzzlesNotationBaseTask):
    """Read meter and rhythm notation labels."""

    task_id = METER_RHYTHM_TASK_ID


@register_task
class PuzzlesNotationDurationEquivalenceLabelTask(_PuzzlesNotationBaseTask):
    """Match a marked duration to the image-visible option card with the same value."""

    task_id = DURATION_EQUIVALENCE_TASK_ID


@register_task
class PuzzlesNotationBarCountValueTask(_PuzzlesNotationBaseTask):
    """Count visible bars in a staff excerpt."""

    task_id = BAR_COUNT_TASK_ID
