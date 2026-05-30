"""Cube surface/net and rolling spatial puzzle tasks."""

from __future__ import annotations

from dataclasses import dataclass
from string import ascii_uppercase
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.drawing import draw_arrow, draw_centered_text, draw_rounded_rect
from ...shared.font_assets import font_asset_version, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, temporary_default_font_family
from ..shared.common import resolve_puzzle_axis_variant
from ..shared.complexity import build_puzzle_complexity, clamp_unit_interval, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.visual_defaults import load_puzzle_noise_defaults


INTERNAL_TASK_ID = "puzzles_spatial_cube_surface_net_internal"
FACE_RELATION_TASK_ID = "task_puzzles__cube_net__cube_net_face_relation_label"
ROLLING_RESULT_TASK_ID = "task_puzzles__cube_net__cube_rolling_result_label"
SURFACE_PATH_TASK_ID = "task_puzzles__cube_net__surface_net_path_label"
SCENE_ID = "cube_net"

FACE_RELATION_QUERY_IDS: Tuple[str, ...] = (
    "opposite_face_label",
    "marked_edge_neighbor_face_label",
)
ROLLING_QUERY_IDS: Tuple[str, ...] = (
    "final_top_face_label",
    "final_front_face_label",
    "final_right_face_label",
)
SURFACE_PATH_QUERY_IDS: Tuple[str, ...] = (
    "folded_path_endpoint_label",
    "folded_path_face_sequence_label",
)
SUPPORTED_QUERY_IDS: Tuple[str, ...] = FACE_RELATION_QUERY_IDS + ROLLING_QUERY_IDS + SURFACE_PATH_QUERY_IDS
SCENE_VARIANTS: Tuple[str, ...] = ("clean_net", "paper_model", "game_mat")

FACE_IDS: Tuple[str, ...] = ("U", "D", "F", "B", "L", "R")
OPPOSITE_FACE = {"U": "D", "D": "U", "F": "B", "B": "F", "L": "R", "R": "L"}
NORMAL_BY_FACE = {
    "U": (0, 1, 0),
    "D": (0, -1, 0),
    "F": (0, 0, 1),
    "B": (0, 0, -1),
    "L": (-1, 0, 0),
    "R": (1, 0, 0),
}
FACE_BY_NORMAL = {value: key for key, value in NORMAL_BY_FACE.items()}
NET_COORDS = {
    "B": (0, -1),
    "U": (0, 0),
    "L": (-1, 1),
    "F": (0, 1),
    "R": (1, 1),
    "D": (0, 2),
}
SIDE_OFFSETS = {
    "top": (0, -1),
    "right": (1, 0),
    "bottom": (0, 1),
    "left": (-1, 0),
}
ROLL_OFFSETS = {
    "N": (-1, 0),
    "E": (0, 1),
    "S": (1, 0),
    "W": (0, -1),
}
FACE_LABEL_POOL: Tuple[str, ...] = tuple("JKLMNPQRSTUVWXYZ23456789")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for cube surface puzzles."""

    canvas_width: int = 1100
    face_relation_canvas_height: int = 760
    rolling_canvas_height: int = 820
    option_count: int = 6
    net_cell_size_px: int = 86
    rolling_grid_rows_min: int = 5
    rolling_grid_rows_max: int = 6
    rolling_grid_cols_min: int = 5
    rolling_grid_cols_max: int = 6
    rolling_path_length_min: int = 4
    rolling_path_length_max: int = 7
    surface_path_step_count_min: int = 3
    surface_path_step_count_max: int = 5
    line_width_px: int = 3
    title_font_size_px: int = 22
    face_font_size_px: int = 31
    option_font_size_px: int = 28


@dataclass(frozen=True)
class FaceOption:
    """One answer option card."""

    option_label: str
    face_id: str
    face_label: str


@dataclass(frozen=True)
class PathSequenceOption:
    """One answer option for a folded surface path."""

    option_label: str
    face_ids: Tuple[str, ...]
    face_labels: Tuple[str, ...]


@dataclass(frozen=True)
class FaceRelationDataset:
    """Trace-ready cube net relation instance."""

    query_id: str
    face_labels: Dict[str, str]
    reference_face: str
    marked_side: str | None
    correct_face: str
    options: Tuple[FaceOption, ...]
    correct_option_label: str


@dataclass(frozen=True)
class RollingDataset:
    """Trace-ready cube rolling instance."""

    query_id: str
    face_labels: Dict[str, str]
    start_orientation: Dict[str, str]
    final_orientation: Dict[str, str]
    target_slot: str
    grid_rows: int
    grid_cols: int
    path_cells: Tuple[Tuple[int, int], ...]
    path_directions: Tuple[str, ...]
    correct_face: str
    options: Tuple[FaceOption, ...]
    correct_option_label: str


@dataclass(frozen=True)
class SurfacePathDataset:
    """Trace-ready folded surface path instance."""

    query_id: str
    face_labels: Dict[str, str]
    start_face: str
    path_sides: Tuple[str, ...]
    face_sequence: Tuple[str, ...]
    endpoint_face: str
    endpoint_options: Tuple[FaceOption, ...]
    sequence_options: Tuple[PathSequenceOption, ...]
    correct_option_label: str


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "spatial")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=INTERNAL_TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=INTERNAL_TASK_ID)
POST_IMAGE_NOISE_DEFAULTS = {
    **load_puzzle_noise_defaults(task_group="spatial", apply_prob=0.5),
    "apply_prob": 0.5,
    "edit_types": ["blur", "downsample", "jpeg", "noise"],
    "edit_count_range": [1, 1],
    "value_ranges": {
        "blur": {"radius": [0.08, 0.24]},
        "downsample": {"scale": [0.94, 0.98]},
        "jpeg": {"quality": [86.0, 95.0]},
        "noise": {"alpha": [0.006, 0.022]},
    },
}


def _sample_cube_surface_font(*, task_id: str, instance_seed: int, params: Mapping[str, Any]) -> str:
    """Sample one role-aware font family for all labels in a cube-net puzzle."""

    return sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.cube_surface_net.label_font",
        params={**dict(_RENDER_DEFAULTS), **dict(params)},
    )


def _font_trace_record(font_family: str) -> Dict[str, Any]:
    """Build trace metadata for the sampled cube-net label font."""

    return {
        "source": "global_font_pool",
        "font_family": str(font_family),
        "font_asset_version": font_asset_version(),
        "scope": "cube_net_panel_face_option_labels",
    }


def _round_evidence_bbox(bbox: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in bbox]


def _projected_keyed_bbox_map(evidence: Mapping[str, Sequence[float]]) -> Dict[str, Any]:
    value = {str(key): _round_evidence_bbox(bbox) for key, bbox in evidence.items()}
    return {
        "type": "keyed_bbox_map",
        "keyed_bbox_map": dict(value),
        "pixel_keyed_bbox_map": dict(value),
        "value": dict(value),
    }


def _task_params_for_query_id(params: Mapping[str, Any]) -> Dict[str, Any]:
    out = dict(params)
    source = out.get("query_id")
    if "query_id" not in out and source is not None and str(source) != "default":
        out["query_id"] = str(source)
    return out


def _resolve_axis(
    *,
    params: Mapping[str, Any],
    instance_seed: int,
    supported: Sequence[str],
    explicit_key: str,
    axis_namespace: str,
) -> Tuple[str, Dict[str, float]]:
    return resolve_puzzle_axis_variant(
        params=_task_params_for_query_id(params),
        gen_defaults=_GEN_DEFAULTS,
        instance_seed=int(instance_seed),
        supported_variants=tuple(str(item) for item in supported),
        task_id=INTERNAL_TASK_ID,
        explicit_key=str(explicit_key),
        weights_key=f"{axis_namespace}_weights",
        balance_flag_key=f"balanced_{axis_namespace}_sampling",
        axis_namespace=str(axis_namespace),
    )


def _get_int(params: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(params.get(str(key), group_default(_GEN_DEFAULTS, str(key), int(fallback))))


def _neg(vec: Sequence[int]) -> Tuple[int, int, int]:
    return (-int(vec[0]), -int(vec[1]), -int(vec[2]))


def _basis_across_side(
    *,
    normal: Tuple[int, int, int],
    up: Tuple[int, int, int],
    right: Tuple[int, int, int],
    side: str,
) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
    if str(side) == "top":
        return tuple(up), _neg(normal), tuple(right)
    if str(side) == "bottom":
        return _neg(up), tuple(normal), tuple(right)
    if str(side) == "right":
        return tuple(right), tuple(up), _neg(normal)
    if str(side) == "left":
        return _neg(right), tuple(up), tuple(normal)
    raise ValueError(f"unsupported side: {side}")


def _net_face_bases() -> Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]]:
    """Return face bases induced by the displayed cube net."""

    coord_to_face = {tuple(coord): str(face) for face, coord in NET_COORDS.items()}
    bases: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]] = {
        "F": ((0, 0, 1), (0, 1, 0), (1, 0, 0)),
    }
    queue = ["F"]
    while queue:
        face = queue.pop(0)
        normal, up, right = bases[str(face)]
        x, y = NET_COORDS[str(face)]
        for side, (dx, dy) in SIDE_OFFSETS.items():
            neighbor = coord_to_face.get((int(x + dx), int(y + dy)))
            if neighbor is None or neighbor in bases:
                continue
            bases[str(neighbor)] = _basis_across_side(normal=normal, up=up, right=right, side=str(side))
            queue.append(str(neighbor))
    if set(bases) != set(FACE_IDS):
        raise ValueError("cube net basis propagation did not cover all faces")
    return bases


NET_FACE_BASES = _net_face_bases()


def _face_across_display_side(face_id: str, side: str) -> str:
    normal, up, right = NET_FACE_BASES[str(face_id)]
    if str(side) == "top":
        target_normal = tuple(up)
    elif str(side) == "bottom":
        target_normal = _neg(up)
    elif str(side) == "right":
        target_normal = tuple(right)
    elif str(side) == "left":
        target_normal = _neg(right)
    else:
        raise ValueError(f"unsupported marked side: {side}")
    return str(FACE_BY_NORMAL[tuple(target_normal)])


def _sample_face_labels(instance_seed: int, namespace: str) -> Dict[str, str]:
    rng = spawn_rng(int(instance_seed), f"{namespace}.face_labels")
    labels = rng.sample(list(FACE_LABEL_POOL), len(FACE_IDS))
    return {face: str(label) for face, label in zip(FACE_IDS, labels)}


def _option_order(
    *,
    face_labels: Mapping[str, str],
    correct_face: str,
    instance_seed: int,
    namespace: str,
) -> Tuple[Tuple[FaceOption, ...], str]:
    correct_index = resolve_selection_index(
        params={},
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.correct_option_index",
    ) % len(FACE_IDS)
    rng = spawn_rng(int(instance_seed), f"{namespace}.option_order")
    distractors = [face for face in FACE_IDS if str(face) != str(correct_face)]
    rng.shuffle(distractors)
    ordered_faces = list(distractors)
    ordered_faces.insert(int(correct_index), str(correct_face))
    ordered_faces = ordered_faces[: len(FACE_IDS)]
    labels = tuple(ascii_uppercase[index] for index in range(len(ordered_faces)))
    options = tuple(
        FaceOption(option_label=str(label), face_id=str(face), face_label=str(face_labels[str(face)]))
        for label, face in zip(labels, ordered_faces)
    )
    return options, str(labels[int(correct_index)])


def _mutated_face_sequence(
    *,
    base_sequence: Sequence[str],
    rng: Any,
    protected_first: bool = True,
) -> Tuple[str, ...]:
    """Return one plausible distractor sequence with one mutated face."""

    sequence = [str(face) for face in base_sequence]
    if not sequence:
        return tuple(sequence)
    start_index = 1 if bool(protected_first) and len(sequence) > 1 else 0
    index = int(rng.randrange(start_index, len(sequence)))
    choices = [face for face in FACE_IDS if str(face) != sequence[index]]
    sequence[index] = str(choices[int(rng.randrange(len(choices)))])
    return tuple(sequence)


def _surface_sequence_options(
    *,
    face_labels: Mapping[str, str],
    correct_sequence: Sequence[str],
    instance_seed: int,
    namespace: str,
) -> Tuple[Tuple[PathSequenceOption, ...], str]:
    correct_index = resolve_selection_index(
        params={},
        instance_seed=int(instance_seed),
        namespace=f"{namespace}.correct_option_index",
    ) % len(FACE_IDS)
    rng = spawn_rng(int(instance_seed), f"{namespace}.sequence_option_order")
    sequences: List[Tuple[str, ...]] = [tuple(str(face) for face in correct_sequence)]
    attempts = 0
    while len(sequences) < len(FACE_IDS) and attempts < 200:
        attempts += 1
        candidate = _mutated_face_sequence(base_sequence=correct_sequence, rng=rng)
        if candidate not in sequences:
            sequences.append(tuple(candidate))
    while len(sequences) < len(FACE_IDS):
        shuffled = list(str(face) for face in correct_sequence)
        rng.shuffle(shuffled)
        candidate = tuple(shuffled)
        if candidate not in sequences:
            sequences.append(candidate)
    correct = sequences.pop(0)
    rng.shuffle(sequences)
    sequences.insert(int(correct_index), correct)
    labels = tuple(ascii_uppercase[index] for index in range(len(sequences)))
    options = tuple(
        PathSequenceOption(
            option_label=str(label),
            face_ids=tuple(str(face) for face in sequence),
            face_labels=tuple(str(face_labels[str(face)]) for face in sequence),
        )
        for label, sequence in zip(labels, sequences)
    )
    return options, str(labels[int(correct_index)])


def _sample_face_relation_dataset(*, query_id: str, params: Mapping[str, Any], instance_seed: int) -> FaceRelationDataset:
    del params
    rng = spawn_rng(int(instance_seed), f"{INTERNAL_TASK_ID}.{query_id}.face_relation")
    face_labels = _sample_face_labels(int(instance_seed), f"{INTERNAL_TASK_ID}.{query_id}")
    reference_face = str(FACE_IDS[int(rng.randrange(len(FACE_IDS)))])
    marked_side: str | None = None
    if str(query_id) == "opposite_face_label":
        correct_face = str(OPPOSITE_FACE[str(reference_face)])
    elif str(query_id) == "marked_edge_neighbor_face_label":
        side_support = tuple(SIDE_OFFSETS.keys())
        marked_side = str(side_support[int(rng.randrange(len(side_support)))])
        correct_face = _face_across_display_side(str(reference_face), str(marked_side))
    else:
        raise ValueError(f"unsupported face-relation query_id: {query_id}")
    options, correct_label = _option_order(
        face_labels=face_labels,
        correct_face=str(correct_face),
        instance_seed=int(instance_seed),
        namespace=f"{FACE_RELATION_TASK_ID}.{query_id}",
    )
    return FaceRelationDataset(
        query_id=str(query_id),
        face_labels=dict(face_labels),
        reference_face=str(reference_face),
        marked_side=marked_side,
        correct_face=str(correct_face),
        options=tuple(options),
        correct_option_label=str(correct_label),
    )


def _sample_surface_path_dataset(*, query_id: str, params: Mapping[str, Any], instance_seed: int) -> SurfacePathDataset:
    rng = spawn_rng(int(instance_seed), f"{INTERNAL_TASK_ID}.{query_id}.surface_path")
    step_min = _get_int(params, "surface_path_step_count_min", _DEFAULTS.surface_path_step_count_min)
    step_max = _get_int(params, "surface_path_step_count_max", _DEFAULTS.surface_path_step_count_max)
    step_count = int(step_min + (resolve_selection_index(params={}, instance_seed=int(instance_seed), namespace=f"{SURFACE_PATH_TASK_ID}.step_count") % max(1, step_max - step_min + 1)))
    face_labels = _sample_face_labels(int(instance_seed), f"{INTERNAL_TASK_ID}.{query_id}")

    sides = tuple(SIDE_OFFSETS.keys())
    for attempt in range(80):
        start_face = str(FACE_IDS[int(rng.randrange(len(FACE_IDS)))])
        current = str(start_face)
        sequence = [str(current)]
        path_sides: List[str] = []
        previous_side: str | None = None
        for _ in range(int(step_count)):
            candidates = list(sides)
            if previous_side is not None and len(candidates) > 1:
                opposite = {"top": "bottom", "bottom": "top", "left": "right", "right": "left"}[str(previous_side)]
                candidates = [side for side in candidates if side != opposite]
            side = str(candidates[int(rng.randrange(len(candidates)))])
            current = _face_across_display_side(str(current), str(side))
            path_sides.append(str(side))
            sequence.append(str(current))
            previous_side = str(side)
        if len(set(sequence)) >= min(3, len(sequence)) or attempt >= 12:
            break

    endpoint_options, endpoint_label = _option_order(
        face_labels=face_labels,
        correct_face=str(sequence[-1]),
        instance_seed=int(instance_seed),
        namespace=f"{SURFACE_PATH_TASK_ID}.{query_id}.endpoint",
    )
    sequence_options, sequence_label = _surface_sequence_options(
        face_labels=face_labels,
        correct_sequence=tuple(sequence),
        instance_seed=int(instance_seed),
        namespace=f"{SURFACE_PATH_TASK_ID}.{query_id}.sequence",
    )
    correct_label = str(endpoint_label if str(query_id) == "folded_path_endpoint_label" else sequence_label)
    if str(query_id) not in SURFACE_PATH_QUERY_IDS:
        raise ValueError(f"unsupported surface-path query_id: {query_id}")
    return SurfacePathDataset(
        query_id=str(query_id),
        face_labels=dict(face_labels),
        start_face=str(sequence[0]),
        path_sides=tuple(path_sides),
        face_sequence=tuple(sequence),
        endpoint_face=str(sequence[-1]),
        endpoint_options=tuple(endpoint_options),
        sequence_options=tuple(sequence_options),
        correct_option_label=str(correct_label),
    )


def _roll_orientation(orientation: Mapping[str, str], direction: str) -> Dict[str, str]:
    top = str(orientation["top"])
    bottom = str(orientation["bottom"])
    north = str(orientation["north"])
    south = str(orientation["south"])
    west = str(orientation["west"])
    east = str(orientation["east"])
    if str(direction) == "N":
        return {"top": south, "bottom": north, "north": top, "south": bottom, "west": west, "east": east}
    if str(direction) == "S":
        return {"top": north, "bottom": south, "north": bottom, "south": top, "west": west, "east": east}
    if str(direction) == "E":
        return {"top": west, "bottom": east, "north": north, "south": south, "west": bottom, "east": top}
    if str(direction) == "W":
        return {"top": east, "bottom": west, "north": north, "south": south, "west": top, "east": bottom}
    raise ValueError(f"unsupported roll direction: {direction}")


def _random_start_orientation(instance_seed: int, namespace: str) -> Dict[str, str]:
    rng = spawn_rng(int(instance_seed), f"{namespace}.start_orientation")
    orientation = {"top": "U", "bottom": "D", "north": "B", "south": "F", "west": "L", "east": "R"}
    for _ in range(int(rng.randrange(1, 7))):
        orientation = _roll_orientation(orientation, str(rng.choice(tuple(ROLL_OFFSETS.keys()))))
    return dict(orientation)


def _sample_path(*, instance_seed: int, rows: int, cols: int, length: int, namespace: str) -> Tuple[Tuple[Tuple[int, int], ...], Tuple[str, ...]]:
    rng = spawn_rng(int(instance_seed), f"{namespace}.path")
    for _attempt in range(80):
        row = int(rng.randrange(1, max(2, int(rows) - 1)))
        col = int(rng.randrange(1, max(2, int(cols) - 1)))
        path = [(row, col)]
        dirs: List[str] = []
        previous: str | None = None
        for _step in range(int(length)):
            candidates = []
            for direction, (dr, dc) in ROLL_OFFSETS.items():
                nr = int(row + dr)
                nc = int(col + dc)
                if 0 <= nr < int(rows) and 0 <= nc < int(cols):
                    candidates.append(str(direction))
            if previous is not None and len(candidates) > 1:
                opposite = {"N": "S", "S": "N", "E": "W", "W": "E"}[str(previous)]
                candidates = [item for item in candidates if item != opposite] or candidates
            direction = str(candidates[int(rng.randrange(len(candidates)))])
            dr, dc = ROLL_OFFSETS[str(direction)]
            row = int(row + dr)
            col = int(col + dc)
            path.append((row, col))
            dirs.append(str(direction))
            previous = str(direction)
        if len(set(path)) >= min(4, len(path)):
            return tuple(path), tuple(dirs)
    return tuple(path), tuple(dirs)


def _sample_rolling_dataset(*, query_id: str, params: Mapping[str, Any], instance_seed: int) -> RollingDataset:
    rng = spawn_rng(int(instance_seed), f"{INTERNAL_TASK_ID}.{query_id}.rolling")
    rows_min = _get_int(params, "rolling_grid_rows_min", _DEFAULTS.rolling_grid_rows_min)
    rows_max = _get_int(params, "rolling_grid_rows_max", _DEFAULTS.rolling_grid_rows_max)
    cols_min = _get_int(params, "rolling_grid_cols_min", _DEFAULTS.rolling_grid_cols_min)
    cols_max = _get_int(params, "rolling_grid_cols_max", _DEFAULTS.rolling_grid_cols_max)
    len_min = _get_int(params, "rolling_path_length_min", _DEFAULTS.rolling_path_length_min)
    len_max = _get_int(params, "rolling_path_length_max", _DEFAULTS.rolling_path_length_max)
    rows = int(rows_min + (resolve_selection_index(params={}, instance_seed=int(instance_seed), namespace=f"{ROLLING_RESULT_TASK_ID}.rows") % max(1, rows_max - rows_min + 1)))
    cols = int(cols_min + (resolve_selection_index(params={}, instance_seed=int(instance_seed), namespace=f"{ROLLING_RESULT_TASK_ID}.cols") % max(1, cols_max - cols_min + 1)))
    path_length = int(len_min + (resolve_selection_index(params={}, instance_seed=int(instance_seed), namespace=f"{ROLLING_RESULT_TASK_ID}.path_length") % max(1, len_max - len_min + 1)))
    slot_by_query = {
        "final_top_face_label": "top",
        "final_front_face_label": "south",
        "final_right_face_label": "east",
    }
    if str(query_id) not in slot_by_query:
        raise ValueError(f"unsupported rolling query_id: {query_id}")
    target_slot = str(slot_by_query[str(query_id)])
    face_labels = _sample_face_labels(int(instance_seed), f"{INTERNAL_TASK_ID}.{query_id}")
    for attempt in range(40):
        start_orientation = _random_start_orientation(int(instance_seed) + int(attempt), f"{INTERNAL_TASK_ID}.{query_id}")
        path_cells, path_dirs = _sample_path(
            instance_seed=int(instance_seed) + int(attempt),
            rows=int(rows),
            cols=int(cols),
            length=int(path_length),
            namespace=f"{INTERNAL_TASK_ID}.{query_id}",
        )
        final_orientation = dict(start_orientation)
        for direction in path_dirs:
            final_orientation = _roll_orientation(final_orientation, str(direction))
        if str(final_orientation[str(target_slot)]) != str(start_orientation[str(target_slot)]) or attempt >= 8:
            break
    correct_face = str(final_orientation[str(target_slot)])
    options, correct_label = _option_order(
        face_labels=face_labels,
        correct_face=str(correct_face),
        instance_seed=int(instance_seed),
        namespace=f"{ROLLING_RESULT_TASK_ID}.{query_id}",
    )
    return RollingDataset(
        query_id=str(query_id),
        face_labels=dict(face_labels),
        start_orientation=dict(start_orientation),
        final_orientation=dict(final_orientation),
        target_slot=str(target_slot),
        grid_rows=int(rows),
        grid_cols=int(cols),
        path_cells=tuple(path_cells),
        path_directions=tuple(path_dirs),
        correct_face=str(correct_face),
        options=tuple(options),
        correct_option_label=str(correct_label),
    )


def _style_face_colors(style: Any) -> Dict[str, Tuple[int, int, int]]:
    colors = list(tuple(int(v) for v in color) for color in tuple(style.state_colors))
    while len(colors) < len(FACE_IDS):
        colors.append(tuple(int(v) for v in style.panel_accent_rgb))
    return {face: tuple(colors[index % len(colors)]) for index, face in enumerate(FACE_IDS)}


def _draw_title(draw: ImageDraw.ImageDraw, text: str, center_x: float, y: float, style: Any, font_size: int) -> None:
    draw_centered_text(
        draw,
        text=str(text),
        center=(float(center_x), float(y)),
        font=load_font(int(font_size), bold=True),
        fill=tuple(style.text_rgb),
        stroke_fill=tuple(style.text_stroke_rgb),
        stroke_width=1,
    )


def _draw_face_label(draw: ImageDraw.ImageDraw, *, text: str, bbox: Sequence[float], style: Any, font_size: int) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    draw_centered_text(
        draw,
        text=str(text),
        center=(0.5 * (x0 + x1), 0.5 * (y0 + y1)),
        font=load_font(int(font_size), bold=True),
        fill=tuple(style.text_rgb),
        stroke_fill=tuple(style.text_stroke_rgb),
        stroke_width=2,
    )


def _draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    *,
    start: Tuple[float, float],
    end: Tuple[float, float],
    fill: Tuple[int, int, int],
    width: int,
    dash_px: int = 10,
    gap_px: int = 7,
) -> None:
    x0, y0 = float(start[0]), float(start[1])
    x1, y1 = float(end[0]), float(end[1])
    length = max(1.0, ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5)
    step = max(1, int(dash_px) + int(gap_px))
    cursor = 0.0
    while cursor < length:
        dash_end = min(length, cursor + max(1, int(dash_px)))
        sx = x0 + (x1 - x0) * (cursor / length)
        sy = y0 + (y1 - y0) * (cursor / length)
        ex = x0 + (x1 - x0) * (dash_end / length)
        ey = y0 + (y1 - y0) * (dash_end / length)
        draw.line([(sx, sy), (ex, ey)], fill=tuple(fill), width=max(1, int(width)))
        cursor += float(step)


def _draw_variant_panel_trim(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Sequence[float],
    scene_variant: str,
    style: Any,
) -> None:
    x0, y0, x1, y1 = [int(round(float(value))) for value in panel_bbox]
    variant = str(scene_variant)
    if variant == "paper_model":
        inner = (x0 + 10, y0 + 10, x1 - 10, y1 - 10)
        segments = [
            ((inner[0], inner[1]), (inner[2], inner[1])),
            ((inner[2], inner[1]), (inner[2], inner[3])),
            ((inner[2], inner[3]), (inner[0], inner[3])),
            ((inner[0], inner[3]), (inner[0], inner[1])),
        ]
        for start, end in segments:
            _draw_dashed_line(draw, start=start, end=end, fill=tuple(style.panel_accent_rgb), width=1, dash_px=12, gap_px=8)
    elif variant == "game_mat":
        draw.rounded_rectangle((x0 + 6, y0 + 6, x1 - 6, y1 - 6), radius=14, outline=tuple(style.panel_accent_rgb), width=3)
        for cx, cy in ((x0 + 20, y0 + 20), (x1 - 20, y0 + 20), (x0 + 20, y1 - 20), (x1 - 20, y1 - 20)):
            draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=tuple(style.panel_accent_rgb))


def _draw_net_fold_seams(
    draw: ImageDraw.ImageDraw,
    *,
    face_bboxes: Mapping[str, Sequence[float]],
    scene_variant: str,
    style: Any,
) -> None:
    if str(scene_variant) != "paper_model":
        return
    seen: set[Tuple[str, str]] = set()
    for face, (x, y) in NET_COORDS.items():
        for dx, dy in SIDE_OFFSETS.values():
            neighbor = next((other for other, coord in NET_COORDS.items() if coord == (x + dx, y + dy)), None)
            if neighbor is None:
                continue
            key = tuple(sorted((str(face), str(neighbor))))
            if key in seen:
                continue
            seen.add(key)
            ax0, ay0, ax1, ay1 = [float(value) for value in face_bboxes[str(face)]]
            bx0, by0, bx1, by1 = [float(value) for value in face_bboxes[str(neighbor)]]
            if abs(ax1 - bx0) <= 1.0 or abs(bx1 - ax0) <= 1.0:
                seam_x = ax1 if abs(ax1 - bx0) <= 1.0 else ax0
                _draw_dashed_line(
                    draw,
                    start=(seam_x, max(ay0, by0) + 4),
                    end=(seam_x, min(ay1, by1) - 4),
                    fill=tuple(style.panel_accent_rgb),
                    width=2,
                    dash_px=8,
                    gap_px=6,
                )
            elif abs(ay1 - by0) <= 1.0 or abs(by1 - ay0) <= 1.0:
                seam_y = ay1 if abs(ay1 - by0) <= 1.0 else ay0
                _draw_dashed_line(
                    draw,
                    start=(max(ax0, bx0) + 4, seam_y),
                    end=(min(ax1, bx1) - 4, seam_y),
                    fill=tuple(style.panel_accent_rgb),
                    width=2,
                    dash_px=8,
                    gap_px=6,
                )


def _scene_variant_style_metadata(scene_variant: str) -> Dict[str, Any]:
    variant = str(scene_variant)
    features = {
        "clean_net": ["standard panel borders"],
        "paper_model": ["dashed paper trim", "dashed fold seams"],
        "game_mat": ["accent inset panel frames", "corner pin markers"],
    }.get(variant, ["standard panel borders"])
    return {
        "scene_variant": variant,
        "visual_features": list(features),
        "semantic_policy": "non_semantic_chrome_only_no_layout_or_answer_change",
    }


def _draw_net_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Sequence[float],
    dataset: FaceRelationDataset,
    style: Any,
    font_size: int,
    cell_size_px: int,
) -> Tuple[Dict[str, List[float]], List[float]]:
    x0, y0, x1, y1 = [int(round(float(value))) for value in panel_bbox]
    draw_rounded_rect(
        draw,
        (x0, y0, x1, y1),
        radius=18,
        fill=tuple(style.panel_fill_rgb),
        outline=tuple(style.panel_border_rgb),
        width=2,
    )
    _draw_title(draw, "Cube net", 0.5 * (x0 + x1), y0 + 30, style, _DEFAULTS.title_font_size_px)
    min_x = min(coord[0] for coord in NET_COORDS.values())
    max_x = max(coord[0] for coord in NET_COORDS.values())
    min_y = min(coord[1] for coord in NET_COORDS.values())
    max_y = max(coord[1] for coord in NET_COORDS.values())
    net_w = (int(max_x - min_x + 1)) * int(cell_size_px)
    net_h = (int(max_y - min_y + 1)) * int(cell_size_px)
    origin_x = int(round(0.5 * (x0 + x1 - net_w)))
    origin_y = int(round(y0 + 72 + max(0, (y1 - y0 - 102 - net_h) * 0.5)))
    face_colors = _style_face_colors(style)
    face_bboxes: Dict[str, List[float]] = {}
    for face_id in sorted(FACE_IDS, key=lambda face: (NET_COORDS[face][1], NET_COORDS[face][0])):
        gx, gy = NET_COORDS[str(face_id)]
        fx0 = origin_x + int(gx - min_x) * int(cell_size_px)
        fy0 = origin_y + int(gy - min_y) * int(cell_size_px)
        fx1 = fx0 + int(cell_size_px)
        fy1 = fy0 + int(cell_size_px)
        fill = tuple(face_colors[str(face_id)])
        draw.rectangle((fx0, fy0, fx1, fy1), fill=fill, outline=tuple(style.grid_rgb), width=2)
        _draw_face_label(
            draw,
            text=str(dataset.face_labels[str(face_id)]),
            bbox=(fx0, fy0, fx1, fy1),
            style=style,
            font_size=int(font_size),
        )
        face_bboxes[str(face_id)] = [float(fx0), float(fy0), float(fx1), float(fy1)]
    ref_bbox = face_bboxes[str(dataset.reference_face)]
    draw.rectangle(tuple(ref_bbox), outline=tuple(style.mark_rgb), width=6)
    if dataset.marked_side is not None:
        rx0, ry0, rx1, ry1 = [float(value) for value in ref_bbox]
        if dataset.marked_side == "top":
            start, end = (rx0 + 8, ry0 + 2), (rx1 - 8, ry0 + 2)
        elif dataset.marked_side == "bottom":
            start, end = (rx0 + 8, ry1 - 2), (rx1 - 8, ry1 - 2)
        elif dataset.marked_side == "left":
            start, end = (rx0 + 2, ry0 + 8), (rx0 + 2, ry1 - 8)
        else:
            start, end = (rx1 - 2, ry0 + 8), (rx1 - 2, ry1 - 8)
        draw.line([start, end], fill=tuple(style.mark_rgb), width=10)
    return face_bboxes, [float(x0), float(y0), float(x1), float(y1)]


def _draw_options(
    draw: ImageDraw.ImageDraw,
    *,
    options: Sequence[FaceOption],
    panel_bbox: Sequence[float],
    title: str,
    style: Any,
    columns: int,
) -> Dict[str, List[float]]:
    x0, y0, x1, y1 = [int(round(float(value))) for value in panel_bbox]
    draw_rounded_rect(
        draw,
        (x0, y0, x1, y1),
        radius=18,
        fill=tuple(style.panel_fill_rgb),
        outline=tuple(style.panel_border_rgb),
        width=2,
    )
    _draw_title(draw, str(title), 0.5 * (x0 + x1), y0 + 28, style, 20)
    columns = max(1, int(columns))
    rows = int((len(options) + columns - 1) // columns)
    pad = 20
    gap = 14
    top = y0 + 58
    usable_w = x1 - x0 - 2 * pad - (columns - 1) * gap
    usable_h = y1 - top - pad - (rows - 1) * gap
    card_w = max(60, int(usable_w / columns))
    card_h = max(54, int(usable_h / rows))
    bboxes: Dict[str, List[float]] = {}
    face_colors = _style_face_colors(style)
    for index, option in enumerate(options):
        row = int(index // columns)
        col = int(index % columns)
        bx0 = x0 + pad + col * (card_w + gap)
        by0 = top + row * (card_h + gap)
        bx1 = bx0 + card_w
        by1 = by0 + card_h
        draw_rounded_rect(
            draw,
            (bx0, by0, bx1, by1),
            radius=10,
            fill=tuple(style.option_fill_rgb),
            outline=tuple(style.panel_border_rgb),
            width=2,
        )
        draw_rounded_rect(
            draw,
            (bx0 + 8, by0 + 8, bx0 + 34, by0 + 34),
            radius=6,
            fill=tuple(style.option_marker_fill_rgb),
            outline=tuple(style.panel_border_rgb),
            width=1,
        )
        draw_centered_text(
            draw,
            text=str(option.option_label),
            center=(bx0 + 21, by0 + 21),
            font=load_font(15, bold=True),
            fill=tuple(style.text_rgb),
            stroke_fill=tuple(style.text_stroke_rgb),
            stroke_width=1,
        )
        swatch = (bx0 + 44, by0 + 11, bx0 + 80, by0 + 47)
        draw.rectangle(swatch, fill=tuple(face_colors[str(option.face_id)]), outline=tuple(style.grid_rgb), width=1)
        _draw_face_label(
            draw,
            text=str(option.face_label),
            bbox=(bx0 + 88, by0 + 12, bx1 - 10, by1 - 10),
            style=style,
            font_size=_DEFAULTS.option_font_size_px,
        )
        bboxes[f"option_{option.option_label}"] = [float(bx0), float(by0), float(bx1), float(by1)]
    return bboxes


def _draw_surface_path_net_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Sequence[float],
    dataset: SurfacePathDataset,
    style: Any,
    font_size: int,
    cell_size_px: int,
) -> Tuple[Dict[str, List[float]], List[float]]:
    x0, y0, x1, y1 = [int(round(float(value))) for value in panel_bbox]
    draw_rounded_rect(
        draw,
        (x0, y0, x1, y1),
        radius=18,
        fill=tuple(style.panel_fill_rgb),
        outline=tuple(style.panel_border_rgb),
        width=2,
    )
    _draw_title(draw, "Folded cube net", 0.5 * (x0 + x1), y0 + 30, style, _DEFAULTS.title_font_size_px)
    min_x = min(coord[0] for coord in NET_COORDS.values())
    max_x = max(coord[0] for coord in NET_COORDS.values())
    min_y = min(coord[1] for coord in NET_COORDS.values())
    max_y = max(coord[1] for coord in NET_COORDS.values())
    net_w = (int(max_x - min_x + 1)) * int(cell_size_px)
    net_h = (int(max_y - min_y + 1)) * int(cell_size_px)
    origin_x = int(round(0.5 * (x0 + x1 - net_w)))
    origin_y = int(round(y0 + 70 + max(0, (y1 - y0 - 110 - net_h) * 0.5)))
    face_colors = _style_face_colors(style)
    face_bboxes: Dict[str, List[float]] = {}
    for face_id in sorted(FACE_IDS, key=lambda face: (NET_COORDS[face][1], NET_COORDS[face][0])):
        gx, gy = NET_COORDS[str(face_id)]
        fx0 = origin_x + int(gx - min_x) * int(cell_size_px)
        fy0 = origin_y + int(gy - min_y) * int(cell_size_px)
        fx1 = fx0 + int(cell_size_px)
        fy1 = fy0 + int(cell_size_px)
        draw.rectangle((fx0, fy0, fx1, fy1), fill=tuple(face_colors[str(face_id)]), outline=tuple(style.grid_rgb), width=2)
        _draw_face_label(
            draw,
            text=str(dataset.face_labels[str(face_id)]),
            bbox=(fx0, fy0, fx1, fy1),
            style=style,
            font_size=int(font_size),
        )
        face_bboxes[str(face_id)] = [float(fx0), float(fy0), float(fx1), float(fy1)]
    start_bbox = face_bboxes[str(dataset.start_face)]
    draw.rectangle(tuple(start_bbox), outline=tuple(style.mark_rgb), width=6)
    draw_centered_text(
        draw,
        text="START",
        center=(0.5 * (start_bbox[0] + start_bbox[2]), start_bbox[1] - 14),
        font=load_font(13, bold=True),
        fill=tuple(style.mark_rgb),
        stroke_fill=tuple(style.text_stroke_rgb),
        stroke_width=2,
    )
    return face_bboxes, [float(x0), float(y0), float(x1), float(y1)]


def _draw_surface_instruction_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Sequence[float],
    dataset: SurfacePathDataset,
    style: Any,
) -> List[float]:
    x0, y0, x1, y1 = [int(round(float(value))) for value in panel_bbox]
    draw_rounded_rect(
        draw,
        (x0, y0, x1, y1),
        radius=18,
        fill=tuple(style.panel_fill_rgb),
        outline=tuple(style.panel_border_rgb),
        width=2,
    )
    _draw_title(draw, "Folded-edge moves", 0.5 * (x0 + x1), y0 + 28, style, 20)
    side_words = {"top": "top edge", "right": "right edge", "bottom": "bottom edge", "left": "left edge"}
    row_h = max(34, int((y1 - y0 - 74) / max(1, len(dataset.path_sides))))
    for index, side in enumerate(dataset.path_sides):
        cy = y0 + 66 + index * row_h + 0.5 * row_h
        badge = (x0 + 28, cy - 15, x0 + 60, cy + 17)
        draw_rounded_rect(
            draw,
            badge,
            radius=8,
            fill=tuple(style.option_marker_fill_rgb),
            outline=tuple(style.panel_border_rgb),
            width=1,
        )
        draw_centered_text(
            draw,
            text=str(index + 1),
            center=(0.5 * (badge[0] + badge[2]), 0.5 * (badge[1] + badge[3])),
            font=load_font(15, bold=True),
            fill=tuple(style.text_rgb),
            stroke_fill=tuple(style.text_stroke_rgb),
            stroke_width=1,
        )
        draw_centered_text(
            draw,
            text=str(side_words[str(side)]),
            center=(x0 + 185, cy),
            font=load_font(19, bold=True),
            fill=tuple(style.text_rgb),
            stroke_fill=tuple(style.text_stroke_rgb),
            stroke_width=1,
        )
    return [float(x0), float(y0), float(x1), float(y1)]


def _draw_sequence_options(
    draw: ImageDraw.ImageDraw,
    *,
    options: Sequence[PathSequenceOption],
    panel_bbox: Sequence[float],
    title: str,
    style: Any,
    columns: int,
) -> Dict[str, List[float]]:
    x0, y0, x1, y1 = [int(round(float(value))) for value in panel_bbox]
    draw_rounded_rect(
        draw,
        (x0, y0, x1, y1),
        radius=18,
        fill=tuple(style.panel_fill_rgb),
        outline=tuple(style.panel_border_rgb),
        width=2,
    )
    _draw_title(draw, str(title), 0.5 * (x0 + x1), y0 + 28, style, 20)
    columns = max(1, int(columns))
    rows = int((len(options) + columns - 1) // columns)
    pad = 20
    gap = 14
    top = y0 + 58
    usable_w = x1 - x0 - 2 * pad - (columns - 1) * gap
    usable_h = y1 - top - pad - (rows - 1) * gap
    card_w = max(120, int(usable_w / columns))
    card_h = max(54, int(usable_h / rows))
    bboxes: Dict[str, List[float]] = {}
    for index, option in enumerate(options):
        row = int(index // columns)
        col = int(index % columns)
        bx0 = x0 + pad + col * (card_w + gap)
        by0 = top + row * (card_h + gap)
        bx1 = bx0 + card_w
        by1 = by0 + card_h
        draw_rounded_rect(
            draw,
            (bx0, by0, bx1, by1),
            radius=10,
            fill=tuple(style.option_fill_rgb),
            outline=tuple(style.panel_border_rgb),
            width=2,
        )
        draw_rounded_rect(
            draw,
            (bx0 + 8, by0 + 8, bx0 + 34, by0 + 34),
            radius=6,
            fill=tuple(style.option_marker_fill_rgb),
            outline=tuple(style.panel_border_rgb),
            width=1,
        )
        draw_centered_text(
            draw,
            text=str(option.option_label),
            center=(bx0 + 21, by0 + 21),
            font=load_font(15, bold=True),
            fill=tuple(style.text_rgb),
            stroke_fill=tuple(style.text_stroke_rgb),
            stroke_width=1,
        )
        sequence_text = " -> ".join(str(label) for label in option.face_labels)
        draw_centered_text(
            draw,
            text=sequence_text,
            center=(0.5 * (bx0 + 54 + bx1), 0.5 * (by0 + by1)),
            font=load_font(17, bold=True),
            fill=tuple(style.text_rgb),
            stroke_fill=tuple(style.text_stroke_rgb),
            stroke_width=1,
        )
        bboxes[f"option_{option.option_label}"] = [float(bx0), float(by0), float(bx1), float(by1)]
    return bboxes


def _draw_cube_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Sequence[float],
    orientation: Mapping[str, str],
    face_labels: Mapping[str, str],
    style: Any,
) -> Tuple[List[float], Dict[str, List[float]]]:
    x0, y0, x1, y1 = [int(round(float(value))) for value in panel_bbox]
    draw_rounded_rect(
        draw,
        (x0, y0, x1, y1),
        radius=18,
        fill=tuple(style.panel_fill_rgb),
        outline=tuple(style.panel_border_rgb),
        width=2,
    )
    _draw_title(draw, "Start cube", 0.5 * (x0 + x1), y0 + 28, style, 20)
    cx = 0.5 * (x0 + x1)
    top_y = y0 + 88
    mid_y = y0 + 162
    bottom_y = y1 - 48
    half_w = min(110.0, 0.28 * (x1 - x0))
    top = [(cx, top_y), (cx + half_w, 0.5 * (top_y + mid_y)), (cx, mid_y), (cx - half_w, 0.5 * (top_y + mid_y))]
    front = [(cx - half_w, 0.5 * (top_y + mid_y)), (cx, mid_y), (cx, bottom_y), (cx - half_w, bottom_y - 0.5 * (mid_y - top_y))]
    right = [(cx, mid_y), (cx + half_w, 0.5 * (top_y + mid_y)), (cx + half_w, bottom_y - 0.5 * (mid_y - top_y)), (cx, bottom_y)]
    face_colors = _style_face_colors(style)
    face_polys = {
        "south": front,
        "east": right,
        "top": top,
    }
    face_bboxes: Dict[str, List[float]] = {}
    for slot in ("south", "east", "top"):
        face_id = str(orientation[str(slot)])
        poly = face_polys[str(slot)]
        draw.polygon(poly, fill=tuple(face_colors[str(face_id)]), outline=tuple(style.grid_rgb))
        draw.line(poly + [poly[0]], fill=tuple(style.grid_rgb), width=2)
        px = sum(point[0] for point in poly) / len(poly)
        py = sum(point[1] for point in poly) / len(poly)
        draw_centered_text(
            draw,
            text=str(face_labels[str(face_id)]),
            center=(px, py),
            font=load_font(28, bold=True),
            fill=tuple(style.text_rgb),
            stroke_fill=tuple(style.text_stroke_rgb),
            stroke_width=2,
        )
        xs = [point[0] for point in poly]
        ys = [point[1] for point in poly]
        face_bboxes[str(slot)] = [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]
    return [float(x0), float(y0), float(x1), float(y1)], face_bboxes


def _draw_path_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel_bbox: Sequence[float],
    dataset: RollingDataset,
    style: Any,
) -> Tuple[List[float], Dict[str, List[float]]]:
    x0, y0, x1, y1 = [int(round(float(value))) for value in panel_bbox]
    draw_rounded_rect(
        draw,
        (x0, y0, x1, y1),
        radius=18,
        fill=tuple(style.panel_fill_rgb),
        outline=tuple(style.panel_border_rgb),
        width=2,
    )
    _draw_title(draw, "Roll path", 0.5 * (x0 + x1), y0 + 28, style, 20)
    board_pad = 44
    top = y0 + 62
    cell = int(min((x1 - x0 - 2 * board_pad) / dataset.grid_cols, (y1 - top - 28) / dataset.grid_rows))
    board_w = int(cell * dataset.grid_cols)
    board_h = int(cell * dataset.grid_rows)
    bx0 = int(round(0.5 * (x0 + x1 - board_w)))
    by0 = int(round(top + 0.5 * max(0, (y1 - top - 28 - board_h))))
    path_set = set(dataset.path_cells)
    cell_bboxes: Dict[str, List[float]] = {}
    for row in range(dataset.grid_rows):
        for col in range(dataset.grid_cols):
            cx0 = bx0 + col * cell
            cy0 = by0 + row * cell
            cx1 = cx0 + cell
            cy1 = cy0 + cell
            fill = tuple(style.step_fill_rgb) if (row, col) in path_set else tuple(style.option_fill_rgb)
            draw.rectangle((cx0, cy0, cx1, cy1), fill=fill, outline=tuple(style.grid_rgb), width=1)
            cell_bboxes[f"cell_{row}_{col}"] = [float(cx0), float(cy0), float(cx1), float(cy1)]
    centers = [
        (float(bx0 + col * cell + 0.5 * cell), float(by0 + row * cell + 0.5 * cell))
        for row, col in dataset.path_cells
    ]
    for index, (start, end) in enumerate(zip(centers, centers[1:])):
        draw_arrow(
            draw,
            start=start,
            end=end,
            fill=tuple(style.mark_rgb),
            width=4,
            head_length_px=14,
            head_width_px=14,
        )
        sx, sy = start
        draw_centered_text(
            draw,
            text=str(index + 1),
            center=(sx, sy),
            font=load_font(13, bold=True),
            fill=tuple(style.text_rgb),
            stroke_fill=tuple(style.text_stroke_rgb),
            stroke_width=1,
        )
    if centers:
        draw_centered_text(
            draw,
            text="S",
            center=centers[0],
            font=load_font(18, bold=True),
            fill=tuple(style.text_rgb),
            stroke_fill=tuple(style.text_stroke_rgb),
            stroke_width=2,
        )
        draw_centered_text(
            draw,
            text="E",
            center=centers[-1],
            font=load_font(18, bold=True),
            fill=tuple(style.text_rgb),
            stroke_fill=tuple(style.text_stroke_rgb),
            stroke_width=2,
        )
    return [float(x0), float(y0), float(x1), float(y1)], cell_bboxes


def _render_face_relation_scene(
    *,
    dataset: FaceRelationDataset,
    params: Mapping[str, Any],
    instance_seed: int,
    scene_variant: str,
) -> Tuple[Image.Image, Dict[str, Any]]:
    width = _get_int(params, "canvas_width", _DEFAULTS.canvas_width)
    height = _get_int(params, "face_relation_canvas_height", _DEFAULTS.face_relation_canvas_height)
    style, style_meta = resolve_puzzle_scene_style(instance_seed=int(instance_seed), namespace=f"{FACE_RELATION_TASK_ID}.cube_surface_net")
    image, background_meta = make_puzzle_scene_background(canvas_width=int(width), canvas_height=int(height), style=style)
    draw = ImageDraw.Draw(image)
    net_panel = (54, 54, 686, int(height) - 54)
    option_panel = (724, 82, int(width) - 54, int(height) - 82)
    net_bboxes, net_panel_bbox = _draw_net_panel(
        draw,
        panel_bbox=net_panel,
        dataset=dataset,
        style=style,
        font_size=_get_int(params, "face_font_size_px", _DEFAULTS.face_font_size_px),
        cell_size_px=_get_int(params, "net_cell_size_px", _DEFAULTS.net_cell_size_px),
    )
    option_bboxes = _draw_options(
        draw,
        options=dataset.options,
        panel_bbox=option_panel,
        title="Face options",
        style=style,
        columns=2,
    )
    _draw_net_fold_seams(draw, face_bboxes=net_bboxes, scene_variant=str(scene_variant), style=style)
    _draw_variant_panel_trim(draw, panel_bbox=net_panel_bbox, scene_variant=str(scene_variant), style=style)
    _draw_variant_panel_trim(draw, panel_bbox=option_panel, scene_variant=str(scene_variant), style=style)
    return image, {
        "background_style": dict(background_meta),
        "scene_style": dict(style_meta),
        "scene_variant_style": _scene_variant_style_metadata(str(scene_variant)),
        "net_panel_bbox_px": list(net_panel_bbox),
        "face_bboxes_px": dict(net_bboxes),
        "option_panel_bboxes_px": dict(option_bboxes),
    }


def _render_rolling_scene(
    *,
    dataset: RollingDataset,
    params: Mapping[str, Any],
    instance_seed: int,
    scene_variant: str,
) -> Tuple[Image.Image, Dict[str, Any]]:
    width = _get_int(params, "canvas_width", _DEFAULTS.canvas_width)
    height = _get_int(params, "rolling_canvas_height", _DEFAULTS.rolling_canvas_height)
    style, style_meta = resolve_puzzle_scene_style(instance_seed=int(instance_seed), namespace=f"{ROLLING_RESULT_TASK_ID}.cube_surface_net")
    image, background_meta = make_puzzle_scene_background(canvas_width=int(width), canvas_height=int(height), style=style)
    draw = ImageDraw.Draw(image)
    cube_panel = (54, 54, 384, 438)
    path_panel = (420, 54, int(width) - 54, 438)
    option_panel = (76, 488, int(width) - 76, int(height) - 54)
    cube_bbox, cube_face_bboxes = _draw_cube_panel(
        draw,
        panel_bbox=cube_panel,
        orientation=dataset.start_orientation,
        face_labels=dataset.face_labels,
        style=style,
    )
    path_bbox, path_cell_bboxes = _draw_path_panel(
        draw,
        panel_bbox=path_panel,
        dataset=dataset,
        style=style,
    )
    option_bboxes = _draw_options(
        draw,
        options=dataset.options,
        panel_bbox=option_panel,
        title="Face options",
        style=style,
        columns=3,
    )
    for panel in (cube_bbox, path_bbox, option_panel):
        _draw_variant_panel_trim(draw, panel_bbox=panel, scene_variant=str(scene_variant), style=style)
    return image, {
        "background_style": dict(background_meta),
        "scene_style": dict(style_meta),
        "scene_variant_style": _scene_variant_style_metadata(str(scene_variant)),
        "start_cube_bbox_px": list(cube_bbox),
        "start_cube_face_bboxes_px": dict(cube_face_bboxes),
        "path_panel_bbox_px": list(path_bbox),
        "path_cell_bboxes_px": dict(path_cell_bboxes),
        "option_panel_bboxes_px": dict(option_bboxes),
    }


def _render_surface_path_scene(
    *,
    dataset: SurfacePathDataset,
    params: Mapping[str, Any],
    instance_seed: int,
    scene_variant: str,
) -> Tuple[Image.Image, Dict[str, Any]]:
    width = _get_int(params, "canvas_width", _DEFAULTS.canvas_width)
    height = _get_int(params, "rolling_canvas_height", _DEFAULTS.rolling_canvas_height)
    style, style_meta = resolve_puzzle_scene_style(instance_seed=int(instance_seed), namespace=f"{SURFACE_PATH_TASK_ID}.cube_surface_net")
    image, background_meta = make_puzzle_scene_background(canvas_width=int(width), canvas_height=int(height), style=style)
    draw = ImageDraw.Draw(image)
    net_panel = (54, 54, 520, 482)
    instruction_panel = (558, 54, int(width) - 54, 482)
    option_panel = (76, 532, int(width) - 76, int(height) - 54)
    face_bboxes, net_panel_bbox = _draw_surface_path_net_panel(
        draw,
        panel_bbox=net_panel,
        dataset=dataset,
        style=style,
        font_size=_get_int(params, "face_font_size_px", _DEFAULTS.face_font_size_px),
        cell_size_px=_get_int(params, "net_cell_size_px", _DEFAULTS.net_cell_size_px),
    )
    instruction_bbox = _draw_surface_instruction_panel(
        draw,
        panel_bbox=instruction_panel,
        dataset=dataset,
        style=style,
    )
    if str(dataset.query_id) == "folded_path_endpoint_label":
        option_bboxes = _draw_options(
            draw,
            options=dataset.endpoint_options,
            panel_bbox=option_panel,
            title="Endpoint options",
            style=style,
            columns=3,
        )
    else:
        option_bboxes = _draw_sequence_options(
            draw,
            options=dataset.sequence_options,
            panel_bbox=option_panel,
            title="Sequence options",
            style=style,
            columns=2,
        )
    _draw_net_fold_seams(draw, face_bboxes=face_bboxes, scene_variant=str(scene_variant), style=style)
    for panel in (net_panel_bbox, instruction_bbox, option_panel):
        _draw_variant_panel_trim(draw, panel_bbox=panel, scene_variant=str(scene_variant), style=style)
    return image, {
        "background_style": dict(background_meta),
        "scene_style": dict(style_meta),
        "scene_variant_style": _scene_variant_style_metadata(str(scene_variant)),
        "net_panel_bbox_px": list(net_panel_bbox),
        "instruction_panel_bbox_px": list(instruction_bbox),
        "face_bboxes_px": dict(face_bboxes),
        "option_panel_bboxes_px": dict(option_bboxes),
    }


def _option_specs_for_trace(options: Sequence[FaceOption]) -> List[Dict[str, str]]:
    return [
        {"option_label": str(option.option_label), "face_id": str(option.face_id), "face_label": str(option.face_label)}
        for option in options
    ]


def _sequence_option_specs_for_trace(options: Sequence[PathSequenceOption]) -> List[Dict[str, Any]]:
    return [
        {
            "option_label": str(option.option_label),
            "face_ids": [str(face) for face in option.face_ids],
            "face_labels": [str(label) for label in option.face_labels],
        }
        for option in options
    ]


def _prompt_defaults() -> Mapping[str, Any]:
    return required_group_defaults(
        _PROMPT_DEFAULTS,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "object_description_face_relation_label",
            "object_description_rolling_result_label",
            "object_description_surface_path_label",
            "json_output_contract",
            "json_output_contract_answer_only",
            "answer_hint_option_letter",
            "evidence_hint_face_relation",
            "evidence_hint_rolling_result",
            "evidence_hint_surface_path",
            "json_example_face_relation",
            "json_example_rolling_result",
            "json_example_surface_path",
            "json_example_answer_only_option_label",
        ),
        context=f"prompt defaults for {INTERNAL_TASK_ID}",
    )


class _CubeSurfaceBaseTask:
    domain = "puzzles"
    task_group = "spatial"
    default_dataset_enabled = True
    supported_query_ids: Tuple[str, ...]

    def _resolve_query_id(self, params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
        return _resolve_axis(
            params=params,
            instance_seed=int(instance_seed),
            supported=tuple(self.supported_query_ids),
            explicit_key="query_id",
            axis_namespace="query_id",
        )

    def _resolve_scene_variant(self, params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
        return _resolve_axis(
            params=params,
            instance_seed=int(instance_seed),
            supported=SCENE_VARIANTS,
            explicit_key="scene_variant",
            axis_namespace="scene_variant",
        )


@register_task
class PuzzlesSpatialCubeNetFaceRelationLabelTask(_CubeSurfaceBaseTask):
    """Select a face label from a cube net relation."""

    task_id = FACE_RELATION_TASK_ID
    supported_query_ids = FACE_RELATION_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_probs = self._resolve_query_id(params, instance_seed=int(instance_seed))
        scene_variant, scene_probs = self._resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = _sample_face_relation_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))
        font_family = _sample_cube_surface_font(
            task_id=self.task_id,
            instance_seed=int(instance_seed),
            params=params,
        )
        with temporary_default_font_family(str(font_family)):
            image, render_meta = _render_face_relation_scene(
                dataset=dataset,
                params=params,
                instance_seed=int(instance_seed),
                scene_variant=str(scene_variant),
            )
        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = _prompt_defaults()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_face_relation_label"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint_face_relation"]),
                "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
                "json_example": str(prompt_defaults["json_example_face_relation"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only_option_label"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        ref_bbox = render_meta["face_bboxes_px"][str(dataset.reference_face)]
        option_bbox = render_meta["option_panel_bboxes_px"][f"option_{dataset.correct_option_label}"]
        evidence_bboxes = {
            "marked_face": _round_evidence_bbox(ref_bbox),
            "selected_option": _round_evidence_bbox(option_bbox),
        }
        answer_gt = TypedValue(type="option_letter", value=str(dataset.correct_option_label))
        evidence_gt = TypedValue(type="keyed_bbox_map", value=dict(evidence_bboxes))
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": 0.46,
                "reasoning_load": 0.45 if str(query_id) == "opposite_face_label" else 0.58,
                "scene_variant_load": {"clean_net": 0.18, "paper_model": 0.24, "game_mat": 0.26}.get(str(scene_variant), 0.2),
            },
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "puzzle_cube_surface_net",
                "scene_id": SCENE_ID,
                "task_id": self.task_id,
                "entities": [
                    {"entity_id": f"face_{face}", "kind": "cube_net_face", "face_id": str(face), "face_label": str(label)}
                    for face, label in sorted(dataset.face_labels.items())
                ],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "reference_face": str(dataset.reference_face),
                    "marked_side": dataset.marked_side,
                    "correct_face": str(dataset.correct_face),
                    "correct_option_label": str(dataset.correct_option_label),
                },
            },
            "query_spec": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "query_id_probabilities": dict(query_probs),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_probs),
                    "option_labels": [str(option.option_label) for option in dataset.options],
                    "answer_support": [str(option.option_label) for option in dataset.options],
                },
            },
            "render_spec": {
                "canvas_width": int(image.width),
                "canvas_height": int(image.height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "post_image_noise": dict(post_noise_meta),
                "label_style": {
                    "font": _font_trace_record(str(font_family)),
                },
                **dict(render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "face_bboxes_px": dict(render_meta["face_bboxes_px"]),
                "option_panel_bboxes_px": dict(render_meta["option_panel_bboxes_px"]),
                "evidence_source": "face_bboxes_px+option_panel_bboxes_px",
            },
            "execution_trace": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "face_labels": dict(dataset.face_labels),
                "net_coords": {str(face): [int(coord[0]), int(coord[1])] for face, coord in NET_COORDS.items()},
                "reference_face": str(dataset.reference_face),
                "marked_side": dataset.marked_side,
                "correct_face": str(dataset.correct_face),
                "option_specs": _option_specs_for_trace(dataset.options),
                "answer_value": str(dataset.correct_option_label),
            },
            "witness_symbolic": {
                "type": "cube_face_relation",
                "value": {
                    "reference_face": str(dataset.reference_face),
                    "marked_side": dataset.marked_side,
                    "correct_face": str(dataset.correct_face),
                    "correct_option_label": str(dataset.correct_option_label),
                },
            },
            "projected_evidence": _projected_keyed_bbox_map(evidence_bboxes),
            "answer_gt": answer_gt.to_dict(),
            "evidence_gt": evidence_gt.to_dict(),
            "complexity": complexity.to_dict(),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesSpatialCubeRollingResultLabelTask(_CubeSurfaceBaseTask):
    """Select the visible face label after rolling a cube along a path."""

    task_id = ROLLING_RESULT_TASK_ID
    supported_query_ids = ROLLING_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_probs = self._resolve_query_id(params, instance_seed=int(instance_seed))
        scene_variant, scene_probs = self._resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = _sample_rolling_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))
        font_family = _sample_cube_surface_font(
            task_id=self.task_id,
            instance_seed=int(instance_seed),
            params=params,
        )
        with temporary_default_font_family(str(font_family)):
            image, render_meta = _render_rolling_scene(
                dataset=dataset,
                params=params,
                instance_seed=int(instance_seed),
                scene_variant=str(scene_variant),
            )
        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = _prompt_defaults()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_rolling_result_label"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint_rolling_result"]),
                "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
                "json_example": str(prompt_defaults["json_example_rolling_result"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only_option_label"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        option_bbox = render_meta["option_panel_bboxes_px"][f"option_{dataset.correct_option_label}"]
        evidence_bboxes = {
            "start_cube": _round_evidence_bbox(render_meta["start_cube_bbox_px"]),
            "roll_path": _round_evidence_bbox(render_meta["path_panel_bbox_px"]),
            "selected_option": _round_evidence_bbox(option_bbox),
        }
        answer_gt = TypedValue(type="option_letter", value=str(dataset.correct_option_label))
        evidence_gt = TypedValue(type="keyed_bbox_map", value=dict(evidence_bboxes))
        path_norm = normalize_int_with_bounds(len(dataset.path_directions), (_DEFAULTS.rolling_path_length_min, _DEFAULTS.rolling_path_length_max))
        grid_norm = normalize_int_with_bounds(dataset.grid_rows * dataset.grid_cols, (25, 36))
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": clamp_unit_interval(0.55 * grid_norm + 0.45 * path_norm),
                "reasoning_load": clamp_unit_interval(0.50 + 0.28 * path_norm),
                "scene_variant_load": {"clean_net": 0.18, "paper_model": 0.24, "game_mat": 0.26}.get(str(scene_variant), 0.2),
            },
        )
        trace_payload = {
            "scene_ir": {
                "scene_kind": "puzzle_cube_surface_net",
                "scene_id": SCENE_ID,
                "task_id": self.task_id,
                "entities": [
                    {"entity_id": f"face_{face}", "kind": "cube_face", "face_id": str(face), "face_label": str(label)}
                    for face, label in sorted(dataset.face_labels.items())
                ],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "target_slot": str(dataset.target_slot),
                    "correct_face": str(dataset.correct_face),
                    "correct_option_label": str(dataset.correct_option_label),
                },
            },
            "query_spec": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "query_id_probabilities": dict(query_probs),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_probs),
                    "option_labels": [str(option.option_label) for option in dataset.options],
                    "answer_support": [str(option.option_label) for option in dataset.options],
                    "path_length": int(len(dataset.path_directions)),
                },
            },
            "render_spec": {
                "canvas_width": int(image.width),
                "canvas_height": int(image.height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "post_image_noise": dict(post_noise_meta),
                "label_style": {
                    "font": _font_trace_record(str(font_family)),
                },
                **dict(render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "start_cube_bbox_px": list(render_meta["start_cube_bbox_px"]),
                "path_panel_bbox_px": list(render_meta["path_panel_bbox_px"]),
                "path_cell_bboxes_px": dict(render_meta["path_cell_bboxes_px"]),
                "option_panel_bboxes_px": dict(render_meta["option_panel_bboxes_px"]),
                "evidence_source": "start_cube_bbox_px+path_panel_bbox_px+option_panel_bboxes_px",
            },
            "execution_trace": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "face_labels": dict(dataset.face_labels),
                "start_orientation": dict(dataset.start_orientation),
                "final_orientation": dict(dataset.final_orientation),
                "target_slot": str(dataset.target_slot),
                "grid_rows": int(dataset.grid_rows),
                "grid_cols": int(dataset.grid_cols),
                "path_cells": [[int(row), int(col)] for row, col in dataset.path_cells],
                "path_directions": [str(direction) for direction in dataset.path_directions],
                "correct_face": str(dataset.correct_face),
                "option_specs": _option_specs_for_trace(dataset.options),
                "answer_value": str(dataset.correct_option_label),
            },
            "witness_symbolic": {
                "type": "cube_rolling_result",
                "value": {
                    "path_directions": [str(direction) for direction in dataset.path_directions],
                    "target_slot": str(dataset.target_slot),
                    "correct_face": str(dataset.correct_face),
                    "correct_option_label": str(dataset.correct_option_label),
                },
            },
            "projected_evidence": _projected_keyed_bbox_map(evidence_bboxes),
            "answer_gt": answer_gt.to_dict(),
            "evidence_gt": evidence_gt.to_dict(),
            "complexity": complexity.to_dict(),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesSpatialCubeSurfaceNetPathLabelTask(_CubeSurfaceBaseTask):
    """Select a folded cube-net path endpoint or visited-face sequence."""

    task_id = SURFACE_PATH_TASK_ID
    supported_query_ids = SURFACE_PATH_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_probs = self._resolve_query_id(params, instance_seed=int(instance_seed))
        scene_variant, scene_probs = self._resolve_scene_variant(params, instance_seed=int(instance_seed))
        dataset = _sample_surface_path_dataset(query_id=str(query_id), params=params, instance_seed=int(instance_seed))
        font_family = _sample_cube_surface_font(
            task_id=self.task_id,
            instance_seed=int(instance_seed),
            params=params,
        )
        with temporary_default_font_family(str(font_family)):
            image, render_meta = _render_surface_path_scene(
                dataset=dataset,
                params=params,
                instance_seed=int(instance_seed),
                scene_variant=str(scene_variant),
            )
        image, post_noise_meta = apply_post_image_noise(
            image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = _prompt_defaults()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_surface_path_label"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint_surface_path"]),
                "answer_hint": str(prompt_defaults["answer_hint_option_letter"]),
                "json_example": str(prompt_defaults["json_example_surface_path"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only_option_label"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        option_bbox = render_meta["option_panel_bboxes_px"][f"option_{dataset.correct_option_label}"]
        evidence_bboxes = {
            "start_face": _round_evidence_bbox(render_meta["face_bboxes_px"][str(dataset.start_face)]),
            "move_instructions": _round_evidence_bbox(render_meta["instruction_panel_bbox_px"]),
            "selected_option": _round_evidence_bbox(option_bbox),
        }
        answer_gt = TypedValue(type="option_letter", value=str(dataset.correct_option_label))
        evidence_gt = TypedValue(type="keyed_bbox_map", value=dict(evidence_bboxes))
        path_norm = normalize_int_with_bounds(len(dataset.path_sides), (_DEFAULTS.surface_path_step_count_min, _DEFAULTS.surface_path_step_count_max))
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": clamp_unit_interval(0.50 + 0.20 * path_norm),
                "reasoning_load": clamp_unit_interval(0.55 + 0.28 * path_norm + (0.08 if str(query_id) == "folded_path_face_sequence_label" else 0.0)),
                "scene_variant_load": {"clean_net": 0.18, "paper_model": 0.24, "game_mat": 0.26}.get(str(scene_variant), 0.2),
            },
        )
        option_specs: List[Dict[str, Any]]
        if str(query_id) == "folded_path_endpoint_label":
            option_specs = [dict(item) for item in _option_specs_for_trace(dataset.endpoint_options)]
        else:
            option_specs = [dict(item) for item in _sequence_option_specs_for_trace(dataset.sequence_options)]
        trace_payload = {
            "scene_ir": {
                "scene_kind": "puzzle_cube_surface_net",
                "scene_id": SCENE_ID,
                "task_id": self.task_id,
                "entities": [
                    {"entity_id": f"face_{face}", "kind": "cube_net_face", "face_id": str(face), "face_label": str(label)}
                    for face, label in sorted(dataset.face_labels.items())
                ],
                "relations": {
                    "query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "start_face": str(dataset.start_face),
                    "path_sides": [str(side) for side in dataset.path_sides],
                    "face_sequence": [str(face) for face in dataset.face_sequence],
                    "endpoint_face": str(dataset.endpoint_face),
                    "correct_option_label": str(dataset.correct_option_label),
                },
            },
            "query_spec": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "query_id_probabilities": dict(query_probs),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_probs),
                    "path_step_count": int(len(dataset.path_sides)),
                    "option_labels": [str(option["option_label"]) for option in option_specs],
                    "answer_support": [str(option["option_label"]) for option in option_specs],
                },
            },
            "render_spec": {
                "canvas_width": int(image.width),
                "canvas_height": int(image.height),
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "post_image_noise": dict(post_noise_meta),
                "label_style": {
                    "font": _font_trace_record(str(font_family)),
                },
                **dict(render_meta),
            },
            "render_map": {
                "image_id": "img0",
                "face_bboxes_px": dict(render_meta["face_bboxes_px"]),
                "instruction_panel_bbox_px": list(render_meta["instruction_panel_bbox_px"]),
                "option_panel_bboxes_px": dict(render_meta["option_panel_bboxes_px"]),
                "evidence_source": "face_bboxes_px+instruction_panel_bbox_px+option_panel_bboxes_px",
            },
            "execution_trace": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "face_labels": dict(dataset.face_labels),
                "net_coords": {str(face): [int(coord[0]), int(coord[1])] for face, coord in NET_COORDS.items()},
                "start_face": str(dataset.start_face),
                "path_sides": [str(side) for side in dataset.path_sides],
                "face_sequence": [str(face) for face in dataset.face_sequence],
                "face_label_sequence": [str(dataset.face_labels[str(face)]) for face in dataset.face_sequence],
                "endpoint_face": str(dataset.endpoint_face),
                "endpoint_face_label": str(dataset.face_labels[str(dataset.endpoint_face)]),
                "option_specs": option_specs,
                "answer_value": str(dataset.correct_option_label),
            },
            "witness_symbolic": {
                "type": "folded_surface_net_path",
                "value": {
                    "path_sides": [str(side) for side in dataset.path_sides],
                    "face_sequence": [str(face) for face in dataset.face_sequence],
                    "endpoint_face": str(dataset.endpoint_face),
                    "correct_option_label": str(dataset.correct_option_label),
                },
            },
            "projected_evidence": _projected_keyed_bbox_map(evidence_bboxes),
            "answer_gt": answer_gt.to_dict(),
            "evidence_gt": evidence_gt.to_dict(),
            "complexity": complexity.to_dict(),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )
