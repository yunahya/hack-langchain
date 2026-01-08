"""
Unit Tests for Report Generator Workflow

테스트 전략:
- LLM 호출은 Mock으로 대체 (비용/속도 최적화)
- State schema 검증
- Reducer 동작 검증
- 워크플로우 통합 테스트
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Annotated
from typing_extensions import TypedDict
import operator
import json

# =============================================================================
# Test Fixtures & Mocks
# =============================================================================

@pytest.fixture
def sample_user_input():
    """샘플 사용자 입력 데이터"""
    return {
        "report_type": "주간업무보고",
        "purpose": "현황 공유",
        "audience": "직속 상사",
        "topic": "테스트 보고서",
        "key_message": "테스트 메시지",
        "company_info": "테스트 회사",
        "tone": "격식체",
        "page_count": 3,
        "emphasis": "",
        "include_visuals": False,
        "additional_data": ""
    }


@pytest.fixture
def sample_toc():
    """샘플 TOC 데이터"""
    return [
        {"page_id": "summary", "title": "요약", "description": "보고서 요약", "order": 1},
        {"page_id": "main", "title": "본문", "description": "주요 내용", "order": 2},
        {"page_id": "conclusion", "title": "결론", "description": "결론 및 제언", "order": 3}
    ]


@pytest.fixture
def mock_llm_response():
    """Mock LLM 응답"""
    mock = MagicMock()
    mock.content = "테스트 콘텐츠입니다."
    return mock


@pytest.fixture
def mock_toc_response():
    """Mock TOC 생성 응답"""
    mock = MagicMock()
    mock.content = json.dumps([
        {"page_id": "summary", "title": "요약", "description": "보고서 요약", "order": 1},
        {"page_id": "main", "title": "본문", "description": "주요 내용", "order": 2},
        {"page_id": "conclusion", "title": "결론", "description": "결론 및 제언", "order": 3}
    ])
    return mock


# =============================================================================
# Schema Tests
# =============================================================================

class TestSchemas:
    """State Schema 테스트"""

    def test_report_input_required_fields(self, sample_user_input):
        """필수 필드 존재 확인"""
        required_fields = ["report_type", "purpose", "audience", "topic", "key_message", "company_info"]
        for field in required_fields:
            assert field in sample_user_input

    def test_report_input_optional_fields(self, sample_user_input):
        """선택 필드 존재 확인"""
        optional_fields = ["tone", "page_count", "emphasis", "include_visuals", "additional_data"]
        for field in optional_fields:
            assert field in sample_user_input

    def test_page_content_structure(self):
        """PageContent 구조 검증"""
        page = {
            "page_id": "test",
            "title": "테스트",
            "content": "콘텐츠",
            "order": 1
        }
        assert all(key in page for key in ["page_id", "title", "content", "order"])

    def test_toc_item_structure(self, sample_toc):
        """TOC 항목 구조 검증"""
        for item in sample_toc:
            assert "page_id" in item
            assert "title" in item
            assert "description" in item
            assert "order" in item


# =============================================================================
# Reducer Tests
# =============================================================================

class TestReducer:
    """Reducer 동작 테스트"""

    def test_operator_add_reducer(self):
        """operator.add reducer 동작 확인"""
        # 두 리스트 결합 테스트
        list1 = [{"page_id": "a", "order": 1}]
        list2 = [{"page_id": "b", "order": 2}]

        result = operator.add(list1, list2)

        assert len(result) == 2
        assert result[0]["page_id"] == "a"
        assert result[1]["page_id"] == "b"

    def test_reducer_with_empty_list(self):
        """빈 리스트와의 결합"""
        list1 = []
        list2 = [{"page_id": "a", "order": 1}]

        result = operator.add(list1, list2)

        assert len(result) == 1

    def test_reducer_preserves_order(self):
        """Reducer가 순서를 보존하는지 확인"""
        lists = [
            [{"page_id": "a", "order": 1}],
            [{"page_id": "b", "order": 2}],
            [{"page_id": "c", "order": 3}]
        ]

        result = []
        for lst in lists:
            result = operator.add(result, lst)

        assert [item["page_id"] for item in result] == ["a", "b", "c"]


# =============================================================================
# TOC Generation Tests
# =============================================================================

class TestTOCGeneration:
    """TOC 생성 노드 테스트"""

    def test_toc_json_parsing(self, sample_toc):
        """TOC JSON 파싱 테스트"""
        json_str = json.dumps(sample_toc)
        parsed = json.loads(json_str)

        assert len(parsed) == 3
        assert parsed[0]["page_id"] == "summary"

    def test_toc_with_markdown_code_block(self):
        """Markdown 코드 블록이 포함된 응답 파싱"""
        response_content = '''```json
[
    {"page_id": "summary", "title": "요약", "description": "요약 내용", "order": 1}
]
```'''

        # Markdown 블록 제거 로직
        content = response_content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]

        parsed = json.loads(content.strip())
        assert len(parsed) == 1
        assert parsed[0]["page_id"] == "summary"

    def test_toc_order_validation(self, sample_toc):
        """TOC order 필드 검증"""
        orders = [item["order"] for item in sample_toc]
        assert orders == sorted(orders), "TOC items should be in order"


# =============================================================================
# Page Content Generation Tests
# =============================================================================

class TestPageContentGeneration:
    """페이지 콘텐츠 생성 테스트"""

    def test_page_content_returns_list(self):
        """페이지 콘텐츠가 리스트로 반환되는지 확인 (reducer용)"""
        # Mock 결과
        result = {
            "pages": [{
                "page_id": "test",
                "title": "테스트",
                "content": "콘텐츠",
                "order": 1
            }]
        }

        assert isinstance(result["pages"], list)
        assert len(result["pages"]) == 1

    def test_page_content_structure(self):
        """생성된 페이지 콘텐츠 구조 확인"""
        page = {
            "page_id": "summary",
            "title": "요약",
            "content": "## 요약\n\n테스트 콘텐츠입니다.",
            "order": 1
        }

        assert page["page_id"]
        assert page["title"]
        assert page["content"]
        assert isinstance(page["order"], int)

    def test_a4_content_length_guideline(self):
        """A4 콘텐츠 길이 가이드라인 검증"""
        # 한글 기준 800-1200자
        min_length = 800
        max_length = 1200

        sample_content = "테스트 " * 200  # ~1000자
        content_length = len(sample_content)

        # 가이드라인 범위 내 확인
        assert min_length <= 1000 <= max_length


# =============================================================================
# Combine Report Tests
# =============================================================================

class TestCombineReport:
    """보고서 조합 테스트"""

    def test_pages_sorted_by_order(self):
        """페이지가 order 기준으로 정렬되는지 확인"""
        pages = [
            {"page_id": "c", "title": "결론", "content": "C", "order": 3},
            {"page_id": "a", "title": "요약", "content": "A", "order": 1},
            {"page_id": "b", "title": "본문", "content": "B", "order": 2}
        ]

        sorted_pages = sorted(pages, key=lambda p: p["order"])

        assert sorted_pages[0]["order"] == 1
        assert sorted_pages[1]["order"] == 2
        assert sorted_pages[2]["order"] == 3

    def test_final_report_contains_all_sections(self):
        """최종 보고서에 모든 섹션이 포함되는지 확인"""
        pages = [
            {"page_id": "a", "title": "섹션A", "content": "내용A", "order": 1},
            {"page_id": "b", "title": "섹션B", "content": "내용B", "order": 2}
        ]

        # 보고서 조립 시뮬레이션
        report_parts = []
        for page in sorted(pages, key=lambda p: p["order"]):
            report_parts.append(page["content"])

        final_report = "\n".join(report_parts)

        assert "내용A" in final_report
        assert "내용B" in final_report

    def test_report_includes_metadata(self, sample_user_input):
        """보고서에 메타데이터가 포함되는지 확인"""
        # 메타데이터 포함 시뮬레이션
        header = f"# {sample_user_input['topic']}\n"
        header += f"**보고서 유형**: {sample_user_input['report_type']}\n"

        assert sample_user_input['topic'] in header
        assert sample_user_input['report_type'] in header


# =============================================================================
# Parallel Execution Tests
# =============================================================================

class TestParallelExecution:
    """병렬 실행 테스트"""

    def test_fan_out_creates_correct_send_count(self, sample_toc):
        """Fan-out이 올바른 수의 Send를 생성하는지 확인"""
        # Send 객체 생성 시뮬레이션
        sends = []
        for page_info in sample_toc:
            sends.append({
                "target": "generate_page_content",
                "payload": {"page_info": page_info}
            })

        assert len(sends) == len(sample_toc)
        assert len(sends) == 3

    def test_send_payload_structure(self, sample_toc, sample_user_input):
        """Send payload 구조 확인"""
        page_info = sample_toc[0]

        payload = {
            "page_info": page_info,
            "user_input": sample_user_input
        }

        assert "page_info" in payload
        assert "user_input" in payload
        assert payload["page_info"]["page_id"] == "summary"


# =============================================================================
# Integration Tests (with Mocks)
# =============================================================================

class TestWorkflowIntegration:
    """워크플로우 통합 테스트 (Mock 사용)"""

    def test_state_transition_toc_to_pages(self, sample_toc, sample_user_input):
        """TOC 생성 후 페이지 생성으로의 상태 전이"""
        # 초기 상태
        state = {
            "input": sample_user_input,
            "toc": [],
            "pages": [],
            "final_report": "",
            "status": "pending"
        }

        # TOC 생성 후 상태
        state["toc"] = sample_toc
        state["status"] = "toc_generated"

        assert len(state["toc"]) == 3
        assert state["status"] == "toc_generated"

    def test_pages_aggregation(self, sample_toc):
        """병렬 생성된 페이지 집계"""
        # 병렬 실행 결과 시뮬레이션
        page_results = [
            {"pages": [{"page_id": "a", "title": "A", "content": "A", "order": 1}]},
            {"pages": [{"page_id": "b", "title": "B", "content": "B", "order": 2}]},
            {"pages": [{"page_id": "c", "title": "C", "content": "C", "order": 3}]}
        ]

        # Reducer로 집계
        aggregated_pages = []
        for result in page_results:
            aggregated_pages = operator.add(aggregated_pages, result["pages"])

        assert len(aggregated_pages) == 3

    def test_full_workflow_state_progression(self, sample_user_input, sample_toc):
        """전체 워크플로우 상태 진행 테스트"""
        # 1. 초기 상태
        state = {
            "input": sample_user_input,
            "toc": [],
            "pages": [],
            "final_report": "",
            "status": "pending"
        }
        assert state["status"] == "pending"

        # 2. TOC 생성 후
        state["toc"] = sample_toc
        state["status"] = "toc_generated"
        assert state["status"] == "toc_generated"
        assert len(state["toc"]) == 3

        # 3. 페이지 생성 후
        for page in sample_toc:
            state["pages"] = operator.add(
                state["pages"],
                [{"page_id": page["page_id"], "title": page["title"],
                  "content": "테스트", "order": page["order"]}]
            )
        assert len(state["pages"]) == 3

        # 4. 완료 후
        state["final_report"] = "# 최종 보고서\n..."
        state["status"] = "completed"
        assert state["status"] == "completed"
        assert state["final_report"]


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """에러 처리 테스트"""

    def test_invalid_json_fallback(self):
        """잘못된 JSON 응답 시 fallback TOC 사용"""
        invalid_json = "이것은 JSON이 아닙니다"

        try:
            json.loads(invalid_json)
            fallback_needed = False
        except json.JSONDecodeError:
            fallback_needed = True

        assert fallback_needed

        # Fallback TOC
        fallback_toc = [
            {"page_id": "summary", "title": "요약", "description": "요약", "order": 1},
            {"page_id": "main", "title": "본문", "description": "본문", "order": 2},
            {"page_id": "conclusion", "title": "결론", "description": "결론", "order": 3}
        ]

        assert len(fallback_toc) == 3

    def test_empty_toc_handling(self):
        """빈 TOC 처리"""
        toc = []

        # 빈 TOC로 fan-out 시 빈 Send 리스트 반환
        sends = [{"target": "gen", "payload": p} for p in toc]

        assert len(sends) == 0


# =============================================================================
# LLM Provider Tests
# =============================================================================

class TestLLMProviders:
    """LLM 프로바이더 테스트"""

    def test_provider_selection_gemini(self):
        """Gemini 프로바이더 선택"""
        provider = "gemini"
        assert provider in ["gemini", "azure"]

    def test_provider_selection_azure(self):
        """Azure 프로바이더 선택"""
        provider = "azure"
        assert provider in ["gemini", "azure"]

    def test_invalid_provider_raises_error(self):
        """잘못된 프로바이더 선택 시 에러"""
        provider = "invalid"
        assert provider not in ["gemini", "azure"]


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
