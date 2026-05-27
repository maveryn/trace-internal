"""Merged urban-market shop attribute counting task."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple, Type

from ....core.task_group_config import get_task_group_defaults
from ...base import Task, TaskOutput
from ...registry import register_task
from ...shared.config_defaults import split_generation_rendering_prompt_defaults
from ..shared.merged_counting_task import rewrite_branch_output, select_query_id
from ._market_shop_category_branch import MarketShopCategoryBranch, QUERY_ID as SHOP_CATEGORY_QUERY_ID
from ._market_shop_color_branch import MarketShopColorBranch, QUERY_IDS as COLOR_QUERY_IDS
from ._market_shop_selling_branch import (
    MarketShopSellingBranch,
    QUERY_ID as SHOP_SELLING_QUERY_ID,
)


TASK_ID = "task_illustrations__market__shop_attribute_count"
SCENE_ID = "market"
QUERY_IDS: Tuple[str, ...] = (SHOP_CATEGORY_QUERY_ID, *COLOR_QUERY_IDS, SHOP_SELLING_QUERY_ID)

_BRANCH_BY_QUERY: Dict[str, Type[Task]] = {
    SHOP_CATEGORY_QUERY_ID: MarketShopCategoryBranch,
    **{query_id: MarketShopColorBranch for query_id in COLOR_QUERY_IDS},
    SHOP_SELLING_QUERY_ID: MarketShopSellingBranch,
}

_TASK_GROUP_DEFAULTS = get_task_group_defaults("illustrations", "counting")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)


@register_task
class IllustrationsCountingMarketShopAttributeCountTask:
    """Count shops by category label, visible color attribute, or sold item."""

    task_id = TASK_ID
    domain = "illustrations"
    task_group = "counting"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_probabilities = select_query_id(
            task_id=TASK_ID,
            params=params,
            defaults=_GEN_DEFAULTS,
            instance_seed=int(instance_seed),
            fallback=QUERY_IDS,
        )
        branch_cls = _BRANCH_BY_QUERY[str(query_id)]
        branch_params = dict(params)
        branch_params["query_id"] = str(query_id)
        output = branch_cls().generate(int(instance_seed), params=branch_params, max_attempts=int(max_attempts))
        return rewrite_branch_output(
            output,
            public_task_id=TASK_ID,
            branch_id=str(branch_cls.branch_id),
            query_probabilities=query_probabilities,
        )


__all__ = ["IllustrationsCountingMarketShopAttributeCountTask", "TASK_ID", "SCENE_ID", "QUERY_IDS"]
