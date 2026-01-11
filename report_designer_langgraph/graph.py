"""
비즈니스 보고서 디자인 워크플로우

엔터프라이즈급 내부 비즈니스 보고서 HTML 디자인을 생성하는 LangGraph 기반 워크플로우.

대상 보고서: 주간업무보고, 기획안, 프로젝트 제안서, 결과 보고서, 회의록 등
입력 소스: report_generator.ipynb에서 생성된 마크다운 콘텐츠

워크플로우 아키텍처:
    START -> fetch_all_data -> prepare_sections
          -> [fan_out] -> design_section (xN 병렬)
          -> combine_results -> publish_report -> END

API 엔드포인트:
    - GET /customization/{report_id} - 디자인 요구사항 (색상, 방향)
    - GET /document-outlines/{report_id} - 섹션이 포함된 아웃라인
    - GET /reports/{report_id} - 보고서 메타데이터
    - PATCH /reports/{report_id}/publish-content - 디자인된 페이지 발행
"""

# 표준 라이브러리
import asyncio
import json

# 서드파티
import httpx

# LangGraph
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

# 로컬 임포트
from report_designer.state import (
    ReportDesignState,
    SectionPayload,
)
from report_designer.prompts import (
    get_system_prompt,
    render_design_prompt,
    build_user_prompt,
)
from report_designer.utils import (
    call_llm_with_fallback,
    extract_body_blocks,
)


# =============================================================================
# HTTP Fetch 노드 (병렬 데이터 가져오기)
# =============================================================================


async def fetch_all_data(state: ReportDesignState) -> dict:
    """
    모든 비즈니스 보고서 데이터를 병렬로 가져옵니다.

    엔드포인트:
    - GET /customization/{report_id} - 디자인 요구사항
    - GET /document-outlines/{report_id} - 섹션이 포함된 아웃라인
    - GET /reports/{report_id} - 보고서 메타데이터
    """
    api_url = state["api_url"]
    token = state["token"]
    report_id = state["report_id"]

    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 병렬 요청
        tasks = [
            client.get(f"{api_url}/customization/{report_id}", headers=headers),
            client.get(f"{api_url}/document-outlines/{report_id}", headers=headers),
            client.get(f"{api_url}/reports/{report_id}", headers=headers),
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

    # 응답 처리
    errors = []
    design_req = {}
    outline = {}
    report_meta = {}

    endpoint_names = ["customization", "document-outlines", "reports"]

    for i, resp in enumerate(responses):
        if isinstance(resp, Exception):
            errors.append(f"{endpoint_names[i]} 가져오기 실패: {str(resp)}")
            continue
        if resp.status_code != 200:
            errors.append(f"{endpoint_names[i]}가 {resp.status_code} 반환")
            continue

        data = resp.json()
        if i == 0:
            design_req = data
        elif i == 1:
            outline = data
        else:
            report_meta = data

    # language_code 추출 (기본값: 비즈니스 보고서용 한국어)
    language_code = report_meta.get("language_code", "ko")

    return {
        "design_requirement": design_req,
        "outline": outline,
        "report_metadata": report_meta,
        "language_code": language_code,
        "errors": errors,
        "status": "data_fetched",
    }


def prepare_sections(state: ReportDesignState) -> dict:
    """
    아웃라인에서 비즈니스 보고서 섹션 배열을 추출합니다.

    섹션에는 report_generator 출력의 콘텐츠가 포함되어야 합니다.
    """
    outline = state.get("outline", {})
    sections = outline.get("sections", [])

    return {
        "sections": sections,
        "status": "sections_prepared",
    }


# =============================================================================
# Design Section 노드 (핵심 처리)
# =============================================================================


async def design_section(state: SectionPayload) -> dict:
    """
    3단계 LLM 폴백으로 단일 비즈니스 보고서 섹션을 디자인합니다.

    이 노드는 Send API를 통해 병렬로 호출됩니다.
    조합: 템플릿 렌더링 + LLM 호출 + body 추출.

    템플릿 처리 내용:
    - 콘텐츠 길이 분석 (짧음/중간/긴/멀티페이지)
    - 레이아웃 패턴 선택 (KPI 대시보드, 데이터 분석 등)
    - 1200자 초과 콘텐츠의 멀티페이지 분할
    """
    section = state["section"]
    design_req = state["design_requirement"]
    language_code = state["language_code"]
    outline_id = state["outline_id"]

    # 레이아웃 결정을 위한 콘텐츠 길이 계산
    content = section.get("content", "")
    content_length = len(content)

    try:
        # Jinja2 템플릿으로 디자인 프롬프트 렌더링
        design_prompt = render_design_prompt(
            section=section,
            design_requirement=design_req,
            content_length=content_length,
        )

        # 시스템 및 사용자 프롬프트 생성
        system_prompt = get_system_prompt(language_code)
        user_prompt = build_user_prompt(design_prompt, language_code)

        # 폴백으로 LLM 호출
        html_content, model_used = await call_llm_with_fallback(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # <body> 블록 추출 (긴 콘텐츠의 경우 여러 개일 수 있음)
        pages = extract_body_blocks(
            html_content=html_content,
            section=section,
            outline_id=outline_id,
            model_used=model_used,
        )

        return {
            "designed_pages": pages,
            "errors": [],
        }

    except Exception as e:
        error_msg = f"섹션 '{section.get('section_title', '알 수 없음')}' 실패: {str(e)}"
        return {
            "designed_pages": [],
            "errors": [error_msg],
        }


# =============================================================================
# 결과 결합 및 발행 노드
# =============================================================================


def combine_results(state: ReportDesignState) -> dict:
    """
    모든 디자인된 페이지를 평탄화, 정렬 및 재인덱싱합니다.

    정렬: (order, page_index) 기준으로 섹션 순서를 유지하고
    멀티페이지 섹션을 올바르게 처리합니다.
    """
    pages = state.get("designed_pages", [])

    # (order, page_index) 기준 정렬
    sorted_pages = sorted(
        pages,
        key=lambda x: (x.get("order", 0), x.get("page_index", 0)),
    )

    # order 재할당 (1부터 시작) 및 page_index 제거
    final_pages = []
    for idx, page in enumerate(sorted_pages, start=1):
        final_pages.append({
            "html_content": page["html_content"],
            "order": idx,
            "section_title": page["section_title"],
            "section_number": page.get("section_number"),
            "outline_id": page["outline_id"],
        })

    # API용 페이로드 생성
    payload = {"publish_content": final_pages}

    return {
        "publish_payload": json.dumps(payload, ensure_ascii=False),
        "status": "combined",
    }


async def publish_report(state: ReportDesignState) -> dict:
    """
    publish_content를 API에 PATCH합니다.

    엔드포인트: PATCH /reports/{report_id}/publish-content
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
                "Content-Type": "application/json",
            },
            content=payload,
        )

    if response.status_code not in (200, 201, 204):
        error_msg = f"발행 실패: {response.status_code} - {response.text[:200]}"
        return {
            "errors": [error_msg],
            "status": "publish_failed",
        }

    return {"status": "completed"}


# =============================================================================
# Fan-out/Fan-in 패턴을 사용한 그래프 구성
# =============================================================================


def fan_out_to_sections(state: ReportDesignState) -> list[Send]:
    """
    섹션들을 병렬 디자인 워커들에게 분배합니다.

    섹션당 하나씩 Send 객체 리스트를 반환합니다.
    20개 이상의 병렬 섹션 디자인을 지원합니다.
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
                    "outline_id": outline_id,
                },
            )
        )

    return sends


def build_report_design_graph():
    """
    비즈니스 보고서 디자인 워크플로우 그래프를 빌드합니다.

    워크플로우:
        START -> fetch_all_data -> prepare_sections
              -> [fan_out] -> design_section (xN 병렬)
              -> combine_results -> publish_report -> END
    """
    builder = StateGraph(ReportDesignState)

    # 노드 추가
    builder.add_node("fetch_all_data", fetch_all_data)
    builder.add_node("prepare_sections", prepare_sections)
    builder.add_node("design_section", design_section)
    builder.add_node("combine_results", combine_results)
    builder.add_node("publish_report", publish_report)

    # 선형 엣지: START -> fetch -> prepare
    builder.add_edge(START, "fetch_all_data")
    builder.add_edge("fetch_all_data", "prepare_sections")

    # Fan-out 엣지: prepare -> [design_section x N]
    builder.add_conditional_edges(
        "prepare_sections",
        fan_out_to_sections,
        ["design_section"],
    )

    # 리듀서로 인해 Fan-in이 자동으로 발생
    # 이후: design_section -> combine -> publish -> END
    builder.add_edge("design_section", "combine_results")
    builder.add_edge("combine_results", "publish_report")
    builder.add_edge("publish_report", END)

    return builder.compile()


# 그래프 빌드
report_design_graph = build_report_design_graph()


# =============================================================================
# 워크플로우 실행
# =============================================================================


async def run_report_design_workflow(
    api_url: str,
    token: str,
    report_id: str,
) -> dict:
    """
    비즈니스 보고서 디자인 워크플로우를 실행합니다.

    Args:
        api_url: API의 베이스 URL (예: "https://api.example.com")
        token: Bearer 인증 토큰
        report_id: 보고서 식별자

    Returns:
        디자인된 페이지와 상태가 포함된 최종 상태

    사용 예시:
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
        "errors": [],
    }

    result = await report_design_graph.ainvoke(initial_state)

    return result
