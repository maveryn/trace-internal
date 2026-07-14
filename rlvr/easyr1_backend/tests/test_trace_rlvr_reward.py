from __future__ import annotations

import json

import numpy as np
import torch
from tensordict import TensorDict

from examples.reward_function.trace_rlvr import compute_score
from verl.protocol import DataProto
from verl.trainer.metrics import reduce_reward_metrics
from verl.trainer.metrics import compute_length_metrics
from verl.utils.py_functional import unflatten_dict


def test_trace_reward_uses_ground_truth_alias_with_annotation_fields() -> None:
    reward_contract = {
        "reward_contract_version": "v0",
        "answer": {"id": "answer_exact_match_v0", "type": "integer"},
        "annotation": {"id": "bbox_set_soft_iou_v0", "type": "bbox_set"},
    }

    score = compute_score(
        [
            {
                "response": '{"answer": 3, "annotation": [[0, 0, 10, 10]]}',
                "response_length": 1,
                "ground_truth": json.dumps({"type": "integer", "value": 2}),
                "annotation_gt": json.dumps({"type": "bbox_set", "value": [[0, 0, 10, 10]]}),
                "reward_contract": json.dumps(reward_contract),
            }
        ],
        trace_output_mode="answer_and_annotation",
        trace_reward_mode="answer_and_annotation",
        trace_annotation_reward_formula="additive",
        trace_answer_weight=0.5,
        trace_annotation_weight=0.5,
        trace_format_weight=0.05,
    )[0]

    assert score["answer_reward"] == 0.0
    assert score["annotation_reward"] == 1.0
    assert score["task_reward_raw"] == 0.5
    assert score["overall"] == 0.525


def test_trace_reward_type_metrics_do_not_collide_with_scalar_reward_metric() -> None:
    reduced = reduce_reward_metrics(
        {
            "annotation_reward": [1.0, 0.0],
            "annotation_type_bbox": [1.0, 0.0],
            "annotation_type_point": [0.0, 1.0],
        }
    )

    assert reduced["reward/annotation_reward"] == 0.5
    assert reduced["reward/annotation_reward_by_type/bbox"] == 1.0
    assert reduced["reward/annotation_reward_by_type/point"] == 0.0
    assert "reward/annotation_reward/bbox" not in reduced
    unflattened = unflatten_dict(reduced)
    assert unflattened["reward"]["annotation_reward"] == 0.5


def test_task_conditioned_reward_routes_mixed_batch_per_row() -> None:
    reward_contract = {
        "reward_contract_version": "v0",
        "answer": {"id": "answer_exact_match_v0", "type": "integer"},
        "annotation": {"id": "bbox_soft_iou_v0", "type": "bbox"},
    }
    common = {
        "response_length": 1,
        "ground_truth": json.dumps({"type": "integer", "value": 2}),
        "annotation_gt": json.dumps({"type": "bbox", "value": [0, 0, 10, 10]}),
        "reward_contract": json.dumps(reward_contract),
    }

    scores = compute_score(
        [
            {
                **common,
                "response": '{"answer":2}',
                "trace_output_mode": "answer",
                "trace_supervision_mode": "answer",
            },
            {
                **common,
                "response": '{"answer":2,"annotation":[0,0,10,10]}',
                "trace_output_mode": "answer_and_annotation",
                "trace_supervision_mode": "answer_and_annotation",
            },
        ],
        trace_output_mode="task_conditioned",
        trace_reward_mode="task_conditioned",
        trace_format_weight=0.0,
    )

    assert [score["overall"] for score in scores] == [1.0, 1.0]
    assert scores[0]["trace_reward_mode_answer"] == 1.0
    assert scores[1]["trace_reward_mode_answer_and_annotation"] == 1.0


def test_task_conditioned_metrics_report_mode_specific_rewards() -> None:
    reduced = reduce_reward_metrics(
        {
            "overall": [1.0, 0.0, 0.5, 1.0],
            "annotation_reward": [0.0, 0.0, 0.0, 1.0],
            "trace_reward_mode_answer": [1.0, 1.0, 0.0, 0.0],
            "trace_reward_mode_answer_and_annotation": [0.0, 0.0, 1.0, 1.0],
        }
    )

    assert reduced["reward/mode_count/answer"] == 2.0
    assert reduced["reward/mode_count/answer_and_annotation"] == 2.0
    assert reduced["reward/by_mode/answer/overall"] == 0.5
    assert reduced["reward/by_mode/answer_and_annotation/overall"] == 0.75


def test_length_metrics_report_mode_specific_response_means() -> None:
    responses = torch.zeros((4, 4), dtype=torch.long)
    attention_mask = torch.tensor(
        [
            [1, 1, 1, 1, 1, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 0, 0],
            [1, 1, 1, 1, 1, 1, 1, 0],
            [1, 1, 1, 1, 1, 1, 1, 1],
        ],
        dtype=torch.long,
    )
    batch = DataProto(
        batch=TensorDict(
            {
                "responses": responses,
                "attention_mask": attention_mask,
            },
            batch_size=[4],
        ),
        non_tensor_batch={
            "trace_output_mode": np.array(
                ["answer", "answer_and_annotation", "answer", "answer_and_annotation"],
                dtype=object,
            )
        },
    )

    metrics = compute_length_metrics(batch)

    assert metrics["response_length/mean"] == 2.5
    assert metrics["response_length/by_mode/answer/mean"] == 2.0
    assert metrics["response_length/by_mode/answer_and_annotation/mean"] == 3.0
