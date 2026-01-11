# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LangGraph-based business report automation workflows with three main components:
1. **Report Designer** (`report_designer/`) - Business report HTML design workflow package
2. **Jupyter Notebooks** (`notebooks/`) - Interactive workflows for report generation and HTML modification
3. **ReAct Agent Template** (`langgraph-template/`) - A reference implementation of a tool-calling agent

## Commands

### Setup
```bash
# Install dependencies (uv recommended)
uv sync --all-extras

# Or with pip
pip install -r requirements.txt
```

### Running Notebooks
```bash
uv run jupyter notebook notebooks/report_generator.ipynb
uv run jupyter notebook notebooks/report_designer.ipynb
uv run jupyter notebook notebooks/html_page_modifier.ipynb
```

### Testing
```bash
uv run pytest tests/ -v

# Run single test file
uv run pytest tests/test_report_generator.py -v
uv run pytest tests/test_report_designer.py -v

# Run specific test class
uv run pytest tests/test_report_generator.py::TestTOCGeneration -v
```

## Architecture

### Report Generator Workflow (`notebooks/report_generator.ipynb`)
```
START -> generate_toc -> [fan_out] -> generate_page_content (×N parallel) -> combine_report -> END
```

Key patterns:
- **State**: `TypedDict` with `Annotated[list, operator.add]` reducer for parallel page aggregation
- **Fan-out**: `Send` API distributes work to parallel page generation nodes
- **Fan-in**: Automatic aggregation at `combine_report` node
- **LLM Response Handling**: `extract_text_content()` handles Gemini's list-based response format

### HTML Page Modifier (`notebooks/html_page_modifier.ipynb`)
```
START -> modify_page_html -> END
```
Simple single-node workflow for AI-powered HTML modifications with design constraints.

### Report Designer Package (`report_designer/`)
```
START -> fetch_all_data -> prepare_sections
      -> [fan_out] -> design_section (×N parallel)
      -> combine_results -> publish_report -> END
```
Key patterns:
- **Fan-out/Fan-in**: Parallel section design with `Send` API
- **3-tier LLM Fallback**: Primary → Retry → Fallback model chain
- **Jinja2 Templates**: `prompts/design_prompt.jinja2` for design instructions

### ReAct Agent Template (`langgraph-template/`)
```
__start__ -> call_model <-> tools -> __end__
```
- Uses `@dataclass` state with `add_messages` annotation
- `Runtime[Context]` pattern for configuration injection
- `IsLastStep` managed variable for recursion limit handling
- `route_model_output` conditional edge for tool call detection

## Key Patterns

### State Schema Options
```python
# Notebook pattern (TypedDict + reducer)
class ReportState(TypedDict):
    pages: Annotated[list[PageContent], operator.add]  # Aggregates parallel results

# Template pattern (@dataclass + add_messages)
@dataclass
class State(InputState):
    messages: Annotated[Sequence[AnyMessage], add_messages]
    is_last_step: IsLastStep = field(default=False)
```

### LLM Provider Configuration
Both Gemini and Azure OpenAI are supported. Configure via `.env`:
```env
GOOGLE_API_KEY=your_key
GEMINI_MODEL=gemini-2.0-flash
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
```

### JSON Parsing from LLM Responses
TOC generation expects JSON but LLMs may wrap in markdown code blocks:
```python
if "```json" in content:
    content = content.split("```json")[1].split("```")[0]
```
Fallback TOC provided when parsing fails.

## Testing Strategy

Tests use mocks for LLM calls (no API costs). Key test categories:
- **Schema tests**: Validate TypedDict field structure
- **Reducer tests**: Verify `operator.add` aggregation behavior
- **Workflow integration**: State transitions without actual LLM calls
- **Error handling**: JSON parsing failures, empty TOC cases
