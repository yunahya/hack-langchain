"""
Utility functions for the Report Draft Generator workflow.

This module provides helper functions for:
- LLM response content extraction (handles various response formats)
- Chat model initialization with support for multiple providers
- JSON parsing from LLM responses
- HTML body block extraction for multi-page sections
- 3-tier LLM fallback chain
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from report_draft_generator.state import DesignedPage, ReportSection


def extract_text_content(response_content: Any) -> str:
    """
    Extract text content from LLM response.

    Some LLMs (e.g., Gemini) return content as a list of parts
    rather than a plain string. This function handles both cases.

    Args:
        response_content: The content attribute from an LLM response.
                         Can be str, list, or other types.

    Returns:
        Extracted text content as a string.

    Example:
        >>> # String content (most LLMs)
        >>> extract_text_content("Hello world")
        'Hello world'
        >>> # List content (Gemini-style)
        >>> extract_text_content([{"text": "Hello"}, {"text": " world"}])
        'Hello world'
    """
    if isinstance(response_content, str):
        return response_content

    if isinstance(response_content, list):
        text_parts: list[str] = []
        for item in response_content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                text_parts.append(item["text"])
            elif hasattr(item, "text"):
                text_parts.append(item.text)
        return "".join(text_parts)

    return str(response_content)


def load_chat_model(
    model: str,
    temperature: float = 0.7,
) -> BaseChatModel:
    """
    Load a chat model based on provider and model name.

    This factory function supports multiple providers through a unified
    interface. The model string format is "provider/model_name" or
    "provider:model_name".

    Supported providers:
    - google (Google Gemini): requires GOOGLE_API_KEY
    - azure_openai (Azure OpenAI): requires AZURE_OPENAI_* env vars
    - openai (OpenAI): requires OPENAI_API_KEY

    Args:
        model: Model identifier in format "provider/model_name" or
               "provider:model_name".
               Examples: "google/gemini-2.0-flash", "azure_openai/gpt-4o"
        temperature: Generation temperature (0.0-2.0).

    Returns:
        Initialized chat model instance.

    Raises:
        ValueError: If the model string format is invalid or provider
                    is not supported.

    Example:
        >>> llm = load_chat_model("google/gemini-2.0-flash", temperature=0.5)
        >>> response = llm.invoke("Hello!")
    """
    # Parse model string - support both "/" and ":" as separators
    if "/" in model:
        provider, model_name = model.split("/", 1)
    elif ":" in model:
        provider, model_name = model.split(":", 1)
    else:
        raise ValueError(
            f"Invalid model format: '{model}'. "
            "Expected 'provider/model_name' or 'provider:model_name'."
        )

    provider = provider.lower()

    # Normalize provider aliases
    provider_aliases = {
        "google": "google",
        "google_genai": "google",
        "gemini": "google",
        "azure_openai": "azure",
        "azure": "azure",
        "openai": "openai",
    }

    if provider not in provider_aliases:
        raise ValueError(
            f"Unsupported provider: '{provider}'. "
            f"Supported: {list(provider_aliases.keys())}"
        )

    normalized_provider = provider_aliases[provider]

    # Create provider-specific model instance
    if normalized_provider == "google":
        return ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=temperature,
        )

    elif normalized_provider == "azure":
        return AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("OPENAI_API_VERSION", "2024-08-01-preview"),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", model_name),
            temperature=temperature,
        )

    elif normalized_provider == "openai":
        return ChatOpenAI(
            model=model_name,
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=temperature,
        )

    # This should never be reached due to the check above
    raise ValueError(f"Unsupported provider: '{provider}'")


def parse_json_from_response(content: str) -> str:
    """
    Extract JSON content from an LLM response that may contain markdown.

    LLMs sometimes wrap JSON in markdown code blocks. This function
    removes the code block markers to extract the raw JSON.

    Args:
        content: Raw response content that may contain markdown.

    Returns:
        Clean JSON string without markdown formatting.

    Example:
        >>> parse_json_from_response('```json\\n[{"a": 1}]\\n```')
        '[{"a": 1}]'
        >>> parse_json_from_response('[{"a": 1}]')
        '[{"a": 1}]'
    """
    content = content.strip()

    # Remove markdown code block markers
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        # Handle generic code blocks
        parts = content.split("```")
        if len(parts) >= 2:
            content = parts[1]

    return content.strip()


@dataclass
class LLMConfig:
    """LLM configuration for fallback chain."""

    name: str  # Model name
    provider: str  # Provider (e.g., "google")
    temperature: float = 1.0  # Generation temperature
    max_retries: int = 3  # Max retry count


# Default LLM configs for 3-tier fallback chain
DEFAULT_LLM_CONFIGS = [
    LLMConfig("gemini-2.0-flash", "google", 1.0),  # Primary
    LLMConfig("gemini-2.0-flash", "google", 1.0),  # Retry
    LLMConfig("gemini-1.5-pro", "google", 1.0),  # Fallback
]


def create_llm(
    config: LLMConfig,
    api_key: str | None = None,
) -> BaseChatModel:
    """
    Factory function to create an LLM from configuration.

    Args:
        config: LLM configuration with name, provider, temperature.
        api_key: Optional API key. If not provided, uses GOOGLE_API_KEY env var.

    Returns:
        Initialized chat model instance.
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_API_KEY")

    return ChatGoogleGenerativeAI(
        model=config.name,
        temperature=config.temperature,
        google_api_key=api_key,
    )


async def call_llm_with_fallback(
    system_prompt: str,
    user_prompt: str,
    configs: list[LLMConfig] | None = None,
) -> tuple[str, str]:
    """
    Call LLM with 3-tier fallback chain.

    Args:
        system_prompt: System prompt for the LLM.
        user_prompt: User prompt for the LLM.
        configs: List of LLM configs for fallback chain.
                 Default: DEFAULT_LLM_CONFIGS.

    Returns:
        tuple[str, str]: (response text, model name used)

    Raises:
        RuntimeError: If all LLM attempts fail.
    """
    if configs is None:
        configs = DEFAULT_LLM_CONFIGS

    for i, config in enumerate(configs):
        try:
            llm = create_llm(config)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = await llm.ainvoke(messages)
            text = extract_text_content(response.content)

            # Check for empty response (trigger fallback to next model)
            if not text.strip() and i < len(configs) - 1:
                print(f"Empty response from {config.name}, trying next model...")
                continue

            return text, config.name

        except Exception as e:
            print(f"LLM {config.name} failed: {e}")
            if i == len(configs) - 1:
                raise RuntimeError(f"All LLM attempts failed. Last error: {e}")

    raise RuntimeError("All LLM attempts failed")


def extract_body_blocks(
    html_content: str,
    section: ReportSection,
    outline_id: str,
    model_used: Optional[str] = None,
) -> list[DesignedPage]:
    """
    Extract all <body>...</body> blocks from LLM output.

    Handles multiple body blocks for multi-page sections (content > 1200 chars).
    Each body block becomes a separate page in the final report.

    Args:
        html_content: Raw HTML output from LLM.
        section: Section data for metadata.
        outline_id: Outline identifier.
        model_used: LLM model name that generated this content.

    Returns:
        List of DesignedPage dicts, one per body block.
    """
    # Remove __PAGE_BREAK__ markers if present
    html_content = html_content.replace("__PAGE_BREAK__", "")

    # Find all body blocks
    body_pattern = r"<body[^>]*>.*?</body>"
    matches = re.findall(body_pattern, html_content, re.DOTALL | re.IGNORECASE)

    pages: list[DesignedPage] = []

    if matches:
        for idx, body_html in enumerate(matches):
            pages.append({
                "html_content": body_html,
                "order": section.get("order", 0),
                "section_title": section.get("section_title", ""),
                "section_number": section.get("section_number"),
                "outline_id": outline_id,
                "page_index": idx,
                "model_used": model_used,
            })
    else:
        # If no body tags found, use entire content
        pages.append({
            "html_content": html_content,
            "order": section.get("order", 0),
            "section_title": section.get("section_title", ""),
            "section_number": section.get("section_number"),
            "outline_id": outline_id,
            "page_index": 0,
            "model_used": model_used,
        })

    return pages
