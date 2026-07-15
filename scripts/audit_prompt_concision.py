#!/usr/bin/env python3
"""Audit rendered Trace prompts for verbosity and repeated scaffolding."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Iterable

from trace.core.task_review_sampling import collect_query_id_samples
from trace.core.seed import hash64
from trace.tasks import TASK_REGISTRY, create_task


SCAFFOLD_TERMS = (
    "image",
    "chart",
    "diagram",
    "table",
    "board",
    "question",
    "answer",
)

_FORMAT_SECTION_RE = re.compile(
    r"\n(?:"
    r"Answer format:|Required answer format:|Final answer format:|Use this answer format:|"
    r"Annotation format:|Required annotation format:|Use this annotation format:|"
    r"Format for the \"answer\" field:|Format for the \"annotation\" field:|"
    r"Example JSON:"
    r")"
)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _term_counts(text: str) -> dict[str, int]:
    lowered = text.lower()
    return {term: len(re.findall(rf"\b{re.escape(term)}\b", lowered)) for term in SCAFFOLD_TERMS}


def _semantic_body(text: str) -> str:
    match = _FORMAT_SECTION_RE.search(text)
    if match is None:
        return text
    return text[: match.start()].strip()


def _prompt_rows_for_output(output: Any, instance_seed: int) -> list[dict[str, Any]]:
    """Convert one generated task output into per-prompt-variant audit rows."""
    rows: list[dict[str, Any]] = []
    prompt_variants = output.prompt_variants or {"active": output.prompt}
    for mode, prompt in sorted(prompt_variants.items()):
        body = _semantic_body(prompt)
        counts = _term_counts(body)
        repeated_terms = {term: count for term, count in counts.items() if count >= 3}
        rows.append(
            {
                "task": getattr(output, "task_id", "") or "",
                "mode": mode,
                "query_id": output.query_id,
                "instance_seed": int(instance_seed),
                "word_count": _word_count(prompt),
                "body_word_count": _word_count(body),
                "repeated_terms": repeated_terms,
                "prompt": prompt,
            }
        )
    return rows


def _resolve_task_ids(raw_tasks: str) -> list[str]:
    if not raw_tasks.strip():
        return sorted(TASK_REGISTRY)
    task_ids = [item.strip() for item in raw_tasks.split(",") if item.strip()]
    unknown = [task_id for task_id in task_ids if task_id not in TASK_REGISTRY]
    if unknown:
        raise ValueError(f"unknown task ids: {', '.join(sorted(unknown))}")
    return sorted(dict.fromkeys(task_ids))


def _iter_prompt_rows(task_ids: Iterable[str], *, samples_per_task: int, max_attempts: int) -> Iterable[dict[str, Any]]:
    for task_id in task_ids:
        task = create_task(task_id)
        emitted = 0
        sample_index = 0
        failures: list[str] = []
        while emitted < samples_per_task and sample_index < samples_per_task * 8:
            seed = hash64(20260415, f"prompt_concision.{task_id}", sample_index)
            try:
                output = task.generate(seed, params={}, max_attempts=max_attempts)
            except Exception as exc:  # pragma: no cover - audit-only resilience
                failures.append(f"{sample_index}: {exc}")
                sample_index += 1
                continue
            for row in _prompt_rows_for_output(output, seed):
                row["task"] = task_id
                yield row
            emitted += 1
            sample_index += 1
        if emitted < samples_per_task:
            failure_note = "; ".join(failures[:3]) if failures else "no samples emitted"
            yield {
                "task": task_id,
                "mode": "<generation_failed>",
                "query_id": "",
                "sample_index": -1,
                "instance_seed": -1,
                "word_count": 0,
                "body_word_count": 0,
                "repeated_terms": {},
                "prompt": failure_note,
            }


def _collect_prompt_sample(output: Any, instance_seed: int) -> dict[str, Any]:
    """Collector callback used by query-id-aware sampling."""
    return {
        "task": getattr(output, "task_id", "") or "",
        "query_id": str(getattr(output, "query_id", "") or ""),
        "sample_index": int(instance_seed),
        "instance_seed": int(instance_seed),
        "rows": _prompt_rows_for_output(output, instance_seed),
    }


def _iter_query_id_prompt_rows(
    task_ids: Iterable[str],
    *,
    samples_per_query_id: int,
    max_attempts: int,
    max_total_samples_per_task: int,
    workers: int,
    progress: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Collect prompt rows while trying to cover each declared or observed query id."""
    rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []
    task_id_list = list(task_ids)
    for index, task_id in enumerate(task_id_list, start=1):
        if progress:
            print(f"[{index}/{len(task_id_list)}] sampling {task_id}", file=sys.stderr, flush=True)
        collected = collect_query_id_samples(
            task_id=str(task_id),
            target_count_per_query_id=int(samples_per_query_id),
            seed=int(hash64(20260415, f"prompt_concision.query_id.{task_id}", 0)),
            max_attempts_per_instance=int(max_attempts),
            max_total_samples_per_task=int(max_total_samples_per_task),
            workers=int(workers),
            collector=_collect_prompt_sample,
        )
        task_row_count_before = len(rows)
        for samples in collected["samples_by_query_id"].values():
            for sample in samples:
                for row in sample["rows"]:
                    row["task"] = task_id
                    rows.append(row)
        if len(rows) == task_row_count_before:
            errors = collected.get("generation_error_counts", {})
            rows.append(
                {
                    "task": task_id,
                    "mode": "<generation_failed>",
                    "query_id": "",
                    "sample_index": -1,
                    "instance_seed": -1,
                    "word_count": 0,
                    "body_word_count": 0,
                    "repeated_terms": {},
                    "prompt": f"no samples emitted; errors={dict(errors)}",
                }
            )
        coverage_rows.append(
            {
                "task": task_id,
                "expected_query_ids": list(collected.get("expected_query_ids", [])),
                "generated_query_id_counts": dict(collected.get("generated_query_id_counts", {})),
                "collected_query_id_counts": dict(collected.get("collected_query_id_counts", {})),
                "incomplete_query_ids": list(collected.get("incomplete_query_ids", [])),
                "generation_error_counts": dict(collected.get("generation_error_counts", {})),
                "total_generated": int(collected.get("total_generated", 0)),
            }
        )
        if progress:
            incomplete = list(collected.get("incomplete_query_ids", []))
            print(
                f"[{index}/{len(task_id_list)}] done {task_id}: "
                f"query_ids={len(collected.get('expected_query_ids', []))}, "
                f"generated={collected.get('total_generated', 0)}, incomplete={len(incomplete)}",
                file=sys.stderr,
                flush=True,
            )
    return rows, coverage_rows


def _write_markdown(
    rows: list[dict[str, Any]],
    output_path: Path,
    *,
    top_k: int,
    coverage_rows: list[dict[str, Any]] | None = None,
    include_all_prompts: bool = False,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    longest = sorted(rows, key=lambda row: int(row["word_count"]), reverse=True)[:top_k]
    repeated = [
        row
        for row in rows
        if row["repeated_terms"]
    ]
    repeated = sorted(
        repeated,
        key=lambda row: (sum(row["repeated_terms"].values()), int(row["word_count"])),
        reverse=True,
    )[:top_k]

    task_counts = Counter(row["task"] for row in rows)
    query_id_counts = Counter((row["task"], row["query_id"]) for row in rows if str(row["mode"]) != "<generation_failed>")
    incomplete_coverage = [
        row
        for row in (coverage_rows or [])
        if row.get("incomplete_query_ids") or row.get("generation_error_counts")
    ]
    lines = [
        "# Prompt Concision Audit",
        "",
        f"- rendered prompts: `{len(rows)}`",
        f"- tasks covered: `{len(task_counts)}`",
        f"- observed query ids covered: `{len(query_id_counts)}`",
        "",
        "## Variant Coverage",
        "",
    ]
    if coverage_rows is None:
        lines.extend(["- query-id-aware sampling: `disabled`", ""])
    else:
        lines.extend(
            [
                f"- tasks with incomplete query ids or generation errors: `{len(incomplete_coverage)}`",
                "",
                "| task | expected_query_ids | collected_query_id_counts | generated | issues |",
                "| --- | --- | --- | ---: | --- |",
            ]
        )
        for row in coverage_rows:
            issues: list[str] = []
            if row.get("incomplete_query_ids"):
                issues.append(f"incomplete={row['incomplete_query_ids']}")
            if row.get("generation_error_counts"):
                issues.append(f"errors={row['generation_error_counts']}")
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(row["task"]),
                        "`" + ", ".join(str(value) for value in row.get("expected_query_ids", [])) + "`",
                        "`" + str(dict(row.get("collected_query_id_counts", {}))) + "`",
                        str(row.get("total_generated", 0)),
                        "`" + ("; ".join(issues) if issues else "") + "`",
                    ]
                )
                + " |"
            )
        lines.append("")

    lines.extend(
        [
        "## Longest Prompts",
        "",
        ]
    )
    for row in longest:
        sample_label = row.get("sample_index", row.get("instance_seed", ""))
        lines.extend(
            [
                f"### {row['task']} / {row['mode']} / sample {sample_label}",
                "",
                f"- `query_id`: `{row['query_id']}`",
                f"- `instance_seed`: `{row.get('instance_seed', '')}`",
                f"- `word_count`: `{row['word_count']}`",
                f"- `body_word_count`: `{row['body_word_count']}`",
                "",
                "```text",
                str(row["prompt"]),
                "```",
                "",
            ]
        )

    lines.extend(["## Repeated Scaffolding Terms", ""])
    for row in repeated:
        sample_label = row.get("sample_index", row.get("instance_seed", ""))
        lines.extend(
            [
                f"### {row['task']} / {row['mode']} / sample {sample_label}",
                "",
                f"- `query_id`: `{row['query_id']}`",
                f"- `instance_seed`: `{row.get('instance_seed', '')}`",
                f"- `word_count`: `{row['word_count']}`",
                f"- `body_word_count`: `{row['body_word_count']}`",
                f"- `repeated_terms`: `{dict(row['repeated_terms'])}`",
                "",
                "```text",
                str(row["prompt"]),
                "```",
                "",
            ]
        )
    if include_all_prompts:
        lines.extend(["## All Prompt Samples", ""])
        for row in sorted(
            rows,
            key=lambda value: (
                str(value["task"]),
                str(value["query_id"]),
                str(value["mode"]),
                int(value.get("sample_index", 0)),
            ),
        ):
            sample_label = row.get("sample_index", row.get("instance_seed", ""))
            lines.extend(
                [
                    f"### {row['task']} / {row['query_id']} / {row['mode']} / sample {sample_label}",
                    "",
                    f"- `instance_seed`: `{row.get('instance_seed', '')}`",
                    f"- `word_count`: `{row['word_count']}`",
                    f"- `body_word_count`: `{row['body_word_count']}`",
                    "",
                    "```text",
                    str(row["prompt"]),
                    "```",
                    "",
                ]
            )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default="", help="Comma-separated task ids. Defaults to all registered tasks.")
    parser.add_argument("--samples-per-task", type=int, default=1)
    parser.add_argument("--query-id-coverage", action="store_true", help="Sample until declared/observed query ids are covered.")
    parser.add_argument("--samples-per-query-id", type=int, default=1)
    parser.add_argument("--max-total-samples-per-task", type=int, default=256)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--max-attempts", type=int, default=128)
    parser.add_argument("--top-k", type=int, default=25)
    parser.add_argument("--include-all-prompts", action="store_true", help="Append every collected prompt sample to the report.")
    parser.add_argument("--progress", action="store_true", help="Print per-task progress to stderr.")
    parser.add_argument("--output", type=Path, default=Path("samples/prompt_concision_audit.md"))
    args = parser.parse_args()

    task_ids = _resolve_task_ids(args.tasks)
    coverage_rows = None
    if bool(args.query_id_coverage):
        rows, coverage_rows = _iter_query_id_prompt_rows(
            task_ids,
            samples_per_query_id=int(args.samples_per_query_id),
            max_attempts=int(args.max_attempts),
            max_total_samples_per_task=int(args.max_total_samples_per_task),
            workers=int(args.workers),
            progress=bool(args.progress),
        )
    else:
        rows = list(_iter_prompt_rows(task_ids, samples_per_task=args.samples_per_task, max_attempts=args.max_attempts))
    _write_markdown(
        rows,
        args.output,
        top_k=int(args.top_k),
        coverage_rows=coverage_rows,
        include_all_prompts=bool(args.include_all_prompts),
    )
    print(f"wrote {args.output} with {len(rows)} rendered prompts")


if __name__ == "__main__":
    main()
