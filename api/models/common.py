"""Common Pydantic models shared across endpoints."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkflowStatus(str, Enum):
    """Workflow execution status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    code: str = Field(..., description="Error code for client handling")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "Workflow execution failed",
                    "detail": "LLM API rate limit exceeded",
                    "code": "WORKFLOW_ERROR",
                }
            ]
        }
    }
