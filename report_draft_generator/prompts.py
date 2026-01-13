"""
Prompt templates for the Report Draft Generator workflow.

This module contains prompt templates for both phases:
- Phase 1 (Content Generation): TOC and page content prompts
- Phase 2 (HTML Design): System prompt, user prompt, and Jinja2 template rendering

Uses PromptManager for Jinja2 template caching.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from report_draft_generator.state import (
    DesignRequirement,
    ReportInput,
    ReportSection,
    TocItem,
)


# =============================================================================
# Jinja2 Template Management
# =============================================================================

# Default prompts directory
PROMPTS_DIR = Path(__file__).parent / "prompts"


class PromptManager:
    """Jinja2 prompt template manager with caching."""

    def __init__(self, prompts_dir: Path | None = None):
        """
        Initialize the prompt manager.

        Args:
            prompts_dir: Directory containing Jinja2 templates.
                         Default: ./prompts relative to this module.
        """
        if prompts_dir is None:
            prompts_dir = PROMPTS_DIR

        self.prompts_dir = prompts_dir
        self.env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._prompt_cache: dict[str, any] = {}

    def get_prompt(self, name: str):
        """Get prompt template with caching."""
        if name not in self._prompt_cache:
            self._prompt_cache[name] = self.env.get_template(name)
        return self._prompt_cache[name]

    def render(self, prompt_name: str, **context) -> str:
        """Render a prompt template with the given context."""
        prompt = self.get_prompt(prompt_name)
        return prompt.render(**context)


# Global prompt manager instance
prompt_manager = PromptManager()


# =============================================================================
# Phase 1: Content Generation Prompts
# =============================================================================


def build_toc_prompt(user_input: ReportInput) -> str:
    """
    Build the prompt for Table of Contents generation.

    The TOC generation uses a lower temperature (0.5) for structured output.
    The prompt instructs the LLM to generate a JSON array of sections.

    Args:
        user_input: User input containing report specifications.

    Returns:
        Formatted prompt string for TOC generation.
    """
    # Extract optional fields with defaults
    page_count = user_input.get("page_count", 3)
    tone = user_input.get("tone", "격식체, 간결함")
    emphasis = user_input.get("emphasis", "")
    include_visuals = user_input.get("include_visuals", False)
    additional_data = user_input.get("additional_data", "")

    return f"""당신은 비즈니스 보고서 구조 전문가입니다.
다음 정보를 바탕으로 보고서의 목차(Table of Contents)를 생성하세요.

## 보고서 정보
- 보고서 유형: {user_input.get("report_type", "일반 보고서")}
- 보고 목적: {user_input.get("purpose", "현황 공유")}
- 보고 대상: {user_input.get("audience", "직속 상사")}
- 주제/제목: {user_input.get("topic", "제목 없음")}
- 핵심 메시지: {user_input.get("key_message", "")}
- 회사/팀 정보: {user_input.get("company_info", "")}
- 목표 페이지 수: {page_count}페이지
- 강조 포인트: {emphasis if emphasis else "없음"}
- 시각화 요소 포함: {"예" if include_visuals else "아니오"}
- 추가 데이터/자료: {additional_data if additional_data else "없음"}

## 요구사항
1. 보고서 유형과 목적에 맞는 적절한 섹션 구조를 생성하세요.
2. 각 섹션은 A4 1페이지 분량으로 작성될 예정입니다.
3. 보고 대상의 수준에 맞게 섹션을 구성하세요.
4. 목표 페이지 수({page_count})에 맞춰 섹션 수를 조절하세요.

## 출력 형식
반드시 아래 JSON 배열 형식으로만 출력하세요. 다른 텍스트는 포함하지 마세요.

[
    {{"page_id": "고유_영문_id", "title": "섹션 제목", "description": "이 섹션에서 다룰 내용 설명 (2-3문장)", "order": 1}},
    {{"page_id": "다음_id", "title": "다음 섹션 제목", "description": "설명...", "order": 2}}
]

JSON 배열만 출력하세요:
"""


def build_page_content_prompt(
    page_info: TocItem,
    user_input: ReportInput,
) -> str:
    """
    Build the prompt for individual page content generation.

    The page generation uses a higher temperature (0.7) for creative content.
    Each page targets A4 size with 800-1200 Korean characters.

    Args:
        page_info: TOC item with page metadata (title, description, order).
        user_input: User input containing report specifications.

    Returns:
        Formatted prompt string for page content generation.
    """
    # Extract optional fields with defaults
    tone = user_input.get("tone", "격식체, 간결함")
    include_visuals = user_input.get("include_visuals", False)
    additional_data = user_input.get("additional_data", "")

    # Build visual instruction if needed
    visual_instruction = ""
    if include_visuals:
        visual_instruction = """
- 적절한 위치에 표(Table)나 차트 설명을 마크다운으로 포함하세요.
- 예: | 항목 | 값 | 또는 [차트: 분기별 매출 추이]
"""

    return f"""당신은 비즈니스 보고서 작성 전문가입니다.
A4 1페이지 분량의 보고서 섹션을 마크다운으로 작성하세요.

## 보고서 맥락
- 보고서 유형: {user_input.get("report_type", "일반 보고서")}
- 보고 목적: {user_input.get("purpose", "현황 공유")}
- 보고 대상: {user_input.get("audience", "직속 상사")}
- 전체 주제: {user_input.get("topic", "제목 없음")}
- 핵심 메시지: {user_input.get("key_message", "")}
- 회사/팀: {user_input.get("company_info", "")}

## 현재 섹션 정보
- 섹션 제목: {page_info["title"]}
- 섹션 설명: {page_info["description"]}
- 섹션 순서: {page_info["order"]}번째

## 작성 지침
- 문체/톤: {tone}
- 분량: A4 1페이지 (800-1200자, 한글 기준)
- 형식: 마크다운 (##, ###, -, **굵게**, *기울임* 활용)
- 구성: 소제목 2-3개로 나누어 작성{visual_instruction}
- 참고 데이터: {additional_data if additional_data else "없음"}

## 주의사항
- 섹션 제목(## {page_info["title"]})부터 시작하세요.
- 전문적이고 읽기 쉬운 비즈니스 문서 스타일로 작성하세요.
- 구체적인 내용을 포함하되, 없는 수치는 만들지 마세요.

마크다운 콘텐츠:
"""


# Default fallback TOC when JSON parsing fails
DEFAULT_FALLBACK_TOC: list[TocItem] = [
    {
        "page_id": "summary",
        "title": "요약",
        "description": "보고서 핵심 내용 요약",
        "order": 1,
    },
    {
        "page_id": "main_content",
        "title": "본문",
        "description": "주요 내용 상세 기술",
        "order": 2,
    },
    {
        "page_id": "conclusion",
        "title": "결론 및 제언",
        "description": "결론과 향후 계획",
        "order": 3,
    },
]


# =============================================================================
# Phase 2: HTML Design Prompts
# =============================================================================

# System prompt template for HTML designer
DESIGN_SYSTEM_PROMPT_TEMPLATE = """당신은 국내 주요 기업의 내부 비즈니스 보고서를 디자인해온 20년 경력의 시니어 문서 디자이너입니다.

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


def get_design_system_prompt(language_code: str = "ko") -> str:
    """
    Get the system prompt with language code applied.

    Args:
        language_code: Report language code (default: "ko").

    Returns:
        Formatted system prompt string.
    """
    return DESIGN_SYSTEM_PROMPT_TEMPLATE.format(language_code=language_code)


def render_design_prompt(
    section: ReportSection,
    design_requirement: DesignRequirement,
    content_length: int,
) -> str:
    """
    Render the design prompt using the Jinja2 template.

    Template variables (used in design_prompt.jinja2):
    - section: Section dict with title, content, section_key, parent_path
    - design_requirement: Color and orientation settings
    - content_length: Character count for layout decisions

    Template includes:
    - Core rules (absolute constraints, required attributes)
    - Length-based content metrics
    - Design system (colors, typography)
    - Layout patterns for business reports
    - Infographic templates for KPI, charts, etc.

    Args:
        section: Section data to design.
        design_requirement: Design customization settings.
        content_length: Character count of section content.

    Returns:
        Rendered design prompt string.
    """
    return prompt_manager.render(
        "design_prompt.jinja2",
        section=section,
        design_requirement=design_requirement,
        content_length=content_length,
    )


def build_design_user_prompt(design_prompt: str, language_code: str = "ko") -> str:
    """
    Build the user prompt for HTML design LLM call.

    Args:
        design_prompt: Design prompt rendered from template.
        language_code: Report language code.

    Returns:
        Complete user prompt string.
    """
    return f"{design_prompt}\n\n{language_code} 언어를 사용하여 비즈니스 보고서 디자인을 시작하세요."
