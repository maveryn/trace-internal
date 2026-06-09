"""Shared paired-canvas rendering and task helpers for icon tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.seed import spawn_rng
from ....core.types import TypedValue
from ...base import TaskOutput
from ...shared.config_defaults import group_default, required_group_defaults
from ...shared.counting_sampling import resolve_counting_target_and_distractor_triplet
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.complexity import (
    build_icon_task_complexity,
    icon_scene_clutter_score,
    icon_target_density_balance,
    icon_visual_scan_score,
)
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_assets import render_icon_rgba, resolve_icon_pool
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import (
    BBox,
    draw_two_panel_panels,
    max_overlap_with_existing,
    panel_geometry_to_trace,
    resolve_two_panel_layout,
    sort_bboxes_reading_order,
)
from ..shared.icon_style import sample_icon_palette
from ..shared.icon_task_rendering import icon_render_style_trace, sample_icon_instance_noise
from ..shared.public_query_task import rewrite_icons_query_output


PANEL_SCENE_ID = "paired_canvas"


@dataclass(frozen=True)
class PairedCanvasDefaults:
    """Fallback defaults for paired-canvas icon tasks."""

    object_count_min: int = 5
    object_count_max: int = 10
    target_count_min: int = 1
    target_count_max: int = 5
    distractor_count_min: int = 1
    distractor_count_max: int = 5
    distractor_margin_over_target: int = 0
    canvas_width: int = 1104
    canvas_height: int = 640
    reference_panel_width_px: int = 516
    panel_gap_px: int = ICON_SHARED_DEFAULTS.panel_gap_px
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = 42
    scene_icon_size_max_px: int = 78
    reference_icon_size_px: int = 78
    reference_icon_size_min_px: int = 42
    reference_icon_size_max_px: int = 78
    scene_max_overlap_fraction: float = 0.04
    scene_placement_max_attempts: int = 160
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    pool_manifest: str = "all_icons.txt"
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 42.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = ICON_SHARED_DEFAULTS.icon_noise_edit_count_range
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: {
            str(edit_type): {str(key): tuple(bounds) for key, bounds in value.items()}
            for edit_type, value in ICON_SHARED_DEFAULTS.icon_noise_value_ranges.items()
        }
    )
    size_scale_small: float = 0.74
    size_scale_large: float = 1.18
    movement_delta_min: float = 0.22
    movement_delta_max: float = 0.34
    min_center_gap_frac: float = 0.135
    rotation_candidates_degrees: Tuple[int, ...] = (0, 90, 180, 270)


@dataclass(frozen=True)
class PairedIconSpec:
    """One icon instance to render in either paired-canvas panel."""

    instance_id: str
    identity_id: str
    icon_id: str
    panel: str
    x_frac: float
    y_frac: float
    nominal_size_px: int
    rotation_degrees: int
    tint_rgb: Tuple[int, int, int]
    noise_edits: Tuple[Any, ...] = ()
    noise_seed: int | None = None


@dataclass(frozen=True)
class RenderedPairedIcon:
    """Trace-ready rendered paired-canvas icon metadata."""

    instance_id: str
    identity_id: str
    icon_id: str
    panel: str
    bbox_xyxy: Tuple[int, int, int, int]
    center_xy: Tuple[float, float]
    normalized_center_xy: Tuple[float, float]
    nominal_size_px: int
    rotation_degrees: int
    tint_rgb: Tuple[int, int, int]
    noise_edits: Tuple[Dict[str, Any], ...]
    noise_seed: int | None
    role: str = "neutral"
    changed_attributes: Tuple[str, ...] = ()
    movement_direction: str | None = None


@dataclass(frozen=True)
class PairedCanvasPayload:
    """Rendered paired-canvas task payload."""

    image: Image.Image
    panel_geometry: Dict[str, Any]
    left_icons: Tuple[Dict[str, Any], ...]
    right_icons: Tuple[Dict[str, Any], ...]
    matching_right_indices: Tuple[int, ...]
    matching_left_indices: Tuple[int, ...]
    target_count: int
    object_count: int
    distractor_count: int
    query_id: str
    query_probabilities: Dict[str, float]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    object_count_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    distractor_count_probabilities: Dict[str, float]
    question_format: str
    trace_relation: Dict[str, Any]


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _center_from_bbox(bbox: Sequence[int | float]) -> Tuple[float, float]:
    return (
        0.5 * (float(bbox[0]) + float(bbox[2])),
        0.5 * (float(bbox[1]) + float(bbox[3])),
    )


def _bbox_for_center(*, content_bbox: BBox, x_frac: float, y_frac: float, sprite_size: Tuple[int, int]) -> BBox:
    x0, y0, x1, y1 = tuple(int(value) for value in content_bbox)
    sprite_w, sprite_h = int(sprite_size[0]), int(sprite_size[1])
    content_w = max(1, int(x1 - x0))
    content_h = max(1, int(y1 - y0))
    cx = int(round(float(x0) + (_clip01(float(x_frac)) * float(content_w))))
    cy = int(round(float(y0) + (_clip01(float(y_frac)) * float(content_h))))
    paste_x0 = int(max(x0, min(x1 - sprite_w, cx - (sprite_w // 2))))
    paste_y0 = int(max(y0, min(y1 - sprite_h, cy - (sprite_h // 2))))
    return (paste_x0, paste_y0, int(paste_x0 + sprite_w), int(paste_y0 + sprite_h))


def _serialize_icon(rendered: RenderedPairedIcon) -> Dict[str, Any]:
    return {
        "entity_kind": "icon_instance",
        "instance_id": str(rendered.instance_id),
        "identity_id": str(rendered.identity_id),
        "icon_id": str(rendered.icon_id),
        "panel": str(rendered.panel),
        "bbox_xyxy": [int(value) for value in rendered.bbox_xyxy],
        "center_xy": [round(float(value), 3) for value in rendered.center_xy],
        "normalized_center_xy": [round(float(value), 4) for value in rendered.normalized_center_xy],
        "nominal_size_px": int(rendered.nominal_size_px),
        "rotation_degrees": int(rendered.rotation_degrees) % 360,
        "tint_rgb": [int(value) for value in rendered.tint_rgb],
        "noise_edits": [dict(edit) for edit in rendered.noise_edits],
        "noise_seed": None if rendered.noise_seed is None else int(rendered.noise_seed),
        "role": str(rendered.role),
        "changed_attributes": [str(value) for value in rendered.changed_attributes],
        "movement_direction": rendered.movement_direction,
    }


def render_paired_canvas(
    *,
    left_icons: Sequence[PairedIconSpec],
    right_icons: Sequence[PairedIconSpec],
    render_params: Mapping[str, Any],
) -> Tuple[Image.Image, Dict[str, Any], Tuple[Dict[str, Any], ...], Tuple[Dict[str, Any], ...]]:
    """Render a two-canvas icon scene with explicit normalized positions."""

    layout = resolve_two_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        reference_panel_width_px=int(render_params["reference_panel_width_px"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_gap_px=int(render_params["panel_gap_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
    draw_two_panel_panels(
        image=image,
        layout=layout,
        background_rgb=tuple(int(v) for v in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(v) for v in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(v) for v in render_params["header_text_rgb"]),
        corner_radius_px=int(render_params["panel_corner_radius_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
        reference_title="Left",
        scene_title="Right",
        icon_canvas_style=render_params.get("_icon_canvas_style_object"),
    )

    rendered_by_panel: Dict[str, List[RenderedPairedIcon]] = {"left": [], "right": []}
    placed_by_panel: Dict[str, List[BBox]] = {"left": [], "right": []}
    content_by_panel = {
        "left": tuple(int(value) for value in layout.reference_content_xyxy),
        "right": tuple(int(value) for value in layout.scene_content_xyxy),
    }
    max_overlap = float(render_params["scene_max_overlap_fraction"])
    for panel_name, specs in (("left", left_icons), ("right", right_icons)):
        content_bbox = content_by_panel[panel_name]
        for spec in specs:
            sprite = render_icon_rgba(
                icon_id=str(spec.icon_id),
                size_px=int(spec.nominal_size_px),
                tint_rgb=tuple(int(value) for value in spec.tint_rgb),
                rotation_degrees=int(spec.rotation_degrees),
                noise_edits=tuple(spec.noise_edits),
                noise_seed=spec.noise_seed,
            )
            bbox = _bbox_for_center(
                content_bbox=content_bbox,
                x_frac=float(spec.x_frac),
                y_frac=float(spec.y_frac),
                sprite_size=sprite.size,
            )
            if float(max_overlap_with_existing(bbox, placed_by_panel[panel_name])) > max_overlap:
                raise ValueError("paired icon canvas placement overlap exceeded configured cap")
            image.alpha_composite(sprite, (int(bbox[0]), int(bbox[1])))
            placed_by_panel[panel_name].append(tuple(int(value) for value in bbox))
            center_xy = _center_from_bbox(bbox)
            rendered_by_panel[panel_name].append(
                RenderedPairedIcon(
                    instance_id=str(spec.instance_id),
                    identity_id=str(spec.identity_id),
                    icon_id=str(spec.icon_id),
                    panel=str(panel_name),
                    bbox_xyxy=tuple(int(value) for value in bbox),
                    center_xy=(float(center_xy[0]), float(center_xy[1])),
                    normalized_center_xy=(float(spec.x_frac), float(spec.y_frac)),
                    nominal_size_px=int(spec.nominal_size_px),
                    rotation_degrees=int(spec.rotation_degrees) % 360,
                    tint_rgb=tuple(int(value) for value in spec.tint_rgb),
                    noise_edits=serialize_icon_noise_edits(spec.noise_edits),
                    noise_seed=None if spec.noise_seed is None else int(spec.noise_seed),
                )
            )

    return (
        image.convert("RGB"),
        panel_geometry_to_trace(layout),
        tuple(_serialize_icon(icon) for icon in rendered_by_panel["left"]),
        tuple(_serialize_icon(icon) for icon in rendered_by_panel["right"]),
    )


def choose_query_id(
    rng,
    *,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
    query_ids: Sequence[str],
    weight_key: str,
    explicit_keys: Sequence[str] = ("query_id", "query_variant"),
) -> Tuple[str, Dict[str, float]]:
    """Resolve one public query id with balanced sampling when weights are uniform."""

    supported = tuple(str(query) for query in query_ids)
    explicit = None
    for key in explicit_keys:
        if key in params and params.get(key) is not None and str(params.get(key)) != "default":
            explicit = str(params.get(key))
            break
    if explicit is not None:
        if explicit not in set(supported):
            raise ValueError(f"unsupported query id for {task_id}: {explicit}")
        return str(explicit), {query: (1.0 if query == explicit else 0.0) for query in supported}

    raw_weights = params.get(
        weight_key,
        params.get(
            "query_id_weights",
            params.get("query_variant_weights", gen_defaults.get(weight_key, {query: 1.0 for query in supported})),
        ),
    )
    if not isinstance(raw_weights, Mapping):
        raise ValueError(f"{weight_key} must be a mapping when provided")
    probabilities = normalize_positive_weights(
        {str(key): float(value) for key, value in raw_weights.items() if str(key) in set(supported)},
        default_keys=supported,
    )
    selected = str(weighted_choice(rng, probabilities, sort_keys=True))
    enabled = bool(params.get("balanced_query_sampling", gen_defaults.get("balanced_query_sampling", True)))
    overridden = any(
        key in params and params.get(key) is not None
        for key in (weight_key, "query_id_weights", "query_variant_weights")
    )
    positive_values = [float(value) for value in probabilities.values() if float(value) > 0.0]
    if bool(enabled) and (not overridden) and positive_values and max(positive_values) - min(positive_values) <= 1e-9:
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}:query",
        )
        positives = [query for query in supported if float(probabilities.get(query, 0.0)) > 0.0]
        selected = str(positives[int(selection_index) % len(positives)])
    return str(selected), {str(key): float(value) for key, value in sorted(probabilities.items())}


def resolve_paired_counts(
    rng,
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    gen_defaults: Mapping[str, Any],
    defaults: PairedCanvasDefaults,
) -> Tuple[int, Dict[str, float], int, Dict[str, float], int, Dict[str, float]]:
    """Resolve target/distractor counts for a paired-canvas counting task."""

    return resolve_counting_target_and_distractor_triplet(
        rng,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=gen_defaults,
        fallback_total_min=int(defaults.object_count_min),
        fallback_total_max=int(defaults.object_count_max),
        fallback_target_min=int(defaults.target_count_min),
        fallback_target_max=int(defaults.target_count_max),
        fallback_distractor_min=int(defaults.distractor_count_min),
        fallback_distractor_max=int(defaults.distractor_count_max),
    )


def sample_palette(rng, *, render_params: Mapping[str, Any]) -> Tuple[Tuple[int, int, int], ...]:
    """Sample a background-safe icon palette."""

    palette_size_min = max(2, int(render_params["palette_size_min"]))
    palette_size_max = max(palette_size_min, int(render_params["palette_size_max"]))
    return tuple(
        tuple(int(channel) for channel in color)
        for color in sample_icon_palette(
            rng,
            palette_size=int(rng.randint(palette_size_min, palette_size_max)),
            channel_min=int(render_params["color_channel_min"]),
            channel_max=int(render_params["color_channel_max"]),
            anchor_colors=(
                tuple(int(v) for v in render_params["background_color_rgb"]),
                tuple(int(v) for v in render_params["panel_fill_rgb"]),
                tuple(int(v) for v in render_params["panel_border_rgb"]),
                tuple(int(v) for v in render_params["header_text_rgb"]),
            ),
            min_color_distance=float(render_params["min_color_distance"]),
            distance_space=str(render_params["color_distance_space"]),
        )
    )


def sample_positions(
    rng,
    *,
    count: int,
    min_gap_frac: float,
    max_attempts: int = 600,
) -> Tuple[Tuple[float, float], ...]:
    """Sample normalized panel positions with a minimum center gap."""

    positions: List[Tuple[float, float]] = []
    gap = max(0.02, float(min_gap_frac))
    for _ in range(int(max_attempts)):
        if len(positions) >= int(count):
            break
        x = float(rng.uniform(0.12, 0.88))
        y = float(rng.uniform(0.13, 0.88))
        if all(((x - ox) ** 2 + (y - oy) ** 2) ** 0.5 >= gap for ox, oy in positions):
            positions.append((x, y))
    if len(positions) < int(count):
        raise ValueError("failed to sample separated paired-canvas positions")
    return tuple((float(x), float(y)) for x, y in positions)


def make_icon_spec(
    *,
    instance_seed: int,
    namespace: str,
    render_params: Mapping[str, Any],
    instance_id: str,
    identity_id: str,
    icon_id: str,
    panel: str,
    position: Tuple[float, float],
    tint_rgb: Tuple[int, int, int],
    size_px: int,
    rotation_degrees: int,
) -> PairedIconSpec:
    """Build one render spec with deterministic per-icon noise."""

    noise_edits, noise_seed = sample_icon_instance_noise(
        instance_seed=int(instance_seed),
        namespace=str(namespace),
        render_params=render_params,
    )
    return PairedIconSpec(
        instance_id=str(instance_id),
        identity_id=str(identity_id),
        icon_id=str(icon_id),
        panel=str(panel),
        x_frac=float(position[0]),
        y_frac=float(position[1]),
        nominal_size_px=int(size_px),
        rotation_degrees=int(rotation_degrees) % 360,
        tint_rgb=tuple(int(value) for value in tint_rgb),
        noise_edits=tuple(noise_edits),
        noise_seed=int(noise_seed),
    )


def sample_base_attributes(
    rng,
    *,
    pool: Sequence[str],
    palette: Sequence[Tuple[int, int, int]],
    count: int,
    render_params: Mapping[str, Any],
    rotation_candidates: Sequence[int],
) -> List[Dict[str, Any]]:
    """Sample visually matchable icon attributes."""

    if len(pool) < int(count):
        raise ValueError("icon pool is too small for paired-canvas task")
    icon_ids = [str(value) for value in pool[: int(count)]]
    attrs: List[Dict[str, Any]] = []
    min_size = int(render_params["scene_icon_size_min_px"])
    max_size = int(render_params["scene_icon_size_max_px"])
    for index, icon_id in enumerate(icon_ids):
        attrs.append(
            {
                "identity_id": f"icon_{index}",
                "icon_id": str(icon_id),
                "tint_rgb": tuple(int(value) for value in rng.choice(tuple(palette))),
                "size_px": int(rng.randint(min_size, max_size)),
                "rotation_degrees": int(rng.choice(tuple(int(v) for v in rotation_candidates))),
            }
        )
    return attrs


def annotation_from_indices(*, panel_icons: Sequence[Mapping[str, Any]], indices: Sequence[int]) -> List[List[int]]:
    """Return reading-order bbox annotation from selected panel icon indices."""

    selected = []
    for index in indices:
        bbox = panel_icons[int(index)].get("bbox_xyxy", ())
        selected.append([int(round(float(value))) for value in bbox])
    return sort_bboxes_reading_order(selected)


def build_paired_prompt(
    *,
    domain: str,
    task_group: str,
    prompt_defaults: Mapping[str, Any],
    question_text: str,
    instance_seed: int,
) -> Any:
    """Render prompt variants for one paired-canvas task."""

    prompt_selection = render_task_prompt_variants(
        domain=str(domain),
        task_group=str(task_group),
        bundle_id=str(prompt_defaults["bundle_id"]),
        scene_key=str(prompt_defaults["scene_key"]),
        task_key=str(prompt_defaults["task_key"]),
        answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
        slots={
            "object_description": str(prompt_defaults["object_description"]),
            "question_text": str(question_text),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "annotation_hint": str(prompt_defaults["annotation_hint"]),
            "answer_hint": str(prompt_defaults["answer_hint"]),
            "json_example": str(prompt_defaults["json_example"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
        },
        instance_seed=int(instance_seed),
    )
    return build_prompt_trace_artifacts(prompt_selection)


def paired_task_output(
    *,
    task_id: str,
    domain: str,
    task_group: str,
    payload: PairedCanvasPayload,
    prompt_artifacts: Any,
    prompt_defaults: Mapping[str, Any],
    render_params: Mapping[str, Any],
    annotation_panel: str,
    answer_value: int,
    annotation_bboxes: Sequence[Sequence[int]],
    complexity: Any,
) -> TaskOutput:
    """Build one TaskOutput for paired-canvas count tasks."""

    entities = [dict(item) for item in payload.left_icons] + [dict(item) for item in payload.right_icons]
    trace_payload = {
        "scene_ir": {
            "scene_kind": f"icons_{PANEL_SCENE_ID}",
            "entities": entities,
            "relations": dict(payload.trace_relation),
            "frames": {
                "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                "panels": dict(payload.panel_geometry),
            },
        },
        "query_spec": {
            "query_id": str(payload.query_id),
            "template_id": str(prompt_defaults["bundle_id"]),
            "prompt_variant": dict(prompt_artifacts.prompt_variant),
            "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
            "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
            "params": {
                "query_id": str(payload.query_id),
                "query_id_probabilities": dict(payload.query_probabilities),
                "object_count": int(payload.object_count),
                "object_count_probabilities": dict(payload.object_count_probabilities),
                "target_count": int(payload.target_count),
                "target_count_probabilities": dict(payload.target_count_probabilities),
                "distractor_count": int(payload.distractor_count),
                "distractor_count_probabilities": dict(payload.distractor_count_probabilities),
                "annotation_panel": str(annotation_panel),
            },
        },
        "render_spec": {
            "canvas_size": [int(render_params["canvas_width"]), int(render_params["canvas_height"])],
            "coord_space": "pixel",
            "panel_geometry": dict(payload.panel_geometry),
            "style": icon_render_style_trace(
                render_params=render_params,
                sampled_palette_rgb=payload.sampled_palette_rgb,
            ),
        },
        "render_map": {
            "image_id": "img0",
            "anchors": {
                "left_icons": [dict(item) for item in payload.left_icons],
                "right_icons": [dict(item) for item in payload.right_icons],
            },
        },
        "execution_trace": {
            "scene_variant": PANEL_SCENE_ID,
            "query_id": str(payload.query_id),
            "query_id_probabilities": dict(payload.query_probabilities),
            "question_format": str(payload.question_format),
            "object_count": int(payload.object_count),
            "object_count_probabilities": dict(payload.object_count_probabilities),
            "target_count": int(payload.target_count),
            "target_count_probabilities": dict(payload.target_count_probabilities),
            "distractor_count": int(payload.distractor_count),
            "distractor_count_probabilities": dict(payload.distractor_count_probabilities),
            "matching_right_indices": list(payload.matching_right_indices),
            "matching_left_indices": list(payload.matching_left_indices),
            "annotation_panel": str(annotation_panel),
            **dict(payload.trace_relation),
        },
        "witness_symbolic": {
            "query_id": str(payload.query_id),
            "matching_right_indices": list(payload.matching_right_indices),
            "matching_left_indices": list(payload.matching_left_indices),
            "annotation_panel": str(annotation_panel),
        },
        "projected_annotation": {
            "type": "bbox_set",
            "bbox_set": [list(bbox) for bbox in annotation_bboxes],
            "pixel_bbox_set": [list(bbox) for bbox in annotation_bboxes],
            "pixel_point_set": [
                [
                    round((float(bbox[0]) + float(bbox[2])) / 2.0, 3),
                    round((float(bbox[1]) + float(bbox[3])) / 2.0, 3),
                ]
                for bbox in annotation_bboxes
            ],
        },
    }
    output = TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        answer_gt=TypedValue(type="integer", value=int(answer_value)),
        annotation_gt=TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes]),
        image=payload.image,
        image_id="img0",
        trace_payload=trace_payload,
        complexity=complexity,
        task_versions=default_task_versions(),
        query_id=str(payload.query_id),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
    )
    return rewrite_icons_query_output(
        output,
        query_id=str(payload.query_id),
        scene_id=PANEL_SCENE_ID,
        query_probabilities=payload.query_probabilities,
    )


def paired_complexity(
    *,
    task_group_defaults: Mapping[str, Any],
    task_id: str,
    object_count: int,
    target_count: int,
    object_count_min: int,
    object_count_max: int,
    left_icons: Sequence[Mapping[str, Any]],
    right_icons: Sequence[Mapping[str, Any]],
    render_params: Mapping[str, Any],
    rule_score: float,
) -> Any:
    """Build generic paired-canvas icon task complexity."""

    visual_scan = icon_visual_scan_score(
        object_count=int(object_count),
        object_count_min=int(object_count_min),
        object_count_max=int(object_count_max),
    )
    ambiguity = icon_target_density_balance(target_count=int(target_count), object_count=max(1, int(object_count)))
    clutter = icon_scene_clutter_score(
        scene_instances=[*list(left_icons), *list(right_icons)],
        scene_icon_size_min_px=int(render_params["scene_icon_size_min_px"]),
        scene_icon_size_max_px=int(render_params["scene_icon_size_max_px"]),
        scene_max_overlap_fraction=float(render_params["scene_max_overlap_fraction"]),
        noise_edit_count_range=render_params["icon_noise_edit_count_range"],
    )
    weights = {
        "visual_scan": float(visual_scan),
        "semantic_match": float(rule_score),
        "rule_inference": float(rule_score),
        "spatial_reasoning": float(rule_score),
        "ambiguity": float(ambiguity),
        "clutter": float(clutter),
    }
    return build_icon_task_complexity(
        task_group_defaults=task_group_defaults,
        task_id=str(task_id),
        criterion_values=weights,
    )


def required_paired_prompt_defaults(prompt_defaults: Mapping[str, Any], *, task_id: str) -> Dict[str, Any]:
    """Return prompt defaults needed by paired-canvas tasks."""

    required = required_group_defaults(
        prompt_defaults,
        (
            "bundle_id",
            "scene_key",
            "task_key",
            "json_output_contract",
            "json_output_contract_answer_only",
            "object_description",
            "annotation_hint",
            "answer_hint",
            "json_example",
            "json_example_answer_only",
        ),
        context=f"prompt defaults for {task_id}",
    )
    merged = dict(prompt_defaults)
    merged.update(required)
    return merged


__all__ = [
    "PANEL_SCENE_ID",
    "PairedCanvasDefaults",
    "PairedCanvasPayload",
    "PairedIconSpec",
    "build_paired_prompt",
    "choose_query_id",
    "annotation_from_indices",
    "make_icon_spec",
    "paired_complexity",
    "paired_task_output",
    "render_paired_canvas",
    "required_paired_prompt_defaults",
    "resolve_icon_pool",
    "resolve_paired_counts",
    "sample_base_attributes",
    "sample_palette",
    "sample_positions",
    "spawn_rng",
]
