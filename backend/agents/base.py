"""Agent 공통 베이스."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.llm import LLMClient, resolve_for_agent


class BaseAgent(ABC):
    """모든 Agent 의 공통 인터페이스.

    각 Agent 는 run(context) 를 구현하며, context(dict)에서 필요한 입력을 읽고
    자신의 출력을 context 에 추가하여 반환한다. 오케스트레이터가 순서를 관리한다.

    LLM 사용: 각 Agent 는 llm_key 로 자신만의 프로바이더/모델을 배정받는다.
      - env AGENT_LLM_<KEY>=provider[:model]  (예: AGENT_LLM_INPUT=openai:gpt-5.4-mini)
      - 없으면 전역 LLM_PROVIDER/LLM_MODEL 을 따르고, 키가 없으면 규칙기반 동작
    """

    name: str = "base"
    llm_key: str = "BASE"           # AGENT_LLM_<llm_key> 환경변수와 매칭

    @abstractmethod
    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        ...

    def get_llm(self, explicit_only: bool = False) -> LLMClient | None:
        """이 Agent 에 배정된 LLM 클라이언트 (없으면 None → 규칙기반).

        explicit_only=True: AGENT_LLM_<KEY> 가 명시된 경우에만 반환.
        (파이프라인 지연을 피하기 위해, 보조 코멘트 성격의 LLM 호출은
        해당 Agent 에 프로바이더를 명시했을 때만 수행하도록 할 때 사용)
        """
        return resolve_for_agent(self.llm_key, explicit_only=explicit_only)

    def log(self, context: dict[str, Any], message: str) -> None:
        context.setdefault("trace", []).append({"agent": self.name, "message": message})
