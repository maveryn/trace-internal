"""Pages-domain rendering defaults for font and non-answer context text."""

from __future__ import annotations

import random
from functools import wraps
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Sequence, Tuple

from PIL import ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ...base import TaskOutput
from ...shared.context_text_assets import sample_context_text
from ...shared.font_assets import font_asset_version, font_role_trace, sample_font_family
from ...shared.text_rendering import load_font, resolve_text_stroke_fill, temporary_default_font_family
from ...shared.visual_style.context_layer import ContextTextElement, context_text_layer_metadata
from ...shared.text_legibility import draw_text_traced


BBox = Tuple[float, float, float, float]
_CONTEXT_DENSITY_WEIGHTS = {
    "clean": 0.04,
    "light": 0.42,
    "one_side_note": 0.38,
    "two_side_notes": 0.16,
}
_CONTEXT_DENSITY_CONFIG = {
    "clean": {"simple_count": 0, "side_note_count": 0},
    "light": {"simple_count": 4, "side_note_count": 0},
    "one_side_note": {"simple_count": 3, "side_note_count": 1},
    "two_side_notes": {"simple_count": 3, "side_note_count": 2},
}


def wrap_pages_generation(
    original_generate: Callable[..., TaskOutput],
    *,
    task_id: str,
    task_group: str,
) -> Callable[..., TaskOutput]:
    """Wrap one pages task generator with domain-wide render audit defaults."""

    @wraps(original_generate)
    def _generate_with_pages_render_defaults(self, instance_seed: int, *, params: dict[str, Any], max_attempts: int) -> TaskOutput:
        font_family = resolve_pages_default_font_family(
            task_id=str(task_id),
            task_group=str(task_group),
            instance_seed=int(instance_seed),
            params=params,
        )
        with temporary_default_font_family(str(font_family)):
            output = original_generate(self, int(instance_seed), params=params, max_attempts=int(max_attempts))
        annotate_pages_font_assets(
            output,
            font_family=str(font_family),
            task_id=str(task_id),
            task_group=str(task_group),
        )
        add_pages_safe_context_text(
            output,
            instance_seed=int(instance_seed),
            params=params,
            task_id=str(task_id),
            task_group=str(task_group),
        )
        return output

    return _generate_with_pages_render_defaults


def resolve_pages_default_font_family(
    *,
    task_id: str,
    task_group: str,
    instance_seed: int,
    params: Mapping[str, Any] | None,
) -> str:
    """Sample one default page font family for read-required page text."""

    resolved_params = _resolve_context_text_params(
        params=params,
        task_id=str(task_id),
        task_group=str(task_group),
    )
    if "pages_font_family" not in resolved_params and "font_family" in resolved_params:
        resolved_params["pages_font_family"] = resolved_params["font_family"]
    if "pages_font_family_weights" not in resolved_params and "font_family_weights" in resolved_params:
        resolved_params["pages_font_family_weights"] = resolved_params["font_family_weights"]
    return sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{task_group}.pages_default_font",
        params=resolved_params,
        explicit_key="pages_font_family",
        weights_key="pages_font_family_weights",
    )


def annotate_pages_font_assets(
    output: TaskOutput,
    *,
    font_family: str,
    task_id: str,
    task_group: str,
) -> None:
    """Record the pages default font family in render metadata."""

    trace_payload = output.trace_payload if isinstance(output.trace_payload, MutableMapping) else None
    if trace_payload is None:
        return
    render_spec = trace_payload.setdefault("render_spec", {})
    if not isinstance(render_spec, MutableMapping):
        return
    font_assets = render_spec.setdefault("font_assets", {})
    if not isinstance(font_assets, MutableMapping):
        font_assets = {}
        render_spec["font_assets"] = font_assets
    font_assets.setdefault("asset_version", font_asset_version())
    font_assets["pages_default_font_family"] = str(font_family)
    font_assets["pages_default_font_role"] = "readout"
    font_assets["pages_default_font_trace"] = font_role_trace(str(font_family), role="readout")
    font_assets["pages_font_sampling_policy"] = "readout_pool_single_family_per_page_instance"
    font_assets["task_id"] = str(task_id)
    font_assets["task_group"] = str(task_group)


def add_pages_safe_context_text(
    output: TaskOutput,
    *,
    instance_seed: int,
    params: Mapping[str, Any] | None,
    task_id: str,
    task_group: str,
) -> None:
    """Draw non-answer context text into safe empty page margins and trace it."""

    trace_payload = output.trace_payload if isinstance(output.trace_payload, MutableMapping) else None
    if trace_payload is None or output.image is None:
        return

    resolved_params = _resolve_context_text_params(
        params=params,
        task_id=str(task_id),
        task_group=str(task_group),
    )
    enabled = bool(resolved_params.get("pages_context_text_enabled", resolved_params.get("context_text_enabled", True)))
    if not enabled:
        _record_context_text_layer(
            trace_payload,
            elements=(),
            enabled=False,
            layout_mode="none",
            layout_spec={"reason": "disabled"},
        )
        return

    image = output.image.convert("RGB").copy()
    draw = ImageDraw.Draw(image)
    width, height = image.size
    occupied = _collect_occupied_bboxes(trace_payload)
    rng = spawn_rng(int(instance_seed), f"{task_id}.{task_group}.pages_context_text")
    context_font_family = sample_font_family(
        role="context",
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.{task_group}.pages_context_text_font",
        params=_context_font_params(resolved_params),
        explicit_key="pages_context_text_font_family",
        weights_key="pages_context_text_font_family_weights",
    )
    text_fill = _coerce_rgb(
        resolved_params.get("pages_context_text_rgb", resolved_params.get("context_text_rgb", (62, 70, 82))),
        fallback=(62, 70, 82),
    )
    muted_fill = _coerce_rgb(
        resolved_params.get("pages_context_muted_text_rgb", resolved_params.get("context_muted_text_rgb", (101, 109, 123))),
        fallback=(101, 109, 123),
    )
    box_fill = _coerce_rgb(
        resolved_params.get("pages_context_box_fill_rgb", resolved_params.get("context_box_fill_rgb", (255, 255, 255))),
        fallback=(255, 255, 255),
    )
    box_border = _coerce_rgb(
        resolved_params.get("pages_context_box_border_rgb", resolved_params.get("context_box_border_rgb", (204, 211, 222))),
        fallback=(204, 211, 222),
    )
    density, density_weights = _resolve_context_density(resolved_params, rng=rng)
    density_config = dict(_CONTEXT_DENSITY_CONFIG[str(density)])
    simple_count_override = resolved_params.get(
        "pages_context_simple_count",
        resolved_params.get("context_text_simple_count"),
    )
    if simple_count_override is not None:
        density_config["simple_count"] = max(0, int(simple_count_override))
    side_note_count_override = resolved_params.get(
        "pages_context_side_note_count",
        resolved_params.get("context_text_side_note_count"),
    )
    if side_note_count_override is not None:
        density_config["side_note_count"] = max(0, int(side_note_count_override))
    default_max_elements = int(density_config["simple_count"]) + (2 * int(density_config["side_note_count"]))
    max_elements = max(
        0,
        int(
            resolved_params.get(
                "pages_context_text_max_elements",
                resolved_params.get("context_text_max_elements", default_max_elements),
            )
        ),
    )
    candidates = _context_candidates(width=int(width), height=int(height))
    selected_candidates = _select_candidate_order(candidates, rng=rng)[: int(density_config["simple_count"])]
    elements: list[ContextTextElement] = []
    occupied_with_context = list(occupied)

    side_notes_added = _draw_side_notes(
        draw,
        elements=elements,
        scene_occupied=occupied,
        occupied=occupied_with_context,
        rng=rng,
        width=int(width),
        height=int(height),
        requested_count=int(density_config["side_note_count"]),
        max_elements=int(max_elements),
        font_family=str(context_font_family),
        text_fill=text_fill,
        muted_fill=muted_fill,
        box_fill=box_fill,
        box_border=box_border,
    )

    for candidate in selected_candidates:
        if len(elements) >= int(max_elements):
            break
        role = str(candidate["role"])
        selection = sample_context_text(str(candidate["manifest_path"]), rng=rng)
        font_size = int(candidate["font_size_px"])
        font = load_font(font_size, bold=bool(candidate["bold"]), font_family=str(context_font_family))
        fitted = _fit_one_line(draw, str(selection.text), font=font, max_width_px=int(candidate["max_width_px"]))
        if not fitted:
            continue
        bbox = _candidate_bbox(
            draw,
            text=fitted,
            font=font,
            slot=str(candidate["slot"]),
            width=int(width),
            height=int(height),
            margin_px=int(candidate["margin_px"]),
        )
        if not _bbox_is_safe(bbox, occupied_with_context, width=int(width), height=int(height), padding_px=8):
            continue
        stroke_width = 1
        fill = text_fill if role == "header" else muted_fill
        draw_text_traced(draw,
            (float(bbox[0]), float(bbox[1])),
            fitted,
            font=font,
            fill=tuple(int(value) for value in fill),
            stroke_width=int(stroke_width),
            stroke_fill=resolve_text_stroke_fill(tuple(fill)),
         role="readout", required=False,)
        trace_bbox = tuple(int(round(value)) for value in bbox)
        element = ContextTextElement(
            context_id=f"pages_context_{len(elements):02d}",
            role=str(role),
            text=str(fitted),
            bbox_xyxy=trace_bbox,
            manifest_path=str(selection.manifest_path),
            source_ids=tuple(selection.source_ids),
            row_index=int(selection.row_index),
            layout_mode=f"safe_margin:{candidate['slot']}",
            font_family=str(context_font_family),
        )
        elements.append(element)
        occupied_with_context.append(tuple(float(value) for value in trace_bbox))

    output.image = image
    layout_mode = f"safe_margin:{density}" if elements else f"safe_margin:{density}:no_safe_slots"
    layout_spec = {
        "placement_policy": "post_render_safe_margin",
        "density": str(density),
        "density_weights": dict(density_weights),
        "candidate_slots": [str(candidate["slot"]) for candidate in candidates],
        "max_elements": int(max_elements),
        "simple_candidate_count": int(density_config["simple_count"]),
        "requested_side_note_count": int(density_config["side_note_count"]),
        "side_notes_added": int(side_notes_added),
        "font_family": str(context_font_family),
        "overlap_padding_px": 8,
    }
    _record_context_text_layer(
        trace_payload,
        elements=tuple(elements),
        enabled=True,
        layout_mode=str(layout_mode),
        layout_spec=layout_spec,
    )


def _resolve_context_text_params(
    *,
    params: Mapping[str, Any] | None,
    task_id: str,
    task_group: str,
) -> dict[str, Any]:
    """Merge task-config context text defaults with explicit generation params."""

    resolved = _context_text_config_defaults(task_id=str(task_id), task_group=str(task_group))
    resolved.update(dict(params or {}))
    return resolved


def _context_text_config_defaults(*, task_id: str, task_group: str) -> dict[str, Any]:
    cfg = get_task_group_defaults("pages", str(task_group))
    visual = cfg.get("visual", {}) if isinstance(cfg, Mapping) else {}
    if not isinstance(visual, Mapping):
        return {}

    resolved: dict[str, Any] = {}
    shared = visual.get("shared", {})
    if isinstance(shared, Mapping):
        shared_context = shared.get("context_text", {})
        if isinstance(shared_context, Mapping):
            resolved.update(dict(shared_context))

    direct_context = visual.get("context_text", {})
    if isinstance(direct_context, Mapping):
        resolved.update(dict(direct_context))

    task_overrides = visual.get("task_overrides", {})
    if isinstance(task_overrides, Mapping):
        task_values = task_overrides.get(str(task_id), {})
        if isinstance(task_values, Mapping):
            task_context = task_values.get("context_text", {})
            if isinstance(task_context, Mapping):
                resolved.update(dict(task_context))
    return resolved


def _context_font_params(params: Mapping[str, Any]) -> dict[str, Any]:
    resolved = dict(params)
    if "pages_context_text_font_family" not in resolved and "context_text_font_family" in resolved:
        resolved["pages_context_text_font_family"] = resolved["context_text_font_family"]
    if "pages_context_text_font_family_weights" not in resolved and "context_text_font_family_weights" in resolved:
        resolved["pages_context_text_font_family_weights"] = resolved["context_text_font_family_weights"]
    return resolved


def _resolve_context_density(params: Mapping[str, Any], *, rng: random.Random) -> tuple[str, dict[str, float]]:
    supported = tuple(_CONTEXT_DENSITY_CONFIG)
    explicit = params.get("pages_context_density", params.get("context_text_density"))
    if explicit is not None:
        density = str(explicit)
        if density not in set(supported):
            raise ValueError(f"unsupported pages context density: {density!r}")
        return density, {key: 1.0 if key == density else 0.0 for key in supported}
    raw_weights = params.get("pages_context_density_weights", params.get("context_text_density_weights", _CONTEXT_DENSITY_WEIGHTS))
    weights = {
        key: float(raw_weights.get(key, _CONTEXT_DENSITY_WEIGHTS[key]))  # type: ignore[union-attr]
        if isinstance(raw_weights, Mapping)
        else float(_CONTEXT_DENSITY_WEIGHTS[key])
        for key in supported
    }
    density = _weighted_choice(rng, weights, fallback=supported)
    total = sum(max(0.0, float(value)) for value in weights.values())
    if total <= 0.0:
        normalized = {key: 1.0 / float(len(supported)) for key in supported}
    else:
        normalized = {key: max(0.0, float(value)) / total for key, value in weights.items()}
    return str(density), dict(normalized)


def _weighted_choice(rng: random.Random, weights: Mapping[str, float], *, fallback: Sequence[str]) -> str:
    weighted = [(str(key), max(0.0, float(weights.get(str(key), 0.0)))) for key in fallback]
    weighted = [(key, value) for key, value in weighted if value > 0.0]
    if not weighted:
        weighted = [(str(key), 1.0) for key in fallback]
    total = sum(value for _key, value in weighted)
    cursor = rng.random() * float(total)
    running = 0.0
    for key, value in weighted:
        running += float(value)
        if cursor <= running:
            return str(key)
    return str(weighted[-1][0])


def _draw_side_notes(
    draw: ImageDraw.ImageDraw,
    *,
    elements: list[ContextTextElement],
    scene_occupied: Sequence[BBox],
    occupied: list[BBox],
    rng: random.Random,
    width: int,
    height: int,
    requested_count: int,
    max_elements: int,
    font_family: str,
    text_fill: Tuple[int, int, int],
    muted_fill: Tuple[int, int, int],
    box_fill: Tuple[int, int, int],
    box_border: Tuple[int, int, int],
) -> int:
    if int(requested_count) <= 0:
        return 0
    candidates = list(_side_note_candidates(width=int(width), height=int(height), occupied=scene_occupied, rng=rng))
    added = 0
    for candidate in candidates:
        if added >= int(requested_count) or len(elements) + 2 > int(max_elements):
            break
        note_bbox = tuple(float(value) for value in candidate["bbox"])
        if not _bbox_is_safe(note_bbox, occupied, width=int(width), height=int(height), padding_px=8):
            continue
        if _draw_one_side_note(
            draw,
            elements=elements,
            note_bbox=note_bbox,
            side=str(candidate["side"]),
            rng=rng,
            width=int(width),
            height=int(height),
            font_family=str(font_family),
            text_fill=text_fill,
            muted_fill=muted_fill,
            box_fill=box_fill,
            box_border=box_border,
        ):
            occupied.append(note_bbox)
            added += 1
    return int(added)


def _side_note_candidates(
    *,
    width: int,
    height: int,
    occupied: Sequence[BBox],
    rng: random.Random,
) -> tuple[dict[str, Any], ...]:
    if not occupied:
        return tuple()
    margin = max(12, min(22, int(round(min(width, height) * 0.018))))
    gutter = max(8, min(16, int(round(min(width, height) * 0.014))))
    min_x = max(0.0, min(float(box[0]) for box in occupied))
    max_x = min(float(width), max(float(box[2]) for box in occupied))
    top_limit = float(max(margin + 42, int(height * 0.16)))
    note_height = float(min(max(132, int(height * 0.23)), max(140, int(height - (2 * margin) - 96))))
    max_top = float(max(top_limit, height - margin - note_height - 40))
    if max_top > top_limit:
        top = float(rng.randint(int(top_limit), int(max_top)))
    else:
        top = float(max(margin, (height - note_height) * 0.5))
    min_width = max(96, min(126, int(round(width * 0.09))))
    max_note_width = max(min_width, min(238, int(round(width * 0.18))))
    candidates: list[dict[str, Any]] = []

    left_available = int(min_x - float(margin) - float(gutter))
    if left_available >= min_width:
        note_width = min(max_note_width, left_available)
        candidates.append(
            {
                "side": "left",
                "bbox": (
                    float(margin),
                    float(top),
                    float(margin + note_width),
                    float(top + note_height),
                ),
            }
        )

    right_available = int(float(width) - max_x - float(margin) - float(gutter))
    if right_available >= min_width:
        note_width = min(max_note_width, right_available)
        candidates.append(
            {
                "side": "right",
                "bbox": (
                    float(width - margin - note_width),
                    float(top),
                    float(width - margin),
                    float(top + note_height),
                ),
            }
        )

    bottom_available = int(float(height) - max(float(box[3]) for box in occupied) - float(margin) - float(gutter))
    bottom_note_height = max(104, min(150, int(round(height * 0.18))))
    if bottom_available >= bottom_note_height:
        bottom_width = max(260, min(int(round(width * 0.58)), int(width - (2 * margin))))
        bottom_left_min = int(margin)
        bottom_left_max = max(bottom_left_min, int(width - margin - bottom_width))
        bottom_left = float(rng.randint(bottom_left_min, bottom_left_max)) if bottom_left_max > bottom_left_min else float(bottom_left_min)
        bottom_top = float(height - margin - bottom_note_height)
        candidates.append(
            {
                "side": "bottom",
                "bbox": (
                    float(bottom_left),
                    float(bottom_top),
                    float(bottom_left + bottom_width),
                    float(bottom_top + bottom_note_height),
                ),
            }
        )

    rng.shuffle(candidates)
    return tuple(candidates)


def _draw_one_side_note(
    draw: ImageDraw.ImageDraw,
    *,
    elements: list[ContextTextElement],
    note_bbox: BBox,
    side: str,
    rng: random.Random,
    width: int,
    height: int,
    font_family: str,
    text_fill: Tuple[int, int, int],
    muted_fill: Tuple[int, int, int],
    box_fill: Tuple[int, int, int],
    box_border: Tuple[int, int, int],
) -> bool:
    left, top, right, bottom = [float(value) for value in note_bbox]
    inner_pad = max(8, min(12, int(round((right - left) * 0.08))))
    inner_width = max(30, int(right - left - (2 * inner_pad)))
    inner_height = max(40, int(bottom - top - (2 * inner_pad)))
    heading_font = load_font(max(10, min(13, int(round(height * 0.014)))), bold=True, font_family=str(font_family))
    body_font = load_font(max(9, min(12, int(round(height * 0.012)))), bold=False, font_family=str(font_family))
    heading_selection = _sample_context_text_filtered("phrases/callout_phrases.txt", rng=rng, avoid_digits=True)
    body_manifest = "paragraphs/context_template_blocks.txt" if inner_width >= 120 and inner_height >= 120 else "sentences/context_template_sentences.txt"
    body_selection = _sample_context_text_filtered(body_manifest, rng=rng, avoid_digits=True)
    heading_text = _fit_one_line(draw, str(heading_selection.text), font=heading_font, max_width_px=int(inner_width))
    max_body_lines = max(2, min(6, int((inner_height - 28) / 15)))
    body_text = _wrap_text_to_lines(
        draw,
        str(body_selection.text),
        font=body_font,
        max_width_px=int(inner_width),
        max_lines=int(max_body_lines),
    )
    if not heading_text or not body_text:
        return False

    draw.rounded_rectangle(
        tuple(int(round(value)) for value in note_bbox),
        radius=8,
        fill=tuple(int(value) for value in box_fill),
        outline=tuple(int(value) for value in box_border),
        width=1,
    )
    divider_y = float(top + inner_pad + 22)
    draw.line(
        (left + inner_pad, divider_y, right - inner_pad, divider_y),
        fill=tuple(int(value) for value in box_border),
        width=1,
    )

    heading_xy = (float(left + inner_pad), float(top + inner_pad + 1))
    body_xy = (float(left + inner_pad), float(top + inner_pad + 32))
    heading_stroke = resolve_text_stroke_fill(tuple(text_fill))
    body_stroke = resolve_text_stroke_fill(tuple(muted_fill))
    heading_bbox_raw = draw.textbbox(heading_xy, heading_text, font=heading_font, stroke_width=1)
    draw_text_traced(draw,
        heading_xy,
        heading_text,
        font=heading_font,
        fill=tuple(int(value) for value in text_fill),
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in heading_stroke),
     role="readout", required=False,)
    body_bbox_raw = draw.multiline_textbbox(body_xy, body_text, font=body_font, spacing=3, stroke_width=1)
    draw.multiline_text(
        body_xy,
        body_text,
        font=body_font,
        fill=tuple(int(value) for value in muted_fill),
        spacing=3,
        stroke_width=1,
        stroke_fill=tuple(int(value) for value in body_stroke),
    )
    elements.extend(
        [
            ContextTextElement(
                context_id=f"pages_context_{len(elements):02d}",
                role="side_note_heading",
                text=str(heading_text),
                bbox_xyxy=_clip_trace_bbox(heading_bbox_raw, width=int(width), height=int(height)),
                manifest_path=str(heading_selection.manifest_path),
                source_ids=tuple(heading_selection.source_ids),
                row_index=int(heading_selection.row_index),
                layout_mode=f"safe_margin:side_note:{side}",
                font_family=str(font_family),
            ),
            ContextTextElement(
                context_id=f"pages_context_{len(elements) + 1:02d}",
                role="side_note_body",
                text=str(body_text),
                bbox_xyxy=_clip_trace_bbox(body_bbox_raw, width=int(width), height=int(height)),
                manifest_path=str(body_selection.manifest_path),
                source_ids=tuple(body_selection.source_ids),
                row_index=int(body_selection.row_index),
                layout_mode=f"safe_margin:side_note:{side}",
                font_family=str(font_family),
            ),
        ]
    )
    return True


def _sample_context_text_filtered(manifest_path: str, *, rng: random.Random, avoid_digits: bool) -> Any:
    last_selection = None
    for _attempt in range(32):
        selection = sample_context_text(str(manifest_path), rng=rng)
        last_selection = selection
        text = str(selection.text)
        if "$" in text or "€" in text or "£" in text or "¥" in text:
            continue
        if bool(avoid_digits) and any(char.isdigit() for char in text):
            continue
        return selection
    if last_selection is None:
        return sample_context_text(str(manifest_path), rng=rng)
    return last_selection


def _record_context_text_layer(
    trace_payload: MutableMapping[str, Any],
    *,
    elements: Iterable[ContextTextElement],
    enabled: bool,
    layout_mode: str,
    layout_spec: Mapping[str, Any],
) -> None:
    element_tuple = tuple(elements)
    render_spec = trace_payload.setdefault("render_spec", {})
    if isinstance(render_spec, MutableMapping):
        render_spec["context_text_layer"] = context_text_layer_metadata(
            element_tuple,
            enabled=bool(enabled),
            layout_mode=str(layout_mode),
            layout_spec=dict(layout_spec),
        )
    render_map = trace_payload.setdefault("render_map", {})
    if isinstance(render_map, MutableMapping):
        render_map["context_text_bboxes_px"] = {
            str(element.context_id): [int(value) for value in element.bbox_xyxy]
            for element in element_tuple
        }


def _context_candidates(width: int, height: int) -> tuple[dict[str, Any], ...]:
    margin = max(10, min(18, int(round(min(width, height) * 0.018))))
    return (
        {
            "role": "header",
            "manifest_path": "phrases/headlines.txt",
            "slot": "top_left",
            "font_size_px": max(11, min(15, int(round(height * 0.016)))),
            "bold": True,
            "margin_px": margin,
            "max_width_px": max(180, int(width * 0.36)),
        },
        {
            "role": "source_note",
            "manifest_path": "phrases/source_notes.txt",
            "slot": "top_center",
            "font_size_px": max(10, min(13, int(round(height * 0.014)))),
            "bold": False,
            "margin_px": margin,
            "max_width_px": max(160, int(width * 0.28)),
        },
        {
            "role": "source_note",
            "manifest_path": "phrases/source_notes.txt",
            "slot": "top_right",
            "font_size_px": max(10, min(13, int(round(height * 0.014)))),
            "bold": False,
            "margin_px": margin,
            "max_width_px": max(180, int(width * 0.36)),
        },
        {
            "role": "footer",
            "manifest_path": "phrases/footers.txt",
            "slot": "bottom_left",
            "font_size_px": max(10, min(13, int(round(height * 0.014)))),
            "bold": False,
            "margin_px": margin,
            "max_width_px": max(220, int(width * 0.44)),
        },
        {
            "role": "caption",
            "manifest_path": "phrases/captions.txt",
            "slot": "bottom_center",
            "font_size_px": max(10, min(13, int(round(height * 0.014)))),
            "bold": False,
            "margin_px": margin,
            "max_width_px": max(160, int(width * 0.28)),
        },
        {
            "role": "caption",
            "manifest_path": "phrases/captions.txt",
            "slot": "bottom_right",
            "font_size_px": max(10, min(13, int(round(height * 0.014)))),
            "bold": False,
            "margin_px": margin,
            "max_width_px": max(180, int(width * 0.36)),
        },
    )


def _select_candidate_order(candidates: Sequence[dict[str, Any]], *, rng: random.Random) -> tuple[dict[str, Any], ...]:
    ordered = list(candidates)
    rng.shuffle(ordered)
    ordered.sort(key=lambda item: 0 if str(item["role"]) in {"header", "footer"} else 1)
    return tuple(ordered)


def _fit_one_line(draw: ImageDraw.ImageDraw, text: str, *, font: Any, max_width_px: int) -> str:
    raw = " ".join(str(text).split())
    if not raw:
        return ""
    if draw.textbbox((0, 0), raw, font=font, stroke_width=1)[2] <= int(max_width_px):
        return raw
    ellipsis = "..."
    words = raw.split()
    fitted = ""
    for word in words:
        candidate = f"{fitted} {word}".strip()
        if draw.textbbox((0, 0), f"{candidate}{ellipsis}", font=font, stroke_width=1)[2] > int(max_width_px):
            break
        fitted = candidate
    if fitted:
        return f"{fitted}{ellipsis}"
    chars: list[str] = []
    for char in raw:
        candidate = "".join(chars) + char
        if draw.textbbox((0, 0), f"{candidate}{ellipsis}", font=font, stroke_width=1)[2] > int(max_width_px):
            break
        chars.append(char)
    return f"{''.join(chars).strip()}{ellipsis}" if chars else ""


def _wrap_text_to_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    font: Any,
    max_width_px: int,
    max_lines: int,
) -> str:
    words = " ".join(str(text).split()).split()
    if not words:
        return ""
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font, stroke_width=1)[2] <= int(max_width_px):
            current = candidate
            continue
        if current:
            lines.append(current)
        current = str(word)
        if len(lines) >= max(1, int(max_lines)):
            break
    if current and len(lines) < max(1, int(max_lines)):
        lines.append(current)
    if not lines:
        return ""
    if len(lines) >= max(1, int(max_lines)):
        last = lines[-1]
        ellipsis = "..."
        while last and draw.textbbox((0, 0), f"{last}{ellipsis}", font=font, stroke_width=1)[2] > int(max_width_px):
            last = " ".join(last.split()[:-1])
        lines[-1] = f"{last}{ellipsis}" if last else ellipsis
    return "\n".join(lines)


def _clip_trace_bbox(bbox: Sequence[float], *, width: int, height: int) -> Tuple[int, int, int, int]:
    x0, y0, x1, y1 = [int(round(float(value))) for value in bbox[:4]]
    clipped_x0 = min(max(0, x0), max(0, int(width) - 1))
    clipped_y0 = min(max(0, y0), max(0, int(height) - 1))
    clipped_x1 = min(max(clipped_x0 + 1, x1), int(width))
    clipped_y1 = min(max(clipped_y0 + 1, y1), int(height))
    return (int(clipped_x0), int(clipped_y0), int(clipped_x1), int(clipped_y1))


def _candidate_bbox(
    draw: ImageDraw.ImageDraw,
    *,
    text: str,
    font: Any,
    slot: str,
    width: int,
    height: int,
    margin_px: int,
) -> BBox:
    bbox = draw.textbbox((0, 0), str(text), font=font, stroke_width=1)
    text_width = float(bbox[2] - bbox[0])
    text_height = float(bbox[3] - bbox[1])
    margin = float(margin_px)
    if str(slot) == "top_right":
        left = float(width) - margin - text_width
        top = margin
    elif str(slot) == "top_center":
        left = (float(width) - text_width) * 0.5
        top = margin
    elif str(slot) == "bottom_left":
        left = margin
        top = float(height) - margin - text_height
    elif str(slot) == "bottom_center":
        left = (float(width) - text_width) * 0.5
        top = float(height) - margin - text_height
    elif str(slot) == "bottom_right":
        left = float(width) - margin - text_width
        top = float(height) - margin - text_height
    else:
        left = margin
        top = margin
    return (
        float(left),
        float(top),
        float(left + text_width),
        float(top + text_height),
    )


def _collect_occupied_bboxes(trace_payload: Mapping[str, Any]) -> list[BBox]:
    render_map = trace_payload.get("render_map", {})
    boxes: list[BBox] = []
    if isinstance(render_map, Mapping):
        for key in ("scene_bbox_px", "page_bbox_px", "calendar_panel_bbox_px"):
            value = render_map.get(key)
            if _looks_like_bbox(value):
                boxes.append(tuple(float(item) for item in value[:4]))  # type: ignore[index]

    scene_ir = trace_payload.get("scene_ir", {})
    entities = scene_ir.get("entities", []) if isinstance(scene_ir, Mapping) else []
    if not isinstance(entities, Sequence):
        return boxes
    for entity in entities:
        if not isinstance(entity, Mapping):
            continue
        for key in ("bbox_px", "bbox_xyxy"):
            value = entity.get(key)
            if _looks_like_bbox(value):
                boxes.append(tuple(float(item) for item in value[:4]))  # type: ignore[index]
    return boxes


def _looks_like_bbox(value: Any) -> bool:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) < 4:
        return False
    try:
        x0, y0, x1, y1 = [float(item) for item in value[:4]]
    except Exception:
        return False
    return x1 > x0 and y1 > y0


def _bbox_is_safe(
    bbox: BBox,
    occupied: Sequence[BBox],
    *,
    width: int,
    height: int,
    padding_px: int,
) -> bool:
    x0, y0, x1, y1 = [float(value) for value in bbox]
    if x0 < 0 or y0 < 0 or x1 > float(width) or y1 > float(height):
        return False
    padded = (
        float(x0 - padding_px),
        float(y0 - padding_px),
        float(x1 + padding_px),
        float(y1 + padding_px),
    )
    return not any(_bboxes_overlap(padded, box) for box in occupied)


def _bboxes_overlap(left: BBox, right: BBox) -> bool:
    return not (
        float(left[2]) <= float(right[0])
        or float(left[0]) >= float(right[2])
        or float(left[3]) <= float(right[1])
        or float(left[1]) >= float(right[3])
    )


def _coerce_rgb(value: Any, *, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) >= 3:
        try:
            return tuple(max(0, min(255, int(channel))) for channel in value[:3])  # type: ignore[return-value]
        except Exception:
            return tuple(int(channel) for channel in fallback)
    return tuple(int(channel) for channel in fallback)


__all__ = [
    "add_pages_safe_context_text",
    "annotate_pages_font_assets",
    "resolve_pages_default_font_family",
    "wrap_pages_generation",
]
