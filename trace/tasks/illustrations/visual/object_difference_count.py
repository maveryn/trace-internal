"""Shared illustration spot-the-difference count task."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from ...shared.font_assets import font_asset_version, get_font_family_record, sample_font_family
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.mixed_object_scene import ObjectPlacementSpec
from ..shared.object_library import STYLE_IDS, aspect_ratio_for_object, choose_object_colors
from ..shared.visual_task_common import (
    MixedVisualScene,
    bbox_list,
    draw_panel_label,
    normalized_variant_weights,
    render_mixed_visual_scene,
    rerender_mixed_visual_scene,
    sample_count_axis,
    sample_object_types,
    sort_bboxes_by_position,
)


TASK_ID = "task_illustrations__difference_pair__object_difference_count"
SCENE_ID = "difference_pair"
SUPPORTED_VARIANTS: Tuple[str, ...] = (
    "added_object_count",
    "removed_object_count",
    "changed_color_object_count",
    "moved_object_count",
)


@dataclass(frozen=True)
class _Defaults:
    object_count_min: int = 8
    object_count_max: int = 13
    target_count_min: int = 1
    target_count_max: int = 5
    canvas_width: int = 640
    canvas_height: int = 420
    outer_margin_px: int = 28
    object_size_min_px: int = 48
    object_size_max_px: int = 82
    object_min_gap_px: int = 7
    max_overlap_fraction: float = 0.01
    placement_max_attempts: int = 260
    moved_min_center_distance_px: int = 72
    render_scale: int = 2


@dataclass(frozen=True)
class _SampleSpec:
    variant: str
    target_count: int
    object_count: int
    variant_probabilities: Dict[str, float]
    target_count_probabilities: Dict[str, float]
    object_count_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "visual")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _variant_support(params: Mapping[str, Any]) -> Tuple[str, ...]:
    raw = params.get("query_id_support", group_default(_GEN_DEFAULTS, "query_id_support", SUPPORTED_VARIANTS))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("query_id_support must be a sequence")
    support = tuple(str(value) for value in raw if str(value) in set(SUPPORTED_VARIANTS))
    if not support:
        raise ValueError("query_id_support resolved no supported variants")
    return tuple(dict.fromkeys(support))


def _resolve_variant(params: Mapping[str, Any], *, instance_seed: int) -> Tuple[str, Dict[str, float]]:
    support = _variant_support(params)
    explicit = params.get("query_id")
    if explicit is not None:
        variant = str(explicit)
        if variant not in set(support):
            raise ValueError(f"query_id/query_id must be one of {support}")
        return str(variant), {str(variant): 1.0}
    weights = normalized_variant_weights(group_default(_GEN_DEFAULTS, "query_id_weights", {variant: 1.0 for variant in support}), support)
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:query_id")
    positive = tuple(value for value in support if float(weights.get(str(value), 0.0)) > 0.0)
    return str(positive[int(index) % len(positive)]), dict(weights)


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    variant, variant_probabilities = _resolve_variant(params, instance_seed=int(instance_seed))
    target_count, target_probs = sample_count_axis(
        params=params,
        defaults=_GEN_DEFAULTS,
        task_id=TASK_ID,
        namespace="target_count",
        low_key="target_count_min",
        high_key="target_count_max",
        explicit_key="target_count",
        fallback_low=_DEFAULTS.target_count_min,
        fallback_high=_DEFAULTS.target_count_max,
        instance_seed=int(instance_seed),
        sampling_divisor=max(1, len(_variant_support(params))),
    )
    object_count, object_probs = sample_count_axis(
        params=params,
        defaults=_GEN_DEFAULTS,
        task_id=TASK_ID,
        namespace="object_count",
        low_key="object_count_min",
        high_key="object_count_max",
        explicit_key="object_count",
        fallback_low=_DEFAULTS.object_count_min,
        fallback_high=_DEFAULTS.object_count_max,
        instance_seed=int(instance_seed),
        sampling_divisor=max(1, len(_variant_support(params)) * (_DEFAULTS.target_count_max - _DEFAULTS.target_count_min + 1)),
    )
    return _SampleSpec(
        variant=str(variant),
        target_count=int(target_count),
        object_count=int(object_count),
        variant_probabilities=dict(variant_probabilities),
        target_count_probabilities=dict(target_probs),
        object_count_probabilities=dict(object_probs),
    )


def _render_fallback() -> Dict[str, Any]:
    return {
        "canvas_width": _DEFAULTS.canvas_width,
        "canvas_height": _DEFAULTS.canvas_height,
        "outer_margin_px": _DEFAULTS.outer_margin_px,
        "object_size_min_px": _DEFAULTS.object_size_min_px,
        "object_size_max_px": _DEFAULTS.object_size_max_px,
        "object_min_gap_px": _DEFAULTS.object_min_gap_px,
        "max_overlap_fraction": _DEFAULTS.max_overlap_fraction,
        "placement_max_attempts": _DEFAULTS.placement_max_attempts,
        "render_scale": _DEFAULTS.render_scale,
    }


def _bbox_area(box: Sequence[float]) -> float:
    return max(0.0, float(box[2]) - float(box[0])) * max(0.0, float(box[3]) - float(box[1]))


def _overlap_area(a: Sequence[float], b: Sequence[float]) -> float:
    x0 = max(float(a[0]), float(b[0]))
    y0 = max(float(a[1]), float(b[1]))
    x1 = min(float(a[2]), float(b[2]))
    y1 = min(float(a[3]), float(b[3]))
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _bbox_center(box: Sequence[float]) -> Tuple[float, float]:
    return ((float(box[0]) + float(box[2])) * 0.5, (float(box[1]) + float(box[3])) * 0.5)


def _center_distance(a: Sequence[float], b: Sequence[float]) -> float:
    ax, ay = _bbox_center(a)
    bx, by = _bbox_center(b)
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def _fits(existing: Sequence[Sequence[float]], candidate: Sequence[float], *, min_gap: float = 10.0) -> bool:
    expanded = (float(candidate[0]) - min_gap, float(candidate[1]) - min_gap, float(candidate[2]) + min_gap, float(candidate[3]) + min_gap)
    for other in existing:
        other_expanded = (float(other[0]) - min_gap, float(other[1]) - min_gap, float(other[2]) + min_gap, float(other[3]) + min_gap)
        if _overlap_area(expanded, other_expanded) <= 0.0:
            continue
        denom = max(1.0, min(_bbox_area(candidate), _bbox_area(other)))
        if _overlap_area(expanded, other_expanded) / denom > 0.02:
            return False
    return True


def _new_bbox_for_type(
    *,
    rng,
    object_type: str,
    content_bbox: Sequence[float],
    existing: Sequence[Sequence[float]],
    height_min: int,
    height_max: int,
    same_size_as: Sequence[float] | None = None,
    min_center_distance_from: Sequence[float] | None = None,
    min_center_distance_px: float = 0.0,
) -> Tuple[float, float, float, float]:
    x0, y0, x1, y1 = [float(v) for v in content_bbox]
    aspect = max(0.35, float(aspect_ratio_for_object(str(object_type))))
    for _attempt in range(400):
        if same_size_as is None:
            h = float(rng.randint(int(height_min), int(height_max)))
            w = max(36.0, h * aspect)
        else:
            w = float(same_size_as[2]) - float(same_size_as[0])
            h = float(same_size_as[3]) - float(same_size_as[1])
        if w >= x1 - x0 or h >= y1 - y0:
            continue
        px = float(rng.uniform(x0, x1 - w))
        py = float(rng.uniform(y0, y1 - h))
        candidate = (px, py, px + w, py + h)
        if min_center_distance_from is not None and _center_distance(candidate, min_center_distance_from) < float(min_center_distance_px):
            continue
        if _fits(existing, candidate):
            return tuple(float(v) for v in candidate)
    raise ValueError("could not place changed object without overlap")


def _changed_colors(rng, placement: ObjectPlacementSpec) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    for _ in range(24):
        primary, accent = choose_object_colors(rng, str(placement.object_type))
        distance = sum(abs(int(primary[i]) - int(placement.primary_color_rgb[i])) for i in range(3))
        if distance >= 80:
            return primary, accent
    return tuple(255 - int(v) for v in placement.primary_color_rgb), tuple(255 - int(v) for v in placement.accent_color_rgb)


def _modify_scene(
    *,
    base: MixedVisualScene,
    sample: _SampleSpec,
    rng,
    instance_seed: int,
    attempt_index: int,
    params: Mapping[str, Any],
) -> Tuple[MixedVisualScene, Tuple[str, ...]]:
    placements = list(base.scene.placements)
    target_ids = tuple(str(p.object_id) for p in rng.sample(placements, int(sample.target_count)))
    target_set = set(target_ids)
    if sample.variant == "removed_object_count":
        modified = [placement for placement in placements if str(placement.object_id) not in target_set]
        return (
            rerender_mixed_visual_scene(
                base_scene=base.scene,
                placements=modified,
                task_id=TASK_ID,
                instance_seed=int(instance_seed),
                attempt_index=int(attempt_index),
                render_defaults=_RENDER_DEFAULTS,
                params=params,
            ),
            target_ids,
        )
    if sample.variant == "changed_color_object_count":
        changed: list[ObjectPlacementSpec] = []
        for placement in placements:
            if str(placement.object_id) in target_set:
                primary, accent = _changed_colors(rng, placement)
                changed.append(replace(placement, primary_color_rgb=primary, accent_color_rgb=accent))
            else:
                changed.append(placement)
        return (
            rerender_mixed_visual_scene(
                base_scene=base.scene,
                placements=changed,
                task_id=TASK_ID,
                instance_seed=int(instance_seed),
                attempt_index=int(attempt_index),
                render_defaults=_RENDER_DEFAULTS,
                params=params,
            ),
            target_ids,
        )
    if sample.variant == "moved_object_count":
        moved: list[ObjectPlacementSpec] = []
        existing = [p.bbox_xyxy for p in placements if str(p.object_id) not in target_set]
        moved_min_distance = float(
            params.get(
                "moved_min_center_distance_px",
                group_default(_GEN_DEFAULTS, "moved_min_center_distance_px", _DEFAULTS.moved_min_center_distance_px),
            )
        )
        for placement in placements:
            if str(placement.object_id) not in target_set:
                moved.append(placement)
                continue
            new_bbox = _new_bbox_for_type(
                rng=rng,
                object_type=str(placement.object_type),
                content_bbox=base.scene.content_bbox,
                existing=existing,
                height_min=_DEFAULTS.object_size_min_px,
                height_max=_DEFAULTS.object_size_max_px,
                same_size_as=placement.bbox_xyxy,
                min_center_distance_from=placement.bbox_xyxy,
                min_center_distance_px=moved_min_distance,
            )
            existing.append(new_bbox)
            moved.append(replace(placement, bbox_xyxy=new_bbox))
        return (
            rerender_mixed_visual_scene(
                base_scene=base.scene,
                placements=moved,
                task_id=TASK_ID,
                instance_seed=int(instance_seed),
                attempt_index=int(attempt_index),
                render_defaults=_RENDER_DEFAULTS,
                params=params,
            ),
            target_ids,
        )
    if sample.variant != "added_object_count":
        raise ValueError(f"unsupported variant: {sample.variant}")
    existing = [placement.bbox_xyxy for placement in placements]
    added: list[ObjectPlacementSpec] = []
    object_types = sample_object_types(rng=rng, count=int(sample.target_count))
    for index, object_type in enumerate(object_types):
        bbox = _new_bbox_for_type(
            rng=rng,
            object_type=str(object_type),
            content_bbox=base.scene.content_bbox,
            existing=existing,
            height_min=_DEFAULTS.object_size_min_px,
            height_max=_DEFAULTS.object_size_max_px,
        )
        existing.append(bbox)
        primary, accent = choose_object_colors(rng, str(object_type))
        added.append(
            ObjectPlacementSpec(
                object_id=f"added_{index:02d}",
                object_type=str(object_type),
                bbox_xyxy=bbox,
                primary_color_rgb=primary,
                accent_color_rgb=accent,
                style_id=str(rng.choice(STYLE_IDS)),
            )
        )
    return (
        rerender_mixed_visual_scene(
            base_scene=base.scene,
            placements=tuple(placements) + tuple(added),
            task_id=TASK_ID,
            instance_seed=int(instance_seed),
            attempt_index=int(attempt_index),
            render_defaults=_RENDER_DEFAULTS,
            params=params,
        ),
        tuple(str(placement.object_id) for placement in added),
    )


def _sample_panel_label_font_trace(*, instance_seed: int, params: Mapping[str, Any]) -> Dict[str, Any]:
    font_family = sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:panel_label_font",
        params=params,
        explicit_key="difference_pair_panel_label_font_family",
        weights_key="difference_pair_panel_label_font_family_weights",
    )
    record = get_font_family_record(str(font_family))
    return {
        "font_asset_version": font_asset_version(),
        "pool": "global_approved_font_pool",
        **record.to_trace(),
    }


def _compose_pair_image(
    scene_a: MixedVisualScene,
    scene_b: MixedVisualScene,
    *,
    panel_label_font_family: str | None = None,
) -> Tuple[Image.Image, Tuple[int, int], Tuple[int, int]]:
    panel_w = int(scene_a.scene.canvas_width)
    panel_h = int(scene_a.scene.canvas_height)
    margin = 28
    header = 48
    gap = 26
    canvas = Image.new("RGB", (margin * 2 + panel_w * 2 + gap, margin * 2 + header + panel_h), (238, 241, 245))
    draw = ImageDraw.Draw(canvas)
    offset_a = (margin, margin + header)
    offset_b = (margin + panel_w + gap, margin + header)
    canvas.paste(scene_a.scene.image, offset_a)
    canvas.paste(scene_b.scene.image, offset_b)
    draw.rectangle((offset_a[0], offset_a[1], offset_a[0] + panel_w, offset_a[1] + panel_h), outline=(65, 72, 82), width=2)
    draw.rectangle((offset_b[0], offset_b[1], offset_b[0] + panel_w, offset_b[1] + panel_h), outline=(65, 72, 82), width=2)
    draw_panel_label(draw, "Scene A", (offset_a[0] + 10, margin + 8), size=22, font_family=panel_label_font_family)
    draw_panel_label(draw, "Scene B", (offset_b[0] + 10, margin + 8), size=22, font_family=panel_label_font_family)
    return canvas, offset_a, offset_b


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    answer_load = (int(sample.target_count) - _DEFAULTS.target_count_min) / max(1, _DEFAULTS.target_count_max - _DEFAULTS.target_count_min)
    object_load = (int(sample.object_count) - _DEFAULTS.object_count_min) / max(1, _DEFAULTS.object_count_max - _DEFAULTS.object_count_min)
    variant_load = {
        "added_object_count": 0.45,
        "removed_object_count": 0.50,
        "changed_color_object_count": 0.62,
        "moved_object_count": 0.72,
    }[str(sample.variant)]
    score = 0.36 * max(0.0, min(1.0, object_load)) + 0.38 * max(0.0, min(1.0, answer_load)) + 0.26 * float(variant_load)
    return TaskComplexity(
        complexity_score=round(float(score), 6),
        complexity_components={
            "object_load": round(float(object_load), 6),
            "answer_load": round(float(answer_load), 6),
            "variant_load": round(float(variant_load), 6),
        },
    )


@register_task
class IllustrationsVisualObjectDifferenceCountTask:
    """Count object-level differences between two illustration panels."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "visual"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        sample = _sample_spec(instance_seed=int(instance_seed), params=params)
        last_error: Exception | None = None
        base: MixedVisualScene | None = None
        changed: MixedVisualScene | None = None
        changed_ids: Tuple[str, ...] = ()
        for attempt in range(max(1, int(max_attempts))):
            try:
                rng = spawn_rng(int(instance_seed), f"{TASK_ID}:sample", int(attempt))
                object_types = sample_object_types(rng=rng, count=int(sample.object_count))
                base = render_mixed_visual_scene(
                    task_id=TASK_ID,
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt),
                    object_types_for_scene=object_types,
                    params=params,
                    render_defaults=_RENDER_DEFAULTS,
                    fallback=_render_fallback(),
                )
                changed, changed_ids = _modify_scene(
                    base=base,
                    sample=sample,
                    rng=rng,
                    instance_seed=int(instance_seed),
                    attempt_index=int(attempt),
                    params=params,
                )
                break
            except Exception as exc:  # pragma: no cover - retry path.
                last_error = exc
                base = None
                changed = None
                changed_ids = ()
        if base is None or changed is None:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        panel_label_font = _sample_panel_label_font_trace(instance_seed=int(instance_seed), params=params)
        image, offset_a, offset_b = _compose_pair_image(
            base,
            changed,
            panel_label_font_family=str(panel_label_font["font_family"]),
        )
        if sample.variant == "removed_object_count":
            evidence_boxes = sort_bboxes_by_position([bbox_list(base.object_bboxes[obj_id], dx=offset_a[0], dy=offset_a[1]) for obj_id in changed_ids])
        else:
            evidence_boxes = sort_bboxes_by_position([bbox_list(changed.object_bboxes[obj_id], dx=offset_b[0], dy=offset_b[1]) for obj_id in changed_ids])
        moved_center_distances_px = {
            str(obj_id): round(float(_center_distance(base.object_bboxes[obj_id], changed.object_bboxes[obj_id])), 3)
            for obj_id in changed_ids
            if str(sample.variant) == "moved_object_count" and obj_id in base.object_bboxes and obj_id in changed.object_bboxes
        }

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_object_difference_count",
                "evidence_hint_object_difference_count",
                "json_example_object_difference_count",
                "json_example_answer_only_object_difference_count",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_object_difference_count"]),
            "evidence_hint": str(prompt_defaults["evidence_hint_object_difference_count"]),
            "json_example": str(prompt_defaults["json_example_object_difference_count"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_object_difference_count"]),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(sample.variant),
            slots=slots,
            instance_seed=int(instance_seed),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_evidence",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": {
                    "scene_a_objects": list(base.serialized_objects),
                    "scene_b_objects": list(changed.serialized_objects),
                },
                "relations": {
                    "query_id": str(sample.variant),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": str(sample.variant),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "target_count": int(sample.target_count),
                    "object_count": int(sample.object_count),
                    "moved_min_center_distance_px": int(
                        params.get(
                            "moved_min_center_distance_px",
                            group_default(_GEN_DEFAULTS, "moved_min_center_distance_px", _DEFAULTS.moved_min_center_distance_px),
                        )
                    ),
                    "query_id_probabilities": dict(sample.variant_probabilities),
                    "target_count_probabilities": dict(sample.target_count_probabilities),
                    "object_count_probabilities": dict(sample.object_count_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": [int(image.width), int(image.height)],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "style": {
                    "source_background_id": str(base.scene.background_id),
                    "scene_a_offset_px": list(offset_a),
                    "scene_b_offset_px": list(offset_b),
                    "panel_label_font": dict(panel_label_font),
                },
            },
            "render_map": {
                "scene_a_object_bboxes_px": base.object_bboxes,
                "scene_b_object_bboxes_px": changed.object_bboxes,
                "scene_a_offset_px": list(offset_a),
                "scene_b_offset_px": list(offset_b),
                "changed_object_ids": list(changed_ids),
                "moved_center_distances_px": dict(moved_center_distances_px),
            },
            "execution_trace": {
                "query_id": str(sample.variant),
                "target_count": int(sample.target_count),
                "changed_object_ids": list(changed_ids),
                "scene_a_objects": list(base.serialized_objects),
                "scene_b_objects": list(changed.serialized_objects),
            },
            "witness_symbolic": {
                "changed_object_ids": list(changed_ids),
                "answer": int(sample.target_count),
            },
            "projected_evidence": {"bbox_set": list(evidence_boxes)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="integer", value=int(sample.target_count)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_boxes)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.variant),
        )


__all__ = ["IllustrationsVisualObjectDifferenceCountTask"]
