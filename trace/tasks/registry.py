"""Task registry for TRACE generation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import re
from functools import wraps
from typing import Any, Dict, Mapping, Sequence, Type

from ..core.taxonomy import resolve_task_query_id
from .base import Task, TaskOutput
from .shared.font_assets import font_role_trace, get_font_family_record, sample_font_family
from .shared.fixed_query import rewrite_public_query_output
from .shared.marker_legibility import collect_semantic_marker_records, semantic_marker_records_summary
from .shared.text_legibility import collect_traced_text_records, traced_text_records_summary
from .shared.text_rendering import temporary_default_font_family


TASK_REGISTRY: Dict[str, Type[Task]] = {}
_V0_TASK_ID_PATTERN = re.compile(
    r"^task_(?P<domain>[a-z0-9_]+)__(?P<scene>[a-z0-9_]+)__(?P<objective>[a-z0-9_]+)$"
)


def _validate_task_id_contract(cls: Type[Task], task_id: str) -> None:
    """Validate canonical task-id naming and taxonomy alignment."""
    task_id_text = str(task_id)
    v0_match = _V0_TASK_ID_PATTERN.match(task_id_text)
    if v0_match is None:
        raise ValueError(
            "task_id must follow taxonomy-v0 public form "
            "'task_<domain>__<scene_id>__<objective_contract>' "
            f"(got: {task_id})"
        )
    domain = getattr(cls, "domain", None)
    task_group = getattr(cls, "task_group", None)
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError(f"task '{task_id}' must define non-empty string attribute 'domain'")
    if not isinstance(task_group, str) or not task_group.strip():
        raise ValueError(f"task '{task_id}' must define non-empty string attribute 'task_group'")
    if v0_match is not None:
        task_domain = str(v0_match.group("domain"))
        if task_domain != str(domain):
            raise ValueError(
                "taxonomy-v0 task_id domain segment must match class domain "
                f"'{domain}' (got: {task_id_text})"
            )


def _attach_collected_text_legibility(
    output: TaskOutput,
    *,
    drawn_text_records: Sequence[Mapping[str, Any]],
) -> TaskOutput:
    """Copy automatically collected visible text metadata into render_spec."""

    if not drawn_text_records:
        return output
    trace_payload = output.trace_payload
    if not isinstance(trace_payload, Mapping):
        return output
    payload = deepcopy(dict(trace_payload))
    render_spec = payload.get("render_spec")
    if not isinstance(render_spec, dict):
        render_spec = {}
        payload["render_spec"] = render_spec
    drawn_text = render_spec.setdefault("drawn_text", {})
    if not isinstance(drawn_text, dict):
        drawn_text = {}
        render_spec["drawn_text"] = drawn_text
    drawn_text["text_legibility"] = traced_text_records_summary(
        drawn_text_records,
        image=output.image,
    )
    return replace(output, trace_payload=payload)


def _attach_collected_marker_legibility(
    output: TaskOutput,
    *,
    marker_records: Sequence[Mapping[str, Any]],
) -> TaskOutput:
    """Copy automatically collected semantic marker metadata into render_spec."""

    if not marker_records:
        return output
    trace_payload = output.trace_payload
    if not isinstance(trace_payload, Mapping):
        return output
    payload = deepcopy(dict(trace_payload))
    render_spec = payload.get("render_spec")
    if not isinstance(render_spec, dict):
        render_spec = {}
        payload["render_spec"] = render_spec
    drawn_markers = render_spec.setdefault("drawn_markers", {})
    if not isinstance(drawn_markers, dict):
        drawn_markers = {}
        render_spec["drawn_markers"] = drawn_markers
    drawn_markers["marker_legibility"] = semantic_marker_records_summary(marker_records)
    return replace(output, trace_payload=payload)


def _attach_collected_visual_legibility(
    output: TaskOutput,
    *,
    drawn_text_records: Sequence[Mapping[str, Any]],
    marker_records: Sequence[Mapping[str, Any]],
) -> TaskOutput:
    output = _attach_collected_text_legibility(
        output,
        drawn_text_records=drawn_text_records,
    )
    return _attach_collected_marker_legibility(
        output,
        marker_records=marker_records,
    )


def _sample_implicit_readout_font(
    *,
    task_id: str,
    instance_seed: int,
    params: Mapping[str, Any] | None,
) -> str:
    """Sample the per-instance readout font used by legacy load_font calls."""

    return sample_font_family(
        role="readout",
        instance_seed=int(instance_seed),
        namespace=f"{task_id}.implicit_readout_font",
        params=params or {},
    )


def _attach_implicit_readout_font(
    output: TaskOutput,
    *,
    task_id: str,
    font_family: str,
) -> TaskOutput:
    """Record the implicit readout font made available during generation."""

    if not str(font_family or "").strip():
        return output
    trace_payload = output.trace_payload
    if not isinstance(trace_payload, Mapping):
        return output
    payload = deepcopy(dict(trace_payload))
    render_spec = payload.get("render_spec")
    if not isinstance(render_spec, dict):
        render_spec = {}
        payload["render_spec"] = render_spec
    font_assets = render_spec.setdefault("font_assets", {})
    if not isinstance(font_assets, dict):
        font_assets = {}
        render_spec["font_assets"] = font_assets
    font_record = get_font_family_record(str(font_family)).to_trace()
    font_record.update(font_role_trace(str(font_family), role="readout"))
    font_assets["implicit_readout_font_family"] = font_record
    if str(task_id).startswith("task_charts__"):
        font_assets.setdefault("chart_font_family", str(font_family))
        font_assets.setdefault("chart_font_asset_version", str(font_record.get("font_asset_version", "")))
    return replace(output, trace_payload=payload)


def _attach_illustration_art_style_metadata(output: TaskOutput, *, task_id: str) -> TaskOutput:
    """Expose canonical art-style metadata for illustration render specs."""

    if not str(task_id).startswith("task_illustrations__"):
        return output
    trace_payload = output.trace_payload
    if not isinstance(trace_payload, Mapping):
        return output
    payload = deepcopy(dict(trace_payload))
    render_spec = payload.get("render_spec")
    if not isinstance(render_spec, dict):
        return output
    style = render_spec.get("style")
    if not isinstance(style, dict):
        return output
    try:
        from .illustrations.shared.style_registry import ART_STYLE_REGISTRY_VERSION, ART_STYLES, art_style_trace
    except Exception:
        return output
    if "art_style_id" not in style and str(style.get("style_id", "")) in ART_STYLES:
        style.update(art_style_trace(str(style["style_id"])))
    if "art_style_ids" not in style and isinstance(style.get("style_ids"), Sequence) and not isinstance(style.get("style_ids"), (str, bytes)):
        art_style_ids = [str(value) for value in style.get("style_ids", []) if str(value) in ART_STYLES]
        if art_style_ids:
            style["art_style_ids"] = art_style_ids
            style["art_style_registry_version"] = ART_STYLE_REGISTRY_VERSION
    return replace(output, trace_payload=payload)


def register_task(cls: Type[Task]) -> Type[Task]:
    """Register task class under `task_id`."""
    task_id = str(getattr(cls, "task_id"))
    _validate_task_id_contract(cls, task_id)
    if task_id in TASK_REGISTRY:
        raise KeyError(f"duplicate task_id: {task_id}")
    v0_match = _V0_TASK_ID_PATTERN.match(task_id)
    generate_impl = cls.generate
    if str(getattr(cls, "domain", "")) == "charts":
        from .charts.shared.render_audit_defaults import wrap_charts_generation

        generate_impl = wrap_charts_generation(
            generate_impl,
            task_id=str(task_id),
            task_group=str(getattr(cls, "task_group", "")),
        )
    if str(getattr(cls, "domain", "")) == "pages":
        from .pages.shared.render_audit_defaults import wrap_pages_generation

        generate_impl = wrap_pages_generation(
            generate_impl,
            task_id=str(task_id),
            task_group=str(getattr(cls, "task_group", "")),
        )
    if v0_match is not None:
        original_generate = generate_impl
        taxonomy_scene_id = str(v0_match.group("scene"))

        @wraps(original_generate)
        def _generate_with_public_query_contract(self, instance_seed, *, params, max_attempts):
            implicit_font_family = _sample_implicit_readout_font(
                task_id=task_id,
                instance_seed=int(instance_seed),
                params=params,
            )
            with collect_traced_text_records() as drawn_text_records:
                with collect_semantic_marker_records() as marker_records:
                    with temporary_default_font_family(implicit_font_family):
                        output = original_generate(self, instance_seed, params=params, max_attempts=max_attempts)
            output = _attach_implicit_readout_font(
                output,
                task_id=task_id,
                font_family=implicit_font_family,
            )
            output = _attach_illustration_art_style_metadata(output, task_id=task_id)
            query_id = str(
                output.query_id
                or resolve_task_query_id(trace_payload=output.trace_payload)
            )
            if not query_id:
                return _attach_collected_visual_legibility(
                    output,
                    drawn_text_records=drawn_text_records,
                    marker_records=marker_records,
                )
            scene_id = str(output.scene_id or taxonomy_scene_id)
            output = rewrite_public_query_output(
                output,
                query_id=query_id,
                scene_id=scene_id,
                preserve_internal_query_id_as="internal_query_id",
            )
            return _attach_collected_visual_legibility(
                output,
                drawn_text_records=drawn_text_records,
                marker_records=marker_records,
            )

        cls.generate = _generate_with_public_query_contract  # type: ignore[method-assign]
    else:
        @wraps(generate_impl)
        def _generate_with_text_collection(self, instance_seed, *, params, max_attempts):
            implicit_font_family = _sample_implicit_readout_font(
                task_id=task_id,
                instance_seed=int(instance_seed),
                params=params,
            )
            with collect_traced_text_records() as drawn_text_records:
                with collect_semantic_marker_records() as marker_records:
                    with temporary_default_font_family(implicit_font_family):
                        output = generate_impl(self, instance_seed, params=params, max_attempts=max_attempts)
            output = _attach_implicit_readout_font(
                output,
                task_id=task_id,
                font_family=implicit_font_family,
            )
            output = _attach_illustration_art_style_metadata(output, task_id=task_id)
            return _attach_collected_visual_legibility(
                output,
                drawn_text_records=drawn_text_records,
                marker_records=marker_records,
            )

        cls.generate = _generate_with_text_collection  # type: ignore[method-assign]
    TASK_REGISTRY[task_id] = cls
    return cls


def create_task(task_id: str) -> Task:
    """Instantiate task by id."""
    if task_id not in TASK_REGISTRY:
        raise KeyError(task_id)
    return TASK_REGISTRY[task_id]()


def is_default_dataset_task(task_id: str) -> bool:
    """Return whether a registered task participates in default dataset builds."""

    if task_id not in TASK_REGISTRY:
        raise KeyError(task_id)
    return bool(getattr(TASK_REGISTRY[task_id], "default_dataset_enabled", True))


def list_task_ids() -> list[str]:
    """Return all registered task ids in deterministic order."""

    return sorted(TASK_REGISTRY)


def list_default_task_ids() -> list[str]:
    """Return registered task ids included in default dataset builds."""

    return [task_id for task_id in list_task_ids() if is_default_dataset_task(task_id)]
