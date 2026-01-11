"""
Report Designer Package

LangGraph-based workflow for generating enterprise-grade Business Report HTML designs.
"""

from report_designer.graph import (
    # Main graph and workflow
    report_design_graph,
    build_report_design_graph,
    run_report_design_workflow,
    # State schemas
    ReportDesignState,
    DesignRequirement,
    Section,
    DesignedPage,
    SectionPayload,
    # LLM configuration
    LLMConfig,
    LLM_CONFIGS,
    create_llm,
    call_llm_with_fallback,
    extract_text_content,
    # Node functions
    fetch_all_data,
    prepare_sections,
    design_section,
    combine_results,
    publish_report,
    fan_out_to_sections,
    extract_body_blocks,
    # Prompt utilities
    prompt_manager,
    render_design_prompt,
)

__all__ = [
    # Main graph and workflow
    "report_design_graph",
    "build_report_design_graph",
    "run_report_design_workflow",
    # State schemas
    "ReportDesignState",
    "DesignRequirement",
    "Section",
    "DesignedPage",
    "SectionPayload",
    # LLM configuration
    "LLMConfig",
    "LLM_CONFIGS",
    "create_llm",
    "call_llm_with_fallback",
    "extract_text_content",
    # Node functions
    "fetch_all_data",
    "prepare_sections",
    "design_section",
    "combine_results",
    "publish_report",
    "fan_out_to_sections",
    "extract_body_blocks",
    # Prompt utilities
    "prompt_manager",
    "render_design_prompt",
]
