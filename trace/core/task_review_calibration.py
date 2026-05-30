"""Calibration status helpers for task-review artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


MODEL_IDS: Dict[str, str] = {
    "qwen25vl7b": "Qwen/Qwen2.5-VL-7B-Instruct",
    "qwen3vl8b": "Qwen/Qwen3-VL-8B-Instruct",
    "qwen3vl4b": "Qwen/Qwen3-VL-4B-Instruct",
}
MODEL_RESPONSE_CAP_THRESHOLDS: Dict[str, float] = {
    "qwen25vl7b": 0.25,
    "qwen3vl8b": 0.25,
    "qwen3vl4b": 0.25,
}
CURRENT_CALIBRATION_MODEL_SLUGS = {"qwen25vl7b"}
CURRENT_CALIBRATION_BASELINE = "v0"
DIFFICULTY_TAIL_THRESHOLD = 0.50


def scene_status_candidates(out_root: Path) -> List[Path]:
    """Return candidate calibration status files for one review root."""

    root = Path(out_root)
    candidates = [
        root.parent / "calibration_sweep_status.json",
        Path("review/calibration_sweep_status.json"),
    ]
    unique: List[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def status_reasons_from_stats(
    stats: Mapping[str, Any],
    *,
    model_slug: str,
    model_response_cap_thresholds: Mapping[str, float] | None = None,
    difficulty_tail_threshold: float = DIFFICULTY_TAIL_THRESHOLD,
) -> tuple[str, List[str]]:
    """Return calibration status/reasons from stats using current gates."""

    thresholds = model_response_cap_thresholds or MODEL_RESPONSE_CAP_THRESHOLDS
    overall = stats.get("overall", {})
    if not isinstance(overall, Mapping):
        overall = {}
    prompt_stats = stats.get("prompt_token_stats", {})
    if not isinstance(prompt_stats, Mapping):
        prompt_stats = {}
    response_stats = stats.get("response_token_stats", {})
    if not isinstance(response_stats, Mapping):
        response_stats = {}

    blocked_reasons: List[str] = []
    if int(prompt_stats.get("over_limit_count") or 0) > 0:
        blocked_reasons.append("prompt_over_limit")
    cap_threshold = float(thresholds.get(str(model_slug), 0.25))
    if float(response_stats.get("cap_rate") or 0.0) > cap_threshold:
        blocked_reasons.append("response_cap_rate")
    if not overall:
        blocked_reasons.append("missing_overall_stats")
    if blocked_reasons:
        return "blocked", blocked_reasons

    tuning_reasons: List[str] = []
    if float(overall.get("hard_frac") or 0.0) >= float(difficulty_tail_threshold):
        tuning_reasons.append("hard_frac")
    if float(overall.get("easy_frac") or 0.0) >= float(difficulty_tail_threshold):
        tuning_reasons.append("easy_frac")
    mean = float(overall.get("mean_solve_rate") or 0.0)
    if mean < 0.10 or mean > 0.75:
        tuning_reasons.append("mean_solve_rate")
    if tuning_reasons:
        return "needs_manual_tuning", tuning_reasons
    return "accepted", []


def model_stats_row_from_record(
    *,
    task_id: str,
    scene_id: str,
    combined_status: str,
    model_slug: str,
    model_record: Mapping[str, Any],
    model_ids: Mapping[str, str] | None = None,
) -> Dict[str, Any] | None:
    """Build one model stats row from a calibration sweep model record."""

    resolved_model_ids = model_ids or MODEL_IDS
    stats = model_record.get("stats", {})
    if not isinstance(stats, Mapping):
        return None
    overall = stats.get("overall", {})
    if not isinstance(overall, Mapping):
        overall = {}
    prompt_stats = stats.get("prompt_token_stats", {})
    if not isinstance(prompt_stats, Mapping):
        prompt_stats = {}
    response_stats = stats.get("response_token_stats", {})
    if not isinstance(response_stats, Mapping):
        response_stats = {}
    reasons = model_record.get("reasons", [])
    if isinstance(reasons, str):
        reason_text = reasons
    elif isinstance(reasons, Sequence):
        reason_text = ", ".join(str(item) for item in reasons)
    else:
        reason_text = ""

    return {
        "task": str(task_id),
        "scene_id": str(scene_id),
        "combined_status": str(combined_status),
        "model": str(model_slug),
        "model_id": str(model_record.get("model_id", resolved_model_ids.get(str(model_slug), ""))),
        "model_status": str(model_record.get("status", "")),
        "reasons": reason_text,
        "hard_frac": overall.get("hard_frac"),
        "easy_frac": overall.get("easy_frac"),
        "band_frac": overall.get("band_frac"),
        "mean_solve_rate": overall.get("mean_solve_rate"),
        "response_cap_rate": response_stats.get("cap_rate"),
        "prompt_max": prompt_stats.get("max"),
        "prompt_over_limit_count": prompt_stats.get("over_limit_count"),
        "rollout_count": overall.get("rollout_count"),
        "prompt_count": overall.get("prompt_count"),
        "max_response_length": model_record.get("max_response_length"),
        "solve_workbook": str(model_record.get("solve_workbook", "")),
        "calibration_stats": str(model_record.get("calibration_stats", "")),
        "output_dir": str(model_record.get("output_dir", "")),
    }


def model_stats_row_from_stats_file(
    *,
    stats_path: Path,
    model_slug: str,
    task_id: str,
    scene_id: str,
    combined_status: str,
    calibration_baseline: str = CURRENT_CALIBRATION_BASELINE,
    model_ids: Mapping[str, str] | None = None,
    model_response_cap_thresholds: Mapping[str, float] | None = None,
    difficulty_tail_threshold: float = DIFFICULTY_TAIL_THRESHOLD,
) -> Dict[str, Any] | None:
    """Build one model stats row from a calibration_stats.json file."""

    resolved_model_ids = model_ids or MODEL_IDS
    try:
        stats = json.loads(Path(stats_path).read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(stats, Mapping):
        return None
    config = stats.get("config", {})
    if not isinstance(config, Mapping):
        config = {}
    if str(config.get("calibration_baseline", "")).strip() != str(calibration_baseline):
        return None
    artifacts = stats.get("artifacts", {})
    if not isinstance(artifacts, Mapping):
        artifacts = {}
    status, reasons = status_reasons_from_stats(
        stats,
        model_slug=str(model_slug),
        model_response_cap_thresholds=model_response_cap_thresholds,
        difficulty_tail_threshold=float(difficulty_tail_threshold),
    )
    record = {
        "model_id": resolved_model_ids.get(str(model_slug), str(model_slug)),
        "status": status,
        "reasons": reasons,
        "stats": stats,
        "max_response_length": config.get("max_response_length"),
        "solve_workbook": artifacts.get("solve_workbook", ""),
        "calibration_stats": artifacts.get("calibration_stats", str(stats_path)),
        "output_dir": config.get("probe_output_dir", str(stats_path.parent)),
    }
    return model_stats_row_from_record(
        task_id=str(task_id),
        scene_id=str(scene_id),
        combined_status=str(combined_status or status),
        model_slug=str(model_slug),
        model_record=record,
        model_ids=resolved_model_ids,
    )


def latest_stats_files_by_task_model(
    *,
    domain: str,
    scene_id: str,
    task_ids: Sequence[str],
    probe_root: Path = Path("rlvr/outputs/calibration/current"),
) -> Dict[tuple[str, str], Path]:
    """Return latest calibration stats files keyed by ``(task_id, model_slug)``."""

    task_set = {str(task_id) for task_id in task_ids}
    root = Path(probe_root)
    if not root.exists():
        return {}
    selected: Dict[tuple[str, str], Path] = {}
    priorities: Dict[tuple[str, str], tuple[bool, int, float]] = {}
    pattern = f"*/{str(domain)}/{str(scene_id)}/task_*/100x*_seed*/calibration_stats.json"
    for stats_path in root.glob(pattern):
        try:
            rel = stats_path.relative_to(root)
        except ValueError:
            continue
        if len(rel.parts) < 6:
            continue
        model_slug = str(rel.parts[0])
        task_id = str(rel.parts[3])
        if task_id not in task_set:
            continue
        rollout_match = re.match(r"100x(?P<rollouts>\d+)_seed", str(rel.parts[4]))
        if rollout_match is None:
            continue
        rollout_count = int(rollout_match.group("rollouts"))
        key = (task_id, model_slug)
        mtime = float(stats_path.stat().st_mtime)
        priority = (int(rollout_count) == 24, int(rollout_count), mtime)
        if key not in selected or priority >= priorities.get(key, (False, -1, 0.0)):
            selected[key] = stats_path
            priorities[key] = priority
    return selected


def load_scene_model_stats_rows(
    *,
    out_root: Path,
    domain: str,
    scene_id: str,
    task_ids: Sequence[str],
    calibration_baseline: str = CURRENT_CALIBRATION_BASELINE,
    current_model_slugs: set[str] | None = None,
    model_ids: Mapping[str, str] | None = None,
    model_response_cap_thresholds: Mapping[str, float] | None = None,
    difficulty_tail_threshold: float = DIFFICULTY_TAIL_THRESHOLD,
    probe_root: Path = Path("rlvr/outputs/calibration/current"),
) -> List[Dict[str, Any]]:
    """Load per-task/model calibration stats for one scene when available."""

    allowed_model_slugs = set(current_model_slugs or CURRENT_CALIBRATION_MODEL_SLUGS)
    resolved_model_ids = model_ids or MODEL_IDS
    status: Dict[str, Any] = {}
    for candidate in scene_status_candidates(Path(out_root)):
        if not candidate.exists():
            continue
        try:
            loaded = json.loads(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(loaded, Mapping):
            status = dict(loaded)
            break
    status_config = status.get("config", {}) if isinstance(status.get("config"), Mapping) else {}
    if str(status_config.get("calibration_baseline", "")).strip() != str(calibration_baseline):
        status = {}
    records = status.get("tasks", {})
    if not isinstance(records, Mapping):
        records = {}

    row_map: Dict[tuple[str, str], Dict[str, Any]] = {}
    combined_status_by_task: Dict[str, str] = {}
    reviewer_override_tasks: set[str] = set()
    reviewer_override_models: set[tuple[str, str]] = set()
    suppress_stats_fallback_tasks: set[str] = set()
    for task_id in sorted(str(item) for item in task_ids):
        record = records.get(task_id, {})
        if not isinstance(record, Mapping):
            continue
        if str(record.get("domain", domain)) != str(domain):
            continue
        if str(record.get("scene_id", scene_id)) != str(scene_id):
            continue

        combined_status_by_task[task_id] = str(record.get("status", ""))
        if str(record.get("status", "")).strip() in {"dry_run", "reviewed_pending_probe"}:
            suppress_stats_fallback_tasks.add(task_id)
        record_has_reviewer_override = bool(record.get("reviewer_override"))
        if record_has_reviewer_override:
            reviewer_override_tasks.add(task_id)
        models = record.get("models", {})
        if not isinstance(models, Mapping):
            continue
        for model_slug in sorted(str(key) for key in models.keys()):
            if model_slug not in allowed_model_slugs:
                continue
            model_record = models.get(model_slug, {})
            if not isinstance(model_record, Mapping):
                continue
            row = model_stats_row_from_record(
                task_id=task_id,
                scene_id=str(record.get("scene_id", scene_id)),
                combined_status=str(record.get("status", "")),
                model_slug=model_slug,
                model_record=model_record,
                model_ids=resolved_model_ids,
            )
            if row is not None:
                row_map[(task_id, model_slug)] = row
                if record_has_reviewer_override or bool(model_record.get("reviewer_override")):
                    reviewer_override_models.add((task_id, model_slug))

    for (task_id, model_slug), stats_path in latest_stats_files_by_task_model(
        domain=str(domain),
        scene_id=str(scene_id),
        task_ids=task_ids,
        probe_root=Path(probe_root),
    ).items():
        if model_slug not in allowed_model_slugs:
            continue
        if task_id in suppress_stats_fallback_tasks:
            continue
        if (task_id, model_slug) in reviewer_override_models:
            continue
        row = model_stats_row_from_stats_file(
            stats_path=stats_path,
            model_slug=model_slug,
            task_id=task_id,
            scene_id=str(scene_id),
            combined_status=combined_status_by_task.get(task_id, ""),
            calibration_baseline=str(calibration_baseline),
            model_ids=resolved_model_ids,
            model_response_cap_thresholds=model_response_cap_thresholds,
            difficulty_tail_threshold=float(difficulty_tail_threshold),
        )
        if row is not None:
            row_map[(task_id, model_slug)] = row

    statuses_by_task: Dict[str, List[str]] = {}
    for (task_id, _model_slug), row in row_map.items():
        status_text = str(row.get("model_status", "")).strip()
        if status_text:
            statuses_by_task.setdefault(task_id, []).append(status_text)
    combined_by_task: Dict[str, str] = {}
    for task_id, statuses in statuses_by_task.items():
        if any(status == "blocked" for status in statuses):
            combined_by_task[task_id] = "blocked"
        elif statuses and all(status == "accepted" for status in statuses):
            combined_by_task[task_id] = "accepted"
        elif statuses:
            combined_by_task[task_id] = "needs_manual_tuning"
    for (task_id, _model_slug), row in row_map.items():
        if task_id in combined_by_task:
            row["combined_status"] = combined_by_task[task_id]
        if task_id in reviewer_override_tasks:
            row["combined_status"] = combined_status_by_task.get(task_id, row.get("combined_status", ""))

    return [row_map[key] for key in sorted(row_map.keys())]


__all__ = [
    "CURRENT_CALIBRATION_BASELINE",
    "CURRENT_CALIBRATION_MODEL_SLUGS",
    "DIFFICULTY_TAIL_THRESHOLD",
    "MODEL_IDS",
    "MODEL_RESPONSE_CAP_THRESHOLDS",
    "latest_stats_files_by_task_model",
    "load_scene_model_stats_rows",
    "model_stats_row_from_record",
    "model_stats_row_from_stats_file",
    "scene_status_candidates",
    "status_reasons_from_stats",
]
