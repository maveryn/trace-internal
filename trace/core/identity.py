"""Deterministic identity helpers for Trace records."""

from __future__ import annotations

from typing import Any, Dict

from .canonical import canonical_json_bytes
from .hash_utils import blake3_hex


def _build_instance_identity_payload(train_instance: Dict[str, Any]) -> Dict[str, Any]:
    """Construct canonical identity payload from training-facing fields.

    Note: image file paths are excluded by design; only image content identity is included.
    """
    images = [
        {
            "image_id": image.get("image_id"),
            "format": image.get("format"),
            "image_hash": image.get("image_hash"),
        }
        for image in train_instance.get("images", [])
    ]
    payload = {
        "instance_version": train_instance.get("instance_version"),
        "instance_seed": train_instance.get("instance_seed"),
        "domain": train_instance.get("domain"),
        "task": train_instance.get("task"),
        "prompt": train_instance.get("prompt"),
        "prompt_variants": dict(train_instance.get("prompt_variants", {})),
        "images": images,
        "answer_gt": train_instance.get("answer_gt"),
        "annotation_gt": train_instance.get("annotation_gt"),
        "reward_contract": train_instance.get("reward_contract"),
        "versions": train_instance.get("versions", {}),
    }
    if "scene_id" in train_instance:
        payload["scene_id"] = train_instance.get("scene_id")
    return payload


def compute_instance_id(train_instance: Dict[str, Any]) -> str:
    """Compute deterministic instance id from canonical training-facing payload."""
    payload = _build_instance_identity_payload(train_instance)
    return blake3_hex(canonical_json_bytes(payload))
