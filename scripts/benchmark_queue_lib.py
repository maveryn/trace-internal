#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
VLMEVAL_ROOT = Path(os.environ.get("VLMEVAL_ROOT", "/home/jovyan/work/VLMEvalKit"))
BASE_MODEL = "Qwen/Qwen3-VL-4B-Instruct"
BASE_MODEL_SLUG = "qwen3-vl-4b-instruct"
DEFAULT_RUN_ROOT = REPO_ROOT / "runs"
DEFAULT_BENCHMARK_ROOT = REPO_ROOT / "benchmark"
DEFAULT_QUEUE_ROOT = DEFAULT_BENCHMARK_ROOT / "queues"


@dataclass(frozen=True)
class BenchmarkSpec:
    key: str
    display: str
    alias: str
    run_name: str
    eval_mode: str = "auto"
    kind: str = "vlmeval"
    split: str | None = None
    max_tokens: int = 16384
    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 20
    presence_penalty: float = 1.5
    repetition_penalty: float = 1.0
    max_model_len: int | None = 32768
    max_pixels: int | None = None
    total_pixels: int | None = None
    max_images: int = 24
    max_videos: int = 3
    generation_batch_size: int | None = None
    video_llm: bool = False
    aggregate_group: str | None = None
    aggregate_run_name: str | None = None
    note: str = ""


@dataclass(frozen=True)
class ModelSpec:
    name: str
    slug: str
    path: str
    default_gpus: tuple[str, ...]
    run_set: str


BENCHMARKS: tuple[BenchmarkSpec, ...] = (
    BenchmarkSpec("chartqapro", "ChartQAPro", "ChartQAPro_CoT", "vlmevalkit_faithful_cot"),
    BenchmarkSpec("chartmuseum", "ChartMuseum", "ChartMuseum", "vlmevalkit_defaults_qwen32b_judge_test", kind="chartmuseum", split="test", eval_mode="chartmuseum_local_judge", max_model_len=32768),
    BenchmarkSpec("charxivdesc", "CharXivDesc", "CharXiv_descriptive_val", "vlmevalkit_defaults_qwen32b_judge"),
    BenchmarkSpec("charxivreason", "CharXivReason", "CharXiv_reasoning_val", "vlmevalkit_defaults_qwen32b_judge"),
    BenchmarkSpec("evochart", "EvoChart", "EvoChart_Qwen3_ZS", "vlmevalkit_vero_qwen3_zs", max_tokens=1024, temperature=1.0, top_p=1.0, top_k=40, presence_penalty=2.0),
    BenchmarkSpec("infovqa", "InfoVQA", "InfoVQA_VAL", "vlmevalkit_defaults_val"),
    BenchmarkSpec("mmmu_pro_vision", "MMMU-ProVis", "MMMU_Pro_V_COT", "vlmevalkit_cot_max2048", max_tokens=2048),
    BenchmarkSpec("mathvision", "MathVision", "MathVision", "vlmevalkit_defaults_qwen32b_judge"),
    BenchmarkSpec("mathvista", "MathVista", "MathVista_MINI", "vlmevalkit_defaults_qwen32b_judge"),
    BenchmarkSpec("mathverse", "MathVerse", "MathVerse_MINI_Vision_Only_cot", "vlmevalkit_defaults_qwen32b_judge"),
    BenchmarkSpec("logicvista", "LogicVista", "LogicVista", "vlmevalkit_defaults_qwen32b_judge"),
    BenchmarkSpec("blink", "Blink", "BLINK", "vlmevalkit_defaults"),
    BenchmarkSpec("erqa", "ERQA", "ERQA", "vlmevalkit_defaults"),
    BenchmarkSpec("embspatial", "EmbSpatial", "EmbSpatialBench", "vlmevalkit_defaults"),
    BenchmarkSpec("robospatialhome", "RoboSpatialHome", "RoboSpatialHome", "vlmevalkit_defaults"),
    BenchmarkSpec("game_qa_lite", "Game-QA-Lite", "Game-QA-Lite", "vlmevalkit_defaults"),
    BenchmarkSpec("countqa", "CountQA", "CountQA", "vlmevalkit_defaults"),
    BenchmarkSpec("vstarbench", "VStarBench", "VStarBench", "vlmevalkit_defaults"),
    BenchmarkSpec("screenspotpro_development", "ScreenSpotPro/Development", "ScreenSpot_Pro_Development", "vlmevalkit_defaults_pooled/development", aggregate_group="screenspotpro", aggregate_run_name="vlmevalkit_defaults_pooled"),
    BenchmarkSpec("screenspotpro_creative", "ScreenSpotPro/Creative", "ScreenSpot_Pro_Creative", "vlmevalkit_defaults_pooled/creative", aggregate_group="screenspotpro", aggregate_run_name="vlmevalkit_defaults_pooled"),
    BenchmarkSpec("screenspotpro_cad", "ScreenSpotPro/CAD", "ScreenSpot_Pro_CAD", "vlmevalkit_defaults_pooled/cad", aggregate_group="screenspotpro", aggregate_run_name="vlmevalkit_defaults_pooled"),
    BenchmarkSpec("screenspotpro_scientific", "ScreenSpotPro/Scientific", "ScreenSpot_Pro_Scientific", "vlmevalkit_defaults_pooled/scientific", aggregate_group="screenspotpro", aggregate_run_name="vlmevalkit_defaults_pooled"),
    BenchmarkSpec("screenspotpro_office", "ScreenSpotPro/Office", "ScreenSpot_Pro_Office", "vlmevalkit_defaults_pooled/office", aggregate_group="screenspotpro", aggregate_run_name="vlmevalkit_defaults_pooled"),
    BenchmarkSpec("screenspotpro_os", "ScreenSpotPro/OS", "ScreenSpot_Pro_OS", "vlmevalkit_defaults_pooled/os", aggregate_group="screenspotpro", aggregate_run_name="vlmevalkit_defaults_pooled"),
    BenchmarkSpec("mmstar", "MMStar", "MMStar", "vlmevalkit_defaults"),
    BenchmarkSpec("mme_realworld_lite", "MME-RealWorld-Lite", "MME-RealWorld-Lite", "vlmevalkit_defaults"),
    BenchmarkSpec("treebench", "TreeBench", "TreeBench", "vlmevalkit_defaults"),
    BenchmarkSpec("vlmblind", "VLMBlind", "VLMBlind", "vlmevalkit_defaults"),
)


ABLATION_MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        "TRACE alpha0 answer step250",
        "trace-qwen3vl4b-alpha0-answer-step250",
        str(REPO_ROOT / "checkpoints/trace_rlvr_merged_hf/trace_qwen3vl4b_alpha0_answer_step250"),
        ("0", "1"),
        "full",
    ),
    ModelSpec(
        "TRACE alpha0.5 answer step250",
        "trace-qwen3vl4b-alpha0-5-answer-step250",
        str(REPO_ROOT / "checkpoints/trace_rlvr_merged_hf/trace_qwen3vl4b_alpha0_5_answer_step250"),
        ("2", "3"),
        "full",
    ),
    ModelSpec(
        "TRACE alpha1 answer step250",
        "trace-qwen3vl4b-alpha1-answer-step250",
        str(REPO_ROOT / "checkpoints/trace_rlvr_merged_hf/trace_qwen3vl4b_alpha1_answer_step250"),
        ("4", "5"),
        "full",
    ),
)

BASE_MODEL_SPEC = ModelSpec("Qwen3-VL-4B-Instruct base", BASE_MODEL_SLUG, BASE_MODEL, ("6", "7"), "remaining_base")


def all_model_specs(include_base: bool = True, include_ablations: bool = True) -> list[ModelSpec]:
    out: list[ModelSpec] = []
    if include_base:
        out.append(BASE_MODEL_SPEC)
    if include_ablations:
        out.extend(ABLATION_MODELS)
    return out


def spec_by_key(key: str) -> BenchmarkSpec:
    for spec in BENCHMARKS:
        if spec.key == key:
            return spec
    raise KeyError(key)


def benchmark_dir(spec: BenchmarkSpec, model_slug: str, benchmark_root: Path = DEFAULT_BENCHMARK_ROOT) -> Path:
    key = spec.aggregate_group or spec.key
    run_name = spec.aggregate_run_name if spec.aggregate_group else spec.run_name
    return benchmark_root / key / model_slug / str(run_name)


def run_dir(spec: BenchmarkSpec, model_slug: str, run_root: Path = DEFAULT_RUN_ROOT) -> Path:
    key = spec.aggregate_group or spec.key
    return run_root / key / model_slug / spec.run_name


def score_path(spec: BenchmarkSpec, model_slug: str, benchmark_root: Path = DEFAULT_BENCHMARK_ROOT) -> Path:
    if spec.aggregate_group:
        return benchmark_dir(spec, model_slug, benchmark_root) / f"{spec.key}_scores.json"
    return benchmark_dir(spec, model_slug, benchmark_root) / "scores.json"


def aggregate_score_path(group: str, run_name: str, model_slug: str, benchmark_root: Path = DEFAULT_BENCHMARK_ROOT) -> Path:
    return benchmark_root / group / model_slug / run_name / "scores.json"


def benchmark_specs_for_run_set(run_set: str, model_slug: str = BASE_MODEL_SLUG) -> list[BenchmarkSpec]:
    specs = list(BENCHMARKS)
    if run_set == "full":
        return specs
    if run_set == "remaining_base":
        return [spec for spec in specs if not score_path(spec, model_slug).exists()]
    if run_set == "base_all":
        return specs
    raise ValueError(f"Unknown run_set {run_set!r}")


def effective_generation_batch_size(
    spec: BenchmarkSpec,
    requested_batch_size: int,
    max_tokens_override: int | None = None,
) -> int:
    max_tokens = spec.max_tokens
    if max_tokens_override is not None and max_tokens_override > 0:
        max_tokens = min(max_tokens, max_tokens_override)
    if spec.generation_batch_size is not None:
        return max(1, min(requested_batch_size, spec.generation_batch_size))
    if spec.video_llm:
        return max(1, min(requested_batch_size, 32))
    if max_tokens_override is not None and max_tokens_override > 0 and max_tokens <= 4096:
        return max(1, requested_batch_size)
    if max_tokens >= 8192:
        return max(1, min(requested_batch_size, 128))
    if max_tokens >= 2048:
        return max(1, min(requested_batch_size, 256))
    return max(1, requested_batch_size)


def local_judge_eval_mode(spec: BenchmarkSpec) -> str | None:
    if spec.kind == "chartmuseum":
        return "chartmuseum_local_judge"
    if spec.alias.startswith("CharXiv_"):
        return "charxiv_local_judge"
    if spec.alias == "MathVision":
        return "mathv_local_judge"
    if spec.alias.startswith("MathVista"):
        return "mathvista_local_judge"
    if spec.alias.startswith("MathVerse"):
        return "mathverse_local_judge"
    if spec.alias == "LogicVista":
        return "logicvista_local_judge"
    return None


def json_default(value: Any) -> Any:
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


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8")
    tmp.replace(path)


@contextmanager
def file_lock(lock_path: Path):
    import fcntl

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _job_done(job_id: str, done_path: Path | None) -> bool:
    return bool(done_path and done_path.exists())


def _pid_alive(pid: Any) -> bool:
    try:
        pid_int = int(pid)
    except Exception:
        return False
    if pid_int <= 0:
        return False
    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def claim_next_job(
    *,
    queue_path: Path,
    jobs: Iterable[tuple[str, Path | None]],
    worker_id: str,
    stale_after_sec: float = 12 * 3600,
    max_attempts: int = 2,
) -> str | None:
    lock_path = queue_path.with_suffix(queue_path.suffix + ".lock")
    now = time.time()
    with file_lock(lock_path):
        state = load_json(queue_path, {"jobs": {}})
        state_jobs = state.setdefault("jobs", {})
        for job_id, done_path in jobs:
            info = state_jobs.get(job_id, {})
            if _job_done(job_id, done_path):
                state_jobs[job_id] = {**info, "status": "done", "done_path": str(done_path), "updated_at": now}
                continue
            attempts = int(info.get("attempts") or 0)
            if info.get("status") == "failed" and attempts >= max_attempts:
                continue
            if info.get("status") == "running":
                if _pid_alive(info.get("pid")):
                    continue
                if now - float(info.get("updated_at", 0)) < stale_after_sec:
                    continue
            if info.get("status") == "done":
                continue
            state_jobs[job_id] = {
                "status": "running",
                "worker": worker_id,
                "pid": os.getpid(),
                "updated_at": now,
                "attempts": attempts + 1,
            }
            write_json(queue_path, state)
            return job_id
        write_json(queue_path, state)
    return None


def mark_job(queue_path: Path, job_id: str, status: str, **extra: Any) -> None:
    now = time.time()
    lock_path = queue_path.with_suffix(queue_path.suffix + ".lock")
    with file_lock(lock_path):
        state = load_json(queue_path, {"jobs": {}})
        state_jobs = state.setdefault("jobs", {})
        previous = state_jobs.get(job_id, {})
        entry = {
            "status": status,
            "worker": extra.pop("worker", None),
            "pid": os.getpid(),
            "updated_at": now,
            **extra,
        }
        if "attempts" not in entry and "attempts" in previous:
            entry["attempts"] = previous["attempts"]
        state_jobs[job_id] = entry
        write_json(queue_path, state)


def score_to_percent(value: Any) -> float | None:
    try:
        score = float(value)
    except Exception:
        return None
    if math.isnan(score):
        return None
    if abs(score) <= 1.0:
        score *= 100.0
    return score


def extract_score_and_rows(scores_obj: dict[str, Any]) -> tuple[float | None, int | None]:
    rows = scores_obj.get("rows")
    rows_int = int(rows) if rows is not None else None
    if "Overall_Accuracy" in scores_obj:
        return float(scores_obj["Overall_Accuracy"]), rows_int
    for key in ("accuracy", "acc", "score", "Overall", "overall"):
        if key in scores_obj:
            return score_to_percent(scores_obj[key]), rows_int
    scores = scores_obj.get("scores", {})
    if isinstance(scores, dict):
        if "Overall_Accuracy" in scores:
            return float(scores["Overall_Accuracy"]), rows_int
        for key in ("Overall", "overall", "accuracy", "acc", "val"):
            if key in scores:
                return score_to_percent(scores[key]), rows_int
        table = scores.get("table")
        if isinstance(table, list):
            for row in table:
                if not isinstance(row, dict):
                    continue
                if any(str(v).lower() == "overall" for v in row.values()):
                    for key in ("acc", "accuracy", "Accuracy (%)", "score", "Score", "Overall", "overall", "1"):
                        if key in row:
                            return score_to_percent(row[key]), int(row.get("tot", row.get("Samples", rows or 0)) or 0)
                    for key, value in row.items():
                        if str(value).lower() == "overall":
                            continue
                        parsed = score_to_percent(value)
                        if parsed is not None:
                            return parsed, int(row.get("tot", row.get("Samples", rows or 0)) or 0)

        numeric_scores: list[float] = []
        skip_keys = {
            "rows",
            "samples",
            "num_correct",
            "num_total",
            "illformed_responses",
            "category_stats",
            "table",
            "tabulated_keys",
            "tabulated_results",
        }
        for key, value in scores.items():
            if str(key).lower() in skip_keys:
                continue
            parsed = score_to_percent(value)
            if parsed is not None:
                numeric_scores.append(parsed)
        if numeric_scores:
            return sum(numeric_scores) / len(numeric_scores), rows_int
    return None, rows_int
