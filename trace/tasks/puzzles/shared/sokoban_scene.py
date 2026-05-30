"""Shared Sokoban-style grid scene generation and rendering."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from string import ascii_uppercase
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ...shared.color_distance import coerce_rgb as _rgb
from ...shared.drawing import draw_centered_text, draw_rounded_rect
from ...shared.text_rendering import load_font
from ...shared.text_legibility import draw_text_traced
from .common import get_int_param as _get_int, get_int_range as _get_range
from .unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px


Cell = Tuple[int, int]
Color = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]

SOKOBAN_PATH_SEQUENCE_QUERY_IDS: Tuple[str, ...] = (
    "shortest_path_sequence_label",
    "valid_path_sequence_label",
    "blocked_path_sequence_label",
)
SOKOBAN_BOX_TARGET_RELATION_QUERY_IDS: Tuple[str, ...] = (
    "nearest_target_for_marked_box_label",
    "box_closest_to_marked_target_label",
    "box_target_manhattan_rank_label",
)
SUPPORTED_SOKOBAN_QUERY_IDS: Tuple[str, ...] = (
    *SOKOBAN_PATH_SEQUENCE_QUERY_IDS,
    *SOKOBAN_BOX_TARGET_RELATION_QUERY_IDS,
)
SUPPORTED_SOKOBAN_SCENE_VARIANTS: Tuple[str, ...] = (
    "warehouse_classic",
    "paper_grid",
    "cool_room",
)

_DIRECTIONS: Mapping[str, Cell] = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}
_DIRECTION_NAMES: Mapping[str, str] = {
    "U": "up",
    "D": "down",
    "L": "left",
    "R": "right",
}
_SCENE_STYLES: Mapping[str, Dict[str, Color]] = {
    "warehouse_classic": {
        "panel": (248, 242, 231),
        "floor": (225, 194, 150),
        "floor_alt": (230, 203, 165),
        "wall": (190, 122, 58),
        "wall_dark": (130, 80, 42),
        "grid": (151, 105, 70),
        "border": (92, 70, 54),
        "box": (128, 72, 37),
        "box_light": (159, 91, 47),
        "target": (44, 157, 66),
        "player": (16, 18, 22),
        "option": (253, 250, 244),
        "accent": (54, 105, 178),
    },
    "paper_grid": {
        "panel": (248, 249, 252),
        "floor": (250, 247, 239),
        "floor_alt": (253, 250, 244),
        "wall": (150, 158, 170),
        "wall_dark": (94, 104, 118),
        "grid": (190, 198, 207),
        "border": (82, 91, 105),
        "box": (145, 100, 65),
        "box_light": (180, 128, 82),
        "target": (51, 149, 112),
        "player": (22, 25, 30),
        "option": (252, 253, 255),
        "accent": (176, 79, 86),
    },
    "cool_room": {
        "panel": (242, 248, 252),
        "floor": (224, 235, 243),
        "floor_alt": (232, 242, 248),
        "wall": (94, 132, 158),
        "wall_dark": (50, 79, 102),
        "grid": (156, 181, 199),
        "border": (58, 78, 94),
        "box": (135, 91, 72),
        "box_light": (171, 120, 91),
        "target": (60, 153, 119),
        "player": (18, 24, 30),
        "option": (250, 253, 255),
        "accent": (205, 132, 55),
    },
}


@dataclass(frozen=True)
class SokobanRenderParams:
    """Resolved visual parameters for one Sokoban panel."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_top_px: int
    board_panel_width_px: int
    board_panel_height_px: int
    option_panel_width_px: int
    option_panel_height_px: int
    option_gap_px: int
    option_row_gap_px: int
    panel_corner_radius_px: int
    board_border_width_px: int
    grid_width_px: int
    coord_gutter_px: int
    main_cell_size_px: int
    mini_cell_size_px: int
    option_label_font_size_px: int
    cell_label_font_size_px: int
    sequence_font_size_px: int
    text_color_rgb: Color
    text_stroke_rgb: Color
    style_overrides: Dict[str, Color]
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class RenderedSokobanScene:
    """Rendered Sokoban scene with traceable geometry."""

    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    scene_bbox_px: BBox
    board_bbox_px: BBox
    option_panel_bbox_map: Dict[str, BBox]
    cell_bbox_map: Dict[str, BBox]


def _int_value(mapping: Mapping[str, Any], key: str, fallback: int) -> int:
    return int(mapping.get(str(key), int(fallback)))


def resolve_sokoban_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    instance_seed: int | None = None,
) -> SokobanRenderParams:
    """Resolve Sokoban render parameters from task/group config."""

    merged = dict(render_defaults)
    merged.update(dict(params))
    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=instance_seed,
        namespace="puzzles.sokoban.unit_size",
    )
    return SokobanRenderParams(
        canvas_width=_int_value(merged, "canvas_width", 1220),
        canvas_height=_int_value(merged, "canvas_height", 900),
        scene_margin_left_px=_int_value(merged, "scene_margin_left_px", 52),
        scene_margin_top_px=_int_value(merged, "scene_margin_top_px", 48),
        board_panel_width_px=_int_value(merged, "board_panel_width_px", 650),
        board_panel_height_px=_int_value(merged, "board_panel_height_px", 740),
        option_panel_width_px=_int_value(merged, "option_panel_width_px", 188),
        option_panel_height_px=_int_value(merged, "option_panel_height_px", 170),
        option_gap_px=_int_value(merged, "option_gap_px", 20),
        option_row_gap_px=_int_value(merged, "option_row_gap_px", 20),
        panel_corner_radius_px=scale_puzzle_px(_int_value(merged, "panel_corner_radius_px", 22), unit_scale, min_px=8),
        board_border_width_px=scale_puzzle_px(_int_value(merged, "board_border_width_px", 4), unit_scale, min_px=2),
        grid_width_px=scale_puzzle_px(_int_value(merged, "grid_width_px", 2), unit_scale, min_px=1),
        coord_gutter_px=scale_puzzle_px(_int_value(merged, "coord_gutter_px", 34), unit_scale, min_px=16),
        main_cell_size_px=scale_puzzle_px(_int_value(merged, "main_cell_size_px", 58), unit_scale, min_px=22),
        mini_cell_size_px=scale_puzzle_px(_int_value(merged, "mini_cell_size_px", 16), unit_scale, min_px=7),
        option_label_font_size_px=scale_puzzle_px(_int_value(merged, "option_label_font_size_px", 28), unit_scale, min_px=14),
        cell_label_font_size_px=scale_puzzle_px(_int_value(merged, "cell_label_font_size_px", 18), unit_scale, min_px=10),
        sequence_font_size_px=scale_puzzle_px(_int_value(merged, "sequence_font_size_px", 22), unit_scale, min_px=11),
        text_color_rgb=_rgb(merged.get("text_color_rgb"), (28, 32, 38)),
        text_stroke_rgb=_rgb(merged.get("text_stroke_rgb"), (255, 255, 255)),
        style_overrides={},
        unit_size_jitter=dict(unit_meta),
    )


def _cell_id(cell: Cell) -> str:
    return f"cell_r{int(cell[0])}_c{int(cell[1])}"


def _box_id(label: str) -> str:
    return f"box_{label}"


def _target_id(label: str) -> str:
    return f"target_{label}"


def _option_id(label: str) -> str:
    return f"option_{label}"


def _add(a: Cell, b: Cell) -> Cell:
    return int(a[0] + b[0]), int(a[1] + b[1])


def _inside(rows: int, cols: int, cell: Cell) -> bool:
    return 0 <= int(cell[0]) < int(rows) and 0 <= int(cell[1]) < int(cols)


def _neighbors(rows: int, cols: int, cell: Cell) -> Iterable[Cell]:
    for delta in _DIRECTIONS.values():
        nxt = _add(cell, delta)
        if _inside(rows, cols, nxt):
            yield nxt


def _connected_components(rows: int, cols: int, walls: set[Cell]) -> List[List[Cell]]:
    seen: set[Cell] = set()
    components: List[List[Cell]] = []
    for row in range(int(rows)):
        for col in range(int(cols)):
            cell = (row, col)
            if cell in walls or cell in seen:
                continue
            queue: deque[Cell] = deque([cell])
            seen.add(cell)
            comp: List[Cell] = []
            while queue:
                cur = queue.popleft()
                comp.append(cur)
                for nxt in _neighbors(rows, cols, cur):
                    if nxt not in walls and nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
            components.append(comp)
    return components


def _largest_component(rows: int, cols: int, walls: set[Cell]) -> List[Cell]:
    components = _connected_components(rows, cols, walls)
    return max(components, key=len) if components else []


def _sample_base_board(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    open_bias: bool = False,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), namespace)
    row_min, row_max = _get_range(
        params,
        gen_defaults,
        min_key="board_rows_min",
        max_key="board_rows_max",
        fallback_min=6,
        fallback_max=9,
    )
    col_min, col_max = _get_range(
        params,
        gen_defaults,
        min_key="board_cols_min",
        max_key="board_cols_max",
        fallback_min=6,
        fallback_max=9,
    )
    wall_min, wall_max = _get_range(
        params,
        gen_defaults,
        min_key="internal_wall_count_min",
        max_key="internal_wall_count_max",
        fallback_min=2,
        fallback_max=9,
    )
    if open_bias:
        wall_max = max(0, min(int(wall_max), 4))
    for _attempt in range(256):
        rows = int(rng.randint(row_min, row_max))
        cols = int(rng.randint(col_min, col_max))
        walls: set[Cell] = set()
        for row in range(rows):
            walls.add((row, 0))
            walls.add((row, cols - 1))
        for col in range(cols):
            walls.add((0, col))
            walls.add((rows - 1, col))
        interior = [(row, col) for row in range(1, rows - 1) for col in range(1, cols - 1)]
        rng.shuffle(interior)
        wall_count = int(rng.randint(wall_min, wall_max))
        walls.update(interior[: min(wall_count, max(0, len(interior) // 4))])
        component = _largest_component(rows, cols, walls)
        if len(component) >= max(12, int(0.55 * (rows - 2) * (cols - 2))):
            return {
                "rows": int(rows),
                "cols": int(cols),
                "walls": set(walls),
                "component": list(component),
            }
    raise ValueError("could not sample connected Sokoban board")


def _shortest_path(passable: set[Cell], start: Cell, goal: Cell) -> List[Cell] | None:
    if start not in passable or goal not in passable:
        return None
    queue: deque[Cell] = deque([start])
    parent: Dict[Cell, Cell | None] = {start: None}
    while queue:
        cur = queue.popleft()
        if cur == goal:
            path: List[Cell] = []
            walk: Cell | None = cur
            while walk is not None:
                path.append(walk)
                walk = parent[walk]
            return list(reversed(path))
        for delta in _DIRECTIONS.values():
            nxt = _add(cur, delta)
            if nxt in passable and nxt not in parent:
                parent[nxt] = cur
                queue.append(nxt)
    return None


def _moves_from_path(path: Sequence[Cell]) -> List[str]:
    moves: List[str] = []
    reverse = {delta: key for key, delta in _DIRECTIONS.items()}
    for prev, nxt in zip(path, path[1:]):
        delta = (int(nxt[0] - prev[0]), int(nxt[1] - prev[1]))
        moves.append(str(reverse[delta]))
    return moves


def _sequence_text(moves: Sequence[str]) -> str:
    return " ".join(str(move) for move in moves)


def _sequence_description(moves: Sequence[str]) -> str:
    return ", ".join(_DIRECTION_NAMES.get(str(move), str(move)) for move in moves)


def _choose_option_labels(option_count: int) -> List[str]:
    return list(ascii_uppercase[: int(option_count)])


def _assign_option_labels(
    *,
    correct: Dict[str, Any],
    distractors: Sequence[Dict[str, Any]],
    option_count: int,
    instance_seed: int,
    cycle_stride: int = 3,
) -> Tuple[List[Dict[str, Any]], str]:
    labels = _choose_option_labels(option_count)
    # Query branches are balanced on consecutive sampling indices, so advance
    # the answer-label cycle by the number of public query branches. This keeps
    # each query branch from collapsing onto a small subset of option letters.
    correct_index = (int(instance_seed) // max(1, int(cycle_stride))) % int(option_count)
    option_specs: List[Dict[str, Any]] = []
    distractor_iter = iter(list(distractors))
    for index, label in enumerate(labels):
        payload = dict(correct) if int(index) == int(correct_index) else dict(next(distractor_iter))
        payload["option_label"] = str(label)
        payload["is_correct"] = bool(int(index) == int(correct_index))
        payload["option_id"] = _option_id(str(label))
        option_specs.append(payload)
    return option_specs, str(labels[correct_index])


def _sample_distinct_cells(
    rng,
    cells: Sequence[Cell],
    count: int,
    *,
    forbidden: Iterable[Cell] = (),
) -> List[Cell]:
    forbidden_set = set(forbidden)
    candidates = [tuple(cell) for cell in cells if tuple(cell) not in forbidden_set]
    rng.shuffle(candidates)
    if len(candidates) < int(count):
        raise ValueError("not enough available Sokoban cells")
    return candidates[: int(count)]


def _candidate_cell_distractors(
    *,
    correct_cell: Cell,
    cells: Sequence[Cell],
    count: int,
    rng,
) -> List[Cell]:
    candidates = [tuple(cell) for cell in cells if tuple(cell) != tuple(correct_cell)]
    candidates.sort(key=lambda cell: (abs(cell[0] - correct_cell[0]) + abs(cell[1] - correct_cell[1]), cell[0], cell[1]))
    near = candidates[: max(count * 3, count)]
    rng.shuffle(near)
    selected = near[: int(count)]
    if len(selected) < int(count):
        rest = [cell for cell in candidates if cell not in set(selected)]
        rng.shuffle(rest)
        selected.extend(rest[: int(count) - len(selected)])
    return selected[: int(count)]


def _simulate_grid_path(passable: set[Cell], start: Cell, moves: Sequence[str]) -> Dict[str, Any]:
    cur = tuple(start)
    path = [cur]
    blocked_at = None
    for idx, move in enumerate([str(item) for item in moves], start=1):
        nxt = _add(cur, _DIRECTIONS[str(move)])
        if nxt not in passable:
            blocked_at = int(idx)
            path.append(nxt)
            break
        cur = nxt
        path.append(cur)
    return {"end": cur, "path": path, "blocked_at_step": blocked_at}


def _mutated_sequence(base: Sequence[str], rng, *, alphabet: Sequence[str] = tuple(_DIRECTIONS.keys())) -> List[str]:
    seq = [str(item) for item in base]
    if not seq:
        return [str(alphabet[int(rng.randrange(len(alphabet)))])]
    op = int(rng.randrange(3))
    if op == 0:
        idx = int(rng.randrange(len(seq)))
        choices = [move for move in alphabet if move != seq[idx]]
        seq[idx] = str(choices[int(rng.randrange(len(choices)))])
    elif op == 1 and len(seq) > 2:
        del seq[int(rng.randrange(len(seq)))]
    else:
        seq.insert(int(rng.randrange(len(seq) + 1)), str(alphabet[int(rng.randrange(len(alphabet)))]))
    return seq


def _build_path_sequence_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.path.{query_id}")
    option_count = _get_int(params, gen_defaults, "option_count", 6)
    dist_min, dist_max = _get_range(
        params,
        gen_defaults,
        min_key="path_length_min",
        max_key="path_length_max",
        fallback_min=4,
        fallback_max=12,
    )
    for attempt in range(256):
        board = _sample_base_board(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed) + attempt,
            namespace=f"{task_id}.path.board",
            open_bias=False,
        )
        rows, cols, walls = int(board["rows"]), int(board["cols"]), set(board["walls"])
        component = list(board["component"])
        box_count = int(rng.randint(1, 3))
        boxes_cells = _sample_distinct_cells(rng, component, box_count, forbidden=())
        boxes = {f"B{idx}": tuple(cell) for idx, cell in enumerate(boxes_cells, start=1)}
        passable = set(component) - set(boxes.values())
        candidate_pairs = []
        shuffled = list(passable)
        rng.shuffle(shuffled)
        for start in shuffled[: min(len(shuffled), 36)]:
            for goal in shuffled:
                if start == goal:
                    continue
                path = _shortest_path(passable, start, goal)
                if path is None:
                    continue
                length = len(path) - 1
                if dist_min <= length <= dist_max:
                    candidate_pairs.append((start, goal, path))
            if candidate_pairs:
                break
        if not candidate_pairs:
            continue
        start, goal, path = candidate_pairs[int(rng.randrange(len(candidate_pairs)))]
        shortest_moves = _moves_from_path(path)
        if str(query_id) == "valid_path_sequence_label":
            correct_moves = list(shortest_moves)
            if len(path) >= 2:
                back = path[-2]
                out_move = _moves_from_path([goal, back])[0]
                in_move = _moves_from_path([back, goal])[0]
                correct_moves = list(shortest_moves) + [out_move, in_move]
            correct_kind = "valid_path"
        elif str(query_id) == "blocked_path_sequence_label":
            prefix = list(shortest_moves[: max(1, len(shortest_moves) // 2)])
            prefix_end = _simulate_grid_path(passable, start, prefix)["end"]
            blocked_moves = [
                move
                for move, delta in _DIRECTIONS.items()
                if _add(prefix_end, delta) not in passable
            ]
            if not blocked_moves:
                continue
            correct_moves = prefix + [str(blocked_moves[int(rng.randrange(len(blocked_moves)))])]
            correct_kind = "blocked_path"
        else:
            correct_moves = list(shortest_moves)
            correct_kind = "shortest_path"
        seen = {_sequence_text(correct_moves)}
        distractors: List[Dict[str, Any]] = []
        for _ in range(512):
            if len(distractors) >= option_count - 1:
                break
            if str(query_id) == "blocked_path_sequence_label":
                candidate = _mutated_sequence(shortest_moves, rng)
                sim = _simulate_grid_path(passable, start, candidate)
                if sim["blocked_at_step"] is not None:
                    continue
            else:
                candidate = _mutated_sequence(shortest_moves, rng)
                sim = _simulate_grid_path(passable, start, candidate)
                if sim["blocked_at_step"] is None and sim["end"] == goal and (
                    str(query_id) != "shortest_path_sequence_label" or len(candidate) == len(shortest_moves)
                ):
                    continue
            key = _sequence_text(candidate)
            if key in seen:
                continue
            seen.add(key)
            distractors.append({"kind": "move_sequence", "moves": list(candidate), "display_text": _sequence_text(candidate)})
        if len(distractors) < option_count - 1:
            continue
        correct = {"kind": "move_sequence", "moves": list(correct_moves), "display_text": _sequence_text(correct_moves)}
        option_specs, answer_label = _assign_option_labels(
            correct=correct,
            distractors=distractors,
            option_count=option_count,
            instance_seed=int(instance_seed),
        )
        return {
            "objective_contract": "path_sequence_label",
            "query_id": str(query_id),
            "rows": rows,
            "cols": cols,
            "walls": sorted([list(cell) for cell in walls]),
            "component_cells": sorted([list(cell) for cell in component]),
            "player_start": list(start),
            "boxes_start": {label: list(cell) for label, cell in sorted(boxes.items())},
            "targets": {"G": list(goal)},
            "path_start": list(start),
            "path_goal": list(goal),
            "shortest_path_cells": [list(cell) for cell in path],
            "shortest_moves": list(shortest_moves),
            "correct_sequence_kind": str(correct_kind),
            "move_sequence": list(correct_moves),
            "move_sequence_text": _sequence_text(correct_moves),
            "move_sequence_description": _sequence_description(correct_moves),
            "option_count": int(option_count),
            "option_specs": option_specs,
            "answer_option_label": str(answer_label),
            "solver_trace": {
                "passable_cells": sorted([list(cell) for cell in passable]),
                "correct_sequence_simulation": _simulate_grid_path(passable, start, correct_moves),
            },
        }
    raise ValueError(f"could not build Sokoban path-sequence dataset for {query_id}")


def _manhattan(a: Cell, b: Cell) -> int:
    return abs(int(a[0] - b[0])) + abs(int(a[1] - b[1]))


def _build_relation_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    rng = spawn_rng(int(instance_seed), f"{task_id}.relation.{query_id}")
    option_count = _get_int(params, gen_defaults, "option_count", 6)
    for attempt in range(256):
        needed = 2 * option_count + 1 if str(query_id) == "box_target_manhattan_rank_label" else option_count + 2
        board = _sample_base_board(
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed) + attempt,
            namespace=f"{task_id}.relation.board",
            open_bias=True,
        )
        rows, cols, walls = int(board["rows"]), int(board["cols"]), set(board["walls"])
        component = list(board["component"])
        if len(component) < int(needed):
            continue
        cells = _sample_distinct_cells(rng, component, needed, forbidden=())
        player = tuple(cells[0])
        if str(query_id) == "nearest_target_for_marked_box_label":
            boxes = {"B1": tuple(cells[1])}
            targets = {f"T{idx}": tuple(cell) for idx, cell in enumerate(cells[2 : 2 + option_count], start=1)}
            distances = {label: _manhattan(boxes["B1"], cell) for label, cell in targets.items()}
            if len(set(distances.values())) < len(distances):
                continue
            answer_target = min(distances, key=lambda label: distances[label])
            correct = {
                "kind": "target_label",
                "display_text": str(answer_target),
                "target_label": str(answer_target),
                "candidate_cells": [list(targets[str(answer_target)])],
            }
            distractors = [
                {
                    "kind": "target_label",
                    "display_text": str(label),
                    "target_label": str(label),
                    "candidate_cells": [list(targets[str(label)])],
                }
                for label in sorted(targets)
                if label != answer_target
            ]
            marked_box_label = "B1"
            marked_target_label = ""
            support = {"answer_target_label": str(answer_target), "distances": dict(distances)}
        elif str(query_id) == "box_closest_to_marked_target_label":
            target = tuple(cells[1])
            targets = {"T1": target}
            boxes = {f"B{idx}": tuple(cell) for idx, cell in enumerate(cells[2 : 2 + option_count], start=1)}
            distances = {label: _manhattan(cell, target) for label, cell in boxes.items()}
            if len(set(distances.values())) < len(distances):
                continue
            answer_box = min(distances, key=lambda label: distances[label])
            correct = {
                "kind": "box_label",
                "display_text": str(answer_box),
                "box_label": str(answer_box),
                "candidate_cells": [list(boxes[str(answer_box)])],
            }
            distractors = [
                {
                    "kind": "box_label",
                    "display_text": str(label),
                    "box_label": str(label),
                    "candidate_cells": [list(boxes[str(label)])],
                }
                for label in sorted(boxes)
                if label != answer_box
            ]
            marked_box_label = ""
            marked_target_label = "T1"
            support = {"answer_box_label": str(answer_box), "distances": dict(distances)}
        else:
            box_cells = cells[1 : 1 + option_count]
            target_cells = cells[1 + option_count : 1 + (2 * option_count)]
            boxes = {f"B{idx}": tuple(cell) for idx, cell in enumerate(box_cells, start=1)}
            targets = {f"T{idx}": tuple(cell) for idx, cell in enumerate(target_cells, start=1)}
            paired_labels = [
                (f"B{idx}", f"T{idx}", _manhattan(boxes[f"B{idx}"], targets[f"T{idx}"]))
                for idx in range(1, option_count + 1)
            ]
            if len(set(dist for _b, _t, dist in paired_labels)) < len(paired_labels):
                continue
            pair_options = sorted(paired_labels, key=lambda item: (item[2], item[0], item[1]))
            rank = 2 + (int(instance_seed) % min(3, option_count - 1))
            answer_pair = pair_options[rank - 1]
            correct = {
                "kind": "pair_label",
                "display_text": f"{answer_pair[0]}-{answer_pair[1]}",
                "box_label": str(answer_pair[0]),
                "target_label": str(answer_pair[1]),
                "candidate_cells": [list(boxes[str(answer_pair[0])]), list(targets[str(answer_pair[1])])],
            }
            distractors = [
                {
                    "kind": "pair_label",
                    "display_text": f"{box_label}-{target_label}",
                    "box_label": str(box_label),
                    "target_label": str(target_label),
                    "candidate_cells": [list(boxes[str(box_label)]), list(targets[str(target_label)])],
                }
                for box_label, target_label, _dist in pair_options
                if (box_label, target_label) != (answer_pair[0], answer_pair[1])
            ]
            marked_box_label = ""
            marked_target_label = ""
            support = {
                "rank": int(rank),
                "rank_word": {2: "second", 3: "third", 4: "fourth"}.get(int(rank), str(rank)),
                "answer_pair": [str(answer_pair[0]), str(answer_pair[1])],
                "pair_distances": [
                    {"box_label": str(b), "target_label": str(t), "distance": int(d)}
                    for b, t, d in paired_labels
                ],
            }
        if len(distractors) < option_count - 1:
            continue
        option_specs, answer_label = _assign_option_labels(
            correct=correct,
            distractors=distractors,
            option_count=option_count,
            instance_seed=int(instance_seed),
        )
        return {
            "objective_contract": "box_target_relation_label",
            "query_id": str(query_id),
            "rows": rows,
            "cols": cols,
            "walls": sorted([list(cell) for cell in walls]),
            "component_cells": sorted([list(cell) for cell in component]),
            "player_start": list(player),
            "boxes_start": {label: list(cell) for label, cell in sorted(boxes.items())},
            "targets": {label: list(cell) for label, cell in sorted(targets.items())},
            "marked_box_label": str(marked_box_label),
            "marked_target_label": str(marked_target_label),
            "relation_support": support,
            "option_count": int(option_count),
            "option_specs": option_specs[:option_count],
            "answer_option_label": str(answer_label),
            "solver_trace": dict(support),
        }
    raise ValueError(f"could not build Sokoban relation dataset for {query_id}")


def build_sokoban_dataset(
    *,
    query_id: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Dict[str, Any]:
    """Build one symbolic Sokoban dataset for a selected query id."""

    if str(query_id) in SOKOBAN_PATH_SEQUENCE_QUERY_IDS:
        return _build_path_sequence_dataset(
            query_id=str(query_id),
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(task_id),
        )
    if str(query_id) in SOKOBAN_BOX_TARGET_RELATION_QUERY_IDS:
        return _build_relation_dataset(
            query_id=str(query_id),
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
            task_id=str(task_id),
        )
    raise ValueError(f"unsupported Sokoban query id: {query_id}")


def _bbox_union(boxes: Iterable[Sequence[float]]) -> BBox:
    items = [tuple(float(value) for value in box) for box in boxes]
    if not items:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        round(min(box[0] for box in items), 3),
        round(min(box[1] for box in items), 3),
        round(max(box[2] for box in items), 3),
        round(max(box[3] for box in items), 3),
    )


def _cell_bbox(origin: Tuple[float, float], cell_size: float, cell: Cell) -> BBox:
    x0 = float(origin[0] + (cell[1] * cell_size))
    y0 = float(origin[1] + (cell[0] * cell_size))
    return (round(x0, 3), round(y0, 3), round(x0 + cell_size, 3), round(y0 + cell_size, 3))


def _draw_x(draw: ImageDraw.ImageDraw, bbox: BBox, *, fill: Color, width: int) -> None:
    pad = max(3.0, min(float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1])) * 0.22)
    draw.line((bbox[0] + pad, bbox[1] + pad, bbox[2] - pad, bbox[3] - pad), fill=fill, width=max(1, int(width)))
    draw.line((bbox[0] + pad, bbox[3] - pad, bbox[2] - pad, bbox[1] + pad), fill=fill, width=max(1, int(width)))


def _draw_player(draw: ImageDraw.ImageDraw, bbox: BBox, *, fill: Color, width: int) -> None:
    cx = (float(bbox[0]) + float(bbox[2])) * 0.5
    cy = (float(bbox[1]) + float(bbox[3])) * 0.5
    size = min(float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1]))
    head_r = size * 0.13
    draw.ellipse((cx - head_r, cy - size * 0.29, cx + head_r, cy - size * 0.03), fill=fill)
    draw.line((cx, cy - size * 0.02, cx, cy + size * 0.24), fill=fill, width=max(1, int(width)))
    draw.line((cx - size * 0.18, cy + size * 0.06, cx + size * 0.18, cy + size * 0.06), fill=fill, width=max(1, int(width)))
    draw.line((cx, cy + size * 0.24, cx - size * 0.16, cy + size * 0.42), fill=fill, width=max(1, int(width)))
    draw.line((cx, cy + size * 0.24, cx + size * 0.16, cy + size * 0.42), fill=fill, width=max(1, int(width)))


def _draw_option_badge(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: BBox,
    label: str,
    style: Mapping[str, Color],
    params: SokobanRenderParams,
) -> None:
    size = min(float(bbox[2] - bbox[0]), float(bbox[3] - bbox[1]))
    radius = size * 0.24
    cx = (float(bbox[0]) + float(bbox[2])) * 0.5
    cy = (float(bbox[1]) + float(bbox[3])) * 0.5
    badge = (cx - radius, cy - radius, cx + radius, cy + radius)
    font = load_font(max(10, int(size * 0.34)), bold=True)
    draw.ellipse(badge, fill=(255, 255, 255), outline=style["accent"], width=max(2, int(size * 0.06)))
    draw_centered_text(
        draw,
        text=str(label),
        center=(cx, cy),
        font=font,
        fill=params.text_color_rgb,
        stroke_fill=params.text_stroke_rgb,
        stroke_width=1,
    )


def _draw_relation_option_overlays(
    draw: ImageDraw.ImageDraw,
    *,
    dataset: Mapping[str, Any],
    cell_bbox_map: Mapping[str, BBox],
    style: Mapping[str, Color],
    params: SokobanRenderParams,
) -> None:
    option_specs = list(dataset.get("option_specs", []))
    for option in option_specs:
        cells = [tuple(cell) for cell in option.get("candidate_cells", [])]
        for cell in cells:
            bbox = cell_bbox_map.get(_cell_id(cell))
            if bbox is None:
                continue
            _draw_option_badge(
                draw,
                bbox=bbox,
                label=str(option.get("option_label", "")),
                style=style,
                params=params,
            )


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    bbox: BBox,
    *,
    fill: Color,
    stroke_fill: Color,
    max_size: int,
    min_size: int = 10,
    bold: bool = True,
) -> None:
    words = str(text).split()
    if not words:
        return
    for size in range(int(max_size), int(min_size) - 1, -1):
        font = load_font(size, bold=bold)
        lines: List[str] = []
        current = ""
        max_width = float(bbox[2] - bbox[0]) - 10.0
        for word in words:
            candidate = f"{current} {word}".strip()
            width = draw.textbbox((0, 0), candidate, font=font, stroke_width=1)[2]
            if width <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        line_height = max(10, int(size * 1.18))
        total_height = line_height * len(lines)
        if total_height <= float(bbox[3] - bbox[1]) - 8:
            y = float(bbox[1]) + (float(bbox[3] - bbox[1]) - total_height) * 0.5
            for line in lines:
                text_bbox = draw.textbbox((0, 0), line, font=font, stroke_width=1)
                x = float(bbox[0]) + (float(bbox[2] - bbox[0]) - float(text_bbox[2] - text_bbox[0])) * 0.5
                draw_text_traced(draw,(x, y), line, fill=fill, font=font, stroke_width=1, stroke_fill=stroke_fill, role="readout", required=False)
                y += line_height
            return


def _draw_board(
    draw: ImageDraw.ImageDraw,
    *,
    rows: int,
    cols: int,
    walls: set[Cell],
    boxes: Mapping[str, Cell],
    targets: Mapping[str, Cell],
    player: Cell | None,
    origin: Tuple[float, float],
    cell_size: float,
    style: Mapping[str, Color],
    params: SokobanRenderParams,
    show_coordinates: bool,
    show_labels: bool,
    marked_box_label: str = "",
    marked_target_label: str = "",
    start_cell: Cell | None = None,
    goal_cell: Cell | None = None,
    candidate_cell: Cell | None = None,
) -> Dict[str, BBox]:
    cell_bbox_map: Dict[str, BBox] = {}
    label_font = load_font(max(9, int(cell_size * 0.30)), bold=True)
    small_font = load_font(max(8, int(cell_size * 0.24)), bold=True)
    for row in range(int(rows)):
        for col in range(int(cols)):
            cell = (row, col)
            bbox = _cell_bbox(origin, cell_size, cell)
            cell_bbox_map[_cell_id(cell)] = bbox
            fill = style["wall"] if cell in walls else (style["floor_alt"] if (row + col) % 2 else style["floor"])
            outline = style["grid"] if cell not in walls else style["wall_dark"]
            draw.rectangle(bbox, fill=fill, outline=outline, width=max(1, int(params.grid_width_px)))
    if show_coordinates:
        coord_font = load_font(max(9, int(params.cell_label_font_size_px)), bold=True)
        for col in range(int(cols)):
            bbox = _cell_bbox(origin, cell_size, (0, col))
            draw_centered_text(
                draw,
                text=str(col),
                center=((bbox[0] + bbox[2]) * 0.5, float(origin[1]) - 15),
                font=coord_font,
                fill=params.text_color_rgb,
                stroke_fill=params.text_stroke_rgb,
                stroke_width=1,
            )
        for row in range(int(rows)):
            bbox = _cell_bbox(origin, cell_size, (row, 0))
            draw_centered_text(
                draw,
                text=str(row),
                center=(float(origin[0]) - 16, (bbox[1] + bbox[3]) * 0.5),
                font=coord_font,
                fill=params.text_color_rgb,
                stroke_fill=params.text_stroke_rgb,
                stroke_width=1,
            )
    for target_label, cell in targets.items():
        bbox = cell_bbox_map[_cell_id(tuple(cell))]
        _draw_x(draw, bbox, fill=style["target"], width=max(2, int(cell_size * 0.08)))
        if show_labels:
            draw_centered_text(
                draw,
                text=str(target_label),
                center=(bbox[2] - cell_size * 0.22, bbox[1] + cell_size * 0.22),
                font=small_font,
                fill=params.text_color_rgb,
                stroke_fill=params.text_stroke_rgb,
                stroke_width=1,
            )
        if str(target_label) == str(marked_target_label):
            draw.rectangle(bbox, outline=style["accent"], width=max(3, int(cell_size * 0.08)))
    if start_cell is not None:
        bbox = cell_bbox_map[_cell_id(tuple(start_cell))]
        draw.ellipse(
            (bbox[0] + cell_size * 0.24, bbox[1] + cell_size * 0.24, bbox[2] - cell_size * 0.24, bbox[3] - cell_size * 0.24),
            fill=(255, 255, 255),
            outline=style["accent"],
            width=max(2, int(cell_size * 0.07)),
        )
        draw_centered_text(
            draw,
            text="S",
            center=((bbox[0] + bbox[2]) * 0.5, (bbox[1] + bbox[3]) * 0.5),
            font=label_font,
            fill=style["accent"],
            stroke_fill=(255, 255, 255),
            stroke_width=1,
        )
    if goal_cell is not None:
        bbox = cell_bbox_map[_cell_id(tuple(goal_cell))]
        draw.ellipse(
            (bbox[0] + cell_size * 0.20, bbox[1] + cell_size * 0.20, bbox[2] - cell_size * 0.20, bbox[3] - cell_size * 0.20),
            fill=(255, 255, 255),
            outline=style["target"],
            width=max(2, int(cell_size * 0.07)),
        )
        draw_centered_text(
            draw,
            text="G",
            center=((bbox[0] + bbox[2]) * 0.5, (bbox[1] + bbox[3]) * 0.5),
            font=label_font,
            fill=style["target"],
            stroke_fill=(255, 255, 255),
            stroke_width=1,
        )
    for box_label, cell in boxes.items():
        bbox = cell_bbox_map[_cell_id(tuple(cell))]
        pad = max(3.0, cell_size * 0.12)
        box_bbox = (bbox[0] + pad, bbox[1] + pad, bbox[2] - pad, bbox[3] - pad)
        draw.rectangle(box_bbox, fill=style["box"], outline=style["box_light"], width=max(2, int(cell_size * 0.05)))
        _draw_x(draw, box_bbox, fill=style["wall_dark"], width=max(1, int(cell_size * 0.04)))
        if show_labels:
            draw_centered_text(
                draw,
                text=str(box_label),
                center=((bbox[0] + bbox[2]) * 0.5, (bbox[1] + bbox[3]) * 0.5),
                font=small_font,
                fill=(255, 255, 255),
                stroke_fill=style["wall_dark"],
                stroke_width=1,
            )
        if str(box_label) == str(marked_box_label):
            draw.rectangle(bbox, outline=style["accent"], width=max(3, int(cell_size * 0.08)))
    if player is not None:
        bbox = cell_bbox_map[_cell_id(tuple(player))]
        _draw_player(draw, bbox, fill=style["player"], width=max(2, int(cell_size * 0.05)))
    if candidate_cell is not None:
        bbox = cell_bbox_map[_cell_id(tuple(candidate_cell))]
        draw.ellipse(
            (bbox[0] + cell_size * 0.18, bbox[1] + cell_size * 0.18, bbox[2] - cell_size * 0.18, bbox[3] - cell_size * 0.18),
            outline=style["accent"],
            width=max(3, int(cell_size * 0.10)),
        )
    board_bbox = _bbox_union(cell_bbox_map.values())
    draw.rectangle(board_bbox, outline=style["border"], width=max(2, int(params.board_border_width_px)))
    return cell_bbox_map


def _draw_sokoban_option(
    draw: ImageDraw.ImageDraw,
    *,
    option: Mapping[str, Any],
    bbox: BBox,
    dataset: Mapping[str, Any],
    style: Mapping[str, Color],
    params: SokobanRenderParams,
) -> None:
    draw_rounded_rect(
        draw,
        bbox,
        radius=int(params.panel_corner_radius_px),
        fill=style["option"],
        outline=style["border"],
        width=2,
    )
    label = str(option["option_label"])
    label_font = load_font(int(params.option_label_font_size_px), bold=True)
    draw_centered_text(
        draw,
        text=label,
        center=(float(bbox[0]) + 24, float(bbox[1]) + 24),
        font=label_font,
        fill=params.text_color_rgb,
        stroke_fill=params.text_stroke_rgb,
        stroke_width=1,
    )
    kind = str(option.get("kind", ""))
    if kind == "cell_snapshot":
        rows, cols = int(dataset["rows"]), int(dataset["cols"])
        mini_size = min(
            (float(bbox[2] - bbox[0]) - 26) / max(1, cols),
            (float(bbox[3] - bbox[1]) - 58) / max(1, rows),
            float(params.mini_cell_size_px),
        )
        origin = (
            float(bbox[0]) + (float(bbox[2] - bbox[0]) - mini_size * cols) * 0.5,
            float(bbox[1]) + 48,
        )
        _draw_board(
            draw,
            rows=rows,
            cols=cols,
            walls={tuple(cell) for cell in dataset["walls"]},
            boxes={},
            targets={},
            player=None,
            origin=origin,
            cell_size=mini_size,
            style=style,
            params=params,
            show_coordinates=False,
            show_labels=False,
            candidate_cell=tuple(option["candidate_cell"]),
        )
    else:
        text = str(option.get("display_text", ""))
        _draw_wrapped_text(
            draw,
            text=text,
            bbox=(bbox[0] + 12, bbox[1] + 44, bbox[2] - 12, bbox[3] - 12),
            fill=params.text_color_rgb,
            stroke_fill=params.text_stroke_rgb,
            max_size=int(params.sequence_font_size_px),
            min_size=10,
            bold=True,
        )


def render_sokoban_scene(
    base_image: Image.Image,
    *,
    dataset: Mapping[str, Any],
    scene_variant: str,
    render_params: SokobanRenderParams,
) -> RenderedSokobanScene:
    """Render one Sokoban scene and return traceable bboxes."""

    image = base_image.convert("RGB")
    draw = ImageDraw.Draw(image)
    style = dict(_SCENE_STYLES.get(str(scene_variant), _SCENE_STYLES["warehouse_classic"]))
    style.update({str(key): tuple(value) for key, value in dict(render_params.style_overrides or {}).items()})
    rows, cols = int(dataset["rows"]), int(dataset["cols"])
    is_relation_family = str(dataset.get("objective_contract")) == "box_target_relation_label"
    uses_board_options = is_relation_family
    board_x0 = (
        float(render_params.canvas_width - render_params.board_panel_width_px) * 0.5
        if uses_board_options
        else float(render_params.scene_margin_left_px)
    )
    board_panel = (
        board_x0,
        float(render_params.scene_margin_top_px),
        float(board_x0 + render_params.board_panel_width_px),
        float(render_params.scene_margin_top_px + render_params.board_panel_height_px),
    )
    draw_rounded_rect(
        draw,
        board_panel,
        radius=int(render_params.panel_corner_radius_px),
        fill=style["panel"],
        outline=style["border"],
        width=2,
    )
    available_w = float(render_params.board_panel_width_px - render_params.coord_gutter_px - 42)
    available_h = float(render_params.board_panel_height_px - render_params.coord_gutter_px - 122)
    cell_size = min(float(render_params.main_cell_size_px), available_w / max(1, cols), available_h / max(1, rows))
    board_origin = (
        float(board_panel[0] + render_params.coord_gutter_px + (available_w - (cell_size * cols)) * 0.5),
        float(board_panel[1] + render_params.coord_gutter_px + 34),
    )
    query_id = str(dataset.get("query_id", ""))
    start_cell = tuple(dataset["path_start"]) if "path_start" in dataset else None
    goal_cell = tuple(dataset["path_goal"]) if "path_goal" in dataset else None
    cell_bbox_map = _draw_board(
        draw,
        rows=rows,
        cols=cols,
        walls={tuple(cell) for cell in dataset["walls"]},
        boxes={str(k): tuple(v) for k, v in dict(dataset.get("boxes_start", {})).items()},
        targets={str(k): tuple(v) for k, v in dict(dataset.get("targets", {})).items()},
        player=tuple(dataset["player_start"]) if "player_start" in dataset else None,
        origin=board_origin,
        cell_size=cell_size,
        style=style,
        params=render_params,
        show_coordinates=True,
        show_labels=False,
        marked_box_label=str(dataset.get("marked_box_label", "")),
        marked_target_label=str(dataset.get("marked_target_label", "")),
        start_cell=start_cell,
        goal_cell=goal_cell,
    )
    if is_relation_family:
        _draw_relation_option_overlays(
            draw,
            dataset=dataset,
            cell_bbox_map=cell_bbox_map,
            style=style,
            params=render_params,
        )
    board_bbox = _bbox_union(cell_bbox_map.values())
    title_font = load_font(20, bold=True)
    subtitle_font = load_font(16, bold=False)
    draw_text_traced(draw,(board_panel[0] + 22, board_panel[1] + 16), "Sokoban grid", fill=render_params.text_color_rgb, font=title_font, role="readout", required=False)
    if str(dataset.get("objective_contract")) == "path_sequence_label":
        draw_text_traced(draw,
            (board_panel[0] + 22, board_panel[3] - 56),
            "Move codes: U=up, D=down, L=left, R=right.",
            fill=render_params.text_color_rgb,
            font=subtitle_font,
         role="readout", required=False,)
        draw_text_traced(draw,
            (board_panel[0] + 22, board_panel[3] - 82),
            "Boxes count as blockers for these path options.",
            fill=render_params.text_color_rgb,
            font=subtitle_font,
         role="readout", required=False,)
    elif query_id == "box_target_manhattan_rank_label":
        rank_word = str(dataset.get("relation_support", {}).get("rank_word", "requested"))
        draw_text_traced(draw,
            (board_panel[0] + 22, board_panel[3] - 82),
            f"Compare same-letter box-target pairs; find the {rank_word} closest pair.",
            fill=render_params.text_color_rgb,
            font=subtitle_font,
         role="readout", required=False,)
    option_panel_bbox_map: Dict[str, BBox] = {}
    if not uses_board_options:
        option_x0 = float(board_panel[2] + 34)
        option_y0 = float(board_panel[1] + 16)
        for index, option in enumerate(dataset["option_specs"]):
            col = index % 2
            row = index // 2
            x0 = option_x0 + col * (render_params.option_panel_width_px + render_params.option_gap_px)
            y0 = option_y0 + row * (render_params.option_panel_height_px + render_params.option_row_gap_px)
            bbox = (
                round(x0, 3),
                round(y0, 3),
                round(x0 + render_params.option_panel_width_px, 3),
                round(y0 + render_params.option_panel_height_px, 3),
            )
            _draw_sokoban_option(draw, option=option, bbox=bbox, dataset=dataset, style=style, params=render_params)
            option_panel_bbox_map[_option_id(str(option["option_label"]))] = bbox
    entities: List[Dict[str, Any]] = []
    for cell_key, bbox in cell_bbox_map.items():
        entities.append({"entity_id": cell_key, "type": "sokoban_cell", "bbox_px": list(bbox)})
    for label, cell in dict(dataset.get("boxes_start", {})).items():
        entities.append({"entity_id": _box_id(str(label)), "type": "sokoban_box", "cell": list(cell), "bbox_px": list(cell_bbox_map[_cell_id(tuple(cell))])})
    for label, cell in dict(dataset.get("targets", {})).items():
        entities.append({"entity_id": _target_id(str(label)), "type": "sokoban_target", "cell": list(cell), "bbox_px": list(cell_bbox_map[_cell_id(tuple(cell))])})
    if "player_start" in dataset:
        entities.append({"entity_id": "player", "type": "sokoban_player", "cell": list(dataset["player_start"]), "bbox_px": list(cell_bbox_map[_cell_id(tuple(dataset["player_start"]))])})
    if uses_board_options:
        for option in dataset.get("option_specs", []):
            cells = [tuple(cell) for cell in option.get("candidate_cells", [])]
            if not cells:
                continue
            bboxes = [cell_bbox_map[_cell_id(cell)] for cell in cells]
            entities.append(
                {
                    "entity_id": _option_id(str(option["option_label"])),
                    "type": "sokoban_board_option",
                    "option_label": str(option["option_label"]),
                    "candidate_cells": [list(cell) for cell in cells],
                    "bbox_px": list(_bbox_union(bboxes)),
                }
            )
    for option_id, bbox in option_panel_bbox_map.items():
        entities.append({"entity_id": option_id, "type": "sokoban_option_panel", "bbox_px": list(bbox)})
    scene_bbox = _bbox_union([board_panel, *option_panel_bbox_map.values()])
    return RenderedSokobanScene(
        image=image,
        entities=tuple(entities),
        scene_bbox_px=scene_bbox,
        board_bbox_px=board_bbox,
        option_panel_bbox_map=dict(option_panel_bbox_map),
        cell_bbox_map=dict(cell_bbox_map),
    )


__all__ = [
    "SOKOBAN_BOX_TARGET_RELATION_QUERY_IDS",
    "SOKOBAN_PATH_SEQUENCE_QUERY_IDS",
    "SUPPORTED_SOKOBAN_QUERY_IDS",
    "SUPPORTED_SOKOBAN_SCENE_VARIANTS",
    "SokobanRenderParams",
    "RenderedSokobanScene",
    "build_sokoban_dataset",
    "render_sokoban_scene",
    "resolve_sokoban_render_params",
]
