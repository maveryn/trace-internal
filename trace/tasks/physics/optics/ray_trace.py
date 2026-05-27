"""Physics optics task for simple ray-tracing with diagonal mirrors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.graph_point_evidence import labeled_grid_point_evidence_artifacts
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_render_int
from ...shared.variant_sampling import (
    apply_balanced_variant_sampling,
    resolve_compatible_scene_query_variants,
    resolve_variant,
)
from ..shared.complexity import build_physics_optics_ray_trace_complexity
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.fixed_query_task import FixedPhysicsQueryVariantTaskMixin
from ..shared.optics_scene import RenderedOpticsScene, render_optics_ray_scene
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES
from ..shared.support_sampling import resolve_integer_choice, resolve_integer_support
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "physics_optics_ray_trace_family"
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = (
    "single_mirror",
    "double_mirror",
    "triple_mirror",
    "quad_mirror",
    "five_mirror",
)
SUPPORTED_QUERY_VARIANTS: Tuple[str, ...] = (
    "bounce_count",
    "target_hit_count",
)
COMPATIBILITY: Dict[str, Sequence[str]] = {
    "single_mirror": ("target_hit_count",),
    "double_mirror": ("target_hit_count",),
    "triple_mirror": ("target_hit_count",),
    "quad_mirror": ("bounce_count",),
    "five_mirror": ("bounce_count",),
}
_SCENE_MIRROR_COUNT = {
    "single_mirror": 1,
    "double_mirror": 2,
    "triple_mirror": 3,
    "quad_mirror": 4,
    "five_mirror": 5,
}
_DIRECTION_STEP = {
    "E": (1, 0),
    "W": (-1, 0),
    "N": (0, -1),
    "S": (0, 1),
}
_REFLECT_SLASH = {"E": "N", "N": "E", "W": "S", "S": "W"}
_REFLECT_BACKSLASH = {"E": "S", "S": "E", "W": "N", "N": "W"}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for optics ray-trace scenes."""

    canvas_width: int = 920
    canvas_height: int = 560
    board_left_px: int = 112
    board_top_px: int = 72
    board_cols: int = 8
    board_rows: int = 8
    cell_size_px: int = 52
    board_grid_width_px: int = 1
    board_outline_width_px: int = 3
    mirror_width_px: int = 7
    mirror_padding_px: int = 6
    ray_width_px: int = 6
    ray_head_length_px: int = 16
    ray_head_width_px: int = 16
    target_radius_px: int = 18
    source_radius_px: int = 14
    bounce_radius_px: int = 8
    target_font_size_px: int = 18
    source_font_size_px: int = 16
    label_stroke_width_px: int = 3
    bounce_count_support_single_mirror: Tuple[int, ...] = (0, 1)
    bounce_count_support_double_mirror: Tuple[int, ...] = (0, 1, 2)
    bounce_count_support_triple_mirror: Tuple[int, ...] = (0, 1, 2, 3)
    bounce_count_support_quad_mirror: Tuple[int, ...] = (0, 1, 2, 3, 4)
    bounce_count_support_five_mirror: Tuple[int, ...] = (1, 2, 3, 4, 5)
    target_hit_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    target_count_min: int = 4
    target_count_max: int = 5


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved scene/query axes and answer support for one instance."""

    scene_variant: str
    query_variant: str
    accent_color_name: str
    target_answer: int
    scene_variant_probabilities: Dict[str, float]
    query_variant_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _MirrorPlacement:
    """One logical mirror placement on the board."""

    mirror_id: str
    col: int
    row: int
    orientation: str
    hit: bool


@dataclass(frozen=True)
class _TargetPlacement:
    """One logical target placement on the board."""

    target_id: str
    col: int
    row: int
    label: int
    hit: bool


@dataclass(frozen=True)
class _SceneLayout:
    """One fully resolved optics board before rendering."""

    scene_variant: str
    query_variant: str
    target_answer: int
    source_row: int
    mirrors: Tuple[_MirrorPlacement, ...]
    targets: Tuple[_TargetPlacement, ...]
    path_cells: Tuple[Tuple[int, int], ...]
    bounce_cells: Tuple[Tuple[int, int], ...]
    source_point_px: Tuple[float, float]
    exit_point_px: Tuple[float, float]
    evidence_entity_ids: Tuple[str, ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "optics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="optics", apply_prob=0.5)


def _target_support_key(*, scene_variant: str, query_variant: str) -> str:
    """Return the active answer-support key for one scene/query pair."""

    if str(query_variant) == "target_hit_count":
        return "target_hit_count_support"
    return f"bounce_count_support_{str(scene_variant)}"


def _resolve_target_answer(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scene_variant: str,
    query_variant: str,
) -> Tuple[int, Dict[str, float]]:
    """Resolve one count answer with deterministic balancing."""

    support_key = _target_support_key(scene_variant=str(scene_variant), query_variant=str(query_variant))
    fallback = getattr(_DEFAULTS, support_key)
    target_params = dict(params)
    return resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=target_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=str(support_key),
        explicit_key="target_answer",
        fallback_support=fallback,
        namespace=f"{TASK_ID}.target_answer.{str(scene_variant)}.{str(query_variant)}",
        balanced_flag_key="balanced_target_answer_sampling",
        use_instance_seed_cycle=True,
        namespace_support_permutation=True,
    )


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    """Resolve scene/query/color axes and one target answer."""

    axis_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.axes")
    scene_variant, scene_probs, query_variant, query_probs = resolve_compatible_scene_query_variants(
        axis_rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_scene_variants=SUPPORTED_SCENE_VARIANTS,
        supported_query_variants=SUPPORTED_QUERY_VARIANTS,
        compatibility=COMPATIBILITY,
        scene_sampling_namespace=f"{TASK_ID}.scene_variant",
        query_sampling_namespace=f"{TASK_ID}.query_variant",
        decouple_scene_sampling=True,
    )
    target_answer, target_answer_probabilities = _resolve_target_answer(
        instance_seed=int(instance_seed),
        params=params,
        scene_variant=str(scene_variant),
        query_variant=str(query_variant),
    )
    color_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.accent_color_name")
    accent_color_name, accent_color_name_probabilities = resolve_variant(
        color_rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
    )
    accent_color_name = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(accent_color_name),
        variant_probabilities=accent_color_name_probabilities,
        supported_variants=SUPPORTED_PHYSICS_COLOR_NAMES,
        balance_flag_key="balanced_accent_color_name_sampling",
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        sampling_namespace=f"{TASK_ID}.accent_color_name",
    )
    return _ResolvedAxes(
        scene_variant=str(scene_variant),
        query_variant=str(query_variant),
        accent_color_name=str(accent_color_name),
        target_answer=int(target_answer),
        scene_variant_probabilities=dict(scene_probs),
        query_variant_probabilities=dict(query_probs),
        accent_color_name_probabilities=dict(accent_color_name_probabilities),
        target_answer_probabilities=dict(target_answer_probabilities),
    )


def _board_render_defaults(params: Mapping[str, Any], *, instance_seed: int | None = None) -> Dict[str, Any]:
    """Return resolved render defaults for the optics board."""

    keys = (
        "canvas_width",
        "canvas_height",
        "board_left_px",
        "board_top_px",
        "board_cols",
        "board_rows",
        "cell_size_px",
        "board_grid_width_px",
        "board_outline_width_px",
        "mirror_width_px",
        "mirror_padding_px",
        "ray_width_px",
        "ray_head_length_px",
        "ray_head_width_px",
        "target_radius_px",
        "source_radius_px",
        "bounce_radius_px",
        "target_font_size_px",
        "source_font_size_px",
        "label_stroke_width_px",
    )
    return {
        key: resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            key,
            int(getattr(_DEFAULTS, key)),
            instance_seed=instance_seed,
            namespace=TASK_ID,
        )
        for key in keys
    }


def _simulate_path(
    *,
    board_cols: int,
    board_rows: int,
    source_row: int,
    mirrors: Mapping[Tuple[int, int], str],
) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]], str]:
    """Return visited cells, hit mirror cells, and the exit direction."""

    col = 0
    row = int(source_row)
    direction = "E"
    visited: List[Tuple[int, int]] = []
    bounces: List[Tuple[int, int]] = []
    seen_states: set[Tuple[int, int, str]] = set()
    max_steps = int(board_cols) * int(board_rows) * 4
    for _ in range(max_steps):
        if not (0 <= int(col) < int(board_cols) and 0 <= int(row) < int(board_rows)):
            break
        state = (int(col), int(row), str(direction))
        if state in seen_states:
            raise ValueError("ray path looped unexpectedly")
        seen_states.add(state)
        visited.append((int(col), int(row)))
        orientation = mirrors.get((int(col), int(row)))
        if orientation is not None:
            bounces.append((int(col), int(row)))
            direction = _REFLECT_SLASH[str(direction)] if str(orientation) == "/" else _REFLECT_BACKSLASH[str(direction)]
        step_col, step_row = _DIRECTION_STEP[str(direction)]
        col = int(col + step_col)
        row = int(row + step_row)
    return visited, bounces, str(direction)


def _compute_path_points(
    *,
    render_defaults: Mapping[str, Any],
    source_row: int,
    path_cells: Sequence[Tuple[int, int]],
    exit_direction: str,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Return the outside source and exit points for the rendered ray."""

    board_left = float(render_defaults["board_left_px"])
    board_top = float(render_defaults["board_top_px"])
    cell_size = float(render_defaults["cell_size_px"])
    board_cols = int(render_defaults["board_cols"])
    board_rows = int(render_defaults["board_rows"])
    source_center_y = float(board_top + ((int(source_row) + 0.5) * cell_size))
    source_point = (float(board_left - (0.75 * cell_size)), float(source_center_y))
    if not path_cells:
        raise ValueError("ray path must include at least one board cell")
    last_col, last_row = path_cells[-1]
    last_center_x = float(board_left + ((int(last_col) + 0.5) * cell_size))
    last_center_y = float(board_top + ((int(last_row) + 0.5) * cell_size))
    if str(exit_direction) == "E":
        exit_point = (float(board_left + (board_cols * cell_size) + (0.55 * cell_size)), float(last_center_y))
    elif str(exit_direction) == "W":
        exit_point = (float(board_left - (0.55 * cell_size)), float(last_center_y))
    elif str(exit_direction) == "N":
        exit_point = (float(last_center_x), float(board_top - (0.55 * cell_size)))
    else:
        exit_point = (float(last_center_x), float(board_top + (board_rows * cell_size) + (0.55 * cell_size)))
    return source_point, exit_point


def _choose_two_distinct_rows(rng, *, board_rows: int) -> Tuple[int, int]:
    """Return two distinct interior rows."""

    rows = list(range(1, int(board_rows) - 1))
    rng.shuffle(rows)
    if len(rows) < 2:
        raise ValueError("optics scenes require at least two interior rows")
    return int(rows[0]), int(rows[1])


def _construct_hit_mirrors(
    rng,
    *,
    board_cols: int,
    board_rows: int,
    bounce_count: int,
) -> Tuple[int, List[Tuple[int, int, str]]]:
    """Construct one non-self-intersecting sequence of hit mirrors."""

    start_row = int(rng.randint(1, int(board_rows) - 2))
    if int(bounce_count) == 0:
        return int(start_row), []
    if int(bounce_count) == 1:
        col1 = int(rng.randint(2, int(board_cols) - 3))
        exit_vertical = "N" if int(start_row) > 1 and (int(start_row) >= int(board_rows) - 2 or rng.random() < 0.5) else "S"
        orientation1 = "/" if str(exit_vertical) == "N" else "\\"
        return int(start_row), [(col1, int(start_row), str(orientation1))]
    if int(bounce_count) == 2:
        col1 = int(rng.randint(2, int(board_cols) - 3))
        row0, row1 = _choose_two_distinct_rows(rng, board_rows=int(board_rows))
        start_row = int(row0)
        vertical_dir = "N" if int(row1) < int(row0) else "S"
        orientation1 = "/" if str(vertical_dir) == "N" else "\\"
        orientation2 = "/" if str(vertical_dir) == "N" else "\\"
        return int(start_row), [(col1, int(row0), str(orientation1)), (col1, int(row1), str(orientation2))]
    row0, row1 = _choose_two_distinct_rows(rng, board_rows=int(board_rows))
    start_row = int(row0)
    if int(bounce_count) == 3:
        col1 = int(rng.randint(2, int(board_cols) - 5))
        col2 = int(rng.randint(int(col1) + 2, int(board_cols) - 3))
        first_vertical = "N" if int(row1) < int(row0) else "S"
        second_vertical = "N" if int(row1) > 1 and (int(row1) >= int(board_rows) - 2 or rng.random() < 0.5) else "S"
        orientation1 = "/" if str(first_vertical) == "N" else "\\"
        orientation2 = "/" if str(first_vertical) == "N" else "\\"
        orientation3 = "/" if str(second_vertical) == "N" else "\\"
        return int(start_row), [
            (col1, int(row0), str(orientation1)),
            (col1, int(row1), str(orientation2)),
            (col2, int(row1), str(orientation3)),
        ]
    rows = list(range(1, int(board_rows) - 1))
    rows.remove(int(row0))
    rows.remove(int(row1))
    rng.shuffle(rows)
    if not rows:
        raise ValueError("multi-bounce optics path needs a third interior row")
    row2 = int(rows[0])
    if int(bounce_count) == 4:
        col1 = int(rng.randint(2, int(board_cols) - 5))
        col2 = int(rng.randint(int(col1) + 2, int(board_cols) - 3))
    else:
        if int(board_cols) < 8:
            raise ValueError("five-bounce optics path needs at least eight columns")
        col1 = int(rng.randint(1, max(1, int(board_cols) - 6)))
        col2 = int(col1 + 2)
        col3 = int(col2 + 2)
    first_vertical = "N" if int(row1) < int(row0) else "S"
    second_vertical = "N" if int(row2) < int(row1) else "S"
    orientation1 = "/" if str(first_vertical) == "N" else "\\"
    orientation2 = "/" if str(first_vertical) == "N" else "\\"
    orientation3 = "/" if str(second_vertical) == "N" else "\\"
    orientation4 = "/" if str(second_vertical) == "N" else "\\"
    mirrors = [
        (col1, int(row0), str(orientation1)),
        (col1, int(row1), str(orientation2)),
        (col2, int(row1), str(orientation3)),
        (col2, int(row2), str(orientation4)),
    ]
    if int(bounce_count) == 4:
        return int(start_row), mirrors
    exit_vertical = "N" if int(row2) >= int(board_rows // 2) else "S"
    orientation5 = "/" if str(exit_vertical) == "N" else "\\"
    mirrors.append((int(col3), int(row2), str(orientation5)))
    return int(start_row), mirrors


def _place_unused_mirrors(
    rng,
    *,
    total_mirror_count: int,
    hit_mirrors: Sequence[Tuple[int, int, str]],
    path_cells: Sequence[Tuple[int, int]],
    board_cols: int,
    board_rows: int,
) -> List[Tuple[int, int, str]]:
    """Add off-path mirrors so the visual scene matches the declared scene variant."""

    occupied = {(int(col), int(row)) for col, row in path_cells}
    used = {(int(col), int(row)) for col, row, _ in hit_mirrors}
    available: List[Tuple[int, int]] = [
        (col, row)
        for row in range(1, int(board_rows) - 1)
        for col in range(1, int(board_cols) - 1)
        if (int(col), int(row)) not in occupied and (int(col), int(row)) not in used
    ]
    rng.shuffle(available)
    mirrors = list(hit_mirrors)
    while len(mirrors) < int(total_mirror_count) and available:
        col, row = available.pop()
        orientation = "/" if rng.random() < 0.5 else "\\"
        mirrors.append((int(col), int(row), str(orientation)))
    if len(mirrors) != int(total_mirror_count):
        raise ValueError("failed to place all non-hit mirrors off the ray path")
    return mirrors


def _choose_targets(
    rng,
    *,
    target_answer: int,
    query_variant: str,
    board_cols: int,
    board_rows: int,
    path_cells: Sequence[Tuple[int, int]],
    mirror_cells: Sequence[Tuple[int, int]],
    target_count_min: int,
    target_count_max: int,
) -> List[_TargetPlacement]:
    """Place hit and distractor targets after the path has been fixed."""

    mirror_set = {(int(col), int(row)) for col, row in mirror_cells}
    path_target_cells = [cell for cell in path_cells if tuple(cell) not in mirror_set]
    if int(target_answer) > len(path_target_cells):
        raise ValueError("not enough non-mirror path cells to place requested hit targets")
    hit_cells: List[Tuple[int, int]] = []
    if int(target_answer) > 0:
        hit_cells = list(path_target_cells)
        rng.shuffle(hit_cells)
        hit_cells = hit_cells[: int(target_answer)]
    occupied = set(path_cells) | mirror_set | set(hit_cells)
    target_total = int(rng.randint(int(target_count_min), int(target_count_max)))
    target_total = max(int(target_total), int(target_answer))
    target_cells = list(hit_cells)
    all_distractor_slots: List[Tuple[int, int]] = [
        (col, row)
        for row in range(int(board_rows))
        for col in range(int(board_cols))
        if (int(col), int(row)) not in occupied
    ]
    path_set = {(int(col), int(row)) for col, row in path_cells}
    preferred_distractor_slots = [
        (col, row)
        for col, row in all_distractor_slots
        if all(abs(int(col) - int(path_col)) + abs(int(row) - int(path_row)) >= 2 for path_col, path_row in path_set)
    ]
    distractor_slots = (
        list(preferred_distractor_slots)
        if len(preferred_distractor_slots) >= max(0, int(target_total) - len(target_cells))
        else list(all_distractor_slots)
    )
    rng.shuffle(distractor_slots)
    while len(target_cells) < int(target_total) and distractor_slots:
        target_cells.append(tuple(distractor_slots.pop()))
    if len(target_cells) < int(target_total):
        raise ValueError("failed to place the requested number of optics targets")
    targets: List[_TargetPlacement] = []
    for label_index, (col, row) in enumerate(target_cells, start=1):
        hit = (int(col), int(row)) in {tuple(cell) for cell in hit_cells}
        targets.append(
            _TargetPlacement(
                target_id=f"target_{int(label_index)}",
                col=int(col),
                row=int(row),
                label=int(label_index),
                hit=bool(hit),
            )
        )
    return targets


def _sample_scene_layout(
    rng,
    *,
    scene_variant: str,
    query_variant: str,
    target_answer: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
) -> _SceneLayout:
    """Construct one ray-trace board matching the requested answer."""

    board_cols = int(render_defaults["board_cols"])
    board_rows = int(render_defaults["board_rows"])
    total_mirror_count = int(_SCENE_MIRROR_COUNT[str(scene_variant)])
    target_count_min = int(params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min)))
    target_count_max = int(params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max)))

    if str(query_variant) == "bounce_count":
        bounce_count = int(target_answer)
    else:
        bounce_support = resolve_integer_support(
            params,
            gen_defaults=_GEN_DEFAULTS,
            key=f"bounce_count_support_{str(scene_variant)}",
            fallback=getattr(_DEFAULTS, f"bounce_count_support_{str(scene_variant)}"),
        )
        feasible_bounces = [int(value) for value in bounce_support if 0 <= int(value) <= int(total_mirror_count)]
        rng.shuffle(feasible_bounces)
        bounce_count = int(feasible_bounces[0] if feasible_bounces else 0)

    source_row, hit_mirrors = _construct_hit_mirrors(
        rng,
        board_cols=int(board_cols),
        board_rows=int(board_rows),
        bounce_count=int(bounce_count),
    )
    mirror_map = {(int(col), int(row)): str(orientation) for col, row, orientation in hit_mirrors}
    path_cells, hit_bounce_cells, exit_direction = _simulate_path(
        board_cols=int(board_cols),
        board_rows=int(board_rows),
        source_row=int(source_row),
        mirrors=mirror_map,
    )
    if int(len(hit_bounce_cells)) != int(bounce_count):
        raise ValueError("constructed optics path did not realize the requested bounce count")

    mirrors = _place_unused_mirrors(
        rng,
        total_mirror_count=int(total_mirror_count),
        hit_mirrors=hit_mirrors,
        path_cells=path_cells,
        board_cols=int(board_cols),
        board_rows=int(board_rows),
    )
    mirror_cells = [(int(col), int(row)) for col, row, _ in mirrors]
    if str(query_variant) == "target_hit_count":
        targets = _choose_targets(
            rng,
            target_answer=int(target_answer),
            query_variant=str(query_variant),
            board_cols=int(board_cols),
            board_rows=int(board_rows),
            path_cells=path_cells,
            mirror_cells=mirror_cells,
            target_count_min=int(target_count_min),
            target_count_max=int(target_count_max),
        )
    else:
        targets = []

    actual_hit_target_count = sum(1 for target in targets if bool(target.hit))
    if str(query_variant) == "target_hit_count" and int(actual_hit_target_count) != int(target_answer):
        raise ValueError("constructed optics targets did not realize the requested hit count")

    source_point_px, exit_point_px = _compute_path_points(
        render_defaults=render_defaults,
        source_row=int(source_row),
        path_cells=path_cells,
        exit_direction=str(exit_direction),
    )
    if str(query_variant) == "bounce_count":
        evidence_entity_ids = tuple(f"bounce_{int(index)}" for index in range(1, len(hit_bounce_cells) + 1))
    else:
        evidence_entity_ids = tuple(str(target.target_id) for target in targets if bool(target.hit))
    mirror_specs = tuple(
        _MirrorPlacement(
            mirror_id=f"mirror_{int(index)}",
            col=int(col),
            row=int(row),
            orientation=str(orientation),
            hit=(int(col), int(row)) in set(hit_bounce_cells),
        )
        for index, (col, row, orientation) in enumerate(mirrors, start=1)
    )
    return _SceneLayout(
        scene_variant=str(scene_variant),
        query_variant=str(query_variant),
        target_answer=int(target_answer),
        source_row=int(source_row),
        mirrors=mirror_specs,
        targets=tuple(targets),
        path_cells=tuple((int(col), int(row)) for col, row in path_cells),
        bounce_cells=tuple((int(col), int(row)) for col, row in hit_bounce_cells),
        source_point_px=tuple(float(value) for value in source_point_px),
        exit_point_px=tuple(float(value) for value in exit_point_px),
        evidence_entity_ids=tuple(str(item) for item in evidence_entity_ids),
    )


def _build_prompt_examples(query_variant: str) -> Tuple[str, str]:
    """Return prompt JSON examples for the active optics query."""

    if str(query_variant) == "bounce_count":
        evidence = [[242, 190], [346, 294]]
    else:
        evidence = [[190, 138], [398, 346]]
    return build_prompt_json_examples(evidence_value=evidence, answer_type="integer")


def _pixel_point_set_evidence_artifacts(
    *,
    points_by_label: Mapping[str, Sequence[float]],
    graph_origin: Sequence[float],
    graph_spacing: int,
    witness_type: str,
    ordered_labels: Sequence[str],
) -> Dict[str, Any]:
    """Expose optics graph-derived witnesses as public pixel point sets."""

    labels = [str(label) for label in ordered_labels]
    if not labels:
        return _empty_pixel_point_set_evidence_artifacts(witness_type=str(witness_type))
    labeled = labeled_grid_point_evidence_artifacts(
        points_by_label=points_by_label,
        graph_origin=graph_origin,
        graph_spacing=int(graph_spacing),
        witness_type=str(witness_type),
        ordered_labels=tuple(labels),
    )
    projected = dict(labeled["projected_evidence"])
    pixel_map = {
        str(label): [float(point[0]), float(point[1])]
        for label, point in dict(projected.get("pixel_point_map", {})).items()
    }
    point_set = [list(pixel_map[str(label)]) for label in labels]
    witness_symbolic = dict(labeled["witness_symbolic"])
    return {
        "evidence_type": "point_set",
        "evidence_value": [list(point) for point in point_set],
        "required_labels": list(labels),
        "witness_symbolic": witness_symbolic,
        "projected_evidence": {
            "type": "point_set",
            "point_set": [list(point) for point in point_set],
            "pixel_point_set": [list(point) for point in point_set],
            "pixel_point_map": dict(pixel_map),
        },
    }


def _empty_pixel_point_set_evidence_artifacts(*, witness_type: str) -> Dict[str, Any]:
    """Return an empty pixel point-set evidence payload."""

    return {
        "evidence_type": "point_set",
        "evidence_value": [],
        "required_labels": [],
        "witness_symbolic": {
            "type": str(witness_type),
            "count": 0,
        },
        "projected_evidence": {
            "type": "point_set",
            "point_set": [],
            "pixel_point_set": [],
            "pixel_point_map": {},
        },
    }


class _PhysicsOpticsRayTraceBaseTask:
    """Return one simple diagram-first optics ray-tracing question."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "optics"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(int(instance_seed), params=params)
        render_defaults = _board_render_defaults(params, instance_seed=int(instance_seed))
        rendered_scene: RenderedOpticsScene | None = None
        scene_layout: _SceneLayout | None = None

        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                scene_layout = _sample_scene_layout(
                    attempt_rng,
                    scene_variant=str(axes.scene_variant),
                    query_variant=str(axes.query_variant),
                    target_answer=int(axes.target_answer),
                    params=params,
                    render_defaults=render_defaults,
                )
            except ValueError:
                continue

            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                scene_id="ray_optics",
                task_group=self.task_group,
                canvas_width=int(render_defaults["canvas_width"]),
                canvas_height=int(render_defaults["canvas_height"]),
                instance_seed=int(instance_seed),
                params=params,
            )
            rendered_scene = render_optics_ray_scene(
                background=background,
                render_defaults=render_defaults,
                accent_color_name=str(axes.accent_color_name),
                scene_variant=str(scene_layout.scene_variant),
                source_row=int(scene_layout.source_row),
                mirrors=[
                    {
                        "col": int(mirror.col),
                        "row": int(mirror.row),
                        "orientation": str(mirror.orientation),
                        "hit": bool(mirror.hit),
                    }
                    for mirror in scene_layout.mirrors
                ],
                targets=[
                    {
                        "target_id": str(target.target_id),
                        "col": int(target.col),
                        "row": int(target.row),
                        "label": int(target.label),
                        "hit": bool(target.hit),
                    }
                    for target in scene_layout.targets
                ],
                bounce_cells=list(scene_layout.bounce_cells),
                ray_polyline_cells=list(scene_layout.path_cells),
                source_point_px=tuple(scene_layout.source_point_px),
                exit_point_px=tuple(scene_layout.exit_point_px),
                evidence_entity_ids=list(scene_layout.evidence_entity_ids),
                query_variant=str(axes.query_variant),
                diagram_style=diagram_style,
            )
            image, post_noise_meta = apply_post_image_noise(
                rendered_scene.image,
                instance_seed=int(instance_seed),
                params=params,
                default_config=POST_IMAGE_NOISE_DEFAULTS,
            )

            prompt_defaults = required_group_defaults(
                _PROMPT_DEFAULTS,
                (
                    "bundle_id",
                    "scene_key",
                    "task_key",
                    "json_output_contract",
                    "json_output_contract_answer_only",
                    "answer_hint",
                    "evidence_hint_bounce_count",
                    "evidence_hint_target_hit_count",
                    "object_description_single_mirror",
                    "object_description_double_mirror",
                    "object_description_triple_mirror",
                    "object_description_quad_mirror",
                    "object_description_five_mirror",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            json_example, json_example_answer_only = _build_prompt_examples(str(axes.query_variant))
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(axes.query_variant),
                answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
                slots={
                    "object_description": str(prompt_defaults[f"object_description_{str(axes.scene_variant)}"]),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_variant)}"]),
                    "answer_hint": str(prompt_defaults["answer_hint"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=int(instance_seed),
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

            answer_gt = TypedValue(type="integer", value=int(axes.target_answer))
            if str(axes.query_variant) == "bounce_count":
                evidence_points_by_label = {
                    str(spec.bounce_id): list(spec.point_px)
                    for spec in rendered_scene.bounce_specs
                    if str(spec.bounce_id) in set(rendered_scene.evidence_entity_ids)
                }
                witness_type = "physics_optics_bounce_points"
            else:
                evidence_points_by_label = {
                    str(spec.target_id): list(spec.point_px)
                    for spec in rendered_scene.target_specs
                    if str(spec.target_id) in set(rendered_scene.evidence_entity_ids)
                }
                witness_type = "physics_optics_hit_target_points"
            evidence_artifacts = _pixel_point_set_evidence_artifacts(
                points_by_label=evidence_points_by_label,
                graph_origin=rendered_scene.graph_origin_px,
                graph_spacing=int(rendered_scene.graph_spacing_px),
                witness_type=str(witness_type),
                ordered_labels=tuple(str(item) for item in rendered_scene.evidence_entity_ids),
            )
            evidence_gt = TypedValue(
                type=str(evidence_artifacts["evidence_type"]),
                value=list(evidence_artifacts["evidence_value"]),
            )
            complexity = build_physics_optics_ray_trace_complexity(
                task_group_defaults=_TASK_GROUP_DEFAULTS,
                task_id=TASK_ID,
                scene_variant=str(axes.scene_variant),
                query_variant=str(axes.query_variant),
                mirror_count=len(scene_layout.mirrors),
                target_count=len(scene_layout.targets),
                target_answer=int(axes.target_answer),
            )
            support_key = _target_support_key(scene_variant=str(axes.scene_variant), query_variant=str(axes.query_variant))
            trace_payload = {
                "scene_ir": {
                    "scene_kind": f"physics_optics_ray_trace_{str(axes.scene_variant)}",
                    "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                    "relations": {
                        "scene_variant": str(axes.scene_variant),
                        "query_variant": str(axes.query_variant),
                        "query_variant": str(axes.query_variant),
                        "target_answer": int(axes.target_answer),
                        "accent_color_name": str(axes.accent_color_name),
                        "evidence_entity_ids": list(rendered_scene.evidence_entity_ids),
                    },
                },
                "query_spec": {
                    "query_variant": str(axes.query_variant),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "scene_variant": str(axes.scene_variant),
                        "query_variant": str(axes.query_variant),
                        "query_variant": str(axes.query_variant),
                        "accent_color_name": str(axes.accent_color_name),
                        "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                        "query_variant_probabilities": dict(axes.query_variant_probabilities),
                        "query_variant_probabilities": dict(axes.query_variant_probabilities),
                        "accent_color_name_probabilities": dict(axes.accent_color_name_probabilities),
                        "target_answer": int(axes.target_answer),
                        "target_answer_probabilities": dict(axes.target_answer_probabilities),
                    },
                },
                "render_spec": {
                    "scene_variant": str(axes.scene_variant),
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "accent_color_name": str(axes.accent_color_name),
                    "technical_diagram_style": dict(diagram_style_meta),
                    "background_style": background_meta,
                    "post_image_noise": post_noise_meta,
                },
                "render_map": dict(rendered_scene.render_map),
                "execution_trace": {
                    "scene_variant": str(axes.scene_variant),
                    "query_variant": str(axes.query_variant),
                    "query_variant": str(axes.query_variant),
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": int(axes.target_answer),
                    "target_answer_support": list(
                        resolve_integer_support(
                            params,
                            gen_defaults=_GEN_DEFAULTS,
                            key=str(support_key),
                            fallback=getattr(_DEFAULTS, str(support_key)),
                        )
                    ),
                    "source_row": int(scene_layout.source_row),
                    "mirror_specs": [
                        {
                            "mirror_id": str(mirror.mirror_id),
                            "col": int(mirror.col),
                            "row": int(mirror.row),
                            "orientation": str(mirror.orientation),
                            "hit": bool(mirror.hit),
                        }
                        for mirror in scene_layout.mirrors
                    ],
                    "target_specs": [
                        {
                            "target_id": str(target.target_id),
                            "col": int(target.col),
                            "row": int(target.row),
                            "hit": bool(target.hit),
                        }
                        for target in scene_layout.targets
                    ],
                    "path_cells": [[int(col), int(row)] for col, row in scene_layout.path_cells],
                    "bounce_cells": [[int(col), int(row)] for col, row in scene_layout.bounce_cells],
                    "evidence_pixel_points": [list(point) for point in evidence_gt.value],
                    "evidence_entity_ids": list(rendered_scene.evidence_entity_ids),
                },
                "witness_symbolic": dict(evidence_artifacts["witness_symbolic"]),
                "projected_evidence": dict(evidence_artifacts["projected_evidence"]),
                "background": background_meta,
                "post_image_noise": post_noise_meta,
            }
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=answer_gt,
                evidence_gt=evidence_gt,
                image=image,
                image_id="img0",
                trace_payload=trace_payload,
                complexity=complexity,
                task_versions=default_task_versions(),
                query_variant=str(axes.query_variant),
                scene_id="ray_optics",
            )

        raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")


@register_task
class PhysicsOpticsRayBounceCountTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsOpticsRayTraceBaseTask,
):
    """Return the number of mirror-bounce points on the ray path."""

    task_id = "task_physics__ray_optics__ray_bounce_count"
    fixed_query_variant = "bounce_count"


@register_task
class PhysicsOpticsRayTargetHitCountTask(
    FixedPhysicsQueryVariantTaskMixin,
    _PhysicsOpticsRayTraceBaseTask,
):
    """Return the number of target points touched by the ray path."""

    task_id = "task_physics__ray_optics__ray_target_hit_count"
    fixed_query_variant = "target_hit_count"


__all__ = [
    "PhysicsOpticsRayBounceCountTask",
    "PhysicsOpticsRayTargetHitCountTask",
]
