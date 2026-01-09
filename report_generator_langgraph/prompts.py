"""
Prompt templates for the Business Report Generator workflow.

This module contains prompt templates for:
- TOC (Table of Contents) generation
- Individual page content generation
"""

from report_generator_langgraph.state import ReportInput, TocItem


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
