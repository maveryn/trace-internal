"""Index old external benchmark run artifacts for browser review."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .models import BenchmarkIndex, BenchmarkRecord, SampleRecord


PRIMARY_NUMERIC_METRICS = (
    "individual_score",
    "accuracy",
    "exact_match",
    "relaxed_overall",
    "anls",
)


def build_benchmark_index(run_root: Path | str, *, repo_root: Path | str | None = None) -> BenchmarkIndex:
    """Build an in-memory index from a benchmark run directory."""

    resolved_run_root = Path(run_root).resolve()
    resolved_repo_root = Path(repo_root).resolve() if repo_root is not None else _infer_repo_root(resolved_run_root)
    index = BenchmarkIndex(
        run_root=resolved_run_root,
        repo_root=resolved_repo_root,
        built_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )

    manifest = _load_json(resolved_run_root / "RUN_MANIFEST.json")
    if isinstance(manifest, dict):
        index.model_id = str(manifest.get("model_id") or "")
        index.run_id = str(manifest.get("run_id") or resolved_run_root.name)
    else:
        index.run_id = resolved_run_root.name

    if not resolved_run_root.exists():
        index.errors.append(f"run root does not exist: {resolved_run_root}")
        return index

    for bench_dir in sorted(path for path in resolved_run_root.iterdir() if path.is_dir()):
        if bench_dir.name in {"local_datasets", "response_cache"}:
            continue
        try:
            _index_benchmark(index, bench_dir)
        except Exception as exc:  # pragma: no cover - defensive indexing
            index.errors.append(f"{bench_dir.name}: {type(exc).__name__}: {exc}")

    return index


def load_sample_payload(index: BenchmarkIndex, sample: SampleRecord) -> dict[str, Any]:
    path = index.run_root / sample.benchmark / sample.source_file
    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f):
            if line_number == sample.source_line:
                return json.loads(line)
    raise FileNotFoundError(f"sample line not found: {path}:{sample.source_line}")


def _index_benchmark(index: BenchmarkIndex, bench_dir: Path) -> None:
    sample_files = _primary_sample_files(bench_dir)
    if not sample_files:
        return

    run_summary = _load_json(bench_dir / "run_summary.json")
    display = str((run_summary or {}).get("display") or bench_dir.name)
    record = BenchmarkRecord(
        benchmark=bench_dir.name,
        display=display,
        run_summary_path=_rel_to_run_root(index, bench_dir / "run_summary.json") if (bench_dir / "run_summary.json").exists() else "",
        model_id=str((run_summary or {}).get("model_id") or index.model_id),
        datetime=str((run_summary or {}).get("datetime") or ""),
        source_files=[_rel_to_bench(bench_dir, path) for path in sample_files],
        result_files=[_rel_to_bench(bench_dir, path) for path in sorted(bench_dir.glob("*results.json"))],
    )

    sample_uids: list[str] = []
    for sample_path in sample_files:
        task_name = _infer_task_name(sample_path)
        with sample_path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f):
                if not line.strip():
                    continue
                row = json.loads(line)
                sample = _record_from_row(
                    index=index,
                    bench_dir=bench_dir,
                    display=display,
                    source_file=_rel_to_bench(bench_dir, sample_path),
                    source_line=line_number,
                    task_name=task_name,
                    row=row,
                )
                index.samples[sample.uid] = sample
                sample_uids.append(sample.uid)
                if sample.image_exists:
                    index.media[sample.media_id] = Path(sample.image_path)
                    record.image_count += 1
                if sample.is_correct is True:
                    record.correct_count += 1
                elif sample.is_correct is False:
                    record.incorrect_count += 1
                else:
                    record.unknown_count += 1
                if sample.category:
                    record.category_counts[sample.category] = record.category_counts.get(sample.category, 0) + 1
                if not record.preview_uid and sample.image_exists:
                    record.preview_uid = sample.uid

    record.sample_count = len(sample_uids)
    if record.sample_count <= 0:
        return
    index.benchmarks[record.benchmark] = record
    index.samples_by_benchmark[record.benchmark] = sample_uids


def _record_from_row(
    *,
    index: BenchmarkIndex,
    bench_dir: Path,
    display: str,
    source_file: str,
    source_line: int,
    task_name: str,
    row: dict[str, Any],
) -> SampleRecord:
    metric_name, metric_payload, score, correct = _extract_metric(row)
    model_response = _first_text(row.get("filtered_resps"))
    if not model_response:
        model_response = str(row.get("prediction") or row.get("response") or "")
    extracted = _extract_answer(row, metric_payload)
    image_path = _resolve_image_path(row.get("image"), bench_dir=bench_dir)
    image_exists = bool(image_path and image_path.exists())
    image_mtime_ns = image_path.stat().st_mtime_ns if image_exists and image_path is not None else 0
    media_id = _stable_hash(str(image_path))[:24] if image_path is not None else ""
    category = _extract_category(row, metric_payload)
    doc_id = str(row.get("doc_id") if row.get("doc_id") is not None else row.get("id") or row.get("index") or source_line)
    uid = _stable_hash(
        "|".join(
            [
                bench_dir.name,
                source_file,
                str(source_line),
                doc_id,
                str(row.get("doc_hash") or ""),
                str(row.get("target") or ""),
            ]
        )
    )[:24]
    return SampleRecord(
        uid=uid,
        benchmark=bench_dir.name,
        display=display,
        source_file=source_file,
        source_line=source_line,
        doc_id=doc_id,
        task_name=str(row.get("image_recovery", {}).get("task_name") or task_name),
        prompt=str(row.get("input") or row.get("question") or row.get("prompt") or ""),
        model_response=model_response,
        target=row.get("target"),
        extracted_answer=extracted,
        score=score,
        is_correct=correct,
        metric_name=metric_name,
        metric_payload=metric_payload,
        image_path=str(image_path) if image_path is not None else "",
        media_id=media_id,
        image_exists=image_exists,
        image_mtime_ns=image_mtime_ns,
        category=category,
    )


def _primary_sample_files(bench_dir: Path) -> list[Path]:
    all_files = sorted(
        path
        for path in bench_dir.glob("*samples*.jsonl")
        if path.name not in {"sample_manifest.jsonl", "image_manifest.jsonl"}
    )
    direct_judge = [path for path in all_files if "direct_judge" in path.name]
    return direct_judge or all_files


def _extract_metric(row: dict[str, Any]) -> tuple[str, Any, float | None, bool | None]:
    for key in PRIMARY_NUMERIC_METRICS:
        value = row.get(key)
        if isinstance(value, (int, float, bool)):
            score = float(value)
            return key, value, score, score >= 0.999

    for key in sorted(row):
        lowered = key.lower()
        if not (lowered.endswith("_acc") or lowered.endswith("_accuracy") or lowered == "judge_accuracy"):
            continue
        payload = row.get(key)
        parsed = _score_from_payload(payload)
        if parsed is not None:
            score, correct = parsed
            return key, payload, score, correct
    return "", None, None, None


def _score_from_payload(payload: Any) -> tuple[float | None, bool | None] | None:
    if isinstance(payload, (int, float, bool)):
        score = float(payload)
        return score, score >= 0.999
    if not isinstance(payload, dict):
        return None
    for key in ("is_correct", "correct"):
        value = payload.get(key)
        if isinstance(value, bool):
            return (1.0 if value else 0.0), value
    for key in ("score", "accuracy", "acc"):
        value = payload.get(key)
        if isinstance(value, (int, float, bool)):
            score = float(value)
            return score, score >= 0.999
    return None


def _extract_answer(row: dict[str, Any], metric_payload: Any) -> str:
    direct = row.get("extracted_answer")
    if direct not in (None, ""):
        return str(direct)
    for payload in _payloads(metric_payload):
        for key in ("pred_parsed", "parsed_pred", "prediction", "pred", "extracted_answer"):
            value = payload.get(key)
            if value not in (None, ""):
                return str(value)
        judge_res = payload.get("judge_res")
        if isinstance(judge_res, dict):
            value = judge_res.get("model_response")
            if value not in (None, ""):
                return str(value)
    return _first_text(row.get("filtered_resps"))


def _extract_category(row: dict[str, Any], metric_payload: Any) -> str:
    """Return the benchmark-provided category/subject label when present."""

    for payload in (row, *_payloads(metric_payload)):
        for key in ("subject", "category", "discipline", "domain"):
            value = payload.get(key)
            if value not in (None, ""):
                return str(value)
        for nested_key in ("mmmu_acc", "meta", "metadata"):
            nested = payload.get(nested_key)
            if not isinstance(nested, dict):
                continue
            for key in ("subject", "category", "discipline", "domain"):
                value = nested.get(key)
                if value not in (None, ""):
                    return str(value)
    return ""


def _payloads(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item


def _first_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        for item in value:
            text = _first_text(item)
            if text:
                return text
    return ""


def _resolve_image_path(value: Any, *, bench_dir: Path) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    if path.is_absolute():
        return path
    return bench_dir / path


def _infer_task_name(path: Path) -> str:
    stem = path.stem
    marker = "_samples_"
    if marker in stem:
        return stem.split(marker, 1)[1]
    return stem


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rel_to_bench(bench_dir: Path, path: Path) -> str:
    try:
        return path.relative_to(bench_dir).as_posix()
    except ValueError:
        return str(path)


def _rel_to_run_root(index: BenchmarkIndex, path: Path) -> str:
    try:
        return path.relative_to(index.run_root).as_posix()
    except ValueError:
        return str(path)


def _infer_repo_root(path: Path) -> Path:
    current = path.resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists() or (candidate / ".git").exists():
            return candidate
    return Path.cwd().resolve()
