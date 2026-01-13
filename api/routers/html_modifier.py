"""
Router for HTML Page Modifier workflow API endpoint.

Provides POST /html-modifier endpoint for AI-powered HTML modification.
"""

import logging

from fastapi import APIRouter, HTTPException

from api.models.html_modifier import HtmlModifierRequest, HtmlModifierResponse
from api.services.workflow_runner import invoke_workflow_sync
from html_page_modifier_langgraph import graph
from html_page_modifier_langgraph.state import (
    PageModificationState,
    PageModificationInput,
)


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/html-modifier",
    response_model=HtmlModifierResponse,
    summary="Modify HTML page",
    description="AI-powered HTML page modification based on natural language requests",
    responses={
        200: {"description": "Successfully modified HTML"},
        500: {"description": "Workflow execution error"},
    },
)
async def modify_html(request: HtmlModifierRequest) -> HtmlModifierResponse:
    """
    Modify HTML content based on user request.

    Takes HTML content and a natural language modification request,
    returns the modified HTML with a summary of changes.
    """
    # Build user input from request
    user_input: PageModificationInput = {
        "html_content": request.html_content,
        "user_request": request.user_request,
        "page_id": request.page_id,
        "page_order": request.page_order,
    }

    # Add optional fields if provided
    if request.preserve_structure is not None:
        user_input["preserve_structure"] = request.preserve_structure
    if request.style_preference:
        user_input["style_preference"] = request.style_preference
    if request.additional_context:
        user_input["additional_context"] = request.additional_context

    # Build initial state
    initial_state: PageModificationState = {
        "input": user_input,
        "modified_html": "",
        "modification_summary": "",
        "status": "pending",
    }

    # Build configurable options
    configurable = None
    if request.config:
        configurable = {
            "model": request.config.model,
            "temperature": request.config.temperature,
            "style_preference": request.config.style_preference,
        }

    try:
        logger.info(f"Processing HTML modification for page: {request.page_id}")

        result, execution_time_ms = invoke_workflow_sync(
            graph=graph,
            initial_state=initial_state,
            configurable=configurable,
        )

        logger.info(
            f"HTML modification completed for page: {request.page_id} "
            f"in {execution_time_ms}ms"
        )

        return HtmlModifierResponse(
            modified_html=result["modified_html"],
            modification_summary=result["modification_summary"],
            status=result["status"],
            execution_time_ms=execution_time_ms,
        )

    except Exception as e:
        logger.error(f"HTML modification failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {str(e)}",
        )
