"""Identity-free sampling primitives for cube-net puzzle cases."""

from __future__ import annotations

from string import ascii_uppercase
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.sampling import sample_without_replacement, uniform_choice
from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default, resolve_required_int_bounds

from .rules import (
    face_across_display_side,
    random_start_orientation,
    roll_orientation,
    sample_roll_path,
)
from .state import (
    DEFAULTS,
    FACE_IDS,
    FACE_LABEL_POOL,
    FaceOption,
    FaceRelationDataset,
    OPPOSITE_FACE,
    PathSequenceOption,
    ROLL_OFFSETS,
    RollingDataset,
    SIDE_OFFSETS,
    SurfacePathDataset,
)


def resolve_scene_int(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: int,
) -> int:
    """Resolve one integer from task params, scene defaults, then code fallback."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


def sample_face_labels(instance_seed: int, namespace: str) -> Dict[str, str]:
    """Assign unique visible labels to the six cube faces."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.face_labels")
    labels = sample_without_replacement(rng, list(FACE_LABEL_POOL), len(FACE_IDS))
    return {face: str(label) for face, label in zip(FACE_IDS, labels)}


def resolve_option_count(
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
) -> int:
    """Resolve the visible MCQ option count for cube-net answer panels."""

    option_count = resolve_scene_int(
        params,
        generation_defaults,
        "option_count",
        DEFAULTS.option_count,
    )
    if int(option_count) < 2 or int(option_count) > len(FACE_IDS):
        raise ValueError("cube-net option_count must be between 2 and the number of cube faces")
    return int(option_count)


def option_order(
    *,
    face_labels: Mapping[str, str],
    correct_face: str,
    option_count: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[Tuple[FaceOption, ...], str]:
    """Build one face-label option set with exactly one correct option."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.option_order")
    if int(option_count) < 2 or int(option_count) > len(FACE_IDS):
        raise ValueError("cube-net option_count must be between 2 and the number of cube faces")
    correct_index = int(rng.randrange(int(option_count)))
    distractors = [face for face in FACE_IDS if str(face) != str(correct_face)]
    rng.shuffle(distractors)
    ordered_faces = list(distractors[: max(0, int(option_count) - 1)])
    ordered_faces.insert(correct_index, str(correct_face))
    labels = tuple(ascii_uppercase[index] for index in range(len(ordered_faces)))
    options = tuple(
        FaceOption(
            option_label=str(label),
            face_id=str(face),
            face_label=str(face_labels[str(face)]),
        )
        for label, face in zip(labels, ordered_faces)
    )
    return options, str(labels[correct_index])


def _mutated_face_sequence(
    *,
    base_sequence: Sequence[str],
    rng: Any,
    protected_first: bool = True,
) -> Tuple[str, ...]:
    """Create one plausible sequence distractor by mutating a nonprotected face."""

    sequence = [str(face) for face in base_sequence]
    if not sequence:
        return tuple(sequence)
    start_index = 1 if bool(protected_first) and len(sequence) > 1 else 0
    index = int(rng.randrange(start_index, len(sequence)))
    choices = [face for face in FACE_IDS if str(face) != sequence[index]]
    sequence[index] = str(uniform_choice(rng, tuple(choices)))
    return tuple(sequence)


def surface_sequence_options(
    *,
    face_labels: Mapping[str, str],
    correct_sequence: Sequence[str],
    option_count: int,
    instance_seed: int,
    namespace: str,
) -> Tuple[Tuple[PathSequenceOption, ...], str]:
    """Build unique folded-path sequence options while preserving the start face."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.sequence_option_order")
    if int(option_count) < 2 or int(option_count) > len(FACE_IDS):
        raise ValueError("cube-net option_count must be between 2 and the number of cube faces")
    correct_index = int(rng.randrange(int(option_count)))
    sequences: list[tuple[str, ...]] = [tuple(str(face) for face in correct_sequence)]
    attempts = 0
    while len(sequences) < int(option_count) and attempts < 200:
        attempts += 1
        candidate = _mutated_face_sequence(base_sequence=correct_sequence, rng=rng)
        if candidate not in sequences:
            sequences.append(tuple(candidate))
    while len(sequences) < int(option_count):
        shuffled = list(str(face) for face in correct_sequence)
        rng.shuffle(shuffled)
        candidate = tuple(shuffled)
        if candidate not in sequences:
            sequences.append(candidate)
    correct = sequences.pop(0)
    rng.shuffle(sequences)
    sequences.insert(correct_index, correct)
    labels = tuple(ascii_uppercase[index] for index in range(len(sequences)))
    options = tuple(
        PathSequenceOption(
            option_label=str(label),
            face_ids=tuple(str(face) for face in sequence),
            face_labels=tuple(str(face_labels[str(face)]) for face in sequence),
        )
        for label, sequence in zip(labels, sequences)
    )
    return options, str(labels[correct_index])


def sample_face_relation_dataset(
    *,
    relation_kind: str,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> FaceRelationDataset:
    """Sample a face-relation puzzle without receiving public query identity."""

    option_count = resolve_option_count(params, generation_defaults)
    rng = spawn_rng(int(instance_seed), f"{namespace}.{relation_kind}.face_relation")
    face_labels = sample_face_labels(int(instance_seed), f"{namespace}.{relation_kind}")
    reference_face = str(uniform_choice(rng, FACE_IDS))
    marked_side: str | None = None
    if str(relation_kind) == "opposite":
        correct_face = str(OPPOSITE_FACE[reference_face])
    elif str(relation_kind) == "edge_neighbor":
        side_support = tuple(SIDE_OFFSETS.keys())
        marked_side = str(uniform_choice(rng, side_support))
        correct_face = face_across_display_side(reference_face, marked_side)
    else:
        raise ValueError(f"unsupported face relation kind: {relation_kind}")
    options, correct_label = option_order(
        face_labels=face_labels,
        correct_face=correct_face,
        option_count=int(option_count),
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.{relation_kind}",
    )
    return FaceRelationDataset(
        relation_kind=str(relation_kind),
        face_labels=dict(face_labels),
        reference_face=reference_face,
        marked_side=marked_side,
        correct_face=correct_face,
        options=tuple(options),
        correct_option_label=str(correct_label),
    )


def sample_surface_path_dataset(
    *,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> SurfacePathDataset:
    """Sample one folded-edge path and both public answer option families."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.surface_path")
    option_count = resolve_option_count(params, generation_defaults)
    step_min, step_max = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="surface_path_step_count_min",
        max_key="surface_path_step_count_max",
        fallback_min=DEFAULTS.surface_path_step_count_min,
        fallback_max=DEFAULTS.surface_path_step_count_max,
        context="cube-net folded path step count",
    )
    step_count = int(rng.randint(int(step_min), int(step_max)))
    face_labels = sample_face_labels(int(instance_seed), f"{namespace}.surface_path")
    sides = tuple(SIDE_OFFSETS.keys())
    sequence: list[str] = []
    path_sides: list[str] = []
    for attempt in range(80):
        start_face = str(uniform_choice(rng, FACE_IDS))
        current = str(start_face)
        sequence = [current]
        path_sides = []
        previous_side: str | None = None
        for _ in range(step_count):
            candidates = list(sides)
            if previous_side is not None and len(candidates) > 1:
                opposite = {
                    "top": "bottom",
                    "bottom": "top",
                    "left": "right",
                    "right": "left",
                }[previous_side]
                candidates = [side for side in candidates if side != opposite]
            side = str(uniform_choice(rng, tuple(candidates)))
            current = face_across_display_side(current, side)
            path_sides.append(side)
            sequence.append(current)
            previous_side = side
        if len(set(sequence)) >= min(3, len(sequence)) or attempt >= 12:
            break

    endpoint_options, endpoint_label = option_order(
        face_labels=face_labels,
        correct_face=str(sequence[-1]),
        option_count=int(option_count),
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.endpoint",
    )
    sequence_options, sequence_label = surface_sequence_options(
        face_labels=face_labels,
        correct_sequence=tuple(sequence),
        option_count=int(option_count),
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.sequence",
    )
    return SurfacePathDataset(
        face_labels=dict(face_labels),
        start_face=str(sequence[0]),
        path_sides=tuple(path_sides),
        face_sequence=tuple(sequence),
        endpoint_face=str(sequence[-1]),
        endpoint_options=tuple(endpoint_options),
        sequence_options=tuple(sequence_options),
        endpoint_correct_option_label=str(endpoint_label),
        sequence_correct_option_label=str(sequence_label),
    )


def sample_rolling_dataset(
    *,
    target_slot: str,
    params: Mapping[str, Any],
    generation_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
) -> RollingDataset:
    """Sample a cube roll path whose final orientation determines the answer."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.{target_slot}.rolling")
    option_count = resolve_option_count(params, generation_defaults)
    rows_min, rows_max = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="rolling_grid_rows_min",
        max_key="rolling_grid_rows_max",
        fallback_min=DEFAULTS.rolling_grid_rows_min,
        fallback_max=DEFAULTS.rolling_grid_rows_max,
        context="cube rolling grid row count",
    )
    cols_min, cols_max = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="rolling_grid_cols_min",
        max_key="rolling_grid_cols_max",
        fallback_min=DEFAULTS.rolling_grid_cols_min,
        fallback_max=DEFAULTS.rolling_grid_cols_max,
        context="cube rolling grid column count",
    )
    len_min, len_max = resolve_required_int_bounds(
        params,
        generation_defaults,
        min_key="rolling_path_length_min",
        max_key="rolling_path_length_max",
        fallback_min=DEFAULTS.rolling_path_length_min,
        fallback_max=DEFAULTS.rolling_path_length_max,
        context="cube rolling path length",
    )
    rows = int(rng.randint(int(rows_min), int(rows_max)))
    cols = int(rng.randint(int(cols_min), int(cols_max)))
    path_length = int(rng.randint(int(len_min), int(len_max)))
    if str(target_slot) not in {"top", "south", "east"}:
        raise ValueError(f"unsupported rolling target slot: {target_slot}")
    face_labels = sample_face_labels(int(instance_seed), f"{namespace}.{target_slot}")
    start_orientation: dict[str, str] = {}
    final_orientation: dict[str, str] = {}
    path_cells: tuple[tuple[int, int], ...] = ()
    path_dirs: tuple[str, ...] = ()
    for attempt in range(40):
        attempt_seed = int(instance_seed) + int(attempt)
        start_orientation = random_start_orientation(
            attempt_seed,
            f"{namespace}.{target_slot}",
        )
        path_cells, path_dirs = sample_roll_path(
            instance_seed=attempt_seed,
            rows=rows,
            cols=cols,
            length=path_length,
            namespace=f"{namespace}.{target_slot}",
        )
        final_orientation = dict(start_orientation)
        for direction in path_dirs:
            final_orientation = roll_orientation(final_orientation, str(direction))
        if str(final_orientation[str(target_slot)]) != str(start_orientation[str(target_slot)]):
            break
        if attempt >= 8:
            break
    correct_face = str(final_orientation[str(target_slot)])
    options, correct_label = option_order(
        face_labels=face_labels,
        correct_face=correct_face,
        option_count=int(option_count),
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.{target_slot}",
    )
    return RollingDataset(
        target_slot=str(target_slot),
        face_labels=dict(face_labels),
        start_orientation=dict(start_orientation),
        final_orientation=dict(final_orientation),
        grid_rows=int(rows),
        grid_cols=int(cols),
        path_cells=tuple(path_cells),
        path_directions=tuple(path_dirs),
        correct_face=correct_face,
        options=tuple(options),
        correct_option_label=str(correct_label),
    )


def face_option_specs(options: Sequence[FaceOption]) -> list[dict[str, str]]:
    """Convert face options to JSON-friendly trace records."""

    return [
        {
            "option_label": str(option.option_label),
            "face_id": str(option.face_id),
            "face_label": str(option.face_label),
        }
        for option in options
    ]


def sequence_option_specs(options: Sequence[PathSequenceOption]) -> list[dict[str, Any]]:
    """Convert sequence options to JSON-friendly trace records."""

    return [
        {
            "option_label": str(option.option_label),
            "face_ids": [str(face) for face in option.face_ids],
            "face_labels": [str(label) for label in option.face_labels],
        }
        for option in options
    ]


__all__ = [
    "face_option_specs",
    "option_order",
    "resolve_option_count",
    "resolve_scene_int",
    "sample_face_labels",
    "sample_face_relation_dataset",
    "sample_rolling_dataset",
    "sample_surface_path_dataset",
    "sequence_option_specs",
    "surface_sequence_options",
]
