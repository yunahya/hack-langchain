"""
LangGraph workflow definition for the HTML Page Modifier.

This module defines the StateGraph with:
- modify_page_html: Modifies HTML based on user request

Workflow Architecture:
    START -> modify_page_html -> END
"""

from __future__ import annotations

import logging

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END

from html_page_modifier_langgraph.context import Configuration
from html_page_modifier_langgraph.prompts import (
    build_modification_prompt,
    build_summary_prompt,
    DEFAULT_MODIFIED_HTML,
    DEFAULT_SUMMARY,
)
from html_page_modifier_langgraph.state import (
    PageModificationState,
    PageModificationInput,
)
from html_page_modifier_langgraph.utils import (
    extract_text_content,
    extract_html_content,
    load_chat_model,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Node Functions
# =============================================================================


def modify_page_html(
    state: PageModificationState,
    config: RunnableConfig,
) -> dict:
    """
    Modify HTML page based on user request.

    This node takes the current HTML content and user's modification
    request, then generates modified HTML using the configured LLM.

    Args:
        state: Current workflow state with user input.
        config: Runtime configuration with model settings.

    Returns:
        Dict with 'modified_html', 'modification_summary', and 'status'.
    """
    cfg = Configuration.from_runnable_config(config)
    llm = load_chat_model(cfg.model, temperature=cfg.temperature)

    user_input = state["input"]

    # Build modification prompt
    prompt = build_modification_prompt(user_input, cfg.style_preference)

    try:
        # Generate modified HTML
        response = llm.invoke(prompt)
        modified_html = extract_html_content(response.content)

        # Generate modification summary
        summary_prompt = build_summary_prompt(user_input["user_request"])
        summary_response = llm.invoke(summary_prompt)
        summary = extract_text_content(summary_response.content).strip()

        logger.info(
            f"Page modified: {user_input.get('page_id', 'unknown')} "
            f"(order: {user_input.get('page_order', 0)})"
        )
        logger.info(f"Modification summary: {summary}")

        return {
            "modified_html": modified_html,
            "modification_summary": summary,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"HTML modification failed: {e}")
        return {
            "modified_html": DEFAULT_MODIFIED_HTML,
            "modification_summary": DEFAULT_SUMMARY,
            "status": "error",
        }


# =============================================================================
# Graph Construction
# =============================================================================


def create_page_modifier_graph() -> StateGraph:
    """
    Create the HTML Page Modifier StateGraph.

    Workflow:
        START -> modify_page_html -> END

    Returns:
        Uncompiled StateGraph instance.
    """
    builder = StateGraph(PageModificationState)

    # Add nodes
    builder.add_node("modify_page_html", modify_page_html)

    # Add edges
    builder.add_edge(START, "modify_page_html")
    builder.add_edge("modify_page_html", END)

    return builder


# Build the graph
builder = create_page_modifier_graph()

# Compile with configuration schema
graph = builder.compile()


# =============================================================================
# Main Function
# =============================================================================


def main() -> None:
    """
    Run the HTML page modifier graph with sample input.

    This demonstrates the complete workflow:
    1. Define HTML content and modification request
    2. Create initial state
    3. Invoke the graph
    4. Print the modified HTML
    """
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Sample HTML content
    sample_html = """
<div class="page-container">
    <header>
        <h1>주간 업무 보고서</h1>
        <p class="date">2024년 4분기</p>
    </header>

    <section class="summary">
        <h2>요약</h2>
        <p>이번 주 마케팅 캠페인 성과가 우수했습니다.</p>
        <ul>
            <li>클릭률 15% 상승</li>
            <li>전환율 3.2% 달성</li>
        </ul>
    </section>
</div>
"""

    # Sample user input
    user_input: PageModificationInput = {
        "html_content": sample_html,
        "user_request": "헤더 배경색을 파란색(#3498db)으로 변경하고, 제목을 흰색으로 만들어주세요. 요약 섹션에 연한 회색 배경을 추가해주세요.",
        "page_id": "weekly_summary",
        "page_order": 1,
    }

    # Build initial state
    initial_state: PageModificationState = {
        "input": user_input,
        "modified_html": "",
        "modification_summary": "",
        "status": "pending",
    }

    logger.info("Starting HTML page modification...")

    # Run the workflow
    result = graph.invoke(initial_state)

    # Print results
    print("\n" + "=" * 60)
    print("MODIFIED HTML")
    print("=" * 60 + "\n")
    print(result["modified_html"])
    print("\n" + "=" * 60)
    print(f"Status: {result['status']}")
    print(f"Summary: {result['modification_summary']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
