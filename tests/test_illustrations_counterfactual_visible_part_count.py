"""Contract tests for illustration counterfactual visible-part counting."""

from __future__ import annotations

from collections import Counter

from trace.tasks import TASK_REGISTRY, create_task
from trace.tasks.illustrations.counterfactual.visible_part_count import (
    AIRPLANE_VARIANT,
    BACKGROUND_STYLES,
    BICYCLE_VARIANT,
    BIRD_VARIANT,
    BUTTERFLY_VARIANT,
    CHAIR_VARIANT,
    CLOVER_VARIANT,
    FORK_VARIANT,
    GLOVE_VARIANT,
    QUADRUPED_VARIANT,
    SNOWFLAKE_VARIANT,
    STAR_VARIANT,
    SUPPORTED_QUERY_IDS,
    TASK_ID,
    TRAFFIC_LIGHT_VARIANT,
)


def test_illustrations_counterfactual_visible_part_count_is_registered() -> None:
    task = TASK_REGISTRY[TASK_ID]()
    assert task.domain == "illustrations"
    assert task.task_group == "counterfactual"
    assert task.default_dataset_enabled is True


def test_illustrations_counterfactual_visible_part_count_contracts_match_trace() -> None:
    cases = [
        (BIRD_VARIANT, 5, 2, "leg"),
        (QUADRUPED_VARIANT, 6, 4, "leg"),
        (AIRPLANE_VARIANT, 4, 2, "wing"),
        (BUTTERFLY_VARIANT, 6, 4, "wing"),
        (BICYCLE_VARIANT, 5, 2, "wheel"),
        (TRAFFIC_LIGHT_VARIANT, 5, 3, "lens"),
        (CLOVER_VARIANT, 6, 3, "leaf"),
        (STAR_VARIANT, 8, 5, "point"),
        (GLOVE_VARIANT, 7, 5, "finger"),
        (FORK_VARIANT, 6, 4, "tine"),
        (SNOWFLAKE_VARIANT, 8, 6, "arm"),
        (CHAIR_VARIANT, 6, 4, "leg"),
    ]
    task = create_task(TASK_ID)
    for index, (variant, answer, canonical, part_kind) in enumerate(cases):
        out = task.generate(2026052600 + index, params={"query_id": variant, "target_answer": answer}, max_attempts=20)
        trace = out.trace_payload
        assert out.scene_id == "single_object_figure"
        assert out.query_id == variant
        assert out.answer_gt.type == "integer"
        assert int(out.answer_gt.value) == int(answer)
        assert out.evidence_gt.type == "bbox_set"
        assert len(out.evidence_gt.value) == int(answer)
        assert trace["projected_evidence"]["bbox_set"] == out.evidence_gt.value
        assert trace["execution_trace"]["counted_part_kind"] == part_kind
        assert trace["execution_trace"]["canonical_bias_answer"] == canonical
        assert trace["execution_trace"]["counterfactual_delta"] == answer - canonical
        assert trace["execution_trace"]["counterfactual_edit_type"] == "visible_part_count_changed"
        colors = trace["render_spec"]["style"]["colors_rgb"]
        assert "primary" in colors
        assert "accent" in colors
        if variant == TRAFFIC_LIGHT_VARIANT:
            assert "traffic_casing" in colors
            assert "traffic_pole" in colors
            assert trace["render_spec"]["style"]["traffic_lens_color_policy"] == "fixed_signal_order"
            assert len(trace["render_spec"]["style"]["traffic_lens_colors_rgb"]) == answer
        if variant == CLOVER_VARIANT:
            assert "clover_fill" in colors
            assert "clover_accent" in colors
        background_style = trace["render_spec"]["style"]["background_style"]
        assert background_style["style_id"] in {style["style_id"] for style in BACKGROUND_STYLES}
        assert trace["render_spec"]["style"]["object_center_px"] != [480.0, 360.0]
        for box in out.evidence_gt.value:
            x0, y0, x1, y1 = [float(value) for value in box]
            assert 0 <= x0 < x1 <= out.image.width
            assert 0 <= y0 < y1 <= out.image.height
        assert all(0.0 <= float(value) <= 1.0 for value in out.complexity.complexity_components.values())


def test_illustrations_counterfactual_visible_part_count_sampling_balances_variants() -> None:
    task = create_task(TASK_ID)
    variants = Counter()
    answers = Counter()
    for index in range(240):
        out = task.generate(2026052700 + index, params={}, max_attempts=20)
        variants[str(out.query_id)] += 1
        answers[int(out.answer_gt.value)] += 1
    assert set(variants) == set(SUPPORTED_QUERY_IDS)
    assert min(variants.values()) >= 8
    assert max(variants.values()) <= 32
    assert set(answers) == {1, 2, 3, 4, 5, 6, 7, 8}
    assert max(answers.values()) <= 70
