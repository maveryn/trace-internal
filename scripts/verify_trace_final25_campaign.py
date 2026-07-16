#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import (  # noqa: E402
    TRACE_FINAL25_BENCHMARKS,
    TRACE_FINAL26_BENCHMARKS,
    extract_score_and_rows,
    run_dir,
    score_path,
    spec_by_key,
)
from final25_media_contract import (  # noqa: E402
    GENERATION_CONTRACT_VERSION,
    MEDIA_CONTRACT_VERSION,
    MEDIA_TRANSPORT,
    QWEN_MAX_IMAGE_PIXELS,
    QWEN_MIN_IMAGE_PIXELS,
)
from run_external_benchmark_generation_api_queue import _generation_contract_hash  # noqa: E402


SUITE_BENCHMARKS: dict[str, tuple[str, ...]] = {
    "frozen": TRACE_FINAL25_BENCHMARKS,
    "all26": TRACE_FINAL26_BENCHMARKS,
}


def _benchmarks_for_suite(suite: str) -> tuple[str, ...]:
    return SUITE_BENCHMARKS[suite]


def _parse_model_entries(values: list[str]) -> dict[str, tuple[str, str]]:
    entries: dict[str, tuple[str, str]] = {}
    for value in values:
        parts = value.split("=", 2)
        if len(parts) != 3 or not all(part.strip() for part in parts):
            raise ValueError(f"invalid --model-entry {value!r}; expected SLUG=MODEL=REVISION")
        slug, model, revision = (part.strip() for part in parts)
        if slug in entries:
            raise ValueError(f"duplicate --model-entry for {slug!r}")
        entries[slug] = (model, revision)
    return entries


def _expected_generation_contract_hash(
    *,
    model: str,
    model_slug: str,
    model_revision: str,
    seed: int,
    dataset_snapshot_sha256: str,
    dataset_revision: str,
    final25_code_hash: str,
) -> str:
    contract_args = argparse.Namespace(
        model=model,
        model_slug=model_slug,
        api_model=model_slug,
        temperature=0.6,
        top_p=1.0,
        top_k=-1,
        presence_penalty=0.0,
        repetition_penalty=1.0,
        max_tokens=4096,
        seed=seed,
        media_transport=MEDIA_TRANSPORT,
        min_image_pixels=QWEN_MIN_IMAGE_PIXELS,
        max_image_pixels=QWEN_MAX_IMAGE_PIXELS,
        max_image_side=1280,
        image_jpeg_quality=85,
        dataset_snapshot_sha256=dataset_snapshot_sha256,
        subset_root=None,
        limit=None,
        sample_seed=0,
    )
    return _generation_contract_hash(
        contract_args,
        model_revision=model_revision,
        dataset_revision=dataset_revision,
        final25_code_hash=final25_code_hash,
    )


def _generation_complete(
    path: Path,
    seed: int,
    dataset_revision: str,
    *,
    expected_model_revision: str,
    expected_contract_hash: str,
) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        generation = payload["generation"]
        rows = int(payload["rows"])
        expected = int(payload["expected_rows"])
        selection = generation.get("selection") or {}
        checks = {
            "rows": rows > 0 and rows == expected,
            "seed": int(generation["seed"]) == seed,
            "temperature": abs(float(generation["temperature"]) - 0.6) < 1e-9,
            "top_p": abs(float(generation["top_p"]) - 1.0) < 1e-9,
            "top_k": int(generation["top_k"]) == -1,
            "presence_penalty": abs(float(generation["presence_penalty"])) < 1e-9,
            "repetition_penalty": abs(float(generation["repetition_penalty"]) - 1.0) < 1e-9,
            "max_tokens": int(generation["max_tokens"]) == 4096,
            "compact_tables": bool(generation.get("compact_prediction_tables")),
            "contract_version": generation.get("contract_version") == GENERATION_CONTRACT_VERSION,
            "contract_hash": generation.get("contract_hash") == expected_contract_hash,
            "media_contract": generation.get("media_contract_version") == MEDIA_CONTRACT_VERSION,
            "media_transport": generation.get("media_transport") == MEDIA_TRANSPORT,
            "min_pixels": int(generation.get("min_image_pixels", 0)) == QWEN_MIN_IMAGE_PIXELS,
            "max_pixels": int(generation.get("max_image_pixels", 0)) == QWEN_MAX_IMAGE_PIXELS,
            "dataset_snapshot": bool(generation.get("dataset_snapshot_sha256")),
            "dataset_revision": generation.get("dataset_revision") == dataset_revision,
            "model_revision": generation.get("model_revision") == expected_model_revision,
            "full_selection": (
                selection.get("mode") == "full"
                and selection.get("limit") is None
                and selection.get("sample_seed") is None
                and selection.get("subset_manifest_sha256") is None
                and payload.get("subset_manifest") is None
            ),
        }
        failed = [name for name, passed in checks.items() if not passed]
        detail = f"{rows}/{expected}" + (f" mismatch={','.join(failed)}" if failed else "")
        return not failed, detail
    except Exception as exc:
        return False, f"invalid:{type(exc).__name__}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify strict TRACE evaluation campaign completeness.")
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("generation", "score"), required=True)
    parser.add_argument(
        "--suite",
        choices=tuple(SUITE_BENCHMARKS),
        default="frozen",
        help="Benchmark coverage to verify (default: frozen Final25).",
    )
    parser.add_argument("--model-slug", action="append", dest="model_slugs", required=True)
    parser.add_argument(
        "--model-entry",
        action="append",
        default=[],
        metavar="SLUG=MODEL=REVISION",
        help="Expected generation model path and immutable revision for each model slug.",
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--dataset-revision",
        default=os.environ.get("TRACE_FINAL25_DATASET_REVISION"),
    )
    parser.add_argument(
        "--dataset-snapshot-sha256",
        default=os.environ.get("TRACE_FINAL25_DATASET_SNAPSHOT"),
    )
    parser.add_argument(
        "--final25-code-hash",
        default=os.environ.get("TRACE_FINAL25_CODE_HASH"),
    )
    args = parser.parse_args()

    try:
        model_entries = _parse_model_entries(args.model_entry)
    except ValueError as exc:
        parser.error(str(exc))
    if args.phase == "generation":
        missing_entries = sorted(set(args.model_slugs) - set(model_entries))
        if missing_entries:
            parser.error(f"generation verification is missing --model-entry for: {missing_entries}")
        if not args.dataset_revision:
            parser.error("generation verification requires --dataset-revision")
        if not args.dataset_snapshot_sha256:
            parser.error("generation verification requires --dataset-snapshot-sha256")
        if not args.final25_code_hash:
            parser.error("generation verification requires --final25-code-hash")

    benchmarks = _benchmarks_for_suite(args.suite)
    records = []
    for seed in args.seeds:
        run_root = args.campaign_root / f"seed_{seed}" / "runs"
        benchmark_root = args.campaign_root / f"seed_{seed}" / "benchmark"
        for model_slug in args.model_slugs:
            for benchmark_key in benchmarks:
                spec = spec_by_key(benchmark_key)
                if args.phase == "generation":
                    path = run_dir(spec, model_slug, run_root) / "generation_summary.json"
                    model, model_revision = model_entries[model_slug]
                    expected_contract_hash = _expected_generation_contract_hash(
                        model=model,
                        model_slug=model_slug,
                        model_revision=model_revision,
                        seed=seed,
                        dataset_snapshot_sha256=args.dataset_snapshot_sha256,
                        dataset_revision=args.dataset_revision,
                        final25_code_hash=args.final25_code_hash,
                    )
                    complete, detail = _generation_complete(
                        path,
                        seed,
                        args.dataset_revision,
                        expected_model_revision=model_revision,
                        expected_contract_hash=expected_contract_hash,
                    )
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
                        "suite": args.suite,
                        "phase": args.phase,
                        "complete": complete,
                        "detail": detail,
                        "path": str(path),
                    }
                )
    incomplete = [record for record in records if not record["complete"]]
    if args.json:
        print(json.dumps({"complete": not incomplete, "suite": args.suite, "records": records}, indent=2))
    else:
        log_tag = "final25" if args.suite == "frozen" else "all26"
        print(
            f"[{log_tag}-verify] phase={args.phase} complete={len(records) - len(incomplete)}/{len(records)} "
            f"incomplete={len(incomplete)}"
        )
        for record in incomplete[:25]:
            print(
                f"[{log_tag}-verify:missing] "
                f"seed={record['seed']} model={record['model_slug']} benchmark={record['benchmark_key']} "
                f"detail={record['detail']}"
            )
    raise SystemExit(1 if incomplete else 0)


if __name__ == "__main__":
    main()
