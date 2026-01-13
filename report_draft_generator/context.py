"""
Configuration context for the Report Draft Generator workflow.

This module defines the Configuration class used by LangGraph's
RunnableConfig to customize workflow behavior at runtime.

Merges settings from both report_generator and report_designer.
"""

from dataclasses import dataclass, field
from typing import Annotated

from langchain_core.runnables import RunnableConfig


@dataclass(kw_only=True)
class Configuration:
    """
    Runtime configuration for the Report Draft Generator workflow.

    This configuration is passed via RunnableConfig and can be
    customized per invocation without modifying the graph structure.

    Attributes:
        model: LLM model identifier in format "provider/model_name".
               Supported providers: google, azure_openai, openai.
               Default: "google/gemini-2.0-flash"
        toc_temperature: Temperature for TOC generation (structured output).
                         Lower values produce more deterministic results.
                         Default: 0.5
        content_temperature: Temperature for page content generation.
                             Higher values produce more creative content.
                             Default: 0.7
        design_temperature: Temperature for HTML design generation.
                            Higher values produce more creative designs.
                            Default: 1.0
        fallback_model: Fallback LLM model for 3-tier fallback chain.
                        Default: "google/gemini-1.5-pro"
        max_retries: Maximum retry count per model in fallback chain.
                     Default: 3

    Example:
        >>> config = {"configurable": {
        ...     "model": "google/gemini-2.0-flash",
        ...     "toc_temperature": 0.3,
        ...     "content_temperature": 0.8,
        ...     "design_temperature": 1.0,
        ... }}
        >>> result = graph.invoke(state, config=config)
    """

    model: str = field(
        default="google/gemini-2.0-flash",
        metadata={
            "description": (
                "LLM model identifier in format 'provider/model_name'. "
                "Supported providers: google, azure_openai, openai."
            ),
            "examples": [
                "google/gemini-2.0-flash",
                "google/gemini-1.5-pro",
                "azure_openai/gpt-4o",
            ],
        },
    )

    toc_temperature: float = field(
        default=0.5,
        metadata={
            "description": (
                "Temperature for TOC generation. "
                "Lower values (0.3-0.5) produce more structured output."
            ),
            "minimum": 0.0,
            "maximum": 1.0,
        },
    )

    content_temperature: float = field(
        default=0.7,
        metadata={
            "description": (
                "Temperature for page content generation. "
                "Higher values (0.6-0.8) produce more creative content."
            ),
            "minimum": 0.0,
            "maximum": 1.0,
        },
    )

    design_temperature: float = field(
        default=1.0,
        metadata={
            "description": (
                "Temperature for HTML design generation. "
                "Higher values (0.8-1.0) produce more creative designs."
            ),
            "minimum": 0.0,
            "maximum": 2.0,
        },
    )

    fallback_model: str = field(
        default="google/gemini-1.5-pro",
        metadata={
            "description": (
                "Fallback LLM model for 3-tier fallback chain. "
                "Used when primary model fails."
            ),
        },
    )

    max_retries: int = field(
        default=3,
        metadata={
            "description": "Maximum retry count per model in fallback chain.",
            "minimum": 1,
            "maximum": 5,
        },
    )

    @classmethod
    def from_runnable_config(
        cls,
        config: RunnableConfig | None = None,
    ) -> "Configuration":
        """
        Extract Configuration from RunnableConfig.

        Args:
            config: LangGraph RunnableConfig with 'configurable' key.

        Returns:
            Configuration instance with values from config or defaults.

        Example:
            >>> config = {"configurable": {"model": "azure_openai/gpt-4o"}}
            >>> cfg = Configuration.from_runnable_config(config)
            >>> cfg.model
            'azure_openai/gpt-4o'
        """
        if config is None:
            return cls()

        configurable = config.get("configurable", {})

        return cls(
            model=configurable.get("model", cls.model),
            toc_temperature=configurable.get("toc_temperature", cls.toc_temperature),
            content_temperature=configurable.get(
                "content_temperature", cls.content_temperature
            ),
            design_temperature=configurable.get(
                "design_temperature", cls.design_temperature
            ),
            fallback_model=configurable.get("fallback_model", cls.fallback_model),
            max_retries=configurable.get("max_retries", cls.max_retries),
        )


# Type alias for annotated configuration
ConfigurableFields = Annotated[Configuration, "Configuration for report draft generation"]
