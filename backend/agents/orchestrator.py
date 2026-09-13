"""멀티 Agent 오케스트레이터.

파이프라인: 입력분석 → 계좌분석 → 검색(MCP) → 최적화 → 평가
각 Agent 는 공유 context 에 자신의 출력을 기록하고, trace 에 수행 로그를 남긴다.
"""
from __future__ import annotations

from typing import Any

from backend.agents.account_agent import AccountAnalysisAgent
from backend.agents.evaluation_agent import EvaluationAgent
from backend.agents.input_agent import InputAnalysisAgent
from backend.agents.optimization_agent import OptimizationAgent
from backend.agents.search_agent import SearchAgent

PIPELINE = [
    InputAnalysisAgent(),
    AccountAnalysisAgent(),
    SearchAgent(),
    OptimizationAgent(),
    EvaluationAgent(),
]


async def run_pipeline(desired_portfolio, account: dict) -> dict[str, Any]:
    context: dict[str, Any] = {
        "desired_portfolio": desired_portfolio,
        "account": account,
        "trace": [],
    }
    for agent in PIPELINE:
        context = await agent.run(context)
    return context
