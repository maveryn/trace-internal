#!/usr/bin/env python3
"""Audit persisted Qwen3 extraction artifacts for the TRACE Final25 suite."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from benchmark_queue_lib import REPO_ROOT, json_default, write_json
from trace_final25_contract import CONTRACT_BY_KEY, OPTION_TEXT_REQUIRED_KEYS


def _normalize_option_value(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().strip(" .,:;\"'`").lower()


def audit_items(root: Path) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    empty: Counter[str] = Counter()
    malformed_option: Counter[str] = Counter()
    missing_binary: Counter[str] = Counter()
    gt_excluded: Counter[str] = Counter()
    missing_option_text: Counter[str] = Counter()
    gt_excluded_from_options: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}

    for path in root.rglob("items/*.json"):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        benchmark = str(row.get("benchmark", ""))
        if benchmark not in CONTRACT_BY_KEY:
            continue
        counts[benchmark] += 1
        extracted = str(row.get("extracted", "")).strip()
        kind = str(row.get("answer_kind", ""))
        valid = {str(item) for item in (row.get("valid_letters") or [])}
        options = {str(key): str(value) for key, value in (row.get("options") or {}).items() if str(value).strip()}
        answer = str(row.get("answer", "")).strip().upper()
        if not extracted:
            empty[benchmark] += 1
        if kind in {"option", "option_value"} and extracted and extracted not in valid | {"Z"}:
            malformed_option[benchmark] += 1
            examples.setdefault("malformed_option", []).append(str(path))
        if kind == "judge_binary" and row.get("judge_score") is None:
            missing_binary[benchmark] += 1
            examples.setdefault("missing_binary", []).append(str(path))
        if kind == "option" and len(answer) == 1 and answer.isalpha() and answer not in valid:
            gt_excluded[benchmark] += 1
            examples.setdefault("gt_excluded", []).append(str(path))
        if benchmark in OPTION_TEXT_REQUIRED_KEYS and not options:
            missing_option_text[benchmark] += 1
            examples.setdefault("missing_option_text", []).append(str(path))
        if kind == "option" and benchmark in OPTION_TEXT_REQUIRED_KEYS and len(answer) == 1 and answer not in options:
            gt_excluded_from_options[benchmark] += 1
            examples.setdefault("gt_excluded_from_options", []).append(str(path))
        if kind == "option_value" and benchmark in OPTION_TEXT_REQUIRED_KEYS:
            normalized_answer = _normalize_option_value(row.get("answer"))
            normalized_options = {_normalize_option_value(value) for value in options.values()}
            if answer not in options and normalized_answer not in normalized_options:
                gt_excluded_from_options[benchmark] += 1
                examples.setdefault("gt_excluded_from_options", []).append(str(path))

    return {
        "root": str(root),
        "files_scanned": int(sum(counts.values())),
        "rows_by_benchmark": dict(sorted(counts.items())),
        "empty_extractions": {key: value for key, value in sorted(empty.items()) if value},
        "malformed_option_extractions": {key: value for key, value in sorted(malformed_option.items()) if value},
        "missing_binary_decisions": {key: value for key, value in sorted(missing_binary.items()) if value},
        "ground_truth_excluded_from_valid_options": {
            key: value for key, value in sorted(gt_excluded.items()) if value
        },
        "missing_required_option_text": {
            key: value for key, value in sorted(missing_option_text.items()) if value
        },
        "ground_truth_excluded_from_parsed_option_text": {
            key: value for key, value in sorted(gt_excluded_from_options.items()) if value
        },
        "examples": {key: paths[:10] for key, paths in sorted(examples.items())},
        "interpretation": (
            "Historical artifacts may contain failures fixed by the current pipeline. "
            "A clean final run must report zero malformed option extractions, missing binary decisions, "
            "ground truths excluded from valid options, missing required option text, and ground truths "
            "excluded from parsed option text."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm-extracted-root", type=Path, default=REPO_ROOT / "benchmark" / "llm_extracted")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_items(args.llm_extracted_root)
    if args.output is not None:
        write_json(args.output, report)
    print(json.dumps(report, indent=2, ensure_ascii=False, default=json_default))


if __name__ == "__main__":
    main()
