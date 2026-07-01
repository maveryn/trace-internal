"""Distribution and sampling-axis helpers for task review workflows."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from .answer_distribution import evaluate_answer_distribution
from .query_ids import LEGACY_DEFAULT_QUERY_ID, NO_BRANCH_QUERY_IDS, SINGLE_QUERY_ID
from .taxonomy import resolve_task_query_id
from .task_review_calibration import CURRENT_CALIBRATION_BASELINE
from .task_review_sampling import resolve_review_query_id


MIN_REVIEW_QUERY_ID_BRANCH_SAMPLES = 10


def as_float(value: Any) -> float | None:
    """Parse one scalar as float when possible."""

    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except Exception:
            return None
    return None


def normalize_probability_map(raw: Any) -> Dict[str, float]:
    """Normalize one probability/weight map into a sorted probability map."""

    if not isinstance(raw, Mapping):
        return {}
    parsed: Dict[str, float] = {}
    for key, value in raw.items():
        numeric = as_float(value)
        if numeric is None:
            continue
        if float(numeric) <= 0.0:
            continue
        parsed[str(key)] = float(numeric)
    total = float(sum(parsed.values()))
    if total <= 0.0:
        return {}
    return {key: (float(parsed[key]) / total) for key in sorted(parsed.keys())}


def extract_sampling_axes(output: Any) -> Dict[str, Dict[str, Any]]:
    """Extract sampling-axis observed values and expected probabilities from one output."""

    trace_payload = getattr(output, "trace_payload", {})
    if not isinstance(trace_payload, Mapping):
        trace_payload = {}
    execution_trace = trace_payload.get("execution_trace", {})
    if not isinstance(execution_trace, Mapping):
        execution_trace = {}
    query_spec = trace_payload.get("query_spec", {})
    if not isinstance(query_spec, Mapping):
        query_spec = {}
    query_params = query_spec.get("params", {})
    if not isinstance(query_params, Mapping):
        query_params = {}

    axes: Dict[str, Dict[str, Any]] = {}

    def _set_axis(axis: str, *, observed: Any, expected: Mapping[str, float], source: str) -> None:
        axis_name = str(axis).strip()
        if not axis_name:
            return
        entry = axes.get(axis_name)
        expected_dict = dict(expected)
        if entry is None:
            axes[axis_name] = {
                "observed": "" if observed is None else str(observed),
                "expected_probabilities": expected_dict,
                "expected_source": str(source),
                "expected_conflict": False,
            }
            return
        if entry.get("observed") in {"", None} and observed is not None:
            entry["observed"] = str(observed)
        existing_expected = entry.get("expected_probabilities", {})
        if existing_expected and existing_expected != expected_dict:
            entry["expected_conflict"] = True
        elif (not existing_expected) and expected_dict:
            entry["expected_probabilities"] = expected_dict
            entry["expected_source"] = str(source)

    for source_name, source in (("execution_trace", execution_trace), ("query_params", query_params)):
        if not isinstance(source, Mapping):
            continue
        for key, value in source.items():
            key_text = str(key)
            if not key_text.endswith("_probabilities"):
                continue
            axis = key_text[: -len("_probabilities")]
            probs = normalize_probability_map(value)
            if not probs:
                continue
            if str(axis) == "query_id":
                observed = getattr(output, "query_id", "")
            else:
                observed = execution_trace.get(str(axis), query_params.get(str(axis), ""))
            _set_axis(str(axis), observed=observed, expected=probs, source=str(source_name))

    if str(getattr(output, "query_id", "") or "").strip() in NO_BRANCH_QUERY_IDS:
        query_axis = axes.get("query_id", {})
        if isinstance(query_axis, Mapping) and query_axis.get("expected_probabilities"):
            axes["query_id"] = {
                "observed": str(getattr(output, "query_id", "") or query_axis.get("observed", "")),
                "expected_probabilities": dict(query_axis.get("expected_probabilities", {})),
                "expected_source": str(query_axis.get("expected_source", "")),
                "expected_conflict": bool(query_axis.get("expected_conflict", False)),
            }

    if "query_id" not in axes:
        axes["query_id"] = {
            "observed": str(getattr(output, "query_id", "") or ""),
            "expected_probabilities": {},
            "expected_source": "",
            "expected_conflict": False,
        }
    return axes


def extract_replay_generation_params(output: Any) -> Dict[str, Any]:
    """Extract explicit generation params that can replay one sampled inspection row."""

    trace_payload = getattr(output, "trace_payload", {})
    if not isinstance(trace_payload, Mapping):
        return {}
    query_spec = trace_payload.get("query_spec", {})
    if not isinstance(query_spec, Mapping):
        return {}
    execution_trace = trace_payload.get("execution_trace", {})
    if not isinstance(execution_trace, Mapping):
        execution_trace = {}
    query_params = query_spec.get("params", {})
    if not isinstance(query_params, Mapping):
        return {}

    replay: Dict[str, Any] = {}
    for key, value in query_params.items():
        key_text = str(key)
        if key_text.endswith("_probabilities") or key_text.endswith("_support"):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            replay[key_text] = value
        elif isinstance(value, (list, tuple)):
            replay[key_text] = list(value)
        elif isinstance(value, Mapping):
            replay[key_text] = dict(value)
    query_id = str(getattr(output, "query_id", "") or "")
    review_query_id = resolve_review_query_id(output)
    if review_query_id:
        if query_id.strip() == SINGLE_QUERY_ID:
            replay["query_id"] = SINGLE_QUERY_ID
        elif query_id.strip() in NO_BRANCH_QUERY_IDS:
            internal_query_id = str(execution_trace.get("internal_query_id", "") or "").strip()
            if internal_query_id and internal_query_id not in {LEGACY_DEFAULT_QUERY_ID, SINGLE_QUERY_ID}:
                replay["query_id"] = str(internal_query_id)
            else:
                replay["query_id"] = str(review_query_id)
        else:
            replay.setdefault("query_id", query_id)
    return replay


def extract_answer_support(output: Any) -> list[str] | None:
    """Extract optional explicit answer support from query params."""

    trace_payload = getattr(output, "trace_payload", {})
    if not isinstance(trace_payload, Mapping):
        return None
    query_spec = trace_payload.get("query_spec", {})
    if not isinstance(query_spec, Mapping):
        return None
    query_params = query_spec.get("params", {})
    if not isinstance(query_params, Mapping):
        return None
    raw = query_params.get("answer_support")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return None
    support = [str(value) for value in raw]
    return support or None


def random_collector(output: Any, instance_seed: int) -> Dict[str, Any]:
    """Collect task-review fields from one generated output."""

    query_id = str(getattr(output, "query_id", "") or "")
    return {
        "instance_seed": int(instance_seed),
        "review_query_id": resolve_review_query_id(output),
        "scene_id": str(getattr(output, "scene_id", "") or ""),
        "query_id": str(
            getattr(output, "query_id", "")
            or resolve_task_query_id(query_id=query_id, trace_payload=getattr(output, "trace_payload", {}))
        ),
        "answer_type": str(output.answer_gt.type),
        "answer_value": output.answer_gt.value,
        "answer_support": extract_answer_support(output),
        "sampling_axes": extract_sampling_axes(output),
        "generation_params": extract_replay_generation_params(output),
    }


def answer_collector(output: Any, instance_seed: int) -> Dict[str, Any]:
    """Collect answer-only fields for distribution checks."""

    query_id = str(getattr(output, "query_id", "") or "")
    return {
        "instance_seed": int(instance_seed),
        "review_query_id": resolve_review_query_id(output),
        "scene_id": str(getattr(output, "scene_id", "") or ""),
        "query_id": str(
            getattr(output, "query_id", "")
            or resolve_task_query_id(query_id=query_id, trace_payload=getattr(output, "trace_payload", {}))
        ),
        "answer_type": str(output.answer_gt.type),
        "answer_value": output.answer_gt.value,
        "answer_support": extract_answer_support(output),
        "generation_params": extract_replay_generation_params(output),
    }


def has_multiple_query_ids(query_id_counts: Mapping[str, int], expected_probabilities: Mapping[str, float]) -> bool:
    """Return true when a task has more than one meaningful query id."""

    expected_non_empty = [str(key) for key in expected_probabilities.keys() if str(key).strip()]
    if len(expected_non_empty) > 1:
        return True
    observed_non_empty = [str(key) for key, value in query_id_counts.items() if str(key).strip() and int(value) > 0]
    return len(observed_non_empty) > 1


def build_query_id_review_warnings(
    *,
    query_id_counts: Mapping[str, int],
    expected_probabilities: Mapping[str, float],
    sample_count: int,
) -> List[Dict[str, Any]]:
    """Return non-gating warnings for weak 100-sample query-branch coverage."""

    if int(sample_count) <= 0:
        return []
    if not has_multiple_query_ids(query_id_counts, expected_probabilities):
        return []
    labels = sorted(
        {
            str(key)
            for key in [*list(query_id_counts.keys()), *list(expected_probabilities.keys())]
            if str(key).strip() not in NO_BRANCH_QUERY_IDS
        }
    )
    thin = [
        {"query_id": str(label), "sample_count": int(query_id_counts.get(str(label), 0))}
        for label in labels
        if int(query_id_counts.get(str(label), 0)) < int(MIN_REVIEW_QUERY_ID_BRANCH_SAMPLES)
    ]
    if not thin:
        return []
    return [
        {
            "kind": "thin_query_id_branch_review_coverage",
            "message": (
                "One or more query_id branches has fewer than "
                f"{int(MIN_REVIEW_QUERY_ID_BRANCH_SAMPLES)} samples in the displayed random review set."
            ),
            "threshold": int(MIN_REVIEW_QUERY_ID_BRANCH_SAMPLES),
            "sample_count": int(sample_count),
            "branches": thin,
            "gating": False,
        }
    ]


def build_sampling_axis_reports(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Build observed/expected sampling distribution report for all discovered axes."""

    axis_names: set[str] = set()
    for row in rows:
        axes = row.get("sampling_axes", {})
        if isinstance(axes, Mapping):
            axis_names.update(str(axis) for axis in axes.keys())

    reports: Dict[str, Dict[str, Any]] = {}
    for axis in sorted(axis_names):
        observed_counts: Dict[str, int] = {}
        expected_map: Dict[str, float] = {}
        expected_conflict = False
        expected_source = ""

        for row in rows:
            axes = row.get("sampling_axes", {})
            axis_entry = axes.get(axis, {}) if isinstance(axes, Mapping) else {}
            observed = axis_entry.get("observed")
            observed_label = str(observed) if observed is not None else ""
            if str(axis) == "query_id" and not observed_label:
                observed_label = str(row.get("review_query_id", "") or row.get("query_id", "") or "")
            observed_counts[observed_label] = int(observed_counts.get(observed_label, 0) + 1)

            raw_expected = axis_entry.get("expected_probabilities", {}) if isinstance(axis_entry, Mapping) else {}
            normalized_expected = normalize_probability_map(raw_expected)
            if normalized_expected:
                if not expected_map:
                    expected_map = dict(normalized_expected)
                    expected_source = str(axis_entry.get("expected_source", ""))
                elif expected_map != normalized_expected:
                    expected_conflict = True
            if bool(axis_entry.get("expected_conflict", False)):
                expected_conflict = True

        total = int(sum(observed_counts.values()))
        max_count = int(max(observed_counts.values())) if observed_counts else 0
        reports[str(axis)] = {
            "sample_count": int(total),
            "observed_counts": dict(sorted(observed_counts.items(), key=lambda item: item[0])),
            "max_observed_frequency": (float(max_count) / float(total)) if int(total) > 0 else 0.0,
            "expected_probabilities": dict(expected_map),
            "expected_source": str(expected_source),
            "expected_conflict": bool(expected_conflict),
        }

    return reports


def build_random_review_report(*, task_id: str, rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Build random-sample review report for one task."""

    answer_report = evaluate_rows(rows)
    sampling_axes = build_sampling_axis_reports(rows)
    query_id_axis = sampling_axes.get("query_id", {})
    query_id_counts = query_id_axis.get("observed_counts", {}) if isinstance(query_id_axis, Mapping) else {}
    query_id_expected = query_id_axis.get("expected_probabilities", {}) if isinstance(query_id_axis, Mapping) else {}
    has_query_ids = has_multiple_query_ids(query_id_counts, query_id_expected)
    warnings = build_query_id_review_warnings(
        query_id_counts=query_id_counts if isinstance(query_id_counts, Mapping) else {},
        expected_probabilities=query_id_expected if isinstance(query_id_expected, Mapping) else {},
        sample_count=int(len(rows)),
    )

    return {
        "task_id": str(task_id),
        "calibration_baseline": CURRENT_CALIBRATION_BASELINE,
        "sample_count": int(len(rows)),
        "answer_distribution": answer_report,
        "sampling_axes": sampling_axes,
        "warnings": list(warnings),
        "query_id_distribution": {
            "has_query_ids": bool(has_query_ids),
            "status": "reported" if bool(has_query_ids) else "skipped_no_query_ids",
            "observed_counts": dict(query_id_counts),
            "expected_probabilities": dict(query_id_expected),
            "expected_source": str(query_id_axis.get("expected_source", "")) if isinstance(query_id_axis, Mapping) else "",
            "expected_conflict": bool(query_id_axis.get("expected_conflict", False)) if isinstance(query_id_axis, Mapping) else False,
            "warnings": list(warnings),
        },
    }


def evaluate_rows(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Evaluate standard answer-distribution checks for one row slice."""

    answer_rows = [
        {
            "answer_type": str(row.get("answer_type", "")),
            "answer_value": row.get("answer_value"),
        }
        for row in rows
    ]
    min_unique_answers = 4
    max_answer_frequency = 1.0 / 3.0
    if not answer_rows:
        return {
            "sample_count": 0,
            "unique_answers": 0,
            "max_answer_count": 0,
            "max_answer_frequency": 0.0,
            "checks": {
                "min_unique_answers": {"pass": False},
                "max_answer_frequency": {"pass": False},
                "max_five_bin_frequency": {"pass": None, "observed": None, "status": "not_reported_no_samples"},
            },
            "pass": False,
        }
    return evaluate_answer_distribution(
        answer_rows,
        min_unique_answers=int(min_unique_answers),
        max_answer_frequency=float(max_answer_frequency),
    )


def build_distribution_review_report(
    *,
    task_id: str,
    domain: str,
    scene_id: str,
    random_rows: Sequence[Mapping[str, Any]],
    random_report: Mapping[str, Any],
    query_id_rows: Mapping[str, List[Dict[str, Any]]] | None,
    query_id_collection_meta: Mapping[str, Any] | None,
) -> Dict[str, Any]:
    """Build distribution review report from random and per-query-id samples."""

    query_id_distribution = random_report.get("query_id_distribution", {})
    has_query_ids = bool(query_id_distribution.get("has_query_ids", False))

    if not has_query_ids:
        single_report = evaluate_rows(random_rows)
        report = {
            "task_id": str(task_id),
            "calibration_baseline": CURRENT_CALIBRATION_BASELINE,
            "domain": str(domain),
            "scene_id": str(scene_id),
            "mode": "single_sample",
            "has_query_ids": False,
            "overall": dict(single_report),
            "per_query_id": {"": dict(single_report)},
            "failed_query_ids": [""] if not bool(single_report.get("pass", False)) else [],
            "incomplete_query_ids": [],
            "pass": bool(single_report.get("pass", False)),
            "query_id_distribution": dict(query_id_distribution),
            "sampling_axes": dict(random_report.get("sampling_axes", {})),
            "warnings": list(random_report.get("warnings", []) or []),
        }
        if str(scene_id).strip():
            report["scene_id"] = str(scene_id)
        return report

    query_id_rows = query_id_rows or {}
    query_id_collection_meta = query_id_collection_meta or {}
    expected_query_ids = list(query_id_collection_meta.get("expected_query_ids", []))
    if not expected_query_ids:
        expected_query_ids = sorted(query_id_rows.keys())
    per_query_id: Dict[str, Any] = {}
    combined_rows: List[Dict[str, Any]] = []

    for query_id in expected_query_ids:
        rows = list(query_id_rows.get(str(query_id), []))
        combined_rows.extend(rows)
        if rows:
            per_query_id[str(query_id)] = evaluate_rows(rows)

    overall = evaluate_rows(combined_rows)
    failed_query_ids = [
        str(query_id)
        for query_id, result in per_query_id.items()
        if not bool(result.get("pass", False))
    ]
    incomplete_query_ids = list(query_id_collection_meta.get("incomplete_query_ids", []))
    no_samples_collected = not bool(combined_rows)
    task_pass = bool((not failed_query_ids) and (not incomplete_query_ids) and (not no_samples_collected))

    report = {
        "task_id": str(task_id),
        "calibration_baseline": CURRENT_CALIBRATION_BASELINE,
        "domain": str(domain),
        "scene_id": str(scene_id),
        "mode": "per_query_id",
        "has_query_ids": True,
        "overall": overall,
        "per_query_id": per_query_id,
        "failed_query_ids": failed_query_ids,
        "incomplete_query_ids": incomplete_query_ids,
        "no_samples_collected": bool(no_samples_collected),
        "pass": bool(task_pass),
        "query_id_distribution": dict(query_id_distribution),
        "sampling_axes": dict(random_report.get("sampling_axes", {})),
        "warnings": list(random_report.get("warnings", []) or []),
        "collection": {
            "target_count_per_query_id": int(query_id_collection_meta.get("target_count_per_query_id", 0)),
            "total_generated": int(query_id_collection_meta.get("total_generated", 0)),
            "expected_query_ids": list(expected_query_ids),
            "generated_query_id_counts": dict(query_id_collection_meta.get("generated_query_id_counts", {})),
            "collected_query_id_counts": dict(query_id_collection_meta.get("collected_query_id_counts", {})),
            "generation_error_counts": dict(query_id_collection_meta.get("generation_error_counts", {})),
        },
    }
    if str(scene_id).strip():
        report["scene_id"] = str(scene_id)
    return report


__all__ = [
    "answer_collector",
    "as_float",
    "build_distribution_review_report",
    "build_random_review_report",
    "build_sampling_axis_reports",
    "build_query_id_review_warnings",
    "evaluate_rows",
    "extract_replay_generation_params",
    "extract_sampling_axes",
    "has_multiple_query_ids",
    "normalize_probability_map",
    "random_collector",
]
