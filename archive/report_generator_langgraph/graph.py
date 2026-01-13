"""
LangGraph workflow definition for the Business Report Generator.

This module defines the StateGraph with:
- generate_toc: Creates Table of Contents from user input
- generate_page_content: Creates individual page content (called via Send)
- combine_report: Assembles final markdown report
- fan_out_to_pages: Returns list[Send] for parallel page generation

Workflow Architecture:
    START -> generate_toc -> [fan_out with Send()] -> generate_page_content (xN parallel) -> combine_report -> END
"""

from __future__ import annotations

import json
import logging
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from report_generator_langgraph.context import Configuration
from report_generator_langgraph.prompts import (
    build_toc_prompt,
    build_page_content_prompt,
    DEFAULT_FALLBACK_TOC,
)
from report_generator_langgraph.state import (
    ReportState,
    PageContent,
    TocItem,
    PageGenerationPayload,
)
from report_generator_langgraph.utils import (
    extract_text_content,
    load_chat_model,
    parse_json_from_response,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Node Functions
# =============================================================================


def generate_toc(
    state: ReportState,
    config: RunnableConfig,
) -> dict:
    """
    Generate Table of Contents (TOC) for the report.

    This node uses a lower temperature for structured JSON output.
    If JSON parsing fails, falls back to a default TOC structure.

    Args:
        state: Current workflow state with user input.
        config: Runtime configuration with model settings.

    Returns:
        Dict with 'toc' list and updated 'status'.
    """
    cfg = Configuration.from_runnable_config(config)
    llm = load_chat_model(cfg.model, temperature=cfg.toc_temperature)

    user_input = state["input"]
    prompt = build_toc_prompt(user_input)

    response = llm.invoke(prompt)
    content = extract_text_content(response.content)

    # Parse JSON from response
    try:
        json_content = parse_json_from_response(content)
        toc: list[TocItem] = json.loads(json_content)
        logger.info(f"TOC generated successfully: {len(toc)} sections")

    except (json.JSONDecodeError, IndexError, TypeError) as e:
        logger.warning(f"JSON parsing failed, using fallback TOC: {e}")
        toc = DEFAULT_FALLBACK_TOC

    return {
        "toc": toc,
        "status": "toc_generated",
    }


def generate_page_content(
    state: PageGenerationPayload,
    config: RunnableConfig,
) -> dict:
    """
    Generate content for a single page.

    This node is called in parallel via Send() for each TOC item.
    Uses higher temperature for creative content generation.

    Note:
        The state parameter is the Send payload (PageGenerationPayload),
        not the full ReportState.

    Args:
        state: Send payload with page_info and user_input.
        config: Runtime configuration with model settings.

    Returns:
        Dict with 'pages' list containing single PageContent.
        Returns list to work with operator.add reducer.
    """
    cfg = Configuration.from_runnable_config(config)
    llm = load_chat_model(cfg.model, temperature=cfg.content_temperature)

    page_info = state["page_info"]
    user_input = state["user_input"]

    prompt = build_page_content_prompt(page_info, user_input)
    response = llm.invoke(prompt)
    content = extract_text_content(response.content)

    logger.info(f"Page generated: {page_info['title']} (order: {page_info['order']})")

    # Return as list for operator.add reducer
    page_content: PageContent = {
        "page_id": page_info["page_id"],
        "title": page_info["title"],
        "content": content,
        "order": page_info["order"],
    }

    return {"pages": [page_content]}


def combine_report(state: ReportState) -> dict:
    """
    Combine all generated pages into the final report.

    Pages are sorted by order and assembled into a markdown document
    with header, table of contents, and section contents.

    Args:
        state: Workflow state with generated pages.

    Returns:
        Dict with 'final_report' markdown string and 'status'.
    """
    user_input = state["input"]

    # Sort pages by order
    sorted_pages = sorted(state["pages"], key=lambda p: p["order"])

    # Build report sections
    sections: list[str] = []

    # Report header
    sections.append(f"# {user_input.get('topic', '비즈니스 보고서')}\n")
    sections.append(f"**보고서 유형**: {user_input.get('report_type', '일반')}\n")
    sections.append(f"**작성 대상**: {user_input.get('audience', '')}\n")
    sections.append(f"**작성 팀**: {user_input.get('company_info', '')}\n")
    sections.append("\n---\n")

    # Table of contents
    sections.append("## 목차\n")
    for i, page in enumerate(sorted_pages, 1):
        sections.append(f"{i}. {page['title']}\n")
    sections.append("\n---\n")

    # Page contents
    for page in sorted_pages:
        sections.append(f"\n{page['content']}\n")
        sections.append("\n---\n")

    final_report = "\n".join(sections)

    logger.info(
        f"Report combined: {len(sorted_pages)} sections, {len(final_report)} chars"
    )

    return {
        "final_report": final_report,
        "status": "completed",
    }


# =============================================================================
# Conditional Edge Functions
# =============================================================================


def fan_out_to_pages(state: ReportState) -> list[Send]:
    """
    Fan-out function for parallel page generation.

    Creates a Send object for each TOC item, enabling parallel
    execution of the generate_page_content node.

    Args:
        state: Workflow state with generated TOC.

    Returns:
        List of Send objects targeting generate_page_content node.
    """
    sends: list[Send] = []

    for page_info in state["toc"]:
        payload: PageGenerationPayload = {
            "page_info": page_info,
            "user_input": state["input"],
        }
        sends.append(Send("generate_page_content", payload))

    logger.info(f"Fan-out: {len(sends)} pages for parallel generation")
    return sends


# =============================================================================
# Graph Construction
# =============================================================================


def create_report_generator_graph() -> StateGraph:
    """
    Create the Report Generator StateGraph.

    Workflow:
        START -> generate_toc -> [fan_out] -> generate_page_content (xN) -> combine_report -> END

    Returns:
        Uncompiled StateGraph instance.
    """
    builder = StateGraph(ReportState)

    # Add nodes
    builder.add_node("generate_toc", generate_toc)
    builder.add_node("generate_page_content", generate_page_content)
    builder.add_node("combine_report", combine_report)

    # Add edges
    # 1. START -> TOC generation
    builder.add_edge(START, "generate_toc")

    # 2. TOC -> Fan-out (parallel page generation)
    # fan_out_to_pages returns list[Send] for parallel execution
    builder.add_conditional_edges(
        "generate_toc",
        fan_out_to_pages,
        ["generate_page_content"],  # All Send targets
    )

    # 3. All page generations -> Combine (automatic fan-in)
    builder.add_edge("generate_page_content", "combine_report")

    # 4. Combine -> END
    builder.add_edge("combine_report", END)

    return builder


# Build the graph
builder = create_report_generator_graph()

# Compile with configuration schema
graph = builder.compile()


# =============================================================================
# Main Function
# =============================================================================


def main() -> None:
    """
    Run the report generator graph with sample input.

    This demonstrates the complete workflow:
    1. Define user input parameters
    2. Create initial state
    3. Invoke the graph
    4. Print the generated report
    """
    from dotenv import load_dotenv
    from report_generator_langgraph.state import ReportState, ReportInput

    # Load environment variables
    load_dotenv()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Sample user input
    user_input: ReportInput = {
        "report_type": "주간업무보고",
        "purpose": "현황 공유",
        "audience": "직속 상사",
        "topic": "마케팅팀 주간업무보고",
        "key_message": "캠페인 성과 및 다음 주 계획",
        "company_info": "ABC 주식회사 마케팅팀",
    }

    # Build initial state
    initial_state: ReportState = {
        "input": user_input,
        "toc": [],
        "pages": [],
        "final_report": "",
        "status": "pending",
    }

    logger.info("Starting report generation...")

    # Run the workflow
    result = graph.invoke(initial_state)

    # Print results
    print("\n" + "=" * 60)
    print("GENERATED REPORT")
    print("=" * 60 + "\n")
    print(result["final_report"])
    print("\n" + "=" * 60)
    print(f"Status: {result['status']}")
    print(f"Pages generated: {len(result['pages'])}")
    print("=" * 60)


if __name__ == "__main__":
    main()
