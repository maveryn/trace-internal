"""Annotation rendering helpers for annotated-series chart tasks."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ...shared.bbox_projection import bbox_union, round_bbox
from ...shared.config_defaults import group_default
from ...shared.context_text_assets import sample_context_text
from ...shared.render_variation import resolve_render_int, resolve_render_rgb
from ...shared.text_rendering import draw_text_centered, load_font
from ..shared.chart_scene import RenderedChartScene
from .event_window_common import TASK_ID, _Annotation, _Dataset, _RENDER_DEFAULTS, _render_choice, _render_default_value

def _text_bbox(draw: ImageDraw.ImageDraw, text: str, center: Tuple[float, float], font: Any) -> List[float]:
    try:
        raw = draw.textbbox((0, 0), str(text), font=font)
        width = float(raw[2] - raw[0])
        height = float(raw[3] - raw[1])
    except Exception:
        width, height = draw.textsize(str(text), font=font)
        width = float(width)
        height = float(height)
    return round_bbox(
        [
            float(center[0]) - 0.5 * float(width),
            float(center[1]) - 0.5 * float(height),
            float(center[0]) + 0.5 * float(width),
            float(center[1]) + 0.5 * float(height),
        ]
    )


def _sample_short_annotation_label(
    params: Mapping[str, Any],
    *,
    instance_seed: int,
    namespace: str,
    manifest_key: str,
    max_chars_key: str,
    sample_attempts_key: str,
    fallback_text: str,
    fallback_max_chars: int,
    draw: ImageDraw.ImageDraw | None = None,
    font: Any | None = None,
    max_width_px: int | None = None,
) -> Tuple[str, Dict[str, Any]]:
    manifest_path = str(_render_default_value(params, str(manifest_key), "phrases/callout_phrases.txt"))
    max_chars = max(4, int(_render_default_value(params, str(max_chars_key), int(fallback_max_chars))))
    sample_attempts = max(1, int(_render_default_value(params, str(sample_attempts_key), 128)))
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}.{str(namespace)}")
    width_limit = int(max_width_px) if max_width_px is not None else None
    last_short: Tuple[str, Dict[str, Any]] | None = None
    for draw_index in range(int(sample_attempts)):
        selection = sample_context_text(manifest_path, rng=rng)
        candidate = " ".join(str(selection.text).split())
        if not candidate or len(candidate) > int(max_chars):
            continue
        trace = {
            "text": str(candidate),
            "manifest_path": str(selection.manifest_path),
            "row_index": int(selection.row_index),
            "source_ids": [str(source_id) for source_id in selection.source_ids],
            "max_chars": int(max_chars),
            "sample_attempts": int(sample_attempts),
            "selected_after_draws": int(draw_index + 1),
        }
        last_short = (str(candidate), dict(trace))
        if draw is not None and font is not None and width_limit is not None:
            try:
                text_width = int(draw.textbbox((0, 0), str(candidate), font=font)[2])
            except Exception:
                text_width = int(draw.textsize(str(candidate), font=font)[0])
            if int(text_width) > int(width_limit):
                continue
        return str(candidate), dict(trace)
    if last_short is not None:
        text, trace = last_short
        trace = dict(trace)
        trace["selected_after_draws"] = int(sample_attempts)
        trace["width_fallback"] = bool(draw is not None and font is not None and width_limit is not None)
        return str(text), trace
    fallback = str(fallback_text)[: int(max_chars)].strip() or "Note"
    return fallback, {
        "text": str(fallback),
        "manifest_path": str(manifest_path),
        "row_index": -1,
        "source_ids": [],
        "max_chars": int(max_chars),
        "sample_attempts": int(sample_attempts),
        "selected_after_draws": int(sample_attempts),
        "fallback_used": True,
    }


def _trace_by_label(rendered_scene: RenderedChartScene) -> Dict[str, Dict[str, Any]]:
    return {str(item["label"]): dict(item) for item in rendered_scene.mark_traces}


def _window_bbox(rendered_scene: RenderedChartScene, labels: Sequence[str]) -> List[float]:
    traces = _trace_by_label(rendered_scene)
    selected = [traces[str(label)] for label in labels]
    plot_left, plot_top, plot_right, plot_bottom = [float(value) for value in rendered_scene.plot_bbox_px]
    centers = [float(item["mark_center_px"][0]) for item in selected]
    all_centers = sorted(float(item["mark_center_px"][0]) for item in rendered_scene.mark_traces)
    gaps = [all_centers[index + 1] - all_centers[index] for index in range(len(all_centers) - 1)]
    slot_pad = 0.5 * float(min(gaps) if gaps else max(32.0, plot_right - plot_left))
    x0 = max(float(plot_left), min(centers) - slot_pad)
    x1 = min(float(plot_right), max(centers) + slot_pad)
    return round_bbox([x0, plot_top, x1, plot_bottom])


def _mark_annotation_point(mark_trace: Mapping[str, Any]) -> List[float]:
    center = [float(value) for value in mark_trace["mark_center_px"]]
    return [round(float(center[0]), 3), round(float(center[1]), 3)]


def _apply_window_annotation(
    *,
    image: Image.Image,
    rendered_scene: RenderedChartScene,
    labels: Sequence[str],
    annotation_labels: Sequence[str],
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Annotation:
    window = _window_bbox(rendered_scene, labels)
    fill_rgb = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "annotation_fill_rgb",
        (247, 180, 68),
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    outline_rgb = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "annotation_outline_rgb",
        (174, 91, 28),
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    alpha = max(24, min(96, int(params.get("annotation_fill_alpha", group_default(_RENDER_DEFAULTS, "annotation_fill_alpha", 46)))))
    outline_width = max(2, int(params.get("annotation_outline_width_px", group_default(_RENDER_DEFAULTS, "annotation_outline_width_px", 3))))
    corner_radius = resolve_render_int(
        params,
        _RENDER_DEFAULTS,
        "annotation_corner_radius_px",
        0,
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )

    base = image.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    if int(corner_radius) > 0:
        overlay_draw.rounded_rectangle(
            tuple(float(v) for v in window),
            radius=int(corner_radius),
            fill=(*fill_rgb, int(alpha)),
            outline=(*outline_rgb, 210),
            width=int(outline_width),
        )
    else:
        overlay_draw.rectangle(
            tuple(float(v) for v in window),
            fill=(*fill_rgb, int(alpha)),
            outline=(*outline_rgb, 210),
            width=int(outline_width),
        )
    annotated = Image.alpha_composite(base, overlay).convert("RGB")
    draw = ImageDraw.Draw(annotated)

    font = load_font(int(params.get("annotation_label_font_size_px", group_default(_RENDER_DEFAULTS, "annotation_label_font_size_px", 18))), bold=True)
    label_text, label_source_trace = _sample_short_annotation_label(
        params,
        instance_seed=int(instance_seed),
        namespace="window_label",
        manifest_key="annotation_label_manifest_path",
        max_chars_key="annotation_label_max_chars",
        sample_attempts_key="annotation_label_sample_attempts",
        fallback_text="Window",
        fallback_max_chars=18,
    )
    try:
        raw_bbox = draw.textbbox((0, 0), str(label_text), font=font)
        text_width = float(raw_bbox[2] - raw_bbox[0])
        text_height = float(raw_bbox[3] - raw_bbox[1])
    except Exception:
        text_width, text_height = draw.textsize(str(label_text), font=font)
        text_width = float(text_width)
        text_height = float(text_height)
    pad_x = 10.0
    pad_y = 5.0
    box_width = float(text_width) + 2.0 * pad_x
    box_height = float(text_height) + 2.0 * pad_y
    label_position = _render_choice(
        params,
        key="annotation_label_position",
        fallback="top_left",
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    if str(label_position) == "top_right":
        label_left = float(window[2]) - 8.0 - float(box_width)
        label_top = float(window[1]) + 8.0
    elif str(label_position) == "bottom_left":
        label_left = float(window[0]) + 8.0
        label_top = float(window[3]) - 8.0 - float(box_height)
    else:
        label_left = float(window[0]) + 8.0
        label_top = float(window[1]) + 8.0
    label_left = max(4.0, min(float(label_left), float(image.size[0]) - float(box_width) - 4.0))
    label_top = max(4.0, min(float(label_top), float(image.size[1]) - float(box_height) - 4.0))
    label_box = [label_left, label_top, label_left + box_width, label_top + box_height]
    label_radius = resolve_render_int(
        params,
        _RENDER_DEFAULTS,
        "annotation_label_radius_px",
        6,
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    draw.rounded_rectangle(tuple(label_box), radius=int(label_radius), fill=(255, 255, 255), outline=outline_rgb, width=2)
    draw_text_centered(
        draw,
        text=str(label_text),
        center=(0.5 * (label_box[0] + label_box[2]), 0.5 * (label_box[1] + label_box[3])),
        font=font,
        fill=outline_rgb,
        stroke_fill=(255, 255, 255),
        stroke_width=0,
    )
    label_bbox = round_bbox(label_box)
    traces = _trace_by_label(rendered_scene)
    annotation_points = [_mark_annotation_point(traces[str(label)]) for label in annotation_labels]
    entities = (
        {
            "entity_id": "annotation_window",
            "entity_type": "annotation_window",
            "attrs": {
                "bbox_px": list(window),
                "label": str(label_text),
                "label_bbox_px": list(label_bbox),
                "covered_labels": [str(label) for label in labels],
                "label_source": dict(label_source_trace),
                "annotation_fill_rgb": list(fill_rgb),
                "annotation_outline_rgb": list(outline_rgb),
                "annotation_corner_radius_px": int(corner_radius),
                "annotation_label_position": str(label_position),
                "annotation_label_radius_px": int(label_radius),
            },
        },
    )
    return _Annotation(
        image=annotated,
        entities=tuple(dict(item) for item in entities),
        point_set=tuple(list(item) for item in annotation_points),
        annotation_bboxes={
            "annotation_window": list(window),
            "annotation_label": list(label_bbox),
        },
    )


def _apply_callout_annotation(
    *,
    image: Image.Image,
    rendered_scene: RenderedChartScene,
    anchor_label: str,
    endpoint_label: str,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Annotation:
    traces = _trace_by_label(rendered_scene)
    anchor_trace = traces[str(anchor_label)]
    endpoint_trace = traces[str(endpoint_label)]
    anchor_center = [float(value) for value in anchor_trace["mark_center_px"]]
    plot_left, plot_top, plot_right, _plot_bottom = [float(value) for value in rendered_scene.plot_bbox_px]
    box_width = float(params.get("callout_box_width_px", group_default(_RENDER_DEFAULTS, "callout_box_width_px", 138)))
    box_height = float(params.get("callout_box_height_px", group_default(_RENDER_DEFAULTS, "callout_box_height_px", 48)))
    gap = 18.0
    if float(anchor_center[0]) < 0.5 * (float(plot_left) + float(plot_right)):
        box_left = float(plot_right) - float(box_width) - float(gap)
    else:
        box_left = float(plot_left) + float(gap)
    box_top = float(plot_top) + float(gap)
    callout_box = round_bbox([box_left, box_top, box_left + box_width, box_top + box_height])
    callout_center = (0.5 * (callout_box[0] + callout_box[2]), 0.5 * (callout_box[1] + callout_box[3]))

    fill_rgb = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "callout_fill_rgb",
        (255, 255, 255),
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    outline_rgb = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "callout_outline_rgb",
        (48, 98, 170),
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    text_rgb = resolve_render_rgb(
        params,
        _RENDER_DEFAULTS,
        "callout_text_rgb",
        (38, 42, 50),
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    corner_radius = resolve_render_int(
        params,
        _RENDER_DEFAULTS,
        "callout_corner_radius_px",
        8,
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    arrow_width = resolve_render_int(
        params,
        _RENDER_DEFAULTS,
        "callout_arrow_width_px",
        3,
        instance_seed=int(instance_seed),
        namespace=TASK_ID,
    )
    annotated = image.convert("RGB")
    draw = ImageDraw.Draw(annotated)
    draw.rounded_rectangle(
        tuple(float(value) for value in callout_box),
        radius=int(corner_radius),
        fill=fill_rgb,
        outline=outline_rgb,
        width=max(2, int(arrow_width)),
    )
    font = load_font(int(params.get("callout_font_size_px", group_default(_RENDER_DEFAULTS, "callout_font_size_px", 20))), bold=True)
    callout_text, callout_source_trace = _sample_short_annotation_label(
        params,
        instance_seed=int(instance_seed),
        namespace="callout_label",
        manifest_key="callout_label_manifest_path",
        max_chars_key="callout_label_max_chars",
        sample_attempts_key="callout_label_sample_attempts",
        fallback_text="Callout",
        fallback_max_chars=14,
        draw=draw,
        font=font,
        max_width_px=max(48, int(box_width - 18)),
    )
    draw_text_centered(
        draw,
        text=str(callout_text),
        center=callout_center,
        font=font,
        fill=text_rgb,
        stroke_fill=(255, 255, 255),
        stroke_width=0,
    )
    line_start = (
        float(callout_box[0] if float(anchor_center[0]) < float(callout_center[0]) else callout_box[2]),
        float(callout_center[1]),
    )
    line_end = (float(anchor_center[0]), float(anchor_center[1]))
    draw.line((line_start, line_end), fill=outline_rgb, width=max(2, int(arrow_width)))
    arrow_r = float(max(5, int(arrow_width) + 3))
    draw.ellipse(
        (
            float(anchor_center[0] - arrow_r),
            float(anchor_center[1] - arrow_r),
            float(anchor_center[0] + arrow_r),
            float(anchor_center[1] + arrow_r),
        ),
        fill=outline_rgb,
        outline=(255, 255, 255),
        width=2,
    )
    arrow_bbox = bbox_union(
        [
            [float(line_start[0]), float(line_start[1]), float(line_end[0]), float(line_end[1])],
            [float(anchor_center[0] - arrow_r), float(anchor_center[1] - arrow_r), float(anchor_center[0] + arrow_r), float(anchor_center[1] + arrow_r)],
        ],
        padding=3.0,
    )
    label_bbox = _text_bbox(draw, str(callout_text), callout_center, font)
    annotation_points = [
        _mark_annotation_point(anchor_trace),
        _mark_annotation_point(endpoint_trace),
    ]
    entities = (
        {
            "entity_id": "annotation_callout",
            "entity_type": "annotation_callout",
            "attrs": {
                "bbox_px": list(callout_box),
                "label": str(callout_text),
                "label_bbox_px": list(label_bbox),
                "arrow_bbox_px": list(arrow_bbox),
                "anchor_label": str(anchor_label),
                "endpoint_label": str(endpoint_label),
                "label_source": dict(callout_source_trace),
                "callout_fill_rgb": list(fill_rgb),
                "callout_outline_rgb": list(outline_rgb),
                "callout_corner_radius_px": int(corner_radius),
                "callout_arrow_width_px": int(arrow_width),
            },
        },
    )
    return _Annotation(
        image=annotated,
        entities=tuple(dict(item) for item in entities),
        point_set=tuple(list(item) for item in annotation_points),
        annotation_bboxes={
            "annotation_callout": list(callout_box),
            "annotation_callout_label": list(label_bbox),
            "annotation_callout_arrow": list(arrow_bbox),
        },
    )


def _apply_annotation(
    *,
    image: Image.Image,
    rendered_scene: RenderedChartScene,
    dataset: _Dataset,
    params: Mapping[str, Any],
    instance_seed: int,
) -> _Annotation:
    if dataset.query_id in {"event_window_extremum_label", "event_window_threshold_count"}:
        return _apply_window_annotation(
            image=image,
            rendered_scene=rendered_scene,
            labels=dataset.window_labels,
            annotation_labels=dataset.annotation_labels,
            params=params,
            instance_seed=int(instance_seed),
        )
    return _apply_callout_annotation(
        image=image,
        rendered_scene=rendered_scene,
        anchor_label=str(dataset.query_params["anchor_label"]),
        endpoint_label=str(dataset.query_params["endpoint_label"]),
        params=params,
        instance_seed=int(instance_seed),
    )
