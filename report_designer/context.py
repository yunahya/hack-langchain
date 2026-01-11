"""
비즈니스 보고서 디자이너 워크플로우의 설정(Configuration) 컨텍스트 모듈.

이 모듈은 LangGraph의 RunnableConfig를 통해 런타임에 워크플로우 동작을
커스터마이징하는 데 사용되는 Configuration 클래스를 정의합니다.
"""

from dataclasses import dataclass, field
from typing import Annotated

from langchain_core.runnables import RunnableConfig


@dataclass(kw_only=True)
class Configuration:
    """
    보고서 디자이너 워크플로우의 런타임 설정.

    이 설정은 RunnableConfig를 통해 전달되며, 그래프 구조를 수정하지 않고도
    각 실행마다 커스터마이징할 수 있습니다.

    Attributes:
        model: "provider/model_name" 형식의 기본 LLM 모델 식별자.
               지원 프로바이더: google.
               기본값: "google/gemini-2.0-flash"
        fallback_model: 기본 모델 실패 시 사용할 폴백 LLM 모델.
                        기본값: "google/gemini-1.5-pro"
        temperature: 디자인 생성 시 사용할 Temperature.
                     기본값: 1.0
        max_retries: 모델당 최대 재시도 횟수.
                     기본값: 3

    사용 예시:
        >>> config = {"configurable": {
        ...     "model": "google/gemini-2.0-flash",
        ...     "fallback_model": "google/gemini-1.5-pro",
        ...     "temperature": 0.8,
        ... }}
        >>> result = graph.invoke(state, config=config)
    """

    model: str = field(
        default="google/gemini-2.0-flash",
        metadata={
            "description": (
                "'provider/model_name' 형식의 기본 LLM 모델 식별자. "
                "지원 프로바이더: google."
            ),
            "examples": [
                "google/gemini-2.0-flash",
                "google/gemini-1.5-pro",
            ],
        },
    )

    fallback_model: str = field(
        default="google/gemini-1.5-pro",
        metadata={
            "description": (
                "기본 모델 실패 시 사용할 폴백 LLM 모델. "
                "3단계 폴백 체인에서 사용됩니다."
            ),
        },
    )

    temperature: float = field(
        default=1.0,
        metadata={
            "description": (
                "디자인 생성 시 사용할 Temperature. "
                "높은 값(0.8-1.0)은 더 창의적인 디자인을 생성합니다."
            ),
            "minimum": 0.0,
            "maximum": 2.0,
        },
    )

    max_retries: int = field(
        default=3,
        metadata={
            "description": "모델당 최대 재시도 횟수.",
            "minimum": 1,
            "maximum": 5,
        },
    )

    @classmethod
    def from_runnable_config(
        cls,
        config: RunnableConfig | None = None,
    ) -> "Configuration":
        """
        RunnableConfig에서 Configuration을 추출합니다.

        Args:
            config: 'configurable' 키를 포함한 LangGraph RunnableConfig.

        Returns:
            config의 값 또는 기본값으로 생성된 Configuration 인스턴스.

        사용 예시:
            >>> config = {"configurable": {"model": "google/gemini-1.5-pro"}}
            >>> cfg = Configuration.from_runnable_config(config)
            >>> cfg.model
            'google/gemini-1.5-pro'
        """
        if config is None:
            return cls()

        configurable = config.get("configurable", {})

        return cls(
            model=configurable.get("model", cls.model),
            fallback_model=configurable.get("fallback_model", cls.fallback_model),
            temperature=configurable.get("temperature", cls.temperature),
            max_retries=configurable.get("max_retries", cls.max_retries),
        )


# 설정용 타입 별칭
ConfigurableFields = Annotated[Configuration, "보고서 디자인을 위한 설정"]
