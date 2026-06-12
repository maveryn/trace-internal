"""Scene-local runtime primitives for container volume-transfer diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from trace.core.seed import spawn_rng
from trace.tasks.shared.config_defaults import group_default
from trace.tasks.shared.deterministic_sampling import resolve_selection_index
from trace.tasks.shared.prompt_json_example import dump_prompt_json_examples
from trace.tasks.shared.text_legibility import draw_text_traced
from trace.tasks.shared.text_rendering import load_font
from trace.tasks.geometry.shared.diagram_style import prepare_geometry_diagram_style_and_background
from trace.tasks.geometry.shared.measurement_rendering import bbox_to_list, bbox_union_from_bboxes as _bbox_union, pad_bbox
from trace.tasks.geometry.shared.noise_defaults import POST_IMAGE_NOISE_DEFAULTS

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]
Color = Tuple[int, int, int]

PROMPT_BUNDLE_ID = "geometry_container_volume_transfer_v0"

QUERY_ID_CONE_TO_CYLINDER_FILL_COUNT = "cone_to_cylinder_fill_count"
QUERY_ID_CYLINDER_TO_CUBOID_FILL_COUNT = "cylinder_to_cuboid_fill_count"
QUERY_ID_CONE_POURS_TO_CYLINDER_HEIGHT = "cone_pours_to_cylinder_height"
QUERY_ID_CYLINDER_POURS_TO_CUBOID_HEIGHT = "cylinder_pours_to_cuboid_height"
QUERY_ID_TARGET_CAPACITY_FROM_SOURCE_AND_COUNT = "target_capacity_from_source_and_count"
QUERY_ID_REPEATED_CONE_POURS_TOTAL_VOLUME = "repeated_cone_pours_total_volume"
QUERY_ID_REPEATED_CYLINDER_POURS_TOTAL_VOLUME = "repeated_cylinder_pours_total_volume"
FILL_COUNT_QUERY_IDS: Tuple[str, ...] = (
    QUERY_ID_CONE_TO_CYLINDER_FILL_COUNT,
    QUERY_ID_CYLINDER_TO_CUBOID_FILL_COUNT,
)
RESULTING_HEIGHT_QUERY_IDS: Tuple[str, ...] = (
    QUERY_ID_CONE_POURS_TO_CYLINDER_HEIGHT,
    QUERY_ID_CYLINDER_POURS_TO_CUBOID_HEIGHT,
)
TARGET_CAPACITY_QUERY_IDS: Tuple[str, ...] = (QUERY_ID_TARGET_CAPACITY_FROM_SOURCE_AND_COUNT,)
TRANSFERRED_VOLUME_QUERY_IDS: Tuple[str, ...] = (
    QUERY_ID_REPEATED_CONE_POURS_TOTAL_VOLUME,
    QUERY_ID_REPEATED_CYLINDER_POURS_TOTAL_VOLUME,
)
QUERY_IDS: Tuple[str, ...] = (
    FILL_COUNT_QUERY_IDS
    + RESULTING_HEIGHT_QUERY_IDS
    + TARGET_CAPACITY_QUERY_IDS
    + TRANSFERRED_VOLUME_QUERY_IDS
)

FILL_COUNT_ANNOTATION_KEYS: Tuple[str, ...] = (
    "source_container_bbox",
    "target_container_bbox",
    "source_dimension_region_bbox",
    "target_dimension_region_bbox",
    "transfer_arrow_bbox",
)
RESULTING_HEIGHT_ANNOTATION_KEYS: Tuple[str, ...] = (
    "source_container_bbox",
    "target_container_bbox",
    "source_dimension_region_bbox",
    "target_base_dimension_region_bbox",
    "transfer_count_bbox",
    "fill_mark_bbox",
)
TARGET_CAPACITY_ANNOTATION_KEYS: Tuple[str, ...] = (
    "source_container_bbox",
    "target_container_bbox",
    "source_dimension_region_bbox",
    "transfer_count_bbox",
    "transfer_arrow_bbox",
)
TRANSFERRED_VOLUME_ANNOTATION_KEYS: Tuple[str, ...] = TARGET_CAPACITY_ANNOTATION_KEYS
ANNOTATION_KEYS: Tuple[str, ...] = FILL_COUNT_ANNOTATION_KEYS


# Cone cases store source base area, source height, target cylinder base area, target height.
_CONE_TO_CYLINDER_CASES: Tuple[Tuple[int, int, int, int], ...] = (
    (12, 6, 8, 6),
    (9, 9, 9, 6),
    (15, 6, 10, 9),
    (12, 9, 9, 12),
    (12, 5, 10, 8),
    (15, 4, 10, 10),
    (18, 5, 12, 15),
    (21, 4, 14, 14),
    (24, 3, 12, 16),
)

# Cylinder-to-cuboid cases store source base area, source height, target length, width, height.
_CYLINDER_TO_CUBOID_CASES: Tuple[Tuple[int, int, int, int, int], ...] = (
    (6, 5, 5, 4, 3),
    (8, 4, 8, 4, 3),
    (10, 3, 10, 4, 3),
    (9, 4, 9, 5, 4),
    (12, 3, 12, 6, 3),
    (14, 2, 14, 7, 2),
    (8, 5, 10, 8, 4),
)

# Resulting-height cases store source base area, source height, target base area,
# target container height, and shown full-pour count.
_CONE_TO_CYLINDER_HEIGHT_CASES: Tuple[Tuple[int, int, int, int, int], ...] = (
    (12, 6, 8, 9, 1),
    (9, 9, 9, 10, 2),
    (15, 6, 12, 10, 3),
    (12, 9, 8, 12, 2),
    (18, 5, 12, 12, 2),
    (21, 4, 14, 10, 3),
    (24, 3, 12, 10, 2),
    (15, 4, 10, 8, 1),
)

# Resulting-height cases store source base area, source height, target length,
# target width, target container height, and shown full-pour count.
_CYLINDER_TO_CUBOID_HEIGHT_CASES: Tuple[Tuple[int, int, int, int, int, int], ...] = (
    (6, 5, 5, 4, 8, 2),
    (8, 4, 8, 4, 7, 2),
    (10, 3, 10, 4, 6, 5),
    (9, 4, 9, 5, 7, 5),
    (12, 3, 9, 4, 8, 5),
    (14, 2, 7, 5, 8, 4),
    (8, 5, 10, 5, 9, 3),
)

# Target-capacity cases store source_kind, target_kind, source base area,
# source height, and shown full-pour count. source_kind 0=cone, 1=cylinder;
# target_kind 0=cylinder, 1=cuboid.
_TARGET_CAPACITY_CASES: Tuple[Tuple[int, int, int, int, int], ...] = (
    (0, 0, 12, 6, 2),
    (0, 1, 9, 9, 3),
    (0, 0, 15, 6, 4),
    (0, 1, 12, 9, 2),
    (0, 0, 18, 5, 5),
    (1, 1, 7, 4, 3),
    (1, 0, 8, 5, 4),
    (1, 1, 9, 4, 5),
    (1, 0, 11, 3, 3),
    (1, 1, 12, 4, 4),
)

# Total-volume cases store source_kind, target_kind, source base area,
# source height, and repeated full-pour count. source_kind 0=cone, 1=cylinder;
# target_kind 0=cylinder, 1=cuboid.
_TRANSFERRED_VOLUME_CASES: Tuple[Tuple[int, int, int, int, int], ...] = (
    (0, 0, 12, 6, 4),
    (0, 1, 15, 6, 3),
    (0, 0, 18, 5, 5),
    (0, 1, 21, 4, 6),
    (0, 0, 24, 3, 5),
    (1, 1, 8, 5, 3),
    (1, 0, 9, 4, 5),
    (1, 1, 11, 3, 4),
    (1, 0, 12, 4, 6),
    (1, 1, 14, 3, 5),
)


@dataclass(frozen=True)
class ResolvedProblem:
    objective: str
    query_id: str
    source_shape: str
    target_shape: str
    source_base_area: int
    source_height: int
    source_volume: int
    target_base_area: int
    target_height: int
    target_length: int
    target_width: int
    target_volume: int
    fill_count: int
    pour_count: int
    resulting_height: float
    answer: int | float
    formula_family: str
    formula: str
    query_probabilities: Dict[str, float]
    case_probabilities: Dict[str, float]
    answer_support_probabilities: Dict[str, float]


@dataclass
class RenderContext:
    image: Image.Image
    draw: ImageDraw.ImageDraw
    width: int
    height: int
    line_color: Color
    secondary_color: Color
    label_color: Color
    label_stroke_color: Color
    source_fill: Color
    target_fill: Color
    liquid_fill: Color
    accent_color: Color
    muted_color: Color
    line_width: int
    label_stroke_width: int
    font: Any
    small_font: Any
    diagram_style_meta: Dict[str, Any]
    background_meta: Dict[str, Any]


@dataclass(frozen=True)
class RenderedScene:
    image: Image.Image
    annotation_bboxes: Dict[str, BBox]
    label_bboxes: Dict[str, BBox]
    scene_entities: Tuple[Dict[str, Any], ...]
    render_map: Dict[str, Any]


def _case_probability_map(case_keys: Sequence[str], selected: str) -> Dict[str, float]:
    return {key: (1.0 if key == str(selected) else 0.0) for key in case_keys}


def _cone_source_volume(source_base_area: int, source_height: int) -> int:
    numerator = int(source_base_area) * int(source_height)
    if numerator % 3 != 0:
        raise ValueError("cone source base_area * height must be divisible by 3")
    return int(numerator // 3)


def _cylinder_source_volume(source_base_area: int, source_height: int) -> int:
    return int(source_base_area) * int(source_height)


def _target_cylinder_volume(target_base_area: int, target_height: int) -> int:
    return int(target_base_area) * int(target_height)


def _target_cuboid_volume(target_length: int, target_width: int, target_height: int) -> int:
    return int(target_length) * int(target_width) * int(target_height)


def _cone_case_key(case: Sequence[int]) -> str:
    source_base_area, source_height, target_base_area, target_height = [int(value) for value in case]
    return f"cone_B{source_base_area}_H{source_height}_cyl_B{target_base_area}_H{target_height}"


def _cuboid_case_key(case: Sequence[int]) -> str:
    source_base_area, source_height, target_length, target_width, target_height = [int(value) for value in case]
    return f"cyl_B{source_base_area}_H{source_height}_cuboid_L{target_length}_W{target_width}_H{target_height}"


def _cone_height_case_key(case: Sequence[int]) -> str:
    source_base_area, source_height, target_base_area, target_height, pour_count = [int(value) for value in case]
    return f"cone_B{source_base_area}_H{source_height}_cyl_B{target_base_area}_H{target_height}_n{pour_count}"


def _cuboid_height_case_key(case: Sequence[int]) -> str:
    source_base_area, source_height, target_length, target_width, target_height, pour_count = [int(value) for value in case]
    return (
        f"cyl_B{source_base_area}_H{source_height}_cuboid_"
        f"L{target_length}_W{target_width}_H{target_height}_n{pour_count}"
    )


def _target_capacity_case_key(case: Sequence[int]) -> str:
    source_kind, target_kind, source_base_area, source_height, pour_count = [int(value) for value in case]
    source_prefix = "cone" if source_kind == 0 else "cyl"
    target_prefix = "cyl" if target_kind == 0 else "cuboid"
    return f"{source_prefix}_B{source_base_area}_H{source_height}_{target_prefix}_n{pour_count}"


def _transferred_volume_case_key(case: Sequence[int]) -> str:
    source_kind, target_kind, source_base_area, source_height, pour_count = [int(value) for value in case]
    source_prefix = "cone" if source_kind == 0 else "cyl"
    target_prefix = "cyl" if target_kind == 0 else "cuboid"
    return f"{source_prefix}_B{source_base_area}_H{source_height}_{target_prefix}_total_n{pour_count}"


def _round1(value: float) -> float:
    return round(float(value) + 1e-9, 1)


def json_answer_value(value: int | float) -> int | float:
    number = float(value)
    if abs(number - round(number)) < 1e-9:
        return int(round(number))
    return _round1(number)


def _fmt_number(value: int | float) -> str:
    number = float(value)
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{_round1(number):.1f}"


def _uniform_support(values: Sequence[int | float]) -> Dict[str, float]:
    support = sorted({json_answer_value(value) for value in values})
    probability = 1.0 / float(max(1, len(support)))
    return {str(value): probability for value in support}


def cone_fill_count_support_probabilities() -> Dict[str, float]:
    return _uniform_support(resolve_cone_fill_count_case(case).fill_count for case in _CONE_TO_CYLINDER_CASES)


def cylinder_fill_count_support_probabilities() -> Dict[str, float]:
    return _uniform_support(resolve_cylinder_fill_count_case(case).fill_count for case in _CYLINDER_TO_CUBOID_CASES)


def cone_resulting_height_support_probabilities() -> Dict[str, float]:
    return _uniform_support(resolve_cone_resulting_height_case(case).answer for case in _CONE_TO_CYLINDER_HEIGHT_CASES)


def cylinder_resulting_height_support_probabilities() -> Dict[str, float]:
    return _uniform_support(resolve_cylinder_resulting_height_case(case).answer for case in _CYLINDER_TO_CUBOID_HEIGHT_CASES)


def target_capacity_support_probabilities() -> Dict[str, float]:
    return _uniform_support(resolve_target_capacity_case(case).target_volume for case in _TARGET_CAPACITY_CASES)


def repeated_cone_volume_support_probabilities() -> Dict[str, float]:
    return _uniform_support(resolve_transferred_volume_case(case).answer for case in _TRANSFERRED_VOLUME_CASES if int(case[0]) == 0)


def repeated_cylinder_volume_support_probabilities() -> Dict[str, float]:
    return _uniform_support(resolve_transferred_volume_case(case).answer for case in _TRANSFERRED_VOLUME_CASES if int(case[0]) == 1)


def _select_case_from_pool(
    *,
    cases: Sequence[Sequence[int]],
    keys: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
    namespace: str,
    validator: Any,
    key_fn: Any,
    expected_length: int,
) -> tuple[Tuple[int, ...], Dict[str, float]]:
    explicit = params.get("transfer_case")
    if explicit is not None:
        if not isinstance(explicit, Sequence) or isinstance(explicit, (str, bytes)):
            raise ValueError("transfer_case must be a numeric sequence")
        case = tuple(int(value) for value in explicit)
        if len(case) != int(expected_length):
            raise ValueError(f"transfer_case must have {expected_length} values")
        validator(case)
        selected_key = str(key_fn(case))
        return case, _case_probability_map(tuple(dict.fromkeys(tuple(keys) + (selected_key,))), selected_key)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    case = tuple(int(value) for value in cases[int(index) % len(cases)])
    return case, {str(key): 1.0 / float(max(1, len(keys))) for key in keys}


def select_cone_fill_count_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(_CONE_TO_CYLINDER_CASES)
    keys = tuple(_cone_case_key(case) for case in cases)
    return _select_case_from_pool(cases=cases, keys=keys, params=params, instance_seed=instance_seed, namespace=f"{namespace}.cone_case", validator=_validate_cone_case, key_fn=_cone_case_key, expected_length=4)


def select_cylinder_fill_count_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(_CYLINDER_TO_CUBOID_CASES)
    keys = tuple(_cuboid_case_key(case) for case in cases)
    return _select_case_from_pool(cases=cases, keys=keys, params=params, instance_seed=instance_seed, namespace=f"{namespace}.cuboid_case", validator=_validate_cuboid_case, key_fn=_cuboid_case_key, expected_length=5)


def select_cone_resulting_height_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(_CONE_TO_CYLINDER_HEIGHT_CASES)
    keys = tuple(_cone_height_case_key(case) for case in cases)
    return _select_case_from_pool(cases=cases, keys=keys, params=params, instance_seed=instance_seed, namespace=f"{namespace}.cone_height_case", validator=_validate_cone_height_case, key_fn=_cone_height_case_key, expected_length=5)


def select_cylinder_resulting_height_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(_CYLINDER_TO_CUBOID_HEIGHT_CASES)
    keys = tuple(_cuboid_height_case_key(case) for case in cases)
    return _select_case_from_pool(cases=cases, keys=keys, params=params, instance_seed=instance_seed, namespace=f"{namespace}.cuboid_height_case", validator=_validate_cuboid_height_case, key_fn=_cuboid_height_case_key, expected_length=6)


def select_target_capacity_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(_TARGET_CAPACITY_CASES)
    keys = tuple(_target_capacity_case_key(case) for case in cases)
    return _select_case_from_pool(cases=cases, keys=keys, params=params, instance_seed=instance_seed, namespace=f"{namespace}.target_capacity_case", validator=_validate_target_capacity_case, key_fn=_target_capacity_case_key, expected_length=5)


def _validate_repeated_cone_volume_case(case: Sequence[int]) -> None:
    _validate_transferred_volume_case(case, required_source_kind=0)


def _validate_repeated_cylinder_volume_case(case: Sequence[int]) -> None:
    _validate_transferred_volume_case(case, required_source_kind=1)


def select_repeated_cone_volume_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(case for case in _TRANSFERRED_VOLUME_CASES if int(case[0]) == 0)
    keys = tuple(_transferred_volume_case_key(case) for case in cases)
    return _select_case_from_pool(cases=cases, keys=keys, params=params, instance_seed=instance_seed, namespace=f"{namespace}.transferred_cone_case", validator=_validate_repeated_cone_volume_case, key_fn=_transferred_volume_case_key, expected_length=5)


def select_repeated_cylinder_volume_case(*, instance_seed: int, params: Mapping[str, Any], namespace: str) -> tuple[Tuple[int, ...], Dict[str, float]]:
    cases = tuple(case for case in _TRANSFERRED_VOLUME_CASES if int(case[0]) == 1)
    keys = tuple(_transferred_volume_case_key(case) for case in cases)
    return _select_case_from_pool(cases=cases, keys=keys, params=params, instance_seed=instance_seed, namespace=f"{namespace}.transferred_cylinder_case", validator=_validate_repeated_cylinder_volume_case, key_fn=_transferred_volume_case_key, expected_length=5)


def _validate_fill_count(source_volume: int, target_volume: int) -> int:
    if int(source_volume) <= 0 or int(target_volume) <= 0:
        raise ValueError("source and target volumes must be positive")
    if int(target_volume) % int(source_volume) != 0:
        raise ValueError("target volume must be an exact multiple of source volume")
    fill_count = int(target_volume) // int(source_volume)
    if not (2 <= int(fill_count) <= 8):
        raise ValueError("fill_count must be in the v1 support range 2..8")
    return int(fill_count)


def _validate_cone_case(case: Sequence[int]) -> None:
    source_base_area, source_height, target_base_area, target_height = [int(value) for value in case]
    if min(source_base_area, source_height, target_base_area, target_height) <= 0:
        raise ValueError("container dimensions must be positive")
    source_volume = _cone_source_volume(source_base_area, source_height)
    target_volume = _target_cylinder_volume(target_base_area, target_height)
    _validate_fill_count(source_volume, target_volume)


def _validate_cuboid_case(case: Sequence[int]) -> None:
    source_base_area, source_height, target_length, target_width, target_height = [int(value) for value in case]
    if min(source_base_area, source_height, target_length, target_width, target_height) <= 0:
        raise ValueError("container dimensions must be positive")
    source_volume = _cylinder_source_volume(source_base_area, source_height)
    target_volume = _target_cuboid_volume(target_length, target_width, target_height)
    _validate_fill_count(source_volume, target_volume)


def _validate_resulting_height(source_volume: int, target_base_area: int, target_height: int, pour_count: int) -> float:
    if min(int(source_volume), int(target_base_area), int(target_height), int(pour_count)) <= 0:
        raise ValueError("resulting-height operands must be positive")
    result = float(int(source_volume) * int(pour_count)) / float(int(target_base_area))
    if not (1.5 <= result <= float(target_height) * 0.9):
        raise ValueError("resulting height must be visible and below target capacity")
    return _round1(result)


def _validate_cone_height_case(case: Sequence[int]) -> None:
    source_base_area, source_height, target_base_area, target_height, pour_count = [int(value) for value in case]
    if min(source_base_area, source_height, target_base_area, target_height, pour_count) <= 0:
        raise ValueError("container dimensions and pour count must be positive")
    source_volume = _cone_source_volume(source_base_area, source_height)
    _validate_resulting_height(source_volume, target_base_area, target_height, pour_count)


def _validate_cuboid_height_case(case: Sequence[int]) -> None:
    source_base_area, source_height, target_length, target_width, target_height, pour_count = [int(value) for value in case]
    if min(source_base_area, source_height, target_length, target_width, target_height, pour_count) <= 0:
        raise ValueError("container dimensions and pour count must be positive")
    source_volume = _cylinder_source_volume(source_base_area, source_height)
    target_base_area = int(target_length) * int(target_width)
    _validate_resulting_height(source_volume, target_base_area, target_height, pour_count)


def _validate_target_capacity_case(case: Sequence[int]) -> None:
    source_kind, target_kind, source_base_area, source_height, pour_count = [int(value) for value in case]
    if source_kind not in (0, 1):
        raise ValueError("target-capacity source_kind must be 0 for cone or 1 for cylinder")
    if target_kind not in (0, 1):
        raise ValueError("target-capacity target_kind must be 0 for cylinder or 1 for cuboid")
    if min(source_base_area, source_height, pour_count) <= 0:
        raise ValueError("target-capacity source dimensions and pour count must be positive")
    if source_kind == 0:
        source_volume = _cone_source_volume(source_base_area, source_height)
    else:
        source_volume = _cylinder_source_volume(source_base_area, source_height)
    target_volume = int(source_volume) * int(pour_count)
    if not (40 <= int(target_volume) <= 220):
        raise ValueError("target capacity must be in the v1 support range 40..220")


def _validate_transferred_volume_case(case: Sequence[int], *, required_source_kind: int) -> None:
    source_kind, target_kind, source_base_area, source_height, pour_count = [int(value) for value in case]
    if int(source_kind) != int(required_source_kind):
        raise ValueError("transferred-volume case uses the wrong source kind")
    if source_kind not in (0, 1):
        raise ValueError("transferred-volume source_kind must be 0 for cone or 1 for cylinder")
    if target_kind not in (0, 1):
        raise ValueError("transferred-volume target_kind must be 0 for cylinder or 1 for cuboid")
    if min(source_base_area, source_height, pour_count) <= 0:
        raise ValueError("transferred-volume source dimensions and pour count must be positive")
    source_volume = (
        _cone_source_volume(source_base_area, source_height)
        if source_kind == 0
        else _cylinder_source_volume(source_base_area, source_height)
    )
    total_volume = int(source_volume) * int(pour_count)
    if not (60 <= int(total_volume) <= 320):
        raise ValueError("transferred volume must be in the v1 support range 60..320")


def resolve_cone_fill_count_case(case: Sequence[int]) -> ResolvedProblem:
    _validate_cone_case(case)
    source_base_area, source_height, target_base_area, target_height = [int(value) for value in case]
    source_volume = _cone_source_volume(source_base_area, source_height)
    target_volume = _target_cylinder_volume(target_base_area, target_height)
    fill_count = _validate_fill_count(source_volume, target_volume)
    return ResolvedProblem(
        objective="fill_count",
        query_id=QUERY_ID_CONE_TO_CYLINDER_FILL_COUNT,
        source_shape="cone",
        target_shape="cylinder",
        source_base_area=source_base_area,
        source_height=source_height,
        source_volume=source_volume,
        target_base_area=target_base_area,
        target_height=target_height,
        target_length=0,
        target_width=0,
        target_volume=target_volume,
        fill_count=fill_count,
        pour_count=fill_count,
        resulting_height=float(target_height),
        answer=fill_count,
        formula_family="container_volume_transfer_fill_count",
        formula="fill_count = target_volume / source_volume; cone_volume = base_area*height/3; cylinder_volume = base_area*height",
        query_probabilities={},
        case_probabilities={},
        answer_support_probabilities={},
    )


def resolve_cylinder_fill_count_case(case: Sequence[int]) -> ResolvedProblem:
    _validate_cuboid_case(case)
    source_base_area, source_height, target_length, target_width, target_height = [int(value) for value in case]
    source_volume = _cylinder_source_volume(source_base_area, source_height)
    target_volume = _target_cuboid_volume(target_length, target_width, target_height)
    fill_count = _validate_fill_count(source_volume, target_volume)
    return ResolvedProblem(
        objective="fill_count",
        query_id=QUERY_ID_CYLINDER_TO_CUBOID_FILL_COUNT,
        source_shape="cylinder",
        target_shape="cuboid",
        source_base_area=source_base_area,
        source_height=source_height,
        source_volume=source_volume,
        target_base_area=0,
        target_height=target_height,
        target_length=target_length,
        target_width=target_width,
        target_volume=target_volume,
        fill_count=fill_count,
        pour_count=fill_count,
        resulting_height=float(target_height),
        answer=fill_count,
        formula_family="container_volume_transfer_fill_count",
        formula="fill_count = target_volume / source_volume; cylinder_volume = base_area*height; cuboid_volume = length*width*height",
        query_probabilities={},
        case_probabilities={},
        answer_support_probabilities={},
    )


def resolve_cone_resulting_height_case(case: Sequence[int]) -> ResolvedProblem:
    _validate_cone_height_case(case)
    source_base_area, source_height, target_base_area, target_height, pour_count = [int(value) for value in case]
    source_volume = _cone_source_volume(source_base_area, source_height)
    target_volume = _target_cylinder_volume(target_base_area, target_height)
    resulting_height = _validate_resulting_height(source_volume, target_base_area, target_height, pour_count)
    return ResolvedProblem(
        objective="resulting_height",
        query_id=QUERY_ID_CONE_POURS_TO_CYLINDER_HEIGHT,
        source_shape="cone",
        target_shape="cylinder",
        source_base_area=source_base_area,
        source_height=source_height,
        source_volume=source_volume,
        target_base_area=target_base_area,
        target_height=target_height,
        target_length=0,
        target_width=0,
        target_volume=target_volume,
        fill_count=0,
        pour_count=pour_count,
        resulting_height=float(resulting_height),
        answer=json_answer_value(resulting_height),
        formula_family="container_volume_transfer_resulting_height",
        formula="resulting_height = pour_count * source_volume / target_base_area; cone_volume = base_area*height/3",
        query_probabilities={},
        case_probabilities={},
        answer_support_probabilities={},
    )


def resolve_cylinder_resulting_height_case(case: Sequence[int]) -> ResolvedProblem:
    _validate_cuboid_height_case(case)
    source_base_area, source_height, target_length, target_width, target_height, pour_count = [int(value) for value in case]
    source_volume = _cylinder_source_volume(source_base_area, source_height)
    target_base_area = int(target_length) * int(target_width)
    target_volume = _target_cuboid_volume(target_length, target_width, target_height)
    resulting_height = _validate_resulting_height(source_volume, target_base_area, target_height, pour_count)
    return ResolvedProblem(
        objective="resulting_height",
        query_id=QUERY_ID_CYLINDER_POURS_TO_CUBOID_HEIGHT,
        source_shape="cylinder",
        target_shape="cuboid",
        source_base_area=source_base_area,
        source_height=source_height,
        source_volume=source_volume,
        target_base_area=target_base_area,
        target_height=target_height,
        target_length=target_length,
        target_width=target_width,
        target_volume=target_volume,
        fill_count=0,
        pour_count=pour_count,
        resulting_height=float(resulting_height),
        answer=json_answer_value(resulting_height),
        formula_family="container_volume_transfer_resulting_height",
        formula="resulting_height = pour_count * source_volume / (target_length * target_width); cylinder_volume = base_area*height",
        query_probabilities={},
        case_probabilities={},
        answer_support_probabilities={},
    )


def resolve_target_capacity_case(case: Sequence[int]) -> ResolvedProblem:
    _validate_target_capacity_case(case)
    source_kind, target_kind, source_base_area, source_height, pour_count = [int(value) for value in case]
    source_shape = "cone" if source_kind == 0 else "cylinder"
    target_shape = "cylinder" if target_kind == 0 else "cuboid"
    if source_shape == "cone":
        source_volume = _cone_source_volume(source_base_area, source_height)
    else:
        source_volume = _cylinder_source_volume(source_base_area, source_height)
    target_volume = int(source_volume) * int(pour_count)
    return ResolvedProblem(
        objective="target_capacity",
        query_id=QUERY_ID_TARGET_CAPACITY_FROM_SOURCE_AND_COUNT,
        source_shape=source_shape,
        target_shape=target_shape,
        source_base_area=int(source_base_area),
        source_height=int(source_height),
        source_volume=int(source_volume),
        target_base_area=0,
        target_height=0,
        target_length=0,
        target_width=0,
        target_volume=int(target_volume),
        fill_count=0,
        pour_count=int(pour_count),
        resulting_height=0.0,
        answer=int(target_volume),
        formula_family="container_volume_transfer_target_capacity",
        formula="target_capacity = pour_count * source_volume; source cone volume = base_area*height/3 or source cylinder volume = base_area*height",
        query_probabilities={},
        case_probabilities={},
        answer_support_probabilities={},
    )


def resolve_transferred_volume_case(case: Sequence[int]) -> ResolvedProblem:
    source_kind, target_kind, source_base_area, source_height, pour_count = [int(value) for value in case]
    query_id = (
        QUERY_ID_REPEATED_CONE_POURS_TOTAL_VOLUME
        if int(source_kind) == 0
        else QUERY_ID_REPEATED_CYLINDER_POURS_TOTAL_VOLUME
    )
    _validate_transferred_volume_case(case, required_source_kind=int(source_kind))
    source_shape = "cone" if source_kind == 0 else "cylinder"
    target_shape = "cylinder" if target_kind == 0 else "cuboid"
    if source_shape == "cone":
        source_volume = _cone_source_volume(source_base_area, source_height)
    else:
        source_volume = _cylinder_source_volume(source_base_area, source_height)
    total_volume = int(source_volume) * int(pour_count)
    return ResolvedProblem(
        objective="transferred_volume",
        query_id=query_id,
        source_shape=source_shape,
        target_shape=target_shape,
        source_base_area=int(source_base_area),
        source_height=int(source_height),
        source_volume=int(source_volume),
        target_base_area=0,
        target_height=0,
        target_length=0,
        target_width=0,
        target_volume=int(total_volume),
        fill_count=0,
        pour_count=int(pour_count),
        resulting_height=0.0,
        answer=int(total_volume),
        formula_family="container_volume_transfer_transferred_volume",
        formula="transferred_volume = pour_count * source_volume; source cone volume = base_area*height/3 or source cylinder volume = base_area*height",
        query_probabilities={},
        case_probabilities={},
        answer_support_probabilities={},
    )


def _draw_text_centered(ctx: RenderContext, text: str, center: Point, *, small: bool = False) -> BBox:
    font = ctx.small_font if bool(small) else ctx.font
    bbox = ctx.draw.textbbox((0, 0), str(text), font=font, stroke_width=ctx.label_stroke_width)
    text_w = float(bbox[2] - bbox[0])
    text_h = float(bbox[3] - bbox[1])
    left = float(center[0]) - text_w / 2.0
    top = float(center[1]) - text_h / 2.0
    draw_text_traced(
        ctx.draw,
        (left, top),
        str(text),
        font=font,
        fill=ctx.label_color,
        stroke_width=ctx.label_stroke_width,
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    return pad_bbox((left, top, left + text_w, top + text_h), 4.0, width=ctx.width, height=ctx.height)


def _draw_value_box(ctx: RenderContext, text: str, center: Point) -> BBox:
    font = ctx.font
    bbox = ctx.draw.textbbox((0, 0), str(text), font=font, stroke_width=ctx.label_stroke_width)
    text_w = float(bbox[2] - bbox[0])
    text_h = float(bbox[3] - bbox[1])
    left = float(center[0]) - text_w / 2.0 - 14.0
    top = float(center[1]) - text_h / 2.0 - 8.0
    right = left + text_w + 28.0
    bottom = top + text_h + 16.0
    ctx.draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=7,
        fill=(255, 255, 255),
        outline=ctx.muted_color,
        width=max(1, ctx.line_width - 1),
    )
    draw_text_traced(
        ctx.draw,
        (left + 14.0, top + 8.0),
        str(text),
        font=font,
        fill=ctx.label_color,
        stroke_width=ctx.label_stroke_width,
        stroke_fill=ctx.label_stroke_color,
        role="readout",
        required=False,
    )
    return pad_bbox((left, top, right, bottom), 2.0, width=ctx.width, height=ctx.height)


def _draw_arrow(ctx: RenderContext, start: Point, end: Point) -> BBox:
    ctx.draw.line([start, end], fill=ctx.accent_color, width=max(3, ctx.line_width + 1))
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = max(1e-6, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    head = 18.0
    wing = 8.0
    p1 = (float(end[0]) - ux * head + px * wing, float(end[1]) - uy * head + py * wing)
    p2 = (float(end[0]) - ux * head - px * wing, float(end[1]) - uy * head - py * wing)
    ctx.draw.polygon([end, p1, p2], fill=ctx.accent_color)
    return _bbox_union(
        (
            (float(start[0]), float(start[1]), float(start[0]), float(start[1])),
            (float(end[0]), float(end[1]), float(end[0]), float(end[1])),
            (float(p1[0]), float(p1[1]), float(p1[0]), float(p1[1])),
            (float(p2[0]), float(p2[1]), float(p2[0]), float(p2[1])),
        ),
        width=ctx.width,
        height=ctx.height,
        pad=8.0,
    )


def _draw_cylinder(
    ctx: RenderContext,
    bbox: BBox,
    *,
    fill: Color,
    liquid: bool = True,
    liquid_fraction: float = 0.72,
    mark_fill_line: bool = False,
) -> BBox | None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    ellipse_h = min(42.0, max(24.0, (y1 - y0) * 0.18))
    body_top = y0 + ellipse_h / 2.0
    body_bottom = y1 - ellipse_h / 2.0
    ctx.draw.rectangle((x0, body_top, x1, body_bottom), fill=fill, outline=ctx.line_color, width=ctx.line_width)
    fill_mark_bbox: BBox | None = None
    if liquid:
        fraction = min(0.95, max(0.08, float(liquid_fraction)))
        fill_y = body_bottom - (body_bottom - body_top) * fraction
        ctx.draw.rectangle((x0 + 4.0, fill_y, x1 - 4.0, body_bottom - 2.0), fill=ctx.liquid_fill)
        if mark_fill_line:
            ctx.draw.line((x0 + 2.0, fill_y, x1 - 2.0, fill_y), fill=ctx.accent_color, width=max(3, ctx.line_width + 1))
            fill_mark_bbox = pad_bbox((x0 + 2.0, fill_y - 1.0, x1 - 2.0, fill_y + 1.0), 7.0, width=ctx.width, height=ctx.height)
    ctx.draw.ellipse((x0, y0, x1, y0 + ellipse_h), fill=fill, outline=ctx.line_color, width=ctx.line_width)
    if liquid:
        top_liquid_ellipse = (x0 + 4.0, fill_y - ellipse_h / 2.0, x1 - 4.0, fill_y + ellipse_h / 2.0)
        ctx.draw.arc(top_liquid_ellipse, start=0, end=180, fill=ctx.accent_color if mark_fill_line else ctx.secondary_color, width=max(1, ctx.line_width - 1))
    ctx.draw.arc((x0, y1 - ellipse_h, x1, y1), start=0, end=180, fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.arc((x0, y1 - ellipse_h, x1, y1), start=180, end=360, fill=ctx.secondary_color, width=max(1, ctx.line_width - 1))
    ctx.draw.line((x0, body_top, x0, body_bottom), fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line((x1, body_top, x1, body_bottom), fill=ctx.line_color, width=ctx.line_width)
    return fill_mark_bbox


def _draw_cone(ctx: RenderContext, bbox: BBox) -> None:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    apex = ((x0 + x1) / 2.0, y0)
    base_top = y1 - min(38.0, max(24.0, (y1 - y0) * 0.16))
    ctx.draw.polygon([apex, (x0, base_top), (x1, base_top)], fill=ctx.source_fill, outline=ctx.line_color)
    ctx.draw.line([apex, (x0, base_top)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.line([apex, (x1, base_top)], fill=ctx.line_color, width=ctx.line_width)
    ctx.draw.ellipse((x0, base_top - 14.0, x1, y1), fill=ctx.source_fill, outline=ctx.line_color, width=ctx.line_width)
    ctx.draw.arc((x0, base_top - 14.0, x1, y1), start=180, end=360, fill=ctx.secondary_color, width=max(1, ctx.line_width - 1))


def _draw_cuboid_tank(
    ctx: RenderContext,
    bbox: BBox,
    *,
    liquid_fraction: float = 0.72,
    mark_fill_line: bool = False,
) -> tuple[BBox, BBox | None]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    depth = min(48.0, max(28.0, (x1 - x0) * 0.18))
    top_shift = (depth, -depth * 0.55)
    front = (x0, y0 + depth * 0.45, x1 - depth, y1)
    back = (front[0] + top_shift[0], front[1] + top_shift[1], front[2] + top_shift[0], front[3] + top_shift[1])
    ctx.draw.polygon(
        [(back[0], back[1]), (back[2], back[1]), (front[2], front[1]), (front[0], front[1])],
        fill=ctx.target_fill,
        outline=ctx.line_color,
    )
    ctx.draw.polygon(
        [(front[2], front[1]), (back[2], back[1]), (back[2], back[3]), (front[2], front[3])],
        fill=ctx.target_fill,
        outline=ctx.line_color,
    )
    ctx.draw.rectangle(front, fill=ctx.target_fill, outline=ctx.line_color, width=ctx.line_width)
    fraction = min(0.95, max(0.08, float(liquid_fraction)))
    fill_y = front[3] - (front[3] - front[1]) * fraction
    ctx.draw.rectangle((front[0] + 8.0, fill_y, front[2] - 8.0, front[3] - 6.0), fill=ctx.liquid_fill, outline=None)
    fill_mark_bbox: BBox | None = None
    if mark_fill_line:
        ctx.draw.line((front[0] + 6.0, fill_y, front[2] - 6.0, fill_y), fill=ctx.accent_color, width=max(3, ctx.line_width + 1))
        fill_mark_bbox = pad_bbox((front[0] + 6.0, fill_y - 1.0, front[2] - 6.0, fill_y + 1.0), 7.0, width=ctx.width, height=ctx.height)
    ctx.draw.rectangle(front, outline=ctx.line_color, width=ctx.line_width)
    return pad_bbox((x0, y0, x1, y1), 4.0, width=ctx.width, height=ctx.height), fill_mark_bbox


def create_render_context(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    render_defaults: Mapping[str, Any],
    random_namespace: str,
) -> tuple[RenderContext, Dict[str, Any]]:
    width = int(params.get("canvas_width", group_default(render_defaults, "canvas_width", 820)))
    height = int(params.get("canvas_height", group_default(render_defaults, "canvas_height", 600)))
    image, background_meta, diagram_style, diagram_style_meta = prepare_geometry_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id="container_volume_transfer",
        canvas_width=int(width),
        canvas_height=int(height),
        require_grid=False,
    )
    fill_palettes: Tuple[Tuple[Color, Color, Color, Color], ...] = (
        ((236, 245, 255), (238, 246, 236), (201, 231, 255), (41, 122, 184)),
        ((255, 241, 230), (237, 241, 255), (218, 236, 255), (177, 93, 48)),
        ((239, 235, 255), (235, 248, 246), (220, 239, 249), (111, 92, 190)),
        ((232, 248, 237), (255, 241, 222), (214, 237, 229), (38, 137, 95)),
    )
    palette_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{random_namespace}.palette",
    )
    source_fill, target_fill, liquid_fill, accent_color = fill_palettes[int(palette_index) % len(fill_palettes)]
    font_size = int(params.get("label_font_size", group_default(render_defaults, "label_font_size", 22)))
    small_font_size = int(params.get("small_label_font_size", group_default(render_defaults, "small_label_font_size", 18)))
    line_width = int(params.get("line_width", group_default(render_defaults, "line_width", 3)))
    return RenderContext(
        image=image,
        draw=ImageDraw.Draw(image),
        width=int(width),
        height=int(height),
        line_color=tuple(int(value) for value in diagram_style.stroke_rgb),
        secondary_color=tuple(int(value) for value in diagram_style.secondary_stroke_rgb),
        label_color=tuple(int(value) for value in diagram_style.label_rgb),
        label_stroke_color=tuple(int(value) for value in diagram_style.label_stroke_rgb),
        source_fill=source_fill,
        target_fill=target_fill,
        liquid_fill=liquid_fill,
        accent_color=accent_color,
        muted_color=tuple(int(value) for value in diagram_style.panel_border_rgb),
        line_width=max(2, int(line_width)),
        label_stroke_width=max(1, int(diagram_style.label_stroke_width_px)),
        font=load_font(max(12, int(font_size)), bold=True),
        small_font=load_font(max(10, int(small_font_size)), bold=True),
        diagram_style_meta=dict(diagram_style_meta),
        background_meta=dict(background_meta),
    ), {
        "technical_diagram": dict(diagram_style_meta),
        "background": dict(background_meta),
    }


def _assert_bboxes_inside(bboxes: Sequence[BBox], *, width: int, height: int) -> None:
    for bbox in bboxes:
        x0, y0, x1, y1 = [float(value) for value in bbox]
        if x0 <= 2.0 or y0 <= 2.0 or x1 >= float(width) - 2.0 or y1 >= float(height) - 2.0:
            raise ValueError("container-volume-transfer label too close to canvas edge")


def render_container_volume_transfer_scene(ctx: RenderContext, problem: ResolvedProblem, *, instance_seed: int) -> RenderedScene:
    rng = spawn_rng(int(instance_seed), f"geometry.container_volume_transfer.{problem.objective}.render.scene")
    is_resulting_height = str(problem.objective) == "resulting_height"
    is_target_capacity = str(problem.objective) == "target_capacity"
    is_transferred_volume = str(problem.objective) == "transferred_volume"
    source_center_x = 215.0 + float(rng.uniform(-14.0, 14.0))
    target_center_x = 595.0 + float(rng.uniform(-14.0, 14.0))
    base_y = 420.0 + float(rng.uniform(-8.0, 10.0))
    source_bbox = (
        source_center_x - 70.0,
        base_y - 230.0,
        source_center_x + 70.0,
        base_y,
    )
    target_bbox = (
        target_center_x - 90.0,
        base_y - 245.0,
        target_center_x + 90.0,
        base_y + 6.0,
    )
    panel_bbox = (
        min(source_bbox[0], target_bbox[0]) - 32.0,
        min(source_bbox[1], target_bbox[1]) - 42.0,
        max(source_bbox[2], target_bbox[2]) + 32.0,
        max(source_bbox[3], target_bbox[3]) + 64.0,
    )
    ctx.draw.rounded_rectangle(
        panel_bbox,
        radius=10,
        fill=(255, 255, 255),
        outline=ctx.muted_color,
        width=max(1, ctx.line_width - 1),
    )
    if problem.source_shape == "cone":
        _draw_cone(ctx, source_bbox)
    else:
        _draw_cylinder(ctx, source_bbox, fill=ctx.source_fill, liquid_fraction=0.78)
    target_fill_fraction = (
        float(problem.resulting_height) / float(problem.target_height)
        if is_resulting_height
        else 0.82
    )
    fill_mark_bbox: BBox | None = None
    if problem.target_shape == "cylinder":
        fill_mark_bbox = _draw_cylinder(
            ctx,
            target_bbox,
            fill=ctx.target_fill,
            liquid_fraction=target_fill_fraction,
            mark_fill_line=is_resulting_height,
        )
    else:
        target_bbox, fill_mark_bbox = _draw_cuboid_tank(
            ctx,
            target_bbox,
            liquid_fraction=target_fill_fraction,
            mark_fill_line=is_resulting_height,
        )

    label_bboxes: Dict[str, BBox] = {}
    label_bboxes["source_title"] = _draw_text_centered(ctx, f"source {problem.source_shape}", (source_center_x, source_bbox[1] - 26.0), small=True)
    label_bboxes["target_title"] = _draw_text_centered(ctx, f"target {problem.target_shape}", (target_center_x, target_bbox[1] - 26.0), small=True)
    label_bboxes["source_base_area"] = _draw_text_centered(ctx, f"base area {problem.source_base_area}", (source_center_x, source_bbox[3] + 26.0), small=True)
    label_bboxes["source_height"] = _draw_text_centered(ctx, f"height {problem.source_height}", (source_bbox[0] - 52.0, (source_bbox[1] + source_bbox[3]) / 2.0), small=True)
    if problem.target_shape == "cylinder":
        if not is_target_capacity:
            label_bboxes["target_base_area"] = _draw_text_centered(ctx, f"base area {problem.target_base_area}", (target_center_x, target_bbox[3] + 26.0), small=True)
        if not is_resulting_height and not is_target_capacity:
            label_bboxes["target_height"] = _draw_text_centered(
                ctx,
                f"height {problem.target_height}",
                (target_bbox[2] + 54.0, (target_bbox[1] + target_bbox[3]) / 2.0),
                small=True,
            )
    else:
        if not is_target_capacity:
            label_bboxes["target_length"] = _draw_text_centered(ctx, f"L {problem.target_length}", (target_center_x, target_bbox[3] + 28.0), small=True)
            label_bboxes["target_width"] = _draw_text_centered(ctx, f"W {problem.target_width}", (target_bbox[2] + 44.0, target_bbox[1] + 58.0), small=True)
        if not is_resulting_height and not is_target_capacity:
            label_bboxes["target_height"] = _draw_text_centered(
                ctx,
                f"H {problem.target_height}",
                (target_bbox[2] + 46.0, (target_bbox[1] + target_bbox[3]) / 2.0 + 18.0),
                small=True,
            )
    if is_resulting_height:
        label_bboxes["transfer_count"] = _draw_value_box(
            ctx,
            f"{problem.pour_count} full pours",
            (ctx.width / 2.0, 78.0 + float(rng.uniform(-4.0, 5.0))),
        )
        if fill_mark_bbox is None:
            raise ValueError("resulting-height task requires a visible fill mark")
        label_bboxes["fill_mark_label"] = _draw_text_centered(
            ctx,
            "height ?",
            (target_bbox[2] + 54.0, (fill_mark_bbox[1] + fill_mark_bbox[3]) / 2.0),
            small=True,
        )
        fill_mark_bbox = _bbox_union((fill_mark_bbox, label_bboxes["fill_mark_label"]), width=ctx.width, height=ctx.height, pad=5.0)
    elif is_target_capacity or is_transferred_volume:
        label_bboxes["transfer_count"] = _draw_value_box(
            ctx,
            f"{problem.pour_count} full pours",
            (ctx.width / 2.0, 78.0 + float(rng.uniform(-4.0, 5.0))),
        )
        question_text = "total volume ?" if is_transferred_volume else "capacity ?"
        label_bboxes["target_capacity_question"] = _draw_text_centered(
            ctx,
            question_text,
            (target_center_x, target_bbox[3] + 28.0),
            small=True,
        )
    else:
        label_bboxes["question"] = _draw_value_box(ctx, "full pours ?", (ctx.width / 2.0, 78.0 + float(rng.uniform(-4.0, 5.0))))
    arrow_bbox = _draw_arrow(
        ctx,
        (source_bbox[2] + 26.0, (source_bbox[1] + source_bbox[3]) / 2.0 - 8.0),
        (target_bbox[0] - 26.0, (target_bbox[1] + target_bbox[3]) / 2.0 - 8.0),
    )
    source_dimension_region = _bbox_union(
        (label_bboxes["source_base_area"], label_bboxes["source_height"]),
        width=ctx.width,
        height=ctx.height,
        pad=6.0,
    )
    if is_resulting_height:
        target_dimension_keys = ("target_base_area",) if problem.target_shape == "cylinder" else ("target_length", "target_width")
    elif is_target_capacity:
        target_dimension_keys = ()
    else:
        target_dimension_keys = (
            ("target_base_area", "target_height")
            if problem.target_shape == "cylinder"
            else ("target_length", "target_width", "target_height")
        )
    target_dimension_region = (
        _bbox_union(
            tuple(label_bboxes[key] for key in target_dimension_keys),
            width=ctx.width,
            height=ctx.height,
            pad=6.0,
        )
        if target_dimension_keys
        else None
    )
    annotation_bboxes = {
        "source_container_bbox": pad_bbox(source_bbox, 5.0, width=ctx.width, height=ctx.height),
        "target_container_bbox": pad_bbox(target_bbox, 5.0, width=ctx.width, height=ctx.height),
        "source_dimension_region_bbox": source_dimension_region,
    }
    if is_resulting_height:
        annotation_bboxes.update(
            {
                "target_base_dimension_region_bbox": target_dimension_region if target_dimension_region is not None else source_dimension_region,
                "transfer_count_bbox": label_bboxes["transfer_count"],
                "fill_mark_bbox": fill_mark_bbox if fill_mark_bbox is not None else target_dimension_region,
            }
        )
    elif is_target_capacity or is_transferred_volume:
        annotation_bboxes.update(
            {
                "transfer_count_bbox": label_bboxes["transfer_count"],
                "transfer_arrow_bbox": arrow_bbox,
            }
        )
    else:
        annotation_bboxes.update(
            {
                "target_dimension_region_bbox": target_dimension_region if target_dimension_region is not None else source_dimension_region,
                "transfer_arrow_bbox": arrow_bbox,
            }
        )
    _assert_bboxes_inside(tuple(annotation_bboxes.values()) + tuple(label_bboxes.values()), width=ctx.width, height=ctx.height)
    scene_entities = (
        {
            "entity_id": "source_container",
            "entity_type": str(problem.source_shape),
            "base_area_units": int(problem.source_base_area),
            "height_units": int(problem.source_height),
            "volume_units": int(problem.source_volume),
            "bbox": bbox_to_list(annotation_bboxes["source_container_bbox"]),
        },
        {
            "entity_id": "target_container",
            "entity_type": str(problem.target_shape),
            "base_area_units": int(problem.target_base_area),
            "length_units": int(problem.target_length),
            "width_units": int(problem.target_width),
            "height_units": int(problem.target_height),
            "volume_units": int(problem.target_volume),
            "resulting_height_units": float(problem.resulting_height),
            "pour_count": int(problem.pour_count),
            "bbox": bbox_to_list(annotation_bboxes["target_container_bbox"]),
        },
    )
    render_map = {
        "coord_space": "pixel",
        "query_id": str(problem.query_id),
        "source_shape": str(problem.source_shape),
        "target_shape": str(problem.target_shape),
        "source_container_bbox": bbox_to_list(annotation_bboxes["source_container_bbox"]),
        "target_container_bbox": bbox_to_list(annotation_bboxes["target_container_bbox"]),
        "annotation_bboxes": {key: bbox_to_list(value) for key, value in annotation_bboxes.items()},
        "label_bboxes": {key: bbox_to_list(value) for key, value in label_bboxes.items()},
        "pour_count": int(problem.pour_count),
        "resulting_height_units": float(problem.resulting_height),
    }
    return RenderedScene(
        image=ctx.image,
        annotation_bboxes=annotation_bboxes,
        label_bboxes=label_bboxes,
        scene_entities=scene_entities,
        render_map=render_map,
    )


def _example_bbox_for_key(key: str) -> list[int]:
    examples = {
        "source_container_bbox": [145, 190, 285, 420],
        "target_container_bbox": [505, 180, 685, 426],
        "source_dimension_region_bbox": [75, 246, 286, 458],
        "target_dimension_region_bbox": [505, 338, 758, 432],
        "target_base_dimension_region_bbox": [505, 338, 706, 432],
        "transfer_arrow_bbox": [305, 286, 485, 322],
        "transfer_count_bbox": [350, 50, 470, 105],
        "fill_mark_bbox": [505, 245, 746, 285],
    }
    return list(examples[str(key)])


def make_prompt_examples(answer: int | float, annotation_keys: Sequence[str]) -> tuple[str, str]:
    answer_value = json_answer_value(answer)
    annotation = {str(key): _example_bbox_for_key(str(key)) for key in annotation_keys}
    return dump_prompt_json_examples(annotation=annotation, answer=answer_value)
