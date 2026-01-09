"""
Configuration context for the HTML Page Modifier workflow.

This module defines the Configuration class used by LangGraph's
RunnableConfig to customize workflow behavior at runtime.
"""

from dataclasses import dataclass, field
from typing import Annotated, Literal

from langchain_core.runnables import RunnableConfig


@dataclass(kw_only=True)
class Configuration:
    """
    Runtime configuration for the HTML Page Modifier workflow.

    This configuration is passed via RunnableConfig and can be
    customized per invocation without modifying the graph structure.

    Attributes:
        model: LLM model identifier in format "provider/model_name".
               Supported providers: google, azure_openai.
               Default: "google/gemini-2.0-flash"
        temperature: Temperature for HTML modification.
                     Lower values produce more deterministic results.
                     Default: 0.3
        style_preference: Default styling approach for modifications.
                          Options: 'inline', 'internal'.
                          Default: 'inline'

    Example:
        >>> config = {"configurable": {
        ...     "model": "azure_openai/gpt-4o",
        ...     "temperature": 0.2,
        ...     "style_preference": "internal",
        ... }}
        >>> result = graph.invoke(state, config=config)
    """

    model: str = field(
        default="google/gemini-2.0-flash",
        metadata={
            "description": (
                "LLM model identifier in format 'provider/model_name'. "
                "Supported providers: google, azure_openai."
            ),
            "examples": [
                "google/gemini-2.0-flash",
                "google/gemini-1.5-pro",
                "azure_openai/gpt-4o",
            ],
        },
    )

    temperature: float = field(
        default=0.3,
        metadata={
            "description": (
                "Temperature for HTML modification. "
                "Lower values (0.2-0.4) produce more deterministic HTML output."
            ),
            "minimum": 0.0,
            "maximum": 1.0,
        },
    )

    style_preference: Literal["inline", "internal"] = field(
        default="inline",
        metadata={
            "description": (
                "Default styling approach: 'inline' for style attributes, "
                "'internal' for <style> tags."
            ),
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
            temperature=configurable.get("temperature", cls.temperature),
            style_preference=configurable.get("style_preference", cls.style_preference),
        )


# Type alias for annotated configuration
ConfigurableFields = Annotated[Configuration, "Configuration for HTML modification"]
