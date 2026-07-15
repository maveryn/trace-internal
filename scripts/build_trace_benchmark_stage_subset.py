#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import (  # noqa: E402
    REPO_ROOT as LIB_REPO_ROOT,
    TRACE_CANDIDATE37_200_SUBSET_ROOT,
    BenchmarkSpec,
    build_vlmeval_dataset,
    spec_by_key,
)
from run_external_benchmark_generation_queue import (  # noqa: E402
    _import_vlmeval_runner,
    _row_hash,
    _safe_row_mapping,
    _stable_hash,
)


DEFAULT_KEYS = (
    "chartmuseum",
    "chartqa",
    "game_qa_lite",
    "screenspot",
    "screenspotpro",
    "chartqapro",
    "puzzlevqa",
    "logicvista",
    "mathvista",
    "cvbench_3d",
    "wemath",
    "mathvision",
    "erqa",
    "treebench",
    "countbenchqa",
    "mathverse",
    "charxivreason",
    "phyx_mini_mc",
    "physics",
    "mmmu_pro_vision",
    "blink",
    "visiongraph_q3",
    "vstarbench",
    "vlmbias",
)


MEDIA_KEYS = {"image", "images", "image_path", "image_paths", "img", "picture", "video", "videos", "video_path", "video_paths"}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _question_hash(row: dict[str, Any]) -> str:
    safe = _safe_row_mapping(row)
    questionish = {
        key: value
        for key, value in safe.items()
        if key.lower() in {"question", "prompt", "query", "problem", "instruction", "text", "answer", "choices"}
    }
    return _stable_hash(questionish or safe)


def _stable_seed(base_seed: int, key: str, target_size: int) -> int:
    digest = hashlib.sha256(f"{base_seed}:{key}:{target_size}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _load_source_rows(spec: BenchmarkSpec, *, sample_seed: int) -> list[dict[str, Any]]:
    if spec.kind == "chartmuseum":
        _, chartmuseum = _import_vlmeval_runner()
        return chartmuseum.load_chartmuseum_rows(spec.split or "test", chartmuseum.DEFAULT_DATA_ROOT, None, sample_seed)

    _import_vlmeval_runner()
    dataset = build_vlmeval_dataset(spec)
    return [row.to_dict() for _, row in dataset.data.iterrows()]


def _entry_for_row(
    *,
    spec: BenchmarkSpec,
    row: dict[str, Any],
    sample_rank: int,
    sample_seed: int,
    source_row_count: int,
    subset_version: str,
    stage: str,
) -> dict[str, Any]:
    return {
        "benchmark_key": spec.key,
        "dataset_alias": spec.alias,
        "question_hash": _question_hash(row),
        "row_hash": _row_hash(row),
        "run_name": spec.run_name,
        "sample_rank": int(sample_rank),
        "sample_seed": int(sample_seed),
        "source_index": row.get("index"),
        "source_row_count": int(source_row_count),
        "spec_key": spec.key,
        "stage": stage,
        "subset_key": None,
        "subset_version": subset_version,
    }


def _previous_rows(previous_root: Path, spec: BenchmarkSpec, *, allow_missing: bool = False) -> list[dict[str, Any]]:
    path = previous_root / f"{spec.key}.jsonl"
    if not path.exists():
        if allow_missing:
            return []
        raise FileNotFoundError(f"Missing previous subset manifest for {spec.key}: {path}")
    rows = [row for row in _read_jsonl(path) if row.get("benchmark_key") in {spec.key, spec.aggregate_group}]
    rows.sort(key=lambda row: int(row["sample_rank"]))
    return rows


def build_subset(
    *,
    keys: list[str],
    previous_root: Path,
    out_root: Path,
    target_size: int,
    sample_seed: int,
    subset_version: str,
    allow_missing_previous: bool = False,
) -> dict[str, Any]:
    benchmark_summaries: list[dict[str, Any]] = []
    out_root.mkdir(parents=True, exist_ok=True)
    for key in keys:
        spec = spec_by_key(key)
        previous = _previous_rows(previous_root, spec, allow_missing=allow_missing_previous)
        source_rows = _load_source_rows(spec, sample_seed=sample_seed)
        source_by_index = {str(row.get("index")): row for row in source_rows}
        previous_indices = [str(row["source_index"]) for row in previous]
        missing_previous = [idx for idx in previous_indices if idx not in source_by_index]
        if missing_previous:
            raise ValueError(f"{key}: previous subset has indices not present in current source rows: {missing_previous[:10]}")

        carried: list[dict[str, Any]] = []
        for rank, prev in enumerate(previous):
            row = source_by_index[str(prev["source_index"])]
            entry = _entry_for_row(
                spec=spec,
                row=row,
                sample_rank=rank,
                sample_seed=sample_seed,
                source_row_count=len(source_rows),
                subset_version=subset_version,
                stage="carried_from_previous",
            )
            entry["previous_sample_rank"] = int(prev["sample_rank"])
            entry["previous_subset_version"] = prev.get("subset_version")
            carried.append(entry)

        remaining = [row for row in source_rows if str(row.get("index")) not in set(previous_indices)]
        rng = random.Random(_stable_seed(sample_seed, key, target_size))
        rng.shuffle(remaining)
        add_count = max(0, min(int(target_size) - len(carried), len(remaining)))
        added = [
            _entry_for_row(
                spec=spec,
                row=row,
                sample_rank=len(carried) + offset,
                sample_seed=sample_seed,
                source_row_count=len(source_rows),
                subset_version=subset_version,
                stage="stage_random_addition",
            )
            for offset, row in enumerate(remaining[:add_count])
        ]
        rows = carried + added
        _write_jsonl(out_root / f"{spec.key}.jsonl", rows)
        benchmark_summaries.append(
            {
                "benchmark_key": spec.key,
                "dataset_alias": spec.alias,
                "manifest": f"{spec.key}.jsonl",
                "previous_rows": len(previous),
                "previous_manifest_missing": not (previous_root / f"{spec.key}.jsonl").exists(),
                "added_rows": len(added),
                "selected_rows": len(rows),
                "source_rows": len(source_rows),
                "target_size": int(target_size),
            }
        )
        print(
            f"{spec.key}: previous={len(previous)} added={len(added)} "
            f"selected={len(rows)} source={len(source_rows)}"
        )

    manifest = {
        "benchmarks": benchmark_summaries,
        "keys": keys,
        "previous_subset_root": str(previous_root.relative_to(LIB_REPO_ROOT) if previous_root.is_relative_to(LIB_REPO_ROOT) else previous_root),
        "sample_seed": int(sample_seed),
        "subset_root": str(out_root.relative_to(LIB_REPO_ROOT) if out_root.is_relative_to(LIB_REPO_ROOT) else out_root),
        "subset_version": subset_version,
        "target_size": int(target_size),
        "allow_missing_previous": bool(allow_missing_previous),
    }
    _write_json(out_root / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-root", type=Path, default=TRACE_CANDIDATE37_200_SUBSET_ROOT)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--target-size", type=int, required=True)
    parser.add_argument("--sample-seed", type=int, default=42)
    parser.add_argument("--subset-version", default="")
    parser.add_argument("--only", nargs="*", default=list(DEFAULT_KEYS))
    parser.add_argument(
        "--allow-missing-previous",
        action="store_true",
        help="Treat a missing previous-stage manifest as an empty carried subset for newly added benchmarks.",
    )
    args = parser.parse_args()
    subset_version = args.subset_version or f"trace_candidate{len(args.only)}_{args.target_size}_seed{args.sample_seed}"
    build_subset(
        keys=list(args.only),
        previous_root=args.previous_root,
        out_root=args.out_root,
        target_size=int(args.target_size),
        sample_seed=int(args.sample_seed),
        subset_version=subset_version,
        allow_missing_previous=bool(args.allow_missing_previous),
    )


if __name__ == "__main__":
    main()
