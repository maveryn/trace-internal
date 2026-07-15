#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from benchmark_queue_lib import TRACE_FINAL25_BENCHMARKS, run_dir, spec_by_key  # noqa: E402


DEFAULT_MODEL_SLUGS = (
    "qwen25vl3b-base",
    "trace-qwen25vl3b-easyr1-all1000-answer-nokl-step500",
    "qwen25vl7b-base",
    "trace-qwen25vl7b-easyr1-all1000-answer-nokl-step500",
    "game-rl-qwen25vl7b",
    "sphinx-qwen7b-500",
    "pcgrpo-qwen25vl7b-jigsaw-care",
    "vero-qwen25-7b",
)

PRUNED_DIR_NAMES = {
    ".git",
    "cache",
    "datasets",
    "easyr1_checkpoints",
    "export_archives",
    "hf_models",
    "hf_verify_cache",
    "LMUData",
    "lmudata",
    "merged_hf",
    "ray",
    "tmp",
    "wandb",
}


@dataclass(frozen=True)
class Candidate:
    seed: int
    model_slug: str
    benchmark_key: str
    summary_path: Path
    row_result_dir: Path
    rows: int
    mtime_ns: int


def _same_float(value: Any, expected: float) -> bool:
    try:
        return abs(float(value) - float(expected)) < 1e-9
    except (TypeError, ValueError):
        return False


def _iter_summary_paths(search_roots: Iterable[Path], campaign_root: Path) -> Iterable[Path]:
    campaign_root = campaign_root.resolve()
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for root, dirs, files in os.walk(search_root):
            root_path = Path(root)
            dirs[:] = [
                name
                for name in dirs
                if name not in PRUNED_DIR_NAMES
                and not (root_path / name).resolve().is_relative_to(campaign_root)
            ]
            if "generation_summary.json" in files:
                yield root_path / "generation_summary.json"


def _candidate_from_summary(
    path: Path,
    *,
    model_slugs: set[str],
    seeds: set[int],
    temperature: float,
    top_p: float,
    top_k: int,
    presence_penalty: float,
    repetition_penalty: float,
    max_tokens: int,
) -> Candidate | None:
    try:
        summary = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    generation = summary.get("generation") or {}
    model_slug = str(summary.get("model_slug") or "")
    try:
        seed = int(generation.get("seed"))
    except (TypeError, ValueError):
        return None
    benchmark_key = path.parents[2].name if len(path.parents) >= 3 else ""
    if model_slug not in model_slugs or seed not in seeds or benchmark_key not in TRACE_FINAL25_BENCHMARKS:
        return None
    if not all(
        (
            _same_float(generation.get("temperature"), temperature),
            _same_float(generation.get("top_p"), top_p),
            int(generation.get("top_k", 0)) == int(top_k),
            _same_float(generation.get("presence_penalty"), presence_penalty),
            _same_float(generation.get("repetition_penalty"), repetition_penalty),
            int(generation.get("max_tokens", 0)) == int(max_tokens),
        )
    ):
        return None
    rows = int(summary.get("rows") or 0)
    expected_rows = int(summary.get("expected_rows") or 0)
    if rows <= 0 or rows != expected_rows:
        return None
    row_result_dir = path.parent / "api_row_results"
    if not row_result_dir.is_dir():
        return None
    result_count = sum(1 for _ in row_result_dir.glob("*.json"))
    if result_count < rows:
        return None
    return Candidate(
        seed=seed,
        model_slug=model_slug,
        benchmark_key=benchmark_key,
        summary_path=path,
        row_result_dir=row_result_dir,
        rows=rows,
        mtime_ns=path.stat().st_mtime_ns,
    )


def _destination_name(source: Path, source_dir: Path, target_dir: Path) -> Path:
    target = target_dir / source.name
    if not target.exists():
        return target
    try:
        if os.path.samefile(source, target):
            return target
    except OSError:
        pass
    digest = hashlib.sha256(f"{source_dir}:{source.name}".encode("utf-8")).hexdigest()[:12]
    return target_dir / f"reuse_{digest}_{source.name}"


def _link_candidate(candidate: Candidate, campaign_root: Path, *, dry_run: bool) -> dict[str, Any]:
    spec = spec_by_key(candidate.benchmark_key)
    run_root = campaign_root / f"seed_{candidate.seed}" / "runs"
    target_dir = run_dir(spec, candidate.model_slug, run_root) / "api_row_results"
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    linked = 0
    existing = 0
    copied = 0
    for source in candidate.row_result_dir.glob("*.json"):
        target = _destination_name(source, candidate.row_result_dir, target_dir)
        if target.exists():
            existing += 1
            continue
        if dry_run:
            linked += 1
            continue
        try:
            os.link(source, target)
            linked += 1
        except OSError:
            shutil.copy2(source, target)
            copied += 1
    return {
        "seed": candidate.seed,
        "model_slug": candidate.model_slug,
        "benchmark_key": candidate.benchmark_key,
        "rows": candidate.rows,
        "source_summary": str(candidate.summary_path),
        "source_row_results": str(candidate.row_result_dir),
        "target_row_results": str(target_dir),
        "linked": linked,
        "copied": copied,
        "already_present": existing,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reuse compatible Final25 per-row generation artifacts.")
    parser.add_argument("--campaign-root", type=Path, required=True)
    parser.add_argument("--search-root", action="append", type=Path, required=True)
    parser.add_argument("--model-slug", action="append", dest="model_slugs", default=[])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    parser.add_argument("--temperature", type=float, default=0.6)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, default=-1)
    parser.add_argument("--presence-penalty", type=float, default=0.0)
    parser.add_argument("--repetition-penalty", type=float, default=1.0)
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    model_slugs = set(args.model_slugs or DEFAULT_MODEL_SLUGS)
    seeds = set(args.seeds)
    candidates: dict[tuple[int, str, str], Candidate] = {}
    scanned = 0
    accepted = 0
    for summary_path in _iter_summary_paths(args.search_root, args.campaign_root):
        scanned += 1
        candidate = _candidate_from_summary(
            summary_path,
            model_slugs=model_slugs,
            seeds=seeds,
            temperature=args.temperature,
            top_p=args.top_p,
            top_k=args.top_k,
            presence_penalty=args.presence_penalty,
            repetition_penalty=args.repetition_penalty,
            max_tokens=args.max_tokens,
        )
        if candidate is None:
            continue
        accepted += 1
        key = (candidate.seed, candidate.model_slug, candidate.benchmark_key)
        previous = candidates.get(key)
        if previous is None or (candidate.rows, candidate.mtime_ns) > (previous.rows, previous.mtime_ns):
            candidates[key] = candidate

    reused = [
        _link_candidate(candidate, args.campaign_root, dry_run=args.dry_run)
        for candidate in sorted(candidates.values(), key=lambda item: (item.model_slug, item.seed, item.benchmark_key))
    ]
    expected = {
        (seed, model_slug, benchmark)
        for seed in seeds
        for model_slug in model_slugs
        for benchmark in TRACE_FINAL25_BENCHMARKS
    }
    found = {(item.seed, item.model_slug, item.benchmark_key) for item in candidates.values()}
    missing = [
        {"seed": seed, "model_slug": model_slug, "benchmark_key": benchmark}
        for seed, model_slug, benchmark in sorted(expected - found)
    ]
    manifest = {
        "campaign_root": str(args.campaign_root),
        "search_roots": [str(path) for path in args.search_root],
        "config": {
            "seeds": sorted(seeds),
            "model_slugs": sorted(model_slugs),
            "temperature": args.temperature,
            "top_p": args.top_p,
            "top_k": args.top_k,
            "presence_penalty": args.presence_penalty,
            "repetition_penalty": args.repetition_penalty,
            "max_tokens": args.max_tokens,
        },
        "summaries_scanned": scanned,
        "compatible_summaries": accepted,
        "selected_sources": len(candidates),
        "reused": reused,
        "missing_model_seed_benchmarks": missing,
        "dry_run": args.dry_run,
    }
    args.campaign_root.mkdir(parents=True, exist_ok=True)
    manifest_path = args.campaign_root / "generation_reuse_manifest.json"
    if not args.dry_run:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        "[reuse:done] "
        f"scanned={scanned} compatible={accepted} selected={len(candidates)} "
        f"missing={len(missing)} linked={sum(item['linked'] for item in reused)} "
        f"copied={sum(item['copied'] for item in reused)} manifest={manifest_path}"
    )


if __name__ == "__main__":
    main()
