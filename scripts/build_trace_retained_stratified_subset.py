#!/usr/bin/env python3
"""Build a retained TRACE RLVR train subset from a staged curriculum probe.

The source RLVR parquet currently does not store query_variant directly. This
script recovers query_variant/scene_variant from sidecar traces through trace_ref,
then samples retained rows with capped proportional allocation against the
original source distribution.
"""

from __future__ import annotations

import argparse
import io
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
import zstandard as zstd


@dataclass(frozen=True)
class RowTraceRef:
    shard_id: str
    line_index: int


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Source TRACE RLVR parquet.")
    parser.add_argument("--probe-jsonl", required=True, help="Staged probe per_instance_staged.jsonl.")
    parser.add_argument(
        "--trace-root",
        required=True,
        help="TRACE dataset root containing traces/<shard>.jsonl.zst.",
    )
    parser.add_argument("--output", required=True, help="Output subset parquet.")
    parser.add_argument("--target-rows", type=int, default=102400)
    parser.add_argument("--seed", type=int, default=20260504)
    parser.add_argument(
        "--strata",
        default="task,query_variant,bucket_id_str",
        help="Comma-separated strata columns. Supported: domain, task_group, task, query_variant, scene_variant, difficulty_bin, bucket_id_str.",
    )
    parser.add_argument("--batch-size", type=int, default=2048)
    parser.add_argument(
        "--summary-json",
        default=None,
        help="Optional output summary JSON path. Defaults to <output>.summary.json.",
    )
    parser.add_argument(
        "--exclude-source-index-parquet",
        action="append",
        default=[],
        help=(
            "Parquet containing source_dataset_index rows to exclude before sampling. "
            "May be repeated; useful for held-out validation splits."
        ),
    )
    return parser.parse_args()


def _parse_json_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    return json.loads(str(value))


def _read_source_metadata(source: Path) -> tuple[pq.ParquetFile, dict[str, list[Any]], list[RowTraceRef]]:
    parquet_file = pq.ParquetFile(source)
    needed = ["domain", "task_group", "task", "difficulty_bin", "bucket_id_str", "trace_ref"]
    missing = [name for name in needed if name not in parquet_file.schema_arrow.names]
    if missing:
        raise SystemExit(f"Source parquet is missing required columns: {missing}")

    table = parquet_file.read(columns=needed, use_threads=True)
    metadata = table.to_pydict()
    refs: list[RowTraceRef] = []
    for value in metadata["trace_ref"]:
        ref = _parse_json_mapping(value)
        refs.append(RowTraceRef(shard_id=str(ref["shard_id"]), line_index=int(ref["line_index"])))
    return parquet_file, metadata, refs


def _trace_path(trace_root: Path, shard_id: str) -> Path:
    direct = trace_root / "traces" / shard_id
    if direct.exists():
        return direct
    if not shard_id.endswith(".zst"):
        zstd_path = trace_root / "traces" / f"{shard_id}.zst"
        if zstd_path.exists():
            return zstd_path
    raise FileNotFoundError(f"Could not resolve trace shard {shard_id!r} under {trace_root / 'traces'}")


def _recover_trace_variants(trace_root: Path, refs: list[RowTraceRef]) -> tuple[list[str], list[str], dict[str, Any]]:
    rows_by_shard_line: dict[str, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    for row_idx, ref in enumerate(refs):
        rows_by_shard_line[ref.shard_id][ref.line_index].append(row_idx)

    query_variants: list[str | None] = [None] * len(refs)
    scene_variants: list[str | None] = [None] * len(refs)
    query_execution_mismatch = 0
    matched = 0

    for shard_id, rows_by_line in sorted(rows_by_shard_line.items()):
        path = _trace_path(trace_root, shard_id)
        with path.open("rb") as fh:
            stream = zstd.ZstdDecompressor().stream_reader(fh) if path.suffix == ".zst" else fh
            text = io.TextIOWrapper(stream, encoding="utf-8")
            for line_index, line in enumerate(text):
                row_indices = rows_by_line.get(line_index)
                if not row_indices:
                    continue
                record = json.loads(line)
                query_spec = record.get("query_spec") or {}
                execution_trace = record.get("execution_trace") or {}
                render_spec = record.get("render_spec") or {}
                query_variant = query_spec.get("query_variant")
                execution_variant = execution_trace.get("query_variant")
                if query_variant != execution_variant:
                    query_execution_mismatch += len(row_indices)
                query_variant = query_variant if query_variant is not None else execution_variant
                scene_variant = render_spec.get("scene_variant", execution_trace.get("scene_variant", ""))
                if query_variant is None:
                    raise SystemExit(f"Missing query_variant in sidecar trace shard={shard_id} line={line_index}")
                for row_idx in row_indices:
                    query_variants[row_idx] = str(query_variant)
                    scene_variants[row_idx] = "" if scene_variant is None else str(scene_variant)
                    matched += 1

    missing = sum(1 for value in query_variants if value is None)
    if missing:
        raise SystemExit(f"Failed to recover query_variant for {missing} source rows.")

    return (
        [str(value) for value in query_variants],
        ["" if value is None else str(value) for value in scene_variants],
        {
            "trace_rows_matched": int(matched),
            "query_execution_query_variant_mismatch": int(query_execution_mismatch),
        },
    )


def _read_retained_indices(probe_jsonl: Path) -> tuple[set[int], dict[int, dict[str, Any]], Counter[str]]:
    retained: set[int] = set()
    probe_rows: dict[int, dict[str, Any]] = {}
    statuses: Counter[str] = Counter()
    with probe_jsonl.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            dataset_index = int(row["dataset_index"])
            status = str(row.get("filter_status", ""))
            statuses[status] += 1
            if status == "retained_band":
                retained.add(dataset_index)
                probe_rows[dataset_index] = {
                    "rollout_count": int(row.get("rollout_count", 0)),
                    "positive_rollout_count": int(row.get("positive_rollout_count", 0)),
                    "solve_rate": float(row.get("solve_rate", 0.0)),
                }
    return retained, probe_rows, statuses


def _read_excluded_source_indices(parquet_paths: list[str]) -> set[int]:
    excluded: set[int] = set()
    for raw_path in parquet_paths:
        path = Path(raw_path).resolve()
        parquet_file = pq.ParquetFile(path)
        if "source_dataset_index" not in parquet_file.schema_arrow.names:
            raise SystemExit(f"Exclude parquet is missing source_dataset_index: {path}")
        table = parquet_file.read(columns=["source_dataset_index"], use_threads=True)
        excluded.update(int(value) for value in table["source_dataset_index"].to_pylist())
    return excluded


def _stratum_for_row(
    row_idx: int,
    *,
    strata: list[str],
    metadata: dict[str, list[Any]],
    query_variants: list[str],
    scene_variants: list[str],
) -> tuple[str, ...]:
    values: list[str] = []
    for column in strata:
        if column == "query_variant":
            values.append(query_variants[row_idx])
        elif column == "scene_variant":
            values.append(scene_variants[row_idx])
        elif column in metadata:
            values.append(str(metadata[column][row_idx]))
        else:
            raise SystemExit(f"Unsupported stratum column: {column!r}")
    return tuple(values)


def _allocate_capped_proportional(
    *,
    original_counts: Counter[tuple[str, ...]],
    retained_counts: Counter[tuple[str, ...]],
    target_rows: int,
) -> dict[tuple[str, ...], int]:
    if target_rows > sum(retained_counts.values()):
        raise SystemExit(
            f"Requested target_rows={target_rows} exceeds retained rows={sum(retained_counts.values())}."
        )

    quotas = {stratum: 0 for stratum in original_counts}
    remaining = int(target_rows)
    while remaining > 0:
        active = [
            stratum
            for stratum in original_counts
            if quotas[stratum] < int(retained_counts.get(stratum, 0))
        ]
        if not active:
            raise SystemExit(f"Could not allocate {remaining} rows; no retained capacity left.")

        active_weight_sum = sum(int(original_counts[stratum]) for stratum in active)
        increments: dict[tuple[str, ...], int] = {}
        fractional: list[tuple[float, int, tuple[str, ...]]] = []
        allocated = 0
        for stratum in active:
            capacity = int(retained_counts[stratum]) - int(quotas[stratum])
            raw = float(remaining) * float(original_counts[stratum]) / float(active_weight_sum)
            take = min(capacity, int(raw))
            increments[stratum] = take
            allocated += take
            fractional.append((raw - int(raw), int(original_counts[stratum]), stratum))

        if allocated == 0:
            for _, _, stratum in sorted(fractional, reverse=True):
                if remaining <= 0:
                    break
                if quotas[stratum] + increments[stratum] >= int(retained_counts[stratum]):
                    continue
                increments[stratum] += 1
                allocated += 1
                remaining -= 1
            if allocated == 0:
                raise SystemExit("Internal allocation error: unable to allocate a row.")
            for stratum, take in increments.items():
                quotas[stratum] += int(take)
        else:
            for stratum, take in increments.items():
                quotas[stratum] += int(take)
            remaining -= int(allocated)

    return {stratum: int(count) for stratum, count in quotas.items() if int(count) > 0}


def _select_rows(
    *,
    retained_by_stratum: dict[tuple[str, ...], list[int]],
    quotas: dict[tuple[str, ...], int],
    seed: int,
) -> list[int]:
    rng = random.Random(seed)
    selected: list[int] = []
    for stratum in sorted(quotas):
        rows = list(retained_by_stratum[stratum])
        quota = int(quotas[stratum])
        if quota > len(rows):
            raise SystemExit(f"Quota exceeds retained capacity for {stratum}: {quota}>{len(rows)}")
        if quota == len(rows):
            selected.extend(rows)
            continue
        selected.extend(rng.sample(rows, quota))
    return sorted(selected)


def _append_column(batch: pa.RecordBatch, name: str, values: list[Any], pa_type: pa.DataType) -> pa.RecordBatch:
    return batch.append_column(name, pa.array(values, type=pa_type))


def _write_subset_parquet(
    *,
    parquet_file: pq.ParquetFile,
    output: Path,
    selected_rows: list[int],
    query_variants: list[str],
    scene_variants: list[str],
    probe_rows: dict[int, dict[str, Any]],
    batch_size: int,
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    selected_set = set(selected_rows)
    global_start = 0
    written = 0
    writer: pq.ParquetWriter | None = None
    try:
        for batch in parquet_file.iter_batches(batch_size=batch_size, use_threads=True):
            global_indices = [global_start + local for local in range(batch.num_rows)]
            take_local = [local for local, global_idx in enumerate(global_indices) if global_idx in selected_set]
            if take_local:
                selected_global = [global_start + local for local in take_local]
                subset = batch.take(pa.array(take_local, type=pa.int32()))
                subset = _append_column(
                    subset,
                    "source_dataset_index",
                    selected_global,
                    pa.int64(),
                )
                subset = _append_column(
                    subset,
                    "query_variant",
                    [query_variants[index] for index in selected_global],
                    pa.string(),
                )
                subset = _append_column(
                    subset,
                    "scene_variant",
                    [scene_variants[index] for index in selected_global],
                    pa.string(),
                )
                subset = _append_column(
                    subset,
                    "curriculum_probe_rollout_count",
                    [probe_rows[index]["rollout_count"] for index in selected_global],
                    pa.int64(),
                )
                subset = _append_column(
                    subset,
                    "curriculum_probe_positive_rollout_count",
                    [probe_rows[index]["positive_rollout_count"] for index in selected_global],
                    pa.int64(),
                )
                subset = _append_column(
                    subset,
                    "curriculum_probe_solve_rate",
                    [probe_rows[index]["solve_rate"] for index in selected_global],
                    pa.float64(),
                )
                if writer is None:
                    writer = pq.ParquetWriter(output, subset.schema)
                writer.write_batch(subset)
                written += subset.num_rows
            global_start += batch.num_rows
    finally:
        if writer is not None:
            writer.close()
    return written


def main() -> None:
    args = _parse_args()
    source = Path(args.source).resolve()
    probe_jsonl = Path(args.probe_jsonl).resolve()
    trace_root = Path(args.trace_root).resolve()
    output = Path(args.output).resolve()
    summary_json = Path(args.summary_json).resolve() if args.summary_json else output.with_suffix(output.suffix + ".summary.json")
    strata = [column.strip() for column in str(args.strata).split(",") if column.strip()]
    if not strata:
        raise SystemExit("At least one stratum column is required.")

    parquet_file, metadata, refs = _read_source_metadata(source)
    query_variants, scene_variants, trace_report = _recover_trace_variants(trace_root, refs)
    retained, probe_rows, probe_status_counts = _read_retained_indices(probe_jsonl)
    probe_retained_rows = len(retained)
    excluded_source_indices = _read_excluded_source_indices(list(args.exclude_source_index_parquet))
    if excluded_source_indices:
        retained.difference_update(excluded_source_indices)
        probe_rows = {row_idx: row for row_idx, row in probe_rows.items() if row_idx not in excluded_source_indices}

    source_rows = len(refs)
    if len(retained) != len(probe_rows):
        raise SystemExit("Internal retained/probe row mismatch.")
    if args.target_rows > len(retained):
        raise SystemExit(f"target_rows={args.target_rows} exceeds retained rows={len(retained)}.")

    original_counts: Counter[tuple[str, ...]] = Counter()
    retained_counts: Counter[tuple[str, ...]] = Counter()
    retained_by_stratum: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for row_idx in range(source_rows):
        stratum = _stratum_for_row(
            row_idx,
            strata=strata,
            metadata=metadata,
            query_variants=query_variants,
            scene_variants=scene_variants,
        )
        original_counts[stratum] += 1
        if row_idx in retained:
            retained_counts[stratum] += 1
            retained_by_stratum[stratum].append(row_idx)

    quotas = _allocate_capped_proportional(
        original_counts=original_counts,
        retained_counts=retained_counts,
        target_rows=int(args.target_rows),
    )
    selected_rows = _select_rows(retained_by_stratum=retained_by_stratum, quotas=quotas, seed=int(args.seed))
    written = _write_subset_parquet(
        parquet_file=parquet_file,
        output=output,
        selected_rows=selected_rows,
        query_variants=query_variants,
        scene_variants=scene_variants,
        probe_rows=probe_rows,
        batch_size=int(args.batch_size),
    )
    if written != int(args.target_rows):
        raise SystemExit(f"Expected to write {args.target_rows} rows, wrote {written}.")

    capped_strata = [
        {
            "stratum": list(stratum),
            "original_count": int(original_counts[stratum]),
            "retained_count": int(retained_counts[stratum]),
            "quota": int(quotas.get(stratum, 0)),
        }
        for stratum in sorted(original_counts)
        if int(quotas.get(stratum, 0)) == int(retained_counts.get(stratum, 0))
        and int(retained_counts.get(stratum, 0)) < int(original_counts[stratum])
    ]
    summary = {
        "source": str(source),
        "probe_jsonl": str(probe_jsonl),
        "trace_root": str(trace_root),
        "output": str(output),
        "target_rows": int(args.target_rows),
        "written_rows": int(written),
        "seed": int(args.seed),
        "strata": strata,
        "source_rows": int(source_rows),
        "probe_retained_rows": int(probe_retained_rows),
        "retained_rows": int(len(retained)),
        "excluded_source_index_parquets": [str(Path(path).resolve()) for path in args.exclude_source_index_parquet],
        "excluded_source_index_count": int(len(excluded_source_indices)),
        "source_strata_count": int(len(original_counts)),
        "retained_strata_count": int(len(retained_counts)),
        "selected_strata_count": int(len(quotas)),
        "capped_strata_count": int(len(capped_strata)),
        "probe_status_counts": {key: int(value) for key, value in sorted(probe_status_counts.items())},
        **trace_report,
        "selected_query_variant_units": int(
            len(
                {
                    (
                        metadata["task"][row_idx],
                        query_variants[row_idx],
                    )
                    for row_idx in selected_rows
                }
            )
        ),
        "capped_strata_sample": capped_strata[:25],
    }
    summary_json.parent.mkdir(parents=True, exist_ok=True)
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        "Built retained TRACE subset:",
        f"source={source}",
        f"output={output}",
        f"rows={written}",
        f"retained_rows={len(retained)}",
        f"strata={len(original_counts)}",
        f"capped_strata={len(capped_strata)}",
        f"summary={summary_json}",
    )


if __name__ == "__main__":
    main()
