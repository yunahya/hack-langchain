"""
HTML Page Modifier - LangGraph Workflow Module

A LangGraph-based workflow for AI-powered HTML page modification.

Features:
- Single HTML page modification based on natural language requests
- Design/layout changes (colors, spacing, structure)
- Multi-LLM support (Gemini, Azure OpenAI)
- Modification summary generation

Workflow Architecture:
    START -> modify_page_html -> END

Usage:
    >>> from html_page_modifier_langgraph import graph
    >>> from html_page_modifier_langgraph.state import PageModificationState, PageModificationInput
    >>>
    >>> # Configure input
    >>> user_input: PageModificationInput = {
    ...     "html_content": "<div><h1>Hello</h1></div>",
    ...     "user_request": "헤더 색상을 파란색으로 변경해주세요",
    ...     "page_id": "main_page",
    ...     "page_order": 1,
    ... }
    >>>
    >>> # Build initial state
    >>> initial_state: PageModificationState = {
    ...     "input": user_input,
    ...     "modified_html": "",
    ...     "modification_summary": "",
    ...     "status": "pending",
    ... }
    >>>
    >>> # Run the workflow
    >>> result = graph.invoke(initial_state)
    >>> print(result["modified_html"])

Configuration:
    The workflow can be customized at runtime via RunnableConfig:

    >>> config = {"configurable": {
    ...     "model": "azure_openai/gpt-4o",
    ...     "temperature": 0.2,
    ...     "style_preference": "internal",
    ... }}
    >>> result = graph.invoke(initial_state, config=config)

Exports:
    - graph: Compiled LangGraph workflow
    - PageModificationState: Workflow state TypedDict
    - PageModificationInput: User input TypedDict
    - Configuration: Runtime configuration dataclass
"""

from html_page_modifier_langgraph.graph import graph
from html_page_modifier_langgraph.state import (
    PageModificationState,
    PageModificationInput,
)
from html_page_modifier_langgraph.context import Configuration


__all__ = [
    # Main export
    "graph",
    # State types
    "PageModificationState",
    "PageModificationInput",
    # Configuration
    "Configuration",
]

__version__ = "0.1.0"
