"""Count icons by set relation between two icon panels."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.sampling import normalize_positive_weights, weighted_choice
from ....core.scene_config import get_scene_defaults
from ....core.seed import spawn_rng
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, split_generation_rendering_prompt_defaults
from ..shared.public_query_task import rewrite_icons_query_output
from .shared.panel_added_removed_count import IconsCountingPanelAddedRemovedCountTask
from .shared.panel_exact_match_count import IconsCountingPanelExactMatchCountTask


TASK_ID = "task_icons__paired_canvas__panel_set_relation_count"
SCENE_ID = "paired_canvas"
QUERY_IDS: Tuple[str, ...] = (
    "right_exact_match_count",
    "added_in_right_count",
    "missing_from_right_count",
)
_SCENE_DEFAULTS = get_scene_defaults("icons", SCENE_ID)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _SCENE_DEFAULTS if isinstance(_SCENE_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


def _query_probabilities(params: Mapping[str, Any]) -> Dict[str, float]:
    raw = params.get("query_id_weights", group_default(_GEN_DEFAULTS, "query_id_weights", {}))
    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping):
        raise ValueError("query_id_weights must be a mapping")
    return normalize_positive_weights(
        {str(key): float(value) for key, value in raw.items() if str(key) in set(QUERY_IDS)},
        default_keys=QUERY_IDS,
    )


def _resolve_query_id(instance_seed: int, params: Mapping[str, Any]) -> tuple[str, Dict[str, float]]:
    explicit = params.get("query_id")
    probabilities = _query_probabilities(params)
    if explicit is not None:
        query_id = str(explicit)
        if query_id not in set(QUERY_IDS):
            raise ValueError(f"query_id must be one of {QUERY_IDS}")
        return query_id, {key: (1.0 if key == query_id else 0.0) for key in QUERY_IDS}
    rng = spawn_rng(int(instance_seed), f"{TASK_ID}:query_id")
    query_id = str(weighted_choice(rng, probabilities, sort_keys=True))
    return query_id, dict(probabilities)


def _variant_params(query_id: str) -> Dict[str, Any]:
    raw = _GEN_DEFAULTS.get("variant_generation_params", {})
    if not isinstance(raw, Mapping):
        return {}
    selected = raw.get(str(query_id), {})
    if not isinstance(selected, Mapping):
        return {}
    return dict(selected)


@register_task
class IconsCountingPanelSetRelationCountTask:
    """Count exact matches, additions, or removals across paired icon panels."""

    task_id = TASK_ID
    domain = "icons"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, probabilities = _resolve_query_id(int(instance_seed), params)
        forced_params = {**_variant_params(str(query_id)), **dict(params)}
        forced_params["query_id"] = str(query_id)
        if str(query_id) == "right_exact_match_count":
            output = IconsCountingPanelExactMatchCountTask().generate(
                int(instance_seed),
                params=forced_params,
                max_attempts=int(max_attempts),
            )
        else:
            output = IconsCountingPanelAddedRemovedCountTask().generate(
                int(instance_seed),
                params=forced_params,
                max_attempts=int(max_attempts),
            )
        return rewrite_icons_query_output(
            output,
            query_id=str(query_id),
            scene_id=SCENE_ID,
            task_id=self.task_id,
            query_probabilities=dict(probabilities),
        )


__all__ = ["IconsCountingPanelSetRelationCountTask", "QUERY_IDS"]
