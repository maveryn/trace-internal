"""Select the wallpaper panel matching a reference wallpaper pattern."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.scene_config import get_scene_defaults
from ....core.taxonomy import resolve_task_taxonomy
from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_generation_rendering_prompt_defaults,
)
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_legibility import draw_centered_traced_text
from ...shared.text_rendering import load_font
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.annotation import keyed_bbox_map_annotation
from ..shared.icon_grid_scene import resolve_fixed_grid_cell_slots
from ..shared.icon_style import sample_single_icon_tint
from ..shared.icon_task_rendering import icon_render_style_trace, resolve_icon_cell_render_params
from ..shared.scene_style import draw_icon_panel_chrome, make_icon_canvas_background
from .wallpaper_shared import (
    LATTICE_COLS,
    LATTICE_ROWS,
    OPTION_LABELS,
    WALLPAPER_GROUP_IDS,
    draw_wallpaper_motifs,
    resolve_wallpaper_group_support,
    select_distinct_icon_ids,
    uniform_str_probability_map,
    wallpaper_chrome_policy_trace,
    wallpaper_safe_canvas_params,
)


TASK_ID = "task_icons__wallpaper_panels__same_pattern_as_reference_label"
SCENE_ID = "wallpaper_panels"
QUERY_ID = "same_pattern_as_reference_label"
REFERENCE_LABEL = "Reference"


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for reference wallpaper matching."""

    option_count_choices: Tuple[int, ...] = (6,)
    lattice_rows: int = LATTICE_ROWS
    lattice_cols: int = LATTICE_COLS
    wallpaper_group_ids: Tuple[str, ...] = WALLPAPER_GROUP_IDS
    canvas_width: int = 1104
    canvas_height: int = 640
    reference_panel_width_px: int = 300
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = 16
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    option_panel_gap_px: int = 18
    scene_icon_size_min_px: int = 21
    scene_icon_size_max_px: int = 31
    cell_box_width_min_px: int = 0
    cell_box_width_max_px: int = 0
    cell_box_height_min_px: int = 0
    cell_box_height_max_px: int = 0
    scene_max_overlap_fraction: float = 0.12
    scene_placement_max_attempts: int = 1
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = 22
    pool_manifest: str = "non_symmetry.txt"
    palette_size_min: int = 1
    palette_size_max: int = 1
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb
    cell_padding_px: int = 0
    cell_icon_padding_px: int = 0
    cell_corner_radius_px: int = 0
    cell_border_rgb: Tuple[int, int, int] = (218, 223, 233)
    cell_label_font_size_px: int = 22
    cell_label_color_rgb: Tuple[int, int, int] = (52, 60, 77)
    scene_content_side_padding_px: int = 0
    scene_content_bottom_padding_px: int = 0
    scene_content_top_offset_px: int = 0
    icon_noise_edit_types: Tuple[str, ...] = ICON_SHARED_DEFAULTS.icon_noise_edit_types
    icon_noise_edit_count_range: Tuple[int, int] = (0, 0)
    icon_noise_value_ranges: Dict[str, Dict[str, Tuple[float, float]]] = field(
        default_factory=lambda: deepcopy(ICON_SHARED_DEFAULTS.icon_noise_value_ranges)
    )


@dataclass(frozen=True)
class _WallpaperSpec:
    option_count: int
    option_labels: Tuple[str, ...]
    answer_label: str
    answer_index: int
    reference_wallpaper_group_id: str
    wallpaper_group_ids_by_label: Dict[str, str]
    option_count_probabilities: Dict[str, float]
    answer_label_probabilities: Dict[str, float]
    reference_wallpaper_group_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _ScenePayload:
    option_count: int
    option_labels: Tuple[str, ...]
    answer_label: str
    answer_index: int
    reference_wallpaper_group_id: str
    wallpaper_group_ids_by_label: Dict[str, str]
    icon_ids_by_label: Dict[str, str]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    nominal_icon_size_px: int
    panel_geometry: Dict[str, Any]
    scene_panels: Tuple[Dict[str, Any], ...]
    scene_elements: Tuple[Dict[str, Any], ...]
    scene_icon_instances: Tuple[Dict[str, Any], ...]
    reference_panel_bbox: Tuple[int, int, int, int]
    answer_panel_bbox: Tuple[int, int, int, int]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_scene_defaults("icons", "pattern")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _int_tuple_param(params: Mapping[str, Any], *, key: str, fallback: Sequence[int]) -> Tuple[int, ...]:
    raw = params.get(key, group_default(_GEN_DEFAULTS, key, list(fallback)))
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"{key} must be a sequence")
    values = tuple(int(value) for value in raw)
    if not values:
        raise ValueError(f"{key} must contain at least one value")
    return values


def _wallpaper_group_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("wallpaper_group_ids")
    if raw is None:
        raw = group_default(_GEN_DEFAULTS, "wallpaper_group_ids", list(_DEFAULTS.wallpaper_group_ids))
    return resolve_wallpaper_group_support(raw, fallback=_DEFAULTS.wallpaper_group_ids)


def _resolve_wallpaper_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _WallpaperSpec:
    option_count_support = tuple(
        int(value)
        for value in _int_tuple_param(params, key="option_count_choices", fallback=_DEFAULTS.option_count_choices)
    )
    if any(value != 6 for value in option_count_support):
        raise ValueError("reference wallpaper matching currently supports six candidate panels")
    group_support = _wallpaper_group_support(params)
    if len(group_support) < 6:
        raise ValueError("reference wallpaper matching requires at least six wallpaper groups")
    base_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{TASK_ID}:wallpaper_spec",
        )
    )

    explicit_option_count = params.get("option_count")
    if explicit_option_count is None:
        option_count = int(option_count_support[int(base_index % len(option_count_support))])
    else:
        option_count = int(explicit_option_count)
        if option_count not in option_count_support:
            raise ValueError("option_count is outside configured support")
    option_labels = OPTION_LABELS[: int(option_count)]

    explicit_answer_label = params.get("answer_label")
    if explicit_answer_label is None:
        answer_index = int((base_index // max(1, len(option_count_support))) % len(option_labels))
        answer_label = str(option_labels[int(answer_index)])
    else:
        answer_label = str(explicit_answer_label).strip().upper()
        if answer_label not in set(option_labels):
            raise ValueError("answer_label must be one of the active option panel labels")
        answer_index = int(option_labels.index(answer_label))

    explicit_reference_group = params.get("reference_wallpaper_group_id", params.get("wallpaper_group_id"))
    if explicit_reference_group is None:
        group_index = int((base_index // max(1, len(option_count_support) * len(option_labels))) % len(group_support))
        reference_wallpaper_group_id = str(group_support[int(group_index)])
    else:
        reference_wallpaper_group_id = str(explicit_reference_group).strip()
        if reference_wallpaper_group_id not in set(group_support):
            raise ValueError("reference_wallpaper_group_id is outside configured support")

    distractor_groups = [str(group_id) for group_id in group_support if str(group_id) != str(reference_wallpaper_group_id)]
    distractor_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:distractor_groups")
    distractor_rng.shuffle(distractor_groups)
    wallpaper_group_ids_by_label: Dict[str, str] = {}
    distractor_index = 0
    for label in option_labels:
        if str(label) == str(answer_label):
            wallpaper_group_ids_by_label[str(label)] = str(reference_wallpaper_group_id)
        else:
            wallpaper_group_ids_by_label[str(label)] = str(distractor_groups[int(distractor_index)])
            distractor_index += 1

    return _WallpaperSpec(
        option_count=int(option_count),
        option_labels=tuple(str(label) for label in option_labels),
        answer_label=str(answer_label),
        answer_index=int(answer_index),
        reference_wallpaper_group_id=str(reference_wallpaper_group_id),
        wallpaper_group_ids_by_label=dict(wallpaper_group_ids_by_label),
        option_count_probabilities=uniform_probability_map(
            option_count_support,
            selected=int(option_count) if explicit_option_count is not None else None,
        ),
        answer_label_probabilities=uniform_str_probability_map(
            option_labels,
            selected=str(answer_label) if explicit_answer_label is not None else None,
        ),
        reference_wallpaper_group_probabilities=uniform_str_probability_map(
            group_support,
            selected=str(reference_wallpaper_group_id) if explicit_reference_group is not None else None,
        ),
    )


def _resolve_wallpaper_render_params(*, params: Mapping[str, Any], instance_seed: int) -> Dict[str, Any]:
    safe_params = wallpaper_safe_canvas_params(params)
    render_params = resolve_icon_cell_render_params(
        params=safe_params,
        render_defaults=_RENDER_DEFAULTS,
        fallback_defaults=_DEFAULTS,
        instance_seed=int(instance_seed),
    )
    render_params["reference_panel_width_px"] = int(
        params.get(
            "reference_panel_width_px",
            group_default(_RENDER_DEFAULTS, "reference_panel_width_px", _DEFAULTS.reference_panel_width_px),
        )
    )
    render_params["option_panel_gap_px"] = int(
        params.get("option_panel_gap_px", group_default(_RENDER_DEFAULTS, "option_panel_gap_px", _DEFAULTS.option_panel_gap_px))
    )
    render_params["lattice_rows"] = int(params.get("lattice_rows", group_default(_RENDER_DEFAULTS, "lattice_rows", _DEFAULTS.lattice_rows)))
    render_params["lattice_cols"] = int(params.get("lattice_cols", group_default(_RENDER_DEFAULTS, "lattice_cols", _DEFAULTS.lattice_cols)))
    return render_params


def _panel_geometry(*, render_params: Mapping[str, Any], option_labels: Sequence[str]) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    width = int(render_params["canvas_width"])
    height = int(render_params["canvas_height"])
    margin = max(0, int(render_params["outer_margin_px"]))
    gap = max(0, int(render_params["option_panel_gap_px"]))
    reference_width = max(220, int(render_params["reference_panel_width_px"]))
    label_band_height = max(28, int(round(float(render_params["cell_label_font_size_px"]) * 1.45)))
    panel_padding = max(0, int(render_params["panel_padding_px"]))

    reference_bbox = (int(margin), int(margin), int(margin + reference_width), int(height - margin))
    options_bbox = (
        int(reference_bbox[2] + gap),
        int(margin),
        int(width - margin),
        int(height - margin),
    )
    if options_bbox[2] <= options_bbox[0]:
        raise ValueError("wallpaper reference-match option area collapsed")

    panel_slots = resolve_fixed_grid_cell_slots(
        options_bbox,
        rows=2,
        cols=3,
        cell_padding_px=max(0, int(gap // 2)),
    )[: len(option_labels)]

    panels: Dict[str, Dict[str, Any]] = {}
    all_panel_specs = [(REFERENCE_LABEL, reference_bbox), *list(zip(option_labels, panel_slots))]
    for label, panel_bbox in all_panel_specs:
        panel_x0, panel_y0, panel_x1, panel_y1 = [int(value) for value in panel_bbox]
        content_bbox = (
            int(panel_x0 + panel_padding),
            int(panel_y0 + label_band_height + max(4, panel_padding // 2)),
            int(panel_x1 - panel_padding),
            int(panel_y1 - panel_padding),
        )
        if content_bbox[2] <= content_bbox[0] or content_bbox[3] <= content_bbox[1]:
            raise ValueError("wallpaper reference-match content bbox collapsed")
        panels[str(label)] = {
            "label": str(label),
            "panel_bbox_xyxy": [int(value) for value in panel_bbox],
            "content_bbox_xyxy": [int(value) for value in content_bbox],
        }

    return (
        {
            "canvas_size": [int(width), int(height)],
            "reference_panel_label": REFERENCE_LABEL,
            "candidate_panel_grid": {"rows": 2, "cols": 3, "option_count": int(len(option_labels))},
            "motif_lattice": {"rows": int(render_params["lattice_rows"]), "cols": int(render_params["lattice_cols"]), "visible_grid": False},
            "panels": {str(label): dict(payload) for label, payload in panels.items()},
        },
        panels,
    )


def _draw_panel_label(draw: ImageDraw.ImageDraw, *, label: str, panel_bbox: Sequence[int], render_params: Mapping[str, Any]) -> None:
    label_font = load_font(int(render_params["cell_label_font_size_px"]), bold=True)
    draw_centered_traced_text(
        draw,
        text=str(label),
        center=(
            0.5 * float(float(panel_bbox[0]) + float(panel_bbox[2])),
            float(panel_bbox[1]) + max(18.0, float(render_params["cell_label_font_size_px"]) * 0.95),
        ),
        font=label_font,
        fill_rgb=tuple(int(v) for v in render_params["cell_label_color_rgb"]),
        stroke_rgb=tuple(int(v) for v in render_params["cell_label_stroke_rgb"]),
        stroke_width=2,
        role="icon_wallpaper_panel_label_text",
        required=False,
    )


def _render_wallpaper_scene(*, rng: Any, instance_seed: int, spec: _WallpaperSpec, pool_manifest: str, render_params: Mapping[str, Any]) -> Tuple[_ScenePayload, Image.Image]:
    panel_labels = (REFERENCE_LABEL, *spec.option_labels)
    icon_ids_by_label = select_distinct_icon_ids(rng, pool_manifest=str(pool_manifest), labels=panel_labels)
    tint_rgb, sampled_palette_rgb = sample_single_icon_tint(
        rng,
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
    nominal_icon_size_px = int(rng.randint(int(render_params["scene_icon_size_min_px"]), int(render_params["scene_icon_size_max_px"])))
    panel_geometry, panels = _panel_geometry(render_params=render_params, option_labels=spec.option_labels)
    image = make_icon_canvas_background(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        style=render_params.get("_icon_canvas_style_object"),
        fallback_rgb=tuple(int(v) for v in render_params["background_color_rgb"]),
    )
    draw = ImageDraw.Draw(image)
    scene_panels: List[Dict[str, Any]] = []
    scene_elements: List[Dict[str, Any]] = []
    scene_icon_instances: List[Dict[str, Any]] = []
    sprite_cache: Dict[Tuple[str, int, bool], Image.Image] = {}
    answer_panel_bbox: Tuple[int, int, int, int] | None = None
    reference_panel_bbox: Tuple[int, int, int, int] | None = None

    for label in panel_labels:
        panel_info = panels[str(label)]
        panel_bbox = tuple(int(value) for value in panel_info["panel_bbox_xyxy"])
        content_bbox = tuple(int(value) for value in panel_info["content_bbox_xyxy"])
        is_reference = str(label) == REFERENCE_LABEL
        group_id = str(spec.reference_wallpaper_group_id if is_reference else spec.wallpaper_group_ids_by_label[str(label)])
        is_answer = bool((not is_reference) and str(label) == str(spec.answer_label))
        if is_reference:
            reference_panel_bbox = tuple(int(value) for value in panel_bbox)
        if is_answer:
            answer_panel_bbox = tuple(int(value) for value in panel_bbox)
        draw_icon_panel_chrome(
            draw,
            bbox=panel_bbox,
            style=render_params.get("_icon_canvas_style_object"),
            fallback_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
            fallback_border_rgb=tuple(int(v) for v in render_params["panel_border_rgb"]),
            radius=int(render_params["panel_corner_radius_px"]),
            border_width=2,
        )
        _draw_panel_label(draw, label=str(label), panel_bbox=panel_bbox, render_params=render_params)
        elements, instances = draw_wallpaper_motifs(
            image,
            task_id=TASK_ID,
            instance_seed=int(instance_seed),
            panel_label=str(label),
            group_id=str(group_id),
            icon_id=str(icon_ids_by_label[str(label)]),
            tint_rgb=tuple(int(v) for v in tint_rgb),
            nominal_icon_size_px=int(nominal_icon_size_px),
            content_bbox=content_bbox,
            render_params=render_params,
            sprite_cache=sprite_cache,
            is_answer_panel=bool(is_answer),
        )
        scene_elements.extend(dict(element) for element in elements)
        scene_icon_instances.extend(dict(instance) for instance in instances)
        scene_panels.append(
            {
                "entity_kind": "wallpaper_panel",
                "label": str(label),
                "panel_role": "reference" if is_reference else "candidate",
                "panel_bbox_xyxy": [int(value) for value in panel_bbox],
                "content_bbox_xyxy": [int(value) for value in content_bbox],
                "icon_id": str(icon_ids_by_label[str(label)]),
                "wallpaper_group_id": str(group_id),
                "is_reference": bool(is_reference),
                "is_answer": bool(is_answer),
                "matches_reference_pattern": bool(is_reference or is_answer),
            }
        )

    if reference_panel_bbox is None or answer_panel_bbox is None:
        raise RuntimeError("wallpaper reference renderer did not produce required panel bboxes")
    return (
        _ScenePayload(
            option_count=int(spec.option_count),
            option_labels=tuple(str(label) for label in spec.option_labels),
            answer_label=str(spec.answer_label),
            answer_index=int(spec.answer_index),
            reference_wallpaper_group_id=str(spec.reference_wallpaper_group_id),
            wallpaper_group_ids_by_label=dict(spec.wallpaper_group_ids_by_label),
            icon_ids_by_label=dict(icon_ids_by_label),
            sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in sampled_palette_rgb),
            nominal_icon_size_px=int(nominal_icon_size_px),
            panel_geometry=dict(panel_geometry),
            scene_panels=tuple(scene_panels),
            scene_elements=tuple(scene_elements),
            scene_icon_instances=tuple(scene_icon_instances),
            reference_panel_bbox=tuple(int(value) for value in reference_panel_bbox),
            answer_panel_bbox=tuple(int(value) for value in answer_panel_bbox),
        ),
        image.convert("RGB"),
    )




@register_task
class IconsPatternWallpaperReferenceMatchTask:
    """Select the candidate wallpaper panel matching the reference pattern."""

    task_id = TASK_ID
    domain = "icons"
    scene_id = "pattern"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        scene_rng = spawn_rng(int(instance_seed), "scene")
        spec = _resolve_wallpaper_spec(instance_seed=int(instance_seed), params=params)
        render_params = _resolve_wallpaper_render_params(params=params, instance_seed=int(instance_seed))
        if int(render_params["lattice_rows"]) != LATTICE_ROWS or int(render_params["lattice_cols"]) != LATTICE_COLS:
            raise ValueError("wallpaper reference task requires a 4x4 invisible motif lattice")
        if int(render_params["scene_icon_size_min_px"]) > int(render_params["scene_icon_size_max_px"]):
            raise ValueError("scene_icon_size_min_px must be <= scene_icon_size_max_px")
        pool_manifest = str(params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest)))

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _attempt in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = _render_wallpaper_scene(
                    rng=scene_rng,
                    instance_seed=int(instance_seed),
                    spec=spec,
                    pool_manifest=str(pool_manifest),
                    render_params=render_params,
                )
                break
            except Exception as exc:  # pragma: no cover
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError(f"failed to generate {self.task_id} instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text",
                "annotation_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            scene_id=self.scene_id,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_annotation_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "annotation_hint": str(prompt_defaults["annotation_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        annotation_payload = keyed_bbox_map_annotation(
            {
                "reference_panel": scene_payload.reference_panel_bbox,
                "selected_panel": scene_payload.answer_panel_bbox,
            }
        )
        taxonomy = resolve_task_taxonomy(str(self.task_id))
        answer_gt = TypedValue(type="option_letter", value=str(scene_payload.answer_label))
        annotation_gt = TypedValue(type=str(annotation_payload["annotation_type"]), value=dict(annotation_payload["annotation_value"]))
        common_ids = {"domain": taxonomy.domain, "scene_id": taxonomy.scene_id, "task_id": str(self.task_id), "query_id": QUERY_ID}
        answer_panel = next(dict(panel) for panel in scene_payload.scene_panels if str(panel.get("label")) == str(scene_payload.answer_label))
        reference_panel = next(dict(panel) for panel in scene_payload.scene_panels if bool(panel.get("is_reference")))
        trace_payload = {
            "taxonomy": {
                "domain": taxonomy.domain,
                "scene_id": taxonomy.scene_id,
                "task_id": str(self.task_id),
                "source_domain": taxonomy.source_domain,
                "source_scene_id": taxonomy.source_scene_id,
                "query_id": QUERY_ID,
            },
            "scene_ir": {
                **common_ids,
                "scene_kind": "icons_wallpaper_panels_reference_match",
                "entities": [
                    *[dict(panel) for panel in scene_payload.scene_panels],
                    *[dict(element) for element in scene_payload.scene_elements],
                    *[dict(instance) for instance in scene_payload.scene_icon_instances],
                ],
                "relations": {
                    "target": "candidate_panel_matching_reference_wallpaper_pattern",
                    "reference_wallpaper_group_id": str(scene_payload.reference_wallpaper_group_id),
                    "answer_label": str(scene_payload.answer_label),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                **common_ids,
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    **common_ids,
                    "query_id_probabilities": {QUERY_ID: 1.0},
                    "option_count": int(scene_payload.option_count),
                    "option_count_probabilities": dict(spec.option_count_probabilities),
                    "option_labels": list(scene_payload.option_labels),
                    "answer_label": str(scene_payload.answer_label),
                    "answer_label_probabilities": dict(spec.answer_label_probabilities),
                    "reference_wallpaper_group_id": str(scene_payload.reference_wallpaper_group_id),
                    "reference_wallpaper_group_probabilities": dict(spec.reference_wallpaper_group_probabilities),
                    "wallpaper_group_ids_by_label": dict(scene_payload.wallpaper_group_ids_by_label),
                    "icon_ids_by_label": dict(scene_payload.icon_ids_by_label),
                    "lattice_rows": int(LATTICE_ROWS),
                    "lattice_cols": int(LATTICE_COLS),
                    "pool_manifest": str(pool_manifest),
                },
            },
            "render_spec": {
                **common_ids,
                "canvas_size": list(scene_payload.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": {
                    **icon_render_style_trace(render_params=render_params, sampled_palette_rgb=scene_payload.sampled_palette_rgb),
                    **wallpaper_chrome_policy_trace(),
                    "reference_panel_width_px": int(render_params["reference_panel_width_px"]),
                    "option_panel_gap_px": int(render_params["option_panel_gap_px"]),
                    "cell_label_font_size_px": int(render_params["cell_label_font_size_px"]),
                    "cell_label_color_rgb": [int(v) for v in render_params["cell_label_color_rgb"]],
                    "nominal_icon_size_px": int(scene_payload.nominal_icon_size_px),
                    "visible_internal_grid": False,
                },
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {
                    "reference_panel_bbox": list(scene_payload.reference_panel_bbox),
                    "selected_panel_bbox": list(scene_payload.answer_panel_bbox),
                    "reference_panel": dict(reference_panel),
                    "answer_panel": dict(answer_panel),
                    "answer_label": str(scene_payload.answer_label),
                },
            },
            "execution_trace": {
                **common_ids,
                "scene_variant": "reference_plus_six_wallpaper_option_panels",
                "question_format": "select_candidate_panel_matching_reference_wallpaper_pattern",
                "query_id_probabilities": {QUERY_ID: 1.0},
                "option_count": int(scene_payload.option_count),
                "option_labels": list(scene_payload.option_labels),
                "answer": str(scene_payload.answer_label),
                "answer_label": str(scene_payload.answer_label),
                "reference_wallpaper_group_id": str(scene_payload.reference_wallpaper_group_id),
                "wallpaper_group_ids_by_label": dict(scene_payload.wallpaper_group_ids_by_label),
                "icon_ids_by_label": dict(scene_payload.icon_ids_by_label),
                "lattice_rows": int(LATTICE_ROWS),
                "lattice_cols": int(LATTICE_COLS),
                "visible_internal_grid": False,
                "annotation_roles": ["reference_panel", "selected_panel"],
            },
            "witness_symbolic": {
                "answer_label": str(scene_payload.answer_label),
                "reference_panel_bbox": list(scene_payload.reference_panel_bbox),
                "selected_panel_bbox": list(scene_payload.answer_panel_bbox),
                "reference_wallpaper_group_id": str(scene_payload.reference_wallpaper_group_id),
                "wallpaper_group_ids_by_label": dict(scene_payload.wallpaper_group_ids_by_label),
                "icon_ids_by_label": dict(scene_payload.icon_ids_by_label),
            },
            "projected_annotation": dict(annotation_payload["projected_annotation"]),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=taxonomy.scene_id,
            query_id=QUERY_ID,
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsPatternWallpaperReferenceMatchTask", "TASK_ID"]
