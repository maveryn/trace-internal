"""Select the accepted string from candidate inputs for a finite automaton."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Sequence, Tuple

import networkx as nx
from PIL import Image, ImageDraw

from ....core.seed import spawn_rng
from ....core.task_group_config import get_task_group_defaults
from ....core.types import TypedValue
from ....core.visual.background import make_background_canvas
from ....core.visual.noise import apply_post_image_noise
from ...base import TaskOutput
from ...registry import register_task
from ...shared.config_defaults import group_default, required_group_defaults, split_generation_rendering_prompt_defaults
from ...shared.deterministic_sampling import resolve_selection_index
from ...shared.output_metadata import default_task_versions
from ...shared.prompt_variants import (
    PROMPT_OUTPUT_MODES,
    build_prompt_trace_artifacts,
    render_task_prompt_variants,
)
from ...shared.text_rendering import load_font
from ..shared.complexity import (
    build_graph_complexity,
    normalize_float_with_bounds,
    normalize_int_with_bounds,
    resolve_graph_complexity_weights,
)
from ..shared.graph_sampling import GraphTopologySample
from ..shared.graph_scene import (
    GraphRenderParams,
    RenderedGraphScene,
    projected_node_point_evidence,
    render_graph_scene,
)
from ..shared.style import SUPPORTED_NODE_COLOR_NAMES
from ..shared.task_support import resolve_graph_named_variant, resolve_graph_render_params
from ..shared.visual_defaults import load_graph_background_defaults, load_graph_noise_defaults
from .automaton_state_simulation_label import (
    AUTOMATON_SYMBOLS,
    SUPPORTED_AUTOMATON_LAYOUT_VARIANTS,
    _build_topology_sample,
    _decorate_automaton_scene,
    _state_labels,
)


TASK_ID = "task_graph__automaton__accepted_string_label"
SCENE_ID = "automaton"

DFA_ACCEPTED_STRING_QUERY_ID = "dfa_accepted_string_label"
NFA_ACCEPTED_STRING_QUERY_ID = "nfa_accepted_string_label"
SUPPORTED_QUERY_IDS = (DFA_ACCEPTED_STRING_QUERY_ID, NFA_ACCEPTED_STRING_QUERY_ID)
OPTION_LABELS = tuple("ABCDEF")


@dataclass(frozen=True)
class _TaskDefaults:
    """Stable fallback defaults for automaton string-acceptance tasks."""

    state_count_min: int = 4
    state_count_max: int = 6
    input_length_min: int = 3
    input_length_max: int = 6
    candidate_count: int = 6
    canvas_width: int = 864
    canvas_height: int = 640
    option_panel_height_px: int = 150
    outer_margin_px: int = 28
    panel_padding_px: int = 24
    panel_corner_radius_px: int = 20
    panel_title_font_size_px: int = 24
    node_shape_variant: str = "circle"
    node_radius_min_px: int = 20
    node_radius_max_px: int = 25
    edge_width_px: int = 4
    arrow_length_px: int = 12
    arrow_width_px: int = 7
    node_border_width_px: int = 2
    label_font_size_px: int = 20
    node_color_name: str = "blue"


@dataclass(frozen=True)
class _ResolvedQuery:
    """Resolved query and visual axes for one string-acceptance instance."""

    query_id: str
    automaton_kind: str
    state_count: int
    input_length: int
    input_length_min: int
    input_length_max: int
    candidate_count: int
    answer_option_index: int
    layout_variant: str
    layout_transform_variant: str
    edge_routing_variant: str
    node_color_name: str
    query_id_probabilities: Dict[str, float]
    state_count_probabilities: Dict[str, float]
    input_length_probabilities: Dict[str, float]
    answer_option_probabilities: Dict[str, float]
    layout_variant_probabilities: Dict[str, float]
    layout_transform_variant_probabilities: Dict[str, float]
    edge_routing_variant_probabilities: Dict[str, float]
    node_color_name_probabilities: Dict[str, float]


@dataclass(frozen=True)
class _AcceptanceSample:
    """One trace-ready automaton and accepted candidate option."""

    graph_sample: GraphTopologySample
    start_label: str
    accepting_labels: Tuple[str, ...]
    answer_option_label: str
    answer_input_string: str
    accepting_path_labels: Tuple[str, ...]
    candidate_strings_by_option: Dict[str, str]
    accepted_option_labels: Tuple[str, ...]
    transition_labels_by_edge: Dict[Tuple[str, str], str]
    transition_function: Dict[str, Dict[str, Tuple[str, ...]]]


_DEFAULTS = _TaskDefaults()
_TASK_GROUP_DEFAULTS = get_task_group_defaults("graph", "relation")
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = split_generation_rendering_prompt_defaults(
    _TASK_GROUP_DEFAULTS if isinstance(_TASK_GROUP_DEFAULTS, Mapping) else {},
    task_id=TASK_ID,
)
POST_IMAGE_BACKGROUND_DEFAULTS = load_graph_background_defaults(task_group="relation")
POST_IMAGE_NOISE_DEFAULTS = load_graph_noise_defaults(task_group="relation", apply_prob=0.5)
_COMPLEXITY_WEIGHTS = resolve_graph_complexity_weights(_TASK_GROUP_DEFAULTS, task_id=TASK_ID)


def _build_prompt_json_examples() -> Tuple[str, str]:
    """Return prompt examples that match accepted-path evidence."""

    example_evidence = [[150, 250], [310, 190], [480, 230]]
    return (
        json.dumps({"evidence": example_evidence, "answer": "C"}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
        json.dumps({"answer": "C"}, ensure_ascii=False, allow_nan=False, separators=(",", ":")),
    )


def _query_id_from_alias(value: Any) -> str | None:
    """Return the public query id encoded by one query/task alias."""

    text = str(value or "").strip()
    aliases = {
        "dfa": DFA_ACCEPTED_STRING_QUERY_ID,
        "dfa_accepted_string": DFA_ACCEPTED_STRING_QUERY_ID,
        "dfa_accepted_string_label": DFA_ACCEPTED_STRING_QUERY_ID,
        "nfa": NFA_ACCEPTED_STRING_QUERY_ID,
        "nfa_accepted_string": NFA_ACCEPTED_STRING_QUERY_ID,
        "nfa_accepted_string_label": NFA_ACCEPTED_STRING_QUERY_ID,
        "automaton_string_acceptance": None,
        "default": None,
    }
    return aliases.get(text)


def _forced_query_id(params: Mapping[str, Any]) -> str | None:
    """Resolve an explicitly requested query id, if present."""

    for key in ("query_id", "query_variant"):
        query_id = _query_id_from_alias(params.get(str(key)))
        if query_id is not None:
            return str(query_id)
    return None


def _resolve_named_variant(
    instance_seed: int,
    *,
    params: Mapping[str, Any],
    explicit_key: str,
    weights_key: str,
    balance_flag_key: str,
    supported: Tuple[str, ...],
    namespace: str,
) -> Tuple[str, Dict[str, float]]:
    """Resolve one balanced query or visual axis."""

    return resolve_graph_named_variant(
        spawn_rng(int(instance_seed), f"{TASK_ID}.{str(namespace)}"),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        explicit_key=str(explicit_key),
        weights_key=str(weights_key),
        balance_flag_key=str(balance_flag_key),
        supported=tuple(str(value) for value in supported),
        instance_seed=int(instance_seed),
        task_id=TASK_ID,
        namespace=str(namespace),
    )


def _uniform_probability(values: Sequence[int | str], *, selected: int | str | None = None) -> Dict[str, float]:
    """Return a uniform probability map over support values."""

    support = tuple(str(value) for value in values)
    if not support:
        return {}
    if selected is not None:
        selected_text = str(selected)
        return {str(value): (1.0 if str(value) == selected_text else 0.0) for value in support}
    probability = 1.0 / float(len(support))
    return {str(value): float(probability) for value in support}


def _resolve_query(instance_seed: int, *, params: Mapping[str, Any]) -> _ResolvedQuery:
    """Resolve one automaton string-acceptance query."""

    forced_query_id = _forced_query_id(params)
    if forced_query_id is None:
        query_id, query_id_probabilities = _resolve_named_variant(
            int(instance_seed),
            params=params,
            explicit_key="query_id",
            weights_key="query_variant_weights",
            balance_flag_key="balanced_query_variant_sampling",
            supported=SUPPORTED_QUERY_IDS,
            namespace="query_variant",
        )
    else:
        query_id = str(forced_query_id)
        query_id_probabilities = {
            str(supported_query_id): (1.0 if str(supported_query_id) == str(query_id) else 0.0)
            for supported_query_id in SUPPORTED_QUERY_IDS
        }
    automaton_kind = "nfa" if str(query_id) == NFA_ACCEPTED_STRING_QUERY_ID else "dfa"

    state_count_min = int(params.get("state_count_min", group_default(_GEN_DEFAULTS, "state_count_min", _DEFAULTS.state_count_min)))
    state_count_max = int(params.get("state_count_max", group_default(_GEN_DEFAULTS, "state_count_max", _DEFAULTS.state_count_max)))
    state_count_support = tuple(int(value) for value in range(max(3, int(state_count_min)), int(state_count_max) + 1))
    if not state_count_support:
        raise ValueError("no feasible state_count support exists for automaton string acceptance")
    explicit_state_count = params.get("state_count")
    if explicit_state_count is not None:
        state_count = int(explicit_state_count)
        if int(state_count) not in set(state_count_support):
            raise ValueError("state_count is outside feasible support")
    else:
        state_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:state_count"))
        state_count = int(state_count_support[int(state_index % len(state_count_support))])

    input_length_min = int(params.get("input_length_min", group_default(_GEN_DEFAULTS, "input_length_min", _DEFAULTS.input_length_min)))
    input_length_max = int(params.get("input_length_max", group_default(_GEN_DEFAULTS, "input_length_max", _DEFAULTS.input_length_max)))
    input_length_support = tuple(int(value) for value in range(max(1, int(input_length_min)), int(input_length_max) + 1))
    if not input_length_support:
        raise ValueError("no feasible input length support exists for automaton string acceptance")
    explicit_input_length = params.get("input_length")
    if explicit_input_length is not None:
        input_length = int(explicit_input_length)
        if int(input_length) not in set(input_length_support):
            raise ValueError("input_length is outside feasible support")
    else:
        length_index = int(resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:input_length"))
        input_length = int(input_length_support[int(length_index % len(input_length_support))])

    candidate_count = int(params.get("candidate_count", group_default(_GEN_DEFAULTS, "candidate_count", _DEFAULTS.candidate_count)))
    candidate_count = max(2, min(int(candidate_count), len(OPTION_LABELS)))
    explicit_answer_option = str(params.get("answer_option", params.get("answer_option_label", ""))).strip().upper()
    if explicit_answer_option:
        if explicit_answer_option not in set(OPTION_LABELS[: int(candidate_count)]):
            raise ValueError("answer_option is outside feasible option-label support")
        answer_option_index = int(OPTION_LABELS.index(explicit_answer_option))
    else:
        answer_option_index = int(
            resolve_selection_index(params=params, instance_seed=int(instance_seed), namespace=f"{TASK_ID}:answer_option")
            % int(candidate_count)
        )

    layout_variant, layout_variant_probabilities = _resolve_named_variant(
        int(instance_seed),
        params=params,
        explicit_key="layout_variant",
        weights_key="layout_variant_weights",
        balance_flag_key="balanced_layout_variant_sampling",
        supported=SUPPORTED_AUTOMATON_LAYOUT_VARIANTS,
        namespace="layout_variant",
    )
    layout_transform_variant, layout_transform_variant_probabilities = _resolve_named_variant(
        int(instance_seed),
        params=params,
        explicit_key="layout_transform_variant",
        weights_key="layout_transform_variant_weights",
        balance_flag_key="balanced_layout_transform_variant_sampling",
        supported=("identity", "mirror_left_right", "mirror_up_down"),
        namespace="layout_transform_variant",
    )
    edge_routing_variant, edge_routing_variant_probabilities = _resolve_named_variant(
        int(instance_seed),
        params=params,
        explicit_key="edge_routing_variant",
        weights_key="edge_routing_variant_weights",
        balance_flag_key="balanced_edge_routing_variant_sampling",
        supported=("straight", "mixed_arc"),
        namespace="edge_routing_variant",
    )
    node_color_name, node_color_name_probabilities = _resolve_named_variant(
        int(instance_seed),
        params=params,
        explicit_key="node_color_name",
        weights_key="node_color_name_weights",
        balance_flag_key="balanced_node_color_name_sampling",
        supported=SUPPORTED_NODE_COLOR_NAMES,
        namespace="node_color_name",
    )

    return _ResolvedQuery(
        query_id=str(query_id),
        automaton_kind=str(automaton_kind),
        state_count=int(state_count),
        input_length=int(input_length),
        input_length_min=int(min(input_length_support)),
        input_length_max=int(max(input_length_support)),
        candidate_count=int(candidate_count),
        answer_option_index=int(answer_option_index),
        layout_variant=str(layout_variant),
        layout_transform_variant=str(layout_transform_variant),
        edge_routing_variant=str(edge_routing_variant),
        node_color_name=str(node_color_name),
        query_id_probabilities=dict(query_id_probabilities),
        state_count_probabilities=_uniform_probability(
            state_count_support,
            selected=int(state_count) if explicit_state_count is not None else None,
        ),
        input_length_probabilities=_uniform_probability(
            input_length_support,
            selected=int(input_length) if explicit_input_length is not None else None,
        ),
        answer_option_probabilities=_uniform_probability(
            OPTION_LABELS[: int(candidate_count)],
            selected=str(OPTION_LABELS[int(answer_option_index)]) if explicit_answer_option else None,
        ),
        layout_variant_probabilities=dict(layout_variant_probabilities),
        layout_transform_variant_probabilities=dict(layout_transform_variant_probabilities),
        edge_routing_variant_probabilities=dict(edge_routing_variant_probabilities),
        node_color_name_probabilities=dict(node_color_name_probabilities),
    )


def _all_binary_strings(*, min_len: int, max_len: int) -> Tuple[str, ...]:
    """Return all binary strings in the requested length interval."""

    values: list[str] = []
    for length in range(int(min_len), int(max_len) + 1):
        for number in range(2 ** int(length)):
            values.append(format(int(number), f"0{int(length)}b"))
    return tuple(values)


def _sample_transition_function(
    rng: random.Random,
    *,
    state_count: int,
    automaton_kind: str,
) -> Dict[int, Dict[str, Tuple[int, ...]]]:
    """Sample DFA or NFA transitions over the binary alphabet."""

    transitions: Dict[int, Dict[str, Tuple[int, ...]]] = {int(state): {} for state in range(int(state_count))}
    has_nondeterministic_branch = False
    for state in range(int(state_count)):
        for symbol in AUTOMATON_SYMBOLS:
            candidates = [int(value) for value in range(int(state_count)) if int(value) != int(state)]
            first_target = int(rng.choice(candidates))
            targets = {int(first_target)}
            if str(automaton_kind) == "nfa" and rng.random() < 0.35:
                extra_candidates = [int(value) for value in candidates if int(value) not in targets]
                if extra_candidates:
                    targets.add(int(rng.choice(extra_candidates)))
                    has_nondeterministic_branch = True
            transitions[int(state)][str(symbol)] = tuple(sorted(int(value) for value in targets))

    if str(automaton_kind) == "nfa" and not has_nondeterministic_branch:
        state = int(rng.randrange(int(state_count)))
        symbol = str(rng.choice(AUTOMATON_SYMBOLS))
        existing = set(int(value) for value in transitions[int(state)][str(symbol)])
        extra_candidates = [
            int(value)
            for value in range(int(state_count))
            if int(value) != int(state) and int(value) not in existing
        ]
        if extra_candidates:
            existing.add(int(rng.choice(extra_candidates)))
            transitions[int(state)][str(symbol)] = tuple(sorted(existing))
    return dict(transitions)


def _accepting_paths(
    *,
    transitions: Mapping[int, Mapping[str, Sequence[int]]],
    input_string: str,
    accepting_states: set[int],
    max_paths: int = 256,
) -> Tuple[Tuple[int, ...], ...]:
    """Return accepting state paths for one candidate input."""

    paths: list[Tuple[int, ...]] = [(0,)]
    for symbol in str(input_string):
        next_paths: list[Tuple[int, ...]] = []
        for path in paths:
            source = int(path[-1])
            for target in transitions.get(int(source), {}).get(str(symbol), ()):
                next_paths.append(tuple([*path, int(target)]))
                if len(next_paths) >= int(max_paths):
                    break
            if len(next_paths) >= int(max_paths):
                break
        paths = list(next_paths)
        if not paths:
            break
    return tuple(path for path in paths if int(path[-1]) in set(int(value) for value in accepting_states))


def _transition_label_map(
    *,
    transitions: Mapping[int, Mapping[str, Sequence[int]]],
    labels: Sequence[str],
) -> Tuple[Dict[Tuple[str, str], str], Dict[str, Dict[str, Tuple[str, ...]]], nx.DiGraph]:
    """Convert symbolic transitions into renderable edge labels and a graph."""

    graph = nx.DiGraph()
    graph.add_nodes_from(range(len(tuple(labels))))
    symbols_by_edge: Dict[Tuple[int, int], list[str]] = {}
    transition_function: Dict[str, Dict[str, Tuple[str, ...]]] = {str(label): {} for label in labels}
    for source, per_symbol in sorted(transitions.items()):
        source_label = str(labels[int(source)])
        for symbol, targets in sorted(per_symbol.items()):
            target_labels: list[str] = []
            for target in targets:
                graph.add_edge(int(source), int(target))
                symbols_by_edge.setdefault((int(source), int(target)), []).append(str(symbol))
                target_labels.append(str(labels[int(target)]))
            transition_function[str(source_label)][str(symbol)] = tuple(str(label) for label in target_labels)

    transition_labels_by_edge: Dict[Tuple[str, str], str] = {}
    for (source, target), symbols in sorted(symbols_by_edge.items()):
        edge_label = ",".join(sorted(set(str(symbol) for symbol in symbols)))
        transition_labels_by_edge[(str(labels[int(source)]), str(labels[int(target)]))] = str(edge_label)
    return (
        dict(transition_labels_by_edge),
        {str(key): {str(symbol): tuple(str(target) for target in targets) for symbol, targets in value.items()} for key, value in transition_function.items()},
        graph,
    )


def _sample_acceptance_automaton(
    rng: random.Random,
    *,
    query: _ResolvedQuery,
) -> _AcceptanceSample:
    """Construct one automaton with exactly one accepted displayed candidate."""

    labels = _state_labels(int(query.state_count))
    option_labels = OPTION_LABELS[: int(query.candidate_count)]
    all_strings = list(_all_binary_strings(min_len=int(query.input_length_min), max_len=int(query.input_length_max)))
    for _ in range(2000):
        transitions = _sample_transition_function(
            rng,
            state_count=int(query.state_count),
            automaton_kind=str(query.automaton_kind),
        )
        accepting_count = int(rng.randint(1, max(1, min(2, int(query.state_count) - 1))))
        accepting_states = set(int(value) for value in rng.sample(range(1, int(query.state_count)), k=int(accepting_count)))
        rng.shuffle(all_strings)
        accepted: list[Tuple[str, Tuple[int, ...]]] = []
        rejected: list[str] = []
        for candidate in all_strings:
            accepting_paths = _accepting_paths(
                transitions=transitions,
                input_string=str(candidate),
                accepting_states=set(accepting_states),
            )
            if accepting_paths:
                if len(str(candidate)) == int(query.input_length):
                    accepted.append((str(candidate), tuple(int(value) for value in accepting_paths[0])))
            else:
                rejected.append(str(candidate))
        if not accepted or len(rejected) < int(query.candidate_count) - 1:
            continue
        answer_string, accepting_path = rng.choice(accepted)
        distractor_pool = [str(value) for value in rejected if str(value) != str(answer_string)]
        same_length = [str(value) for value in distractor_pool if len(str(value)) == len(str(answer_string))]
        other_lengths = [str(value) for value in distractor_pool if len(str(value)) != len(str(answer_string))]
        selected_distractors: list[str] = []
        rng.shuffle(same_length)
        rng.shuffle(other_lengths)
        for value in [*same_length, *other_lengths]:
            if len(selected_distractors) >= int(query.candidate_count) - 1:
                break
            if str(value) not in selected_distractors:
                selected_distractors.append(str(value))
        if len(selected_distractors) < int(query.candidate_count) - 1:
            continue

        candidate_strings_by_option: Dict[str, str] = {}
        distractor_iter = iter(selected_distractors)
        answer_label = str(option_labels[int(query.answer_option_index)])
        for index, option_label in enumerate(option_labels):
            if int(index) == int(query.answer_option_index):
                candidate_strings_by_option[str(option_label)] = str(answer_string)
            else:
                candidate_strings_by_option[str(option_label)] = str(next(distractor_iter))
        accepted_option_labels = tuple(
            str(option_label)
            for option_label, candidate in candidate_strings_by_option.items()
            if _accepting_paths(
                transitions=transitions,
                input_string=str(candidate),
                accepting_states=set(accepting_states),
            )
        )
        if accepted_option_labels != (answer_label,):
            continue

        transition_labels_by_edge, transition_function, graph = _transition_label_map(
            transitions=transitions,
            labels=labels,
        )
        graph_sample = _build_topology_sample(
            graph=graph,
            labels=labels,
            transition_labels_by_edge=transition_labels_by_edge,
        )
        accepting_labels = tuple(str(labels[int(index)]) for index in sorted(int(value) for value in accepting_states))
        accepting_path_labels = tuple(str(labels[int(index)]) for index in accepting_path)
        return _AcceptanceSample(
            graph_sample=graph_sample,
            start_label=str(labels[0]),
            accepting_labels=tuple(str(label) for label in accepting_labels),
            answer_option_label=str(answer_label),
            answer_input_string=str(answer_string),
            accepting_path_labels=tuple(str(label) for label in accepting_path_labels),
            candidate_strings_by_option={str(key): str(value) for key, value in candidate_strings_by_option.items()},
            accepted_option_labels=tuple(str(value) for value in accepted_option_labels),
            transition_labels_by_edge={(str(left), str(right)): str(value) for (left, right), value in transition_labels_by_edge.items()},
            transition_function={str(key): {str(symbol): tuple(str(target) for target in targets) for symbol, targets in value.items()} for key, value in transition_function.items()},
        )
    raise ValueError("failed to sample automaton with one accepted displayed string")


def _draw_candidate_options_panel(
    *,
    rendered_scene: RenderedGraphScene,
    sample: _AcceptanceSample,
    render_params: GraphRenderParams,
    option_panel_height_px: int,
) -> Tuple[Image.Image, Dict[str, list[int]], Dict[str, Any]]:
    """Extend the graph render with a labeled candidate-string option panel."""

    graph_image = rendered_scene.image.convert("RGB")
    width, graph_height = graph_image.size
    panel_height = max(118, int(option_panel_height_px))
    image = Image.new(
        "RGB",
        (int(width), int(graph_height + panel_height)),
        tuple(int(value) for value in render_params.background_color_rgb),
    )
    image.paste(graph_image, (0, 0))
    draw = ImageDraw.Draw(image)

    margin = int(render_params.outer_margin_px)
    panel = (
        int(margin),
        int(graph_height + 14),
        int(width - margin),
        int(graph_height + panel_height - 22),
    )
    draw.rounded_rectangle(
        panel,
        radius=16,
        fill=tuple(int(value) for value in render_params.panel_fill_rgb),
        outline=tuple(int(value) for value in render_params.panel_border_rgb),
        width=2,
    )
    title_font = load_font(17, bold=True)
    option_font = load_font(20, bold=True)
    text_fill = tuple(int(value) for value in render_params.title_color_rgb)
    draw.text((panel[0] + 18, panel[1] + 10), "Candidate strings", fill=text_fill, font=title_font)

    option_bboxes: Dict[str, list[int]] = {}
    columns = 3
    rows = 2
    gap_x = 14
    gap_y = 10
    chip_top = int(panel[1] + 40)
    chip_left = int(panel[0] + 18)
    chip_right = int(panel[2] - 18)
    chip_bottom = int(panel[3] - 12)
    cell_w = int((chip_right - chip_left - (columns - 1) * gap_x) / columns)
    cell_h = int((chip_bottom - chip_top - (rows - 1) * gap_y) / rows)
    for index, option_label in enumerate(OPTION_LABELS[: len(sample.candidate_strings_by_option)]):
        row = int(index // columns)
        col = int(index % columns)
        x0 = int(chip_left + col * (cell_w + gap_x))
        y0 = int(chip_top + row * (cell_h + gap_y))
        x1 = int(x0 + cell_w)
        y1 = int(y0 + cell_h)
        draw.rounded_rectangle(
            (x0, y0, x1, y1),
            radius=10,
            fill=(255, 255, 255),
            outline=(205, 214, 226),
            width=1,
        )
        text = f"{str(option_label)}: {sample.candidate_strings_by_option[str(option_label)]}"
        bbox = draw.textbbox((0, 0), text, font=option_font)
        tx = int(x0 + max(10, (cell_w - int(bbox[2] - bbox[0])) // 2))
        ty = int(y0 + max(4, (cell_h - int(bbox[3] - bbox[1])) // 2) - 1)
        draw.text((tx, ty), text, fill=text_fill, font=option_font)
        option_bboxes[str(option_label)] = [int(x0), int(y0), int(x1), int(y1)]

    return image, option_bboxes, {
        "candidate_options_panel_xyxy": [int(value) for value in panel],
        "candidate_option_bboxes_xyxy": {str(key): list(value) for key, value in option_bboxes.items()},
    }


def _build_complexity(
    *,
    query: _ResolvedQuery,
    sample: _AcceptanceSample,
    render_params: GraphRenderParams,
    rendered_scene: RenderedGraphScene,
) -> Any:
    """Build one within-task normalized complexity record."""

    state_count = int(query.state_count)
    edge_count = int(sample.graph_sample.edge_count)
    input_length = len(str(sample.answer_input_string))
    crossing_norm = normalize_float_with_bounds(float(rendered_scene.crossing_count), (0.0, max(1.0, float(edge_count))))
    nfa_bonus = 0.18 if str(query.automaton_kind) == "nfa" else 0.0
    components = {
        "visual_scan": (0.42 * normalize_int_with_bounds(int(edge_count), (max(3, state_count), max(4, state_count * 3))))
        + (0.28 * normalize_int_with_bounds(int(state_count), (_DEFAULTS.state_count_min, _DEFAULTS.state_count_max)))
        + (0.30 * normalize_int_with_bounds(int(query.candidate_count), (2, len(OPTION_LABELS)))),
        "topology_reasoning": min(
            1.0,
            0.22
            + nfa_bonus
            + (0.42 * normalize_int_with_bounds(int(input_length), (_DEFAULTS.input_length_min, _DEFAULTS.input_length_max)))
            + (0.18 * normalize_int_with_bounds(int(len(sample.accepting_labels)), (1, 3))),
        ),
        "ambiguity": (0.42 * normalize_int_with_bounds(int(query.candidate_count), (2, len(OPTION_LABELS))))
        + (0.34 * normalize_int_with_bounds(int(len(sample.accepting_labels)), (1, 3)))
        + (0.24 if str(query.automaton_kind) == "nfa" else 0.10),
        "clutter": (0.58 * normalize_int_with_bounds(int(edge_count), (3, max(4, state_count * 3))))
        + (0.25 * crossing_norm)
        + (0.17 * normalize_int_with_bounds(int(render_params.node_radius_px), (_DEFAULTS.node_radius_min_px, _DEFAULTS.node_radius_max_px))),
    }
    return build_graph_complexity(weights=_COMPLEXITY_WEIGHTS, components=components)


@register_task
class GraphRelationAutomatonStringAcceptanceLabelTask:
    """Choose which candidate input string is accepted by a finite automaton."""

    task_id = TASK_ID
    domain = "graph"
    task_group = "relation"

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        """Generate one automaton string-acceptance instance."""

        query = _resolve_query(int(instance_seed), params=params)
        render_params = resolve_graph_render_params(
            params,
            instance_seed=int(instance_seed),
            task_id=TASK_ID,
            render_defaults=_RENDER_DEFAULTS,
            fallback_defaults=_DEFAULTS,
            node_color_name=str(query.node_color_name),
            node_shape_variant="circle",
            edge_routing_variant=str(query.edge_routing_variant),
        )
        graph_rng = spawn_rng(int(instance_seed), f"{TASK_ID}.graph")
        last_error: Exception | None = None
        sample: _AcceptanceSample | None = None
        rendered_scene: RenderedGraphScene | None = None
        image: Image.Image | None = None
        background_meta: Dict[str, Any] = {}
        post_noise_meta: Dict[str, Any] = {}
        option_bboxes: Dict[str, list[int]] = {}
        option_panel_meta: Dict[str, Any] = {}
        for attempt in range(max(1, int(max_attempts))):
            try:
                sample = _sample_acceptance_automaton(graph_rng, query=query)
                background, background_meta = make_background_canvas(
                    canvas_width=int(render_params.canvas_width),
                    canvas_height=int(render_params.canvas_height),
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_BACKGROUND_DEFAULTS,
                )
                node_style_by_label = {
                    str(sample.start_label): {
                        "halo_rgb": tuple(int(value) for value in render_params.title_color_rgb),
                        "halo_width_px": 3,
                        "halo_pad_px": 6,
                    }
                }
                rendered_scene = render_graph_scene(
                    graph_sample=sample.graph_sample,
                    layout_variant=str(query.layout_variant),
                    layout_transform_variant=str(query.layout_transform_variant),
                    render_params=render_params,
                    layout_seed=int(instance_seed + attempt),
                    scene_title="State Transition Diagram",
                    directed=True,
                    base_image=background,
                    edge_text_labels_by_label=sample.transition_labels_by_edge,
                    edge_text_label_font_size_px=max(15, int(render_params.label_font_size_px) - 3),
                    node_style_by_label=node_style_by_label,
                    layout_fallback_variants=("circular", "shell", "layered", "spring"),
                )
                _decorate_automaton_scene(
                    rendered_scene,
                    start_label=str(sample.start_label),
                    accepting_labels=tuple(str(label) for label in sample.accepting_labels),
                    render_params=render_params,
                )
                image_with_options, option_bboxes, option_panel_meta = _draw_candidate_options_panel(
                    rendered_scene=rendered_scene,
                    sample=sample,
                    render_params=render_params,
                    option_panel_height_px=int(
                        params.get(
                            "option_panel_height_px",
                            group_default(_RENDER_DEFAULTS, "option_panel_height_px", _DEFAULTS.option_panel_height_px),
                        )
                    ),
                )
                image, post_noise_meta = apply_post_image_noise(
                    image_with_options,
                    instance_seed=int(instance_seed),
                    params=params,
                    default_config=POST_IMAGE_NOISE_DEFAULTS,
                )
                break
            except Exception as exc:  # pragma: no cover - exercised through retry loop
                last_error = exc
                continue
        else:
            raise RuntimeError("failed to generate automaton string-acceptance instance") from last_error
        if sample is None or rendered_scene is None or image is None:
            raise RuntimeError("failed to generate automaton string-acceptance instance")

        prompt_defaults = required_group_defaults(
            _PROMPT_DEFAULTS,
            (
                "bundle_id",
                "scene_key",
                "task_key",
                "json_output_contract",
                "json_output_contract_answer_only",
                "object_description",
                "evidence_hint",
                "answer_hint",
                "json_example",
                "json_example_answer_only",
            ),
            context=f"prompt defaults for {self.task_id}",
        )
        prompt_json_example, prompt_json_example_answer_only = _build_prompt_json_examples()
        prompt_selection = render_task_prompt_variants(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id=str(prompt_defaults["bundle_id"]),
            scene_key=str(prompt_defaults["scene_key"]),
            task_key=str(prompt_defaults["task_key"]),
            query_key=str(query.query_id),
            answer_or_evidence_keys=PROMPT_OUTPUT_MODES,
            slots={
                "object_description": str(prompt_defaults["object_description"]),
                "json_output_contract": str(prompt_defaults["json_output_contract"]),
                "json_output_contract_answer_only": str(prompt_defaults["json_output_contract_answer_only"]),
                "evidence_hint": str(prompt_defaults["evidence_hint"]),
                "answer_hint": str(prompt_defaults["answer_hint"]),
                "json_example": str(prompt_json_example),
                "json_example_answer_only": str(prompt_json_example_answer_only),
            },
            instance_seed=int(instance_seed),
        )
        prompt_artifacts = build_prompt_trace_artifacts(prompt_selection)

        evidence_projection = projected_node_point_evidence(rendered_scene, sample.accepting_path_labels)
        evidence_path = [[int(round(float(point[0]))), int(round(float(point[1])))] for point in evidence_projection["pixel_point_sequence"]]
        if len(evidence_path) != len(sample.accepting_path_labels):
            raise RuntimeError("automaton acceptance evidence path projection is incomplete")
        answer_gt = TypedValue(type="string", value=str(sample.answer_option_label))
        evidence_gt = TypedValue(type="point_sequence", value=list(evidence_path))

        path_label_set = set(str(label) for label in sample.accepting_path_labels)
        node_entities = [
            {
                "entity_id": f"state_{node.label}",
                "entity_kind": "automaton_state",
                "label": str(node.label),
                "is_start_state": bool(str(node.label) == str(sample.start_label)),
                "is_accepting_state": bool(str(node.label) in set(sample.accepting_labels)),
                "is_in_evidence_path": bool(str(node.label) in path_label_set),
                "path_positions": [int(index) for index, label in enumerate(sample.accepting_path_labels) if str(label) == str(node.label)],
                "center_px": list(node.center_xy),
                "bbox_xyxy": list(node.bbox_xyxy),
                "successors": list(sample.graph_sample.successors_by_label[str(node.label)]),
                "predecessors": list(sample.graph_sample.predecessors_by_label[str(node.label)]),
            }
            for node in rendered_scene.nodes
        ]
        edge_entities = [
            {
                "entity_id": str(edge.edge_id),
                "entity_kind": "automaton_transition",
                "source_state_label": str(edge.node_u_label),
                "target_state_label": str(edge.node_v_label),
                "transition_symbols": str(sample.transition_labels_by_edge[(str(edge.node_u_label), str(edge.node_v_label))]).split(","),
                "segment_px": [list(edge.segment_px[0]), list(edge.segment_px[1])],
                "route_variant": str(edge.route_variant),
                "control_px": list(edge.control_px) if edge.control_px is not None else None,
                "edge_label_bbox_xyxy": list(edge.edge_label_bbox_xyxy) if edge.edge_label_bbox_xyxy is not None else None,
            }
            for edge in rendered_scene.edges
        ]
        option_entities = [
            {
                "entity_id": f"candidate_option_{option_label}",
                "entity_kind": "candidate_input_string",
                "option_label": str(option_label),
                "input_string": str(input_string),
                "is_answer": bool(str(option_label) == str(sample.answer_option_label)),
                "is_accepted": bool(str(option_label) in set(sample.accepted_option_labels)),
                "bbox_xyxy": list(option_bboxes[str(option_label)]),
            }
            for option_label, input_string in sample.candidate_strings_by_option.items()
        ]
        transition_entries = [
            {
                "source_state": str(left),
                "target_state": str(right),
                "symbols": str(symbols).split(","),
            }
            for (left, right), symbols in sample.transition_labels_by_edge.items()
        ]
        complexity = _build_complexity(
            query=query,
            sample=sample,
            render_params=render_params,
            rendered_scene=rendered_scene,
        )
        render_panel_geometry = dict(rendered_scene.panel_geometry)
        render_panel_geometry["canvas_size"] = [int(image.width), int(image.height)]
        render_panel_geometry.update(dict(option_panel_meta))

        trace_payload = {
            "scene_ir": {
                "scene_kind": "automaton_string_acceptance",
                "entities": [*node_entities, *edge_entities, *option_entities],
                "relations": {
                    "query_variant": "default",
                    "query_id": str(query.query_id),
                    "automaton_kind": str(query.automaton_kind),
                    "acceptance_rule": "a candidate string is accepted when at least one path from the start state ends in a double-ring accepting state after all symbols are consumed",
                    "start_state_label": str(sample.start_label),
                    "accepting_state_labels": list(sample.accepting_labels),
                    "candidate_strings_by_option": dict(sample.candidate_strings_by_option),
                    "answer_option_label": str(sample.answer_option_label),
                    "answer_input_string": str(sample.answer_input_string),
                    "accepted_option_labels": list(sample.accepted_option_labels),
                    "accepting_path_labels": list(sample.accepting_path_labels),
                    "transition_function": {
                        str(state): {str(symbol): list(targets) for symbol, targets in per_symbol.items()}
                        for state, per_symbol in sample.transition_function.items()
                    },
                    "transition_labels_by_edge": list(transition_entries),
                    "query_variant_probabilities": dict(query.query_id_probabilities),
                    "state_count_probabilities": dict(query.state_count_probabilities),
                    "input_length_probabilities": dict(query.input_length_probabilities),
                    "answer_option_probabilities": dict(query.answer_option_probabilities),
                },
                "frames": {
                    "pixel": {"origin": [0.0, 0.0], "x_positive": "right", "y_positive": "down"},
                    "panels": dict(render_panel_geometry),
                },
            },
            "query_spec": {
                "query_variant": "default",
                "query_id": str(query.query_id),
                "template_id": str(prompt_defaults["bundle_id"]),
                "prompt_variant": dict(prompt_artifacts.prompt_variant),
                "prompt_variant_active_key": str(prompt_artifacts.prompt_variant_active_key),
                "prompt_variants": dict(prompt_artifacts.prompt_variants_for_trace),
                "params": {
                    "query_variant": str(query.query_id),
                    "query_id": str(query.query_id),
                    "query_variant_probabilities": dict(query.query_id_probabilities),
                    "automaton_kind": str(query.automaton_kind),
                    "state_count": int(query.state_count),
                    "state_count_probabilities": dict(query.state_count_probabilities),
                    "input_length": int(query.input_length),
                    "input_length_min": int(query.input_length_min),
                    "input_length_max": int(query.input_length_max),
                    "input_length_probabilities": dict(query.input_length_probabilities),
                    "candidate_count": int(query.candidate_count),
                    "answer_option_label": str(sample.answer_option_label),
                    "answer_option_probabilities": dict(query.answer_option_probabilities),
                    "answer_input_string": str(sample.answer_input_string),
                    "start_state_label": str(sample.start_label),
                    "accepting_state_labels": list(sample.accepting_labels),
                    "layout_variant": str(query.layout_variant),
                    "layout_variant_probabilities": dict(query.layout_variant_probabilities),
                    "layout_transform_variant": str(query.layout_transform_variant),
                    "layout_transform_variant_probabilities": dict(query.layout_transform_variant_probabilities),
                    "edge_routing_variant": str(query.edge_routing_variant),
                    "edge_routing_variant_probabilities": dict(query.edge_routing_variant_probabilities),
                    "node_color_name": str(query.node_color_name),
                    "node_color_name_probabilities": dict(query.node_color_name_probabilities),
                },
            },
            "render_spec": {
                "canvas_size": [int(image.width), int(image.height)],
                "coord_space": "pixel",
                "panel_geometry": dict(render_panel_geometry),
                "style": {
                    "node_color_name": str(query.node_color_name),
                    "theme_tone": str(render_params.theme_tone),
                    "panel_style_variant": str(render_params.panel_style_variant),
                    "background_color_rgb": list(render_params.background_color_rgb),
                    "panel_fill_rgb": list(render_params.panel_fill_rgb),
                    "panel_border_rgb": list(render_params.panel_border_rgb),
                    "title_color_rgb": list(render_params.title_color_rgb),
                    "edge_color_rgb": list(render_params.edge_color_rgb),
                    "node_fill_rgb": list(render_params.node_fill_rgb),
                    "node_border_rgb": list(render_params.node_border_rgb),
                    "label_text_rgb": list(render_params.label_text_rgb),
                    "label_stroke_rgb": list(render_params.label_stroke_rgb),
                    "node_shape_variant": "circle",
                    "node_radius_px": int(render_params.node_radius_px),
                    "edge_width_px": int(render_params.edge_width_px),
                    "edge_routing_variant": str(rendered_scene.edge_routing_variant),
                    "arrow_length_px": int(render_params.arrow_length_px),
                    "arrow_width_px": int(render_params.arrow_width_px),
                    "node_border_width_px": int(render_params.node_border_width_px),
                    "label_font_size_px": int(render_params.label_font_size_px),
                    "resolved_label_font_size_px": int(rendered_scene.resolved_label_font_size_px),
                    "label_stroke_width_px": int(rendered_scene.resolved_label_stroke_width_px),
                    "automaton_accepting_state_glyph": "double_inner_ring",
                    "automaton_start_state_glyph": "incoming_start_arrow",
                    "transition_labels_by_edge": list(transition_entries),
                    "candidate_option_bboxes_xyxy": dict(option_bboxes),
                    "background_meta": dict(background_meta),
                    "post_image_noise_meta": dict(post_noise_meta),
                },
            },
            "render_map": {"image_id": "img0", "anchors": {}},
            "execution_trace": {
                "query_variant": str(query.query_id),
                "query_id": str(query.query_id),
                "query_variant_probabilities": dict(query.query_id_probabilities),
                "scene_variant": str(rendered_scene.layout_variant),
                "question_format": str(query.query_id),
                "automaton_kind": str(query.automaton_kind),
                "state_count": int(query.state_count),
                "edge_count": int(sample.graph_sample.edge_count),
                "input_length": int(query.input_length),
                "candidate_count": int(query.candidate_count),
                "answer_option": str(sample.answer_option_label),
                "candidate_strings_by_option": dict(sample.candidate_strings_by_option),
                "answer": str(sample.answer_option_label),
                "answer_option_label": str(sample.answer_option_label),
                "answer_input_string": str(sample.answer_input_string),
                "accepted_option_labels": list(sample.accepted_option_labels),
                "accepting_path_labels": list(sample.accepting_path_labels),
                "start_state_label": str(sample.start_label),
                "accepting_state_labels": list(sample.accepting_labels),
                "transition_function": {
                    str(state): {str(symbol): list(targets) for symbol, targets in per_symbol.items()}
                    for state, per_symbol in sample.transition_function.items()
                },
                "transition_labels_by_edge": list(transition_entries),
                "option_bboxes": dict(option_bboxes),
                "state_count_probabilities": dict(query.state_count_probabilities),
                "input_length_probabilities": dict(query.input_length_probabilities),
                "answer_option_probabilities": dict(query.answer_option_probabilities),
                "layout_variant_requested": str(query.layout_variant),
                "layout_variant_used": str(rendered_scene.layout_variant),
                "layout_transform_variant": str(rendered_scene.layout_transform_variant),
                "edge_routing_variant": str(rendered_scene.edge_routing_variant),
                "node_color_name": str(query.node_color_name),
                "crossing_count": int(rendered_scene.crossing_count),
            },
            "witness_symbolic": {
                "type": "automaton_accepting_path",
                "answer_option_label": str(sample.answer_option_label),
                "answer_input_string": str(sample.answer_input_string),
                "state_path_labels": list(sample.accepting_path_labels),
            },
            "projected_evidence": {
                "type": "point_sequence",
                "point_sequence": list(evidence_path),
                "pixel_point_sequence": list(evidence_path),
                "pixel_bbox_set": list(evidence_projection["pixel_bbox_set"]),
            },
        }

        return TaskOutput(
            prompt=str(prompt_artifacts.prompt),
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            trace_payload=trace_payload,
            complexity=complexity,
            task_versions=default_task_versions(),
            query_variant="default",
            scene_id=SCENE_ID,
            query_id=str(query.query_id),
            prompt_variants=dict(prompt_artifacts.prompt_variants),
        )


__all__ = ["GraphRelationAutomatonStringAcceptanceLabelTask"]
