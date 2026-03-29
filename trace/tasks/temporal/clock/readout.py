"""Analog-clock temporal task with direct time readout and minute offsets."""

from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ..shared.clock_scene import (
    ClockRenderParams,
    SUPPORTED_TEMPORAL_CLOCK_SCENE_VARIANTS,
    render_clock_scene,
    resolve_clock_render_params,
)
from ..shared.complexity import (
    build_temporal_complexity,
    normalize_float_with_bounds,
    normalize_int_with_bounds,
    resolve_temporal_complexity_weights,
)
from ..shared.task_support import resolve_temporal_named_variant
from ..shared.style import (
    SUPPORTED_TEMPORAL_CLOCK_COLOR_NAMES,
    SUPPORTED_TEMPORAL_CLOCK_STYLE_VARIANTS,
    build_temporal_clock_theme,
)
from ..shared.time_format import (
    add_clock_minutes,
    clock_hand_angle_gap_deg,
    clock_total_minutes,
    format_clock_hhmm,
    split_clock_total_minutes,
)
from ..shared.visual_defaults import load_temporal_background_defaults, load_temporal_noise_defaults


TASK_ID = "task_temporal_clock_readout"
SUPPORTED_TASK_VARIANTS: Tuple[str, ...] = (
    "shown_time",
    "minutes_after",
    "minutes_before",
)

_TIME_READING_BASE_BY_VARIANT = {
    "shown_time": 0.28,
    "minutes_after": 0.58,
    "minutes_before": 0.58,
}
_VISUAL_SCAN_BASE_BY_SCENE = {
    "classic": 0.34,
    "minimal": 0.22,
    "outline": 0.26,
}
_VISUAL_SCAN_STYLE_BONUS = {
    "studio": 0.00,
    "accented": 0.04,
    "marker": 0.06,
}
_CLUTTER_BASE_BY_SCENE = {
    "classic": 0.32,
    "minimal": 0.12,
    "outline": 0.18,
}
_CLUTTER_STYLE_BONUS = {
    "studio": 0.00,
    "accented": 0.05,
    "marker": 0.08,
}


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for temporal clock-readout scenes."""

    hour_min: int = 1
    hour_max: int = 12
    minute_min: int = 0
    minute_max: int = 55
    minute_step: int = 5
    min_hand_angle_gap_deg: float = 10.0
    canvas_width: int = 640
    canvas_height: int = 640
    outer_margin_px: int = 36
    face_radius_px: int = 236
    bezel_width_px: int = 10
    numeral_font_size_px: int = 28
    major_tick_length_px: int = 18
    minor_tick_length_px: int = 8
    major_tick_width_px: int = 4
    minor_tick_width_px: int = 2
    minor_tick_dot_radius_px: int = 3
    hour_hand_width_px: int = 12
    minute_hand_width_px: int = 8
    hand_bbox_padding_px: int = 6
    center_dot_radius_px: int = 8
    inner_ring_inset_px: int = 18
    inner_ring_width_px: int = 4


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved semantic and visual support for one clock-readout instance."""

    task_variant: str
    scene_variant: str
    style_variant: str
    accent_color_name: str
    shown_total_minutes: int
    shown_hour: int
    shown_minute: int
    delta_minutes: int | None
    answer_time_text: str
    hour_support: Tuple[int, int]
    minute_support: Tuple[int, int, int]
    delta_minutes_support: Tuple[int, ...]
    min_hand_angle_gap_deg: float
    task_variant_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    accent_color_name_probabilities: Dict[str, float]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("temporal", "clock")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
_COMPLEXITY_WEIGHTS = resolve_temporal_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)
POST_IMAGE_BACKGROUND_DEFAULTS = load_temporal_background_defaults(task_group="clock")
POST_IMAGE_NOISE_DEFAULTS = load_temporal_noise_defaults(task_group="clock", apply_prob=0.0)


def _canonical_hand_example_bboxes() -> list[list[int]]:
    """Return one stable two-hand bbox example for prompt examples."""

    return [
        [298, 270, 322, 405],
        [314, 148, 330, 406],
    ]


def _build_prompt_json_examples(*, task_variant: str, delta_minutes: int | None) -> tuple[str, str]:
    """Return prompt JSON examples that match the active offset semantics."""

    shown_total_minutes = clock_total_minutes(3, 25)
    answer_total_minutes = int(shown_total_minutes)
    if str(task_variant) == "minutes_after":
        answer_total_minutes = add_clock_minutes(int(shown_total_minutes), int(delta_minutes))
    elif str(task_variant) == "minutes_before":
        answer_total_minutes = add_clock_minutes(int(shown_total_minutes), -int(delta_minutes))
    answer_text = str(format_clock_hhmm(int(answer_total_minutes)))
    answer_and_evidence = {
        "evidence": _canonical_hand_example_bboxes(),
        "answer": str(answer_text),
    }
    answer_only = {"answer": str(answer_text)}
    return (
        json.dumps(answer_and_evidence, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps(answer_only, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _resolve_named_variant(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Tuple[str, ...],
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named temporal axis."""

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{namespace}")
    return resolve_temporal_named_variant(
        rng,
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported=supported,
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace=str(namespace),
    )


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one concrete clock-readout query from balanced supports."""

    task_variant, task_variant_probabilities = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        supported=SUPPORTED_TASK_VARIANTS,
        namespace="task_variant",
    )
    scene_variant, scene_variant_probabilities = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_TEMPORAL_CLOCK_SCENE_VARIANTS,
        namespace="scene_variant",
    )
    style_variant, style_variant_probabilities = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_TEMPORAL_CLOCK_STYLE_VARIANTS,
        namespace="style_variant",
    )
    accent_color_name, accent_color_name_probabilities = _resolve_named_variant(
        instance_seed=int(instance_seed),
        params=params,
        explicit_key="accent_color_name",
        weights_key="accent_color_name_weights",
        balance_flag_key="balanced_accent_color_name_sampling",
        supported=SUPPORTED_TEMPORAL_CLOCK_COLOR_NAMES,
        namespace="accent_color_name",
    )

    hour_min = int(params.get("hour_min", group_default(_GEN_DEFAULTS, "hour_min", _DEFAULTS.hour_min)))
    hour_max = int(params.get("hour_max", group_default(_GEN_DEFAULTS, "hour_max", _DEFAULTS.hour_max)))
    minute_min = int(params.get("minute_min", group_default(_GEN_DEFAULTS, "minute_min", _DEFAULTS.minute_min)))
    minute_max = int(params.get("minute_max", group_default(_GEN_DEFAULTS, "minute_max", _DEFAULTS.minute_max)))
    minute_step = int(params.get("minute_step", group_default(_GEN_DEFAULTS, "minute_step", _DEFAULTS.minute_step)))
    min_hand_angle_gap_deg = float(
        params.get(
            "min_hand_angle_gap_deg",
            group_default(_GEN_DEFAULTS, "min_hand_angle_gap_deg", _DEFAULTS.min_hand_angle_gap_deg),
        )
    )
    if minute_step <= 0:
        raise ValueError("minute_step must be positive for temporal clock tasks")
    if float(min_hand_angle_gap_deg) < 0.0:
        raise ValueError("min_hand_angle_gap_deg must be non-negative for temporal clock tasks")

    minute_support = tuple(range(int(minute_min), int(minute_max) + 1, int(minute_step)))
    if not minute_support:
        raise ValueError("minute support is empty for temporal clock tasks")
    if minute_support[0] < 0 or minute_support[-1] > 59:
        raise ValueError("minute support must stay within 0..59 for temporal clock tasks")
    hour_support = tuple(range(int(hour_min), int(hour_max) + 1))
    if not hour_support:
        raise ValueError("hour support is empty for temporal clock tasks")
    if hour_support[0] < 1 or hour_support[-1] > 12:
        raise ValueError("hour support must stay within 1..12 for temporal clock tasks")

    shown_total_support = tuple(
        clock_total_minutes(int(hour), int(minute))
        for hour in hour_support
        for minute in minute_support
        if float(clock_hand_angle_gap_deg(clock_total_minutes(int(hour), int(minute)))) >= float(min_hand_angle_gap_deg)
    )
    if not shown_total_support:
        raise ValueError("shown time support is empty after clock-hand angle-gap filtering")
    shown_index = resolve_selection_index(
        params=params,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:shown_total_minutes",
    )

    explicit_hour = params.get("shown_hour")
    explicit_minute = params.get("shown_minute")
    explicit_total = params.get("shown_total_minutes")
    if explicit_total is not None:
        shown_total_minutes = int(explicit_total)
    elif explicit_hour is not None or explicit_minute is not None:
        if explicit_hour is None or explicit_minute is None:
            raise ValueError("shown_hour and shown_minute must be provided together")
        shown_total_minutes = clock_total_minutes(int(explicit_hour), int(explicit_minute))
    else:
        shown_total_minutes = int(shown_total_support[int(shown_index % len(shown_total_support))])
    if int(shown_total_minutes) not in shown_total_support:
        raise ValueError("shown time is outside configured support for temporal clock tasks")

    delta_support_raw = params.get("delta_minutes_support", group_default(_GEN_DEFAULTS, "delta_minutes_support", ()))
    delta_support = tuple(int(value) for value in delta_support_raw)
    delta_minutes: int | None = None
    if str(task_variant) in {"minutes_after", "minutes_before"}:
        if not delta_support:
            raise ValueError("delta_minutes_support is empty for offset clock variants")
        explicit_delta = params.get("delta_minutes")
        if explicit_delta is not None:
            delta_minutes = int(explicit_delta)
            if int(delta_minutes) not in delta_support:
                raise ValueError("delta_minutes is outside configured support for temporal clock tasks")
        else:
            delta_index = resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{TASK_ID}:delta_minutes",
            )
            delta_minutes = int(delta_support[int(delta_index % len(delta_support))])

    answer_total_minutes = int(shown_total_minutes)
    if str(task_variant) == "minutes_after":
        answer_total_minutes = add_clock_minutes(int(shown_total_minutes), int(delta_minutes))
    elif str(task_variant) == "minutes_before":
        answer_total_minutes = add_clock_minutes(int(shown_total_minutes), -int(delta_minutes))

    shown_hour, shown_minute = split_clock_total_minutes(int(shown_total_minutes))
    return _ResolvedQuery(
        task_variant=str(task_variant),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        accent_color_name=str(accent_color_name),
        shown_total_minutes=int(shown_total_minutes),
        shown_hour=int(shown_hour),
        shown_minute=int(shown_minute),
        delta_minutes=(int(delta_minutes) if delta_minutes is not None else None),
        answer_time_text=str(format_clock_hhmm(int(answer_total_minutes))),
        hour_support=(int(hour_support[0]), int(hour_support[-1])),
        minute_support=(int(minute_support[0]), int(minute_support[-1]), int(minute_step)),
        delta_minutes_support=tuple(int(value) for value in delta_support),
        min_hand_angle_gap_deg=float(min_hand_angle_gap_deg),
        task_variant_probabilities=dict(task_variant_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        accent_color_name_probabilities=dict(accent_color_name_probabilities),
    )


@register_task
class TemporalClockReadoutTask:
    """Return one clock time or one minute-offset time from a single analog clock."""

    task_id = TASK_ID
    domain = "temporal"
    task_group = "clock"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query = _resolve_query(int(instance_seed), params=params)
        render_params = resolve_clock_render_params(
            params,
            render_defaults=_RENDER_DEFAULTS,
            fallback_values=asdict(_DEFAULTS),
        )
        clock_theme = build_temporal_clock_theme(
            accent_color_name=str(query.accent_color_name),
            style_variant=str(query.style_variant),
        )

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_clock_scene(
            background,
            scene_variant=str(query.scene_variant),
            shown_total_minutes=int(query.shown_total_minutes),
            render_params=render_params,
            visual_theme=clock_theme,
        )
        image, post_noise_meta = apply_post_image_noise(
            rendered_scene.image,
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_NOISE_DEFAULTS,
        )

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "task_family_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_classic",
                "object_description_minimal",
                "object_description_outline",
                "evidence_hint",
                "answer_hint",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        object_description = str(prompt_defaults[f"object_description_{str(query.scene_variant)}"])
        json_example, json_example_answer_only = _build_prompt_json_examples(
            task_variant=str(query.task_variant),
            delta_minutes=(int(query.delta_minutes) if query.delta_minutes is not None else None),
        )
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            task_family_key=str(prompt_defaults["task_family_key"]),
            task_key=str(prompt_defaults["task_key"]),
            task_variant_key=str(query.task_variant),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(object_description),
                "delta_minutes": (str(query.delta_minutes) if query.delta_minutes is not None else ""),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_bboxes = [
            [round(float(value), 3) for value in rendered_scene.hour_hand_bbox_px],
            [round(float(value), 3) for value in rendered_scene.minute_hand_bbox_px],
        ]
        answer_gt = TypedValue(type="string", value=str(query.answer_time_text))
        evidence_gt = TypedValue(type="bbox_set", value=list(evidence_bboxes))

        trace_payload = {
            "scene_ir": {
                "scene_kind": "temporal_clock_single",
                "entities": [dict(entity) for entity in rendered_scene.entities],
                "relations": {
                    "task_variant": str(query.task_variant),
                    "scene_variant": str(query.scene_variant),
                    "shown_total_minutes": int(query.shown_total_minutes),
                    "shown_time_text": str(format_clock_hhmm(int(query.shown_total_minutes))),
                    "delta_minutes": (int(query.delta_minutes) if query.delta_minutes is not None else None),
                    "answer_time_text": str(query.answer_time_text),
                },
            },
            "query_spec": {
                "task_variant": str(query.task_variant),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "task_variant": str(query.task_variant),
                    "scene_variant": str(query.scene_variant),
                    "style_variant": str(query.style_variant),
                    "accent_color_name": str(query.accent_color_name),
                    "task_variant_probabilities": dict(query.task_variant_probabilities),
                    "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                    "style_variant_probabilities": dict(query.style_variant_probabilities),
                    "accent_color_name_probabilities": dict(query.accent_color_name_probabilities),
                    "hour_support": [int(query.hour_support[0]), int(query.hour_support[1])],
                    "minute_support": [int(value) for value in query.minute_support],
                    "delta_minutes_support": [int(value) for value in query.delta_minutes_support],
                    "min_hand_angle_gap_deg": float(query.min_hand_angle_gap_deg),
                },
            },
            "render_spec": {
                "canvas_width": int(render_params.canvas_width),
                "canvas_height": int(render_params.canvas_height),
                "coord_space": "pixel",
                "scene_variant": str(query.scene_variant),
                "background_style": dict(background_meta),
                "post_image_noise": dict(post_noise_meta),
                "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
                "clock_style": {
                    "accent_color_name": str(query.accent_color_name),
                    "style_variant": str(query.style_variant),
                    "face_radius_px": int(render_params.face_radius_px),
                    "bezel_width_px": int(render_params.bezel_width_px),
                    "numeral_font_size_px": int(render_params.numeral_font_size_px),
                    "hour_hand_width_px": int(render_params.hour_hand_width_px),
                    "minute_hand_width_px": int(render_params.minute_hand_width_px),
                    "minor_tick_dot_radius_px": int(render_params.minor_tick_dot_radius_px),
                    "inner_ring_inset_px": int(render_params.inner_ring_inset_px),
                    "inner_ring_width_px": int(render_params.inner_ring_width_px),
                    "resolved_colors_rgb": {
                        "face_fill": [int(value) for value in clock_theme.face_fill_rgb],
                        "face_outline": [int(value) for value in clock_theme.face_outline_rgb],
                        "numerals": [int(value) for value in clock_theme.numeral_color_rgb],
                        "ticks": [int(value) for value in clock_theme.tick_color_rgb],
                        "hour_hand": [int(value) for value in clock_theme.hour_hand_color_rgb],
                        "minute_hand": [int(value) for value in clock_theme.minute_hand_color_rgb],
                        "center_dot": [int(value) for value in clock_theme.center_dot_color_rgb],
                        "inner_ring": (
                            [int(value) for value in clock_theme.inner_ring_rgb]
                            if clock_theme.inner_ring_rgb is not None
                            else None
                        ),
                    },
                    "minor_tick_mode": str(clock_theme.minor_tick_mode),
                },
            },
            "render_map": {
                "image_id": "img0",
                "scene_bbox_px": [round(float(value), 3) for value in rendered_scene.scene_bbox_px],
                "face_bbox_px": [round(float(value), 3) for value in rendered_scene.face_bbox_px],
                "center_px": [round(float(value), 3) for value in rendered_scene.center_px],
                "hand_bboxes_px": {
                    "hour": [round(float(value), 3) for value in rendered_scene.hour_hand_bbox_px],
                    "minute": [round(float(value), 3) for value in rendered_scene.minute_hand_bbox_px],
                },
                "hand_tips_px": {
                    "hour": [round(float(value), 3) for value in rendered_scene.hour_hand_tip_px],
                    "minute": [round(float(value), 3) for value in rendered_scene.minute_hand_tip_px],
                },
            },
            "execution_trace": {
                "task_variant": str(query.task_variant),
                "scene_variant": str(query.scene_variant),
                "style_variant": str(query.style_variant),
                "accent_color_name": str(query.accent_color_name),
                "shown_total_minutes": int(query.shown_total_minutes),
                "shown_hour": int(query.shown_hour),
                "shown_minute": int(query.shown_minute),
                "shown_time_text": str(format_clock_hhmm(int(query.shown_total_minutes))),
                "delta_minutes": (int(query.delta_minutes) if query.delta_minutes is not None else None),
                "answer_time_text": str(query.answer_time_text),
                "hour_support": [int(query.hour_support[0]), int(query.hour_support[1])],
                "minute_support": [int(value) for value in query.minute_support],
                "delta_minutes_support": [int(value) for value in query.delta_minutes_support],
                "min_hand_angle_gap_deg": float(query.min_hand_angle_gap_deg),
                "task_variant_probabilities": dict(query.task_variant_probabilities),
                "scene_variant_probabilities": dict(query.scene_variant_probabilities),
                "style_variant_probabilities": dict(query.style_variant_probabilities),
                "accent_color_name_probabilities": dict(query.accent_color_name_probabilities),
                "question_format": str(query.task_variant),
                "supporting_parts": ["hour_hand", "minute_hand"],
            },
            "witness_symbolic": {
                "type": "bbox_set",
                "value": list(evidence_bboxes),
            },
            "projected_evidence": {
                "bbox_set": list(evidence_bboxes),
                "pixel_point_map": {
                    "clock_center": [round(float(value), 3) for value in rendered_scene.center_px],
                    "hour_hand_tip": [round(float(value), 3) for value in rendered_scene.hour_hand_tip_px],
                    "minute_hand_tip": [round(float(value), 3) for value in rendered_scene.minute_hand_tip_px],
                },
            },
        }

        minute_complexity = 0.25 if int(query.shown_minute) in {0, 15, 30, 45} else 0.55
        hand_angle_gap = abs(
            ((float(rendered_scene.entities[2]["attrs"]["angle_deg"]) - float(rendered_scene.entities[1]["attrs"]["angle_deg"]) + 180.0) % 360.0)
            - 180.0
        )
        complexity = build_temporal_complexity(
            weights=_COMPLEXITY_WEIGHTS,
            components={
                "time_reading": min(
                    1.0,
                    float(_TIME_READING_BASE_BY_VARIANT[str(query.task_variant)])
                    + (0.25 * float(minute_complexity))
                    + (0.20 * float(normalize_int_with_bounds(int(query.shown_minute), [0, 55]))),
                ),
                "visual_scan": min(
                    1.0,
                    float(_VISUAL_SCAN_BASE_BY_SCENE[str(query.scene_variant)])
                    + float(_VISUAL_SCAN_STYLE_BONUS[str(query.style_variant)])
                    + (0.10 * float(normalize_int_with_bounds(int(query.shown_minute), [0, 55]))),
                ),
                "ambiguity": min(
                    1.0,
                    (0.45 * float(1.0 - normalize_float_with_bounds(float(hand_angle_gap), [20.0, 180.0])))
                    + (0.30 * float(minute_complexity))
                    + (0.25 * (0.25 if str(query.task_variant) == "shown_time" else 0.55)),
                ),
                "clutter": min(
                    1.0,
                    float(_CLUTTER_BASE_BY_SCENE[str(query.scene_variant)])
                    + float(_CLUTTER_STYLE_BONUS[str(query.style_variant)]),
                ),
            },
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
            task_variant=str(query.task_variant),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["TemporalClockReadoutTask"]
