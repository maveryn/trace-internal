"""Shared dataset builders and render defaults for printed map-navigation tasks."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from ....shared.config_defaults import resolve_required_int_bounds
from ....shared.deterministic_sampling import resolve_selection_index
from ....shared.render_variation import resolve_layout_jitter
from .common import (
    resolve_diagrams_axis_variant,
    resolve_diagrams_int_param,
    resolve_diagrams_rgb_triple,
)


SUPPORTED_DOCUMENT_MAP_SCENE_VARIANTS: Tuple[str, ...] = ("campus_map",)
SUPPORTED_DOCUMENT_MAP_QUERY_VARIANTS: Tuple[str, ...] = (
    "destination_after_directions",
    "landmark_after_route_step",
)

_GRID_COLS = 5
_GRID_ROWS = 4
_LANDMARK_NAMES: Tuple[str, ...] = (
    "Library",
    "Atrium",
    "Clinic",
    "Studio",
    "Workshop",
    "Gallery",
    "Foundry",
    "Theater",
    "Cafeteria",
    "Depot",
    "Dormitory",
    "Garden",
    "Plaza",
    "Archive",
    "Gym",
    "Observatory",
    "Bookstore",
    "Lab Annex",
    "North Hall",
    "South Hall",
    "East Lab",
    "West Lab",
    "Market",
    "Chapel",
    "Arcade",
    "Tower",
    "Pool",
    "Annex",
    "Dining",
    "Media Lab",
    "Makerspace",
    "Maple Lab",
    "Cedar Lab",
    "Elm Hall",
    "Pine Hall",
    "Delta Lab",
    "Sigma Hall",
    "Harbor Lab",
    "Valley Hall",
    "Union",
    "Gateway",
    "Courtyard",
    "Auditorium",
    "Commons",
    "Greenhouse",
    "Data Lab",
    "Print Shop",
    "Music Hall",
    "Health Hub",
    "Design Lab",
    "Field House",
    "Science Hall",
    "Transit Hub",
)
_ZONE_LABELS: Tuple[str, ...] = (
    "North Green",
    "Research Row",
    "West Yard",
    "South Court",
    "East Quad",
    "South Lawn",
    "North Quad",
    "Maker Row",
    "Study Grove",
    "Transit Yard",
    "Arts Court",
    "Science Park",
    "Harbor Wing",
    "Valley Court",
    "Market Lane",
    "Civic Yard",
    "Garden Row",
    "Central Field",
    "Elm Court",
    "Cedar Yard",
    "Maple Quad",
    "River Walk",
    "Depot Row",
    "Clinic Zone",
)
_TITLE_OPTIONS: Tuple[str, ...] = (
    "Campus Orientation Map",
    "Facility Walking Map",
    "Site Navigation Map",
    "Visitor Route Map",
    "Campus Guide Map",
)
_ZONE_LAYOUTS: Tuple[Dict[str, object], ...] = (
    {"zone_id": "zone_north_west", "cell_bounds": (0, 0, 2, 1)},
    {"zone_id": "zone_north_east", "cell_bounds": (3, 0, 4, 1)},
    {"zone_id": "zone_south_west", "cell_bounds": (0, 2, 2, 3)},
    {"zone_id": "zone_south_east", "cell_bounds": (3, 2, 4, 3)},
)


Cell = Tuple[int, int]


@dataclass(frozen=True)
class MapDefaults:
    """Default generation bounds for map-navigation label tasks."""

    landmark_count_min: int = 10
    landmark_count_max: int = 14
    direction_step_count_min: int = 2
    direction_step_count_max: int = 4
    highlighted_route_step_min: int = 2
    highlighted_route_step_max: int = 5


@dataclass(frozen=True)
class MapRenderParams:
    """Resolved rendering knobs for one printed campus-map scene."""

    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    title_font_size_px: int
    title_band_height_px: int
    map_corner_radius_px: int
    map_border_width_px: int
    path_width_px: int
    highlighted_path_width_px: int
    landmark_width_px: int
    landmark_height_px: int
    landmark_corner_radius_px: int
    landmark_border_width_px: int
    landmark_label_font_size_px: int
    zone_label_font_size_px: int
    legend_font_size_px: int
    compass_font_size_px: int
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]
    map_fill_rgb: Tuple[int, int, int]
    map_border_rgb: Tuple[int, int, int]
    zone_border_rgb: Tuple[int, int, int]
    path_rgb: Tuple[int, int, int]
    highlighted_path_rgb: Tuple[int, int, int]
    landmark_fill_rgb: Tuple[int, int, int]
    landmark_border_rgb: Tuple[int, int, int]
    landmark_label_rgb: Tuple[int, int, int]
    label_stroke_rgb: Tuple[int, int, int]
    zone_label_rgb: Tuple[int, int, int]
    compass_rgb: Tuple[int, int, int]
    layout_jitter_meta: Dict[str, Any]


def resolve_map_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active map scene variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DOCUMENT_MAP_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_map_query_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active semantic map-query variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DOCUMENT_MAP_QUERY_VARIANTS,
        task_id=str(task_id),
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
    )


def resolve_map_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    instance_seed: int | None = None,
) -> MapRenderParams:
    """Resolve rendering params for printed campus-map scenes."""

    def _int(key: str, fallback: int) -> int:
        return resolve_diagrams_int_param(
            params,
            render_defaults,
            key,
            fallback,
            instance_seed=instance_seed,
            namespace="pages.map",
        )

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_diagrams_rgb_triple(
            params,
            render_defaults,
            key,
            fallback,
            instance_seed=instance_seed,
            namespace="pages.map",
        )

    layout_jitter_meta = resolve_layout_jitter(
        params,
        render_defaults,
        instance_seed=instance_seed,
        namespace="pages.map.layout",
    )

    return MapRenderParams(
        canvas_width=_int("canvas_width", 1280),
        canvas_height=_int("canvas_height", 900),
        outer_margin_px=_int("outer_margin_px", 46),
        panel_padding_px=_int("panel_padding_px", 26),
        panel_corner_radius_px=_int("panel_corner_radius_px", 20),
        title_font_size_px=_int("title_font_size_px", 30),
        title_band_height_px=_int("title_band_height_px", 70),
        map_corner_radius_px=_int("map_corner_radius_px", 24),
        map_border_width_px=_int("map_border_width_px", 3),
        path_width_px=_int("path_width_px", 12),
        highlighted_path_width_px=_int("highlighted_path_width_px", 18),
        landmark_width_px=_int("landmark_width_px", 126),
        landmark_height_px=_int("landmark_height_px", 58),
        landmark_corner_radius_px=_int("landmark_corner_radius_px", 12),
        landmark_border_width_px=_int("landmark_border_width_px", 3),
        landmark_label_font_size_px=_int("landmark_label_font_size_px", 18),
        zone_label_font_size_px=_int("zone_label_font_size_px", 24),
        legend_font_size_px=_int("legend_font_size_px", 17),
        compass_font_size_px=_int("compass_font_size_px", 18),
        panel_fill_rgb=_triple("panel_fill_rgb", (252, 252, 249)),
        panel_border_rgb=_triple("panel_border_rgb", (77, 88, 99)),
        title_color_rgb=_triple("title_color_rgb", (34, 40, 48)),
        map_fill_rgb=_triple("map_fill_rgb", (246, 247, 240)),
        map_border_rgb=_triple("map_border_rgb", (86, 96, 91)),
        zone_border_rgb=_triple("zone_border_rgb", (196, 202, 188)),
        path_rgb=_triple("path_rgb", (184, 186, 176)),
        highlighted_path_rgb=_triple("highlighted_path_rgb", (205, 92, 46)),
        landmark_fill_rgb=_triple("landmark_fill_rgb", (255, 255, 252)),
        landmark_border_rgb=_triple("landmark_border_rgb", (72, 88, 104)),
        landmark_label_rgb=_triple("landmark_label_rgb", (28, 34, 42)),
        label_stroke_rgb=_triple("label_stroke_rgb", (255, 255, 255)),
        zone_label_rgb=_triple("zone_label_rgb", (72, 84, 78)),
        compass_rgb=_triple("compass_rgb", (45, 52, 60)),
        layout_jitter_meta=dict(layout_jitter_meta),
    )


def _neighbors(cell: Cell) -> Iterable[Cell]:
    x, y = int(cell[0]), int(cell[1])
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx = int(x + dx)
        ny = int(y + dy)
        if 0 <= nx < _GRID_COLS and 0 <= ny < _GRID_ROWS:
            yield (nx, ny)


def _sample_connected_cells(*, rng, count: int) -> list[Cell]:
    """Sample a connected subset of grid cells for map landmarks."""

    start = (int(rng.randrange(_GRID_COLS)), int(rng.randrange(_GRID_ROWS)))
    selected: list[Cell] = [start]
    selected_set = {start}
    frontier = [cell for cell in _neighbors(start)]
    while len(selected) < int(count):
        if not frontier:
            candidates = [cell for cell in ((x, y) for y in range(_GRID_ROWS) for x in range(_GRID_COLS)) if cell not in selected_set]
            frontier.extend(candidates)
        choice = frontier.pop(int(rng.randrange(len(frontier))))
        if choice in selected_set:
            continue
        if any(neighbor in selected_set for neighbor in _neighbors(choice)):
            selected.append(choice)
            selected_set.add(choice)
            for neighbor in _neighbors(choice):
                if neighbor not in selected_set and neighbor not in frontier:
                    frontier.append(neighbor)
    return sorted(selected, key=lambda item: (int(item[1]), int(item[0])))


def _build_adjacency(cells: Sequence[Cell]) -> Dict[Cell, list[Cell]]:
    selected = {tuple(cell) for cell in cells}
    out: Dict[Cell, list[Cell]] = {}
    for cell in selected:
        out[cell] = sorted([neighbor for neighbor in _neighbors(cell) if neighbor in selected], key=lambda item: (item[1], item[0]))
    return out


def _route_between(adjacency: Mapping[Cell, Sequence[Cell]], start: Cell, end: Cell) -> list[Cell]:
    queue: deque[Cell] = deque([start])
    parent: Dict[Cell, Cell | None] = {start: None}
    while queue:
        current = queue.popleft()
        if current == end:
            break
        for neighbor in adjacency[current]:
            if neighbor in parent:
                continue
            parent[neighbor] = current
            queue.append(neighbor)
    if end not in parent:
        return [start]
    path: list[Cell] = []
    current: Cell | None = end
    while current is not None:
        path.append(current)
        current = parent[current]
    return list(reversed(path))


def _sample_route(
    *,
    rng,
    cells: Sequence[Cell],
    adjacency: Mapping[Cell, Sequence[Cell]],
    min_edges: int,
    max_edges: int,
) -> list[Cell]:
    """Sample a simple connected route with bounded edge count."""

    cell_list = list(cells)
    for _ in range(300):
        start = cell_list[int(rng.randrange(len(cell_list)))]
        path = [start]
        while len(path) - 1 < int(max_edges):
            choices = [cell for cell in adjacency[path[-1]] if cell not in path]
            if not choices:
                break
            path.append(choices[int(rng.randrange(len(choices)))])
            if len(path) - 1 >= int(min_edges) and rng.random() < 0.36:
                break
        if int(min_edges) <= len(path) - 1 <= int(max_edges):
            return list(path)
    best_path: list[Cell] = [cell_list[0]]
    for start in cell_list:
        for end in cell_list:
            if start == end:
                continue
            path = _route_between(adjacency, start, end)
            if len(best_path) < len(path) <= int(max_edges) + 1:
                best_path = path
    if len(best_path) - 1 < int(min_edges):
        raise ValueError("could not sample a feasible map route")
    return list(best_path[: int(max_edges) + 1])


def _direction_between(source: Cell, target: Cell) -> str:
    dx = int(target[0] - source[0])
    dy = int(target[1] - source[1])
    if dx == 1 and dy == 0:
        return "east"
    if dx == -1 and dy == 0:
        return "west"
    if dx == 0 and dy == -1:
        return "north"
    if dx == 0 and dy == 1:
        return "south"
    raise ValueError(f"route cells are not adjacent: {source} -> {target}")


def _ordinal(value: int) -> str:
    if 10 <= int(value) % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(int(value) % 10, "th")
    return f"{int(value)}{suffix}"


def _sample_zone_specs(*, rng) -> list[Dict[str, object]]:
    labels = [str(label) for label in rng.sample(list(_ZONE_LABELS), len(_ZONE_LAYOUTS))]
    return [
        {
            "zone_id": str(layout["zone_id"]),
            "zone_label": str(labels[index]),
            "cell_bounds": [int(value) for value in layout["cell_bounds"]],
        }
        for index, layout in enumerate(_ZONE_LAYOUTS)
    ]


def _zone_for_cell(cell: Cell, *, zone_specs: Sequence[Mapping[str, object]]) -> Dict[str, object]:
    x, y = int(cell[0]), int(cell[1])
    if y <= 1 and x <= 2:
        return dict(zone_specs[0])
    if y <= 1:
        return dict(zone_specs[1])
    if x <= 2:
        return dict(zone_specs[2])
    return dict(zone_specs[3])


def _title(*, rng) -> str:
    return str(_TITLE_OPTIONS[int(rng.randrange(len(_TITLE_OPTIONS)))])


def build_map_navigation_dataset(
    *,
    query_variant: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: MapDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one printed-map navigation query instance."""

    if str(scene_variant) != "campus_map":
        raise ValueError(f"unsupported map scene variant: {scene_variant}")
    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    zone_specs = _sample_zone_specs(rng=rng)
    landmark_count_min, landmark_count_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="landmark_count_min",
        max_key="landmark_count_max",
        fallback_min=int(defaults.landmark_count_min),
        fallback_max=int(defaults.landmark_count_max),
        context=f"{task_id} landmark count",
    )
    landmark_count = int(
        int(landmark_count_min)
        + (
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.landmark_count",
            )
            % (int(landmark_count_max) - int(landmark_count_min) + 1)
        )
    )
    cells = _sample_connected_cells(rng=rng, count=int(landmark_count))
    labels = [str(label) for label in rng.sample(list(_LANDMARK_NAMES), int(landmark_count))]
    adjacency = _build_adjacency(cells)
    landmark_specs: list[Dict[str, object]] = []
    cell_to_landmark_id: Dict[Cell, str] = {}
    for index, (cell, label) in enumerate(zip(cells, labels)):
        zone = _zone_for_cell(cell, zone_specs=zone_specs)
        landmark_id = f"landmark_{index}"
        cell_to_landmark_id[cell] = landmark_id
        landmark_specs.append(
            {
                "landmark_id": landmark_id,
                "landmark_bbox_id": f"landmark_bbox_{index}",
                "landmark_label_bbox_id": f"landmark_label_bbox_{index}",
                "landmark_label": str(label),
                "grid_col": int(cell[0]),
                "grid_row": int(cell[1]),
                "zone_id": str(zone["zone_id"]),
                "zone_label": str(zone["zone_label"]),
            }
        )

    path_specs = []
    edge_index = 0
    for source in cells:
        for target in adjacency[source]:
            if (int(source[1]), int(source[0])) > (int(target[1]), int(target[0])):
                continue
            path_specs.append(
                {
                    "path_id": f"path_{edge_index}",
                    "path_bbox_id": f"path_bbox_{edge_index}",
                    "source_landmark_id": str(cell_to_landmark_id[source]),
                    "target_landmark_id": str(cell_to_landmark_id[target]),
                    "source_grid_col": int(source[0]),
                    "source_grid_row": int(source[1]),
                    "target_grid_col": int(target[0]),
                    "target_grid_row": int(target[1]),
                }
            )
            edge_index += 1

    lookup = {str(spec["landmark_id"]): dict(spec) for spec in landmark_specs}
    highlighted_route: list[Cell] = []
    route_landmark_ids: list[str] = []
    evidence_landmark_bbox_ids: list[str] = []
    evidence_zone_label_bbox_ids: list[str] = []
    answer_label: str
    question_text: str
    evidence_semantics: str

    if str(query_variant) == "destination_after_directions":
        step_min, step_max = resolve_required_int_bounds(
            params,
            gen_defaults,
            min_key="direction_step_count_min",
            max_key="direction_step_count_max",
            fallback_min=int(defaults.direction_step_count_min),
            fallback_max=int(defaults.direction_step_count_max),
            context=f"{task_id} direction step count",
        )
        route = _sample_route(rng=rng, cells=cells, adjacency=adjacency, min_edges=int(step_min), max_edges=int(step_max))
        route_landmark_ids = [str(cell_to_landmark_id[cell]) for cell in route]
        route_labels = [str(lookup[landmark_id]["landmark_label"]) for landmark_id in route_landmark_ids]
        directions = [_direction_between(source, target) for source, target in zip(route, route[1:])]
        answer_label = str(route_labels[-1])
        evidence_landmark_bbox_ids = [str(lookup[landmark_id]["landmark_bbox_id"]) for landmark_id in route_landmark_ids]
        direction_text = ", then ".join(str(direction) for direction in directions)
        question_text = (
            f"Starting at \"{route_labels[0]}\", follow the map directions to the next labeled landmark each time: "
            f"{direction_text}. What landmark do you reach? Return the exact landmark label."
        )
        evidence_semantics = "route_landmarks_ordered"
    elif str(query_variant) == "landmark_after_route_step":
        step_min, step_max = resolve_required_int_bounds(
            params,
            gen_defaults,
            min_key="highlighted_route_step_min",
            max_key="highlighted_route_step_max",
            fallback_min=int(defaults.highlighted_route_step_min),
            fallback_max=int(defaults.highlighted_route_step_max),
            context=f"{task_id} highlighted route step",
        )
        route = _sample_route(rng=rng, cells=cells, adjacency=adjacency, min_edges=max(int(step_min), 3), max_edges=int(step_max) + 1)
        route_landmark_ids = [str(cell_to_landmark_id[cell]) for cell in route]
        highlighted_route = list(route)
        route_labels = [str(lookup[landmark_id]["landmark_label"]) for landmark_id in route_landmark_ids]
        max_step = min(int(step_max), len(route_labels) - 1)
        step_index = int(
            int(step_min)
            + (
                resolve_selection_index(
                    params=params,
                    instance_seed=int(instance_seed),
                    namespace=f"{task_id}.highlighted_route_step",
                )
                % max(1, int(max_step) - int(step_min) + 1)
            )
        )
        answer_label = str(route_labels[step_index])
        evidence_landmark_bbox_ids = [
            str(lookup[landmark_id]["landmark_bbox_id"]) for landmark_id in route_landmark_ids[: int(step_index) + 1]
        ]
        question_text = (
            f"On the highlighted orange route from \"{route_labels[0]}\" to \"{route_labels[-1]}\", "
            f"what is the {_ordinal(step_index)} landmark reached after \"{route_labels[0]}\"? "
            "Return the exact landmark label."
        )
        evidence_semantics = "highlighted_route_landmarks_ordered_to_answer"
    else:
        raise ValueError(f"unsupported map query variant: {query_variant}")

    return {
        "scene_title": _title(rng=rng),
        "query_variant": str(query_variant),
        "scene_variant": "campus_map",
        "question_text": str(question_text),
        "question_format": "map_navigation_label",
        "view_family": "printed_campus_map",
        "grid_cols": int(_GRID_COLS),
        "grid_rows": int(_GRID_ROWS),
        "landmark_count": int(landmark_count),
        "zone_specs": [dict(spec) for spec in zone_specs],
        "landmark_specs": [dict(spec) for spec in landmark_specs],
        "path_specs": [dict(spec) for spec in path_specs],
        "highlighted_route_landmark_ids": list(route_landmark_ids if highlighted_route else []),
        "route_landmark_ids": list(route_landmark_ids),
        "answer_label": str(answer_label),
        "evidence_landmark_bbox_ids": list(evidence_landmark_bbox_ids),
        "evidence_zone_label_bbox_ids": list(evidence_zone_label_bbox_ids),
        "evidence_bbox_ids": [*evidence_landmark_bbox_ids, *evidence_zone_label_bbox_ids],
        "evidence_semantics": str(evidence_semantics),
    }


__all__ = [
    "MapDefaults",
    "MapRenderParams",
    "SUPPORTED_DOCUMENT_MAP_SCENE_VARIANTS",
    "SUPPORTED_DOCUMENT_MAP_QUERY_VARIANTS",
    "build_map_navigation_dataset",
    "resolve_map_render_params",
    "resolve_map_scene_variant",
    "resolve_map_query_variant",
]
