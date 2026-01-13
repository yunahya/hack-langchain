"""Pydantic models for Report Generator API endpoint."""

from typing import Optional, List

from pydantic import BaseModel, Field


class ReportGeneratorConfigOptions(BaseModel):
    """Configuration options for report generator workflow."""

    model: str = Field(
        default="google/gemini-2.0-flash",
        description="LLM model in format 'provider/model_name'",
        examples=["google/gemini-2.0-flash", "azure_openai/gpt-4o", "openai/gpt-4o"],
    )
    toc_temperature: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Temperature for TOC generation (lower = more structured)",
    )
    content_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for page content generation (higher = more creative)",
    )


class ReportGeneratorRequest(BaseModel):
    """Request body for report generation."""

    report_type: str = Field(
        ...,
        description="Report type: 주간업무보고, 기획안, 프로젝트 제안서, 결과 보고서, 회의록",
        examples=["주간업무보고", "기획안", "프로젝트 제안서"],
    )
    purpose: str = Field(
        ...,
        description="Report purpose: 승인 요청, 현황 공유, 의사결정 요청, 아이디어 제안",
        examples=["현황 공유", "승인 요청", "의사결정 요청"],
    )
    audience: str = Field(
        ...,
        description="Target audience: 직속 상사, 임원, 타부서, 외부 클라이언트",
        examples=["직속 상사", "임원", "외부 클라이언트"],
    )
    topic: str = Field(
        ...,
        description="Report topic/title",
        examples=["마케팅팀 주간업무보고", "신규 서비스 기획안"],
    )
    key_message: str = Field(
        ...,
        description="Core message or keywords to emphasize",
        examples=["캠페인 성과 및 다음 주 계획", "예산 승인 필요"],
    )
    company_info: str = Field(
        ...,
        description="Company/team name and industry context",
        examples=["ABC 주식회사 마케팅팀", "XYZ 스타트업 개발팀"],
    )
    tone: Optional[str] = Field(
        default=None,
        description="Writing style: 격식체/반말, 간결함/상세함",
        examples=["격식체, 간결함", "격식체, 상세함"],
    )
    page_count: Optional[int] = Field(
        default=3,
        ge=1,
        le=10,
        description="Target number of pages",
    )
    emphasis: Optional[str] = Field(
        default=None,
        description="Points to emphasize in the report",
    )
    include_visuals: Optional[bool] = Field(
        default=False,
        description="Whether to include visual elements (tables, charts)",
    )
    additional_data: Optional[str] = Field(
        default=None,
        description="Additional data or reference materials",
    )
    config: Optional[ReportGeneratorConfigOptions] = Field(
        default=None,
        description="LLM configuration options",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "report_type": "주간업무보고",
                    "purpose": "현황 공유",
                    "audience": "직속 상사",
                    "topic": "마케팅팀 주간업무보고",
                    "key_message": "캠페인 성과 및 다음 주 계획",
                    "company_info": "ABC 주식회사 마케팅팀",
                    "page_count": 3,
                    "config": {
                        "model": "google/gemini-2.0-flash",
                        "toc_temperature": 0.5,
                        "content_temperature": 0.7,
                    },
                }
            ]
        }
    }


class TocItemResponse(BaseModel):
    """Table of contents item in response."""

    page_id: str = Field(..., description="Unique page identifier")
    title: str = Field(..., description="Section title")
    description: str = Field(..., description="Brief section description")
    order: int = Field(..., ge=1, description="Section order")


class PageContentResponse(BaseModel):
    """Page content in response."""

    page_id: str = Field(..., description="Unique page identifier")
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Markdown content for the page")
    order: int = Field(..., ge=1, description="Section order")


class ReportGeneratorResponse(BaseModel):
    """Response body for report generation."""

    final_report: str = Field(
        ...,
        description="Combined markdown report with all sections",
    )
    toc: List[TocItemResponse] = Field(
        ...,
        description="Generated table of contents",
    )
    pages: List[PageContentResponse] = Field(
        ...,
        description="Individual page contents",
    )
    status: str = Field(
        ...,
        description="Workflow status: completed or error",
    )
    execution_time_ms: int = Field(
        ...,
        ge=0,
        description="Execution time in milliseconds",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "final_report": "# 마케팅팀 주간업무보고\n\n## 목차\n1. 요약\n2. 본문\n...",
                    "toc": [
                        {
                            "page_id": "summary",
                            "title": "요약",
                            "description": "주간 업무 핵심 요약",
                            "order": 1,
                        }
                    ],
                    "pages": [
                        {
                            "page_id": "summary",
                            "title": "요약",
                            "content": "## 요약\n\n이번 주 주요 성과...",
                            "order": 1,
                        }
                    ],
                    "status": "completed",
                    "execution_time_ms": 5678,
                }
            ]
        }
    }
