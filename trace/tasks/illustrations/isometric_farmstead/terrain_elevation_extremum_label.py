"""Select the lettered terrain tile at the elevation extremum."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

from trace.core.scene_config import get_scene_defaults
from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import (
    group_default,
    required_group_defaults,
    split_scene_generation_rendering_prompt_defaults,
)
from trace.tasks.shared.deterministic_sampling import resolve_selection_index, uniform_probability_map
from trace.tasks.shared.fixed_query import select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.illustrations.shared.canvas_profiles import resolve_canvas_profile
from trace.tasks.illustrations.shared.option_rendering import sample_visual_label_font_trace

from .shared.output import (
    bbox_projection,
    isometric_farmstead_elevation_render_map,
    isometric_farmstead_render_spec,
    isometric_farmstead_scene_ir,
    rounded_bbox,
)
from .shared.prompts import build_isometric_farmstead_prompt_artifacts
from .shared.rendering import (
    DEFAULT_CANDIDATE_LABELS,
    SCENE_ID,
    SUPPORTED_LEVELS,
    render_isometric_farmstead_scene,
)
from .shared.state import IsoFarmsteadScene, IsoFarmsteadTile


TASK_ID = "task_illustrations__isometric_farmstead__terrain_elevation_extremum_label"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = ("highest_terrain_tile", "lowest_terrain_tile")


@dataclass(frozen=True)
class _SampleSpec:
    selected_query: str
    prompt_query_key: str
    query_probabilities: dict[str, float]
    candidate_count: int
    candidate_count_probabilities: dict[str, float]
    canvas_width: int
    canvas_height: int
    canvas_profile: str
    canvas_profile_probabilities: dict[str, float]


_SCENE_DEFAULTS = get_scene_defaults("illustrations", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_scene_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _support_values(
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    *,
    support_key: str,
    fallback: Sequence[int],
) -> tuple[int, ...]:
    raw = params.get(str(support_key), group_default(defaults, str(support_key), tuple(fallback)))
    values = (raw,) if isinstance(raw, int) else tuple(raw if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)) else ())
    support = tuple(dict.fromkeys(int(value) for value in values))
    if not support:
        raise ValueError(f"{support_key} must include at least one value")
    return support


def _select_count(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    defaults: Mapping[str, Any],
    support_key: str,
    explicit_key: str,
    fallback: Sequence[int],
    namespace: str,
) -> tuple[int, dict[str, float]]:
    support = _support_values(params, defaults, support_key=str(support_key), fallback=fallback)
    explicit = params.get(str(explicit_key))
    if explicit is not None:
        value = int(explicit)
        if value not in set(support):
            raise ValueError(f"{explicit_key} must be one of {support}")
        return value, {str(value): 1.0}
    index = resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=str(namespace))
    value = int(support[int(index) % len(support)])
    return value, dict(uniform_probability_map(support))


def _sample_spec(*, instance_seed: int, params: Mapping[str, Any]) -> _SampleSpec:
    selected_query, query_probabilities, task_params = select_task_query_id(
        instance_seed=int(instance_seed),
        params=params,
        supported_query_ids=SUPPORTED_QUERY_IDS,
        default_query_id="highest_terrain_tile",
        task_id=TASK_ID,
        namespace=f"{TASK_ID}:query",
    )
    candidate_count, candidate_count_probabilities = _select_count(
        instance_seed=int(instance_seed),
        params=task_params,
        defaults=_GEN_DEFAULTS,
        support_key="candidate_count_support",
        explicit_key="candidate_count",
        fallback=(4,),
        namespace=f"{TASK_ID}:candidate_count",
    )
    if candidate_count > len(DEFAULT_CANDIDATE_LABELS):
        raise ValueError(f"candidate_count must be at most {len(DEFAULT_CANDIDATE_LABELS)}")
    profile = resolve_canvas_profile(
        params=task_params,
        defaults=_RENDER_DEFAULTS,
        fallback_width=1200,
        fallback_height=800,
        instance_seed=int(instance_seed),
        namespace=f"{TASK_ID}:canvas_profile",
    )
    return _SampleSpec(
        selected_query=str(selected_query),
        prompt_query_key=str(selected_query),
        query_probabilities=dict(query_probabilities),
        candidate_count=int(candidate_count),
        candidate_count_probabilities=dict(candidate_count_probabilities),
        canvas_width=int(profile.width),
        canvas_height=int(profile.height),
        canvas_profile=str(profile.profile_id),
        canvas_profile_probabilities=dict(profile.probabilities),
    )


def _tile_inside_canvas(tile: IsoFarmsteadTile, *, width: int, height: int) -> bool:
    return (
        0.0 <= float(tile.bbox_xyxy[0])
        and float(tile.bbox_xyxy[2]) <= float(width)
        and 0.0 <= float(tile.bbox_xyxy[1])
        and float(tile.bbox_xyxy[3]) <= float(height)
    )


def _label_box_for_tile(tile: IsoFarmsteadTile) -> tuple[float, float, float, float]:
    cx, cy = tile.center_xy
    return (float(cx) - 18.0, float(cy) - 15.0, float(cx) + 18.0, float(cy) + 13.0)


def _boxes_intersect(left: Sequence[float], right: Sequence[float], *, pad: float = 0.0) -> bool:
    return (
        float(left[0]) - float(pad) < float(right[2])
        and float(left[2]) + float(pad) > float(right[0])
        and float(left[1]) - float(pad) < float(right[3])
        and float(left[3]) + float(pad) > float(right[1])
    )


def _label_clear_of_context(scene: IsoFarmsteadScene, tile: IsoFarmsteadTile) -> bool:
    label_box = _label_box_for_tile(tile)
    return not any(_boxes_intersect(label_box, entity.bbox_xyxy, pad=8.0) for entity in scene.entities)


def _eligible_tiles_by_level(scene: IsoFarmsteadScene) -> dict[int, list[IsoFarmsteadTile]]:
    eligible_ids = {str(value) for value in scene.trace.get("eligible_tile_ids", [])}
    active_levels = tuple(int(level) for level in scene.trace.get("levels", SUPPORTED_LEVELS))
    by_level: dict[int, list[IsoFarmsteadTile]] = {int(level): [] for level in active_levels}
    width, height = scene.image.size
    for tile in scene.tiles:
        if str(tile.tile_id) not in eligible_ids:
            continue
        if not bool(tile.metadata.get("candidate_allowed", False)):
            continue
        if str(tile.terrain) != "grass":
            continue
        if not _tile_inside_canvas(tile, width=width, height=height):
            continue
        if not _label_clear_of_context(scene, tile):
            continue
        by_level[int(tile.level)].append(tile)
    return {level: sorted(tiles, key=lambda item: (item.row, item.col)) for level, tiles in by_level.items()}


def _select_candidate_tiles(
    *,
    scene: IsoFarmsteadScene,
    selected_query: str,
    candidate_count: int,
    instance_seed: int,
) -> tuple[dict[str, str], str]:
    """Select one unique elevation-extremum tile plus distractor tiles."""

    by_level = _eligible_tiles_by_level(scene)
    active_levels = tuple(level for level in sorted(by_level) if by_level[level])
    if len(active_levels) < 2:
        raise ValueError("not enough active elevation levels with eligible candidate tiles")
    if str(selected_query) == "highest_terrain_tile":
        target_level = max(active_levels)
        distractor_levels = [level for level in active_levels if int(level) < int(target_level)]
    elif str(selected_query) == "lowest_terrain_tile":
        target_level = min(active_levels)
        distractor_levels = [level for level in active_levels if int(level) > int(target_level)]
    else:
        raise ValueError(f"unsupported elevation query: {selected_query}")

    answer_pool = list(by_level[int(target_level)])
    distractor_pool = [tile for level in distractor_levels for tile in by_level[int(level)]]
    if not answer_pool:
        raise ValueError(f"no eligible target tiles at level {target_level}")
    if len(distractor_pool) < int(candidate_count) - 1:
        raise ValueError("not enough eligible elevation distractor tiles")

    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:candidate_tiles:{selected_query}")
    answer_tile = rng.choice(answer_pool)
    rng.shuffle(distractor_pool)
    labels = list(DEFAULT_CANDIDATE_LABELS[: int(candidate_count)])
    selected_label = str(labels[int(instance_seed) % int(candidate_count)])
    distractor_labels = [str(label) for label in labels if str(label) != selected_label]
    candidate_tile_ids_by_label = {selected_label: str(answer_tile.tile_id)}
    for label, tile in zip(distractor_labels, distractor_pool[: int(candidate_count) - 1]):
        candidate_tile_ids_by_label[str(label)] = str(tile.tile_id)
    candidate_tile_ids_by_label = {str(label): str(candidate_tile_ids_by_label[str(label)]) for label in labels}
    return candidate_tile_ids_by_label, selected_label


@register_task
class IllustrationsIsometricFarmsteadTerrainElevationExtremumLabelTask:
    """Choose the lettered terrain tile that is highest or lowest."""

    task_id = TASK_ID
    domain = "illustrations"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one option-selection instance with task-owned candidate and answer binding."""

        sample = _sample_spec(instance_seed=int(instance_seed), params=params)
        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            [
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "answer_hint_terrain_elevation_extremum_label",
                "annotation_hint_terrain_elevation_extremum_label",
                "json_example_terrain_elevation_extremum_label",
                "json_example_answer_only_terrain_elevation_extremum_label",
            ],
            context=f"prompt defaults for {TASK_ID}",
        )
        last_error: Exception | None = None
        for attempt in range(max(1, int(max_attempts))):
            try:
                scene_seed = int(instance_seed) + int(attempt) * 1009
                base_scene = render_isometric_farmstead_scene(
                    scene_seed,
                    width=sample.canvas_width,
                    height=sample.canvas_height,
                    canvas_profile=sample.canvas_profile,
                    canvas_profile_probabilities=sample.canvas_profile_probabilities,
                )
                candidates_by_label, selected_label = _select_candidate_tiles(
                    scene=base_scene,
                    selected_query=sample.selected_query,
                    candidate_count=sample.candidate_count,
                    instance_seed=scene_seed,
                )
                labels_by_tile_id = {str(tile_id): str(label) for label, tile_id in candidates_by_label.items()}
                label_font_trace = sample_visual_label_font_trace(
                    namespace_prefix=TASK_ID,
                    instance_seed=scene_seed,
                    params={**dict(_RENDER_DEFAULTS), **dict(params)},
                    namespace_suffix="terrain_tile_labels",
                    explicit_key="terrain_tile_label_font_family",
                    weights_key="terrain_tile_label_font_weights",
                )
                scene = render_isometric_farmstead_scene(
                    scene_seed,
                    width=sample.canvas_width,
                    height=sample.canvas_height,
                    canvas_profile=sample.canvas_profile,
                    canvas_profile_probabilities=sample.canvas_profile_probabilities,
                    candidate_labels_by_tile_id=labels_by_tile_id,
                    label_font_family=str(label_font_trace["font_family"]),
                )
                break
            except Exception as exc:
                last_error = exc
        else:
            raise RuntimeError(f"could not generate {TASK_ID}: {last_error}") from last_error

        tiles_by_id = {str(tile.tile_id): tile for tile in scene.tiles}
        selected_tile_id = str(candidates_by_label[str(selected_label)])
        selected_tile = tiles_by_id[selected_tile_id]
        annotation_value = rounded_bbox(selected_tile.bbox_xyxy)
        prompt_artifacts = build_isometric_farmstead_prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=prompt_defaults,
            prompt_query_key=sample.prompt_query_key,
            slots={
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "answer_hint": str(prompt_defaults["answer_hint_terrain_elevation_extremum_label"]),
                "annotation_hint": str(prompt_defaults["annotation_hint_terrain_elevation_extremum_label"]),
                "json_example": str(prompt_defaults["json_example_terrain_elevation_extremum_label"]),
                "json_example_answer_only": str(prompt_defaults["json_example_answer_only_terrain_elevation_extremum_label"]),
            },
            instance_seed=int(instance_seed),
        )
        render_map = isometric_farmstead_elevation_render_map(
            scene=scene,
            candidate_tile_ids_by_label=candidates_by_label,
            selected_label=str(selected_label),
        )
        query_params = {
            "query_id": str(sample.selected_query),
            "prompt_query_key": str(sample.prompt_query_key),
            "query_id_probabilities": dict(sample.query_probabilities),
            "candidate_count": int(sample.candidate_count),
            "candidate_count_probabilities": dict(sample.candidate_count_probabilities),
            "candidate_labels": list(DEFAULT_CANDIDATE_LABELS[: int(sample.candidate_count)]),
            "candidate_tile_ids_by_label": dict(candidates_by_label),
            "candidate_levels_by_label": dict(render_map["candidate_levels_by_label"]),
            "selected_label": str(selected_label),
            "selected_tile_id": str(selected_tile_id),
            "selected_tile_level": int(selected_tile.level),
            "canvas_profile": str(sample.canvas_profile),
            "canvas_profile_probabilities": dict(sample.canvas_profile_probabilities),
        }
        trace_payload = {
            "scene_ir": isometric_farmstead_scene_ir(
                domain=self.domain,
                scene_id=SCENE_ID,
                scene=scene,
                relations={
                    "operation": "select_elevation_extremum",
                    "extremum": "highest" if sample.selected_query == "highest_terrain_tile" else "lowest",
                    "candidate_tile_ids_by_label": dict(candidates_by_label),
                    "selected_label": str(selected_label),
                    "selected_tile_id": str(selected_tile_id),
                    "selected_tile_level": int(selected_tile.level),
                },
            ),
            "query_spec": {
                "task_id": TASK_ID,
                "query_id": str(sample.selected_query),
                "prompt_query_key": str(sample.prompt_query_key),
                "prompt_variant_active_key": prompt_artifacts.prompt_variant_active_key,
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": query_params,
            },
            "render_spec": {
                **isometric_farmstead_render_spec(scene, scene_id=SCENE_ID),
                "style": {
                    **isometric_farmstead_render_spec(scene, scene_id=SCENE_ID)["style"],
                    "label_font": dict(label_font_trace),
                },
            },
            "render_map": render_map,
            "execution_trace": {
                "query_id": str(sample.selected_query),
                "prompt_query_key": str(sample.prompt_query_key),
                "scene_id": SCENE_ID,
                "answer": str(selected_label),
                "selected_label": str(selected_label),
                "selected_tile_id": str(selected_tile_id),
                "selected_tile_level": int(selected_tile.level),
                "candidate_tile_ids_by_label": dict(candidates_by_label),
                "candidate_levels_by_label": dict(render_map["candidate_levels_by_label"]),
                "renderer": dict(scene.trace),
            },
            "witness_symbolic": {
                "answer_label": str(selected_label),
                "selected_tile_id": str(selected_tile_id),
                "selected_tile_level": int(selected_tile.level),
                "selected_tile_bbox": list(annotation_value),
            },
            "projected_annotation": bbox_projection(annotation_value),
        }
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            prompt_variants={str(key): str(value) for key, value in prompt_artifacts.prompt_variants.items()},
            answer_gt=TypedValue(type="option_letter", value=str(selected_label)),
            annotation_gt=TypedValue(type="bbox", value=list(annotation_value)),
            image=scene.image,
            image_id="img0",
            trace_payload=trace_payload,
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample.selected_query),
        )


__all__ = [
    "IllustrationsIsometricFarmsteadTerrainElevationExtremumLabelTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
