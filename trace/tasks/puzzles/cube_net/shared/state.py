"""Passive state, constants, and dataclasses for cube-net puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


SCENE_ID = "cube_net"
DOMAIN = "puzzles"

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
class CubeNetDefaults:
    """Stable code fallbacks for scene-level cube-net generation/rendering."""

    canvas_width: int = 1100
    face_relation_canvas_height: int = 760
    rolling_canvas_height: int = 820
    option_count: int = 4
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


DEFAULTS = CubeNetDefaults()


@dataclass(frozen=True)
class FaceOption:
    """One labeled face-answer option card."""

    option_label: str
    face_id: str
    face_label: str


@dataclass(frozen=True)
class PathSequenceOption:
    """One labeled answer option for a folded surface path sequence."""

    option_label: str
    face_ids: Tuple[str, ...]
    face_labels: Tuple[str, ...]


@dataclass(frozen=True)
class FaceRelationDataset:
    """Concrete cube-net relation case sampled before task answer binding."""

    relation_kind: str
    face_labels: Dict[str, str]
    reference_face: str
    marked_side: str | None
    correct_face: str
    options: Tuple[FaceOption, ...]
    correct_option_label: str


@dataclass(frozen=True)
class RollingDataset:
    """Concrete cube rolling case sampled before task answer binding."""

    target_slot: str
    face_labels: Dict[str, str]
    start_orientation: Dict[str, str]
    final_orientation: Dict[str, str]
    grid_rows: int
    grid_cols: int
    path_cells: Tuple[Tuple[int, int], ...]
    path_directions: Tuple[str, ...]
    correct_face: str
    options: Tuple[FaceOption, ...]
    correct_option_label: str


@dataclass(frozen=True)
class SurfacePathDataset:
    """Concrete folded-surface path case with endpoint and sequence options."""

    face_labels: Dict[str, str]
    start_face: str
    path_sides: Tuple[str, ...]
    face_sequence: Tuple[str, ...]
    endpoint_face: str
    endpoint_options: Tuple[FaceOption, ...]
    sequence_options: Tuple[PathSequenceOption, ...]
    endpoint_correct_option_label: str
    sequence_correct_option_label: str


__all__ = [
    "DEFAULTS",
    "DOMAIN",
    "FACE_BY_NORMAL",
    "FACE_IDS",
    "FACE_LABEL_POOL",
    "FaceOption",
    "FaceRelationDataset",
    "NET_COORDS",
    "NORMAL_BY_FACE",
    "OPPOSITE_FACE",
    "PathSequenceOption",
    "ROLL_OFFSETS",
    "SCENE_ID",
    "SCENE_VARIANTS",
    "SIDE_OFFSETS",
    "SurfacePathDataset",
    "RollingDataset",
]
