"""
비즈니스 보고서 디자이너 워크플로우의 유틸리티 함수 모듈.

이 모듈은 다음 헬퍼 함수들을 제공합니다:
- LLM 응답 콘텐츠 추출 (다양한 응답 형식 처리)
- 3단계 폴백을 지원하는 챗 모델 초기화
- 멀티 페이지 섹션을 위한 HTML body 블록 추출
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from report_designer.state import DesignedPage, Section


@dataclass
class LLMConfig:
    """폴백 체인을 위한 LLM 설정."""

    name: str  # 모델명
    provider: str  # 프로바이더 (예: "google")
    temperature: float = 1.0  # 생성 온도
    max_retries: int = 3  # 최대 재시도 횟수


# 기본 LLM 설정 (안정성을 위한 3단계 폴백)
DEFAULT_LLM_CONFIGS = [
    LLMConfig("gemini-2.0-flash", "google", 1.0),  # 기본
    LLMConfig("gemini-2.0-flash", "google", 1.0),  # 재시도
    LLMConfig("gemini-1.5-pro", "google", 1.0),  # 폴백
]


def extract_text_content(response_content: Any) -> str:
    """
    LLM 응답에서 텍스트 콘텐츠를 추출합니다.

    일부 LLM(예: Gemini)은 콘텐츠를 일반 문자열이 아닌 파트 리스트로 반환합니다.
    이 함수는 두 경우를 모두 처리합니다.

    Args:
        response_content: LLM 응답의 content 속성.
                         str, list 또는 기타 타입일 수 있습니다.

    Returns:
        추출된 텍스트 콘텐츠 문자열.

    사용 예시:
        >>> # 문자열 콘텐츠 (대부분의 LLM)
        >>> extract_text_content("Hello world")
        'Hello world'
        >>> # 리스트 콘텐츠 (Gemini 스타일)
        >>> extract_text_content([{"text": "Hello"}, {"text": " world"}])
        'Hello world'
    """
    if isinstance(response_content, str):
        return response_content

    if isinstance(response_content, list):
        text_parts: list[str] = []
        for item in response_content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                text_parts.append(item["text"])
            elif hasattr(item, "text"):
                text_parts.append(item.text)
        return "".join(text_parts)

    return str(response_content)


def create_llm(
    config: LLMConfig,
    api_key: str | None = None,
) -> BaseChatModel:
    """
    설정에 기반하여 LLM을 생성하는 팩토리 함수.

    Args:
        config: name, provider, temperature를 포함한 LLM 설정.
        api_key: 선택적 API 키. 제공되지 않으면 GOOGLE_API_KEY 환경변수 사용.

    Returns:
        초기화된 챗 모델 인스턴스.
    """
    if api_key is None:
        api_key = os.getenv("GOOGLE_API_KEY")

    return ChatGoogleGenerativeAI(
        model=config.name,
        temperature=config.temperature,
        google_api_key=api_key,
    )


def load_chat_model(
    model: str,
    temperature: float = 1.0,
) -> BaseChatModel:
    """
    프로바이더와 모델명에 기반하여 챗 모델을 로드합니다.

    이 팩토리 함수는 통합된 인터페이스를 통해 여러 프로바이더를 지원합니다.
    모델 문자열 형식은 "provider/model_name"입니다.

    지원 프로바이더:
    - google (Google Gemini): GOOGLE_API_KEY 필요

    Args:
        model: "provider/model_name" 형식의 모델 식별자.
               예시: "google/gemini-2.0-flash", "google/gemini-1.5-pro"
        temperature: 생성 온도 (0.0-2.0).

    Returns:
        초기화된 챗 모델 인스턴스.

    Raises:
        ValueError: 모델 문자열 형식이 잘못되었거나 프로바이더가
                    지원되지 않는 경우.

    사용 예시:
        >>> llm = load_chat_model("google/gemini-2.0-flash", temperature=1.0)
        >>> response = llm.invoke("Hello!")
    """
    # 모델 문자열 파싱
    if "/" in model:
        provider, model_name = model.split("/", 1)
    elif ":" in model:
        provider, model_name = model.split(":", 1)
    else:
        raise ValueError(
            f"잘못된 모델 형식: '{model}'. "
            "'provider/model_name' 또는 'provider:model_name' 형식이어야 합니다."
        )

    provider = provider.lower()

    # 프로바이더 별칭 정규화
    provider_aliases = {
        "google": "google",
        "google_genai": "google",
        "gemini": "google",
    }

    if provider not in provider_aliases:
        raise ValueError(
            f"지원되지 않는 프로바이더: '{provider}'. "
            f"지원 목록: {list(provider_aliases.keys())}"
        )

    # Google 모델 생성
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        temperature=temperature,
    )


async def call_llm_with_fallback(
    system_prompt: str,
    user_prompt: str,
    configs: list[LLMConfig] | None = None,
) -> tuple[str, str]:
    """
    3단계 폴백 체인으로 LLM을 호출합니다.

    Args:
        system_prompt: LLM에 전달할 시스템 프롬프트.
        user_prompt: LLM에 전달할 사용자 프롬프트.
        configs: 폴백 체인용 LLM 설정 목록.
                 기본값: DEFAULT_LLM_CONFIGS.

    Returns:
        tuple[str, str]: (응답 텍스트, 사용된 모델명)

    Raises:
        RuntimeError: 모든 LLM 시도가 실패한 경우.
    """
    if configs is None:
        configs = DEFAULT_LLM_CONFIGS

    for i, config in enumerate(configs):
        try:
            llm = create_llm(config)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
            response = await llm.ainvoke(messages)
            text = extract_text_content(response.content)

            # 빈 응답 확인 (다음 모델로 폴백 트리거)
            if not text.strip() and i < len(configs) - 1:
                print(f"{config.name}에서 빈 응답, 다음 모델 시도 중...")
                continue

            return text, config.name

        except Exception as e:
            print(f"LLM {config.name} 실패: {e}")
            if i == len(configs) - 1:
                raise RuntimeError(f"모든 LLM 시도 실패. 마지막 오류: {e}")

    raise RuntimeError("모든 LLM 시도 실패")


def extract_body_blocks(
    html_content: str,
    section: Section,
    outline_id: str,
    model_used: Optional[str] = None,
) -> list[DesignedPage]:
    """
    LLM 출력에서 모든 <body>...</body> 블록을 추출합니다.

    멀티 페이지 섹션(콘텐츠 > 1200자)에서 반환되는 여러 body 블록을 처리합니다.
    각 body 블록은 최종 보고서에서 별도의 페이지가 됩니다.

    Args:
        html_content: LLM의 원본 HTML 출력.
        section: 메타데이터용 섹션 데이터.
        outline_id: 아웃라인 식별자.
        model_used: 이 콘텐츠를 생성한 LLM 모델명.

    Returns:
        body 블록당 하나씩, DesignedPage 딕셔너리 목록.
    """
    # __PAGE_BREAK__ 마커 제거 (있는 경우)
    html_content = html_content.replace("__PAGE_BREAK__", "")

    # 모든 body 블록 찾기
    body_pattern = r"<body[^>]*>.*?</body>"
    matches = re.findall(body_pattern, html_content, re.DOTALL | re.IGNORECASE)

    pages: list[DesignedPage] = []

    if matches:
        for idx, body_html in enumerate(matches):
            pages.append({
                "html_content": body_html,
                "order": section.get("order", 0),
                "section_title": section.get("section_title", ""),
                "section_number": section.get("section_number"),
                "outline_id": outline_id,
                "page_index": idx,
                "model_used": model_used,
            })
    else:
        # body 태그를 찾지 못한 경우, 전체 콘텐츠 사용
        pages.append({
            "html_content": html_content,
            "order": section.get("order", 0),
            "section_title": section.get("section_title", ""),
            "section_number": section.get("section_number"),
            "outline_id": outline_id,
            "page_index": 0,
            "model_used": model_used,
        })

    return pages
