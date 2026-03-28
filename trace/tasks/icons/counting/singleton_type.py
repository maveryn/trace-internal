"""Count icons whose type appears exactly once in the image."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
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
from ..shared.complexity import build_icons_counting_singleton_type_complexity
from ..shared.defaults import ICON_SHARED_DEFAULTS
from ..shared.icon_assets import render_icon_rgba, resolve_icon_pool
from ..shared.icon_noise import serialize_icon_noise_edits
from ..shared.icon_scene import (
    IconInstanceSpec,
    max_overlap_with_existing,
    random_paste_bbox,
    resolve_single_panel_layout,
    serialize_rendered_icon_instance,
    single_panel_geometry_to_trace,
    sort_bboxes_reading_order,
    draw_single_panel,
    RenderedIconInstance,
)
from ..shared.icon_style import icon_palette_meets_distance_constraints, sample_icon_palette, sample_icon_tints
from ..shared.icon_task_rendering import (
    icon_render_style_trace,
    resolve_icon_render_params,
    sample_icon_instance_noise,
)


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for singleton-type counting scenes."""

    object_count_min: int = 6
    object_count_max: int = 15
    target_count_min: int = 0
    target_count_max: int = 5
    repeated_type_count_min: int = 1
    repeated_type_count_max: int = 4
    repeated_type_multiplicity_min: int = 2
    repeated_type_multiplicity_max: int = 4
    canvas_width: int = ICON_SHARED_DEFAULTS.canvas_width
    canvas_height: int = ICON_SHARED_DEFAULTS.canvas_height
    outer_margin_px: int = ICON_SHARED_DEFAULTS.outer_margin_px
    panel_padding_px: int = ICON_SHARED_DEFAULTS.panel_padding_px
    panel_corner_radius_px: int = ICON_SHARED_DEFAULTS.panel_corner_radius_px
    scene_icon_size_min_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_min_px
    scene_icon_size_max_px: int = ICON_SHARED_DEFAULTS.scene_icon_size_max_px
    scene_max_overlap_fraction: float = ICON_SHARED_DEFAULTS.scene_max_overlap_fraction
    scene_placement_max_attempts: int = ICON_SHARED_DEFAULTS.scene_placement_max_attempts
    scene_size_shrink_rounds: int = ICON_SHARED_DEFAULTS.scene_size_shrink_rounds
    scene_size_shrink_factor: float = ICON_SHARED_DEFAULTS.scene_size_shrink_factor
    panel_title_font_size_px: int = ICON_SHARED_DEFAULTS.panel_title_font_size_px
    pool_manifest: str = "all_icons.txt"
    rotation_candidates_degrees: Tuple[int, ...] = (0, 90, 180, 270)
    palette_size_min: int = 8
    palette_size_max: int = 12
    color_channel_min: int = 24
    color_channel_max: int = 220
    min_color_distance: float = 40.0
    color_distance_space: str = "lab"
    background_color_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.background_color_rgb
    panel_fill_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_fill_rgb
    panel_border_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.panel_border_rgb
    header_text_rgb: Tuple[int, int, int] = ICON_SHARED_DEFAULTS.header_text_rgb


@dataclass(frozen=True)
class _CountSpec:
    """Resolved singleton/repeated type counts for one instance."""

    object_count: int
    target_count: int
    repeated_type_count: int
    repeated_type_multiplicities: Tuple[int, ...]
    distinct_type_count: int
    object_count_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _ScenePayload:
    """Trace-ready payload for one singleton-type counting instance."""

    object_count: int
    target_count: int
    repeated_type_count: int
    repeated_type_multiplicities: Tuple[int, ...]
    distinct_type_count: int
    singleton_icon_ids: Tuple[str, ...]
    repeated_icon_ids: Tuple[str, ...]
    scene_icon_ids: Tuple[str, ...]
    scene_rotations_degrees: Tuple[int, ...]
    singleton_indices: Tuple[int, ...]
    singleton_bboxes: Tuple[Tuple[int, int, int, int], ...]
    type_frequencies: Dict[str, int]
    sampled_palette_rgb: Tuple[Tuple[int, int, int], ...]
    panel_geometry: Dict[str, Any]
    scene_instances: Tuple[Dict[str, Any], ...]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("icons", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id="task_icons_counting_singleton_type",
)


def _rotation_candidates() -> Tuple[int, ...]:
    """Return the supported scene rotations for singleton-type counting."""

    return tuple(int(value) for value in _DEFAULTS.rotation_candidates_degrees)


def _bounded_compositions(total: int, parts: int, *, min_part: int, max_part: int) -> List[Tuple[int, ...]]:
    """Enumerate ordered integer compositions under inclusive part bounds."""

    if int(parts) <= 0:
        return [()] if int(total) == 0 else []
    if int(parts) == 1:
        if int(min_part) <= int(total) <= int(max_part):
            return [(int(total),)]
        return []
    compositions: List[Tuple[int, ...]] = []
    remaining_parts = int(parts) - 1
    for head in range(int(min_part), int(max_part) + 1):
        min_rest = int(remaining_parts) * int(min_part)
        max_rest = int(remaining_parts) * int(max_part)
        rest_total = int(total) - int(head)
        if rest_total < min_rest or rest_total > max_rest:
            continue
        for tail in _bounded_compositions(
            int(rest_total),
            int(remaining_parts),
            min_part=int(min_part),
            max_part=int(max_part),
        ):
            compositions.append((int(head), *tuple(int(value) for value in tail)))
    return compositions


def _resolve_count_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _CountSpec:
    """Resolve balanced singleton and repeated-type counts for one instance."""

    object_count_min = int(params.get("object_count_min", group_default(_GEN_DEFAULTS, "object_count_min", _DEFAULTS.object_count_min)))
    object_count_max = int(params.get("object_count_max", group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max)))
    target_count_min = int(params.get("target_count_min", group_default(_GEN_DEFAULTS, "target_count_min", _DEFAULTS.target_count_min)))
    target_count_max = int(params.get("target_count_max", group_default(_GEN_DEFAULTS, "target_count_max", _DEFAULTS.target_count_max)))
    repeated_type_count_min = int(
        params.get(
            "repeated_type_count_min",
            group_default(_GEN_DEFAULTS, "repeated_type_count_min", _DEFAULTS.repeated_type_count_min),
        )
    )
    repeated_type_count_max = int(
        params.get(
            "repeated_type_count_max",
            group_default(_GEN_DEFAULTS, "repeated_type_count_max", _DEFAULTS.repeated_type_count_max),
        )
    )
    repeated_type_multiplicity_min = int(
        params.get(
            "repeated_type_multiplicity_min",
            group_default(
                _GEN_DEFAULTS,
                "repeated_type_multiplicity_min",
                _DEFAULTS.repeated_type_multiplicity_min,
            ),
        )
    )
    repeated_type_multiplicity_max = int(
        params.get(
            "repeated_type_multiplicity_max",
            group_default(
                _GEN_DEFAULTS,
                "repeated_type_multiplicity_max",
                _DEFAULTS.repeated_type_multiplicity_max,
            ),
        )
    )
    if object_count_min <= 0 or object_count_max < object_count_min:
        raise ValueError("object_count range is invalid")
    if target_count_min < 0 or target_count_max < target_count_min:
        raise ValueError("target_count range is invalid")
    if repeated_type_count_min <= 0 or repeated_type_count_max < repeated_type_count_min:
        raise ValueError("repeated_type_count range is invalid")
    if repeated_type_multiplicity_min < 2 or repeated_type_multiplicity_max < repeated_type_multiplicity_min:
        raise ValueError("repeated_type_multiplicity range is invalid")

    answer_support = tuple(range(int(target_count_min), int(target_count_max) + 1))
    if not answer_support:
        raise ValueError("singleton target support is empty")
    selection_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace="task_icons_counting_singleton_type:count_spec",
        )
    )
    explicit_target = params.get("target_count")
    if explicit_target is not None:
        target_count = int(explicit_target)
    else:
        target_count = int(answer_support[int(selection_index % len(answer_support))])
    if target_count not in answer_support:
        raise ValueError("target_count is outside configured support")

    object_support = tuple(
        value
        for value in range(
            max(int(object_count_min), int(target_count) + int(repeated_type_multiplicity_min)),
            int(object_count_max) + 1,
        )
    )
    if not object_support:
        raise ValueError("no feasible object_count values exist for singleton-type counting")
    explicit_object_count = params.get("object_count")
    if explicit_object_count is not None:
        object_count = int(explicit_object_count)
    else:
        object_offset = int(selection_index // len(answer_support))
        object_count = int(object_support[int(object_offset % len(object_support))])
    if object_count not in object_support:
        raise ValueError("object_count is outside configured singleton-type support")

    repeated_icon_count = int(object_count) - int(target_count)
    if repeated_icon_count < int(repeated_type_multiplicity_min):
        raise ValueError("repeated icon count is too small to form one repeated type")

    min_group_count = max(
        int(repeated_type_count_min),
        (int(repeated_icon_count) + int(repeated_type_multiplicity_max) - 1) // int(repeated_type_multiplicity_max),
    )
    max_group_count = min(
        int(repeated_type_count_max),
        int(repeated_icon_count) // int(repeated_type_multiplicity_min),
    )
    if min_group_count > max_group_count:
        raise ValueError("no feasible repeated_type_count values exist for singleton-type counting")
    group_support = tuple(range(int(min_group_count), int(max_group_count) + 1))
    partition_index = int(selection_index // max(1, len(answer_support) * len(object_support)))
    repeated_type_count = int(group_support[int(partition_index % len(group_support))])
    multiplicity_support = _bounded_compositions(
        int(repeated_icon_count),
        int(repeated_type_count),
        min_part=int(repeated_type_multiplicity_min),
        max_part=int(repeated_type_multiplicity_max),
    )
    if not multiplicity_support:
        raise ValueError("no feasible repeated multiplicities exist for singleton-type counting")
    repeated_type_multiplicities = tuple(
        int(value)
        for value in multiplicity_support[int(partition_index % len(multiplicity_support))]
    )

    return _CountSpec(
        object_count=int(object_count),
        target_count=int(target_count),
        repeated_type_count=int(repeated_type_count),
        repeated_type_multiplicities=tuple(repeated_type_multiplicities),
        distinct_type_count=int(target_count) + int(repeated_type_count),
        object_count_probabilities=dict(
            uniform_probability_map(
                object_support,
                selected=int(object_count) if explicit_object_count is not None else None,
            )
        ),
        target_count_probabilities=dict(
            uniform_probability_map(
                answer_support,
                selected=int(target_count) if explicit_target is not None else None,
            )
        ),
    )


def _sample_scene(
    rng,
    *,
    instance_seed: int,
    count_spec: _CountSpec,
    pool_manifest: str,
    render_params: Mapping[str, Any],
) -> Tuple[_ScenePayload, Image.Image]:
    """Sample and render one single-panel singleton-type counting scene."""

    pool = list(resolve_icon_pool(str(pool_manifest)))
    if len(pool) < int(count_spec.distinct_type_count):
        raise ValueError("icon pool is too small for singleton-type counting scene")

    sampled_icon_ids = [str(icon_id) for icon_id in rng.sample(pool, int(count_spec.distinct_type_count))]
    singleton_icon_ids = [str(icon_id) for icon_id in sampled_icon_ids[: int(count_spec.target_count)]]
    repeated_icon_ids = [str(icon_id) for icon_id in sampled_icon_ids[int(count_spec.target_count) :]]
    scene_icon_ids = list(singleton_icon_ids)
    type_frequencies: Dict[str, int] = {}
    for icon_id in singleton_icon_ids:
        type_frequencies[str(icon_id)] = 1
    for icon_id, multiplicity in zip(repeated_icon_ids, count_spec.repeated_type_multiplicities):
        type_frequencies[str(icon_id)] = int(multiplicity)
        scene_icon_ids.extend([str(icon_id)] * int(multiplicity))
    if len(scene_icon_ids) != int(count_spec.object_count):
        raise ValueError("singleton-type scene did not realize the requested object count")
    rng.shuffle(scene_icon_ids)

    palette_size = int(rng.randint(int(render_params["palette_size_min"]), int(render_params["palette_size_max"])))
    palette = sample_icon_palette(
        rng,
        palette_size=int(palette_size),
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
    if not icon_palette_meets_distance_constraints(
        palette=palette,
        anchor_colors=(
            tuple(int(v) for v in render_params["background_color_rgb"]),
            tuple(int(v) for v in render_params["panel_fill_rgb"]),
            tuple(int(v) for v in render_params["panel_border_rgb"]),
            tuple(int(v) for v in render_params["header_text_rgb"]),
        ),
        min_color_distance=float(render_params["min_color_distance"]),
        distance_space=str(render_params["color_distance_space"]),
    ):
        raise ValueError("sampled icon palette did not satisfy strict distance constraints")
    sampled_tints = list(sample_icon_tints(rng, palette=palette, count=int(count_spec.object_count)))
    rotation_candidates = _rotation_candidates()

    layout = resolve_single_panel_layout(
        canvas_width=int(render_params["canvas_width"]),
        canvas_height=int(render_params["canvas_height"]),
        outer_margin_px=int(render_params["outer_margin_px"]),
        panel_padding_px=int(render_params["panel_padding_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
    )
    image = Image.new("RGBA", (int(layout.canvas_width), int(layout.canvas_height)))
    draw_single_panel(
        image=image,
        layout=layout,
        background_rgb=tuple(int(v) for v in render_params["background_color_rgb"]),
        panel_fill_rgb=tuple(int(v) for v in render_params["panel_fill_rgb"]),
        panel_border_rgb=tuple(int(v) for v in render_params["panel_border_rgb"]),
        title_color_rgb=tuple(int(v) for v in render_params["header_text_rgb"]),
        corner_radius_px=int(render_params["panel_corner_radius_px"]),
        title_font_size_px=int(render_params["panel_title_font_size_px"]),
        scene_title="Scene",
    )
    scene_content_bbox = tuple(int(value) for value in layout.scene_content_xyxy)

    min_size = max(16, int(render_params["scene_icon_size_min_px"]))
    max_size = max(min_size, int(render_params["scene_icon_size_max_px"]))
    max_overlap_fraction = max(0.0, min(1.0, float(render_params["scene_max_overlap_fraction"])))
    placement_attempts = max(1, int(render_params["scene_placement_max_attempts"]))
    shrink_rounds = max(0, int(render_params["scene_size_shrink_rounds"]))
    shrink_factor = max(0.1, min(1.0, float(render_params["scene_size_shrink_factor"])))

    placed_bboxes: List[Tuple[int, int, int, int]] = []
    scene_instances: List[Dict[str, Any]] = []
    singleton_indices: List[int] = []
    singleton_bboxes: List[Tuple[int, int, int, int]] = []
    scene_rotations_degrees: List[int] = []

    for index, icon_id in enumerate(scene_icon_ids):
        tint_rgb = tuple(int(channel) for channel in sampled_tints.pop(0))
        rotation_degrees = int(rng.choice(rotation_candidates))
        noise_edits, noise_seed = sample_icon_instance_noise(
            instance_seed=int(instance_seed),
            namespace=f"{IconsCountingSingletonTypeTask.task_id}:scene_icon_{int(index)}",
            render_params=render_params,
        )
        sprite = None
        paste_bbox = None
        nominal_size = None
        content_w = max(1, int(scene_content_bbox[2] - scene_content_bbox[0]))
        content_h = max(1, int(scene_content_bbox[3] - scene_content_bbox[1]))
        current_max_size = min(int(max_size), int(content_w), int(content_h))
        for shrink_round in range(int(shrink_rounds) + 1):
            round_max_size = max(int(min_size), int(round(float(current_max_size) * (float(shrink_factor) ** int(shrink_round)))))
            for _ in range(int(placement_attempts)):
                sampled_size = int(rng.randint(int(min_size), int(round_max_size)))
                candidate_sprite = render_icon_rgba(
                    icon_id=str(icon_id),
                    size_px=int(sampled_size),
                    tint_rgb=tuple(int(channel) for channel in tint_rgb),
                    rotation_degrees=int(rotation_degrees),
                    mirror_x=False,
                    noise_edits=tuple(noise_edits),
                    noise_seed=int(noise_seed),
                )
                try:
                    candidate_bbox = random_paste_bbox(
                        sprite_size=candidate_sprite.size,
                        content_bbox=scene_content_bbox,
                        rng=rng,
                    )
                except ValueError:
                    continue
                if float(max_overlap_with_existing(candidate_bbox, placed_bboxes)) > float(max_overlap_fraction):
                    continue
                sprite = candidate_sprite
                paste_bbox = tuple(int(value) for value in candidate_bbox)
                nominal_size = int(sampled_size)
                break
            if sprite is not None and paste_bbox is not None and nominal_size is not None:
                break
        if sprite is None or paste_bbox is None or nominal_size is None:
            raise ValueError("failed to place singleton-type icon within scene content under overlap constraints")

        image.alpha_composite(sprite, (int(paste_bbox[0]), int(paste_bbox[1])))
        placed_bboxes.append(tuple(int(value) for value in paste_bbox))
        is_singleton_type = int(type_frequencies[str(icon_id)]) == 1
        if bool(is_singleton_type):
            singleton_indices.append(int(index))
            singleton_bboxes.append(tuple(int(value) for value in paste_bbox))
        scene_rotations_degrees.append(int(rotation_degrees) % 360)
        rendered_instance = RenderedIconInstance(
            instance_id=f"scene_icon_{int(index)}",
            icon_id=str(icon_id),
            panel="scene",
            bbox_xyxy=tuple(int(value) for value in paste_bbox),
            nominal_size_px=int(nominal_size),
            rotation_degrees=int(rotation_degrees) % 360,
            mirror_x=False,
            tint_rgb=tuple(int(value) for value in tint_rgb),
            noise_edits=serialize_icon_noise_edits(tuple(noise_edits)),
            noise_seed=int(noise_seed),
        )
        scene_instances.append(
            serialize_rendered_icon_instance(
                rendered_instance,
                entity_kind="scene_icon",
                extra_fields={
                    "index": int(index),
                    "type_frequency": int(type_frequencies[str(icon_id)]),
                    "is_singleton_type": bool(is_singleton_type),
                },
            )
        )

    return (
        _ScenePayload(
            object_count=int(count_spec.object_count),
            target_count=int(count_spec.target_count),
            repeated_type_count=int(count_spec.repeated_type_count),
            repeated_type_multiplicities=tuple(int(value) for value in count_spec.repeated_type_multiplicities),
            distinct_type_count=int(count_spec.distinct_type_count),
            singleton_icon_ids=tuple(str(icon_id) for icon_id in singleton_icon_ids),
            repeated_icon_ids=tuple(str(icon_id) for icon_id in repeated_icon_ids),
            scene_icon_ids=tuple(str(icon_id) for icon_id in scene_icon_ids),
            scene_rotations_degrees=tuple(int(value) for value in scene_rotations_degrees),
            singleton_indices=tuple(int(value) for value in singleton_indices),
            singleton_bboxes=tuple(tuple(int(value) for value in bbox) for bbox in singleton_bboxes),
            type_frequencies={str(key): int(value) for key, value in type_frequencies.items()},
            sampled_palette_rgb=tuple(tuple(int(channel) for channel in color) for color in palette),
            panel_geometry=single_panel_geometry_to_trace(layout),
            scene_instances=tuple(dict(entity) for entity in scene_instances),
        ),
        image.convert("RGB"),
    )


@register_task
class IconsCountingSingletonTypeTask:
    """Count icons whose type appears exactly once in the image."""

    task_id = "task_icons_counting_singleton_type"
    domain = "icons"
    task_group = "counting"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one deterministic singleton-type counting instance."""

        count_spec = _resolve_count_spec(instance_seed=int(instance_seed), params=params)
        render_params = resolve_icon_render_params(
            params=params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
        )
        pool_manifest = str(
            params.get("pool_manifest", group_default(_GEN_DEFAULTS, "pool_manifest", _DEFAULTS.pool_manifest))
        )
        scene_rng = spawn_rng(int(instance_seed), "scene")

        scene_payload = None
        image = None
        last_error: Exception | None = None
        for _ in range(max(1, int(max_attempts))):
            try:
                scene_payload, image = _sample_scene(
                    scene_rng,
                    instance_seed=int(instance_seed),
                    count_spec=count_spec,
                    pool_manifest=str(pool_manifest),
                    render_params=render_params,
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through retry loop
                last_error = exc
                continue
        if scene_payload is None or image is None:
            raise RuntimeError("failed to generate task_icons_counting_singleton_type instance") from last_error

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "question_text",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "question_text": str(prompt_defaults["question_text"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_defaults["json_example"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only"]),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_bboxes = sort_bboxes_reading_order(scene_payload.singleton_bboxes)
        answer_gt = TypedValue(type="integer", value=int(scene_payload.target_count))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))
        task_variant = "singleton_type_count"
        trace_payload = {
            "scene_ir": {
                "scene_kind": "icons_singleton_type_counting",
                "entities": [dict(entity) for entity in scene_payload.scene_instances],
                "relations": {
                    "counting_rule": "singleton_icon_type_frequency",
                    "singleton_icon_ids": list(scene_payload.singleton_icon_ids),
                    "repeated_icon_ids": list(scene_payload.repeated_icon_ids),
                    "type_frequencies": dict(scene_payload.type_frequencies),
                    "singleton_indices": list(scene_payload.singleton_indices),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(scene_payload.panel_geometry),
                },
            },
            "query_spec": {
                "task_variant": str(task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "object_count": int(scene_payload.object_count),
                    "target_count": int(scene_payload.target_count),
                    "repeated_type_count": int(scene_payload.repeated_type_count),
                    "repeated_type_multiplicities": list(scene_payload.repeated_type_multiplicities),
                    "distinct_type_count": int(scene_payload.distinct_type_count),
                    "object_count_probabilities": dict(count_spec.object_count_probabilities),
                    "target_count_probabilities": dict(count_spec.target_count_probabilities),
                    "pool_manifest": str(pool_manifest),
                    "rotation_candidates_degrees": list(_rotation_candidates()),
                },
            },
            "render_spec": {
                "canvas_size": list(scene_payload.panel_geometry["canvas_size"]),
                "coord_space": "pixel",
                "panel_geometry": dict(scene_payload.panel_geometry),
                "style": icon_render_style_trace(
                    render_params=render_params,
                    sampled_palette_rgb=scene_payload.sampled_palette_rgb,
                ),
            },
            "render_map": {
                "image_id": "img0",
                "anchors": {},
            },
            "execution_trace": {
                "scene_variant": "single_panel_scene",
                "task_variant": str(task_variant),
                "question_format": "count_singleton_type_icons",
                "object_count": int(scene_payload.object_count),
                "target_count": int(scene_payload.target_count),
                "repeated_type_count": int(scene_payload.repeated_type_count),
                "repeated_type_multiplicities": list(scene_payload.repeated_type_multiplicities),
                "distinct_type_count": int(scene_payload.distinct_type_count),
                "scene_icon_ids": list(scene_payload.scene_icon_ids),
                "scene_rotations_degrees": list(scene_payload.scene_rotations_degrees),
                "type_frequencies": dict(scene_payload.type_frequencies),
                "singleton_indices": list(scene_payload.singleton_indices),
            },
            "witness_symbolic": {
                "singleton_icon_ids": list(scene_payload.singleton_icon_ids),
                "type_frequencies": dict(scene_payload.type_frequencies),
                "singleton_indices": list(scene_payload.singleton_indices),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
            },
        }
        complexity = build_icons_counting_singleton_type_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=self.task_id,
            object_count=int(scene_payload.object_count),
            target_count=int(scene_payload.target_count),
            repeated_type_count=int(scene_payload.repeated_type_count),
            distinct_type_count=int(scene_payload.distinct_type_count),
            object_count_min=int(
                params.get("object_count_min", group_default(_GEN_DEFAULTS, "object_count_min", _DEFAULTS.object_count_min))
            ),
            object_count_max=int(
                params.get("object_count_max", group_default(_GEN_DEFAULTS, "object_count_max", _DEFAULTS.object_count_max))
            ),
            scene_instances=scene_payload.scene_instances,
            render_params=render_params,
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            task_variant=str(task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["IconsCountingSingletonTypeTask"]
