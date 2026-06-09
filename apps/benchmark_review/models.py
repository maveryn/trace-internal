"""Data models for the benchmark-review app."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class SampleRecord:
    """One evaluated benchmark item."""

    uid: str
    benchmark: str
    display: str
    source_file: str
    source_line: int
    doc_id: str
    task_name: str
    prompt: str
    model_response: str
    target: Any
    extracted_answer: str
    score: float | None
    is_correct: bool | None
    metric_name: str
    metric_payload: Any
    image_path: str
    media_id: str
    image_exists: bool
    image_mtime_ns: int
    category: str = ""

    @property
    def status(self) -> str:
        if self.is_correct is True:
            return "correct"
        if self.is_correct is False:
            return "incorrect"
        return "unknown"

    @property
    def target_label(self) -> str:
        return _stringify(self.target)


@dataclass
class BenchmarkRecord:
    """One benchmark inside a model run."""

    benchmark: str
    display: str
    sample_count: int = 0
    correct_count: int = 0
    incorrect_count: int = 0
    unknown_count: int = 0
    image_count: int = 0
    preview_uid: str = ""
    source_files: List[str] = field(default_factory=list)
    result_files: List[str] = field(default_factory=list)
    run_summary_path: str = ""
    model_id: str = ""
    datetime: str = ""
    category_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def accuracy(self) -> float | None:
        denom = self.correct_count + self.incorrect_count
        if denom <= 0:
            return None
        return self.correct_count / denom


@dataclass
class BenchmarkIndex:
    """In-memory benchmark-review index."""

    run_root: Path
    repo_root: Path
    built_at: str
    model_id: str = ""
    run_id: str = ""
    benchmarks: Dict[str, BenchmarkRecord] = field(default_factory=dict)
    samples: Dict[str, SampleRecord] = field(default_factory=dict)
    samples_by_benchmark: Dict[str, List[str]] = field(default_factory=dict)
    media: Dict[str, Path] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def as_summary(self) -> Dict[str, Any]:
        return {
            "run_root": str(self.run_root),
            "repo_root": str(self.repo_root),
            "built_at": self.built_at,
            "model_id": self.model_id,
            "run_id": self.run_id,
            "benchmark_count": len(self.benchmarks),
            "sample_count": len(self.samples),
            "errors": list(self.errors),
            "benchmarks": {key: asdict(value) for key, value in sorted(self.benchmarks.items())},
        }


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)
