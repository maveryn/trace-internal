from __future__ import annotations

from verl.workers.rollout.vllm_rollout_spmd import _iter_stop_token_ids


def test_iter_stop_token_ids_accepts_scalar_and_list_values() -> None:
    assert _iter_stop_token_ids(None) == []
    assert _iter_stop_token_ids(42) == [42]
    assert _iter_stop_token_ids([151645, 151643]) == [151645, 151643]
