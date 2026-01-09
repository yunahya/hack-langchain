"""
State definitions for the HTML Page Modifier workflow.

This module defines TypedDict schemas for:
- PageModificationInput: User input structure for HTML modification
- PageModificationState: Workflow state schema
"""

from typing_extensions import TypedDict, NotRequired


class PageModificationInput(TypedDict, total=False):
    """
    User input schema for HTML page modification.

    Required fields define the basic modification request.
    Optional fields enhance context and behavior.
    """

    # Required fields
    html_content: str
    """Current HTML content to be modified."""

    user_request: str
    """User's modification request in natural language."""

    page_id: str
    """Unique identifier for the page (e.g., 'summary', 'header')."""

    page_order: int
    """Page order number for multi-page documents."""

    # Optional fields
    preserve_structure: NotRequired[bool]
    """Whether to preserve the original HTML structure as much as possible."""

    style_preference: NotRequired[str]
    """Preferred styling approach: 'inline', 'internal', or 'external'."""

    additional_context: NotRequired[str]
    """Additional context or constraints for the modification."""


class PageModificationState(TypedDict):
    """
    Workflow state schema for HTML page modification.

    Simple linear workflow without parallel processing.
    """

    # Input
    input: PageModificationInput
    """User input for HTML modification."""

    # Output
    modified_html: str
    """Modified HTML content."""

    modification_summary: str
    """Brief summary of changes made."""

    # Workflow metadata
    status: str
    """Current workflow status: 'pending', 'processing', 'completed', 'error'."""
