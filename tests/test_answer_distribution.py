"""Unit tests for task-agnostic answer-distribution checks."""

from __future__ import annotations

from trace.core.answer_distribution import evaluate_answer_distribution


def test_distribution_checks_pass_balanced_categorical_answers() -> None:
    rows = []
    for label in ("A", "B", "C", "D", "E"):
        rows.extend({"answer_type": "option_letter", "answer_value": label} for _ in range(20))
    report = evaluate_answer_distribution(rows)
    assert report["checks"]["min_unique_answers"]["pass"] is True
    assert report["checks"]["max_answer_frequency"]["pass"] is True
    assert report["checks"]["max_five_bin_frequency"]["pass"] is None
    assert report["pass"] is True


def test_distribution_checks_fail_on_max_answer_frequency() -> None:
    rows = []
    rows.extend({"answer_type": "integer", "answer_value": 1} for _ in range(36))
    for value in range(2, 10):
        rows.extend({"answer_type": "integer", "answer_value": value} for _ in range(8))
    report = evaluate_answer_distribution(rows)
    assert report["sample_count"] == 100
    assert report["checks"]["max_answer_frequency"]["pass"] is False
    assert report["pass"] is False


def test_distribution_reports_numeric_five_bin_summary_without_gating() -> None:
    rows = []
    rows.extend({"answer_type": "number", "answer_value": value} for value in [0.0] * 60)
    rows.extend({"answer_type": "number", "answer_value": value} for value in [4.0] * 10)
    rows.extend({"answer_type": "number", "answer_value": value} for value in [-4.0] * 10)
    rows.extend({"answer_type": "number", "answer_value": value} for value in [2.0] * 10)
    rows.extend({"answer_type": "number", "answer_value": value} for value in [-2.0] * 10)
    report = evaluate_answer_distribution(rows)
    assert report["sample_count"] == 100
    assert report["checks"]["min_unique_answers"]["pass"] is True
    assert report["checks"]["max_answer_frequency"]["pass"] is False
    assert report["checks"]["max_five_bin_frequency"]["pass"] is None
    assert report["checks"]["max_five_bin_frequency"]["status"] == "reported_not_gated_numeric_answers"
    assert report["checks"]["max_five_bin_frequency"]["observed"] == 0.6
    assert report["pass"] is False


def test_distribution_pass_ignores_numeric_bin_skew_when_core_checks_pass() -> None:
    rows = []
    values = [0.0] * 20 + [1.0] * 18 + [2.0] * 18 + [9.0] * 16 + [10.0] * 14 + [11.0] * 14
    for value in values:
        rows.append({"answer_type": "number", "answer_value": value})
    report = evaluate_answer_distribution(rows)
    assert report["checks"]["min_unique_answers"]["pass"] is True
    assert report["checks"]["max_answer_frequency"]["pass"] is True
    assert report["checks"]["max_five_bin_frequency"]["pass"] is None
    assert report["checks"]["max_five_bin_frequency"]["observed"] is not None
    assert report["pass"] is True
