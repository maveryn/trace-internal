"""Direct rectangular-solid measurement tasks."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.prompt_json_example import dump_prompt_json_examples
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font
from ..shared.complexity import build_geometry_measurement_complexity, normalize_linear
from ..shared.diagram_style import prepare_geometry_diagram_style_and_background
from ..shared.fixed_query_task import (
    geometry_selected_probability_map as _probability_map,
    select_indexed_geometry_query_id,
)
from ..shared.measurement_rendering import (
    bbox_from_points,
    bbox_to_list,
    draw_label_backplate,
    pad_bbox,
    readout_text_metadata,
)
from ..shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS
from ..shared.vector2d import (
    add as _add,
    mul as _mul,
    perp as _perp,
    point_to_list as _point_to_list,
    sub as _sub,
    unit as _unit,
)

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

SCENE_ID = "rectangular_solid"
TASK_GROUP = "measurement"
TASK_ID_MISSING_DIMENSION = "task_geometry__rectangular_solid__cuboid_volume_missing_dimension_value"
TASK_ID_SURFACE_AREA = "task_geometry__rectangular_solid__cuboid_surface_area_value"
TASK_ID_FRAME_EDGE = "task_geometry__rectangular_solid__cube_edge_from_frame_length_value"
TASK_ID_OPEN_BOX_NET = "task_geometry__rectangular_solid__open_box_net_dimension_value"
TASK_ID = TASK_ID_MISSING_DIMENSION
PROMPT_BUNDLE_ID = "geometry_rectangular_solid_v0"

QUERY_ID_MISSING_LENGTH = "missing_length_from_volume"
QUERY_ID_MISSING_WIDTH = "missing_width_from_volume"
QUERY_ID_MISSING_HEIGHT = "missing_height_from_volume"
QUERY_ID_SURFACE_AREA = "surface_area_from_dimensions"
QUERY_ID_CUBE_EDGE_TOTAL_FRAME = "cube_edge_from_total_frame"
QUERY_ID_CUBE_EDGE_PARTIAL_FRAME = "cube_edge_from_partial_frame"
QUERY_ID_OPEN_BOX_DIMENSION = "open_box_dimension_from_corner_cut"
QUERY_ID_OPEN_BOX_VOLUME = "open_box_volume_from_net"
MISSING_DIMENSION_QUERY_IDS: Tuple[str, ...] = (
    QUERY_ID_MISSING_LENGTH,
    QUERY_ID_MISSING_WIDTH,
    QUERY_ID_MISSING_HEIGHT,
)
SURFACE_AREA_QUERY_IDS: Tuple[str, ...] = (QUERY_ID_SURFACE_AREA,)
FRAME_EDGE_QUERY_IDS: Tuple[str, ...] = (
    QUERY_ID_CUBE_EDGE_TOTAL_FRAME,
    QUERY_ID_CUBE_EDGE_PARTIAL_FRAME,
)
OPEN_BOX_NET_QUERY_IDS: Tuple[str, ...] = (
    QUERY_ID_OPEN_BOX_DIMENSION,
    QUERY_ID_OPEN_BOX_VOLUME,
)
QUERY_IDS: Tuple[str, ...] = MISSING_DIMENSION_QUERY_IDS
_ROLE_BY_QUERY_ID: Dict[str, str] = {
    QUERY_ID_MISSING_LENGTH: "length",
    QUERY_ID_MISSING_WIDTH: "width",
    QUERY_ID_MISSING_HEIGHT: "height",
    QUERY_ID_SURFACE_AREA: "surface_area",
    QUERY_ID_CUBE_EDGE_TOTAL_FRAME: "cube_edge",
    QUERY_ID_CUBE_EDGE_PARTIAL_FRAME: "cube_edge",
    QUERY_ID_OPEN_BOX_DIMENSION: "base_dimension",
    QUERY_ID_OPEN_BOX_VOLUME: "open_box_volume",
}
ANNOTATION_KEYS: Tuple[str, ...] = (
    "length_segment_start",
    "length_segment_end",
    "width_segment_start",
    "width_segment_end",
    "height_segment_start",
    "height_segment_end",
)
FRAME_ANNOTATION_KEYS: Tuple[str, ...] = (
    "frame_bbox",
    "given_length_region_bbox",
    "target_edge_bbox",
)
NET_ANNOTATION_KEYS: Tuple[str, ...] = (
    "sheet_bbox",
    "cutout_bbox",
    "base_panel_bbox",
    "target_region_bbox",
)

_TASK_GROUP_DEFAULTS = get_task_group_defaults("geometry", TASK_GROUP)
_CUBOID_CASES: Tuple[Tuple[int, int, int], ...] = (
    (3, 4, 5),
    (4, 5, 6),
    (3, 6, 7),
    (5, 6, 8),
    (4, 7, 9),
    (6, 8, 9),
    (5, 9, 10),
    (7, 8, 11),
    (6, 10, 12),
    (8, 9, 12),
)
_CUBE_EDGE_VALUES: Tuple[int, ...] = tuple(range(2, 13))
_PARTIAL_FRAME_EDGE_COUNTS: Tuple[int, ...] = (4, 5, 6, 7, 8)
_OPEN_BOX_CASES: Tuple[Tuple[int, int, int], ...] = (
    (10, 8, 2),
    (12, 9, 2),
    (13, 10, 2),
    (14, 10, 3),
    (15, 11, 3),
    (16, 12, 2),
    (17, 13, 3),
    (18, 12, 3),
    (18, 15, 4),
    (20, 14, 4),
)
_OPEN_BOX_DIMENSION_ROLES: Tuple[str, ...] = ("base_length", "base_width")


@dataclass(frozen=True)
class _TaskContract:
    task_id: str
    query_ids: Tuple[str, ...]
    formula_family: str
    formula: str
    answer_kind: str


_CONTRACTS_BY_TASK_ID: Dict[str, _TaskContract] = {
    TASK_ID_MISSING_DIMENSION: _TaskContract(
        task_id=TASK_ID_MISSING_DIMENSION,
        query_ids=MISSING_DIMENSION_QUERY_IDS,
        formula_family="cuboid_volume_missing_dimension",
        formula="missing_dimension = volume / (known_dimension_1 * known_dimension_2)",
        answer_kind="dimension",
    ),
    TASK_ID_SURFACE_AREA: _TaskContract(
        task_id=TASK_ID_SURFACE_AREA,
        query_ids=SURFACE_AREA_QUERY_IDS,
        formula_family="cuboid_surface_area",
        formula="surface_area = 2 * (length*width + length*height + width*height)",
        answer_kind="surface_area",
    ),
    TASK_ID_FRAME_EDGE: _TaskContract(
        task_id=TASK_ID_FRAME_EDGE,
        query_ids=FRAME_EDGE_QUERY_IDS,
        formula_family="cube_edge_from_frame_length",
        formula="cube_edge = frame_length / visible_frame_edge_count",
        answer_kind="cube_edge",
    ),
    TASK_ID_OPEN_BOX_NET: _TaskContract(
        task_id=TASK_ID_OPEN_BOX_NET,
        query_ids=OPEN_BOX_NET_QUERY_IDS,
        formula_family="open_box_net_corner_cut",
        formula="base_length = sheet_length - 2*cut_size; base_width = sheet_width - 2*cut_size; volume = base_length*base_width*cut_size",
        answer_kind="open_box",
    ),
}


@dataclass(frozen=True)
class _ResolvedProblem:
    task_id: str
    query_id: str
    target_role: str
    length: int
    width: int
    height: int
    volume: int
    surface_area: int
    cube_edge: int
    visible_frame_edge_count: int
    frame_length: int
    sheet_length: int
    sheet_width: int
    cut_size: int
    base_length: int
    base_width: int
    open_box_volume: int
    answer: int
    formula_family: str
    formula: str
    query_probabilities: Dict[str, float]
    case_probabilities: Dict[str, float]
    answer_support_probabilities: Dict[str, float]


@dataclass
class _RenderContext:
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    label_color: Color
    label_stroke_color: Color
    label_backing_color: Color
    face_front: Color
    face_side: Color
    face_top: Color
    accent_color: Color
    muted_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_type: str
    annotation_keyed_points: Dict[str, Point]
    annotation_keyed_bboxes: Dict[str, BBox]
    annotation_roles: Tuple[str, ...]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def _case_key(case: Sequence[int]) -> str:
    length, width, height = [int(value) for value in case]
    return f"L{length}_W{width}_H{height}"


def _surface_area_for_case(case: Sequence[int]) -> int:
    length, width, height = [int(value) for value in case]
    return int(2 * ((length * width) + (length * height) + (width * height)))


def _open_box_values_for_case(case: Sequence[int]) -> tuple[int, int, int, int, int, int]:
    sheet_length, sheet_width, cut_size = [int(value) for value in case]
    base_length = int(sheet_length - 2 * cut_size)
    base_width = int(sheet_width - 2 * cut_size)
    volume = int(base_length * base_width * cut_size)
    return sheet_length, sheet_width, cut_size, base_length, base_width, volume


def _answer_support_probabilities(*, selected: int, target_role: str, answer_kind: str) -> Dict[str, float]:
    if answer_kind == "open_box":
        if str(target_role) == "open_box_volume":
            support = tuple(sorted({_open_box_values_for_case(case)[5] for case in _OPEN_BOX_CASES}))
        elif str(target_role) == "base_length":
            support = tuple(sorted({_open_box_values_for_case(case)[3] for case in _OPEN_BOX_CASES}))
        elif str(target_role) == "base_width":
            support = tuple(sorted({_open_box_values_for_case(case)[4] for case in _OPEN_BOX_CASES}))
        else:
            support = tuple(sorted({value for case in _OPEN_BOX_CASES for value in _open_box_values_for_case(case)[3:5]}))
    elif answer_kind == "cube_edge":
        support = _CUBE_EDGE_VALUES
    elif answer_kind == "surface_area":
        support = tuple(sorted({_surface_area_for_case(case) for case in _CUBOID_CASES}))
    else:
        role_index = {"length": 0, "width": 1, "height": 2}[str(target_role)]
        support = tuple(sorted({int(case[role_index]) for case in _CUBOID_CASES}))
    return _probability_map(support, selected=int(selected))


def _select_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    task_id: str,
) -> tuple[Tuple[int, int, int], Dict[str, float]]:
    explicit_dimensions = params.get("dimensions")
    explicit_dimension_fields = any(key in params for key in ("length_units", "width_units", "height_units"))
    if explicit_dimensions is not None or explicit_dimension_fields:
        if explicit_dimensions is not None:
            if not isinstance(explicit_dimensions, Sequence) or isinstance(explicit_dimensions, (str, bytes)) or len(explicit_dimensions) != 3:
                raise ValueError("dimensions must be [length, width, height]")
            length, width, height = [int(value) for value in explicit_dimensions]
        else:
            missing = [key for key in ("length_units", "width_units", "height_units") if key not in params]
            if missing:
                raise ValueError(f"explicit cuboid dimensions require all three fields; missing {missing}")
            length = int(params["length_units"])
            width = int(params["width_units"])
            height = int(params["height_units"])
        case = (length, width, height)
        _validate_dimensions(case)
        return case, {_case_key(case): 1.0}

    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.cuboid_case",
    )
    case = _CUBOID_CASES[int(index) % len(_CUBOID_CASES)]
    probability = 1.0 / float(len(_CUBOID_CASES))
    return case, {_case_key(candidate): probability for candidate in _CUBOID_CASES}


def _select_cube_edge(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    task_id: str,
) -> tuple[int, Dict[str, float]]:
    explicit_edge = params.get("edge_units")
    if explicit_edge is not None:
        edge = int(explicit_edge)
        _validate_cube_edge(edge)
        return edge, {str(edge): 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.cube_edge",
    )
    edge = int(_CUBE_EDGE_VALUES[int(index) % len(_CUBE_EDGE_VALUES)])
    probability = 1.0 / float(len(_CUBE_EDGE_VALUES))
    return edge, {str(candidate): probability for candidate in _CUBE_EDGE_VALUES}


def _select_partial_frame_edge_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    task_id: str,
) -> tuple[int, Dict[str, float]]:
    explicit_count = params.get("highlighted_edge_count")
    if explicit_count is not None:
        count = int(explicit_count)
        if count not in _PARTIAL_FRAME_EDGE_COUNTS:
            raise ValueError("highlighted_edge_count must be one of 4, 5, 6, 7, or 8")
        return count, {str(count): 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.partial_frame_edge_count",
    )
    count = int(_PARTIAL_FRAME_EDGE_COUNTS[int(index) % len(_PARTIAL_FRAME_EDGE_COUNTS)])
    probability = 1.0 / float(len(_PARTIAL_FRAME_EDGE_COUNTS))
    return count, {str(candidate): probability for candidate in _PARTIAL_FRAME_EDGE_COUNTS}


def _open_box_case_key(case: Sequence[int]) -> str:
    sheet_length, sheet_width, cut_size = [int(value) for value in case]
    return f"sheet{sheet_length}x{sheet_width}_cut{cut_size}"


def _select_open_box_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    task_id: str,
) -> tuple[Tuple[int, int, int], Dict[str, float]]:
    explicit_case = params.get("open_box_case")
    explicit_fields = any(key in params for key in ("sheet_length_units", "sheet_width_units", "cut_size_units"))
    if explicit_case is not None or explicit_fields:
        if explicit_case is not None:
            if not isinstance(explicit_case, Sequence) or isinstance(explicit_case, (str, bytes)) or len(explicit_case) != 3:
                raise ValueError("open_box_case must be [sheet_length, sheet_width, cut_size]")
            case = tuple(int(value) for value in explicit_case)
        else:
            missing = [key for key in ("sheet_length_units", "sheet_width_units", "cut_size_units") if key not in params]
            if missing:
                raise ValueError(f"explicit open-box dimensions require all three fields; missing {missing}")
            case = (int(params["sheet_length_units"]), int(params["sheet_width_units"]), int(params["cut_size_units"]))
        _validate_open_box_case(case)
        return case, {_open_box_case_key(case): 1.0}
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.open_box_case",
    )
    case = _OPEN_BOX_CASES[int(index) % len(_OPEN_BOX_CASES)]
    probability = 1.0 / float(len(_OPEN_BOX_CASES))
    return case, {_open_box_case_key(candidate): probability for candidate in _OPEN_BOX_CASES}


def _select_open_box_dimension_role(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    task_id: str,
) -> tuple[str, Dict[str, float]]:
    explicit_role = params.get("target_dimension_role")
    if explicit_role is not None:
        role = str(explicit_role)
        if role not in _OPEN_BOX_DIMENSION_ROLES:
            raise ValueError("target_dimension_role must be base_length or base_width")
        return role, _probability_map(_OPEN_BOX_DIMENSION_ROLES, selected=role)
    index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.target_dimension_role",
    )
    role = _OPEN_BOX_DIMENSION_ROLES[int(index) % len(_OPEN_BOX_DIMENSION_ROLES)]
    return str(role), _probability_map(_OPEN_BOX_DIMENSION_ROLES)


def _validate_dimensions(case: Sequence[int]) -> None:
    length, width, height = [int(value) for value in case]
    if min(length, width, height) <= 0:
        raise ValueError("cuboid dimensions must be positive integers")
    if max(length, width, height) > 60:
        raise ValueError("cuboid dimensions are too large for this renderer")


def _validate_cube_edge(edge: int) -> None:
    if int(edge) not in _CUBE_EDGE_VALUES:
        raise ValueError("edge_units must be an integer from 2 to 12")


def _validate_open_box_case(case: Sequence[int]) -> None:
    sheet_length, sheet_width, cut_size, base_length, base_width, _volume = _open_box_values_for_case(case)
    if min(sheet_length, sheet_width, cut_size) <= 0:
        raise ValueError("open-box sheet dimensions and cut size must be positive integers")
    if base_length < 3 or base_width < 3:
        raise ValueError("open-box resulting base dimensions must each be at least 3")
    if max(sheet_length, sheet_width) > 40:
        raise ValueError("open-box sheet dimensions are too large for this renderer")


def _resolve_frame_problem(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    contract: _TaskContract,
    query_id: str,
    query_probabilities: Dict[str, float],
) -> _ResolvedProblem:
    edge, edge_probabilities = _select_cube_edge(
        instance_seed=int(instance_seed),
        params=params,
        task_id=str(contract.task_id),
    )
    if str(query_id) == QUERY_ID_CUBE_EDGE_TOTAL_FRAME:
        visible_frame_edge_count = 12
        frame_length = int(edge * visible_frame_edge_count)
        explicit_total = params.get("total_frame_length_units")
        if explicit_total is not None and int(explicit_total) != int(frame_length):
            raise ValueError("total_frame_length_units must equal 12 * edge_units")
        case_probabilities = {f"edge{edge}_total12": 1.0 if len(edge_probabilities) == 1 else 0.0}
        if len(edge_probabilities) != 1:
            case_probabilities = {f"edge{candidate}_total12": probability for candidate, probability in edge_probabilities.items()}
    else:
        visible_frame_edge_count, count_probabilities = _select_partial_frame_edge_count(
            instance_seed=int(instance_seed),
            params=params,
            task_id=str(contract.task_id),
        )
        frame_length = int(edge * visible_frame_edge_count)
        explicit_partial = params.get("highlighted_frame_length_units")
        if explicit_partial is not None and int(explicit_partial) != int(frame_length):
            raise ValueError("highlighted_frame_length_units must equal highlighted_edge_count * edge_units")
        case_probabilities = {
            f"edge{edge}_partial{visible_frame_edge_count}": float(edge_probabilities.get(str(edge), 1.0))
            * float(count_probabilities.get(str(visible_frame_edge_count), 1.0))
        }
        if len(edge_probabilities) != 1 or len(count_probabilities) != 1:
            case_probabilities = {
                f"edge{candidate_edge}_partial{candidate_count}": float(edge_probability) * float(count_probability)
                for candidate_edge, edge_probability in edge_probabilities.items()
                for candidate_count, count_probability in count_probabilities.items()
            }
    explicit_edge = params.get("edge_units")
    if explicit_edge is not None and int(explicit_edge) != int(edge):
        raise ValueError("edge_units mismatch")
    return _ResolvedProblem(
        task_id=str(contract.task_id),
        query_id=str(query_id),
        target_role="cube_edge",
        length=int(edge),
        width=int(edge),
        height=int(edge),
        volume=int(edge**3),
        surface_area=int(6 * edge * edge),
        cube_edge=int(edge),
        visible_frame_edge_count=int(visible_frame_edge_count),
        frame_length=int(frame_length),
        sheet_length=0,
        sheet_width=0,
        cut_size=0,
        base_length=0,
        base_width=0,
        open_box_volume=0,
        answer=int(edge),
        formula_family="cube_edge_from_frame_length",
        formula=str(contract.formula),
        query_probabilities=dict(query_probabilities),
        case_probabilities=dict(case_probabilities),
        answer_support_probabilities=_answer_support_probabilities(
            selected=int(edge),
            target_role="cube_edge",
            answer_kind=str(contract.answer_kind),
        ),
    )


def _resolve_open_box_problem(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    contract: _TaskContract,
    query_id: str,
    query_probabilities: Dict[str, float],
) -> _ResolvedProblem:
    case, case_probabilities = _select_open_box_case(
        instance_seed=int(instance_seed),
        params=params,
        task_id=str(contract.task_id),
    )
    sheet_length, sheet_width, cut_size, base_length, base_width, volume = _open_box_values_for_case(case)
    if str(query_id) == QUERY_ID_OPEN_BOX_DIMENSION:
        target_role, role_probabilities = _select_open_box_dimension_role(
            instance_seed=int(instance_seed),
            params=params,
            task_id=str(contract.task_id),
        )
        answer = base_length if target_role == "base_length" else base_width
        if len(role_probabilities) > 1:
            case_probabilities = {
                f"{case_key}_{role}": float(case_probability) * float(role_probability)
                for case_key, case_probability in case_probabilities.items()
                for role, role_probability in role_probabilities.items()
            }
        else:
            case_probabilities = {f"{case_key}_{target_role}": probability for case_key, probability in case_probabilities.items()}
    else:
        if "target_dimension_role" in params:
            raise ValueError("target_dimension_role is only supported for open_box_dimension_from_corner_cut")
        target_role = "open_box_volume"
        answer = volume
    explicit_volume = params.get("open_box_volume_units")
    if explicit_volume is not None and int(explicit_volume) != int(volume):
        raise ValueError("open_box_volume_units must equal base_length * base_width * cut_size")
    return _ResolvedProblem(
        task_id=str(contract.task_id),
        query_id=str(query_id),
        target_role=str(target_role),
        length=int(base_length),
        width=int(base_width),
        height=int(cut_size),
        volume=int(volume),
        surface_area=0,
        cube_edge=0,
        visible_frame_edge_count=0,
        frame_length=0,
        sheet_length=int(sheet_length),
        sheet_width=int(sheet_width),
        cut_size=int(cut_size),
        base_length=int(base_length),
        base_width=int(base_width),
        open_box_volume=int(volume),
        answer=int(answer),
        formula_family="open_box_net_corner_cut",
        formula=str(contract.formula),
        query_probabilities=dict(query_probabilities),
        case_probabilities=dict(case_probabilities),
        answer_support_probabilities=_answer_support_probabilities(
            selected=int(answer),
            target_role=str(target_role),
            answer_kind=str(contract.answer_kind),
        ),
    )


def _resolve_problem(*, instance_seed: int, params: Mapping[str, Any], contract: _TaskContract) -> _ResolvedProblem:
    query_id, query_probabilities = select_indexed_geometry_query_id(
        params=params,
        query_ids=contract.query_ids,
        task_id=contract.task_id,
        instance_seed=int(instance_seed),
    )
    target_role = _ROLE_BY_QUERY_ID[str(query_id)]
    if contract.answer_kind == "open_box":
        return _resolve_open_box_problem(
            instance_seed=int(instance_seed),
            params=params,
            contract=contract,
            query_id=str(query_id),
            query_probabilities=dict(query_probabilities),
        )
    if contract.answer_kind == "cube_edge":
        return _resolve_frame_problem(
            instance_seed=int(instance_seed),
            params=params,
            contract=contract,
            query_id=str(query_id),
            query_probabilities=dict(query_probabilities),
        )
    case, case_probabilities = _select_case(
        instance_seed=int(instance_seed),
        params=params,
        task_id=str(contract.task_id),
    )
    length, width, height = [int(value) for value in case]
    volume = int(length * width * height)
    surface_area = _surface_area_for_case(case)
    explicit_volume = params.get("volume_units")
    if explicit_volume is not None and int(explicit_volume) != int(volume):
        raise ValueError("volume_units must equal length_units * width_units * height_units")
    explicit_surface_area = params.get("surface_area_units")
    if explicit_surface_area is not None and int(explicit_surface_area) != int(surface_area):
        raise ValueError("surface_area_units must equal 2 * (length*width + length*height + width*height)")
    if contract.answer_kind == "surface_area":
        answer = int(surface_area)
    else:
        answer = {"length": length, "width": width, "height": height}[str(target_role)]
    return _ResolvedProblem(
        task_id=str(contract.task_id),
        query_id=str(query_id),
        target_role=str(target_role),
        length=int(length),
        width=int(width),
        height=int(height),
        volume=int(volume),
        surface_area=int(surface_area),
        cube_edge=0,
        visible_frame_edge_count=0,
        frame_length=0,
        sheet_length=0,
        sheet_width=0,
        cut_size=0,
        base_length=0,
        base_width=0,
        open_box_volume=0,
        answer=int(answer),
        formula_family=str(contract.formula_family),
        formula=str(contract.formula),
        query_probabilities=dict(query_probabilities),
        case_probabilities=dict(case_probabilities),
        answer_support_probabilities=_answer_support_probabilities(
            selected=int(answer),
            target_role=str(target_role),
            answer_kind=str(contract.answer_kind),
        ),
    )


def _make_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    rendering_defaults: Mapping[str, Any],
) -> _RenderContext:
    width = int(params.get("canvas_width", group_default(rendering_defaults, "canvas_width", 820)))
    height = int(params.get("canvas_height", group_default(rendering_defaults, "canvas_height", 600)))
    image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        task_group=TASK_GROUP,
        canvas_width=int(width),
        canvas_height=int(height),
        allow_dark=False,
        require_grid=None,
    )
    face_palettes: Tuple[Tuple[Color, Color, Color], ...] = (
        ((237, 246, 255), (218, 235, 249), (246, 251, 255)),
        ((244, 248, 238), (224, 239, 219), (251, 253, 246)),
        ((255, 242, 232), (247, 222, 208), (255, 249, 243)),
        ((245, 241, 255), (227, 220, 246), (252, 249, 255)),
    )
    palette_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{SCENE_ID}.face_palette",
    )
    face_front, face_side, face_top = face_palettes[int(palette_index) % len(face_palettes)]
    font_size = int(params.get("label_font_size", group_default(rendering_defaults, "label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", group_default(rendering_defaults, "small_label_font_size", 18)))
    line_width = int(params.get("line_width", group_default(rendering_defaults, "line_width", 3)))
    label_stroke_width = int(
        params.get(
            "label_stroke_width",
            group_default(rendering_defaults, "label_stroke_width", int(diagram_style.label_stroke_width_px)),
        )
    )
    return _RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=int(width),
        height=int(height),
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        label_backing_color=tuple(int(value) for value in diagram_style.panel_fill_rgb),
        face_front=tuple(int(value) for value in face_front),
        face_side=tuple(int(value) for value in face_side),
        face_top=tuple(int(value) for value in face_top),
        accent_color=tuple(int(value) for value in diagram_style.accent_rgb),
        muted_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(0, int(label_stroke_width)),
        font=load_font(max(12, int(font_size))),
        small_font=load_font(max(10, int(small_font_size))),
        diagram_style_meta=dict(diagram_style_meta),
        background_meta=dict(background_meta),
    )


def _draw_text_centered(ctx: _RenderContext, text: str, center: Point, *, small: bool = True) -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    bbox = ctx.draw.textbbox(
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        stroke_width=max(0, int(ctx.label_stroke_width)),
    )
    draw_label_backplate(ctx, bbox)
    draw_text_traced(
        ctx.draw,
        (float(center[0]), float(center[1])),
        str(text),
        anchor="mm",
        font=font,
        fill=ctx.label_color,
        stroke_width=max(0, int(ctx.label_stroke_width)),
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=True,
        extra_metadata=readout_text_metadata(ctx, ctx.label_color),
    )
    return pad_bbox(bbox, 4.0, width=ctx.width, height=ctx.height)


def _draw_value_box(ctx: _RenderContext, text: str, center: Point) -> BBox:
    font = ctx.font
    bbox = ctx.draw.textbbox((0, 0), str(text), font=font, stroke_width=max(0, int(ctx.label_stroke_width)))
    text_w = float(bbox[2] - bbox[0])
    text_h = float(bbox[3] - bbox[1])
    left = float(center[0]) - text_w / 2.0 - 14.0
    top = float(center[1]) - text_h / 2.0 - 9.0
    right = left + text_w + 28.0
    bottom = top + text_h + 18.0
    ctx.draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=6,
        fill=(255, 255, 255),
        outline=ctx.muted_color,
        width=max(1, ctx.line_width - 1),
    )
    draw_text_traced(
        ctx.draw,
        ((left + right) / 2.0, (top + bottom) / 2.0),
        str(text),
        anchor="mm",
        font=font,
        fill=ctx.label_color,
        stroke_width=max(0, int(ctx.label_stroke_width)),
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=True,
        extra_metadata=readout_text_metadata(ctx, ctx.label_color),
    )
    return pad_bbox((left, top, right, bottom), 2.0, width=ctx.width, height=ctx.height)


def _draw_dimension(
    ctx: _RenderContext,
    start: Point,
    end: Point,
    label: str,
    *,
    offset: Point,
    label_offset: Point,
    color: Color | None = None,
) -> tuple[Point, Point, BBox]:
    line_color = color or ctx.secondary_color
    dim_start = _add(start, offset)
    dim_end = _add(end, offset)
    ctx.draw.line([dim_start, dim_end], fill=line_color, width=max(2, ctx.line_width - 1))
    direction = _unit(_sub(dim_end, dim_start))
    normal = _perp(direction)
    tick = 7.0
    for point in (dim_start, dim_end):
        ctx.draw.line(
            [
                _add(point, _mul(normal, -tick)),
                _add(point, _mul(normal, tick)),
            ],
            fill=line_color,
            width=max(1, ctx.line_width - 2),
        )
    midpoint = ((float(dim_start[0]) + float(dim_end[0])) / 2.0, (float(dim_start[1]) + float(dim_end[1])) / 2.0)
    label_bbox = _draw_text_centered(ctx, label, _add(midpoint, label_offset), small=True)
    return dim_start, dim_end, label_bbox


def _assert_bboxes_inside(bboxes: Sequence[BBox], *, width: int, height: int) -> None:
    for bbox in bboxes:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        if x0 <= 3.0 or y0 <= 3.0 or x1 >= float(width) - 3.0 or y1 >= float(height) - 3.0:
            raise ValueError("rectangular-solid label too close to canvas edge")


def _segment_bbox(start: Point, end: Point, *, width: int, height: int, pad: float = 8.0) -> BBox:
    return pad_bbox(
        (
            min(float(start[0]), float(end[0])),
            min(float(start[1]), float(end[1])),
            max(float(start[0]), float(end[0])),
            max(float(start[1]), float(end[1])),
        ),
        float(pad),
        width=int(width),
        height=int(height),
    )


def _draw_hatched_cutout(ctx: _RenderContext, bbox: BBox) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    ctx.draw.rectangle((x0, y0, x1, y1), fill=(255, 248, 244), outline=ctx.secondary_color, width=max(1, ctx.line_width - 2))
    step = 10.0
    offset = -float(y1 - y0)
    while offset < float(x1 - x0):
        start = (x0 + max(0.0, offset), y1 if offset < 0 else y0)
        end = (x0 + min(float(x1 - x0), offset + float(y1 - y0)), y0 if offset < 0 else y0 + min(float(y1 - y0), float(x1 - x0) - offset))
        ctx.draw.line([start, end], fill=ctx.muted_color, width=1)
        offset += step


def _render_open_box_net_scene(ctx: _RenderContext, problem: _ResolvedProblem, *, instance_seed: int) -> _RenderedScene:
    rng = spawn_rng(int(instance_seed), f"{problem.task_id}.render.open_box_net_scene")
    sheet_length = float(problem.sheet_length)
    sheet_width = float(problem.sheet_width)
    cut_size = float(problem.cut_size)
    scale = min((ctx.width - 210.0) / sheet_length, (ctx.height - 190.0) / sheet_width)
    scale *= float(rng.uniform(0.88, 0.97))
    sheet_px_w = sheet_length * scale
    sheet_px_h = sheet_width * scale
    left = (ctx.width - sheet_px_w) / 2.0 + float(rng.uniform(-24.0, 24.0))
    top = (ctx.height - sheet_px_h) / 2.0 + float(rng.uniform(8.0, 30.0))
    right = left + sheet_px_w
    bottom = top + sheet_px_h
    cut = cut_size * scale
    sheet_bbox = pad_bbox((left, top, right, bottom), 4.0, width=ctx.width, height=ctx.height)
    base_bbox = (left + cut, top + cut, right - cut, bottom - cut)
    cutout_bboxes: Dict[str, BBox] = {
        "top_left": (left, top, left + cut, top + cut),
        "top_right": (right - cut, top, right, top + cut),
        "bottom_left": (left, bottom - cut, left + cut, bottom),
        "bottom_right": (right - cut, bottom - cut, right, bottom),
    }
    flap_bboxes: Dict[str, BBox] = {
        "top": (left + cut, top, right - cut, top + cut),
        "bottom": (left + cut, bottom - cut, right - cut, bottom),
        "left": (left, top + cut, left + cut, bottom - cut),
        "right": (right - cut, top + cut, right, bottom - cut),
    }
    ctx.draw.rounded_rectangle(
        (left - 16.0, top - 16.0, right + 16.0, bottom + 16.0),
        radius=8,
        fill=(255, 255, 255),
        outline=ctx.muted_color,
        width=max(1, ctx.line_width - 2),
    )
    for bbox in cutout_bboxes.values():
        _draw_hatched_cutout(ctx, bbox)
    for bbox in flap_bboxes.values():
        ctx.draw.rectangle(bbox, fill=ctx.face_top, outline=ctx.line_color, width=max(2, ctx.line_width - 1))
    ctx.draw.rectangle(base_bbox, fill=ctx.face_front, outline=ctx.line_color, width=ctx.line_width)
    for x0, y0, x1, y1 in flap_bboxes.values():
        ctx.draw.rectangle((x0, y0, x1, y1), outline=ctx.secondary_color, width=1)

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["sheet_length"] = _draw_text_centered(
        ctx,
        f"sheet length {int(problem.sheet_length)}",
        ((left + right) / 2.0, bottom + 28.0),
        small=True,
    )
    label_bboxes["sheet_width"] = _draw_text_centered(
        ctx,
        f"sheet width {int(problem.sheet_width)}",
        (left - 48.0, (top + bottom) / 2.0),
        small=True,
    )
    label_bboxes["cut_size"] = _draw_text_centered(
        ctx,
        f"cut {int(problem.cut_size)}",
        ((cutout_bboxes["top_left"][0] + cutout_bboxes["top_left"][2]) / 2.0, (cutout_bboxes["top_left"][1] + cutout_bboxes["top_left"][3]) / 2.0),
        small=True,
    )
    if problem.target_role == "base_length":
        target_bbox = _segment_bbox(
            (base_bbox[0], base_bbox[3]),
            (base_bbox[2], base_bbox[3]),
            width=ctx.width,
            height=ctx.height,
            pad=12.0,
        )
        label_bboxes["target"] = _draw_text_centered(ctx, "?", ((base_bbox[0] + base_bbox[2]) / 2.0, base_bbox[3] - 18.0), small=True)
    elif problem.target_role == "base_width":
        target_bbox = _segment_bbox(
            (base_bbox[2], base_bbox[1]),
            (base_bbox[2], base_bbox[3]),
            width=ctx.width,
            height=ctx.height,
            pad=12.0,
        )
        label_bboxes["target"] = _draw_text_centered(ctx, "?", (base_bbox[2] - 18.0, (base_bbox[1] + base_bbox[3]) / 2.0), small=True)
    else:
        target_bbox = pad_bbox(base_bbox, 4.0, width=ctx.width, height=ctx.height)
        label_bboxes["volume"] = _draw_value_box(ctx, "Volume ?", (ctx.width / 2.0, 52.0 + float(rng.uniform(-5.0, 7.0))))

    annotation_bboxes = {
        "sheet_bbox": sheet_bbox,
        "cutout_bbox": pad_bbox(cutout_bboxes["top_left"], 4.0, width=ctx.width, height=ctx.height),
        "base_panel_bbox": pad_bbox(base_bbox, 4.0, width=ctx.width, height=ctx.height),
        "target_region_bbox": target_bbox,
    }
    _assert_bboxes_inside(tuple(annotation_bboxes.values()) + tuple(label_bboxes.values()), width=ctx.width, height=ctx.height)
    scene_entities = (
        {
            "entity_id": "open_box_net",
            "entity_type": "corner_cut_open_box_net",
            "sheet_length_units": int(problem.sheet_length),
            "sheet_width_units": int(problem.sheet_width),
            "cut_size_units": int(problem.cut_size),
            "base_length_units": int(problem.base_length),
            "base_width_units": int(problem.base_width),
            "height_units": int(problem.height),
            "open_box_volume_units": int(problem.open_box_volume),
            "bbox": bbox_to_list(sheet_bbox),
        },
    )
    render_map = {
        "coord_space": "pixel",
        "query_id": str(problem.query_id),
        "target_role": str(problem.target_role),
        "sheet_bbox": bbox_to_list(sheet_bbox),
        "cutout_bboxes": {key: bbox_to_list(value) for key, value in cutout_bboxes.items()},
        "flap_bboxes": {key: bbox_to_list(value) for key, value in flap_bboxes.items()},
        "base_panel_bbox": bbox_to_list(base_bbox),
        "annotation_bboxes": {key: bbox_to_list(value) for key, value in annotation_bboxes.items()},
        "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
        "scale_px_per_unit": round(float(scale), 3),
    }
    return _RenderedScene(
        image=ctx.image,
        annotation_type="keyed_bbox_map",
        annotation_keyed_points={},
        annotation_keyed_bboxes=dict(annotation_bboxes),
        annotation_roles=NET_ANNOTATION_KEYS,
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map=render_map,
    )


def _render_frame_scene(ctx: _RenderContext, problem: _ResolvedProblem, *, instance_seed: int) -> _RenderedScene:
    rng = spawn_rng(int(instance_seed), f"{problem.task_id}.render.frame_scene")
    depth_vec = (0.68, -0.44)
    local_points = {
        "front_bottom_left": (0.0, 0.0),
        "front_bottom_right": (1.0, 0.0),
        "back_bottom_left": depth_vec,
        "back_bottom_right": (1.0 + depth_vec[0], depth_vec[1]),
        "front_top_left": (0.0, -1.0),
        "front_top_right": (1.0, -1.0),
        "back_top_left": (depth_vec[0], depth_vec[1] - 1.0),
        "back_top_right": (1.0 + depth_vec[0], depth_vec[1] - 1.0),
    }
    min_x = min(point[0] for point in local_points.values())
    max_x = max(point[0] for point in local_points.values())
    min_y = min(point[1] for point in local_points.values())
    max_y = max(point[1] for point in local_points.values())
    span_x = max(1e-6, max_x - min_x)
    span_y = max(1e-6, max_y - min_y)
    scale = min((ctx.width - 300.0) / span_x, (ctx.height - 220.0) / span_y)
    scale *= float(rng.uniform(0.88, 0.98))
    local_center = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    target_center = (
        (ctx.width / 2.0) + float(rng.uniform(-28.0, 28.0)),
        (ctx.height / 2.0) + float(rng.uniform(-8.0, 24.0)),
    )

    def transform(point: Point) -> Point:
        return (
            (float(point[0]) - float(local_center[0])) * float(scale) + float(target_center[0]),
            (float(point[1]) - float(local_center[1])) * float(scale) + float(target_center[1]),
        )

    points = {key: transform(point) for key, point in local_points.items()}
    edge_defs: Dict[str, Tuple[str, str]] = {
        "front_bottom": ("front_bottom_left", "front_bottom_right"),
        "right_depth_bottom": ("front_bottom_right", "back_bottom_right"),
        "back_bottom": ("back_bottom_left", "back_bottom_right"),
        "left_depth_bottom": ("front_bottom_left", "back_bottom_left"),
        "front_left_vertical": ("front_bottom_left", "front_top_left"),
        "front_right_vertical": ("front_bottom_right", "front_top_right"),
        "back_right_vertical": ("back_bottom_right", "back_top_right"),
        "back_left_vertical": ("back_bottom_left", "back_top_left"),
        "front_top": ("front_top_left", "front_top_right"),
        "right_depth_top": ("front_top_right", "back_top_right"),
        "back_top": ("back_top_left", "back_top_right"),
        "left_depth_top": ("front_top_left", "back_top_left"),
    }
    draw_order = (
        "back_bottom",
        "back_left_vertical",
        "back_top",
        "left_depth_bottom",
        "left_depth_top",
        "right_depth_bottom",
        "right_depth_top",
        "back_right_vertical",
        "front_bottom",
        "front_left_vertical",
        "front_right_vertical",
        "front_top",
    )
    partial_paths: Tuple[Tuple[str, ...], ...] = (
        (
            "front_bottom",
            "right_depth_bottom",
            "back_right_vertical",
            "right_depth_top",
            "front_top",
            "front_left_vertical",
            "left_depth_bottom",
            "back_bottom",
        ),
        (
            "front_left_vertical",
            "front_top",
            "right_depth_top",
            "back_right_vertical",
            "right_depth_bottom",
            "front_bottom",
            "left_depth_bottom",
            "back_left_vertical",
        ),
        (
            "left_depth_top",
            "back_top",
            "back_right_vertical",
            "right_depth_bottom",
            "front_bottom",
            "front_left_vertical",
            "front_top",
            "right_depth_top",
        ),
    )
    path_index = resolve_selection_index(
        params={},
        instance_seed=int(instance_seed),
        namespace=f"{problem.task_id}.partial_frame_path",
    )
    if str(problem.query_id) == QUERY_ID_CUBE_EDGE_PARTIAL_FRAME:
        highlighted_edges = tuple(partial_paths[int(path_index) % len(partial_paths)][: int(problem.visible_frame_edge_count)])
    else:
        highlighted_edges = tuple(edge_defs.keys())

    full_frame_bbox = bbox_from_points(tuple(points.values()), width=ctx.width, height=ctx.height, pad=10.0)
    ctx.draw.rounded_rectangle(
        (full_frame_bbox[0] - 18.0, full_frame_bbox[1] - 18.0, full_frame_bbox[2] + 18.0, full_frame_bbox[3] + 18.0),
        radius=8,
        fill=(255, 255, 255),
        outline=ctx.muted_color,
        width=max(1, ctx.line_width - 2),
    )
    for edge_id in draw_order:
        start_key, end_key = edge_defs[edge_id]
        edge_color = ctx.muted_color if edge_id not in highlighted_edges else ctx.accent_color
        edge_width = max(2, ctx.line_width - 1) if edge_id not in highlighted_edges else max(5, ctx.line_width + 2)
        ctx.draw.line([points[start_key], points[end_key]], fill=edge_color, width=edge_width)
    for point in points.values():
        radius = 4.0
        ctx.draw.ellipse(
            (point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius),
            fill=ctx.line_color,
            outline=(255, 255, 255),
            width=1,
        )

    target_edge_id = "front_bottom"
    target_start_key, target_end_key = edge_defs[target_edge_id]
    target_start = points[target_start_key]
    target_end = points[target_end_key]
    target_mid = ((target_start[0] + target_end[0]) / 2.0, (target_start[1] + target_end[1]) / 2.0)
    target_edge_bbox = _segment_bbox(target_start, target_end, width=ctx.width, height=ctx.height, pad=10.0)
    label_bboxes: Dict[str, BBox] = {
        "target_edge": _draw_text_centered(ctx, "?", (target_mid[0], target_mid[1] + 26.0), small=True)
    }
    readout_text = (
        f"Total frame length {int(problem.frame_length)}"
        if str(problem.query_id) == QUERY_ID_CUBE_EDGE_TOTAL_FRAME
        else f"Highlighted length {int(problem.frame_length)}"
    )
    label_bboxes["frame_length"] = _draw_value_box(ctx, readout_text, (ctx.width / 2.0, 52.0 + float(rng.uniform(-5.0, 7.0))))

    highlighted_points = tuple(
        point
        for edge_id in highlighted_edges
        for point in (points[edge_defs[edge_id][0]], points[edge_defs[edge_id][1]])
    )
    highlighted_bbox = bbox_from_points(highlighted_points, width=ctx.width, height=ctx.height, pad=12.0)
    given_length_bbox = full_frame_bbox if str(problem.query_id) == QUERY_ID_CUBE_EDGE_TOTAL_FRAME else highlighted_bbox
    annotation_bboxes = {
        "frame_bbox": full_frame_bbox,
        "given_length_region_bbox": given_length_bbox,
        "target_edge_bbox": target_edge_bbox,
    }
    _assert_bboxes_inside(tuple(annotation_bboxes.values()) + tuple(label_bboxes.values()), width=ctx.width, height=ctx.height)
    scene_entities = (
        {
            "entity_id": "cube_frame",
            "entity_type": "cube_wire_frame",
            "edge_units": int(problem.cube_edge),
            "visible_frame_edge_count": int(problem.visible_frame_edge_count),
            "frame_length_units": int(problem.frame_length),
            "total_frame_length_units": int(problem.cube_edge * 12),
            "bbox": bbox_to_list(full_frame_bbox),
        },
    )
    render_map = {
        "coord_space": "pixel",
        "query_id": str(problem.query_id),
        "target_role": str(problem.target_role),
        "cube_vertices": {key: _point_to_list(value) for key, value in points.items()},
        "frame_edges": {
            edge_id: [_point_to_list(points[start_key]), _point_to_list(points[end_key])]
            for edge_id, (start_key, end_key) in edge_defs.items()
        },
        "highlighted_edges": list(highlighted_edges),
        "target_edge": str(target_edge_id),
        "annotation_bboxes": {key: bbox_to_list(value) for key, value in annotation_bboxes.items()},
        "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
        "scale_px_per_edge": round(float(scale), 3),
    }
    return _RenderedScene(
        image=ctx.image,
        annotation_type="keyed_bbox_map",
        annotation_keyed_points={},
        annotation_keyed_bboxes=dict(annotation_bboxes),
        annotation_roles=FRAME_ANNOTATION_KEYS,
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map=render_map,
    )


def _render_scene(ctx: _RenderContext, problem: _ResolvedProblem, *, instance_seed: int) -> _RenderedScene:
    if problem.target_role in {"base_length", "base_width", "open_box_volume"}:
        return _render_open_box_net_scene(ctx, problem, instance_seed=int(instance_seed))
    if problem.target_role == "cube_edge":
        return _render_frame_scene(ctx, problem, instance_seed=int(instance_seed))

    rng = spawn_rng(int(instance_seed), f"{problem.task_id}.render.scene")
    length = float(problem.length)
    width_units = float(problem.width)
    height_units = float(problem.height)
    depth_vec = (0.64 * width_units, -0.42 * width_units)

    local_points = {
        "front_bottom_left": (0.0, 0.0),
        "front_bottom_right": (length, 0.0),
        "back_bottom_left": depth_vec,
        "back_bottom_right": (length + depth_vec[0], depth_vec[1]),
        "front_top_left": (0.0, -height_units),
        "front_top_right": (length, -height_units),
        "back_top_left": (depth_vec[0], depth_vec[1] - height_units),
        "back_top_right": (length + depth_vec[0], depth_vec[1] - height_units),
    }
    min_x = min(point[0] for point in local_points.values())
    max_x = max(point[0] for point in local_points.values())
    min_y = min(point[1] for point in local_points.values())
    max_y = max(point[1] for point in local_points.values())
    span_x = max(1e-6, max_x - min_x)
    span_y = max(1e-6, max_y - min_y)
    scale = min((ctx.width - 230.0) / span_x, (ctx.height - 210.0) / span_y)
    scale *= float(rng.uniform(0.84, 0.93))
    local_center = ((min_x + max_x) / 2.0, (min_y + max_y) / 2.0)
    target_center = (
        (ctx.width / 2.0) + float(rng.uniform(-26.0, 26.0)),
        (ctx.height / 2.0) + float(rng.uniform(-18.0, 18.0)),
    )

    def transform(point: Point) -> Point:
        return (
            (float(point[0]) - float(local_center[0])) * float(scale) + float(target_center[0]),
            (float(point[1]) - float(local_center[1])) * float(scale) + float(target_center[1]),
        )

    points = {key: transform(point) for key, point in local_points.items()}
    fbl = points["front_bottom_left"]
    fbr = points["front_bottom_right"]
    bbl = points["back_bottom_left"]
    bbr = points["back_bottom_right"]
    ftl = points["front_top_left"]
    ftr = points["front_top_right"]
    btl = points["back_top_left"]
    btr = points["back_top_right"]

    top_face = (ftl, ftr, btr, btl)
    side_face = (fbr, bbr, btr, ftr)
    front_face = (fbl, fbr, ftr, ftl)
    for polygon, fill in ((top_face, ctx.face_top), (side_face, ctx.face_side), (front_face, ctx.face_front)):
        ctx.draw.polygon(list(polygon), fill=fill)
        ctx.draw.line(list(polygon) + [polygon[0]], fill=ctx.line_color, width=ctx.line_width)
    for edge in ((bbl, bbr), (bbl, btl), (bbl, fbl), (bbr, btr)):
        ctx.draw.line(edge, fill=ctx.line_color, width=max(1, ctx.line_width - 1))

    labels = {
        "length": "L ?" if problem.target_role == "length" else f"L {int(problem.length)}",
        "width": "W ?" if problem.target_role == "width" else f"W {int(problem.width)}",
        "height": "H ?" if problem.target_role == "height" else f"H {int(problem.height)}",
    }
    label_bboxes: Dict[str, BBox] = {}
    length_start, length_end, label_bboxes["length"] = _draw_dimension(
        ctx,
        fbl,
        fbr,
        labels["length"],
        offset=(0.0, 34.0),
        label_offset=(0.0, 19.0),
        color=ctx.secondary_color,
    )
    width_start, width_end, label_bboxes["width"] = _draw_dimension(
        ctx,
        fbr,
        bbr,
        labels["width"],
        offset=(26.0, 15.0),
        label_offset=(24.0, 5.0),
        color=ctx.secondary_color,
    )
    height_start, height_end, label_bboxes["height"] = _draw_dimension(
        ctx,
        fbl,
        ftl,
        labels["height"],
        offset=(-34.0, 0.0),
        label_offset=(-27.0, 0.0),
        color=ctx.secondary_color,
    )

    readout_center = (ctx.width / 2.0, 50.0 + float(rng.uniform(-6.0, 8.0)))
    if problem.target_role == "surface_area":
        label_bboxes["surface_area"] = _draw_value_box(ctx, "Surface area ?", readout_center)
    else:
        label_bboxes["volume"] = _draw_value_box(ctx, f"Volume {int(problem.volume)}", readout_center)
    _assert_bboxes_inside(label_bboxes.values(), width=ctx.width, height=ctx.height)

    annotation = {
        "length_segment_start": length_start,
        "length_segment_end": length_end,
        "width_segment_start": width_start,
        "width_segment_end": width_end,
        "height_segment_start": height_start,
        "height_segment_end": height_end,
    }
    entity_bbox = bbox_from_points(tuple(points.values()), width=ctx.width, height=ctx.height, pad=10.0)
    scene_entities = (
        {
            "entity_id": "cuboid",
            "entity_type": "rectangular_prism",
            "length_units": int(problem.length),
            "width_units": int(problem.width),
            "height_units": int(problem.height),
            "volume_units": int(problem.volume),
            "surface_area_units": int(problem.surface_area),
            "bbox": bbox_to_list(entity_bbox),
        },
    )
    render_map = {
        "coord_space": "pixel",
        "query_id": str(problem.query_id),
        "target_role": str(problem.target_role),
        "cuboid_vertices": {key: _point_to_list(value) for key, value in points.items()},
        "dimension_segments": {
            "length": [_point_to_list(length_start), _point_to_list(length_end)],
            "width": [_point_to_list(width_start), _point_to_list(width_end)],
            "height": [_point_to_list(height_start), _point_to_list(height_end)],
        },
        "face_bboxes": {
            "front": bbox_to_list(bbox_from_points(front_face, width=ctx.width, height=ctx.height, pad=4.0)),
            "side": bbox_to_list(bbox_from_points(side_face, width=ctx.width, height=ctx.height, pad=4.0)),
            "top": bbox_to_list(bbox_from_points(top_face, width=ctx.width, height=ctx.height, pad=4.0)),
        },
        "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
        "scale_px_per_unit": round(float(scale), 3),
    }
    return _RenderedScene(
        image=ctx.image,
        annotation_type="keyed_point_map",
        annotation_keyed_points={key: tuple(value) for key, value in annotation.items()},
        annotation_keyed_bboxes={},
        annotation_roles=ANNOTATION_KEYS,
        label_bboxes=dict(label_bboxes),
        scene_entities=scene_entities,
        render_map=render_map,
    )


def _make_prompt_examples(*, answer: int, annotation_type: str, annotation_roles: Sequence[str]) -> tuple[str, str]:
    if str(annotation_type) == "keyed_bbox_map" and tuple(annotation_roles) == NET_ANNOTATION_KEYS:
        annotation = {
            "sheet_bbox": [150, 120, 670, 470],
            "cutout_bbox": [150, 120, 225, 195],
            "base_panel_bbox": [225, 195, 595, 395],
            "target_region_bbox": [225, 380, 595, 410],
        }
    elif str(annotation_type) == "keyed_bbox_map":
        annotation = {
            "frame_bbox": [210, 145, 610, 465],
            "given_length_region_bbox": [210, 145, 610, 465],
            "target_edge_bbox": [235, 430, 455, 455],
        }
    else:
        annotation = {
            "length_segment_start": [180, 420],
            "length_segment_end": [470, 420],
            "width_segment_start": [500, 392],
            "width_segment_end": [590, 340],
            "height_segment_start": [145, 390],
            "height_segment_end": [145, 190],
        }
    return dump_prompt_json_examples(annotation=annotation, answer=int(answer))


@register_task
class GeometryRectangularSolidCuboidVolumeMissingDimensionValueTask:
    """Solve a missing cuboid dimension from volume and two dimensions."""

    task_id = TASK_ID
    domain = "geometry"
    task_group = TASK_GROUP
    scene_id = SCENE_ID
    public_scene_id = SCENE_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        contract = _CONTRACTS_BY_TASK_ID[str(self.task_id)]
        _generation_defaults, rendering_defaults, prompt_defaults = split_generation_rendering_prompt_defaults(
            _TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
        )
        problem = _resolve_problem(instance_seed=int(instance_seed), params=params, contract=contract)
        rendered: _RenderedScene | None = None
        ctx: _RenderContext | None = None
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            attempt_params = dict(params)
            attempt_params["_render_attempt"] = int(attempt)
            try:
                ctx = _make_render_context(
                    instance_seed=int(instance_seed) + int(attempt),
                    params=attempt_params,
                    rendering_defaults=rendering_defaults,
                )
                rendered = _render_scene(ctx, problem, instance_seed=int(instance_seed) + int(attempt))
                break
            except Exception as exc:
                last_error = exc
                continue
        if rendered is None or ctx is None:
            raise RuntimeError(f"failed to generate {self.task_id}") from last_error

        image, noise_meta = apply_post_image_noise(
            rendered.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )
        prompt_defaults = required_group_defaults(
            prompt_defaults,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "object_description",
                "json_output_contract",
                "json_output_contract_answer_only",
                "annotation_hint",
                "answer_hint_integer",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _make_prompt_examples(
            answer=int(problem.answer),
            annotation_type=str(rendered.annotation_type),
            annotation_roles=rendered.annotation_roles,
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(problem.query_id),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint_integer"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        if rendered.annotation_type == "keyed_bbox_map":
            annotation_value = {str(key): bbox_to_list(value) for key, value in rendered.annotation_keyed_bboxes.items()}
            projected_annotation = {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_value),
                "pixel_keyed_bbox_map": dict(annotation_value),
            }
        else:
            annotation_value = {str(key): _point_to_list(value) for key, value in rendered.annotation_keyed_points.items()}
            projected_annotation = {
                "type": "keyed_point_map",
                "keyed_point_map": dict(annotation_value),
                "pixel_keyed_point_map": dict(annotation_value),
            }
        trace_payload: Dict[str, Any] = {
            "scene_ir": {
                "domain": self.domain,
                "task_group": self.task_group,
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "type": str(problem.formula_family),
                    "length": int(problem.length),
                    "width": int(problem.width),
                    "height": int(problem.height),
                    "volume": int(problem.volume),
                    "surface_area": int(problem.surface_area),
                    "cube_edge": int(problem.cube_edge),
                    "visible_frame_edge_count": int(problem.visible_frame_edge_count),
                    "frame_length": int(problem.frame_length),
                    "sheet_length": int(problem.sheet_length),
                    "sheet_width": int(problem.sheet_width),
                    "cut_size": int(problem.cut_size),
                    "base_length": int(problem.base_length),
                    "base_width": int(problem.base_width),
                    "open_box_volume": int(problem.open_box_volume),
                    "target_role": str(problem.target_role),
                    "annotation_roles": list(rendered.annotation_roles),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "params": {
                    "query_id": str(problem.query_id),
                    "query_id_probabilities": dict(problem.query_probabilities),
                    "cuboid_case_probabilities": dict(problem.case_probabilities),
                    "target_role": str(problem.target_role),
                    "answer_support_probabilities": dict(problem.answer_support_probabilities),
                    "visible_frame_edge_count": int(problem.visible_frame_edge_count),
                    "sheet_length": int(problem.sheet_length),
                    "sheet_width": int(problem.sheet_width),
                    "cut_size": int(problem.cut_size),
                    "base_length": int(problem.base_length),
                    "base_width": int(problem.base_width),
                },
            },
            "render_spec": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "canvas": {"width": int(image.size[0]), "height": int(image.size[1])},
                "style": {
                    "technical_diagram": dict(ctx.diagram_style_meta),
                    "background": dict(ctx.background_meta),
                    "post_image_noise": dict(noise_meta),
                },
                "prompt": {
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                },
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "length": int(problem.length),
                "width": int(problem.width),
                "height": int(problem.height),
                "volume": int(problem.volume),
                "surface_area": int(problem.surface_area),
                "cube_edge": int(problem.cube_edge),
                "visible_frame_edge_count": int(problem.visible_frame_edge_count),
                "frame_length": int(problem.frame_length),
                "sheet_length": int(problem.sheet_length),
                "sheet_width": int(problem.sheet_width),
                "cut_size": int(problem.cut_size),
                "base_length": int(problem.base_length),
                "base_width": int(problem.base_width),
                "open_box_volume": int(problem.open_box_volume),
                "target_role": str(problem.target_role),
                "formula_family": str(problem.formula_family),
                "formula": str(problem.formula),
                "answer": int(problem.answer),
                "annotation_roles": list(rendered.annotation_roles),
            },
            "witness_symbolic": {
                "task_id": self.task_id,
                "scene_id": SCENE_ID,
                "query_id": str(problem.query_id),
                "formula_family": str(problem.formula_family),
                "length": int(problem.length),
                "width": int(problem.width),
                "height": int(problem.height),
                "volume": int(problem.volume),
                "surface_area": int(problem.surface_area),
                "cube_edge": int(problem.cube_edge),
                "visible_frame_edge_count": int(problem.visible_frame_edge_count),
                "frame_length": int(problem.frame_length),
                "sheet_length": int(problem.sheet_length),
                "sheet_width": int(problem.sheet_width),
                "cut_size": int(problem.cut_size),
                "base_length": int(problem.base_length),
                "base_width": int(problem.base_width),
                "open_box_volume": int(problem.open_box_volume),
                "target_role": str(problem.target_role),
                "answer_value": int(problem.answer),
            },
            "projected_annotation": projected_annotation,
        }
        complexity = build_geometry_measurement_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            visual_scan=0.58,
            measurement_precision=0.46,
            ambiguity=0.42,
            output_burden=normalize_linear(len(annotation_value), min_value=4, max_value=6),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=TypedValue(type="integer", value=int(problem.answer)),
            annotation_gt=TypedValue(type=str(rendered.annotation_type), value=dict(annotation_value)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(problem.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


@register_task
class GeometryRectangularSolidCuboidSurfaceAreaValueTask(GeometryRectangularSolidCuboidVolumeMissingDimensionValueTask):
    """Compute total surface area of a labeled cuboid."""

    task_id = TASK_ID_SURFACE_AREA


@register_task
class GeometryRectangularSolidCubeEdgeFromFrameLengthValueTask(GeometryRectangularSolidCuboidVolumeMissingDimensionValueTask):
    """Compute cube edge length from a total or highlighted frame length."""

    task_id = TASK_ID_FRAME_EDGE


@register_task
class GeometryRectangularSolidOpenBoxNetDimensionValueTask(GeometryRectangularSolidCuboidVolumeMissingDimensionValueTask):
    """Compute open-box dimensions or volume from a corner-cut net."""

    task_id = TASK_ID_OPEN_BOX_NET


__all__ = [
    "ANNOTATION_KEYS",
    "FRAME_EDGE_QUERY_IDS",
    "FRAME_ANNOTATION_KEYS",
    "GeometryRectangularSolidCubeEdgeFromFrameLengthValueTask",
    "GeometryRectangularSolidCuboidSurfaceAreaValueTask",
    "GeometryRectangularSolidCuboidVolumeMissingDimensionValueTask",
    "GeometryRectangularSolidOpenBoxNetDimensionValueTask",
    "MISSING_DIMENSION_QUERY_IDS",
    "NET_ANNOTATION_KEYS",
    "OPEN_BOX_NET_QUERY_IDS",
    "SURFACE_AREA_QUERY_IDS",
    "QUERY_ID_CUBE_EDGE_PARTIAL_FRAME",
    "QUERY_ID_CUBE_EDGE_TOTAL_FRAME",
    "QUERY_ID_OPEN_BOX_DIMENSION",
    "QUERY_ID_OPEN_BOX_VOLUME",
    "QUERY_ID_SURFACE_AREA",
    "QUERY_ID_MISSING_HEIGHT",
    "QUERY_ID_MISSING_LENGTH",
    "QUERY_ID_MISSING_WIDTH",
    "QUERY_IDS",
    "SCENE_ID",
    "TASK_ID",
    "TASK_ID_FRAME_EDGE",
    "TASK_ID_MISSING_DIMENSION",
    "TASK_ID_OPEN_BOX_NET",
    "TASK_ID_SURFACE_AREA",
]
