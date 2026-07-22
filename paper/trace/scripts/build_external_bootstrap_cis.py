#!/usr/bin/env python3
"""Compute paired item-cluster bootstrap intervals for Base versus Trace."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd
from huggingface_hub import HfApi, hf_hub_download
from tqdm.auto import tqdm


REPO_ROOT = Path(__file__).resolve().parents[3]
PAPER_ROOT = REPO_ROOT / "paper" / "trace"
SUITE_PATH = REPO_ROOT / "evaluation" / "trace_eval" / "suite.v1.json"

HF_REPO_ID = "maveryn/trace-eval-runs"
HF_REVISION = "4178a839b689babe16f8ac36f0de7b1b2c5ef36c"
RUNS = {
    "3B": {
        "run_id": "qwen2.5-vl-3b-comparison-temp06-seeds42-44-v1",
        "base_model_id": "qwen2.5-vl-3b-base",
        "trace_model_id": "trace-qwen2.5-vl-3b",
    },
    "7B": {
        "run_id": "qwen2.5-vl-7b-comparison-temp06-seeds42-44-v1",
        "base_model_id": "qwen2.5-vl-7b-base",
        "trace_model_id": "trace-qwen2.5-vl-7b",
    },
}
SEEDS = (42, 43, 44)
EXPECTED_BENCHMARKS = 24
AGGREGATE_ONLY_BENCHMARKS = frozenset(
    {
        "chartqapro",
        "countbenchqa",
        "mathvision",
        "mathvista",
        "puzzlevqa",
        "tablevqabench",
        "visualpuzzles",
    }
)
COMPOSITE_ROW_BENCHMARKS = frozenset({"wemath"})
PAPER_BENCHMARK_DISPLAY_NAMES = {"spatialvizbench_cot": "SpatialVizBench"}
CATEGORY_TABLE_STYLES = {
    "Charts & Tables": "TraceChartsBand",
    "Visual Math": "TraceMathBand",
    "Science & General": "TraceScienceBand",
    "Spatial Reasoning": "TraceSpatialBand",
    "Perception & Counting": "TracePerceptionBand",
    "Puzzles & Logic": "TracePuzzlesBand",
}
VLMEVAL_ROOT = Path(
    os.environ.get("VLMEVALKIT_ROOT", str(REPO_ROOT.parent / "VLMEvalKit"))
).resolve()
_SOURCE_CACHE: dict[str, pd.DataFrame] = {}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=42)
    parser.add_argument("--download-workers", type=int, default=12)
    parser.add_argument("--bootstrap-chunk-size", type=int, default=256)
    parser.add_argument(
        "--token-file",
        type=Path,
        default=REPO_ROOT / "hf-token.txt",
        help="Optional Hugging Face token file; never recorded in provenance.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PAPER_ROOT / "data" / "external_benchmark_bootstrap_cis.json",
    )
    parser.add_argument(
        "--provenance-output",
        type=Path,
        default=PAPER_ROOT / "provenance" / "external_benchmark_bootstrap_cis.json",
    )
    parser.add_argument(
        "--table-output",
        type=Path,
        default=PAPER_ROOT / "tables" / "external_bootstrap_cis.tex",
    )
    args = parser.parse_args()
    if args.bootstrap_replicates < 1_000:
        parser.error("--bootstrap-replicates must be at least 1000")
    if args.download_workers < 1 or args.bootstrap_chunk_size < 1:
        parser.error("worker and chunk counts must be positive")
    return args


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scorer_source_hashes() -> dict[str, str]:
    paths = (
        VLMEVAL_ROOT / "scripts" / "batched_chartqapro_vllm.py",
        VLMEVAL_ROOT / "vlmeval" / "dataset" / "image_mcq.py",
        VLMEVAL_ROOT / "vlmeval" / "dataset" / "image_vqa.py",
        VLMEVAL_ROOT / "vlmeval" / "dataset" / "utils" / "chartqapro.py",
        VLMEVAL_ROOT / "vlmeval" / "dataset" / "utils" / "mathv.py",
        VLMEVAL_ROOT / "vlmeval" / "dataset" / "utils" / "mathvista.py",
        VLMEVAL_ROOT / "vlmeval" / "dataset" / "utils" / "puzzlevqa.py",
        VLMEVAL_ROOT / "vlmeval" / "dataset" / "utils" / "tablevqabench.py",
        VLMEVAL_ROOT / "vlmeval" / "dataset" / "utils" / "visualpuzzles.py",
    )
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing pinned scorer sources: {missing}")
    return {str(path.relative_to(VLMEVAL_ROOT)): _sha256(path) for path in paths}


def _token(token_file: Path) -> str | None:
    environment_token = os.environ.get("HF_TOKEN")
    if environment_token:
        return environment_token.strip()
    if token_file.is_file():
        return token_file.read_text(encoding="utf-8").strip()
    return None


def _score_paths(token: str | None) -> dict[tuple[str, str, int, str], str]:
    files = HfApi(token=token).list_repo_files(
        repo_id=HF_REPO_ID,
        repo_type="dataset",
        revision=HF_REVISION,
    )
    selected: dict[tuple[str, str, int, str], str] = {}
    for scale, spec in RUNS.items():
        run_id = str(spec["run_id"])
        prefix = f"runs/{run_id}/data/scores/"
        model_ids = {str(spec["base_model_id"]), str(spec["trace_model_id"])}
        for path in files:
            if not path.startswith(prefix) or not path.endswith(".parquet"):
                continue
            fields: dict[str, str] = {}
            for component in Path(path).parts:
                if "=" in component:
                    key, value = component.split("=", maxsplit=1)
                    fields[key] = value
            model_id = fields.get("model")
            seed_raw = fields.get("seed")
            benchmark_id = fields.get("benchmark")
            if model_id not in model_ids or seed_raw is None or benchmark_id is None:
                continue
            seed = int(seed_raw)
            if seed not in SEEDS:
                continue
            key = (scale, model_id, seed, benchmark_id)
            if key in selected:
                raise RuntimeError(f"duplicate score part for {key}")
            selected[key] = path

    expected_parts = len(RUNS) * 2 * len(SEEDS) * EXPECTED_BENCHMARKS
    if len(selected) != expected_parts:
        raise RuntimeError(
            f"expected {expected_parts} Base/Trace score parts, found {len(selected)}"
        )
    for scale, spec in RUNS.items():
        model_ids = (str(spec["base_model_id"]), str(spec["trace_model_id"]))
        benchmark_sets = [
            {
                benchmark
                for candidate_scale, candidate_model, seed, benchmark in selected
                if candidate_scale == scale and candidate_model == model_id and seed in SEEDS
            }
            for model_id in model_ids
        ]
        if (
            benchmark_sets[0] != benchmark_sets[1]
            or len(benchmark_sets[0]) != EXPECTED_BENCHMARKS
        ):
            raise RuntimeError(f"benchmark inventory drift for {scale}")
    return selected


def _extraction_paths(token: str | None) -> dict[tuple[str, str, int, str], str]:
    files = HfApi(token=token).list_repo_files(
        repo_id=HF_REPO_ID,
        repo_type="dataset",
        revision=HF_REVISION,
    )
    selected: dict[tuple[str, str, int, str], str] = {}
    for scale, spec in RUNS.items():
        run_id = str(spec["run_id"])
        prefix = f"runs/{run_id}/data/extractions/"
        model_ids = {str(spec["base_model_id"]), str(spec["trace_model_id"])}
        for path in files:
            if not path.startswith(prefix) or not path.endswith(".parquet"):
                continue
            fields: dict[str, str] = {}
            for component in Path(path).parts:
                if "=" in component:
                    key, value = component.split("=", maxsplit=1)
                    fields[key] = value
            model_id = fields.get("model")
            seed_raw = fields.get("seed")
            benchmark_id = fields.get("benchmark")
            if (
                model_id not in model_ids
                or seed_raw is None
                or benchmark_id not in AGGREGATE_ONLY_BENCHMARKS
            ):
                continue
            seed = int(seed_raw)
            if seed not in SEEDS:
                continue
            key = (scale, model_id, seed, benchmark_id)
            if key in selected:
                raise RuntimeError(f"duplicate extraction part for {key}")
            selected[key] = path

    expected_parts = len(RUNS) * 2 * len(SEEDS) * len(AGGREGATE_ONLY_BENCHMARKS)
    if len(selected) != expected_parts:
        raise RuntimeError(
            f"expected {expected_parts} extraction parts, found {len(selected)}"
        )
    return selected


def _download_parts(
    remote_paths: Mapping[tuple[str, str, int, str], str],
    *,
    token: str | None,
    workers: int,
    description: str,
) -> dict[tuple[str, str, int, str], Path]:
    def download(item: tuple[tuple[str, str, int, str], str]) -> tuple[tuple[str, str, int, str], Path]:
        key, remote_path = item
        local = hf_hub_download(
            repo_id=HF_REPO_ID,
            repo_type="dataset",
            revision=HF_REVISION,
            filename=remote_path,
            token=token,
        )
        return key, Path(local)

    downloaded: dict[tuple[str, str, int, str], Path] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        iterator = executor.map(download, sorted(remote_paths.items()))
        for key, path in tqdm(
            iterator,
            total=len(remote_paths),
            desc=description,
            unit="file",
        ):
            downloaded[key] = path
    return downloaded


def _load_row_scores(
    path: Path,
    *,
    expected_model: str,
    expected_seed: int,
    expected_benchmark: str,
    validate_aggregate: bool = True,
) -> pd.DataFrame:
    frame = pd.read_parquet(
        path,
        columns=[
            "model_id",
            "seed",
            "benchmark_id",
            "score_scope",
            "source_ordinal",
            "source_row_sha256",
            "score_unit",
            "score_value",
            "excluded",
        ],
    )
    aggregate = frame.loc[frame["score_scope"] == "aggregate"]
    rows = frame.loc[(frame["score_scope"] == "row") & ~frame["excluded"]].copy()
    if len(aggregate) != 1 or rows.empty:
        raise RuntimeError(f"invalid score-scope rows in {path}")
    if set(rows["model_id"]) != {expected_model}:
        raise RuntimeError(f"model identity drift in {path}")
    if set(rows["seed"].astype(int)) != {expected_seed}:
        raise RuntimeError(f"seed identity drift in {path}")
    if set(rows["benchmark_id"]) != {expected_benchmark}:
        raise RuntimeError(f"benchmark identity drift in {path}")
    if set(rows["score_unit"]) != {"fraction"}:
        raise RuntimeError(f"row scores are not fractions in {path}")
    if rows["source_ordinal"].isna().any() or rows["source_row_sha256"].isna().any():
        raise RuntimeError(f"score rows have missing source identity in {path}")
    rows["source_ordinal"] = rows["source_ordinal"].astype(int)
    if rows["source_ordinal"].duplicated().any():
        raise RuntimeError(f"duplicate source ordinal in {path}")
    values = rows["score_value"].astype(float)
    if not np.isfinite(values).all():
        raise RuntimeError(f"non-finite score value in {path}")
    if validate_aggregate:
        canonical = float(aggregate.iloc[0]["score_value"])
        recovered = 100.0 * float(values.mean())
        if not math.isclose(recovered, canonical, rel_tol=0.0, abs_tol=1e-6):
            raise RuntimeError(
                f"row-score aggregate mismatch for {expected_model}/{expected_seed}/"
                f"{expected_benchmark}: {recovered} != {canonical}"
            )
    return rows.set_index("source_ordinal")[["source_row_sha256", "score_value"]].sort_index()


def _load_wemath_group_scores(
    path: Path,
    *,
    expected_model: str,
    expected_seed: int,
) -> pd.DataFrame:
    rows = _load_row_scores(
        path,
        expected_model=expected_model,
        expected_seed=expected_seed,
        expected_benchmark="wemath",
        validate_aggregate=False,
    )
    source = _source_frame("wemath")
    if len(source) != len(rows) or not source.index.equals(rows.index):
        raise RuntimeError(f"WeMath source alignment drift in {path}")

    scored = source[["ID", "key"]].copy()
    scored["score_value"] = rows["score_value"].to_numpy(float)
    scored["source_row_sha256"] = rows["source_row_sha256"].to_numpy(str)
    grouped: list[dict[str, Any]] = []
    for group_id, group in scored.groupby("ID", sort=False):
        is_multi = group["key"].map(str).str.endswith("_multi")
        multi = group.loc[is_multi, "score_value"]
        singles = group.loc[~is_multi, "score_value"]
        if len(multi) != 1 or len(singles) not in {2, 3}:
            raise RuntimeError(f"invalid WeMath group {group_id!r} in {path}")
        all_single_correct = bool((singles == 1.0).all())
        multi_correct = bool(multi.iloc[0] == 1.0)
        strict_score = (
            1.0
            if all_single_correct and multi_correct
            else 0.5
            if all_single_correct
            else 0.0
        )
        component_hashes = "\n".join(group["source_row_sha256"].map(str))
        grouped.append(
            {
                "source_row_sha256": hashlib.sha256(
                    component_hashes.encode("utf-8")
                ).hexdigest(),
                "score_value": strict_score,
            }
        )

    result = pd.DataFrame(grouped)
    result.index = pd.Index(np.arange(len(result), dtype=int), name="source_ordinal")
    canonical = _canonical_aggregate(path)
    recovered = 100.0 * float(result["score_value"].mean())
    if round(recovered, 2) != canonical:
        raise RuntimeError(
            f"WeMath strict-score aggregate mismatch for {expected_model}/{expected_seed}: "
            f"{recovered} != {canonical}"
        )
    return result


def _canonical_aggregate(path: Path) -> float:
    frame = pd.read_parquet(
        path,
        columns=["score_scope", "score_unit", "score_value", "excluded"],
    )
    aggregate = frame.loc[(frame["score_scope"] == "aggregate") & ~frame["excluded"]]
    if len(aggregate) != 1 or aggregate.iloc[0]["score_unit"] != "percent":
        raise RuntimeError(f"invalid canonical aggregate in {path}")
    value = float(aggregate.iloc[0]["score_value"])
    if not math.isfinite(value):
        raise RuntimeError(f"non-finite canonical aggregate in {path}")
    return value


def _source_frame(benchmark: str) -> pd.DataFrame:
    cached = _SOURCE_CACHE.get(benchmark)
    if cached is not None:
        return cached
    if not VLMEVAL_ROOT.is_dir():
        raise RuntimeError(
            f"VLMEvalKit checkout not found at {VLMEVAL_ROOT}; set VLMEVALKIT_ROOT"
        )
    for path in (REPO_ROOT, VLMEVAL_ROOT):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from scripts.benchmark_queue_lib import build_vlmeval_dataset, spec_by_key

    required = {
        "chartqapro": ["index", "answer", "question_type", "year"],
        "countbenchqa": ["index", "answer"],
        "mathvision": ["index", "choices", "answer", "category"],
        "mathvista": [
            "index",
            "question_type",
            "answer_type",
            "answer",
            "answer_option",
            "choices",
        ],
        "puzzlevqa": ["index", "options", "answer"],
        "tablevqabench": ["index", "answer", "split"],
        "visualpuzzles": ["index", "answer"],
        "wemath": ["index", "ID", "key"],
    }[benchmark]
    dataset = build_vlmeval_dataset(spec_by_key(benchmark))
    source = dataset.data.reset_index(drop=True)
    missing = sorted(set(required) - set(source.columns))
    if missing:
        raise RuntimeError(f"{benchmark} source data lacks columns: {missing}")
    filtered = source[required].copy()
    filtered.index = pd.Index(np.arange(len(filtered), dtype=int), name="source_ordinal")
    _SOURCE_CACHE[benchmark] = filtered
    return filtered


def _load_extractions(
    path: Path,
    *,
    expected_model: str,
    expected_seed: int,
    expected_benchmark: str,
) -> pd.DataFrame:
    frame = pd.read_parquet(
        path,
        columns=[
            "model_id",
            "seed",
            "benchmark_id",
            "source_index",
            "source_ordinal",
            "source_row_sha256",
            "extraction_status",
            "extraction_value_json",
        ],
    )
    if frame.empty:
        raise RuntimeError(f"empty extraction ledger in {path}")
    if set(frame["model_id"]) != {expected_model}:
        raise RuntimeError(f"model identity drift in {path}")
    if set(frame["seed"].astype(int)) != {expected_seed}:
        raise RuntimeError(f"seed identity drift in {path}")
    if set(frame["benchmark_id"]) != {expected_benchmark}:
        raise RuntimeError(f"benchmark identity drift in {path}")
    statuses = set(frame["extraction_status"])
    if not statuses <= {"resolved", "invalid"}:
        raise RuntimeError(f"unsupported extraction statuses {sorted(statuses)} in {path}")
    invalid = frame["extraction_status"] == "invalid"
    invalid_values = frame.loc[invalid, "extraction_value_json"].dropna().map(json.loads)
    if invalid_values.map(lambda value: value is not None).any():
        raise RuntimeError(f"invalid extraction rows unexpectedly retain values in {path}")
    if frame["source_ordinal"].isna().any() or frame["source_row_sha256"].isna().any():
        raise RuntimeError(f"extraction rows have missing source identity in {path}")
    frame["source_ordinal"] = frame["source_ordinal"].astype(int)
    frame = frame.sort_values("source_ordinal").set_index("source_ordinal")
    expected = np.arange(len(frame), dtype=int)
    if not np.array_equal(frame.index.to_numpy(), expected):
        raise RuntimeError(f"non-contiguous source ordinals in {path}")
    try:
        frame["prediction"] = frame["extraction_value_json"].map(
            lambda value: None if pd.isna(value) else json.loads(value)
        ).map(lambda value: "__missing_prediction__" if value is None else value)
    except Exception as exc:
        raise RuntimeError(f"invalid extraction JSON in {path}") from exc
    return frame


def _validate_source_alignment(source: pd.DataFrame, extractions: pd.DataFrame, *, benchmark: str) -> None:
    if len(source) != len(extractions) or not source.index.equals(extractions.index):
        raise RuntimeError(f"source row-count or ordinal drift for {benchmark}")
    source_indices = source["index"].map(str).to_numpy()
    extraction_indices = extractions["source_index"].map(str).to_numpy()
    if not np.array_equal(source_indices, extraction_indices):
        raise RuntimeError(f"source index drift for {benchmark}")


def _score_tablevqabench(source: pd.DataFrame, predictions: pd.Series) -> pd.DataFrame:
    for path in (VLMEVAL_ROOT,):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    from vlmeval.dataset.utils.tablevqabench import (
        evaluate_fintabnet,
        evaluate_tabfact,
        evaluate_wtq,
    )

    records = source.copy()
    records["prediction"] = predictions.map(str)
    scored: list[dict[str, Any]] = []
    for split, group in records.groupby("split", sort=False):
        rows = group.reset_index().to_dict(orient="records")
        if split == "fintabnetqa":
            evaluate_fintabnet(rows, ["accuracy"])
        elif split == "vtabfact":
            evaluate_tabfact(rows, ["accuracy"])
        elif split in {"vwtq", "vwtq_syn"}:
            evaluate_wtq(rows, ["accuracy"])
        else:
            raise RuntimeError(f"unknown TableVQABench split: {split}")
        scored.extend(rows)

    scored_frame = pd.DataFrame(scored).set_index("source_ordinal").sort_index()
    primary = scored_frame["scores"].map(
        lambda values: 0.0 if values.get("accuracy") is None else float(values["accuracy"])
    )
    exact = scored_frame.apply(
        lambda row: float(row["scores"].get("exact_score", 0.0))
        if row["split"] == "fintabnetqa"
        else np.nan,
        axis=1,
    )
    return pd.DataFrame(
        {
            "score_value": primary,
            "score_aux": exact,
            "stratum": scored_frame["split"].map(str),
        },
        index=scored_frame.index,
    )


def _score_reconstructed_rows(
    benchmark: str,
    source: pd.DataFrame,
    extractions: pd.DataFrame,
) -> pd.DataFrame:
    predictions = extractions["prediction"]
    if benchmark == "chartqapro":
        scripts_root = VLMEVAL_ROOT / "scripts"
        if str(scripts_root) not in sys.path:
            sys.path.insert(0, str(scripts_root))
        import batched_chartqapro_vllm as chartqapro

        values: list[float] = []
        for ordinal, row in source.iterrows():
            one = {
                "answer": row["answer"],
                "question_type": row["question_type"],
                "year": row["year"],
                "prediction": str(predictions.loc[ordinal]),
            }
            values.append(float(chartqapro.evaluate_rows([one], "prediction")["Overall"]))
    elif benchmark == "countbenchqa":
        values = [
            float(str(row["answer"]) in str(predictions.loc[ordinal]))
            for ordinal, row in source.iterrows()
        ]
    elif benchmark == "mathvision":
        from vlmeval.dataset.utils import mathv

        mathv.is_equal = getattr(mathv.is_equal, "__wrapped__", mathv.is_equal)

        values = []
        for ordinal, row in source.iterrows():
            item = row.to_dict()
            item["res"] = predictions.loc[ordinal]
            values.append(float(bool(mathv.post_check(item, prefetch=False))))
    elif benchmark == "mathvista":
        from vlmeval.dataset.utils.mathvista import post_check

        values = []
        for ordinal, row in source.iterrows():
            item = row.to_dict()
            item["res"] = predictions.loc[ordinal]
            values.append(float(bool(post_check(item, prefetch=False))))
    elif benchmark == "puzzlevqa":
        from vlmeval.dataset.utils.puzzlevqa import (
            extract_answer,
            extract_lang_content,
            extract_last_boxed_content,
            to_choice_letter,
        )

        values = []
        for ordinal, row in source.iterrows():
            options = row["options"]
            if isinstance(options, str):
                options = ast.literal_eval(options)
            raw_prediction = str(predictions.loc[ordinal])
            predicted = extract_answer(raw_prediction)
            if predicted == "Z":
                predicted = extract_lang_content(extract_last_boxed_content(raw_prediction))
            predicted = predicted.lower()
            target = to_choice_letter(options, row["answer"]).lower()
            values.append(float(predicted == target))
    elif benchmark == "visualpuzzles":
        from vlmeval.dataset.utils.visualpuzzles import (
            extract_answer,
            extract_lang_content,
            extract_last_boxed_content,
        )

        values = []
        raw_values = []
        for ordinal, row in source.iterrows():
            raw_prediction = str(predictions.loc[ordinal])
            raw_predicted = extract_answer(raw_prediction)
            predicted = raw_predicted
            if raw_predicted == "Z":
                predicted = extract_lang_content(extract_last_boxed_content(raw_prediction))
            raw_values.append(float(raw_predicted.lower() == str(row["answer"]).lower()))
            values.append(float(predicted.lower() == str(row["answer"]).lower()))
    elif benchmark == "tablevqabench":
        result = _score_tablevqabench(source, predictions)
        result.insert(0, "source_row_sha256", extractions["source_row_sha256"])
        return result
    else:
        raise RuntimeError(f"no aggregate-score reconstruction for {benchmark}")

    result = pd.DataFrame(
        {
            "source_row_sha256": extractions["source_row_sha256"],
            "score_value": np.asarray(values, dtype=float),
        },
        index=source.index,
    )
    if benchmark == "visualpuzzles":
        result["score_raw_parser"] = np.asarray(raw_values, dtype=float)
    return result


def _tablevqabench_metric(frame: pd.DataFrame) -> float:
    values: list[float] = []
    for split in ("fintabnetqa", "vtabfact", "vwtq", "vwtq_syn"):
        group = frame.loc[frame["stratum"] == split]
        if group.empty:
            raise RuntimeError(f"missing TableVQABench split: {split}")
        values.append(float(group["score_value"].mean()))
        if split == "fintabnetqa":
            values.append(float(group["score_aux"].mean()))
    return float(np.mean(values))


def _load_reconstructed_scores(
    extraction_path: Path,
    score_path: Path,
    *,
    expected_model: str,
    expected_seed: int,
    expected_benchmark: str,
) -> pd.DataFrame:
    source = _source_frame(expected_benchmark)
    extractions = _load_extractions(
        extraction_path,
        expected_model=expected_model,
        expected_seed=expected_seed,
        expected_benchmark=expected_benchmark,
    )
    _validate_source_alignment(source, extractions, benchmark=expected_benchmark)
    rows = _score_reconstructed_rows(expected_benchmark, source, extractions)
    point = (
        _tablevqabench_metric(rows)
        if expected_benchmark == "tablevqabench"
        else float(rows["score_value"].mean())
    )
    canonical = _canonical_aggregate(score_path)
    if (
        expected_benchmark == "visualpuzzles"
        and not math.isclose(100.0 * point, canonical, rel_tol=0.0, abs_tol=1e-6)
    ):
        raw_point = float(rows["score_raw_parser"].mean())
        if math.isclose(100.0 * raw_point, canonical, rel_tol=0.0, abs_tol=1e-6):
            rows["score_value"] = rows["score_raw_parser"]
            point = raw_point
    adjustment = 0.0
    if not math.isclose(100.0 * point, canonical, rel_tol=0.0, abs_tol=1e-6):
        adjustment = canonical / 100.0 - point
        one_item_tolerance = 1.01 / len(rows)
        if expected_benchmark == "tablevqabench" or abs(adjustment) > one_item_tolerance:
            raise RuntimeError(
                f"reconstructed aggregate mismatch for {expected_model}/{expected_seed}/"
                f"{expected_benchmark}: {100.0 * point} != {canonical}"
            )
        # Some archived official scorers retain only the aggregate after an
        # Excel round trip. A one-item-equivalent discrepancy can result from
        # type inference in that round trip. Center the recovered item vector
        # on the immutable official aggregate while preserving item variation.
        rows["score_value"] = rows["score_value"] + adjustment
        point = float(rows["score_value"].mean())
    if not math.isclose(100.0 * point, canonical, rel_tol=0.0, abs_tol=1e-6):
        raise RuntimeError(
            f"reconstructed aggregate mismatch for {expected_model}/{expected_seed}/"
            f"{expected_benchmark}: {100.0 * point} != {canonical}"
        )
    rows = rows.sort_index()
    rows.attrs["aggregate_center_adjustment"] = float(adjustment)
    return rows


def _bootstrap_interval(values: np.ndarray, *, replicates: int, seed: int, chunk_size: int) -> tuple[float, float]:
    if values.ndim != 1 or values.size < 2:
        raise ValueError("bootstrap values must be a one-dimensional sample")
    rng = np.random.default_rng(seed)
    draws = np.empty(replicates, dtype=np.float64)
    for start in range(0, replicates, chunk_size):
        stop = min(start + chunk_size, replicates)
        indices = rng.integers(0, values.size, size=(stop - start, values.size))
        draws[start:stop] = values[indices].mean(axis=1)
    lower, upper = np.percentile(draws, (2.5, 97.5))
    return float(lower), float(upper)


def _bootstrap_tablevqabench(
    base: pd.DataFrame,
    trace: pd.DataFrame,
    *,
    replicates: int,
    seed: int,
    chunk_size: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    base_draws = np.empty(replicates, dtype=np.float64)
    trace_draws = np.empty(replicates, dtype=np.float64)
    strata = ("fintabnetqa", "vtabfact", "vwtq", "vwtq_syn")
    for start in range(0, replicates, chunk_size):
        stop = min(start + chunk_size, replicates)
        count = stop - start
        base_components: list[np.ndarray] = []
        trace_components: list[np.ndarray] = []
        for stratum in strata:
            ordinals = base.index[base["stratum"] == stratum].to_numpy(int)
            if not np.array_equal(ordinals, trace.index[trace["stratum"] == stratum].to_numpy(int)):
                raise RuntimeError(f"TableVQABench stratum mismatch for {stratum}")
            sampled = rng.integers(0, len(ordinals), size=(count, len(ordinals)))
            base_primary = base.loc[ordinals, "score_value"].to_numpy(float)
            trace_primary = trace.loc[ordinals, "score_value"].to_numpy(float)
            base_components.append(base_primary[sampled].mean(axis=1))
            trace_components.append(trace_primary[sampled].mean(axis=1))
            if stratum == "fintabnetqa":
                base_aux = base.loc[ordinals, "score_aux"].to_numpy(float)
                trace_aux = trace.loc[ordinals, "score_aux"].to_numpy(float)
                base_components.append(base_aux[sampled].mean(axis=1))
                trace_components.append(trace_aux[sampled].mean(axis=1))
        base_draws[start:stop] = np.mean(base_components, axis=0)
        trace_draws[start:stop] = np.mean(trace_components, axis=0)

    delta_draws = trace_draws - base_draws
    return {
        "base_point": _tablevqabench_metric(base),
        "trace_point": _tablevqabench_metric(trace),
        "base_ci": tuple(float(x) for x in np.percentile(base_draws, (2.5, 97.5))),
        "trace_ci": tuple(float(x) for x in np.percentile(trace_draws, (2.5, 97.5))),
        "delta_ci": tuple(float(x) for x in np.percentile(delta_draws, (2.5, 97.5))),
    }


def _scale_benchmark_result(
    *,
    scale: str,
    benchmark: str,
    paths: Mapping[tuple[str, str, int, str], Path],
    extraction_paths: Mapping[tuple[str, str, int, str], Path],
    replicates: int,
    bootstrap_seed: int,
    chunk_size: int,
) -> dict[str, Any]:
    spec = RUNS[scale]
    base_id = str(spec["base_model_id"])
    trace_id = str(spec["trace_model_id"])
    canonical_points = {
        model_id: float(
            np.mean(
                [
                    _canonical_aggregate(
                        paths[(scale, model_id, seed, benchmark)]
                    )
                    for seed in SEEDS
                ]
            )
        )
        for model_id in (base_id, trace_id)
    }
    model_seed_frames: dict[tuple[str, int], pd.DataFrame] = {}
    for model_id in (base_id, trace_id):
        for seed in SEEDS:
            if benchmark in COMPOSITE_ROW_BENCHMARKS:
                model_seed_frames[(model_id, seed)] = _load_wemath_group_scores(
                    paths[(scale, model_id, seed, benchmark)],
                    expected_model=model_id,
                    expected_seed=seed,
                )
            elif benchmark in AGGREGATE_ONLY_BENCHMARKS:
                model_seed_frames[(model_id, seed)] = _load_reconstructed_scores(
                    extraction_paths[(scale, model_id, seed, benchmark)],
                    paths[(scale, model_id, seed, benchmark)],
                    expected_model=model_id,
                    expected_seed=seed,
                    expected_benchmark=benchmark,
                )
            else:
                model_seed_frames[(model_id, seed)] = _load_row_scores(
                    paths[(scale, model_id, seed, benchmark)],
                    expected_model=model_id,
                    expected_seed=seed,
                    expected_benchmark=benchmark,
                )

    reference = model_seed_frames[(base_id, SEEDS[0])]
    reference_index = reference.index
    reference_hashes = reference["source_row_sha256"]
    for key, frame in model_seed_frames.items():
        if not frame.index.equals(reference_index):
            raise RuntimeError(f"source ordinal mismatch for {scale}/{benchmark}/{key}")
        if not frame["source_row_sha256"].equals(reference_hashes):
            raise RuntimeError(f"source hash mismatch for {scale}/{benchmark}/{key}")

    base_values = np.column_stack(
        [model_seed_frames[(base_id, seed)]["score_value"].to_numpy(float) for seed in SEEDS]
    ).mean(axis=1)
    trace_values = np.column_stack(
        [model_seed_frames[(trace_id, seed)]["score_value"].to_numpy(float) for seed in SEEDS]
    ).mean(axis=1)
    scale_seed = int.from_bytes(
        hashlib.sha256(f"{bootstrap_seed}:{scale}:{benchmark}".encode("utf-8")).digest()[:8],
        byteorder="big",
    )
    if benchmark == "tablevqabench":
        base_table = pd.DataFrame(
            {
                "score_value": np.column_stack(
                    [model_seed_frames[(base_id, seed)]["score_value"] for seed in SEEDS]
                ).mean(axis=1),
                "score_aux": np.column_stack(
                    [model_seed_frames[(base_id, seed)]["score_aux"] for seed in SEEDS]
                ).mean(axis=1),
                "stratum": reference["stratum"],
            },
            index=reference_index,
        )
        trace_table = pd.DataFrame(
            {
                "score_value": np.column_stack(
                    [model_seed_frames[(trace_id, seed)]["score_value"] for seed in SEEDS]
                ).mean(axis=1),
                "score_aux": np.column_stack(
                    [model_seed_frames[(trace_id, seed)]["score_aux"] for seed in SEEDS]
                ).mean(axis=1),
                "stratum": reference["stratum"],
            },
            index=reference_index,
        )
        table_result = _bootstrap_tablevqabench(
            base_table,
            trace_table,
            replicates=replicates,
            seed=scale_seed,
            chunk_size=chunk_size,
        )
        base_point = float(table_result["base_point"])
        trace_point = float(table_result["trace_point"])
        base_ci = table_result["base_ci"]
        trace_ci = table_result["trace_ci"]
        delta_ci = table_result["delta_ci"]
    else:
        delta_values = trace_values - base_values
        base_point = float(base_values.mean())
        trace_point = float(trace_values.mean())
        base_ci = _bootstrap_interval(
            base_values,
            replicates=replicates,
            seed=scale_seed,
            chunk_size=chunk_size,
        )
        trace_ci = _bootstrap_interval(
            trace_values,
            replicates=replicates,
            seed=scale_seed + 1,
            chunk_size=chunk_size,
        )
        delta_ci = _bootstrap_interval(
            delta_values,
            replicates=replicates,
            seed=scale_seed + 2,
            chunk_size=chunk_size,
        )
    base_shift = canonical_points[base_id] - 100.0 * base_point
    trace_shift = canonical_points[trace_id] - 100.0 * trace_point
    if abs(base_shift) > 0.01 or abs(trace_shift) > 0.01:
        raise RuntimeError(
            f"bootstrap point estimate does not reproduce canonical aggregate for "
            f"{scale}/{benchmark}: base shift={base_shift}, trace shift={trace_shift}"
        )
    delta_shift = trace_shift - base_shift
    result = {
        "evaluated_items": int(len(reference_index)),
        "decoding_seeds": list(SEEDS),
        "row_score_source": (
            "grouped_strict_score_from_archived_row_ledger"
            if benchmark in COMPOSITE_ROW_BENCHMARKS
            else "reconstructed_from_pinned_extractions_and_official_scorer"
            if benchmark in AGGREGATE_ONLY_BENCHMARKS
            else "archived_row_score_ledger"
        ),
        "base": {
            "model_id": base_id,
            "score": canonical_points[base_id],
            "ci95": [
                float(100.0 * base_ci[0] + base_shift),
                float(100.0 * base_ci[1] + base_shift),
            ],
        },
        "trace": {
            "model_id": trace_id,
            "score": canonical_points[trace_id],
            "ci95": [
                float(100.0 * trace_ci[0] + trace_shift),
                float(100.0 * trace_ci[1] + trace_shift),
            ],
        },
        "paired_delta": {
            "score": canonical_points[trace_id] - canonical_points[base_id],
            "ci95": [
                float(100.0 * delta_ci[0] + delta_shift),
                float(100.0 * delta_ci[1] + delta_shift),
            ],
        },
    }
    if benchmark in AGGREGATE_ONLY_BENCHMARKS:
        result["aggregate_center_adjustments_points"] = {
            model_id: {
                str(seed): float(
                    100.0
                    * model_seed_frames[(model_id, seed)].attrs.get(
                        "aggregate_center_adjustment", 0.0
                    )
                )
                for seed in SEEDS
            }
            for model_id in (base_id, trace_id)
        }
    return result


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _latex(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "_": r"\_",
        "#": r"\#",
    }
    return "".join(replacements.get(character, character) for character in value)


def _signed(value: float) -> str:
    if abs(value) < 0.005:
        value = 0.0
    return f"{value:+.2f}"


def _interval_cell(lower: float, upper: float) -> str:
    interval = rf"$[{_signed(lower)},\ {_signed(upper)}]$"
    excludes_zero = lower > 1e-9 or upper < -1e-9
    return rf"\textbf{{{interval}}}" if excludes_zero else interval


def _write_table(path: Path, results: Mapping[str, Mapping[str, Any]]) -> None:
    suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    benchmark_rows = {
        str(item["key"]): item for item in suite["benchmarks"]
    }
    categories = suite["categories"]
    expected = set(benchmark_rows)
    for scale in ("3B", "7B"):
        actual = set(results[scale])
        if actual != expected:
            raise RuntimeError(
                f"bootstrap/table benchmark drift for {scale}: "
                f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
            )

    lines = [
        "% Generated by paper/trace/scripts/build_external_bootstrap_cis.py. Do not edit.",
        r"\begin{table}[t]",
        r"  \centering",
        r"  \fontsize{8.5}{9.5}\selectfont",
        r"  \setlength{\tabcolsep}{5pt}",
        r"  \renewcommand{\arraystretch}{1.10}",
        r"  \caption{Paired Base-to-\trace improvements on the external evaluation suite, in percentage points. Intervals are 95\% bootstrap percentile intervals, computed from the 2.5th and 97.5th percentiles of 10,000 paired item-bootstrap replicates; each sampled item carries results from all three decoding seeds. Bold intervals exclude zero. These intervals quantify variation over evaluation items rather than independently trained checkpoints.}",
        r"  \label{tab:external-bootstrap-cis}",
        r"  \begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.20\textwidth} *{4}{>{\centering\arraybackslash}X}@{}}",
        r"    \toprule",
        r"    & \multicolumn{2}{c}{3B} & \multicolumn{2}{c}{7B} \\",
        r"    \cmidrule(lr){2-3}\cmidrule(l){4-5}",
        r"    Benchmark & $\Delta$ & 95\% CI & $\Delta$ & 95\% CI \\",
        r"    \midrule",
    ]
    for category_index, (category, benchmark_keys) in enumerate(categories.items()):
        if category_index:
            lines.append(r"    \specialrule{0.35pt}{0pt}{0pt}")
        style = CATEGORY_TABLE_STYLES[str(category)]
        lines.append(
            rf"    \rowcolor{{{style}}} \multicolumn{{5}}{{@{{}}l@{{}}}}{{\textbf{{{_latex(str(category))}}}}} \\"
        )
        for benchmark in benchmark_keys:
            item = benchmark_rows[str(benchmark)]
            display = PAPER_BENCHMARK_DISPLAY_NAMES.get(
                str(benchmark), str(item["display"])
            )
            cells: list[str] = []
            for scale in ("3B", "7B"):
                delta = results[scale][str(benchmark)]["paired_delta"]
                lower, upper = (float(value) for value in delta["ci95"])
                cells.extend(
                    [
                        rf"${_signed(float(delta['score']))}$",
                        _interval_cell(lower, upper),
                    ]
                )
            lines.append(
                rf"    \rowcolor{{{style}}} {_latex(display)} & "
                + " & ".join(cells)
                + r" \\"
            )
    lines.extend(
        [
            r"    \bottomrule",
            r"  \end{tabularx}",
            r"\end{table}",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = _parse_args()
    token = _token(args.token_file)
    remote_paths = _score_paths(token)
    remote_extraction_paths = _extraction_paths(token)
    local_paths = _download_parts(
        remote_paths,
        token=token,
        workers=args.download_workers,
        description="Download score ledgers",
    )
    local_extraction_paths = _download_parts(
        remote_extraction_paths,
        token=token,
        workers=args.download_workers,
        description="Download extraction ledgers",
    )
    benchmarks = sorted({key[3] for key in local_paths})
    results: dict[str, dict[str, Any]] = {scale: {} for scale in RUNS}
    total = len(RUNS) * len(benchmarks)
    with tqdm(total=total, desc="Paired item bootstrap", unit="comparison") as progress:
        for scale in RUNS:
            for benchmark in benchmarks:
                results[scale][benchmark] = _scale_benchmark_result(
                    scale=scale,
                    benchmark=benchmark,
                    paths=local_paths,
                    extraction_paths=local_extraction_paths,
                    replicates=args.bootstrap_replicates,
                    bootstrap_seed=args.bootstrap_seed,
                    chunk_size=args.bootstrap_chunk_size,
                )
                progress.update(1)

    payload = {
        "schema_version": "trace_external_benchmark_bootstrap_cis_v1",
        "method": {
            "confidence_level": 0.95,
            "interval": "percentile",
            "replicates": args.bootstrap_replicates,
            "seed": args.bootstrap_seed,
            "resampling_unit": "benchmark_item_or_official_score_group",
            "pairing": "Base and Trace scores paired by source ordinal and source-row hash",
            "seed_handling": "Each item cluster carries scores from all three decoding seeds; scores are averaged within item before resampling.",
            "tablevqabench_resampling": "Item bootstrap stratified by official split; all five official split metrics are recomputed per replicate.",
            "wemath_resampling": "The official strict score is recomputed per 2-step or 3-step problem family, and the 525 paired families are resampled.",
            "canonical_point_alignment": "Each bootstrap distribution is centered on the immutable mean of the three reported seed aggregates. Alignment larger than 0.01 percentage points is rejected.",
            "aggregate_only_centering": "Recovered row vectors must reproduce the canonical aggregate exactly. A discrepancy no larger than one item may be centered on that aggregate to account for archived scorer type coercion; every adjustment is recorded per model and seed.",
        },
        "source": {
            "repository_id": HF_REPO_ID,
            "repository_type": "dataset",
            "revision": HF_REVISION,
            "score_parts": len(local_paths),
            "extraction_parts": len(local_extraction_paths),
            "aggregate_only_row_reconstruction": sorted(AGGREGATE_ONLY_BENCHMARKS),
            "composite_row_metrics": sorted(COMPOSITE_ROW_BENCHMARKS),
            "row_reconstruction_validated_against_canonical_aggregate": True,
            "evaluation_suite_path": str(SUITE_PATH.relative_to(REPO_ROOT)),
            "evaluation_suite_sha256": _sha256(SUITE_PATH),
            "vlmevalkit_root": str(VLMEVAL_ROOT),
            "vlmevalkit_revision": subprocess.check_output(
                ("git", "rev-parse", "HEAD"), cwd=VLMEVAL_ROOT, text=True
            ).strip(),
            "vlmevalkit_scorer_sha256": _scorer_source_hashes(),
        },
        "results": results,
    }
    _write_json(args.output, payload)
    _write_table(args.table_output, results)

    generator = Path(__file__).resolve()
    provenance = {
        "schema_version": "trace_external_benchmark_bootstrap_provenance_v1",
        "generator": {
            "path": str(generator.relative_to(REPO_ROOT)),
            "sha256": _sha256(generator),
        },
        "source": payload["source"],
        "parameters": payload["method"],
        "output": {
            "path": str(args.output.relative_to(REPO_ROOT)),
            "sha256": _sha256(args.output),
            "bytes": args.output.stat().st_size,
        },
        "table_output": {
            "path": str(args.table_output.relative_to(REPO_ROOT)),
            "sha256": _sha256(args.table_output),
            "bytes": args.table_output.stat().st_size,
        },
    }
    _write_json(args.provenance_output, provenance)
    print(f"[ok] wrote {args.output}")
    print(f"[ok] wrote {args.table_output}")
    print(f"[ok] wrote {args.provenance_output}")


if __name__ == "__main__":
    main()
