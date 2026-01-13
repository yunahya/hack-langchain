"""
Workflow execution service for LangGraph graphs.

Provides helper functions for invoking workflows with timing.
"""

import time
from typing import Any, Dict, Optional, Tuple

from langchain_core.runnables import RunnableConfig


def invoke_workflow_sync(
    graph: Any,
    initial_state: Dict[str, Any],
    configurable: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    Invoke a LangGraph workflow synchronously.

    Args:
        graph: Compiled LangGraph StateGraph.
        initial_state: Initial state dictionary.
        configurable: Optional configuration dict for RunnableConfig.

    Returns:
        Tuple of (result_state, execution_time_ms).
    """
    start_time = time.time()

    config: RunnableConfig = {}
    if configurable:
        config["configurable"] = configurable

    result = graph.invoke(initial_state, config=config)

    execution_time_ms = int((time.time() - start_time) * 1000)
    return result, execution_time_ms


async def invoke_workflow_async(
    graph: Any,
    initial_state: Dict[str, Any],
    configurable: Optional[Dict[str, Any]] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    Invoke a LangGraph workflow asynchronously.

    Args:
        graph: Compiled LangGraph StateGraph.
        initial_state: Initial state dictionary.
        configurable: Optional configuration dict for RunnableConfig.

    Returns:
        Tuple of (result_state, execution_time_ms).
    """
    start_time = time.time()

    config: RunnableConfig = {}
    if configurable:
        config["configurable"] = configurable

    result = await graph.ainvoke(initial_state, config=config)

    execution_time_ms = int((time.time() - start_time) * 1000)
    return result, execution_time_ms
