"""Shared dataset builders and render defaults for topology bead-loop puzzles."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any, Dict, List, Mapping, MutableSequence, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.color_distance import color_distance
from ...shared.config_defaults import group_default
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.render_variation import resolve_render_int, resolve_render_rgb
from .common import resolve_puzzle_axis_variant
from .symbol_rendering import PUZZLE_OBJECT_TYPES


SUPPORTED_PUZZLE_CYCLIC_ORDER_SCENE_VARIANTS: Tuple[str, ...] = (
    "necklace_board",
    "charm_card_grid",
    "route_loop_diagram",
    "token_ring_outline",
)
SOURCE_PUZZLE_BEAD_LOOP_SCENE_VARIANT_MAP = {
    "loop_strip": "necklace_board",
    "loop_card": "charm_card_grid",
    "loop_outline": "token_ring_outline",
}
SUPPORTED_PUZZLE_BEAD_LOOP_SCENE_VARIANTS: Tuple[str, ...] = SUPPORTED_PUZZLE_CYCLIC_ORDER_SCENE_VARIANTS
SUPPORTED_PUZZLE_BEAD_LOOP_QUERY_VARIANTS: Tuple[str, ...] = (
    "cyclic_order_equivalent_label",
)
SUPPORTED_PUZZLE_CYCLIC_ORDER_TOKEN_RENDER_STYLES: Tuple[str, ...] = (
    "colored_beads",
    "shape_tokens",
    "colored_shape_tokens",
    "outline_shape_tokens",
    "symbol_badges",
)
SOURCE_PUZZLE_BEAD_TOKEN_MODE_MAP = {
    "color": "colored_beads",
    "shape": "shape_tokens",
    "mixed": "colored_shape_tokens",
}
TOKEN_RENDER_STYLE_SOURCE_MODE = {
    "colored_beads": "color",
    "shape_tokens": "shape",
    "colored_shape_tokens": "mixed",
    "outline_shape_tokens": "shape",
    "symbol_badges": "mixed",
}
SUPPORTED_PUZZLE_BEAD_TOKEN_MODES: Tuple[str, ...] = SUPPORTED_PUZZLE_CYCLIC_ORDER_TOKEN_RENDER_STYLES
SUPPORTED_PUZZLE_LOOP_PATH_STYLES: Tuple[str, ...] = (
    "ellipse",
    "rounded_rect",
    "polygon_loop",
    "wavy_loop",
    "beaded_string",
)
BEAD_COLOR_SPECS: Tuple[Tuple[str, Tuple[int, int, int]], ...] = (
    ("sky", (64, 175, 225)),
    ("forest", (46, 95, 60)),
    ("violet", (83, 54, 154)),
    ("lime", (185, 225, 30)),
    ("sand", (208, 144, 98)),
    ("magenta", (205, 85, 138)),
    ("mint", (86, 225, 142)),
    ("crimson", (222, 42, 33)),
)
LOOP_SHAPE_VARIANTS: Tuple[str, ...] = (
    "circle",
    "wide",
    "tall",
)
LOOP_START_ANGLES_DEG: Tuple[int, ...] = (-90, -45, 0, 45, 90, 135, 180)
BEAD_COLOR_DISTANCE_SPACE = "lab"
BEAD_COLOR_MIN_DISTANCE = 50.0


def _resolve_int_param(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    key: str,
    fallback: int,
) -> int:
    """Resolve one integer generation or rendering parameter."""

    return int(params.get(str(key), group_default(defaults, str(key), int(fallback))))


def _variant_param(
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    *,
    query_variant: str,
    key: str,
    fallback: Any,
) -> Any:
    """Resolve one generation value with optional query-variant-specific defaults."""

    if str(key) in params:
        return params.get(str(key))

    for source in (
        params.get("query_variant_overrides"),
        group_default(gen_defaults, "query_variant_overrides", {}),
    ):
        if not isinstance(source, Mapping):
            continue
        variant_defaults = source.get(str(query_variant), {})
        if isinstance(variant_defaults, Mapping) and str(key) in variant_defaults:
            return variant_defaults.get(str(key))

    return group_default(gen_defaults, str(key), fallback)


@dataclass(frozen=True)
class PuzzleBeadLoopDefaults:
    """Default generation bounds for topology bead-loop puzzles."""

    option_count_min: int = 6
    option_count_max: int = 7
    valid_option_count_min: int = 1
    valid_option_count_max: int = 5
    bead_count_min: int = 4
    bead_count_max: int = 6
    shape_bead_count_max: int = 6
    min_color_distance: float = 50.0
    color_distance_space: str = "lab"


@dataclass(frozen=True)
class PuzzleBeadLoopRenderParams:
    """Resolved rendering params for topology bead-loop scenes."""

    canvas_width: int
    canvas_height: int
    scene_margin_left_px: int
    scene_margin_right_px: int
    scene_margin_top_px: int
    scene_margin_bottom_px: int
    reference_panel_height_px: int
    reference_panel_padding_px: int
    reference_loop_width_px: int
    reference_loop_height_px: int
    reference_label_font_size_px: int
    reference_to_options_gap_px: int
    option_image_width_px: int
    option_image_height_px: int
    option_gap_px: int
    option_row_gap_px: int
    option_label_gap_px: int
    option_label_font_size_px: int
    panel_corner_radius_px: int
    border_width_px: int
    loop_stroke_width_px: int
    bead_size_px: int
    shape_bead_inset_px: int
    panel_fill_rgb: Tuple[int, int, int]
    instruction_fill_rgb: Tuple[int, int, int]
    border_color_rgb: Tuple[int, int, int]
    loop_color_rgb: Tuple[int, int, int]
    text_color_rgb: Tuple[int, int, int]
    text_stroke_rgb: Tuple[int, int, int]
    shape_fill_rgb: Tuple[int, int, int]


def resolve_bead_loop_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the topology cyclic-order scene variant."""

    explicit = params.get("scene_variant")
    if explicit is not None and str(explicit) in SOURCE_PUZZLE_BEAD_LOOP_SCENE_VARIANT_MAP:
        selected = str(SOURCE_PUZZLE_BEAD_LOOP_SCENE_VARIANT_MAP[str(explicit)])
        return selected, {
            value: (1.0 if str(value) == selected else 0.0)
            for value in SUPPORTED_PUZZLE_CYCLIC_ORDER_SCENE_VARIANTS
        }
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_CYCLIC_ORDER_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_bead_loop_query_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the topology bead-loop semantic variant."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_BEAD_LOOP_QUERY_VARIANTS,
        task_id=str(task_id),
        explicit_key="query_variant",
        weights_key="query_variant_weights",
        balance_flag_key="balanced_query_variant_sampling",
        axis_namespace="query_variant",
    )


def resolve_cyclic_order_token_render_style(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the non-semantic token-rendering style."""

    explicit_style = params.get("token_render_style")
    if explicit_style is None:
        source_mode = params.get("bead_token_mode")
        if source_mode is not None:
            selected = str(SOURCE_PUZZLE_BEAD_TOKEN_MODE_MAP.get(str(source_mode), str(source_mode)))
            if selected not in set(SUPPORTED_PUZZLE_CYCLIC_ORDER_TOKEN_RENDER_STYLES):
                raise ValueError(f"unsupported bead_token_mode: {source_mode}")
            return selected, {
                value: (1.0 if str(value) == selected else 0.0)
                for value in SUPPORTED_PUZZLE_CYCLIC_ORDER_TOKEN_RENDER_STYLES
            }
    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_CYCLIC_ORDER_TOKEN_RENDER_STYLES,
        task_id=str(task_id),
        explicit_key="token_render_style",
        weights_key="token_render_style_weights",
        balance_flag_key="balanced_token_render_style_sampling",
        axis_namespace="token_render_style",
    )


def resolve_bead_loop_token_mode(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Backward-compatible alias for token-rendering style resolution."""

    return resolve_cyclic_order_token_render_style(
        params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        task_id=str(task_id),
    )


def resolve_cyclic_order_path_style(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the closed-loop path shape used by all reference/option loops."""

    return resolve_puzzle_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_PUZZLE_LOOP_PATH_STYLES,
        task_id=str(task_id),
        explicit_key="loop_path_style",
        weights_key="loop_path_style_weights",
        balance_flag_key="balanced_loop_path_style_sampling",
        axis_namespace="loop_path_style",
    )


def resolve_bead_loop_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
    instance_seed: int | None = None,
) -> PuzzleBeadLoopRenderParams:
    """Resolve rendering params for topology bead-loop scenes."""

    def _int(key: str, fallback: int) -> int:
        return resolve_render_int(
            params,
            render_defaults,
            str(key),
            int(fallback),
            instance_seed=instance_seed,
            namespace="puzzle_bead_loop_render",
        )

    def _rgb(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_render_rgb(
            params,
            render_defaults,
            str(key),
            fallback,
            instance_seed=instance_seed,
            namespace="puzzle_bead_loop_render",
        )

    return PuzzleBeadLoopRenderParams(
        canvas_width=int(_int("canvas_width", 1200)),
        canvas_height=int(_int("canvas_height", 920)),
        scene_margin_left_px=int(_int("scene_margin_left_px", 64)),
        scene_margin_right_px=int(_int("scene_margin_right_px", 64)),
        scene_margin_top_px=int(_int("scene_margin_top_px", 56)),
        scene_margin_bottom_px=int(_int("scene_margin_bottom_px", 56)),
        reference_panel_height_px=int(_int("reference_panel_height_px", 238)),
        reference_panel_padding_px=int(_int("reference_panel_padding_px", 24)),
        reference_loop_width_px=int(_int("reference_loop_width_px", 356)),
        reference_loop_height_px=int(_int("reference_loop_height_px", 170)),
        reference_label_font_size_px=int(_int("reference_label_font_size_px", 28)),
        reference_to_options_gap_px=int(_int("reference_to_options_gap_px", 54)),
        option_image_width_px=int(_int("option_image_width_px", 172)),
        option_image_height_px=int(_int("option_image_height_px", 154)),
        option_gap_px=int(_int("option_gap_px", 28)),
        option_row_gap_px=int(_int("option_row_gap_px", 38)),
        option_label_gap_px=int(_int("option_label_gap_px", 16)),
        option_label_font_size_px=int(_int("option_label_font_size_px", 28)),
        panel_corner_radius_px=int(_int("panel_corner_radius_px", 28)),
        border_width_px=int(_int("border_width_px", 3)),
        loop_stroke_width_px=int(_int("loop_stroke_width_px", 5)),
        bead_size_px=int(_int("bead_size_px", 30)),
        shape_bead_inset_px=int(_int("shape_bead_inset_px", 2)),
        panel_fill_rgb=_rgb("panel_fill_rgb", (248, 249, 252)),
        instruction_fill_rgb=_rgb("instruction_fill_rgb", (240, 244, 250)),
        border_color_rgb=_rgb("border_color_rgb", (86, 94, 108)),
        loop_color_rgb=_rgb("loop_color_rgb", (78, 87, 102)),
        text_color_rgb=_rgb("text_color_rgb", (28, 32, 38)),
        text_stroke_rgb=_rgb("text_stroke_rgb", (255, 255, 255)),
        shape_fill_rgb=_rgb("shape_fill_rgb", (73, 110, 186)),
    )


def rotate_token_sequence(tokens: Sequence[str], offset: int) -> Tuple[str, ...]:
    """Return one cyclic rotation of the token sequence."""

    items = [str(token) for token in tokens]
    if not items:
        return tuple()
    shift = int(offset) % int(len(items))
    return tuple(items[shift:] + items[:shift])


def bead_sequences_are_rotation_equivalent(a: Sequence[str], b: Sequence[str]) -> bool:
    """Return whether two bead sequences match up to cyclic rotation only."""

    left = tuple(str(item) for item in a)
    right = tuple(str(item) for item in b)
    if len(left) != len(right):
        return False
    if not left:
        return True
    doubled = list(left) + list(left)
    width = len(left)
    return any(tuple(doubled[index : index + width]) == right for index in range(width))


def _token_mode_bead_count_bounds(
    token_render_style: str,
    *,
    defaults: PuzzleBeadLoopDefaults,
) -> Tuple[int, int]:
    """Return the active token-count bounds for one token-rendering style."""

    if str(token_render_style) in {"shape_tokens", "outline_shape_tokens"}:
        return int(defaults.bead_count_min), int(defaults.shape_bead_count_max)
    return int(defaults.bead_count_min), int(defaults.bead_count_max)


def _clamp_bead_count_bounds_for_token_mode(
    token_render_style: str,
    *,
    bead_count_min: int,
    bead_count_max: int,
    defaults: PuzzleBeadLoopDefaults,
) -> Tuple[int, int]:
    """Clamp caller-provided token-count bounds to the active token-rendering support."""

    if str(token_render_style) not in {"shape_tokens", "outline_shape_tokens"}:
        return int(bead_count_min), int(bead_count_max)
    clamped_max = min(int(bead_count_max), int(defaults.shape_bead_count_max))
    clamped_min = min(int(bead_count_min), int(clamped_max))
    return int(clamped_min), int(clamped_max)


def _token_catalog_for_mode(
    token_render_style: str,
    *,
    bead_count: int,
    min_color_distance: float,
    color_distance_space: str,
    rng,
) -> Dict[str, Dict[str, Any]]:
    """Build the token catalog for one token-rendering style."""

    def _sample_distinct_color_specs() -> List[Tuple[str, Tuple[int, int, int]]]:
        shuffled = list(BEAD_COLOR_SPECS)
        rng.shuffle(shuffled)
        for candidate_specs in combinations(shuffled, int(bead_count)):
            if all(
                float(color_distance(color_a, color_b, distance_space=str(color_distance_space))) >= float(min_color_distance)
                for (_, color_a), (_, color_b) in combinations(candidate_specs, 2)
            ):
                selected = list(candidate_specs)
                rng.shuffle(selected)
                return selected
        raise RuntimeError("no bead-color subset satisfied the required Lab-distance separation")

    selected_style = str(token_render_style)
    if selected_style == "colored_beads":
        colors = _sample_distinct_color_specs()
        return {
            str(color_name): {
                "token_label": str(color_name),
                "render_mode": "color",
                "object_type": "circle",
                "fill_rgb": [int(value) for value in color_rgb],
            }
            for color_name, color_rgb in colors
        }
    if selected_style in {"shape_tokens", "outline_shape_tokens"}:
        shapes = rng.sample(list(PUZZLE_OBJECT_TYPES), int(bead_count))
        return {
            str(shape): {
                "token_label": str(shape),
                "render_mode": "outline_shape" if selected_style == "outline_shape_tokens" else "shape",
                "object_type": str(shape),
                "fill_rgb": None,
            }
            for shape in shapes
        }

    colors = _sample_distinct_color_specs()
    shapes = rng.sample(list(PUZZLE_OBJECT_TYPES), int(bead_count))
    render_mode = "symbol_badge" if selected_style == "symbol_badges" else "mixed"
    return {
        f"{shape}:{color_name}": {
            "token_label": f"{shape}:{color_name}",
            "render_mode": str(render_mode),
            "object_type": str(shape),
            "fill_rgb": [int(value) for value in color_rgb],
        }
        for shape, (color_name, color_rgb) in zip(shapes, colors)
    }


def _invalid_candidate_sequences(reference_tokens: Sequence[str]) -> List[Tuple[str, ...]]:
    """Return deterministic non-rotation-equivalent candidate distractor sequences."""

    tokens = [str(token) for token in reference_tokens]
    size = len(tokens)
    candidates: List[Tuple[str, ...]] = []
    if size < 2:
        return candidates

    candidates.append(tuple(reversed(tokens)))
    for index in range(size - 1):
        swapped = list(tokens)
        swapped[index], swapped[index + 1] = swapped[index + 1], swapped[index]
        candidates.append(tuple(swapped))
    swapped = list(tokens)
    swapped[0], swapped[-1] = swapped[-1], swapped[0]
    candidates.append(tuple(swapped))
    for insertion_index in range(2, size):
        moved = list(tokens)
        token = moved.pop(0)
        moved.insert(int(insertion_index), token)
        candidates.append(tuple(moved))
    return candidates


def build_bead_equivalence_dataset_for_variant(
    *,
    query_variant: str,
    token_render_style: str | None = None,
    bead_token_mode: str | None = None,
    loop_path_style: str = "ellipse",
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: PuzzleBeadLoopDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one deterministic topology bead-loop equivalence dataset."""

    selected_variant = str(query_variant)
    if selected_variant not in set(SUPPORTED_PUZZLE_BEAD_LOOP_QUERY_VARIANTS):
        raise ValueError(f"unsupported topology bead-loop query_variant: {query_variant}")
    if token_render_style is None:
        token_render_style = SOURCE_PUZZLE_BEAD_TOKEN_MODE_MAP.get(str(bead_token_mode), str(bead_token_mode))
    selected_token_style = str(token_render_style)
    if selected_token_style not in set(SUPPORTED_PUZZLE_CYCLIC_ORDER_TOKEN_RENDER_STYLES):
        raise ValueError(f"unsupported topology cyclic-order token_render_style: {token_render_style}")
    selected_loop_path_style = str(loop_path_style)
    if selected_loop_path_style not in set(SUPPORTED_PUZZLE_LOOP_PATH_STYLES):
        raise ValueError(f"unsupported topology cyclic-order loop_path_style: {loop_path_style}")
    source_token_mode = str(TOKEN_RENDER_STYLE_SOURCE_MODE[str(selected_token_style)])

    rng = spawn_rng(int(instance_seed), f"{task_id}.bead_loop_dataset")
    option_count_min = int(
        _variant_param(
            params,
            gen_defaults,
            query_variant=str(selected_variant),
            key="option_count_min",
            fallback=int(defaults.option_count_min),
        )
    )
    option_count_max = int(
        _variant_param(
            params,
            gen_defaults,
            query_variant=str(selected_variant),
            key="option_count_max",
            fallback=int(defaults.option_count_max),
        )
    )
    valid_option_count_min = int(
        params.get(
            "valid_option_count_min",
            group_default(gen_defaults, "valid_option_count_min", int(defaults.valid_option_count_min)),
        )
    )
    valid_option_count_max = int(
        params.get(
            "valid_option_count_max",
            group_default(gen_defaults, "valid_option_count_max", int(defaults.valid_option_count_max)),
        )
    )
    bead_count_min, bead_count_max = _token_mode_bead_count_bounds(selected_token_style, defaults=defaults)
    bead_count_min = int(
        _variant_param(
            params,
            gen_defaults,
            query_variant=str(selected_variant),
            key="bead_count_min",
            fallback=int(bead_count_min),
        )
    )
    bead_count_max = int(
        _variant_param(
            params,
            gen_defaults,
            query_variant=str(selected_variant),
            key="bead_count_max",
            fallback=int(bead_count_max),
        )
    )
    bead_count_min, bead_count_max = _clamp_bead_count_bounds_for_token_mode(
        selected_token_style,
        bead_count_min=int(bead_count_min),
        bead_count_max=int(bead_count_max),
        defaults=defaults,
    )
    min_color_distance = float(
        params.get(
            "min_color_distance",
            group_default(gen_defaults, "min_color_distance", float(defaults.min_color_distance)),
        )
    )
    color_distance_space = str(
        params.get(
            "color_distance_space",
            group_default(gen_defaults, "color_distance_space", str(defaults.color_distance_space)),
        )
    ).strip().lower()

    if selected_variant == "cyclic_order_equivalent_label":
        valid_option_count_min = 1
        valid_option_count_max = 1
    valid_support = list(range(int(valid_option_count_min), int(valid_option_count_max) + 1))
    explicit_valid_option_count = params.get("valid_option_count")
    if explicit_valid_option_count is not None:
        valid_option_count = int(explicit_valid_option_count)
        if int(valid_option_count) not in set(valid_support):
            raise ValueError("valid_option_count is outside configured supported range")
    else:
        valid_selection_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}:valid_option_count",
            )
        )
        valid_option_count = int(valid_support[int(valid_selection_index) % len(valid_support)])
    bead_count_min = max(int(bead_count_min), int(valid_option_count))
    if int(bead_count_min) > int(bead_count_max):
        raise ValueError("bead_count_max must allow at least as many unique rotations as the valid option support")

    min_option_count = max(int(option_count_min), int(valid_option_count) + 1)
    if int(min_option_count) > int(option_count_max):
        raise ValueError("option_count_max must allow at least one invalid option beyond the valid support")

    answer_position_override: int | None = None
    if selected_variant == "cyclic_order_equivalent_label":
        answer_selection_index = int(
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}:answer_option_label",
            )
        )
        answer_position_override = int(answer_selection_index) % int(option_count_max)

    option_count = int(rng.randint(int(min_option_count), int(option_count_max)))
    if answer_position_override is not None:
        option_count = max(int(option_count), int(answer_position_override) + 1)

    bead_count = int(rng.randint(int(bead_count_min), int(bead_count_max)))
    token_catalog = _token_catalog_for_mode(
        selected_token_style,
        bead_count=int(bead_count),
        min_color_distance=float(min_color_distance),
        color_distance_space=str(color_distance_space),
        rng=rng,
    )
    reference_tokens = tuple(str(token) for token in rng.sample(list(token_catalog.keys()), int(bead_count)))
    valid_offsets = list(rng.sample(list(range(int(bead_count))), int(valid_option_count)))
    valid_sequences = [rotate_token_sequence(reference_tokens, int(offset)) for offset in valid_offsets]

    invalid_needed = int(option_count - valid_option_count)
    invalid_candidates = []
    for candidate in _invalid_candidate_sequences(reference_tokens):
        if bead_sequences_are_rotation_equivalent(reference_tokens, candidate):
            continue
        invalid_candidates.append(candidate)
    if len(invalid_candidates) < int(invalid_needed):
        raise RuntimeError("insufficient topology distractor candidates for bead-loop task")
    selected_invalid_sequences = invalid_candidates[: int(invalid_needed)]

    option_records: List[Dict[str, Any]] = []
    for offset, sequence in zip(valid_offsets, valid_sequences):
        option_records.append(
            {
                "is_valid": True,
                "rotation_offset": int(offset),
                "token_sequence": list(sequence),
            }
        )
    for sequence in selected_invalid_sequences:
        option_records.append(
            {
                "is_valid": False,
                "rotation_offset": None,
                "token_sequence": list(sequence),
            }
        )
    if selected_variant == "cyclic_order_equivalent_label":
        valid_records = [record for record in option_records if bool(record["is_valid"])]
        invalid_records = [record for record in option_records if not bool(record["is_valid"])]
        if len(valid_records) != 1:
            raise RuntimeError("equivalent-label cyclic-order queries require exactly one valid option")
        rng.shuffle(invalid_records)
        answer_position = (
            int(answer_position_override) % int(option_count)
            if answer_position_override is not None
            else 0
        )
        option_records = list(invalid_records)
        option_records.insert(int(answer_position), dict(valid_records[0]))
    else:
        rng.shuffle(option_records)

    labels = [chr(ord("A") + index) for index in range(int(option_count))]
    option_specs: List[Dict[str, Any]] = []
    valid_option_choice_ids: List[str] = []
    valid_option_labels: List[str] = []
    for option_index, (option_label, option_record) in enumerate(zip(labels, option_records), start=1):
        option_choice_id = f"option_{int(option_index)}"
        loop_shape_variant = str(LOOP_SHAPE_VARIANTS[int(rng.randint(0, len(LOOP_SHAPE_VARIANTS) - 1))])
        start_angle_deg = int(LOOP_START_ANGLES_DEG[int(rng.randint(0, len(LOOP_START_ANGLES_DEG) - 1))])
        bead_specs = [
            dict(token_catalog[str(token_label)])
            for token_label in option_record["token_sequence"]
        ]
        spec = {
            "option_index": int(option_index - 1),
            "option_label": str(option_label),
            "option_choice_id": str(option_choice_id),
            "is_valid": bool(option_record["is_valid"]),
            "rotation_offset": option_record["rotation_offset"],
            "token_sequence": [str(token) for token in option_record["token_sequence"]],
            "loop_shape_variant": str(loop_shape_variant),
            "loop_path_style": str(selected_loop_path_style),
            "start_angle_deg": int(start_angle_deg),
            "bead_specs": bead_specs,
        }
        option_specs.append(spec)
        if bool(spec["is_valid"]):
            valid_option_choice_ids.append(str(option_choice_id))
            valid_option_labels.append(str(option_label))

    reference_bead_specs = [dict(token_catalog[str(token_label)]) for token_label in reference_tokens]
    return {
        "reference_token_sequence": [str(token) for token in reference_tokens],
        "reference_bead_specs": reference_bead_specs,
        "reference_loop_shape_variant": str(LOOP_SHAPE_VARIANTS[int(rng.randint(0, len(LOOP_SHAPE_VARIANTS) - 1))]),
        "reference_loop_path_style": str(selected_loop_path_style),
        "reference_start_angle_deg": int(-90),
        "option_specs": option_specs,
        "option_count": int(option_count),
        "option_count_range": [int(option_count_min), int(option_count_max)],
        "valid_option_count": int(valid_option_count),
        "valid_option_count_range": [int(valid_option_count_min), int(valid_option_count_max)],
        "valid_option_choice_ids": [str(value) for value in valid_option_choice_ids],
        "valid_option_labels": [str(value) for value in valid_option_labels],
        "answer_option_choice_id": str(valid_option_choice_ids[0])
        if selected_variant == "cyclic_order_equivalent_label"
        else None,
        "answer_option_label": str(valid_option_labels[0])
        if selected_variant == "cyclic_order_equivalent_label"
        else None,
        "bead_count": int(bead_count),
        "bead_count_range": [int(bead_count_min), int(bead_count_max)],
        "token_render_style": str(selected_token_style),
        "bead_token_mode": str(source_token_mode),
        "loop_path_style": str(selected_loop_path_style),
        "equivalence_rule": "same_cyclic_order_up_to_rotation_no_reflection",
        "color_distance_space": str(color_distance_space),
        "min_color_distance": float(min_color_distance),
        "question_format": str(selected_variant),
        "view_family": "topology_loop_option_label",
        "solver_trace": {
            "query_variant": str(selected_variant),
            "token_render_style": str(selected_token_style),
            "bead_token_mode": str(source_token_mode),
            "loop_path_style": str(selected_loop_path_style),
            "reference_token_sequence": [str(token) for token in reference_tokens],
            "valid_option_labels": [str(value) for value in valid_option_labels],
            "valid_option_choice_ids": [str(value) for value in valid_option_choice_ids],
            "answer_option_choice_id": str(valid_option_choice_ids[0])
            if selected_variant == "cyclic_order_equivalent_label"
            else None,
            "answer_option_label": str(valid_option_labels[0])
            if selected_variant == "cyclic_order_equivalent_label"
            else None,
            "equivalence_rule": "same_cyclic_order_up_to_rotation_no_reflection",
            "color_distance_space": str(color_distance_space),
            "min_color_distance": float(min_color_distance),
            "rotation_allowed": True,
            "reflection_allowed": False,
        },
    }


__all__ = [
    "BEAD_COLOR_SPECS",
    "SOURCE_PUZZLE_BEAD_LOOP_SCENE_VARIANT_MAP",
    "SOURCE_PUZZLE_BEAD_TOKEN_MODE_MAP",
    "PuzzleBeadLoopDefaults",
    "PuzzleBeadLoopRenderParams",
    "SUPPORTED_PUZZLE_CYCLIC_ORDER_SCENE_VARIANTS",
    "SUPPORTED_PUZZLE_CYCLIC_ORDER_TOKEN_RENDER_STYLES",
    "SUPPORTED_PUZZLE_BEAD_LOOP_SCENE_VARIANTS",
    "SUPPORTED_PUZZLE_BEAD_LOOP_QUERY_VARIANTS",
    "SUPPORTED_PUZZLE_BEAD_TOKEN_MODES",
    "SUPPORTED_PUZZLE_LOOP_PATH_STYLES",
    "TOKEN_RENDER_STYLE_SOURCE_MODE",
    "bead_sequences_are_rotation_equivalent",
    "build_bead_equivalence_dataset_for_variant",
    "resolve_cyclic_order_path_style",
    "resolve_cyclic_order_token_render_style",
    "resolve_bead_loop_render_params",
    "resolve_bead_loop_scene_variant",
    "resolve_bead_loop_query_variant",
    "resolve_bead_loop_token_mode",
    "rotate_token_sequence",
]
