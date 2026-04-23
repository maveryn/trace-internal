from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable


def trace_validation_name_from_source(src: str) -> str:
    """
    Build a stable benchmark name from a local parquet path or HF-style source.
    """
    if "@" in src and not os.path.exists(src):
        repo, split = src.split("@", 1)
        return f"{repo.split('/')[-1]}@{split}"

    parts = src.split("/")
    if len(parts) >= 2 and not src.endswith(".parquet") and not os.path.exists(src):
        repo = parts[-2]
        split = parts[-1]
        return f"{repo}@{split}"

    stem = Path(src).stem
    return stem or "val"


def normalize_validation_sources(val_files) -> list[str]:
    if val_files is None:
        return []
    if isinstance(val_files, str):
        return [val_files]
    return [str(path) for path in list(val_files)]


def filter_trace_validation_sources(
    val_files,
    excluded_benchmarks: Iterable[str] | None = None,
) -> list[str]:
    excluded = {str(name).strip().lower() for name in (excluded_benchmarks or []) if str(name).strip()}
    sources = normalize_validation_sources(val_files)
    if not excluded:
        return sources

    filtered: list[str] = []
    for src in sources:
        benchmark_name = trace_validation_name_from_source(src).strip().lower()
        benchmark_stem = Path(src).stem.strip().lower()
        if benchmark_name in excluded or benchmark_stem in excluded:
            continue
        filtered.append(src)
    return filtered
