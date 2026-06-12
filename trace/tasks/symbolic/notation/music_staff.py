"""Music-staff notation symbolic tasks."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults
from ...shared.mcq import option_label_for_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.common import load_symbolic_task_defaults, projected_symbolic_bbox_annotation, resolve_symbolic_axis_variant
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
from ..shared.scene_style import make_symbolic_scene_background, resolve_symbolic_scene_style
from ..shared.unit_size_jitter import with_symbolic_unit_size_jitter
from ..shared.visual_defaults import load_symbolic_noise_defaults


SCENE_ID = "music_staff"
PITCH_NAMESPACE_ID = "symbolic_music_staff_pitch_namespace"
KEY_SCALE_NAMESPACE_ID = "symbolic_music_staff_key_scale_namespace"
METER_RHYTHM_NAMESPACE_ID = "symbolic_music_staff_meter_rhythm_namespace"
NOTE_NAME_TASK_ID = "task_symbolic__music_staff__note_name_label"
INTERVAL_NAME_TASK_ID = "task_symbolic__music_staff__interval_name_label"
SAME_PITCH_PAIR_COUNT_TASK_ID = "task_symbolic__music_staff__same_pitch_pair_count"
TRANSPOSED_PITCH_PAIR_COUNT_TASK_ID = "task_symbolic__music_staff__transposed_pitch_pair_count"
KEY_SIGNATURE_TASK_ID = "task_symbolic__music_staff__key_signature_label"
SCALE_VALIDATION_COUNT_TASK_ID = "task_symbolic__music_staff__scale_validation_count"
SCALE_DEGREE_FUNCTION_TASK_ID = "task_symbolic__music_staff__scale_degree_function_label"
CHORD_HARMONY_TASK_ID = "task_symbolic__music_staff__chord_harmony_label"
DOMINANT_CHORD_COUNT_TASK_ID = "task_symbolic__music_staff__dominant_chord_count"
METER_TYPE_TASK_ID = "task_symbolic__music_staff__meter_type_count"
ARTICULATION_SYMBOL_TASK_ID = "task_symbolic__music_staff__articulation_symbol_label"
DURATION_EQUIVALENCE_TASK_ID = "task_symbolic__music_staff__duration_equivalence_label"
BAR_COUNT_TASK_ID = "task_symbolic__music_staff__bar_count_value"

PITCH_INTERVAL_QUERY_IDS: Tuple[str, ...] = (
    "note_name_label",
    "interval_name_label",
    "same_pitch_pair_count",
    "transposed_pitch_pair_count",
)
KEY_SCALE_QUERY_IDS: Tuple[str, ...] = (
    "key_signature_label",
    "scale_validation_count",
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
    "meter_type_count",
    "articulation_symbol_label",
)
DURATION_EQUIVALENCE_QUERY_IDS: Tuple[str, ...] = ("duration_equivalence_label",)
BAR_COUNT_QUERY_IDS: Tuple[str, ...] = ("bar_count_value",)

SCENE_VARIANTS: Tuple[str, ...] = (
    "engraved_sheet",
    "exam_scan",
    "notebook_staff",
)
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
SIMPLE_METER_SIGNATURES: Tuple[str, ...] = ("2/4", "3/4", "4/4")
COMPOUND_METER_SIGNATURES: Tuple[str, ...] = ("6/8", "9/8")
METER_TYPE_SIGNATURE_UNITS: Dict[str, int] = {
    **TIME_SIGNATURE_UNITS,
    "6/8": 6,
    "9/8": 9,
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
    annotation_item_ids: Tuple[str, ...]
    spec: MusicSceneSpec
    scene_variant: str
    query_slots: Dict[str, str]
    metadata: Dict[str, Any]
    target_answer_support: Tuple[int | str, ...]


_TASK_GROUP_DEFAULTS = get_scene_defaults("symbolic", "notation")
POST_IMAGE_NOISE_DEFAULTS = load_symbolic_noise_defaults(scene_id="notation", apply_prob=0.5)


def _load_defaults(task_id: str) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, float]]:
    return load_symbolic_task_defaults(_TASK_GROUP_DEFAULTS, task_id=str(task_id))


def _supported_queries(task_id: str) -> Tuple[str, ...]:
    if str(task_id) == NOTE_NAME_TASK_ID:
        return ("note_name_label",)
    if str(task_id) == INTERVAL_NAME_TASK_ID:
        return ("interval_name_label",)
    if str(task_id) == SAME_PITCH_PAIR_COUNT_TASK_ID:
        return ("same_pitch_pair_count",)
    if str(task_id) == TRANSPOSED_PITCH_PAIR_COUNT_TASK_ID:
        return ("transposed_pitch_pair_count",)
    if str(task_id) == KEY_SIGNATURE_TASK_ID:
        return ("key_signature_label",)
    if str(task_id) == SCALE_VALIDATION_COUNT_TASK_ID:
        return ("scale_validation_count",)
    if str(task_id) == SCALE_DEGREE_FUNCTION_TASK_ID:
        return ("scale_degree_function_label",)
    if str(task_id) == CHORD_HARMONY_TASK_ID:
        return CHORD_HARMONY_QUERY_IDS
    if str(task_id) == DOMINANT_CHORD_COUNT_TASK_ID:
        return DOMINANT_CHORD_COUNT_QUERY_IDS
    if str(task_id) == METER_TYPE_TASK_ID:
        return ("meter_type_count",)
    if str(task_id) == ARTICULATION_SYMBOL_TASK_ID:
        return ("articulation_symbol_label",)
    if str(task_id) == DURATION_EQUIVALENCE_TASK_ID:
        return DURATION_EQUIVALENCE_QUERY_IDS
    if str(task_id) == BAR_COUNT_TASK_ID:
        return BAR_COUNT_QUERY_IDS
    raise ValueError(f"unsupported music-notation task_id: {task_id}")


def _resolve_scene_variant(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], *, instance_seed: int, task_id: str) -> Tuple[str, Dict[str, float]]:
    return resolve_symbolic_axis_variant(
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
        if effective_params.get("query_variant") is not None:
            effective_params["query_id"] = str(effective_params["query_variant"])
    return resolve_symbolic_axis_variant(
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


def _resolve_chord_inversion(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    return resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=INVERSION_NAMES,
        task_id=CHORD_HARMONY_TASK_ID,
        explicit_key="chord_inversion",
        weights_key="chord_inversion_weights",
        balance_flag_key="balanced_chord_inversion_sampling",
        axis_namespace="chord_inversion",
    )


def _resolve_dominant_count_target(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    min_value = int(params.get("target_answer_min", gen_defaults.get("target_answer_min", 0)))
    max_value = int(params.get("target_answer_max", gen_defaults.get("target_answer_max", 4)))
    if int(min_value) > int(max_value):
        raise ValueError("target_answer_min must be <= target_answer_max for dominant chord count")
    support = tuple(range(int(min_value), int(max_value) + 1))
    selected, probabilities = resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=[str(value) for value in support],
        task_id=DOMINANT_CHORD_COUNT_TASK_ID,
        explicit_key="target_answer",
        weights_key="target_answer_weights",
        balance_flag_key="balanced_target_answer_sampling",
        axis_namespace="target_answer",
    )
    return int(selected), tuple(int(value) for value in support), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_same_pitch_count_target(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    min_value = int(params.get("target_answer_min", gen_defaults.get("target_answer_min", 0)))
    max_value = int(params.get("target_answer_max", gen_defaults.get("target_answer_max", 4)))
    if int(min_value) > int(max_value):
        raise ValueError("target_answer_min must be <= target_answer_max for same-pitch pair count")
    support = tuple(range(int(min_value), int(max_value) + 1))
    selected, probabilities = resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=[str(value) for value in support],
        task_id=SAME_PITCH_PAIR_COUNT_TASK_ID,
        explicit_key="target_answer",
        weights_key="target_answer_weights",
        balance_flag_key="balanced_target_answer_sampling",
        axis_namespace="target_answer",
    )
    return int(selected), tuple(int(value) for value in support), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_transposed_pitch_count_target(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    min_value = int(params.get("target_answer_min", gen_defaults.get("target_answer_min", 0)))
    max_value = int(params.get("target_answer_max", gen_defaults.get("target_answer_max", 4)))
    if int(min_value) > int(max_value):
        raise ValueError("target_answer_min must be <= target_answer_max for transposed-pitch pair count")
    support = tuple(range(int(min_value), int(max_value) + 1))
    selected, probabilities = resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=[str(value) for value in support],
        task_id=TRANSPOSED_PITCH_PAIR_COUNT_TASK_ID,
        explicit_key="target_answer",
        weights_key="target_answer_weights",
        balance_flag_key="balanced_target_answer_sampling",
        axis_namespace="target_answer",
    )
    return int(selected), tuple(int(value) for value in support), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_scale_validation_count_target(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    min_value = int(params.get("target_answer_min", gen_defaults.get("target_answer_min", 0)))
    max_value = int(params.get("target_answer_max", gen_defaults.get("target_answer_max", 4)))
    if int(min_value) > int(max_value):
        raise ValueError("target_answer_min must be <= target_answer_max for scale validation count")
    support = tuple(range(int(min_value), int(max_value) + 1))
    selected, probabilities = resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=[str(value) for value in support],
        task_id=SCALE_VALIDATION_COUNT_TASK_ID,
        explicit_key="target_answer",
        weights_key="target_answer_weights",
        balance_flag_key="balanced_target_answer_sampling",
        axis_namespace="target_answer",
    )
    return int(selected), tuple(int(value) for value in support), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_meter_type_count_target(params: Mapping[str, Any], gen_defaults: Mapping[str, Any], *, instance_seed: int) -> Tuple[int, Tuple[int, ...], Dict[str, float]]:
    min_value = int(params.get("target_answer_min", gen_defaults.get("target_answer_min", 0)))
    max_value = int(params.get("target_answer_max", gen_defaults.get("target_answer_max", 4)))
    if int(min_value) > int(max_value):
        raise ValueError("target_answer_min must be <= target_answer_max for meter type count")
    support = tuple(range(int(min_value), int(max_value) + 1))
    selected, probabilities = resolve_symbolic_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=[str(value) for value in support],
        task_id=METER_TYPE_TASK_ID,
        explicit_key="target_answer",
        weights_key="target_answer_weights",
        balance_flag_key="balanced_target_answer_sampling",
        axis_namespace="target_answer",
    )
    return int(selected), tuple(int(value) for value in support), {str(key): float(value) for key, value in probabilities.items()}


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


def _pitch_interval_dataset(
    query_id: str,
    *,
    instance_seed: int,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{PITCH_NAMESPACE_ID}.{query_id}.dataset")
    if str(query_id) == "note_name_label":
        pitch = _random_staff_pitch(rng, allow_accidental=True)
        note = StaffNote("target_note", 0, 2.0, pitch, accidental_visible=True, marker="A")
        answer = format_pitch(pitch, include_octave=False)
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "marked note"),
            systems=(StaffSystem(clef="treble", slot_count=5, notes=(note,)),),
        )
        return _Dataset(PITCH_NAMESPACE_ID, str(query_id), "string", answer, ("target_note",), spec, str(scene_variant), {"target_marker": "A"}, {"target_pitch": format_pitch(pitch, include_octave=True)}, tuple())

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
        return _Dataset(PITCH_NAMESPACE_ID, str(query_id), "string", answer, ("interval_note_1", "interval_note_2"), spec, str(scene_variant), {}, {"interval_answer": answer}, tuple())

    if str(query_id) == "same_pitch_pair_count":
        pair_count = 4
        target_count, target_answer_support, target_answer_probabilities = _resolve_same_pitch_count_target(
            params,
            gen_defaults,
            instance_seed=int(instance_seed),
        )
        if int(target_count) > int(pair_count):
            raise ValueError("same-pitch target count cannot exceed shown pair count")
        target_indices = set(rng.sample(range(pair_count), int(target_count)))
        notes = []
        ranges = []
        annotation = []
        pair_records = []
        slot = 0.9
        for pair_index in range(pair_count):
            pitch_a = _random_staff_pitch(rng, low_step=0, high_step=8, allow_accidental=True)
            is_target = pair_index in target_indices
            if is_target:
                pitch_b = pitch_a
            else:
                for _attempt in range(80):
                    candidate = _random_staff_pitch(rng, low_step=0, high_step=8, allow_accidental=True)
                    if pitch_midi(candidate) != pitch_midi(pitch_a):
                        pitch_b = candidate
                        break
                else:
                    pitch_b = Pitch("D", int(pitch_a.octave), 0)
                    if pitch_midi(pitch_b) == pitch_midi(pitch_a):
                        pitch_b = Pitch("E", int(pitch_a.octave), 0)
            start_slot = float(slot - 0.25)
            note_a = StaffNote(f"pair_{pair_index + 1}_note_a", 0, float(slot), pitch_a, accidental_visible=True)
            note_b = StaffNote(f"pair_{pair_index + 1}_note_b", 0, float(slot + 0.48), pitch_b, accidental_visible=True)
            notes.extend([note_a, note_b])
            range_id = f"pair_{pair_index + 1}"
            ranges.append(StaffRange(range_id, 0, float(start_slot), float(slot + 0.72), str(pair_index + 1)))
            if is_target:
                annotation.append(range_id)
            pair_records.append(
                {
                    "pair_index_1based": int(pair_index + 1),
                    "pitch_a": format_pitch(pitch_a, include_octave=True),
                    "pitch_b": format_pitch(pitch_b, include_octave=True),
                    "same_pitch": bool(pitch_midi(pitch_a) == pitch_midi(pitch_b)),
                }
            )
            slot += 1.35
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "same pitch count"),
            systems=(StaffSystem(clef="treble", slot_count=max(8, int(slot) + 1), notes=tuple(notes), ranges=tuple(ranges)),),
        )
        return _Dataset(
            PITCH_NAMESPACE_ID,
            str(query_id),
            "integer",
            int(target_count),
            tuple(annotation),
            spec,
            str(scene_variant),
            {},
            {
                "pair_count": int(pair_count),
                "target_pair_indices_1based": [int(index) + 1 for index in sorted(target_indices)],
                "target_answer_probabilities": dict(target_answer_probabilities),
                "pairs": list(pair_records),
            },
            tuple(int(value) for value in target_answer_support),
        )

    if str(query_id) == "transposed_pitch_pair_count":
        pair_count = 4
        target_count, target_answer_support, target_answer_probabilities = _resolve_transposed_pitch_count_target(
            params,
            gen_defaults,
            instance_seed=int(instance_seed),
        )
        if int(target_count) > int(pair_count):
            raise ValueError("transposed-pitch target count cannot exceed shown pair count")
        interval_number = int(rng.choice((3, 4, 5)))
        interval_quality = "perfect" if interval_number in (4, 5) else "major"
        target_indices = set(rng.sample(range(pair_count), int(target_count)))
        notes = []
        ranges = []
        annotation = []
        pair_records = []
        slot = 0.9
        interval_label = ""
        for pair_index in range(pair_count):
            source = _random_staff_pitch(rng, low_step=0, high_step=4, allow_accidental=False)
            expected = build_interval_pitch(source, interval_number, interval_quality) or Pitch("E", 4)
            interval_label = interval_name(source, expected)
            is_target = pair_index in target_indices
            if is_target:
                shown = expected
            else:
                shown = Pitch(
                    str(expected.letter),
                    int(expected.octave),
                    int(expected.accidental) + (1 if int(expected.accidental) <= 0 else -1),
                )
                if pitch_midi(shown) == pitch_midi(expected):
                    shown = Pitch(str(expected.letter), int(expected.octave), int(expected.accidental) - 1)
            start_slot = float(slot - 0.25)
            note_a = StaffNote(f"pair_{pair_index + 1}_source", 0, float(slot), source, accidental_visible=True)
            note_b = StaffNote(f"pair_{pair_index + 1}_shown", 0, float(slot + 0.48), shown, accidental_visible=True)
            notes.extend([note_a, note_b])
            range_id = f"pair_{pair_index + 1}"
            ranges.append(StaffRange(range_id, 0, float(start_slot), float(slot + 0.72), str(pair_index + 1)))
            if is_target:
                annotation.append(range_id)
            pair_records.append(
                {
                    "pair_index_1based": int(pair_index + 1),
                    "source_pitch": format_pitch(source, include_octave=True),
                    "expected_pitch": format_pitch(expected, include_octave=True),
                    "shown_pitch": format_pitch(shown, include_octave=True),
                    "matches_target_interval": bool(pitch_midi(shown) == pitch_midi(expected)),
                }
            )
            slot += 1.35
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "transposition count"),
            systems=(StaffSystem(clef="treble", slot_count=max(8, int(slot) + 1), notes=tuple(notes), ranges=tuple(ranges)),),
        )
        return _Dataset(
            PITCH_NAMESPACE_ID,
            str(query_id),
            "integer",
            int(target_count),
            tuple(annotation),
            spec,
            str(scene_variant),
            {"interval_name": str(interval_label)},
            {
                "pair_count": int(pair_count),
                "target_pair_indices_1based": [int(index) + 1 for index in sorted(target_indices)],
                "target_answer_probabilities": dict(target_answer_probabilities),
                "pairs": list(pair_records),
            },
            tuple(int(value) for value in target_answer_support),
        )

    raise ValueError(f"unsupported pitch-interval query_id: {query_id}")


def _key_scale_dataset(
    query_id: str,
    *,
    instance_seed: int,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{KEY_SCALE_NAMESPACE_ID}.{query_id}.dataset")
    visible_key_labels = tuple(key for key in KEY_SIGNATURES if key != "C major")
    key_label = rng.choice(visible_key_labels)
    root = KEY_SIGNATURES[key_label][0]
    key_text = _key_signature_text(key_label)
    if str(query_id) == "key_signature_label":
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "key signature"),
            systems=(StaffSystem(clef="treble", slot_count=3, key_signature=key_text, key_signature_id="key_signature"),),
        )
        return _Dataset(KEY_SCALE_NAMESPACE_ID, str(query_id), "string", key_label, ("key_signature",), spec, str(scene_variant), {}, {"key_label": key_label}, tuple(KEY_SIGNATURES.keys()))

    if str(query_id) == "scale_validation_count":
        fragment_count = 4
        target_count, target_answer_support, target_answer_probabilities = _resolve_scale_validation_count_target(
            params,
            gen_defaults,
            instance_seed=int(instance_seed),
        )
        if int(target_count) > int(fragment_count):
            raise ValueError("scale-validation target count cannot exceed shown fragment count")
        target_indices = set(rng.sample(range(fragment_count), int(target_count)))
        notes = []
        ranges = []
        annotation = []
        fragment_records = []
        slot = 0.85
        for fragment_index in range(fragment_count):
            is_correct = fragment_index in target_indices
            start_slot = float(slot - 0.22)
            fragment_degrees = tuple(range(1, 6))
            altered_degree = rng.choice(fragment_degrees)
            fragment_note_ids = []
            for degree in fragment_degrees:
                pitch = major_scale_pitch(root, int(degree))
                if (not is_correct) and int(degree) == int(altered_degree):
                    pitch = Pitch(str(pitch.letter), int(pitch.octave), int(pitch.accidental) + (1 if pitch.accidental <= 0 else -1))
                note_id = f"fragment_{fragment_index + 1}_note_{degree}"
                fragment_note_ids.append(note_id)
                notes.append(StaffNote(note_id, 0, float(slot), pitch, accidental_visible=True))
                slot += 0.32
            range_id = f"fragment_{fragment_index + 1}"
            ranges.append(StaffRange(range_id, 0, float(start_slot), float(slot - 0.12), str(fragment_index + 1)))
            if is_correct:
                annotation.append(range_id)
            fragment_records.append(
                {
                    "fragment_index_1based": int(fragment_index + 1),
                    "is_correct_scale_fragment": bool(is_correct),
                    "degrees": [int(value) for value in fragment_degrees],
                    "altered_degree": None if is_correct else int(altered_degree),
                    "note_ids": list(fragment_note_ids),
                }
            )
            slot += 0.32
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "scale validation count"),
            systems=(
                StaffSystem(
                    clef="treble",
                    slot_count=max(8, int(slot) + 1),
                    key_signature=key_text,
                    key_signature_id="key_signature",
                    notes=tuple(notes),
                    ranges=tuple(ranges),
                ),
            ),
        )
        return _Dataset(
            KEY_SCALE_NAMESPACE_ID,
            str(query_id),
            "integer",
            int(target_count),
            tuple(annotation),
            spec,
            str(scene_variant),
            {"target_key": key_label},
            {
                "fragment_count": int(fragment_count),
                "target_fragment_indices_1based": [int(index) + 1 for index in sorted(target_indices)],
                "target_answer_probabilities": dict(target_answer_probabilities),
                "fragments": list(fragment_records),
            },
            tuple(int(value) for value in target_answer_support),
        )

    degree = rng.randrange(1, 8)
    pitch = major_scale_pitch(root, degree)
    note = StaffNote("degree_note", 0, 2.5, pitch, accidental_visible=True, marker="A")
    spec = MusicSceneSpec(
        title=_title_for(scene_variant, "scale degree"),
        systems=(StaffSystem(clef="treble", slot_count=5, key_signature=key_text, key_signature_id="key_signature", notes=(note,)),),
    )
    answer = DEGREE_NAMES[int(degree) - 1]
    return _Dataset(KEY_SCALE_NAMESPACE_ID, str(query_id), "string", answer, ("key_signature", "degree_note"), spec, str(scene_variant), {"target_key": key_label, "target_marker": "A"}, {"degree_1based": int(degree), "note": format_pitch(pitch, include_octave=True)}, DEGREE_NAMES)


def _chord_harmony_dataset(
    query_id: str,
    *,
    instance_seed: int,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> _Dataset:
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
        inversion_name, inversion_probabilities = _resolve_chord_inversion(params, gen_defaults, instance_seed=int(instance_seed))
        inversion = int(INVERSION_NAMES.index(str(inversion_name)))
        quality_support = ("dominant seventh", "major seventh") if inversion == 3 else ("major triad", "minor triad", "dominant seventh", "major seventh")
        quality = rng.choice(quality_support)
        base = _normalize_chord_for_staff(root, quality)
        chord = StaffChord("target_chord", 0, 2.5, _invert_chord(base, inversion), marker="A", accidental_visible=True)
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "chord inversion"),
            systems=(StaffSystem(clef="treble", slot_count=5, chords=(chord,)),),
        )
        answer = INVERSION_NAMES[inversion]
        return _Dataset(
            CHORD_HARMONY_TASK_ID,
            str(query_id),
            "string",
            answer,
            ("target_chord",),
            spec,
            str(scene_variant),
            {"target_marker": "A"},
            {
                "quality": quality,
                "quality_support": list(quality_support),
                "inversion_index": int(inversion),
                "chord_inversion_probabilities": dict(inversion_probabilities),
            },
            INVERSION_NAMES,
        )

    key_label = rng.choice(("G major", "F major"))
    key_root = KEY_SIGNATURES[key_label][0]
    chord_count = 6
    target_count, target_answer_support, target_answer_probabilities = _resolve_dominant_count_target(
        params,
        gen_defaults,
        instance_seed=int(instance_seed),
    )
    if int(target_count) > int(chord_count):
        raise ValueError("dominant chord target count cannot exceed shown chord count")
    dominant_positions = set(rng.sample(range(chord_count), int(target_count)))
    chords = []
    annotation = []
    for idx in range(chord_count):
        degree = 5 if idx in dominant_positions else rng.choice((1, 2, 3, 4, 6))
        chord_root = major_scale_pitch(key_root, degree)
        quality = QUALITY_BY_MAJOR_DEGREE[degree - 1]
        item_id = f"chord_{idx + 1}"
        chords.append(StaffChord(item_id, 0, 1.0 + idx * 0.9, _normalize_chord_for_staff(chord_root, quality), marker=str(idx + 1), accidental_visible=True))
        if degree == 5:
            annotation.append(item_id)
    spec = MusicSceneSpec(
        title=_title_for(scene_variant, "dominant count"),
        systems=(StaffSystem(clef="treble", slot_count=8, key_signature=_key_signature_text(key_label), key_signature_id="key_signature", chords=tuple(chords)),),
    )
    answer = len(dominant_positions)
    return _Dataset(
        CHORD_HARMONY_TASK_ID,
        str(query_id),
        "integer",
        int(answer),
        tuple(annotation),
        spec,
        str(scene_variant),
        {"target_key": key_label},
        {
            "dominant_positions": sorted(int(v) + 1 for v in dominant_positions),
            "target_answer_probabilities": dict(target_answer_probabilities),
        },
        tuple(int(value) for value in target_answer_support),
    )


def _meter_rhythm_dataset(
    query_id: str,
    *,
    instance_seed: int,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> _Dataset:
    rng = spawn_rng(int(instance_seed), f"{METER_RHYTHM_NAMESPACE_ID}.{query_id}.dataset")
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
        return _Dataset(METER_RHYTHM_NAMESPACE_ID, str(query_id), "integer", int(bar_count), tuple(r.item_id for r in ranges), spec, str(scene_variant), {}, {"time_signature": sig}, tuple(range(3, 8)))

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
        return _Dataset(METER_RHYTHM_NAMESPACE_ID, str(query_id), "string", answer_label, ("target_duration", f"option_{answer_label}"), spec, str(scene_variant), {"target_marker": "A"}, {"target_duration_units": int(target_units), "option_units": list(option_units)}, tuple(option_label_for_index(i) for i in range(len(options))))

    if str(query_id) == "meter_type_count":
        measure_count = 4
        target_meter_type = str(params.get("target_meter_type", rng.choice(("simple", "compound"))))
        if target_meter_type not in {"simple", "compound"}:
            raise ValueError("target_meter_type must be 'simple' or 'compound'")
        target_count, target_answer_support, target_answer_probabilities = _resolve_meter_type_count_target(
            params,
            gen_defaults,
            instance_seed=int(instance_seed),
        )
        if int(target_count) > int(measure_count):
            raise ValueError("meter type target count cannot exceed shown measure count")
        target_indices = set(rng.sample(range(measure_count), int(target_count)))
        notes = []
        texts = []
        barlines = [StaffBarline("barline_0", 0, 0.65)]
        ranges = []
        annotation = []
        measure_records = []
        slot = 0.95
        for measure_index in range(measure_count):
            is_target = measure_index in target_indices
            meter_type = target_meter_type if is_target else ("compound" if target_meter_type == "simple" else "simple")
            signature_pool = SIMPLE_METER_SIGNATURES if meter_type == "simple" else COMPOUND_METER_SIGNATURES
            sig = rng.choice(signature_pool)
            start_slot = float(slot - 0.28)
            texts.append(StaffText(f"measure_{measure_index + 1}_time_signature", 0, float(slot), str(sig), y_offset_steps=-4.7, bold=True))
            slot += 0.55
            parts = _duration_partition(METER_TYPE_SIGNATURE_UNITS[sig], rng)
            for part_index, part in enumerate(parts, start=1):
                notes.append(
                    StaffNote(
                        f"measure_{measure_index + 1}_note_{part_index}",
                        0,
                        float(slot),
                        Pitch("B", 4),
                        duration_units=int(part),
                        filled=int(part) <= 3,
                        dotted=int(part) in (3, 6),
                    )
                )
                slot += 0.36
            end_slot = float(slot - 0.14)
            range_id = f"measure_{measure_index + 1}"
            ranges.append(StaffRange(range_id, 0, float(start_slot), float(end_slot), str(measure_index + 1)))
            if is_target:
                annotation.append(range_id)
            barlines.append(StaffBarline(f"barline_{measure_index + 1}", 0, float(slot)))
            measure_records.append(
                {
                    "measure_index_1based": int(measure_index + 1),
                    "time_signature": str(sig),
                    "meter_type": str(meter_type),
                    "is_target": bool(is_target),
                }
            )
            slot += 0.25
        spec = MusicSceneSpec(
            title=_title_for(scene_variant, "meter count"),
            systems=(
                StaffSystem(
                    clef="treble",
                    slot_count=max(9, int(slot) + 1),
                    notes=tuple(notes),
                    texts=tuple(texts),
                    barlines=tuple(barlines),
                    ranges=tuple(ranges),
                ),
            ),
        )
        return _Dataset(
            METER_RHYTHM_NAMESPACE_ID,
            str(query_id),
            "integer",
            int(target_count),
            tuple(annotation),
            spec,
            str(scene_variant),
            {"target_meter_type": str(target_meter_type)},
            {
                "measure_count": int(measure_count),
                "target_meter_type": str(target_meter_type),
                "target_measure_indices_1based": [int(index) + 1 for index in sorted(target_indices)],
                "target_answer_probabilities": dict(target_answer_probabilities),
                "measures": list(measure_records),
            },
            tuple(int(value) for value in target_answer_support),
        )

    symbol = rng.choice(ARTICULATION_SYMBOLS)
    pitch = Pitch("B", 4)
    note = StaffNote("symbol_note", 0, 2.2, pitch, marker="A")
    spec = MusicSceneSpec(
        title=_title_for(scene_variant, "articulation"),
        systems=(StaffSystem(clef="treble", slot_count=5, notes=(note,), symbols=(StaffSymbol("target_symbol", 0, 2.2, pitch, symbol),)),),
    )
    return _Dataset(METER_RHYTHM_NAMESPACE_ID, str(query_id), "string", symbol, ("symbol_note", "target_symbol"), spec, str(scene_variant), {"target_marker": "A"}, {"symbol": symbol}, ARTICULATION_SYMBOLS)


def _build_dataset(
    task_id: str,
    source_namespace: str,
    query_id: str,
    *,
    instance_seed: int,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
) -> _Dataset:
    if str(source_namespace) == PITCH_NAMESPACE_ID:
        return replace(
            _pitch_interval_dataset(
                str(query_id),
                instance_seed=int(instance_seed),
                scene_variant=str(scene_variant),
                params=params,
                gen_defaults=gen_defaults,
            ),
            task_id=str(task_id),
        )
    if str(source_namespace) == KEY_SCALE_NAMESPACE_ID:
        return replace(
            _key_scale_dataset(
                str(query_id),
                instance_seed=int(instance_seed),
                scene_variant=str(scene_variant),
                params=params,
                gen_defaults=gen_defaults,
            ),
            task_id=str(task_id),
        )
    if str(source_namespace) == CHORD_HARMONY_TASK_ID:
        return replace(
            _chord_harmony_dataset(
                str(query_id),
                instance_seed=int(instance_seed),
                scene_variant=str(scene_variant),
                params=params,
                gen_defaults=gen_defaults,
            ),
            task_id=str(task_id),
        )
    if str(source_namespace) == DOMINANT_CHORD_COUNT_TASK_ID:
        return replace(
            _chord_harmony_dataset(
                str(query_id),
                instance_seed=int(instance_seed),
                scene_variant=str(scene_variant),
                params=params,
                gen_defaults=gen_defaults,
            ),
            task_id=str(task_id),
        )
    if str(source_namespace) == METER_RHYTHM_NAMESPACE_ID:
        return replace(
            _meter_rhythm_dataset(
                str(query_id),
                instance_seed=int(instance_seed),
                scene_variant=str(scene_variant),
                params=params,
                gen_defaults=gen_defaults,
            ),
            task_id=str(task_id),
        )
    if str(source_namespace) == DURATION_EQUIVALENCE_TASK_ID:
        return replace(
            _meter_rhythm_dataset(
                str(query_id),
                instance_seed=int(instance_seed),
                scene_variant=str(scene_variant),
                params=params,
                gen_defaults=gen_defaults,
            ),
            task_id=str(task_id),
        )
    if str(source_namespace) == BAR_COUNT_TASK_ID:
        return replace(
            _meter_rhythm_dataset(
                str(query_id),
                instance_seed=int(instance_seed),
                scene_variant=str(scene_variant),
                params=params,
                gen_defaults=gen_defaults,
            ),
            task_id=str(task_id),
        )
    raise ValueError(f"unsupported music-notation source namespace: {source_namespace}")


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
        f"annotation_hint_{query_id}",
        f"json_example_{query_id}",
        f"json_example_answer_only_{query_id}",
    )
    prompt_values = required_group_defaults(prompt_defaults, required_keys, context=f"prompt defaults for {task_id}")
    slots = {
        "object_description": str(prompt_values[f"object_description_{scene_variant}"]),
        "json_output_contract": str(prompt_values["json_output_contract"]),
        "json_output_contract_answer_only": str(prompt_values["json_output_contract_answer_only"]),
        "annotation_hint": str(prompt_values[f"annotation_hint_{query_id}"]),
        "answer_hint": str(prompt_values[f"answer_hint_{query_id}"]),
        "json_example": str(prompt_values[f"json_example_{query_id}"]),
        "json_example_answer_only": str(prompt_values[f"json_example_answer_only_{query_id}"]),
        "target_key": str(dataset.query_slots.get("target_key", "")),
        "target_marker": str(dataset.query_slots.get("target_marker", "A")),
        "interval_name": str(dataset.query_slots.get("interval_name", "")),
        "target_meter_type": str(dataset.query_slots.get("target_meter_type", "")),
    }
    prompt_selection = render_task_prompt_variants(
        domain="symbolic",
        scene_id="notation",
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


class _SymbolicBaseTask:
    domain = "symbolic"
    scene_id = "notation"
    default_dataset_enabled = True
    task_id: str
    source_namespace: str

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities = _resolve_query_id(params, gen_defaults, instance_seed=int(instance_seed), task_id=str(self.task_id))
        scene_variant, scene_variant_probabilities = _resolve_scene_variant(params, gen_defaults, instance_seed=int(instance_seed), task_id=str(self.task_id))
        last_error: Exception | None = None
        dataset: _Dataset | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            try:
                dataset = _build_dataset(
                    str(self.task_id),
                    str(self.source_namespace),
                    str(query_id),
                    instance_seed=int(instance_seed) + int(attempt_index),
                    scene_variant=str(scene_variant),
                    params=params,
                    gen_defaults=gen_defaults,
                )
                break
            except Exception as exc:
                last_error = exc
        if dataset is None:
            raise RuntimeError("failed to generate music-notation symbolic instance") from last_error

        render_params = resolve_music_render_params(params, render_defaults, instance_seed=int(instance_seed))
        scene_style, scene_style_meta = resolve_symbolic_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.music_notation_background",
        )
        background, background_meta = make_symbolic_scene_background(
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
        annotation_projection = projected_symbolic_bbox_annotation(rendered_scene.item_bboxes, list(dataset.annotation_item_ids))
        annotation_bboxes = [[round(float(value), 3) for value in bbox] for bbox in annotation_projection["bbox_set"]]
        answer_gt = TypedValue(
            type=str(dataset.answer_type),
            value=int(dataset.answer_value) if str(dataset.answer_type) == "integer" else str(dataset.answer_value),
        )
        annotation_gt = TypedValue(type="bbox_set", value=list(annotation_bboxes))
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
            "render_map": with_symbolic_unit_size_jitter({
                "image_id": "img0",
                "scene_bbox_px": list(rendered_scene.scene_bbox_px),
                "item_bboxes_px": {str(key): list(value) for key, value in rendered_scene.item_bboxes.items()},
                "annotation_source": "item_bboxes_px",
                "layout_jitter": dict(rendered_scene.layout_jitter),
            }, render_params.unit_size_jitter),
            "execution_trace": {
                **dict(query_params),
                "answer_value": answer_value,
                "answer_type": str(dataset.answer_type),
                "annotation_item_ids": [str(item) for item in dataset.annotation_item_ids],
                "notation_metadata": dict(dataset.metadata),
                "question_format": str(dataset.query_id),
            },
            "witness_symbolic": {"type": "bbox_set", "value": list(annotation_bboxes)},
            "projected_annotation": {"type": "bbox_set", "bbox_set": list(annotation_bboxes), "value": list(annotation_bboxes)},
            "answer_gt": answer_gt.to_dict(),
            "annotation_gt": annotation_gt.to_dict(),
        }
        return TaskOutput(
            prompt=str(prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(dataset.query_id),
            prompt_variants=dict(prompt_variants),
        )


def _reasoning_load(query_id: str) -> float:
    return {
        "note_name_label": 0.22,
        "interval_name_label": 0.48,
        "same_pitch_pair_count": 0.42,
        "transposed_pitch_pair_count": 0.52,
        "key_signature_label": 0.28,
        "scale_validation_count": 0.58,
        "scale_degree_function_label": 0.42,
        "chord_quality_label": 0.50,
        "roman_numeral_label": 0.62,
        "chord_inversion_label": 0.58,
        "dominant_count_value": 0.70,
        "bar_count_value": 0.30,
        "duration_equivalence_label": 0.38,
        "meter_type_count": 0.34,
        "articulation_symbol_label": 0.24,
    }.get(str(query_id), 0.4)


@register_task
class SymbolicNoteNameLabelTask(_SymbolicBaseTask):
    """Read the note name of a marked staff note."""

    task_id = NOTE_NAME_TASK_ID
    source_namespace = PITCH_NAMESPACE_ID
    supported_query_ids = ("note_name_label",)


@register_task
class SymbolicIntervalNameLabelTask(_SymbolicBaseTask):
    """Read the interval name between two staff notes."""

    task_id = INTERVAL_NAME_TASK_ID
    source_namespace = PITCH_NAMESPACE_ID
    supported_query_ids = ("interval_name_label",)


@register_task
class SymbolicSamePitchPairCountTask(_SymbolicBaseTask):
    """Count marked note pairs that show the same pitch."""

    task_id = SAME_PITCH_PAIR_COUNT_TASK_ID
    source_namespace = PITCH_NAMESPACE_ID
    supported_query_ids = ("same_pitch_pair_count",)


@register_task
class SymbolicTransposedPitchPairCountTask(_SymbolicBaseTask):
    """Count marked note pairs that match the requested transposition."""

    task_id = TRANSPOSED_PITCH_PAIR_COUNT_TASK_ID
    source_namespace = PITCH_NAMESPACE_ID
    supported_query_ids = ("transposed_pitch_pair_count",)


@register_task
class SymbolicKeySignatureLabelTask(_SymbolicBaseTask):
    """Read a visible key signature label."""

    task_id = KEY_SIGNATURE_TASK_ID
    source_namespace = KEY_SCALE_NAMESPACE_ID
    supported_query_ids = ("key_signature_label",)


@register_task
class SymbolicScaleValidationCountTask(_SymbolicBaseTask):
    """Count scale fragments that correctly fit the requested key."""

    task_id = SCALE_VALIDATION_COUNT_TASK_ID
    source_namespace = KEY_SCALE_NAMESPACE_ID
    supported_query_ids = ("scale_validation_count",)


@register_task
class SymbolicScaleDegreeFunctionLabelTask(_SymbolicBaseTask):
    """Read the scale-degree function of a marked note."""

    task_id = SCALE_DEGREE_FUNCTION_TASK_ID
    source_namespace = KEY_SCALE_NAMESPACE_ID
    supported_query_ids = ("scale_degree_function_label",)


@register_task
class SymbolicChordHarmonyLabelTask(_SymbolicBaseTask):
    """Read chord quality, inversion, and roman-numeral harmony cues."""

    task_id = CHORD_HARMONY_TASK_ID
    source_namespace = CHORD_HARMONY_TASK_ID
    supported_query_ids = CHORD_HARMONY_QUERY_IDS


@register_task
class SymbolicDominantChordCountTask(_SymbolicBaseTask):
    """Count dominant chords in a visible harmonic context."""

    task_id = DOMINANT_CHORD_COUNT_TASK_ID
    source_namespace = DOMINANT_CHORD_COUNT_TASK_ID
    supported_query_ids = DOMINANT_CHORD_COUNT_QUERY_IDS


@register_task
class SymbolicMeterTypeCountTask(_SymbolicBaseTask):
    """Count measures whose visible time signature has a requested meter type."""

    task_id = METER_TYPE_TASK_ID
    source_namespace = METER_RHYTHM_NAMESPACE_ID
    supported_query_ids = ("meter_type_count",)


@register_task
class SymbolicArticulationSymbolLabelTask(_SymbolicBaseTask):
    """Read the articulation symbol attached to a marked note."""

    task_id = ARTICULATION_SYMBOL_TASK_ID
    source_namespace = METER_RHYTHM_NAMESPACE_ID
    supported_query_ids = ("articulation_symbol_label",)


@register_task
class SymbolicDurationEquivalenceLabelTask(_SymbolicBaseTask):
    """Match a marked duration to the image-visible option card with the same value."""

    task_id = DURATION_EQUIVALENCE_TASK_ID
    source_namespace = DURATION_EQUIVALENCE_TASK_ID
    supported_query_ids = DURATION_EQUIVALENCE_QUERY_IDS


@register_task
class SymbolicBarCountValueTask(_SymbolicBaseTask):
    """Count visible bars in a staff excerpt."""

    task_id = BAR_COUNT_TASK_ID
    source_namespace = BAR_COUNT_TASK_ID
    supported_query_ids = BAR_COUNT_QUERY_IDS
