"""Physics magnetism task for fields around a current-carrying wire."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_arrow, draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


FAMILY_ID = "physics_magnetism_wire_field_family"
SCENE_ID = "wire_magnetism"
QUERY_ID = "field_direction_at_point"
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="magnetism", apply_prob=0.5)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "magnetism")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)


@dataclass(frozen=True)
class _WireScenario:
    orientation: str
    current_direction: str
    current_vector_phys: Tuple[int, int]
    point_offset_phys: Tuple[int, int]
    field_direction: str
    option_map: Dict[str, str]
    correct_label: str


def _bbox(values: Tuple[float, float, float, float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _phys_to_screen_vector(vector: Tuple[int, int], length: float) -> Tuple[float, float]:
    return (float(vector[0] * length), float(-vector[1] * length))


def _make_scenario(instance_seed: int, params: Mapping[str, Any]) -> _WireScenario:
    orientations = ("horizontal", "vertical")
    orientation = str(params.get("orientation") or orientations[int(hash64(int(instance_seed), f"{FAMILY_ID}.orientation", 0) % 2)])
    if orientation == "horizontal":
        current_options = (("right", (1, 0)), ("left", (-1, 0)))
        offset_options = (("above", (0, 1)), ("below", (0, -1)))
    else:
        current_options = (("up", (0, 1)), ("down", (0, -1)))
        offset_options = (("right", (1, 0)), ("left", (-1, 0)))
    current_name, current_vector = current_options[int(hash64(int(instance_seed), f"{FAMILY_ID}.current", 0) % len(current_options))]
    _, point_offset = offset_options[int(hash64(int(instance_seed), f"{FAMILY_ID}.point_offset", 0) % len(offset_options))]
    z_sign = int(current_vector[0] * point_offset[1] - current_vector[1] * point_offset[0])
    field_direction = "out_of_page" if z_sign > 0 else "into_page"
    distractors = ["north", "south", "east", "west"]
    distractors.append("into_page" if field_direction == "out_of_page" else "out_of_page")
    correct_index = int(hash64(int(instance_seed), f"{FAMILY_ID}.correct_option", 0) % len(OPTION_LABELS))
    option_map: Dict[str, str] = {}
    distractor_index = 0
    for index, label in enumerate(OPTION_LABELS):
        if index == correct_index:
            option_map[str(label)] = str(field_direction)
        else:
            option_map[str(label)] = str(distractors[distractor_index])
            distractor_index += 1
    correct_label = str(OPTION_LABELS[correct_index])
    return _WireScenario(
        orientation=str(orientation),
        current_direction=str(current_name),
        current_vector_phys=tuple(current_vector),
        point_offset_phys=tuple(point_offset),
        field_direction=str(field_direction),
        option_map=dict(option_map),
        correct_label=str(correct_label),
    )


def _draw_field_symbol(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    direction: str,
    font: Any,
    style: Any,
) -> None:
    x, y = float(center[0]), float(center[1])
    stroke = tuple(int(v) for v in style.stroke_rgb)
    if direction == "out_of_page":
        draw.ellipse((x - 17, y - 17, x + 17, y + 17), fill=tuple(style.panel_alt_fill_rgb), outline=stroke, width=3)
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=stroke)
    else:
        draw.ellipse((x - 17, y - 17, x + 17, y + 17), fill=tuple(style.panel_alt_fill_rgb), outline=stroke, width=3)
        draw.line((x - 9, y - 9, x + 9, y + 9), fill=stroke, width=4)
        draw.line((x - 9, y + 9, x + 9, y - 9), fill=stroke, width=4)


def _draw_option_symbol(
    draw: ImageDraw.ImageDraw,
    *,
    center: Tuple[float, float],
    direction: str,
    style: Any,
) -> None:
    x, y = float(center[0]), float(center[1])
    if direction in {"out_of_page", "into_page"}:
        _draw_field_symbol(draw, center=(x, y), direction=str(direction), font=None, style=style)
        return
    vectors = {
        "north": (0.0, -1.0),
        "south": (0.0, 1.0),
        "east": (1.0, 0.0),
        "west": (-1.0, 0.0),
    }
    vx, vy = vectors[str(direction)]
    draw_arrow(
        draw,
        start=(x - vx * 22.0, y - vy * 22.0),
        end=(x + vx * 22.0, y + vy * 22.0),
        fill=tuple(int(v) for v in style.stroke_rgb),
        width=6,
        head_length_px=14,
        head_width_px=13,
    )


def _render_scene(
    *,
    image: Image.Image,
    scenario: _WireScenario,
    font_family: str,
    style: Any,
) -> Tuple[Image.Image, Dict[str, List[float]], Dict[str, Any]]:
    draw = ImageDraw.Draw(image)
    canvas_width, canvas_height = image.size
    title_font = load_font(27, bold=True, font_family=font_family)
    label_font = load_font(25, bold=True, font_family=font_family)
    option_font = load_font(20, bold=True, font_family=font_family)
    text_rgb = tuple(int(v) for v in style.label_rgb)
    stroke = tuple(int(v) for v in style.stroke_rgb)
    accent = tuple(int(v) for v in style.accent_rgb)

    panel = (56, 54, 744, canvas_height - 62)
    option_panel = (780, 88, canvas_width - 56, canvas_height - 96)
    draw.rounded_rectangle(panel, radius=18, fill=tuple(style.panel_fill_rgb), outline=tuple(style.panel_border_rgb), width=3)
    draw.rounded_rectangle(option_panel, radius=18, fill=tuple(style.panel_fill_rgb), outline=tuple(style.panel_border_rgb), width=3)
    draw_centered_text(draw, text="current-carrying wire", center=(panel[0] + 0.5 * (panel[2] - panel[0]), panel[1] + 32), font=title_font, fill=text_rgb, stroke_fill=resolve_text_stroke_fill(text_rgb), stroke_width=1)
    draw_centered_text(draw, text="Field at P", center=(option_panel[0] + 0.5 * (option_panel[2] - option_panel[0]), option_panel[1] + 34), font=title_font, fill=text_rgb, stroke_fill=resolve_text_stroke_fill(text_rgb), stroke_width=1)

    wire_center = (390.0, 352.0)
    wire_half = 215.0
    if scenario.orientation == "horizontal":
        wire_start = (wire_center[0] - wire_half, wire_center[1])
        wire_end = (wire_center[0] + wire_half, wire_center[1])
    else:
        wire_start = (wire_center[0], wire_center[1] + wire_half)
        wire_end = (wire_center[0], wire_center[1] - wire_half)
    arrow_vec = _phys_to_screen_vector(scenario.current_vector_phys, 132.0)
    arrow_start = (wire_center[0] - arrow_vec[0] * 0.5, wire_center[1] - arrow_vec[1] * 0.5)
    arrow_end = (wire_center[0] + arrow_vec[0] * 0.5, wire_center[1] + arrow_vec[1] * 0.5)
    point_vec = _phys_to_screen_vector(scenario.point_offset_phys, 138.0)
    point_p = (wire_center[0] + point_vec[0], wire_center[1] + point_vec[1])

    draw.line((wire_start, wire_end), fill=stroke, width=16)
    draw.line((wire_start, wire_end), fill=tuple(style.panel_alt_fill_rgb), width=8)
    draw_arrow(draw, start=arrow_start, end=arrow_end, fill=accent, width=9, head_length_px=26, head_width_px=24)
    current_label_center = (arrow_end[0] + 28, arrow_end[1] - 24)
    draw_centered_text(draw, text="I", center=current_label_center, font=label_font, fill=accent, stroke_fill=resolve_text_stroke_fill(accent), stroke_width=2)

    draw.ellipse((point_p[0] - 15, point_p[1] - 15, point_p[0] + 15, point_p[1] + 15), fill=(255, 255, 255), outline=stroke, width=4)
    draw_centered_text(draw, text="P", center=(point_p[0], point_p[1] - 36), font=label_font, fill=text_rgb, stroke_fill=resolve_text_stroke_fill(text_rgb), stroke_width=1)
    draw.line((point_p[0], point_p[1], wire_center[0], wire_center[1]), fill=tuple(style.guide_rgb), width=2)

    option_bboxes: Dict[str, List[float]] = {}
    box_w = 96.0
    box_h = 86.0
    gap_x = 20.0
    gap_y = 28.0
    start_x = option_panel[0] + 28.0
    start_y = option_panel[1] + 92.0
    for idx, (label, direction) in enumerate(sorted(scenario.option_map.items())):
        col = idx % 2
        row = idx // 2
        left = start_x + col * (box_w + gap_x)
        top = start_y + row * (box_h + gap_y)
        box = (left, top, left + box_w, top + box_h)
        draw.rounded_rectangle(box, radius=14, fill=tuple(style.panel_alt_fill_rgb), outline=tuple(style.panel_border_rgb), width=3)
        draw_centered_text(draw, text=str(label), center=(box[0] + 22, box[1] + 43), font=option_font, fill=text_rgb, stroke_fill=resolve_text_stroke_fill(text_rgb), stroke_width=1)
        _draw_option_symbol(draw, center=(box[0] + 63, box[1] + 43), direction=str(direction), style=style)
        option_bboxes[str(label)] = _bbox(box)

    wire_bbox = _bbox(
        (
            min(wire_start[0], wire_end[0], arrow_start[0], arrow_end[0]) - 28,
            min(wire_start[1], wire_end[1], arrow_start[1], arrow_end[1]) - 36,
            max(wire_start[0], wire_end[0], arrow_start[0], arrow_end[0]) + 40,
            max(wire_start[1], wire_end[1], arrow_start[1], arrow_end[1]) + 36,
        )
    )
    point_bbox = _bbox((point_p[0] - 26, point_p[1] - 48, point_p[0] + 26, point_p[1] + 24))
    annotation_map = {"wire_current": wire_bbox, "point_p": point_bbox}
    render_map = {
        "wire_start": [round(float(wire_start[0]), 3), round(float(wire_start[1]), 3)],
        "wire_end": [round(float(wire_end[0]), 3), round(float(wire_end[1]), 3)],
        "point_p": [round(float(point_p[0]), 3), round(float(point_p[1]), 3)],
        "option_bboxes": option_bboxes,
        "option_map": dict(scenario.option_map),
        "correct_label": str(scenario.correct_label),
    }
    return image, annotation_map, render_map


@register_task
class PhysicsWireMagnetismFieldDirectionChoiceTask:
    """Choose the magnetic-field direction at a point near a straight current-carrying wire."""

    task_id = "task_physics__wire_magnetism__wire_field_direction_choice"
    domain = "physics"
    task_group = "magnetism"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        canvas_width = int(_RENDER_DEFAULTS.get("canvas_width", 1080))
        canvas_height = int(_RENDER_DEFAULTS.get("canvas_height", 700))
        background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
            instance_seed=int(instance_seed),
            params=params,
            scene_id=SCENE_ID,
            task_group=self.task_group,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            require_grid=True,
        )
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.font",
            params=params,
        )
        font_record = get_font_family_record(str(font_family))
        scenario = _make_scenario(int(instance_seed), params)
        rendered, annotation_map, render_map = _render_scene(
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
                f"answer_hint_{QUERY_ID}",
                f"annotation_hint_{QUERY_ID}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_gt = TypedValue(type="option_letter", value=str(scenario.correct_label))
        annotation_gt = TypedValue(type="keyed_bbox_map", value={str(k): list(v) for k, v in annotation_map.items()})
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
        trace_payload = {
            "scene_ir": {
                "scene_kind": "physics_wire_magnetism_straight_wire",
                "entities": [],
                "relations": {
                    "query_id": QUERY_ID,
                    "orientation": str(scenario.orientation),
                    "current_direction": str(scenario.current_direction),
                    "point_offset_phys": list(scenario.point_offset_phys),
                    "field_direction": str(scenario.field_direction),
                    "correct_label": str(scenario.correct_label),
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
                    "target_answer": str(scenario.correct_label),
                    "field_direction": str(scenario.field_direction),
                    "orientation": str(scenario.orientation),
                },
            },
            "render_spec": {
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "wire_magnetism_diagram",
                },
                "technical_diagram_style": dict(diagram_style_meta),
                "background_style": background_meta,
                "post_image_noise": post_noise_meta,
            },
            "render_map": dict(render_map),
            "execution_trace": {
                "query_id": QUERY_ID,
                "field_direction": str(scenario.field_direction),
                "option_map": dict(scenario.option_map),
                "target_answer": str(scenario.correct_label),
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
            complexity=TaskComplexity(
                complexity_score=0.50,
                complexity_components={
                    "visual_scan": 0.24,
                    "right_hand_rule": 0.50,
                    "ambiguity": 0.14,
                    "output_burden": 0.12,
                },
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )
