"""TRACE dataset export helpers for the local RLVR stack."""

from __future__ import annotations

import json
import os
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping

from tqdm.auto import tqdm


PromptVariantMode = Literal["active", "answer_only", "answer_and_evidence"]
ImagePathMode = Literal["relative", "absolute", "dataset_relative"]
ImageStorageMode = Literal["path_dict", "embedded_bytes"]
OutputFormat = Literal["jsonl", "parquet"]
_PARQUET_JSON_COLUMNS = ("answer_gt", "evidence_gt", "reward_contract", "trace_ref")
_PARQUET_WRITE_CHUNK_SIZE = 4096
_PROGRESS_DISABLED_VALUES = {"0", "false", "no", "off"}
_EXPORT_PROGRESS_ENABLED = (
    os.environ.get("TRACE_EXPORT_PROGRESS")
    or os.environ.get("TRACE_BUILD_PROGRESS")
    or "1"
).strip().lower() not in _PROGRESS_DISABLED_VALUES


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

def _iter_chunks(rows: list[dict[str, Any]], chunk_size: int) -> Iterable[list[dict[str, Any]]]:
    """Yield fixed-size row chunks in order."""

    for start in range(0, len(rows), chunk_size):
        yield rows[start : start + chunk_size]


def _resolve_parquet_cpu_count(parquet_cpu_count: int | None) -> int | None:
    """Normalize the requested parquet CPU count."""

    if parquet_cpu_count is None:
        return None
    parsed = int(parquet_cpu_count)
    if parsed < 0:
        raise ValueError("parquet_cpu_count must be >= 0")
    if parsed == 0:
        return max(1, int(os.cpu_count() or 1))
    return parsed


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
    progress_enabled = _EXPORT_PROGRESS_ENABLED
    records: list[dict[str, Any]] = []
    total_bytes = path.stat().st_size
    with (
        path.open("r", encoding="utf-8") as handle,
        tqdm(
            total=total_bytes,
            desc="Read TRACE JSONL",
            unit="B",
            unit_scale=True,
            dynamic_ncols=True,
            disable=not progress_enabled,
        ) as progress_bar,
    ):
        for line_number, raw_line in enumerate(handle, start=1):
            progress_bar.update(len(raw_line.encode("utf-8")))
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


def _normalize_multimodal_prompt(prompt: str, *, image_count: int) -> str:
    """Prefix RLVR image placeholders so exported multimodal rows match their image payload.

    vLLM's multimodal replacement expects prompt tokens to contain one `<image>` marker
    per image item. TRACE prompts intentionally avoid transport-specific placeholders, so
    RLVR export normalizes them into the local RLVR multimodal convention.
    """

    if image_count <= 0:
        return prompt
    cleaned_prompt = prompt.replace("<image>", "").strip()
    return f"{'<image>' * image_count}{cleaned_prompt}"


def _build_prompt_columns(record: Mapping[str, Any], *, image_count: int) -> dict[str, str]:
    """Export both public TRACE prompt variants so one parquet can drive multiple ablations."""

    return {
        "prompt_active": _normalize_multimodal_prompt(_select_prompt(record, "active"), image_count=image_count),
        "prompt_answer_only": _normalize_multimodal_prompt(_select_prompt(record, "answer_only"), image_count=image_count),
        "prompt_answer_and_evidence": _normalize_multimodal_prompt(
            _select_prompt(record, "answer_and_evidence"),
            image_count=image_count,
        ),
    }


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
    image_storage_mode: ImageStorageMode,
) -> list[dict[str, Any]]:
    """Build RLVR image records in the path-dict shape that the loader normalizes."""

    exported: list[dict[str, Any]] = []
    for image_path in _iter_image_paths(train_record, dataset_root):
        if image_storage_mode == "embedded_bytes":
            exported.append(
                {
                    "bytes": image_path.read_bytes(),
                    "format": image_path.suffix.lower().lstrip(".") or "png",
                }
            )
            continue
        if image_storage_mode != "path_dict":
            raise ValueError(f"unsupported image-storage mode: {image_storage_mode}")
        exported.append(
            {
                "path": _format_image_path(
                    image_path,
                    dataset_root=dataset_root,
                    output_parent=output_parent,
                    image_path_mode=image_path_mode,
                )
            }
        )
    return exported


def _extract_complexity_score(train_record: Mapping[str, Any]) -> float:
    task_complexity = train_record.get("task_complexity")
    instance_id = str(train_record.get("instance_id", "")).strip() or "<missing-instance-id>"
    if not isinstance(task_complexity, Mapping):
        raise ValueError(f"TRACE RLVR export requires task_complexity on {instance_id}")
    raw_score = task_complexity.get("complexity_score")
    try:
        score = float(raw_score)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"TRACE RLVR export requires numeric task_complexity.complexity_score on {instance_id}") from exc
    if not math.isfinite(score):
        raise ValueError(f"TRACE RLVR export requires finite task_complexity.complexity_score on {instance_id}")
    return score


def _build_curriculum_assignments(records: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Assign task-local curriculum bins using 3-way quantiles with sensible fallback.

    Policy:
    - Work within each task only; TRACE complexity is not cross-task comparable.
    - Target 3 bins per task (`q0`, `q1`, `q2`) by default.
    - Fall back to fewer bins when a task has too few rows or too few distinct scores.
    - Keep identical complexity scores together when assigning bins.
    """

    task_rows: dict[str, list[tuple[str, float]]] = {}
    for record in records:
        instance_id = str(record.get("instance_id", "")).strip()
        if not instance_id:
            raise ValueError("TRACE RLVR export requires instance_id")
        task = str(record.get("task", "")).strip()
        if not task:
            raise ValueError(f"TRACE RLVR export requires task on {instance_id}")
        score = _extract_complexity_score(record)
        task_rows.setdefault(task, []).append((instance_id, score))

    assignments: dict[str, dict[str, Any]] = {}
    for task, rows in task_rows.items():
        rows_sorted = sorted(rows, key=lambda item: (item[1], item[0]))
        unique_scores = sorted({score for _, score in rows_sorted})
        bucket_count = max(1, min(3, len(rows_sorted), len(unique_scores)))
        total_rows = len(rows_sorted)

        score_groups: dict[float, list[str]] = {}
        for instance_id, score in rows_sorted:
            score_groups.setdefault(score, []).append(instance_id)

        rows_before_group = 0
        for score in unique_scores:
            grouped_instance_ids = score_groups[score]
            group_size = len(grouped_instance_ids)
            group_midpoint = rows_before_group + (0.5 * group_size)
            difficulty_bin = min(bucket_count - 1, int((group_midpoint * bucket_count) / total_rows))
            bucket_id = f"{task}::q{difficulty_bin}"
            for instance_id in grouped_instance_ids:
                assignments[instance_id] = {
                    "complexity_score": score,
                    "difficulty_bin": difficulty_bin,
                    "bucket_id_str": bucket_id,
                }
            rows_before_group += group_size
    return assignments


def build_rlvr_row(
    train_record: Mapping[str, Any],
    *,
    dataset_root: Path,
    output_parent: Path,
    prompt_variant: PromptVariantMode = "answer_and_evidence",
    image_path_mode: ImagePathMode = "relative",
    image_storage_mode: ImageStorageMode = "path_dict",
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
    exported_images = _build_exported_images(
        train_record,
        dataset_root=dataset_root,
        output_parent=output_parent,
        image_path_mode=image_path_mode,
        image_storage_mode=image_storage_mode,
    )
    prompt_columns = _build_prompt_columns(train_record, image_count=len(exported_images))
    prompt = {
        "active": prompt_columns["prompt_active"],
        "answer_only": prompt_columns["prompt_answer_only"],
        "answer_and_evidence": prompt_columns["prompt_answer_and_evidence"],
    }[prompt_variant]

    return {
        "uid": instance_id,
        "instance_id": instance_id,
        "domain": str(train_record.get("domain", "")),
        "task_group": str(train_record.get("task_group", "")),
        "task": str(train_record.get("task", "")),
        "complexity_score": _extract_complexity_score(train_record),
        "prompt": prompt,
        **prompt_columns,
        "prompt_mode": prompt_variant,
        "images": exported_images,
        "answer_gt": dict(answer_gt),
        "evidence_gt": dict(evidence_gt),
        "reward_contract": dict(reward_contract),
        "trace_ref": dict(train_record.get("trace_ref", {}))
        if isinstance(train_record.get("trace_ref"), Mapping)
        else train_record.get("trace_ref"),
    }


def _write_jsonl_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with (
        path.open("w", encoding="utf-8") as handle,
        tqdm(
            total=len(rows),
            desc="Write RLVR JSONL",
            unit="row",
            dynamic_ncols=True,
            disable=not _EXPORT_PROGRESS_ENABLED,
        ) as progress_bar,
    ):
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False, sort_keys=True))
            handle.write("\n")
            progress_bar.update(1)


def _write_parquet_rows(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    parquet_cpu_count: int | None = None,
    image_storage_mode: ImageStorageMode = "path_dict",
) -> None:
    import pyarrow as pa

    path.parent.mkdir(parents=True, exist_ok=True)
    progress_enabled = _EXPORT_PROGRESS_ENABLED
    parquet_rows = []
    with tqdm(
        total=len(rows),
        desc="Prepare parquet rows",
        unit="row",
        dynamic_ncols=True,
        disable=not progress_enabled,
    ) as progress_bar:
        for row in rows:
            parquet_row = dict(row)
            for key in _PARQUET_JSON_COLUMNS:
                if key in parquet_row:
                    parquet_row[key] = json.dumps(
                        parquet_row[key],
                        ensure_ascii=False,
                        allow_nan=False,
                        sort_keys=True,
                    )
            parquet_rows.append(parquet_row)
            progress_bar.update(1)
    requested_cpu_count = _resolve_parquet_cpu_count(parquet_cpu_count)
    prior_cpu_count = pa.cpu_count()
    prior_io_thread_count = pa.io_thread_count()
    try:
        if requested_cpu_count is not None:
            pa.set_cpu_count(int(requested_cpu_count))
            pa.set_io_thread_count(int(requested_cpu_count))

        if image_storage_mode == "embedded_bytes":
            from datasets import Dataset, Sequence
            from datasets import Image as HFImage

            if progress_enabled:
                tqdm.write("Writing parquet via datasets backend")
            dataset = Dataset.from_list(parquet_rows)
            dataset = dataset.cast_column("images", Sequence(HFImage()))
            dataset.to_parquet(str(path))
            return

        if image_storage_mode != "path_dict":
            raise ValueError(f"unsupported image-storage mode: {image_storage_mode}")

        import pyarrow.parquet as pq

        writer = None
        chunk_count = max(1, math.ceil(len(parquet_rows) / _PARQUET_WRITE_CHUNK_SIZE))
        try:
            with tqdm(
                total=chunk_count,
                desc="Write parquet",
                unit="chunk",
                dynamic_ncols=True,
                disable=not progress_enabled,
            ) as progress_bar:
                for chunk_rows in _iter_chunks(parquet_rows, _PARQUET_WRITE_CHUNK_SIZE):
                    table = pa.Table.from_pylist(chunk_rows)
                    if writer is None:
                        writer = pq.ParquetWriter(path, table.schema, compression="snappy")
                    writer.write_table(table, row_group_size=len(chunk_rows))
                    progress_bar.update(1)
        finally:
            if writer is not None:
                writer.close()
    finally:
        pa.set_cpu_count(int(prior_cpu_count))
        pa.set_io_thread_count(int(prior_io_thread_count))


def export_trace_dataset_to_rlvr(
    source_path: str | Path,
    output_path: str | Path,
    *,
    output_format: OutputFormat | None = None,
    prompt_variant: PromptVariantMode = "answer_and_evidence",
    image_path_mode: ImagePathMode = "relative",
    image_storage_mode: ImageStorageMode = "path_dict",
    parquet_cpu_count: int | None = None,
) -> RLVRExportResult:
    """Export one TRACE dataset to an RLVR-ready JSONL or parquet file."""

    if prompt_variant not in {"active", "answer_only", "answer_and_evidence"}:
        raise ValueError(f"unsupported prompt variant: {prompt_variant}")
    if image_path_mode not in {"relative", "absolute", "dataset_relative"}:
        raise ValueError(f"unsupported image-path mode: {image_path_mode}")
    if image_storage_mode not in {"path_dict", "embedded_bytes"}:
        raise ValueError(f"unsupported image-storage mode: {image_storage_mode}")

    dataset_root, train_instances_path = resolve_train_instances_source(source_path)
    final_output_path, final_format = resolve_export_output_path(output_path, output_format=output_format)
    if final_format == "jsonl" and image_storage_mode == "embedded_bytes":
        raise ValueError("embedded_bytes image storage is only supported for parquet exports")
    output_parent = final_output_path.parent.resolve()

    records = _read_jsonl_records(train_instances_path)
    if _EXPORT_PROGRESS_ENABLED:
        tqdm.write(f"Assign curriculum bins for {len(records)} rows")
    curriculum_assignments = _build_curriculum_assignments(records)
    rows = []
    with tqdm(
        total=len(records),
        desc="Build RLVR rows",
        unit="row",
        dynamic_ncols=True,
        disable=not _EXPORT_PROGRESS_ENABLED,
    ) as progress_bar:
        for record in records:
            rows.append(
                {
                    **build_rlvr_row(
                        record,
                        dataset_root=dataset_root,
                        output_parent=output_parent,
                        prompt_variant=prompt_variant,
                        image_path_mode=image_path_mode,
                        image_storage_mode=image_storage_mode,
                    ),
                    **curriculum_assignments[str(record.get("instance_id", "")).strip()],
                }
            )
            progress_bar.update(1)

    if final_format == "parquet":
        _write_parquet_rows(
            final_output_path,
            rows,
            parquet_cpu_count=parquet_cpu_count,
            image_storage_mode=image_storage_mode,
        )
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
