"""Pydantic models for API request and response schemas."""

from api.models.common import ErrorResponse, WorkflowStatus
from api.models.html_modifier import (
    HtmlModifierRequest,
    HtmlModifierResponse,
    HtmlModifierConfigOptions,
)
from api.models.report_generator import (
    ReportGeneratorRequest,
    ReportGeneratorResponse,
    ReportGeneratorConfigOptions,
    TocItemResponse,
    PageContentResponse,
)

__all__ = [
    "ErrorResponse",
    "WorkflowStatus",
    "HtmlModifierRequest",
    "HtmlModifierResponse",
    "HtmlModifierConfigOptions",
    "ReportGeneratorRequest",
    "ReportGeneratorResponse",
    "ReportGeneratorConfigOptions",
    "TocItemResponse",
    "PageContentResponse",
]
