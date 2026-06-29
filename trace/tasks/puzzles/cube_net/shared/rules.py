"""Cube topology and rolling mechanics for cube-net puzzle scenes."""

from __future__ import annotations

from typing import Dict, Mapping, Sequence, Tuple

from trace.core.sampling import uniform_choice
from trace.core.seed import spawn_rng

from .state import (
    FACE_BY_NORMAL,
    FACE_IDS,
    NET_COORDS,
    ROLL_OFFSETS,
    SIDE_OFFSETS,
)


Vector3 = Tuple[int, int, int]
FaceBasis = Tuple[Vector3, Vector3, Vector3]


def _neg(vec: Sequence[int]) -> Vector3:
    return (-int(vec[0]), -int(vec[1]), -int(vec[2]))


def basis_across_side(
    *,
    normal: Vector3,
    up: Vector3,
    right: Vector3,
    side: str,
) -> FaceBasis:
    """Return the neighboring face basis created by folding across one net edge."""

    if str(side) == "top":
        return tuple(up), _neg(normal), tuple(right)
    if str(side) == "bottom":
        return _neg(up), tuple(normal), tuple(right)
    if str(side) == "right":
        return tuple(right), tuple(up), _neg(normal)
    if str(side) == "left":
        return _neg(right), tuple(up), tuple(normal)
    raise ValueError(f"unsupported side: {side}")


def net_face_bases() -> Dict[str, FaceBasis]:
    """Propagate 3-D face bases from the displayed cube net without task routing."""

    coord_to_face = {tuple(coord): str(face) for face, coord in NET_COORDS.items()}
    bases: Dict[str, FaceBasis] = {
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
            bases[str(neighbor)] = basis_across_side(
                normal=normal,
                up=up,
                right=right,
                side=str(side),
            )
            queue.append(str(neighbor))
    if set(bases) != set(FACE_IDS):
        raise ValueError("cube net basis propagation did not cover all faces")
    return bases


NET_FACE_BASES = net_face_bases()


def face_across_display_side(face_id: str, side: str) -> str:
    """Return the folded cube face across one visible side of a net face."""

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


def roll_orientation(orientation: Mapping[str, str], direction: str) -> Dict[str, str]:
    """Apply one cardinal rolling step to the cube orientation slots."""

    top = str(orientation["top"])
    bottom = str(orientation["bottom"])
    north = str(orientation["north"])
    south = str(orientation["south"])
    west = str(orientation["west"])
    east = str(orientation["east"])
    if str(direction) == "N":
        return {
            "top": south,
            "bottom": north,
            "north": top,
            "south": bottom,
            "west": west,
            "east": east,
        }
    if str(direction) == "S":
        return {
            "top": north,
            "bottom": south,
            "north": bottom,
            "south": top,
            "west": west,
            "east": east,
        }
    if str(direction) == "E":
        return {
            "top": west,
            "bottom": east,
            "north": north,
            "south": south,
            "west": bottom,
            "east": top,
        }
    if str(direction) == "W":
        return {
            "top": east,
            "bottom": west,
            "north": north,
            "south": south,
            "west": top,
            "east": bottom,
        }
    raise ValueError(f"unsupported roll direction: {direction}")


def random_start_orientation(instance_seed: int, namespace: str) -> Dict[str, str]:
    """Sample a valid start orientation by applying random legal roll steps."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.start_orientation")
    orientation = {
        "top": "U",
        "bottom": "D",
        "north": "B",
        "south": "F",
        "west": "L",
        "east": "R",
    }
    for _ in range(int(rng.randrange(1, 7))):
        orientation = roll_orientation(
            orientation,
            str(uniform_choice(rng, tuple(ROLL_OFFSETS.keys()))),
        )
    return dict(orientation)


def sample_roll_path(
    *,
    instance_seed: int,
    rows: int,
    cols: int,
    length: int,
    namespace: str,
) -> Tuple[Tuple[Tuple[int, int], ...], Tuple[str, ...]]:
    """Sample a bounded grid path whose cells and directions are mutually valid."""

    rng = spawn_rng(int(instance_seed), f"{namespace}.path")
    fallback_path: list[tuple[int, int]] = [(0, 0)]
    fallback_dirs: list[str] = []
    for _attempt in range(80):
        row = int(rng.randrange(1, max(2, int(rows) - 1)))
        col = int(rng.randrange(1, max(2, int(cols) - 1)))
        path = [(row, col)]
        dirs: list[str] = []
        previous: str | None = None
        for _step in range(int(length)):
            candidates = []
            for direction, (dr, dc) in ROLL_OFFSETS.items():
                nr = int(row + dr)
                nc = int(col + dc)
                if 0 <= nr < int(rows) and 0 <= nc < int(cols):
                    candidates.append(str(direction))
            if previous is not None and len(candidates) > 1:
                opposite = {"N": "S", "S": "N", "E": "W", "W": "E"}[previous]
                candidates = [item for item in candidates if item != opposite] or candidates
            direction = str(uniform_choice(rng, tuple(candidates)))
            dr, dc = ROLL_OFFSETS[direction]
            row = int(row + dr)
            col = int(col + dc)
            path.append((row, col))
            dirs.append(direction)
            previous = direction
        fallback_path = list(path)
        fallback_dirs = list(dirs)
        if len(set(path)) >= min(4, len(path)):
            return tuple(path), tuple(dirs)
    return tuple(fallback_path), tuple(fallback_dirs)


__all__ = [
    "NET_FACE_BASES",
    "basis_across_side",
    "face_across_display_side",
    "net_face_bases",
    "random_start_orientation",
    "roll_orientation",
    "sample_roll_path",
]
