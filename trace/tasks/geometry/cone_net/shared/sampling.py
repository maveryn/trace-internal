"""Sampling helpers for cone-net geometry cases."""

from __future__ import annotations

from typing import Any, Mapping

from trace.tasks.shared.deterministic_sampling import resolve_selection_index

from .state import ConeNetCase

CONE_NET_CASES: tuple[ConeNetCase, ...] = (
    ConeNetCase(9, 120),
    ConeNetCase(10, 144),
    ConeNetCase(12, 150),
    ConeNetCase(14, 180),
    ConeNetCase(15, 120),
    ConeNetCase(16, 135),
    ConeNetCase(18, 160),
    ConeNetCase(20, 162),
    ConeNetCase(21, 120),
    ConeNetCase(24, 150),
    ConeNetCase(24, 180),
    ConeNetCase(30, 144),
)


def resolve_cone_net_case(
    *,
    instance_seed: int,
    params: Mapping[str, Any],
    namespace: str,
) -> tuple[ConeNetCase, int]:
    """Select and validate one cone-net measurement case."""

    explicit_case = params.get("case_index")
    if explicit_case is None:
        selection_index = resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=str(namespace),
        )
        case_index = int(selection_index) % len(CONE_NET_CASES)
    else:
        case_index = int(explicit_case) % len(CONE_NET_CASES)

    selected = CONE_NET_CASES[int(case_index)]
    slant_height = int(params.get("slant_height", selected.slant_height))
    theta_degrees = int(params.get("theta_degrees", selected.theta_degrees))
    if slant_height <= 0:
        raise ValueError("cone net slant height must be positive")
    if not 0 < theta_degrees < 360:
        raise ValueError("cone net central angle must be between 0 and 360 degrees")
    return ConeNetCase(int(slant_height), int(theta_degrees)), int(case_index)


__all__ = ["CONE_NET_CASES", "resolve_cone_net_case"]
