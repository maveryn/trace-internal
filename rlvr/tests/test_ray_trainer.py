import numpy as np

from verl.trainer.ray_trainer import build_rollout_group_uids, compute_uid_group_reward_metrics


def test_build_rollout_group_uids_prefers_exported_uid() -> None:
    uids = np.array(["u0", "u1"], dtype=object)
    batch = {
        "uid": uids,
        "instance_id": np.array(["i0", "i1"], dtype=object),
    }

    resolved = build_rollout_group_uids(batch, batch_size=2)

    assert resolved is uids


def test_build_rollout_group_uids_falls_back_to_instance_id() -> None:
    instance_ids = np.array(["i0", "i1"], dtype=object)
    batch = {
        "instance_id": instance_ids,
    }

    resolved = build_rollout_group_uids(batch, batch_size=2)

    assert resolved is instance_ids


def test_build_rollout_group_uids_generates_uuid_fallback() -> None:
    resolved = build_rollout_group_uids({}, batch_size=3)

    assert resolved.shape == (3,)
    assert resolved.dtype == object
    assert len(set(resolved.tolist())) == 3


def test_compute_uid_group_reward_metrics_uses_best_rollout_per_prompt() -> None:
    metrics = compute_uid_group_reward_metrics(
        uid_list=["p0", "p0", "p1", "p1", "p2", "p2"],
        seq_scores=np.array([0.0, 0.0, 0.5, 1.0, 0.2, 0.3], dtype=np.float32),
        zero_solve_threshold=0.0,
    )

    assert metrics["rlvr_stats/zero_solve_count"] == 1.0
    assert metrics["rlvr_stats/zero_solve_rate"] == (1.0 / 3.0)
    assert metrics["rlvr_stats/perfect_solve_count"] == 1.0
    assert metrics["rlvr_stats/perfect_solve_rate"] == (1.0 / 3.0)
