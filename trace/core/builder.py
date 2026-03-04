"""Dataset build pipeline for TRACE."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image

from ..tasks import create_task
from . import error_codes
from .canonical import canonical_json_bytes
from .config import BuildConfig, BuildTaskConfig
from .hash_utils import blake3_file, blake3_hex
from .identity import compute_instance_id
from .seed import SEED_DERIVATION_VERSION, hash64
from .trace_store import TraceShardWriter
from .type_registry import DEFAULT_REGISTRY_PATH, TypeRegistry, load_type_registry
from .types import CurriculumIndex, ImageRecord, TaskComplexity, TraceInstance, TrainInstance
from .validation import validate_dataset


class BuildError(RuntimeError):
    """Raised when a dataset build fails."""


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


def _dataset_id_from_config(config: BuildConfig, type_registry: TypeRegistry, type_registry_hash: str) -> str:
    payload = {
        "dataset_name": config.dataset_name,
        "instance_version": config.instance_version,
        "image_format": config.image_format,
        "strict_repro": config.strict_repro,
        "max_attempts_per_instance": config.max_attempts_per_instance,
        "sampling_seed": config.sampling_seed,
        "tasks": [
            {"task_id": task.task_id, "count": task.count, "params": task.params}
            for task in config.tasks
        ],
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
        "strict_repro": config.strict_repro,
        "max_attempts_per_instance": config.max_attempts_per_instance,
        "sampling_seed": config.sampling_seed,
        "tasks": [
            {"task_id": task.task_id, "count": task.count, "params": task.params}
            for task in config.tasks
        ],
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


def _expected_task_counts(tasks: List[BuildTaskConfig]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for task in tasks:
        out[task.task_id] = out.get(task.task_id, 0) + int(task.count)
    return out


def build_dataset(config: BuildConfig, *, code_hash: str = "local") -> Path:
    """Build a dataset into output_root and return finalized dataset path."""
    output_root = Path(config.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    type_registry_path = DEFAULT_REGISTRY_PATH
    type_registry = load_type_registry(type_registry_path)
    type_registry_hash = blake3_file(type_registry_path)

    dataset_id = _dataset_id_from_config(config, type_registry, type_registry_hash)

    temp_root = output_root / "tmp" / dataset_id
    final_root = output_root / "datasets" / dataset_id
    failure_root = output_root / "failed_builds" / dataset_id

    if temp_root.exists():
        shutil.rmtree(temp_root)
    temp_root.mkdir(parents=True, exist_ok=True)

    if final_root.exists():
        raise BuildError(f"final dataset path already exists: {final_root}")

    warning_messages: List[str] = []

    instances: List[Dict[str, Any]] = []
    curriculum: List[Dict[str, Any]] = []
    accepted_by_task: Dict[str, int] = {}
    rejected_by_task: Dict[str, int] = {}
    rejected_reason_by_task: Dict[str, Dict[str, int]] = {}
    evidence_format_map: Dict[str, str] = {}

    try:
        with TraceShardWriter(temp_root) as trace_writer:
            for task_cfg in config.tasks:
                task = create_task(task_cfg.task_id)
                accepted = 0
                rejected = 0
                rejection_reasons: Dict[str, int] = {}
                seed_index = 0
                max_candidates = max(1, int(task_cfg.count) * 20)

                while accepted < int(task_cfg.count) and seed_index < max_candidates:
                    instance_seed = hash64(config.sampling_seed, task_cfg.task_id, seed_index)
                    seed_index += 1
                    try:
                        generated = task.generate(
                            instance_seed,
                            params=task_cfg.params,
                            max_attempts=config.max_attempts_per_instance,
                        )
                    except Exception as exc:
                        rejected += 1
                        reason = type(exc).__name__
                        rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
                        continue

                    if not type_registry.validate_answer_type(generated.answer_gt.type):
                        raise BuildError(f"unregistered answer type: {generated.answer_gt.type}")
                    if not type_registry.validate_evidence_type(generated.evidence_gt.type):
                        raise BuildError(f"unregistered evidence type: {generated.evidence_gt.type}")

                    image_rel_path = Path("images") / task.domain / task.task_id / f"{accepted:06d}.{config.image_format}"
                    image_abs_path = temp_root / image_rel_path
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

                    trace_instance = TraceInstance(
                        instance_id=instance_id,
                        scene_ir=generated.trace_payload["scene_ir"],
                        query_spec=generated.trace_payload["query_spec"],
                        render_spec=generated.trace_payload["render_spec"],
                        render_map=generated.trace_payload["render_map"],
                        execution_trace=generated.trace_payload["execution_trace"],
                        witness_symbolic=generated.trace_payload["witness_symbolic"],
                        projected_evidence=generated.trace_payload["projected_evidence"],
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
                    train_dict = train.to_dict()
                    instances.append(train_dict)
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
                if accepted < int(task_cfg.count):
                    warning_messages.append(
                        f"task {task_cfg.task_id} shortfall: expected {task_cfg.count}, accepted {accepted}"
                    )

        _to_jsonl(temp_root / "train_instances.jsonl", instances)
        _to_jsonl(temp_root / "curriculum_index.jsonl", curriculum)

        expected_counts = _expected_task_counts(config.tasks)
        validation_report = validate_dataset(
            instances,
            staging_root=temp_root,
            expected_task_counts=expected_counts,
            dataset_id=dataset_id,
            expected_instance_version=config.instance_version,
        )
        _to_json_file(temp_root / "validation_report.json", validation_report)

        total_accepted = sum(accepted_by_task.values())
        total_rejected = sum(rejected_by_task.values())
        rejection_rate = (float(total_rejected) / float(total_accepted + total_rejected)) if (total_accepted + total_rejected) else 0.0

        build_report = {
            "build_report_schema_version": "v1",
            "dataset_id": dataset_id,
            "accepted_counts_by_task": dict(sorted(accepted_by_task.items())),
            "rejected_counts_by_task": dict(sorted(rejected_by_task.items())),
            "rejection_reason_breakdown_by_task": dict(sorted(rejected_reason_by_task.items())),
            "final_rejection_rate": rejection_rate,
            "resolved_evidence_format_map": dict(sorted(evidence_format_map.items())),
            "trace_shard_manifest": {
                "shards": [
                    {
                        "shard_id": "trace_shard_0001.jsonl.zst",
                        "path": "traces/trace_shard_0001.jsonl.zst",
                        "record_count": len(instances),
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
            try:
                if failure_root.exists():
                    shutil.rmtree(failure_root)
                _write_failure_bundle(
                    failure_root=failure_root,
                    validation_report=validation_report,
                    resolved_build_config=_serialize_config(config),
                    warning_messages=warning_messages,
                )
            except Exception as exc:
                warning_messages.append(
                    f"{error_codes.IO_FAILURE_BUNDLE_WRITE_FAILED}: {exc}"
                )
            raise BuildError(f"validation failed with {validation_report['total_errors']} errors")

        final_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(temp_root), str(final_root))
        return final_root

    except Exception:
        # Keep temp_root for debugging on failure.
        raise
