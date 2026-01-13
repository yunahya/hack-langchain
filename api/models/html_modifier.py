"""Pydantic models for HTML Modifier API endpoint."""

from typing import Optional, Literal

from pydantic import BaseModel, Field


class HtmlModifierConfigOptions(BaseModel):
    """Configuration options for HTML modifier workflow."""

    model: str = Field(
        default="google/gemini-2.0-flash",
        description="LLM model in format 'provider/model_name'",
        examples=["google/gemini-2.0-flash", "azure_openai/gpt-4o", "openai/gpt-4o"],
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="LLM temperature for generation",
    )
    style_preference: Literal["inline", "internal"] = Field(
        default="inline",
        description="CSS styling approach: inline styles or internal <style> tag",
    )


class HtmlModifierRequest(BaseModel):
    """Request body for HTML page modification."""

    html_content: str = Field(
        ...,
        description="Current HTML content to modify",
        min_length=1,
    )
    user_request: str = Field(
        ...,
        description="Modification request in natural language (Korean supported)",
        min_length=1,
    )
    page_id: str = Field(
        ...,
        description="Unique identifier for the page",
    )
    page_order: int = Field(
        ...,
        ge=0,
        description="Page order number for multi-page documents",
    )
    preserve_structure: Optional[bool] = Field(
        default=True,
        description="Whether to preserve the original HTML structure",
    )
    style_preference: Optional[Literal["inline", "internal"]] = Field(
        default=None,
        description="Override for CSS styling approach",
    )
    additional_context: Optional[str] = Field(
        default=None,
        description="Additional context or constraints for modification",
    )
    config: Optional[HtmlModifierConfigOptions] = Field(
        default=None,
        description="LLM configuration options",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "html_content": "<div><h1>주간 보고서</h1><p>내용</p></div>",
                    "user_request": "헤더 배경색을 파란색(#3498db)으로 변경해주세요",
                    "page_id": "weekly_report",
                    "page_order": 1,
                    "config": {
                        "model": "google/gemini-2.0-flash",
                        "temperature": 0.3,
                    },
                }
            ]
        }
    }


class HtmlModifierResponse(BaseModel):
    """Response body for HTML page modification."""

    modified_html: str = Field(
        ...,
        description="Modified HTML content",
    )
    modification_summary: str = Field(
        ...,
        description="Brief summary of changes made (in Korean)",
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
                    "modified_html": '<div><h1 style="background-color: #3498db; color: white;">주간 보고서</h1><p>내용</p></div>',
                    "modification_summary": "헤더 배경색을 파란색(#3498db)으로 변경하고 텍스트를 흰색으로 설정했습니다.",
                    "status": "completed",
                    "execution_time_ms": 1234,
                }
            ]
        }
    }
