#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import (  # noqa: E402
    TRACE_FINAL25_BENCHMARKS,
    extract_score_and_rows,
    run_dir,
    score_path,
    spec_by_key,
)


def _generation_complete(path: Path, seed: int) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        generation = payload["generation"]
        rows = int(payload["rows"])
        expected = int(payload["expected_rows"])
        valid = (
            rows > 0
            and rows == expected
            and int(generation["seed"]) == seed
            and abs(float(generation["temperature"]) - 0.6) < 1e-9
            and abs(float(generation["top_p"]) - 1.0) < 1e-9
            and int(generation["top_k"]) == -1
            and abs(float(generation["presence_penalty"])) < 1e-9
            and abs(float(generation["repetition_penalty"]) - 1.0) < 1e-9
            and int(generation["max_tokens"]) == 4096
            and bool(generation.get("compact_prediction_tables"))
        )
        return valid, f"{rows}/{expected}"
    except Exception as exc:
        return False, f"invalid:{type(exc).__name__}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify strict TRACE Final25 campaign completeness.")
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("generation", "score"), required=True)
    parser.add_argument("--model-slug", action="append", dest="model_slugs", required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    records = []
    for seed in args.seeds:
        run_root = args.campaign_root / f"seed_{seed}" / "runs"
        benchmark_root = args.campaign_root / f"seed_{seed}" / "benchmark"
        for model_slug in args.model_slugs:
            for benchmark_key in TRACE_FINAL25_BENCHMARKS:
                spec = spec_by_key(benchmark_key)
                if args.phase == "generation":
                    path = run_dir(spec, model_slug, run_root) / "generation_summary.json"
                    complete, detail = _generation_complete(path, seed)
                else:
                    path = score_path(spec, model_slug, benchmark_root)
                    if not path.exists():
                        complete, detail = False, "missing"
                    else:
                        try:
                            payload = json.loads(path.read_text(encoding="utf-8"))
                            score, rows = extract_score_and_rows(payload)
                            complete = score is not None and math.isfinite(float(score)) and int(rows or payload.get("rows") or 0) > 0
                            detail = f"score={score} rows={rows or payload.get('rows')}"
                        except Exception as exc:
                            complete, detail = False, f"invalid:{type(exc).__name__}"
                records.append(
                    {
                        "seed": seed,
                        "model_slug": model_slug,
                        "benchmark_key": benchmark_key,
                        "phase": args.phase,
                        "complete": complete,
                        "detail": detail,
                        "path": str(path),
                    }
                )
    incomplete = [record for record in records if not record["complete"]]
    if args.json:
        print(json.dumps({"complete": not incomplete, "records": records}, indent=2))
    else:
        print(
            f"[final25-verify] phase={args.phase} complete={len(records) - len(incomplete)}/{len(records)} "
            f"incomplete={len(incomplete)}"
        )
        for record in incomplete[:25]:
            print(
                "[final25-verify:missing] "
                f"seed={record['seed']} model={record['model_slug']} benchmark={record['benchmark_key']} "
                f"detail={record['detail']}"
            )
    raise SystemExit(1 if incomplete else 0)


if __name__ == "__main__":
    main()
