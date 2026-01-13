"""
State definitions for the Business Report Generator workflow.

This module defines TypedDict schemas for:
- ReportInput: User input structure (required + optional fields)
- PageContent: Individual page content structure
- ReportState: Workflow state with reducer for parallel page aggregation
"""

from typing import Annotated
from typing_extensions import TypedDict, NotRequired
import operator


class ReportInput(TypedDict, total=False):
    """
    User input schema for report generation.

    Required fields define the basic report structure.
    Optional fields enhance output quality.
    """

    # Required fields
    report_type: str
    """Report type: 주간업무보고, 기획안, 프로젝트 제안서, 결과 보고서, 회의록, etc."""

    purpose: str
    """Report purpose: 승인 요청, 현황 공유, 의사결정 요청, 아이디어 제안, etc."""

    audience: str
    """Target audience: 직속 상사, 임원, 타부서, 외부 클라이언트, etc."""

    topic: str
    """Report topic/title."""

    key_message: str
    """Core message or keywords to emphasize."""

    company_info: str
    """Company/team name and industry context."""

    # Optional fields (for quality enhancement)
    tone: NotRequired[str]
    """Writing style: 격식체/반말, 간결함/상세함."""

    page_count: NotRequired[int]
    """Target number of pages (default: 3)."""

    emphasis: NotRequired[str]
    """Points to emphasize in the report."""

    include_visuals: NotRequired[bool]
    """Whether to include visual elements (charts, tables)."""

    additional_data: NotRequired[str]
    """Additional data or reference materials."""


class PageContent(TypedDict):
    """
    Individual page content structure.

    Each page is generated in parallel and combined into the final report.
    """

    page_id: str
    """Unique identifier for the page (e.g., 'exec_summary', 'analysis')."""

    title: str
    """Section title."""

    content: str
    """A4 page-appropriate markdown content (800-1200 characters for Korean)."""

    order: int
    """Sort order for final report assembly."""


class TocItem(TypedDict):
    """Table of Contents item structure."""

    page_id: str
    """Unique identifier matching PageContent.page_id."""

    title: str
    """Section title."""

    description: str
    """Brief description of section contents (2-3 sentences)."""

    order: int
    """Section order in the report."""


class ReportState(TypedDict):
    """
    Workflow state schema with reducer for parallel processing.

    The `pages` field uses `operator.add` reducer to aggregate
    results from parallel page generation nodes.
    """

    # Input
    input: ReportInput
    """User input for report generation."""

    # Generated Table of Contents
    toc: list[TocItem]
    """Generated TOC: [{page_id, title, description, order}, ...]."""

    # Page contents - uses reducer for parallel processing
    pages: Annotated[list[PageContent], operator.add]
    """
    Generated page contents.

    Uses operator.add reducer to aggregate results from parallel
    page generation. Each node returns a single-item list.
    """

    # Final output
    final_report: str
    """Combined markdown report."""

    # Workflow metadata
    status: str
    """Current workflow status."""


class PageGenerationPayload(TypedDict):
    """
    Payload structure for Send() API in parallel page generation.

    This is passed to generate_page_content node via Send().
    """

    page_info: TocItem
    """TOC item containing page metadata."""

    user_input: ReportInput
    """Original user input for context."""
