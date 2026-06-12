"""Relationship-label task over pedigree charts."""

from __future__ import annotations

from typing import Any, Dict

from ....core.types import TypedValue
from ...base import TaskOutput
from ...registry import register_task
from ...shared.output_metadata import default_task_versions
from .shared.task_common import (
    OPTION_LABELS,
    PEDIGREE_RELATIONSHIP_LABELS,
    SCENE_ID,
    PedigreeRelationshipQuerySample,
    _common_slots,
    _draw_pedigree_options,
    _person_label,
    _prompt_artifacts,
    _render_sample,
    _resolve_style,
    _sections_for_task,
    _select_relationship_options,
    _select_variant,
    _trace_payload,
    projected_keyed_pedigree_person_annotation,
    sample_pedigree_relationship,
)


RELATIONSHIP_TASK_ID = "task_graph__pedigree_chart__relationship_label"
SCENE_ID = "pedigree_chart"


@register_task
class GraphPedigreeRelationshipLabelTask:
    """Identify a relationship between two labeled people in a pedigree chart."""

    task_id = RELATIONSHIP_TASK_ID
    domain = "graph"
    scene_id = "pedigree_chart"
    supported_query_ids = ("relationship_label_between_two_people",)

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        for selector_key in ("query_id", "query_variant"):
            requested = params.get(selector_key)
            if requested is not None and str(requested) not in {"", "default", "relationship_label_between_two_people"}:
                raise ValueError(f"unsupported query_id for {self.task_id}: {requested}")
        gen_defaults, render_defaults, prompt_defaults = _sections_for_task(self.task_id)
        style = _resolve_style(int(instance_seed), params=params, gen_defaults=gen_defaults, rng_namespace=self.task_id)
        target_relationship, relationship_probs = _select_variant(
            int(instance_seed),
            rng_namespace=self.task_id,
            params=params,
            gen_defaults=gen_defaults,
            supported=PEDIGREE_RELATIONSHIP_LABELS,
            explicit_key="target_relationship",
            weights_key="relationship_label_weights",
        )
        sample_query: PedigreeRelationshipQuerySample = sample_pedigree_relationship(
            int(instance_seed),
            target_relationship=str(target_relationship),
            max_attempts=max(80, int(max_attempts)),
        )
        option_values, correct_option = _select_relationship_options(str(sample_query.answer))
        image, rendered_scene, render_params, background_meta, post_noise_meta = _render_sample(
            render_namespace=self.task_id,
            instance_seed=int(instance_seed),
            params=params,
            render_defaults=render_defaults,
            style=style,
            sample=sample_query.sample,
            highlighted_person_ids=(sample_query.person_a_id, sample_query.person_b_id),
            bottom_reserved_px=88,
        )
        _draw_pedigree_options(
            image=image,
            render_params=render_params,
            option_values_by_label=option_values,
        )
        annotation_projection = projected_keyed_pedigree_person_annotation(rendered_scene, sample_query.annotation_roles)
        prompt_artifacts = _prompt_artifacts(
            domain=self.domain,
            scene_id=SCENE_ID,
            prompt_defaults=prompt_defaults,
            query_id=str(sample_query.query_id),
            slots={
                **_common_slots(
                    prompt_defaults,
                    answer_example="A",
                ),
                "person_label_a": _person_label(sample_query.sample, sample_query.person_a_id),
                "person_label_b": _person_label(sample_query.sample, sample_query.person_b_id),
            },
            instance_seed=int(instance_seed),
        )
        query_params = {
            "scene_variant": str(style.scene_variant),
            "scene_variant_probabilities": dict(style.scene_variant_probabilities),
            "relationship_label_probabilities": dict(relationship_probs),
            "relationship_label": str(target_relationship),
            "person_count": int(len(sample_query.sample.people)),
            "template_name": str(sample_query.sample.template_name),
            "node_color_name": str(style.node_color_name),
            "node_color_name_probabilities": dict(style.node_color_name_probabilities),
            "option_count": len(OPTION_LABELS),
            "option_values_by_label": dict(option_values),
            "answer_support": list(PEDIGREE_RELATIONSHIP_LABELS),
        }
        execution_trace = {
            "task_id": self.task_id,
            "scene_id": SCENE_ID,
            "query_id": str(sample_query.query_id),
            "answer": str(correct_option),
            "answer_relationship": str(sample_query.answer),
            "option_values_by_label": dict(option_values),
            "person_a_id": str(sample_query.person_a_id),
            "person_a_label": _person_label(sample_query.sample, sample_query.person_a_id),
            "person_b_id": str(sample_query.person_b_id),
            "person_b_label": _person_label(sample_query.sample, sample_query.person_b_id),
            "annotation_role_to_person_id": dict(annotation_projection["role_person_id_map"]),
            "selected_option_label": str(correct_option),
        }
        trace_payload = _trace_payload(
            task_identifier=self.task_id,
            query_id=str(sample_query.query_id),
            prompt_defaults=prompt_defaults,
            prompt_artifacts=prompt_artifacts,
            sample=sample_query.sample,
            rendered_scene=rendered_scene,
            render_params=render_params,
            style=style,
            background_meta=background_meta,
            post_noise_meta=post_noise_meta,
            query_params=query_params,
            execution_trace=execution_trace,
            witness_symbolic={
                "type": "pedigree_relationship_label",
                "answer_option": str(correct_option),
                "relationship_label": str(sample_query.answer),
                "option_values_by_label": dict(option_values),
                "annotation_role_to_person_id": dict(annotation_projection["role_person_id_map"]),
            },
            projected_annotation=annotation_projection,
        )
        answer_gt = TypedValue(type="option_letter", value=str(correct_option))
        annotation_gt = TypedValue(
            type="keyed_bbox_map",
            value=dict(annotation_projection["keyed_bbox_map"]),
        )
        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            annotation_gt=annotation_gt,
            image=image,
            image_id="img0",
            trace_payload=dict(trace_payload),
            task_versions=default_task_versions(),
            scene_id=SCENE_ID,
            query_id=str(sample_query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphPedigreeRelationshipLabelTask", "RELATIONSHIP_TASK_ID"]
