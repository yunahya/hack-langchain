"""
Business Report Design Workflow

LangGraph-based workflow for generating enterprise-grade Internal Business Report HTML designs.

Target Reports: 주간업무보고, 기획안, 프로젝트 제안서, 결과 보고서, 회의록 등
Input Source: report_generator.ipynb에서 생성된 마크다운 콘텐츠

Workflow Architecture:
    START -> fetch_all_data -> prepare_sections
          -> [fan_out] -> design_section (xN parallel)
          -> combine_results -> publish_report -> END

API Endpoints:
    - GET /customization/{report_id} - Design requirements (colors, orientation)
    - GET /document-outlines/{report_id} - Outline with sections
    - GET /reports/{report_id} - Report metadata
    - PATCH /reports/{report_id}/publish-content - Publish designed pages
"""

# Standard library
import os
import re
import json
import asyncio
import operator
from pathlib import Path
from typing import TypedDict, Annotated, Optional

# Third-party
import httpx
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

# LangChain & LangGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from dataclasses import dataclass

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PROMPTS_DIR = Path(__file__).parent / "prompts" if "__file__" in dir() else Path("prompts")


# =============================================================================
# State Schema Definitions
# =============================================================================

class DesignRequirement(TypedDict):
    """Design customization for business reports from /customization endpoint.

    Used by: design_prompt.jinja2 template
    """
    primary_color: str      # e.g., "#1E40AF" - Main brand color
    secondary_color: str    # e.g., "#3B82F6" - Supporting color
    accent_color: str       # e.g., "#10B981" - Highlight/accent color
    pdf_orientation: str    # "portrait" | "landscape"


class Section(TypedDict):
    """A business report section to be designed.

    Fields aligned with design_prompt.jinja2 template requirements:
    - section_key: Special identifiers for layout decisions
    - parent_path: Breadcrumb navigation path
    - title: Section heading
    - content: Markdown/HTML content from report_generator
    """
    order: int                      # Sorting order
    section_title: str              # Display title
    section_number: Optional[str]   # e.g., "1.0", "2.1"
    section_key: str                # "EXECUTIVE_SUMMARY", "DATA_TABLE", etc.
    title: str                      # Main section title for header
    content: str                    # Markdown/HTML content
    parent_path: Optional[str]      # Breadcrumb path (e.g., "금주 업무 현황 > 성과 분석")


class DesignedPage(TypedDict):
    """Output from designing a single business report page."""
    html_content: str
    order: int
    section_title: str
    section_number: Optional[str]
    outline_id: str
    page_index: int              # For multi-page sections (content > 1200 chars)
    model_used: Optional[str]    # Track which LLM generated this


class ReportDesignState(TypedDict):
    """Main workflow state for business report design.

    Uses Annotated with operator.add for parallel aggregation of designed pages.
    """
    # API Inputs
    api_url: str
    token: str
    report_id: str

    # Fetched data from API
    design_requirement: Optional[DesignRequirement]
    outline: Optional[dict]
    report_metadata: Optional[dict]
    language_code: str
    sections: list[Section]

    # Parallel results - MUST use reducer for fan-in
    designed_pages: Annotated[list[DesignedPage], operator.add]

    # Final output
    publish_payload: Optional[str]

    # Metadata
    status: str
    errors: Annotated[list[str], operator.add]


class SectionPayload(TypedDict):
    """Payload sent to each parallel section processor via Send API."""
    section: Section
    design_requirement: DesignRequirement
    language_code: str
    outline_id: str


# =============================================================================
# LLM Configuration with 3-tier Fallback
# =============================================================================

@dataclass
class LLMConfig:
    """LLM configuration for fallback chain."""
    name: str
    provider: str  # "google"
    temperature: float = 1.0
    max_retries: int = 3


# LLM configurations (3-tier fallback for reliability)
LLM_CONFIGS = [
    LLMConfig("gemini-2.0-flash", "google", 1.0),    # Primary
    LLMConfig("gemini-2.0-flash", "google", 1.0),    # Retry
    LLMConfig("gemini-1.5-pro", "google", 1.0),      # Fallback
]


def create_llm(config: LLMConfig) -> ChatGoogleGenerativeAI:
    """Factory function to create LLM based on config."""
    return ChatGoogleGenerativeAI(
        model=config.name,
        temperature=config.temperature,
        google_api_key=GOOGLE_API_KEY,
    )


def extract_text_content(content) -> str:
    """
    Extract text from LLM response content.
    Handles both string and list-based responses (Gemini format).
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, str):
                texts.append(part)
            elif hasattr(part, 'text'):
                texts.append(part.text)
            elif isinstance(part, dict) and 'text' in part:
                texts.append(part['text'])
        return ''.join(texts)
    return str(content)


async def call_llm_with_fallback(
    system_prompt: str,
    user_prompt: str,
    configs: list[LLMConfig] = None
) -> tuple[str, str]:
    """
    Call LLM with 3-tier fallback chain.

    Returns:
        tuple[str, str]: (response_text, model_used)
    """
    if configs is None:
        configs = LLM_CONFIGS

    for i, config in enumerate(configs):
        try:
            llm = create_llm(config)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = await llm.ainvoke(messages)
            text = extract_text_content(response.content)

            # Check for empty response (triggers next in chain)
            if not text.strip() and i < len(configs) - 1:
                print(f"Empty response from {config.name}, trying next...")
                continue

            return text, config.name

        except Exception as e:
            print(f"LLM {config.name} failed: {e}")
            if i == len(configs) - 1:
                raise RuntimeError(f"All LLM attempts failed. Last error: {e}")

    raise RuntimeError("All LLM attempts failed")


# =============================================================================
# Jinja2 Prompt Loader for Business Report Design
# =============================================================================

class PromptManager:
    """Manages Jinja2 prompt templates with caching."""

    def __init__(self, prompts_dir: Path):
        self.env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._prompt_cache = {}

    def get_prompt(self, name: str):
        """Get prompt template with caching."""
        if name not in self._prompt_cache:
            self._prompt_cache[name] = self.env.get_template(name)
        return self._prompt_cache[name]

    def render(self, prompt_name: str, **context) -> str:
        """Render prompt template with given context."""
        prompt = self.get_prompt(prompt_name)
        return prompt.render(**context)


# Initialize prompt manager
prompt_manager = PromptManager(PROMPTS_DIR)


def render_design_prompt(
    section: Section,
    design_requirement: DesignRequirement,
    content_length: int
) -> str:
    """
    Render the business report design prompt template.

    Template variables (from design_prompt.jinja2):
    - section: Section dict with title, content, section_key, parent_path
    - design_requirement: Colors and orientation
    - content_length: Character count for layout decisions

    The template includes:
    - Core rules (absolute constraints, required attributes)
    - Content metrics based on length
    - Design system (colors, typography)
    - Layout patterns for business reports
    - Infographic templates for KPIs, charts, etc.
    """
    return prompt_manager.render(
        "design_prompt.jinja2",
        section=section,
        design_requirement=design_requirement,
        content_length=content_length
    )


# =============================================================================
# HTTP Fetch Nodes (Parallel Data Fetching)
# =============================================================================

async def fetch_all_data(state: ReportDesignState) -> dict:
    """
    Fetch all business report data in parallel.

    Endpoints (unchanged):
    - GET /customization/{report_id} - Design requirements
    - GET /document-outlines/{report_id} - Outline with sections
    - GET /reports/{report_id} - Report metadata
    """
    api_url = state["api_url"]
    token = state["token"]
    report_id = state["report_id"]

    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Parallel fetch
        tasks = [
            client.get(f"{api_url}/customization/{report_id}", headers=headers),
            client.get(f"{api_url}/document-outlines/{report_id}", headers=headers),
            client.get(f"{api_url}/reports/{report_id}", headers=headers),
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

    # Process responses
    errors = []
    design_req = {}
    outline = {}
    report_meta = {}

    endpoint_names = ["customization", "document-outlines", "reports"]

    for i, resp in enumerate(responses):
        if isinstance(resp, Exception):
            errors.append(f"Fetch {endpoint_names[i]} failed: {str(resp)}")
            continue
        if resp.status_code != 200:
            errors.append(f"Fetch {endpoint_names[i]} returned {resp.status_code}")
            continue

        data = resp.json()
        if i == 0:
            design_req = data
        elif i == 1:
            outline = data
        else:
            report_meta = data

    # Extract language_code (default: Korean for business reports)
    language_code = report_meta.get("language_code", "ko")

    return {
        "design_requirement": design_req,
        "outline": outline,
        "report_metadata": report_meta,
        "language_code": language_code,
        "errors": errors,
        "status": "data_fetched"
    }


def prepare_sections(state: ReportDesignState) -> dict:
    """
    Extract business report sections array from outline.

    Sections should contain content from report_generator output.
    """
    outline = state.get("outline", {})
    sections = outline.get("sections", [])

    return {
        "sections": sections,
        "status": "sections_prepared"
    }


# =============================================================================
# Design Section Node (Core Processing)
# =============================================================================

# System prompt for the LLM - Business Report Designer
SYSTEM_PROMPT_TEMPLATE = """당신은 국내 주요 기업의 내부 비즈니스 보고서를 디자인해온 20년 경력의 시니어 문서 디자이너입니다.

당신의 특별한 능력:
- 콘텐츠를 읽고 정보의 본질적 구조를 파악
- 내용의 특성에 가장 적합한 레이아웃을 직관적으로 선택
- 복잡한 정보를 시각적으로 명료하게 재구성
- HTML/CSS만으로 전문적인 인포그래픽과 차트를 구현
- A4 페이지를 전문적이고 풍성하게 채우는 공간 활용의 전문가
- Flexbox/Grid 레이아웃의 달인 - 요소들이 절대 겹치지 않는 안정적 구조 설계
- {language_code} 언어로 주간업무보고, 기획안, 프로젝트 제안서, 결과 보고서, 회의록 등 비즈니스 문서를 디자인합니다.

당신은 Fortune 500대 기업들의 마케팅팀, 경영진, 프로젝트팀 등에서 의사결정을 위한 비즈니스 보고서를 디자인해왔습니다.

주요 비즈니스 보고서 유형:
- 주간업무보고: 핵심 성과 지표(KPI), 채널별 성과, 차주 계획
- 기획안: 배경, 목표, 실행 계획, 기대 효과
- 프로젝트 제안서: 현황 분석, 솔루션, 일정, 예산
- 결과 보고서: 성과 요약, 데이터 분석, 인사이트, 권고사항
- 회의록: 참석자, 논의사항, 결정사항, 액션아이템"""


def extract_body_blocks(
    html_content: str,
    section: Section,
    outline_id: str,
    model_used: Optional[str] = None
) -> list[DesignedPage]:
    """
    Extract all <body>...</body> blocks from LLM output.

    Handles multi-page sections (content > 1200 chars) that return multiple body blocks.
    Each body block becomes a separate page in the final report.
    """
    # Remove __PAGE_BREAK__ markers if any
    html_content = html_content.replace("__PAGE_BREAK__", "")

    # Find all body blocks
    body_pattern = r'<body[^>]*>.*?</body>'
    matches = re.findall(body_pattern, html_content, re.DOTALL | re.IGNORECASE)

    pages = []

    if matches:
        for idx, body_html in enumerate(matches):
            pages.append({
                "html_content": body_html,
                "order": section.get("order", 0),
                "section_title": section.get("section_title", ""),
                "section_number": section.get("section_number"),
                "outline_id": outline_id,
                "page_index": idx,
                "model_used": model_used
            })
    else:
        # No body tags found, use entire content
        pages.append({
            "html_content": html_content,
            "order": section.get("order", 0),
            "section_title": section.get("section_title", ""),
            "section_number": section.get("section_number"),
            "outline_id": outline_id,
            "page_index": 0,
            "model_used": model_used
        })

    return pages


async def design_section(state: SectionPayload) -> dict:
    """
    Design a single business report section with 3-tier LLM fallback.

    This node is called in parallel via Send API.
    Combines: template rendering + LLM call + body extraction.

    Template handles:
    - Content length analysis (short/medium/long/multi-page)
    - Layout pattern selection (KPI dashboard, data analysis, etc.)
    - Multi-page splitting for content > 1200 chars
    """
    section = state["section"]
    design_req = state["design_requirement"]
    language_code = state["language_code"]
    outline_id = state["outline_id"]

    # Calculate content length for layout decisions
    content = section.get("content", "")
    content_length = len(content)

    try:
        # Render design prompt using Jinja2 template
        design_prompt = render_design_prompt(
            section=section,
            design_requirement=design_req,
            content_length=content_length
        )

        # Create system and user prompts
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(language_code=language_code)
        user_prompt = f"{design_prompt}\n\n{language_code} 언어를 사용하여 비즈니스 보고서 디자인을 시작하세요."

        # Call LLM with fallback
        html_content, model_used = await call_llm_with_fallback(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        # Extract <body> blocks (may be multiple for long content)
        pages = extract_body_blocks(
            html_content=html_content,
            section=section,
            outline_id=outline_id,
            model_used=model_used
        )

        return {
            "designed_pages": pages,
            "errors": []
        }

    except Exception as e:
        error_msg = f"Section '{section.get('section_title', 'Unknown')}' failed: {str(e)}"
        return {
            "designed_pages": [],
            "errors": [error_msg]
        }


# =============================================================================
# Combine Results & Publish Nodes
# =============================================================================

def combine_results(state: ReportDesignState) -> dict:
    """
    Flatten, sort, and re-index all designed pages.

    Sorting: by (order, page_index) to maintain section order
    and handle multi-page sections correctly.
    """
    pages = state.get("designed_pages", [])

    # Sort by (order, page_index)
    sorted_pages = sorted(
        pages,
        key=lambda x: (x.get("order", 0), x.get("page_index", 0))
    )

    # Re-assign order (1-based) and remove page_index
    final_pages = []
    for idx, page in enumerate(sorted_pages, start=1):
        final_pages.append({
            "html_content": page["html_content"],
            "order": idx,
            "section_title": page["section_title"],
            "section_number": page.get("section_number"),
            "outline_id": page["outline_id"]
        })

    # Create payload for API
    payload = {"publish_content": final_pages}

    return {
        "publish_payload": json.dumps(payload, ensure_ascii=False),
        "status": "combined"
    }


async def publish_report(state: ReportDesignState) -> dict:
    """
    PATCH the publish_content to the API.

    Endpoint (unchanged): PATCH /reports/{report_id}/publish-content
    """
    api_url = state["api_url"]
    token = state["token"]
    report_id = state["report_id"]
    payload = state.get("publish_payload", "{}")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.patch(
            f"{api_url}/reports/{report_id}/publish-content",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            content=payload
        )

    if response.status_code not in (200, 201, 204):
        error_msg = f"Publish failed: {response.status_code} - {response.text[:200]}"
        return {
            "errors": [error_msg],
            "status": "publish_failed"
        }

    return {"status": "completed"}


# =============================================================================
# Graph Construction with Fan-out/Fan-in Pattern
# =============================================================================

def fan_out_to_sections(state: ReportDesignState) -> list[Send]:
    """
    Distribute sections to parallel design workers.

    Returns list of Send objects, one per section.
    Supports up to 20+ parallel section designs.
    """
    sections = state.get("sections", [])
    design_req = state.get("design_requirement", {})
    language_code = state.get("language_code", "ko")
    outline = state.get("outline", {})
    outline_id = outline.get("id", "")

    sends = []
    for section in sections:
        sends.append(
            Send(
                "design_section",
                {
                    "section": section,
                    "design_requirement": design_req,
                    "language_code": language_code,
                    "outline_id": outline_id
                }
            )
        )

    return sends


def build_report_design_graph():
    """
    Build the business report design workflow graph.

    Workflow:
        START -> fetch_all_data -> prepare_sections
              -> [fan_out] -> design_section (xN parallel)
              -> combine_results -> publish_report -> END
    """
    builder = StateGraph(ReportDesignState)

    # Add nodes
    builder.add_node("fetch_all_data", fetch_all_data)
    builder.add_node("prepare_sections", prepare_sections)
    builder.add_node("design_section", design_section)
    builder.add_node("combine_results", combine_results)
    builder.add_node("publish_report", publish_report)

    # Linear edges: START -> fetch -> prepare
    builder.add_edge(START, "fetch_all_data")
    builder.add_edge("fetch_all_data", "prepare_sections")

    # Fan-out edge: prepare -> [design_section x N]
    builder.add_conditional_edges(
        "prepare_sections",
        fan_out_to_sections,
        ["design_section"]
    )

    # Fan-in happens automatically due to reducer
    # Then: design_section -> combine -> publish -> END
    builder.add_edge("design_section", "combine_results")
    builder.add_edge("combine_results", "publish_report")
    builder.add_edge("publish_report", END)

    return builder.compile()


# Build the graph
report_design_graph = build_report_design_graph()


# =============================================================================
# Workflow Execution
# =============================================================================

async def run_report_design_workflow(
    api_url: str,
    token: str,
    report_id: str
) -> dict:
    """
    Execute the business report design workflow.

    Args:
        api_url: Base URL for the API (e.g., "https://api.example.com")
        token: Bearer authentication token
        report_id: Report identifier

    Returns:
        Final state with designed pages and status

    Example:
        result = await run_report_design_workflow(
            api_url="https://api.example.com",
            token="your_token_here",
            report_id="report-123"
        )
    """
    initial_state = {
        "api_url": api_url,
        "token": token,
        "report_id": report_id,
        "design_requirement": None,
        "outline": None,
        "report_metadata": None,
        "language_code": "ko",
        "sections": [],
        "designed_pages": [],
        "publish_payload": None,
        "status": "pending",
        "errors": []
    }

    result = await report_design_graph.ainvoke(initial_state)

    return result
