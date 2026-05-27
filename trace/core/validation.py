"""Pre-finalize validation for TRACE dataset builds."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Mapping

from . import error_codes
from .canonical import canonical_json_bytes
from .hash_utils import blake3_file, blake3_hex
from .identity import compute_instance_id
from .prompts import load_prompt_bundle
from .prompts.schema import REQUIRED_PROMPT_VARIANTS
from .reward_contracts import validate_reward_contract_payload
from .trace_store import read_trace_shard


@dataclass(frozen=True)
class _ValidationError:
    """Structured validation error for machine/human reporting."""

    error_code: str
    message: str
    category: str
    context: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category,
        }
        out.update(self.context)
        return out


def _category_for_code(code: str) -> str:
    """Derive top-level error category prefix from an error code string."""
    return code.split("_", 1)[0]


def _err(code: str, message: str, **context: Any) -> _ValidationError:
    """Build a structured validation error with derived category metadata."""
    return _ValidationError(
        error_code=code,
        message=message,
        category=_category_for_code(code),
        context=context,
    )


_REQUIRED_INSTANCE_FIELDS = [
    "instance_version",
    "instance_id",
    "instance_seed",
    "domain",
    "task_group",
    "task",
    "scene_id",
    "query_id",
    "prompt",
    "prompt_variants",
    "images",
    "answer_gt",
    "evidence_gt",
    "reward_contract",
    "task_complexity",
    "trace_ref",
    "versions",
]

_PROMPT_PLACEHOLDER_PATTERN = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")


def _to_int(value: Any) -> int | None:
    """Best-effort integer coercion used for metadata validation checks."""
    try:
        return int(value)
    except Exception:
        return None


def _validate_prompt_contract(instance: Mapping[str, Any], trace_record: Mapping[str, Any]) -> List[_ValidationError]:
    """Validate prompt metadata/bundle conformance for one train/trace pair."""
    errors: List[_ValidationError] = []
    iid = instance.get("instance_id", "<missing>")
    prompt_text = instance.get("prompt")

    if isinstance(prompt_text, str):
        unresolved_tokens = sorted({match.group(0) for match in _PROMPT_PLACEHOLDER_PATTERN.finditer(prompt_text)})
        if unresolved_tokens:
            errors.append(
                _err(
                    error_codes.PROMPT_UNRESOLVED_PLACEHOLDER,
                    "prompt contains unresolved template placeholder(s)",
                    instance_id=iid,
                    field_path="prompt",
                    unresolved_tokens=unresolved_tokens,
                )
            )

    prompt_variants = instance.get("prompt_variants")
    if prompt_variants is not None:
        if not isinstance(prompt_variants, Mapping):
            errors.append(
                _err(
                    error_codes.SCHEMA_TYPE_MISMATCH,
                    "prompt_variants must be a mapping when present",
                    instance_id=iid,
                    field_path="prompt_variants",
                )
            )
        else:
            for variant_key, variant_prompt in prompt_variants.items():
                if not isinstance(variant_prompt, str):
                    errors.append(
                        _err(
                            error_codes.SCHEMA_TYPE_MISMATCH,
                            "prompt_variants values must be strings",
                            instance_id=iid,
                            field_path=f"prompt_variants.{variant_key}",
                        )
                    )
                    continue
                unresolved_tokens = sorted(
                    {match.group(0) for match in _PROMPT_PLACEHOLDER_PATTERN.finditer(variant_prompt)}
                )
                if unresolved_tokens:
                    errors.append(
                        _err(
                            error_codes.PROMPT_UNRESOLVED_PLACEHOLDER,
                            "prompt_variants contains unresolved template placeholder(s)",
                            instance_id=iid,
                            field_path=f"prompt_variants.{variant_key}",
                            unresolved_tokens=unresolved_tokens,
                        )
                    )

    query_spec = trace_record.get("query_spec")
    if not isinstance(query_spec, Mapping):
        errors.append(
            _err(
                error_codes.PROMPT_METADATA_MISSING,
                "trace query_spec is missing or invalid for prompt validation",
                instance_id=iid,
                field_path="query_spec",
            )
        )
        return errors

    prompt_variant = query_spec.get("prompt_variant")
    if not isinstance(prompt_variant, Mapping):
        errors.append(
            _err(
                error_codes.PROMPT_METADATA_MISSING,
                "trace query_spec.prompt_variant is missing or invalid",
                instance_id=iid,
                field_path="query_spec.prompt_variant",
            )
        )
        return errors

    required_meta_fields = (
        "prompt_bundle_id",
        "scene_key",
        "task_key",
        "scene_template_index",
        "task_template_index",
        "variant_count_by_key",
    )
    for field in required_meta_fields:
        if field not in prompt_variant:
            errors.append(
                _err(
                    error_codes.PROMPT_METADATA_MISSING,
                    f"missing required prompt metadata field '{field}'",
                    instance_id=iid,
                    field_path=f"query_spec.prompt_variant.{field}",
                )
            )

    bundle_id = str(prompt_variant.get("prompt_bundle_id", "")).strip()
    scene_key = str(prompt_variant.get("scene_key", "")).strip()
    task_key = str(prompt_variant.get("task_key", "")).strip()
    query_key_raw = prompt_variant.get("query_key")
    query_key = str(query_key_raw).strip() if query_key_raw not in (None, "") else ""
    variant_count_by_key = prompt_variant.get("variant_count_by_key")

    if not bundle_id:
        errors.append(
            _err(
                error_codes.PROMPT_METADATA_MISSING,
                "prompt bundle id is empty",
                instance_id=iid,
                field_path="query_spec.prompt_variant.prompt_bundle_id",
            )
        )
    if not scene_key:
        errors.append(
            _err(
                error_codes.PROMPT_METADATA_MISSING,
                "scene_key is empty",
                instance_id=iid,
                field_path="query_spec.prompt_variant.scene_key",
            )
        )
    if not task_key:
        errors.append(
            _err(
                error_codes.PROMPT_METADATA_MISSING,
                "task_key is empty",
                instance_id=iid,
                field_path="query_spec.prompt_variant.task_key",
            )
        )
    if not isinstance(variant_count_by_key, Mapping):
        errors.append(
            _err(
                error_codes.PROMPT_METADATA_MISSING,
                "variant_count_by_key must be a mapping",
                instance_id=iid,
                field_path="query_spec.prompt_variant.variant_count_by_key",
            )
        )

    if errors:
        return errors

    trace_taxonomy = trace_record.get("taxonomy") if isinstance(trace_record.get("taxonomy"), Mapping) else {}
    taxonomy_source = trace_taxonomy.get("source") if isinstance(trace_taxonomy.get("source"), Mapping) else {}
    domain = str(
        prompt_variant.get("prompt_domain")
        or taxonomy_source.get("prompt_domain")
        or taxonomy_source.get("implementation_domain")
        or instance.get("domain", "")
    )
    task_group = str(
        prompt_variant.get("prompt_task_group")
        or taxonomy_source.get("prompt_task_group")
        or taxonomy_source.get("implementation_task_group")
        or instance.get("task_group", "")
    )
    try:
        bundle = load_prompt_bundle(domain=domain, task_group=task_group, bundle_id=bundle_id)
    except FileNotFoundError as exc:
        errors.append(
            _err(
                error_codes.PROMPT_BUNDLE_NOT_FOUND,
                str(exc),
                instance_id=iid,
                prompt_bundle_id=bundle_id,
                domain=domain,
                task_group=task_group,
            )
        )
        return errors
    except Exception as exc:
        errors.append(
            _err(
                error_codes.PROMPT_BUNDLE_INVALID,
                f"invalid prompt bundle: {exc}",
                instance_id=iid,
                prompt_bundle_id=bundle_id,
                domain=domain,
                task_group=task_group,
            )
        )
        return errors

    if scene_key not in bundle.scene_templates:
        errors.append(
            _err(
                error_codes.PROMPT_KEY_MISSING,
                "prompt scene key not found in bundle",
                instance_id=iid,
                prompt_bundle_id=bundle_id,
                scene_key=scene_key,
            )
        )
    if task_key not in bundle.task_templates:
        errors.append(
            _err(
                error_codes.PROMPT_KEY_MISSING,
                "prompt task key not found in bundle",
                instance_id=iid,
                prompt_bundle_id=bundle_id,
                task_key=task_key,
            )
        )
    if query_key and query_key not in bundle.query_templates:
        errors.append(
            _err(
                error_codes.PROMPT_KEY_MISSING,
                "prompt query key not found in bundle",
                instance_id=iid,
                prompt_bundle_id=bundle_id,
                query_key=query_key,
            )
        )
    if errors:
        return errors

    scene_templates = bundle.scene_templates[scene_key]
    task_templates = bundle.task_templates[task_key]
    query_templates = (
        bundle.query_templates[query_key]
        if query_key
        else ()
    )
    mode_templates = dict(bundle.answer_or_evidence_templates)
    if len(scene_templates) != REQUIRED_PROMPT_VARIANTS:
        errors.append(
            _err(
                error_codes.PROMPT_BUNDLE_INVALID,
                "scene template variant count does not match required count",
                instance_id=iid,
                prompt_bundle_id=bundle_id,
                scene_key=scene_key,
                required_count=REQUIRED_PROMPT_VARIANTS,
                actual_count=len(scene_templates),
            )
        )
    if len(task_templates) != REQUIRED_PROMPT_VARIANTS:
        errors.append(
            _err(
                error_codes.PROMPT_BUNDLE_INVALID,
                "task template variant count does not match required count",
                instance_id=iid,
                prompt_bundle_id=bundle_id,
                task_key=task_key,
                required_count=REQUIRED_PROMPT_VARIANTS,
                actual_count=len(task_templates),
            )
        )
    if query_key and len(query_templates) != REQUIRED_PROMPT_VARIANTS:
        errors.append(
            _err(
                error_codes.PROMPT_BUNDLE_INVALID,
                "query template variant count does not match required count",
                instance_id=iid,
                prompt_bundle_id=bundle_id,
                query_key=query_key,
                required_count=REQUIRED_PROMPT_VARIANTS,
                actual_count=len(query_templates),
            )
        )

    scene_count_key = f"scene:{scene_key}"
    task_count_key = f"task:{task_key}"
    query_count_key = f"query:{query_key}" if query_key else None
    observed_scene_count = _to_int(variant_count_by_key.get(scene_count_key))
    observed_task_count = _to_int(variant_count_by_key.get(task_count_key))
    observed_query_count = (
        _to_int(variant_count_by_key.get(query_count_key))
        if query_count_key is not None
        else None
    )
    expected_scene_count = len(scene_templates)
    expected_task_count = len(task_templates)
    expected_query_count = (len(query_templates) if query_key else None)
    mode_key = str(prompt_variant.get("answer_or_evidence_key", "")).strip() if mode_templates else ""
    mode_query_id_index = _to_int(prompt_variant.get("answer_or_evidence_query_id_index")) if mode_templates else None
    expected_mode_count = len(mode_templates[mode_key]) if mode_key in mode_templates else None

    if observed_scene_count is None:
        errors.append(
            _err(
                error_codes.PROMPT_METADATA_MISSING,
                "missing scene variant count in prompt metadata",
                instance_id=iid,
                field_path=f"query_spec.prompt_variant.variant_count_by_key.{scene_count_key}",
            )
        )
    elif observed_scene_count != expected_scene_count:
        errors.append(
            _err(
                error_codes.PROMPT_VARIANT_COUNT_MISMATCH,
                "scene variant count mismatch between metadata and bundle",
                instance_id=iid,
                prompt_bundle_id=bundle_id,
                scene_key=scene_key,
                expected_count=expected_scene_count,
                actual_count=observed_scene_count,
            )
        )

    if observed_task_count is None:
        errors.append(
            _err(
                error_codes.PROMPT_METADATA_MISSING,
                "missing query id count in prompt metadata",
                instance_id=iid,
                field_path=f"query_spec.prompt_variant.variant_count_by_key.{task_count_key}",
            )
        )
    elif observed_task_count != expected_task_count:
        errors.append(
            _err(
                error_codes.PROMPT_VARIANT_COUNT_MISMATCH,
                "query id count mismatch between metadata and bundle",
                instance_id=iid,
                prompt_bundle_id=bundle_id,
                task_key=task_key,
                expected_count=expected_task_count,
                actual_count=observed_task_count,
            )
        )
    if query_count_key is not None:
        if observed_query_count is None:
            errors.append(
                _err(
                    error_codes.PROMPT_METADATA_MISSING,
                    "missing query id count in prompt metadata",
                    instance_id=iid,
                    field_path=f"query_spec.prompt_variant.variant_count_by_key.{query_count_key}",
                )
            )
        elif observed_query_count != expected_query_count:
            errors.append(
                _err(
                    error_codes.PROMPT_VARIANT_COUNT_MISMATCH,
                    "query id count mismatch between metadata and bundle",
                    instance_id=iid,
                    prompt_bundle_id=bundle_id,
                    query_key=query_key,
                    expected_count=expected_query_count,
                    actual_count=observed_query_count,
                )
            )

    if mode_templates:
        if not mode_key:
            errors.append(
                _err(
                    error_codes.PROMPT_METADATA_MISSING,
                    "missing answer_or_evidence key in prompt metadata",
                    instance_id=iid,
                    field_path="query_spec.prompt_variant.answer_or_evidence_key",
                )
            )
        elif mode_key not in mode_templates:
            errors.append(
                _err(
                    error_codes.PROMPT_KEY_MISSING,
                    "prompt answer_or_evidence key not found in bundle",
                    instance_id=iid,
                    prompt_bundle_id=bundle_id,
                    answer_or_evidence_key=mode_key,
                )
            )
        else:
            mode_count_key = f"answer_or_evidence:{mode_key}"
            observed_mode_count = _to_int(variant_count_by_key.get(mode_count_key))
            if observed_mode_count is None:
                errors.append(
                    _err(
                        error_codes.PROMPT_METADATA_MISSING,
                        "missing answer_or_evidence variant count in prompt metadata",
                        instance_id=iid,
                        field_path=f"query_spec.prompt_variant.variant_count_by_key.{mode_count_key}",
                    )
                )
            elif observed_mode_count != expected_mode_count:
                errors.append(
                    _err(
                        error_codes.PROMPT_VARIANT_COUNT_MISMATCH,
                        "answer_or_evidence variant count mismatch between metadata and bundle",
                        instance_id=iid,
                        prompt_bundle_id=bundle_id,
                        answer_or_evidence_key=mode_key,
                        expected_count=expected_mode_count,
                        actual_count=observed_mode_count,
                    )
                )

    scene_template_index = _to_int(prompt_variant.get("scene_template_index"))
    task_template_index = _to_int(prompt_variant.get("task_template_index"))
    query_template_index = (
        _to_int(prompt_variant.get("query_template_index"))
        if query_key
        else None
    )
    if (
        scene_template_index is None
        or scene_template_index < 0
        or scene_template_index >= expected_scene_count
    ):
        errors.append(
            _err(
                error_codes.PROMPT_VARIANT_INDEX_OUT_OF_RANGE,
                "scene variant index out of range",
                instance_id=iid,
                prompt_bundle_id=bundle_id,
                scene_key=scene_key,
                query_id_index=prompt_variant.get("scene_template_index"),
                variant_count=expected_scene_count,
            )
        )
    if task_template_index is None or task_template_index < 0 or task_template_index >= expected_task_count:
        errors.append(
            _err(
                error_codes.PROMPT_VARIANT_INDEX_OUT_OF_RANGE,
                "query id index out of range",
                instance_id=iid,
                prompt_bundle_id=bundle_id,
                task_key=task_key,
                query_id_index=prompt_variant.get("task_template_index"),
                variant_count=expected_task_count,
            )
        )
    if query_key and expected_query_count is not None:
        if (
            query_template_index is None
            or query_template_index < 0
            or query_template_index >= expected_query_count
        ):
            errors.append(
                _err(
                    error_codes.PROMPT_VARIANT_INDEX_OUT_OF_RANGE,
                    "query template index out of range",
                    instance_id=iid,
                    prompt_bundle_id=bundle_id,
                    query_key=query_key,
                    query_id_index=prompt_variant.get("query_template_index"),
                    variant_count=expected_query_count,
                )
            )
    if mode_templates and mode_key in mode_templates and expected_mode_count is not None:
        if mode_query_id_index is None or mode_query_id_index < 0 or mode_query_id_index >= expected_mode_count:
            errors.append(
                _err(
                    error_codes.PROMPT_VARIANT_INDEX_OUT_OF_RANGE,
                    "answer_or_evidence variant index out of range",
                    instance_id=iid,
                    prompt_bundle_id=bundle_id,
                    answer_or_evidence_key=mode_key,
                    query_id_index=prompt_variant.get("answer_or_evidence_query_id_index"),
                    variant_count=expected_mode_count,
                )
            )

    required_slots = list(bundle.required_slots_by_key.get(f"scene:{scene_key}", ()))
    required_slots.extend(bundle.required_slots_by_key.get(f"task:{task_key}", ()))
    if query_key:
        required_slots.extend(bundle.required_slots_by_key.get(f"query:{query_key}", ()))
    if mode_templates and mode_key:
        required_slots.extend(bundle.required_slots_by_key.get(f"answer_or_evidence:{mode_key}", ()))
    if required_slots:
        slot_values = prompt_variant.get("slot_values")
        if not isinstance(slot_values, Mapping):
            errors.append(
                _err(
                    error_codes.PROMPT_REQUIRED_SLOT_MISSING,
                    "prompt metadata is missing slot_values for required slots",
                    instance_id=iid,
                    field_path="query_spec.prompt_variant.slot_values",
                    required_slots=sorted(set(str(slot) for slot in required_slots)),
                )
            )
        else:
            missing_slots = sorted(
                {
                    str(slot)
                    for slot in required_slots
                    if str(slot) not in slot_values or slot_values.get(str(slot)) in (None, "")
                }
            )
            if missing_slots:
                errors.append(
                    _err(
                        error_codes.PROMPT_REQUIRED_SLOT_MISSING,
                        "required prompt slot values are missing in metadata",
                        instance_id=iid,
                        field_path="query_spec.prompt_variant.slot_values",
                        missing_slots=missing_slots,
                    )
                )

    if mode_templates:
        if not isinstance(prompt_variants, Mapping):
            errors.append(
                _err(
                    error_codes.PROMPT_METADATA_MISSING,
                    "prompt_variants is required when bundle defines answer_or_evidence templates",
                    instance_id=iid,
                    field_path="prompt_variants",
                )
            )
        else:
            missing_modes = sorted(
                [
                    mode_name
                    for mode_name in mode_templates.keys()
                    if str(prompt_variants.get(mode_name, "")).strip() == ""
                ]
            )
            if missing_modes:
                errors.append(
                    _err(
                        error_codes.PROMPT_METADATA_MISSING,
                        "prompt_variants is missing required answer_or_evidence prompts",
                        instance_id=iid,
                        field_path="prompt_variants",
                        missing_modes=missing_modes,
                    )
                )
            elif mode_key and isinstance(prompt_text, str) and prompt_text.strip() and str(prompt_variants.get(mode_key, "")).strip() != prompt_text.strip():
                errors.append(
                    _err(
                        error_codes.PROMPT_METADATA_MISSING,
                        "prompt text does not match active prompt_variants entry",
                        instance_id=iid,
                        field_path=f"prompt_variants.{mode_key}",
                    )
                )

    return errors


def _validate_schema(instance: Mapping[str, Any]) -> List[_ValidationError]:
    """Validate required TrainInstance fields and envelope-schema invariants."""
    errors: List[_ValidationError] = []
    iid = instance.get("instance_id", "<missing>")

    for field in _REQUIRED_INSTANCE_FIELDS:
        if field not in instance:
            errors.append(
                _err(
                    error_codes.SCHEMA_MISSING_FIELD,
                    f"missing required field '{field}'",
                    instance_id=iid,
                    field_path=field,
                )
            )

    if "answer_gt" in instance:
        answer = instance["answer_gt"]
        if not isinstance(answer, dict) or "type" not in answer or "value" not in answer:
            errors.append(
                _err(
                    error_codes.SCHEMA_TYPE_MISMATCH,
                    "answer_gt must be an object with keys {type, value}",
                    instance_id=iid,
                    field_path="answer_gt",
                )
            )

    if "evidence_gt" in instance:
        evidence = instance["evidence_gt"]
        if not isinstance(evidence, dict) or "type" not in evidence or "value" not in evidence:
            errors.append(
                _err(
                    error_codes.SCHEMA_TYPE_MISMATCH,
                    "evidence_gt must be an object with keys {type, value}",
                    instance_id=iid,
                    field_path="evidence_gt",
                )
            )

    if "reward_contract" in instance:
        reward_contract = instance["reward_contract"]
        reward_contract_error = validate_reward_contract_payload(
            reward_contract,
            answer_type=instance.get("answer_gt", {}).get("type") if isinstance(instance.get("answer_gt"), dict) else None,
            evidence_type=(
                instance.get("evidence_gt", {}).get("type") if isinstance(instance.get("evidence_gt"), dict) else None
            ),
        )
        if reward_contract_error is not None:
            errors.append(
                _err(
                    error_codes.SCHEMA_INVALID_VALUE,
                    reward_contract_error,
                    instance_id=iid,
                    field_path="reward_contract",
                )
            )

    if "images" in instance and not isinstance(instance["images"], list):
        errors.append(
            _err(
                error_codes.SCHEMA_TYPE_MISMATCH,
                "images must be a list",
                instance_id=iid,
                field_path="images",
            )
        )

    # Catch canonicalization failures early (non-string key/non-finite/unsupported types).
    try:
        canonical_json_bytes(dict(instance))
    except Exception as exc:
        code = getattr(exc, "code", error_codes.SCHEMA_CANONICALIZATION_FAILED)
        errors.append(
            _err(
                code,
                str(exc),
                instance_id=iid,
                field_path="<instance>",
            )
        )

    return errors


def validate_dataset(
    instances: List[Dict[str, Any]],
    *,
    staging_root: str | Path,
    expected_task_counts: Mapping[str, int],
    dataset_id: str,
    expected_instance_version: str,
) -> Dict[str, Any]:
    """Run required pre-finalize checks and return a full validation report."""
    root = Path(staging_root)
    errors: List[_ValidationError] = []

    for inst in instances:
        errors.extend(_validate_schema(inst))

    versions = sorted({str(inst.get("instance_version")) for inst in instances})
    if len(versions) > 1:
        errors.append(
            _err(
                error_codes.VERSION_MIXED_INSTANCE_VERSION,
                f"mixed instance versions detected: {versions}",
                field_path="instance_version",
            )
        )
    for inst in instances:
        iid = inst.get("instance_id", "<missing>")
        version = inst.get("instance_version")
        if version != expected_instance_version:
            errors.append(
                _err(
                    error_codes.VERSION_UNSUPPORTED_INSTANCE_VERSION,
                    f"unexpected instance_version {version!r}, expected {expected_instance_version!r}",
                    instance_id=iid,
                    field_path="instance_version",
                )
            )

    trace_cache: Dict[str, List[Dict[str, Any]]] = {}
    for inst in instances:
        iid = inst.get("instance_id", "<missing>")

        recomputed_id = compute_instance_id(inst)
        if recomputed_id != iid:
            errors.append(
                _err(
                    error_codes.IDENTITY_INSTANCE_ID_MISMATCH,
                    "instance_id does not match canonical identity payload",
                    instance_id=iid,
                    recomputed_instance_id=recomputed_id,
                )
            )

        trace_ref = inst.get("trace_ref")
        if not isinstance(trace_ref, dict):
            errors.append(
                _err(
                    error_codes.TRACE_REF_MISSING,
                    "trace_ref is missing or invalid",
                    instance_id=iid,
                    field_path="trace_ref",
                )
            )
            continue

        shard_id = trace_ref.get("shard_id")
        line_index = trace_ref.get("line_index")
        trace_hash = trace_ref.get("trace_record_hash")
        shard_path = root / "traces" / str(shard_id)

        if not shard_path.exists():
            errors.append(
                _err(
                    error_codes.TRACE_REF_NOT_FOUND,
                    "trace shard not found",
                    instance_id=iid,
                    trace_ref=trace_ref,
                )
            )
            continue

        if shard_id not in trace_cache:
            trace_cache[str(shard_id)] = read_trace_shard(shard_path)

        records = trace_cache[str(shard_id)]
        if not isinstance(line_index, int) or line_index < 0 or line_index >= len(records):
            errors.append(
                _err(
                    error_codes.TRACE_REF_INDEX_OUT_OF_RANGE,
                    "trace_ref line_index out of range",
                    instance_id=iid,
                    trace_ref=trace_ref,
                )
            )
            continue

        record = records[line_index]
        actual_hash = blake3_hex(canonical_json_bytes(record))
        if actual_hash != trace_hash:
            errors.append(
                _err(
                    error_codes.TRACE_REF_HASH_MISMATCH,
                    "trace_ref hash mismatch",
                    instance_id=iid,
                    expected_trace_hash=trace_hash,
                    actual_trace_hash=actual_hash,
                )
            )

        if record.get("instance_id") != iid:
            errors.append(
                _err(
                    error_codes.TRACE_REF_HASH_MISMATCH,
                    "trace record instance_id mismatch",
                    instance_id=iid,
                    trace_instance_id=record.get("instance_id"),
                )
            )

        errors.extend(_validate_prompt_contract(inst, record))

        trace_reward_contract = record.get("reward_contract")
        if trace_reward_contract is None:
            errors.append(
                _err(
                    error_codes.SCHEMA_MISSING_FIELD,
                    "trace record is missing reward_contract",
                    instance_id=iid,
                    field_path="trace.reward_contract",
                )
            )
        else:
            reward_contract_error = validate_reward_contract_payload(
                trace_reward_contract,
                answer_type=inst.get("answer_gt", {}).get("type") if isinstance(inst.get("answer_gt"), dict) else None,
                evidence_type=inst.get("evidence_gt", {}).get("type") if isinstance(inst.get("evidence_gt"), dict) else None,
            )
            if reward_contract_error is not None:
                errors.append(
                    _err(
                        error_codes.SCHEMA_INVALID_VALUE,
                        reward_contract_error,
                        instance_id=iid,
                        field_path="trace.reward_contract",
                    )
                )
            elif trace_reward_contract != inst.get("reward_contract"):
                errors.append(
                    _err(
                        error_codes.SCHEMA_INVALID_VALUE,
                        "trace reward_contract must match the training record reward_contract",
                        instance_id=iid,
                        field_path="trace.reward_contract",
                    )
                )

        for i, image in enumerate(inst.get("images", [])):
            rel_path = image.get("path")
            image_hash = image.get("image_hash")
            field_prefix = f"images[{i}]"
            if not isinstance(rel_path, str):
                errors.append(
                    _err(
                        error_codes.IMAGE_FILE_NOT_FOUND,
                        "image path missing or non-string",
                        instance_id=iid,
                        field_path=f"{field_prefix}.path",
                    )
                )
                continue
            rel = Path(rel_path)
            if rel.is_absolute():
                errors.append(
                    _err(
                        error_codes.IMAGE_PATH_NOT_RELATIVE,
                        "image path must be dataset-root-relative",
                        instance_id=iid,
                        field_path=f"{field_prefix}.path",
                        image_path=rel_path,
                    )
                )
                continue
            full_path = root / rel
            if not full_path.exists():
                errors.append(
                    _err(
                        error_codes.IMAGE_FILE_NOT_FOUND,
                        "image file not found",
                        instance_id=iid,
                        field_path=f"{field_prefix}.path",
                        image_path=rel_path,
                    )
                )
                continue
            if not image_hash:
                errors.append(
                    _err(
                        error_codes.IMAGE_HASH_MISSING,
                        "image_hash is missing",
                        instance_id=iid,
                        field_path=f"{field_prefix}.image_hash",
                    )
                )
                continue
            actual_image_hash = blake3_file(full_path)
            if actual_image_hash != image_hash:
                errors.append(
                    _err(
                        error_codes.IMAGE_HASH_MISMATCH,
                        "image hash mismatch",
                        instance_id=iid,
                        image_path=rel_path,
                        expected_image_hash=image_hash,
                        actual_image_hash=actual_image_hash,
                    )
                )

    observed_counts = Counter(str(inst.get("task")) for inst in instances)
    for task_id, expected_count in expected_task_counts.items():
        have = int(observed_counts.get(task_id, 0))
        if have < int(expected_count):
            errors.append(
                _err(
                    error_codes.COUNT_PER_TASK_SHORTFALL,
                    "accepted count below expectation",
                    task=task_id,
                    expected_count=int(expected_count),
                    actual_count=have,
                )
            )
    expected_set = set(expected_task_counts)
    for task_id, have in observed_counts.items():
        if task_id not in expected_set:
            errors.append(
                _err(
                    error_codes.COUNT_UNEXPECTED_TASK_PRESENT,
                    "unexpected task appears in build output",
                    task=task_id,
                    actual_count=int(have),
                )
            )

    ordered = sorted(
        errors,
        key=lambda err: (
            err.error_code,
            str(err.context.get("instance_id", "")),
            str(err.context.get("field_path", "")),
            err.message,
        ),
    )

    error_counts_by_code = Counter(err.error_code for err in ordered)
    error_counts_by_category = Counter(err.category for err in ordered)

    report = {
        "total_errors": int(len(ordered)),
        "error_counts_by_code": dict(sorted(error_counts_by_code.items())),
        "error_counts_by_category": dict(sorted(error_counts_by_category.items())),
        "errors": [err.to_dict() for err in ordered],
        "build_context": {
            "dataset_id": dataset_id,
            "temp_path": str(root),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }
    return report
