"""Physics thermodynamics task for constant-pressure piston boundary work."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_many as _bbox_union
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.drawing import draw_arrow, draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.support_sampling import resolve_integer_support
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "task_physics__piston_cylinder__boundary_work_value"
FAMILY_ID = "physics_thermodynamics_piston_cylinder_family"
SCENE_ID = "piston_cylinder"
QUERY_ID = "constant_pressure_boundary_work"
SUPPORTED_ORIENTATIONS: Tuple[str, ...] = ("vertical_pair", "horizontal_pair")

POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="thermodynamics", apply_prob=0.5)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "thermodynamics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for piston-cylinder boundary-work scenes."""

    canvas_width: int = 1160
    canvas_height: int = 740
    panel_left_px: int = 58
    panel_top_px: int = 52
    panel_right_margin_px: int = 58
    panel_bottom_margin_px: int = 58
    cylinder_width_px: int = 238
    cylinder_height_px: int = 330
    horizontal_cylinder_width_px: int = 342
    horizontal_cylinder_height_px: int = 208
    piston_thickness_px: int = 24
    label_font_size_px: int = 26
    state_font_size_px: int = 24
    title_font_size_px: int = 30
    pressure_mpa_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    volume_l_support: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 9)
    min_volume_delta: int = 2
    max_volume_delta: int = 6
    boundary_work_answer_support: Tuple[int, ...] = (
        -36,
        -30,
        -24,
        -20,
        -18,
        -16,
        -15,
        -12,
        -10,
        -9,
        -8,
        -6,
        -5,
        -4,
        -3,
        -2,
        2,
        3,
        4,
        5,
        6,
        8,
        9,
        10,
        12,
        15,
        16,
        18,
        20,
        24,
        30,
        36,
    )


@dataclass(frozen=True)
class _PistonScenario:
    """Resolved constant-pressure boundary-work scenario."""

    pressure_mpa: int
    initial_volume_l: int
    final_volume_l: int
    boundary_work_kj: int
    orientation: str
    orientation_probabilities: Dict[str, float]
    pressure_probabilities: Dict[str, float]
    initial_volume_probabilities: Dict[str, float]
    final_volume_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered piston-cylinder scene plus prompt-facing annotation metadata."""

    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _integer_support(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(key),
        fallback=fallback,
    )


def _feasible_scenarios(params: Mapping[str, Any]) -> Tuple[Tuple[int, int, int, int], ...]:
    pressures = _integer_support(params, "pressure_mpa_support", _DEFAULTS.pressure_mpa_support)
    volumes = _integer_support(params, "volume_l_support", _DEFAULTS.volume_l_support)
    configured_answers = set(
        _integer_support(params, "boundary_work_answer_support", _DEFAULTS.boundary_work_answer_support)
    )
    min_delta = int(params.get("min_volume_delta", group_default(_GEN_DEFAULTS, "min_volume_delta", _DEFAULTS.min_volume_delta)))
    max_delta = int(params.get("max_volume_delta", group_default(_GEN_DEFAULTS, "max_volume_delta", _DEFAULTS.max_volume_delta)))
    scenarios: List[Tuple[int, int, int, int]] = []
    for pressure in pressures:
        for initial_volume in volumes:
            for final_volume in volumes:
                delta = int(final_volume) - int(initial_volume)
                if int(delta) == 0:
                    continue
                if abs(int(delta)) < int(min_delta) or abs(int(delta)) > int(max_delta):
                    continue
                answer = int(pressure) * int(delta)
                if int(answer) not in configured_answers:
                    continue
                scenarios.append((int(pressure), int(initial_volume), int(final_volume), int(answer)))
    if not scenarios:
        raise ValueError("no feasible piston-cylinder boundary-work scenarios for configured supports")
    return tuple(scenarios)


def _probability_map(values: Sequence[str], selected: str | None = None) -> Dict[str, float]:
    if selected is not None:
        return {str(value): (1.0 if str(value) == str(selected) else 0.0) for value in values}
    probability = 1.0 / float(len(values)) if values else 0.0
    return {str(value): float(probability) for value in values}


def _uniform_int_probability_map(values: Sequence[int], selected: int | None = None) -> Dict[str, float]:
    return {str(key): float(value) for key, value in uniform_probability_map(values, selected=selected).items()}


def _resolve_orientation(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = str(params.get("orientation") or "").strip()
    if explicit:
        if explicit not in SUPPORTED_ORIENTATIONS:
            raise ValueError(f"unsupported orientation for {TASK_ID}: {explicit}")
        return explicit, _probability_map(SUPPORTED_ORIENTATIONS, selected=explicit)
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.orientation")
    selected, probabilities = resolve_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=SUPPORTED_ORIENTATIONS,
        explicit_key="orientation",
        weights_key="orientation_weights",
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=SUPPORTED_ORIENTATIONS,
        balance_flag_key="balanced_orientation_sampling",
        explicit_key="orientation",
        weights_key="orientation_weights",
        sampling_namespace=f"{FAMILY_ID}.orientation",
    )
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def _resolve_scenario(instance_seed: int, params: Mapping[str, Any]) -> _PistonScenario:
    query_id = str(params.get("query_id", QUERY_ID))
    if query_id != QUERY_ID:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {query_id}")

    orientation, orientation_probabilities = _resolve_orientation(int(instance_seed), params)
    pressure_support = _integer_support(params, "pressure_mpa_support", _DEFAULTS.pressure_mpa_support)
    volume_support = _integer_support(params, "volume_l_support", _DEFAULTS.volume_l_support)
    feasible = _feasible_scenarios(params)
    explicit_pressure = params.get("pressure_mpa", params.get("pressure"))
    explicit_initial = params.get("initial_volume_l", params.get("volume_start"))
    explicit_final = params.get("final_volume_l", params.get("volume_end"))
    explicit_answer = params.get("target_answer", params.get("boundary_work_kj"))

    candidates = list(feasible)
    if explicit_pressure is not None:
        candidates = [item for item in candidates if int(item[0]) == int(explicit_pressure)]
    if explicit_initial is not None:
        candidates = [item for item in candidates if int(item[1]) == int(explicit_initial)]
    if explicit_final is not None:
        candidates = [item for item in candidates if int(item[2]) == int(explicit_final)]
    if explicit_answer is not None:
        candidates = [item for item in candidates if int(item[3]) == int(explicit_answer)]
    if not candidates:
        raise ValueError("explicit piston-cylinder parameters do not define a feasible scenario")

    if explicit_pressure is not None and explicit_initial is not None and explicit_final is not None:
        selected_tuple = candidates[0]
    elif explicit_answer is not None:
        index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.target_answer_tuple",
        )
        selected_tuple = candidates[int(index) % len(candidates)]
    else:
        answers = sorted({int(answer) for _, _, _, answer in candidates}, key=lambda value: (abs(int(value)), int(value) < 0))
        if bool(params.get("balanced_target_answer_sampling", group_default(_GEN_DEFAULTS, "balanced_target_answer_sampling", True))):
            answer_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{FAMILY_ID}.target_answer",
            )
            target_answer = int(answers[int(answer_index) % len(answers)])
        else:
            rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.target_answer")
            target_answer = int(answers[int(rng.randrange(len(answers)))])
        answer_candidates = [item for item in candidates if int(item[3]) == int(target_answer)]
        tuple_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.target_answer_tuple",
        )
        selected_tuple = answer_candidates[int(tuple_index) % len(answer_candidates)]

    pressure, initial_volume, final_volume, answer = selected_tuple
    if explicit_answer is not None and int(answer) != int(explicit_answer):
        raise ValueError("target_answer does not match resolved piston-cylinder scenario")

    return _PistonScenario(
        pressure_mpa=int(pressure),
        initial_volume_l=int(initial_volume),
        final_volume_l=int(final_volume),
        boundary_work_kj=int(answer),
        orientation=str(orientation),
        orientation_probabilities=orientation_probabilities,
        pressure_probabilities=_uniform_int_probability_map(pressure_support, selected=int(pressure) if explicit_pressure is not None else None),
        initial_volume_probabilities=_uniform_int_probability_map(volume_support, selected=int(initial_volume) if explicit_initial is not None else None),
        final_volume_probabilities=_uniform_int_probability_map(volume_support, selected=int(final_volume) if explicit_final is not None else None),
        target_answer_probabilities=_uniform_int_probability_map(
            sorted({int(item[3]) for item in feasible}),
            selected=int(answer) if explicit_answer is not None else None,
        ),
    )


def _draw_label_box(
    draw: ImageDraw.ImageDraw,
    *,
    lines: Sequence[str],
    center: Tuple[float, float],
    font: Any,
    style: Any,
) -> List[float]:
    text_bboxes = [draw.textbbox((0, 0), str(line), font=font, stroke_width=1) for line in lines]
    text_width = max(float(bbox[2] - bbox[0]) for bbox in text_bboxes)
    line_height = max(float(bbox[3] - bbox[1]) for bbox in text_bboxes) + 8.0
    box_width = float(text_width + 38.0)
    box_height = float(line_height * len(lines) + 20.0)
    cx, cy = float(center[0]), float(center[1])
    box = _bbox((cx - box_width / 2.0, cy - box_height / 2.0, cx + box_width / 2.0, cy + box_height / 2.0))
    draw.rounded_rectangle(
        tuple(box),
        radius=12,
        fill=tuple(int(v) for v in style.label_fill_rgb),
        outline=tuple(int(v) for v in style.label_border_rgb),
        width=3,
    )
    line_bboxes: List[List[float]] = []
    first_y = float(cy - (line_height * (len(lines) - 1) / 2.0))
    label_rgb = tuple(int(v) for v in style.label_rgb)
    for index, line in enumerate(lines):
        bbox = draw_centered_text(
            draw,
            text=str(line),
            center=(float(cx), float(first_y + index * line_height)),
            font=font,
            fill=label_rgb,
            stroke_fill=resolve_text_stroke_fill(label_rgb),
            stroke_width=1,
        )
        line_bboxes.append(list(bbox))
    return _bbox(_bbox_union(box, *line_bboxes))


def _draw_vertical_cylinder(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    volume_l: int,
    max_volume_l: int,
    scenario: _PistonScenario,
    style: Any,
    font: Any,
    label: str,
    gas_rgb: Tuple[int, int, int],
    render_defaults: Mapping[str, Any],
) -> Tuple[List[float], List[float]]:
    cx, bottom = float(center[0]), float(center[1])
    width = float(render_defaults.get("cylinder_width_px", _DEFAULTS.cylinder_width_px))
    height = float(render_defaults.get("cylinder_height_px", _DEFAULTS.cylinder_height_px))
    left = float(cx - width / 2.0)
    right = float(cx + width / 2.0)
    top = float(bottom - height)
    stroke = tuple(int(v) for v in style.stroke_rgb)
    glass = (238, 248, 251)
    fill_fraction = 0.24 + 0.60 * (float(volume_l) / float(max_volume_l))
    gas_top = float(bottom - 18.0 - fill_fraction * (height - 54.0))
    inner = (left + 18.0, gas_top, right - 18.0, bottom - 18.0)
    draw.rounded_rectangle((left, top, right, bottom), radius=22, fill=glass, outline=stroke, width=5)
    draw.rectangle(inner, fill=gas_rgb)
    draw.arc((inner[0], gas_top - 14.0, inner[2], gas_top + 14.0), 0, 180, fill=tuple(max(0, v - 45) for v in gas_rgb), width=4)
    piston_y = float(gas_top - 18.0)
    piston = (left + 8.0, piston_y, right - 8.0, piston_y + float(render_defaults.get("piston_thickness_px", _DEFAULTS.piston_thickness_px)))
    draw.rounded_rectangle(piston, radius=9, fill=tuple(int(v) for v in style.muted_fill_rgb), outline=stroke, width=4)
    rod_x = float((piston[0] + piston[2]) / 2.0)
    draw.line((rod_x, top - 44.0, rod_x, piston[1]), fill=stroke, width=8)
    draw.rectangle((rod_x - 32.0, top - 54.0, rod_x + 32.0, top - 38.0), fill=tuple(int(v) for v in style.muted_fill_rgb), outline=stroke, width=3)
    draw.rounded_rectangle((left, top, right, bottom), radius=22, fill=None, outline=stroke, width=5)
    label_bbox = draw_centered_text(
        draw,
        text=str(label),
        center=(cx, float(top - 82.0)),
        font=font,
        fill=tuple(int(v) for v in style.label_rgb),
        stroke_fill=resolve_text_stroke_fill(tuple(int(v) for v in style.label_rgb)),
        stroke_width=1,
    )
    apparatus_bbox = _bbox(_bbox_union((left, top - 58.0, right, bottom), label_bbox, padding=6.0))
    piston_bbox = _bbox(piston)
    return apparatus_bbox, piston_bbox


def _draw_horizontal_cylinder(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    volume_l: int,
    max_volume_l: int,
    scenario: _PistonScenario,
    style: Any,
    font: Any,
    label: str,
    gas_rgb: Tuple[int, int, int],
    render_defaults: Mapping[str, Any],
) -> Tuple[List[float], List[float]]:
    cy = float(center[1])
    left = float(center[0])
    width = float(render_defaults.get("horizontal_cylinder_width_px", _DEFAULTS.horizontal_cylinder_width_px))
    height = float(render_defaults.get("horizontal_cylinder_height_px", _DEFAULTS.horizontal_cylinder_height_px))
    right = float(left + width)
    top = float(cy - height / 2.0)
    bottom = float(cy + height / 2.0)
    stroke = tuple(int(v) for v in style.stroke_rgb)
    glass = (238, 248, 251)
    fill_fraction = 0.24 + 0.60 * (float(volume_l) / float(max_volume_l))
    gas_right = float(left + 18.0 + fill_fraction * (width - 54.0))
    inner = (left + 18.0, top + 18.0, gas_right, bottom - 18.0)
    draw.rounded_rectangle((left, top, right, bottom), radius=22, fill=glass, outline=stroke, width=5)
    draw.rectangle(inner, fill=gas_rgb)
    draw.arc((gas_right - 15.0, inner[1], gas_right + 15.0, inner[3]), 270, 90, fill=tuple(max(0, v - 45) for v in gas_rgb), width=4)
    piston_x = float(gas_right + 14.0)
    thickness = float(render_defaults.get("piston_thickness_px", _DEFAULTS.piston_thickness_px))
    piston = (piston_x, top + 8.0, piston_x + thickness, bottom - 8.0)
    draw.rounded_rectangle(piston, radius=9, fill=tuple(int(v) for v in style.muted_fill_rgb), outline=stroke, width=4)
    rod_y = float((piston[1] + piston[3]) / 2.0)
    draw.line((piston[2], rod_y, right + 44.0, rod_y), fill=stroke, width=8)
    draw.rectangle((right + 38.0, rod_y - 32.0, right + 54.0, rod_y + 32.0), fill=tuple(int(v) for v in style.muted_fill_rgb), outline=stroke, width=3)
    draw.rounded_rectangle((left, top, right, bottom), radius=22, fill=None, outline=stroke, width=5)
    label_bbox = draw_centered_text(
        draw,
        text=str(label),
        center=(float((left + right) / 2.0), float(top - 36.0)),
        font=font,
        fill=tuple(int(v) for v in style.label_rgb),
        stroke_fill=resolve_text_stroke_fill(tuple(int(v) for v in style.label_rgb)),
        stroke_width=1,
    )
    apparatus_bbox = _bbox(_bbox_union((left, top, right + 54.0, bottom), label_bbox, padding=6.0))
    piston_bbox = _bbox(piston)
    return apparatus_bbox, piston_bbox


def _render_piston_cylinder(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scenario: _PistonScenario,
) -> _RenderedScene:
    canvas_width = int(_RENDER_DEFAULTS.get("canvas_width", _DEFAULTS.canvas_width))
    canvas_height = int(_RENDER_DEFAULTS.get("canvas_height", _DEFAULTS.canvas_height))
    background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        task_group="thermodynamics",
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        require_grid=True,
    )
    draw = ImageDraw.Draw(background)
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.render")
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{FAMILY_ID}.font",
        params=params,
    )
    label_font = load_font(int(_RENDER_DEFAULTS.get("label_font_size_px", _DEFAULTS.label_font_size_px)), bold=True, font_family=str(font_family))
    state_font = load_font(int(_RENDER_DEFAULTS.get("state_font_size_px", _DEFAULTS.state_font_size_px)), bold=True, font_family=str(font_family))
    title_font = load_font(int(_RENDER_DEFAULTS.get("title_font_size_px", _DEFAULTS.title_font_size_px)), bold=True, font_family=str(font_family))

    panel = (
        float(_RENDER_DEFAULTS.get("panel_left_px", _DEFAULTS.panel_left_px)),
        float(_RENDER_DEFAULTS.get("panel_top_px", _DEFAULTS.panel_top_px)),
        float(canvas_width - _RENDER_DEFAULTS.get("panel_right_margin_px", _DEFAULTS.panel_right_margin_px)),
        float(canvas_height - _RENDER_DEFAULTS.get("panel_bottom_margin_px", _DEFAULTS.panel_bottom_margin_px)),
    )
    draw.rounded_rectangle(
        panel,
        radius=18,
        fill=tuple(int(v) for v in diagram_style.panel_fill_rgb),
        outline=tuple(int(v) for v in diagram_style.panel_border_rgb),
        width=3,
    )
    title_rgb = tuple(int(v) for v in diagram_style.label_rgb)
    pressure_bbox = _draw_label_box(
        draw,
        lines=(f"Constant pressure: P = {int(scenario.pressure_mpa)} MPa", "Use 1 MPa x L = 1 kJ"),
        center=(float(canvas_width * 0.5), float(panel[1] + 54.0)),
        font=title_font,
        style=diagram_style,
    )
    stroke_rgb = tuple(int(v) for v in diagram_style.stroke_rgb)
    gas_palette = (
        (92, 169, 219),
        (84, 184, 147),
        (139, 156, 224),
        (217, 153, 82),
        (177, 128, 202),
    )
    gas_rgb = gas_palette[int(hash64(int(instance_seed), f"{FAMILY_ID}.gas_color", 0) % len(gas_palette))]
    max_volume = max(_integer_support(params, "volume_l_support", _DEFAULTS.volume_l_support))
    jitter_x = float(rng.randint(-12, 12))
    jitter_y = float(rng.randint(-8, 8))

    if str(scenario.orientation) == "vertical_pair":
        left_center = (float(canvas_width * 0.32 + jitter_x), float(panel[3] - 104.0 + jitter_y))
        right_center = (float(canvas_width * 0.68 + jitter_x), float(panel[3] - 104.0 + jitter_y))
        initial_bbox, initial_piston_bbox = _draw_vertical_cylinder(
            draw,
            center=left_center,
            volume_l=int(scenario.initial_volume_l),
            max_volume_l=int(max_volume),
            scenario=scenario,
            style=diagram_style,
            font=label_font,
            label="Initial",
            gas_rgb=gas_rgb,
            render_defaults=_RENDER_DEFAULTS,
        )
        final_bbox, final_piston_bbox = _draw_vertical_cylinder(
            draw,
            center=right_center,
            volume_l=int(scenario.final_volume_l),
            max_volume_l=int(max_volume),
            scenario=scenario,
            style=diagram_style,
            font=label_font,
            label="Final",
            gas_rgb=gas_rgb,
            render_defaults=_RENDER_DEFAULTS,
        )
        arrow_start = (float(left_center[0] + 155.0), float(panel[1] + 210.0))
        arrow_end = (float(right_center[0] - 155.0), float(panel[1] + 210.0))
        initial_label_center = (float(left_center[0]), float(panel[3] - 36.0))
        final_label_center = (float(right_center[0]), float(panel[3] - 36.0))
    else:
        left_origin = (float(panel[0] + 96.0 + jitter_x), float(panel[1] + 330.0 + jitter_y))
        right_origin = (float(canvas_width * 0.57 + jitter_x), float(panel[1] + 330.0 + jitter_y))
        initial_bbox, initial_piston_bbox = _draw_horizontal_cylinder(
            draw,
            center=left_origin,
            volume_l=int(scenario.initial_volume_l),
            max_volume_l=int(max_volume),
            scenario=scenario,
            style=diagram_style,
            font=label_font,
            label="Initial",
            gas_rgb=gas_rgb,
            render_defaults=_RENDER_DEFAULTS,
        )
        final_bbox, final_piston_bbox = _draw_horizontal_cylinder(
            draw,
            center=right_origin,
            volume_l=int(scenario.final_volume_l),
            max_volume_l=int(max_volume),
            scenario=scenario,
            style=diagram_style,
            font=label_font,
            label="Final",
            gas_rgb=gas_rgb,
            render_defaults=_RENDER_DEFAULTS,
        )
        arrow_start = (float(panel[0] + 500.0), float(panel[1] + 330.0 + jitter_y))
        arrow_end = (float(panel[0] + 590.0), float(panel[1] + 330.0 + jitter_y))
        initial_label_center = (float(panel[0] + 266.0 + jitter_x), float(panel[3] - 76.0))
        final_label_center = (float(canvas_width * 0.72 + jitter_x), float(panel[3] - 76.0))

    draw_arrow(
        draw,
        start=arrow_start,
        end=arrow_end,
        fill=stroke_rgb,
        width=7,
        head_length_px=24,
        head_width_px=22,
    )
    arrow_label_bbox = draw_centered_text(
        draw,
        text="process",
        center=(float((arrow_start[0] + arrow_end[0]) * 0.5), float(arrow_start[1] - 28.0)),
        font=state_font,
        fill=title_rgb,
        stroke_fill=resolve_text_stroke_fill(title_rgb),
        stroke_width=1,
    )
    process_arrow_bbox = _bbox(
        _bbox_union(
            (
                min(arrow_start[0], arrow_end[0]) - 18.0,
                min(arrow_start[1], arrow_end[1]) - 18.0,
                max(arrow_start[0], arrow_end[0]) + 28.0,
                max(arrow_start[1], arrow_end[1]) + 18.0,
            ),
            arrow_label_bbox,
        )
    )
    initial_state_label = _draw_label_box(
        draw,
        lines=(f"P = {int(scenario.pressure_mpa)} MPa", f"Vi = {int(scenario.initial_volume_l)} L"),
        center=initial_label_center,
        font=state_font,
        style=diagram_style,
    )
    final_state_label = _draw_label_box(
        draw,
        lines=(f"P = {int(scenario.pressure_mpa)} MPa", f"Vf = {int(scenario.final_volume_l)} L"),
        center=final_label_center,
        font=state_font,
        style=diagram_style,
    )
    piston_cylinder_bbox = _bbox(_bbox_union(initial_bbox, final_bbox, initial_piston_bbox, final_piston_bbox, padding=8.0))

    image, post_noise_meta = apply_post_image_noise(
        background,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_map = {
        "piston_cylinder": piston_cylinder_bbox,
        "initial_state_label": initial_state_label,
        "final_state_label": final_state_label,
        "process_arrow": process_arrow_bbox,
    }
    scene_entities = [
        {"id": "piston_cylinder", "bbox_px": piston_cylinder_bbox},
        {"id": "initial_state_label", "pressure_mpa": int(scenario.pressure_mpa), "volume_l": int(scenario.initial_volume_l), "bbox_px": initial_state_label},
        {"id": "final_state_label", "pressure_mpa": int(scenario.pressure_mpa), "volume_l": int(scenario.final_volume_l), "bbox_px": final_state_label},
        {"id": "process_arrow", "bbox_px": process_arrow_bbox},
    ]
    render_map = {
        "query_id": QUERY_ID,
        "orientation": str(scenario.orientation),
        "pressure_mpa": int(scenario.pressure_mpa),
        "initial_volume_l": int(scenario.initial_volume_l),
        "final_volume_l": int(scenario.final_volume_l),
        "delta_volume_l": int(scenario.final_volume_l - scenario.initial_volume_l),
        "boundary_work_kj": int(scenario.boundary_work_kj),
        "initial_piston_bbox_px": initial_piston_bbox,
        "final_piston_bbox_px": final_piston_bbox,
        "pressure_label_bbox_px": pressure_bbox,
        "gas_rgb": list(int(v) for v in gas_rgb),
        "technical_diagram_style": dict(diagram_style_meta),
        "background_style": background_meta,
        "post_image_noise": post_noise_meta,
    }
    return _RenderedScene(
        image=image,
        annotation_bbox_map={str(key): list(value) for key, value in annotation_map.items()},
        scene_entities=scene_entities,
        render_map=render_map,
    )


@register_task
class PhysicsPistonCylinderBoundaryWorkValueTask:
    """Compute signed boundary work for a constant-pressure piston-cylinder process."""

    domain = "physics"
    task_group = "thermodynamics"
    task_id = TASK_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        scenario = _resolve_scenario(int(instance_seed), params)
        rendered = _render_piston_cylinder(
            instance_seed=int(instance_seed),
            params=params,
            scenario=scenario,
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
                f"answer_hint_{QUERY_ID}",
                f"annotation_hint_{QUERY_ID}",
            ),
            context=f"prompt defaults for {TASK_ID}",
        )
        answer_gt = TypedValue(type="integer", value=int(scenario.boundary_work_kj))
        annotation_gt = TypedValue(type="keyed_bbox_map", value={str(k): list(v) for k, v in rendered.annotation_bbox_map.items()})
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
            query_key=QUERY_ID,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{QUERY_ID}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{QUERY_ID}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.font",
            params=params,
        )
        font_record = get_font_family_record(str(font_family))
        trace_payload = {
            "scene_ir": {
                "scene_kind": "physics_piston_cylinder_constant_pressure",
                "entities": list(rendered.scene_entities),
                "relations": {
                    "query_id": QUERY_ID,
                    "pressure_mpa": int(scenario.pressure_mpa),
                    "initial_volume_l": int(scenario.initial_volume_l),
                    "final_volume_l": int(scenario.final_volume_l),
                    "boundary_work_kj": int(scenario.boundary_work_kj),
                    "orientation": str(scenario.orientation),
                },
            },
            "query_spec": {
                "query_id": QUERY_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": QUERY_ID,
                    "pressure_mpa": int(scenario.pressure_mpa),
                    "initial_volume_l": int(scenario.initial_volume_l),
                    "final_volume_l": int(scenario.final_volume_l),
                    "target_answer": int(scenario.boundary_work_kj),
                    "orientation": str(scenario.orientation),
                    "orientation_probabilities": dict(scenario.orientation_probabilities),
                    "pressure_mpa_probabilities": dict(scenario.pressure_probabilities),
                    "initial_volume_l_probabilities": dict(scenario.initial_volume_probabilities),
                    "final_volume_l_probabilities": dict(scenario.final_volume_probabilities),
                    "target_answer_probabilities": dict(scenario.target_answer_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(rendered.image.size[0]),
                "canvas_height": int(rendered.image.size[1]),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "piston_cylinder_diagram",
                },
                "technical_diagram_style": dict(rendered.render_map["technical_diagram_style"]),
                "background_style": dict(rendered.render_map["background_style"]),
                "post_image_noise": dict(rendered.render_map["post_image_noise"]),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "query_id": QUERY_ID,
                "pressure_mpa": int(scenario.pressure_mpa),
                "initial_volume_l": int(scenario.initial_volume_l),
                "final_volume_l": int(scenario.final_volume_l),
                "delta_volume_l": int(scenario.final_volume_l - scenario.initial_volume_l),
                "boundary_work_kj": int(scenario.boundary_work_kj),
                "target_answer": int(scenario.boundary_work_kj),
                "annotation_entity_ids": sorted(annotation_gt.value.keys()),
            },
            "witness_symbolic": {
                "type": "object_map",
                "ids": sorted(annotation_gt.value.keys()),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": dict(annotation_gt.value),
                "pixel_keyed_bbox_map": dict(annotation_gt.value),
            },
            "background": dict(rendered.render_map["background_style"]),
            "post_image_noise": dict(rendered.render_map["post_image_noise"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=rendered.image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=TaskComplexity(
                complexity_score=0.41,
                complexity_components={
                    "state_readout": 0.36,
                    "boundary_work_relation": 0.34,
                    "signed_delta_volume": 0.14,
                    "ambiguity": 0.06,
                    "output_burden": 0.10,
                },
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )
