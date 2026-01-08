# hack-langchain

---

## 필수 인풋

**1. 보고서 기본 정보**
- 보고서 유형 (주간업무보고, 기획안, 프로젝트 제안서, 결과 보고서, 회의록 등)
- 보고 목적 (승인 요청, 현황 공유, 의사결정 요청, 아이디어 제안 등)
- 보고 대상 (직속 상사, 임원, 타부서, 외부 클라이언트 등)

**2. 핵심 내용**
- 주제/제목
- 담고 싶은 핵심 메시지나 키워드
- 관련 데이터나 자료 (파일 업로드 또는 텍스트 입력)

**3. 맥락 정보**
- 회사/팀 이름, 업종
- 프로젝트명
- 기존 보고서 양식이나 템플릿 (있다면 업로드)

---

## 선택 인풋 (퀄리티 향상용)


**4. 톤앤매너**
- 문체 (격식체/반말, 간결함/상세함)
- 분량 (1페이지, 3페이지 등)
- 강조하고 싶은 부분

**5. 디자인 선호**
- 색상 톤 (회사 CI 컬러, 또는 선호 색상)
- 출력 형식 (PPT, Word, PDF)5
- 시각화 요소 포함 여부 (차트, 표, 아이콘 등)

---

## 실제 UX 설계 팁

처음부터 많은 걸 물으면 사용자가 이탈할 수 있으니, **단계별로 나눠서** 받는 게 좋아요:

1단계: 보고서 유형 + 목적 + 대상 (3개만 빠르게)
2단계: 핵심 내용 입력
3단계: 세부 옵션 (선택사항으로)

이렇게 하면 "빨리 초안만 보고 싶은 사람"과 "꼼꼼하게 커스텀하고 싶은 사람" 둘 다 만족시킬 수 있어요.

---

혹시 특정 보고서 유형(예: 기획안, 주간보고 등)에 맞춰서 더 구체적인 인풋 구조를 잡아볼까요?

---

## 노트북 실행 방법

### 1. 의존성 설치

**uv 사용 (권장)**
```bash
# uv 설치 (없는 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 프로젝트 초기화 및 의존성 설치
uv sync

# 개발 의존성 포함
uv sync --all-extras
```

**pip 사용**
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일에 LLM API 키 설정:

```env
# Google Gemini (권장)
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-2.0-flash

# Azure OpenAI (선택)
AZURE_OPENAI_API_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
OPENAI_API_VERSION=2024-08-01-preview
```

### 3. 노트북 실행

```bash
# uv 사용
uv run jupyter notebook notebooks/report_generator.ipynb

# pip 사용
jupyter notebook notebooks/report_generator.ipynb
```

### 4. 테스트 실행

```bash
# uv 사용
uv run pytest tests/ -v

# pip 사용
pytest tests/ -v
```

---

## 워크플로우 구조

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│    START    │ --> │  TOC 생성   │ --> │ 페이지 생성 (×N) │ --> │  결과 조합  │ --> END
└─────────────┘     └─────────────┘     │    (병렬 처리)    │     └─────────────┘
                                        └─────────────────┘
```

### 주요 기능
- **TOC 동적 생성**: 보고서 유형/목적에 따라 적절한 섹션 자동 구성
- **병렬 페이지 생성**: LangGraph `Send` API로 각 페이지 동시 생성
- **A4 최적화**: 한 페이지당 800-1200자 (한글 기준) 콘텐츠 생성
- **LLM 선택**: Gemini / Azure OpenAI 런타임 선택 가능

---

## 프로젝트 구조

```
hack-langchain/
├── notebooks/
│   └── report_generator.ipynb   # 메인 구현 노트북
├── tests/
│   └── test_report_generator.py # 유닛 테스트
├── .env                         # 환경 변수 (API 키)
├── pyproject.toml               # 프로젝트 설정 (uv/pip)
├── requirements.txt             # 의존성 (pip용)
└── README.md
```# hack-langchain
