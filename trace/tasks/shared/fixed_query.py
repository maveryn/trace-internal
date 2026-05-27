"""Shared helpers for public tasks backed by internal query branches."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any, Dict, Mapping, Sequence

from ..base import TaskOutput


_UNSET = object()


def force_query_id_params(params: Mapping[str, Any], *, query_id: str) -> Dict[str, Any]:
    """Return params that force one internal query branch."""

    forced = dict(params)
    requested_query_id = forced.get("query_id")
    if requested_query_id is not None and str(requested_query_id) != str(query_id):
        raise ValueError(
            "public task query_id must match query_id "
            f"'{query_id}' (got: {requested_query_id})"
        )
    forced["query_id"] = str(query_id)
    return forced


def probability_map(values: Sequence[str]) -> Dict[str, float]:
    """Return a uniform probability map over string values."""

    resolved = tuple(str(value) for value in values)
    if not resolved:
        return {}
    weight = 1.0 / float(len(resolved))
    return {str(value): float(weight) for value in resolved}


def normalize_probability_map(values: Mapping[str, float]) -> Dict[str, float]:
    """Return a JSON-stable string-keyed probability map."""

    return {str(key): float(value) for key, value in values.items()}


def rewrite_public_query_output(
    output: TaskOutput,
    *,
    query_id: str,
    scene_id: str | None = None,
    task_id: str | None = None,
    include_render_spec: bool = False,
    include_scene_ir_root: bool = False,
    query_id_probabilities: Mapping[str, float] | object = _UNSET,
    params_query_id_probabilities: Mapping[str, float] | object = _UNSET,
    variant_probabilities: Mapping[str, float] | object = _UNSET,
    scene_variant_probabilities: Mapping[str, float] | object = _UNSET,
    preserve_internal_query_id_as: str | Sequence[str] | None = None,
    preserve_prior_task_id_as: str | None = None,
    clear_keys: Sequence[str] = (),
    extra_fields: Mapping[str, Any] | None = None,
    extra_param_fields: Mapping[str, Any] | None = None,
    prompt_metadata: Mapping[str, Any] | None = None,
    update_existing_taxonomy: bool = False,
) -> TaskOutput:
    """Rewrite trace/query metadata for a narrowed public task.

    Domain wrappers choose which optional probability fields to emit so this
    helper can preserve existing task-review and replay contracts.
    """

    payload = deepcopy(output.trace_payload if isinstance(output.trace_payload, Mapping) else {})
    query_id_text = str(query_id)
    scene_id_text = None if scene_id is None else str(scene_id)
    task_id_text = None if task_id is None else str(task_id)
    clear_key_values = tuple(str(key) for key in clear_keys)
    extra_field_map = {str(key): value for key, value in dict(extra_fields or {}).items()}
    extra_param_field_map = {str(key): value for key, value in dict(extra_param_fields or extra_field_map).items()}
    prompt_metadata_map = {str(key): value for key, value in dict(prompt_metadata or {}).items()}
    if preserve_internal_query_id_as is None:
        preserve_internal_keys: tuple[str, ...] = ()
    elif isinstance(preserve_internal_query_id_as, str):
        preserve_internal_keys = (str(preserve_internal_query_id_as),)
    else:
        preserve_internal_keys = tuple(str(key) for key in preserve_internal_query_id_as)
    top_query_probabilities = (
        _UNSET
        if query_id_probabilities is _UNSET
        else normalize_probability_map(query_id_probabilities)  # type: ignore[arg-type]
    )
    if params_query_id_probabilities is _UNSET:
        params_probabilities = top_query_probabilities
    else:
        params_probabilities = normalize_probability_map(params_query_id_probabilities)  # type: ignore[arg-type]
    variant_probability_map = (
        _UNSET
        if variant_probabilities is _UNSET
        else normalize_probability_map(variant_probabilities)  # type: ignore[arg-type]
    )
    scene_variant_probability_map = (
        _UNSET
        if scene_variant_probabilities is _UNSET
        else normalize_probability_map(scene_variant_probabilities)  # type: ignore[arg-type]
    )

    def _preserve_internal(value: Dict[str, Any]) -> None:
        if not preserve_internal_keys:
            return
        prior_variant = value.get("query_id")
        if prior_variant is not None and str(prior_variant) != "default":
            for key in preserve_internal_keys:
                value.setdefault(str(key), str(prior_variant))

    def _rewrite_task_id(value: Dict[str, Any]) -> None:
        if task_id_text is None:
            return
        prior_task_id = value.get("task_id")
        if (
            preserve_prior_task_id_as
            and prior_task_id is not None
            and str(prior_task_id) != task_id_text
        ):
            value.setdefault(str(preserve_prior_task_id_as), str(prior_task_id))
        value["task_id"] = task_id_text

    def _rewrite_prompt_metadata(value: Dict[str, Any]) -> None:
        if not prompt_metadata_map:
            return
        prompt_variant = value.get("prompt_variant")
        if isinstance(prompt_variant, dict):
            prompt_variant.update(prompt_metadata_map)
        prompt_variants = value.get("prompt_variants")
        if not isinstance(prompt_variants, dict):
            return
        for prompt_variant_record in prompt_variants.values():
            if not isinstance(prompt_variant_record, dict):
                continue
            metadata = prompt_variant_record.get("metadata")
            if isinstance(metadata, dict):
                metadata.update(prompt_metadata_map)

    def _clear_mapping_keys(value: Dict[str, Any]) -> None:
        for key in clear_key_values:
            value.pop(str(key), None)

    def _rewrite_mapping(value: Any) -> None:
        if not isinstance(value, dict):
            return
        _clear_mapping_keys(value)
        _preserve_internal(value)
        _rewrite_task_id(value)
        if scene_id_text is not None:
            value["scene_id"] = scene_id_text
        value["query_id"] = query_id_text
        if top_query_probabilities is not _UNSET:
            value["query_id_probabilities"] = dict(top_query_probabilities)  # type: ignore[arg-type]
        if variant_probability_map is not _UNSET:
            value["variant_probabilities"] = dict(variant_probability_map)  # type: ignore[arg-type]
        if scene_variant_probability_map is not _UNSET and scene_variant_probability_map:
            value["scene_variant_probabilities"] = dict(scene_variant_probability_map)  # type: ignore[arg-type]
        value.update(extra_field_map)
        _rewrite_prompt_metadata(value)

        params = value.get("params")
        if not isinstance(params, dict):
            return
        _clear_mapping_keys(params)
        _preserve_internal(params)
        _rewrite_task_id(params)
        if scene_id_text is not None:
            params["scene_id"] = scene_id_text
        params["query_id"] = query_id_text
        if params_probabilities is not _UNSET:
            params["query_id_probabilities"] = dict(params_probabilities)  # type: ignore[arg-type]
        if variant_probability_map is not _UNSET:
            params["variant_probabilities"] = dict(variant_probability_map)  # type: ignore[arg-type]
        if scene_variant_probability_map is not _UNSET and scene_variant_probability_map:
            params["scene_variant_probabilities"] = dict(scene_variant_probability_map)  # type: ignore[arg-type]
        params.update(extra_param_field_map)

    def _rewrite_scene_ir_root(value: Any) -> None:
        if not isinstance(value, dict):
            return
        _clear_mapping_keys(value)
        _preserve_internal(value)
        _rewrite_task_id(value)
        if scene_id_text is not None:
            value["scene_id"] = scene_id_text
        value["query_id"] = query_id_text

    def _rewrite_existing_taxonomy() -> None:
        if not update_existing_taxonomy:
            return
        taxonomy = payload.get("taxonomy")
        if not isinstance(taxonomy, dict):
            return
        if scene_id_text is not None:
            taxonomy["scene_id"] = scene_id_text
        if task_id_text is not None:
            prior_task_id = taxonomy.get("task_id")
            if (
                preserve_prior_task_id_as
                and prior_task_id is not None
                and str(prior_task_id) != task_id_text
            ):
                taxonomy.setdefault(str(preserve_prior_task_id_as), str(prior_task_id))
            taxonomy["task_id"] = task_id_text
        taxonomy["query_id"] = query_id_text
        public = taxonomy.get("public")
        if isinstance(public, dict):
            if scene_id_text is not None:
                public["scene_id"] = scene_id_text
            if task_id_text is not None:
                public["task_id"] = task_id_text
            public["query_id"] = query_id_text

    keys = ["query_spec", "execution_trace"]
    if include_render_spec:
        keys.append("render_spec")
    for key in keys:
        _rewrite_mapping(payload.get(str(key)))

    scene_ir = payload.get("scene_ir")
    if isinstance(scene_ir, dict):
        if include_scene_ir_root:
            _rewrite_scene_ir_root(scene_ir)
        _rewrite_mapping(scene_ir.get("relations"))
    _rewrite_existing_taxonomy()

    return replace(
        output,
        trace_payload=payload,
        query_id=query_id_text,
        scene_id=scene_id_text if scene_id_text is not None else output.scene_id,
    )


__all__ = [
    "force_query_id_params",
    "normalize_probability_map",
    "probability_map",
    "rewrite_public_query_output",
]
