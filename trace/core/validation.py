"""Pre-finalize validation for TRACE dataset builds."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from . import error_codes
from .canonical import canonical_json_bytes
from .hash_utils import blake3_file, blake3_hex
from .identity import compute_instance_id
from .trace_store import read_trace_shard


@dataclass(frozen=True)
class ValidationError:
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
    return code.split("_", 1)[0]


def _err(code: str, message: str, **context: Any) -> ValidationError:
    return ValidationError(
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
    "prompt",
    "images",
    "answer_gt",
    "evidence_gt",
    "task_complexity",
    "trace_ref",
    "versions",
]


def _validate_schema(instance: Mapping[str, Any]) -> List[ValidationError]:
    errors: List[ValidationError] = []
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
    errors: List[ValidationError] = []

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
