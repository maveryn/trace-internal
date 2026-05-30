"""Shared illustration odd-scene option task."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import create_task, register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import PROMPT_OUTPUT_MODES, build_prompt_trace_artifacts, render_task_prompt_variants
from ..shared.visual_task_common import SOURCE_SCENE_BY_TASK, bbox_list, draw_label_badge, fit_source_image, sample_visual_label_font_trace


TASK_ID = "task_illustrations__scene_options__odd_scene_label"
SCENE_ID = "scene_options"
QUERY_ID = "odd_scene_label"
OPTION_LABELS: Tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
DEFAULT_SOURCE_QUERIES: Mapping[str, Mapping[str, Any]] = {
    "environment_road": {
        "source_task_id": "task_illustrations__environment__feature_relation_count",
        "source_query_params": {"query_id": "on_feature_object_count", "theme_id": "park_road", "feature_type": "road"},
        "count_phrase": "objects on the road",
    },
    "environment_river": {
        "source_task_id": "task_illustrations__environment__feature_relation_count",
        "source_query_params": {"query_id": "on_feature_object_count", "theme_id": "river_meadow", "feature_type": "river"},
        "count_phrase": "objects in or on the river",
    },
    "park_sitting": {
        "source_task_id": "task_illustrations__park_playground__person_count",
        "source_query_params": {"query_id": "sitting_person_count"},
        "count_phrase": "people sitting",
    },
    "park_walking": {
        "source_task_id": "task_illustrations__park_playground__person_count",
        "source_query_params": {"query_id": "walking_person_count"},
        "count_phrase": "people walking",
    },
    "park_standing": {
        "source_task_id": "task_illustrations__park_playground__person_count",
        "source_query_params": {"query_id": "standing_person_count"},
        "count_phrase": "people standing",
    },
    "construction_tools": {
        "source_task_id": "task_illustrations__construction_site__worker_attribute_count",
        "source_query_params": {"query_id": "tool_holding_worker_count"},
        "count_phrase": "workers holding tools",
    },
}
DEFAULT_COUNT_PAIRS: Tuple[Tuple[int, int], ...] = ((2, 3), (3, 2), (3, 4), (4, 3), (4, 5), (5, 4), (5, 6))
OPTION_FRAME_STYLES: Dict[str, Dict[str, Any]] = {
    "slate_grid": {
        "canvas_rgb": (238, 241, 245),
        "panel_outline_rgb": (66, 73, 84),
        "badge_fill_rgb": (255, 255, 255),
        "badge_outline_rgb": (43, 50, 60),
    },
    "warm_grid": {
        "canvas_rgb": (244, 240, 232),
        "panel_outline_rgb": (82, 68, 54),
        "badge_fill_rgb": (255, 252, 244),
        "badge_outline_rgb": (82, 68, 54),
    },
    "cool_grid": {
        "canvas_rgb": (235, 242, 244),
        "panel_outline_rgb": (42, 70, 83),
        "badge_fill_rgb": (249, 253, 254),
        "badge_outline_rgb": (42, 70, 83),
    },
}


@dataclass(frozen=True)
class _Defaults:
    option_count: int = 6
    panel_width: int = 300
    panel_height: int = 196
    render_margin: int = 26
    panel_gap: int = 22


@dataclass(frozen=True)
class _SourceQuery:
    key: str
    source_task_id: str
    source_query_params: Dict[str, Any]
    count_phrase: str


@dataclass(frozen=True)
class _SampleSpec:
    correct_index: int
    option_count: int
    source_query: _SourceQuery
    common_count: int
    odd_count: int
    correct_index_probabilities: Dict[str, float]
    source_query_probabilities: Dict[str, float]
    count_pair_probabilities: Dict[str, float]


_DEFAULTS = _Defaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "visual")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _uniform_string_probabilities(values: Sequence[str], *, selected: str | None = None) -> Dict[str, float]:
    support = tuple(str(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        return {str(selected): 1.0}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def _source_query_support(params: Mapping[str, Any]) -> Tuple[_SourceQuery, ...]:
    raw = params.get("source_query_support", group_default(_GEN_DEFAULTS, "source_query_support", tuple(DEFAULT_SOURCE_QUERIES)))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("source_query_support must be a sequence")
    queries: list[_SourceQuery] = []
    for value in raw:
        key = str(value)
        if key not in DEFAULT_SOURCE_QUERIES:
            raise ValueError(f"unsupported source_query key {key!r}")
        spec = DEFAULT_SOURCE_QUERIES[key]
        queries.append(
            _SourceQuery(
                key=key,
                source_task_id=str(spec["source_task_id"]),
                source_query_params=dict(spec["source_query_params"]),
                count_phrase=str(spec["count_phrase"]),
            )
        )
    seen_keys: set[str] = set()
    queries = [query for query in queries if not (query.key in seen_keys or seen_keys.add(query.key))]
    if not queries:
        raise ValueError("source_query_support resolved no source queries")
    return tuple(queries)


def _count_pair_support(params: Mapping[str, Any]) -> Tuple[Tuple[int, int], ...]:
    raw = params.get("count_pair_support", group_default(_GEN_DEFAULTS, "count_pair_support", DEFAULT_COUNT_PAIRS))
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise ValueError("count_pair_support must be a sequence")
    pairs: list[Tuple[int, int]] = []
    for value in raw:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
            raise ValueError("each count_pair_support entry must contain two integer counts")
        common_count, odd_count = int(value[0]), int(value[1])
        if common_count < 1 or odd_count < 1 or common_count == odd_count:
            raise ValueError("count_pair_support counts must be positive and different")
        pairs.append((common_count, odd_count))
    if not pairs:
        raise ValueError("count_pair_support resolved no valid count pairs")
    return tuple(dict.fromkeys(pairs))


def _sample_spec(*, params: Mapping[str, Any], instance_seed: int) -> _SampleSpec:
    source_queries = _source_query_support(params)
    count_pairs = _count_pair_support(params)
    option_count = int(params.get("option_count", group_default(_GEN_DEFAULTS, "option_count", _DEFAULTS.option_count)))
    option_count = max(3, min(len(OPTION_LABELS), int(option_count)))

    explicit_index = params.get("correct_option_index")
    if explicit_index is not None:
        correct_index = int(explicit_index)
        if correct_index < 0 or correct_index >= option_count:
            raise ValueError("correct_option_index outside option range")
        index_probs = {str(correct_index): 1.0}
    else:
        raw_index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:correct_option")
        correct_index = int(raw_index) % int(option_count)
        index_probs = {str(index): 1.0 / float(option_count) for index in range(option_count)}

    explicit_source = params.get("source_query_key")
    if explicit_source is not None:
        selected_key = str(explicit_source)
        matching = tuple(query for query in source_queries if query.key == selected_key)
        if not matching:
            raise ValueError(f"source_query_key must be one of {[query.key for query in source_queries]}")
        source_query = matching[0]
        source_query_probs = {selected_key: 1.0}
    else:
        raw_source = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:source_query")
        source_query = source_queries[int(raw_source) % len(source_queries)]
        source_query_probs = _uniform_string_probabilities(tuple(query.key for query in source_queries))

    explicit_common = params.get("common_count")
    explicit_odd = params.get("odd_count")
    if explicit_common is not None or explicit_odd is not None:
        if explicit_common is None or explicit_odd is None:
            raise ValueError("common_count and odd_count must be provided together")
        common_count, odd_count = int(explicit_common), int(explicit_odd)
        if common_count < 1 or odd_count < 1 or common_count == odd_count:
            raise ValueError("common_count and odd_count must be positive and different")
        count_pair_probs = {f"{common_count}->{odd_count}": 1.0}
    else:
        raw_pair = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:count_pair")
        common_count, odd_count = count_pairs[int(raw_pair) % len(count_pairs)]
        pair_probability = 1.0 / float(len(count_pairs))
        count_pair_probs = {f"{common}->{odd}": pair_probability for common, odd in count_pairs}

    return _SampleSpec(
        correct_index=int(correct_index),
        option_count=int(option_count),
        source_query=source_query,
        common_count=int(common_count),
        odd_count=int(odd_count),
        correct_index_probabilities=dict(index_probs),
        source_query_probabilities=dict(source_query_probs),
        count_pair_probabilities=dict(count_pair_probs),
    )


def _panel_size(params: Mapping[str, Any]) -> Tuple[int, int]:
    width = int(params.get("panel_width", group_default(_RENDER_DEFAULTS, "panel_width", _DEFAULTS.panel_width)))
    height = int(params.get("panel_height", group_default(_RENDER_DEFAULTS, "panel_height", _DEFAULTS.panel_height)))
    if width < 120 or height < 80:
        raise ValueError("panel_width/panel_height too small")
    return int(width), int(height)


def _render_panel(
    *,
    source_query: _SourceQuery,
    target_count: int,
    panel_index: int,
    instance_seed: int,
    params: Mapping[str, Any],
    max_attempts: int,
) -> Tuple[Image.Image, Dict[str, Any]]:
    seed_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:panel_seed:{source_query.key}:{int(panel_index)}:{int(target_count)}")
    panel_seed = int(seed_rng.randint(0, 2**63 - 1))
    source_params: Dict[str, Any] = {**dict(source_query.source_query_params), "target_count": int(target_count)}
    out = create_task(str(source_query.source_task_id)).generate(
        panel_seed,
        params=source_params,
        max_attempts=max(20, int(max_attempts)),
    )
    return out.image.convert("RGB"), {
        "source_task_id": str(source_query.source_task_id),
        "source_scene_id": str(SOURCE_SCENE_BY_TASK.get(str(source_query.source_task_id), out.scene_id)),
        "source_trace_ref": dict(out.trace_payload).get("trace_ref"),
    }


def _rgb(style: Mapping[str, Any], key: str) -> Tuple[int, int, int]:
    value = style[key]
    return (int(value[0]), int(value[1]), int(value[2]))


def _sample_option_frame_style(rng) -> Dict[str, Any]:
    style_id = str(rng.choice(tuple(OPTION_FRAME_STYLES)))
    return {"style_id": style_id, **dict(OPTION_FRAME_STYLES[style_id])}


def _compose_options(
    *,
    panels: Sequence[Image.Image],
    labels: Sequence[str],
    params: Mapping[str, Any],
    frame_style: Mapping[str, Any],
    label_font_family: str,
) -> Tuple[Image.Image, Dict[str, list[float]]]:
    panel_w, panel_h = _panel_size(params)
    margin = int(params.get("render_margin", group_default(_RENDER_DEFAULTS, "render_margin", _DEFAULTS.render_margin)))
    gap = int(params.get("panel_gap", group_default(_RENDER_DEFAULTS, "panel_gap", _DEFAULTS.panel_gap)))
    columns = 3
    rows = (len(panels) + columns - 1) // columns
    full_w = 2 * margin + columns * panel_w + (columns - 1) * gap
    full_h = 2 * margin + rows * panel_h + (rows - 1) * gap
    canvas = Image.new("RGB", (int(full_w), int(full_h)), _rgb(frame_style, "canvas_rgb"))
    draw = ImageDraw.Draw(canvas)
    panel_bboxes: Dict[str, list[float]] = {}
    for index, panel in enumerate(panels):
        row = index // columns
        col = index % columns
        x = int(margin + col * (panel_w + gap))
        y = int(margin + row * (panel_h + gap))
        thumb = fit_source_image(panel, width=panel_w, height=panel_h)
        canvas.paste(thumb, (x, y))
        draw.rectangle((x, y, x + panel_w, y + panel_h), outline=_rgb(frame_style, "panel_outline_rgb"), width=2)
        label = str(labels[index])
        draw_label_badge(
            draw,
            label,
            (x + 8, y + 8, x + 44, y + 36),
            font_family=label_font_family,
            fill=_rgb(frame_style, "badge_fill_rgb"),
            outline=_rgb(frame_style, "badge_outline_rgb"),
        )
        panel_bboxes[label] = bbox_list((x, y, x + panel_w, y + panel_h))
    return canvas, panel_bboxes


def _build_complexity(sample: _SampleSpec) -> TaskComplexity:
    panel_count_load = (int(sample.option_count) - 3) / max(1.0, float(len(OPTION_LABELS) - 3))
    same_panel_fraction = (int(sample.option_count) - 1) / max(1.0, float(sample.option_count))
    return TaskComplexity(
        complexity_score=0.66,
        complexity_components={
            "panel_count_load": round(float(panel_count_load), 6),
            "same_panel_fraction": round(float(same_panel_fraction), 6),
            "odd_panel_fraction": round(float(1.0 / max(1.0, float(sample.option_count))), 6),
            "visual_scan_load": 1.0,
        },
    )


@register_task
class IllustrationsVisualOddSceneLabelTask:
    """Choose the one panel with a different named count than the other panels."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "visual"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        sample = _sample_spec(params=params, instance_seed=int(instance_seed))
        option_count = int(sample.option_count)
        labels = OPTION_LABELS[:option_count]
        same_scene_count = int(option_count) - 1
        style_rng = spawn_rng(int(instance_seed), f"{TASK_ID}:style")
        frame_style = _sample_option_frame_style(style_rng)
        label_font = sample_visual_label_font_trace(
            task_id=TASK_ID,
            instance_seed=int(instance_seed),
            params=params,
            namespace_suffix="option_label_font",
            explicit_key="scene_options_label_font_family",
            weights_key="scene_options_label_font_family_weights",
        )
        panels: list[Image.Image] = []
        panel_sources: list[Dict[str, Any]] = []
        for index in range(option_count):
            target_count = int(sample.odd_count) if int(index) == int(sample.correct_index) else int(sample.common_count)
            panel, source_info = _render_panel(
                source_query=sample.source_query,
                target_count=int(target_count),
                panel_index=int(index),
                instance_seed=int(instance_seed),
                params=params,
                max_attempts=max_attempts,
            )
            panels.append(panel)
            source_info = dict(source_info)
            source_info["role"] = "odd" if int(index) == int(sample.correct_index) else "majority"
            source_info["panel_target_count"] = int(target_count)
            panel_sources.append(source_info)

        image, panel_bboxes = _compose_options(
            panels=panels,
            labels=labels,
            params=params,
            frame_style=frame_style,
            label_font_family=str(label_font["font_family"]),
        )
        answer_label = str(labels[int(sample.correct_index)])
        evidence_boxes = [panel_bboxes[answer_label]]

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_odd_scene_label",
                "evidence_hint_odd_scene_label",
                "json_example_odd_scene_label",
                "json_example_answer_only_odd_scene_label",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        slots = {
            "option_labels": ", ".join(labels),
            "option_count": str(option_count),
            "same_scene_count": str(same_scene_count),
            "count_phrase": str(sample.source_query.count_phrase),
            "json_output_contract": str(prompt_defaults["json_output_contract"]),
            "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
            "answer_hint": str(prompt_defaults["answer_hint_odd_scene_label"]).format(option_labels=", ".join(labels)),
            "evidence_hint": str(prompt_defaults["evidence_hint_odd_scene_label"]),
            "json_example": str(prompt_defaults["json_example_odd_scene_label"]),
            "json_example_answer_only": str(prompt_defaults["json_example_answer_only_odd_scene_label"]),
        }
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=QUERY_ID,
            slots=slots,
            instance_seed=int(instance_seed),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            preferred_mode="answer_and_evidence",
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)
        option_records = [
            {
                "label": str(labels[index]),
                "bbox": panel_bboxes[str(labels[index])],
                "source_task_id": str(panel_sources[index]["source_task_id"]),
                "source_scene_id": str(panel_sources[index]["source_scene_id"]),
                "role": str(panel_sources[index]["role"]),
                "target_count": int(panel_sources[index]["panel_target_count"]),
            }
            for index in range(option_count)
        ]
        trace_payload = {
            "scene_ir": {
                "domain": self.domain,
                "scene_id": SCENE_ID,
                "entities": {
                    "options": list(option_records),
                    "source_query_key": str(sample.source_query.key),
                    "source_task_id": str(sample.source_query.source_task_id),
                    "source_scene_id": str(SOURCE_SCENE_BY_TASK.get(str(sample.source_query.source_task_id), "")),
                    "count_phrase": str(sample.source_query.count_phrase),
                },
                "relations": {
                    "query_id": QUERY_ID,
                    "common_count": int(sample.common_count),
                    "odd_count": int(sample.odd_count),
                },
            },
            "query_spec": {
                "task_id": self.task_id,
                "query_id": QUERY_ID,
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "option_count": int(option_count),
                    "correct_option_index": int(sample.correct_index),
                    "correct_label": str(answer_label),
                    "source_query_key": str(sample.source_query.key),
                    "source_task_id": str(sample.source_query.source_task_id),
                    "source_query_params": dict(sample.source_query.source_query_params),
                    "count_phrase": str(sample.source_query.count_phrase),
                    "common_count": int(sample.common_count),
                    "odd_count": int(sample.odd_count),
                    "correct_index_probabilities": dict(sample.correct_index_probabilities),
                    "source_query_probabilities": dict(sample.source_query_probabilities),
                    "count_pair_probabilities": dict(sample.count_pair_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": [int(image.width), int(image.height)],
                "coord_space": "pixel",
                "scene_id": SCENE_ID,
                "style": {
                    "panel_grid": [int((option_count + 2) // 3), 3],
                    "panel_size": list(_panel_size(params)),
                    "frame_style": dict(frame_style),
                    "option_label_font": dict(label_font),
                },
            },
            "render_map": {
                "option_bboxes_px": dict(panel_bboxes),
                "correct_option_label": str(answer_label),
                "option_sources": list(option_records),
            },
            "execution_trace": {
                "query_id": QUERY_ID,
                "answer": str(answer_label),
                "correct_option_label": str(answer_label),
                "source_query_key": str(sample.source_query.key),
                "common_count": int(sample.common_count),
                "odd_count": int(sample.odd_count),
            },
            "witness_symbolic": {
                "answer": str(answer_label),
                "correct_option_label": str(answer_label),
                "odd_panel_target_count": int(sample.odd_count),
                "common_panel_target_count": int(sample.common_count),
            },
            "projected_evidence": {"bbox_set": list(evidence_boxes)},
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="option_letter", value=str(answer_label)),
            evidence_gt=TypedValue(type="bbox_set", value=list(evidence_boxes)),
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=_build_complexity(sample),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=QUERY_ID,
        )


__all__ = ["IllustrationsVisualOddSceneLabelTask"]
