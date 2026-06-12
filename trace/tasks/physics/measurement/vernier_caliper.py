"""Physics measurement task for Vernier caliper readout diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.bbox_projection import bbox_union_many as _bbox_union_many
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.drawing import draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_legibility import draw_text_traced
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "task_physics__vernier_caliper__length_readout_value"
TASK_NAMESPACE = "physics_measurement_vernier_caliper"
SCENE_ID = "vernier_caliper"
QUERY_ID = "main_scale_vernier_mm"
VERNIER_DIVISIONS = 10
VERNIER_RESOLUTION_MM = 0.1

POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="measurement", apply_prob=0.5)
_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "measurement")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_NAMESPACE,
)


@dataclass(frozen=True)
class _CaliperScenario:
    """Resolved Vernier caliper measurement."""

    main_mm: int
    aligned_vernier_tick: int
    answer_mm: float
    target_answer_probabilities: Dict[str, float]
    main_mm_probabilities: Dict[str, float]
    aligned_vernier_tick_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _RenderedScene:
    """Rendered caliper and verifier payload fragments."""

    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for Vernier caliper scenes."""

    canvas_width: int = 1180
    canvas_height: int = 720
    panel_left_px: int = 58
    panel_top_px: int = 54
    panel_right_margin_px: int = 58
    panel_bottom_margin_px: int = 58
    main_scale_left_px: int = 174
    main_scale_y_px: int = 266
    mm_px: int = 13
    main_scale_max_mm: int = 70
    label_font_size_px: int = 22
    small_font_size_px: int = 17
    title_font_size_px: int = 28
    jaw_top_px: int = 170
    jaw_bottom_px: int = 510


_DEFAULTS = _TaskDefaults()


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _probability_map(values: Sequence[int], selected: int | None = None) -> Dict[str, float]:
    if selected is not None:
        return {str(int(value)): (1.0 if int(value) == int(selected) else 0.0) for value in values}
    if not values:
        return {}
    probability = 1.0 / float(len(values))
    return {str(int(value)): float(probability) for value in values}


def _main_mm_support() -> Tuple[int, ...]:
    raw = group_default(_GEN_DEFAULTS, "main_mm_support", tuple(range(8, 56)))
    support = tuple(sorted({int(value) for value in raw}))
    if not support:
        raise ValueError("main_mm_support must contain at least one integer")
    return support


def _aligned_tick_support() -> Tuple[int, ...]:
    raw = group_default(_GEN_DEFAULTS, "aligned_vernier_tick_support", tuple(range(1, VERNIER_DIVISIONS)))
    support = tuple(sorted({int(value) for value in raw}))
    if not support or any(value < 0 or value >= VERNIER_DIVISIONS for value in support):
        raise ValueError("aligned_vernier_tick_support must be in 0..9")
    return support


def _resolve_scenario(instance_seed: int, params: Mapping[str, Any]) -> _CaliperScenario:
    explicit_query = str(params.get("query_id") or QUERY_ID).strip()
    if explicit_query != QUERY_ID:
        raise ValueError(f"unsupported query_id for {TASK_ID}: {explicit_query}")

    main_support = _main_mm_support()
    tick_support = _aligned_tick_support()
    explicit_main = params.get("main_mm")
    explicit_tick = params.get("aligned_vernier_tick", params.get("vernier_tick"))
    explicit_answer = params.get("target_answer", params.get("answer_mm"))
    if explicit_answer is not None:
        answer_tenths = int(round(float(explicit_answer) * 10.0))
        inferred_main_mm = int(answer_tenths // 10)
        inferred_aligned_tick = int(answer_tenths % 10)
        main_mm = int(explicit_main) if explicit_main is not None else int(inferred_main_mm)
        aligned_tick = int(explicit_tick) if explicit_tick is not None else int(inferred_aligned_tick)
        if main_mm not in set(main_support) or aligned_tick not in set(tick_support):
            raise ValueError(f"unsupported target_answer for {TASK_ID}: {explicit_answer}")
        if int(main_mm * 10 + aligned_tick) != int(answer_tenths):
            raise ValueError("target_answer is inconsistent with explicit main_mm or aligned_vernier_tick")
    else:
        if explicit_main is not None:
            main_mm = int(explicit_main)
            if main_mm not in set(main_support):
                raise ValueError(f"main_mm={main_mm} is outside configured support")
        else:
            index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_NAMESPACE}.main_mm",
            )
            main_mm = int(main_support[int(index) % len(main_support)])

        if explicit_tick is not None:
            aligned_tick = int(explicit_tick)
            if aligned_tick not in set(tick_support):
                raise ValueError(f"aligned_vernier_tick={aligned_tick} is outside configured support")
        else:
            index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_NAMESPACE}.aligned_vernier_tick",
            )
            aligned_tick = int(tick_support[int(index) % len(tick_support)])

    answer_tenths = int(main_mm * 10 + aligned_tick)
    answer_mm = round(float(answer_tenths) / 10.0, 1)
    answer_support = [int(main * 10 + tick) for main in main_support for tick in tick_support]
    selected = int(answer_tenths)
    return _CaliperScenario(
        main_mm=int(main_mm),
        aligned_vernier_tick=int(aligned_tick),
        answer_mm=float(answer_mm),
        target_answer_probabilities={f"{value / 10.0:.1f}": (1.0 if int(value) == selected else 0.0) for value in answer_support},
        main_mm_probabilities=_probability_map(main_support, selected=int(main_mm)),
        aligned_vernier_tick_probabilities=uniform_probability_map(tick_support, selected=int(aligned_tick)),
    )


def _draw_label(
    draw: ImageDraw.ImageDraw,
    xy: Tuple[float, float],
    text: str,
    font: Any,
    fill: Tuple[int, int, int],
    *,
    anchor: str = "mm",
    backing_fill: Tuple[int, int, int] | None = None,
) -> List[float]:
    stroke_width = 1
    if backing_fill is not None:
        text_bbox = draw.textbbox(
            (float(xy[0]), float(xy[1])),
            str(text),
            font=font,
            stroke_width=stroke_width,
            anchor=anchor,
        )
        pad_x = 7.0
        pad_y = 4.0
        backing_bbox = (
            float(text_bbox[0]) - pad_x,
            float(text_bbox[1]) - pad_y,
            float(text_bbox[2]) + pad_x,
            float(text_bbox[3]) + pad_y,
        )
        draw.rounded_rectangle(
            backing_bbox,
            radius=5,
            fill=tuple(int(value) for value in backing_fill),
            outline=tuple(int(value) for value in backing_fill),
            width=1,
        )
    record = draw_text_traced(
        draw,
        (float(xy[0]), float(xy[1])),
        str(text),
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=resolve_text_stroke_fill(fill),
        role="readout",
        required=True,
        anchor=anchor,
    )
    return _bbox(record["bbox_px"])


def _draw_main_scale(
    draw: ImageDraw.ImageDraw,
    *,
    left_x: float,
    scale_y: float,
    mm_px: float,
    max_mm: int,
    font_family: str,
    style: Any,
) -> Tuple[Dict[int, List[float]], Dict[int, float], List[float]]:
    stroke = tuple(int(value) for value in style.stroke_rgb)
    guide = tuple(int(value) for value in style.guide_rgb)
    label_rgb = tuple(int(value) for value in style.label_rgb)
    backing_fill = tuple(int(value) for value in style.label_fill_rgb)
    label_font = load_font(int(_RENDER_DEFAULTS.get("label_font_size_px", _DEFAULTS.label_font_size_px)), bold=True, font_family=font_family)
    small_font = load_font(int(_RENDER_DEFAULTS.get("small_font_size_px", _DEFAULTS.small_font_size_px)), bold=True, font_family=font_family)
    body_top = float(scale_y - 46.0)
    body_bottom = float(scale_y + 42.0)
    right_x = float(left_x + max_mm * mm_px)
    label_y = float(body_top - 18.0)
    draw.rounded_rectangle(
        (left_x - 22.0, body_top, right_x + 24.0, body_bottom),
        radius=13,
        fill=tuple(int(value) for value in style.panel_alt_fill_rgb),
        outline=stroke,
        width=3,
    )
    draw.line((left_x, scale_y, right_x, scale_y), fill=stroke, width=4)

    tick_bboxes: List[List[float]] = []
    tick_bbox_map: Dict[int, List[float]] = {}
    label_bboxes: List[List[float]] = []
    tick_xs: Dict[int, float] = {}
    for tick in range(0, int(max_mm) + 1):
        x = float(left_x + tick * mm_px)
        tick_xs[int(tick)] = x
        if tick % 10 == 0:
            tick_len = 37.0
            tick_width = 3
        elif tick % 5 == 0:
            tick_len = 28.0
            tick_width = 2
        else:
            tick_len = 18.0
            tick_width = 1
        draw.line((x, scale_y, x, scale_y - tick_len), fill=stroke if tick % 5 == 0 else guide, width=tick_width)
        tick_bbox = _bbox((x - 2.0, scale_y - tick_len - 2.0, x + 2.0, scale_y + 2.0))
        tick_bboxes.append(tick_bbox)
        tick_bbox_map[int(tick)] = tick_bbox
        if tick % 10 == 0:
            label_bboxes.append(_draw_label(draw, (x, label_y), str(tick), label_font, label_rgb, backing_fill=backing_fill))
    unit_bbox = _draw_label(draw, (right_x + 38.0, label_y), "mm", small_font, label_rgb, backing_fill=backing_fill)
    scale_bbox = _bbox(_bbox_union_many(*(tick_bboxes + label_bboxes + [unit_bbox]), padding=8.0))
    return tick_bbox_map, tick_xs, scale_bbox


def _draw_caliper(
    draw: ImageDraw.ImageDraw,
    *,
    scenario: _CaliperScenario,
    font_family: str,
    style: Any,
    render_defaults: Mapping[str, Any],
    layout_shift: Tuple[float, float],
    accent_rgb: Tuple[int, int, int],
) -> Tuple[Dict[str, List[float]], Dict[str, Any], List[Dict[str, Any]]]:
    dx, dy = float(layout_shift[0]), float(layout_shift[1])
    left_x = float(render_defaults.get("main_scale_left_px", _DEFAULTS.main_scale_left_px)) + dx
    scale_y = float(render_defaults.get("main_scale_y_px", _DEFAULTS.main_scale_y_px)) + dy
    mm_px = float(render_defaults.get("mm_px", _DEFAULTS.mm_px))
    max_mm = int(render_defaults.get("main_scale_max_mm", _DEFAULTS.main_scale_max_mm))
    jaw_top = float(render_defaults.get("jaw_top_px", _DEFAULTS.jaw_top_px)) + dy
    jaw_bottom = float(render_defaults.get("jaw_bottom_px", _DEFAULTS.jaw_bottom_px)) + dy
    stroke = tuple(int(value) for value in style.stroke_rgb)
    guide = tuple(int(value) for value in style.guide_rgb)
    label_rgb = tuple(int(value) for value in style.label_rgb)
    backing_fill = tuple(int(value) for value in style.label_fill_rgb)
    title_font = load_font(int(render_defaults.get("title_font_size_px", _DEFAULTS.title_font_size_px)), bold=True, font_family=font_family)
    label_font = load_font(int(render_defaults.get("small_font_size_px", _DEFAULTS.small_font_size_px)), bold=True, font_family=font_family)

    tick_bbox_map, _tick_xs, full_main_scale_region = _draw_main_scale(
        draw,
        left_x=left_x,
        scale_y=scale_y,
        mm_px=mm_px,
        max_mm=max_mm,
        font_family=font_family,
        style=style,
    )
    vernier_zero_x = float(left_x + (float(scenario.main_mm) + float(scenario.aligned_vernier_tick) * VERNIER_RESOLUTION_MM) * mm_px)
    moving_body_top = float(scale_y + 72.0)
    moving_body_bottom = float(scale_y + 174.0)
    vernier_span_px = float((VERNIER_DIVISIONS - 1) * mm_px)
    vernier_right = float(vernier_zero_x + vernier_span_px)

    title_bbox = draw_centered_text(
        draw,
        text="Vernier caliper",
        center=(float(left_x + max_mm * mm_px * 0.5), float(jaw_top - 40.0)),
        font=title_font,
        fill=label_rgb,
        stroke_fill=resolve_text_stroke_fill(label_rgb),
        stroke_width=1,
    )

    rail_y = float(scale_y + 8.0)
    draw.rounded_rectangle(
        (left_x - 68.0, rail_y - 18.0, left_x + max_mm * mm_px + 66.0, rail_y + 16.0),
        radius=12,
        fill=tuple(int(value) for value in style.muted_fill_rgb),
        outline=stroke,
        width=3,
    )

    fixed_jaw_x = left_x
    jaw_fill = tuple(int(value) for value in style.panel_alt_fill_rgb)
    draw.polygon(
        [
            (fixed_jaw_x - 45.0, jaw_top),
            (fixed_jaw_x + 14.0, jaw_top),
            (fixed_jaw_x + 14.0, jaw_bottom),
            (fixed_jaw_x - 15.0, jaw_bottom),
            (fixed_jaw_x - 15.0, scale_y + 52.0),
            (fixed_jaw_x - 45.0, scale_y + 26.0),
        ],
        fill=jaw_fill,
        outline=stroke,
    )
    draw.line((fixed_jaw_x + 14.0, jaw_top, fixed_jaw_x + 14.0, jaw_bottom), fill=stroke, width=4)

    draw.rounded_rectangle(
        (vernier_zero_x - 18.0, moving_body_top, vernier_right + 26.0, moving_body_bottom),
        radius=12,
        fill=tuple(int(value) for value in style.panel_fill_rgb),
        outline=stroke,
        width=3,
    )
    draw.polygon(
        [
            (vernier_zero_x - 10.0, jaw_top + 10.0),
            (vernier_zero_x + 42.0, jaw_top + 10.0),
            (vernier_zero_x + 42.0, scale_y + 78.0),
            (vernier_zero_x + 15.0, scale_y + 78.0),
            (vernier_zero_x + 15.0, jaw_bottom),
            (vernier_zero_x - 10.0, jaw_bottom),
        ],
        fill=tuple(int(value) for value in style.panel_fill_rgb),
        outline=stroke,
    )
    draw.line((vernier_zero_x, jaw_top + 8.0, vernier_zero_x, jaw_bottom), fill=stroke, width=4)

    measured_object_bbox = _bbox((fixed_jaw_x + 16.0, jaw_bottom - 104.0, vernier_zero_x - 4.0, jaw_bottom - 34.0))
    object_fill = tuple(int(value) for value in accent_rgb)
    if measured_object_bbox[2] - measured_object_bbox[0] > 24.0:
        draw.rounded_rectangle(tuple(measured_object_bbox), radius=10, fill=object_fill, outline=stroke, width=3)

    vernier_y = float(moving_body_top + 24.0)
    vernier_label_bboxes: List[List[float]] = []
    vernier_tick_bboxes: List[List[float]] = []
    for tick in range(0, VERNIER_DIVISIONS):
        x = float(vernier_zero_x + tick * (0.9 * mm_px))
        tick_len = 42.0 if tick in (0, VERNIER_DIVISIONS - 1) else 30.0
        draw.line((x, vernier_y, x, vernier_y + tick_len), fill=stroke if tick in (0, VERNIER_DIVISIONS - 1) else guide, width=2)
        vernier_tick_bboxes.append(_bbox((x - 2.0, vernier_y - 2.0, x + 2.0, vernier_y + tick_len + 2.0)))
        if tick in (0, 5, 9):
            label_x = x + 7.0 if tick == 0 else x
            vernier_label_bboxes.append(
                _draw_label(
                    draw,
                    (label_x, vernier_y + tick_len + 20.0),
                    str(tick),
                    label_font,
                    label_rgb,
                    backing_fill=backing_fill,
                )
            )
    vernier_zero_bbox = _bbox((vernier_zero_x - 8.0, vernier_y - 8.0, vernier_zero_x + 8.0, vernier_y + 52.0))
    aligned_tick_x = float(vernier_zero_x + int(scenario.aligned_vernier_tick) * (0.9 * mm_px))
    aligned_tick_bbox = _bbox((aligned_tick_x - 8.0, vernier_y - 8.0, aligned_tick_x + 8.0, vernier_y + 56.0))
    vernier_scale_region = _bbox(_bbox_union_many(*(vernier_tick_bboxes + vernier_label_bboxes), padding=8.0))

    nearest_main_tick = int(scenario.main_mm + scenario.aligned_vernier_tick)
    local_tick_keys = [
        tick
        for tick in range(max(0, int(scenario.main_mm) - 2), min(max_mm, int(scenario.main_mm + scenario.aligned_vernier_tick) + 2) + 1)
        if tick in tick_bbox_map
    ]
    local_scale_boxes = [tick_bbox_map[tick] for tick in local_tick_keys]
    main_scale_region = _bbox(_bbox_union_many(*local_scale_boxes, padding=8.0)) if local_scale_boxes else full_main_scale_region

    reading_text = "0.1 mm vernier"
    _draw_label(
        draw,
        (float(vernier_right + 90.0), float(moving_body_top + 18.0)),
        reading_text,
        label_font,
        label_rgb,
        backing_fill=backing_fill,
    )

    annotation_map = {
        "main_scale_region": main_scale_region,
        "vernier_zero": vernier_zero_bbox,
        "vernier_scale_region": vernier_scale_region,
        "aligned_vernier_tick": aligned_tick_bbox,
    }
    scene_entities = [
        {"id": key, "bbox_px": list(value)}
        for key, value in annotation_map.items()
    ]
    render_map = {
        "main_mm": int(scenario.main_mm),
        "aligned_vernier_tick": int(scenario.aligned_vernier_tick),
        "vernier_resolution_mm": float(VERNIER_RESOLUTION_MM),
        "answer_mm": float(scenario.answer_mm),
        "main_scale_max_mm": int(max_mm),
        "mm_px": round(float(mm_px), 3),
        "vernier_zero_x_px": round(float(vernier_zero_x), 3),
        "aligned_vernier_tick_x_px": round(float(aligned_tick_x), 3),
        "nearest_aligned_main_tick": int(nearest_main_tick),
        "full_main_scale_region_px": list(full_main_scale_region),
        "title_bbox_px": list(title_bbox),
        "measured_object_bbox_px": measured_object_bbox,
    }
    return annotation_map, render_map, scene_entities


def _render_caliper(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    scenario: _CaliperScenario,
) -> _RenderedScene:
    canvas_width = int(_RENDER_DEFAULTS.get("canvas_width", _DEFAULTS.canvas_width))
    canvas_height = int(_RENDER_DEFAULTS.get("canvas_height", _DEFAULTS.canvas_height))
    background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
        instance_seed=int(instance_seed),
        params=params,
        scene_id=SCENE_ID,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        require_grid=True,
    )
    draw = ImageDraw.Draw(background)
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.render")
    panel = (
        float(_RENDER_DEFAULTS.get("panel_left_px", _DEFAULTS.panel_left_px)),
        float(_RENDER_DEFAULTS.get("panel_top_px", _DEFAULTS.panel_top_px)),
        float(canvas_width - int(_RENDER_DEFAULTS.get("panel_right_margin_px", _DEFAULTS.panel_right_margin_px))),
        float(canvas_height - int(_RENDER_DEFAULTS.get("panel_bottom_margin_px", _DEFAULTS.panel_bottom_margin_px))),
    )
    draw.rounded_rectangle(
        panel,
        radius=20,
        fill=tuple(int(value) for value in diagram_style.panel_fill_rgb),
        outline=tuple(int(value) for value in diagram_style.panel_border_rgb),
        width=3,
    )
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_NAMESPACE}.font",
        params=params,
    )
    font_record = get_font_family_record(str(font_family))
    object_palette = (
        (215, 90, 74),
        (75, 146, 216),
        (63, 159, 112),
        (190, 129, 55),
        (143, 99, 190),
    )
    object_rgb = object_palette[int(hash64(int(instance_seed), f"{TASK_NAMESPACE}.object_color", 0) % len(object_palette))]
    annotation_map, render_map, scene_entities = _draw_caliper(
        draw,
        scenario=scenario,
        font_family=str(font_family),
        style=diagram_style,
        render_defaults=_RENDER_DEFAULTS,
        layout_shift=(float(rng.randint(-18, 18)), float(rng.randint(-8, 12))),
        accent_rgb=object_rgb,
    )
    image, post_noise_meta = apply_post_image_noise(
        background,
        instance_seed=int(instance_seed),
        params=params,
        default_config=POST_IMAGE_NOISE_DEFAULTS,
    )
    render_map.update(
        {
            "object_rgb": list(int(value) for value in object_rgb),
            "font": {
                "font_family": str(font_family),
                "font_asset_version": font_asset_version(),
                "font_asset": font_record.to_trace(),
            },
            "technical_diagram_style": dict(diagram_style_meta),
            "background_style": dict(background_meta),
            "post_image_noise": dict(post_noise_meta),
        }
    )
    return _RenderedScene(
        image=image,
        annotation_bbox_map={str(key): list(value) for key, value in annotation_map.items()},
        scene_entities=list(scene_entities),
        render_map=render_map,
    )


@register_task
class PhysicsVernierCaliperLengthReadoutValueTask:
    """Read a length from a visible Vernier caliper."""

    domain = "physics"
    scene_id = "measurement"
    task_id = TASK_ID
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        scenario = _resolve_scenario(int(instance_seed), params)
        rendered = _render_caliper(instance_seed=int(instance_seed), params=params, scenario=scenario)
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
        answer_gt = TypedValue(type="number", value=float(scenario.answer_mm))
        annotation_gt = TypedValue(type="keyed_bbox_map", value={str(key): list(value) for key, value in rendered.annotation_bbox_map.items()})
        json_example, json_example_answer_only = build_prompt_json_examples(
            annotation_value=annotation_gt.value,
            answer_type=str(answer_gt.type),
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
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
        trace_payload = {
            "scene_ir": {
                "scene_kind": "physics_vernier_caliper_readout",
                "entities": list(rendered.scene_entities),
                "relations": {
                    "query_id": QUERY_ID,
                    "main_mm": int(scenario.main_mm),
                    "aligned_vernier_tick": int(scenario.aligned_vernier_tick),
                    "vernier_resolution_mm": float(VERNIER_RESOLUTION_MM),
                    "answer_mm": float(scenario.answer_mm),
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
                    "main_mm": int(scenario.main_mm),
                    "aligned_vernier_tick": int(scenario.aligned_vernier_tick),
                    "target_answer": float(scenario.answer_mm),
                    "main_mm_probabilities": dict(scenario.main_mm_probabilities),
                    "aligned_vernier_tick_probabilities": dict(scenario.aligned_vernier_tick_probabilities),
                    "target_answer_probabilities": dict(scenario.target_answer_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(rendered.image.size[0]),
                "canvas_height": int(rendered.image.size[1]),
                "font": {
                    "font_family": str(rendered.render_map["font"]["font"]),
                    "font_asset_version": str(rendered.render_map["font"]["font_asset_version"]),
                    "font_asset": dict(rendered.render_map["font"]["font_asset"]),
                    "scope": "vernier_caliper_diagram",
                },
                "technical_diagram_style": dict(rendered.render_map["technical_diagram_style"]),
                "background_style": dict(rendered.render_map["background_style"]),
                "post_image_noise": dict(rendered.render_map["post_image_noise"]),
            },
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "query_id": QUERY_ID,
                "main_mm": int(scenario.main_mm),
                "aligned_vernier_tick": int(scenario.aligned_vernier_tick),
                "vernier_resolution_mm": float(VERNIER_RESOLUTION_MM),
                "target_answer": float(scenario.answer_mm),
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )
