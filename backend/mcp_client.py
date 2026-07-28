"""MCP 클라이언트 — 검색Agent가 ETF DB MCP 서버(stdio)에 연결하는 헬퍼."""
from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

_SERVER_PATH = Path(__file__).resolve().parent / "mcp_server" / "etf_mcp_server.py"

# MCP SDK 는 보안상 서브프로세스에 최소 환경변수(PATH 등)만 전달한다.
# DB 접속 정보와 API 키는 명시적으로 넘겨야 한다 — 이것을 빠뜨리면
# 서브프로세스가 기본값(127.0.0.1)으로 DB 접속을 시도해 Docker 등에서 실패한다.
_PASS_ENV_PREFIXES = ("ETF_DB_", "AGENT_LLM_")
_PASS_ENV_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
                  "GOOGLE_API_KEY", "LLM_PROVIDER", "LLM_MODEL")


def _server_env() -> dict[str, str]:
    env = dict(get_default_environment())
    for key, value in os.environ.items():
        if key.startswith(_PASS_ENV_PREFIXES) or key in _PASS_ENV_KEYS:
            env[key] = value
    return env


@asynccontextmanager
async def etf_mcp_session():
    """ETF DB MCP 서버를 stdio 서브프로세스로 기동하고 세션을 연다."""
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(_SERVER_PATH)],
        env=_server_env(),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_tool(session: ClientSession, name: str, arguments: dict) -> list | dict:
    """MCP 도구를 호출하고 JSON 파싱된 결과를 반환한다.

    도구 실행 오류(isError)나 JSON 이 아닌 응답은 예외로 승격시킨다 —
    호출측(검색Agent)이 이를 잡아 DB 폴백으로 전환하고 원인을 trace 에 남긴다.
    """
    result = await session.call_tool(name, arguments)
    texts = [c.text for c in result.content if getattr(c, "type", "") == "text"]
    joined = "\n".join(texts).strip()
    if getattr(result, "isError", False):
        raise RuntimeError(f"MCP 도구 '{name}' 실행 오류: {joined[:500] or '(내용 없음)'}")
    if not joined:
        return []
    try:
        return json.loads(joined)
    except json.JSONDecodeError:
        raise RuntimeError(f"MCP 도구 '{name}' 응답이 JSON 이 아님: {joined[:500]}")
