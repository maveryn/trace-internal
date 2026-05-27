"""Games rhythm-lanes tasks over falling notes and hit timing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.support_sampling import resolve_integer_choice
from ..shared.complexity import build_games_rhythm_lanes_complexity
from ..shared.fixed_query_task import rewrite_public_query_output
from ..shared.layout import resolve_games_layout_jitter
from ..shared.rhythm_common import (
    SUPPORTED_RHYTHM_COLOR_KEYS,
    SUPPORTED_RHYTHM_QUERY_IDS,
    SUPPORTED_RHYTHM_SCENE_VARIANTS,
    SUPPORTED_RHYTHM_STYLE_VARIANTS,
    RhythmNote,
    RhythmSample,
    lane_label,
    note_entity_id,
    occupied_cells,
    validate_rhythm_sample,
)
from ..shared.rhythm_scene import RhythmRenderParams, render_rhythm_lanes_scene
from ..shared.sampling import resolve_games_named_axis, resolve_games_query_id
from ..shared.visual_defaults import load_games_background_defaults, load_games_noise_defaults


TASK_ID = "games_rhythm_lanes_base"
COUNT_QUERY_IDS: Tuple[str, ...] = ("lane_hit_count", "lane_color_hit_count")
LANE_CHOICE_QUERY_IDS: Tuple[str, ...] = ("most_hits_lane_label", "earliest_hit_lane_label")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for visible rhythm-lanes scenes."""

    lane_count_support: Tuple[int, ...] = (5, 6, 7, 8)
    row_count_support: Tuple[int, ...] = (10, 11, 12, 13, 14)
    beat_window_support: Tuple[int, ...] = (5, 6, 7)
    hit_count_support: Tuple[int, ...] = (1, 2, 3, 4, 5)
    canvas_width: int = 760
    canvas_height: int = 900
    panel_margin_px: int = 42
    grid_width_px: int = 650
    grid_height_px: int = 790
    grid_border_width_px: int = 5
    row_gap_px: int = 4
    lane_gap_px: int = 9
    note_radius_px: int = 13
    label_font_size_px: int = 25


@dataclass(frozen=True)
class _ResolvedAxes:
    """Resolved semantic and visual axes for one rhythm instance."""

    query_id: str
    scene_variant: str
    style_variant: str
    lane_count: int
    row_count: int
    beat_window: int
    target_hit_count: int
    query_id_probabilities: Dict[str, float]
    scene_variant_probabilities: Dict[str, float]
    style_variant_probabilities: Dict[str, float]
    lane_count_probabilities: Dict[str, float]
    row_count_probabilities: Dict[str, float]
    beat_window_probabilities: Dict[str, float]
    target_hit_count_probabilities: Dict[str, float]


class _NoteBuilder:
    """Mutable helper that places non-overlapping rhythm notes."""

    def __init__(self, *, lane_count: int, row_count: int, rng) -> None:
        self.lane_count = int(lane_count)
        self.row_count = int(row_count)
        self.rng = rng
        self.notes: list[RhythmNote] = []
        self.occupied: dict[int, set[int]] = {lane: set() for lane in range(int(lane_count))}

    def can_place(self, *, lane: int, bottom_row: int, length: int) -> bool:
        if not (0 <= int(lane) < int(self.lane_count)):
            return False
        if int(bottom_row) < 1 or int(length) < 1:
            return False
        if int(bottom_row) + int(length) - 1 > int(self.row_count):
            return False
        rows = set(range(int(bottom_row), int(bottom_row) + int(length)))
        return not bool(rows & self.occupied[int(lane)])

    def add_note(self, *, lane: int, bottom_row: int, length: int, color_key: str, kind: str | None = None) -> RhythmNote:
        if not self.can_place(lane=int(lane), bottom_row=int(bottom_row), length=int(length)):
            raise ValueError("cannot place rhythm note")
        note = RhythmNote(
            note_id=note_entity_id(len(self.notes)),
            lane_index=int(lane),
            bottom_row=int(bottom_row),
            length=int(length),
            color_key=str(color_key),
            kind=str(kind or ("hold" if int(length) > 1 else "tap")),
        )
        for row in occupied_cells(note):
            self.occupied[int(lane)].add(int(row))
        self.notes.append(note)
        return note

    def add_random_note(
        self,
        *,
        lanes: Sequence[int],
        bottom_rows: Sequence[int],
        colors: Sequence[str],
        lengths: Sequence[int] = (1, 1, 1, 2, 2, 3),
    ) -> RhythmNote | None:
        lane_values = [int(lane) for lane in lanes if 0 <= int(lane) < int(self.lane_count)]
        row_values = [int(row) for row in bottom_rows if 1 <= int(row) <= int(self.row_count)]
        color_values = [str(color) for color in colors if str(color) in SUPPORTED_RHYTHM_COLOR_KEYS]
        length_values = [max(1, int(length)) for length in lengths]
        self.rng.shuffle(lane_values)
        self.rng.shuffle(row_values)
        self.rng.shuffle(color_values)
        self.rng.shuffle(length_values)
        for lane in lane_values:
            for row in row_values:
                for length in length_values:
                    if not self.can_place(lane=int(lane), bottom_row=int(row), length=int(length)):
                        continue
                    color = str(color_values[0] if color_values else self.rng.choice(SUPPORTED_RHYTHM_COLOR_KEYS))
                    return self.add_note(lane=int(lane), bottom_row=int(row), length=int(length), color_key=color)
        return None


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("games", "rhythm")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_games_background_defaults(task_group="rhythm")
POST_IMAGE_NOISE_DEFAULTS = load_games_noise_defaults(task_group="rhythm", apply_prob=0.5)


def _resolve_query_id(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced rhythm query id."""

    return resolve_games_query_id(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        supported_variants=tuple(str(value) for value in supported_query_ids),
    )


def _resolve_named_axis(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Sequence[str],
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced named rhythm axis."""

    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace=str(namespace),
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported_variants=[str(value) for value in supported],
    )


def _resolve_axes(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    supported_query_ids: Sequence[str],
) -> _ResolvedAxes:
    """Resolve all semantic and visual axes for one rhythm instance."""

    query_id, query_id_probabilities = _resolve_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=supported_query_ids,
    )
    scene_variant, scene_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="scene_variant",
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        supported=SUPPORTED_RHYTHM_SCENE_VARIANTS,
    )
    style_variant, style_variant_probabilities = _resolve_named_axis(
        instance_seed=int(instance_seed),
        params=params,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported=SUPPORTED_RHYTHM_STYLE_VARIANTS,
    )
    lane_count, lane_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="lane_count_support",
        explicit_key="lane_count",
        fallback_support=_DEFAULTS.lane_count_support,
        namespace=f"{TASK_ID}.lane_count",
        balanced_flag_key="balanced_lane_count_sampling",
        namespace_support_permutation=True,
    )
    row_count, row_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="row_count_support",
        explicit_key="row_count",
        fallback_support=_DEFAULTS.row_count_support,
        namespace=f"{TASK_ID}.row_count",
        balanced_flag_key="balanced_row_count_sampling",
        namespace_support_permutation=True,
    )
    beat_window, beat_window_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="beat_window_support",
        explicit_key="beat_window",
        fallback_support=_DEFAULTS.beat_window_support,
        namespace=f"{TASK_ID}.beat_window",
        balanced_flag_key="balanced_beat_window_sampling",
        namespace_support_permutation=True,
    )
    target_hit_count, target_hit_count_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="hit_count_support",
        explicit_key="target_hit_count",
        fallback_support=_DEFAULTS.hit_count_support,
        namespace=f"{TASK_ID}.target_hit_count",
        balanced_flag_key="balanced_hit_count_sampling",
        namespace_support_permutation=True,
    )
    if int(beat_window) > int(row_count):
        raise ValueError("beat_window cannot exceed row_count")
    if int(target_hit_count) > int(beat_window):
        raise ValueError("target_hit_count cannot exceed beat_window")
    return _ResolvedAxes(
        query_id=str(query_id),
        scene_variant=str(scene_variant),
        style_variant=str(style_variant),
        lane_count=int(lane_count),
        row_count=int(row_count),
        beat_window=int(beat_window),
        target_hit_count=int(target_hit_count),
        query_id_probabilities=dict(query_id_probabilities),
        scene_variant_probabilities=dict(scene_variant_probabilities),
        style_variant_probabilities=dict(style_variant_probabilities),
        lane_count_probabilities=dict(lane_count_probabilities),
        row_count_probabilities=dict(row_count_probabilities),
        beat_window_probabilities=dict(beat_window_probabilities),
        target_hit_count_probabilities=dict(target_hit_count_probabilities),
    )


def _render_params(params: Mapping[str, Any], *, instance_seed: int) -> RhythmRenderParams:
    """Resolve rhythm rendering parameters from config/defaults."""

    return RhythmRenderParams(
        canvas_width=int(params.get("canvas_width", group_default(_RENDER_DEFAULTS, "canvas_width", _DEFAULTS.canvas_width))),
        canvas_height=int(params.get("canvas_height", group_default(_RENDER_DEFAULTS, "canvas_height", _DEFAULTS.canvas_height))),
        panel_margin_px=int(params.get("panel_margin_px", group_default(_RENDER_DEFAULTS, "panel_margin_px", _DEFAULTS.panel_margin_px))),
        grid_width_px=int(params.get("grid_width_px", group_default(_RENDER_DEFAULTS, "grid_width_px", _DEFAULTS.grid_width_px))),
        grid_height_px=int(params.get("grid_height_px", group_default(_RENDER_DEFAULTS, "grid_height_px", _DEFAULTS.grid_height_px))),
        grid_border_width_px=int(params.get("grid_border_width_px", group_default(_RENDER_DEFAULTS, "grid_border_width_px", _DEFAULTS.grid_border_width_px))),
        row_gap_px=int(params.get("row_gap_px", group_default(_RENDER_DEFAULTS, "row_gap_px", _DEFAULTS.row_gap_px))),
        lane_gap_px=int(params.get("lane_gap_px", group_default(_RENDER_DEFAULTS, "lane_gap_px", _DEFAULTS.lane_gap_px))),
        note_radius_px=int(params.get("note_radius_px", group_default(_RENDER_DEFAULTS, "note_radius_px", _DEFAULTS.note_radius_px))),
        label_font_size_px=int(params.get("label_font_size_px", group_default(_RENDER_DEFAULTS, "label_font_size_px", _DEFAULTS.label_font_size_px))),
        layout_jitter_meta=resolve_games_layout_jitter(
            params,
            _RENDER_DEFAULTS,
            instance_seed=int(instance_seed),
            namespace="games.rhythm.layout",
        ),
    )


def _select_lane(*, rng, lane_count: int, params: Mapping[str, Any], key: str = "selected_lane_index") -> int:
    """Select a lane, honoring a zero-based explicit lane index."""

    explicit = params.get(str(key), params.get("target_lane_index"))
    if explicit is not None:
        lane = int(explicit)
        if not (0 <= int(lane) < int(lane_count)):
            raise ValueError(f"{key} out of range")
        return int(lane)
    return int(rng.randrange(int(lane_count)))


def _target_color(*, rng, params: Mapping[str, Any]) -> str:
    """Select the color to query for color-filtered counting."""

    explicit = params.get("target_color_key", params.get("target_color"))
    if explicit is not None:
        color = str(explicit)
        if color not in SUPPORTED_RHYTHM_COLOR_KEYS:
            raise ValueError(f"unsupported target_color_key: {color}")
        return color
    return str(rng.choice(SUPPORTED_RHYTHM_COLOR_KEYS))


def _fill_distractors(builder: _NoteBuilder, *, rng, axes: _ResolvedAxes, minimum_total: int) -> None:
    """Fill the scene with extra notes that cannot change the active timing answer."""

    lane_count = int(axes.lane_count)
    row_count = int(axes.row_count)
    rows = tuple(range(int(axes.beat_window) + 1, row_count + 1))
    if not rows:
        return
    attempts = 0
    while len(builder.notes) < int(minimum_total) and attempts < 240:
        attempts += 1
        lane = int(rng.randrange(lane_count))
        builder.add_random_note(
            lanes=(lane,),
            bottom_rows=rows,
            colors=SUPPORTED_RHYTHM_COLOR_KEYS,
        )


def _sample_count_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> RhythmSample:
    """Construct a lane-specific hit-count rhythm query."""

    selected_lane = _select_lane(rng=rng, lane_count=int(axes.lane_count), params=params)
    target_color = _target_color(rng=rng, params=params) if str(axes.query_id) == "lane_color_hit_count" else None
    target_count = int(axes.target_hit_count)
    builder = _NoteBuilder(lane_count=int(axes.lane_count), row_count=int(axes.row_count), rng=rng)
    target_rows = list(range(1, int(axes.beat_window) + 1))
    rng.shuffle(target_rows)
    evidence_ids: list[str] = []
    for row in target_rows[:target_count]:
        color = str(target_color) if target_color is not None else str(rng.choice(SUPPORTED_RHYTHM_COLOR_KEYS))
        note = builder.add_note(lane=selected_lane, bottom_row=int(row), length=1, color_key=color)
        evidence_ids.append(str(note.note_id))

    if str(axes.query_id) == "lane_color_hit_count":
        other_colors = [color for color in SUPPORTED_RHYTHM_COLOR_KEYS if str(color) != str(target_color)]
        for _ in range(int(rng.randrange(1, 3))):
            builder.add_random_note(
                lanes=(selected_lane,),
                bottom_rows=tuple(range(1, int(axes.beat_window) + 1)),
                colors=other_colors,
                lengths=(1, 1, 2),
            )
        builder.add_random_note(
            lanes=(selected_lane,),
            bottom_rows=tuple(range(int(axes.beat_window) + 1, int(axes.row_count) + 1)),
            colors=(str(target_color),),
            lengths=(1, 2, 3),
        )
    else:
        for _ in range(int(rng.randrange(1, 3))):
            builder.add_random_note(
                lanes=(selected_lane,),
                bottom_rows=tuple(range(int(axes.beat_window) + 1, int(axes.row_count) + 1)),
                colors=SUPPORTED_RHYTHM_COLOR_KEYS,
                lengths=(1, 2, 3),
            )

    target_total = int(rng.randrange(max(14, int(axes.lane_count) * 3), max(15, int(axes.lane_count) * 5 + 3)))
    _fill_distractors(builder, rng=rng, axes=axes, minimum_total=target_total)
    notes = tuple(builder.notes)
    sample = RhythmSample(
        lane_count=int(axes.lane_count),
        row_count=int(axes.row_count),
        beat_window=int(axes.beat_window),
        query_id=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        selected_lane_index=int(selected_lane),
        selected_lane_label=lane_label(int(selected_lane)),
        target_color_key=target_color,
        answer=int(target_count),
        notes=notes,
        evidence_entity_ids=tuple(evidence_ids),
        construction_mode=f"{str(axes.query_id)}_constructed_count",
    )
    validate_rhythm_sample(sample)
    return sample


def _sample_most_hits_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> RhythmSample:
    """Construct a unique most-hit-lane query."""

    target_lane = _select_lane(rng=rng, lane_count=int(axes.lane_count), params=params, key="target_lane_index")
    target_count = int(axes.target_hit_count)
    builder = _NoteBuilder(lane_count=int(axes.lane_count), row_count=int(axes.row_count), rng=rng)
    rows = list(range(1, int(axes.beat_window) + 1))
    rng.shuffle(rows)
    evidence_ids: list[str] = []
    for row in rows[:target_count]:
        note = builder.add_note(
            lane=target_lane,
            bottom_row=int(row),
            length=1,
            color_key=str(rng.choice(SUPPORTED_RHYTHM_COLOR_KEYS)),
        )
        evidence_ids.append(str(note.note_id))

    for lane in range(int(axes.lane_count)):
        if int(lane) == int(target_lane):
            continue
        lane_hits = int(rng.randrange(0, max(1, target_count)))
        lane_rows = list(range(1, int(axes.beat_window) + 1))
        rng.shuffle(lane_rows)
        for row in lane_rows[:lane_hits]:
            builder.add_note(
                lane=lane,
                bottom_row=int(row),
                length=1,
                color_key=str(rng.choice(SUPPORTED_RHYTHM_COLOR_KEYS)),
            )
    target_total = int(rng.randrange(max(15, int(axes.lane_count) * 3), max(16, int(axes.lane_count) * 5 + 5)))
    _fill_distractors(builder, rng=rng, axes=axes, minimum_total=target_total)
    sample = RhythmSample(
        lane_count=int(axes.lane_count),
        row_count=int(axes.row_count),
        beat_window=int(axes.beat_window),
        query_id=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        selected_lane_index=None,
        selected_lane_label=None,
        target_color_key=None,
        answer=int(lane_label(int(target_lane))),
        notes=tuple(builder.notes),
        evidence_entity_ids=tuple(evidence_ids),
        construction_mode="most_hits_unique_lane",
    )
    validate_rhythm_sample(sample)
    return sample


def _sample_earliest_hit_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> RhythmSample:
    """Construct a unique earliest-hit-lane query."""

    target_lane = _select_lane(rng=rng, lane_count=int(axes.lane_count), params=params, key="target_lane_index")
    target_time = int(rng.randrange(1, min(3, int(axes.beat_window)) + 1))
    builder = _NoteBuilder(lane_count=int(axes.lane_count), row_count=int(axes.row_count), rng=rng)
    target_note = builder.add_note(
        lane=target_lane,
        bottom_row=int(target_time),
        length=1,
        color_key=str(rng.choice(SUPPORTED_RHYTHM_COLOR_KEYS)),
    )
    later_rows = tuple(range(int(target_time) + 1, int(axes.beat_window) + 1))
    for lane in range(int(axes.lane_count)):
        if int(lane) == int(target_lane):
            continue
        if not later_rows or rng.random() < 0.20:
            continue
        builder.add_random_note(
            lanes=(lane,),
            bottom_rows=later_rows,
            colors=SUPPORTED_RHYTHM_COLOR_KEYS,
            lengths=(1, 1, 2),
        )
    target_total = int(rng.randrange(max(13, int(axes.lane_count) * 3), max(14, int(axes.lane_count) * 5 + 2)))
    _fill_distractors(builder, rng=rng, axes=axes, minimum_total=target_total)
    sample = RhythmSample(
        lane_count=int(axes.lane_count),
        row_count=int(axes.row_count),
        beat_window=int(axes.beat_window),
        query_id=str(axes.query_id),
        scene_variant=str(axes.scene_variant),
        selected_lane_index=None,
        selected_lane_label=None,
        target_color_key=None,
        answer=int(lane_label(int(target_lane))),
        notes=tuple(builder.notes),
        evidence_entity_ids=(str(target_note.note_id),),
        construction_mode="earliest_hit_unique_lane",
    )
    validate_rhythm_sample(sample)
    return sample


def _sample_scene(*, rng, axes: _ResolvedAxes, params: Mapping[str, Any]) -> RhythmSample:
    """Construct one rhythm scene for the requested query."""

    query = str(axes.query_id)
    if query in {"lane_hit_count", "lane_color_hit_count"}:
        return _sample_count_scene(rng=rng, axes=axes, params=params)
    if query == "most_hits_lane_label":
        return _sample_most_hits_scene(rng=rng, axes=axes, params=params)
    if query == "earliest_hit_lane_label":
        return _sample_earliest_hit_scene(rng=rng, axes=axes, params=params)
    raise ValueError(f"unsupported rhythm query_id: {query}")


def _build_prompt_json_examples(query_id: str) -> Tuple[str, str]:
    """Return deterministic prompt examples for rhythm JSON output."""

    if str(query_id) in {"most_hits_lane_label", "earliest_hit_lane_label"}:
        answer_value = 4
        evidence_value = [[318, 392, 401, 438]]
    else:
        answer_value = 3
        evidence_value = [[260, 498, 341, 545], [260, 432, 341, 479], [260, 302, 341, 349]]
    return (
        json.dumps({"evidence": evidence_value, "answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
        json.dumps({"answer": answer_value}, separators=(",", ":"), ensure_ascii=False),
    )


class GamesRhythmLanesTask:
    """Return one grounded query over a visible rhythm-game lane grid."""

    task_id = TASK_ID
    domain = "games"
    task_group = "rhythm"
    supported_query_ids: Tuple[str, ...] = SUPPORTED_RHYTHM_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        axes = _resolve_axes(
            int(instance_seed),
            params=params,
            supported_query_ids=tuple(getattr(self, "supported_query_ids", SUPPORTED_RHYTHM_QUERY_IDS)),
        )
        render_params = _render_params(params, instance_seed=int(instance_seed))

        sampled_scene: RhythmSample | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            attempt_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_scene = _sample_scene(rng=attempt_rng, axes=axes, params=params)
            except ValueError:
                continue
            break
        if sampled_scene is None:
            raise RuntimeError(f"{self.task_id} failed to generate a valid scene after {max_attempts} attempts")

        background, background_meta = make_background_canvas(
            canvas_width=int(render_params.canvas_width),
            canvas_height=int(render_params.canvas_height),
            instance_seed=int(instance_seed),
            params=params,
            default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
        )
        rendered_scene = render_rhythm_lanes_scene(
            lane_count=int(sampled_scene.lane_count),
            row_count=int(sampled_scene.row_count),
            beat_window=int(sampled_scene.beat_window),
            notes=sampled_scene.notes,
            background=background,
            style_variant=str(axes.style_variant),
            params=render_params,
        )
        evidence_bboxes = [
            list(rendered_scene.render_map["entity_bboxes_px"][str(entity_id)])
            for entity_id in sampled_scene.evidence_entity_ids
        ]
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
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description_falling_notes",
                "rhythm_motion_rule_text",
                "answer_hint_lane_hit_count",
                "evidence_hint_lane_hit_count",
                "answer_hint_lane_color_hit_count",
                "evidence_hint_lane_color_hit_count",
                "answer_hint_most_hits_lane_label",
                "evidence_hint_most_hits_lane_label",
                "answer_hint_earliest_hit_lane_label",
                "evidence_hint_earliest_hit_lane_label",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        json_example, json_example_answer_only = _build_prompt_json_examples(str(axes.query_id))
        selected_lane_label = sampled_scene.selected_lane_label or ""
        target_color = sampled_scene.target_color_key or ""
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(axes.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description_falling_notes"]),
                "rhythm_motion_rule_text": str(prompt_defaults["rhythm_motion_rule_text"]),
                "beat_window": str(sampled_scene.beat_window),
                "selected_lane_label": str(selected_lane_label),
                "target_color": str(target_color),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults[f"answer_hint_{str(axes.query_id)}"]),
                "evidence_hint": str(prompt_defaults[f"evidence_hint_{str(axes.query_id)}"]),
                "json_example": str(json_example),
                "json_example_answer_only": str(json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        answer_gt = TypedValue(type="integer", value=int(sampled_scene.answer))
        evidence_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in evidence_bboxes])
        complexity = build_games_rhythm_lanes_complexity(
            task_group_defaults=_TASK_GROUP_DEFAULTS,
            task_id=TASK_ID,
            query_id=str(axes.query_id),
            lane_count=int(sampled_scene.lane_count),
            row_count=int(sampled_scene.row_count),
            beat_window=int(sampled_scene.beat_window),
            note_count=len(sampled_scene.notes),
            evidence_count=len(sampled_scene.evidence_entity_ids),
        )
        note_trace = [
            {
                "note_id": str(note.note_id),
                "lane_index": int(note.lane_index),
                "lane_label": lane_label(int(note.lane_index)),
                "bottom_row_from_hit_line": int(note.bottom_row),
                "length_rows": int(note.length),
                "color_key": str(note.color_key),
                "kind": str(note.kind),
            }
            for note in sampled_scene.notes
        ]
        trace_payload = {
            "scene_ir": {
                "scene_kind": f"games_rhythm_{str(axes.scene_variant)}",
                "entities": [dict(entity) for entity in rendered_scene.scene_entities],
                "relations": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "lane_count": int(sampled_scene.lane_count),
                    "row_count": int(sampled_scene.row_count),
                    "beat_window": int(sampled_scene.beat_window),
                    "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                },
            },
            "query_spec": {
                "query_id": str(axes.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "scene_variant": str(axes.scene_variant),
                    "query_id": str(axes.query_id),
                    "style_variant": str(axes.style_variant),
                    "lane_count": int(sampled_scene.lane_count),
                    "row_count": int(sampled_scene.row_count),
                    "beat_window": int(sampled_scene.beat_window),
                    "target_hit_count": int(axes.target_hit_count),
                    "selected_lane_index": sampled_scene.selected_lane_index,
                    "selected_lane_label": sampled_scene.selected_lane_label,
                    "target_color_key": sampled_scene.target_color_key,
                    "answer_lane_label": str(sampled_scene.answer),
                    "scene_variant_probabilities": dict(axes.scene_variant_probabilities),
                    "query_id_probabilities": dict(axes.query_id_probabilities),
                    "style_variant_probabilities": dict(axes.style_variant_probabilities),
                    "lane_count_probabilities": dict(axes.lane_count_probabilities),
                    "row_count_probabilities": dict(axes.row_count_probabilities),
                    "beat_window_probabilities": dict(axes.beat_window_probabilities),
                    "target_hit_count_probabilities": dict(axes.target_hit_count_probabilities),
                },
            },
            "render_spec": {
                "scene_variant": str(axes.scene_variant),
                "style_variant": str(axes.style_variant),
                "canvas_width": int(image.size[0]),
                "canvas_height": int(image.size[1]),
                "layout_jitter": dict(rendered_scene.render_map.get("layout_jitter", {})),
            },
            "render_map": dict(rendered_scene.render_map),
            "execution_trace": {
                "scene_variant": str(axes.scene_variant),
                "query_id": str(axes.query_id),
                "style_variant": str(axes.style_variant),
                "lane_count": int(sampled_scene.lane_count),
                "row_count": int(sampled_scene.row_count),
                "beat_window": int(sampled_scene.beat_window),
                "selected_lane_index": sampled_scene.selected_lane_index,
                "selected_lane_label": sampled_scene.selected_lane_label,
                "target_color_key": sampled_scene.target_color_key,
                "answer": int(sampled_scene.answer),
                "notes": note_trace,
                "evidence_entity_ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
                "construction_mode": str(sampled_scene.construction_mode),
            },
            "witness_symbolic": {
                "type": "object_set",
                "ids": [str(entity_id) for entity_id in sampled_scene.evidence_entity_ids],
            },
            "projected_evidence": {
                "bbox_set": [list(bbox) for bbox in evidence_bboxes],
            },
            "background": background_meta,
            "post_image_noise": post_noise_meta,
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            scene_id="rhythm",
            query_id=str(axes.query_id),
        )


def _rewrite_generated_output(output: TaskOutput) -> TaskOutput:
    """Rewrite public rhythm query fields to the active query-id contract."""

    query_id = str(output.query_id)
    probabilities = None
    payload = output.trace_payload if isinstance(output.trace_payload, Mapping) else {}
    query_spec = payload.get("query_spec") if isinstance(payload, Mapping) else None
    if isinstance(query_spec, Mapping):
        spec_params = query_spec.get("params")
        if isinstance(spec_params, Mapping):
            raw_probabilities = spec_params.get("query_id_probabilities")
            if isinstance(raw_probabilities, Mapping):
                probabilities = {str(key): float(value) for key, value in raw_probabilities.items()}
    return rewrite_public_query_output(output, query_id=query_id, query_id_probabilities=probabilities)


@register_task
class GamesRhythmHitWindowCountTask(GamesRhythmLanesTask):
    """Count notes in a lane that reach the hit line within a beat window."""

    task_id = "task_games__rhythm__hit_window_count"
    supported_query_ids = COUNT_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _rewrite_generated_output(super().generate(int(instance_seed), params=params, max_attempts=int(max_attempts)))


@register_task
class GamesRhythmLaneChoiceLabelTask(GamesRhythmLanesTask):
    """Choose a lane by hit-count or earliest-hit timing."""

    task_id = "task_games__rhythm__lane_choice_value"
    supported_query_ids = LANE_CHOICE_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return _rewrite_generated_output(super().generate(int(instance_seed), params=params, max_attempts=int(max_attempts)))


__all__ = [
    "GamesRhythmHitWindowCountTask",
    "GamesRhythmLaneChoiceLabelTask",
    "GamesRhythmLanesTask",
]
