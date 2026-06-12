"""Consolidated ScreenSpot-style GUI professional target task."""

from __future__ import annotations

from ...registry import register_task
from trace.tasks.shared.fixed_query import FixedPagesQueryTaskMixin
from .professional_target_common import (
    ProfessionalGuiRelationTaskBase,
    ProfessionalTaskDefinition,
    ProfessionalVariantSpec,
)


TASK_ID = "pages_workspace_professional_target_source"
SUPPORTED_QUERY_IDS = (
    "toolbar_palette_control_label",
    "property_panel_control_label",
    "canvas_workspace_control_label",
    "code_workspace_control_label",
    "file_dialog_control_label",
)


def _variant(
    name: str,
    *,
    layout: str,
    scene_title: str,
    context_title: str,
    guide_title: str,
    header_title: str,
    context_kind: str,
    guide_kind: str,
    header_kind: str,
    control_role: str,
    context_pool: tuple[str, ...],
    actions: tuple[str, ...],
    cues: tuple[str, ...],
    instruction_templates: tuple[str, ...],
) -> ProfessionalVariantSpec:
    return ProfessionalVariantSpec(
        name=name,
        layout=layout,
        scene_title=scene_title,
        context_title=context_title,
        guide_title=guide_title,
        header_title=header_title,
        context_kind=context_kind,
        guide_kind=guide_kind,
        header_kind=header_kind,
        control_role=control_role,
        context_pool_key=f"{name}_context_pool",
        action_pool_key=f"{name}_action_pool",
        cue_pool_key=f"{name}_cue_pool",
        context_pool=context_pool,
        action_pool=actions,
        cue_pool=cues,
        instruction_templates=instruction_templates,
    )


_DEFAULT_INSTRUCTIONS = (
    'For "{context_label}", use the guide cue "{cue_label}".',
    'In "{context_label}", choose the control for "{cue_label}".',
    'Find the "{cue_label}" control associated with "{context_label}".',
    'Use "{cue_label}" for the visible context "{context_label}".',
    'Select the labeled control for "{cue_label}" in "{context_label}".',
)


TASK_DEFINITION = ProfessionalTaskDefinition(
    task_id=TASK_ID,
    scene_kind="gui_professional_target",
    question_format="gui_professional_target_label",
    supported_query_ids=SUPPORTED_QUERY_IDS,
    variants=(
        _variant(
            "toolbar_palette_control_label",
            layout="toolbar_palette",
            scene_title="Tool Palette Workspace",
            context_title="Tool contexts",
            guide_title="Tool Cue Guide",
            header_title="Coded tool headers",
            context_kind="tool_context",
            guide_kind="tool_cue_card",
            header_kind="tool_code_header",
            control_role="toolbar_palette_control",
            context_pool=("Sketch", "Model", "Inspect", "Annotate", "Review"),
            actions=("Copy", "Mirror", "Align", "Measure", "Reset"),
            cues=("copy item", "flip item", "line up", "read span", "fresh state"),
            instruction_templates=_DEFAULT_INSTRUCTIONS,
        ),
        _variant(
            "property_panel_control_label",
            layout="property_panel",
            scene_title="Inspector Settings Panel",
            context_title="Inspector sections",
            guide_title="Setting Cue Guide",
            header_title="Coded setting headers",
            context_kind="inspector_section",
            guide_kind="setting_cue_card",
            header_kind="setting_code_header",
            control_role="property_panel_control",
            context_pool=("General", "Layout", "Display", "Data", "Output"),
            actions=("Name", "Width", "Visible", "Required", "Format"),
            cues=("title field", "wide value", "show item", "must fill", "output type"),
            instruction_templates=_DEFAULT_INSTRUCTIONS,
        ),
        _variant(
            "canvas_workspace_control_label",
            layout="canvas_tool",
            scene_title="Canvas And Viewport Controls",
            context_title="Canvas targets",
            guide_title="Canvas Cue Guide",
            header_title="Coded viewport headers",
            context_kind="canvas_target",
            guide_kind="canvas_cue_card",
            header_kind="canvas_code_header",
            control_role="canvas_workspace_control",
            context_pool=("Object A", "Object B", "Object C", "Object D", "Object E"),
            actions=("Bounds", "Guide", "Mask", "Note", "Measure"),
            cues=("edge box", "helper line", "cover area", "text note", "read length"),
            instruction_templates=_DEFAULT_INSTRUCTIONS,
        ),
        _variant(
            "code_workspace_control_label",
            layout="code_workspace",
            scene_title="IDE Workspace Controls",
            context_title="Code targets",
            guide_title="IDE Cue Guide",
            header_title="Coded IDE headers",
            context_kind="code_target",
            guide_kind="ide_cue_card",
            header_kind="ide_code_header",
            control_role="code_workspace_control",
            context_pool=("App", "Tests", "API", "Worker", "Docs"),
            actions=("Open", "Save", "Split", "Search", "Kill"),
            cues=("show file", "write disk", "second pane", "find text", "end shell"),
            instruction_templates=_DEFAULT_INSTRUCTIONS,
        ),
        _variant(
            "file_dialog_control_label",
            layout="file_dialog",
            scene_title="File Dialog And Window Controls",
            context_title="Dialog locations",
            guide_title="Dialog Cue Guide",
            header_title="Coded dialog headers",
            context_kind="dialog_location",
            guide_kind="dialog_cue_card",
            header_kind="dialog_code_header",
            control_role="file_dialog_control",
            context_pool=("Desktop", "Downloads", "Projects", "Shared", "Archive"),
            actions=("Select", "Preview", "Save", "Open", "Options"),
            cues=("pick file", "quick view", "write file", "choose file", "extra choices"),
            instruction_templates=_DEFAULT_INSTRUCTIONS,
        ),
    ),
)


class PagesRelationProfessionalTargetLabelTask(ProfessionalGuiRelationTaskBase):
    """Identify a labeled target control in a professional application workspace."""

    task_id = TASK_ID
    definition = TASK_DEFINITION


@register_task
class PagesWorkspaceToolbarPaletteControlLabelTask(FixedPagesQueryTaskMixin):
    """Identify a toolbar-palette control from a visible guide cue."""

    task_id = "task_pages__workspace__toolbar_palette_control_label"
    domain = "pages"
    scene_id = "relation"
    public_scene_id = "workspace"
    fixed_query_id = "toolbar_palette_control_label"
    source_task_cls = PagesRelationProfessionalTargetLabelTask


@register_task
class PagesWorkspacePropertyPanelControlLabelTask(FixedPagesQueryTaskMixin):
    """Identify a property-panel control from a visible setting cue."""

    task_id = "task_pages__workspace__property_panel_control_label"
    domain = "pages"
    scene_id = "relation"
    public_scene_id = "workspace"
    fixed_query_id = "property_panel_control_label"
    source_task_cls = PagesRelationProfessionalTargetLabelTask


@register_task
class PagesWorkspaceCanvasWorkspaceControlLabelTask(FixedPagesQueryTaskMixin):
    """Identify a canvas workspace control from a visible canvas cue."""

    task_id = "task_pages__workspace__canvas_workspace_control_label"
    domain = "pages"
    scene_id = "relation"
    public_scene_id = "workspace"
    fixed_query_id = "canvas_workspace_control_label"
    source_task_cls = PagesRelationProfessionalTargetLabelTask


@register_task
class PagesWorkspaceCodeWorkspaceControlLabelTask(FixedPagesQueryTaskMixin):
    """Identify an IDE workspace control from a visible code cue."""

    task_id = "task_pages__workspace__code_workspace_control_label"
    domain = "pages"
    scene_id = "relation"
    public_scene_id = "workspace"
    fixed_query_id = "code_workspace_control_label"
    source_task_cls = PagesRelationProfessionalTargetLabelTask


@register_task
class PagesWorkspaceFileDialogControlLabelTask(FixedPagesQueryTaskMixin):
    """Identify a file-dialog control from a visible dialog cue."""

    task_id = "task_pages__workspace__file_dialog_control_label"
    domain = "pages"
    scene_id = "relation"
    public_scene_id = "workspace"
    fixed_query_id = "file_dialog_control_label"
    source_task_cls = PagesRelationProfessionalTargetLabelTask


__all__ = [
    "PagesRelationProfessionalTargetLabelTask",
    "PagesWorkspaceCanvasWorkspaceControlLabelTask",
    "PagesWorkspaceCodeWorkspaceControlLabelTask",
    "PagesWorkspaceFileDialogControlLabelTask",
    "PagesWorkspacePropertyPanelControlLabelTask",
    "PagesWorkspaceToolbarPaletteControlLabelTask",
    "SUPPORTED_QUERY_IDS",
]
