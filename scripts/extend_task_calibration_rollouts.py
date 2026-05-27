#!/usr/bin/env python3
"""Legacy helper to extend existing TRACE calibration rollouts.

The current calibration baseline should use ``run_task_calibration_sweep.py``
to generate fresh ``100x24`` artifacts directly. This runner remains only for
manual recovery of older partial probes where a task already has a completed
``100x16`` calibration artifact and we want to add an ``x8`` companion run
without discarding the original model outputs.  It writes a merged ``100x24``
probe directory, exports solve-rate workbooks from that merged directory, and
updates the calibration sweep status files.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load_sweep_module():
    path = REPO_ROOT / "scripts" / "run_task_calibration_sweep.py"
    spec = importlib.util.spec_from_file_location("_trace_calibration_sweep", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load sweep module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[str(spec.name)] = module
    spec.loader.exec_module(module)
    return module


sweep = _load_sweep_module()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default="", help="Comma-separated task ids. Defaults to all active defaults.")
    parser.add_argument("--domain", action="append", default=[], help="Restrict to one public domain. Repeatable.")
    parser.add_argument("--scene", action="append", default=[], help="Restrict to <domain>/<scene_id>. Repeatable.")
    parser.add_argument("--start-at", default="", help="Start at this task id after sorting.")
    parser.add_argument("--start-after", default="", help="Start after this task id after sorting.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of tasks to process.")
    parser.add_argument("--models", default="qwen25vl7b", help="Comma-separated model aliases or HF ids.")
    parser.add_argument("--seed", type=int, default=20260507)
    parser.add_argument("--extra-seed", type=int, default=20260515)
    parser.add_argument("--sample-count", type=int, default=100)
    parser.add_argument("--base-rollouts", type=int, default=16)
    parser.add_argument("--extra-rollouts", type=int, default=8)
    parser.add_argument("--combined-rollouts", type=int, default=24)
    parser.add_argument("--batch-size", type=int, default=1600)
    parser.add_argument("--retry-batch-size", type=int, default=800)
    parser.add_argument("--max-prompt-length", type=int, default=2048)
    parser.add_argument("--max-tokens", type=int, default=0)
    parser.add_argument("--max-model-len", type=int, default=0)
    parser.add_argument("--max-num-batched-tokens", type=int, default=24576)
    parser.add_argument("--max-num-seqs", type=int, default=1600)
    parser.add_argument("--max-pixels", type=int, default=4194304)
    parser.add_argument("--gpu", default="0")
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    parser.add_argument("--gpu-wait-interval", type=int, default=60)
    parser.add_argument("--gpu-max-used-mb", type=int, default=1024)
    parser.add_argument("--gpu-max-utilization", type=int, default=10)
    parser.add_argument("--no-wait-for-gpu", action="store_true")
    parser.add_argument("--probe-backend", choices=("local_vllm", "openai_server"), default="openai_server")
    parser.add_argument("--server-base-url", default="")
    parser.add_argument("--server-api-key", default="EMPTY")
    parser.add_argument("--server-model", default="")
    parser.add_argument("--server-timeout", type=float, default=600.0)
    parser.add_argument("--server-max-retries", type=int, default=3)
    parser.add_argument("--server-concurrency", type=int, default=128)
    parser.add_argument("--output-root", default="out/calibration/current")
    parser.add_argument("--probe-root", default="rlvr/outputs/calibration/current")
    parser.add_argument("--review-root", default="plans/task-reviews")
    parser.add_argument("--status-json", default="plans/calibration_sweep_status.json")
    parser.add_argument("--status-md", default="plans/calibration_sweep_status.md")
    parser.add_argument("--calibration-baseline", default="v0")
    parser.add_argument("--per-rollout-response-mode", choices=("none", "full", "truncated"), default="full")
    parser.add_argument("--per-rollout-response-max-chars", type=int, default=4000)
    parser.add_argument("--force-extra", action="store_true", help="Rerun the extra rollout probe even if complete.")
    parser.add_argument("--force-combine", action="store_true", help="Rewrite the combined probe directory.")
    parser.add_argument("--force-stats", action="store_true", help="Re-export combined solve-rate stats.")
    parser.add_argument("--skip-extra", action="store_true", help="Only combine/export from an existing extra run.")
    parser.add_argument("--skip-scene-workbooks", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _probe_output_dir(args: argparse.Namespace, task_id: str, model: Any, *, rollouts: int, seed: int) -> Path:
    task_args = copy.copy(args)
    task_args.rollouts_per_prompt = int(rollouts)
    task_args.seed = int(seed)
    return sweep._probe_output_dir(task_args, task_id, model)


def _extra_output_dir(args: argparse.Namespace, task_id: str, model: Any) -> Path:
    taxonomy = sweep.resolve_task_taxonomy(task_id)
    return (
        Path(args.probe_root)
        / model.slug
        / str(taxonomy.domain)
        / str(taxonomy.scene_id)
        / task_id
        / (
            f"{int(args.sample_count)}x{int(args.extra_rollouts)}_seed{int(args.extra_seed)}"
            f"_extend_from{int(args.base_rollouts)}"
        )
    )


def _combined_output_dir(args: argparse.Namespace, task_id: str, model: Any) -> Path:
    return _probe_output_dir(args, task_id, model, rollouts=int(args.combined_rollouts), seed=int(args.seed))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _read_rollout_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _write_rollout_jsonl_gz(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def _weighted_mean(base: dict[str, Any], extra: dict[str, Any], key: str, *, base_n: int, extra_n: int) -> float:
    total = base_n + extra_n
    if total <= 0:
        return 0.0
    return (
        (float(base.get(key) or 0.0) * float(base_n))
        + (float(extra.get(key) or 0.0) * float(extra_n))
    ) / float(total)


def _merge_instance_rows(base_row: dict[str, Any], extra_row: dict[str, Any]) -> dict[str, Any]:
    base_n = int(base_row.get("rollout_count") or 0)
    extra_n = int(extra_row.get("rollout_count") or 0)
    total = base_n + extra_n
    merged = dict(base_row)

    positive = int(base_row.get("positive_rollout_count") or 0) + int(extra_row.get("positive_rollout_count") or 0)
    perfect = int(base_row.get("perfect_rollout_count") or 0) + int(extra_row.get("perfect_rollout_count") or 0)
    max_token = int(base_row.get("max_token_rollout_count") or 0) + int(extra_row.get("max_token_rollout_count") or 0)
    extraction_none = int(base_row.get("extraction_none_count") or 0) + int(extra_row.get("extraction_none_count") or 0)
    crop_or_no_extract = int(base_row.get("crop_or_no_extract_rollout_count") or 0) + int(
        extra_row.get("crop_or_no_extract_rollout_count") or 0
    )

    merged.update(
        {
            "rollout_count": total,
            "positive_rollout_count": positive,
            "perfect_rollout_count": perfect,
            "max_token_rollout_count": max_token,
            "extraction_none_count": extraction_none,
            "crop_or_no_extract_rollout_count": crop_or_no_extract,
            "solve_rate": float(positive / total) if total else 0.0,
            "perfect_rate": float(perfect / total) if total else 0.0,
            "max_token_rollout_rate": float(max_token / total) if total else 0.0,
            "extraction_none_rate": float(extraction_none / total) if total else 0.0,
            "crop_or_no_extract_rate": float(crop_or_no_extract / total) if total else 0.0,
            "zero_solve": positive == 0,
            "perfect_solve": positive == total if total else False,
            "max_generated_tokens": max(int(base_row.get("max_generated_tokens") or 0), int(extra_row.get("max_generated_tokens") or 0)),
        }
    )
    if extra_row.get("max_generation_tokens_setting") is not None:
        merged["max_generation_tokens_setting"] = extra_row.get("max_generation_tokens_setting")

    for key in (
        "mean_task_reward",
        "mean_answer_reward",
        "mean_overall_reward",
        "mean_format_reward",
        "mean_generated_tokens",
        "json_found_rate",
        "format_json_ok_rate",
        "format_schema_ok_rate",
        "probe_extraction_fallback_rate",
    ):
        if key in base_row or key in extra_row:
            merged[key] = _weighted_mean(base_row, extra_row, key, base_n=base_n, extra_n=extra_n)
    return merged


def _combine_per_instance(base_path: Path, extra_path: Path, combined_path: Path) -> list[dict[str, Any]]:
    base_rows = _read_jsonl(base_path)
    extra_rows = _read_jsonl(extra_path)
    if len(base_rows) != len(extra_rows):
        raise ValueError(f"base/extra row count mismatch: {base_path} has {len(base_rows)}, {extra_path} has {len(extra_rows)}")
    extra_by_uid = {str(row.get("uid")): row for row in extra_rows}
    merged_rows: list[dict[str, Any]] = []
    for base_row in base_rows:
        uid = str(base_row.get("uid"))
        extra_row = extra_by_uid.get(uid)
        if extra_row is None:
            raise ValueError(f"missing extra row for uid={uid}")
        if int(base_row.get("dataset_index") or 0) != int(extra_row.get("dataset_index") or 0):
            raise ValueError(f"dataset_index mismatch for uid={uid}")
        merged_rows.append(_merge_instance_rows(base_row, extra_row))
    _write_jsonl(combined_path, merged_rows)
    return merged_rows


def _combine_per_rollout(base_path: Path, extra_path: Path, combined_path: Path, *, base_counts: dict[int, int]) -> None:
    def rows() -> Iterable[dict[str, Any]]:
        yield from _read_rollout_jsonl(base_path)
        for row in _read_rollout_jsonl(extra_path):
            dataset_index = int(row.get("dataset_index") or 0)
            row = dict(row)
            row["rollout_index"] = int(row.get("rollout_index") or 0) + int(base_counts.get(dataset_index, 0))
            yield row

    _write_rollout_jsonl_gz(combined_path, rows())


def _write_summary_files(output_dir: Path, rows: list[dict[str, Any]], *, args: argparse.Namespace, task_id: str, model: Any) -> None:
    rollout_count = sum(int(row.get("rollout_count") or 0) for row in rows)
    positive_count = sum(int(row.get("positive_rollout_count") or 0) for row in rows)
    prompt_count = len(rows)
    max_token_count = sum(int(row.get("max_token_rollout_count") or 0) for row in rows)
    payload = {
        "task_id": task_id,
        "model": model.model_id,
        "prompt_count": prompt_count,
        "rollout_count": rollout_count,
        "positive_rollout_count": positive_count,
        "positive_rollout_rate": float(positive_count / rollout_count) if rollout_count else 0.0,
        "zero_solve_count": sum(1 for row in rows if int(row.get("positive_rollout_count") or 0) == 0),
        "perfect_solve_count": sum(
            1
            for row in rows
            if int(row.get("positive_rollout_count") or 0) == int(row.get("rollout_count") or 0)
            and int(row.get("rollout_count") or 0) > 0
        ),
        "max_token_rollout_count": max_token_count,
        "max_token_rollout_rate": float(max_token_count / rollout_count) if rollout_count else 0.0,
        "extension": {
            "base_rollouts": int(args.base_rollouts),
            "extra_rollouts": int(args.extra_rollouts),
            "combined_rollouts": int(args.combined_rollouts),
            "base_seed": int(args.seed),
            "extra_seed": int(args.extra_seed),
        },
    }
    for filename in ("summary.json", "per_task_summary.json", "per_task_bucket_summary.json"):
        (output_dir / filename).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _combine_outputs(args: argparse.Namespace, task_id: str, model: Any, base_dir: Path, extra_dir: Path, combined_dir: Path) -> list[dict[str, Any]]:
    base_instance = base_dir / "per_instance.jsonl"
    extra_instance = extra_dir / "per_instance.jsonl"
    base_rollout = base_dir / "per_rollout.jsonl.gz"
    extra_rollout = extra_dir / "per_rollout.jsonl.gz"
    if not base_instance.exists():
        raise FileNotFoundError(f"missing base per_instance file: {base_instance}")
    if not extra_instance.exists():
        raise FileNotFoundError(f"missing extra per_instance file: {extra_instance}")
    if not base_rollout.exists():
        raise FileNotFoundError(f"missing base per_rollout file: {base_rollout}")
    if not extra_rollout.exists():
        raise FileNotFoundError(f"missing extra per_rollout file: {extra_rollout}")
    if combined_dir.exists() and bool(args.force_combine):
        shutil.rmtree(combined_dir)
    combined_dir.mkdir(parents=True, exist_ok=True)
    rows = _combine_per_instance(base_instance, extra_instance, combined_dir / "per_instance.jsonl")
    base_counts = {int(row.get("dataset_index") or 0): int(row.get("rollout_count") or 0) for row in _read_jsonl(base_instance)}
    _combine_per_rollout(base_rollout, extra_rollout, combined_dir / "per_rollout.jsonl.gz", base_counts=base_counts)
    _write_summary_files(combined_dir, rows, args=args, task_id=task_id, model=model)
    return rows


def _run_extra_probe(args: argparse.Namespace, task_id: str, model: Any, parquet: Path, extra_dir: Path) -> int:
    per_instance = extra_dir / "per_instance.jsonl"
    if (
        per_instance.exists()
        and sweep._line_count(per_instance) == int(args.sample_count)
        and not bool(args.force_extra)
    ):
        return int(args.batch_size)
    if args.skip_extra:
        raise FileNotFoundError(f"missing complete extra probe output: {per_instance}")
    if extra_dir.exists() and bool(args.force_extra):
        shutil.rmtree(extra_dir)

    extra_args = copy.copy(args)
    extra_args.rollouts_per_prompt = int(args.extra_rollouts)
    extra_args.seed = int(args.extra_seed)

    batch_sizes = [int(args.batch_size)]
    if int(args.retry_batch_size) > 0 and int(args.retry_batch_size) != int(args.batch_size):
        batch_sizes.append(int(args.retry_batch_size))

    last_error: subprocess.CalledProcessError | None = None
    for batch_size in batch_sizes:
        if str(args.probe_backend) == "local_vllm":
            sweep._wait_for_gpu(args)
        extra_dir.mkdir(parents=True, exist_ok=True)
        log_path = extra_dir / f"run_batch{batch_size}.log"
        cmd = sweep._probe_command(extra_args, model, parquet, extra_dir, batch_size=batch_size)
        try:
            sweep._run_command(cmd, env=sweep._probe_env(extra_args), log_path=log_path, dry_run=bool(args.dry_run))
            return batch_size
        except subprocess.CalledProcessError as exc:
            last_error = exc
            if batch_size == batch_sizes[-1] or not sweep._looks_like_oom(log_path):
                raise
            print(f"[retry] {task_id}/{model.slug} failed with likely OOM at batch={batch_size}; retrying smaller batch")
            sweep._discard_failed_output(extra_dir, batch_size=batch_size)
    assert last_error is not None
    raise last_error


def _export_combined_stats(args: argparse.Namespace, task_id: str, model: Any, parquet: Path, combined_dir: Path) -> dict[str, Any]:
    stats_path = combined_dir / "calibration_stats.json"
    if stats_path.exists() and sweep._json_file_matches_baseline(stats_path, str(args.calibration_baseline)) and not bool(args.force_stats):
        return sweep._load_json(stats_path)

    label = (
        f"{model.slug}_{str(args.calibration_baseline)}_"
        f"{int(args.sample_count)}x{int(args.combined_rollouts)}_seed{int(args.seed)}"
    )
    cmd = [
        sys.executable,
        "scripts/export_curriculum_probe_calibration_stats.py",
        "--task-id",
        task_id,
        "--parquet",
        str(parquet),
        "--probe-output-dir",
        str(combined_dir),
        "--out-root",
        str(args.review_root),
        "--review-label",
        label,
        "--calibration-baseline",
        str(args.calibration_baseline),
        "--hard-threshold",
        "0",
        "--easy-threshold",
        str(sweep._easy_threshold_for_rollouts(int(args.combined_rollouts))),
        "--max-prompt-length",
        str(args.max_prompt_length),
        "--max-response-length",
        str(sweep._max_tokens_for_model(args, model)),
        "--group-key",
        "query_id",
    ]
    sweep._run_command(cmd, dry_run=bool(args.dry_run))
    return sweep._load_json(stats_path) if stats_path.exists() else {}


def _update_status_record(
    args: argparse.Namespace,
    status: dict[str, Any],
    task_id: str,
    model: Any,
    *,
    parquet: Path,
    dataset_root: Path,
    combined_dir: Path,
    stats: dict[str, Any],
    batch_size: int,
    active_model_slugs: list[str],
) -> None:
    taxonomy = sweep.resolve_task_taxonomy(task_id)
    record = status.setdefault("tasks", {}).setdefault(
        task_id,
        {
            "task_id": task_id,
            "domain": str(taxonomy.domain),
            "scene_id": str(taxonomy.scene_id),
            "models": {},
        },
    )
    record.update(
        {
            "task_id": task_id,
            "domain": str(taxonomy.domain),
            "scene_id": str(taxonomy.scene_id),
            "calibration_baseline": str(args.calibration_baseline),
            "updated_at": sweep._now(),
            "parquet": sweep._rel(parquet),
            "dataset_root": sweep._rel(dataset_root),
        }
    )
    workbook = sweep._review_workbook_path(args, task_id)
    if workbook.exists():
        record["review_workbook"] = sweep._rel(workbook)

    model_status, reasons = sweep._model_status(stats, cap_threshold=model.response_cap_threshold)
    stats_artifacts = stats.get("artifacts") if isinstance(stats.get("artifacts"), dict) else {}
    model_record: dict[str, Any] = {
        "model_id": model.model_id,
        "response_cap_threshold": model.response_cap_threshold,
        "max_response_length": sweep._max_tokens_for_model(args, model),
        "max_model_len": sweep._max_model_len_for_model(args, model),
        "output_dir": sweep._rel(combined_dir),
        "calibration_stats": sweep._rel(combined_dir / "calibration_stats.json"),
        "solve_workbook": stats_artifacts.get("solve_workbook"),
        "batch_size": int(batch_size),
        "status": model_status,
        "reasons": reasons,
        "stats": stats,
    }
    if str(args.probe_backend) == "openai_server":
        model_record["server_base_url"] = sweep._server_base_url_for_model(args, model)
        model_record["server_model"] = sweep._server_model_for_model(args, model)
    record.setdefault("models", {})[model.slug] = model_record
    active_records = {
        slug: record["models"][slug]
        for slug in active_model_slugs
        if isinstance(record.get("models"), dict) and slug in record["models"]
    }
    record["status"] = sweep._combined_status(active_records)


def _selected_task_paths(args: argparse.Namespace, task_id: str) -> tuple[Path, Path]:
    sample_args = copy.copy(args)
    sample_args.seed = int(args.seed)
    return sweep._dataset_paths(sample_args, task_id)[2:4]


def _rebuild_status_config(args: argparse.Namespace, models: list[Any], code_revision: str) -> dict[str, Any]:
    return {
        "sample_count": int(args.sample_count),
        "calibration_baseline": str(args.calibration_baseline),
        "rollouts_per_prompt": int(args.combined_rollouts),
        "base_rollouts": int(args.base_rollouts),
        "extra_rollouts": int(args.extra_rollouts),
        "seed": int(args.seed),
        "extra_seed": int(args.extra_seed),
        "hard_threshold_solved_rollouts": 0,
        "hard_fraction_threshold": sweep.HARD_FRACTION_THRESHOLD,
        "easy_threshold_solved_rollouts": sweep._easy_threshold_for_rollouts(int(args.combined_rollouts)),
        "easy_fraction_threshold": sweep.EASY_FRACTION_THRESHOLD,
        "easy_definition": f"solved_rollouts >= {sweep._easy_threshold_for_rollouts(int(args.combined_rollouts))}",
        "mean_solve_rate_min": sweep.MEAN_SOLVE_RATE_MIN,
        "mean_solve_rate_max": sweep.MEAN_SOLVE_RATE_MAX,
        "max_prompt_length": int(args.max_prompt_length),
        "max_response_length": int(args.max_tokens) if int(args.max_tokens) > 0 else None,
        "max_response_length_defaults": dict(sweep.MAX_TOKENS_DEFAULTS) if int(args.max_tokens) <= 0 else None,
        "max_model_len": int(args.max_model_len) if int(args.max_model_len) > 0 else None,
        "max_model_len_defaults": dict(sweep.MAX_MODEL_LEN_DEFAULTS) if int(args.max_model_len) <= 0 else None,
        "models": {model.slug: {"model_id": model.model_id, "response_cap_threshold": model.response_cap_threshold} for model in models},
        "probe_backend": str(args.probe_backend),
        "server_base_url": str(args.server_base_url).strip() if str(args.probe_backend) == "openai_server" and str(args.server_base_url).strip() else None,
        "server_base_url_defaults": dict(sweep.SERVER_BASE_URL_DEFAULTS) if str(args.probe_backend) == "openai_server" and not str(args.server_base_url).strip() else None,
        "server_model": str(args.server_model) if str(args.probe_backend) == "openai_server" and str(args.server_model).strip() else None,
        "server_concurrency": int(args.server_concurrency) if str(args.probe_backend) == "openai_server" else None,
        "code_revision": code_revision,
        "per_rollout_response_mode": str(args.per_rollout_response_mode),
        "per_rollout_response_max_chars": int(args.per_rollout_response_max_chars),
    }


def main() -> int:
    args = _parse_args()
    if int(args.base_rollouts) + int(args.extra_rollouts) != int(args.combined_rollouts):
        raise SystemExit("--base-rollouts + --extra-rollouts must equal --combined-rollouts")
    task_ids = sweep._select_tasks(args)
    models = sweep._parse_models(args.models)
    code_revision = sweep._git_revision()
    status_path = Path(args.status_json)
    status = sweep._load_json(status_path) or {"tasks": {}}
    status["config"] = _rebuild_status_config(args, models, code_revision)
    active_model_slugs = [model.slug for model in models]

    print(
        "[extend] "
        f"selected_tasks={len(task_ids)} models={[model.slug for model in models]} "
        f"base={args.base_rollouts} extra={args.extra_rollouts} combined={args.combined_rollouts}"
    )
    touched_scenes: set[tuple[str, str]] = set()
    for task_index, task_id in enumerate(task_ids, 1):
        taxonomy = sweep.resolve_task_taxonomy(task_id)
        touched_scenes.add((str(taxonomy.domain), str(taxonomy.scene_id)))
        parquet, dataset_root = _selected_task_paths(args, task_id)
        if not parquet.exists():
            raise FileNotFoundError(f"missing calibration sample parquet for {task_id}: {parquet}")
        print(f"[task {task_index}/{len(task_ids)}] {taxonomy.domain}/{taxonomy.scene_id}/{task_id}")
        for model in models:
            base_dir = _probe_output_dir(args, task_id, model, rollouts=int(args.base_rollouts), seed=int(args.seed))
            extra_dir = _extra_output_dir(args, task_id, model)
            combined_dir = _combined_output_dir(args, task_id, model)
            print(f"[model] {model.slug} base={base_dir.name} extra={extra_dir.name} combined={combined_dir.name}")
            if args.dry_run:
                continue
            if not base_dir.exists():
                raise FileNotFoundError(f"missing base probe output for {task_id}/{model.slug}: {base_dir}")
            batch_size = _run_extra_probe(args, task_id, model, parquet, extra_dir)
            combined_complete = (combined_dir / "per_instance.jsonl").exists() and sweep._line_count(
                combined_dir / "per_instance.jsonl"
            ) == int(args.sample_count)
            if bool(args.force_combine) or not combined_complete:
                rows = _combine_outputs(args, task_id, model, base_dir, extra_dir, combined_dir)
                print(f"[combine] {task_id}/{model.slug} rows={len(rows)}")
            stats = _export_combined_stats(args, task_id, model, parquet, combined_dir)
            _update_status_record(
                args,
                status,
                task_id,
                model,
                parquet=parquet,
                dataset_root=dataset_root,
                combined_dir=combined_dir,
                stats=stats,
                batch_size=batch_size,
                active_model_slugs=active_model_slugs,
            )
            sweep._write_status_files(args, status)
        print(f"[task {task_index}/{len(task_ids)}] status={status['tasks'][task_id].get('status')}")

    sweep._rebuild_scene_workbooks(args, touched_scenes)
    if not args.dry_run:
        sweep._write_status_files(args, status)
    print(f"[done] status_json={args.status_json} status_md={args.status_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
