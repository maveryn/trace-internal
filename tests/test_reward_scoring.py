"""TRACE core reward-scoring tests."""

from __future__ import annotations

import json

import numpy as np

from trace.core.reward_scoring import score_trace_response


def _reward_contract(evidence_id: str, evidence_type: str, answer_type: str = "integer") -> dict[str, object]:
    return {
        "reward_contract_version": "v0",
        "answer": {"id": "answer_exact_match_v0", "type": answer_type},
        "evidence": {"id": evidence_id, "type": evidence_type},
    }


def test_core_reward_scoring_uses_trace_v0_contract_ids() -> None:
    score = score_trace_response(
        response='{"answer":2,"evidence":[[10,10,20,20]]}',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "bbox_set", "value": [[10, 10, 20, 20]]},
        reward_contract=_reward_contract("bbox_set_soft_iou_v0", "bbox_set"),
    )

    assert score["overall"] == 1.0
    assert score["answer_reward"] == 1.0
    assert score["evidence_reward"] == 1.0


def test_core_reward_scoring_scores_keyed_point_map_by_shared_keys() -> None:
    response = json.dumps({"answer": 2, "evidence": {"A": [132, 200], "extra": [0, 0]}})
    score = score_trace_response(
        response=response,
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "keyed_point_map", "value": {"A": [100, 200], "B": [320, 420]}},
        reward_contract=_reward_contract("keyed_point_map_soft_distance_v0", "keyed_point_map"),
        point_half_life_px=32.0,
    )

    assert np.isclose(score["evidence_reward"], 0.5 / 3.0)
    assert score["evidence_parse_ok"] == 1.0
    assert score["evidence_shared_key_count"] == 1.0
    assert score["evidence_missing_key_count"] == 1.0
    assert score["evidence_extra_key_count"] == 1.0


def test_core_reward_scoring_scores_keyed_bbox_map_by_shared_keys() -> None:
    response = json.dumps(
        {
            "answer": 2,
            "evidence": {
                "source": [10, 10, 20, 20],
                "extra": [0, 0, 5, 5],
            },
        }
    )
    score = score_trace_response(
        response=response,
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={
            "type": "keyed_bbox_map",
            "value": {
                "source": [10, 10, 20, 20],
                "target": [30, 30, 40, 40],
            },
        },
        reward_contract=_reward_contract("keyed_bbox_map_soft_iou_v0", "keyed_bbox_map"),
    )

    assert np.isclose(score["evidence_reward"], 1.0 / 3.0)
    assert score["evidence_parse_ok"] == 1.0
    assert score["evidence_shared_key_count"] == 1.0
    assert score["evidence_missing_key_count"] == 1.0
    assert score["evidence_extra_key_count"] == 1.0


def test_core_reward_scoring_accepts_legacy_v1_evidence_contract_alias() -> None:
    score = score_trace_response(
        response='{"answer":2,"evidence":[[10,10,20,20]]}',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "bbox_set", "value": [[10, 10, 20, 20]]},
        reward_contract={
            "reward_contract_version": "v1",
            "answer": {"id": "answer_exact_match_v1", "type": "integer"},
            "evidence": {"id": "bbox_set_soft_iou_v1", "type": "bbox_set"},
        },
    )

    assert score["overall"] == 1.0
    assert score["evidence_reward"] == 1.0
