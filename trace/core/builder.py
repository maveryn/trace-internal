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
from .json_io import write_json_file
from .reward_contracts import resolve_reward_contract
from .sampling import normalize_positive_weights, weighted_choice
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
    domain_sampling_probabilities: Dict[str, float]
    task_group_sampling_probabilities: Dict[str, float]
    warnings: List[str]


def _to_jsonl(path: Path, records: List[Dict[str, Any]]) -> None:
    """Write JSONL records with deterministic key ordering per row."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True))
            handle.write("\n")


def _serialize_task_config(task: BuildTaskConfig) -> Dict[str, Any]:
    """Serialize task config into dataset-id/report-friendly mapping."""
    return {
        "task_id": task.task_id,
        "count": task.count,
        "weight": task.weight,
        "params": dict(task.params),
    }


def _dataset_id_from_config(config: BuildConfig, type_registry: TypeRegistry, type_registry_hash: str) -> str:
    """Compute deterministic dataset id from build-critical configuration."""
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
    """Persist an image artifact in the requested build output format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format=image_format.upper())


def _serialize_config(config: BuildConfig) -> Dict[str, Any]:
    """Serialize build config for failure bundles and diagnostics."""
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
    """Persist failure diagnostics under `failed_builds/<dataset_id>/`."""
    failure_root.mkdir(parents=True, exist_ok=True)
    if validation_report is not None:
        write_json_file(failure_root / "validation_report.json", validation_report)
    write_json_file(failure_root / "resolved_build_config.json", resolved_build_config)
    write_json_file(failure_root / "log_reference.json", {"warnings": warning_messages})


def _ensure_unique_task_ids(tasks: List[BuildTaskConfig]) -> None:
    """Fail fast when build config contains duplicate task identifiers."""
    seen: set[str] = set()
    for task in tasks:
        if task.task_id in seen:
            raise BuildError(f"duplicate task_id in config: {task.task_id}")
        seen.add(task.task_id)


def _resolve_task_targets(config: BuildConfig) -> tuple[Dict[str, int], Dict[str, float], str]:
    """Resolve per-task target counts and global task probabilities."""
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
    try:
        task_probabilities = normalize_positive_weights(configured_weights)
    except ValueError as exc:
        raise BuildError(str(exc)) from exc
    target_counts = {task.task_id: 0 for task in config.tasks}

    sampler_rng = random.Random(hash64(config.sampling_seed, "global_task_sampler", 0))
    for _ in range(int(config.num_instances)):
        sampled_task = weighted_choice(sampler_rng, task_probabilities)
        target_counts[sampled_task] += 1

    return target_counts, task_probabilities, "weighted_task_sampler"


def _aggregate_sampling_probabilities(task_probabilities: Mapping[str, float]) -> tuple[Dict[str, float], Dict[str, float]]:
    """Aggregate domain/task-group probabilities from task-level weights."""
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
    """Generate one staging dataset pass and return in-memory build summary."""
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
    evidence_format_map: Dict[str, str] = {}

    with TraceShardWriter(stage_root) as trace_writer:
        for task_cfg in config.tasks:
            task = create_task(task_cfg.task_id)
            task_target = int(target_counts_by_task.get(task_cfg.task_id, 0))
            accepted = 0
            rejected = 0
            rejection_reasons: Dict[str, int] = {}
            seed_index = 0
            max_candidates = max(1, task_target * 20)

            while accepted < task_target and seed_index < max_candidates:
                instance_seed = hash64(config.sampling_seed, f"{task_cfg.task_id}:instance_seed", seed_index)
                seed_index += 1

                params = dict(task_cfg.params)
                params["_sampling_index"] = int(seed_index - 1)
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

                task_variant_used = str(getattr(generated, "task_variant", "default") or "default")
                if not type_registry.validate_answer_type(generated.answer_gt.type):
                    raise BuildError(f"unregistered answer type: {generated.answer_gt.type}")
                if not type_registry.validate_evidence_type(generated.evidence_gt.type):
                    raise BuildError(f"unregistered evidence type: {generated.evidence_gt.type}")
                try:
                    reward_contract = resolve_reward_contract(
                        answer_type=generated.answer_gt.type,
                        evidence_type=generated.evidence_gt.type,
                    )
                except ValueError as exc:
                    raise BuildError(str(exc)) from exc

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
                    "prompt_variants": dict(getattr(generated, "prompt_variants", {}) or {}),
                    "images": [image_record.to_dict()],
                    "answer_gt": generated.answer_gt.to_dict(),
                    "evidence_gt": generated.evidence_gt.to_dict(),
                    "reward_contract": reward_contract.to_dict(),
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
                    query_spec.setdefault("task_variant", task_variant_used)

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
                    reward_contract=reward_contract,
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
                    prompt_variants=dict(getattr(generated, "prompt_variants", {}) or {}),
                    images=[image_record],
                    answer_gt=generated.answer_gt,
                    evidence_gt=generated.evidence_gt,
                    reward_contract=reward_contract,
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
                accepted += 1

            accepted_by_task[task_cfg.task_id] = accepted
            rejected_by_task[task_cfg.task_id] = rejected
            rejected_reason_by_task[task_cfg.task_id] = dict(sorted(rejection_reasons.items()))

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
            _build_staging(
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

        validation_report = validate_dataset(
            primary.instances,
            staging_root=temp_root,
            expected_task_counts=primary.target_counts_by_task,
            dataset_id=dataset_id,
            expected_instance_version=config.instance_version,
        )
        write_json_file(temp_root / "validation_report.json", validation_report)

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
            },
            "accepted_counts_by_task": primary.accepted_by_task,
            "rejected_counts_by_task": primary.rejected_by_task,
            "rejection_reason_breakdown_by_task": primary.rejected_reason_by_task,
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
        write_json_file(temp_root / "build_report.json", build_report)

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
