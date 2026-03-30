"""Shared dataset builders and render defaults for flow-diagram tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from ....core.seed import spawn_rng
from ...shared.config_defaults import resolve_required_int_bounds
from ...shared.deterministic_sampling import resolve_selection_index
from ..shared.common import resolve_diagrams_axis_variant, resolve_diagrams_int_param, resolve_diagrams_rgb_triple


SUPPORTED_DIAGRAM_FLOW_SCENE_VARIANTS: Tuple[str, ...] = ("flowchart", "swimlane")
SUPPORTED_DIAGRAM_FLOW_TASK_VARIANTS: Tuple[str, ...] = ("direct_next_step", "branch_next_step")

_PROCESS_VERBS: Tuple[str, ...] = (
    "Review",
    "Approve",
    "Prepare",
    "Verify",
    "Update",
    "Archive",
    "Submit",
    "Schedule",
    "Record",
    "Confirm",
    "Package",
    "Inspect",
    "Route",
    "Deliver",
    "Close",
    "Issue",
    "Create",
    "Check",
    "Release",
    "Log",
)
_PROCESS_OBJECTS: Tuple[str, ...] = (
    "Request",
    "Order",
    "Ticket",
    "Report",
    "Invoice",
    "Packet",
    "Claim",
    "Notice",
    "Draft",
    "Form",
    "Payment",
    "Shipment",
    "Profile",
    "Summary",
    "Record",
    "Plan",
    "Return",
    "File",
    "Booking",
    "Approval",
)
_DECISION_LABELS: Tuple[str, ...] = (
    "Approved?",
    "Need Fix?",
    "Info Complete?",
    "Payment OK?",
    "Ready to Ship?",
    "Policy Match?",
    "Manager OK?",
    "Stock Ready?",
)
_TITLE_OPTIONS: Tuple[str, ...] = (
    "Process Flow",
    "Workflow Diagram",
    "Approval Flow",
    "Service Flow",
    "Request Flow",
)
_SWIMLANE_TITLE_SETS: Tuple[Tuple[str, str, str], ...] = (
    ("Intake", "Review", "Completion"),
    ("Request", "Operations", "Release"),
    ("Client", "Processing", "Records"),
    ("Draft", "Approval", "Delivery"),
)


@dataclass(frozen=True)
class FlowDefaults:
    """Default generation bounds for flow-diagram next-step tasks."""

    direct_node_count_min: int = 5
    direct_node_count_max: int = 6
    lane_count: int = 3


@dataclass(frozen=True)
class FlowRenderParams:
    """Resolved rendering knobs for one flow-diagram scene."""

    canvas_width: int
    canvas_height: int
    outer_margin_px: int
    panel_padding_px: int
    panel_corner_radius_px: int
    title_font_size_px: int
    title_band_height_px: int
    lane_gutter_width_px: int
    lane_label_font_size_px: int
    lane_divider_width_px: int
    lane_fill_rgb: Tuple[int, int, int]
    lane_divider_rgb: Tuple[int, int, int]
    node_width_px: int
    node_height_px: int
    decision_diameter_px: int
    node_corner_radius_px: int
    node_border_width_px: int
    edge_width_px: int
    arrow_head_length_px: int
    arrow_head_width_px: int
    label_font_size_px: int
    branch_label_font_size_px: int
    branch_label_padding_px: int
    panel_fill_rgb: Tuple[int, int, int]
    panel_border_rgb: Tuple[int, int, int]
    title_color_rgb: Tuple[int, int, int]
    node_fill_rgb: Tuple[int, int, int]
    decision_fill_rgb: Tuple[int, int, int]
    node_border_rgb: Tuple[int, int, int]
    edge_color_rgb: Tuple[int, int, int]
    label_color_rgb: Tuple[int, int, int]
    label_stroke_rgb: Tuple[int, int, int]
    branch_label_fill_rgb: Tuple[int, int, int]
    branch_label_border_rgb: Tuple[int, int, int]
    branch_label_text_rgb: Tuple[int, int, int]

def resolve_flow_scene_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active flow scene variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_FLOW_SCENE_VARIANTS,
        task_id=str(task_id),
        explicit_key="scene_variant",
        weights_key="scene_variant_weights",
        balance_flag_key="balanced_scene_variant_sampling",
        axis_namespace="scene_variant",
    )


def resolve_flow_task_variant(
    params: Mapping[str, Any],
    *,
    gen_defaults: Mapping[str, Any],
    instance_seed: int,
    task_id: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve the active semantic flow task variant."""

    return resolve_diagrams_axis_variant(
        params=params,
        gen_defaults=gen_defaults,
        instance_seed=int(instance_seed),
        supported_variants=SUPPORTED_DIAGRAM_FLOW_TASK_VARIANTS,
        task_id=str(task_id),
        explicit_key="task_variant",
        weights_key="task_variant_weights",
        balance_flag_key="balanced_task_variant_sampling",
        axis_namespace="task_variant",
    )


def resolve_flow_render_params(
    params: Mapping[str, Any],
    *,
    render_defaults: Mapping[str, Any],
) -> FlowRenderParams:
    """Resolve rendering params for flow scenes."""

    def _triple(key: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        return resolve_diagrams_rgb_triple(params, render_defaults, key, fallback)

    return FlowRenderParams(
        canvas_width=int(resolve_diagrams_int_param(params, render_defaults, "canvas_width", 1200)),
        canvas_height=int(resolve_diagrams_int_param(params, render_defaults, "canvas_height", 840)),
        outer_margin_px=int(resolve_diagrams_int_param(params, render_defaults, "outer_margin_px", 52)),
        panel_padding_px=int(resolve_diagrams_int_param(params, render_defaults, "panel_padding_px", 28)),
        panel_corner_radius_px=int(resolve_diagrams_int_param(params, render_defaults, "panel_corner_radius_px", 30)),
        title_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "title_font_size_px", 32)),
        title_band_height_px=int(resolve_diagrams_int_param(params, render_defaults, "title_band_height_px", 78)),
        lane_gutter_width_px=int(resolve_diagrams_int_param(params, render_defaults, "lane_gutter_width_px", 160)),
        lane_label_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "lane_label_font_size_px", 24)),
        lane_divider_width_px=int(resolve_diagrams_int_param(params, render_defaults, "lane_divider_width_px", 3)),
        lane_fill_rgb=_triple("lane_fill_rgb", (243, 246, 251)),
        lane_divider_rgb=_triple("lane_divider_rgb", (206, 213, 223)),
        node_width_px=int(resolve_diagrams_int_param(params, render_defaults, "node_width_px", 214)),
        node_height_px=int(resolve_diagrams_int_param(params, render_defaults, "node_height_px", 84)),
        decision_diameter_px=int(resolve_diagrams_int_param(params, render_defaults, "decision_diameter_px", 132)),
        node_corner_radius_px=int(resolve_diagrams_int_param(params, render_defaults, "node_corner_radius_px", 22)),
        node_border_width_px=int(resolve_diagrams_int_param(params, render_defaults, "node_border_width_px", 3)),
        edge_width_px=int(resolve_diagrams_int_param(params, render_defaults, "edge_width_px", 5)),
        arrow_head_length_px=int(resolve_diagrams_int_param(params, render_defaults, "arrow_head_length_px", 18)),
        arrow_head_width_px=int(resolve_diagrams_int_param(params, render_defaults, "arrow_head_width_px", 16)),
        label_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "label_font_size_px", 28)),
        branch_label_font_size_px=int(resolve_diagrams_int_param(params, render_defaults, "branch_label_font_size_px", 20)),
        branch_label_padding_px=int(resolve_diagrams_int_param(params, render_defaults, "branch_label_padding_px", 10)),
        panel_fill_rgb=_triple("panel_fill_rgb", (252, 252, 255)),
        panel_border_rgb=_triple("panel_border_rgb", (88, 98, 112)),
        title_color_rgb=_triple("title_color_rgb", (34, 40, 48)),
        node_fill_rgb=_triple("node_fill_rgb", (242, 246, 255)),
        decision_fill_rgb=_triple("decision_fill_rgb", (249, 243, 231)),
        node_border_rgb=_triple("node_border_rgb", (77, 90, 109)),
        edge_color_rgb=_triple("edge_color_rgb", (78, 87, 101)),
        label_color_rgb=_triple("label_color_rgb", (29, 34, 41)),
        label_stroke_rgb=_triple("label_stroke_rgb", (255, 255, 255)),
        branch_label_fill_rgb=_triple("branch_label_fill_rgb", (255, 255, 255)),
        branch_label_border_rgb=_triple("branch_label_border_rgb", (173, 181, 192)),
        branch_label_text_rgb=_triple("branch_label_text_rgb", (58, 66, 77)),
    )


def _sample_process_labels(*, count: int, rng) -> List[str]:
    """Sample unique short process labels for one diagram."""

    candidates = [f"{verb} {obj}" for verb in _PROCESS_VERBS for obj in _PROCESS_OBJECTS]
    if int(count) > len(candidates):
        raise ValueError("requested more process labels than available combinations")
    sampled = list(rng.sample(candidates, int(count)))
    return [str(label) for label in sampled]


def _scene_title(*, rng) -> str:
    """Sample one short scene title."""

    return str(_TITLE_OPTIONS[int(rng.randrange(len(_TITLE_OPTIONS)))])


def _lane_specs(*, rng) -> List[Dict[str, Any]]:
    """Sample one ordered swimlane title set."""

    titles = _SWIMLANE_TITLE_SETS[int(rng.randrange(len(_SWIMLANE_TITLE_SETS)))]
    return [
        {
            "lane_id": f"lane_{index}",
            "lane_label": str(label),
            "lane_bbox_id": f"lane_bbox_{index}",
            "lane_label_bbox_id": f"lane_label_bbox_{index}",
        }
        for index, label in enumerate(titles)
    ]


def _direct_topology(
    *,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    defaults: FlowDefaults,
    gen_defaults: Mapping[str, Any],
    rng,
    task_id: str,
) -> Dict[str, Any]:
    """Build one direct next-step flow instance."""

    node_count_min, node_count_max = resolve_required_int_bounds(
        params,
        gen_defaults,
        min_key="direct_node_count_min",
        max_key="direct_node_count_max",
        fallback_min=int(defaults.direct_node_count_min),
        fallback_max=int(defaults.direct_node_count_max),
        context=f"{task_id} direct node count",
    )
    node_count = int(
        node_count_min
        + (
            resolve_selection_index(
                params=params,
                instance_seed=int(instance_seed),
                namespace=f"{task_id}.direct_node_count",
            )
            % (int(node_count_max) - int(node_count_min) + 1)
        )
    )
    labels = _sample_process_labels(count=int(node_count), rng=rng)
    lane_specs = _lane_specs(rng=rng) if str(scene_variant) == "swimlane" else []

    if str(scene_variant) == "swimlane":
        centers = [
            (0.16, 0.18),
            (0.50, 0.50),
            (0.84, 0.50),
            (0.84, 0.82),
            (0.50, 0.82),
            (0.16, 0.82),
        ]
        lane_ids = ["lane_0", "lane_1", "lane_1", "lane_2", "lane_2", "lane_2"]
        edge_waypoints = {
            0: [(0.16, 0.50)],
            1: [],
            2: [],
            3: [],
            4: [],
        }
    else:
        centers = [
            (0.16, 0.24),
            (0.48, 0.24),
            (0.80, 0.24),
            (0.80, 0.60),
            (0.48, 0.60),
            (0.16, 0.60),
        ]
        lane_ids = [None] * 6
        edge_waypoints = {0: [], 1: [], 2: [], 3: [], 4: []}

    node_specs: List[Dict[str, Any]] = []
    for index in range(int(node_count)):
        node_specs.append(
            {
                "node_id": f"node_{index}",
                "node_bbox_id": f"node_bbox_{index}",
                "node_label_bbox_id": f"node_label_bbox_{index}",
                "node_kind": "process",
                "node_label": str(labels[index]),
                "center_rel": [float(centers[index][0]), float(centers[index][1])],
                "lane_id": lane_ids[index],
            }
        )

    edge_specs: List[Dict[str, Any]] = []
    for index in range(int(node_count) - 1):
        edge_specs.append(
            {
                "edge_id": f"edge_{index}",
                "source_node_id": f"node_{index}",
                "target_node_id": f"node_{index + 1}",
                "edge_label": None,
                "edge_label_bbox_id": None,
                "waypoints_rel": [
                    [float(point[0]), float(point[1])]
                    for point in edge_waypoints.get(index, [])
                ],
            }
        )

    query_index = int(
        resolve_selection_index(
            params=params,
            instance_seed=int(instance_seed),
            namespace=f"{task_id}.query_node",
        )
        % (int(node_count) - 1)
    )
    answer_index = int(query_index + 1)
    question_text = f"What is the next step after {labels[query_index]}? Return the exact step label shown."
    return {
        "scene_title": _scene_title(rng=rng),
        "lane_specs": lane_specs,
        "node_specs": node_specs,
        "edge_specs": edge_specs,
        "query_node_id": f"node_{query_index}",
        "query_node_label": str(labels[query_index]),
        "query_branch_label": None,
        "answer_node_id": f"node_{answer_index}",
        "answer_node_label": str(labels[answer_index]),
        "answer_node_bbox_id": f"node_bbox_{answer_index}",
        "question_text": str(question_text),
        "topology_node_count": int(node_count),
        "lane_count": len(lane_specs),
        "question_format": "flow_next_step_label",
        "view_family": "process_flow_diagram",
    }


def _branch_topology(
    *,
    scene_variant: str,
    rng,
) -> Dict[str, Any]:
    """Build one decision-branch next-step flow instance."""

    labels = _sample_process_labels(count=5, rng=rng)
    decision_label = str(_DECISION_LABELS[int(rng.randrange(len(_DECISION_LABELS)))])
    lane_specs = _lane_specs(rng=rng) if str(scene_variant) == "swimlane" else []

    if str(scene_variant) == "swimlane":
        node_specs = [
            {"node_id": "node_0", "node_bbox_id": "node_bbox_0", "node_label_bbox_id": "node_label_bbox_0", "node_kind": "process", "node_label": labels[0], "center_rel": [0.13, 0.18], "lane_id": "lane_0"},
            {"node_id": "node_1", "node_bbox_id": "node_bbox_1", "node_label_bbox_id": "node_label_bbox_1", "node_kind": "process", "node_label": labels[1], "center_rel": [0.34, 0.50], "lane_id": "lane_1"},
            {"node_id": "node_2", "node_bbox_id": "node_bbox_2", "node_label_bbox_id": "node_label_bbox_2", "node_kind": "decision", "node_label": decision_label, "center_rel": [0.60, 0.50], "lane_id": "lane_1"},
            {"node_id": "node_3", "node_bbox_id": "node_bbox_3", "node_label_bbox_id": "node_label_bbox_3", "node_kind": "process", "node_label": labels[2], "center_rel": [0.44, 0.82], "lane_id": "lane_2"},
            {"node_id": "node_4", "node_bbox_id": "node_bbox_4", "node_label_bbox_id": "node_label_bbox_4", "node_kind": "process", "node_label": labels[3], "center_rel": [0.90, 0.50], "lane_id": "lane_1"},
            {"node_id": "node_5", "node_bbox_id": "node_bbox_5", "node_label_bbox_id": "node_label_bbox_5", "node_kind": "process", "node_label": labels[4], "center_rel": [0.90, 0.82], "lane_id": "lane_2"},
        ]
        edge_specs = [
            {"edge_id": "edge_0", "source_node_id": "node_0", "target_node_id": "node_1", "edge_label": None, "edge_label_bbox_id": None, "waypoints_rel": [[0.13, 0.50]]},
            {"edge_id": "edge_1", "source_node_id": "node_1", "target_node_id": "node_2", "edge_label": None, "edge_label_bbox_id": None, "waypoints_rel": []},
            {"edge_id": "edge_2", "source_node_id": "node_2", "target_node_id": "node_3", "edge_label": "Yes", "edge_label_bbox_id": "edge_label_bbox_yes", "waypoints_rel": []},
            {"edge_id": "edge_3", "source_node_id": "node_2", "target_node_id": "node_4", "edge_label": "No", "edge_label_bbox_id": "edge_label_bbox_no", "waypoints_rel": []},
            {"edge_id": "edge_4", "source_node_id": "node_3", "target_node_id": "node_5", "edge_label": None, "edge_label_bbox_id": None, "waypoints_rel": []},
            {"edge_id": "edge_5", "source_node_id": "node_4", "target_node_id": "node_5", "edge_label": None, "edge_label_bbox_id": None, "waypoints_rel": [[0.90, 0.82]]},
        ]
    else:
        node_specs = [
            {"node_id": "node_0", "node_bbox_id": "node_bbox_0", "node_label_bbox_id": "node_label_bbox_0", "node_kind": "process", "node_label": labels[0], "center_rel": [0.10, 0.26], "lane_id": None},
            {"node_id": "node_1", "node_bbox_id": "node_bbox_1", "node_label_bbox_id": "node_label_bbox_1", "node_kind": "process", "node_label": labels[1], "center_rel": [0.38, 0.26], "lane_id": None},
            {"node_id": "node_2", "node_bbox_id": "node_bbox_2", "node_label_bbox_id": "node_label_bbox_2", "node_kind": "decision", "node_label": decision_label, "center_rel": [0.62, 0.26], "lane_id": None},
            {"node_id": "node_3", "node_bbox_id": "node_bbox_3", "node_label_bbox_id": "node_label_bbox_3", "node_kind": "process", "node_label": labels[2], "center_rel": [0.52, 0.60], "lane_id": None},
            {"node_id": "node_4", "node_bbox_id": "node_bbox_4", "node_label_bbox_id": "node_label_bbox_4", "node_kind": "process", "node_label": labels[3], "center_rel": [0.90, 0.26], "lane_id": None},
            {"node_id": "node_5", "node_bbox_id": "node_bbox_5", "node_label_bbox_id": "node_label_bbox_5", "node_kind": "process", "node_label": labels[4], "center_rel": [0.90, 0.60], "lane_id": None},
        ]
        edge_specs = [
            {"edge_id": "edge_0", "source_node_id": "node_0", "target_node_id": "node_1", "edge_label": None, "edge_label_bbox_id": None, "waypoints_rel": []},
            {"edge_id": "edge_1", "source_node_id": "node_1", "target_node_id": "node_2", "edge_label": None, "edge_label_bbox_id": None, "waypoints_rel": []},
            {"edge_id": "edge_2", "source_node_id": "node_2", "target_node_id": "node_3", "edge_label": "Yes", "edge_label_bbox_id": "edge_label_bbox_yes", "waypoints_rel": []},
            {"edge_id": "edge_3", "source_node_id": "node_2", "target_node_id": "node_4", "edge_label": "No", "edge_label_bbox_id": "edge_label_bbox_no", "waypoints_rel": []},
            {"edge_id": "edge_4", "source_node_id": "node_3", "target_node_id": "node_5", "edge_label": None, "edge_label_bbox_id": None, "waypoints_rel": []},
            {"edge_id": "edge_5", "source_node_id": "node_4", "target_node_id": "node_5", "edge_label": None, "edge_label_bbox_id": None, "waypoints_rel": [[0.90, 0.60]]},
        ]

    branch_label = "Yes" if bool(rng.randrange(2)) else "No"
    answer_node_id = "node_3" if str(branch_label) == "Yes" else "node_4"
    answer_node_label = labels[2] if str(branch_label) == "Yes" else labels[3]
    question_text = (
        f"Following the {branch_label} branch from {decision_label}, what is the next step? "
        "Return the exact step label shown."
    )
    return {
        "scene_title": _scene_title(rng=rng),
        "lane_specs": lane_specs,
        "node_specs": node_specs,
        "edge_specs": edge_specs,
        "query_node_id": "node_2",
        "query_node_label": str(decision_label),
        "query_branch_label": str(branch_label),
        "answer_node_id": str(answer_node_id),
        "answer_node_label": str(answer_node_label),
        "answer_node_bbox_id": f"{answer_node_id.replace('node', 'node_bbox')}",
        "question_text": str(question_text),
        "topology_node_count": 6,
        "lane_count": len(lane_specs),
        "question_format": "flow_next_step_label",
        "view_family": "process_flow_diagram",
    }


def build_flow_next_step_dataset(
    *,
    task_variant: str,
    scene_variant: str,
    params: Mapping[str, Any],
    instance_seed: int,
    gen_defaults: Mapping[str, Any],
    defaults: FlowDefaults,
    task_id: str,
) -> Dict[str, Any]:
    """Build one flow-diagram next-step dataset instance."""

    rng = spawn_rng(int(instance_seed), f"{task_id}.dataset")
    variant = str(task_variant)
    if variant == "direct_next_step":
        dataset = _direct_topology(
            scene_variant=str(scene_variant),
            params=params,
            instance_seed=int(instance_seed),
            defaults=defaults,
            gen_defaults=gen_defaults,
            rng=rng,
            task_id=str(task_id),
        )
    elif variant == "branch_next_step":
        dataset = _branch_topology(scene_variant=str(scene_variant), rng=rng)
    else:
        raise ValueError(f"unsupported flow task variant: {task_variant}")
    return {
        "scene_title": str(dataset["scene_title"]),
        "task_variant": str(task_variant),
        "scene_variant": str(scene_variant),
        "question_text": str(dataset["question_text"]),
        "question_format": str(dataset["question_format"]),
        "view_family": str(dataset["view_family"]),
        "topology_node_count": int(dataset["topology_node_count"]),
        "lane_count": int(dataset["lane_count"]),
        "query_node_id": str(dataset["query_node_id"]),
        "query_node_label": str(dataset["query_node_label"]),
        "query_branch_label": dataset["query_branch_label"],
        "answer_node_id": str(dataset["answer_node_id"]),
        "answer_node_label": str(dataset["answer_node_label"]),
        "answer_node_bbox_id": str(dataset["answer_node_bbox_id"]),
        "lane_specs": [dict(spec) for spec in dataset["lane_specs"]],
        "node_specs": [dict(spec) for spec in dataset["node_specs"]],
        "edge_specs": [dict(spec) for spec in dataset["edge_specs"]],
    }


__all__ = [
    "FlowDefaults",
    "FlowRenderParams",
    "SUPPORTED_DIAGRAM_FLOW_SCENE_VARIANTS",
    "SUPPORTED_DIAGRAM_FLOW_TASK_VARIANTS",
    "build_flow_next_step_dataset",
    "resolve_flow_render_params",
    "resolve_flow_scene_variant",
    "resolve_flow_task_variant",
]
