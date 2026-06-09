#!/usr/bin/env python3
"""Prepare a dataset-only We-Math preview for the benchmark app."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = REPO_ROOT / "runs" / "external_benchmarks" / "qwen25vl7b" / "20260522T062435Z"
DEFAULT_DATASET_ROOT = REPO_ROOT / "external" / "We-Math"
DEFAULT_DATASET_ID = "We-Math/We-Math"
DEFAULT_BENCHMARK = "wemath"


def main() -> None:
    args = _parse_args()
    run_root = args.run_root.resolve()
    dataset_root = args.dataset_root.resolve()
    bench_dir = run_root / args.benchmark
    image_dir = bench_dir / "images"
    sample_file = bench_dir / f"{args.benchmark}_{args.split}_samples.jsonl"

    if bench_dir.exists() and not args.overwrite:
        raise SystemExit(f"{bench_dir} already exists; pass --overwrite to refresh it")

    dataset_rows = _load_rows(dataset_root=dataset_root, split=args.split)
    total_rows = len(dataset_rows)
    limit = total_rows if args.max_samples is None else min(int(args.max_samples), total_rows)

    zip_path = dataset_root / f"{args.split}.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"We-Math image zip not found: {zip_path}")

    bench_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path) as image_zip:
        available_names = set(image_zip.namelist())
        for index, row in enumerate(dataset_rows[:limit]):
            question = str(row.get("question") or "").strip()
            option_text = str(row.get("option") or "").strip()
            answer_letter = str(row.get("answer") or "").strip()
            image_path = str(row.get("image_path") or "").strip()
            if not question or not answer_letter or not image_path:
                continue

            image_member = _resolve_zip_member(image_path, available_names)
            if image_member is None:
                raise FileNotFoundError(f"image_path {image_path!r} not found in {zip_path}")

            suffix = Path(image_path).suffix.lower() or ".png"
            image_name = f"{args.benchmark}_{args.split}_{index:05d}{suffix}"
            output_image_path = image_dir / image_name
            output_image_path.write_bytes(image_zip.read(image_member))

            parsed_options = _parse_options(option_text)
            target = parsed_options.get(answer_letter, answer_letter)
            prompt = _format_prompt(question, option_text)
            knowledge_concepts = _split_knowledge_concepts(row.get("knowledge concept"))
            source = {
                "dataset_id": args.dataset_id,
                "dataset_root": _rel_to_repo(dataset_root),
                "split": args.split,
                "row_index": index,
                "original_id": row.get("ID"),
                "key": row.get("key"),
                "question_number": row.get("question number"),
                "knowledge_concept": row.get("knowledge concept"),
                "knowledge_concepts": knowledge_concepts,
                "knowledge_concept_description": row.get("knowledge concept description"),
                "image_path": image_path,
                "image_zip_member": image_member,
                "answer_letter": answer_letter,
                "answer_option": target,
                "options": parsed_options,
            }
            doc_id = f"{args.split}_{index:05d}"
            rows.append(
                {
                    "doc_id": doc_id,
                    "id": doc_id,
                    "input": prompt,
                    "question": question,
                    "target": target,
                    "answer": answer_letter,
                    "filtered_resps": [],
                    "prediction": "",
                    "response": "",
                    "image": f"images/{image_name}",
                    "doc_hash": _stable_hash(
                        json.dumps(
                            {
                                "q": question,
                                "option": option_text,
                                "answer": answer_letter,
                                "source": source,
                            },
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    ),
                    "preview_mode": "dataset_only",
                    "category": knowledge_concepts[0] if knowledge_concepts else "",
                    "source": source,
                }
            )

    with sample_file.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "benchmark": args.benchmark,
        "display": args.display,
        "model_id": "dataset-preview/no-model-response",
        "datetime": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "mode": "dataset_only_preview",
        "dataset_id": args.dataset_id,
        "dataset_root": _rel_to_repo(dataset_root),
        "dataset_split": args.split,
        "sample_file": sample_file.name,
        "sample_count": len(rows),
        "source_row_count": total_rows,
        "max_samples": args.max_samples,
        "image_source_zip": _rel_to_repo(zip_path),
        "license": "cc-by-nc-4.0",
    }
    (bench_dir / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (bench_dir / "dataset_preview_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {len(rows)} samples")
    print(f"benchmark: {bench_dir}")
    print(f"samples: {sample_file}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET_ID)
    parser.add_argument("--split", default="testmini")
    parser.add_argument("--benchmark", default=DEFAULT_BENCHMARK)
    parser.add_argument("--display", default="We-Math")
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def _load_rows(*, dataset_root: Path, split: str) -> list[dict[str, Any]]:
    json_path = dataset_root / f"{split}.json"
    if not json_path.exists():
        raise FileNotFoundError(f"We-Math split JSON not found: {json_path}")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TypeError(f"expected list payload in {json_path}")
    return [dict(row) for row in payload if isinstance(row, dict)]


def _resolve_zip_member(image_path: str, available_names: set[str]) -> str | None:
    normalized = str(image_path).lstrip("/").replace("\\", "/")
    candidates = (
        normalized,
        f"data/{normalized}",
    )
    for candidate in candidates:
        if candidate in available_names:
            return candidate
    return None


def _parse_options(option_text: str) -> dict[str, str]:
    options: dict[str, str] = {}
    text = str(option_text or "").strip()
    if not text:
        return options
    # We-Math options are usually "A. ...;B. ...; ...", sometimes with
    # inconsistent spacing before the next label.
    matches = list(re.finditer(r"(?:^|;)\s*([A-E])\.\s*", text))
    for index, match in enumerate(matches):
        label = str(match.group(1))
        start = match.start(1)
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        value = text[start:end].strip().rstrip(";").strip()
        if value:
            options[label] = value
    return options


def _split_knowledge_concepts(value: Any) -> list[str]:
    return [part.strip() for part in str(value or "").split(";") if part.strip()]


def _format_prompt(question: str, option_text: str) -> str:
    question = str(question or "").strip()
    option_text = str(option_text or "").strip()
    if not option_text:
        return question
    return f"{question}\n\nOptions:\n{option_text}"


def _stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rel_to_repo(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
