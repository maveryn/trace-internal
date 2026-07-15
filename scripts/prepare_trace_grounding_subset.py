#!/usr/bin/env python3
"""Prepare the fixed Trace grounding benchmark subset manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import (  # noqa: E402
    TRACE_GROUNDING_SUBSET_ROOT,
    VLMEVAL_ROOT,
    BenchmarkSpec,
    benchmark_specs_for_run_set,
    filter_benchmark_specs,
    json_default,
    materialize_grounding_benchmark_files,
)
from run_external_benchmark_generation_queue import _row_hash  # noqa: E402


DEFAULT_SAMPLE_SEED = 42
REFCOCOG_TEST_SAMPLE_COUNT = 1000


def _import_build_dataset():
    scripts_root = VLMEVAL_ROOT / "scripts"
    for path in (VLMEVAL_ROOT, scripts_root):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from vlmeval.dataset import build_dataset

    return build_dataset


def _stable_int(*parts: Any) -> int:
    digest = hashlib.blake2b(
        "::".join(str(part) for part in parts).encode("utf-8"),
        digest_size=8,
    ).hexdigest()
    return int(digest, 16)


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, default=json_default).encode("utf-8")
    ).hexdigest()


def _question_hash(row: pd.Series) -> str:
    raw = row.to_dict()
    for key in ("question", "query", "prompt", "instruction", "input"):
        value = raw.get(key)
        if value not in (None, ""):
            return _stable_hash({key: value})
    return _stable_hash({str(key): value for key, value in raw.items() if str(key) not in {"image", "image_path"}})


def _select_frame(spec: BenchmarkSpec, frame: pd.DataFrame, *, sample_seed: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    if spec.key != "refcoco":
        return frame.reset_index(drop=True), {
            "selection": "all_rows",
            "source_filter": None,
            "source_rows_after_filter": len(frame),
        }

    filtered = frame[frame["split"].astype(str) == "RefCOCOg_test"].copy()
    if filtered.empty:
        raise ValueError("RefCOCO subset expected non-empty split == RefCOCOg_test")
    positions = list(range(len(filtered)))
    rng = random.Random(_stable_int(sample_seed, spec.key, "RefCOCOg_test"))
    rng.shuffle(positions)
    positions = sorted(positions[: min(REFCOCOG_TEST_SAMPLE_COUNT, len(filtered))], key=lambda pos: str(filtered.iloc[pos]["index"]))
    return filtered.iloc[positions].reset_index(drop=True), {
        "selection": "fixed_random_subset",
        "source_filter": {"split": "RefCOCOg_test"},
        "source_rows_after_filter": len(filtered),
        "target_rows": REFCOCOG_TEST_SAMPLE_COUNT,
    }


def _manifest_row(
    *,
    spec: BenchmarkSpec,
    row: pd.Series,
    sample_rank: int,
    sample_seed: int,
    source_row_count: int,
    selection: dict[str, Any],
) -> dict[str, Any]:
    return {
        "subset_version": "trace_grounding_v1",
        "benchmark_key": spec.key,
        "dataset_alias": spec.alias,
        "run_name": spec.run_name,
        "source_index": row["index"],
        "sample_rank": sample_rank,
        "sample_seed": sample_seed,
        "source_row_count": source_row_count,
        "selection": selection["selection"],
        "source_filter": selection["source_filter"],
        "source_rows_after_filter": selection["source_rows_after_filter"],
        "row_hash": _row_hash(row),
        "question_hash": _question_hash(row),
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]], *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} exists; pass --overwrite")
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, default=json_default) + "\n")
    tmp.replace(path)


def _write_text(path: Path, text: str, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} exists; pass --overwrite")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-root", type=Path, default=TRACE_GROUNDING_SUBSET_ROOT)
    parser.add_argument("--benchmarks", nargs="*", default=[])
    parser.add_argument("--sample-seed", type=int, default=DEFAULT_SAMPLE_SEED)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    specs = benchmark_specs_for_run_set("trace_grounding")
    specs = filter_benchmark_specs(specs, only=args.benchmarks)
    if not specs:
        raise ValueError("No grounding benchmarks selected")

    materialize_grounding_benchmark_files(specs)
    build_dataset = _import_build_dataset()

    summaries = []
    for spec in specs:
        dataset = build_dataset(spec.alias)
        if dataset is None:
            raise RuntimeError(f"VLMEvalKit could not build dataset {spec.alias}")
        frame = dataset.data.copy().reset_index(drop=True)
        selected, selection = _select_frame(spec, frame, sample_seed=args.sample_seed)
        rows = [
            _manifest_row(
                spec=spec,
                row=selected.iloc[idx],
                sample_rank=idx,
                sample_seed=args.sample_seed,
                source_row_count=len(frame),
                selection=selection,
            )
            for idx in range(len(selected))
        ]
        _write_jsonl(args.out_root / f"{spec.key}.jsonl", rows, overwrite=args.overwrite)
        summaries.append(
            {
                "benchmark_key": spec.key,
                "dataset_alias": spec.alias,
                "source_rows": len(frame),
                "selected_rows": len(rows),
                **selection,
                "manifest": f"{spec.key}.jsonl",
            }
        )
        print(f"[subset] {spec.key} alias={spec.alias} source={len(frame)} selected={len(rows)}")

    manifest = {
        "subset_version": "trace_grounding_v1",
        "sample_seed": args.sample_seed,
        "benchmarks": summaries,
    }
    manifest_path = args.out_root / "manifest.json"
    if manifest_path.exists() and not args.overwrite:
        raise FileExistsError(f"{manifest_path} exists; pass --overwrite")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    lines = [
        "# Trace Grounding Benchmark Subsets",
        "",
        "Fixed manifest-only subsets for grounding benchmark evaluation.",
        "",
        f"- sample seed: `{args.sample_seed}`",
        "- `RefCOCO` is restricted to `split == RefCOCOg_test` and sampled to 1000 rows.",
        "- Other grounding benchmarks are kept at full size.",
        "",
        "| benchmark | alias | selected rows | source rows | selection |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for item in summaries:
        filt = item["source_filter"]
        selection_text = item["selection"] if not filt else f"{item['selection']} ({json.dumps(filt, sort_keys=True)})"
        lines.append(
            f"| `{item['benchmark_key']}` | `{item['dataset_alias']}` | {item['selected_rows']} | "
            f"{item['source_rows']} | {selection_text} |"
        )
    lines.append("")
    _write_text(args.out_root / "README.md", "\n".join(lines), overwrite=args.overwrite)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
