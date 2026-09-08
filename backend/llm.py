"""멀티 프로바이더 LLM 클라이언트 (anthropic / openai / gemini).

각 Agent 는 서로 다른 프로바이더·모델을 사용할 수 있다:

  - 전역 기본:   LLM_PROVIDER=openai            (auto = 키 있는 첫 프로바이더)
  - 전역 모델:   LLM_MODEL=gpt-5.4-mini
  - Agent 별:    AGENT_LLM_INPUT=openai:gpt-5.4-mini
                 AGENT_LLM_EVALUATION=gemini:gemini-3.6-flash
                 AGENT_LLM_ACCOUNT=anthropic     (모델 생략 시 프로바이더 기본 모델)

API 키: ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY(GOOGLE_API_KEY)

SDK 대신 REST API(httpx)를 직접 호출하여 의존성을 최소화한다.
호출 실패는 LLMError 로 던지며, 각 Agent 는 이를 잡아 규칙기반으로 폴백한다.
"""
from __future__ import annotations

from dataclasses import dataclass

import os

import httpx

from backend import config

# 프로바이더별 기본 모델 (env 로 오버라이드 가능)
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-5",
    "openai": "gpt-5.4-mini",
    "gemini": "gemini-3.6-flash",
}

# LLM 호출 타임아웃 (초).
# Vercel 등 프록시 뒤에서 서빙할 때는 프록시 타임아웃(약 30초)보다 짧아야
# "느린 LLM → 프록시 502" 대신 규칙기반 폴백으로 제시간에 응답할 수 있다.
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "25"))
_TIMEOUT = httpx.Timeout(LLM_TIMEOUT_SECONDS, connect=10.0)


class LLMError(Exception):
    """LLM 호출 실패 (키 없음/HTTP 오류/응답 형식 오류)."""


def _api_key(provider: str) -> str:
    return {
        "anthropic": config.ANTHROPIC_API_KEY,
        "openai": config.OPENAI_API_KEY,
        "gemini": config.GEMINI_API_KEY,
    }.get(provider, "")


def available_providers() -> list[str]:
    """API 키가 설정된 프로바이더 목록 (auto 선택 우선순위 순)."""
    return [p for p in ("anthropic", "openai", "gemini") if _api_key(p)]


@dataclass
class LLMClient:
    provider: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"

    async def complete(self, prompt: str, system: str | None = None,
                       max_tokens: int = 1024) -> str:
        """단일 프롬프트 완성 호출. 실패 시 LLMError."""
        key = _api_key(self.provider)
        if not key:
            raise LLMError(f"{self.provider} API 키가 설정되지 않았습니다.")
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                if self.provider == "anthropic":
                    return await self._anthropic(client, key, prompt, system, max_tokens)
                if self.provider == "openai":
                    return await self._openai(client, key, prompt, system, max_tokens)
                if self.provider == "gemini":
                    return await self._gemini(client, key, prompt, system, max_tokens)
        except httpx.HTTPError as exc:
            raise LLMError(f"{self.label} HTTP 오류: {exc}") from exc
        raise LLMError(f"지원하지 않는 프로바이더: {self.provider}")

    async def _anthropic(self, client: httpx.AsyncClient, key: str,
                         prompt: str, system: str | None, max_tokens: int) -> str:
        body: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            json=body,
        )
        if r.status_code != 200:
            raise LLMError(f"{self.label} 응답 {r.status_code}: {r.text[:300]}")
        data = r.json()
        return "".join(c.get("text", "") for c in data.get("content", []))

    async def _openai(self, client: httpx.AsyncClient, key: str,
                      prompt: str, system: str | None, max_tokens: int) -> str:
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": self.model,
                "messages": messages,
                "max_completion_tokens": max_tokens,
            },
        )
        if r.status_code != 200:
            raise LLMError(f"{self.label} 응답 {r.status_code}: {r.text[:300]}")
        data = r.json()
        return data["choices"][0]["message"]["content"] or ""

    async def _gemini(self, client: httpx.AsyncClient, key: str,
                      prompt: str, system: str | None, max_tokens: int) -> str:
        body: dict = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        r = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            headers={"x-goog-api-key": key},
            json=body,
        )
        if r.status_code != 200:
            raise LLMError(f"{self.label} 응답 {r.status_code}: {r.text[:300]}")
        data = r.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"{self.label} 응답 형식 오류: {str(data)[:300]}") from exc
        return "".join(p.get("text", "") for p in parts)


def _parse_spec(spec: str) -> LLMClient | None:
    """'provider' 또는 'provider:model' 문자열을 LLMClient 로 변환."""
    if not spec or spec == "none":
        return None
    provider, _, model = spec.partition(":")
    provider = provider.strip().lower()
    if provider not in DEFAULT_MODELS:
        return None
    return LLMClient(provider=provider, model=model.strip() or DEFAULT_MODELS[provider])


def _global_client() -> LLMClient | None:
    provider = config.LLM_PROVIDER
    if provider == "none":
        return None
    if provider == "auto":
        avail = available_providers()
        if not avail:
            return None
        provider = avail[0]
    if provider not in DEFAULT_MODELS:
        return None
    model = config.LLM_MODEL or DEFAULT_MODELS[provider]
    return LLMClient(provider=provider, model=model)


def resolve_for_agent(agent_key: str, explicit_only: bool = False) -> LLMClient | None:
    """Agent 별 LLM 클라이언트 결정.

    1) AGENT_LLM_<KEY> 오버라이드가 있으면 그 프로바이더:모델 사용
    2) 없으면 전역 설정(LLM_PROVIDER/LLM_MODEL) 사용
       (explicit_only=True 인 경우 1)이 없으면 None — 선택적 코멘트용 Agent 에서 사용)
    3) 해당 프로바이더의 API 키가 없으면 None (규칙기반 동작)
    """
    spec = config.AGENT_LLM_OVERRIDES.get(agent_key.upper(), "")
    client = _parse_spec(spec)
    if client is None:
        if explicit_only and not spec:
            return None
        client = _global_client()
    if client is None or not _api_key(client.provider):
        return None
    return client
