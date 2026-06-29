"""Voxel-ladder topology and route helper rules."""

from __future__ import annotations

from collections import deque
from typing import Any, Iterable, Sequence

from trace.tasks.shared.named_colors import named_color

from .state import Ladder, Node


def checkpoint_item_id(color_name: str) -> str:
    """Return the render-map item id for a checkpoint color."""

    return f"checkpoint_{str(color_name)}"


def normalize_path(
    nodes: Sequence[Node],
    *,
    mirror_x: bool,
    swap_xy: bool,
) -> tuple[Node, ...]:
    """Apply simple orientation transforms and normalize to nonnegative coords."""

    transformed: list[Node] = []
    for x, y, z in nodes:
        nx, ny = (-int(x) if mirror_x else int(x)), int(y)
        if swap_xy:
            nx, ny = ny, nx
        transformed.append((int(nx), int(ny), int(z)))
    min_x = min(node[0] for node in transformed)
    min_y = min(node[1] for node in transformed)
    return tuple((int(x - min_x), int(y - min_y), int(z)) for x, y, z in transformed)


def build_route_path(rng: Any, *, ladder_count: int) -> tuple[Node, ...]:
    """Construct one connected route with horizontal runs and vertical ladders."""

    x = y = z = 0
    path: list[Node] = [(x, y, z)]
    for segment_index in range(int(ladder_count) + 1):
        step_count = int(rng.randint(2, 3))
        axis = (segment_index + int(rng.randrange(2))) % 2
        for _ in range(step_count):
            if axis == 0:
                x += 1
            else:
                y += 1
            path.append((x, y, z))
            axis = 1 - axis if rng.random() < 0.35 else axis
        if segment_index < int(ladder_count):
            z += 1
            path.append((x, y, z))
    return normalize_path(
        path,
        mirror_x=bool(rng.randrange(2)),
        swap_xy=bool(rng.randrange(2)),
    )


def orthogonal_neighbors(node: Node) -> Iterable[Node]:
    """Yield same-height side-adjacent cube coordinates."""

    x, y, z = node
    yield (x + 1, y, z)
    yield (x - 1, y, z)
    yield (x, y + 1, z)
    yield (x, y - 1, z)


def route_edges(route_nodes: Sequence[Node]) -> tuple[tuple[Node, Node], ...]:
    """Return consecutive route edges."""

    return tuple(
        (tuple(route_nodes[index]), tuple(route_nodes[index + 1]))
        for index in range(len(route_nodes) - 1)
    )


def is_ladder_edge(edge: tuple[Node, Node]) -> bool:
    """Return whether an edge changes height at one x/y coordinate."""

    a, b = edge
    return int(a[0]) == int(b[0]) and int(a[1]) == int(b[1]) and int(a[2]) != int(b[2])


def make_graph_edges(
    cubes: Sequence[Node],
    ladders: Sequence[Ladder],
) -> tuple[tuple[Node, Node], ...]:
    """Build the undirected movement graph for cube tops and ladders."""

    cube_set = set(cubes)
    edges: set[tuple[Node, Node]] = set()
    for node in cube_set:
        for neighbor in orthogonal_neighbors(node):
            if neighbor in cube_set:
                edges.add(tuple(sorted((node, neighbor))))  # type: ignore[arg-type]
    for ladder in ladders:
        edges.add(tuple(sorted((ladder.lower, ladder.upper))))  # type: ignore[arg-type]
    return tuple(sorted(edges))


def reachable_nodes(start: Node, edges: Sequence[tuple[Node, Node]]) -> set[Node]:
    """Return all nodes reachable from start in the movement graph."""

    adjacency: dict[Node, list[Node]] = {}
    for a, b in edges:
        adjacency.setdefault(tuple(a), []).append(tuple(b))
        adjacency.setdefault(tuple(b), []).append(tuple(a))
    seen = {tuple(start)}
    queue: deque[Node] = deque([tuple(start)])
    while queue:
        node = queue.popleft()
        for neighbor in adjacency.get(node, []):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return seen


def sequence_text(labels: Sequence[str]) -> str:
    """Return prompt/render text for a checkpoint-color route sequence."""

    return " > ".join(str(label) for label in labels)


def sequence_rgb(labels: Sequence[str]) -> tuple[tuple[int, int, int], ...]:
    """Return canonical named-color RGBs for a checkpoint sequence."""

    return tuple(tuple(int(v) for v in named_color(str(label))) for label in labels)


def sequence_distractors(
    rng: Any,
    correct: Sequence[str],
    all_labels: Sequence[str],
    option_count: int,
) -> list[tuple[str, ...]]:
    """Generate distinct wrong options while preserving one route-sequence answer."""

    correct_tuple = tuple(str(label) for label in correct)
    candidates: set[tuple[str, ...]] = {correct_tuple}
    labels = [str(label) for label in all_labels]
    if len(correct_tuple) > 1:
        candidates.add(tuple(reversed(correct_tuple)))
    for label in labels:
        if label in set(correct_tuple):
            continue
        for insert_at in range(len(correct_tuple) + 1):
            seq = list(correct_tuple)
            seq.insert(insert_at, label)
            candidates.add(tuple(seq))
        for replace_at in range(len(correct_tuple)):
            seq = list(correct_tuple)
            seq[replace_at] = label
            candidates.add(tuple(seq))
    for remove_at in range(len(correct_tuple)):
        seq = list(correct_tuple)
        seq.pop(remove_at)
        if seq:
            candidates.add(tuple(seq))
    for _ in range(64):
        seq = list(correct_tuple)
        rng.shuffle(seq)
        if seq:
            candidates.add(tuple(seq))
        if len(labels) >= len(correct_tuple):
            sampled = list(labels)
            rng.shuffle(sampled)
            candidates.add(tuple(sampled[: len(correct_tuple)]))
        if len(candidates) >= int(option_count):
            break
    suffix = 1
    while len(candidates) < int(option_count):
        prefix_len = max(1, min(len(labels), len(correct_tuple)))
        candidates.add(tuple(labels[:prefix_len] + [labels[int(suffix) % len(labels)]]))
        suffix += 1
    return [item for item in sorted(candidates) if item != correct_tuple][
        : int(option_count) - 1
    ]
