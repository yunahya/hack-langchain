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
from api.services.workflow_runner import invoke_workflow_sync
from report_generator_langgraph import graph
from report_generator_langgraph.state import ReportState, ReportInput


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
        "company_info": request.company_info,
    }

    # Add optional fields if provided
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
    initial_state: ReportState = {
        "input": user_input,
        "toc": [],
        "pages": [],
        "final_report": "",
        "status": "pending",
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

        result, execution_time_ms = invoke_workflow_sync(
            graph=graph,
            initial_state=initial_state,
            configurable=configurable,
        )

        logger.info(
            f"Report generation completed: {request.topic} "
            f"with {len(result['pages'])} pages in {execution_time_ms}ms"
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

        # Convert pages to response format
        pages_response = [
            PageContentResponse(
                page_id=page["page_id"],
                title=page["title"],
                content=page["content"],
                order=page["order"],
            )
            for page in result["pages"]
        ]

        return ReportGeneratorResponse(
            final_report=result["final_report"],
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
