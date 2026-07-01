"""Neutral spinner probability sampling and probability helpers."""

from __future__ import annotations

from math import gcd
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

from .....core.seed import spawn_rng
from .....core.sampling import uniform_choice
from ...shared.common import get_int_param as _get_int
from ...shared.common import get_int_range as _get_range


COLOR_PALETTE: Tuple[Tuple[str, Tuple[int, int, int]], ...] = (
    ("red", (213, 76, 76)),
    ("blue", (58, 112, 194)),
    ("green", (55, 151, 103)),
    ("yellow", (232, 184, 57)),
    ("purple", (139, 101, 201)),
    ("orange", (220, 126, 58)),
    ("teal", (42, 154, 166)),
    ("pink", (207, 88, 143)),
)
SHAPE_POOL: Tuple[str, ...] = ("circle", "triangle", "square", "diamond", "star")


def format_fraction(numerator: int, denominator: int) -> str:
    """Return one reduced probability fraction."""

    if int(denominator) <= 0:
        raise ValueError("probability denominator must be positive")
    common = gcd(abs(int(numerator)), abs(int(denominator)))
    return f"{int(numerator) // common}/{int(denominator) // common}"


def normalize_int_with_bounds(value: int, bounds: Sequence[int]) -> float:
    """Normalize an integer within inclusive calibration bounds."""

    low = int(bounds[0])
    high = int(bounds[1])
    if int(high) <= int(low):
        return 0.0
    return max(0.0, min(1.0, (float(value) - float(low)) / float(high - low)))


def valid_favorable_count(count: int, total: int, *, min_count: int, max_count: int) -> bool:
    """Check that an event is nontrivial and within configured support."""

    return int(min_count) <= int(count) <= min(int(total) - 1, int(max_count))


def color_names(sectors: Sequence[Mapping[str, Any]]) -> List[str]:
    """Return sorted color names present in spinner sectors."""

    return sorted({str(sector["color_name"]) for sector in sectors})


def shape_names(sectors: Sequence[Mapping[str, Any]]) -> List[str]:
    """Return sorted marker-shape names present in spinner sectors."""

    return sorted({str(sector["shape"]) for sector in sectors})


def configured_single_count_limits(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    *,
    total: int,
) -> tuple[int, int]:
    """Resolve the single-spinner favorable-count range."""

    min_count = _get_int(params, gen_defaults, "single_favorable_count_min", 2)
    max_count = _get_int(params, gen_defaults, "single_favorable_count_max", max(2, int(total) - 2))
    return int(min_count), int(max_count)


def color_shape_event_candidates(
    *,
    sectors: Sequence[Mapping[str, Any]],
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    operator: str,
) -> List[Dict[str, Any]]:
    """Return candidates for one color/shape conjunction or disjunction event."""

    total = len(sectors)
    min_count, max_count = configured_single_count_limits(params, gen_defaults, total=int(total))
    candidates: List[Dict[str, Any]] = []
    operator_text = str(operator)
    if operator_text not in {"and", "or"}:
        raise ValueError(f"unsupported color/shape spinner operator: {operator}")
    for color in color_names(sectors):
        for shape in shape_names(sectors):
            if operator_text == "and":
                favorable = [
                    str(sector["sector_id"])
                    for sector in sectors
                    if str(sector["color_name"]) == str(color) and str(sector["shape"]) == str(shape)
                ]
            else:
                favorable = [
                    str(sector["sector_id"])
                    for sector in sectors
                    if str(sector["color_name"]) == str(color) or str(sector["shape"]) == str(shape)
                ]
            if valid_favorable_count(len(favorable), total, min_count=min_count, max_count=max_count):
                candidates.append(
                    {
                        "event_description": f"{color} {operator_text} marked with a {shape}",
                        "target_color": str(color),
                        "target_shape": str(shape),
                        "favorable_sector_ids": list(favorable),
                    }
                )
    return candidates


def sample_spinner_sectors(
    *,
    spinner_id: str,
    sector_count: int,
    rng,
    color_pool_size: int,
    number_min: int,
    number_max: int,
    show_number: bool = True,
    show_shape: bool = True,
) -> List[Dict[str, Any]]:
    """Sample visible sector records for one equal-sector spinner."""

    color_pool = list(COLOR_PALETTE[: max(3, min(len(COLOR_PALETTE), int(color_pool_size)))])
    sectors: List[Dict[str, Any]] = []
    for index in range(int(sector_count)):
        color_name, color_rgb = uniform_choice(rng, tuple(color_pool), sort_keys=False)
        shape = str(uniform_choice(rng, SHAPE_POOL, sort_keys=False))
        number = int(rng.randint(int(number_min), int(number_max)))
        sectors.append(
            {
                "sector_id": f"{spinner_id}_sector_{index}",
                "spinner_id": str(spinner_id),
                "sector_index": int(index),
                "color_name": str(color_name),
                "color_rgb": [int(value) for value in color_rgb],
                "shape": str(shape),
                "number": int(number),
                "show_number": bool(show_number),
                "show_shape": bool(show_shape),
            }
        )
    return sectors


def select_event_candidate(
    candidates: Sequence[Mapping[str, Any]],
    *,
    rng,
    favorable_key: str,
    total_outcome_count: int,
) -> Dict[str, Any]:
    """Choose one event candidate and bind reduced probability fields."""

    if not candidates:
        raise RuntimeError("failed to choose a nontrivial spinner probability event")
    shuffled = [dict(candidate) for candidate in candidates]
    rng.shuffle(shuffled)
    selected = dict(shuffled[0])
    favorable_count = len(selected[str(favorable_key)])
    selected["favorable_outcome_count"] = int(favorable_count)
    selected["total_outcome_count"] = int(total_outcome_count)
    selected["answer_value"] = format_fraction(int(favorable_count), int(total_outcome_count))
    return selected


def build_single_spinner_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    rng_namespace: str,
    event_builder: Callable[..., Mapping[str, Any]],
) -> Dict[str, Any]:
    """Build a single-spinner dataset using a task-owned event builder."""

    rng = spawn_rng(int(instance_seed), str(rng_namespace))
    sector_min, sector_max = _get_range(
        params,
        gen_defaults,
        min_key="single_sector_count_min",
        max_key="single_sector_count_max",
        fallback_min=6,
        fallback_max=10,
    )
    color_pool_size = _get_int(params, gen_defaults, "single_color_pool_size", 6)
    number_min, number_max = _get_range(
        params,
        gen_defaults,
        min_key="number_min",
        max_key="number_max",
        fallback_min=1,
        fallback_max=12,
    )
    for _attempt in range(300):
        sector_count = int(params.get("single_sector_count", rng.randint(int(sector_min), int(sector_max))))
        sectors = sample_spinner_sectors(
            spinner_id="spinner",
            sector_count=int(sector_count),
            rng=rng,
            color_pool_size=int(color_pool_size),
            number_min=int(number_min),
            number_max=int(number_max),
            show_number=False,
            show_shape=True,
        )
        try:
            event = dict(
                event_builder(
                    sectors=sectors,
                    params=params,
                    gen_defaults=gen_defaults,
                    rng=rng,
                )
            )
        except RuntimeError:
            continue
        return {
            "mode": "single",
            "spinner_specs": [{"spinner_id": "spinner", "title": "Spinner", "sectors": sectors}],
            "sector_count": int(sector_count),
            "sector_count_range": [int(sector_min), int(sector_max)],
            "event": event,
            "answer_value": str(event["answer_value"]),
            "calculation_supporting_item_ids": list(event["favorable_sector_ids"]),
            "annotation_item_ids": ["spinner_panel"],
        }
    raise RuntimeError("failed to build single-spinner probability dataset")


def build_pair_spinner_dataset(
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    rng_namespace: str,
    event_builder: Callable[..., Mapping[str, Any]],
) -> Dict[str, Any]:
    """Build a two-spinner dataset using a task-owned event builder."""

    rng = spawn_rng(int(instance_seed), str(rng_namespace))
    sector_min, sector_max = _get_range(
        params,
        gen_defaults,
        min_key="pair_sector_count_min",
        max_key="pair_sector_count_max",
        fallback_min=4,
        fallback_max=6,
    )
    color_pool_size = _get_int(params, gen_defaults, "pair_color_pool_size", 5)
    number_min, number_max = _get_range(
        params,
        gen_defaults,
        min_key="number_min",
        max_key="number_max",
        fallback_min=1,
        fallback_max=12,
    )
    for _attempt in range(500):
        count_a = int(params.get("pair_sector_count_a", rng.randint(int(sector_min), int(sector_max))))
        count_b = int(params.get("pair_sector_count_b", rng.randint(int(sector_min), int(sector_max))))
        sectors_a = sample_spinner_sectors(
            spinner_id="spinner_a",
            sector_count=int(count_a),
            rng=rng,
            color_pool_size=int(color_pool_size),
            number_min=int(number_min),
            number_max=int(number_max),
            show_number=False,
            show_shape=False,
        )
        sectors_b = sample_spinner_sectors(
            spinner_id="spinner_b",
            sector_count=int(count_b),
            rng=rng,
            color_pool_size=int(color_pool_size),
            number_min=int(number_min),
            number_max=int(number_max),
            show_number=False,
            show_shape=False,
        )
        try:
            event = dict(
                event_builder(
                    sectors_a=sectors_a,
                    sectors_b=sectors_b,
                    params=params,
                    gen_defaults=gen_defaults,
                    rng=rng,
                )
            )
        except RuntimeError:
            continue
        return {
            "mode": "pair",
            "spinner_specs": [
                {"spinner_id": "spinner_a", "title": "Spinner A", "sectors": sectors_a},
                {"spinner_id": "spinner_b", "title": "Spinner B", "sectors": sectors_b},
            ],
            "sector_count_a": int(count_a),
            "sector_count_b": int(count_b),
            "sector_count_range": [int(sector_min), int(sector_max)],
            "event": event,
            "answer_value": str(event["answer_value"]),
            "calculation_supporting_item_ids": list(event["supporting_sector_ids"]),
            "annotation_item_ids": ["spinner_a_panel", "spinner_b_panel"],
        }
    raise RuntimeError("failed to build pair-spinner probability dataset")


__all__ = [
    "COLOR_PALETTE",
    "SHAPE_POOL",
    "build_pair_spinner_dataset",
    "build_single_spinner_dataset",
    "color_names",
    "color_shape_event_candidates",
    "configured_single_count_limits",
    "format_fraction",
    "normalize_int_with_bounds",
    "select_event_candidate",
    "shape_names",
    "valid_favorable_count",
]
