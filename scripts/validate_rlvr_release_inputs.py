#!/usr/bin/env python3
"""Fail-closed validation for the frozen paper RLVR release inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = REPO_ROOT / "evaluation" / "trace_eval" / "suite.v1.json"
DEFAULT_PROVENANCE = (
    REPO_ROOT / "evaluation" / "trace_eval" / "benchmark_provenance.v1.json"
)
DEFAULT_RESULTS = (
    REPO_ROOT / "results" / "canonical" / "trace_eval_v1" / "release" / "results.json"
)
DEFAULT_FILE_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "workflows"
    / "PUBLIC_RELEASE"
    / "rlvr_public_file_manifest.v1.json"
)

EXPECTED_MODELS = (
    "qwen2.5-vl-3b-base",
    "trace-qwen2.5-vl-3b",
    "qwen2.5-vl-7b-base",
    "trace-qwen2.5-vl-7b",
    "vero-qwen2.5-vl-7b",
    "game-rl-qwen2.5-vl-7b",
    "sphinx-qwen2.5-vl-7b",
    "pcgrpo-qwen2.5-vl-7b",
)
EXPECTED_SEEDS = (42, 43, 44)
EXPECTED_RESULT_REVISIONS = {
    "4178a839b689babe16f8ac36f0de7b1b2c5ef36c",
    "4ca25af7a4d7daa644e6f35e070dbed1af078321",
}
EXPECTED_RESULT_SHA256 = {
    "3a7acbf1d9baf3f32fe7ba7b4e522cc713a648fecf438eeae0319b013d8efda7",
    "578e574d68702af0b83a9c1962bd73c36f8887787cc9ac10a8f7da3d207c10ac",
    "7af92decffc261ad70bd2925632a4aeb3aa61a14cbc5974d285a264a32082c85",
}
EXPECTED_PROMPT_SHA256 = "f394927d9abcfb7a1e43ef48a30c29b8c70e6facdbda314d7b27c59d8c3ae900"
EXPECTED_EASYR1_REVISION = "dd71bbd252694f5f850213eec15795b6b88d9fea"
EXPECTED_TRAINING_CONFIG_RECEIPT = (
    "docs/workflows/PUBLIC_RELEASE/rlvr_training_configs.v1.json"
)
EXPECTED_TRAINING_ENVIRONMENT_RECEIPT = (
    "docs/workflows/PUBLIC_RELEASE/rlvr_training_environments.v1.json"
)
EXPECTED_TRAINING_ENTRYPOINTS = {
    "rlvr/configs/trace-qwen2.5-vl-3b.yaml",
    "rlvr/configs/trace-qwen2.5-vl-7b.yaml",
    "rlvr/train.py",
}
EXPECTED_TRAINING_ADAPTATIONS = {
    "rlvr/easyr1_backend/examples/reward_function/trace_rlvr.py",
    "rlvr/easyr1_backend/scripts/model_merger.py",
    "rlvr/easyr1_backend/verl/trainer/config.py",
    "rlvr/easyr1_backend/verl/trainer/data_loader.py",
    "rlvr/easyr1_backend/verl/trainer/metrics.py",
    "rlvr/easyr1_backend/verl/utils/dataset.py",
}
FORBIDDEN_TRAINING_SOURCES = {
    "rlvr/easyr1_backend/examples/config.yaml",
    "rlvr/easyr1_backend/pyproject.toml",
    "rlvr/easyr1_backend/requirements.txt",
    "rlvr/easyr1_backend/setup.py",
    "rlvr/easyr1_backend/tests/test_trace_rlvr_reward.py",
    "scripts/run_trace_qwen25vl3b_easyr1_all1000_answer_nokl_step500_job.sh",
    "scripts/run_trace_qwen25vl3b_easyr1_answer_nokl_tmpfs.sh",
    "scripts/run_trace_qwen25vl3b_easyr1_nokl_tmpfs.sh",
    "scripts/run_trace_qwen25vl7b_easyr1_answer_nokl_tmpfs.sh",
}
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_content(revision: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"{revision}:{path}"],
        check=True,
        capture_output=True,
    ).stdout


def _require_text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty string")
    return value


def _require_commit(value: Any, context: str) -> str:
    text = _require_text(value, context)
    if COMMIT_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{context} must be a full immutable Git commit: {text!r}")
    return text


def _require_url(value: Any, context: str) -> str:
    text = _require_text(value, context)
    if not text.startswith(("https://", "http://")):
        raise ValueError(f"{context} must be an HTTP(S) URL: {text!r}")
    return text


def _assert_close(actual: Any, expected: Any, context: str) -> None:
    if not math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=1e-10):
        raise ValueError(f"{context}: {actual!r} != {expected!r}")


def _mean(values: Iterable[float]) -> float:
    result = [float(value) for value in values]
    if not result:
        raise ValueError("cannot average an empty collection")
    return statistics.fmean(result)


def _stddev(values: Iterable[float]) -> float:
    result = [float(value) for value in values]
    return statistics.stdev(result) if len(result) > 1 else 0.0


def validate_provenance(
    suite: dict[str, Any], provenance: dict[str, Any]
) -> dict[str, Any]:
    if provenance.get("schema_version") != "trace_eval_benchmark_provenance_v1":
        raise ValueError("unexpected benchmark provenance schema")
    if provenance.get("suite_id") != "trace_eval_v1":
        raise ValueError("provenance is not for trace_eval_v1")
    if provenance.get("status") != "reviewed_release_input":
        raise ValueError("benchmark provenance has not been reviewed")
    if provenance.get("vlmevalkit", {}).get("revision") != suite["vlmevalkit"]["commit"]:
        raise ValueError("VLMEvalKit revision differs between suite and provenance")

    suite_rows = suite.get("benchmarks")
    entries = provenance.get("benchmarks")
    if not isinstance(suite_rows, list) or len(suite_rows) != 24:
        raise ValueError("trace_eval_v1 must contain exactly 24 benchmarks")
    if not isinstance(entries, list) or len(entries) != 24:
        raise ValueError("provenance must contain exactly 24 benchmarks")
    suite_ids = [row["key"] for row in suite_rows]
    provenance_ids = [row.get("benchmark_id") for row in entries]
    if provenance_ids != suite_ids:
        raise ValueError("provenance benchmark order/identity differs from suite.v1.json")
    if len(set(provenance_ids)) != 24:
        raise ValueError("duplicate benchmark provenance identity")

    license_statuses: dict[str, int] = defaultdict(int)
    for suite_row, entry in zip(suite_rows, entries, strict=True):
        benchmark_id = suite_row["key"]
        expected = {
            "public_name": suite_row["display"],
            "official_alias": suite_row["official_alias"],
            "category": suite_row["category"],
            "row_count": int(suite_row["rows"]),
        }
        for field, value in expected.items():
            if entry.get(field) != value:
                raise ValueError(
                    f"{benchmark_id}.{field}: {entry.get(field)!r} != {value!r}"
                )

        source = entry.get("source")
        if not isinstance(source, dict):
            raise ValueError(f"{benchmark_id}.source must be an object")
        _require_url(source.get("repository"), f"{benchmark_id}.source.repository")
        revision = _require_text(source.get("revision"), f"{benchmark_id}.source.revision")
        if len(revision) < 7:
            raise ValueError(f"{benchmark_id}.source.revision is not immutable enough")
        _require_text(source.get("revision_kind"), f"{benchmark_id}.source.revision_kind")
        _require_text(source.get("split"), f"{benchmark_id}.source.split")
        source_rows = source.get("source_row_count")
        if not isinstance(source_rows, int) or source_rows <= 0:
            raise ValueError(f"{benchmark_id}.source.source_row_count must be positive")

        artifact = entry.get("evaluation_artifact")
        if not isinstance(artifact, dict):
            raise ValueError(f"{benchmark_id}.evaluation_artifact must be an object")
        if "url" in artifact:
            _require_url(artifact["url"], f"{benchmark_id}.evaluation_artifact.url")
        else:
            _require_url(
                artifact.get("repository"),
                f"{benchmark_id}.evaluation_artifact.repository",
            )
            _require_text(
                artifact.get("repository_revision"),
                f"{benchmark_id}.evaluation_artifact.repository_revision",
            )
            _require_text(artifact.get("path"), f"{benchmark_id}.evaluation_artifact.path")
        checksum = artifact.get("checksum")
        if checksum is not None:
            if checksum.get("algorithm") not in {"md5", "sha256"}:
                raise ValueError(f"unsupported artifact checksum for {benchmark_id}")
            _require_text(checksum.get("value"), f"{benchmark_id}.checksum.value")

        terms = entry.get("license_or_terms")
        if not isinstance(terms, dict):
            raise ValueError(f"{benchmark_id}.license_or_terms must be an object")
        status = _require_text(terms.get("status"), f"{benchmark_id}.license.status")
        expression = terms.get("expression")
        if status == "not_declared":
            if expression is not None:
                raise ValueError(f"{benchmark_id} must not invent an undeclared license")
        else:
            _require_text(expression, f"{benchmark_id}.license.expression")
        _require_url(terms.get("evidence"), f"{benchmark_id}.license.evidence")
        license_statuses[status] += 1

        citations = entry.get("citations")
        if not isinstance(citations, list) or not citations:
            raise ValueError(f"{benchmark_id} must have at least one citation")
        for index, citation in enumerate(citations):
            if not isinstance(citation, dict):
                raise ValueError(f"{benchmark_id}.citations[{index}] must be an object")
            _require_text(citation.get("title"), f"{benchmark_id}.citations[{index}].title")
            _require_url(citation.get("url"), f"{benchmark_id}.citations[{index}].url")

        _require_text(entry.get("prompt_route"), f"{benchmark_id}.prompt_route")
        _require_text(entry.get("official_scorer"), f"{benchmark_id}.official_scorer")
        adapter = entry.get("adapter")
        if not isinstance(adapter, dict):
            raise ValueError(f"{benchmark_id}.adapter must be an object")
        if adapter.get("status") not in {"none", "approved", "approved_required"}:
            raise ValueError(f"{benchmark_id}.adapter has an unreviewed status")
        _require_text(adapter.get("description"), f"{benchmark_id}.adapter.description")

    return {
        "benchmarks": 24,
        "rows_per_model_seed": sum(int(row["rows"]) for row in suite_rows),
        "license_statuses": dict(sorted(license_statuses.items())),
    }


def _index_unique(
    rows: list[dict[str, Any]], fields: tuple[str, ...], label: str
) -> dict[tuple[Any, ...], dict[str, Any]]:
    result: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        identity = tuple(row[field] for field in fields)
        if identity in result:
            raise ValueError(f"duplicate {label} identity: {identity}")
        result[identity] = row
    return result


def validate_results(suite: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
    if results.get("schema_version") != "trace_eval_release_results_v1":
        raise ValueError("unexpected release result schema")
    if results.get("status") != "canonical":
        raise ValueError("release results are not canonical")
    if tuple(results.get("seeds", ())) != EXPECTED_SEEDS:
        raise ValueError("release result seeds differ from 42/43/44")
    if results.get("generation", {}).get(
        "historical_final_answer_only_manifest_is_input"
    ) is not False:
        raise ValueError("historical final_answer_only_manifest must not be an input")
    if results.get("suite", {}).get("suite_id") != "trace_eval_v1":
        raise ValueError("release results are not bound to trace_eval_v1")
    if results.get("suite", {}).get("benchmark_count") != 24:
        raise ValueError("release results do not cover exactly 24 benchmarks")
    if results.get("suite", {}).get("rows_per_model_seed") != 32_805:
        raise ValueError("unexpected trace_eval_v1 row total")

    models = results.get("models")
    if not isinstance(models, list):
        raise ValueError("results.models must be an array")
    model_ids = tuple(row.get("model_id") for row in models)
    if model_ids != EXPECTED_MODELS:
        raise ValueError(f"unexpected model order/set: {model_ids}")
    for model in models:
        for field in (
            "model_id",
            "model_revision",
            "repository_id",
            "repository_revision",
            "source_run_id",
            "source_sha256",
        ):
            _require_text(model.get(field), f"{model.get('model_id')}.{field}")

    artifacts = results.get("source_artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 3:
        raise ValueError("results must identify the three immutable source bundles")
    revisions = {row.get("repository_revision") for row in artifacts}
    result_hashes = {row.get("result_sha256") for row in artifacts}
    if revisions != EXPECTED_RESULT_REVISIONS:
        raise ValueError(f"unexpected result artifact revisions: {revisions}")
    if result_hashes != EXPECTED_RESULT_SHA256:
        raise ValueError(f"unexpected result artifact hashes: {result_hashes}")

    benchmark_ids = tuple(row["key"] for row in suite["benchmarks"])
    benchmark_rows = {row["key"]: int(row["rows"]) for row in suite["benchmarks"]}
    categories = suite["categories"]
    scores = results.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("results.scores must be an object")

    benchmark_scores = scores.get("benchmark_scores")
    if not isinstance(benchmark_scores, list) or len(benchmark_scores) != 576:
        raise ValueError("expected 8 x 3 x 24 benchmark score rows")
    indexed = _index_unique(
        benchmark_scores,
        ("model_id", "seed", "benchmark_id"),
        "benchmark score",
    )
    expected_identities = {
        (model_id, seed, benchmark_id)
        for model_id in EXPECTED_MODELS
        for seed in EXPECTED_SEEDS
        for benchmark_id in benchmark_ids
    }
    if set(indexed) != expected_identities:
        raise ValueError("benchmark score identities are incomplete or contain extras")
    for identity, row in indexed.items():
        if row.get("evaluated_rows") != benchmark_rows[identity[2]]:
            raise ValueError(f"row-count mismatch for {identity}")
        score = row.get("score")
        if not isinstance(score, (int, float)) or not math.isfinite(float(score)):
            raise ValueError(f"non-finite score for {identity}")

    category_scores = _index_unique(
        scores.get("category_scores", []),
        ("model_id", "seed", "category_name"),
        "category score",
    )
    overall_scores = _index_unique(
        scores.get("overall_scores", []),
        ("model_id", "seed"),
        "overall score",
    )
    for model_id in EXPECTED_MODELS:
        for seed in EXPECTED_SEEDS:
            benchmark_values = {
                benchmark_id: float(indexed[(model_id, seed, benchmark_id)]["score"])
                for benchmark_id in benchmark_ids
            }
            for category, members in categories.items():
                row = category_scores[(model_id, seed, category)]
                _assert_close(
                    row["score"],
                    _mean(benchmark_values[item] for item in members),
                    f"category score {(model_id, seed, category)}",
                )
            overall = _mean(benchmark_values.values())
            _assert_close(
                overall_scores[(model_id, seed)]["score"],
                overall,
                f"overall score {(model_id, seed)}",
            )

    benchmark_summaries = _index_unique(
        scores.get("benchmark_summaries", []),
        ("model_id", "benchmark_id"),
        "benchmark summary",
    )
    category_summaries = _index_unique(
        scores.get("category_summaries", []),
        ("model_id", "category_name"),
        "category summary",
    )
    overall_summaries = _index_unique(
        scores.get("overall_summaries", []),
        ("model_id",),
        "overall summary",
    )
    for model_id in EXPECTED_MODELS:
        for benchmark_id in benchmark_ids:
            values = [indexed[(model_id, seed, benchmark_id)]["score"] for seed in EXPECTED_SEEDS]
            summary = benchmark_summaries[(model_id, benchmark_id)]
            _assert_close(summary["mean"], _mean(values), f"benchmark mean {model_id}/{benchmark_id}")
            _assert_close(
                summary["stddev"], _stddev(values), f"benchmark stddev {model_id}/{benchmark_id}"
            )
        for category in categories:
            values = [category_scores[(model_id, seed, category)]["score"] for seed in EXPECTED_SEEDS]
            summary = category_summaries[(model_id, category)]
            _assert_close(summary["mean"], _mean(values), f"category mean {model_id}/{category}")
            _assert_close(
                summary["stddev"], _stddev(values), f"category stddev {model_id}/{category}"
            )
        values = [overall_scores[(model_id, seed)]["score"] for seed in EXPECTED_SEEDS]
        summary = overall_summaries[(model_id,)]
        _assert_close(summary["mean"], _mean(values), f"overall mean {model_id}")
        _assert_close(summary["stddev"], _stddev(values), f"overall stddev {model_id}")

    comparisons = results.get("comparisons")
    if not isinstance(comparisons, list) or len(comparisons) != 6:
        raise ValueError("expected the six paper model-to-base comparisons")
    for comparison in comparisons:
        model_id = comparison["model_id"]
        base_id = comparison["base_model_id"]
        values = [
            overall_scores[(model_id, seed)]["score"]
            - overall_scores[(base_id, seed)]["score"]
            for seed in EXPECTED_SEEDS
        ]
        _assert_close(
            comparison["overall_delta"]["mean"],
            _mean(values),
            f"overall paired delta {model_id}",
        )
        _assert_close(
            comparison["overall_delta"]["stddev"],
            _stddev(values),
            f"overall paired delta stddev {model_id}",
        )

    return {
        "models": len(models),
        "seeds": len(EXPECTED_SEEDS),
        "benchmark_scores": len(benchmark_scores),
        "overall_means": {
            model_id: overall_summaries[(model_id,)]["mean"] for model_id in EXPECTED_MODELS
        },
    }


def _nested_value(value: dict[str, Any], keys: tuple[str, ...]) -> Any:
    current: Any = value
    for key in keys:
        current = current.get(key) if isinstance(current, dict) else None
    return current


def _assert_sanitized_receipt(value: dict[str, Any], label: str) -> None:
    serialized = json.dumps(value, sort_keys=True).lower()
    forbidden = ("/home/", "/dev/shm", "shadeform", "10.0.", "gpu-")
    leaked = [marker for marker in forbidden if marker in serialized]
    if leaked:
        raise ValueError(f"{label} contains machine-local metadata: {leaked}")


def validate_training_receipts(release_inputs: dict[str, Any]) -> dict[str, Any]:
    receipt_rows = release_inputs.get("training_receipts")
    if not isinstance(receipt_rows, dict):
        raise ValueError("training receipts are not frozen")
    expected = {
        "resolved_configs": (
            EXPECTED_TRAINING_CONFIG_RECEIPT,
            "trace-rlvr-training-config-receipt-v1",
        ),
        "environments": (
            EXPECTED_TRAINING_ENVIRONMENT_RECEIPT,
            "trace-rlvr-training-environment-receipt-v1",
        ),
    }
    loaded: dict[str, dict[str, Any]] = {}
    release_metadata_revision = _require_commit(
        release_inputs.get("release_metadata_source_revision"),
        "release_metadata_source_revision",
    )
    for name, (expected_path, expected_schema) in expected.items():
        row = receipt_rows.get(name)
        if not isinstance(row, dict) or row.get("path") != expected_path:
            raise ValueError(f"unexpected {name} training receipt path")
        source_revision = _require_commit(
            row.get("source_revision"), f"{name} training receipt source_revision"
        )
        if source_revision != release_metadata_revision:
            raise ValueError(f"{name} training receipt is not bound to the release snapshot")
        path = REPO_ROOT / expected_path
        frozen_sha256 = _sha256_bytes(_git_content(source_revision, expected_path))
        if row.get("sha256") != frozen_sha256:
            raise ValueError(f"stale frozen {name} training receipt hash")
        if row.get("sha256") != _sha256_path(path):
            raise ValueError(f"stale {name} training receipt hash")
        if row.get("schema_version") != expected_schema:
            raise ValueError(f"unexpected {name} training receipt schema reference")
        value = _load(path)
        if value.get("schema_version") != expected_schema:
            raise ValueError(f"unexpected {name} training receipt schema")
        if value.get("status") != "sanitized_canonical_wandb_receipt":
            raise ValueError(f"{name} training receipt is not canonical")
        _assert_sanitized_receipt(value, name)
        loaded[name] = value

    configs = loaded["resolved_configs"]
    if configs.get("prompt", {}).get("sha256") != EXPECTED_PROMPT_SHA256:
        raise ValueError("resolved training receipt has the wrong prompt hash")
    dataset = configs.get("dataset", {})
    if dataset.get("revision") != "e317b746b258630682367cc6a9d87dedd195113c":
        raise ValueError("resolved training receipt has the wrong dataset revision")
    expected_shards = [
        f"data/train/trace_rlvr_train_64000_all1000_seed42-{index:05d}-of-00016.parquet"
        for index in range(16)
    ]
    if dataset.get("train", {}).get("shards") != expected_shards:
        raise ValueError("resolved training receipt does not name the canonical 16 shards")
    if dataset.get("train", {}).get("rows") != 64_000:
        raise ValueError("resolved training receipt has the wrong train row count")
    if dataset.get("validation", {}).get("rows") != 2_000:
        raise ValueError("resolved training receipt has the wrong validation row count")

    common = configs.get("common_resolved_config")
    if not isinstance(common, dict):
        raise ValueError("resolved training receipt is missing the common config")
    expected_common = {
        ("algorithm", "adv_estimator"): "grpo",
        ("algorithm", "disable_kl"): True,
        ("algorithm", "use_kl_loss"): False,
        ("data", "prompt_key"): "prompt_answer",
        ("data", "answer_key"): "answer_gt",
        ("data", "rollout_batch_size"): 128,
        ("trainer", "max_steps"): 500,
        ("trainer", "save_freq"): 100,
        ("trainer", "val_freq"): 100,
        ("trainer", "save_limit"): 1,
        ("trainer", "find_last_checkpoint"): False,
        ("trainer", "load_checkpoint_path"): None,
        ("trainer", "n_gpus_per_node"): 8,
        ("worker", "actor", "global_batch_size"): 128,
        ("worker", "actor", "optim", "lr"): 1e-6,
        ("worker", "reward", "reward_mode"): "answer",
        ("worker", "reward", "answer_scoring"): "exact_json",
        ("worker", "reward", "overall_formula"): "0.95 * answer + 0.05 * format",
        ("worker", "rollout", "n"): 8,
        ("worker", "rollout", "tensor_parallel_size"): 2,
    }
    for keys, expected_value in expected_common.items():
        actual = _nested_value(common, keys)
        if actual != expected_value:
            raise ValueError(
                f"resolved training receipt {'.'.join(keys)}: "
                f"{actual!r} != {expected_value!r}"
            )
    common_keys = json.dumps(common, sort_keys=True).lower()
    if "annotation" in common_keys or "task_conditioned" in common_keys:
        raise ValueError("public resolved config exposes annotation/task-conditioned training")

    config_runs = configs.get("runs")
    if not isinstance(config_runs, list):
        raise ValueError("resolved training receipt runs must be an array")
    indexed_runs = {row.get("config_id"): row for row in config_runs}
    expected_runs = {
        "trace-qwen2.5-vl-3b": {
            "wandb_run_id": "kijsydl8",
            "wandb_config_sha256": "2d8a1461468c5950fe2a4daafa9df524d3f5c64bf1a1cff3201f9931f9bc8b35",
            "source_revision": "847e9f5279f8111fdbfef1c8b8631fc621c23456",
            "base_model": "Qwen/Qwen2.5-VL-3B-Instruct@66285546d2b821cf421d4f5eb2576359d3770cd3",
        },
        "trace-qwen2.5-vl-7b": {
            "wandb_run_id": "usqbkpd6",
            "wandb_config_sha256": "19dea84aa0fb748566f42974819f331ef58fde8738f0b18d8dc0876be9baab31",
            "source_revision": "d29b23f6085764ea831adb5edc5a23f89b0d98f3",
            "base_model": "Qwen/Qwen2.5-VL-7B-Instruct@cc594898137f460bfe9f0759e9844b3ce807cfb5",
        },
    }
    if set(indexed_runs) != set(expected_runs):
        raise ValueError("resolved training receipt must contain exactly the 3B and 7B configs")
    for config_id, fields in expected_runs.items():
        for field, expected_value in fields.items():
            if indexed_runs[config_id].get(field) != expected_value:
                raise ValueError(f"unexpected {config_id} {field}")

    public_interface = configs.get("public_interface", {})
    if set(public_interface.get("config_destinations", ())) != {
        "rlvr/configs/trace-qwen2.5-vl-3b.yaml",
        "rlvr/configs/trace-qwen2.5-vl-7b.yaml",
    }:
        raise ValueError("training receipt exposes unexpected public configs")
    if public_interface.get("cli_destination") != "rlvr/train.py":
        raise ValueError("training receipt exposes an unexpected public CLI")
    if public_interface.get("subcommands") != [
        "check",
        "prepare",
        "run",
        "smoke",
        "merge",
    ]:
        raise ValueError("training receipt has an unexpected public CLI contract")
    if public_interface.get("automatic_uploads") is not False:
        raise ValueError("public training interface must not upload artifacts")

    environments = loaded["environments"]
    platform = environments.get("reference_platform", {})
    if platform.get("cuda") != "12.8" or platform.get("gpu_count") != 8:
        raise ValueError("unexpected canonical training hardware receipt")
    required_pins = {
        "torch": "2.8.0+cu128",
        "torchvision": "0.23.0+cu128",
        "transformers": "4.57.6",
        "vllm": "0.10.2",
        "ray": "2.56.0",
        "flash_attn": "2.8.3",
        "datasets": "5.0.0",
        "qwen-vl-utils": "0.0.14",
    }
    pins = environments.get("common_reproduction_pins", {})
    for package, expected_version in required_pins.items():
        if pins.get(package) != expected_version:
            raise ValueError(f"unexpected canonical environment pin for {package}")
    environment_runs = {
        row.get("config_id"): row for row in environments.get("runs", [])
    }
    expected_requirements = {
        "trace-qwen2.5-vl-3b": "798ce596e11a5266591ffe01f0ca0cf29d6968308784cab476960fc1de0ecca8",
        "trace-qwen2.5-vl-7b": "132c380fac1fc11bea08ff130b978e997703b303f989e5b72aca4bcdfd5dd276",
    }
    if set(environment_runs) != set(expected_requirements):
        raise ValueError("environment receipt must contain exactly the 3B and 7B runs")
    for config_id, expected_hash in expected_requirements.items():
        if environment_runs[config_id].get("wandb_requirements_sha256") != expected_hash:
            raise ValueError(f"unexpected requirements receipt for {config_id}")

    return {
        "configs": len(config_runs),
        "train_shards": len(expected_shards),
        "environment_runs": len(environment_runs),
    }


def validate_file_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("schema_version") != "trace-rlvr-public-file-manifest-v1":
        raise ValueError("unexpected public file manifest schema")
    if manifest.get("status") != "reviewed_release_input_freeze":
        raise ValueError("public file manifest has not been reviewed")
    if manifest.get("review_policy", {}).get("default") != "deny":
        raise ValueError("public release boundary must be default-deny")
    if manifest.get("dependency_review", {}).get("status") != "reviewed":
        raise ValueError("public release dependency exclusions have not been reviewed")

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("public file allowlist is empty")
    source_identities: set[tuple[str, str, str]] = set()
    destinations: set[str] = set()
    status_counts: dict[str, int] = defaultdict(int)
    for entry in files:
        source_path = _require_text(entry.get("source_path"), "files[].source_path")
        source_revision = _require_commit(
            entry.get("source_revision"), f"{source_path}.source_revision"
        )
        source_sha256 = _require_text(
            entry.get("source_sha256"), f"{source_path}.source_sha256"
        )
        if len(source_sha256) != 64:
            raise ValueError(f"invalid source SHA-256 for {source_path}")
        destination = _require_text(
            entry.get("destination_path"), f"{source_path}.destination_path"
        )
        if destination.startswith("/") or ".." in Path(destination).parts:
            raise ValueError(f"unsafe public destination: {destination}")
        if "final25" in destination.lower() or "final26" in destination.lower():
            raise ValueError(f"historical campaign name leaked into destination: {destination}")
        identity = (source_revision, source_path, destination)
        if identity in source_identities:
            raise ValueError(f"duplicate file map entry: {identity}")
        if destination in destinations:
            raise ValueError(f"duplicate public destination: {destination}")
        source_identities.add(identity)
        destinations.add(destination)
        if entry.get("owner") != "rlvr":
            raise ValueError(f"unexpected owner for {source_path}")
        status = entry.get("review_status")
        if status not in {"approved_exact_copy", "approved_for_public_adaptation"}:
            raise ValueError(f"unreviewed file status for {source_path}: {status!r}")
        if status == "approved_for_public_adaptation" and not entry.get("adaptations"):
            raise ValueError(f"missing public adaptations for {source_path}")
        status_counts[str(status)] += 1

        actual = _sha256_bytes(_git_content(source_revision, source_path))
        if actual != source_sha256:
            raise ValueError(f"frozen source hash mismatch for {source_path}")

    training_files = [
        entry
        for entry in files
        if entry.get("component")
        in {"answer_only_training", "answer_only_training_entrypoint"}
    ]
    training_sources = {entry["source_path"] for entry in training_files}
    forbidden_sources = FORBIDDEN_TRAINING_SOURCES.intersection(training_sources)
    if forbidden_sources:
        raise ValueError(
            f"excluded training sources are allowlisted: {sorted(forbidden_sources)}"
        )
    verl_entries = [
        entry
        for entry in training_files
        if entry["source_path"].startswith("rlvr/easyr1_backend/verl/")
    ]
    if len(verl_entries) != 64:
        raise ValueError(f"expected the reviewed 64-file verl unit, found {len(verl_entries)}")
    if len({entry["source_path"] for entry in verl_entries}) != 64:
        raise ValueError("duplicate files in the reviewed verl unit")
    entrypoint_rows = [
        entry
        for entry in training_files
        if entry.get("component") == "answer_only_training_entrypoint"
    ]
    if {entry["destination_path"] for entry in entrypoint_rows} != (
        EXPECTED_TRAINING_ENTRYPOINTS
    ):
        raise ValueError("public training entrypoints must be exactly two configs and one CLI")
    if any(
        entry["source_path"] != EXPECTED_TRAINING_CONFIG_RECEIPT
        or entry["review_status"] != "approved_for_public_adaptation"
        for entry in entrypoint_rows
    ):
        raise ValueError("public training entrypoints are not bound to the reviewed receipt")
    adapted_training_sources = {
        entry["source_path"]
        for entry in training_files
        if entry.get("component") == "answer_only_training"
        and entry["review_status"] == "approved_for_public_adaptation"
    }
    if adapted_training_sources != EXPECTED_TRAINING_ADAPTATIONS:
        raise ValueError(
            "unexpected exact/adapted training boundary: "
            f"{sorted(adapted_training_sources)}"
        )
    merger_row = next(
        entry
        for entry in training_files
        if entry["source_path"] == "rlvr/easyr1_backend/scripts/model_merger.py"
    )
    if not any("upload" in item.lower() for item in merger_row["adaptations"]):
        raise ValueError("model merger adaptation does not explicitly remove uploads")

    old_manifest = "rlvr/experiments/final_answer_only_manifest.json"
    if any(entry["source_path"] == old_manifest for entry in files):
        raise ValueError("historical final_answer_only_manifest is allowlisted")
    denylist = manifest.get("denylist")
    if not isinstance(denylist, list) or not any(
        entry.get("path_or_pattern") == old_manifest for entry in denylist
    ):
        raise ValueError("historical final_answer_only_manifest is not explicitly denylisted")

    release_inputs = manifest.get("release_inputs", {})
    release_metadata_revision = _require_commit(
        release_inputs.get("release_metadata_source_revision"),
        "release_metadata_source_revision",
    )
    release_metadata_revisions = {
        entry["source_revision"]
        for entry in files
        if entry.get("component") == "release_metadata"
    }
    if release_metadata_revisions != {release_metadata_revision}:
        raise ValueError("release metadata files do not share the frozen source revision")
    if any(
        entry["source_revision"] != release_metadata_revision
        for entry in entrypoint_rows
    ):
        raise ValueError("public training entrypoints are not bound to the release snapshot")
    if release_inputs.get("answer_prompt_sha256") != EXPECTED_PROMPT_SHA256:
        raise ValueError("answer-only prompt hash differs from the training contract")
    if release_inputs.get("vlmevalkit", {}).get("revision") != (
        "a8b12bf1c3737a33fc1de967c202f9c592b22e86"
    ):
        raise ValueError("unexpected public VLMEvalKit revision")
    if release_inputs.get("judge", {}).get("revision") != (
        "9216db5781bf21249d130ec9da846c4624c16137"
    ):
        raise ValueError("unexpected public judge revision")
    training_runs = release_inputs.get("training_runs")
    if not isinstance(training_runs, list) or [row.get("parameter_scale") for row in training_runs] != [
        "3B",
        "7B",
    ]:
        raise ValueError("both final 3B and 7B training sources must be frozen")
    expected_training_source_paths = {
        entry["source_path"]
        for entry in training_files
        if entry.get("component") == "answer_only_training"
    }
    run_hashes: dict[str, dict[str, str]] = {}
    for run in training_runs:
        scale = str(run["parameter_scale"])
        hashes = run.get("source_file_sha256")
        if not isinstance(hashes, dict) or set(hashes) != expected_training_source_paths:
            raise ValueError(f"{scale} source receipt is incomplete or contains extras")
        if any(not isinstance(value, str) or len(value) != 64 for value in hashes.values()):
            raise ValueError(f"{scale} source receipt contains an invalid SHA-256")
        run_hashes[scale] = hashes
    differing_sources = {
        path
        for path in expected_training_source_paths
        if run_hashes["3B"][path] != run_hashes["7B"][path]
    }
    expected_differences = {
        "rlvr/easyr1_backend/examples/reward_function/trace_rlvr.py",
        "rlvr/easyr1_backend/verl/trainer/config.py",
    }
    if differing_sources != expected_differences:
        raise ValueError(
            f"unexpected differences between canonical run sources: {sorted(differing_sources)}"
        )
    equivalence = release_inputs.get("training_source_equivalence_review", {})
    if equivalence.get("status") != "reviewed_nonsemantic_difference" or set(
        equivalence.get("differing_release_files", ())
    ) != expected_differences:
        raise ValueError("training source-equivalence review is stale")
    runtime = release_inputs.get("vendored_runtime", {})
    if runtime.get("upstream_revision") != EXPECTED_EASYR1_REVISION:
        raise ValueError("unexpected EasyR1 upstream revision")
    if runtime.get("license") != "Apache-2.0" or runtime.get("verl_file_count") != 64:
        raise ValueError("unexpected vendored EasyR1 license or file count")
    training_receipt_report = validate_training_receipts(release_inputs)
    training_contract = release_inputs.get("training_contract", {})
    expected_contract_values = {
        ("prompt_key",): "prompt_answer",
        ("answer_key",): "answer_gt",
        ("output_mode",): "answer",
        ("reward", "answer_scoring"): "exact_json",
        ("reward", "answer_weight"): 1.0,
        ("reward", "format_weight"): 0.05,
        ("reward", "annotation_weight"): 0.0,
        ("algorithm", "disable_kl"): True,
        ("algorithm", "use_kl_loss"): False,
        ("batching", "rollout_batch_size"): 128,
        ("batching", "rollouts_per_prompt"): 8,
        ("schedule", "max_steps"): 500,
        ("schedule", "checkpoint_selection"): "global_step_500",
    }
    for keys, expected in expected_contract_values.items():
        actual = _nested_value(training_contract, keys)
        if actual != expected:
            raise ValueError(
                f"training contract {'.'.join(keys)}: {actual!r} != {expected!r}"
            )
    for scale in ("3B", "7B"):
        scale_contract = training_contract.get("scale_specific", {}).get(scale, {})
        if scale_contract.get("save_limit") != 1:
            raise ValueError(f"{scale} canonical run must retain one checkpoint")
        if scale_contract.get("find_last_checkpoint") is not False:
            raise ValueError(f"{scale} canonical run must not discover a prior checkpoint")
        if scale_contract.get("load_checkpoint_path") is not None:
            raise ValueError(f"{scale} canonical run must not resume")

    required_destinations = {
        "rlvr/evaluation/trace_eval/benchmark_provenance.v1.json",
        "rlvr/evaluation/trace_eval/results.json",
        "rlvr/evaluation/scripts/build_release_results.py",
        "rlvr/evaluation/trace_eval/suite.v1.json",
        "rlvr/examples/prompts/trace_vero_json_system_prompt_answer.txt",
        *EXPECTED_TRAINING_ENTRYPOINTS,
    }
    missing = required_destinations.difference(destinations)
    if missing:
        raise ValueError(f"required public release files are not mapped: {sorted(missing)}")
    recorded_counts = manifest.get("counts", {})
    if recorded_counts.get("files") != len(files):
        raise ValueError("public file manifest count is stale")
    if recorded_counts.get("exact_copy") != status_counts["approved_exact_copy"]:
        raise ValueError("exact-copy count is stale")
    if recorded_counts.get("public_adaptation") != status_counts[
        "approved_for_public_adaptation"
    ]:
        raise ValueError("public-adaptation count is stale")

    return {
        "files": len(files),
        "exact_copy": status_counts["approved_exact_copy"],
        "public_adaptation": status_counts["approved_for_public_adaptation"],
        "denylist_rules": len(denylist),
        "training_receipts": training_receipt_report,
    }


def validate_release_inputs(
    *,
    suite_path: Path = DEFAULT_SUITE,
    provenance_path: Path = DEFAULT_PROVENANCE,
    results_path: Path = DEFAULT_RESULTS,
    file_manifest_path: Path = DEFAULT_FILE_MANIFEST,
) -> dict[str, Any]:
    suite = _load(suite_path)
    if suite.get("schema_version") != "trace-eval-suite-v1":
        raise ValueError("unexpected trace_eval_v1 suite schema")
    if suite.get("suite_id") != "trace_eval_v1" or suite.get("status") != "canonical":
        raise ValueError("suite.v1.json is not the canonical trace_eval_v1 suite")
    provenance = _load(provenance_path)
    results = _load(results_path)
    file_manifest = _load(file_manifest_path)
    return {
        "status": "ok",
        "suite_id": "trace_eval_v1",
        "provenance": validate_provenance(suite, provenance),
        "results": validate_results(suite, results),
        "public_file_manifest": validate_file_manifest(file_manifest),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--provenance", type=Path, default=DEFAULT_PROVENANCE)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--file-manifest", type=Path, default=DEFAULT_FILE_MANIFEST)
    args = parser.parse_args()
    report = validate_release_inputs(
        suite_path=args.suite,
        provenance_path=args.provenance,
        results_path=args.results,
        file_manifest_path=args.file_manifest,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
