"""Physics optics task for image-property inference from a thin lens diagram."""

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
from ...shared.bbox_projection import bbox_union_many
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_arrow, draw_centered_text, draw_dashed_line
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.named_colors import named_color
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ...shared.variant_sampling import apply_balanced_variant_sampling, resolve_variant
from ..shared.complexity import build_physics_complexity, resolve_physics_complexity_weights
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.option_cards import OptionCardRenderResult, draw_lettered_option_cards
from ..shared.style import SUPPORTED_PHYSICS_COLOR_NAMES
from ..shared.visual_defaults import load_physics_noise_defaults


TASK_ID = "task_physics__lens_optics__image_property_choice"
FAMILY_ID = "physics_optics_lens_optics_family"
SCENE_ID = "lens_optics"
QUERY_ID = "converging_lens_image_property_choice"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (QUERY_ID,)
SUPPORTED_SCENE_VARIANTS: Tuple[str, ...] = ("clean_axis", "paper_grid", "lab_card")
OPTION_LETTERS: Tuple[str, ...] = ("A", "B", "C", "D")
OBJECT_POSITION_CASES: Tuple[str, ...] = (
    "beyond_2f",
    "at_2f",
    "between_f_2f",
    "inside_f",
)
CASE_TO_PROPERTY: Dict[str, str] = {
    "beyond_2f": "real_inverted_smaller",
    "at_2f": "real_inverted_same_size",
    "between_f_2f": "real_inverted_larger",
    "inside_f": "virtual_upright_larger",
}
PROPERTY_TEXT: Dict[str, str] = {
    "real_inverted_smaller": "real, inverted,\nsmaller",
    "real_inverted_same_size": "real, inverted,\nsame size",
    "real_inverted_larger": "real, inverted,\nlarger",
    "virtual_upright_larger": "virtual, upright,\nlarger",
}
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "optics")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="optics", apply_prob=0.5)


@dataclass(frozen=True)
class _Axes:
    scene_variant: str
    query_id: str
    object_position_case: str
    correct_option_letter: str
    accent_color_name: str
    scene_variant_probabilities: Dict[str, float]
    query_id_probabilities: Dict[str, float]
    object_position_case_probabilities: Dict[str, float]
    correct_option_letter_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _Scenario:
    scene_variant: str
    query_id: str
    object_position_case: str
    image_property: str
    correct_option_letter: str
    accent_color_name: str
    option_map: Dict[str, str]
    focal_length_px: float
    object_x_factor: float


@dataclass(frozen=True)
class _RenderedScene:
    image: Image.Image
    annotation_bbox_map: Dict[str, List[float]]
    scene_entities: List[Dict[str, Any]]
    render_map: Dict[str, Any]


def _bbox(values: Sequence[float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _clip_bbox(bbox: Sequence[float], *, width: int, height: int) -> List[float]:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    return _bbox(
        (
            max(0.0, min(float(width), min(x0, x1))),
            max(0.0, min(float(height), min(y0, y1))),
            max(0.0, min(float(width), max(x0, x1))),
            max(0.0, min(float(height), max(y0, y1))),
        )
    )


def _resolve_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported: Sequence[str],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    selected, probabilities = resolve_variant(
        spawn_rng(int(instance_seed), namespace),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=supported,
        explicit_key=explicit_key,
        weights_key=weights_key,
    )
    selected = apply_balanced_variant_sampling(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        selected_variant=str(selected),
        variant_probabilities=probabilities,
        supported_variants=supported,
        balance_flag_key=balance_flag_key,
        explicit_key=explicit_key,
        weights_key=weights_key,
        sampling_namespace=namespace,
    )
    return str(selected), {str(key): float(value) for key, value in probabilities.items()}


def _resolve_axes(instance_seed: int, params: Mapping[str, Any]) -> _Axes:
    scene_variant, scene_probs = _resolve_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=SUPPORTED_SCENE_VARIANTS,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        namespace=f"{FAMILY_ID}.scene_variant",
    )
    query_id, query_probs = _resolve_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=SUPPORTED_QUERY_IDS,
        explicit_key="query_id",
        weights_key="query_id_weights",
        balance_flag_key="balanced_query_id_sampling",
        namespace=f"{FAMILY_ID}.query_id",
    )
    position_case, position_probs = _resolve_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=OBJECT_POSITION_CASES,
        explicit_key="object_position_case",
        weights_key="object_position_case_weights",
        balance_flag_key="balanced_object_position_case_sampling",
        namespace=f"{FAMILY_ID}.object_position_case",
    )
    correct_letter, letter_probs = _resolve_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=OPTION_LETTERS,
        explicit_key="correct_option_letter",
        weights_key="correct_option_letter_weights",
        balance_flag_key="balanced_correct_option_letter_sampling",
        namespace=f"{FAMILY_ID}.correct_option_letter",
    )
    accent_color, accent_probs = _resolve_axis(
        instance_seed=int(instance_seed),
        params=params,
        supported=SUPPORTED_PHYSICS_COLOR_NAMES,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        balance_flag_key="balanced_accent_color_name_sampling",
        namespace=f"{FAMILY_ID}.accent_color_name",
    )
    return _Axes(
        scene_variant=str(scene_variant),
        query_id=str(query_id),
        object_position_case=str(position_case),
        correct_option_letter=str(correct_letter),
        accent_color_name=str(accent_color),
        scene_variant_probabilities=dict(scene_probs),
        query_id_probabilities=dict(query_probs),
        object_position_case_probabilities=dict(position_probs),
        correct_option_letter_probabilities=dict(letter_probs),
        accent_color_name_probabilities=dict(accent_probs),
    )


def _option_map(*, instance_seed: int, image_property: str, correct_option_letter: str) -> Dict[str, str]:
    remaining = [property_id for property_id in PROPERTY_TEXT if str(property_id) != str(image_property)]
    rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.option_map")
    rng.shuffle(remaining)
    result: Dict[str, str] = {}
    cursor = 0
    for letter in OPTION_LETTERS:
        if str(letter) == str(correct_option_letter):
            result[str(letter)] = str(image_property)
        else:
            result[str(letter)] = str(remaining[cursor])
            cursor += 1
    return dict(result)


def _make_scenario(instance_seed: int, axes: _Axes, params: Mapping[str, Any]) -> _Scenario:
    focal_length = float(params.get("focal_length_px", group_default(_RENDER_DEFAULTS, "focal_length_px", 116)))
    factor_by_case = {
        "beyond_2f": 2.55,
        "at_2f": 2.0,
        "between_f_2f": 1.55,
        "inside_f": 0.62,
    }
    image_property = str(CASE_TO_PROPERTY[str(axes.object_position_case)])
    return _Scenario(
        scene_variant=str(axes.scene_variant),
        query_id=str(axes.query_id),
        object_position_case=str(axes.object_position_case),
        image_property=str(image_property),
        correct_option_letter=str(axes.correct_option_letter),
        accent_color_name=str(axes.accent_color_name),
        option_map=_option_map(
            instance_seed=int(instance_seed),
            image_property=str(image_property),
            correct_option_letter=str(axes.correct_option_letter),
        ),
        focal_length_px=float(focal_length),
        object_x_factor=float(factor_by_case[str(axes.object_position_case)]),
    )


def _draw_option_cards(
    draw: ImageDraw.ImageDraw,
    *,
    scenario: _Scenario,
    option_left: float,
    option_top: float,
    card_width: float,
    card_height: float,
    card_gap: float,
    font_family: str,
    style: Any,
) -> OptionCardRenderResult:
    letter_font = load_font(22, bold=True, font_family=font_family)
    option_font = load_font(21, bold=True, font_family=font_family)
    label_rgb = tuple(int(v) for v in style.label_rgb)
    return draw_lettered_option_cards(
        draw,
        options=[(str(letter), PROPERTY_TEXT[str(scenario.option_map[str(letter)])]) for letter in OPTION_LETTERS],
        option_left=option_left,
        option_top=option_top,
        card_width=card_width,
        card_height=card_height,
        card_gap_x=0.0,
        card_gap_y=card_gap,
        columns=1,
        option_font=option_font,
        letter_font=letter_font,
        text_rgb=label_rgb,
        card_fill_rgb=tuple(int(v) for v in style.panel_alt_fill_rgb),
        card_outline_rgb=tuple(int(v) for v in style.panel_border_rgb),
        label_fill_rgb=tuple(int(v) for v in style.label_fill_rgb),
        label_outline_rgb=tuple(int(v) for v in style.label_border_rgb),
        label_text_rgb=label_rgb,
        card_radius_px=14.0,
        text_align="center",
        text_left_offset_px=76.0,
        text_right_padding_px=16.0,
        line_spacing_px=5.0,
    )


def _render_scene(
    *,
    image: Image.Image,
    scenario: _Scenario,
    font_family: str,
    style: Any,
    render_defaults: Mapping[str, Any],
) -> _RenderedScene:
    draw = ImageDraw.Draw(image)
    width, height = image.size
    label_rgb = tuple(int(v) for v in style.label_rgb)
    stroke_rgb = tuple(int(v) for v in style.stroke_rgb)
    axis_rgb = tuple(int(v) for v in style.axis_rgb)
    accent_rgb = tuple(int(v) for v in named_color(str(scenario.accent_color_name)))
    title_font = load_font(int(render_defaults.get("title_font_size_px", 28)), bold=True, font_family=font_family)
    label_font = load_font(int(render_defaults.get("label_font_size_px", 22)), bold=True, font_family=font_family)
    small_font = load_font(int(render_defaults.get("small_font_size_px", 18)), bold=True, font_family=font_family)

    diagram = _bbox(
        (
            float(render_defaults.get("diagram_left_px", 54)),
            float(render_defaults.get("diagram_top_px", 54)),
            float(render_defaults.get("diagram_right_px", 760)),
            float(render_defaults.get("diagram_bottom_px", 666)),
        )
    )
    draw.rounded_rectangle(
        tuple(diagram),
        radius=18,
        fill=tuple(int(v) for v in style.panel_fill_rgb),
        outline=tuple(int(v) for v in style.panel_border_rgb),
        width=3,
    )
    if str(scenario.scene_variant) in {"paper_grid", "lab_card"}:
        spacing = float(render_defaults.get("grid_spacing_px", 42))
        x = diagram[0] + spacing
        while x < diagram[2]:
            draw.line((x, diagram[1], x, diagram[3]), fill=tuple(int(v) for v in style.grid_minor_rgb), width=1)
            x += spacing
        y = diagram[1] + spacing
        while y < diagram[3]:
            draw.line((diagram[0], y, diagram[2], y), fill=tuple(int(v) for v in style.grid_minor_rgb), width=1)
            y += spacing

    title_center = ((diagram[0] + diagram[2]) * 0.5, diagram[1] + 32.0)
    draw_centered_text(
        draw,
        text="Converging lens diagram",
        center=title_center,
        font=title_font,
        fill=label_rgb,
        stroke_fill=resolve_text_stroke_fill(label_rgb),
        stroke_width=1,
    )

    axis_y = float(render_defaults.get("axis_y_px", 370))
    lens_x = float(render_defaults.get("lens_x_px", 430))
    focal = float(scenario.focal_length_px)
    axis_left = diagram[0] + 42.0
    axis_right = diagram[2] - 42.0
    draw.line((axis_left, axis_y, axis_right, axis_y), fill=axis_rgb, width=int(render_defaults.get("axis_width_px", 4)))
    draw.polygon([(axis_right + 14, axis_y), (axis_right - 5, axis_y - 8), (axis_right - 5, axis_y + 8)], fill=axis_rgb)

    lens_height = float(render_defaults.get("lens_height_px", 294))
    lens_width = float(render_defaults.get("lens_width_px", 34))
    lens_bbox = _bbox((lens_x - lens_width, axis_y - lens_height * 0.5, lens_x + lens_width, axis_y + lens_height * 0.5))
    draw.ellipse(tuple(lens_bbox), fill=tuple(int(v) for v in style.panel_alt_fill_rgb), outline=accent_rgb, width=4)
    draw.line((lens_x, lens_bbox[1] - 12, lens_x, lens_bbox[3] + 12), fill=accent_rgb, width=3)
    lens_label_bbox = draw_centered_text(
        draw,
        text="lens",
        center=(lens_x, lens_bbox[1] - 28),
        font=small_font,
        fill=label_rgb,
        stroke_fill=resolve_text_stroke_fill(label_rgb),
        stroke_width=1,
    )
    lens_annotation_bbox = bbox_union_many(lens_bbox, lens_label_bbox, padding=3.0)

    focal_boxes: List[List[float]] = []
    for side_sign in (-1, 1):
        for factor, label in ((1.0, "F"), (2.0, "2F")):
            mark_x = lens_x + side_sign * factor * focal
            tick = _bbox((mark_x - 3.0, axis_y - 14.0, mark_x + 3.0, axis_y + 14.0))
            draw.line((mark_x, axis_y - 14.0, mark_x, axis_y + 14.0), fill=axis_rgb, width=3)
            text_bbox = draw_centered_text(
                draw,
                text=str(label),
                center=(mark_x, axis_y + 34.0),
                font=small_font,
                fill=label_rgb,
                stroke_fill=resolve_text_stroke_fill(label_rgb),
                stroke_width=1,
            )
            focal_boxes.append(bbox_union_many(tick, text_bbox, padding=3.0))
    focal_marks_bbox = bbox_union_many(*focal_boxes, padding=5.0)

    object_x = lens_x - float(scenario.object_x_factor) * focal
    object_height = float(render_defaults.get("object_arrow_height_px", 122))
    object_base = (object_x, axis_y)
    object_tip = (object_x, axis_y - object_height)
    draw_arrow(
        draw,
        start=object_base,
        end=object_tip,
        fill=stroke_rgb,
        width=int(render_defaults.get("object_arrow_width_px", 8)),
        head_length_px=float(render_defaults.get("object_arrow_head_length_px", 22)),
        head_width_px=float(render_defaults.get("object_arrow_head_width_px", 22)),
    )
    draw.line((object_x - 24, axis_y, object_x + 24, axis_y), fill=stroke_rgb, width=4)
    object_label_bbox = draw_centered_text(
        draw,
        text="object",
        center=(object_x, object_tip[1] - 26.0),
        font=label_font,
        fill=label_rgb,
        stroke_fill=resolve_text_stroke_fill(label_rgb),
        stroke_width=1,
    )
    object_arrow_bbox = _bbox((object_x - 31.0, object_tip[1] - 11.0, object_x + 31.0, axis_y + 10.0))
    object_annotation_bbox = bbox_union_many(object_arrow_bbox, object_label_bbox, padding=3.0)

    # Neutral construction guides indicate optical context without drawing the solved image.
    guide_y = object_tip[1]
    draw_dashed_line(
        draw,
        start=(object_x, guide_y),
        end=(lens_x, guide_y),
        fill=accent_rgb,
        width=2,
        dash_px=9,
        gap_px=7,
    )
    draw_dashed_line(
        draw,
        start=(object_x, object_tip[1]),
        end=(lens_x, axis_y),
        fill=accent_rgb,
        width=2,
        dash_px=9,
        gap_px=7,
    )

    option_cards = _draw_option_cards(
        draw,
        scenario=scenario,
        option_left=float(render_defaults.get("option_left_px", 796)),
        option_top=float(render_defaults.get("option_top_px", 82)),
        card_width=float(render_defaults.get("option_card_width_px", 278)),
        card_height=float(render_defaults.get("option_card_height_px", 116)),
        card_gap=float(render_defaults.get("option_card_gap_px", 18)),
        font_family=str(font_family),
        style=style,
    )
    option_bboxes = option_cards.option_bboxes

    annotation = {
        "lens": _clip_bbox(lens_annotation_bbox, width=width, height=height),
        "object_arrow": _clip_bbox(object_annotation_bbox, width=width, height=height),
        "focal_marks": _clip_bbox(focal_marks_bbox, width=width, height=height),
    }
    scene_entities = [
        {
            "entity_id": "lens",
            "entity_type": "converging_lens",
            "bbox_px": list(annotation["lens"]),
            "meta": {"lens_type": "converging"},
        },
        {
            "entity_id": "object_arrow",
            "entity_type": "object_arrow",
            "bbox_px": list(annotation["object_arrow"]),
            "meta": {"object_position_case": str(scenario.object_position_case)},
        },
        {
            "entity_id": "focal_marks",
            "entity_type": "focal_mark_set",
            "bbox_px": list(annotation["focal_marks"]),
            "meta": {"focal_length_px": float(focal)},
        },
    ]
    render_map = {
        "diagram_bbox_px": list(diagram),
        "axis_y_px": round(float(axis_y), 3),
        "lens_x_px": round(float(lens_x), 3),
        "focal_length_px": round(float(focal), 3),
        "object_x_px": round(float(object_x), 3),
        "object_position_case": str(scenario.object_position_case),
        "image_property": str(scenario.image_property),
        "correct_option_letter": str(scenario.correct_option_letter),
        "option_map": dict(scenario.option_map),
        "option_text_map": {str(letter): PROPERTY_TEXT[str(value)] for letter, value in scenario.option_map.items()},
        "option_bboxes_px": {str(letter): list(bbox) for letter, bbox in option_bboxes.items()},
        "option_letter_bboxes_px": {str(letter): list(bbox) for letter, bbox in option_cards.option_letter_bboxes.items()},
        "option_text_bboxes_px": {str(letter): list(bbox) for letter, bbox in option_cards.option_text_bboxes.items()},
        "annotation_keyed_bboxes_px": dict(annotation),
    }
    return _RenderedScene(
        image=image,
        annotation_bbox_map=dict(annotation),
        scene_entities=[dict(entity) for entity in scene_entities],
        render_map=dict(render_map),
    )


def _build_complexity(scenario: _Scenario) -> TaskComplexity:
    weights = resolve_physics_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=FAMILY_ID)
    conceptual = 0.60 if scenario.object_position_case in {"between_f_2f", "inside_f"} else 0.52
    return build_physics_complexity(
        weights=weights,
        components={
            "visual_scan": 0.28,
            "lens_reasoning": float(conceptual),
            "ambiguity": 0.12,
            "output_burden": 0.14,
        },
    )


@register_task
class PhysicsLensOpticsImagePropertyChoiceTask:
    """Choose the image property implied by a converging-lens object position."""

    task_id = TASK_ID
    domain = "physics"
    task_group = "optics"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        params = dict(params or {})
        axes = _resolve_axes(int(instance_seed), params)
        scenario = _make_scenario(int(instance_seed), axes, params)
        canvas_width = int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", 1120)))
        canvas_height = int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", 720)))
        background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
            instance_seed=int(instance_seed),
            params=params,
            scene_id=SCENE_ID,
            task_group=self.task_group,
            canvas_width=int(canvas_width),
            canvas_height=int(canvas_height),
            require_grid=True,
        )
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.font",
            params=params,
        )
        font_record = get_font_family_record(str(font_family))
        rendered = _render_scene(
            image=background,
            scenario=scenario,
            font_family=str(font_family),
            style=diagram_style,
            render_defaults=_RENDER_DEFAULTS,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered.image,
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
        answer_gt = TypedValue(type="option_letter", value=str(scenario.correct_option_letter))
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
                "scene_kind": f"physics_lens_optics_{scenario.scene_variant}",
                "entities": [dict(entity) for entity in rendered.scene_entities],
                "relations": {
                    "query_id": QUERY_ID,
                    "lens_type": "converging",
                    "object_position_case": str(scenario.object_position_case),
                    "image_property": str(scenario.image_property),
                    "correct_option_letter": str(scenario.correct_option_letter),
                    "accent_color_name": str(scenario.accent_color_name),
                    "option_map": dict(scenario.option_map),
                },
            },
            "query_spec": {
                "query_id": QUERY_ID,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(scenario.scene_variant),
                    "query_id": QUERY_ID,
                    "answer_support": list(OPTION_LETTERS),
                    "object_position_case": str(scenario.object_position_case),
                    "image_property": str(scenario.image_property),
                    "correct_option_letter": str(scenario.correct_option_letter),
                    "accent_color_name": str(axes.accent_color_name),
                    "target_answer": str(scenario.correct_option_letter),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "object_position_case_probabilities": dict(axes.object_position_case_probabilities),
                    "correct_option_letter_probabilities": dict(axes.correct_option_letter_probabilities),
                    "accent_color_name_probabilities": dict(axes.accent_color_name_probabilities),
                },
            },
            "render_spec": {
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "lens_optics_diagram",
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
            "render_map": dict(rendered.render_map),
            "execution_trace": {
                "query_id": QUERY_ID,
                "lens_type": "converging",
                "object_position_case": str(scenario.object_position_case),
                "image_property": str(scenario.image_property),
                "option_map": dict(scenario.option_map),
                "correct_option_letter": str(scenario.correct_option_letter),
                "accent_color_name": str(scenario.accent_color_name),
                "focal_length_px": float(scenario.focal_length_px),
                "object_x_factor": float(scenario.object_x_factor),
                "annotation_entity_ids": sorted(annotation_gt.value.keys()),
            },
            "witness_symbolic": {
                "type": "object_map",
                "ids": sorted(annotation_gt.value.keys()),
            },
            "projected_annotation": {
                "type": "keyed_bbox_map",
                "keyed_bbox_map": {str(k): list(v) for k, v in annotation_gt.value.items()},
                "pixel_keyed_bbox_map": {str(k): list(v) for k, v in annotation_gt.value.items()},
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
            complexity=_build_complexity(scenario),
            task_versions=default_task_versions(),
            query_id=QUERY_ID,
            scene_id=SCENE_ID,
        )


__all__ = [
    "CASE_TO_PROPERTY",
    "OBJECT_POSITION_CASES",
    "OPTION_LETTERS",
    "PROPERTY_TEXT",
    "PhysicsLensOpticsImagePropertyChoiceTask",
]
