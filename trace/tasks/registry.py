"""Task registry for TRACE generation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import re
from functools import wraps
from typing import Any, Dict, Mapping, Sequence, Type

from ..core.scene_package_migration import is_scene_package_task, parse_public_task_id
from ..core.taxonomy import resolve_task_query_id
from .base import Task, TaskOutput
from .shared.font_assets import font_role_trace, get_font_family_record, sample_font_family
from .shared.fixed_query import explicit_query_id_param, rewrite_public_query_output
from .shared.marker_legibility import collect_semantic_marker_records, semantic_marker_records_summary
from .shared.text_legibility import collect_traced_text_records, traced_text_records_summary
from .shared.text_rendering import temporary_default_font_family


_ALL_TASKS_REGISTERED = False
_ALL_TASKS_REGISTERING = False
_TASKS_REGISTERING_BY_ID: set[str] = set()


class _TaskRegistry(dict[str, Type[Task]]):
    """Registry mapping with lazy task-module loading.

    Direct task-id lookups import only the corresponding taxonomy-v0 public
    module. Collection-style operations import every discoverable task because
    callers asking for registry-wide views should see global failures.
    """

    def __contains__(self, key: object) -> bool:
        if dict.__contains__(self, key):
            return True
        if isinstance(key, str):
            ensure_task_registered(key)
        return dict.__contains__(self, key)

    def __getitem__(self, key: str) -> Type[Task]:
        ensure_task_registered(str(key))
        return dict.__getitem__(self, key)

    def get(self, key: object, default: Any = None) -> Any:
        if isinstance(key, str):
            ensure_task_registered(key)
        return dict.get(self, key, default)

    def keys(self):  # type: ignore[override]
        ensure_all_tasks_registered()
        return dict.keys(self)

    def items(self):  # type: ignore[override]
        ensure_all_tasks_registered()
        return dict.items(self)

    def values(self):  # type: ignore[override]
        ensure_all_tasks_registered()
        return dict.values(self)

    def __iter__(self):  # type: ignore[override]
        ensure_all_tasks_registered()
        return dict.__iter__(self)

    def __len__(self) -> int:
        ensure_all_tasks_registered()
        return dict.__len__(self)


TASK_REGISTRY: Dict[str, Type[Task]] = _TaskRegistry()
_V0_TASK_ID_PATTERN = re.compile(
    r"^task_(?P<domain>[a-z0-9_]+)__(?P<scene>[a-z0-9_]+)__(?P<objective>[a-z0-9_]+)$"
)


def _raw_task_registered(task_id: str) -> bool:
    """Return whether ``task_id`` is already registered without autoloading."""

    return dict.__contains__(TASK_REGISTRY, str(task_id))


def ensure_task_registered(task_id: str) -> None:
    """Import the direct public task module for ``task_id`` when possible."""

    global _ALL_TASKS_REGISTERED
    task_id = str(task_id)
    if _raw_task_registered(task_id) or task_id in _TASKS_REGISTERING_BY_ID:
        return
    try:
        parse_public_task_id(task_id)
    except ValueError:
        return

    _TASKS_REGISTERING_BY_ID.add(task_id)
    try:
        from .autoload import register_task_module

        register_task_module(task_id)
    finally:
        _TASKS_REGISTERING_BY_ID.discard(task_id)

    if _raw_task_registered(task_id):
        return
    if _ALL_TASKS_REGISTERED:
        return


def ensure_scene_tasks_registered(domain: str, scene_id: str) -> None:
    """Import all public task modules for one scene."""

    from .autoload import register_scene_task_modules

    register_scene_task_modules(str(domain), str(scene_id))


def ensure_all_tasks_registered() -> None:
    """Import all discoverable task modules into ``TASK_REGISTRY``."""

    global _ALL_TASKS_REGISTERED, _ALL_TASKS_REGISTERING
    if _ALL_TASKS_REGISTERED or _ALL_TASKS_REGISTERING:
        return
    _ALL_TASKS_REGISTERING = True
    try:
        from .autoload import register_all_task_modules

        register_all_task_modules()
    finally:
        _ALL_TASKS_REGISTERING = False
    _ALL_TASKS_REGISTERED = True


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
    scene_id = getattr(cls, "scene_id", None)
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError(f"task '{task_id}' must define non-empty string attribute 'domain'")
    migrated_task = is_scene_package_task(task_id_text, domain=str(domain))
    if migrated_task:
        if scene_id is not None:
            raise ValueError(f"migrated scene-package task '{task_id}' must not define 'scene_id'")
    if v0_match is not None:
        task_domain = str(v0_match.group("domain"))
        if task_domain != str(domain):
            raise ValueError(
                "taxonomy-v0 task_id domain segment must match class domain "
                f"'{domain}' (got: {task_id_text})"
            )


def _coerce_supported_query_ids(raw: Any) -> tuple[str, ...]:
    """Return a normalized query-id tuple from a class attribute."""

    if raw is None:
        return tuple()
    if isinstance(raw, str):
        values = (raw,)
    else:
        try:
            values = tuple(raw)
        except TypeError:
            values = (raw,)
    return tuple(str(value) for value in values if str(value))


def _ensure_supported_query_ids(cls: Type[Task], *, task_id: str) -> tuple[str, ...]:
    """Attach a public-query support declaration when a task has a single clear query."""

    supported = _coerce_supported_query_ids(getattr(cls, "supported_query_ids", ()))
    if not supported:
        supported = _coerce_supported_query_ids(getattr(cls, "supported_queries", ()))
    if supported:
        cls.supported_query_ids = supported  # type: ignore[attr-defined]
        return supported

    for attr in ("fixed_query_id", "query_id"):
        value = getattr(cls, attr, None)
        if value is not None and str(value):
            supported = (str(value),)
            cls.supported_query_ids = supported  # type: ignore[attr-defined]
            return supported

    try:
        objective = parse_public_task_id(str(task_id)).objective_contract
    except Exception:
        objective = ""
    supported = (str(objective),) if str(objective) else tuple()
    if supported:
        cls.supported_query_ids = supported  # type: ignore[attr-defined]
    return supported


def _validate_requested_query_id(params: Mapping[str, Any], *, supported_query_ids: Sequence[str], task_id: str) -> None:
    """Reject caller-provided query ids not owned by this public task."""

    requested = explicit_query_id_param(params or {}, allow_default=True)
    if requested is None or str(requested) == "default":
        return
    supported = tuple(str(value) for value in supported_query_ids if str(value))
    if str(requested) not in set(supported):
        raise ValueError(f"unsupported query_id for {task_id}: {requested}; supported: {supported}")


def _normalize_public_query_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """Return params with legacy query_variant copied into canonical query_id."""

    normalized = dict(params or {})
    requested = explicit_query_id_param(normalized, allow_default=True)
    if requested is not None and str(requested) != "default" and normalized.get("query_id") is None:
        normalized["query_id"] = str(requested)
    return normalized


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
    if dict.__contains__(TASK_REGISTRY, task_id):
        raise KeyError(f"duplicate task_id: {task_id}")
    v0_match = _V0_TASK_ID_PATTERN.match(task_id)
    task_parts = parse_public_task_id(task_id)
    supported_query_ids = _ensure_supported_query_ids(cls, task_id=task_id)
    migrated_task = is_scene_package_task(task_id, domain=str(task_parts.domain))
    generate_impl = cls.generate
    if str(getattr(cls, "domain", "")) == "charts":
        from .charts.shared.render_audit_defaults import wrap_charts_generation

        generate_impl = wrap_charts_generation(
            generate_impl,
            task_id=str(task_id),
            scene_id=str(task_parts.scene_id),
        )
    if str(getattr(cls, "domain", "")) == "pages":
        from .pages.shared.render_audit_defaults import wrap_pages_generation, wrap_pages_scene_generation

        if migrated_task:
            generate_impl = wrap_pages_scene_generation(
                generate_impl,
                task_id=str(task_id),
                scene_id=str(task_parts.scene_id),
            )
        else:
            generate_impl = wrap_pages_generation(
                generate_impl,
                task_id=str(task_id),
                scene_id=str(getattr(cls, "scene_id", "")),
            )
    if v0_match is not None:
        original_generate = generate_impl
        taxonomy_scene_id = str(v0_match.group("scene"))

        @wraps(original_generate)
        def _generate_with_public_query_contract(self, instance_seed, *, params, max_attempts):
            params = _normalize_public_query_params(params)
            _validate_requested_query_id(
                params,
                supported_query_ids=supported_query_ids,
                task_id=task_id,
            )
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
    ensure_task_registered(str(task_id))
    if not dict.__contains__(TASK_REGISTRY, str(task_id)):
        ensure_all_tasks_registered()
    if not dict.__contains__(TASK_REGISTRY, str(task_id)):
        raise KeyError(task_id)
    return dict.__getitem__(TASK_REGISTRY, str(task_id))()


def is_default_dataset_task(task_id: str) -> bool:
    """Return whether a registered task participates in default dataset builds."""

    ensure_task_registered(str(task_id))
    if not dict.__contains__(TASK_REGISTRY, str(task_id)):
        ensure_all_tasks_registered()
    if not dict.__contains__(TASK_REGISTRY, str(task_id)):
        raise KeyError(task_id)
    return bool(getattr(dict.__getitem__(TASK_REGISTRY, str(task_id)), "default_dataset_enabled", True))


def list_task_ids() -> list[str]:
    """Return all registered task ids in deterministic order."""

    ensure_all_tasks_registered()
    return sorted(dict.keys(TASK_REGISTRY))


def list_default_task_ids() -> list[str]:
    """Return registered task ids included in default dataset builds."""

    return [task_id for task_id in list_task_ids() if is_default_dataset_task(task_id)]
