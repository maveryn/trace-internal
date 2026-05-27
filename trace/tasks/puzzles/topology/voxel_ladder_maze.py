"""Voxel-ladder maze puzzle tasks."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.named_colors import named_color, sample_named_color_palette
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import draw_text_centered, load_font
from ..shared.common import projected_puzzle_bbox_evidence
from ..shared.complexity import build_puzzle_complexity, normalize_int_with_bounds, resolve_puzzle_complexity_weights
from ..shared.scene_style import make_puzzle_scene_background, resolve_puzzle_scene_style
from ..shared.unit_size_jitter import resolve_puzzle_unit_size_scale, scale_puzzle_px, with_puzzle_unit_size_jitter
from ..shared.visual_defaults import load_puzzle_noise_defaults


ROUTE_LABEL_TASK_ID = "task_puzzles__voxel_ladder__voxel_ladder_route_label"
ROUTE_COUNT_TASK_ID = "task_puzzles__voxel_ladder__voxel_ladder_route_count"
SCENE_ID = "voxel_ladder"
LABEL_QUERY_IDS: Tuple[str, ...] = ("checkpoint_sequence_label", "unreachable_checkpoint_label")
COUNT_QUERY_IDS: Tuple[str, ...] = ("reachable_checkpoint_count", "shortest_ladder_count")
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "clean_isometric_voxels",
    "worksheet_voxel_maze",
    "game_board_voxel_maze",
)
OPTION_LABELS: Tuple[str, ...] = tuple("ABCDEF")

Color = Tuple[int, int, int]
Node = Tuple[int, int, int]
BBox = Tuple[float, float, float, float]

_TASK_GROUP_DEFAULTS = get_task_group_defaults("puzzles", "topology")
_COMPLEXITY_WEIGHTS = resolve_puzzle_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=ROUTE_LABEL_TASK_ID)
POST_IMAGE_NOISE_DEFAULTS = load_puzzle_noise_defaults(task_group="topology", apply_prob=0.0)


@dataclass(frozen=True)
class _Checkpoint:
    label: str
    color_name: str
    color_rgb: Color
    node: Node
    reachable: bool
    on_goal_route: bool


@dataclass(frozen=True)
class _Ladder:
    ladder_id: str
    lower: Node
    upper: Node
    on_goal_route: bool


@dataclass(frozen=True)
class _VoxelMazeDataset:
    query_id: str
    scene_variant: str
    cubes: Tuple[Node, ...]
    route_nodes: Tuple[Node, ...]
    route_edges: Tuple[Tuple[Node, Node], ...]
    start_node: Node
    goal_node: Node
    checkpoints: Tuple[_Checkpoint, ...]
    ladders: Tuple[_Ladder, ...]
    graph_edges: Tuple[Tuple[Node, Node], ...]
    answer_value: Any
    answer_type: str
    supporting_item_ids: Tuple[str, ...]
    option_specs: Tuple[Dict[str, Any], ...]
    reachable_checkpoint_count: int
    shortest_ladder_count: int
    route_checkpoint_sequence: Tuple[str, ...]


@dataclass(frozen=True)
class _RenderParams:
    canvas_width: int
    canvas_height: int
    board_left_px: int
    board_top_px: int
    board_width_px: int
    board_height_px: int
    option_panel_width_px: int
    cube_width_px: int
    cube_height_px: int
    cube_depth_px: int
    label_font_size_px: int
    option_font_size_px: int
    panel_fill_rgb: Color
    panel_border_rgb: Color
    text_rgb: Color
    text_stroke_rgb: Color
    neutral_top_rgb: Color
    neutral_left_rgb: Color
    neutral_right_rgb: Color
    start_top_rgb: Color
    goal_top_rgb: Color
    checkpoint_top_rgb: Color
    ladder_rgb: Color
    shadow_rgb: Color
    unit_size_scale: float
    unit_size_jitter: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedVoxelMaze:
    image: Image.Image
    entities: Tuple[Dict[str, Any], ...]
    item_bbox_map: Dict[str, BBox]
    scene_bbox_px: BBox


def _to_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(fallback)


def _normalize_rgb(value: Any, fallback: Color) -> Color:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        return (
            max(0, min(255, _to_int(value[0], fallback[0]))),
            max(0, min(255, _to_int(value[1], fallback[1]))),
            max(0, min(255, _to_int(value[2], fallback[2]))),
        )
    return tuple(int(channel) for channel in fallback)


def _rgb_option(params: Mapping[str, Any], defaults: Mapping[str, Any], key: str, fallback: Color, *, seed: int) -> Color:
    raw = params.get(str(key), group_default(defaults, str(key), fallback))
    options = params.get(f"{key}_options", group_default(defaults, f"{key}_options", None))
    if isinstance(options, list) and options:
        rng = spawn_rng(int(seed), f"voxel_ladder.render.{key}")
        return _normalize_rgb(options[int(rng.randrange(len(options)))], fallback)
    return _normalize_rgb(raw, fallback)


def _get_int_range(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
) -> Tuple[int, int]:
    lower = _to_int(params.get(min_key, group_default(defaults, min_key, fallback_min)), fallback_min)
    upper = _to_int(params.get(max_key, group_default(defaults, max_key, fallback_max)), fallback_max)
    if lower > upper:
        raise ValueError(f"{min_key} must be <= {max_key}")
    return int(lower), int(upper)


def _balanced_int(
    *,
    seed: int,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    min_key: str,
    max_key: str,
    fallback_min: int,
    fallback_max: int,
    namespace: str,
) -> Tuple[int, Tuple[int, int]]:
    lower, upper = _get_int_range(
        params,
        defaults,
        min_key=min_key,
        max_key=max_key,
        fallback_min=fallback_min,
        fallback_max=fallback_max,
    )
    explicit = params.get(key)
    if explicit is not None:
        value = _to_int(explicit, lower)
        if not (lower <= value <= upper):
            raise ValueError(f"{key} must be in [{lower}, {upper}]")
        return int(value), (lower, upper)
    support = list(range(lower, upper + 1))
    if bool(params.get("balanced_answer_sampling", group_default(defaults, "balanced_answer_sampling", True))):
        stable_offset = sum((index + 1) * ord(char) for index, char in enumerate(str(namespace)))
        idx = (int(seed) + int(stable_offset)) % len(support)
        return int(support[idx]), (lower, upper)
    rng = spawn_rng(int(seed), namespace)
    return int(rng.choice(support)), (lower, upper)


def _choose_axis(params: Mapping[str, Any], defaults: Mapping[str, Any], *, key: str, supported: Sequence[str], seed: int, namespace: str) -> Tuple[str, Dict[str, float]]:
    explicit = params.get(key)
    if explicit is None and key == "query_id":
        explicit = params.get("query_id")
    if explicit is None and key == "query_id":
        raw_query_id = params.get("query_id")
        if raw_query_id is not None and str(raw_query_id) != "default":
            explicit = raw_query_id
    if explicit is not None:
        text = str(explicit)
        if text not in set(map(str, supported)):
            raise ValueError(f"unsupported {key}: {text}")
        return text, {text: 1.0}
    weights_raw = params.get(f"{key}_weights", group_default(defaults, f"{key}_weights", None))
    weights: Dict[str, float] = {}
    if isinstance(weights_raw, Mapping):
        weights = {str(item): float(value) for item, value in weights_raw.items() if str(item) in set(supported) and float(value) > 0.0}
    if not weights:
        weights = {str(item): 1.0 for item in supported}
    labels = list(weights)
    total = float(sum(weights.values()))
    probabilities = {label: float(value) / total for label, value in weights.items()}
    if bool(params.get(f"balanced_{key}_sampling", group_default(defaults, f"balanced_{key}_sampling", True))):
        return str(labels[int(seed) % len(labels)]), probabilities
    rng = spawn_rng(int(seed), namespace)
    threshold = float(rng.random()) * total
    cumulative = 0.0
    for label in labels:
        cumulative += float(weights[label])
        if threshold <= cumulative:
            return str(label), probabilities
    return str(labels[-1]), probabilities


def _normalize_path(nodes: Sequence[Node], *, mirror_x: bool, swap_xy: bool) -> Tuple[Node, ...]:
    transformed: List[Node] = []
    for x, y, z in nodes:
        nx, ny = (-int(x) if mirror_x else int(x)), int(y)
        if swap_xy:
            nx, ny = ny, nx
        transformed.append((int(nx), int(ny), int(z)))
    min_x = min(node[0] for node in transformed)
    min_y = min(node[1] for node in transformed)
    return tuple((int(x - min_x), int(y - min_y), int(z)) for x, y, z in transformed)


def _build_route_path(rng: Any, *, ladder_count: int) -> Tuple[Node, ...]:
    x = 0
    y = 0
    z = 0
    path: List[Node] = [(x, y, z)]
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
    return _normalize_path(path, mirror_x=bool(rng.randrange(2)), swap_xy=bool(rng.randrange(2)))


def _neighbors(node: Node) -> Iterable[Node]:
    x, y, z = node
    yield (x + 1, y, z)
    yield (x - 1, y, z)
    yield (x, y + 1, z)
    yield (x, y - 1, z)


def _route_edges(route_nodes: Sequence[Node]) -> Tuple[Tuple[Node, Node], ...]:
    return tuple((tuple(route_nodes[index]), tuple(route_nodes[index + 1])) for index in range(len(route_nodes) - 1))  # type: ignore[arg-type]


def _is_ladder_edge(edge: Tuple[Node, Node]) -> bool:
    a, b = edge
    return int(a[0]) == int(b[0]) and int(a[1]) == int(b[1]) and int(a[2]) != int(b[2])


def _checkpoint_item_id(label: str) -> str:
    return f"checkpoint_{str(label)}"


def _make_graph_edges(cubes: Sequence[Node], ladders: Sequence[_Ladder]) -> Tuple[Tuple[Node, Node], ...]:
    cube_set = set(cubes)
    edges: set[Tuple[Node, Node]] = set()
    for node in cube_set:
        for neighbor in _neighbors(node):
            if neighbor in cube_set:
                edges.add(tuple(sorted((node, neighbor))))  # type: ignore[arg-type]
    for ladder in ladders:
        edges.add(tuple(sorted((ladder.lower, ladder.upper))))  # type: ignore[arg-type]
    return tuple(sorted(edges))


def _reachable_nodes(start: Node, edges: Sequence[Tuple[Node, Node]]) -> set[Node]:
    adjacency: Dict[Node, List[Node]] = {}
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


def _sequence_text(labels: Sequence[str]) -> str:
    return " > ".join(str(label) for label in labels)


def _sequence_distractors(rng: Any, correct: Sequence[str], all_labels: Sequence[str], option_count: int) -> List[Tuple[str, ...]]:
    correct_tuple = tuple(str(label) for label in correct)
    candidates: set[Tuple[str, ...]] = {correct_tuple}
    labels = [str(label) for label in all_labels]
    if len(correct) > 1:
        candidates.add(tuple(reversed(correct_tuple)))
    for label in labels:
        if label not in set(correct_tuple):
            for insert_at in range(len(correct) + 1):
                seq = list(correct_tuple)
                seq.insert(insert_at, label)
                candidates.add(tuple(seq))
            for replace_at in range(len(correct)):
                seq = list(correct_tuple)
                seq[replace_at] = label
                candidates.add(tuple(seq))
    for remove_at in range(len(correct)):
        seq = list(correct_tuple)
        seq.pop(remove_at)
        if seq:
            candidates.add(tuple(seq))
    for _ in range(64):
        seq = list(correct_tuple)
        rng.shuffle(seq)
        if seq:
            candidates.add(tuple(seq))
        if len(labels) >= len(correct):
            sampled = list(labels)
            rng.shuffle(sampled)
            candidates.add(tuple(sampled[: len(correct)]))
        if len(candidates) >= int(option_count):
            break
    suffix = 1
    while len(candidates) < int(option_count):
        candidates.add(tuple([str(label) for label in labels[: max(1, min(len(labels), len(correct)))]] + [str(labels[int(suffix) % len(labels)])]))
        suffix += 1
    return [item for item in sorted(candidates) if item != correct_tuple][: int(option_count) - 1]


def _build_dataset(
    *,
    task_id: str,
    query_id: str,
    scene_variant: str,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
) -> _VoxelMazeDataset:
    rng = spawn_rng(int(instance_seed), f"{task_id}.{query_id}.voxel_ladder")
    answer_axis_seed = int(instance_seed) // 2
    if str(query_id) == "shortest_ladder_count":
        ladder_count, _ = _balanced_int(
            seed=answer_axis_seed,
            params=params,
            defaults=gen_defaults,
            key="shortest_ladder_count",
            min_key="shortest_ladder_count_min",
            max_key="shortest_ladder_count_max",
            fallback_min=1,
            fallback_max=3,
            namespace=f"{task_id}.ladder_count",
        )
    else:
        ladder_min, ladder_max = _get_int_range(
            params,
            gen_defaults,
            min_key="shortest_ladder_count_min",
            max_key="shortest_ladder_count_max",
            fallback_min=1,
            fallback_max=3,
        )
        ladder_count = int(rng.randint(ladder_min, ladder_max))
    route_nodes = _build_route_path(rng, ladder_count=int(ladder_count))
    route_edges = _route_edges(route_nodes)
    ladder_edges = [edge for edge in route_edges if _is_ladder_edge(edge)]
    ladders = tuple(
        _Ladder(
            ladder_id=f"ladder_{index}",
            lower=min(edge[0], edge[1], key=lambda node: node[2]),
            upper=max(edge[0], edge[1], key=lambda node: node[2]),
            on_goal_route=True,
        )
        for index, edge in enumerate(ladder_edges)
    )
    cubes: set[Node] = set(route_nodes)
    route_candidates = [node for node in route_nodes[1:-1] if not any(node == ladder.upper for ladder in ladders)]
    if len(route_candidates) < 5:
        route_candidates = list(route_nodes[1:-1])
    if str(query_id) == "reachable_checkpoint_count":
        desired_reachable, _ = _balanced_int(
            seed=answer_axis_seed,
            params=params,
            defaults=gen_defaults,
            key="reachable_checkpoint_count",
            min_key="reachable_checkpoint_count_min",
            max_key="reachable_checkpoint_count_max",
            fallback_min=2,
            fallback_max=5,
            namespace=f"{task_id}.reachable_count",
        )
        main_count = min(int(desired_reachable), max(2, len(route_candidates)))
    else:
        route_min, route_max = _get_int_range(
            params,
            gen_defaults,
            min_key="route_checkpoint_count_min",
            max_key="route_checkpoint_count_max",
            fallback_min=2,
            fallback_max=4,
        )
        main_count = min(int(rng.randint(route_min, route_max)), max(2, len(route_candidates)))
    step = max(1, len(route_candidates) // max(1, main_count))
    main_nodes = list(route_candidates[::step][:main_count])
    while len(main_nodes) < main_count:
        candidate = route_candidates[int(rng.randrange(len(route_candidates)))]
        if candidate not in main_nodes:
            main_nodes.append(candidate)
    main_nodes = sorted(main_nodes, key=lambda node: route_nodes.index(node))

    reachable_branch_nodes: List[Node] = []
    if str(query_id) in {"checkpoint_sequence_label", "reachable_checkpoint_count"}:
        branch_needed = 1 if str(query_id) == "checkpoint_sequence_label" else max(0, int(desired_reachable) - len(main_nodes))  # type: ignore[name-defined]
        branch_sources = list(route_nodes[1:-1])
        rng.shuffle(branch_sources)
        if branch_needed > 0:
            for source in branch_sources:
                for neighbor in _neighbors(source):
                    if neighbor not in cubes and neighbor[2] >= 0:
                        cubes.add(neighbor)
                        reachable_branch_nodes.append(neighbor)
                        branch_needed -= 1
                        break
                if branch_needed <= 0:
                    break

    unreachable_nodes: List[Node] = []
    if str(query_id) in {"unreachable_checkpoint_label", "reachable_checkpoint_count", "shortest_ladder_count"}:
        unreachable_count = 1 if str(query_id) == "unreachable_checkpoint_label" else int(rng.randint(1, 2))
        max_x = max(node[0] for node in cubes)
        max_y = max(node[1] for node in cubes)
        for index in range(unreachable_count):
            node = (max_x + 3 + index, max_y + int(rng.randint(0, 2)), int(rng.randint(0, max(1, ladder_count))))
            cubes.add(node)
            unreachable_nodes.append(node)

    label_count = len(main_nodes) + len(reachable_branch_nodes) + len(unreachable_nodes)
    sampled_palette = sample_named_color_palette(rng, palette_size=int(label_count))
    if len(sampled_palette) < int(label_count):
        raise RuntimeError("voxel-ladder checkpoint count exceeds canonical named-color palette")
    checkpoints: List[_Checkpoint] = []
    label_index = 0
    for node in main_nodes:
        color_name, color_rgb = sampled_palette[label_index]
        checkpoints.append(_Checkpoint(str(color_name), str(color_name), tuple(int(v) for v in color_rgb), node, True, True))
        label_index += 1
    for node in reachable_branch_nodes:
        color_name, color_rgb = sampled_palette[label_index]
        checkpoints.append(_Checkpoint(str(color_name), str(color_name), tuple(int(v) for v in color_rgb), node, True, False))
        label_index += 1
    for node in unreachable_nodes:
        color_name, color_rgb = sampled_palette[label_index]
        checkpoints.append(_Checkpoint(str(color_name), str(color_name), tuple(int(v) for v in color_rgb), node, False, False))
        label_index += 1

    route_checkpoint_labels = tuple(str(cp.color_name) for cp in sorted((cp for cp in checkpoints if cp.on_goal_route), key=lambda cp: route_nodes.index(cp.node)))
    reachable_checkpoint_count = sum(1 for cp in checkpoints if cp.reachable)
    option_specs: List[Dict[str, Any]] = []
    if str(query_id) == "checkpoint_sequence_label":
        option_count, _ = _balanced_int(
            seed=answer_axis_seed,
            params=params,
            defaults=gen_defaults,
            key="route_option_count",
            min_key="route_option_count_min",
            max_key="route_option_count_max",
            fallback_min=4,
            fallback_max=5,
            namespace=f"{task_id}.route_option_count",
        )
        correct_sequence = tuple(route_checkpoint_labels)
        distractors = _sequence_distractors(rng, correct_sequence, [cp.color_name for cp in checkpoints], int(option_count))
        correct_index = answer_axis_seed % int(option_count)
        option_sequences = list(distractors)
        option_sequences.insert(correct_index, correct_sequence)
        option_specs = [
            {
                "option_label": OPTION_LABELS[index],
                "sequence_items": list(option_sequences[index]),
                "sequence_text": _sequence_text(option_sequences[index]),
                "sequence_rgb": [list(named_color(str(name))) for name in option_sequences[index]],
                "is_correct": bool(index == correct_index),
            }
            for index in range(int(option_count))
        ]
        answer_value = str(OPTION_LABELS[correct_index])
        answer_type = "option_letter"
        supporting_item_ids = ("cube_start",) + tuple(_checkpoint_item_id(label) for label in route_checkpoint_labels) + tuple(ladder.ladder_id for ladder in ladders if ladder.on_goal_route) + ("cube_goal",)
    elif str(query_id) == "unreachable_checkpoint_label":
        unreachable_cp = next(cp for cp in checkpoints if not cp.reachable)
        answer_value = str(unreachable_cp.color_name)
        answer_type = "string"
        supporting_item_ids = (_checkpoint_item_id(unreachable_cp.color_name),)
    elif str(query_id) == "reachable_checkpoint_count":
        answer_value = int(reachable_checkpoint_count)
        answer_type = "integer"
        supporting_item_ids = tuple(_checkpoint_item_id(cp.color_name) for cp in checkpoints if cp.reachable)
    elif str(query_id) == "shortest_ladder_count":
        answer_value = int(len(ladders))
        answer_type = "integer"
        supporting_item_ids = tuple(ladder.ladder_id for ladder in ladders if ladder.on_goal_route)
    else:
        raise ValueError(f"unsupported query_id: {query_id}")

    graph_edges = _make_graph_edges(tuple(sorted(cubes)), ladders)
    reachable = _reachable_nodes(route_nodes[0], graph_edges)
    for cp in checkpoints:
        if bool(cp.reachable) != bool(cp.node in reachable):
            raise RuntimeError("voxel-ladder checkpoint reachability drift")
    if str(query_id) in {"reachable_checkpoint_count", "shortest_ladder_count"} and int(answer_value) == 0:
        raise RuntimeError("voxel-ladder generated zero-count query unexpectedly")

    return _VoxelMazeDataset(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        cubes=tuple(sorted(cubes)),
        route_nodes=tuple(route_nodes),
        route_edges=tuple(route_edges),
        start_node=tuple(route_nodes[0]),
        goal_node=tuple(route_nodes[-1]),
        checkpoints=tuple(checkpoints),
        ladders=tuple(ladders),
        graph_edges=tuple(graph_edges),
        answer_value=answer_value,
        answer_type=str(answer_type),
        supporting_item_ids=tuple(str(item) for item in supporting_item_ids),
        option_specs=tuple(option_specs),
        reachable_checkpoint_count=int(reachable_checkpoint_count),
        shortest_ladder_count=int(len(ladders)),
        route_checkpoint_sequence=tuple(route_checkpoint_labels),
    )


def _resolve_render_params(params: Mapping[str, Any], render_defaults: Mapping[str, Any], *, instance_seed: int) -> _RenderParams:
    unit_scale, unit_meta = resolve_puzzle_unit_size_scale(
        params,
        render_defaults,
        instance_seed=int(instance_seed),
        namespace="puzzles.voxel_ladder.unit_size",
    )
    cube_width = scale_puzzle_px(_to_int(params.get("cube_width_px", group_default(render_defaults, "cube_width_px", 72)), 72), unit_scale, min_px=50)
    cube_height = max(26, int(round(float(cube_width) * 0.50)))
    cube_depth = max(30, int(round(float(cube_width) * 0.58)))
    return _RenderParams(
        canvas_width=max(900, _to_int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 1100)), 1100)),
        canvas_height=max(720, _to_int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 820)), 820)),
        board_left_px=max(40, _to_int(params.get("board_left_px", group_default(render_defaults, "board_left_px", 58)), 58)),
        board_top_px=max(40, _to_int(params.get("board_top_px", group_default(render_defaults, "board_top_px", 76)), 76)),
        board_width_px=max(580, _to_int(params.get("board_width_px", group_default(render_defaults, "board_width_px", 720)), 720)),
        board_height_px=max(560, _to_int(params.get("board_height_px", group_default(render_defaults, "board_height_px", 640)), 640)),
        option_panel_width_px=max(240, _to_int(params.get("option_panel_width_px", group_default(render_defaults, "option_panel_width_px", 300)), 300)),
        cube_width_px=int(cube_width),
        cube_height_px=int(cube_height),
        cube_depth_px=int(cube_depth),
        label_font_size_px=max(16, scale_puzzle_px(_to_int(params.get("label_font_size_px", group_default(render_defaults, "label_font_size_px", 25)), 25), unit_scale, min_px=16)),
        option_font_size_px=max(16, _to_int(params.get("option_font_size_px", group_default(render_defaults, "option_font_size_px", 24)), 24)),
        panel_fill_rgb=_rgb_option(params, render_defaults, "panel_fill_rgb", (248, 250, 252), seed=int(instance_seed)),
        panel_border_rgb=_rgb_option(params, render_defaults, "panel_border_rgb", (82, 91, 105), seed=int(instance_seed)),
        text_rgb=_rgb_option(params, render_defaults, "text_rgb", (24, 28, 35), seed=int(instance_seed)),
        text_stroke_rgb=_rgb_option(params, render_defaults, "text_stroke_rgb", (255, 255, 255), seed=int(instance_seed)),
        neutral_top_rgb=_rgb_option(params, render_defaults, "neutral_top_rgb", (179, 185, 192), seed=int(instance_seed)),
        neutral_left_rgb=_rgb_option(params, render_defaults, "neutral_left_rgb", (129, 137, 148), seed=int(instance_seed)),
        neutral_right_rgb=_rgb_option(params, render_defaults, "neutral_right_rgb", (151, 159, 169), seed=int(instance_seed)),
        start_top_rgb=_rgb_option(params, render_defaults, "start_top_rgb", (86, 128, 235), seed=int(instance_seed)),
        goal_top_rgb=_rgb_option(params, render_defaults, "goal_top_rgb", (236, 92, 88), seed=int(instance_seed)),
        checkpoint_top_rgb=_rgb_option(params, render_defaults, "checkpoint_top_rgb", (96, 222, 111), seed=int(instance_seed)),
        ladder_rgb=_rgb_option(params, render_defaults, "ladder_rgb", (33, 37, 42), seed=int(instance_seed)),
        shadow_rgb=_rgb_option(params, render_defaults, "shadow_rgb", (222, 226, 232), seed=int(instance_seed)),
        unit_size_scale=float(unit_scale),
        unit_size_jitter=dict(unit_meta),
    )


def _cube_polygons(node: Node, *, origin_x: float, origin_y: float, params: _RenderParams) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]], List[Tuple[float, float]], BBox]:
    x, y, z = node
    w = float(params.cube_width_px)
    h = float(params.cube_height_px)
    d = float(params.cube_depth_px)
    cx = float(origin_x) + ((float(x) - float(y)) * w * 0.5)
    cy = float(origin_y) + ((float(x) + float(y)) * h * 0.5) - (float(z) * d)
    top = [(cx, cy - h * 0.5), (cx + w * 0.5, cy), (cx, cy + h * 0.5), (cx - w * 0.5, cy)]
    left = [(cx - w * 0.5, cy), (cx, cy + h * 0.5), (cx, cy + h * 0.5 + d), (cx - w * 0.5, cy + d)]
    right = [(cx + w * 0.5, cy), (cx, cy + h * 0.5), (cx, cy + h * 0.5 + d), (cx + w * 0.5, cy + d)]
    points = top + left + right
    bbox = (
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )
    return top, left, right, bbox


def _node_top_center(node: Node, *, origin_x: float, origin_y: float, params: _RenderParams) -> Tuple[float, float]:
    x, y, z = node
    return (
        float(origin_x) + ((float(x) - float(y)) * float(params.cube_width_px) * 0.5),
        float(origin_y) + ((float(x) + float(y)) * float(params.cube_height_px) * 0.5) - (float(z) * float(params.cube_depth_px)),
    )


def _blend(color: Color, target: Color, amount: float) -> Color:
    return tuple(int(round((float(channel) * (1.0 - amount)) + (float(target_channel) * amount))) for channel, target_channel in zip(color, target))


def _cube_colors(kind: str, params: _RenderParams, *, top_override: Color | None = None) -> Tuple[Color, Color, Color]:
    if kind == "start":
        top = params.start_top_rgb
    elif kind == "goal":
        top = params.goal_top_rgb
    elif kind == "checkpoint":
        top = tuple(int(v) for v in (top_override or params.checkpoint_top_rgb))
    else:
        top = params.neutral_top_rgb
    return top, _blend(top, (30, 36, 46), 0.28), _blend(top, (30, 36, 46), 0.16)


def _inflate_bbox(bbox: BBox, pad: float) -> BBox:
    return (float(bbox[0]) - pad, float(bbox[1]) - pad, float(bbox[2]) + pad, float(bbox[3]) + pad)


def _union_bboxes(bboxes: Iterable[BBox]) -> BBox:
    items = list(bboxes)
    return (
        min(b[0] for b in items),
        min(b[1] for b in items),
        max(b[2] for b in items),
        max(b[3] for b in items),
    )


def _render_voxel_maze(background: Image.Image, *, dataset: _VoxelMazeDataset, render_params: _RenderParams) -> _RenderedVoxelMaze:
    image = background.convert("RGB")
    draw = ImageDraw.Draw(image)
    raw_bboxes = [_cube_polygons(node, origin_x=0, origin_y=0, params=render_params)[3] for node in dataset.cubes]
    raw_bbox = _union_bboxes(raw_bboxes)
    board_right = float(render_params.board_left_px + render_params.board_width_px)
    if dataset.option_specs:
        board_right = float(render_params.canvas_width - render_params.option_panel_width_px - 44)
    board_center_x = float(render_params.board_left_px + board_right) * 0.5
    board_center_y = float(render_params.board_top_px + (0.52 * render_params.board_height_px))
    origin_x = board_center_x - ((raw_bbox[0] + raw_bbox[2]) * 0.5)
    origin_y = board_center_y - ((raw_bbox[1] + raw_bbox[3]) * 0.5)
    cube_bboxes = {node: _cube_polygons(node, origin_x=origin_x, origin_y=origin_y, params=render_params)[3] for node in dataset.cubes}
    scene_bbox = _inflate_bbox(_union_bboxes(cube_bboxes.values()), 24.0)
    floor = [
        (scene_bbox[0] - 18, scene_bbox[3] - 34),
        (scene_bbox[0] + 0.5 * (scene_bbox[2] - scene_bbox[0]), scene_bbox[3] - 110),
        (scene_bbox[2] + 24, scene_bbox[3] - 34),
        (scene_bbox[0] + 0.5 * (scene_bbox[2] - scene_bbox[0]), scene_bbox[3] + 42),
    ]
    draw.polygon(floor, fill=tuple(int(v) for v in render_params.shadow_rgb))

    item_bbox_map: Dict[str, BBox] = {}
    entities: List[Dict[str, Any]] = []
    checkpoint_by_node = {cp.node: cp for cp in dataset.checkpoints}
    label_font = load_font(int(render_params.label_font_size_px), bold=True)
    small_font = load_font(max(13, int(render_params.label_font_size_px * 0.62)), bold=True)
    for node in sorted(dataset.cubes, key=lambda n: (n[0] + n[1], n[2], n[0])):
        cp = checkpoint_by_node.get(node)
        kind = "neutral"
        item_id = f"cube_{node[0]}_{node[1]}_{node[2]}"
        label_text = ""
        text_fill = render_params.text_rgb
        if node == dataset.start_node:
            kind = "start"
            item_id = "cube_start"
            label_text = "START"
            text_fill = (255, 255, 255)
        elif node == dataset.goal_node:
            kind = "goal"
            item_id = "cube_goal"
            label_text = "GOAL"
            text_fill = (255, 255, 255)
        elif cp is not None:
            kind = "checkpoint"
            item_id = _checkpoint_item_id(cp.color_name)
            label_text = ""
        top, left, right, bbox = _cube_polygons(node, origin_x=origin_x, origin_y=origin_y, params=render_params)
        top_color, left_color, right_color = _cube_colors(kind, render_params, top_override=cp.color_rgb if cp is not None else None)
        outline = _blend(render_params.panel_border_rgb, (0, 0, 0), 0.08)
        draw.polygon(left, fill=left_color, outline=outline)
        draw.polygon(right, fill=right_color, outline=outline)
        draw.polygon(top, fill=top_color, outline=outline)
        cx, cy = _node_top_center(node, origin_x=origin_x, origin_y=origin_y, params=render_params)
        if cp is not None:
            marker_radius = max(8.0, 0.16 * float(render_params.cube_width_px))
            marker_bbox = (
                cx - marker_radius,
                cy - (0.58 * marker_radius),
                cx + marker_radius,
                cy + (0.58 * marker_radius),
            )
            draw.ellipse(marker_bbox, outline=(255, 255, 255), width=max(3, int(round(0.055 * render_params.cube_width_px))))
            draw.ellipse(
                (
                    cx - (0.43 * marker_radius),
                    cy - (0.25 * marker_radius),
                    cx + (0.43 * marker_radius),
                    cy + (0.25 * marker_radius),
                ),
                fill=_blend(top_color, (255, 255, 255), 0.18),
                outline=_blend(top_color, (0, 0, 0), 0.25),
                width=1,
            )
        item_bbox_map[item_id] = _inflate_bbox(bbox, 3.0)
        entities.append(
            {
                "item_id": item_id,
                "entity_type": "voxel_maze_cube",
                "node": [int(node[0]), int(node[1]), int(node[2])],
                "cube_kind": kind,
                "label": label_text,
                "checkpoint_color_name": str(cp.color_name) if cp is not None else None,
                "checkpoint_color_rgb": list(cp.color_rgb) if cp is not None else None,
                "bbox_px": [round(float(v), 3) for v in item_bbox_map[item_id]],
            }
        )
        if label_text:
            font = small_font if label_text in {"START", "GOAL"} else label_font
            draw_text_centered(
                draw,
                text=label_text,
                center=(cx, cy + (0.05 * render_params.cube_height_px)),
                font=font,
                fill=text_fill,
                stroke_fill=render_params.text_stroke_rgb if text_fill != (255, 255, 255) else (28, 32, 38),
                stroke_width=2,
            )

    ladder_pad = float(max(6, int(0.12 * render_params.cube_width_px)))
    for ladder in dataset.ladders:
        lx, ly = _node_top_center(ladder.lower, origin_x=origin_x, origin_y=origin_y, params=render_params)
        ux, uy = _node_top_center(ladder.upper, origin_x=origin_x, origin_y=origin_y, params=render_params)
        x_offset = 0.20 * float(render_params.cube_width_px)
        p0 = (lx + x_offset, ly + 0.32 * float(render_params.cube_height_px))
        p1 = (ux + x_offset, uy + 0.32 * float(render_params.cube_height_px))
        rail_gap = max(6.0, 0.07 * float(render_params.cube_width_px))
        width = max(3, int(round(0.055 * render_params.cube_width_px)))
        for delta in (-rail_gap, rail_gap):
            draw.line((p0[0] + delta, p0[1], p1[0] + delta, p1[1]), fill=render_params.ladder_rgb, width=width)
        rung_count = max(2, int(abs(p0[1] - p1[1]) // max(18, render_params.cube_depth_px * 0.36)))
        for rung_index in range(1, rung_count + 1):
            t = rung_index / float(rung_count + 1)
            ry = p0[1] + ((p1[1] - p0[1]) * t)
            rx = p0[0] + ((p1[0] - p0[0]) * t)
            draw.line((rx - rail_gap, ry, rx + rail_gap, ry), fill=render_params.ladder_rgb, width=max(2, width - 1))
        bbox = (
            min(p0[0], p1[0]) - ladder_pad,
            min(p0[1], p1[1]) - ladder_pad,
            max(p0[0], p1[0]) + ladder_pad,
            max(p0[1], p1[1]) + ladder_pad,
        )
        item_bbox_map[ladder.ladder_id] = bbox
        entities.append(
            {
                "item_id": ladder.ladder_id,
                "entity_type": "voxel_maze_ladder",
                "lower_node": [int(v) for v in ladder.lower],
                "upper_node": [int(v) for v in ladder.upper],
                "on_goal_route": bool(ladder.on_goal_route),
                "bbox_px": [round(float(v), 3) for v in bbox],
            }
        )

    if dataset.option_specs:
        panel_x0 = float(render_params.canvas_width - render_params.option_panel_width_px - 34)
        panel_y0 = 96.0
        panel_x1 = float(render_params.canvas_width - 34)
        panel_y1 = panel_y0 + 62.0 + (float(len(dataset.option_specs)) * 54.0)
        draw.rounded_rectangle((panel_x0, panel_y0, panel_x1, panel_y1), radius=18, fill=render_params.panel_fill_rgb, outline=render_params.panel_border_rgb, width=2)
        title_font = load_font(21, bold=True)
        draw_text_centered(draw, text="Color route options", center=((panel_x0 + panel_x1) / 2.0, panel_y0 + 30), font=title_font, fill=render_params.text_rgb, stroke_fill=render_params.text_stroke_rgb, stroke_width=1)
        option_font = load_font(int(render_params.option_font_size_px), bold=True)
        for index, option in enumerate(dataset.option_specs):
            y0 = panel_y0 + 58 + (index * 54)
            card_bbox = (panel_x0 + 18, y0, panel_x1 - 18, y0 + 42)
            draw.rounded_rectangle(card_bbox, radius=10, fill=(255, 255, 255), outline=_blend(render_params.panel_border_rgb, (255, 255, 255), 0.18), width=2)
            draw.text((card_bbox[0] + 14, card_bbox[1] + 8), f"{option['option_label']}.", fill=render_params.text_rgb, font=option_font)
            sequence_items = [str(item) for item in option.get("sequence_items", [])]
            dot_radius = 10.0
            dot_step = 34.0
            dot_x = float(card_bbox[0] + 60)
            dot_y = float(card_bbox[1] + 21)
            for item_index, color_name in enumerate(sequence_items):
                center_x = dot_x + (float(item_index) * dot_step)
                color_rgb = tuple(int(v) for v in named_color(str(color_name)))
                draw.ellipse(
                    (center_x - dot_radius, dot_y - dot_radius, center_x + dot_radius, dot_y + dot_radius),
                    fill=color_rgb,
                    outline=_blend(color_rgb, (0, 0, 0), 0.35),
                    width=2,
                )
                if item_index < len(sequence_items) - 1:
                    x0 = center_x + dot_radius + 4
                    x1 = center_x + dot_step - dot_radius - 4
                    draw.line((x0, dot_y, x1, dot_y), fill=render_params.text_rgb, width=2)
                    draw.polygon(
                        [(x1, dot_y), (x1 - 5, dot_y - 4), (x1 - 5, dot_y + 4)],
                        fill=render_params.text_rgb,
                    )
            item_bbox_map[f"option_{option['option_label']}"] = card_bbox
            entities.append(
                {
                    "item_id": f"option_{option['option_label']}",
                    "entity_type": "voxel_maze_route_option",
                    "option_label": str(option["option_label"]),
                    "sequence_text": str(option["sequence_text"]),
                    "sequence_items": list(sequence_items),
                    "sequence_rgb": [list(named_color(str(color_name))) for color_name in sequence_items],
                    "is_correct": bool(option["is_correct"]),
                    "bbox_px": [round(float(v), 3) for v in card_bbox],
                }
            )

    rounded_scene_bbox = tuple(round(float(v), 3) for v in scene_bbox)
    return _RenderedVoxelMaze(
        image=image,
        entities=tuple(entities),
        item_bbox_map={key: tuple(round(float(v), 3) for v in value) for key, value in item_bbox_map.items()},
        scene_bbox_px=rounded_scene_bbox,  # type: ignore[arg-type]
    )


class _PuzzlesTopologyVoxelLadderMazeBaseTask:
    domain = "puzzles"
    task_group = "topology"
    default_dataset_enabled = True
    task_id: str
    supported_query_ids: Tuple[str, ...]
    task_key: str

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        gen_defaults, render_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
            task_id=str(self.task_id),
        )
        query_id, query_probabilities = _choose_axis(
            params,
            gen_defaults,
            key="query_id",
            supported=self.supported_query_ids,
            seed=int(instance_seed),
            namespace=f"{self.task_id}.query_id",
        )
        scene_variant, scene_variant_probabilities = _choose_axis(
            params,
            gen_defaults,
            key="scene_variant",
            supported=SUPPORTED_SCENE_VARIANTS,
            seed=int(instance_seed) // max(1, len(self.supported_query_ids)),
            namespace=f"{self.task_id}.scene_variant",
        )
        dataset = _build_dataset(
            task_id=str(self.task_id),
            query_id=str(query_id),
            scene_variant=str(scene_variant),
            params=params,
            gen_defaults=gen_defaults,
            instance_seed=int(instance_seed),
        )
        render_params = _resolve_render_params(params, render_defaults, instance_seed=int(instance_seed))
        scene_style, scene_style_meta = resolve_puzzle_scene_style(
            instance_seed=int(instance_seed),
            namespace=f"{self.task_id}.voxel_ladder_background",
        )
        background, background_meta = make_puzzle_scene_background(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            style=scene_style,
        )
        rendered = _render_voxel_maze(background, dataset=dataset, render_params=render_params)
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults_required = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                f"object_description_{scene_variant}",
                f"answer_hint_{query_id}",
                f"evidence_hint_{query_id}",
                f"json_example_{query_id}",
                f"json_example_answer_only_{query_id}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_hint = str(prompt_defaults_required[f"answer_hint_{query_id}"])
        evidence_hint = str(prompt_defaults_required[f"evidence_hint_{query_id}"])
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults_required["bundle_id"]),
            scene_key=str(prompt_defaults_required["scene_key"]),
            task_key=str(prompt_defaults_required["task_key"]),
            query_key=str(query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults_required[f"object_description_{scene_variant}"]),
                "json_output_contract": str(prompt_defaults_required["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults_required["json_output_contract_answer_only"]),
                "answer_hint": answer_hint,
                "evidence_hint": evidence_hint,
                "json_example": str(prompt_defaults_required[f"json_example_{query_id}"]),
                "json_example_answer_only": str(prompt_defaults_required[f"json_example_answer_only_{query_id}"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_projection = projected_puzzle_bbox_evidence(rendered.item_bbox_map, dataset.supporting_item_ids)
        evidence_bboxes = [[round(float(v), 3) for v in bbox] for bbox in evidence_projection["bbox_set"]]
        if len(evidence_bboxes) != len(dataset.supporting_item_ids):
            raise ValueError("voxel-ladder evidence projection does not match supporting item ids")
        answer_gt = TypedValue(type=str(dataset.answer_type), value=dataset.answer_value)
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        visual_scan = normalize_int_with_bounds(len(dataset.cubes), [8, 20])
        route_load = normalize_int_with_bounds(len(dataset.route_nodes), [5, 14])
        evidence_load = min(1.0, len(evidence_bboxes) / 8.0)
        complexity = build_puzzle_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "visual_scan": float(visual_scan),
                "reasoning_load": min(1.0, 0.35 + (0.35 * float(route_load)) + (0.20 * float(evidence_load))),
                "scene_variant_load": 0.38 if str(scene_variant) == "game_board_voxel_maze" else 0.30,
            },
        )

        rounded_bboxes = {key: [round(float(v), 3) for v in bbox] for key, bbox in rendered.item_bbox_map.items()}
        checkpoint_specs = [
            {
                "label": cp.color_name,
                "color_name": cp.color_name,
                "color_rgb": list(cp.color_rgb),
                "node": [int(v) for v in cp.node],
                "reachable": bool(cp.reachable),
                "on_goal_route": bool(cp.on_goal_route),
                "item_id": _checkpoint_item_id(cp.color_name),
            }
            for cp in dataset.checkpoints
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"puzzle_topology_voxel_ladder_{scene_variant}",
                "entities": [dict(entity) for entity in rendered.entities],
                "relations": {
                    "scene_id": SCENE_ID,
                    "query_id": str(query_id),
                    "internal_query_id": str(query_id),
                    "scene_variant": str(scene_variant),
                    "answer_value": dataset.answer_value,
                    "supporting_item_ids": list(dataset.supporting_item_ids),
                },
            },
            "query_spec": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "template_id": str(prompt_defaults_required["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_id": SCENE_ID,
                    "query_id": str(query_id),
                    "query_id_probabilities": dict(query_probabilities),
                    "scene_variant": str(scene_variant),
                    "scene_variant_probabilities": dict(scene_variant_probabilities),
                },
            },
            "render_spec": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(scene_variant),
                "background_style": dict(background_meta),
                "scene_style": dict(scene_style_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": [round(float(v), 3) for v in rendered.scene_bbox_px],
                "layout": "isometric_voxel_platforms_with_ladders",
                "cube_width_px": int(render_params.cube_width_px),
                "cube_height_px": int(render_params.cube_height_px),
                "cube_depth_px": int(render_params.cube_depth_px),
                "unit_size_jitter": dict(render_params.unit_size_jitter),
            },
            "render_map": with_puzzle_unit_size_jitter(
                {
                    "image_id": "img0",
                    "scene_bbox_px": [round(float(v), 3) for v in rendered.scene_bbox_px],
                    "item_bboxes_px": dict(rounded_bboxes),
                    "evidence_source": "item_bboxes_px",
                },
                render_params.unit_size_jitter,
            ),
            "execution_trace": {
                "scene_id": SCENE_ID,
                "query_id": str(query_id),
                "internal_query_id": str(query_id),
                "scene_variant": str(scene_variant),
                "question_format": str(query_id),
                "view_family": "isometric_voxel_ladder",
                "topology_rule": "walk_on_adjacent_same-height cube tops and use black ladders for vertical transitions",
                "start_node": [int(v) for v in dataset.start_node],
                "goal_node": [int(v) for v in dataset.goal_node],
                "route_nodes": [[int(v) for v in node] for node in dataset.route_nodes],
                "route_edges": [[[int(v) for v in a], [int(v) for v in b]] for a, b in dataset.route_edges],
                "graph_edges": [[[int(v) for v in a], [int(v) for v in b]] for a, b in dataset.graph_edges],
                "checkpoints": checkpoint_specs,
                "ladders": [
                    {
                        "ladder_id": ladder.ladder_id,
                        "lower": [int(v) for v in ladder.lower],
                        "upper": [int(v) for v in ladder.upper],
                        "on_goal_route": bool(ladder.on_goal_route),
                    }
                    for ladder in dataset.ladders
                ],
                "option_specs": [dict(option) for option in dataset.option_specs],
                "route_checkpoint_sequence": list(dataset.route_checkpoint_sequence),
                "reachable_checkpoint_count": int(dataset.reachable_checkpoint_count),
                "shortest_ladder_count": int(dataset.shortest_ladder_count),
                "answer_value": dataset.answer_value,
                "supporting_item_ids": list(dataset.supporting_item_ids),
                "supporting_evidence_source": "item_bboxes_px",
                "evidence_policy": "bbox_set over route/count support items",
                "query_id_probabilities": dict(query_probabilities),
                "scene_variant_probabilities": dict(scene_variant_probabilities),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
                "item_ids": list(dataset.supporting_item_ids),
            },
            "projected_evidence": dict(evidence_projection),
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
            complexity=TaskComplexity(
                complexity_score=float(complexity.complexity_score),
                complexity_components=dict(complexity.complexity_components),
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class PuzzlesTopologyVoxelLadderRouteLabelTask(_PuzzlesTopologyVoxelLadderMazeBaseTask):
    """Label query over a voxel ladder route."""

    task_id = ROUTE_LABEL_TASK_ID
    supported_query_ids = LABEL_QUERY_IDS
    task_key = "voxel_ladder_route_label_query"


@register_task
class PuzzlesTopologyVoxelLadderRouteCountTask(_PuzzlesTopologyVoxelLadderMazeBaseTask):
    """Count query over a voxel ladder route."""

    task_id = ROUTE_COUNT_TASK_ID
    supported_query_ids = COUNT_QUERY_IDS
    task_key = "voxel_ladder_route_count_query"


__all__ = [
    "PuzzlesTopologyVoxelLadderRouteCountTask",
    "PuzzlesTopologyVoxelLadderRouteLabelTask",
]
