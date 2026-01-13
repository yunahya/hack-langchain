# LangGraph Workflows API

LangGraph 워크플로우를 REST API로 제공하는 FastAPI 서버

## 파일 구조

```
api/
├── main.py              # FastAPI 앱 엔트리포인트
├── config.py            # 환경설정 (CORS, 기본값)
├── models/              # Pydantic 요청/응답 모델
│   ├── common.py        # 공통 모델 (ErrorResponse)
│   ├── html_modifier.py # HTML 수정 API 모델
│   └── report_generator.py # 보고서 생성 API 모델
├── routers/             # API 엔드포인트
│   ├── html_modifier.py # POST /api/v1/html-modifier
│   └── report_generator.py # POST /api/v1/report-generator
└── services/
    └── workflow_runner.py # LangGraph 워크플로우 실행 헬퍼
```

## 실행 방법

### 1. 환경변수 설정

`.env` 파일에 LLM API 키 추가:

```env
GOOGLE_API_KEY=your_google_api_key
```

### 2. 서버 실행

```bash
# 개발 모드
uv run uvicorn api.main:app --reload --port 8000
```

### 3. API 문서 확인

http://localhost:8000/docs (Swagger UI)

---

## API 엔드포인트

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/html-modifier` | HTML 페이지 AI 수정 |
| POST | `/api/v1/report-generator` | 비즈니스 보고서 AI 생성 |

---

## Next.js에서 호출하기

### 환경변수 설정

```env
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### HTML Modifier 호출

```typescript
const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/html-modifier`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    html_content: '<h1>제목</h1>',
    user_request: '배경색을 파란색으로 변경해주세요',
    page_id: 'main',
    page_order: 1
  })
});

const { modified_html, modification_summary } = await response.json();
```

### Report Generator 호출

```typescript
const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/report-generator`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    report_type: '주간업무보고',
    purpose: '현황 공유',
    audience: '직속 상사',
    topic: '마케팅팀 주간업무보고',
    key_message: '캠페인 성과',
    company_info: 'ABC 주식회사'
  })
});

const { final_report, toc, pages } = await response.json();
```

---

## 요청/응답 스펙

### HTML Modifier

**Request:**
```json
{
  "html_content": "<h1>제목</h1>",
  "user_request": "배경색을 파란색으로",
  "page_id": "main",
  "page_order": 1
}
```

**Response:**
```json
{
  "modified_html": "<h1 style=\"background: blue;\">제목</h1>",
  "modification_summary": "배경색을 파란색으로 변경했습니다.",
  "status": "completed",
  "execution_time_ms": 1234
}
```

### Report Generator

**Request:**
```json
{
  "report_type": "주간업무보고",
  "purpose": "현황 공유",
  "audience": "직속 상사",
  "topic": "마케팅팀 주간업무보고",
  "key_message": "캠페인 성과",
  "company_info": "ABC 주식회사",
  "page_count": 3
}
```

**Response:**
```json
{
  "final_report": "# 마케팅팀 주간업무보고\n...",
  "toc": [{ "page_id": "summary", "title": "요약", "order": 1 }],
  "pages": [{ "page_id": "summary", "title": "요약", "content": "...", "order": 1 }],
  "status": "completed",
  "execution_time_ms": 5678
}
```

---

## 지원 LLM 모델

| Provider | 모델 형식 | 환경변수 |
|----------|----------|----------|
| Google Gemini | `google/gemini-2.0-flash` | `GOOGLE_API_KEY` |
| Azure OpenAI | `azure_openai/gpt-4o` | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` |
| OpenAI | `openai/gpt-4o` | `OPENAI_API_KEY` |

요청 시 `config.model` 파라미터로 모델 변경 가능:

```json
{
  "config": {
    "model": "openai/gpt-4o"
  }
}
```
