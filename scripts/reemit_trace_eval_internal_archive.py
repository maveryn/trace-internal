#!/usr/bin/env python3
"""Re-emit a legacy TRACE archive spool without host-local paths or credentials.

The legacy archive schema is intentionally retained: logical run/model/seed/
benchmark/stage identities, record ids, request hashes, and rich provenance are
unchanged.  Only explicitly mapped machine-local roots are rewritten to stable
``trace-local-ref://`` references.  Any unmapped path or credential fails the
operation before the output spool is eligible for upload.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

try:
    from scripts.final25_hf_archive_lib import (
        ArchiveIntegrityError,
        ArchiveValidationError,
        _atomic_write_bytes,
        _is_secret_key,
        canonical_json,
        emit_slice_ready,
        load_descriptor,
        sha256_bytes,
        sha256_file,
    )
except ModuleNotFoundError:  # Supports direct ``python scripts/...`` invocation.
    from final25_hf_archive_lib import (
        ArchiveIntegrityError,
        ArchiveValidationError,
        _atomic_write_bytes,
        _is_secret_key,
        canonical_json,
        emit_slice_ready,
        load_descriptor,
        sha256_bytes,
        sha256_file,
    )


SCRUB_SCHEMA_VERSION = "trace-eval-internal-archive-scrub-v1"
LOCAL_REFERENCE_SCHEME = "trace-local-ref://"
LABEL_RE = re.compile(r"[a-z0-9][a-z0-9._-]*\Z")
KNOWN_MACHINE_ROOT_RE = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:"
    r"/dev/shm|/home|/tmp|/var/tmp|/private/tmp|/Users|/root|/mnt|/workspace|"
    r"file://|~/"
    r")"
)
ABSOLUTE_POSIX_PATH_RE = re.compile(
    r"(?:^|(?<=[\s\"'=(\[:]))/(?!/)"
    r"(?:[A-Za-z0-9._~-]+/)+[A-Za-z0-9._~:@%+=,-]+"
)
CREDENTIAL_VALUE_PATTERNS = (
    ("hf-token", re.compile(r"\bhf_[A-Za-z0-9]{20,}\b")),
    (
        "github-token",
        re.compile(r"\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b"),
    ),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "authorization",
        re.compile(
            r"(?ix)\b(?:"
            r"bearer\s+(?=[A-Za-z0-9._~+/=-]{20,}\b)(?=[A-Za-z0-9._~+/=-]*[0-9._~+/=-])"
            r"[A-Za-z0-9._~+/=-]+|"
            r"basic\s+(?=[A-Za-z0-9+/=]{20,}\b)(?=[A-Za-z0-9+/=]*[0-9+/=])"
            r"[A-Za-z0-9+/]+={0,2}"
            r")"
        ),
    ),
    ("url-userinfo", re.compile(r"(?i)https?://[^\s/@:]+:[^\s/@]+@")),
    (
        "secret-query-parameter",
        re.compile(
            r"(?i)(?:[?&]|\b)(?:access_token|api_key|auth_token|password|secret|token)="
            r"[^\s&#]{8,}"
        ),
    ),
)


@dataclass(frozen=True)
class RootMapping:
    source: str
    label: str

    @property
    def replacement(self) -> str:
        return f"{LOCAL_REFERENCE_SCHEME}{self.label}"


@dataclass
class ScrubStats:
    rewritten_strings: int = 0
    root_replacements: int = 0


def parse_root_mapping(value: str) -> RootMapping:
    source, separator, label = value.rpartition("=")
    source = source.rstrip("/\\")
    label = label.strip().lower()
    if not separator or not source or not label:
        raise argparse.ArgumentTypeError("root mappings must have the form /absolute/root=label")
    if not Path(source).is_absolute():
        raise argparse.ArgumentTypeError("mapped roots must be absolute")
    if not LABEL_RE.fullmatch(label):
        raise argparse.ArgumentTypeError(
            "mapping labels must contain only lowercase letters, numbers, dot, underscore, or dash"
        )
    return RootMapping(source=source, label=label)


def _credential_category(value: str) -> str | None:
    for category, pattern in CREDENTIAL_VALUE_PATTERNS:
        if pattern.search(value):
            return category
    return None


def _unsafe_path_category(value: str) -> str | None:
    if KNOWN_MACHINE_ROOT_RE.search(value):
        return "machine-root"
    if ABSOLUTE_POSIX_PATH_RE.search(value):
        return "absolute-path"
    return None


def _replace_mapped_roots(value: str, mappings: Sequence[RootMapping]) -> tuple[str, int]:
    result = value
    replacements = 0
    for mapping in sorted(
        mappings, key=lambda item: (-len(item.source), item.source, item.label)
    ):
        pattern = re.compile(re.escape(mapping.source) + r"(?=$|[/\\])")
        result, count = pattern.subn(mapping.replacement, result)
        replacements += count
    return result, replacements


def scrub_value(
    value: Any,
    *,
    mappings: Sequence[RootMapping],
    location: str,
    stats: ScrubStats,
) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key, child in value.items():
            key = str(raw_key)
            if _is_secret_key(re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")):
                raise ArchiveValidationError(f"credential field is forbidden at {location}.{key}")
            result[key] = scrub_value(
                child,
                mappings=mappings,
                location=f"{location}.{key}",
                stats=stats,
            )
        return result
    if isinstance(value, list):
        return [
            scrub_value(
                child,
                mappings=mappings,
                location=f"{location}[{index}]",
                stats=stats,
            )
            for index, child in enumerate(value)
        ]
    if isinstance(value, str):
        category = _credential_category(value)
        if category is not None:
            raise ArchiveValidationError(f"{category} is forbidden at {location}")
        scrubbed, replacements = _replace_mapped_roots(value, mappings)
        if replacements:
            stats.rewritten_strings += 1
            stats.root_replacements += replacements
        category = _unsafe_path_category(scrubbed)
        if category is not None:
            raise ArchiveValidationError(
                f"unmapped {category} is forbidden at {location}; add an explicit root mapping"
            )
        return scrubbed
    return value


def verify_safe_value(value: Any, *, location: str) -> int:
    strings = 0
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            if _is_secret_key(re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")):
                raise ArchiveValidationError(f"credential field is forbidden at {location}.{key}")
            strings += verify_safe_value(child, location=f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            strings += verify_safe_value(child, location=f"{location}[{index}]")
    elif isinstance(value, str):
        strings += 1
        credential = _credential_category(value)
        if credential is not None:
            raise ArchiveValidationError(f"{credential} is forbidden at {location}")
        category = _unsafe_path_category(value)
        if category is not None:
            raise ArchiveValidationError(f"{category} is forbidden at {location}")
    return strings


def _read_records(root: Path, descriptor: Mapping[str, Any]) -> list[dict[str, Any]]:
    payload = root / str(descriptor["payload_path"])
    if sha256_file(payload) != descriptor["payload_sha256"]:
        raise ArchiveIntegrityError(f"payload digest mismatch: {payload}")
    records = [
        json.loads(line)
        for line in payload.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(records) != descriptor["rows"]:
        raise ArchiveIntegrityError(f"payload row count mismatch: {payload}")
    return records


def _record_ids(records: Iterable[Mapping[str, Any]]) -> list[str]:
    return [str(record.get("record_id", "")) for record in records]


def _descriptor_set_digest(descriptors: Iterable[Mapping[str, Any]]) -> str:
    values = sorted(str(descriptor["descriptor_id"]) for descriptor in descriptors)
    return sha256_bytes(canonical_json(values).encode("utf-8"))


def reemit_spool(
    *,
    source_root: Path | str,
    output_root: Path | str,
    mappings: Sequence[RootMapping],
) -> dict[str, Any]:
    source = Path(source_root).expanduser().resolve()
    output = Path(output_root).expanduser().resolve()
    if source == output:
        raise ArchiveValidationError("source and output spools must be different")
    descriptor_paths = sorted((source / "ready").glob("*.ready.json"))
    if not descriptor_paths:
        raise ArchiveValidationError(f"source spool has no ready descriptors: {source}")
    if len({mapping.label for mapping in mappings}) != len(mappings):
        raise ArchiveValidationError("each mapped root must use a unique label")

    source_descriptors: list[dict[str, Any]] = []
    output_descriptors: list[dict[str, Any]] = []
    expected_ready: set[Path] = set()
    expected_payloads: set[Path] = set()
    logical_identities: set[str] = set()
    stats = ScrubStats()
    changed_descriptors = 0
    total_records = 0

    for descriptor_path in descriptor_paths:
        descriptor = load_descriptor(descriptor_path, spool_root=source)
        source_records = _read_records(source, descriptor)
        scrubbed_records = scrub_value(
            source_records,
            mappings=mappings,
            location=f"descriptor[{descriptor['descriptor_id']}].records",
            stats=stats,
        )
        scrubbed_provenance = scrub_value(
            descriptor["provenance"],
            mappings=mappings,
            location=f"descriptor[{descriptor['descriptor_id']}].provenance",
            stats=stats,
        )
        scrubbed_aggregate = scrub_value(
            descriptor["aggregate"],
            mappings=mappings,
            location=f"descriptor[{descriptor['descriptor_id']}].aggregate",
            stats=stats,
        )
        identity = descriptor["identity"]
        logical_key = canonical_json(
            {
                key: identity[key]
                for key in ("run_id", "model_slug", "seed", "benchmark", "stage")
            }
        )
        if logical_key in logical_identities:
            raise ArchiveIntegrityError(
                f"duplicate logical archive identity: {logical_key}"
            )
        logical_identities.add(logical_key)

        emitted_path = emit_slice_ready(
            output,
            stage=identity["stage"],
            run_id=identity["run_id"],
            model=identity["model"],
            model_revision=identity["model_revision"],
            seed=int(identity["seed"]),
            benchmark=identity["benchmark"],
            dataset_alias=identity["dataset_alias"],
            dataset_split=identity["dataset_split"],
            dataset_revision=identity["dataset_revision"],
            records=scrubbed_records,
            provenance=scrubbed_provenance,
            aggregate=scrubbed_aggregate,
            model_slug=identity["model_slug"],
        )
        emitted = load_descriptor(emitted_path, spool_root=output)
        emitted["created_at"] = descriptor.get("created_at")
        _atomic_write_bytes(
            emitted_path,
            (json.dumps(emitted, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        emitted = load_descriptor(emitted_path, spool_root=output)
        output_records = _read_records(output, emitted)
        if emitted["identity"] != identity:
            raise ArchiveIntegrityError("re-emission changed an archive identity")
        if _record_ids(output_records) != _record_ids(source_records):
            raise ArchiveIntegrityError("re-emission changed record identities or row order")
        if emitted["rows"] != descriptor["rows"]:
            raise ArchiveIntegrityError("re-emission changed the row count")
        if emitted["descriptor_id"] != descriptor["descriptor_id"]:
            changed_descriptors += 1
        source_descriptors.append(descriptor)
        output_descriptors.append(emitted)
        total_records += int(emitted["rows"])
        expected_ready.add(emitted_path.resolve())
        expected_payloads.add((output / emitted["payload_path"]).resolve())

    actual_ready = {
        path.resolve() for path in (output / "ready").glob("*.ready.json")
    }
    actual_payloads = {
        path.resolve() for path in (output / "payloads").glob("*.jsonl")
    }
    if actual_ready != expected_ready or actual_payloads != expected_payloads:
        raise ArchiveIntegrityError(
            "output spool contains files outside this deterministic re-emission; use a fresh output root"
        )

    safety = verify_spool(root=output, include_staged=False)
    receipt = {
        "changed_descriptors": changed_descriptors,
        "descriptor_count": len(output_descriptors),
        "logical_identity_count": len(logical_identities),
        "mapping_labels": sorted(mapping.label for mapping in mappings),
        "output_descriptor_set_sha256": _descriptor_set_digest(output_descriptors),
        "record_count": total_records,
        "rewritten_strings": stats.rewritten_strings,
        "root_replacements": stats.root_replacements,
        "safety": safety,
        "schema_version": SCRUB_SCHEMA_VERSION,
        "source_descriptor_set_sha256": _descriptor_set_digest(source_descriptors),
    }
    receipt_path = output / "control" / "scrub-receipt.json"
    _atomic_write_bytes(
        receipt_path,
        (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return receipt


def _verify_parquet(path: Path) -> tuple[int, int]:
    strings = 0
    rows = 0
    parquet = pq.ParquetFile(path)
    string_columns = [
        field.name
        for field in parquet.schema_arrow
        if pa.types.is_string(field.type) or pa.types.is_large_string(field.type)
    ]
    for batch_index, batch in enumerate(
        parquet.iter_batches(columns=string_columns, batch_size=4096)
    ):
        rows += batch.num_rows
        for column_name, column in zip(batch.schema.names, batch.columns):
            for row_offset, value in enumerate(column.to_pylist()):
                if value is None:
                    continue
                strings += 1
                credential = _credential_category(value)
                if credential is not None:
                    raise ArchiveValidationError(
                        f"{credential} is forbidden in "
                        f"{path.name}:{batch_index}:{row_offset}:{column_name}"
                    )
                category = _unsafe_path_category(value)
                if category is not None:
                    raise ArchiveValidationError(
                        f"{category} is forbidden in "
                        f"{path.name}:{batch_index}:{row_offset}:{column_name}"
                    )
    return rows, strings


def verify_spool(
    *,
    root: Path | str,
    include_staged: bool = True,
    require_staged: bool = False,
) -> dict[str, Any]:
    spool = Path(root).expanduser().resolve()
    descriptors = []
    strings = 0
    records = 0
    for descriptor_path in sorted((spool / "ready").glob("*.ready.json")):
        descriptor = load_descriptor(descriptor_path, spool_root=spool)
        strings += verify_safe_value(
            descriptor,
            location=f"descriptor[{descriptor['descriptor_id']}]",
        )
        payload_records = _read_records(spool, descriptor)
        strings += verify_safe_value(
            payload_records,
            location=f"payload[{descriptor['descriptor_id']}]",
        )
        descriptors.append(descriptor)
        records += len(payload_records)
    if not descriptors:
        raise ArchiveValidationError(f"spool has no ready descriptors: {spool}")

    staged_parquet = sorted((spool / "staged" / "data").rglob("*.parquet"))
    staged_manifests = sorted((spool / "staged" / "metadata").rglob("*.json"))
    staged_rows = 0
    if include_staged:
        if require_staged and (not staged_parquet or not staged_manifests):
            raise ArchiveIntegrityError(
                "staged Parquet and manifests are required but absent"
            )
        for path in staged_manifests:
            strings += verify_safe_value(
                json.loads(path.read_text(encoding="utf-8")),
                location=path.name,
            )
        for path in staged_parquet:
            rows, checked = _verify_parquet(path)
            staged_rows += rows
            strings += checked
        if staged_parquet and len(staged_parquet) != len(descriptors):
            raise ArchiveIntegrityError(
                f"staged Parquet count {len(staged_parquet)} does not match "
                f"descriptors {len(descriptors)}"
            )
        if staged_manifests and len(staged_manifests) != len(descriptors):
            raise ArchiveIntegrityError(
                f"staged manifest count {len(staged_manifests)} does not match "
                f"descriptors {len(descriptors)}"
            )

    return {
        "descriptor_count": len(descriptors),
        "descriptor_set_sha256": _descriptor_set_digest(descriptors),
        "record_count": records,
        "staged_manifest_count": len(staged_manifests),
        "staged_parquet_count": len(staged_parquet),
        "staged_row_count": staged_rows,
        "strings_checked": strings,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    reemit = commands.add_parser(
        "reemit", help="Create a path-free, upload-eligible spool."
    )
    reemit.add_argument("--source-root", type=Path, required=True)
    reemit.add_argument("--output-root", type=Path, required=True)
    reemit.add_argument(
        "--map-root",
        action="append",
        type=parse_root_mapping,
        required=True,
        help="Rewrite /absolute/root=label to trace-local-ref://label (repeatable).",
    )
    verify = commands.add_parser(
        "verify",
        help="Verify descriptors, payloads, and staged upload files.",
    )
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--no-staged", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "reemit":
            report = reemit_spool(
                source_root=args.source_root,
                output_root=args.output_root,
                mappings=args.map_root,
            )
        else:
            report = verify_spool(
                root=args.root,
                include_staged=not args.no_staged,
                require_staged=not args.no_staged,
            )
        print(json.dumps(report, sort_keys=True))
        return 0
    except Exception as error:
        print(f"archive scrub error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
