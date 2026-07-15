#!/usr/bin/env python3
"""Build a deterministic smaller Trace RLVR training parquet from a full train parquet."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Path to the source Trace RLVR parquet.")
    parser.add_argument("--output", required=True, help="Path to the output subset parquet.")
    parser.add_argument(
        "--target-rows",
        type=int,
        default=8000,
        help="Target number of rows in the subset parquet.",
    )
    parser.add_argument(
        "--group-column",
        default="task",
        help="Column used to preserve coverage across the subset.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Parquet scan batch size.",
    )
    return parser.parse_args()


def _scan_group_counts(source: Path, group_column: str, batch_size: int) -> tuple[pq.ParquetFile, Counter]:
    parquet_file = pq.ParquetFile(source)
    available_columns = set(parquet_file.schema_arrow.names)
    if group_column not in available_columns:
        raise SystemExit(
            f"Group column {group_column!r} not found in {source}. "
            f"Available columns: {sorted(available_columns)}"
        )

    counts: Counter[str] = Counter()
    for batch in parquet_file.iter_batches(
        batch_size=batch_size,
        columns=[group_column],
        use_threads=True,
    ):
        counts.update(str(value) for value in batch.column(0).to_pylist())
    return parquet_file, counts


def _allocate_group_quotas(counts: Counter[str], target_rows: int) -> dict[str, int]:
    groups = sorted(counts)
    if not groups:
        raise SystemExit("No groups found in source parquet.")

    total_available = sum(counts.values())
    if target_rows > total_available:
        raise SystemExit(
            f"Requested target_rows={target_rows} exceeds total available rows={total_available}."
        )

    quotas = {group: 0 for group in groups}
    remaining = target_rows

    while remaining > 0:
        progress = False
        available_groups = [group for group in groups if quotas[group] < counts[group]]
        if not available_groups:
            break
        per_group = max(1, remaining // len(available_groups))
        for group in available_groups:
            capacity = counts[group] - quotas[group]
            take = min(capacity, per_group, remaining)
            if take <= 0:
                continue
            quotas[group] += take
            remaining -= take
            progress = True
            if remaining == 0:
                break
        if not progress:
            break

    if remaining != 0:
        raise SystemExit(f"Failed to allocate full target rows. Remaining={remaining}.")
    return quotas


def _build_group_positions(counts: Counter[str], quotas: dict[str, int]) -> dict[str, set[int]]:
    positions: dict[str, set[int]] = {}
    for group, total in counts.items():
        quota = quotas.get(group, 0)
        if quota <= 0:
            positions[group] = set()
            continue
        if quota >= total:
            positions[group] = set(range(total))
            continue
        positions[group] = {(index * total) // quota for index in range(quota)}
    return positions


def _write_subset(
    parquet_file: pq.ParquetFile,
    output: Path,
    group_column: str,
    batch_size: int,
    positions_by_group: dict[str, set[int]],
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    group_index = parquet_file.schema_arrow.get_field_index(group_column)
    seen_per_group: Counter[str] = Counter()
    written_rows = 0

    writer: pq.ParquetWriter | None = None
    try:
        for batch in parquet_file.iter_batches(batch_size=batch_size, use_threads=True):
            groups = batch.column(group_index).to_pylist()
            take_indices: list[int] = []
            for row_idx, group_value in enumerate(groups):
                group = str(group_value)
                position = seen_per_group[group]
                if position in positions_by_group[group]:
                    take_indices.append(row_idx)
                seen_per_group[group] += 1

            if not take_indices:
                continue

            subset_batch = batch.take(pa.array(take_indices, type=pa.int32()))
            if writer is None:
                writer = pq.ParquetWriter(output, subset_batch.schema)
            writer.write_batch(subset_batch)
            written_rows += subset_batch.num_rows
    finally:
        if writer is not None:
            writer.close()

    return written_rows


def main() -> None:
    args = _parse_args()
    source = Path(args.source).resolve()
    output = Path(args.output).resolve()

    parquet_file, counts = _scan_group_counts(
        source=source,
        group_column=args.group_column,
        batch_size=args.batch_size,
    )
    quotas = _allocate_group_quotas(counts=counts, target_rows=args.target_rows)
    positions_by_group = _build_group_positions(counts=counts, quotas=quotas)
    written_rows = _write_subset(
        parquet_file=parquet_file,
        output=output,
        group_column=args.group_column,
        batch_size=args.batch_size,
        positions_by_group=positions_by_group,
    )

    print(
        "Built Trace train subset:",
        f"source={source}",
        f"output={output}",
        f"rows={written_rows}",
        f"groups={len(counts)}",
        f"group_column={args.group_column}",
    )


if __name__ == "__main__":
    main()
