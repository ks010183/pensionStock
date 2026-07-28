"""FastAPI 백엔드 — 멀티 Agent ETF 포트폴리오 최적화 API.

실행:  uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger("uvicorn.error")

from backend import database as db
from backend.agents.orchestrator import run_pipeline

app = FastAPI(title="ETF Portfolio Optimizer", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 개발용 — 운영 시 도메인 제한 필요
    allow_methods=["*"],
    allow_headers=["*"],
)


class HoldingIn(BaseModel):
    etf_code: str
    amount: float = Field(gt=0, description="평가금액(원)")


class AccountIn(BaseModel):
    account_type: str = Field("pension", pattern="^(pension|personal)$")
    cash: float = Field(ge=0, description="매수가능 현금(원)")
    holdings: list[HoldingIn] = []


class RecommendIn(BaseModel):
    desired_portfolio: str | list[dict] = Field(
        description='자유 텍스트("삼성전자 20%, 현대차 10%") 또는 [{"name":..,"weight":..}]'
    )
    account: AccountIn


def _flatten_exception(exc: BaseException) -> list[BaseException]:
    """ExceptionGroup(TaskGroup) 안의 실제 원인 예외들을 재귀적으로 풀어낸다."""
    if isinstance(exc, BaseExceptionGroup):
        out: list[BaseException] = []
        for sub in exc.exceptions:
            out.extend(_flatten_exception(sub))
        return out
    if exc.__cause__ is not None and exc.__cause__ is not exc:
        return [exc, *_flatten_exception(exc.__cause__)]
    return [exc]


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """예기치 못한 오류를 로그에 전체 트레이스백으로 남기고, 근본 원인을 응답에 포함.

    docker compose logs backend 로 전체 트레이스백을 확인할 수 있다.
    """
    logger.error("Unhandled error on %s %s\n%s",
                 request.method, request.url.path,
                 "".join(traceback.format_exception(exc)))
    causes = " | ".join(
        f"{e.__class__.__name__}: {e}" for e in _flatten_exception(exc)
    )
    return JSONResponse(status_code=500, content={"detail": causes})


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/health/db")
def health_db():
    """DB 연결 상태 점검 (문제 발생 시 원인 메시지 반환)."""
    try:
        db.all_etfs()
        return {"status": "ok", "db": "connected"}
    except Exception as exc:
        return JSONResponse(status_code=503,
                            content={"status": "error", "db": f"{exc.__class__.__name__}: {exc}"})


@app.get("/api/etfs")
def list_etfs():
    """전체 ETF 목록 (계좌 보유 입력용)."""
    return db.all_etfs()


@app.get("/api/stocks/search")
def search_stocks(q: str):
    """종목 검색 (입력 자동완성용)."""
    stock = db.find_stock(q)
    return [stock] if stock else []


@app.post("/api/recommend")
async def recommend(body: RecommendIn):
    """멀티 Agent 파이프라인 실행: 입력분석 → 계좌분석 → 검색(MCP) → 최적화 → 평가."""
    context = await run_pipeline(
        desired_portfolio=body.desired_portfolio,
        account=body.account.model_dump(),
    )
    return {
        "target_detail": context.get("target_detail", []),
        "account_analysis": context.get("account_analysis", {}),
        "search_results": context.get("search_results", {}),
        "search_comment": context.get("search_comment"),
        "optimization": context.get("optimization", {}),
        "evaluation": context.get("evaluation", {}),
        "trace": context.get("trace", []),
    }
