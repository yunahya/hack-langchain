# HTML Page Modifier - LangGraph Package

## Overview

AI-powered HTML page modification workflow using LangGraph. Modifies single HTML pages based on natural language requests.

## Architecture

```
START -> modify_page_html -> END
```

## Module Structure

| File | Purpose |
|------|---------|
| `state.py` | TypedDict schemas (PageModificationInput, PageModificationState) |
| `graph.py` | LangGraph workflow definition and node functions |
| `prompts.py` | Prompt templates for modification and summary generation |
| `utils.py` | Helper functions (LLM loading, content extraction) |
| `context.py` | Runtime Configuration dataclass |
| `__init__.py` | Package exports (graph, state types, Configuration) |

## State Schema

```python
PageModificationInput:
  html_content: str       # Current HTML to modify
  user_request: str       # Natural language modification request
  page_id: str            # Page identifier
  page_order: int         # Page order number
  # Optional
  preserve_structure: bool
  style_preference: str   # 'inline' | 'internal'
  additional_context: str

PageModificationState:
  input: PageModificationInput
  modified_html: str
  modification_summary: str
  status: str  # 'pending' | 'processing' | 'completed' | 'error'
```

## Quick Usage

```python
from html_page_modifier_langgraph import graph, PageModificationState, PageModificationInput

user_input: PageModificationInput = {
    "html_content": "<div><h1>Hello</h1></div>",
    "user_request": "Change header color to blue",
    "page_id": "main",
    "page_order": 1,
}

initial_state: PageModificationState = {
    "input": user_input,
    "modified_html": "",
    "modification_summary": "",
    "status": "pending",
}

result = graph.invoke(initial_state)
print(result["modified_html"])
```

## Runtime Configuration

```python
config = {"configurable": {
    "model": "google/gemini-2.0-flash",  # or "azure_openai/gpt-4o"
    "temperature": 0.3,
    "style_preference": "inline",  # or "internal"
}}
result = graph.invoke(initial_state, config=config)
```

## Supported LLM Providers

| Provider | Model Format | Required Env Vars |
|----------|--------------|-------------------|
| Google Gemini | `google/gemini-2.0-flash` | `GOOGLE_API_KEY` |
| Azure OpenAI | `azure_openai/gpt-4o` | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` |
| OpenAI | `openai/gpt-4o` | `OPENAI_API_KEY` |

## Key Functions

### `load_chat_model(model, temperature)` in utils.py
Factory function for LLM initialization. Supports `provider/model_name` format.

### `extract_html_content(response_content)` in utils.py
Extracts clean HTML from LLM responses, handling markdown code blocks.

### `build_modification_prompt(user_input, style_preference)` in prompts.py
Builds the HTML modification prompt with style preferences.

## Development Guidelines

1. **State immutability**: Node functions return dicts, not mutated state
2. **Error handling**: Always return fallback values on error (see `DEFAULT_MODIFIED_HTML`)
3. **Prompt engineering**: Modify prompts in `prompts.py`, not in graph.py
4. **Configuration**: Add new config fields to `Configuration` dataclass in context.py

## Running Standalone

```bash
# Run with sample HTML
python -m html_page_modifier_langgraph.graph
```

## LangGraph Server Integration

This package follows LangGraph template conventions for deployment with `langgraph dev`.
