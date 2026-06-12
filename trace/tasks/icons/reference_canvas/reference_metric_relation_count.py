"""Count scene icons satisfying a metric relation to the reference icon."""

from __future__ import annotations

from typing import Any, Dict

from ...registry import register_task
from ..shared.public_query_task import rewrite_icons_query_output
from .shared.reference_match_count import (
    METRIC_RELATION_TASK_ID,
    SCENE_ID,
    _SIZE_RELATION_ALIASES,
    _SIZE_RELATION_VARIANTS,
    _resolve_query_id,
    _task_defaults,
    _variant_mapping,
)
from .shared.size_relation import IconsCountingSizeRelationTask


@register_task
class IconsReferenceCanvasReferenceMetricRelationCountTask:
    """Count scene icons that are smaller or larger than the reference."""

    task_id = METRIC_RELATION_TASK_ID
    domain = "icons"
    supported_variants = _SIZE_RELATION_VARIANTS
    variant_aliases = _SIZE_RELATION_ALIASES

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int):
        gen_defaults, render_defaults, _prompt_defaults = _task_defaults(str(self.task_id))
        query_id, query_probabilities = _resolve_query_id(
            task_id=str(self.task_id),
            gen_defaults=gen_defaults,
            supported_variants=tuple(self.supported_variants),
            aliases=self.variant_aliases,
            instance_seed=int(instance_seed),
            params=params,
        )
        forced_params = {
            **_variant_mapping(gen_defaults, "variant_generation_params", variant=str(query_id)),
            **_variant_mapping(render_defaults, "variant_render_params", variant=str(query_id)),
            **dict(params),
            "query_id": str(query_id),
        }
        output = IconsCountingSizeRelationTask().generate(
            int(instance_seed),
            params=forced_params,
            max_attempts=int(max_attempts),
        )
        return rewrite_icons_query_output(
            output,
            query_id=str(query_id),
            scene_id=SCENE_ID,
            task_id=str(self.task_id),
            query_probabilities=dict(query_probabilities),
        )


__all__ = ["IconsReferenceCanvasReferenceMetricRelationCountTask"]
