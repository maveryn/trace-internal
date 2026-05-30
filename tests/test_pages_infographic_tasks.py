"""Behavior tests for pages infographic arithmetic tasks."""

from __future__ import annotations

import json

import pytest

from trace.tasks.pages.infographic.metric_arithmetic_value import (
    COLUMN_PROFILE_COMPARISON_VARIANTS,
    FACT_LOOKUP_VARIANTS,
    FILTERED_SECTION_EXTREMUM_VARIANTS,
    FILTERED_METRIC_TOTAL_VARIANTS,
    SECTION_RANKED_TOTAL_VARIANTS,
    SUPPORTED_QUERY_IDS,
    PagesInfographicFactLookupLabelTask,
    PagesInfographicMetricArithmeticValuePublicTask,
    PagesInfographicSectionRankLabelTask,
)


METRIC_VALUE_QUERY_IDS = (
    *SUPPORTED_QUERY_IDS,
    *FILTERED_METRIC_TOTAL_VARIANTS,
    *COLUMN_PROFILE_COMPARISON_VARIANTS,
)
SECTION_RANK_QUERY_IDS = (
    *SECTION_RANKED_TOTAL_VARIANTS,
    *FILTERED_SECTION_EXTREMUM_VARIANTS,
)
FACT_LOOKUP_QUERY_IDS = FACT_LOOKUP_VARIANTS


def _extract_prompt_json_example(prompt: str) -> dict:
    marker = "Example JSON:\n"
    assert marker in str(prompt)
    payload = str(prompt).split(marker, 1)[1].strip()
    return json.loads(payload)


def _expected_answer(trace: dict) -> int | str:
    values_by_label = {str(label): int(value) for label, value in trace["values_by_label"].items()}
    target_labels = [str(label) for label in trace["target_labels"]]
    variant = str(trace.get("internal_query_id") or trace.get("source_query_id") or trace.get("query_id") or trace["query_id"])
    if variant == "sum_named_metrics":
        return int(sum(values_by_label[label] for label in target_labels))
    if variant == "section_extrema_arithmetic":
        value_a = values_by_label[str(trace["target_groups"]["section_a_extremum"][0])]
        value_b = values_by_label[str(trace["target_groups"]["section_b_extremum"][0])]
        if str(trace["extrema_operation"]) == "sum":
            return int(value_a + value_b)
        return int(abs(value_a - value_b))
    if variant == "section_total_extrema_difference":
        group_a = [str(label) for label in trace["target_groups"]["highest_total_section"]]
        group_b = [str(label) for label in trace["target_groups"]["lowest_total_section"]]
        return int(sum(values_by_label[label] for label in group_a) - sum(values_by_label[label] for label in group_b))
    if variant == "section_total_except_named":
        included = [str(label) for label in trace["target_groups"]["included"]]
        return int(sum(values_by_label[label] for label in included))
    if variant == "section_icon_total_value":
        included = [str(label) for label in trace["target_groups"]["filtered_icon_cards"]]
        return int(sum(values_by_label[label] for label in included))
    if variant == "section_icon_total_difference_value":
        group_a = [str(label) for label in trace["target_groups"]["section_a_filtered_icon_cards"]]
        group_b = [str(label) for label in trace["target_groups"]["section_b_filtered_icon_cards"]]
        total_a = sum(values_by_label[label] for label in group_a)
        total_b = sum(values_by_label[label] for label in group_b)
        return int(abs(total_a - total_b))
    if variant == "section_icon_extremum_label":
        direction = str(trace["rank_direction"])
        totals = {str(section): int(total) for section, total in trace["filtered_section_totals"].items()}
        target_total = max(totals.values()) if direction == "highest" else min(totals.values())
        winners = [section for section, total in totals.items() if int(total) == int(target_total)]
        assert len(winners) == 1
        return str(winners[0])
    if variant == "value_for_named_item":
        return str(values_by_label[target_labels[0]])
    if variant == "item_for_named_value":
        return str(target_labels[0])
    if variant == "detail_for_named_item":
        cards = {str(card["label"]): dict(card) for card in trace["cards"]}
        return f"Ref {int(cards[target_labels[0]]['caption_number'])}"
    raise AssertionError(f"unsupported variant: {variant}")


def _assert_bbox_inside_canvas(bbox: list[float], *, width: int, height: int) -> None:
    assert len(bbox) == 4
    x0, y0, x1, y1 = [float(value) for value in bbox]
    assert 0 <= x0 < x1 <= width
    assert 0 <= y0 < y1 <= height


@pytest.mark.parametrize("query_id", METRIC_VALUE_QUERY_IDS)
def test_pages_infographic_metric_arithmetic_variants_match_contract(query_id: str) -> None:
    task = PagesInfographicMetricArithmeticValuePublicTask()
    out = task.generate(
        97100 + METRIC_VALUE_QUERY_IDS.index(query_id),
        params={"query_id": query_id, "card_count": 20, "section_count": 4, "operand_count": 4},
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert out.query_id == query_id
    assert out.answer_gt.type == "integer"
    assert out.evidence_gt.type == "keyed_bbox_map"
    assert sorted(out.prompt_variants.keys()) == ["answer_and_evidence", "answer_only"]
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    assert int(execution["card_count"]) == 20
    assert int(execution["section_count"]) == 4
    assert len(execution["cards"]) == 20
    assert len(trace["scene_ir"]["entities"]) == 20
    assert set(trace["render_map"]["label_bboxes_px"].keys()) == set(execution["labels"])
    assert set(trace["render_map"]["value_bboxes_px"].keys()) == set(execution["labels"])

    expected = _expected_answer(execution)
    assert int(out.answer_gt.value) == int(expected)
    assert int(execution["answer_value"]) == int(expected)
    assert int(trace["query_spec"]["params"]["target_answer"]) == int(expected)
    assert trace["projected_evidence"]["keyed_bbox_map"] == out.evidence_gt.value

    target_labels = [str(label) for label in execution["target_labels"]]
    evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value.values()]
    assert len(evidence_bboxes) == len(target_labels)
    assert set(out.evidence_gt.value.keys()) == set(target_labels)
    for bbox in evidence_bboxes:
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))

    for label in target_labels:
        assert trace["projected_evidence"]["card_bbox_map"][label] == out.evidence_gt.value[label]
    for value in execution["target_values"]:
        assert isinstance(int(value), int)
    assert set(execution["target_groups"].keys()).issubset(
        {
            "highest_total_section",
            "included",
            "lowest_total_section",
            "excluded",
            "section_a_extremum",
            "section_b_extremum",
            "filtered_icon_cards",
            "section_a_filtered_icon_cards",
            "section_b_filtered_icon_cards",
        }
    )

    example = _extract_prompt_json_example(out.prompt)
    assert sorted(example.keys()) == ["answer", "evidence"]
    assert isinstance(example["answer"], int)
    assert isinstance(example["evidence"], dict)


def test_pages_infographic_metric_arithmetic_is_deterministic() -> None:
    task = PagesInfographicMetricArithmeticValuePublicTask()
    params = {"query_id": "sum_named_metrics", "card_count": 22, "section_count": 4, "operand_count": 5}
    out_a = task.generate(98231, params=params, max_attempts=10)
    out_b = task.generate(98231, params=params, max_attempts=10)

    assert out_a.prompt == out_b.prompt
    assert out_a.answer_gt.to_dict() == out_b.answer_gt.to_dict()
    assert out_a.evidence_gt.to_dict() == out_b.evidence_gt.to_dict()
    assert out_a.trace_payload["execution_trace"] == out_b.trace_payload["execution_trace"]
    assert out_a.complexity.to_dict() == out_b.complexity.to_dict()


def test_pages_infographic_metric_arithmetic_supports_larger_variable_sections() -> None:
    task = PagesInfographicMetricArithmeticValuePublicTask()
    out = task.generate(
        98531,
        params={"query_id": "section_total_except_named", "card_count": 30, "section_count": 6},
        max_attempts=10,
    )

    trace = out.trace_payload["execution_trace"]
    render = out.trace_payload["render_spec"]
    assert int(trace["card_count"]) == 30
    assert int(trace["section_count"]) == 6
    assert trace["section_card_counts"] == [5, 5, 5, 5, 5, 5]
    assert int(trace["target_operand_count"]) >= 3
    assert out.image.size == (int(render["canvas_width"]), int(render["canvas_height"]))
    for card in trace["cards"]:
        _assert_bbox_inside_canvas(card["card_bbox_px"], width=int(render["canvas_width"]), height=int(render["canvas_height"]))


def test_pages_infographic_metric_arithmetic_complexity_components_are_normalized() -> None:
    task = PagesInfographicMetricArithmeticValuePublicTask()
    out = task.generate(99231, params={"query_id": "section_total_except_named"}, max_attempts=10)

    complexity = out.complexity.to_dict()
    assert 0.0 <= float(complexity["complexity_score"]) <= 1.0
    assert set(complexity["complexity_components"].keys()) == {
        "reasoning_load",
        "scene_variant_load",
        "visual_scan",
    }
    assert all(0.0 <= float(value) <= 1.0 for value in complexity["complexity_components"].values())


def test_pages_infographic_section_ranked_total_label_matches_contract() -> None:
    task = PagesInfographicSectionRankLabelTask()
    out = task.generate(
        99421,
        params={
            "query_id": "section_ranked_total_label",
            "card_count": 24,
            "section_count": 4,
            "rank_direction": "highest",
            "rank_position": 2,
        },
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert out.query_id == "section_ranked_total_label"
    assert execution["source_query_id"] == "section_ranked_total_label"
    assert out.answer_gt.type == "string"
    assert out.evidence_gt.type == "keyed_bbox_map"
    assert execution["question_format"] == "label_open"
    assert execution["answer_type"] == "string"
    assert execution["rank_direction"] == "highest"
    assert int(execution["rank_position"]) == 2

    ranked = sorted(
        ((str(section), int(total)) for section, total in execution["section_totals"].items()),
        key=lambda item: item[1],
        reverse=True,
    )
    expected_section = ranked[1][0]
    assert str(out.answer_gt.value) == expected_section
    assert str(execution["answer_value"]) == expected_section
    assert str(trace["query_spec"]["params"]["target_answer"]) == expected_section

    target_labels = [str(label) for label in execution["target_groups"]["answer_section"]]
    evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value.values()]
    assert len(target_labels) == execution["section_card_counts"][execution["section_titles"].index(expected_section)]
    assert len(evidence_bboxes) == len(target_labels)
    assert set(out.evidence_gt.value.keys()) == set(target_labels)
    for bbox in evidence_bboxes:
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))

    example = _extract_prompt_json_example(out.prompt)
    assert sorted(example.keys()) == ["answer", "evidence"]
    assert isinstance(example["answer"], str)
    assert isinstance(example["evidence"], dict)


@pytest.mark.parametrize("query_id", SECTION_RANK_QUERY_IDS)
def test_pages_infographic_section_rank_label_variants_match_contract(query_id: str) -> None:
    task = PagesInfographicSectionRankLabelTask()
    out = task.generate(
        99731 + SECTION_RANK_QUERY_IDS.index(query_id),
        params={"query_id": query_id, "card_count": 24, "section_count": 4},
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]

    assert out.query_id == query_id
    assert execution["source_query_id"] == query_id
    assert out.scene_id == "infographic"
    if query_id == "section_icon_extremum_label":
        assert execution["answer_type"] == "string"
        assert execution["question_format"] == "label_open"
        expected = _expected_answer(execution)
        assert str(out.answer_gt.value) == str(expected)
        assert str(trace["query_spec"]["params"]["target_answer"]) == str(out.answer_gt.value)
        assert execution["comparison_icon_kind"]
        assert execution["rank_direction"] in {"highest", "lowest"}
    else:
        assert execution["answer_type"] == "string"
        assert execution["question_format"] == "label_open"
        ranked = sorted(
            ((str(section), int(total)) for section, total in execution["section_totals"].items()),
            key=lambda item: item[1],
            reverse=str(execution["rank_direction"]) == "highest",
        )
        expected = ranked[int(execution["rank_position"]) - 1][0]
        assert str(out.answer_gt.value) == expected
        assert str(trace["query_spec"]["params"]["target_answer"]) == expected
    assert trace["projected_evidence"]["keyed_bbox_map"] == out.evidence_gt.value


@pytest.mark.parametrize("query_id", FACT_LOOKUP_QUERY_IDS)
def test_pages_infographic_fact_lookup_variants_match_contract(query_id: str) -> None:
    task = PagesInfographicFactLookupLabelTask()
    out = task.generate(
        100731 + FACT_LOOKUP_QUERY_IDS.index(query_id),
        params={"query_id": query_id, "card_count": 24, "section_count": 4},
        max_attempts=10,
    )
    trace = out.trace_payload
    execution = trace["execution_trace"]
    render = trace["render_spec"]

    assert out.query_id == query_id
    assert execution["source_query_id"] == query_id
    assert out.scene_id == "infographic"
    assert out.answer_gt.type == "string"
    assert execution["answer_type"] == "string"
    assert execution["question_format"] == "label_open"
    assert execution["target_labels"]
    assert execution["target_sections"]

    expected = _expected_answer(execution)
    assert str(out.answer_gt.value) == str(expected)
    assert str(execution["answer_value"]) == str(expected)
    assert str(trace["query_spec"]["params"]["target_answer"]) == str(expected)

    evidence_targets = [dict(item) for item in execution["evidence_targets"]]
    assert evidence_targets
    evidence_bboxes = [[float(value) for value in bbox] for bbox in out.evidence_gt.value.values()]
    assert len(evidence_bboxes) == len(evidence_targets)
    assert trace["projected_evidence"]["keyed_bbox_map"] == out.evidence_gt.value
    assert trace["projected_evidence"]["evidence_targets"] == evidence_targets

    for bbox in evidence_bboxes:
        _assert_bbox_inside_canvas(bbox, width=int(render["canvas_width"]), height=int(render["canvas_height"]))

    target = evidence_targets[0]
    label = str(target["label"])
    if query_id == "value_for_named_item":
        assert evidence_targets == [{"label": label, "bbox_kind": "card"}]
        assert trace["projected_evidence"]["card_bbox_map"][label] == out.evidence_gt.value[label]
    elif query_id == "item_for_named_value":
        assert evidence_targets == [{"label": label, "bbox_kind": "card"}]
        assert trace["projected_evidence"]["card_bbox_map"][label] == out.evidence_gt.value[label]
        assert execution["target_value_text"]
    else:
        assert query_id == "detail_for_named_item"
        assert evidence_targets == [{"label": label, "bbox_kind": "card"}]
        assert trace["projected_evidence"]["card_bbox_map"][label] == out.evidence_gt.value[label]
        assert str(out.answer_gt.value).startswith("Ref ")

    example = _extract_prompt_json_example(out.prompt)
    assert sorted(example.keys()) == ["answer", "evidence"]
    assert isinstance(example["answer"], str)
    assert isinstance(example["evidence"], dict)
