from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np
from PIL import Image

if "qwen_vl_utils" not in sys.modules:
    vision_process = types.SimpleNamespace(fetch_video=lambda *args, **kwargs: [])
    sys.modules["qwen_vl_utils"] = types.SimpleNamespace(vision_process=vision_process)
    sys.modules["qwen_vl_utils.vision_process"] = vision_process

from examples.reward_function.reward_trace import compute_score
from verl.trainer.ppo.metric_utils import compute_rollout_group_metrics
from verl.utils.dataset import TraceRLHFDataset
from verl.utils.trace_mode import (
    default_trace_system_prompt_path,
    resolve_trace_prompt_key,
    resolve_trace_reward_mode,
    resolve_trace_system_prompt,
)
from verl.utils.trace_reward import score_trace_response


def _reward_contract(evidence_id: str, evidence_type: str, answer_type: str = "integer") -> dict[str, object]:
    return {
        "reward_contract_version": "v1",
        "answer": {"id": "answer_exact_match_v1", "type": answer_type},
        "evidence": {"id": evidence_id, "type": evidence_type},
    }


def test_trace_reward_supports_all_active_evidence_contracts() -> None:
    cases = [
        (
            {"answer": 3, "evidence": [[10, 10, 20, 20], [30, 30, 40, 40]]},
            {"type": "integer", "value": 3},
            {"type": "bbox_set", "value": [[10, 10, 20, 20], [30, 30, 40, 40]]},
            _reward_contract("bbox_set_iou_v1", "bbox_set"),
        ),
        (
            {"answer": 5, "evidence": [2, 4, 6]},
            {"type": "integer", "value": 5},
            {"type": "integer_list", "value": [2, 4, 6]},
            _reward_contract("numeric_exact_v1", "integer_list"),
        ),
        (
            {"answer": 2, "evidence": [["B", "D"], ["D", "G"]]},
            {"type": "integer", "value": 2},
            {"type": "edge_set", "value": [["D", "B"], ["G", "D"]]},
            _reward_contract("symbolic_set_exact_v1", "edge_set"),
        ),
        (
            {"answer": 2, "evidence": [[1, 1], [1, 2], [1, 3]]},
            {"type": "integer", "value": 2},
            {"type": "grid_point_path", "value": [[1, 1], [1, 2], [1, 3]]},
            _reward_contract("sequence_exact_v1", "grid_point_path"),
        ),
        (
            {"answer": 4, "evidence": [[0, 0], [4, 0], [0, 3]]},
            {"type": "integer", "value": 4},
            {"type": "graph_point_set", "value": [[0, 3], [0, 0], [4, 0]]},
            _reward_contract("point_set_match_v1", "graph_point_set"),
        ),
    ]

    for payload, answer_gt, evidence_gt, reward_contract in cases:
        response = f'<think>reasoning</think><answer>{json.dumps(payload)}</answer>'
        score = score_trace_response(
            response=response,
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            reward_contract=reward_contract,
        )
        assert score["overall"] == 1.0
        assert score["answer_reward"] == 1.0
        assert score["evidence_reward"] == 1.0
        assert score["format"] == 1.0


def test_trace_reward_answer_mode_ignores_evidence_in_overall() -> None:
    reward_contract = _reward_contract("symbolic_set_exact_v1", "label_set")

    score = score_trace_response(
        response='<think>reasoning</think><answer>{"answer":2}</answer>',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "label_set", "value": ["D", "B"]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["answer_reward"] == 1.0
    assert score["evidence_reward"] == 0.0
    assert score["overall"] == 1.0
    assert score["trace_reward_mode_answer"] == 1.0
    assert score["trace_reward_mode_answer_only"] == 1.0
    assert score["trace_reward_mode_answer_and_evidence"] == 0.0


def test_trace_reward_format_requires_answer_tag_json_not_think_tag() -> None:
    reward_contract = _reward_contract("symbolic_set_exact_v1", "label_set")

    score = score_trace_response(
        response='Reasoning outside tags is allowed. <answer>{"answer":2}</answer> trailing text is ignored.',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "label_set", "value": ["D", "B"]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["format"] == 1.0
    assert score["format_structure_ok"] == 1.0
    assert score["format_json_ok"] == 1.0
    assert score["format_schema_ok"] == 1.0
    assert score["answer_reward"] == 1.0


def test_trace_reward_format_rejects_non_json_inside_answer_tag() -> None:
    reward_contract = _reward_contract("symbolic_set_exact_v1", "label_set")

    score = score_trace_response(
        response='<answer>The answer is {"answer":2}</answer>',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "label_set", "value": ["D", "B"]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
    )

    assert score["format"] == 0.0
    assert score["format_structure_ok"] == 1.0
    assert score["format_json_ok"] == 0.0
    assert score["format_schema_ok"] == 0.0
    assert score["answer_reward"] == 1.0


def test_trace_reward_answer_mode_does_not_gate_correctness_on_format() -> None:
    reward_contract = _reward_contract("symbolic_set_exact_v1", "label_set")

    score = score_trace_response(
        response='The answer is {"answer":2}.',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "label_set", "value": ["D", "B"]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        format_weight=0.1,
    )

    assert score["answer_reward"] == 1.0
    assert score["format"] == 0.0
    assert score["overall"] == 0.9
    assert score["zero_reward"] == 0.0


def test_trace_reward_zero_reward_tracks_task_correctness_not_format_bonus() -> None:
    reward_contract = _reward_contract("symbolic_set_exact_v1", "label_set")

    score = score_trace_response(
        response='<answer>{"answer":3}</answer>',
        answer_gt={"type": "integer", "value": 2},
        evidence_gt={"type": "label_set", "value": ["D", "B"]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        format_weight=0.1,
    )

    assert score["answer_reward"] == 0.0
    assert score["format"] == 1.0
    assert score["overall"] == 0.1
    assert score["zero_reward"] == 1.0


def test_trace_reward_answer_scoring_mode_can_use_legacy_strict_matching() -> None:
    reward_contract = _reward_contract("symbolic_set_exact_v1", "label_set", answer_type="string")

    current = score_trace_response(
        response='<answer>{"answer":"The answer is B."}</answer>',
        answer_gt={"type": "string", "value": "B"},
        evidence_gt={"type": "label_set", "value": ["D", "B"]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="exact_json",
    )
    legacy = score_trace_response(
        response='<answer>{"answer":"The answer is B."}</answer>',
        answer_gt={"type": "string", "value": "B"},
        evidence_gt={"type": "label_set", "value": ["D", "B"]},
        reward_contract=reward_contract,
        trace_reward_mode="answer",
        trace_answer_scoring="legacy_strict",
    )

    assert current["answer_reward"] == 0.0
    assert current["trace_answer_scoring_exact_json"] == 1.0
    assert legacy["answer_reward"] == 1.0
    assert legacy["trace_answer_scoring_legacy_strict"] == 1.0


def test_trace_dataset_helpers_support_trace_rows(tmp_path: Path) -> None:
    image_path = tmp_path / "images" / "sample.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (12, 12), (255, 255, 255)).save(image_path)

    dataset = TraceRLHFDataset.__new__(TraceRLHFDataset)
    dataset.prompt_key = "prompt"
    dataset.answer_key = "answer"
    dataset.image_dir = None
    dataset.dataset_root = tmp_path
    dataset.system_prompt = "System contract"
    dataset.format_prompt = None
    dataset.format_prompt_variant = "boxed_only"
    dataset.image_key = "images"
    dataset.video_key = "videos"

    prompt_key, answer_key = dataset._resolve_prompt_answer_keys(
        {"prompt": "Solve it", "answer_gt": {"type": "integer", "value": 4}}
    )
    assert (prompt_key, answer_key) == ("prompt", "answer_gt")

    prompt_key, answer_key = dataset._resolve_prompt_answer_keys(
        {"prompt": "Solve it", "ground_truth": ["A"]}
    )
    assert (prompt_key, answer_key) == ("prompt", "ground_truth")

    dataset.prompt_key = "prompt_answer"
    dataset.answer_key = "answer_gt"
    prompt_key, answer_key = dataset._resolve_prompt_answer_keys(
        {"prompt_answer_only": "Solve it", "answer_gt": {"type": "integer", "value": 4}}
    )
    assert (prompt_key, answer_key) == ("prompt_answer_only", "answer_gt")

    messages = dataset._build_messages(
        {
            "prompt_answer": "What is shown?",
            "answer_gt": {"type": "integer", "value": 1},
            "images": [{"path": "images/sample.png"}],
        },
        prompt_key="prompt_answer",
    )
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    normalized = dataset._normalize_trace_metadata_fields(
        {
            "answer_gt": '{"type":"integer","value":2}',
            "reward_contract": '{"answer":{"id":"answer_exact_match_v1"}}',
        }
    )
    assert normalized["answer_gt"]["value"] == 2
    assert normalized["reward_contract"]["answer"]["id"] == "answer_exact_match_v1"


def test_trace_output_mode_resolves_prompt_reward_and_system_prompt_defaults() -> None:
    assert resolve_trace_prompt_key("auto", trace_output_mode="answer") == "prompt_answer"
    assert resolve_trace_prompt_key("auto", trace_output_mode="evidence") == "prompt_answer_and_evidence"
    assert resolve_trace_prompt_key("auto", trace_output_mode="answer_and_evidence") == "prompt_answer_and_evidence"
    assert resolve_trace_reward_mode("auto", trace_output_mode="answer") == "answer"
    assert resolve_trace_reward_mode("auto", trace_output_mode="evidence") == "answer_and_evidence"
    assert resolve_trace_reward_mode("auto", trace_output_mode="answer_and_evidence") == "answer_and_evidence"
    assert resolve_trace_reward_mode("answer_only", trace_output_mode="answer_and_evidence") == "answer"

    answer_prompt_path = default_trace_system_prompt_path(trace_output_mode="answer")
    evidence_alias_prompt_path = default_trace_system_prompt_path(trace_output_mode="evidence")
    evidence_prompt_path = default_trace_system_prompt_path(trace_output_mode="answer_and_evidence")
    assert answer_prompt_path.name == "trace_vero_json_system_prompt_answer.txt"
    assert evidence_alias_prompt_path == evidence_prompt_path
    assert evidence_prompt_path.name == "trace_vero_json_system_prompt_answer_and_evidence.txt"
    assert resolve_trace_system_prompt("auto", trace_output_mode="answer") == str(answer_prompt_path)
    assert resolve_trace_system_prompt("auto", trace_output_mode="evidence") == str(evidence_prompt_path)
    assert resolve_trace_system_prompt("auto", trace_output_mode="answer_and_evidence") == str(evidence_prompt_path)


def test_reward_trace_wrapper_returns_score_key() -> None:
    result = compute_score(
        data_source="trace",
        solution_str='<think>reasoning</think><answer>{"answer":2}</answer>',
        ground_truth=2,
        extra_info={
            "answer_gt": {"type": "integer", "value": 2},
            "evidence_gt": {"type": "label_set", "value": ["D", "B"]},
            "reward_contract": _reward_contract("symbolic_set_exact_v1", "label_set"),
        },
        trace_reward_mode="answer",
        trace_format_weight=0.1,
    )
    assert result["score"] == 1.0
    assert result["overall"] == 1.0


def test_reward_trace_wrapper_accepts_legacy_answer_scoring_mode() -> None:
    result = compute_score(
        data_source="trace",
        solution_str='<answer>{"answer":"The answer is B."}</answer>',
        ground_truth="B",
        extra_info={
            "answer_gt": {"type": "string", "value": "B"},
            "evidence_gt": {"type": "label_set", "value": ["D", "B"]},
            "reward_contract": _reward_contract("symbolic_set_exact_v1", "label_set", answer_type="string"),
        },
        trace_reward_mode="answer",
        trace_answer_scoring="legacy_strict",
        trace_format_weight=0.1,
    )
    assert result["answer_reward"] == 1.0
    assert result["trace_answer_scoring_legacy_strict"] == 1.0


def test_reward_trace_wrapper_uses_trace_output_mode_when_reward_mode_is_auto() -> None:
    result = compute_score(
        data_source="trace",
        solution_str='<think>reasoning</think><answer>{"answer":2}</answer>',
        ground_truth=2,
        extra_info={
            "answer_gt": {"type": "integer", "value": 2},
            "evidence_gt": {"type": "label_set", "value": ["D", "B"]},
            "reward_contract": _reward_contract("symbolic_set_exact_v1", "label_set"),
        },
        trace_reward_mode="auto",
        trace_output_mode="answer",
        trace_format_weight=0.1,
    )
    assert result["trace_reward_mode_answer"] == 1.0
    assert result["overall"] == 1.0


def test_rollout_group_metrics_are_grouped_by_uid() -> None:
    metrics = compute_rollout_group_metrics(
        ["a", "a", "b", "b"],
        np.array([0.0, 0.0, 1.0, 1.0]),
        zero_solve_threshold=0.0,
        perfect_solve_threshold=1.0,
    )
    assert metrics["rlvr_stats/zero_solve_count"] == 1.0
    assert metrics["rlvr_stats/perfect_solve_count"] == 1.0


def test_rollout_group_metrics_expect_task_scores_not_format_weighted_overall() -> None:
    # Prompt a has no correct rollout but every rollout would have been positive
    # under additive overall reward because of the format bonus.
    metrics = compute_rollout_group_metrics(
        ["a", "a", "b", "b"],
        np.array([0.0, 0.0, 1.0, 0.0]),
        zero_solve_threshold=0.0,
        perfect_solve_threshold=1.0,
    )
    assert metrics["rlvr_stats/zero_solve_count"] == 1.0
    assert metrics["rlvr_stats/perfect_solve_count"] == 0.0
