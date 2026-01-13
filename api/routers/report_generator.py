"""
Router for Report Generator workflow API endpoint.

Provides POST /report-generator endpoint for AI-powered report generation.
"""

import logging

from fastapi import APIRouter, HTTPException

from api.models.report_generator import (
    ReportGeneratorRequest,
    ReportGeneratorResponse,
    TocItemResponse,
    PageContentResponse,
)
from api.services.workflow_runner import invoke_workflow_async
from report_draft_generator import graph
from report_draft_generator.state import (
    DraftGeneratorState,
    ReportInput,
    DEFAULT_DESIGN_REQUIREMENT,
)


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/report-generator",
    response_model=ReportGeneratorResponse,
    summary="Generate business report",
    description="AI-powered Korean business report generation with parallel page creation",
    responses={
        200: {"description": "Successfully generated report"},
        500: {"description": "Workflow execution error"},
    },
)
async def generate_report(request: ReportGeneratorRequest) -> ReportGeneratorResponse:
    """
    Generate a business report based on user specifications.

    Creates a structured report with TOC and multiple pages,
    generated in parallel for faster execution.
    """
    # Build user input from request
    user_input: ReportInput = {
        "report_type": request.report_type,
        "purpose": request.purpose,
        "audience": request.audience,
        "topic": request.topic,
        "key_message": request.key_message,
        "company_name": request.company_name,
    }

    # Add optional fields if provided
    if request.company_info:
        user_input["company_info"] = request.company_info
    if request.tone:
        user_input["tone"] = request.tone
    if request.page_count:
        user_input["page_count"] = request.page_count
    if request.emphasis:
        user_input["emphasis"] = request.emphasis
    if request.include_visuals is not None:
        user_input["include_visuals"] = request.include_visuals
    if request.additional_data:
        user_input["additional_data"] = request.additional_data

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

    # Build configurable options
    configurable = None
    if request.config:
        configurable = {
            "model": request.config.model,
            "toc_temperature": request.config.toc_temperature,
            "content_temperature": request.config.content_temperature,
        }

    try:
        logger.info(f"Generating report: {request.topic}")

        result, execution_time_ms = await invoke_workflow_async(
            graph=graph,
            initial_state=initial_state,
            configurable=configurable,
        )

        logger.info(
            f"Report generation completed: {request.topic} "
            f"with {len(result['sections'])} sections in {execution_time_ms}ms"
        )

        # Convert TOC items to response format
        toc_response = [
            TocItemResponse(
                page_id=item["page_id"],
                title=item["title"],
                description=item["description"],
                order=item["order"],
            )
            for item in result["toc"]
        ]

        # Convert sections to pages response format (backward compatibility)
        pages_response = [
            PageContentResponse(
                page_id=section["page_id"],
                title=section["title"],
                content=section["content"],
                order=section["order"],
            )
            for section in sorted(result["sections"], key=lambda x: x["order"])
        ]

        # Build final_report from final_html or combine section contents
        final_report = result.get("final_html") or "\n\n".join(
            f"## {section['title']}\n\n{section['content']}"
            for section in sorted(result["sections"], key=lambda x: x["order"])
        )

        return ReportGeneratorResponse(
            final_report=final_report,
            toc=toc_response,
            pages=pages_response,
            status=result["status"],
            execution_time_ms=execution_time_ms,
        )

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {str(e)}",
        )
