"""Physics mechanics task for center-of-mass stack stability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_many as _bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.render_variation import resolve_render_int
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


FAMILY_ID = "physics_mechanics_stack_stability_family"
SCENE_ID = "stack_stability"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("stable_stack_label", "tipping_stack_label")
OPTION_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
STATUS_STABLE = "stable"
STATUS_TIPPING = "tipping"
TIP_DIRECTIONS: Tuple[str, ...] = ("left", "right")

_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "mechanics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="mechanics", apply_prob=0.5)


@dataclass(frozen=True)
class _TaskDefaults:
    canvas_width: int = 1180
    canvas_height: int = 780
    board_left_px: int = 48
    board_top_px: int = 48
    board_right_margin_px: int = 48
    board_bottom_margin_px: int = 48
    cell_gap_x_px: int = 26
    cell_gap_y_px: int = 28
    brick_width_px: int = 80
    brick_height_px: int = 32
    brick_gap_px: int = 3
    label_font_size_px: int = 31
    title_font_size_px: int = 25
    small_font_size_px: int = 18
    label_stroke_width_px: int = 2
    support_width_px: int = 5
    projection_width_px: int = 4
    com_radius_px: int = 8


@dataclass(frozen=True)
class _ResolvedAxes:
    query_id: str
    correct_option_letter: str
    query_id_probabilities: Dict[str, float]
    correct_option_letter_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _StackProfile:
    status: str
    tip_direction: str | None
    row_offsets: Tuple[float, ...]


@dataclass(frozen=True)
class _StackCandidateSpec:
    label: str
    status: str
    tip_direction: str | None
    row_offsets: Tuple[float, ...]
    brick_fill_rgb: Tuple[int, int, int]
    brick_outline_rgb: Tuple[int, int, int]


@dataclass(frozen=True)
class _StackSceneSpec:
    query_id: str
    correct_option_letter: str
    candidates: Tuple[_StackCandidateSpec, ...]


@dataclass(frozen=True)
class _RenderedStack:
    label: str
    status: str
    tip_direction: str | None
    brick_bboxes_px: Tuple[List[float], ...]
    stack_bbox_px: List[float]
    support_bbox_px: List[float]
    center_of_mass_point_px: List[float]
    center_of_mass_bbox_px: List[float]
    projection_point_px: List[float]
    projection_bbox_px: List[float]
    support_left_px: float
    support_right_px: float
    com_offset_units: float


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()

_STABLE_OFFSET_PATTERNS: Tuple[Tuple[float, ...], ...] = (
    (0.0, 0.10, -0.06, 0.05),
    (0.0, -0.18, -0.06, 0.08, 0.16),
    (0.0, 0.22, 0.08, -0.08),
    (0.0, -0.22, -0.10, 0.06, 0.12),
    (0.0, 0.26, 0.12, -0.02, -0.10),
    (0.0, -0.26, -0.14, 0.02, 0.08),
)
_TIPPING_RIGHT_OFFSET_PATTERNS: Tuple[Tuple[float, ...], ...] = (
    (0.0, 0.48, 0.92, 1.34),
    (0.0, 0.40, 0.84, 1.22, 1.58),
    (0.0, 0.54, 0.98, 1.38),
    (0.0, 0.36, 0.76, 1.14, 1.48),
)
_BRICK_PALETTES: Tuple[Tuple[Tuple[int, int, int], Tuple[int, int, int]], ...] = (
    ((198, 92, 70), (115, 50, 42)),
    ((211, 130, 76), (121, 72, 40)),
    ((177, 110, 91), (98, 60, 54)),
    ((189, 146, 88), (105, 79, 45)),
    ((158, 118, 95), (84, 64, 55)),
    ((207, 116, 102), (117, 61, 57)),
    ((180, 125, 72), (101, 66, 37)),
    ((196, 103, 65), (111, 55, 37)),
)


def _bbox_from_center(center: Tuple[float, float], half_w: float, half_h: float) -> List[float]:
    return [
        round(float(center[0] - half_w), 3),
        round(float(center[1] - half_h), 3),
        round(float(center[0] + half_w), 3),
        round(float(center[1] + half_h), 3),
    ]


def _expand_bbox(bbox: Sequence[float], padding: float) -> List[float]:
    return [
        round(float(bbox[0]) - float(padding), 3),
        round(float(bbox[1]) - float(padding), 3),
        round(float(bbox[2]) + float(padding), 3),
        round(float(bbox[3]) + float(padding), 3),
    ]


def _resolve_query_id(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{FAMILY_ID}.query_id"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_QUERY_IDS,
        balance_flag_key="balanced_query_id_sampling",
        explicit_key="query_id",
        weights_key="query_id_weights",
        sampling_namespace=f"{FAMILY_ID}.query_id",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_correct_option_letter(instance_seed: int, *, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), f"{FAMILY_ID}.correct_option_letter"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=OPTION_LETTERS,
        explicit_key="correct_option_letter",
        weights_key="correct_option_letter_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=OPTION_LETTERS,
        balance_flag_key="balanced_correct_option_letter_sampling",
        explicit_key="correct_option_letter",
        weights_key="correct_option_letter_weights",
        sampling_namespace=f"{FAMILY_ID}.correct_option_letter",
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_axes(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedAxes:
    query_id, query_probs = _resolve_query_id(int(instance_seed), params=params)
    correct_option_letter, letter_probs = _resolve_correct_option_letter(int(instance_seed), params=params)
    return _ResolvedAxes(
        query_id=str(query_id),
        correct_option_letter=str(correct_option_letter),
        query_id_probabilities=dict(query_probs),
        correct_option_letter_probabilities=dict(letter_probs),
    )


def _profile_for_status(rng, *, status: str, forced_tip_direction: str | None = None) -> _StackProfile:
    if str(status) == STATUS_STABLE:
        offsets = tuple(float(value) for value in rng.choice(_STABLE_OFFSET_PATTERNS))
        return _StackProfile(status=STATUS_STABLE, tip_direction=None, row_offsets=offsets)
    direction = str(forced_tip_direction or rng.choice(TIP_DIRECTIONS))
    base_offsets = tuple(float(value) for value in rng.choice(_TIPPING_RIGHT_OFFSET_PATTERNS))
    if direction == "left":
        base_offsets = tuple(-float(value) for value in base_offsets)
    return _StackProfile(status=STATUS_TIPPING, tip_direction=direction, row_offsets=base_offsets)


def _make_scene_spec(instance_seed: int, *, axes: _ResolvedAxes, params: Mapping[str, Any]) -> _StackSceneSpec:
    _ = params
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.scene")
    correct_status = STATUS_STABLE if str(axes.query_id) == "stable_stack_label" else STATUS_TIPPING
    distractor_status = STATUS_TIPPING if correct_status == STATUS_STABLE else STATUS_STABLE
    palettes = list(_BRICK_PALETTES)
    rng.shuffle(palettes)
    candidates: List[_StackCandidateSpec] = []
    for index, letter in enumerate(OPTION_LETTERS):
        status = correct_status if str(letter) == str(axes.correct_option_letter) else distractor_status
        forced_direction = None
        if status == STATUS_TIPPING:
            forced_direction = TIP_DIRECTIONS[(index + int(instance_seed)) % len(TIP_DIRECTIONS)]
        profile = _profile_for_status(rng, status=status, forced_tip_direction=forced_direction)
        fill, outline = palettes[index % len(palettes)]
        candidates.append(
            _StackCandidateSpec(
                label=str(letter),
                status=str(profile.status),
                tip_direction=profile.tip_direction,
                row_offsets=tuple(float(value) for value in profile.row_offsets),
                brick_fill_rgb=tuple(int(value) for value in fill),
                brick_outline_rgb=tuple(int(value) for value in outline),
            )
        )
    return _StackSceneSpec(
        query_id=str(axes.query_id),
        correct_option_letter=str(axes.correct_option_letter),
        candidates=tuple(candidates),
    )


def _draw_dashed_vertical_line(
    draw: ImageDraw.ImageDraw,
    *,
    x: float,
    y0: float,
    y1: float,
    fill: Tuple[int, int, int],
    width: int,
    dash_px: float = 10.0,
    gap_px: float = 7.0,
) -> None:
    top = min(float(y0), float(y1))
    bottom = max(float(y0), float(y1))
    y = top
    while y < bottom:
        y_next = min(bottom, y + float(dash_px))
        draw.line([(float(x), float(y)), (float(x), float(y_next))], fill=fill, width=int(width))
        y = y_next + float(gap_px)


def _lighten(rgb: Tuple[int, int, int], amount: int = 28) -> Tuple[int, int, int]:
    return tuple(min(255, int(value) + int(amount)) for value in rgb)


def _render_candidate(
    *,
    draw: ImageDraw.ImageDraw,
    candidate: _StackCandidateSpec,
    cell_bbox: Sequence[float],
    render_defaults: Mapping[str, Any],
    style: Any,
    font_family: str,
    instance_seed: int,
) -> _RenderedStack:
    cell_left, cell_top, cell_right, cell_bottom = [float(value) for value in cell_bbox]
    brick_width = float(render_defaults["brick_width_px"])
    brick_height = float(render_defaults["brick_height_px"])
    brick_gap = float(render_defaults["brick_gap_px"])
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.candidate.{candidate.label}")
    base_x = float((cell_left + cell_right) / 2.0 + rng.randint(-10, 10))
    ground_y = float(cell_bottom - 34.0 + rng.randint(-3, 4))
    top_margin = float(cell_top + 54.0)
    row_count = len(candidate.row_offsets)
    stack_height = row_count * brick_height + max(0, row_count - 1) * brick_gap
    if ground_y - stack_height < top_margin:
        ground_y = top_margin + stack_height

    label_font = load_font(int(render_defaults["label_font_size_px"]), bold=True, font_family=font_family)
    small_font = load_font(int(render_defaults["small_font_size_px"]), bold=True, font_family=font_family)
    label_rgb = tuple(int(v) for v in style.label_rgb)
    guide_rgb = tuple(int(v) for v in style.guide_rgb)
    support_rgb = tuple(int(v) for v in style.stroke_rgb)
    projection_rgb = tuple(int(v) for v in style.accent_rgb)
    com_fill = (223, 48, 54)
    com_outline = (112, 30, 34)

    draw.rounded_rectangle(
        [cell_left, cell_top, cell_right, cell_bottom],
        radius=14,
        fill=tuple(int(v) for v in style.panel_alt_fill_rgb),
        outline=tuple(int(v) for v in style.panel_border_rgb),
        width=2,
    )
    draw.line(
        [(cell_left + 22, ground_y), (cell_right - 22, ground_y)],
        fill=guide_rgb,
        width=2,
    )

    label_center = (cell_left + 34, cell_top + 30)
    label_bbox = _bbox_from_center(label_center, 20, 18)
    draw.rounded_rectangle(
        label_bbox,
        radius=8,
        fill=tuple(int(v) for v in style.label_fill_rgb),
        outline=tuple(int(v) for v in style.label_border_rgb),
        width=2,
    )
    draw_centered_text(
        draw,
        text=str(candidate.label),
        center=label_center,
        font=label_font,
        fill=label_rgb,
        stroke_fill=resolve_text_stroke_fill(label_rgb),
        stroke_width=int(render_defaults["label_stroke_width_px"]),
    )

    brick_bboxes: List[List[float]] = []
    brick_centers: List[Tuple[float, float]] = []
    for row_index, offset_units in enumerate(candidate.row_offsets):
        row_from_bottom = int(row_index)
        cx = float(base_x + float(offset_units) * brick_width)
        y1 = float(ground_y - row_from_bottom * (brick_height + brick_gap))
        y0 = float(y1 - brick_height)
        bbox = [
            round(float(cx - brick_width / 2.0), 3),
            round(float(y0), 3),
            round(float(cx + brick_width / 2.0), 3),
            round(float(y1), 3),
        ]
        brick_bboxes.append(bbox)
        brick_centers.append((float(cx), float((y0 + y1) / 2.0)))
        draw.rounded_rectangle(
            bbox,
            radius=5,
            fill=tuple(int(v) for v in candidate.brick_fill_rgb),
            outline=tuple(int(v) for v in candidate.brick_outline_rgb),
            width=3,
        )
        top_highlight_y = float(y0 + 6)
        draw.line(
            [(bbox[0] + 9, top_highlight_y), (bbox[2] - 9, top_highlight_y)],
            fill=_lighten(candidate.brick_fill_rgb, 34),
            width=2,
        )
        mid_x = float((bbox[0] + bbox[2]) / 2.0)
        draw.line(
            [(mid_x, bbox[1] + 7), (mid_x, bbox[3] - 7)],
            fill=tuple(int(v) for v in candidate.brick_outline_rgb),
            width=1,
        )

    stack_bbox = _expand_bbox(_bbox_union(*brick_bboxes), 3.0)
    bottom_bbox = brick_bboxes[0]
    support_y = float(ground_y + 12.0)
    support_bbox = [
        round(float(bottom_bbox[0]), 3),
        round(float(support_y - 8.0), 3),
        round(float(bottom_bbox[2]), 3),
        round(float(support_y + 8.0), 3),
    ]
    support_width = int(render_defaults["support_width_px"])
    draw.line([(bottom_bbox[0], support_y), (bottom_bbox[2], support_y)], fill=support_rgb, width=support_width)
    draw.line([(bottom_bbox[0], support_y - 10), (bottom_bbox[0], support_y + 10)], fill=support_rgb, width=support_width)
    draw.line([(bottom_bbox[2], support_y - 10), (bottom_bbox[2], support_y + 10)], fill=support_rgb, width=support_width)

    com_x = float(sum(point[0] for point in brick_centers) / len(brick_centers))
    com_y = float(sum(point[1] for point in brick_centers) / len(brick_centers))
    projection_y = float(support_y)
    projection_width = int(render_defaults["projection_width_px"])
    _draw_dashed_vertical_line(
        draw,
        x=com_x,
        y0=com_y,
        y1=projection_y,
        fill=projection_rgb,
        width=projection_width,
    )
    com_radius = int(render_defaults["com_radius_px"])
    com_bbox = _bbox_from_center((com_x, com_y), com_radius, com_radius)
    draw.ellipse(com_bbox, fill=com_fill, outline=com_outline, width=3)
    draw.line([(com_x - com_radius + 3, com_y), (com_x + com_radius - 3, com_y)], fill=(255, 255, 255), width=2)
    draw.line([(com_x, com_y - com_radius + 3), (com_x, com_y + com_radius - 3)], fill=(255, 255, 255), width=2)
    draw_centered_text(
        draw,
        text="COM",
        center=(min(cell_right - 35.0, max(cell_left + 35.0, com_x + 35.0)), com_y - 18.0),
        font=small_font,
        fill=com_fill,
        stroke_fill=resolve_text_stroke_fill(com_fill),
        stroke_width=1,
    )
    projection_point_bbox = _bbox_from_center((com_x, projection_y), 5.0, 5.0)
    draw.ellipse(projection_point_bbox, fill=projection_rgb, outline=support_rgb, width=2)

    projection_bbox = [
        round(float(com_x - projection_width - 5), 3),
        round(float(min(com_y, projection_y) - 5), 3),
        round(float(com_x + projection_width + 5), 3),
        round(float(max(com_y, projection_y) + 5), 3),
    ]
    com_offset_units = float((com_x - float((bottom_bbox[0] + bottom_bbox[2]) / 2.0)) / brick_width)
    return _RenderedStack(
        label=str(candidate.label),
        status=str(candidate.status),
        tip_direction=candidate.tip_direction,
        brick_bboxes_px=tuple(list(bbox) for bbox in brick_bboxes),
        stack_bbox_px=list(stack_bbox),
        support_bbox_px=list(support_bbox),
        center_of_mass_point_px=[round(float(com_x), 3), round(float(com_y), 3)],
        center_of_mass_bbox_px=list(com_bbox),
        projection_point_px=[round(float(com_x), 3), round(float(projection_y), 3)],
        projection_bbox_px=list(projection_bbox),
        support_left_px=float(bottom_bbox[0]),
        support_right_px=float(bottom_bbox[2]),
        com_offset_units=round(float(com_offset_units), 4),
    )


def _resolve_render_defaults(params: Mapping[str, Any], *, instance_seed: int) -> Dict[str, int]:
    keys = (
        "board_left_px",
        "board_top_px",
        "board_right_margin_px",
        "board_bottom_margin_px",
        "cell_gap_x_px",
        "cell_gap_y_px",
        "brick_width_px",
        "brick_height_px",
        "brick_gap_px",
        "label_font_size_px",
        "title_font_size_px",
        "small_font_size_px",
        "label_stroke_width_px",
        "support_width_px",
        "projection_width_px",
        "com_radius_px",
    )
    return {
        str(key): resolve_render_int(
            params,
            _RENDER_DEFAULTS,
            str(key),
            int(getattr(_DEFAULTS, str(key))),
            instance_seed=int(instance_seed),
            namespace=FAMILY_ID,
        )
        for key in keys
    }


def _render_scene(
    *,
    image: Image.Image,
    spec: _StackSceneSpec,
    render_defaults: Mapping[str, Any],
    font_family: str,
    style: Any,
    instance_seed: int,
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    title_font = load_font(int(render_defaults["title_font_size_px"]), bold=True, font_family=font_family)
    label_rgb = tuple(int(v) for v in style.label_rgb)
    board_left = float(render_defaults["board_left_px"])
    board_top = float(render_defaults["board_top_px"])
    board_right = float(width - int(render_defaults["board_right_margin_px"]))
    board_bottom = float(height - int(render_defaults["board_bottom_margin_px"]))
    board_bbox = [board_left, board_top, board_right, board_bottom]
    draw.rounded_rectangle(
        board_bbox,
        radius=20,
        fill=tuple(int(v) for v in style.panel_fill_rgb),
        outline=tuple(int(v) for v in style.panel_border_rgb),
        width=3,
    )
    draw_centered_text(
        draw,
        text="center-of-mass stability checks",
        center=((board_left + board_right) / 2.0, board_top + 26.0),
        font=title_font,
        fill=label_rgb,
        stroke_fill=resolve_text_stroke_fill(label_rgb),
        stroke_width=1,
    )

    gap_x = float(render_defaults["cell_gap_x_px"])
    gap_y = float(render_defaults["cell_gap_y_px"])
    inner_left = board_left + 24.0
    inner_right = board_right - 24.0
    inner_top = board_top + 58.0
    inner_bottom = board_bottom - 24.0
    cell_width = float((inner_right - inner_left - 2.0 * gap_x) / 3.0)
    cell_height = float((inner_bottom - inner_top - gap_y) / 2.0)
    rendered_stacks: Dict[str, _RenderedStack] = {}
    entities: List[Dict[str, Any]] = []
    for index, candidate in enumerate(spec.candidates):
        row = int(index // 3)
        col = int(index % 3)
        cell_left = inner_left + col * (cell_width + gap_x)
        cell_top = inner_top + row * (cell_height + gap_y)
        cell_bbox = [
            round(float(cell_left), 3),
            round(float(cell_top), 3),
            round(float(cell_left + cell_width), 3),
            round(float(cell_top + cell_height), 3),
        ]
        rendered = _render_candidate(
            draw=draw,
            candidate=candidate,
            cell_bbox=cell_bbox,
            render_defaults=render_defaults,
            style=style,
            font_family=str(font_family),
            instance_seed=int(instance_seed),
        )
        rendered_stacks[str(candidate.label)] = rendered
        entities.append(
            {
                "entity_id": f"stack_{candidate.label}",
                "entity_type": "brick_stack_option",
                "bbox_px": list(rendered.stack_bbox_px),
                "meta": {
                    "option_letter": str(candidate.label),
                    "status": str(candidate.status),
                    "tip_direction": candidate.tip_direction,
                    "is_correct": str(candidate.label) == str(spec.correct_option_letter),
                    "row_offsets": [round(float(value), 4) for value in candidate.row_offsets],
                    "com_offset_units": float(rendered.com_offset_units),
                    "support_left_px": round(float(rendered.support_left_px), 3),
                    "support_right_px": round(float(rendered.support_right_px), 3),
                    "com_x_px": rendered.center_of_mass_point_px[0],
                },
            }
        )

    selected = rendered_stacks[str(spec.correct_option_letter)]
    annotation_bbox_map = {
        "center_of_mass": list(selected.center_of_mass_bbox_px),
        "projection": list(selected.projection_bbox_px),
        "support_footprint": list(selected.support_bbox_px),
    }
    render_map = {
        "query_id": str(spec.query_id),
        "correct_option_letter": str(spec.correct_option_letter),
        "candidate_statuses": {
            str(label): str(rendered.status)
            for label, rendered in sorted(rendered_stacks.items())
        },
        "candidate_tip_directions": {
            str(label): rendered.tip_direction
            for label, rendered in sorted(rendered_stacks.items())
        },
        "candidate_com_points_px": {
            str(label): list(rendered.center_of_mass_point_px)
            for label, rendered in sorted(rendered_stacks.items())
        },
        "candidate_projection_points_px": {
            str(label): list(rendered.projection_point_px)
            for label, rendered in sorted(rendered_stacks.items())
        },
        "candidate_support_bboxes_px": {
            str(label): list(rendered.support_bbox_px)
            for label, rendered in sorted(rendered_stacks.items())
        },
        "candidate_stack_bboxes_px": {
            str(label): list(rendered.stack_bbox_px)
            for label, rendered in sorted(rendered_stacks.items())
        },
        "annotation_keyed_bboxes_px": dict(annotation_bbox_map),
    }
    return _RenderedScene(
        image=image,
        annotation_bbox_map={str(key): list(value) for key, value in annotation_bbox_map.items()},
        scene_entities=[dict(entity) for entity in entities],
        render_map=dict(render_map),
    )


@register_task
class PhysicsMechanicsStackStabilityStatusLabelTask:
    """Choose the brick stack whose center-of-mass projection matches the queried stability status."""

    task_id = "task_physics__stack_stability__stability_status_label"
    domain = "physics"
    task_group = "mechanics"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        params = dict(params or {})
        last_error: Exception | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_seed = int(instance_seed) + (attempt_index * 7919)
            try:
                axes = _resolve_axes(attempt_seed, params=params)
                spec = _make_scene_spec(attempt_seed, axes=axes, params=params)
            except Exception as exc:  # pragma: no cover - surfaced if all attempts fail.
                last_error = exc
                continue

            canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width)))
            canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height)))
            background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
                instance_seed=attempt_seed,
                params=params,
                scene_id=SCENE_ID,
                task_group=self.task_group,
                canvas_width=int(canvas_width),
                canvas_height=int(canvas_height),
                require_grid=True,
            )
            font_family = sample_font_family(
                role="readout",
                instance_seed=attempt_seed,
                namespace=f"{FAMILY_ID}.font",
                params=params,
            )
            font_record = get_font_family_record(str(font_family))
            render_defaults = _resolve_render_defaults(params, instance_seed=attempt_seed)
            rendered = _render_scene(
                image=background,
                spec=spec,
                render_defaults=render_defaults,
                font_family=str(font_family),
                style=diagram_style,
                instance_seed=attempt_seed,
            )
            image, post_noise_meta = apply_post_image_noise(
                rendered.image,
                instance_seed=attempt_seed,
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
                    "object_description",
                    f"answer_hint_{str(spec.query_id)}",
                    f"annotation_hint_{str(spec.query_id)}",
                ),
                context=f"prompt defaults for {self.task_id}",
            )
            answer_gt = TypedValue(type="option_letter", value=str(spec.correct_option_letter))
            annotation_gt = TypedValue(type="keyed_bbox_map", value={str(key): list(value) for key, value in rendered.annotation_bbox_map.items()})
            json_example, json_example_answer_only = build_prompt_json_examples(
                annotation_value=annotation_gt.value,
                answer_type=str(answer_gt.type),
            )
            prompt_selection = render_task_prompt_variants(
                domain=self.domain,
                task_group=self.task_group,
                bundle_id=str(prompt_defaults["bundle_id"]),
                scene_key=str(prompt_defaults["scene_key"]),
                task_key=str(prompt_defaults["task_key"]),
                query_key=str(spec.query_id),
                slots={
                    "object_description": str(prompt_defaults["object_description"]),
                    "json_output_contract": str(prompt_defaults["json_output_contract"]),
                    "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                    "answer_hint": str(prompt_defaults[f"answer_hint_{str(spec.query_id)}"]),
                    "annotation_hint": str(prompt_defaults[f"annotation_hint_{str(spec.query_id)}"]),
                    "json_example": str(json_example),
                    "json_example_answer_only": str(json_example_answer_only),
                },
                instance_seed=attempt_seed,
                answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            )
            prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
            complexity = TaskComplexity(
                complexity_score=0.42,
                complexity_components={
                    "visual_scan": 0.34,
                    "center_of_mass_reasoning": 0.38,
                    "ambiguity": 0.16,
                    "output_burden": 0.12,
                },
            )
            trace_payload = {
                "scene_ir": {
                    "scene_kind": "physics_stack_stability_brick_stacks",
                    "entities": [dict(entity) for entity in rendered.scene_entities],
                    "relations": {
                        "query_id": str(spec.query_id),
                        "correct_option_letter": str(spec.correct_option_letter),
                        "target_status": STATUS_STABLE if str(spec.query_id) == "stable_stack_label" else STATUS_TIPPING,
                    },
                },
                "query_spec": {
                    "query_id": str(spec.query_id),
                    "template_id": str(prompt_defaults["bundle_id"]),
                    "prompt_variant": dict(prompt_artifacts.prompt_variant),
                    "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                    "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                    "params": {
                        "query_id": str(spec.query_id),
                        "target_answer": str(spec.correct_option_letter),
                        "answer_support": list(OPTION_LETTERS),
                    },
                },
                "render_spec": {
                    "canvas_width": int(image.size[0]),
                    "canvas_height": int(image.size[1]),
                    "font": {
                        "font_family": str(font_family),
                        "font_asset_version": font_asset_version(),
                        "font_asset": font_record.to_trace(),
                        "scope": "stack_stability_diagram",
                    },
                    "technical_diagram_style": dict(diagram_style_meta),
                    "background_style": background_meta,
                    "render_defaults": dict(render_defaults),
                    "post_image_noise": post_noise_meta,
                },
                "render_map": dict(rendered.render_map),
                "execution_trace": {
                    "query_id": str(spec.query_id),
                    "correct_option_letter": str(spec.correct_option_letter),
                    "target_status": STATUS_STABLE if str(spec.query_id) == "stable_stack_label" else STATUS_TIPPING,
                    "candidate_statuses": dict(rendered.render_map["candidate_statuses"]),
                    "candidate_tip_directions": dict(rendered.render_map["candidate_tip_directions"]),
                    "annotation_entity_ids": sorted(annotation_gt.value.keys()),
                },
                "sampling": {
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "correct_option_letter_probabilities": dict(axes.correct_option_letter_probabilities),
                },
                "witness_symbolic": {
                    "type": "keyed_bbox_map",
                    "keys": sorted(annotation_gt.value.keys()),
                },
                "projected_annotation": {
                    "type": "keyed_bbox_map",
                    "keyed_bbox_map": dict(annotation_gt.value),
                    "pixel_keyed_bbox_map": dict(annotation_gt.value),
                },
                "background": background_meta,
                "post_image_noise": post_noise_meta,
            }
            return TaskOutput(
                prompt=str(prompt_artifacts.prompt),
                prompt_variants=dict(prompt_artifacts.prompt_variants),
                answer_gt=answer_gt,
                annotation_gt=annotation_gt,
                image=image,
                image_id="img0",
                trace_payload=trace_payload,
                complexity=complexity,
                task_versions=default_task_versions(),
                scene_id=SCENE_ID,
                query_id=str(spec.query_id),
            )
        raise RuntimeError(f"failed to generate stack-stability instance after {max_attempts} attempts: {last_error}")
