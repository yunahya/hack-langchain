"""
비즈니스 보고서 디자이너 워크플로우의 상태(State) 정의 모듈.

이 모듈은 다음 TypedDict 스키마를 정의합니다:
- DesignRequirement: API에서 가져온 디자인 커스터마이징 설정
- Section: 비즈니스 보고서 섹션 구조
- DesignedPage: 단일 페이지 디자인 결과물
- ReportDesignState: 리듀서를 포함한 메인 워크플로우 상태
- SectionPayload: 병렬 섹션 처리를 위한 페이로드
"""

import operator
from typing import Annotated, Optional

from typing_extensions import TypedDict


class DesignRequirement(TypedDict):
    """/customization 엔드포인트에서 가져온 비즈니스 보고서 디자인 설정.

    사용처: design_prompt.jinja2 템플릿
    """

    primary_color: str  # 예: "#1E40AF" - 메인 브랜드 색상
    secondary_color: str  # 예: "#3B82F6" - 보조 색상
    accent_color: str  # 예: "#10B981" - 강조/포인트 색상
    pdf_orientation: str  # "portrait"(세로) | "landscape"(가로)


class Section(TypedDict):
    """디자인할 비즈니스 보고서 섹션.

    design_prompt.jinja2 템플릿 요구사항에 맞춘 필드 구성:
    - section_key: 레이아웃 결정을 위한 특수 식별자
    - parent_path: 브레드크럼 네비게이션 경로
    - title: 섹션 제목
    - content: report_generator에서 생성된 마크다운/HTML 콘텐츠
    """

    order: int  # 정렬 순서
    section_title: str  # 표시 제목
    section_number: Optional[str]  # 예: "1.0", "2.1"
    section_key: str  # "EXECUTIVE_SUMMARY", "DATA_TABLE" 등
    title: str  # 헤더용 메인 섹션 제목
    content: str  # 마크다운/HTML 콘텐츠
    parent_path: Optional[str]  # 브레드크럼 경로 (예: "금주 업무 현황 > 성과 분석")


class DesignedPage(TypedDict):
    """단일 비즈니스 보고서 페이지 디자인 결과물."""

    html_content: str  # 디자인된 HTML 콘텐츠
    order: int  # 페이지 순서
    section_title: str  # 섹션 제목
    section_number: Optional[str]  # 섹션 번호
    outline_id: str  # 아웃라인 ID
    page_index: int  # 멀티 페이지 섹션용 (콘텐츠 > 1200자일 때)
    model_used: Optional[str]  # 이 페이지를 생성한 LLM 모델명


class ReportDesignState(TypedDict):
    """비즈니스 보고서 디자인을 위한 메인 워크플로우 상태.

    병렬로 생성된 페이지들을 집계하기 위해 operator.add와 함께 Annotated를 사용합니다.
    """

    # API 입력값
    api_url: str  # API 베이스 URL
    token: str  # 인증 토큰
    report_id: str  # 보고서 ID

    # API에서 가져온 데이터
    design_requirement: Optional[DesignRequirement]  # 디자인 요구사항
    outline: Optional[dict]  # 보고서 아웃라인
    report_metadata: Optional[dict]  # 보고서 메타데이터
    language_code: str  # 언어 코드 (기본값: "ko")
    sections: list[Section]  # 디자인할 섹션 목록

    # 병렬 처리 결과 - fan-in을 위해 반드시 리듀서 사용 필요
    designed_pages: Annotated[list[DesignedPage], operator.add]

    # 최종 출력
    publish_payload: Optional[str]  # API에 전송할 JSON 페이로드

    # 메타데이터
    status: str  # 현재 워크플로우 상태
    errors: Annotated[list[str], operator.add]  # 에러 메시지 목록


class SectionPayload(TypedDict):
    """Send API를 통해 각 병렬 섹션 처리기에 전달되는 페이로드."""

    section: Section  # 디자인할 섹션
    design_requirement: DesignRequirement  # 디자인 요구사항
    language_code: str  # 언어 코드
    outline_id: str  # 아웃라인 ID
