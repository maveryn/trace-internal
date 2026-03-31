"""Public RLVR reward-contract metadata for TRACE instances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping


REWARD_CONTRACT_VERSION = "v1"
ANSWER_REWARD_CONTRACT_ID = "answer_exact_match_v1"

EVIDENCE_REWARD_CONTRACT_IDS = frozenset(
    {
        "bbox_set_iou_v1",
        "numeric_exact_v1",
        "symbolic_set_exact_v1",
        "sequence_exact_v1",
        "point_set_match_v1",
    }
)

_EVIDENCE_REWARD_BY_TYPE = {
    "bbox_set": "bbox_set_iou_v1",
    "integer": "numeric_exact_v1",
    "integer_list": "numeric_exact_v1",
    "label_set": "symbolic_set_exact_v1",
    "edge_set": "symbolic_set_exact_v1",
    "id_set": "symbolic_set_exact_v1",
    "label_sequence": "sequence_exact_v1",
    "label_path": "sequence_exact_v1",
    "id_path": "sequence_exact_v1",
    "grid_point_path": "sequence_exact_v1",
    "point_path": "sequence_exact_v1",
    "graph_point": "point_set_match_v1",
    "graph_point_set": "point_set_match_v1",
    "grid_point_set": "point_set_match_v1",
    "point_set": "point_set_match_v1",
}


@dataclass(frozen=True)
class RewardMatcherSpec:
    """One side of a public reward contract."""

    id: str
    type: str

    def to_dict(self) -> Dict[str, str]:
        return {"id": self.id, "type": self.type}


@dataclass(frozen=True)
class RewardContract:
    """Portable reward metadata stored with TRACE instances."""

    reward_contract_version: str
    answer: RewardMatcherSpec
    evidence: RewardMatcherSpec

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reward_contract_version": self.reward_contract_version,
            "answer": self.answer.to_dict(),
            "evidence": self.evidence.to_dict(),
        }


def resolve_evidence_reward_contract_id(evidence_type: str) -> str:
    """Resolve the public evidence reward id for one evidence type."""

    normalized = str(evidence_type).strip()
    if not normalized:
        raise ValueError("reward_contract requires a non-empty evidence type")
    resolved = _EVIDENCE_REWARD_BY_TYPE.get(normalized)
    if resolved is None:
        raise ValueError(f"unsupported evidence type for reward_contract: {normalized}")
    return resolved


def resolve_reward_contract(*, answer_type: str, evidence_type: str) -> RewardContract:
    """Resolve the public reward contract for one TRACE instance."""

    normalized_answer_type = str(answer_type).strip()
    normalized_evidence_type = str(evidence_type).strip()
    if not normalized_answer_type:
        raise ValueError("reward_contract requires a non-empty answer type")
    evidence_contract_id = resolve_evidence_reward_contract_id(normalized_evidence_type)
    return RewardContract(
        reward_contract_version=REWARD_CONTRACT_VERSION,
        answer=RewardMatcherSpec(id=ANSWER_REWARD_CONTRACT_ID, type=normalized_answer_type),
        evidence=RewardMatcherSpec(id=evidence_contract_id, type=normalized_evidence_type),
    )


def validate_reward_contract_payload(
    payload: Mapping[str, Any],
    *,
    answer_type: str | None = None,
    evidence_type: str | None = None,
) -> str | None:
    """Return a human-readable validation message when a payload is invalid."""

    if not isinstance(payload, Mapping):
        return "reward_contract must be an object"

    version = payload.get("reward_contract_version")
    if version != REWARD_CONTRACT_VERSION:
        return f"reward_contract_version must be {REWARD_CONTRACT_VERSION!r}"

    answer = payload.get("answer")
    if not isinstance(answer, Mapping):
        return "reward_contract.answer must be an object with keys {id, type}"
    answer_id = answer.get("id")
    answer_payload_type = answer.get("type")
    if not isinstance(answer_id, str) or not answer_id:
        return "reward_contract.answer.id must be a non-empty string"
    if not isinstance(answer_payload_type, str) or not answer_payload_type:
        return "reward_contract.answer.type must be a non-empty string"
    if answer_id != ANSWER_REWARD_CONTRACT_ID:
        return f"reward_contract.answer.id must be {ANSWER_REWARD_CONTRACT_ID!r}"

    evidence = payload.get("evidence")
    if not isinstance(evidence, Mapping):
        return "reward_contract.evidence must be an object with keys {id, type}"
    evidence_id = evidence.get("id")
    evidence_payload_type = evidence.get("type")
    if not isinstance(evidence_id, str) or not evidence_id:
        return "reward_contract.evidence.id must be a non-empty string"
    if not isinstance(evidence_payload_type, str) or not evidence_payload_type:
        return "reward_contract.evidence.type must be a non-empty string"
    if evidence_id not in EVIDENCE_REWARD_CONTRACT_IDS:
        allowed = ", ".join(sorted(EVIDENCE_REWARD_CONTRACT_IDS))
        return f"reward_contract.evidence.id must be one of {{{allowed}}}"

    if answer_type is not None and str(answer_type).strip() != answer_payload_type:
        return "reward_contract.answer.type must match answer_gt.type"
    if evidence_type is not None and str(evidence_type).strip() != evidence_payload_type:
        return "reward_contract.evidence.type must match evidence_gt.type"

    if evidence_type is not None:
        try:
            expected_evidence_id = resolve_evidence_reward_contract_id(str(evidence_type))
        except ValueError as exc:
            return str(exc)
        if evidence_id != expected_evidence_id:
            return (
                "reward_contract.evidence.id must match the resolved contract for "
                f"evidence_gt.type ({expected_evidence_id})"
            )

    return None
