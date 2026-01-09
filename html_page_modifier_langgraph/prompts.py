"""
Prompt templates for the HTML Page Modifier workflow.

This module contains prompt templates for:
- HTML modification based on user requests
- Modification summary generation
"""

from html_page_modifier_langgraph.state import PageModificationInput


def build_modification_prompt(
    user_input: PageModificationInput,
    style_preference: str = "inline",
) -> str:
    """
    Build the prompt for HTML modification.

    Args:
        user_input: User input containing HTML and modification request.
        style_preference: 'inline' or 'internal' for CSS styling approach.

    Returns:
        Formatted prompt string for LLM.
    """
    style_instruction = (
        "inline style 속성을 사용하세요"
        if style_preference == "inline"
        else "<style> 태그 내에 CSS를 포함하세요"
    )

    return f"""당신은 HTML/CSS 디자인 전문가입니다.
주어진 HTML을 사용자 요청에 따라 수정하세요.

## 현재 페이지 정보
- Page ID: {user_input.get("page_id", "unknown")}
- Page Order: {user_input.get("page_order", 0)}

## 현재 HTML
```html
{user_input["html_content"]}
```

## 사용자 수정 요청
{user_input["user_request"]}

## 지침
1. 사용자 요청에 정확히 맞게 HTML을 수정하세요.
2. 기존 HTML 구조를 최대한 유지하면서 필요한 부분만 수정하세요.
3. CSS 스타일은 {style_instruction}.
4. 수정된 HTML만 반환하세요. 설명이나 추가 텍스트는 포함하지 마세요.
5. 코드 블록(```)으로 감싸지 마세요. 순수 HTML만 반환하세요.

수정된 HTML:
"""


def build_summary_prompt(user_request: str) -> str:
    """
    Build the prompt for generating modification summary.

    Args:
        user_request: Original user modification request.

    Returns:
        Formatted prompt string for LLM.
    """
    return f"""다음 HTML 수정 요청에 대해 수행된 변경 사항을 1-2문장으로 간략히 요약하세요.

수정 요청: {user_request}

요약 (한국어로):
"""


# Default fallback values
DEFAULT_MODIFIED_HTML = "<div>수정에 실패했습니다. 다시 시도해주세요.</div>"
DEFAULT_SUMMARY = "수정 작업이 완료되지 않았습니다."
