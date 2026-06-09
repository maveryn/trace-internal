#!/usr/bin/env python
"""Audit semantic-marker legibility metadata in generated TRACE task samples."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping


MARKER_PROMPT_TERMS = (
    "marked",
    "highlight",
    "highlighted",
    "outlined",
    "selected",
    "target cell",
    "target point",
    "target region",
)


def _iter_marker_legibility_blocks(value: Any, *, field_path: str = "render_spec") -> Iterable[tuple[str, Mapping[str, Any]]]:
    if not isinstance(value, Mapping):
        return
    block = value.get("marker_legibility")
    if isinstance(block, Mapping):
        yield f"{field_path}.marker_legibility", block
    for key, child in value.items():
        if key == "marker_legibility":
            continue
        if isinstance(child, Mapping):
            yield from _iter_marker_legibility_blocks(child, field_path=f"{field_path}.{key}")
        elif isinstance(child, list):
            for index, item in enumerate(child):
                if isinstance(item, Mapping):
                    yield from _iter_marker_legibility_blocks(item, field_path=f"{field_path}.{key}[{index}]")


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def runtime_marker_coverage_findings(
    *,
    sample_count: int,
    max_attempts: int,
    domain: str | None = None,
    require_prompt_markers: bool = False,
    fail_generation_errors: bool = False,
) -> list[str]:
    """Generate small samples and report marker-legibility coverage issues."""

    from trace.core.seed import hash64
    from trace.tasks import create_task
    from trace.tasks.registry import list_default_task_ids

    findings: list[str] = []
    task_ids = [
        task_id
        for task_id in list_default_task_ids()
        if domain is None or task_id.startswith(f"task_{domain}__")
    ]
    for task_id in task_ids:
        task = create_task(task_id)
        generated = False
        last_error: Exception | None = None
        for sample_index in range(max(1, int(sample_count))):
            instance_seed = int(hash64(0, f"{task_id}:marker_legibility_runtime", sample_index))
            try:
                output = task.generate(instance_seed, params={}, max_attempts=max(1, int(max_attempts)))
            except Exception as exc:  # pragma: no cover - audit reporting path.
                last_error = exc
                continue
            generated = True
            trace_payload = output.trace_payload if isinstance(output.trace_payload, Mapping) else {}
            render_spec = trace_payload.get("render_spec", {}) if isinstance(trace_payload, Mapping) else {}
            blocks = list(_iter_marker_legibility_blocks(render_spec))
            failure_count = sum(_to_int(block.get("failure_count")) for _, block in blocks)
            marker_count = sum(_to_int(block.get("drawn_marker_record_count")) for _, block in blocks)
            if failure_count > 0:
                findings.append(f"{task_id}: sample {sample_index} has marker_legibility failure_count={failure_count}")
            prompt = str(output.prompt or "").lower()
            if bool(require_prompt_markers) and marker_count <= 0 and any(term in prompt for term in MARKER_PROMPT_TERMS):
                findings.append(
                    f"{task_id}: sample {sample_index} prompt mentions a semantic marker but records no marker_legibility metadata"
                )
        if not generated and fail_generation_errors:
            findings.append(f"{task_id}: failed to generate runtime marker-legibility sample: {last_error}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--runtime-coverage", action="store_true", help="generate samples and inspect marker metadata")
    parser.add_argument("--runtime-domain", default="", help="optional active domain name for runtime coverage")
    parser.add_argument("--runtime-sample-count", type=int, default=1)
    parser.add_argument("--runtime-max-attempts", type=int, default=120)
    parser.add_argument(
        "--require-prompt-markers",
        action="store_true",
        help="fail when marker-like prompt wording appears without marker metadata",
    )
    parser.add_argument("--fail-generation-errors", action="store_true")
    parser.add_argument("--max-findings", type=int, default=80)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)

    if bool(args.runtime_coverage):
        findings = runtime_marker_coverage_findings(
            sample_count=max(1, int(args.runtime_sample_count)),
            max_attempts=max(1, int(args.runtime_max_attempts)),
            domain=str(args.runtime_domain).strip() or None,
            require_prompt_markers=bool(args.require_prompt_markers),
            fail_generation_errors=bool(args.fail_generation_errors),
        )
        if findings:
            print("Runtime marker-legibility coverage audit found issues.", file=sys.stderr)
            for finding in findings[: max(0, int(args.max_findings))]:
                print(finding, file=sys.stderr)
            remaining = len(findings) - max(0, int(args.max_findings))
            if remaining > 0:
                print(f"... {remaining} more findings omitted", file=sys.stderr)
            return 1
        print("marker-legibility runtime coverage audit passed")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
