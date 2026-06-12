"""Physics magnetism task for counting induced-current directions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from random import Random
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.types import TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_arrow, draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_NAMESPACE = "physics_magnetism_electromagnetic_induction"
TASK_ID = "task_physics__electromagnetic_induction__induced_current_direction_count"
SCENE_ID = "electromagnetic_induction"
QUERY_IDS: Tuple[str, ...] = (
    "clockwise_induced_current_count",
    "counterclockwise_induced_current_count",
    "no_induced_current_count",
)
QUERY_TO_CURRENT_CLASS: Dict[str, str] = {
    "clockwise_induced_current_count": "clockwise",
    "counterclockwise_induced_current_count": "counterclockwise",
    "no_induced_current_count": "no_current",
}
CURRENT_CLASSES: Tuple[str, ...] = ("clockwise", "counterclockwise", "no_current")
FIELD_ORIENTATIONS: Tuple[str, ...] = ("into_page", "out_of_page")
ANSWER_SUPPORT: Tuple[int, ...] = tuple(range(7))
PANEL_COUNT = 6
PANEL_MECHANISMS_BY_FLUX_CHANGE: Dict[str, Tuple[str, ...]] = {
    "increasing": ("loop_enters_field", "field_strength_increases", "loop_area_expands"),
    "decreasing": ("loop_leaves_field", "field_strength_decreases", "loop_area_contracts"),
    "none": ("loop_slides_inside_uniform_field", "stationary_constant_field"),
}

POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(scene_id="magnetism", apply_prob=0.5)
_TASK_GROUP_DEFAULTS = get_scene_defaults("physics", "magnetism")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_NAMESPACE,
)


@dataclass(frozen=True)
class _PanelSpec:
    panel_id: str
    current_class: str
    field_orientation: str
    flux_change: str
    mechanism: str
    region_side: str
    bbox_px: List[float]


@dataclass(frozen=True)
class _InductionScenario:
    query_id: str
    target_current_class: str
    target_answer: int
    panels: Tuple[_PanelSpec, ...]
    query_id_probabilities: Dict[str, float]
    target_answer_probabilities: Dict[str, float]


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _uniform_probability_map(values: Sequence[Any]) -> Dict[str, float]:
    if not values:
        return {}
    weight = 1.0 / float(len(values))
    return {str(value): float(weight) for value in values}


def _selected_probability_map(selected: Any) -> Dict[str, float]:
    return {str(selected): 1.0}


def _resolve_query_id(instance_seed: int, params: Mapping[str, Any]) -> Tuple[str, Dict[str, float]]:
    explicit = params.get("query_id")
    if explicit is not None:
        query_id = str(explicit)
        if query_id not in QUERY_IDS:
            raise ValueError(f"unsupported query_id for {TASK_ID}: {query_id}")
        return query_id, _selected_probability_map(query_id)
    index = int(hash64(int(instance_seed), f"{TASK_NAMESPACE}.query_id", 0) % len(QUERY_IDS))
    return str(QUERY_IDS[index]), _uniform_probability_map(QUERY_IDS)


def _resolve_target_answer(instance_seed: int, params: Mapping[str, Any]) -> Tuple[int, Dict[str, float]]:
    raw_support = params.get("target_answer_support", group_default(_GEN_DEFAULTS, "target_answer_support", ANSWER_SUPPORT))
    support = tuple(int(value) for value in raw_support)
    if not support:
        raise ValueError(f"target_answer_support for {TASK_ID} cannot be empty")
    for value in support:
        if int(value) < 0 or int(value) > PANEL_COUNT:
            raise ValueError(f"target_answer_support values for {TASK_ID} must be in 0..{PANEL_COUNT}")
    explicit = params.get("target_answer")
    if explicit is not None:
        target_answer = int(explicit)
        if target_answer not in set(support):
            raise ValueError(f"target_answer for {TASK_ID} must be in configured support {sorted(support)}")
        return int(target_answer), _selected_probability_map(target_answer)
    index = int(hash64(int(instance_seed), f"{TASK_NAMESPACE}.target_answer", 0) % len(support))
    return int(support[index]), {str(value): 1.0 / float(len(support)) for value in support}


def _induced_current_class(field_orientation: str, flux_change: str) -> str:
    if str(flux_change) == "none":
        return "no_current"
    induced_field = "out_of_page" if str(flux_change) == "increasing" and str(field_orientation) == "into_page" else ""
    if str(flux_change) == "increasing" and str(field_orientation) == "out_of_page":
        induced_field = "into_page"
    if str(flux_change) == "decreasing":
        induced_field = str(field_orientation)
    return "clockwise" if str(induced_field) == "into_page" else "counterclockwise"


def _make_panel_spec(panel_id: str, current_class: str, rng: Random, bbox_px: List[float]) -> _PanelSpec:
    if current_class == "no_current":
        field_orientation = str(rng.choice(FIELD_ORIENTATIONS))
        flux_change = "none"
    else:
        field_orientation = str(rng.choice(FIELD_ORIENTATIONS))
        desired_induced_field = "into_page" if current_class == "clockwise" else "out_of_page"
        flux_change = "decreasing" if desired_induced_field == field_orientation else "increasing"
    mechanism = str(rng.choice(PANEL_MECHANISMS_BY_FLUX_CHANGE[str(flux_change)]))
    region_side = str(rng.choice(("left", "right")))
    resolved = _induced_current_class(str(field_orientation), str(flux_change))
    if str(resolved) != str(current_class):
        raise RuntimeError(f"internal induction mapping error: expected {current_class}, got {resolved}")
    return _PanelSpec(
        panel_id=str(panel_id),
        current_class=str(current_class),
        field_orientation=str(field_orientation),
        flux_change=str(flux_change),
        mechanism=str(mechanism),
        region_side=str(region_side),
        bbox_px=list(bbox_px),
    )


def _make_scenario(instance_seed: int, params: Mapping[str, Any]) -> _InductionScenario:
    query_id, query_probs = _resolve_query_id(int(instance_seed), params)
    target_answer, answer_probs = _resolve_target_answer(int(instance_seed), params)
    target_class = str(QUERY_TO_CURRENT_CLASS[str(query_id)])
    distractor_classes = [value for value in CURRENT_CLASSES if str(value) != target_class]
    rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.panel_classes")
    panel_classes = [target_class for _ in range(int(target_answer))]
    panel_classes.extend(str(rng.choice(distractor_classes)) for _ in range(PANEL_COUNT - int(target_answer)))
    rng.shuffle(panel_classes)

    panel_bboxes = _panel_layout(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1180))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 820))),
    )
    panels: List[_PanelSpec] = []
    for index, current_class in enumerate(panel_classes):
        panel_rng = spawn_rng(int(instance_seed), f"{TASK_NAMESPACE}.panel_spec", index)
        panels.append(
            _make_panel_spec(
                panel_id=f"panel_{index + 1}",
                current_class=str(current_class),
                rng=panel_rng,
                bbox_px=list(panel_bboxes[index]),
            )
        )
    return _InductionScenario(
        query_id=str(query_id),
        target_current_class=str(target_class),
        target_answer=int(target_answer),
        panels=tuple(panels),
        query_id_probabilities=dict(query_probs),
        target_answer_probabilities=dict(answer_probs),
    )


def _panel_layout(*, canvas_width: int, canvas_height: int) -> List[List[float]]:
    margin_x = 54.0
    top = 68.0
    gap_x = 26.0
    gap_y = 28.0
    panel_w = (float(canvas_width) - (2.0 * margin_x) - (2.0 * gap_x)) / 3.0
    panel_h = (float(canvas_height) - top - 52.0 - gap_y) / 2.0
    bboxes: List[List[float]] = []
    for row in range(2):
        for col in range(3):
            left = margin_x + (float(col) * (panel_w + gap_x))
            y = top + (float(row) * (panel_h + gap_y))
            bboxes.append(_bbox((left, y, left + panel_w, y + panel_h)))
    return bboxes


def _draw_field_symbol(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    direction: str,
    stroke_rgb: Sequence[int],
    fill_rgb: Sequence[int],
) -> None:
    x, y = float(center[0]), float(center[1])
    stroke = tuple(int(v) for v in stroke_rgb)
    fill = tuple(int(v) for v in fill_rgb)
    draw.ellipse((x - 11, y - 11, x + 11, y + 11), fill=fill, outline=stroke, width=2)
    if str(direction) == "out_of_page":
        draw.ellipse((x - 3.5, y - 3.5, x + 3.5, y + 3.5), fill=stroke)
    else:
        draw.line((x - 6, y - 6, x + 6, y + 6), fill=stroke, width=3)
        draw.line((x - 6, y + 6, x + 6, y - 6), fill=stroke, width=3)


def _draw_field_region(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[float, float, float, float],
    direction: str,
    style: Any,
    shaded: bool,
) -> None:
    left, top, right, bottom = [float(value) for value in bbox]
    if shaded:
        draw.rounded_rectangle(
            (left, top, right, bottom),
            radius=12,
            fill=tuple(int(v) for v in style.panel_alt_fill_rgb),
            outline=tuple(int(v) for v in style.panel_border_rgb),
            width=2,
        )
    spacing_x = max(54.0, (right - left) / 4.0)
    spacing_y = max(45.0, (bottom - top) / 4.0)
    x = left + spacing_x * 0.5
    while x <= right - 18:
        y = top + spacing_y * 0.5
        while y <= bottom - 18:
            _draw_field_symbol(
                draw,
                center=(x, y),
                direction=str(direction),
                stroke_rgb=style.stroke_rgb,
                fill_rgb=style.panel_fill_rgb,
            )
            y += spacing_y
        x += spacing_x


def _draw_loop(
    draw: ImageDraw.ImageDraw,
    *,
    bbox: Tuple[float, float, float, float],
    stroke_rgb: Sequence[int],
) -> None:
    stroke = tuple(int(v) for v in stroke_rgb)
    copper = (178, 105, 42)
    draw.rounded_rectangle(bbox, radius=10, outline=stroke, width=8)
    inset = (bbox[0] + 4, bbox[1] + 4, bbox[2] - 4, bbox[3] - 4)
    draw.rounded_rectangle(inset, radius=8, outline=copper, width=4)


def _draw_area_change_arrows(
    draw: ImageDraw.ImageDraw,
    *,
    loop_bbox: Tuple[float, float, float, float],
    expanding: bool,
    fill_rgb: Sequence[int],
) -> None:
    left, top, right, bottom = [float(value) for value in loop_bbox]
    cx = 0.5 * (left + right)
    cy = 0.5 * (top + bottom)
    if bool(expanding):
        pairs = [
            ((left + 8, cy), (left - 30, cy)),
            ((right - 8, cy), (right + 30, cy)),
            ((cx, top + 8), (cx, top - 28)),
            ((cx, bottom - 8), (cx, bottom + 28)),
        ]
    else:
        pairs = [
            ((left - 30, cy), (left + 8, cy)),
            ((right + 30, cy), (right - 8, cy)),
            ((cx, top - 28), (cx, top + 8)),
            ((cx, bottom + 28), (cx, bottom - 8)),
        ]
    for start, end in pairs:
        draw_arrow(
            draw,
            start=start,
            end=end,
            fill=tuple(int(v) for v in fill_rgb),
            width=4,
            head_length_px=12,
            head_width_px=10,
        )


def _panel_cue_text(mechanism: str) -> str:
    return {
        "loop_enters_field": "loop enters field",
        "loop_leaves_field": "loop leaves field",
        "field_strength_increases": "B stronger",
        "field_strength_decreases": "B weaker",
        "loop_area_expands": "area grows",
        "loop_area_contracts": "area shrinks",
        "loop_slides_inside_uniform_field": "slides in uniform B",
        "stationary_constant_field": "constant B",
    }[str(mechanism)]


def _draw_panel(
    draw: ImageDraw.ImageDraw,
    *,
    panel: _PanelSpec,
    font_family: str,
    style: Any,
) -> None:
    left, top, right, bottom = [float(value) for value in panel.bbox_px]
    panel_fill = tuple(int(v) for v in style.panel_fill_rgb)
    panel_border = tuple(int(v) for v in style.panel_border_rgb)
    label_rgb = tuple(int(v) for v in style.label_rgb)
    accent = tuple(int(v) for v in style.accent_rgb)
    draw.rounded_rectangle((left, top, right, bottom), radius=16, fill=panel_fill, outline=panel_border, width=3)

    cue_font = load_font(18, bold=True, font_family=font_family)
    cue_y = bottom - 26.0
    inner = (left + 18.0, top + 18.0, right - 18.0, bottom - 56.0)
    mechanism = str(panel.mechanism)
    full_field = mechanism not in {"loop_enters_field", "loop_leaves_field"}
    if full_field:
        _draw_field_region(
            draw,
            bbox=inner,
            direction=str(panel.field_orientation),
            style=style,
            shaded=False,
        )
        loop_w, loop_h = 104.0, 78.0
        cx = 0.5 * (inner[0] + inner[2])
        cy = 0.5 * (inner[1] + inner[3])
        loop_bbox = (cx - loop_w / 2.0, cy - loop_h / 2.0, cx + loop_w / 2.0, cy + loop_h / 2.0)
        _draw_loop(draw, bbox=loop_bbox, stroke_rgb=style.stroke_rgb)
        if mechanism == "loop_area_expands":
            _draw_area_change_arrows(draw, loop_bbox=loop_bbox, expanding=True, fill_rgb=accent)
        elif mechanism == "loop_area_contracts":
            _draw_area_change_arrows(draw, loop_bbox=loop_bbox, expanding=False, fill_rgb=accent)
        elif mechanism == "loop_slides_inside_uniform_field":
            draw_arrow(
                draw,
                start=(loop_bbox[2] + 16.0, cy),
                end=(loop_bbox[2] + 68.0, cy),
                fill=accent,
                width=5,
                head_length_px=15,
                head_width_px=13,
            )
        elif mechanism == "field_strength_increases":
            draw_arrow(
                draw,
                start=(right - 68.0, top + 72.0),
                end=(right - 68.0, top + 28.0),
                fill=accent,
                width=5,
                head_length_px=14,
                head_width_px=12,
            )
        elif mechanism == "field_strength_decreases":
            draw_arrow(
                draw,
                start=(right - 68.0, top + 28.0),
                end=(right - 68.0, top + 72.0),
                fill=accent,
                width=5,
                head_length_px=14,
                head_width_px=12,
            )
    else:
        boundary_x = 0.5 * (inner[0] + inner[2])
        if panel.region_side == "right":
            field_bbox = (boundary_x, inner[1], inner[2], inner[3])
            enter_arrow = ((boundary_x - 92.0, 0.5 * (inner[1] + inner[3])), (boundary_x - 24.0, 0.5 * (inner[1] + inner[3])))
            leave_arrow = ((boundary_x + 80.0, 0.5 * (inner[1] + inner[3])), (boundary_x + 12.0, 0.5 * (inner[1] + inner[3])))
            loop_cx = boundary_x - 18.0 if mechanism == "loop_enters_field" else boundary_x + 50.0
        else:
            field_bbox = (inner[0], inner[1], boundary_x, inner[3])
            enter_arrow = ((boundary_x + 92.0, 0.5 * (inner[1] + inner[3])), (boundary_x + 24.0, 0.5 * (inner[1] + inner[3])))
            leave_arrow = ((boundary_x - 80.0, 0.5 * (inner[1] + inner[3])), (boundary_x - 12.0, 0.5 * (inner[1] + inner[3])))
            loop_cx = boundary_x + 18.0 if mechanism == "loop_enters_field" else boundary_x - 50.0
        _draw_field_region(
            draw,
            bbox=field_bbox,
            direction=str(panel.field_orientation),
            style=style,
            shaded=True,
        )
        loop_h = 76.0
        loop_w = 98.0
        cy = 0.5 * (inner[1] + inner[3])
        loop_bbox = (loop_cx - loop_w / 2.0, cy - loop_h / 2.0, loop_cx + loop_w / 2.0, cy + loop_h / 2.0)
        _draw_loop(draw, bbox=loop_bbox, stroke_rgb=style.stroke_rgb)
        arrow_start, arrow_end = enter_arrow if mechanism == "loop_enters_field" else leave_arrow
        draw_arrow(
            draw,
            start=arrow_start,
            end=arrow_end,
            fill=accent,
            width=5,
            head_length_px=15,
            head_width_px=13,
        )

    draw_centered_text(
        draw,
        text=_panel_cue_text(mechanism),
        center=(0.5 * (left + right), cue_y),
        font=cue_font,
        fill=label_rgb,
        stroke_fill=resolve_text_stroke_fill(label_rgb),
        stroke_width=1,
    )


def _render_scene(
    *,
    image: Image.Image,
    scenario: _InductionScenario,
    font_family: str,
    style: Any,
) -> Tuple[Image.Image, List[List[float]], List[Dict[str, Any]], Dict[str, Any]]:
    draw = ImageDraw.Draw(image)
    matching_bboxes: List[List[float]] = []
    entities: List[Dict[str, Any]] = []
    panel_bboxes: Dict[str, List[float]] = {}
    for panel in scenario.panels:
        _draw_panel(draw, panel=panel, font_family=font_family, style=style)
        panel_bboxes[str(panel.panel_id)] = list(panel.bbox_px)
        is_match = str(panel.current_class) == str(scenario.target_current_class)
        if is_match:
            matching_bboxes.append(list(panel.bbox_px))
        entities.append(
            {
                "entity_id": str(panel.panel_id),
                "entity_type": "induction_panel",
                "bbox_px": list(panel.bbox_px),
                "meta": {
                    "field_orientation": str(panel.field_orientation),
                    "flux_change": str(panel.flux_change),
                    "mechanism": str(panel.mechanism),
                    "region_side": str(panel.region_side),
                    "induced_current_class": str(panel.current_class),
                    "matches_query": bool(is_match),
                },
            }
        )
    render_map = {
        "panel_bboxes": dict(panel_bboxes),
        "matching_panel_ids": [str(panel.panel_id) for panel in scenario.panels if str(panel.current_class) == str(scenario.target_current_class)],
        "panel_specs": [
            {
                "panel_id": str(panel.panel_id),
                "field_orientation": str(panel.field_orientation),
                "flux_change": str(panel.flux_change),
                "mechanism": str(panel.mechanism),
                "region_side": str(panel.region_side),
                "induced_current_class": str(panel.current_class),
            }
            for panel in scenario.panels
        ],
    }
    return image, [list(bbox) for bbox in matching_bboxes], [dict(entity) for entity in entities], dict(render_map)


def _prompt_examples() -> Tuple[str, str]:
    return (
        json.dumps(
            {
                "annotation": [[60, 70, 390, 420], [420, 70, 750, 420]],
                "answer": 2,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        json.dumps({"answer": 2}, ensure_ascii=False, separators=(",", ":")),
    )


@register_task
class PhysicsElectromagneticInductionDirectionCountTask:
    """Count mini-panels by induced-current direction from visible flux-change cues."""

    task_id = TASK_ID
    domain = "physics"
    scene_id = "magnetism"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        scenario = _make_scenario(int(instance_seed), params)
        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1180)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 820)))
        background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
            instance_seed=int(instance_seed),
            params=params,
            scene_id=SCENE_ID,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            require_grid=True,
        )
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{TASK_NAMESPACE}.font",
            params=params,
        )
        font_record = get_font_family_record(str(font_family))
        rendered, annotation_bboxes, scene_entities, render_map = _render_scene(
            image=background,
            scenario=scenario,
            font_family=str(font_family),
            style=diagram_style,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered,
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
                "object_description",
                f"answer_hint_{scenario.query_id}",
                f"annotation_hint_{scenario.query_id}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_gt = TypedValue(type="integer", value=int(scenario.target_answer))
        annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
        json_example, json_example_answer_only = _prompt_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(scenario.query_id),
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{scenario.query_id}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{scenario.query_id}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        matching_panel_ids = list(render_map["matching_panel_ids"])
        trace_payload = {
            "scene_ir": {
                "scene_kind": "physics_electromagnetic_induction_six_panel_count",
                "entities": [dict(entity) for entity in scene_entities],
                "relations": {
                    "query_id": str(scenario.query_id),
                    "target_current_class": str(scenario.target_current_class),
                    "target_answer": int(scenario.target_answer),
                    "matching_panel_ids": list(matching_panel_ids),
                },
            },
            "query_spec": {
                "query_id": str(scenario.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(scenario.query_id),
                    "target_answer": int(scenario.target_answer),
                    "target_current_class": str(scenario.target_current_class),
                    "answer_support": list(ANSWER_SUPPORT),
                    "panel_count": PANEL_COUNT,
                },
            },
            "render_spec": {
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "electromagnetic_induction_panels",
                    "selection_policy": {
                        "pool": "global_approved_font_pool",
                        "include_tags": [],
                        "exclude_tags": [],
                        "exclusion_reason": "",
                    },
                },
                "technical_diagram_style": dict(diagram_style_meta),
                "background_style": background_meta,
                "post_image_noise": post_noise_meta,
            },
            "render_map": dict(render_map),
            "execution_trace": {
                "query_id": str(scenario.query_id),
                "target_current_class": str(scenario.target_current_class),
                "target_answer": int(scenario.target_answer),
                "matching_panel_ids": list(matching_panel_ids),
                "panel_current_classes": {
                    str(panel.panel_id): str(panel.current_class)
                    for panel in scenario.panels
                },
                "panel_flux_changes": {
                    str(panel.panel_id): str(panel.flux_change)
                    for panel in scenario.panels
                },
                "panel_field_orientations": {
                    str(panel.panel_id): str(panel.field_orientation)
                    for panel in scenario.panels
                },
                "panel_mechanisms": {
                    str(panel.panel_id): str(panel.mechanism)
                    for panel in scenario.panels
                },
                "annotation_entity_ids": list(matching_panel_ids),
            },
            "sampling": {
                "query_id_probabilities": dict(scenario.query_id_probabilities),
                "target_answer_probabilities": dict(scenario.target_answer_probabilities),
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "entity_ids": list(matching_panel_ids),
            },
            "projected_annotation": {
                "type": "bbox_set",
                "bbox_set": [list(bbox) for bbox in annotation_gt.value],
                "pixel_bbox_set": [list(bbox) for bbox in annotation_gt.value],
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
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(scenario.query_id),
        )


__all__ = [
    "ANSWER_SUPPORT",
    "CURRENT_CLASSES",
    "PhysicsElectromagneticInductionDirectionCountTask",
]
