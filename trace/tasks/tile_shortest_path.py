"""Tile shortest-path task with unique-answer-by-construction generation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from PIL import Image, ImageDraw

from ..core.seed import spawn_rng
from ..core.types import TaskComplexity, TypedValue
from .base import TaskOutput
from .registry import register_task


Coord = Tuple[int, int]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable defaults for the tile shortest-path task."""

    rows: int = 8
    cols: int = 8
    min_shortest_len: int = 6
    obstacle_prob_min: float = 0.16
    obstacle_prob_max: float = 0.36
    canvas_size: int = 640
    margin: int = 24
    evidence_type: str = "point_path"


_DEFAULTS = _TaskDefaults()


def _neighbors(cell: Coord, rows: int, cols: int) -> Iterable[Coord]:
    r, c = cell
    if r > 0:
        yield (r - 1, c)
    if r + 1 < rows:
        yield (r + 1, c)
    if c > 0:
        yield (r, c - 1)
    if c + 1 < cols:
        yield (r, c + 1)


def _bfs_dist_count(rows: int, cols: int, blocked: Sequence[Sequence[bool]], start: Coord) -> Tuple[List[List[int]], List[List[int]]]:
    dist = [[-1 for _ in range(cols)] for _ in range(rows)]
    count = [[0 for _ in range(cols)] for _ in range(rows)]
    sr, sc = start
    dist[sr][sc] = 0
    count[sr][sc] = 1
    queue: deque[Coord] = deque([start])
    while queue:
        r, c = queue.popleft()
        for nr, nc in _neighbors((r, c), rows, cols):
            if blocked[nr][nc]:
                continue
            nd = dist[r][c] + 1
            if dist[nr][nc] == -1:
                dist[nr][nc] = nd
                count[nr][nc] = count[r][c]
                queue.append((nr, nc))
            elif dist[nr][nc] == nd:
                count[nr][nc] += count[r][c]
    return dist, count


def _reconstruct_unique_path(
    rows: int,
    cols: int,
    blocked: Sequence[Sequence[bool]],
    start: Coord,
    goal: Coord,
    dist_start: Sequence[Sequence[int]],
    dist_goal: Sequence[Sequence[int]],
) -> List[Coord] | None:
    shortest = dist_start[goal[0]][goal[1]]
    if shortest < 0:
        return None
    path: List[Coord] = [start]
    cur = start
    while cur != goal:
        r, c = cur
        candidates: List[Coord] = []
        for nr, nc in _neighbors(cur, rows, cols):
            if blocked[nr][nc]:
                continue
            if dist_start[nr][nc] != dist_start[r][c] + 1:
                continue
            if dist_start[nr][nc] + dist_goal[nr][nc] != shortest:
                continue
            candidates.append((nr, nc))
        # Enforce unique witness path semantics for this task.
        if len(candidates) != 1:
            return None
        cur = candidates[0]
        path.append(cur)
    return path


def _cell_id(rc: Coord) -> str:
    return f"cell_{rc[0]}_{rc[1]}"


def _sample_maze(
    rng,
    *,
    rows: int,
    cols: int,
    min_shortest_len: int,
    obstacle_prob_min: float,
    obstacle_prob_max: float,
    max_attempts: int,
) -> Tuple[List[List[bool]], Coord, Coord, List[Coord], int]:
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    for _ in range(max_attempts):
        obstacle_prob = rng.uniform(obstacle_prob_min, obstacle_prob_max)
        blocked = [[rng.random() < obstacle_prob for _ in range(cols)] for _ in range(rows)]

        open_cells = [coord for coord in cells if not blocked[coord[0]][coord[1]]]
        if len(open_cells) < 2:
            continue

        start = rng.choice(open_cells)
        goal = rng.choice(open_cells)
        if start == goal:
            continue

        dist_start, count_start = _bfs_dist_count(rows, cols, blocked, start)
        shortest = dist_start[goal[0]][goal[1]]
        if shortest < min_shortest_len:
            continue
        if count_start[goal[0]][goal[1]] != 1:
            continue

        dist_goal, _ = _bfs_dist_count(rows, cols, blocked, goal)
        path = _reconstruct_unique_path(rows, cols, blocked, start, goal, dist_start, dist_goal)
        if path is None:
            continue
        if len(path) - 1 != shortest:
            continue
        return blocked, start, goal, path, shortest

    raise RuntimeError("failed to sample unique shortest-path maze")


def _render_maze(
    rows: int,
    cols: int,
    blocked: Sequence[Sequence[bool]],
    start: Coord,
    goal: Coord,
    path: Sequence[Coord],
    *,
    canvas_size: int,
    margin: int,
) -> Tuple[Image.Image, Dict[str, Tuple[float, float, float, float]]]:
    usable_w = max(8, canvas_size - 2 * margin)
    usable_h = max(8, canvas_size - 2 * margin)
    cell_size = max(8, min(usable_w // cols, usable_h // rows))
    board_w = cell_size * cols
    board_h = cell_size * rows
    ox = (canvas_size - board_w) // 2
    oy = (canvas_size - board_h) // 2

    image = Image.new("RGB", (canvas_size, canvas_size), (246, 246, 246))
    draw = ImageDraw.Draw(image)

    path_set = set(path)
    bbox_map: Dict[str, Tuple[float, float, float, float]] = {}

    for r in range(rows):
        for c in range(cols):
            x0 = ox + c * cell_size
            y0 = oy + r * cell_size
            x1 = x0 + cell_size
            y1 = y0 + cell_size
            cell = (r, c)
            fill = (255, 255, 255)
            if blocked[r][c]:
                fill = (20, 20, 20)
            elif cell in path_set:
                fill = (164, 211, 255)
            draw.rectangle([x0, y0, x1, y1], fill=fill, outline=(110, 110, 110), width=1)
            bbox_map[_cell_id(cell)] = (float(x0), float(y0), float(x1), float(y1))

    for rc, color in ((start, (36, 149, 59)), (goal, (190, 44, 44))):
        x0, y0, x1, y1 = bbox_map[_cell_id(rc)]
        cx = (x0 + x1) / 2.0
        cy = (y0 + y1) / 2.0
        radius = max(4, int(round(cell_size * 0.22)))
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color, outline=(12, 12, 12), width=1)

    return image, bbox_map


@register_task
class TileShortestPathTask:
    """Task emitting shortest-path length with grounded path evidence."""

    task_id = "tile_shortest_path"
    domain = "tile"
    task_group = "path"

    @staticmethod
    def supported_query_types(_params: Dict[str, Any] | None = None) -> List[str]:
        """Return query types supported by this task."""
        return ["shortest_path"]

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        rows = int(params.get("rows", _DEFAULTS.rows))
        cols = int(params.get("cols", _DEFAULTS.cols))
        min_shortest_len = int(params.get("min_shortest_len", _DEFAULTS.min_shortest_len))
        obstacle_prob_min = float(params.get("obstacle_prob_min", _DEFAULTS.obstacle_prob_min))
        obstacle_prob_max = float(params.get("obstacle_prob_max", _DEFAULTS.obstacle_prob_max))
        canvas_size = int(params.get("canvas_size", _DEFAULTS.canvas_size))
        margin = int(params.get("margin", _DEFAULTS.margin))
        evidence_type = str(params.get("evidence_type", _DEFAULTS.evidence_type))
        query_type = str(params.get("query_type", "shortest_path"))
        if evidence_type not in {"point_path", "bbox_set"}:
            raise ValueError(f"unsupported evidence_type: {evidence_type}")
        if query_type != "shortest_path":
            raise ValueError(f"unsupported query_type: {query_type}")

        task_rng = spawn_rng(instance_seed, "task")
        blocked, start, goal, path, shortest_len = _sample_maze(
            task_rng,
            rows=rows,
            cols=cols,
            min_shortest_len=min_shortest_len,
            obstacle_prob_min=obstacle_prob_min,
            obstacle_prob_max=obstacle_prob_max,
            max_attempts=max_attempts,
        )

        image, bbox_map = _render_maze(
            rows,
            cols,
            blocked,
            start,
            goal,
            path,
            canvas_size=canvas_size,
            margin=margin,
        )

        path_ids = [_cell_id(rc) for rc in path]
        path_points = []
        path_bboxes = []
        for cell_id in path_ids:
            x0, y0, x1, y1 = bbox_map[cell_id]
            path_bboxes.append([x0, y0, x1, y1])
            path_points.append([(x0 + x1) / 2.0, (y0 + y1) / 2.0])

        evidence_value: Any
        if evidence_type == "point_path":
            evidence_value = path_points
        else:
            evidence_value = path_bboxes

        prompt = (
            "A tile maze is shown on one image. Black tiles are blocked, green is start, and red is goal. "
            "Moves are allowed only between edge-adjacent non-black tiles (no diagonals). "
            "The maze is generated so the shortest path is unique. "
            "Return the shortest-path length in steps as the answer and include path evidence."
        )

        adjacency_open: Dict[str, List[str]] = {}
        for r in range(rows):
            for c in range(cols):
                if blocked[r][c]:
                    continue
                nid = _cell_id((r, c))
                neighbors = []
                for nr, nc in _neighbors((r, c), rows, cols):
                    if not blocked[nr][nc]:
                        neighbors.append(_cell_id((nr, nc)))
                adjacency_open[nid] = sorted(neighbors)

        scene_entities = []
        for r in range(rows):
            for c in range(cols):
                cid = _cell_id((r, c))
                scene_entities.append(
                    {
                        "entity_id": cid,
                        "entity_type": "tile_cell",
                        "attrs": {
                            "row": r,
                            "col": c,
                            "blocked": bool(blocked[r][c]),
                            "is_start": cid == _cell_id(start),
                            "is_goal": cid == _cell_id(goal),
                        },
                    }
                )

        render_map = {
            "image_id": "img0",
            "anchors": {
                cid: {
                    "bbox": list(bbox),
                    "point": [
                        (bbox[0] + bbox[2]) / 2.0,
                        (bbox[1] + bbox[3]) / 2.0,
                    ],
                    "coord_space": "pixel",
                }
                for cid, bbox in sorted(bbox_map.items())
            },
        }

        trace_payload = {
            "scene_ir": {
                "scene_kind": "tile_maze",
                "entities": scene_entities,
                "relations": {"adjacency_open": adjacency_open},
            },
            "query_spec": {
                "query_type": query_type,
                "template_id": "shortest_path_v1",
                "dsl_program": [
                    {"out": "cells", "op": "select", "entity_type": "tile_cell"},
                    {
                        "out": "open_cells",
                        "op": "filter",
                        "in": "cells",
                        "predicate": {"blocked": False},
                    },
                    {
                        "out": "path",
                        "op": "shortest_path",
                        "relation": "adjacency_open",
                        "start": _cell_id(start),
                        "goal": _cell_id(goal),
                    },
                    {"out": "answer", "op": "path_length", "in": "path"},
                ],
            },
            "render_spec": {
                "canvas_size": canvas_size,
                "margin": margin,
                "rows": rows,
                "cols": cols,
                "coord_space": "pixel",
            },
            "render_map": render_map,
            "execution_trace": {
                "shortest_path_len": shortest_len,
                "path_ids": path_ids,
                "path_cell_count": len(path_ids),
            },
            "witness_symbolic": {"type": "id_path", "ids": path_ids},
            "projected_evidence": {
                "point_path": path_points,
                "bbox_set": path_bboxes,
            },
        }

        complexity_score = min(1.0, max(0.0, float(shortest_len) / float(rows * cols)))
        complexity = TaskComplexity(
            complexity_score=complexity_score,
            complexity_components={
                "rows": rows,
                "cols": cols,
                "path_len": shortest_len,
                "blocked_ratio": sum(sum(1 for v in row if v) for row in blocked) / float(rows * cols),
            },
        )

        return TaskOutput(
            prompt=prompt,
            answer_gt=TypedValue(type="integer", value=int(shortest_len)),
            evidence_gt=TypedValue(type=evidence_type, value=evidence_value),
            image=image,
            image_id="img0",
            image_rel_path=f"images/{self.domain}/{self.task_id}/{int(instance_seed)}.png",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions={
                "dsl_spec_version": "v1",
                "template_version": "v1",
                "operator_bundle_version": "v1",
                "domain_capability_version": "v1",
                "renderer_version": "v1",
            },
            query_type=query_type,
        )
