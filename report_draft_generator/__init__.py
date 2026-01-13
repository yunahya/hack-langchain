"""
Report Draft Generator - Unified LangGraph Workflow.

A merged pipeline that combines report content generation with HTML design
into a single workflow for creating professional business reports.

Usage:
    from report_draft_generator import graph

    result = await graph.ainvoke({
        "input": {
            "report_type": "주간업무보고",
            "purpose": "현황 공유",
            "audience": "직속 상사",
            "topic": "마케팅팀 주간업무보고",
            "key_message": "캠페인 성과 공유",
            "company_info": "ABC 주식회사",
        },
        "toc": [],
        "sections": [],
        "design_requirement": {
            "primary_color": "#1E40AF",
            "secondary_color": "#3B82F6",
            "accent_color": "#10B981",
            "pdf_orientation": "portrait",
        },
        "designed_pages": [],
        "final_html": None,
        "status": "pending",
        "errors": [],
    })
"""

from report_draft_generator.graph import graph

__all__ = ["graph"]
