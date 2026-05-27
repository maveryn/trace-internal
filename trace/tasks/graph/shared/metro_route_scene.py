"""Shared metro-route graph sampler and renderer."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
import math
import random
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ...shared.text_rendering import draw_text_centered, fit_font_to_box, load_font
from .graph_sampling import graph_label_sort_key
from .graph_scene import BBox, GraphRenderParams, Point
from .label_assets import SUPPORTED_GRAPH_LABEL_VARIANTS, resolve_graph_node_labels


GridPoint = Tuple[int, int]
LabelEdge = Tuple[str, str]
SUPPORTED_METRO_LABEL_VARIANTS: Tuple[str, ...] = SUPPORTED_GRAPH_LABEL_VARIANTS


@dataclass(frozen=True)
class MetroRouteTemplate:
    """One fixed schematic route template before label assignment."""

    route_id: str
    route_name: str
    color_rgb: Tuple[int, int, int]
    grid_points: Tuple[GridPoint, ...]


@dataclass(frozen=True)
class MetroRouteNetworkSample:
    """Trace-ready sampled metro-route network."""

    station_labels: Tuple[str, ...]
    label_by_coord: Dict[GridPoint, str]
    coord_by_label: Dict[str, GridPoint]
    route_templates: Tuple[MetroRouteTemplate, ...]
    route_station_labels: Dict[str, Tuple[str, ...]]
    station_route_ids_by_label: Dict[str, Tuple[str, ...]]
    adjacency_by_label: Dict[str, Tuple[str, ...]]
    edge_labels: Tuple[LabelEdge, ...]
    transfer_labels: Tuple[str, ...]
    target_transfer_count: int
    route_count: int
    station_count: int
    label_variant: str
    terminal_labels: Tuple[str, ...] = ()
    query_label: str = ""
    source_label: str = ""
    goal_label: str = ""
    target_labels: Tuple[str, ...] = ()
    target_terminal_count: int = 0
    target_single_route_count: int = 0
    target_exact_distance_count: int = 0
    target_shortest_path_length: int = 0
    target_route_transfer_count: int = 0
    target_route_sequence: Tuple[str, ...] = ()
    target_path_transfer_labels: Tuple[str, ...] = ()
    label_source_kind: str = ""
    label_bucket: str = ""
    label_manifest: str = ""
    label_filter: Mapping[str, Any] | None = None
    label_bucket_probabilities: Mapping[str, float] | None = None


@dataclass(frozen=True)
class RenderedMetroStation:
    """One rendered metro station."""

    label: str
    grid_point: GridPoint
    route_ids: Tuple[str, ...]
    is_transfer: bool
    center_xy: Point
    bbox_xyxy: BBox


@dataclass(frozen=True)
class RenderedMetroRoute:
    """One rendered metro route polyline."""

    route_id: str
    route_name: str
    color_rgb: Tuple[int, int, int]
    station_labels: Tuple[str, ...]
    polyline_px: Tuple[Point, ...]


@dataclass(frozen=True)
class RenderedMetroRouteScene:
    """Full metro-route render output."""

    image: Image.Image
    panel_geometry: Dict[str, Any]
    stations: Tuple[RenderedMetroStation, ...]
    routes: Tuple[RenderedMetroRoute, ...]
    resolved_label_font_size_px: int
    route_line_width_px: int
    station_radius_px: int
    transfer_station_radius_px: int


@dataclass(frozen=True)
class MetroTransferTripCandidate:
    """One source-via-goal trip with a unique minimum-transfer station path."""

    source_coord: GridPoint
    via_coord: GridPoint
    goal_coord: GridPoint
    path_coords: Tuple[GridPoint, ...]
    route_sequence: Tuple[str, ...]
    route_transfer_count: int


METRO_ROUTE_TEMPLATES: Tuple[MetroRouteTemplate, ...] = (
    MetroRouteTemplate(
        route_id="R",
        route_name="Red",
        color_rgb=(217, 72, 69),
        grid_points=((1, 3), (3, 3), (5, 3), (7, 3), (9, 3)),
    ),
    MetroRouteTemplate(
        route_id="B",
        route_name="Blue",
        color_rgb=(56, 111, 197),
        grid_points=((5, 1), (5, 3), (5, 5), (5, 7), (5, 9)),
    ),
    MetroRouteTemplate(
        route_id="G",
        route_name="Green",
        color_rgb=(56, 151, 95),
        grid_points=((1, 7), (3, 7), (5, 7), (7, 7), (9, 7)),
    ),
    MetroRouteTemplate(
        route_id="O",
        route_name="Orange",
        color_rgb=(225, 137, 55),
        grid_points=((3, 1), (3, 3), (3, 5), (3, 7), (3, 9)),
    ),
    MetroRouteTemplate(
        route_id="P",
        route_name="Purple",
        color_rgb=(134, 91, 193),
        grid_points=((1, 1), (3, 3), (5, 5), (7, 7), (9, 9)),
    ),
    MetroRouteTemplate(
        route_id="T",
        route_name="Teal",
        color_rgb=(32, 151, 156),
        grid_points=((1, 9), (3, 7), (5, 5), (7, 3), (9, 1)),
    ),
)
_METRO_ROUTE_TEMPLATE_BY_ID: Dict[str, MetroRouteTemplate] = {
    str(route.route_id): route for route in METRO_ROUTE_TEMPLATES
}


def _station_sort_key(coord: GridPoint) -> Tuple[int, int]:
    return (int(coord[1]), int(coord[0]))


def _canonical_label_edge(left: str, right: str) -> LabelEdge:
    ordered = sorted((str(left), str(right)), key=graph_label_sort_key)
    return (ordered[0], ordered[1])


def _combo_transfer_count(route_templates: Sequence[MetroRouteTemplate]) -> int:
    coord_counts = Counter(
        tuple(int(value) for value in coord)
        for route in route_templates
        for coord in route.grid_points
    )
    return sum(1 for count in coord_counts.values() if int(count) >= 2)


def feasible_metro_transfer_counts(*, route_count_min: int, route_count_max: int) -> Tuple[int, ...]:
    """Return transfer counts feasible for the fixed route template family."""

    values: set[int] = set()
    for route_count in range(max(1, int(route_count_min)), min(len(METRO_ROUTE_TEMPLATES), int(route_count_max)) + 1):
        for combo in combinations(METRO_ROUTE_TEMPLATES, int(route_count)):
            values.add(int(_combo_transfer_count(combo)))
    return tuple(sorted(values))


def _route_combo_coords(route_templates: Sequence[MetroRouteTemplate]) -> Tuple[Tuple[GridPoint, ...], Dict[GridPoint, Tuple[str, ...]], Dict[str, Tuple[GridPoint, ...]], Dict[GridPoint, Tuple[GridPoint, ...]]]:
    """Return station coords, route memberships, route coords, and station adjacency for a route combo."""

    station_coords = tuple(
        sorted(
            {tuple(int(value) for value in coord) for route in route_templates for coord in route.grid_points},
            key=_station_sort_key,
        )
    )
    coords_by_route = {
        str(route.route_id): tuple(tuple(int(value) for value in coord) for coord in route.grid_points)
        for route in route_templates
    }
    route_ids_by_coord: dict[GridPoint, list[str]] = defaultdict(list)
    adjacency: dict[GridPoint, set[GridPoint]] = {tuple(coord): set() for coord in station_coords}
    for route in route_templates:
        for coord in route.grid_points:
            route_ids_by_coord[tuple(int(value) for value in coord)].append(str(route.route_id))
        for left, right in zip(route.grid_points, route.grid_points[1:]):
            left_coord = tuple(int(value) for value in left)
            right_coord = tuple(int(value) for value in right)
            adjacency[left_coord].add(right_coord)
            adjacency[right_coord].add(left_coord)
    station_routes = {
        tuple(coord): tuple(sorted(route_ids))
        for coord, route_ids in route_ids_by_coord.items()
    }
    adjacency_tuple = {
        tuple(coord): tuple(sorted(neighbors, key=_station_sort_key))
        for coord, neighbors in adjacency.items()
    }
    return tuple(station_coords), dict(station_routes), dict(coords_by_route), dict(adjacency_tuple)


def _single_route_coords(route_templates: Sequence[MetroRouteTemplate]) -> Tuple[GridPoint, ...]:
    station_coords, route_ids_by_coord, _, _ = _route_combo_coords(route_templates)
    return tuple(coord for coord in station_coords if len(route_ids_by_coord[coord]) == 1)


def _same_route_coords(route_templates: Sequence[MetroRouteTemplate], query_coord: GridPoint) -> Tuple[GridPoint, ...]:
    _, route_ids_by_coord, coords_by_route, _ = _route_combo_coords(route_templates)
    query_routes = route_ids_by_coord[tuple(query_coord)]
    coords = {coord for route_id in query_routes for coord in coords_by_route[str(route_id)]}
    return tuple(sorted(coords, key=_station_sort_key))


def _bfs_dist_count(
    adjacency: Mapping[GridPoint, Sequence[GridPoint]],
    *,
    start: GridPoint,
) -> Tuple[Dict[GridPoint, int], Dict[GridPoint, int]]:
    """Return shortest distances and shortest-path counts from one station."""

    start_coord = tuple(int(value) for value in start)
    dist: Dict[GridPoint, int] = {start_coord: 0}
    count: Dict[GridPoint, int] = {start_coord: 1}
    queue: list[GridPoint] = [start_coord]
    head = 0
    while head < len(queue):
        node = queue[head]
        head += 1
        for neighbor in adjacency.get(tuple(node), ()):
            neighbor_coord = tuple(int(value) for value in neighbor)
            candidate_dist = int(dist[node]) + 1
            if neighbor_coord not in dist:
                dist[neighbor_coord] = int(candidate_dist)
                count[neighbor_coord] = int(count[node])
                queue.append(neighbor_coord)
            elif int(dist[neighbor_coord]) == int(candidate_dist):
                count[neighbor_coord] = int(count[neighbor_coord]) + int(count[node])
    return dict(dist), dict(count)


def _unique_shortest_coord_path(
    adjacency: Mapping[GridPoint, Sequence[GridPoint]],
    *,
    source: GridPoint,
    goal: GridPoint,
) -> Tuple[GridPoint, ...] | None:
    """Return the unique shortest coordinate path, or ``None`` if ambiguous/unreachable."""

    source_coord = tuple(int(value) for value in source)
    goal_coord = tuple(int(value) for value in goal)
    dist, count = _bfs_dist_count(adjacency, start=source_coord)
    if goal_coord not in dist or int(count.get(goal_coord, 0)) != 1:
        return None
    path = [goal_coord]
    current = goal_coord
    while current != source_coord:
        previous = [
            tuple(neighbor)
            for neighbor in adjacency.get(tuple(current), ())
            if tuple(neighbor) in dist and int(dist[tuple(neighbor)]) == int(dist[current]) - 1
        ]
        if len(previous) != 1:
            return None
        current = tuple(previous[0])
        path.append(current)
    path.reverse()
    return tuple(path)


def _edge_route_ids_by_coord(routes: Sequence[MetroRouteTemplate]) -> Dict[Tuple[GridPoint, GridPoint], Tuple[str, ...]]:
    """Map each undirected station edge to the route ids that contain it."""

    edge_routes: dict[Tuple[GridPoint, GridPoint], list[str]] = defaultdict(list)
    for route in routes:
        for left, right in zip(route.grid_points, route.grid_points[1:]):
            key = tuple(sorted((tuple(left), tuple(right))))  # type: ignore[assignment]
            edge_routes[key].append(str(route.route_id))
    return {
        (tuple(key[0]), tuple(key[1])): tuple(sorted(route_ids))
        for key, route_ids in edge_routes.items()
    }


def _simple_coord_paths(
    adjacency: Mapping[GridPoint, Sequence[GridPoint]],
    *,
    source: GridPoint,
    goal: GridPoint,
    max_nodes: int,
) -> Tuple[Tuple[GridPoint, ...], ...]:
    """Enumerate simple station paths in a small fixed metro template."""

    source_coord = tuple(int(value) for value in source)
    goal_coord = tuple(int(value) for value in goal)
    paths: list[Tuple[GridPoint, ...]] = []
    stack: list[Tuple[GridPoint, Tuple[GridPoint, ...]]] = [(source_coord, (source_coord,))]
    while stack:
        node, path = stack.pop()
        if len(path) > int(max_nodes):
            continue
        if tuple(node) == goal_coord:
            paths.append(tuple(path))
            continue
        for neighbor in adjacency.get(tuple(node), ()):
            neighbor_coord = tuple(int(value) for value in neighbor)
            if neighbor_coord in path:
                continue
            stack.append((neighbor_coord, (*path, neighbor_coord)))
    return tuple(paths)


def _minimum_route_changes_for_coord_path(
    path: Sequence[GridPoint],
    edge_route_ids: Mapping[Tuple[GridPoint, GridPoint], Sequence[str]],
) -> Tuple[int, Tuple[str, ...]]:
    """Return the fewest route switches needed for one station path."""

    states: dict[str | None, Tuple[int, Tuple[str, ...]]] = {None: (0, ())}
    for left, right in zip(path, path[1:]):
        key = tuple(sorted((tuple(left), tuple(right))))  # type: ignore[assignment]
        route_ids = tuple(str(route_id) for route_id in edge_route_ids[key])
        next_states: dict[str, Tuple[int, Tuple[str, ...]]] = {}
        for previous_route, (change_count, route_sequence) in states.items():
            for route_id in route_ids:
                candidate_count = int(change_count) + (0 if previous_route in (None, route_id) else 1)
                candidate_sequence = (*route_sequence, str(route_id))
                current = next_states.get(str(route_id))
                if current is None or (candidate_count, candidate_sequence) < current:
                    next_states[str(route_id)] = (int(candidate_count), tuple(candidate_sequence))
        states = dict(next_states)
    if not states:
        return 0, ()
    best_count, best_sequence = min(states.values(), key=lambda item: (int(item[0]), tuple(item[1])))
    return int(best_count), tuple(str(route_id) for route_id in best_sequence)


def _route_change_station_coords(path: Sequence[GridPoint], route_sequence: Sequence[str]) -> Tuple[GridPoint, ...]:
    """Return stations where the selected route sequence changes."""

    changes: list[GridPoint] = []
    for edge_index in range(1, len(route_sequence)):
        if str(route_sequence[edge_index]) != str(route_sequence[edge_index - 1]):
            changes.append(tuple(int(value) for value in path[edge_index]))
    return tuple(changes)


@lru_cache(maxsize=None)
def _metro_transfer_trip_candidates_for_route_ids(route_ids: Tuple[str, ...]) -> Tuple[MetroTransferTripCandidate, ...]:
    """Return unique minimum-transfer source-via-goal trip candidates."""

    routes = tuple(_METRO_ROUTE_TEMPLATE_BY_ID[str(route_id)] for route_id in route_ids)
    station_coords, _, _, adjacency = _route_combo_coords(routes)
    edge_route_ids = _edge_route_ids_by_coord(routes)
    pair_paths: dict[Tuple[GridPoint, GridPoint], Tuple[Tuple[GridPoint, ...], ...]] = {
        (tuple(source), tuple(goal)): _simple_coord_paths(
            adjacency,
            source=tuple(source),
            goal=tuple(goal),
            max_nodes=len(station_coords),
        )
        for source in station_coords
        for goal in station_coords
        if tuple(source) != tuple(goal)
    }

    candidates: list[MetroTransferTripCandidate] = []
    for source in station_coords:
        for via in station_coords:
            if tuple(via) == tuple(source):
                continue
            for goal in station_coords:
                if tuple(goal) in {tuple(source), tuple(via)}:
                    continue
                scored_paths: list[Tuple[int, int, Tuple[GridPoint, ...], Tuple[str, ...]]] = []
                for first_leg in pair_paths.get((tuple(source), tuple(via)), ()):
                    first_leg_prefix = set(first_leg[:-1])
                    for second_leg in pair_paths.get((tuple(via), tuple(goal)), ()):
                        if any(tuple(coord) in first_leg_prefix for coord in second_leg[1:]):
                            continue
                        path = tuple((*first_leg, *second_leg[1:]))
                        transfer_count, route_sequence = _minimum_route_changes_for_coord_path(path, edge_route_ids)
                        scored_paths.append((int(transfer_count), len(path) - 1, tuple(path), tuple(route_sequence)))
                if not scored_paths:
                    continue
                best_transfer_count = min(item[0] for item in scored_paths)
                best_length = min(item[1] for item in scored_paths if item[0] == best_transfer_count)
                best_paths = [
                    item
                    for item in scored_paths
                    if item[0] == best_transfer_count and item[1] == best_length
                ]
                unique_path_coords = {tuple(item[2]) for item in best_paths}
                if len(unique_path_coords) != 1:
                    continue
                best = min(best_paths, key=lambda item: tuple(item[3]))
                candidates.append(
                    MetroTransferTripCandidate(
                        source_coord=tuple(source),
                        via_coord=tuple(via),
                        goal_coord=tuple(goal),
                        path_coords=tuple(best[2]),
                        route_sequence=tuple(str(route_id) for route_id in best[3]),
                        route_transfer_count=int(best[0]),
                    )
                )
    return tuple(candidates)


def _metro_transfer_trip_candidates(routes: Sequence[MetroRouteTemplate]) -> Tuple[MetroTransferTripCandidate, ...]:
    route_ids = tuple(sorted((str(route.route_id) for route in routes)))
    return _metro_transfer_trip_candidates_for_route_ids(tuple(route_ids))


def _exact_distance_coords(
    route_templates: Sequence[MetroRouteTemplate],
    *,
    query_coord: GridPoint,
    query_distance: int,
) -> Tuple[GridPoint, ...]:
    _, _, _, adjacency = _route_combo_coords(route_templates)
    dist, _ = _bfs_dist_count(adjacency, start=tuple(query_coord))
    return tuple(sorted((coord for coord, distance in dist.items() if int(distance) == int(query_distance)), key=_station_sort_key))


def _matching_route_combos(
    *,
    query_id: str,
    target_count: int,
    route_count_min: int,
    route_count_max: int,
    query_distance: int = 0,
) -> Tuple[Tuple[MetroRouteTemplate, ...], ...]:
    """Return route combos that can realize one query answer value."""

    combos: list[Tuple[MetroRouteTemplate, ...]] = []
    for route_count in range(max(1, int(route_count_min)), min(len(METRO_ROUTE_TEMPLATES), int(route_count_max)) + 1):
        for combo in combinations(METRO_ROUTE_TEMPLATES, int(route_count)):
            routes = tuple(combo)
            if str(query_id) == "metro_transfer_station_count":
                if int(_combo_transfer_count(routes)) == int(target_count):
                    combos.append(routes)
            elif str(query_id) == "metro_single_route_station_count":
                if len(_single_route_coords(routes)) == int(target_count):
                    combos.append(routes)
            elif str(query_id) == "metro_exact_distance_count":
                station_coords, _, _, _ = _route_combo_coords(routes)
                if any(
                    len(_exact_distance_coords(routes, query_coord=coord, query_distance=int(query_distance))) == int(target_count)
                    for coord in station_coords
                ):
                    combos.append(routes)
            elif str(query_id) == "metro_shortest_path_length":
                station_coords, _, _, adjacency = _route_combo_coords(routes)
                found = False
                for left_index, source in enumerate(station_coords):
                    for goal in station_coords[left_index + 1 :]:
                        path = _unique_shortest_coord_path(adjacency, source=source, goal=goal)
                        if path is not None and len(path) - 1 == int(target_count):
                            found = True
                            break
                    if found:
                        break
                if found:
                    combos.append(routes)
            elif str(query_id) == "metro_transfer_count":
                if any(
                    int(candidate.route_transfer_count) == int(target_count)
                    for candidate in _metro_transfer_trip_candidates(routes)
                ):
                    combos.append(routes)
            else:
                raise ValueError(f"unsupported metro query_id: {query_id}")
    return tuple(combos)


def feasible_metro_answer_counts(
    *,
    query_id: str,
    route_count_min: int,
    route_count_max: int,
    query_distance: int = 0,
) -> Tuple[int, ...]:
    """Return feasible answer values for one metro query family."""

    values: set[int] = set()
    for route_count in range(max(1, int(route_count_min)), min(len(METRO_ROUTE_TEMPLATES), int(route_count_max)) + 1):
        for combo in combinations(METRO_ROUTE_TEMPLATES, int(route_count)):
            routes = tuple(combo)
            if str(query_id) == "metro_transfer_station_count":
                values.add(int(_combo_transfer_count(routes)))
            elif str(query_id) == "metro_single_route_station_count":
                values.add(int(len(_single_route_coords(routes))))
            elif str(query_id) == "metro_exact_distance_count":
                station_coords, _, _, _ = _route_combo_coords(routes)
                for coord in station_coords:
                    values.add(int(len(_exact_distance_coords(routes, query_coord=coord, query_distance=int(query_distance)))))
            elif str(query_id) == "metro_shortest_path_length":
                station_coords, _, _, adjacency = _route_combo_coords(routes)
                for left_index, source in enumerate(station_coords):
                    for goal in station_coords[left_index + 1 :]:
                        path = _unique_shortest_coord_path(adjacency, source=source, goal=goal)
                        if path is not None:
                            values.add(int(len(path) - 1))
            elif str(query_id) == "metro_transfer_count":
                for candidate in _metro_transfer_trip_candidates(routes):
                    values.add(int(candidate.route_transfer_count))
            else:
                raise ValueError(f"unsupported metro query_id: {query_id}")
    return tuple(sorted(values))


def _build_labeled_metro_sample(
    rng: random.Random,
    *,
    routes: Sequence[MetroRouteTemplate],
    label_variant: str,
) -> MetroRouteNetworkSample:
    """Build one labeled metro sample from already-selected route templates."""

    station_coords, _, _, _ = _route_combo_coords(tuple(routes))
    resolved_labels = resolve_graph_node_labels(
        rng,
        label_variant=str(label_variant),
        object_count=len(station_coords),
        max_chars=4,
        sequential_numbers=False,
    )
    station_labels = tuple(str(label) for label in resolved_labels.labels)
    label_by_coord = {
        tuple(int(value) for value in coord): str(label)
        for coord, label in zip(station_coords, station_labels)
    }
    coord_by_label = {str(label): tuple(coord) for coord, label in label_by_coord.items()}

    route_station_labels: dict[str, Tuple[str, ...]] = {}
    station_route_ids: dict[str, list[str]] = defaultdict(list)
    adjacency_sets: dict[str, set[str]] = {str(label): set() for label in station_labels}
    edge_set: set[LabelEdge] = set()
    for route in routes:
        labels = tuple(str(label_by_coord[tuple(coord)]) for coord in route.grid_points)
        route_station_labels[str(route.route_id)] = labels
        for label in labels:
            station_route_ids[str(label)].append(str(route.route_id))
        for left, right in zip(labels, labels[1:]):
            adjacency_sets[str(left)].add(str(right))
            adjacency_sets[str(right)].add(str(left))
            edge_set.add(_canonical_label_edge(str(left), str(right)))

    station_route_ids_by_label = {
        str(label): tuple(sorted(route_ids))
        for label, route_ids in station_route_ids.items()
    }
    transfer_labels = tuple(
        sorted(
            (label for label, route_ids in station_route_ids_by_label.items() if len(route_ids) >= 2),
            key=graph_label_sort_key,
        )
    )
    terminal_coords = {
        tuple(int(value) for value in route.grid_points[0])
        for route in routes
    } | {
        tuple(int(value) for value in route.grid_points[-1])
        for route in routes
    }
    terminal_labels = tuple(sorted((str(label_by_coord[coord]) for coord in terminal_coords), key=graph_label_sort_key))

    adjacency_by_label = {
        str(label): tuple(sorted(neighbors, key=graph_label_sort_key))
        for label, neighbors in adjacency_sets.items()
    }
    edge_labels = tuple(sorted(edge_set, key=lambda pair: (graph_label_sort_key(pair[0]), graph_label_sort_key(pair[1]))))
    return MetroRouteNetworkSample(
        station_labels=tuple(str(label) for label in station_labels),
        label_by_coord=dict(label_by_coord),
        coord_by_label=dict(coord_by_label),
        route_templates=tuple(routes),
        route_station_labels=dict(route_station_labels),
        station_route_ids_by_label=dict(station_route_ids_by_label),
        adjacency_by_label=dict(adjacency_by_label),
        edge_labels=tuple(edge_labels),
        transfer_labels=tuple(transfer_labels),
        target_transfer_count=int(len(transfer_labels)),
        route_count=int(len(routes)),
        station_count=int(len(station_coords)),
        label_variant=str(resolved_labels.label_variant),
        terminal_labels=tuple(terminal_labels),
        target_labels=tuple(transfer_labels),
        target_terminal_count=int(len(terminal_labels)),
        label_source_kind=str(resolved_labels.label_source_kind),
        label_bucket=str(resolved_labels.label_bucket),
        label_manifest=str(resolved_labels.label_manifest),
        label_filter=dict(resolved_labels.label_filter),
        label_bucket_probabilities=dict(resolved_labels.label_bucket_probabilities),
    )


def sample_metro_query_network(
    rng: random.Random,
    *,
    query_id: str,
    target_count: int,
    route_count_min: int,
    route_count_max: int,
    label_variant: str,
    query_distance: int = 0,
) -> MetroRouteNetworkSample:
    """Sample a metro-route graph plus witness payload for one query family."""

    feasible = _matching_route_combos(
        query_id=str(query_id),
        target_count=int(target_count),
        route_count_min=int(route_count_min),
        route_count_max=int(route_count_max),
        query_distance=int(query_distance),
    )
    if not feasible:
        raise ValueError("no feasible metro route combo for requested query target")
    routes = tuple(rng.choice(feasible))
    sample = _build_labeled_metro_sample(rng, routes=routes, label_variant=str(label_variant))
    if str(query_id) == "metro_transfer_station_count":
        if int(sample.target_transfer_count) != int(target_count):
            raise ValueError("sampled metro transfer count did not match target")
        return sample
    if str(query_id) == "metro_single_route_station_count":
        single_coords = _single_route_coords(routes)
        labels = tuple(sorted((str(sample.label_by_coord[coord]) for coord in single_coords), key=graph_label_sort_key))
        return MetroRouteNetworkSample(
            **{**sample.__dict__, "target_labels": labels, "target_single_route_count": int(len(labels))}
        )
    if str(query_id) == "metro_exact_distance_count":
        station_coords, _, _, _ = _route_combo_coords(routes)
        candidates = [
            coord
            for coord in station_coords
            if len(_exact_distance_coords(routes, query_coord=coord, query_distance=int(query_distance))) == int(target_count)
        ]
        if not candidates:
            raise ValueError("sampled metro exact-distance query has no matching station")
        query_coord = tuple(rng.choice(candidates))
        exact_coords = _exact_distance_coords(routes, query_coord=query_coord, query_distance=int(query_distance))
        labels = tuple(sorted((str(sample.label_by_coord[coord]) for coord in exact_coords), key=graph_label_sort_key))
        query_label = str(sample.label_by_coord[query_coord])
        return MetroRouteNetworkSample(
            **{
                **sample.__dict__,
                "query_label": query_label,
                "target_labels": labels,
                "target_exact_distance_count": int(len(labels)),
            }
        )
    if str(query_id) == "metro_shortest_path_length":
        station_coords, _, _, adjacency = _route_combo_coords(routes)
        candidates: list[Tuple[GridPoint, GridPoint, Tuple[GridPoint, ...]]] = []
        for left_index, source in enumerate(station_coords):
            for goal in station_coords[left_index + 1 :]:
                path = _unique_shortest_coord_path(adjacency, source=source, goal=goal)
                if path is not None and len(path) - 1 == int(target_count):
                    candidates.append((tuple(source), tuple(goal), tuple(path)))
        if not candidates:
            raise ValueError("sampled metro shortest-path query has no matching pair")
        source_coord, goal_coord, path_coords = rng.choice(candidates)
        path_labels = tuple(str(sample.label_by_coord[coord]) for coord in path_coords)
        return MetroRouteNetworkSample(
            **{
                **sample.__dict__,
                "source_label": str(sample.label_by_coord[source_coord]),
                "goal_label": str(sample.label_by_coord[goal_coord]),
                "target_labels": tuple(path_labels),
                "target_shortest_path_length": int(len(path_labels) - 1),
            }
        )
    if str(query_id) == "metro_transfer_count":
        candidates = [
            candidate
            for candidate in _metro_transfer_trip_candidates(routes)
            if int(candidate.route_transfer_count) == int(target_count)
        ]
        if not candidates:
            raise ValueError("sampled metro transfer-count query has no matching trip")
        candidate = rng.choice(candidates)
        path_labels = tuple(str(sample.label_by_coord[coord]) for coord in candidate.path_coords)
        transfer_labels = tuple(
            str(sample.label_by_coord[coord])
            for coord in _route_change_station_coords(candidate.path_coords, candidate.route_sequence)
        )
        return MetroRouteNetworkSample(
            **{
                **sample.__dict__,
                "query_label": str(sample.label_by_coord[candidate.via_coord]),
                "source_label": str(sample.label_by_coord[candidate.source_coord]),
                "goal_label": str(sample.label_by_coord[candidate.goal_coord]),
                "target_labels": tuple(path_labels),
                "target_route_transfer_count": int(candidate.route_transfer_count),
                "target_route_sequence": tuple(str(route_id) for route_id in candidate.route_sequence),
                "target_path_transfer_labels": tuple(transfer_labels),
            }
        )
    raise ValueError(f"unsupported metro query_id: {query_id}")


def sample_metro_transfer_network(
    rng: random.Random,
    *,
    target_transfer_count: int,
    route_count_min: int,
    route_count_max: int,
    label_variant: str,
) -> MetroRouteNetworkSample:
    """Sample a metro-route graph with a requested number of transfer stations."""

    return sample_metro_query_network(
        rng,
        query_id="metro_transfer_station_count",
        target_count=int(target_transfer_count),
        route_count_min=int(route_count_min),
        route_count_max=int(route_count_max),
        label_variant=str(label_variant),
    )


def projected_metro_station_point_evidence(
    rendered_scene: RenderedMetroRouteScene,
    labels: Sequence[str],
) -> Dict[str, Any]:
    """Project ordered station labels into pixel point/bbox evidence."""

    station_by_label = {str(station.label): station for station in rendered_scene.stations}
    point_map: Dict[str, list[float]] = {}
    point_set: list[list[float]] = []
    bbox_set: list[list[float]] = []
    for label in [str(value) for value in labels]:
        station = station_by_label.get(str(label))
        if station is None:
            continue
        point = [float(station.center_xy[0]), float(station.center_xy[1])]
        bbox = [float(value) for value in station.bbox_xyxy]
        point_map[str(label)] = list(point)
        point_set.append(list(point))
        bbox_set.append(list(bbox))
    return {
        "pixel_point_map": point_map,
        "pixel_point_set": point_set,
        "pixel_point_sequence": list(point_set),
        "pixel_bbox_set": bbox_set,
    }


def _resolve_metro_panel_geometry(render_params: GraphRenderParams) -> Dict[str, Any]:
    width = int(render_params.canvas_width)
    height = int(render_params.canvas_height)
    margin = int(render_params.outer_margin_px)
    panel = (margin, margin, width - margin, height - margin)
    title_band_height = max(40, int(round(float(render_params.panel_title_font_size_px) * 1.8)))
    title_band = (panel[0], panel[1], panel[2], panel[1] + title_band_height)
    legend_band = (panel[0] + 18, title_band[3] + 4, panel[2] - 18, title_band[3] + 36)
    content = (
        panel[0] + max(36, int(render_params.panel_padding_px) + 18),
        legend_band[3] + 18,
        panel[2] - max(36, int(render_params.panel_padding_px) + 18),
        panel[3] - max(30, int(render_params.panel_padding_px)),
    )
    return {
        "canvas_size": [int(width), int(height)],
        "scene_panel_xyxy": [int(value) for value in panel],
        "title_band_xyxy": [int(value) for value in title_band],
        "legend_band_xyxy": [int(value) for value in legend_band],
        "scene_content_xyxy": [int(value) for value in content],
    }


def _grid_to_pixel(coord: GridPoint, content_bbox: Sequence[int]) -> Point:
    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    x, y = (int(coord[0]), int(coord[1]))
    px = x0 + ((x1 - x0) * ((float(x) - 1.0) / 8.0))
    py = y0 + ((y1 - y0) * ((float(y) - 1.0) / 8.0))
    return (int(round(px)), int(round(py)))


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, font: Any, *, stroke_width: int = 0) -> Tuple[int, int, int, int]:
    try:
        bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(stroke_width)))
        return (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        return (0, 0, int(width), int(height))


def _draw_panel(
    image: Image.Image,
    *,
    panel_geometry: Mapping[str, Any],
    render_params: GraphRenderParams,
    scene_title: str,
) -> None:
    draw = ImageDraw.Draw(image)
    panel = tuple(int(value) for value in panel_geometry["scene_panel_xyxy"])
    draw.rounded_rectangle(
        panel,
        radius=max(0, int(render_params.panel_corner_radius_px)),
        fill=tuple(int(value) for value in render_params.panel_fill_rgb),
        outline=tuple(int(value) for value in render_params.panel_border_rgb),
        width=2,
    )
    title_band = tuple(int(value) for value in panel_geometry["title_band_xyxy"])
    draw_text_centered(
        draw,
        text=str(scene_title),
        center=(0.5 * float(title_band[0] + title_band[2]), 0.5 * float(title_band[1] + title_band[3])),
        font=load_font(int(render_params.panel_title_font_size_px), bold=True),
        fill=tuple(int(value) for value in render_params.title_color_rgb),
        stroke_fill=tuple(int(value) for value in render_params.panel_fill_rgb),
        stroke_width=2,
    )


def _draw_route_legend(
    draw: ImageDraw.ImageDraw,
    *,
    routes: Sequence[MetroRouteTemplate],
    legend_bbox: Sequence[int],
) -> None:
    x0, y0, x1, y1 = [int(value) for value in legend_bbox]
    if not routes:
        return
    font = load_font(13, bold=True)
    slot_width = max(1, int((x1 - x0) / len(routes)))
    for index, route in enumerate(routes):
        left = x0 + (index * slot_width) + 8
        cy = int(round(0.5 * (y0 + y1)))
        color = tuple(int(value) for value in route.color_rgb)
        draw.line((left, cy, left + 30, cy), fill=color, width=8)
        draw.rounded_rectangle((left - 2, cy - 7, left + 32, cy + 7), radius=6, outline=color, width=1)
        draw.text((left + 40, cy - 8), str(route.route_name), font=font, fill=(67, 75, 91))


def _label_anchor_for_station(center: Point, content_bbox: Sequence[int]) -> Point:
    x0, y0, x1, y1 = [int(value) for value in content_bbox]
    cx, cy = int(center[0]), int(center[1])
    horizontal = -1 if cx > (x0 + x1) / 2 else 1
    vertical = -1 if cy > (y0 + y1) / 2 else 1
    return (int(cx + horizontal * 18), int(cy + vertical * 17))


def render_metro_scene(
    *,
    metro_sample: MetroRouteNetworkSample,
    render_params: GraphRenderParams,
    base_image: Image.Image,
    scene_title: str = "Metro Route Graph",
) -> RenderedMetroRouteScene:
    """Render one sampled metro-route graph scene."""

    image = base_image.convert("RGB")
    draw = ImageDraw.Draw(image)
    panel_geometry = _resolve_metro_panel_geometry(render_params)
    _draw_panel(image, panel_geometry=panel_geometry, render_params=render_params, scene_title=str(scene_title))
    _draw_route_legend(
        draw,
        routes=metro_sample.route_templates,
        legend_bbox=panel_geometry["legend_band_xyxy"],
    )

    content_bbox = tuple(int(value) for value in panel_geometry["scene_content_xyxy"])
    route_line_width = max(8, int(render_params.edge_width_px) * 2 + 2)
    station_radius = max(8, int(round(float(render_params.node_radius_px) * 0.48)))
    transfer_radius = max(station_radius + 7, int(round(float(render_params.node_radius_px) * 0.78)))
    coord_centers = {
        tuple(coord): _grid_to_pixel(tuple(coord), content_bbox)
        for coord in metro_sample.label_by_coord
    }

    rendered_routes: list[RenderedMetroRoute] = []
    for route in metro_sample.route_templates:
        polyline = tuple(_grid_to_pixel(tuple(coord), content_bbox) for coord in route.grid_points)
        for left, right in zip(polyline, polyline[1:]):
            draw.line(
                (left[0], left[1], right[0], right[1]),
                fill=(255, 255, 255),
                width=route_line_width + 6,
            )
        draw.line(
            tuple(point for xy in polyline for point in xy),
            fill=tuple(int(value) for value in route.color_rgb),
            width=route_line_width,
        )
        rendered_routes.append(
            RenderedMetroRoute(
                route_id=str(route.route_id),
                route_name=str(route.route_name),
                color_rgb=tuple(int(value) for value in route.color_rgb),
                station_labels=tuple(str(value) for value in metro_sample.route_station_labels[str(route.route_id)]),
                polyline_px=tuple(tuple(int(v) for v in point) for point in polyline),
            )
        )

    max_label = max(metro_sample.station_labels, key=len)
    label_font = fit_font_to_box(
        draw,
        text=str(max_label),
        max_width=34,
        max_height=22,
        max_size_px=max(13, int(render_params.label_font_size_px) - 3),
        min_size_px=10,
        bold=True,
    )
    label_font_size = int(getattr(label_font, "size", 13))
    label_stroke_width = max(1, int(round(float(label_font_size) * 0.08)))
    rendered_stations: list[RenderedMetroStation] = []
    for coord in sorted(metro_sample.label_by_coord, key=_station_sort_key):
        label = str(metro_sample.label_by_coord[coord])
        route_ids = tuple(str(value) for value in metro_sample.station_route_ids_by_label[label])
        is_transfer = len(route_ids) >= 2
        center = tuple(int(value) for value in coord_centers[coord])
        radius = int(transfer_radius if is_transfer else station_radius)
        if str(metro_sample.query_label) and str(label) == str(metro_sample.query_label):
            halo_radius = int(radius + 8)
            halo_bbox = (
                center[0] - halo_radius,
                center[1] - halo_radius,
                center[0] + halo_radius,
                center[1] + halo_radius,
            )
            draw.ellipse(halo_bbox, outline=(22, 25, 31), width=4)
        bbox = (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius)
        draw.ellipse(
            bbox,
            fill=(255, 255, 255),
            outline=(48, 55, 67) if is_transfer else (88, 98, 114),
            width=4 if is_transfer else 2,
        )
        if is_transfer:
            inner = (center[0] - station_radius, center[1] - station_radius, center[0] + station_radius, center[1] + station_radius)
            draw.ellipse(inner, outline=(48, 55, 67), width=3)

        anchor = _label_anchor_for_station(center, content_bbox)
        text_bbox = _text_bbox(draw, label, label_font, stroke_width=label_stroke_width)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        label_box = (
            anchor[0] - int(text_width // 2) - 5,
            anchor[1] - int(text_height // 2) - 4,
            anchor[0] + int(math.ceil(text_width / 2.0)) + 5,
            anchor[1] + int(math.ceil(text_height / 2.0)) + 4,
        )
        draw.rounded_rectangle(label_box, radius=5, fill=(255, 255, 255), outline=(213, 219, 229), width=1)
        draw_text_centered(
            draw,
            text=label,
            center=(float(anchor[0]), float(anchor[1])),
            font=label_font,
            fill=(43, 50, 61),
            stroke_fill=(255, 255, 255),
            stroke_width=label_stroke_width,
        )
        rendered_stations.append(
            RenderedMetroStation(
                label=str(label),
                grid_point=tuple(int(value) for value in coord),
                route_ids=tuple(route_ids),
                is_transfer=bool(is_transfer),
                center_xy=tuple(center),
                bbox_xyxy=tuple(int(value) for value in bbox),
            )
        )

    return RenderedMetroRouteScene(
        image=image,
        panel_geometry=dict(panel_geometry),
        stations=tuple(rendered_stations),
        routes=tuple(rendered_routes),
        resolved_label_font_size_px=int(label_font_size),
        route_line_width_px=int(route_line_width),
        station_radius_px=int(station_radius),
        transfer_station_radius_px=int(transfer_radius),
    )


__all__ = [
    "METRO_ROUTE_TEMPLATES",
    "MetroRouteNetworkSample",
    "MetroRouteTemplate",
    "RenderedMetroRoute",
    "RenderedMetroRouteScene",
    "RenderedMetroStation",
    "SUPPORTED_METRO_LABEL_VARIANTS",
    "feasible_metro_answer_counts",
    "feasible_metro_transfer_counts",
    "projected_metro_station_point_evidence",
    "render_metro_scene",
    "sample_metro_query_network",
    "sample_metro_transfer_network",
]
