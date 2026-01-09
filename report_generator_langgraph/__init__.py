"""
Business Report Generator - LangGraph Workflow Module

A LangGraph-based workflow for generating Korean business reports
with parallel page generation using the Send() API.

Features:
- Dynamic TOC generation based on report type and purpose
- Parallel page content generation using Send() API
- operator.add reducer for aggregating parallel results
- Multi-LLM support (Gemini, Azure OpenAI)
- A4-optimized page content (800-1200 Korean characters)

Workflow Architecture:
    START -> generate_toc -> [fan_out] -> generate_page_content (xN) -> combine_report -> END

Usage:
    >>> from report_generator_langgraph import graph
    >>> from report_generator_langgraph.state import ReportState, ReportInput
    >>>
    >>> # Configure input
    >>> user_input: ReportInput = {
    ...     "report_type": "주간업무보고",
    ...     "purpose": "현황 공유",
    ...     "audience": "직속 상사",
    ...     "topic": "마케팅팀 주간업무보고",
    ...     "key_message": "캠페인 성과 공유",
    ...     "company_info": "ABC 주식회사 마케팅팀",
    ... }
    >>>
    >>> # Build initial state
    >>> initial_state: ReportState = {
    ...     "input": user_input,
    ...     "toc": [],
    ...     "pages": [],
    ...     "final_report": "",
    ...     "status": "pending",
    ... }
    >>>
    >>> # Run the workflow
    >>> result = graph.invoke(initial_state)
    >>> print(result["final_report"])

Configuration:
    The workflow can be customized at runtime via RunnableConfig:

    >>> config = {"configurable": {
    ...     "model": "azure_openai/gpt-4o",
    ...     "toc_temperature": 0.3,
    ...     "content_temperature": 0.8,
    ... }}
    >>> result = graph.invoke(initial_state, config=config)

Exports:
    - graph: Compiled LangGraph workflow
    - ReportState: Workflow state TypedDict
    - ReportInput: User input TypedDict
    - PageContent: Page content TypedDict
    - Configuration: Runtime configuration dataclass
"""

from report_generator_langgraph.graph import graph
from report_generator_langgraph.state import (
    ReportState,
    ReportInput,
    PageContent,
    TocItem,
    PageGenerationPayload,
)
from report_generator_langgraph.context import Configuration


__all__ = [
    # Main export
    "graph",
    # State types
    "ReportState",
    "ReportInput",
    "PageContent",
    "TocItem",
    "PageGenerationPayload",
    # Configuration
    "Configuration",
]

__version__ = "0.1.0"
