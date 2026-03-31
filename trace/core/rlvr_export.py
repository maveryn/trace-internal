"""TRACE dataset export helpers for the local RLVR stack."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping


PromptVariantMode = Literal["active", "answer_only", "answer_and_evidence"]
ImagePathMode = Literal["relative", "absolute", "dataset_relative"]
OutputFormat = Literal["jsonl", "parquet"]


@dataclass(frozen=True)
class RLVRExportResult:
    """Summary for one TRACE-to-RLVR export run."""

    source_dataset_root: Path
    train_instances_path: Path
    output_path: Path
    output_format: OutputFormat
    prompt_variant: PromptVariantMode
    image_path_mode: ImagePathMode
    row_count: int


def resolve_train_instances_source(path: str | Path) -> tuple[Path, Path]:
    """Resolve a TRACE dataset root plus its train-instances file."""

    candidate = Path(path).expanduser().resolve()
    if candidate.is_dir():
        train_instances_path = candidate / "train_instances.jsonl"
        dataset_root = candidate
    else:
        train_instances_path = candidate
        dataset_root = candidate.parent

    if not train_instances_path.exists():
        raise FileNotFoundError(f"TRACE train-instances file not found: {train_instances_path}")
    if train_instances_path.name != "train_instances.jsonl":
        raise ValueError(
            "TRACE RLVR export expects a dataset root or a file named "
            f"'train_instances.jsonl', got: {train_instances_path.name}"
        )
    return dataset_root, train_instances_path


def resolve_export_output_path(
    output_path: str | Path,
    *,
    output_format: OutputFormat | None = None,
) -> tuple[Path, OutputFormat]:
    """Resolve the concrete export file path plus normalized format."""

    candidate = Path(output_path).expanduser()
    suffix = candidate.suffix.lower()

    inferred_format: OutputFormat | None = None
    if suffix == ".parquet":
        inferred_format = "parquet"
    elif suffix in {".jsonl", ".json"}:
        inferred_format = "jsonl"

    final_format = output_format or inferred_format or "jsonl"
    if final_format not in {"jsonl", "parquet"}:
        raise ValueError(f"unsupported RLVR export format: {final_format}")

    if inferred_format is not None and output_format is not None and inferred_format != output_format:
        raise ValueError(
            "output format mismatch: "
            f"path {candidate} implies {inferred_format}, but --format={output_format}"
        )

    if candidate.exists() and candidate.is_dir():
        filename = "train.parquet" if final_format == "parquet" else "train.jsonl"
        return candidate / filename, final_format
    if candidate.suffix:
        return candidate, final_format

    candidate.mkdir(parents=True, exist_ok=True)
    filename = "train.parquet" if final_format == "parquet" else "train.jsonl"
    return candidate / filename, final_format


def _read_jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_number} of {path}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"expected JSON object on line {line_number} of {path}")
            records.append(payload)
    return records


def _select_prompt(record: Mapping[str, Any], prompt_variant: PromptVariantMode) -> str:
    prompt = str(record.get("prompt", ""))
    if prompt_variant == "active":
        return prompt

    prompt_variants = record.get("prompt_variants")
    if isinstance(prompt_variants, Mapping):
        candidate = prompt_variants.get(prompt_variant)
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return prompt


def _iter_image_paths(record: Mapping[str, Any], dataset_root: Path) -> Iterable[Path]:
    images = record.get("images")
    if not isinstance(images, list):
        raise ValueError("TRACE RLVR export requires images to be a list")

    for image in images:
        if isinstance(image, Mapping):
            raw_path = image.get("path")
        elif isinstance(image, str):
            raw_path = image
        else:
            raise ValueError(f"unsupported image entry for RLVR export: {image!r}")

        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError(f"image entry is missing a usable path: {image!r}")

        image_path = Path(raw_path)
        yield image_path if image_path.is_absolute() else (dataset_root / image_path)


def _format_image_path(
    image_path: Path,
    *,
    dataset_root: Path,
    output_parent: Path,
    image_path_mode: ImagePathMode,
) -> str:
    resolved = image_path.resolve()
    if image_path_mode == "absolute":
        return str(resolved)
    if image_path_mode == "dataset_relative":
        try:
            return str(resolved.relative_to(dataset_root.resolve()).as_posix())
        except ValueError as exc:
            raise ValueError(
                f"cannot express image path {resolved} relative to dataset root {dataset_root}"
            ) from exc
    if image_path_mode != "relative":
        raise ValueError(f"unsupported image-path mode: {image_path_mode}")
    relative = os.path.relpath(str(resolved), start=str(output_parent.resolve()))
    return str(Path(relative).as_posix())


def _build_exported_images(
    train_record: Mapping[str, Any],
    *,
    dataset_root: Path,
    output_parent: Path,
    image_path_mode: ImagePathMode,
) -> list[dict[str, str]]:
    """Build RLVR image records in the path-dict shape that the loader normalizes."""

    return [
        {
            "path": _format_image_path(
                image_path,
                dataset_root=dataset_root,
                output_parent=output_parent,
                image_path_mode=image_path_mode,
            )
        }
        for image_path in _iter_image_paths(train_record, dataset_root)
    ]


def build_rlvr_row(
    train_record: Mapping[str, Any],
    *,
    dataset_root: Path,
    output_parent: Path,
    prompt_variant: PromptVariantMode = "answer_and_evidence",
    image_path_mode: ImagePathMode = "relative",
) -> dict[str, Any]:
    """Convert one TRACE train record into an RLVR-ready row."""

    instance_id = str(train_record.get("instance_id", "")).strip()
    if not instance_id:
        raise ValueError("TRACE RLVR export requires instance_id")

    answer_gt = train_record.get("answer_gt")
    evidence_gt = train_record.get("evidence_gt")
    reward_contract = train_record.get("reward_contract")
    if not isinstance(answer_gt, Mapping):
        raise ValueError(f"TRACE RLVR export requires answer_gt on {instance_id}")
    if not isinstance(evidence_gt, Mapping):
        raise ValueError(f"TRACE RLVR export requires evidence_gt on {instance_id}")
    if not isinstance(reward_contract, Mapping):
        raise ValueError(f"TRACE RLVR export requires reward_contract on {instance_id}")

    return {
        "uid": instance_id,
        "instance_id": instance_id,
        "domain": str(train_record.get("domain", "")),
        "task_group": str(train_record.get("task_group", "")),
        "task": str(train_record.get("task", "")),
        "prompt": _select_prompt(train_record, prompt_variant),
        "prompt_mode": prompt_variant,
        "images": _build_exported_images(
            train_record,
            dataset_root=dataset_root,
            output_parent=output_parent,
            image_path_mode=image_path_mode,
        ),
        "answer_gt": dict(answer_gt),
        "evidence_gt": dict(evidence_gt),
        "reward_contract": dict(reward_contract),
        "trace_ref": dict(train_record.get("trace_ref", {}))
        if isinstance(train_record.get("trace_ref"), Mapping)
        else train_record.get("trace_ref"),
    }


def _write_jsonl_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False, sort_keys=True))
            handle.write("\n")


def _write_parquet_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path)


def export_trace_dataset_to_rlvr(
    source_path: str | Path,
    output_path: str | Path,
    *,
    output_format: OutputFormat | None = None,
    prompt_variant: PromptVariantMode = "answer_and_evidence",
    image_path_mode: ImagePathMode = "relative",
) -> RLVRExportResult:
    """Export one TRACE dataset to an RLVR-ready JSONL or parquet file."""

    if prompt_variant not in {"active", "answer_only", "answer_and_evidence"}:
        raise ValueError(f"unsupported prompt variant: {prompt_variant}")
    if image_path_mode not in {"relative", "absolute", "dataset_relative"}:
        raise ValueError(f"unsupported image-path mode: {image_path_mode}")

    dataset_root, train_instances_path = resolve_train_instances_source(source_path)
    final_output_path, final_format = resolve_export_output_path(output_path, output_format=output_format)
    output_parent = final_output_path.parent.resolve()

    records = _read_jsonl_records(train_instances_path)
    rows = [
        build_rlvr_row(
            record,
            dataset_root=dataset_root,
            output_parent=output_parent,
            prompt_variant=prompt_variant,
            image_path_mode=image_path_mode,
        )
        for record in records
    ]

    if final_format == "parquet":
        _write_parquet_rows(final_output_path, rows)
    else:
        _write_jsonl_rows(final_output_path, rows)

    return RLVRExportResult(
        source_dataset_root=dataset_root,
        train_instances_path=train_instances_path,
        output_path=final_output_path.resolve(),
        output_format=final_format,
        prompt_variant=prompt_variant,
        image_path_mode=image_path_mode,
        row_count=len(rows),
    )
