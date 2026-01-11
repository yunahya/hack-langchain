# Notebooks - Claude Instructions

## Project Context

This directory contains Jupyter notebooks for **LangGraph Business Workflows**:
1. **Report Generator**: Automated business report generation with parallel page creation
2. **HTML Page Modifier**: AI-powered single page HTML modification
3. **Report Design Workflow**: AI-powered Sustainability Report HTML design (migrated from Dify)

---

## Notebooks

### `report_generator.ipynb`
LangGraph-based business report generation workflow featuring:
- **TOC Generation**: Dynamic table of contents based on report type/purpose
- **Parallel Page Generation**: Uses `Send` API for concurrent content creation
- **A4 Optimization**: 800-1200 characters per page (Korean)
- **Multi-LLM Support**: Gemini (default) and Azure OpenAI

### `report_designer.ipynb`
LangGraph-based AI report design workflow (migrated from Dify).

**Note**: Core workflow logic is available in the `report_designer` package at project root.
See `report_designer/` for the reusable module implementation.

#### Quick Usage
```python
from report_designer import run_report_design_workflow

result = await run_report_design_workflow(
    api_url="https://gen-api.i-esg.io",
    token="your_token",
    report_id="your_report_id"
)
```

### `html_page_modifier.ipynb`
Interactive notebook for LangGraph-based HTML page modification:
- **Single Page Focus**: One HTML page in, one modified HTML page out
- **AI-Powered Modification**: Modifies HTML based on user request
- **Design Changes**: Layout, colors, spacing, structure modifications
- **Multi-LLM Support**: Gemini (default) and Azure OpenAI
- **Package Equivalent**: See `html_page_modifier_langgraph/` for production package

#### Architecture
```
START -> modify_page_html -> END
```

#### State Schema
```python
PageModificationInput:
  - html_content: str     # Current HTML to modify
  - user_request: str     # Natural language request
  - page_id: str          # Page identifier
  - page_order: int       # Page order number

PageModificationState:
  - input: PageModificationInput
  - modified_html: str            # Output HTML
  - modification_summary: str     # Brief change description
  - status: str                   # 'pending' | 'completed'
```

#### Quick Usage (Notebook)
```python
result = modify_html(
    html_content="<div>...</div>",
    user_request="헤더 색상을 파란색으로 변경해주세요",
    page_id="summary",
    page_order=1
)
# result["modified_html"] contains the updated HTML
```

#### Output Files
Test results are saved to `test-files/` directory:
- `{page_id}_original.html` - Original HTML
- `{page_id}_modified.html` - Modified HTML

---

## report_generator.ipynb Architecture

```
START -> generate_toc -> [fan_out] -> generate_page_content (x N) -> combine_report -> END
```

### State Schema
```python
ReportState:
  - input: ReportInput       # User inputs (required + optional)
  - toc: list[dict]          # Generated sections
  - pages: Annotated[list, operator.add]  # Reducer for parallel results
  - final_report: str        # Combined markdown output
  - status: str              # Workflow status
```

### Required Input Fields
- `report_type`: 주간업무보고, 기획안, 프로젝트 제안서, etc.
- `purpose`: 승인 요청, 현황 공유, 의사결정 요청, etc.
- `audience`: 직속 상사, 임원, 타부서, etc.
- `topic`: Report title/subject
- `key_message`: Core message or keywords
- `company_info`: Company/team name and industry

### Optional Input Fields
- `tone`: Writing style (격식체/반말, 간결함/상세함)
- `page_count`: Target pages (default: 3)
- `emphasis`: Points to emphasize
- `include_visuals`: Include charts/tables
- `additional_data`: Reference data

## Environment Variables

```env
# Google Gemini (Primary)
GOOGLE_API_KEY=your_key
GEMINI_MODEL=gemini-2.0-flash

# Azure OpenAI (Alternative)
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
OPENAI_API_VERSION=2024-08-01-preview
```

## Development Guidelines

### When Modifying the Notebook
1. **Preserve Cell Structure**: Each cell has a specific purpose (setup, schema, nodes, graph)
2. **Test with Sample Input**: Use the existing `sample_input` in Cell 8
3. **Maintain Type Hints**: All functions use `TypedDict` for state management
4. **Handle LLM Response Variations**: Use `extract_text_content()` for response parsing

### LangGraph Patterns Used
- **`operator.add` Reducer**: For aggregating parallel page results
- **`Send` API**: Fan-out pattern for parallel page generation
- **Conditional Edges**: Dynamic routing based on TOC generation
- **Automatic Fan-in**: All parallel branches merge at `combine_report`

### Common Issues
- **JSON Parsing Failures**: TOC generation may fail; fallback TOC is provided
- **LLM Response Format**: Gemini returns list content; use `extract_text_content()`
- **Missing API Keys**: Check `.env` file configuration

## Running Notebooks

```bash
# With uv (recommended)
uv run jupyter notebook notebooks/report_generator.ipynb
uv run jupyter notebook notebooks/report_designer.ipynb
uv run jupyter notebook notebooks/html_page_modifier.ipynb

# With pip
jupyter notebook notebooks/report_generator.ipynb
```

## Quick Usage

```python
report = generate_report(
    report_type="주간업무보고",
    purpose="현황 공유",
    audience="직속 상사",
    topic="마케팅팀 주간업무보고",
    key_message="캠페인 성과 공유",
    company_info="ABC 주식회사 마케팅팀"
)
```
