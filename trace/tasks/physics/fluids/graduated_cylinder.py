"""Physics fluid-measurement tasks for graduated-cylinder diagrams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Tuple

from PIL import Image, ImageDraw

from ....core.seed import hash64, spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.drawing import draw_centered_text
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_json_example import build_prompt_json_examples
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ...shared.text_legibility import draw_traced_text
from ...shared.text_rendering import load_font, resolve_text_stroke_fill
from ..shared.diagram_style import prepare_physics_diagram_style_and_background
from ..shared.visual_defaults import load_physics_noise_defaults


FAMILY_ID = "physics_fluids_graduated_cylinder_family"
SCENE_ID = "graduated_cylinder"
POST_IMAGE_NOISE_DEFAULTS = load_physics_noise_defaults(task_group="fluids", apply_prob=0.5)
_TASK_GROUP_DEFAULTS = get_task_group_defaults("physics", "fluids")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=FAMILY_ID,
)


@dataclass(frozen=True)
class _CylinderScale:
    capacity_ml: int
    major_tick_ml: int
    minor_tick_ml: int


@dataclass(frozen=True)
class _CylinderGeometry:
    left: float
    top: float
    width: float
    height: float
    bottom: float
    scale_left: bool


def _bbox(values: Tuple[float, float, float, float]) -> List[float]:
    return [round(float(value), 3) for value in values]


def _volume_to_y(geometry: _CylinderGeometry, scale: _CylinderScale, volume_ml: int) -> float:
    usable_top = float(geometry.top + 28)
    usable_bottom = float(geometry.bottom - 22)
    frac = max(0.0, min(1.0, float(volume_ml) / float(scale.capacity_ml)))
    return float(usable_bottom - frac * (usable_bottom - usable_top))


def _draw_label(draw: ImageDraw.ImageDraw, xy: Tuple[float, float], text: str, font: Any, fill: Tuple[int, int, int]) -> List[float]:
    bbox = draw.textbbox((float(xy[0]), float(xy[1])), str(text), font=font, stroke_width=1)
    draw_traced_text(
        draw,
        xy=(float(xy[0]), float(xy[1])),
        text=str(text),
        font=font,
        fill_rgb=fill,
        stroke_width=1,
        stroke_rgb=resolve_text_stroke_fill(fill),
        role="readout",
        required=True,
    )
    return _bbox(tuple(float(v) for v in bbox))


def _draw_cylinder(
    draw: ImageDraw.ImageDraw,
    *,
    geometry: _CylinderGeometry,
    scale: _CylinderScale,
    volume_ml: int,
    title: str,
    font_family: str,
    style: Any,
    liquid_rgb: Tuple[int, int, int],
) -> Dict[str, Any]:
    label_font = load_font(22, bold=True, font_family=font_family)
    small_font = load_font(18, bold=True, font_family=font_family)
    title_font = load_font(24, bold=True, font_family=font_family)
    outline = tuple(int(v) for v in style.stroke_rgb)
    guide = tuple(int(v) for v in style.guide_rgb)
    text_rgb = tuple(int(v) for v in style.label_rgb)
    glass_fill = (238, 247, 252)

    left, top, width, height, bottom = geometry.left, geometry.top, geometry.width, geometry.height, geometry.bottom
    right = float(left + width)
    body = (left, top + 18, right, bottom)
    draw.rounded_rectangle(body, radius=16, fill=glass_fill, outline=outline, width=4)
    draw.ellipse((left, top, right, top + 38), fill=(248, 252, 254), outline=outline, width=4)
    draw.arc((left, bottom - 20, right, bottom + 20), 0, 180, fill=outline, width=3)

    level_y = _volume_to_y(geometry, scale, volume_ml)
    fill_box = (left + 8, level_y, right - 8, bottom - 10)
    draw.rectangle(fill_box, fill=tuple(int(v) for v in liquid_rgb))
    draw.arc((left + 8, level_y - 10, right - 8, level_y + 10), 0, 180, fill=tuple(max(0, int(v) - 40) for v in liquid_rgb), width=4)
    draw.line((left + 10, level_y, right - 10, level_y), fill=tuple(max(0, int(v) - 45) for v in liquid_rgb), width=2)

    scale_x = left - 20 if geometry.scale_left else right + 20
    tick_dir = 1 if geometry.scale_left else -1
    label_x = scale_x - 54 if geometry.scale_left else scale_x + 10
    scale_bboxes: List[List[float]] = []
    for tick_value in range(0, int(scale.capacity_ml) + 1, int(scale.minor_tick_ml)):
        y = _volume_to_y(geometry, scale, tick_value)
        is_major = tick_value % int(scale.major_tick_ml) == 0
        tick_len = 22 if is_major else 12
        draw.line((scale_x, y, scale_x + tick_dir * tick_len, y), fill=outline if is_major else guide, width=3 if is_major else 2)
        if is_major:
            text_bbox = _draw_label(draw, (label_x, y - 11), str(tick_value), small_font, text_rgb)
            scale_bboxes.append(text_bbox)
    unit_bbox = _draw_label(draw, (label_x, bottom + 18), "mL", small_font, text_rgb)
    scale_bboxes.append(unit_bbox)
    title_bbox = draw_centered_text(
        draw,
        text=str(title),
        center=(left + width * 0.5, top - 24),
        font=title_font,
        fill=text_rgb,
        stroke_fill=resolve_text_stroke_fill(text_rgb),
        stroke_width=1,
    )

    scale_region = _bbox(
        (
            min([scale_x] + [b[0] for b in scale_bboxes]) - 8,
            min(b[1] for b in scale_bboxes) - 8,
            max([scale_x] + [b[2] for b in scale_bboxes]) + 8,
            max(b[3] for b in scale_bboxes) + 8,
        )
    )
    meniscus = _bbox((left + 8, level_y - 12, right - 8, level_y + 12))
    return {
        "meniscus": meniscus,
        "scale_region": scale_region,
        "title_bbox": title_bbox,
        "level_y": round(float(level_y), 3),
        "volume_ml": int(volume_ml),
    }


def _choose_scale(instance_seed: int) -> _CylinderScale:
    options = (
        _CylinderScale(50, 10, 5),
        _CylinderScale(80, 20, 5),
        _CylinderScale(100, 20, 5),
        _CylinderScale(120, 20, 10),
    )
    return options[int(hash64(int(instance_seed), f"{FAMILY_ID}.scale", 0) % len(options))]


def _choose_volume(instance_seed: int, scale: _CylinderScale, *, min_ml: int = 10, max_margin_ml: int = 10) -> int:
    support = [v for v in range(int(min_ml), int(scale.capacity_ml - max_margin_ml) + 1, int(scale.minor_tick_ml))]
    support = [v for v in support if v % int(scale.major_tick_ml) != 0 or len(support) < 8]
    return int(support[int(hash64(int(instance_seed), f"{FAMILY_ID}.volume", 0) % len(support))])


class _PhysicsGraduatedCylinderBaseTask:
    domain = "physics"
    task_group = "fluids"
    default_dataset_enabled = True
    fixed_query_id: str

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        _ = int(max_attempts)
        params = dict(params or {})
        query_id = str(self.fixed_query_id)
        canvas_width = int(_RENDER_DEFAULTS.get("canvas_width", 1040))
        canvas_height = int(_RENDER_DEFAULTS.get("canvas_height", 720))
        background, background_meta, diagram_style, diagram_style_meta = prepare_physics_diagram_style_and_background(
            instance_seed=int(instance_seed),
            params=params,
            scene_id=SCENE_ID,
            task_group=self.task_group,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            require_grid=True,
        )
        draw = ImageDraw.Draw(background)
        rng = spawn_rng(int(instance_seed), f"{FAMILY_ID}.scene")
        font_family = sample_font_family(
            role="readout",
            instance_seed=int(instance_seed),
            namespace=f"{FAMILY_ID}.font",
            params=params,
        )
        font_record = get_font_family_record(str(font_family))
        scale = _choose_scale(int(instance_seed))
        liquid_palette = [(93, 168, 218), (72, 181, 154), (146, 183, 77), (120, 148, 226)]
        liquid_rgb = liquid_palette[int(hash64(int(instance_seed), f"{FAMILY_ID}.liquid", 0) % len(liquid_palette))]
        draw.rounded_rectangle((54, 52, canvas_width - 54, canvas_height - 58), radius=18, fill=tuple(diagram_style.panel_fill_rgb), outline=tuple(diagram_style.panel_border_rgb), width=3)

        if query_id == "single_cylinder_volume_readout":
            volume_ml = int(params.get("volume_ml", _choose_volume(int(instance_seed), scale)))
            geometry = _CylinderGeometry(
                left=float(canvas_width * 0.44),
                top=150.0 + rng.randint(-10, 10),
                width=170.0,
                height=420.0,
                bottom=570.0 + rng.randint(-8, 8),
                scale_left=bool(hash64(int(instance_seed), f"{FAMILY_ID}.scale_side", 0) % 2),
            )
            rendered = _draw_cylinder(
                draw,
                geometry=geometry,
                scale=scale,
                volume_ml=volume_ml,
                title="Volume",
                font_family=str(font_family),
                style=diagram_style,
                liquid_rgb=liquid_rgb,
            )
            answer_value = int(volume_ml)
            annotation_map = {
                "meniscus": list(rendered["meniscus"]),
                "scale_region": list(rendered["scale_region"]),
            }
            render_map = {"cylinders": {"single": rendered}, "scale": scale.__dict__}
        else:
            before = _choose_volume(int(instance_seed), scale, min_ml=10, max_margin_ml=35)
            displacement_support = [
                v
                for v in range(int(scale.minor_tick_ml), 41, int(scale.minor_tick_ml))
                if before + v <= scale.capacity_ml - 8
            ]
            displacement = int(displacement_support[int(hash64(int(instance_seed), f"{FAMILY_ID}.displacement", 0) % len(displacement_support))])
            after = int(before + displacement)
            left_geometry = _CylinderGeometry(210.0, 158.0, 155.0, 405.0, 565.0, True)
            right_geometry = _CylinderGeometry(650.0, 158.0, 155.0, 405.0, 565.0, False)
            before_rendered = _draw_cylinder(
                draw,
                geometry=left_geometry,
                scale=scale,
                volume_ml=before,
                title="Before",
                font_family=str(font_family),
                style=diagram_style,
                liquid_rgb=liquid_rgb,
            )
            after_rendered = _draw_cylinder(
                draw,
                geometry=right_geometry,
                scale=scale,
                volume_ml=after,
                title="After",
                font_family=str(font_family),
                style=diagram_style,
                liquid_rgb=liquid_rgb,
            )
            # A simple submerged object, drawn below the after meniscus without
            # hiding the scale or the readout line.
            obj_cx = right_geometry.left + right_geometry.width * 0.52
            obj_y = min(right_geometry.bottom - 56, float(after_rendered["level_y"]) + 46)
            draw.ellipse((obj_cx - 28, obj_y - 22, obj_cx + 28, obj_y + 22), fill=(154, 114, 88), outline=tuple(diagram_style.stroke_rgb), width=3)
            answer_value = int(displacement)
            annotation_map = {
                "before_meniscus": list(before_rendered["meniscus"]),
                "before_scale_region": list(before_rendered["scale_region"]),
                "after_meniscus": list(after_rendered["meniscus"]),
                "after_scale_region": list(after_rendered["scale_region"]),
            }
            render_map = {
                "cylinders": {"before": before_rendered, "after": after_rendered},
                "scale": scale.__dict__,
                "before_volume_ml": int(before),
                "after_volume_ml": int(after),
                "displacement_ml": int(displacement),
            }

        image, post_noise_meta = apply_post_image_noise(
            background,
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
                f"answer_hint_{query_id}",
                f"annotation_hint_{query_id}",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        answer_gt = TypedValue(type="integer", value=int(answer_value))
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
            query_key=str(query_id),
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{query_id}"]),
                "annotation_hint": str(prompt_defaults[f"annotation_hint_{query_id}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"physics_graduated_cylinder_{query_id}",
                "entities": [],
                "relations": {
                    "query_id": str(query_id),
                    "scale": scale.__dict__,
                    "target_answer": int(answer_value),
                },
            },
            "query_spec": {
                "query_id": str(query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_id": str(query_id),
                    "target_answer": int(answer_value),
                    "answer_support": list(range(0, int(scale.capacity_ml) + 1, int(scale.minor_tick_ml))),
                },
            },
            "render_spec": {
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "font": {
                    "font_family": str(font_family),
                    "font_asset_version": font_asset_version(),
                    "font_asset": font_record.to_trace(),
                    "scope": "graduated_cylinder_diagram",
                },
                "technical_diagram_style": dict(diagram_style_meta),
                "background_style": background_meta,
                "post_image_noise": post_noise_meta,
            },
            "render_map": dict(render_map),
            "execution_trace": {
                "query_id": str(query_id),
                "target_answer": int(answer_value),
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
                complexity_score=0.36 if query_id == "single_cylinder_volume_readout" else 0.48,
                complexity_components={
                    "visual_readout": 0.46,
                    "arithmetic": 0.12 if query_id == "before_after_displacement_volume" else 0.0,
                    "ambiguity": 0.12,
                    "output_burden": 0.10,
                },
            ),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(query_id),
        )


@register_task
class PhysicsGraduatedCylinderVolumeReadoutValueTask(_PhysicsGraduatedCylinderBaseTask):
    """Read one graduated-cylinder liquid volume."""

    task_id = "task_physics__graduated_cylinder__volume_readout_value"
    fixed_query_id = "single_cylinder_volume_readout"


@register_task
class PhysicsGraduatedCylinderDisplacementVolumeValueTask(_PhysicsGraduatedCylinderBaseTask):
    """Compute displaced volume from before/after graduated-cylinder readings."""

    task_id = "task_physics__graduated_cylinder__displacement_volume_value"
    fixed_query_id = "before_after_displacement_volume"
