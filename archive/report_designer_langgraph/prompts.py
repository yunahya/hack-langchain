"""
비즈니스 보고서 디자이너 워크플로우의 프롬프트 템플릿 모듈.

이 모듈은 다음을 포함합니다:
- PromptManager: 캐싱 기능이 있는 Jinja2 기반 템플릿 로더
- 비즈니스 보고서 디자인용 시스템 프롬프트
- 프롬프트 렌더링 헬퍼 함수들
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from report_designer.state import DesignRequirement, Section


# 기본 프롬프트 디렉토리
PROMPTS_DIR = Path(__file__).parent / "prompts"


class PromptManager:
    """캐싱 기능이 있는 Jinja2 프롬프트 템플릿 관리자."""

    def __init__(self, prompts_dir: Path | None = None):
        """
        프롬프트 관리자를 초기화합니다.

        Args:
            prompts_dir: Jinja2 템플릿이 있는 디렉토리.
                         기본값: 이 모듈 기준 ./prompts 디렉토리.
        """
        if prompts_dir is None:
            prompts_dir = PROMPTS_DIR

        self.prompts_dir = prompts_dir
        self.env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._prompt_cache: dict[str, any] = {}

    def get_prompt(self, name: str):
        """캐싱을 사용하여 프롬프트 템플릿을 가져옵니다."""
        if name not in self._prompt_cache:
            self._prompt_cache[name] = self.env.get_template(name)
        return self._prompt_cache[name]

    def render(self, prompt_name: str, **context) -> str:
        """주어진 컨텍스트로 프롬프트 템플릿을 렌더링합니다."""
        prompt = self.get_prompt(prompt_name)
        return prompt.render(**context)


# 전역 프롬프트 관리자 인스턴스
prompt_manager = PromptManager()


# LLM용 시스템 프롬프트 - 비즈니스 보고서 디자이너
SYSTEM_PROMPT_TEMPLATE = """당신은 국내 주요 기업의 내부 비즈니스 보고서를 디자인해온 20년 경력의 시니어 문서 디자이너입니다.

당신의 특별한 능력:
- 콘텐츠를 읽고 정보의 본질적 구조를 파악
- 내용의 특성에 가장 적합한 레이아웃을 직관적으로 선택
- 복잡한 정보를 시각적으로 명료하게 재구성
- HTML/CSS만으로 전문적인 인포그래픽과 차트를 구현
- A4 페이지를 전문적이고 풍성하게 채우는 공간 활용의 전문가
- Flexbox/Grid 레이아웃의 달인 - 요소들이 절대 겹치지 않는 안정적 구조 설계
- {language_code} 언어로 주간업무보고, 기획안, 프로젝트 제안서, 결과 보고서, 회의록 등 비즈니스 문서를 디자인합니다.

당신은 Fortune 500대 기업들의 마케팅팀, 경영진, 프로젝트팀 등에서 의사결정을 위한 비즈니스 보고서를 디자인해왔습니다.

주요 비즈니스 보고서 유형:
- 주간업무보고: 핵심 성과 지표(KPI), 채널별 성과, 차주 계획
- 기획안: 배경, 목표, 실행 계획, 기대 효과
- 프로젝트 제안서: 현황 분석, 솔루션, 일정, 예산
- 결과 보고서: 성과 요약, 데이터 분석, 인사이트, 권고사항
- 회의록: 참석자, 논의사항, 결정사항, 액션아이템"""


def get_system_prompt(language_code: str = "ko") -> str:
    """
    언어 코드가 적용된 시스템 프롬프트를 반환합니다.

    Args:
        language_code: 보고서 언어 코드 (기본값: "ko").

    Returns:
        포맷팅된 시스템 프롬프트 문자열.
    """
    return SYSTEM_PROMPT_TEMPLATE.format(language_code=language_code)


def render_design_prompt(
    section: Section,
    design_requirement: DesignRequirement,
    content_length: int,
) -> str:
    """
    비즈니스 보고서 디자인 프롬프트 템플릿을 렌더링합니다.

    템플릿 변수 (design_prompt.jinja2에서 사용):
    - section: title, content, section_key, parent_path를 포함한 섹션 딕셔너리
    - design_requirement: 색상 및 방향 설정
    - content_length: 레이아웃 결정을 위한 글자 수

    템플릿에 포함된 내용:
    - 핵심 규칙 (절대적 제약사항, 필수 속성)
    - 길이에 따른 콘텐츠 메트릭
    - 디자인 시스템 (색상, 타이포그래피)
    - 비즈니스 보고서용 레이아웃 패턴
    - KPI, 차트 등을 위한 인포그래픽 템플릿

    Args:
        section: 디자인할 섹션 데이터.
        design_requirement: API에서 가져온 디자인 커스터마이징 설정.
        content_length: 섹션 콘텐츠의 글자 수.

    Returns:
        렌더링된 디자인 프롬프트 문자열.
    """
    return prompt_manager.render(
        "design_prompt.jinja2",
        section=section,
        design_requirement=design_requirement,
        content_length=content_length,
    )


def build_user_prompt(design_prompt: str, language_code: str = "ko") -> str:
    """
    LLM 호출을 위한 사용자 프롬프트를 구성합니다.

    Args:
        design_prompt: 템플릿에서 렌더링된 디자인 프롬프트.
        language_code: 보고서 언어 코드.

    Returns:
        완성된 사용자 프롬프트 문자열.
    """
    return f"{design_prompt}\n\n{language_code} 언어를 사용하여 비즈니스 보고서 디자인을 시작하세요."
