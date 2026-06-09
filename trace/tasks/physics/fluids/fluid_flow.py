"""Physics fluids task for steady-flow continuity speed readouts."""

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


TASK_ID = "task_physics__fluid_flow__continuity_speed_value"
FAMILY_ID = "physics_fluids_fluid_flow_family"
SCENE_ID = "fluid_flow"
QUERY_ID = "continuity_missing_speed"
SUPPORTED_ORIENTATIONS: Tuple[str, ...] = ("horizontal_pipe", "vertical_pipe")
SUPPORTED_MISSING_STATIONS: Tuple[str, ...] = ("v1", "v2")

POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="fluids", apply_prob=0.5)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "fluids")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for fluid-flow continuity scenes."""

    canvas_width: int = 1120
    canvas_height: int = 720
    panel_margin_x_px: int = 58
    panel_margin_top_px: int = 52
    panel_margin_bottom_px: int = 58
    label_font_size_px: int = 24
    station_font_size_px: int = 28
    title_font_size_px: int = 28
    area_cm2_support: Tuple[int, ...] = (2, 3, 4, 5, 6, 8, 9, 10, 12)
    speed_m_s_support: Tuple[int, ...] = (2, 3, 4, 5, 6, 8, 9, 10, 12, 15, 16, 18, 20, 24)


@dataclass(frozen=True)
class _FlowScenario:
    """Resolved continuity scenario for a two-station flow diagram."""

    orientation: str
    missing_station: str
    area_1_cm2: int
    area_2_cm2: int
    speed_1_m_s: int
    speed_2_m_s: int
    target_answer: int
    orientation_probabilities: Dict[str, float]
    missing_station_probabilities: Dict[str, float]
    area_1_cm2_probabilities: Dict[str, float]
    area_2_cm2_probabilities: Dict[str, float]
    speed_1_m_s_probabilities: Dict[str, float]
    speed_2_m_s_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered fluid-flow scene plus prompt-facing annotation metadata."""

    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


_DEFAULTS = _TaskDefaults()


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _clamp_bbox(bbox: Sequence[float], *, width: int, height: int) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in bbox[:4]]
    return _bbox(
        (
            max(0.0, min(float(width - 1), x0)),
            max(0.0, min(float(height - 1), y0)),
            max(1.0, min(float(width), x1)),
            max(1.0, min(float(height), y1)),
        )
    )


def _integer_support(params: Mapping[str, Any], key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    return resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(key),
        fallback=fallback,
    )


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


def _normalize_missing_station(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    aliases = {
        "1": "v1",
        "station_1": "v1",
        "speed_1": "v1",
        "v1": "v1",
        "2": "v2",
        "station_2": "v2",
        "speed_2": "v2",
        "v2": "v2",
    }
    if text not in aliases:
        raise ValueError(f"unsupported missing_speed_station for {TASK_ID}: {value}")
    return aliases[text]


def _feasible_scenarios(params: Mapping[str, Any]) -> Tuple[Tuple[str, int, int, int, int, int], ...]:
    areas = _integer_support(params, "area_cm2_support", _DEFAULTS.area_cm2_support)
    speeds = _integer_support(params, "speed_m_s_support", _DEFAULTS.speed_m_s_support)
    speed_set = {int(value) for value in speeds}
    scenarios: List[Tuple[str, int, int, int, int, int]] = []
    for area_1 in areas:
        for area_2 in areas:
            if int(area_1) == int(area_2):
                continue
            for speed_1 in speeds:
                numerator = int(area_1) * int(speed_1)
                if numerator % int(area_2) != 0:
                    continue
                speed_2 = numerator // int(area_2)
                if int(speed_2) not in speed_set:
                    continue
                scenarios.append(("v2", int(area_1), int(area_2), int(speed_1), int(speed_2), int(speed_2)))
                scenarios.append(("v1", int(area_1), int(area_2), int(speed_1), int(speed_2), int(speed_1)))
    if not scenarios:
        raise ValueError("no feasible fluid-flow continuity scenarios for configured supports")
    return tuple(scenarios)


def _resolve_scenario(instance_seed: int, params: Mapping[str, Any]) -> _FlowScenario:
    query_id = str(params.get("query_id", QUERY_ID))
    if query_id != QUERY_ID:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {query_id}")

    orientation, orientation_probabilities = _resolve_orientation(int(instance_seed), params)
    area_support = _integer_support(params, "area_cm2_support", _DEFAULTS.area_cm2_support)
    speed_support = _integer_support(params, "speed_m_s_support", _DEFAULTS.speed_m_s_support)
    feasible = list(_feasible_scenarios(params))
    explicit_missing = _normalize_missing_station(params.get("missing_speed_station", params.get("missing_station")))
    explicit_area_1 = params.get("area_1_cm2", params.get("area1_cm2"))
    explicit_area_2 = params.get("area_2_cm2", params.get("area2_cm2"))
    explicit_speed_1 = params.get("speed_1_m_s", params.get("v1_m_s"))
    explicit_speed_2 = params.get("speed_2_m_s", params.get("v2_m_s"))
    explicit_answer = params.get("target_answer")

    candidates = list(feasible)
    if explicit_missing is not None:
        candidates = [item for item in candidates if str(item[0]) == str(explicit_missing)]
    if explicit_area_1 is not None:
        candidates = [item for item in candidates if int(item[1]) == int(explicit_area_1)]
    if explicit_area_2 is not None:
        candidates = [item for item in candidates if int(item[2]) == int(explicit_area_2)]
    if explicit_speed_1 is not None:
        candidates = [item for item in candidates if int(item[3]) == int(explicit_speed_1)]
    if explicit_speed_2 is not None:
        candidates = [item for item in candidates if int(item[4]) == int(explicit_speed_2)]
    if explicit_answer is not None:
        candidates = [item for item in candidates if int(item[5]) == int(explicit_answer)]
    if not candidates:
        raise ValueError("explicit fluid-flow parameters do not define a feasible continuity scenario")

    if explicit_missing is not None and explicit_area_1 is not None and explicit_area_2 is not None and (
        (explicit_speed_1 is not None and str(explicit_missing) == "v2")
        or (explicit_speed_2 is not None and str(explicit_missing) == "v1")
    ):
        selected_tuple = candidates[0]
    else:
        missing_values = sorted({str(item[0]) for item in candidates})
        if explicit_missing is None and bool(
            params.get("balanced_missing_station_sampling", group_default(_GEN_DEFAULTS, "balanced_missing_station_sampling", True))
        ):
            missing_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{FAMILY_ID}.missing_station",
            )
            selected_missing = str(missing_values[int(missing_index) % len(missing_values)])
            candidates = [item for item in candidates if str(item[0]) == selected_missing]

        answers = sorted({int(item[5]) for item in candidates})
        if explicit_answer is None and bool(
            params.get("balanced_target_answer_sampling", group_default(_GEN_DEFAULTS, "balanced_target_answer_sampling", True))
        ):
            answer_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{FAMILY_ID}.target_answer",
            )
            selected_answer = int(answers[int(answer_index) % len(answers)])
            candidates = [item for item in candidates if int(item[5]) == int(selected_answer)]
        elif explicit_answer is None:
            rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.target_answer")
            selected_answer = int(answers[int(rng.randrange(len(answers)))])
            candidates = [item for item in candidates if int(item[5]) == int(selected_answer)]

        tuple_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.scenario_tuple",
        )
        selected_tuple = candidates[int(tuple_index) % len(candidates)]

    missing_station, area_1, area_2, speed_1, speed_2, answer = selected_tuple
    return _FlowScenario(
        orientation=str(orientation),
        missing_station=str(missing_station),
        area_1_cm2=int(area_1),
        area_2_cm2=int(area_2),
        speed_1_m_s=int(speed_1),
        speed_2_m_s=int(speed_2),
        target_answer=int(answer),
        orientation_probabilities=orientation_probabilities,
        missing_station_probabilities=_probability_map(SUPPORTED_MISSING_STATIONS, selected=explicit_missing),
        area_1_cm2_probabilities=_uniform_int_probability_map(area_support, selected=int(area_1) if explicit_area_1 is not None else None),
        area_2_cm2_probabilities=_uniform_int_probability_map(area_support, selected=int(area_2) if explicit_area_2 is not None else None),
        speed_1_m_s_probabilities=_uniform_int_probability_map(speed_support, selected=int(speed_1) if explicit_speed_1 is not None else None),
        speed_2_m_s_probabilities=_uniform_int_probability_map(speed_support, selected=int(speed_2) if explicit_speed_2 is not None else None),
        target_answer_probabilities=_uniform_int_probability_map(
            sorted({int(item[5]) for item in feasible}),
            selected=int(answer) if explicit_answer is not None else None,
        ),
    )


def _pipe_size(area_cm2: int) -> float:
    return float(54.0 + 8.0 * (float(area_cm2) ** 0.5))


def _draw_label_box(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    center: Tuple[float, float],
    font: Any,
    style: Any,
    missing: bool = False,
) -> List[float]:
    text_bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
    text_w = float(text_bbox[2] - text_bbox[0])
    text_h = float(text_bbox[3] - text_bbox[1])
    pad_x = 13.0
    pad_y = 8.0
    cx, cy = float(center[0]), float(center[1])
    box = _bbox((cx - text_w / 2.0 - pad_x, cy - text_h / 2.0 - pad_y, cx + text_w / 2.0 + pad_x, cy + text_h / 2.0 + pad_y))
    if bool(missing):
        fill = (255, 235, 235)
        outline = (170, 42, 42)
        text_rgb = (178, 38, 38)
    else:
        fill = tuple(int(v) for v in style.label_fill_rgb)
        outline = tuple(int(v) for v in style.label_border_rgb)
        text_rgb = tuple(int(v) for v in style.label_rgb)
    draw.rounded_rectangle(tuple(box), radius=10, fill=fill, outline=outline, width=3)
    text_draw_bbox = draw_centered_text(
        draw,
        text=str(text),
        center=(cx, cy),
        font=font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )
    return _bbox(_bbox_union(box, text_draw_bbox))


def _draw_station_marker(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    label: str,
    font: Any,
    style: Any,
) -> List[float]:
    cx, cy = float(center[0]), float(center[1])
    radius = 21.0
    bbox = _bbox((cx - radius, cy - radius, cx + radius, cy + radius))
    draw.ellipse(tuple(bbox), fill=tuple(int(v) for v in style.label_fill_rgb), outline=tuple(int(v) for v in style.stroke_rgb), width=3)
    text_bbox = draw_centered_text(
        draw,
        text=str(label),
        center=(cx, cy),
        font=font,
        fill=tuple(int(v) for v in style.label_rgb),
        stroke_fill=resolve_text_stroke_fill(tuple(int(v) for v in style.label_rgb)),
        stroke_width=1,
    )
    return _bbox(_bbox_union(bbox, text_bbox))


def _draw_horizontal_flow(
    draw: ImageDraw.ImageDraw,
    *,
    scenario: _FlowScenario,
    style: Any,
    font: Any,
    station_font: Any,
    fluid_rgb: Tuple[int, int, int],
    panel: Sequence[float],
) -> Tuple[Dict[str, List[float]], Dict[str, Any]]:
    rng_offset = 0.0
    x1 = float(panel[0] + 255.0 + rng_offset)
    x2 = float(panel[2] - 255.0 + rng_offset)
    cy = float((panel[1] + panel[3]) * 0.52)
    h1 = _pipe_size(int(scenario.area_1_cm2))
    h2 = _pipe_size(int(scenario.area_2_cm2))
    stroke = tuple(int(v) for v in style.stroke_rgb)
    pipe_fill = tuple(min(255, int(v) + 42) for v in fluid_rgb)
    body_poly = [
        (x1, cy - h1 / 2.0),
        (x2, cy - h2 / 2.0),
        (x2, cy + h2 / 2.0),
        (x1, cy + h1 / 2.0),
    ]
    draw.polygon(body_poly, fill=pipe_fill, outline=stroke)
    draw.line(body_poly + [body_poly[0]], fill=stroke, width=5)
    draw.ellipse((x1 - 16.0, cy - h1 / 2.0, x1 + 16.0, cy + h1 / 2.0), fill=tuple(int(v) for v in fluid_rgb), outline=stroke, width=4)
    draw.ellipse((x2 - 16.0, cy - h2 / 2.0, x2 + 16.0, cy + h2 / 2.0), fill=tuple(int(v) for v in fluid_rgb), outline=stroke, width=4)

    arrow_start = (float(x1 + 102.0), cy)
    arrow_end = (float(x2 - 102.0), cy)
    draw_arrow(draw, start=arrow_start, end=arrow_end, fill=stroke, width=7, head_length_px=24, head_width_px=22)
    arrow_bbox = _bbox((arrow_start[0] - 12.0, arrow_start[1] - 18.0, arrow_end[0] + 30.0, arrow_end[1] + 18.0))

    marker_1 = _draw_station_marker(draw, center=(x1, cy - h1 / 2.0 - 46.0), label="1", font=station_font, style=style)
    marker_2 = _draw_station_marker(draw, center=(x2, cy - h2 / 2.0 - 46.0), label="2", font=station_font, style=style)
    area_1 = _draw_label_box(draw, text=f"A1 = {int(scenario.area_1_cm2)} cm^2", center=(x1, cy + max(h1, h2) / 2.0 + 58.0), font=font, style=style)
    area_2 = _draw_label_box(draw, text=f"A2 = {int(scenario.area_2_cm2)} cm^2", center=(x2, cy + max(h1, h2) / 2.0 + 58.0), font=font, style=style)
    speed_1_text = "v1 = ?" if str(scenario.missing_station) == "v1" else f"v1 = {int(scenario.speed_1_m_s)} m/s"
    speed_2_text = "v2 = ?" if str(scenario.missing_station) == "v2" else f"v2 = {int(scenario.speed_2_m_s)} m/s"
    speed_1 = _draw_label_box(draw, text=speed_1_text, center=(x1, cy + max(h1, h2) / 2.0 + 112.0), font=font, style=style, missing=str(scenario.missing_station) == "v1")
    speed_2 = _draw_label_box(draw, text=speed_2_text, center=(x2, cy + max(h1, h2) / 2.0 + 112.0), font=font, style=style, missing=str(scenario.missing_station) == "v2")
    pipe_bbox = _bbox((x1 - 20.0, cy - max(h1, h2) / 2.0 - 4.0, x2 + 20.0, cy + max(h1, h2) / 2.0 + 4.0))
    return (
        {
            "station_1": _bbox(_bbox_union(marker_1, area_1, speed_1, (x1 - 24.0, cy - h1 / 2.0, x1 + 24.0, cy + h1 / 2.0), padding=6.0)),
            "station_2": _bbox(_bbox_union(marker_2, area_2, speed_2, (x2 - 24.0, cy - h2 / 2.0, x2 + 24.0, cy + h2 / 2.0), padding=6.0)),
            "flow_path": _bbox(_bbox_union(pipe_bbox, arrow_bbox, padding=8.0)),
        },
        {
            "pipe_bbox_px": pipe_bbox,
            "flow_arrow_bbox_px": arrow_bbox,
            "station_1_center_px": [round(float(x1), 3), round(float(cy), 3)],
            "station_2_center_px": [round(float(x2), 3), round(float(cy), 3)],
        },
    )


def _draw_vertical_flow(
    draw: ImageDraw.ImageDraw,
    *,
    scenario: _FlowScenario,
    style: Any,
    font: Any,
    station_font: Any,
    fluid_rgb: Tuple[int, int, int],
    panel: Sequence[float],
) -> Tuple[Dict[str, List[float]], Dict[str, Any]]:
    cx = float((panel[0] + panel[2]) * 0.5)
    y1 = float(panel[1] + 204.0)
    y2 = float(panel[3] - 126.0)
    w1 = _pipe_size(int(scenario.area_1_cm2))
    w2 = _pipe_size(int(scenario.area_2_cm2))
    stroke = tuple(int(v) for v in style.stroke_rgb)
    pipe_fill = tuple(min(255, int(v) + 42) for v in fluid_rgb)
    body_poly = [
        (cx - w1 / 2.0, y1),
        (cx + w1 / 2.0, y1),
        (cx + w2 / 2.0, y2),
        (cx - w2 / 2.0, y2),
    ]
    draw.polygon(body_poly, fill=pipe_fill, outline=stroke)
    draw.line(body_poly + [body_poly[0]], fill=stroke, width=5)
    draw.ellipse((cx - w1 / 2.0, y1 - 16.0, cx + w1 / 2.0, y1 + 16.0), fill=tuple(int(v) for v in fluid_rgb), outline=stroke, width=4)
    draw.ellipse((cx - w2 / 2.0, y2 - 16.0, cx + w2 / 2.0, y2 + 16.0), fill=tuple(int(v) for v in fluid_rgb), outline=stroke, width=4)
    arrow_start = (cx, float(y1 + 88.0))
    arrow_end = (cx, float(y2 - 88.0))
    draw_arrow(draw, start=arrow_start, end=arrow_end, fill=stroke, width=7, head_length_px=24, head_width_px=22)
    arrow_bbox = _bbox((cx - 18.0, arrow_start[1] - 12.0, cx + 18.0, arrow_end[1] + 30.0))

    marker_1 = _draw_station_marker(draw, center=(cx - w1 / 2.0 - 48.0, y1), label="1", font=station_font, style=style)
    marker_2 = _draw_station_marker(draw, center=(cx + w2 / 2.0 + 48.0, y2), label="2", font=station_font, style=style)
    area_1 = _draw_label_box(draw, text=f"A1 = {int(scenario.area_1_cm2)} cm^2", center=(cx - 230.0, y1 + 48.0), font=font, style=style)
    area_2 = _draw_label_box(draw, text=f"A2 = {int(scenario.area_2_cm2)} cm^2", center=(cx + 230.0, y2 - 48.0), font=font, style=style)
    speed_1_text = "v1 = ?" if str(scenario.missing_station) == "v1" else f"v1 = {int(scenario.speed_1_m_s)} m/s"
    speed_2_text = "v2 = ?" if str(scenario.missing_station) == "v2" else f"v2 = {int(scenario.speed_2_m_s)} m/s"
    speed_1 = _draw_label_box(draw, text=speed_1_text, center=(cx - 230.0, y1 + 102.0), font=font, style=style, missing=str(scenario.missing_station) == "v1")
    speed_2 = _draw_label_box(draw, text=speed_2_text, center=(cx + 230.0, y2 + 6.0), font=font, style=style, missing=str(scenario.missing_station) == "v2")
    pipe_bbox = _bbox((cx - max(w1, w2) / 2.0 - 4.0, y1 - 20.0, cx + max(w1, w2) / 2.0 + 4.0, y2 + 20.0))
    return (
        {
            "station_1": _bbox(_bbox_union(marker_1, area_1, speed_1, (cx - w1 / 2.0, y1 - 24.0, cx + w1 / 2.0, y1 + 24.0), padding=6.0)),
            "station_2": _bbox(_bbox_union(marker_2, area_2, speed_2, (cx - w2 / 2.0, y2 - 24.0, cx + w2 / 2.0, y2 + 24.0), padding=6.0)),
            "flow_path": _bbox(_bbox_union(pipe_bbox, arrow_bbox, padding=8.0)),
        },
        {
            "pipe_bbox_px": pipe_bbox,
            "flow_arrow_bbox_px": arrow_bbox,
            "station_1_center_px": [round(float(cx), 3), round(float(y1), 3)],
            "station_2_center_px": [round(float(cx), 3), round(float(y2), 3)],
        },
    )


def _render_fluid_flow(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scenario: _FlowScenario,
) -> _RenderedScene:
    canvas_width = int(_RENDER_DEFAULTS.get("canvas_width", _DEFAULTS.canvas_width))
    canvas_height = int(_RENDER_DEFAULTS.get("canvas_height", _DEFAULTS.canvas_height))
    background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        task_group="fluids",
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        require_grid=True,
    )
    draw = ImageDraw.Draw(background)
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{FAMILY_ID}.font",
        params=params,
    )
    label_font = load_font(int(_RENDER_DEFAULTS.get("label_font_size_px", _DEFAULTS.label_font_size_px)), bold=True, font_family=str(font_family))
    station_font = load_font(int(_RENDER_DEFAULTS.get("station_font_size_px", _DEFAULTS.station_font_size_px)), bold=True, font_family=str(font_family))
    title_font = load_font(int(_RENDER_DEFAULTS.get("title_font_size_px", _DEFAULTS.title_font_size_px)), bold=True, font_family=str(font_family))
    panel = (
        float(_RENDER_DEFAULTS.get("panel_margin_x_px", _DEFAULTS.panel_margin_x_px)),
        float(_RENDER_DEFAULTS.get("panel_margin_top_px", _DEFAULTS.panel_margin_top_px)),
        float(canvas_width - _RENDER_DEFAULTS.get("panel_margin_x_px", _DEFAULTS.panel_margin_x_px)),
        float(canvas_height - _RENDER_DEFAULTS.get("panel_margin_bottom_px", _DEFAULTS.panel_margin_bottom_px)),
    )
    draw.rounded_rectangle(
        panel,
        radius=18,
        fill=tuple(int(v) for v in diagram_style.panel_fill_rgb),
        outline=tuple(int(v) for v in diagram_style.panel_border_rgb),
        width=3,
    )
    _draw_label_box(
        draw,
        text="Steady incompressible flow",
        center=(float(canvas_width * 0.5), float(panel[1] + 48.0)),
        font=title_font,
        style=diagram_style,
    )
    fluid_palette = (
        (85, 168, 220),
        (72, 184, 154),
        (126, 149, 217),
        (213, 143, 77),
        (153, 123, 196),
    )
    fluid_rgb = fluid_palette[int(hash64(int(instance_seed), f"{FAMILY_ID}.fluid_color", 0) % len(fluid_palette))]
    if str(scenario.orientation) == "vertical_pipe":
        annotation_map, render_geometry = _draw_vertical_flow(
            draw,
            scenario=scenario,
            style=diagram_style,
            font=label_font,
            station_font=station_font,
            fluid_rgb=fluid_rgb,
            panel=panel,
        )
    else:
        annotation_map, render_geometry = _draw_horizontal_flow(
            draw,
            scenario=scenario,
            style=diagram_style,
            font=label_font,
            station_font=station_font,
            fluid_rgb=fluid_rgb,
            panel=panel,
        )

    image, post_noise_meta = apply_post_image_noise(
        background,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    annotation_map = {
        str(key): _clamp_bbox(value, width=int(image.size[0]), height=int(image.size[1]))
        for key, value in annotation_map.items()
    }
    scene_entities = [
        {"id": "station_1", "area_cm2": int(scenario.area_1_cm2), "speed_m_s": int(scenario.speed_1_m_s), "bbox_px": list(annotation_map["station_1"])},
        {"id": "station_2", "area_cm2": int(scenario.area_2_cm2), "speed_m_s": int(scenario.speed_2_m_s), "bbox_px": list(annotation_map["station_2"])},
        {"id": "flow_path", "bbox_px": list(annotation_map["flow_path"])},
    ]
    render_map = {
        "query_id": QUERY_ID,
        "orientation": str(scenario.orientation),
        "missing_station": str(scenario.missing_station),
        "area_1_cm2": int(scenario.area_1_cm2),
        "area_2_cm2": int(scenario.area_2_cm2),
        "speed_1_m_s": int(scenario.speed_1_m_s),
        "speed_2_m_s": int(scenario.speed_2_m_s),
        "target_answer": int(scenario.target_answer),
        "continuity_lhs": int(scenario.area_1_cm2 * scenario.speed_1_m_s),
        "continuity_rhs": int(scenario.area_2_cm2 * scenario.speed_2_m_s),
        "fluid_rgb": list(int(v) for v in fluid_rgb),
        "technical_diagram_style": dict(diagram_style_meta),
        "background_style": background_meta,
        "post_image_noise": post_noise_meta,
    }
    render_map.update(render_geometry)
    return _RenderedScene(
        image=image,
        annotation_bbox_map=annotation_map,
        scene_entities=scene_entities,
        render_map=render_map,
    )


@register_task
class PhysicsFluidFlowContinuitySpeedValueTask:
    """Compute a missing steady-flow speed from continuity."""

    domain = "physics"
    task_group = "fluids"
    task_id = TASK_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        scenario = _resolve_scenario(int(instance_seed), params)
        rendered = _render_fluid_flow(
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
        answer_gt = TypedValue(type="integer", value=int(scenario.target_answer))
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
                "scene_kind": "physics_fluid_flow_continuity",
                "entities": list(rendered.scene_entities),
                "relations": {
                    "query_id": QUERY_ID,
                    "missing_station": str(scenario.missing_station),
                    "area_1_cm2": int(scenario.area_1_cm2),
                    "area_2_cm2": int(scenario.area_2_cm2),
                    "speed_1_m_s": int(scenario.speed_1_m_s),
                    "speed_2_m_s": int(scenario.speed_2_m_s),
                    "target_answer": int(scenario.target_answer),
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
                    "missing_station": str(scenario.missing_station),
                    "area_1_cm2": int(scenario.area_1_cm2),
                    "area_2_cm2": int(scenario.area_2_cm2),
                    "speed_1_m_s": int(scenario.speed_1_m_s),
                    "speed_2_m_s": int(scenario.speed_2_m_s),
                    "target_answer": int(scenario.target_answer),
                    "orientation": str(scenario.orientation),
                    "orientation_probabilities": dict(scenario.orientation_probabilities),
                    "missing_station_probabilities": dict(scenario.missing_station_probabilities),
                    "area_1_cm2_probabilities": dict(scenario.area_1_cm2_probabilities),
                    "area_2_cm2_probabilities": dict(scenario.area_2_cm2_probabilities),
                    "speed_1_m_s_probabilities": dict(scenario.speed_1_m_s_probabilities),
                    "speed_2_m_s_probabilities": dict(scenario.speed_2_m_s_probabilities),
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
                    "scope": "fluid_flow_diagram",
                },
                "technical_diagram_style": dict(rendered.render_map["technical_diagram_style"]),
                "background_style": dict(rendered.render_map["background_style"]),
                "post_image_noise": dict(rendered.render_map["post_image_noise"]),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "query_id": QUERY_ID,
                "missing_station": str(scenario.missing_station),
                "area_1_cm2": int(scenario.area_1_cm2),
                "area_2_cm2": int(scenario.area_2_cm2),
                "speed_1_m_s": int(scenario.speed_1_m_s),
                "speed_2_m_s": int(scenario.speed_2_m_s),
                "continuity_lhs": int(scenario.area_1_cm2 * scenario.speed_1_m_s),
                "continuity_rhs": int(scenario.area_2_cm2 * scenario.speed_2_m_s),
                "target_answer": int(scenario.target_answer),
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
                complexity_score=0.38,
                complexity_components={
                    "station_readout": 0.34,
                    "continuity_relation": 0.32,
                    "arithmetic": 0.14,
                    "ambiguity": 0.08,
                    "output_burden": 0.12,
                },
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )
