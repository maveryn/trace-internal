"""Documents-domain visual-default loader helpers."""

from __future__ import annotations

from typing import Any, Dict

from ...shared.visual_defaults import default_noise_fallback, load_task_group_background_defaults, load_task_group_noise_defaults


def paper_background_fallback() -> Dict[str, Any]:
    """Return the canonical low-structure paper-like background fallback."""

    return {
        "enabled": True,
        "styles": {
            "paper_light": {
                "kind": "solid",
                "color": [241, 241, 238],
            }
        },
        "weights": {"paper_light": 1.0},
    }


def load_documents_background_defaults(*, task_group: str) -> Dict[str, Any]:
    """Load documents-task background config with the canonical fallback."""

    return load_task_group_background_defaults(
        domain="documents",
        task_group=str(task_group),
        fallback=paper_background_fallback(),
        merge_with_fallback=True,
    )


def load_documents_noise_defaults(*, task_group: str, apply_prob: float) -> Dict[str, Any]:
    """Load documents-task post-image noise config with the canonical fallback."""

    return load_task_group_noise_defaults(
        domain="documents",
        task_group=str(task_group),
        fallback=default_noise_fallback(apply_prob=float(apply_prob)),
        merge_with_fallback=False,
    )


__all__ = [
    "load_documents_background_defaults",
    "load_documents_noise_defaults",
    "paper_background_fallback",
]
