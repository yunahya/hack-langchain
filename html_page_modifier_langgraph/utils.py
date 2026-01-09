"""
Utility functions for the HTML Page Modifier workflow.

This module provides helper functions for:
- LLM response content extraction (handles various response formats)
- HTML content extraction from markdown code blocks
- Chat model initialization with support for multiple providers
"""

from __future__ import annotations

import os
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI, ChatOpenAI


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
        >>> extract_text_content("Hello world")
        'Hello world'
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


def extract_html_content(response_content: Any) -> str:
    """
    Extract HTML content from LLM response.

    Handles markdown code blocks (```html ... ```) that LLMs often
    wrap HTML content in. Also handles plain HTML responses.

    Args:
        response_content: The content attribute from an LLM response.

    Returns:
        Clean HTML content without markdown formatting.

    Example:
        >>> extract_html_content('```html\\n<div>Hello</div>\\n```')
        '<div>Hello</div>'
        >>> extract_html_content('<div>Hello</div>')
        '<div>Hello</div>'
    """
    content = extract_text_content(response_content)
    content = content.strip()

    # Remove markdown code blocks
    if "```html" in content:
        content = content.split("```html")[1].split("```")[0]
    elif "```" in content:
        parts = content.split("```")
        if len(parts) >= 2:
            content = parts[1]
            # Remove language identifier if present at start
            lines = content.split("\n")
            if lines and lines[0].strip().lower() in ("html", "htm", ""):
                content = "\n".join(lines[1:])

    return content.strip()


def load_chat_model(
    model: str,
    temperature: float = 0.3,
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
        temperature: Generation temperature (0.0-1.0).
                     Default is 0.3 for more deterministic HTML output.

    Returns:
        Initialized chat model instance.

    Raises:
        ValueError: If the model string format is invalid or provider
                    is not supported.

    Example:
        >>> llm = load_chat_model("google/gemini-2.0-flash", temperature=0.3)
        >>> response = llm.invoke("Modify this HTML...")
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
