"""Dataset build pipeline for TRACE."""

from __future__ import annotations

import json
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping

from PIL import Image

from ..tasks import create_task
from . import error_codes
from .canonical import canonical_json_bytes
from .config import BuildConfig, BuildTaskConfig
from .hash_utils import blake3_file, blake3_hex
from .identity import compute_instance_id
from .seed import SEED_DERIVATION_VERSION, hash64
from .strict_repro import compare_staging_dirs
from .trace_store import TraceShardWriter
from .type_registry import DEFAULT_REGISTRY_PATH, TypeRegistry, load_type_registry
from .types import CurriculumIndex, ImageRecord, TraceInstance, TrainInstance
from .validation import validate_dataset


class BuildError(RuntimeError):
    """Raised when a dataset build fails."""


@dataclass
class _BuildStageResult:
    """In-memory summary from one staging build pass."""

    instances: List[Dict[str, Any]]
    curriculum: List[Dict[str, Any]]
    target_counts_by_task: Dict[str, int]
    task_sampling_probabilities: Dict[str, float]
    sampler_mode: str
    accepted_by_task: Dict[str, int]
    rejected_by_task: Dict[str, int]
    rejected_reason_by_task: Dict[str, Dict[str, int]]
    evidence_format_map: Dict[str, str]
    accepted_query_counts_by_task: Dict[str, Dict[str, int]]
    query_sampling_probabilities_by_task: Dict[str, Dict[str, float]]
    domain_sampling_probabilities: Dict[str, float]
    task_group_sampling_probabilities: Dict[str, float]
    warnings: List[str]


def _to_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _to_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True))
            handle.write("\n")


def _normalize_weights(weights: Mapping[str, float]) -> Dict[str, float]:
    positive = {key: float(value) for key, value in weights.items() if float(value) > 0.0}
    total = sum(positive.values())
    if total <= 0.0:
        raise BuildError("at least one positive weight is required")
    return {key: value / total for key, value in sorted(positive.items())}


def _weighted_choice(rng: random.Random, probabilities: Mapping[str, float]) -> str:
    roll = rng.random()
    cumulative = 0.0
    last_key = None
    for key, prob in probabilities.items():
        cumulative += float(prob)
        last_key = key
        if roll <= cumulative:
            return key
    if last_key is None:
        raise BuildError("cannot sample from an empty probability map")
    return last_key


def _serialize_task_config(task: BuildTaskConfig) -> Dict[str, Any]:
    return {
        "task_id": task.task_id,
        "count": task.count,
        "weight": task.weight,
        "params": dict(task.params),
        "query_weights": dict(task.query_weights),
        "expected_query_counts": dict(task.expected_query_counts),
    }


def _dataset_id_from_config(config: BuildConfig, type_registry: TypeRegistry, type_registry_hash: str) -> str:
    payload = {
        "dataset_name": config.dataset_name,
        "instance_version": config.instance_version,
        "image_format": config.image_format,
        "strict_repro": config.strict_repro,
        "max_attempts_per_instance": config.max_attempts_per_instance,
        "sampling_seed": config.sampling_seed,
        "num_instances": config.num_instances,
        "tasks": [_serialize_task_config(task) for task in config.tasks],
        "type_registry_version": type_registry.version,
        "type_registry_hash": type_registry_hash,
    }
    return blake3_hex(canonical_json_bytes(payload))


def _save_image(image: Image.Image, path: Path, image_format: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format=image_format.upper())


def _serialize_config(config: BuildConfig) -> Dict[str, Any]:
    return {
        "output_root": config.output_root,
        "dataset_name": config.dataset_name,
        "instance_version": config.instance_version,
        "image_format": config.image_format,
        "num_instances": config.num_instances,
        "strict_repro": config.strict_repro,
        "max_attempts_per_instance": config.max_attempts_per_instance,
        "sampling_seed": config.sampling_seed,
        "tasks": [_serialize_task_config(task) for task in config.tasks],
    }


def _write_failure_bundle(
    *,
    failure_root: Path,
    validation_report: Dict[str, Any] | None,
    resolved_build_config: Dict[str, Any],
    warning_messages: List[str],
) -> None:
    failure_root.mkdir(parents=True, exist_ok=True)
    if validation_report is not None:
        _to_json_file(failure_root / "validation_report.json", validation_report)
    _to_json_file(failure_root / "resolved_build_config.json", resolved_build_config)
    _to_json_file(failure_root / "log_reference.json", {"warnings": warning_messages})


def _ensure_unique_task_ids(tasks: List[BuildTaskConfig]) -> None:
    seen: set[str] = set()
    for task in tasks:
        if task.task_id in seen:
            raise BuildError(f"duplicate task_id in config: {task.task_id}")
        seen.add(task.task_id)


def _resolve_task_targets(config: BuildConfig) -> tuple[Dict[str, int], Dict[str, float], str]:
    _ensure_unique_task_ids(config.tasks)
    has_explicit_counts = all(task.count is not None for task in config.tasks)

    if has_explicit_counts:
        target_counts: Dict[str, int] = {}
        for task in config.tasks:
            count = int(task.count or 0)
            if count < 0:
                raise BuildError(f"task count must be non-negative for {task.task_id}")
            target_counts[task.task_id] = count
        total = sum(target_counts.values())
        if total <= 0:
            raise BuildError("at least one task must request a positive count")
        task_probabilities = {
            task_id: float(count) / float(total)
            for task_id, count in sorted(target_counts.items())
        }
        return target_counts, task_probabilities, "explicit_counts"

    if config.num_instances is None or int(config.num_instances) <= 0:
        raise BuildError("num_instances must be positive when explicit per-task counts are not provided")

    configured_weights = {
        task.task_id: (float(task.weight) if task.weight is not None else 1.0)
        for task in config.tasks
    }
    task_probabilities = _normalize_weights(configured_weights)
    target_counts = {task.task_id: 0 for task in config.tasks}

    sampler_rng = random.Random(hash64(config.sampling_seed, "global_task_sampler", 0))
    for _ in range(int(config.num_instances)):
        sampled_task = _weighted_choice(sampler_rng, task_probabilities)
        target_counts[sampled_task] += 1

    return target_counts, task_probabilities, "weighted_task_sampler"


def _resolve_query_types(task: Any, params: Mapping[str, Any]) -> List[str]:
    if hasattr(task, "supported_query_types"):
        values = getattr(task, "supported_query_types")(dict(params))
        out = [str(v) for v in values]
    elif "query_type" in params:
        out = [str(params["query_type"])]
    else:
        out = ["default"]

    deduped: List[str] = []
    seen: set[str] = set()
    for item in out:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    if not deduped:
        deduped = ["default"]
    return deduped


def _resolve_query_probabilities(query_types: List[str], configured: Mapping[str, float]) -> Dict[str, float]:
    if not configured:
        p = 1.0 / float(len(query_types))
        return {query_type: p for query_type in query_types}

    selected = {query_type: float(configured.get(query_type, 0.0)) for query_type in query_types}
    if sum(selected.values()) <= 0.0:
        raise BuildError("configured query_weights must have at least one positive weight for supported query types")
    return _normalize_weights(selected)


def _expected_query_counts(tasks: List[BuildTaskConfig]) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    for task in tasks:
        if task.expected_query_counts:
            out[task.task_id] = {
                str(query_type): int(count)
                for query_type, count in task.expected_query_counts.items()
            }
    return out


def _aggregate_sampling_probabilities(task_probabilities: Mapping[str, float]) -> tuple[Dict[str, float], Dict[str, float]]:
    domain_probs: Dict[str, float] = {}
    task_group_probs: Dict[str, float] = {}
    for task_id, probability in task_probabilities.items():
        task = create_task(task_id)
        domain = str(getattr(task, "domain"))
        task_group = str(getattr(task, "task_group"))
        domain_probs[domain] = domain_probs.get(domain, 0.0) + float(probability)
        task_group_probs[task_group] = task_group_probs.get(task_group, 0.0) + float(probability)
    return dict(sorted(domain_probs.items())), dict(sorted(task_group_probs.items()))


def _build_staging(
    config: BuildConfig,
    *,
    stage_root: Path,
    code_hash: str,
    type_registry: TypeRegistry,
) -> _BuildStageResult:
    if stage_root.exists():
        shutil.rmtree(stage_root)
    stage_root.mkdir(parents=True, exist_ok=True)

    target_counts_by_task, task_probabilities, sampler_mode = _resolve_task_targets(config)
    domain_probs, task_group_probs = _aggregate_sampling_probabilities(task_probabilities)

    warning_messages: List[str] = []
    instances: List[Dict[str, Any]] = []
    curriculum: List[Dict[str, Any]] = []

    accepted_by_task: Dict[str, int] = {}
    rejected_by_task: Dict[str, int] = {}
    rejected_reason_by_task: Dict[str, Dict[str, int]] = {}
    accepted_query_counts_by_task: Dict[str, Dict[str, int]] = {}
    query_sampling_probabilities_by_task: Dict[str, Dict[str, float]] = {}
    evidence_format_map: Dict[str, str] = {}

    with TraceShardWriter(stage_root) as trace_writer:
        for task_cfg in config.tasks:
            task = create_task(task_cfg.task_id)
            task_target = int(target_counts_by_task.get(task_cfg.task_id, 0))
            accepted = 0
            rejected = 0
            rejection_reasons: Dict[str, int] = {}
            accepted_query_counts: Dict[str, int] = {}
            seed_index = 0
            max_candidates = max(1, task_target * 20)

            query_types = _resolve_query_types(task, task_cfg.params)
            query_probabilities = _resolve_query_probabilities(query_types, task_cfg.query_weights)
            query_sampling_probabilities_by_task[task_cfg.task_id] = dict(sorted(query_probabilities.items()))

            while accepted < task_target and seed_index < max_candidates:
                instance_seed = hash64(config.sampling_seed, f"{task_cfg.task_id}:instance_seed", seed_index)
                query_rng = random.Random(hash64(config.sampling_seed, f"{task_cfg.task_id}:query_sampler", seed_index))
                sampled_query_type = _weighted_choice(query_rng, query_probabilities)
                seed_index += 1

                params = dict(task_cfg.params)
                params["query_type"] = sampled_query_type
                try:
                    generated = task.generate(
                        instance_seed,
                        params=params,
                        max_attempts=config.max_attempts_per_instance,
                    )
                except Exception as exc:
                    rejected += 1
                    reason = type(exc).__name__
                    rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                    continue

                query_type_used = str(getattr(generated, "query_type", sampled_query_type) or sampled_query_type)
                if not type_registry.validate_answer_type(generated.answer_gt.type):
                    raise BuildError(f"unregistered answer type: {generated.answer_gt.type}")
                if not type_registry.validate_evidence_type(generated.evidence_gt.type):
                    raise BuildError(f"unregistered evidence type: {generated.evidence_gt.type}")

                image_rel_path = Path("images") / task.domain / task.task_id / f"{accepted:06d}.{config.image_format}"
                image_abs_path = stage_root / image_rel_path
                _save_image(generated.image, image_abs_path, config.image_format)
                image_hash = blake3_file(image_abs_path)

                image_record = ImageRecord(
                    image_id=generated.image_id,
                    format=config.image_format,
                    image_hash=image_hash,
                    path=str(image_rel_path.as_posix()),
                )

                partial_record = {
                    "instance_version": config.instance_version,
                    "instance_seed": int(instance_seed),
                    "domain": task.domain,
                    "task_group": task.task_group,
                    "task": task.task_id,
                    "prompt": generated.prompt,
                    "images": [image_record.to_dict()],
                    "answer_gt": generated.answer_gt.to_dict(),
                    "evidence_gt": generated.evidence_gt.to_dict(),
                    "versions": {
                        "seed_derivation_version": SEED_DERIVATION_VERSION,
                        **generated.task_versions,
                        "code_hash": code_hash,
                    },
                }
                instance_id = compute_instance_id(partial_record)

                trace_payload = dict(generated.trace_payload)
                query_spec = trace_payload.get("query_spec")
                if isinstance(query_spec, dict):
                    query_spec.setdefault("query_type", query_type_used)

                trace_instance = TraceInstance(
                    instance_id=instance_id,
                    scene_ir=trace_payload["scene_ir"],
                    query_spec=trace_payload["query_spec"],
                    render_spec=trace_payload["render_spec"],
                    render_map=trace_payload["render_map"],
                    execution_trace=trace_payload["execution_trace"],
                    witness_symbolic=trace_payload["witness_symbolic"],
                    projected_evidence=trace_payload["projected_evidence"],
                    answer_gt=generated.answer_gt,
                    evidence_gt=generated.evidence_gt,
                )
                trace_ref = trace_writer.append(trace_instance.to_dict())

                train = TrainInstance(
                    instance_version=config.instance_version,
                    instance_id=instance_id,
                    instance_seed=int(instance_seed),
                    domain=task.domain,
                    task_group=task.task_group,
                    task=task.task_id,
                    prompt=generated.prompt,
                    images=[image_record],
                    answer_gt=generated.answer_gt,
                    evidence_gt=generated.evidence_gt,
                    task_complexity=generated.complexity,
                    trace_ref=trace_ref,
                    versions={
                        "seed_derivation_version": SEED_DERIVATION_VERSION,
                        **generated.task_versions,
                        "code_hash": code_hash,
                    },
                )

                instances.append(train.to_dict())
                curriculum.append(
                    CurriculumIndex(
                        instance_id=instance_id,
                        domain=task.domain,
                        task_group=task.task_group,
                        task=task.task_id,
                        task_complexity=generated.complexity,
                    ).to_dict()
                )
                evidence_format_map[task.task_id] = generated.evidence_gt.type
                accepted_query_counts[query_type_used] = accepted_query_counts.get(query_type_used, 0) + 1
                accepted += 1

            accepted_by_task[task_cfg.task_id] = accepted
            rejected_by_task[task_cfg.task_id] = rejected
            rejected_reason_by_task[task_cfg.task_id] = dict(sorted(rejection_reasons.items()))
            accepted_query_counts_by_task[task_cfg.task_id] = dict(sorted(accepted_query_counts.items()))

            if accepted < task_target:
                warning_messages.append(
                    f"task {task_cfg.task_id} shortfall: expected {task_target}, accepted {accepted}"
                )

    _to_jsonl(stage_root / "train_instances.jsonl", instances)
    _to_jsonl(stage_root / "curriculum_index.jsonl", curriculum)

    return _BuildStageResult(
        instances=instances,
        curriculum=curriculum,
        target_counts_by_task=dict(sorted(target_counts_by_task.items())),
        task_sampling_probabilities=dict(sorted(task_probabilities.items())),
        sampler_mode=sampler_mode,
        accepted_by_task=dict(sorted(accepted_by_task.items())),
        rejected_by_task=dict(sorted(rejected_by_task.items())),
        rejected_reason_by_task=dict(sorted(rejected_reason_by_task.items())),
        evidence_format_map=dict(sorted(evidence_format_map.items())),
        accepted_query_counts_by_task={
            task_id: dict(sorted(counts.items()))
            for task_id, counts in sorted(accepted_query_counts_by_task.items())
        },
        query_sampling_probabilities_by_task={
            task_id: dict(sorted(probabilities.items()))
            for task_id, probabilities in sorted(query_sampling_probabilities_by_task.items())
        },
        domain_sampling_probabilities=domain_probs,
        task_group_sampling_probabilities=task_group_probs,
        warnings=warning_messages,
    )


def build_dataset(config: BuildConfig, *, code_hash: str = "local") -> Path:
    """Build a dataset into output_root and return finalized dataset path."""
    output_root = Path(config.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    type_registry_path = DEFAULT_REGISTRY_PATH
    type_registry = load_type_registry(type_registry_path)
    type_registry_hash = blake3_file(type_registry_path)

    dataset_id = _dataset_id_from_config(config, type_registry, type_registry_hash)

    temp_root = output_root / "tmp" / dataset_id
    repro_root = output_root / "tmp" / f"{dataset_id}__strict_repro"
    final_root = output_root / "datasets" / dataset_id
    failure_root = output_root / "failed_builds" / dataset_id

    if final_root.exists():
        raise BuildError(f"final dataset path already exists: {final_root}")

    validation_report: Dict[str, Any] | None = None
    warning_messages: List[str] = []

    try:
        primary = _build_staging(
            config,
            stage_root=temp_root,
            code_hash=code_hash,
            type_registry=type_registry,
        )
        warning_messages.extend(primary.warnings)

        if config.strict_repro:
            repro = _build_staging(
                config,
                stage_root=repro_root,
                code_hash=code_hash,
                type_registry=type_registry,
            )
            repro_mismatch = compare_staging_dirs(temp_root, repro_root)
            if repro_mismatch is not None:
                summary = json.dumps(repro_mismatch, ensure_ascii=False, sort_keys=True)
                raise BuildError(f"strict_repro_mismatch: {summary}")
            shutil.rmtree(repro_root)

        expected_query_counts = _expected_query_counts(config.tasks)
        validation_report = validate_dataset(
            primary.instances,
            staging_root=temp_root,
            expected_task_counts=primary.target_counts_by_task,
            expected_query_counts=expected_query_counts,
            observed_query_counts=primary.accepted_query_counts_by_task,
            dataset_id=dataset_id,
            expected_instance_version=config.instance_version,
        )
        _to_json_file(temp_root / "validation_report.json", validation_report)

        total_accepted = sum(primary.accepted_by_task.values())
        total_rejected = sum(primary.rejected_by_task.values())
        rejection_rate = (
            float(total_rejected) / float(total_accepted + total_rejected)
            if (total_accepted + total_rejected)
            else 0.0
        )

        build_report = {
            "build_report_schema_version": "v1",
            "dataset_id": dataset_id,
            "sampler": {
                "mode": primary.sampler_mode,
                "task_sampling_probabilities": primary.task_sampling_probabilities,
                "domain_sampling_probabilities": primary.domain_sampling_probabilities,
                "task_group_sampling_probabilities": primary.task_group_sampling_probabilities,
                "query_sampling_probabilities_by_task": primary.query_sampling_probabilities_by_task,
            },
            "accepted_counts_by_task": primary.accepted_by_task,
            "rejected_counts_by_task": primary.rejected_by_task,
            "rejection_reason_breakdown_by_task": primary.rejected_reason_by_task,
            "query_type_accepted_counts_by_task": primary.accepted_query_counts_by_task,
            "final_rejection_rate": rejection_rate,
            "resolved_evidence_format_map": primary.evidence_format_map,
            "trace_shard_manifest": {
                "shards": [
                    {
                        "shard_id": "trace_shard_0001.jsonl.zst",
                        "path": "traces/trace_shard_0001.jsonl.zst",
                        "record_count": len(primary.instances),
                    }
                ],
            },
            "trace_hash_policy": {
                "algorithm": "blake3",
                "canonicalization": "RFC8785 JCS",
                "seed_derivation_version": SEED_DERIVATION_VERSION,
            },
            "type_registry": {
                "type_registry_version": type_registry.version,
                "path": str(type_registry_path),
                "hash": type_registry_hash,
            },
            "code_provenance": {
                "code_hash": code_hash,
                "identity_input": False,
            },
            "split_metadata": None,
            "image_encoding": {
                "image_format": config.image_format,
                "compression": None,
                "color_mode": "RGB",
                "resolution_policy": "task_defined",
            },
            "warnings": warning_messages,
        }
        _to_json_file(temp_root / "build_report.json", build_report)

        if int(validation_report.get("total_errors", 0)) > 0:
            raise BuildError(f"validation failed with {validation_report['total_errors']} errors")

        final_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(temp_root), str(final_root))
        return final_root

    except Exception as exc:
        warning_messages.append(f"build_error: {exc}")
        try:
            if failure_root.exists():
                shutil.rmtree(failure_root)
            _write_failure_bundle(
                failure_root=failure_root,
                validation_report=validation_report,
                resolved_build_config=_serialize_config(config),
                warning_messages=warning_messages,
            )
        except Exception as bundle_exc:
            warning_messages.append(f"{error_codes.IO_FAILURE_BUNDLE_WRITE_FAILED}: {bundle_exc}")
        raise
