# hack-langchain

LangGraph 기반 비즈니스 워크플로우 모음

- **Report Generator**: 비즈니스 보고서 자동 생성 (병렬 페이지 생성)
- **HTML Page Modifier**: AI 기반 HTML 페이지 수정
- **React Agent Template**: 도구 호출 에이전트 템플릿

---

## Quick Start

### LangGraph Studio 실행 (권장)

```bash
# 의존성 설치
uv sync

# LangGraph Studio 실행
langgraph dev
```

브라우저에서 `http://localhost:8123` 접속

### CLI 실행

```bash
# Report Generator
python -m report_generator_langgraph.graph

# HTML Page Modifier
python -m html_page_modifier_langgraph.graph
```

---

## 프로젝트 구조

```
hack-langchain/
├── report_generator_langgraph/     # 비즈니스 보고서 생성 워크플로우
├── html_page_modifier_langgraph/   # HTML 페이지 수정 워크플로우
├── langgraph-template/             # React Agent 템플릿
├── notebooks/                      # Jupyter 노트북 (프로토타입)
├── langgraph.json                  # LangGraph Studio 설정
├── pyproject.toml                  # 프로젝트 설정 (uv/pip)
└── .env                            # 환경 변수 (API 키)
```

---

## 1. Report Generator (`report_generator_langgraph/`)

### 목적
비즈니스 보고서를 자동으로 생성합니다. 보고서 유형, 목적, 대상에 맞게 목차(TOC)를 동적으로 생성하고, 각 페이지를 병렬로 생성합니다.

### 워크플로우

```
START → generate_toc → [fan_out/Send()] → generate_page_content (×N 병렬) → combine_report → END
```

| 노드 | 설명 |
|------|------|
| `generate_toc` | 입력 정보 기반 목차(TOC) 생성 |
| `generate_page_content` | 개별 페이지 콘텐츠 생성 (Send API로 병렬 처리) |
| `combine_report` | 페이지들을 최종 마크다운 보고서로 조합 |

### 모듈 구조

| 파일 | 역할 |
|------|------|
| `__init__.py` | 패키지 exports (graph, state types, Configuration) |
| `state.py` | 상태 스키마 정의 (ReportInput, ReportState, PageContent, TocItem) |
| `graph.py` | LangGraph 워크플로우 정의 및 노드 함수 |
| `prompts.py` | LLM 프롬프트 템플릿 (TOC 생성, 페이지 생성) |
| `context.py` | 런타임 Configuration 클래스 |
| `utils.py` | 헬퍼 함수 (LLM 로딩, 콘텐츠 추출, JSON 파싱) |

### 인풋 스키마

#### 필수 인풋

| 필드 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `report_type` | str | 보고서 유형 | 주간업무보고, 기획안, 프로젝트 제안서 |
| `purpose` | str | 보고 목적 | 승인 요청, 현황 공유, 의사결정 요청 |
| `audience` | str | 보고 대상 | 직속 상사, 임원, 타부서 |
| `topic` | str | 주제/제목 | 마케팅팀 주간업무보고 |
| `key_message` | str | 핵심 메시지 | 캠페인 성과 공유 |
| `company_info` | str | 회사/팀 정보 | ABC 주식회사 마케팅팀 |

#### 선택 인풋

| 필드 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `tone` | str | 문체 | 격식체 |
| `page_count` | int | 페이지 수 | 3 |
| `emphasis` | str | 강조 포인트 | - |
| `include_visuals` | bool | 시각화 요소 포함 | False |
| `additional_data` | str | 추가 자료 | - |

### 사용 예시

```python
from report_generator_langgraph import graph, ReportState, ReportInput

user_input: ReportInput = {
    # 필수
    "report_type": "주간업무보고",
    "purpose": "현황 공유",
    "audience": "직속 상사",
    "topic": "마케팅팀 주간업무보고",
    "key_message": "캠페인 성과 공유",
    "company_info": "ABC 주식회사 마케팅팀",
    # 선택
    "page_count": 3,
    "include_visuals": True,
}

initial_state: ReportState = {
    "input": user_input,
    "toc": [],
    "pages": [],
    "final_report": "",
    "status": "pending",
}

result = graph.invoke(initial_state)
print(result["final_report"])
```

### 런타임 설정

```python
config = {"configurable": {
    "model": "google/gemini-2.0-flash",  # 또는 "azure_openai/gpt-4o"
    "toc_temperature": 0.3,
    "content_temperature": 0.8,
}}
result = graph.invoke(initial_state, config=config)
```

---

## 2. HTML Page Modifier (`html_page_modifier_langgraph/`)

### 목적
단일 HTML 페이지를 자연어 요청에 따라 수정합니다. 디자인, 레이아웃, 색상, 구조 변경을 지원합니다.

### 워크플로우

```
START → modify_page_html → END
```

| 노드 | 설명 |
|------|------|
| `modify_page_html` | 사용자 요청에 따라 HTML 수정 및 변경 요약 생성 |

### 모듈 구조

| 파일 | 역할 |
|------|------|
| `__init__.py` | 패키지 exports (graph, state types, Configuration) |
| `state.py` | 상태 스키마 정의 (PageModificationInput, PageModificationState) |
| `graph.py` | LangGraph 워크플로우 정의 및 노드 함수 |
| `prompts.py` | LLM 프롬프트 템플릿 (HTML 수정, 요약 생성) |
| `context.py` | 런타임 Configuration 클래스 |
| `utils.py` | 헬퍼 함수 (LLM 로딩, HTML/텍스트 추출) |

### 인풋 스키마

#### 필수 인풋

| 필드 | 타입 | 설명 |
|------|------|------|
| `html_content` | str | 수정할 HTML 콘텐츠 |
| `user_request` | str | 자연어 수정 요청 |
| `page_id` | str | 페이지 식별자 |
| `page_order` | int | 페이지 순서 |

#### 선택 인풋

| 필드 | 타입 | 설명 | 기본값 |
|------|------|------|--------|
| `preserve_structure` | bool | 구조 유지 여부 | True |
| `style_preference` | str | 스타일 방식 | "inline" |
| `additional_context` | str | 추가 컨텍스트 | - |

### 사용 예시

```python
from html_page_modifier_langgraph import graph, PageModificationState, PageModificationInput

user_input: PageModificationInput = {
    "html_content": "<div><h1>제목</h1><p>내용</p></div>",
    "user_request": "헤더 배경색을 파란색(#3498db)으로 변경해주세요",
    "page_id": "main_page",
    "page_order": 1,
}

initial_state: PageModificationState = {
    "input": user_input,
    "modified_html": "",
    "modification_summary": "",
    "status": "pending",
}

result = graph.invoke(initial_state)
print(result["modified_html"])
print(result["modification_summary"])
```

### 런타임 설정

```python
config = {"configurable": {
    "model": "google/gemini-2.0-flash",
    "temperature": 0.3,
    "style_preference": "inline",  # 또는 "internal"
}}
result = graph.invoke(initial_state, config=config)
```

---

## 3. React Agent Template (`langgraph-template/`)

### 목적
도구 호출(Tool Calling)을 지원하는 ReAct 에이전트 템플릿입니다. 사용자 질문에 대해 도구를 선택하고 실행하는 루프를 수행합니다.

### 워크플로우

```
START → call_model ←→ tools → END
           ↓
    (tool_calls 없으면 END)
```

| 노드 | 설명 |
|------|------|
| `call_model` | LLM 호출 및 도구 선택 결정 |
| `tools` | 선택된 도구 실행 (ToolNode) |

### 모듈 구조

| 파일 | 역할 |
|------|------|
| `__init__.py` | 패키지 exports (graph) |
| `state.py` | 상태 스키마 정의 (InputState, State) |
| `graph.py` | ReAct 에이전트 그래프 정의 |
| `context.py` | 런타임 Context 클래스 |
| `tools.py` | 사용 가능한 도구 정의 |
| `prompts.py` | 시스템 프롬프트 템플릿 |
| `utils.py` | 헬퍼 함수 (LLM 로딩) |

### 인풋 스키마

| 필드 | 타입 | 설명 |
|------|------|------|
| `messages` | list[AnyMessage] | 대화 메시지 히스토리 |

### 사용 예시

```python
from langgraph_template import graph

result = graph.invoke({
    "messages": [{"role": "user", "content": "What is the weather in Seoul?"}]
})
print(result["messages"][-1].content)
```

---

## 4. Notebooks (`notebooks/`)

프로토타입 및 실험용 Jupyter 노트북

| 파일 | 설명 |
|------|------|
| `report_generator.ipynb` | Report Generator 프로토타입 |
| `html_page_modifier.ipynb` | HTML Page Modifier 프로토타입 |

### 실행 방법

```bash
uv run jupyter notebook notebooks/report_generator.ipynb
```

---

## 환경 설정

### 의존성 설치

```bash
# uv 사용 (권장)
uv sync

# pip 사용
pip install -r requirements.txt
```

### 환경 변수 (.env)

```env
# Google Gemini (기본)
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-2.0-flash

# Azure OpenAI (선택)
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
OPENAI_API_VERSION=2024-08-01-preview

# OpenAI (선택)
OPENAI_API_KEY=your_openai_key
```

---

## 지원 LLM

| Provider | 모델 포맷 | 필수 환경 변수 |
|----------|-----------|----------------|
| Google Gemini | `google/gemini-2.0-flash` | `GOOGLE_API_KEY` |
| Azure OpenAI | `azure_openai/gpt-4o` | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` |
| OpenAI | `openai/gpt-4o` | `OPENAI_API_KEY` |

---

## 테스트

```bash
uv run pytest tests/ -v
```
