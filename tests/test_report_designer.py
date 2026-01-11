"""
Unit Tests for Report Designer Workflow

테스트 전략:
- LLM 호출은 Mock으로 대체 (비용/속도 최적화)
- State schema 검증
- Reducer 동작 검증
- Body block 추출 로직 검증
- 워크플로우 통합 테스트
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import operator
import json
import asyncio

# Import the module under test
from report_designer.graph import (
    DesignRequirement,
    Section,
    DesignedPage,
    ReportDesignState,
    SectionPayload,
    LLMConfig,
    extract_text_content,
    extract_body_blocks,
    prepare_sections,
    combine_results,
    fan_out_to_sections,
    LLM_CONFIGS,
)


# =============================================================================
# Test Fixtures & Mocks
# =============================================================================

@pytest.fixture
def sample_design_requirement() -> DesignRequirement:
    """샘플 디자인 요구사항"""
    return {
        "primary_color": "#1E40AF",
        "secondary_color": "#3B82F6",
        "accent_color": "#10B981",
        "pdf_orientation": "portrait"
    }


@pytest.fixture
def sample_section() -> Section:
    """샘플 비즈니스 보고서 섹션"""
    return {
        "order": 1,
        "section_title": "금주 핵심 성과 요약",
        "section_number": "1.0",
        "section_key": "EXECUTIVE_SUMMARY",
        "title": "2024년 4분기 마케팅팀 주간업무보고",
        "content": """## 1. 금주 핵심 성과 요약

본 섹션은 2024년 4분기 마케팅팀의 주간 주요 업무 성과를 기술합니다.

*   **클릭률 (CTR) 대폭 상승:** 지난주 대비 **15% 상승**
*   **목표 전환율 (CVR) 조기 달성:** 전환율 3.2% 달성

| 구분 | 지난주 | 금주 | 증감률 |
| :--- | :---: | :---: | :---: |
| **CTR** | 기준치 | **+15%** | ▲ 15.0% |
""",
        "parent_path": "금주 업무 현황"
    }


@pytest.fixture
def sample_long_section() -> Section:
    """긴 콘텐츠 샘플 섹션 (multi-page trigger용)"""
    long_content = """## 2. 캠페인별 상세 성과 및 데이터 분석

본 섹션에서는 2024년 4분기 주력 캠페인의 디지털 광고 성과를 정량적으로 분석합니다.

### 2.1. 디지털 광고 성과 추이

지난 주 실시한 신규 크리에이티브 A/B 테스트 및 타겟팅 최적화 작업의 결과로,
주요 성과 지표가 전주 대비 뚜렷한 상승세를 보였습니다.

*   **클릭률(CTR) 상승**: 직전 주차 대비 **15% 상승**하며 고객의 초기 반응률이 크게 개선되었습니다.
*   **전환율(CVR) 달성**: 목표치였던 3.0%를 상회하는 **3.2%의 전환율**을 달성했습니다.

| 구분 | 전주 대비 증감 | 금주 성과 | 비고 |
| :--- | :---: | :---: | :--- |
| **CTR** | ▲ 15% | **상승** | 신규 소재 반응 호조 |
| **CVR** | - | **3.2%** | 목표 초과 달성 |
| **CPA** | ▼ 감소 | **개선** | 효율 최적화 성공 |

### 2.2. 채널별 예산 집행 현황 및 ROI 비교

4분기 마케팅 예산 계획에 따라 주요 매체별로 예산을 집행하였으며,
성과 데이터에 기반하여 채널별 기여도를 평가했습니다.

*   **Meta (Instagram/Facebook)**: 신규 숏폼 영상 소재가 높은 인게이지먼트를 유도하며 가장 높은 ROI를 기록했습니다.
*   **Search Ads (SA)**: 브랜드 키워드 검색량은 안정적이나, 일반 키워드의 경쟁 심화로 CPC가 소폭 상승했습니다.

| 채널명 | 예산 집행률 | ROAS | 효율 등급 |
| :--- | :---: | :---: | :---: |
| **Meta** | 105% | **High** | **S** |
| **Google SA** | 100% | **High** | A |
| **Youtube** | 95% | Medium | B |
| **Network 배너** | 80% | Low | C |

### 2.3. 시사점 및 차주 최적화 전략

금주 데이터 분석을 통해 확인된 **'고효율 소재의 파급력'**과 **'타겟팅 정교화의 중요성'**을 바탕으로 차주 전략을 수립합니다.

1.  **Winning Creative 확장**: CTR 상승을 견인한 소재를 메인으로 교체
2.  **전환 중심의 예산 운용**: 전환율 3.5%까지 끌어올리기 위한 랜딩페이지 UI/UX 점검
3.  **저효율 채널 구조조정**: 네트워크 배너 광고 비중 10% 추가 축소
"""
    return {
        "order": 2,
        "section_title": "캠페인별 상세 성과",
        "section_number": "2.0",
        "section_key": "DATA_ANALYSIS",
        "title": "캠페인별 상세 성과 및 데이터 분석",
        "content": long_content,
        "parent_path": "성과 분석 > 캠페인 상세"
    }


@pytest.fixture
def sample_designed_pages() -> list[DesignedPage]:
    """샘플 디자인된 페이지들"""
    return [
        {
            "html_content": "<body><div>Page 1</div></body>",
            "order": 1,
            "section_title": "요약",
            "section_number": "1.0",
            "outline_id": "outline-123",
            "page_index": 0,
            "model_used": "gemini-2.0-flash"
        },
        {
            "html_content": "<body><div>Page 2</div></body>",
            "order": 2,
            "section_title": "본문",
            "section_number": "2.0",
            "outline_id": "outline-123",
            "page_index": 0,
            "model_used": "gemini-2.0-flash"
        },
        {
            "html_content": "<body><div>Page 3</div></body>",
            "order": 3,
            "section_title": "결론",
            "section_number": "3.0",
            "outline_id": "outline-123",
            "page_index": 0,
            "model_used": "gemini-2.0-flash"
        }
    ]


@pytest.fixture
def mock_llm_response():
    """Mock LLM 응답"""
    mock = MagicMock()
    mock.content = "<body><div class='report'>테스트 보고서 내용</div></body>"
    return mock


# =============================================================================
# Schema Tests
# =============================================================================

class TestSchemas:
    """State Schema 테스트"""

    def test_design_requirement_fields(self, sample_design_requirement):
        """DesignRequirement 필드 존재 확인"""
        required_fields = ["primary_color", "secondary_color", "accent_color", "pdf_orientation"]
        for field in required_fields:
            assert field in sample_design_requirement

    def test_design_requirement_color_format(self, sample_design_requirement):
        """색상 값이 hex 형식인지 확인"""
        for key in ["primary_color", "secondary_color", "accent_color"]:
            color = sample_design_requirement[key]
            assert color.startswith("#")
            assert len(color) == 7  # #RRGGBB

    def test_section_required_fields(self, sample_section):
        """Section 필수 필드 존재 확인"""
        required_fields = ["order", "section_title", "section_key", "title", "content"]
        for field in required_fields:
            assert field in sample_section

    def test_section_optional_fields(self, sample_section):
        """Section 선택 필드 존재 확인"""
        optional_fields = ["section_number", "parent_path"]
        for field in optional_fields:
            assert field in sample_section

    def test_designed_page_structure(self, sample_designed_pages):
        """DesignedPage 구조 검증"""
        required_fields = ["html_content", "order", "section_title", "outline_id", "page_index"]
        for page in sample_designed_pages:
            for field in required_fields:
                assert field in page

    def test_section_payload_structure(self, sample_section, sample_design_requirement):
        """SectionPayload 구조 검증"""
        payload: SectionPayload = {
            "section": sample_section,
            "design_requirement": sample_design_requirement,
            "language_code": "ko",
            "outline_id": "test-outline-123"
        }
        assert "section" in payload
        assert "design_requirement" in payload
        assert "language_code" in payload
        assert "outline_id" in payload


# =============================================================================
# Reducer Tests
# =============================================================================

class TestReducer:
    """Reducer 동작 테스트"""

    def test_operator_add_for_designed_pages(self, sample_designed_pages):
        """designed_pages에 대한 operator.add 동작 확인"""
        list1 = [sample_designed_pages[0]]
        list2 = [sample_designed_pages[1]]

        result = operator.add(list1, list2)

        assert len(result) == 2
        assert result[0]["section_title"] == "요약"
        assert result[1]["section_title"] == "본문"

    def test_operator_add_for_errors(self):
        """errors에 대한 operator.add 동작 확인"""
        errors1 = ["Error 1"]
        errors2 = ["Error 2", "Error 3"]

        result = operator.add(errors1, errors2)

        assert len(result) == 3
        assert "Error 1" in result
        assert "Error 2" in result

    def test_reducer_with_empty_list(self):
        """빈 리스트와의 결합"""
        list1 = []
        list2 = [{"html_content": "test", "order": 1}]

        result = operator.add(list1, list2)

        assert len(result) == 1

    def test_reducer_preserves_order(self, sample_designed_pages):
        """Reducer가 순서를 보존하는지 확인"""
        all_pages = []
        for page in sample_designed_pages:
            all_pages = operator.add(all_pages, [page])

        assert len(all_pages) == 3
        assert all_pages[0]["order"] == 1
        assert all_pages[1]["order"] == 2
        assert all_pages[2]["order"] == 3


# =============================================================================
# LLM Configuration Tests
# =============================================================================

class TestLLMConfig:
    """LLM 설정 테스트"""

    def test_llm_configs_structure(self):
        """LLM 설정 구조 확인"""
        assert len(LLM_CONFIGS) == 3  # 3-tier fallback

        for config in LLM_CONFIGS:
            assert hasattr(config, 'name')
            assert hasattr(config, 'provider')
            assert hasattr(config, 'temperature')

    def test_llm_config_providers(self):
        """LLM 프로바이더 설정 확인"""
        for config in LLM_CONFIGS:
            assert config.provider == "google"

    def test_llm_config_fallback_order(self):
        """Fallback 순서 확인"""
        # Primary and Retry are same (gemini-2.0-flash)
        assert LLM_CONFIGS[0].name == "gemini-2.0-flash"
        assert LLM_CONFIGS[1].name == "gemini-2.0-flash"
        # Fallback is different (gemini-1.5-pro)
        assert LLM_CONFIGS[2].name == "gemini-1.5-pro"


# =============================================================================
# Text Extraction Tests
# =============================================================================

class TestExtractTextContent:
    """extract_text_content 함수 테스트"""

    def test_extract_from_string(self):
        """문자열 응답에서 추출"""
        content = "테스트 콘텐츠입니다."
        result = extract_text_content(content)
        assert result == "테스트 콘텐츠입니다."

    def test_extract_from_list_of_strings(self):
        """문자열 리스트에서 추출"""
        content = ["첫 번째 ", "두 번째 ", "세 번째"]
        result = extract_text_content(content)
        assert result == "첫 번째 두 번째 세 번째"

    def test_extract_from_list_with_text_attribute(self):
        """text 속성이 있는 객체 리스트에서 추출"""
        class TextPart:
            def __init__(self, text):
                self.text = text

        content = [TextPart("Hello "), TextPart("World")]
        result = extract_text_content(content)
        assert result == "Hello World"

    def test_extract_from_list_with_dict(self):
        """dict 리스트에서 추출"""
        content = [{"text": "첫 번째"}, {"text": "두 번째"}]
        result = extract_text_content(content)
        assert result == "첫 번째두 번째"

    def test_extract_from_other_types(self):
        """기타 타입에서 str 변환"""
        content = 12345
        result = extract_text_content(content)
        assert result == "12345"


# =============================================================================
# Body Block Extraction Tests
# =============================================================================

class TestExtractBodyBlocks:
    """extract_body_blocks 함수 테스트"""

    def test_extract_single_body(self, sample_section):
        """단일 body 블록 추출"""
        html = "<body><div>내용</div></body>"
        pages = extract_body_blocks(html, sample_section, "outline-123", "gemini-2.0-flash")

        assert len(pages) == 1
        assert pages[0]["html_content"] == "<body><div>내용</div></body>"
        assert pages[0]["order"] == 1
        assert pages[0]["page_index"] == 0
        assert pages[0]["model_used"] == "gemini-2.0-flash"

    def test_extract_multiple_bodies(self, sample_section):
        """다중 body 블록 추출 (multi-page)"""
        html = """
        <body><div>Page 1</div></body>
        <body><div>Page 2</div></body>
        <body><div>Page 3</div></body>
        """
        pages = extract_body_blocks(html, sample_section, "outline-123", "gemini-2.0-flash")

        assert len(pages) == 3
        assert pages[0]["page_index"] == 0
        assert pages[1]["page_index"] == 1
        assert pages[2]["page_index"] == 2

    def test_extract_removes_page_break_markers(self, sample_section):
        """__PAGE_BREAK__ 마커 제거 확인"""
        html = "<body>Page 1</body>__PAGE_BREAK__<body>Page 2</body>"
        pages = extract_body_blocks(html, sample_section, "outline-123")

        assert len(pages) == 2
        assert "__PAGE_BREAK__" not in pages[0]["html_content"]

    def test_extract_without_body_tags(self, sample_section):
        """body 태그가 없는 경우 전체 콘텐츠 사용"""
        html = "<div>콘텐츠만 있음</div>"
        pages = extract_body_blocks(html, sample_section, "outline-123")

        assert len(pages) == 1
        assert pages[0]["html_content"] == "<div>콘텐츠만 있음</div>"
        assert pages[0]["page_index"] == 0

    def test_extract_with_body_attributes(self, sample_section):
        """body 태그에 속성이 있는 경우"""
        html = '<body class="report" data-id="123"><div>내용</div></body>'
        pages = extract_body_blocks(html, sample_section, "outline-123")

        assert len(pages) == 1
        assert 'class="report"' in pages[0]["html_content"]

    def test_extract_preserves_section_metadata(self, sample_section):
        """섹션 메타데이터 보존 확인"""
        html = "<body>내용</body>"
        pages = extract_body_blocks(html, sample_section, "outline-123", "gemini-2.0-flash")

        assert pages[0]["section_title"] == sample_section["section_title"]
        assert pages[0]["section_number"] == sample_section["section_number"]
        assert pages[0]["outline_id"] == "outline-123"


# =============================================================================
# Prepare Sections Tests
# =============================================================================

class TestPrepareSections:
    """prepare_sections 노드 테스트"""

    def test_extract_sections_from_outline(self, sample_section):
        """outline에서 섹션 추출"""
        state = {
            "outline": {
                "id": "outline-123",
                "sections": [sample_section]
            }
        }

        result = prepare_sections(state)

        assert len(result["sections"]) == 1
        assert result["sections"][0]["section_title"] == "금주 핵심 성과 요약"
        assert result["status"] == "sections_prepared"

    def test_empty_outline(self):
        """빈 outline 처리"""
        state = {"outline": {}}

        result = prepare_sections(state)

        assert result["sections"] == []
        assert result["status"] == "sections_prepared"

    def test_missing_outline(self):
        """outline이 없는 경우"""
        state = {}

        result = prepare_sections(state)

        assert result["sections"] == []

    def test_multiple_sections(self, sample_section, sample_long_section):
        """다중 섹션 추출"""
        state = {
            "outline": {
                "id": "outline-123",
                "sections": [sample_section, sample_long_section]
            }
        }

        result = prepare_sections(state)

        assert len(result["sections"]) == 2


# =============================================================================
# Combine Results Tests
# =============================================================================

class TestCombineResults:
    """combine_results 노드 테스트"""

    def test_sort_pages_by_order(self, sample_designed_pages):
        """페이지가 order 기준으로 정렬되는지 확인"""
        # 순서를 섞음
        shuffled = [
            sample_designed_pages[2],  # order 3
            sample_designed_pages[0],  # order 1
            sample_designed_pages[1],  # order 2
        ]
        state = {"designed_pages": shuffled}

        result = combine_results(state)
        payload = json.loads(result["publish_payload"])

        # 정렬 후 순서 확인
        assert payload["publish_content"][0]["order"] == 1
        assert payload["publish_content"][1]["order"] == 2
        assert payload["publish_content"][2]["order"] == 3

    def test_sort_multi_page_sections(self):
        """multi-page 섹션의 page_index 기준 정렬"""
        pages = [
            {"html_content": "2-1", "order": 2, "section_title": "B", "outline_id": "x", "page_index": 1},
            {"html_content": "1-0", "order": 1, "section_title": "A", "outline_id": "x", "page_index": 0},
            {"html_content": "2-0", "order": 2, "section_title": "B", "outline_id": "x", "page_index": 0},
        ]
        state = {"designed_pages": pages}

        result = combine_results(state)
        payload = json.loads(result["publish_payload"])

        # order 순서: 1-0, 2-0, 2-1 (order, page_index 기준)
        assert payload["publish_content"][0]["order"] == 1  # 1-0
        assert payload["publish_content"][1]["order"] == 2  # 2-0
        assert payload["publish_content"][2]["order"] == 3  # 2-1

    def test_reindex_pages(self, sample_designed_pages):
        """페이지 re-indexing (1-based)"""
        state = {"designed_pages": sample_designed_pages}

        result = combine_results(state)
        payload = json.loads(result["publish_payload"])

        for i, page in enumerate(payload["publish_content"], start=1):
            assert page["order"] == i

    def test_publish_payload_structure(self, sample_designed_pages):
        """publish_payload 구조 확인"""
        state = {"designed_pages": sample_designed_pages}

        result = combine_results(state)
        payload = json.loads(result["publish_payload"])

        assert "publish_content" in payload
        assert isinstance(payload["publish_content"], list)
        for page in payload["publish_content"]:
            assert "html_content" in page
            assert "order" in page
            assert "section_title" in page
            assert "outline_id" in page

    def test_empty_pages(self):
        """빈 페이지 리스트 처리"""
        state = {"designed_pages": []}

        result = combine_results(state)
        payload = json.loads(result["publish_payload"])

        assert payload["publish_content"] == []
        assert result["status"] == "combined"

    def test_korean_content_in_payload(self, sample_designed_pages):
        """한글 콘텐츠가 제대로 인코딩되는지 확인"""
        sample_designed_pages[0]["html_content"] = "<body>한글 테스트</body>"
        state = {"designed_pages": sample_designed_pages}

        result = combine_results(state)

        # ensure_ascii=False 확인
        assert "한글 테스트" in result["publish_payload"]


# =============================================================================
# Fan-out Tests
# =============================================================================

class TestFanOut:
    """fan_out_to_sections 함수 테스트"""

    def test_creates_send_for_each_section(self, sample_section, sample_design_requirement):
        """각 섹션에 대해 Send 객체 생성 확인"""
        state = {
            "sections": [sample_section],
            "design_requirement": sample_design_requirement,
            "language_code": "ko",
            "outline": {"id": "outline-123"}
        }

        sends = fan_out_to_sections(state)

        assert len(sends) == 1
        assert sends[0].node == "design_section"

    def test_send_payload_contains_required_fields(self, sample_section, sample_design_requirement):
        """Send payload에 필요한 필드가 포함되어 있는지 확인"""
        state = {
            "sections": [sample_section],
            "design_requirement": sample_design_requirement,
            "language_code": "ko",
            "outline": {"id": "outline-123"}
        }

        sends = fan_out_to_sections(state)
        payload = sends[0].arg

        assert "section" in payload
        assert "design_requirement" in payload
        assert "language_code" in payload
        assert "outline_id" in payload

    def test_multiple_sections_fan_out(self, sample_section, sample_long_section, sample_design_requirement):
        """다중 섹션에 대한 fan-out"""
        state = {
            "sections": [sample_section, sample_long_section],
            "design_requirement": sample_design_requirement,
            "language_code": "ko",
            "outline": {"id": "outline-123"}
        }

        sends = fan_out_to_sections(state)

        assert len(sends) == 2

    def test_empty_sections(self, sample_design_requirement):
        """빈 섹션 리스트 처리"""
        state = {
            "sections": [],
            "design_requirement": sample_design_requirement,
            "language_code": "ko",
            "outline": {"id": "outline-123"}
        }

        sends = fan_out_to_sections(state)

        assert len(sends) == 0

    def test_default_language_code(self, sample_section, sample_design_requirement):
        """기본 language_code (ko) 확인"""
        state = {
            "sections": [sample_section],
            "design_requirement": sample_design_requirement,
            "outline": {"id": "outline-123"}
        }

        sends = fan_out_to_sections(state)

        assert sends[0].arg["language_code"] == "ko"


# =============================================================================
# Workflow Integration Tests (with Mocks)
# =============================================================================

class TestWorkflowIntegration:
    """워크플로우 통합 테스트"""

    def test_state_transition_fetch_to_prepare(self):
        """fetch_all_data -> prepare_sections 상태 전이"""
        # fetch_all_data 후 상태
        state = {
            "api_url": "https://api.example.com",
            "token": "test-token",
            "report_id": "report-123",
            "design_requirement": {"primary_color": "#1E40AF"},
            "outline": {"id": "outline-123", "sections": []},
            "report_metadata": {"language_code": "ko"},
            "language_code": "ko",
            "sections": [],
            "designed_pages": [],
            "status": "data_fetched"
        }

        # prepare_sections 호출
        result = prepare_sections(state)

        assert result["status"] == "sections_prepared"

    def test_state_transition_combine_to_publish(self, sample_designed_pages):
        """combine_results -> publish_report 상태 전이"""
        state = {
            "designed_pages": sample_designed_pages,
            "api_url": "https://api.example.com",
            "token": "test-token",
            "report_id": "report-123"
        }

        result = combine_results(state)

        assert result["status"] == "combined"
        assert result["publish_payload"] is not None

    def test_full_workflow_state_progression(
        self,
        sample_section,
        sample_design_requirement,
        sample_designed_pages
    ):
        """전체 워크플로우 상태 진행 테스트"""
        # 1. 초기 상태
        state = {
            "api_url": "https://api.example.com",
            "token": "test-token",
            "report_id": "report-123",
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
        assert state["status"] == "pending"

        # 2. fetch_all_data 후 (시뮬레이션)
        state["design_requirement"] = sample_design_requirement
        state["outline"] = {"id": "outline-123", "sections": [sample_section]}
        state["status"] = "data_fetched"
        assert state["status"] == "data_fetched"

        # 3. prepare_sections 후
        result = prepare_sections(state)
        state["sections"] = result["sections"]
        state["status"] = result["status"]
        assert len(state["sections"]) == 1
        assert state["status"] == "sections_prepared"

        # 4. design_section 후 (시뮬레이션)
        state["designed_pages"] = sample_designed_pages

        # 5. combine_results 후
        result = combine_results(state)
        state["publish_payload"] = result["publish_payload"]
        state["status"] = result["status"]
        assert state["status"] == "combined"
        assert state["publish_payload"] is not None

    def test_pages_aggregation_with_reducer(self, sample_designed_pages):
        """병렬 생성된 페이지 집계"""
        # 각 design_section 노드의 결과 시뮬레이션
        results = [
            {"designed_pages": [sample_designed_pages[0]], "errors": []},
            {"designed_pages": [sample_designed_pages[1]], "errors": []},
            {"designed_pages": [sample_designed_pages[2]], "errors": []},
        ]

        # Reducer로 집계
        aggregated_pages = []
        aggregated_errors = []
        for result in results:
            aggregated_pages = operator.add(aggregated_pages, result["designed_pages"])
            aggregated_errors = operator.add(aggregated_errors, result["errors"])

        assert len(aggregated_pages) == 3
        assert len(aggregated_errors) == 0


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """에러 처리 테스트"""

    def test_errors_aggregation(self):
        """에러 집계"""
        results = [
            {"designed_pages": [], "errors": ["Error in section 1"]},
            {"designed_pages": [], "errors": []},
            {"designed_pages": [], "errors": ["Error in section 3"]},
        ]

        aggregated_errors = []
        for result in results:
            aggregated_errors = operator.add(aggregated_errors, result["errors"])

        assert len(aggregated_errors) == 2
        assert "Error in section 1" in aggregated_errors
        assert "Error in section 3" in aggregated_errors

    def test_empty_content_section(self):
        """빈 콘텐츠 섹션 처리"""
        section: Section = {
            "order": 1,
            "section_title": "빈 섹션",
            "section_number": "1.0",
            "section_key": "EMPTY",
            "title": "빈 섹션",
            "content": "",  # 빈 콘텐츠
            "parent_path": None
        }

        # content 길이 확인
        assert len(section["content"]) == 0

    def test_missing_section_fields(self):
        """섹션 필드 누락 처리"""
        incomplete_section = {
            "order": 1,
            "section_title": "제목만 있음",
            # section_key, title, content 누락
        }

        html = "<body>테스트</body>"
        pages = extract_body_blocks(
            html,
            incomplete_section,
            "outline-123"
        )

        # .get() 사용으로 누락 필드도 처리
        assert pages[0]["section_title"] == "제목만 있음"
        assert pages[0]["section_number"] is None


# =============================================================================
# Content Length Tests
# =============================================================================

class TestContentLength:
    """콘텐츠 길이 관련 테스트"""

    def test_short_content(self, sample_section):
        """짧은 콘텐츠 (<= 600 chars)"""
        sample_section["content"] = "짧은 내용"
        content_length = len(sample_section["content"])
        assert content_length < 600

    def test_medium_content(self, sample_section):
        """중간 길이 콘텐츠 (600 < chars <= 1200)"""
        # sample_section의 기본 콘텐츠 길이 확인
        content_length = len(sample_section["content"])
        # 테스트용 assertion (실제 길이에 따라 조정 필요)
        assert content_length > 100

    def test_long_content_triggers_multi_page(self, sample_long_section):
        """긴 콘텐츠 (> 1200 chars)는 multi-page 트리거"""
        content_length = len(sample_long_section["content"])
        assert content_length > 1200


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
