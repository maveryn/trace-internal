"""Count metro stations by route-membership predicate."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple

from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.fixed_query import force_query_id_params, select_task_query_id
from ...shared.output_metadata import default_task_versions
from .shared.instance import PUBLIC_METRO_SCENE_ID, build_metro_route_instance


TASK_ID = "task_graph__metro__station_membership_count"
TRANSFER_QUERY_ID = "metro_transfer_station_count"
SINGLE_ROUTE_QUERY_ID = "metro_single_route_station_count"
SUPPORTED_QUERY_IDS: Tuple[str, ...] = (TRANSFER_QUERY_ID, SINGLE_ROUTE_QUERY_ID)

_QUERY_ALIASES: Dict[str, str] = {
    "transfer_station_count": TRANSFER_QUERY_ID,
    "single_route_station_count": SINGLE_ROUTE_QUERY_ID,
    "non_transfer_station_count": SINGLE_ROUTE_QUERY_ID,
}

_QUERY_PROMPT_KEYS: Dict[str, Tuple[str, str]] = {
    TRANSFER_QUERY_ID: ("annotation_hint_transfer_station_count", "metro_transfer_station_count_query"),
    SINGLE_ROUTE_QUERY_ID: ("annotation_hint_single_route_station_count", "metro_single_route_station_count_query"),
}


def _selection_params(params: Mapping[str, Any]) -> Dict[str, Any]:
    """Normalize local query aliases before using the shared query selector."""

    normalized = dict(params)
    for selector_key in ("query_id", "query_variant"):
        requested = normalized.get(selector_key)
        if requested is not None:
            normalized[selector_key] = _QUERY_ALIASES.get(str(requested), str(requested))
    has_explicit_selector = any(str(normalized.get(key, "")) not in {"", "None"} for key in ("query_id", "query_variant"))
    if not has_explicit_selector and normalized.get("target_transfer_count") is not None:
        normalized["query_id"] = TRANSFER_QUERY_ID
    return normalized


def _branch_params(params: Mapping[str, Any], *, query_id: str) -> Dict[str, Any]:
    """Apply objective-owned sampling constraints for one station-membership query."""

    branch = dict(params)
    if str(query_id) == SINGLE_ROUTE_QUERY_ID:
        branch.setdefault("target_count_min", 8)
        branch.setdefault("target_count_max", 12)
        branch.setdefault("route_count_min", 2)
        branch.setdefault("route_count_max", 3)
    else:
        branch.setdefault("target_count_min", 1)
        branch.setdefault("target_count_max", 6)
        branch.setdefault("route_count_min", 3)
        branch.setdefault("route_count_max", 5)
    return branch


def _trace_with_query_probabilities(trace_payload: Mapping[str, Any], query_probs: Mapping[str, float]) -> Dict[str, Any]:
    """Return trace payload with public local-query probabilities recorded."""

    trace = dict(trace_payload)
    query_spec = dict(trace.get("query_spec") or {})
    params = dict(query_spec.get("params") or {})
    params["query_id_probabilities"] = {str(key): float(value) for key, value in query_probs.items()}
    query_spec["params"] = params
    trace["query_spec"] = query_spec
    return trace


@register_task
class GraphCountingMetroStationMembershipCountTask:
    """Count stations by transfer or single-route membership."""

    task_id = TASK_ID
    domain = "graph"
    scene_id = PUBLIC_METRO_SCENE_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        del max_attempts
        query_id, query_probs, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=_selection_params(params),
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=TRANSFER_QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        prompt_annotation_key, prompt_task_key_fallback = _QUERY_PROMPT_KEYS[str(query_id)]
        branch_params = _branch_params(task_params, query_id=str(query_id))
        forced_params = force_query_id_params(branch_params, query_id=str(query_id))
        bundle = build_metro_route_instance(
            instance_key=TASK_ID,
            query_id=str(query_id),
            prompt_annotation_key=str(prompt_annotation_key),
            prompt_task_key_fallback=str(prompt_task_key_fallback),
            instance_seed=int(instance_seed),
            params=forced_params,
            domain=self.domain,
        )
        return TaskOutput(
            prompt=str(bundle.prompt),
            answer_gt=TypedValue(type="integer", value=int(bundle.answer_value)),
            annotation_gt=TypedValue(type=str(bundle.annotation_type), value=list(bundle.annotation_value)),
            image=bundle.image,
            image_id="img0",
            trace_payload=_trace_with_query_probabilities(bundle.trace_payload, query_probs),
            task_versions=default_task_versions(),
            scene_id=PUBLIC_METRO_SCENE_ID,
            query_id=str(bundle.query_id),
            prompt_variants=dict(bundle.prompt_variants),
        )


__all__ = ["GraphCountingMetroStationMembershipCountTask", "TASK_ID"]
