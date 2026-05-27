#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
VLMEVAL_ROOT = Path(os.environ.get("VLMEVAL_ROOT", "/home/jovyan/work/VLMEvalKit"))

SCREENSPOT_PRO_ALIASES = [
    "ScreenSpot_Pro_Development",
    "ScreenSpot_Pro_Creative",
    "ScreenSpot_Pro_CAD",
    "ScreenSpot_Pro_Scientific",
    "ScreenSpot_Pro_Office",
    "ScreenSpot_Pro_OS",
]


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
    return str(value)


def _import_build_dataset():
    for path in (VLMEVAL_ROOT, VLMEVAL_ROOT / "scripts"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from vlmeval.dataset import build_dataset

    return build_dataset


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    tmp.replace(path)


def materialize_alias(alias: str, cache_root: Path, force: bool) -> dict[str, Any]:
    output_dir = cache_root / alias
    parquet_path = output_dir / "data.parquet"
    summary_path = output_dir / "summary.json"
    if parquet_path.exists() and summary_path.exists() and not force:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["skipped_existing"] = True
        return summary

    build_dataset = _import_build_dataset()
    t0 = time.time()
    dataset = build_dataset(alias)
    if dataset is None:
        raise RuntimeError(f"VLMEvalKit could not build dataset {alias}")
    data = dataset.data.copy()
    output_dir.mkdir(parents=True, exist_ok=True)
    data.to_parquet(parquet_path, index=False, compression="zstd")
    summary = {
        "alias": alias,
        "rows": int(len(data)),
        "columns": list(map(str, data.columns)),
        "parquet": str(parquet_path),
        "elapsed_sec": time.time() - t0,
        "vlmeval_root": str(VLMEVAL_ROOT),
        "lmu_data_root": os.environ.get("LMUData", os.environ.get("LMU_DATA", "/home/jovyan/LMUData")),
    }
    _write_json(summary_path, summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aliases", nargs="+", default=SCREENSPOT_PRO_ALIASES)
    parser.add_argument("--cache-root", type=Path, default=REPO_ROOT / "benchmark/cache/vlmeval")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    args.cache_root.mkdir(parents=True, exist_ok=True)
    for alias in args.aliases:
        print(f"[materialize:start] {alias}", flush=True)
        try:
            summary = materialize_alias(alias, args.cache_root, args.force)
        except Exception as exc:
            print(f"[materialize:error] {alias}: {exc!r}", flush=True)
            raise
        print(
            f"[materialize:done] {alias} rows={summary.get('rows')} "
            f"parquet={summary.get('parquet')} elapsed={summary.get('elapsed_sec', 0):.1f}s "
            f"skipped={summary.get('skipped_existing', False)}",
            flush=True,
        )


if __name__ == "__main__":
    main()
