"""
Report Designer 패키지

엔터프라이즈급 비즈니스 보고서 HTML 디자인을 생성하는 LangGraph 기반 워크플로우.
"""

# 상태 스키마
from report_designer.state import (
    DesignRequirement,
    DesignedPage,
    ReportDesignState,
    Section,
    SectionPayload,
)

# 설정
from report_designer.context import (
    Configuration,
    ConfigurableFields,
)

# 프롬프트
from report_designer.prompts import (
    PromptManager,
    build_user_prompt,
    get_system_prompt,
    prompt_manager,
    render_design_prompt,
)

# 유틸리티
from report_designer.utils import (
    DEFAULT_LLM_CONFIGS,
    LLMConfig,
    call_llm_with_fallback,
    create_llm,
    extract_body_blocks,
    extract_text_content,
    load_chat_model,
)

# 그래프 및 워크플로우
from report_designer.graph import (
    build_report_design_graph,
    combine_results,
    design_section,
    fan_out_to_sections,
    fetch_all_data,
    prepare_sections,
    publish_report,
    report_design_graph,
    run_report_design_workflow,
)


__all__ = [
    # 상태 스키마
    "DesignRequirement",
    "DesignedPage",
    "ReportDesignState",
    "Section",
    "SectionPayload",
    # 설정
    "Configuration",
    "ConfigurableFields",
    # 프롬프트
    "PromptManager",
    "build_user_prompt",
    "get_system_prompt",
    "prompt_manager",
    "render_design_prompt",
    # 유틸리티
    "DEFAULT_LLM_CONFIGS",
    "LLMConfig",
    "call_llm_with_fallback",
    "create_llm",
    "extract_body_blocks",
    "extract_text_content",
    "load_chat_model",
    # 그래프 및 워크플로우
    "build_report_design_graph",
    "combine_results",
    "design_section",
    "fan_out_to_sections",
    "fetch_all_data",
    "prepare_sections",
    "publish_report",
    "report_design_graph",
    "run_report_design_workflow",
]
