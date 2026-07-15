#!/usr/bin/env python3
"""Prepare fixed manifest-only external benchmark subsets for TRACE RLVR eval."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from benchmark_queue_lib import (
    ALL_BENCHMARKS,
    BENCHMARKS,
    REPO_ROOT,
    TRACE_CANDIDATE37_200_BENCHMARKS,
    TRACE_CANDIDATE37_200_SUBSET_ROOT,
    VLMEVAL_ROOT,
    BenchmarkSpec,
    build_vlmeval_dataset,
    filter_benchmark_specs,
)


DEFAULT_OUT_ROOT = REPO_ROOT / "benchmark/subsets/external_eval_v1"
DEFAULT_BENCHMARKS = (
    "chartqapro",
    "charxivreason",
    "mathvista",
    "mmmu_pro_vision",
    "countqa",
    "game_qa_lite",
    "blink",
    "screenspotpro",
)
DEFAULT_SAMPLE_COUNT = 1000
DEFAULT_SAMPLE_SEED = 42
PRESETS = {
    "external_eval_v1": {
        "out_root": DEFAULT_OUT_ROOT,
        "benchmarks": DEFAULT_BENCHMARKS,
        "sample_count": DEFAULT_SAMPLE_COUNT,
        "sample_seed": DEFAULT_SAMPLE_SEED,
    },
    "trace_candidate37_200": {
        "out_root": TRACE_CANDIDATE37_200_SUBSET_ROOT,
        "benchmarks": TRACE_CANDIDATE37_200_BENCHMARKS,
        "sample_count": 200,
        "sample_seed": DEFAULT_SAMPLE_SEED,
    },
}

MEDIA_KEYS = {
    "image",
    "images",
    "image_path",
    "image_paths",
    "img",
    "picture",
    "video",
    "videos",
    "video_path",
    "video_paths",
}
QUESTION_KEYS = (
    "question",
    "query",
    "prompt",
    "instruction",
    "input",
)


def _import_vlmeval_dataset_builder():
    scripts_root = VLMEVAL_ROOT / "scripts"
    for path in (VLMEVAL_ROOT, scripts_root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from vlmeval.dataset import build_dataset

    return build_dataset


def _json_default(value: Any) -> Any:
    try:
        import numpy as np

        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.bool_):
            return bool(value)
    except Exception:
        pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return str(value)


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=_json_default).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _stable_int(*parts: Any) -> int:
    digest = hashlib.blake2b(
        "::".join(str(part) for part in parts).encode("utf-8"),
        digest_size=8,
    ).hexdigest()
    return int(digest, 16)


def _safe_row_dict(row: pd.Series) -> dict[str, Any]:
    raw = row.to_dict()
    return {str(key): value for key, value in raw.items() if str(key) not in MEDIA_KEYS}


def _question_hash(row: pd.Series) -> str:
    raw = row.to_dict()
    for key in QUESTION_KEYS:
        if key in raw and raw[key] not in (None, ""):
            return _stable_hash({key: raw[key]})
    return _stable_hash(_safe_row_dict(row))


def _load_frame(spec: BenchmarkSpec) -> pd.DataFrame:
    _import_vlmeval_dataset_builder()
    dataset = build_vlmeval_dataset(spec)
    frame = dataset.data.copy()
    if "index" not in frame.columns:
        raise RuntimeError(f"Dataset {spec.alias} does not expose an index column")
    return frame.reset_index(drop=True)


def _sample_indices(frame: pd.DataFrame, count: int, *, seed: int, salt: str) -> list[int]:
    source_positions = list(range(len(frame)))
    if count >= len(source_positions):
        return source_positions
    rng = random.Random(_stable_int(seed, salt))
    rng.shuffle(source_positions)
    return sorted(source_positions[:count], key=lambda pos: str(frame.iloc[pos]["index"]))


def _largest_remainder_counts(total: int, weights: dict[str, int]) -> dict[str, int]:
    weight_total = sum(weights.values())
    if weight_total <= 0:
        raise ValueError("Cannot allocate from empty weights")
    raw = {key: total * value / weight_total for key, value in weights.items()}
    counts = {key: int(raw[key]) for key in weights}
    remaining = total - sum(counts.values())
    order = sorted(weights, key=lambda key: (raw[key] - counts[key], weights[key], key), reverse=True)
    for key in order[:remaining]:
        counts[key] += 1
    return counts


def _manifest_row(
    *,
    spec: BenchmarkSpec,
    row: pd.Series,
    sample_rank: int,
    sample_seed: int,
    source_row_count: int,
    subset_key: str | None = None,
    aggregate_sample_rank: int | None = None,
) -> dict[str, Any]:
    safe = _safe_row_dict(row)
    out = {
        "subset_version": "external_eval_v1",
        "benchmark_key": spec.aggregate_group or spec.key,
        "subset_key": subset_key,
        "spec_key": spec.key,
        "dataset_alias": spec.alias,
        "run_name": spec.run_name,
        "source_index": row["index"],
        "sample_rank": sample_rank,
        "sample_seed": sample_seed,
        "source_row_count": source_row_count,
        "row_hash": _stable_hash(safe),
        "question_hash": _question_hash(row),
    }
    if aggregate_sample_rank is not None:
        out["aggregate_sample_rank"] = aggregate_sample_rank
    return out


def _write_jsonl(path: Path, rows: list[dict[str, Any]], *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; pass --overwrite")
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=_json_default) + "\n")
    tmp.replace(path)


def _write_json(path: Path, obj: Any, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; pass --overwrite")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True, default=_json_default), encoding="utf-8")
    tmp.replace(path)


def _prepare_nonaggregate(
    *,
    spec: BenchmarkSpec,
    out_root: Path,
    sample_count: int,
    sample_seed: int,
    overwrite: bool,
) -> dict[str, Any]:
    frame = _load_frame(spec)
    positions = _sample_indices(frame, min(sample_count, len(frame)), seed=sample_seed, salt=spec.key)
    rows = [
        _manifest_row(
            spec=spec,
            row=frame.iloc[position],
            sample_rank=rank,
            sample_seed=sample_seed,
            source_row_count=len(frame),
        )
        for rank, position in enumerate(positions)
    ]
    _write_jsonl(out_root / f"{spec.key}.jsonl", rows, overwrite=overwrite)
    return {
        "benchmark_key": spec.key,
        "dataset_alias": spec.alias,
        "source_rows": len(frame),
        "selected_rows": len(rows),
        "manifest": f"{spec.key}.jsonl",
    }


def _prepare_aggregate(
    *,
    group: str,
    specs: list[BenchmarkSpec],
    out_root: Path,
    sample_count: int,
    sample_seed: int,
    overwrite: bool,
) -> dict[str, Any]:
    frames = {spec.key: _load_frame(spec) for spec in specs}
    source_counts = {key: len(frame) for key, frame in frames.items()}
    selected_counts = _largest_remainder_counts(sample_count, source_counts)
    aggregate_rows: list[dict[str, Any]] = []
    subset_summaries = []
    for spec in specs:
        frame = frames[spec.key]
        positions = _sample_indices(
            frame,
            min(selected_counts[spec.key], len(frame)),
            seed=sample_seed,
            salt=spec.key,
        )
        subset_rows = [
            _manifest_row(
                spec=spec,
                row=frame.iloc[position],
                sample_rank=rank,
                sample_seed=sample_seed,
                source_row_count=len(frame),
                subset_key=spec.key,
            )
            for rank, position in enumerate(positions)
        ]
        _write_jsonl(out_root / f"{spec.key}.jsonl", subset_rows, overwrite=overwrite)
        for row in subset_rows:
            row = dict(row)
            row["aggregate_sample_rank"] = len(aggregate_rows)
            aggregate_rows.append(row)
        subset_summaries.append(
            {
                "spec_key": spec.key,
                "dataset_alias": spec.alias,
                "source_rows": len(frame),
                "selected_rows": len(subset_rows),
                "manifest": f"{spec.key}.jsonl",
            }
        )
    _write_jsonl(out_root / f"{group}.jsonl", aggregate_rows, overwrite=overwrite)
    return {
        "benchmark_key": group,
        "source_rows": sum(source_counts.values()),
        "selected_rows": len(aggregate_rows),
        "manifest": f"{group}.jsonl",
        "subsets": subset_summaries,
    }


def _write_readme(path: Path, manifest: dict[str, Any], *, overwrite: bool) -> None:
    lines = [
        "---",
        "license: other",
        "tags:",
        "- trace",
        "- external-eval",
        "- benchmark-subsets",
        "---",
        "",
        "# TRACE External Eval Subsets v1",
        "",
        "Manifest-only fixed subsets for TRACE RLVR checkpoint evaluation.",
        "",
        "These files contain source dataset indices and hashes only. They do not",
        "redistribute benchmark images or media.",
        "",
        f"- sample seed: `{manifest['sample_seed']}`",
        f"- target rows per benchmark: `{manifest['sample_count_per_benchmark']}`",
        "",
        "| benchmark | selected rows | source rows | manifest |",
        "| --- | ---: | ---: | --- |",
    ]
    for item in manifest["benchmarks"]:
        lines.append(
            f"| `{item['benchmark_key']}` | {item['selected_rows']} | "
            f"{item['source_rows']} | `{item['manifest']}` |"
        )
    lines.extend(
        [
            "",
            "ScreenSpotPro is sampled as one pooled aggregate over its six VLMEval",
            "subsets. Per-subset manifests are included so queue workers can run the",
            "existing subset jobs while preserving the aggregate sample.",
            "",
        ]
    )
    text = "\n".join(lines)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; pass --overwrite")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=sorted(PRESETS), default=None)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--benchmarks", nargs="*", default=list(DEFAULT_BENCHMARKS))
    parser.add_argument("--sample-count", type=int, default=DEFAULT_SAMPLE_COUNT)
    parser.add_argument("--sample-seed", type=int, default=DEFAULT_SAMPLE_SEED)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.preset:
        preset = PRESETS[args.preset]
        args.out_root = Path(preset["out_root"])
        args.benchmarks = list(preset["benchmarks"])
        args.sample_count = int(preset["sample_count"])
        args.sample_seed = int(preset["sample_seed"])

    specs = filter_benchmark_specs(ALL_BENCHMARKS, only=args.benchmarks)
    if args.dry_run:
        print(f"[dry-run] out_root={args.out_root}")
        print(f"[dry-run] sample_count={args.sample_count} sample_seed={args.sample_seed}")
        for spec in specs:
            print(f"[dry-run] {spec.key} alias={spec.alias} run={spec.run_name}")
        return 0
    grouped: dict[str, list[BenchmarkSpec]] = defaultdict(list)
    nonaggregate: list[BenchmarkSpec] = []
    for spec in specs:
        if spec.aggregate_group:
            grouped[spec.aggregate_group].append(spec)
        else:
            nonaggregate.append(spec)
    direct_keys = {spec.key for spec in nonaggregate}
    grouped = {
        group: group_specs
        for group, group_specs in grouped.items()
        if group not in direct_keys
    }

    summaries = []
    for spec in nonaggregate:
        print(f"[subset] {spec.key} alias={spec.alias}")
        summaries.append(
            _prepare_nonaggregate(
                spec=spec,
                out_root=args.out_root,
                sample_count=args.sample_count,
                sample_seed=args.sample_seed,
                overwrite=args.overwrite,
            )
        )
    for group, group_specs in sorted(grouped.items()):
        print(f"[subset] {group} aggregate_specs={len(group_specs)}")
        summaries.append(
            _prepare_aggregate(
                group=group,
                specs=sorted(group_specs, key=lambda spec: spec.key),
                out_root=args.out_root,
                sample_count=args.sample_count,
                sample_seed=args.sample_seed,
                overwrite=args.overwrite,
            )
        )

    manifest = {
        "subset_version": "external_eval_v1",
        "sample_seed": args.sample_seed,
        "sample_count_per_benchmark": args.sample_count,
        "benchmarks": summaries,
        "total_selected_rows": sum(item["selected_rows"] for item in summaries),
    }
    _write_json(args.out_root / "manifest.json", manifest, overwrite=args.overwrite)
    _write_readme(args.out_root / "README.md", manifest, overwrite=args.overwrite)
    print(f"[done] wrote {args.out_root} rows={manifest['total_selected_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
