"""
LangGraph workflow for the Report Draft Generator.

This module defines the unified workflow that merges report generation
and HTML design into a single pipeline:

Phase 1 (Content Generation):
    START -> generate_toc -> [fan_out] -> generate_page_content (×N parallel)
          -> combine_and_prepare

Phase 2 (HTML Design):
    combine_and_prepare -> [fan_out] -> design_section (×N parallel)
                        -> combine_results -> END

Key patterns:
- Send API for fan-out parallel processing
- operator.add reducers for fan-in aggregation
- 3-tier LLM fallback chain for design reliability
- Unified ReportSection schema serving both phases
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from report_draft_generator.context import Configuration
from report_draft_generator.prompts import (
    build_toc_prompt,
    build_page_content_prompt,
    get_design_system_prompt,
    render_design_prompt,
    build_design_user_prompt,
    DEFAULT_FALLBACK_TOC,
)
from report_draft_generator.state import (
    DraftGeneratorState,
    ReportSection,
    TocItem,
    DesignedPage,
    PageGenerationPayload,
    DesignSectionPayload,
    DEFAULT_DESIGN_REQUIREMENT,
)
from report_draft_generator.utils import (
    extract_text_content,
    load_chat_model,
    parse_json_from_response,
    call_llm_with_fallback,
    extract_body_blocks,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Output Directory Management
# =============================================================================

# Global output directory for current run (set at workflow start)
_output_dir: Path | None = None


def get_output_dir() -> Path:
    """Get or create the output directory for current workflow run."""
    global _output_dir
    if _output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _output_dir = Path("outputs") / f"report_{timestamp}"
        _output_dir.mkdir(parents=True, exist_ok=True)
        # Create subdirectories
        (_output_dir / "01_toc").mkdir(exist_ok=True)
        (_output_dir / "02_sections").mkdir(exist_ok=True)
        (_output_dir / "03_designed").mkdir(exist_ok=True)
        logger.info(f"📁 Output directory created: {_output_dir}")
    return _output_dir


def reset_output_dir() -> None:
    """Reset output directory for a new workflow run."""
    global _output_dir
    _output_dir = None


def save_file(subdir: str, filename: str, content: str, is_json: bool = False) -> Path:
    """
    Save content to a file in the output directory.

    Args:
        subdir: Subdirectory name (e.g., '01_toc', '02_sections')
        filename: File name
        content: Content to save
        is_json: If True, pretty-print JSON content

    Returns:
        Path to the saved file
    """
    output_dir = get_output_dir()
    file_path = output_dir / subdir / filename

    if is_json and isinstance(content, (dict, list)):
        content = json.dumps(content, ensure_ascii=False, indent=2)

    file_path.write_text(content, encoding="utf-8")
    logger.info(f"💾 Saved: {file_path}")
    return file_path


# =============================================================================
# Phase 1: Content Generation Nodes
# =============================================================================


def generate_toc(
    state: DraftGeneratorState,
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
        logger.info(f"✅ TOC generated successfully: {len(toc)} sections")

    except (json.JSONDecodeError, IndexError, TypeError) as e:
        logger.warning(f"⚠️ JSON parsing failed, using fallback TOC: {e}")
        toc = DEFAULT_FALLBACK_TOC

    # Save TOC to file
    save_file(
        "01_toc",
        "toc.json",
        json.dumps(toc, ensure_ascii=False, indent=2),
    )

    # Also save the raw LLM response for debugging
    save_file("01_toc", "toc_raw_response.txt", content)

    return {
        "toc": toc,
        "status": "toc_generated",
    }


def generate_page_content(
    state: PageGenerationPayload,
    config: RunnableConfig,
) -> dict:
    """
    Generate content for a single page and format as ReportSection.

    This node is called in parallel via Send() for each TOC item.
    Uses higher temperature for creative content generation.

    The output is a unified ReportSection that contains both generator
    fields (content) and designer fields (section_key, section_number).

    Note:
        The state parameter is the Send payload (PageGenerationPayload),
        not the full DraftGeneratorState.

    Args:
        state: Send payload with page_info and user_input.
        config: Runtime configuration with model settings.

    Returns:
        Dict with 'sections' list containing single ReportSection.
        Returns list to work with operator.add reducer.
    """
    cfg = Configuration.from_runnable_config(config)
    llm = load_chat_model(cfg.model, temperature=cfg.content_temperature)

    page_info = state["page_info"]
    user_input = state["user_input"]

    prompt = build_page_content_prompt(page_info, user_input)
    response = llm.invoke(prompt)
    content = extract_text_content(response.content)

    logger.info(f"✅ Page generated: {page_info['title']} (order: {page_info['order']})")

    # Save section markdown to file
    safe_page_id = page_info["page_id"].replace("/", "_").replace("\\", "_")
    save_file(
        "02_sections",
        f"{page_info['order']:02d}_{safe_page_id}.md",
        content,
    )

    # Create unified ReportSection with both generator and designer fields
    section: ReportSection = {
        # Core fields (from generator)
        "order": page_info["order"],
        "page_id": page_info["page_id"],
        "title": page_info["title"],
        "content": content,
        # Designer fields (auto-derived)
        "section_title": page_info["title"],
        "section_number": f"{page_info['order']}.0",
        "section_key": page_info["page_id"].upper(),
        "parent_path": None,
    }

    return {"sections": [section]}


def combine_and_prepare(state: DraftGeneratorState) -> dict:
    """
    Bridge Phase 1 (Generation) to Phase 2 (Design).

    This node:
    1. Receives aggregated sections from parallel page generation
    2. Initializes default design requirements if not set
    3. Saves combined markdown report
    4. Marks state as ready for design phase

    Args:
        state: Workflow state with generated sections.

    Returns:
        Dict with 'design_requirement' and updated 'status'.
    """
    sections = state.get("sections", [])
    design_req = state.get("design_requirement")
    user_input = state.get("input", {})

    # Use default design requirement if not provided
    if not design_req:
        design_req = DEFAULT_DESIGN_REQUIREMENT

    # Sort sections by order
    sorted_sections = sorted(sections, key=lambda s: s.get("order", 0))

    # Build combined markdown report
    markdown_parts = [
        f"# {user_input.get('topic', '비즈니스 보고서')}",
        "",
        f"**보고서 유형**: {user_input.get('report_type', '일반')}",
        f"**보고 대상**: {user_input.get('audience', '')}",
        f"**작성 팀**: {user_input.get('company_info', '')}",
        "",
        "---",
        "",
        "## 목차",
        "",
    ]

    # Add TOC
    for section in sorted_sections:
        markdown_parts.append(f"- {section.get('title', 'Untitled')}")

    markdown_parts.extend(["", "---", ""])

    # Add section contents
    for section in sorted_sections:
        markdown_parts.append(section.get("content", ""))
        markdown_parts.extend(["", "---", ""])

    combined_markdown = "\n".join(markdown_parts)

    # Save combined markdown
    save_file("02_sections", "00_combined_report.md", combined_markdown)

    # Save sections as JSON for reference
    save_file(
        "02_sections",
        "sections_data.json",
        json.dumps(sorted_sections, ensure_ascii=False, indent=2),
    )

    logger.info(
        f"✅ Prepared {len(sections)} sections for design phase. "
        f"Colors: {design_req.get('primary_color')}"
    )

    return {
        "design_requirement": design_req,
        "status": "ready_for_design",
    }


# =============================================================================
# Phase 2: HTML Design Nodes
# =============================================================================


async def design_section(state: DesignSectionPayload) -> dict:
    """
    Design a single section with 3-tier LLM fallback.

    This node is called in parallel via Send() for each section.
    Combines: template rendering + LLM call + body extraction.

    Template processing:
    - Content length analysis (short/medium/long/multipage)
    - Layout pattern selection (KPI dashboard, data analysis, etc.)
    - Multi-page splitting for content > 1200 chars

    Args:
        state: Send payload with section, design_requirement, language_code.

    Returns:
        Dict with 'designed_pages' list and 'errors'.
    """
    section = state["section"]
    design_req = state["design_requirement"]
    language_code = state.get("language_code", "ko")
    outline_id = state.get("outline_id", "draft")

    # Calculate content length for layout decisions
    content = section.get("content", "")
    content_length = len(content)

    try:
        # Render design prompt with Jinja2 template
        design_prompt = render_design_prompt(
            section=section,
            design_requirement=design_req,
            content_length=content_length,
        )

        # Build system and user prompts
        system_prompt = get_design_system_prompt(language_code)
        user_prompt = build_design_user_prompt(design_prompt, language_code)

        # Call LLM with fallback chain
        html_content, model_used = await call_llm_with_fallback(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # Extract <body> blocks (multiple for multi-page sections)
        pages = extract_body_blocks(
            html_content=html_content,
            section=section,
            outline_id=outline_id,
            model_used=model_used,
        )

        # Save each designed page HTML
        section_order = section.get("order", 0)
        safe_title = section.get("page_id", "unknown").replace("/", "_").replace("\\", "_")

        for page_idx, page in enumerate(pages):
            filename = f"{section_order:02d}_{safe_title}"
            if len(pages) > 1:
                filename += f"_page{page_idx + 1}"
            filename += ".html"

            # Wrap body content in full HTML document for preview
            full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{section.get('section_title', 'Section')}</title>
</head>
{page.get('html_content', '')}
</html>"""
            save_file("03_designed", filename, full_html)

        logger.info(
            f"✅ Section designed: {section.get('section_title')} "
            f"({len(pages)} pages, model: {model_used})"
        )

        return {
            "designed_pages": pages,
            "errors": [],
        }

    except Exception as e:
        error_msg = f"Section '{section.get('section_title', 'unknown')}' failed: {str(e)}"
        logger.error(error_msg)
        return {
            "designed_pages": [],
            "errors": [error_msg],
        }


def combine_results(state: DraftGeneratorState) -> dict:
    """
    Combine all designed pages into final output.

    Sorts pages by (order, page_index) to maintain section order
    and handle multi-page sections correctly.

    Args:
        state: Workflow state with designed pages.

    Returns:
        Dict with 'final_html' (optional) and 'status'.
    """
    pages = state.get("designed_pages", [])
    errors = state.get("errors", [])

    # Sort by (order, page_index)
    sorted_pages = sorted(
        pages,
        key=lambda x: (x.get("order", 0), x.get("page_index", 0)),
    )

    # Reassign order (1-based) for final output
    final_pages: list[DesignedPage] = []
    for idx, page in enumerate(sorted_pages, start=1):
        final_pages.append({
            "html_content": page["html_content"],
            "order": idx,
            "section_title": page["section_title"],
            "section_number": page.get("section_number"),
            "outline_id": page["outline_id"],
            "page_index": page.get("page_index", 0),
            "model_used": page.get("model_used"),
        })

    # Optionally combine all HTML into a single document
    html_parts = [p["html_content"] for p in final_pages]
    final_html = "\n<!-- PAGE BREAK -->\n".join(html_parts) if html_parts else None

    # Save final combined HTML report
    output_dir = get_output_dir()

    if final_html:
        # Create a complete HTML document
        full_report = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Report Draft - Final</title>
    <style>
        @media print {{
            .page-break {{ page-break-after: always; }}
        }}
    </style>
</head>
<body>
{final_html}
</body>
</html>"""
        # Save in root of output directory
        final_path = output_dir / "final_report.html"
        final_path.write_text(full_report, encoding="utf-8")
        logger.info(f"💾 Final report saved: {final_path}")

    # Save designed pages data as JSON
    pages_data_path = output_dir / "03_designed" / "pages_data.json"
    pages_data_path.write_text(
        json.dumps(final_pages, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"💾 Pages data saved: {pages_data_path}")

    # Save summary
    summary = {
        "status": "completed" if not errors else "completed_with_errors",
        "total_pages": len(final_pages),
        "errors_count": len(errors),
        "errors": errors,
        "output_directory": str(output_dir),
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"💾 Summary saved: {summary_path}")

    logger.info(
        f"✅ Combined {len(final_pages)} pages. "
        f"Errors: {len(errors)}. "
        f"Output: {output_dir}"
    )

    return {
        "designed_pages": [],  # Clear for reducer, use final_pages below
        "final_html": final_html,
        "status": "completed" if not errors else "completed_with_errors",
    }


# =============================================================================
# Fan-out Functions
# =============================================================================


def fan_out_to_pages(state: DraftGeneratorState) -> list[Send]:
    """
    Fan-out function for parallel page content generation.

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

    logger.info(f"Fan-out to pages: {len(sends)} parallel tasks")
    return sends


def fan_out_to_design(state: DraftGeneratorState) -> list[Send]:
    """
    Fan-out function for parallel section design.

    Creates a Send object for each section, enabling parallel
    execution of the design_section node.

    Args:
        state: Workflow state with generated sections.

    Returns:
        List of Send objects targeting design_section node.
    """
    sections = state.get("sections", [])
    design_req = state.get("design_requirement", DEFAULT_DESIGN_REQUIREMENT)

    sends: list[Send] = []

    for section in sections:
        payload: DesignSectionPayload = {
            "section": section,
            "design_requirement": design_req,
            "language_code": "ko",  # Default for business reports
            "outline_id": f"draft_{section.get('page_id', 'unknown')}",
        }
        sends.append(Send("design_section", payload))

    logger.info(f"Fan-out to design: {len(sends)} parallel tasks")
    return sends


# =============================================================================
# Graph Construction
# =============================================================================


def create_draft_generator_graph() -> StateGraph:
    """
    Create the Report Draft Generator StateGraph.

    Workflow:
        Phase 1 (Content Generation):
            START -> generate_toc -> [fan_out] -> generate_page_content (×N)
                  -> combine_and_prepare

        Phase 2 (HTML Design):
            combine_and_prepare -> [fan_out] -> design_section (×N)
                               -> combine_results -> END

    Returns:
        Compiled StateGraph instance.
    """
    builder = StateGraph(DraftGeneratorState)

    # Add nodes
    # Phase 1: Content Generation
    builder.add_node("generate_toc", generate_toc)
    builder.add_node("generate_page_content", generate_page_content)
    builder.add_node("combine_and_prepare", combine_and_prepare)

    # Phase 2: HTML Design
    builder.add_node("design_section", design_section)
    builder.add_node("combine_results", combine_results)

    # Add edges
    # 1. START -> TOC generation
    builder.add_edge(START, "generate_toc")

    # 2. TOC -> Fan-out (parallel page generation)
    builder.add_conditional_edges(
        "generate_toc",
        fan_out_to_pages,
        ["generate_page_content"],
    )

    # 3. Page generation -> Combine and prepare
    builder.add_edge("generate_page_content", "combine_and_prepare")

    # 4. Prepare -> Fan-out (parallel section design)
    builder.add_conditional_edges(
        "combine_and_prepare",
        fan_out_to_design,
        ["design_section"],
    )

    # 5. Section design -> Combine results
    builder.add_edge("design_section", "combine_results")

    # 6. Combine -> END
    builder.add_edge("combine_results", END)

    return builder


# Build and compile the graph
builder = create_draft_generator_graph()
graph = builder.compile()


# =============================================================================
# Main Function
# uv run python -m report_draft_generator.graph
# =============================================================================

async def main() -> None:
    """
    Run the report draft generator with sample input.

    This demonstrates the complete workflow:
    1. Define user input parameters
    2. Create initial state
    3. Invoke the graph
    4. Print results

    Output files are saved to: outputs/report_{timestamp}/
    """
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Reset output directory for fresh run
    reset_output_dir()

    # Sample user input
    from report_draft_generator.state import ReportInput

    user_input: ReportInput = {
        "report_type": "주간업무보고",
        "purpose": "현황 공유",
        "audience": "직속 상사",
        "topic": "마케팅팀 주간업무보고",
        "key_message": "캠페인 성과 및 다음 주 계획",
        "company_info": "ABC 주식회사 마케팅팀",
    }

    # Build initial state
    initial_state: DraftGeneratorState = {
        "input": user_input,
        "toc": [],
        "sections": [],
        "design_requirement": DEFAULT_DESIGN_REQUIREMENT,
        "designed_pages": [],
        "final_html": None,
        "status": "pending",
        "errors": [],
    }

    logger.info("Starting report draft generation...")

    # Run the workflow (async because design_section is async)
    result = await graph.ainvoke(initial_state)

    # Print results
    output_dir = get_output_dir()

    print("\n" + "=" * 60)
    print("📋 REPORT DRAFT GENERATOR - COMPLETE")
    print("=" * 60)
    print(f"Status: {result['status']}")
    print(f"Sections generated: {len(result.get('sections', []))}")
    print(f"Pages designed: {len(result.get('designed_pages', []))}")
    print(f"Errors: {len(result.get('errors', []))}")

    if result.get("errors"):
        print("\n⚠️ Errors:")
        for error in result["errors"]:
            print(f"  - {error}")

    if result.get("final_html"):
        print(f"\nFinal HTML length: {len(result['final_html'])} chars")

    print(f"\n📁 Output saved to: {output_dir}")
    print("\nOutput structure:")
    print(f"  {output_dir}/")
    print("  ├── 01_toc/")
    print("  │   ├── toc.json")
    print("  │   └── toc_raw_response.txt")
    print("  ├── 02_sections/")
    print("  │   ├── 00_combined_report.md")
    print("  │   ├── 01_*.md, 02_*.md, ...")
    print("  │   └── sections_data.json")
    print("  ├── 03_designed/")
    print("  │   ├── 01_*.html, 02_*.html, ...")
    print("  │   └── pages_data.json")
    print("  ├── final_report.html")
    print("  └── summary.json")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
