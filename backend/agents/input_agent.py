"""입력분석 Agent.

유저가 입력한 희망 포트폴리오(자유 텍스트 또는 구조화 리스트)를 상세화 분석하여
{종목코드: 목표비중%} 형태로 정규화해 출력한다.

LLM 파싱: 이 Agent 에 배정된 프로바이더(anthropic/openai/gemini — AGENT_LLM_INPUT
또는 전역 LLM_PROVIDER)로 자유 텍스트를 파싱하고, LLM 이 없거나 실패하면
규칙기반(정규식) 파서로 폴백한다. 두 경우 모두 DB 종목 매칭으로 검증한다.
"""
from __future__ import annotations

import json
import re
from typing import Any

from backend import database as db
from backend.agents.base import BaseAgent
from backend.llm import LLMClient

_PATTERN = re.compile(r"([가-힣A-Za-z0-9&\.\-]+)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*%?")

_PARSE_SYSTEM = (
    "당신은 한국 주식 포트폴리오 입력을 구조화하는 파서입니다. "
    "반드시 JSON 배열만 출력하세요. 다른 텍스트를 붙이지 마세요."
)


def _parse_with_rules(text: str) -> list[tuple[str, float]]:
    """'삼성전자 20%, 현대차 10%' 같은 텍스트를 (이름, 비중) 리스트로 파싱."""
    pairs: list[tuple[str, float]] = []
    for name, pct in _PATTERN.findall(text):
        try:
            pairs.append((name.strip(), float(pct)))
        except ValueError:
            continue
    return pairs


async def _parse_with_llm(llm: LLMClient, text: str) -> list[tuple[str, float]]:
    """LLM 으로 자유 텍스트에서 (종목명, 비중%) 목록을 추출."""
    raw = await llm.complete(
        prompt=(
            "다음 문장에서 한국 주식 종목명과 희망 비중(%)을 추출해 "
            'JSON 배열로만 답하세요. 형식: [{"name": "삼성전자", "weight": 20}]\n\n'
            f"문장: {text}"
        ),
        system=_PARSE_SYSTEM,
        max_tokens=1024,
    )
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return []
    return [(d["name"], float(d["weight"])) for d in json.loads(m.group(0))]


class InputAnalysisAgent(BaseAgent):
    name = "입력분석Agent"
    llm_key = "INPUT"

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        raw = context.get("desired_portfolio")

        # 1) 파싱: 구조화 입력([{name, weight}]) 또는 자유 텍스트
        if isinstance(raw, list):
            pairs = [(d["name"], float(d["weight"])) for d in raw]
            self.log(context, f"구조화 입력 {len(pairs)}건 수신")
        else:
            text = str(raw or "")
            llm = self.get_llm()
            pairs = []
            if llm is not None:
                try:
                    pairs = await _parse_with_llm(llm, text)
                    self.log(context, f"LLM 파싱 성공 ({llm.label}, {len(pairs)}건)")
                except Exception as exc:  # LLM 실패 시 규칙기반 폴백
                    pairs = []
                    self.log(
                        context,
                        f"LLM 파싱 실패({llm.label}: {exc.__class__.__name__}) → 규칙기반 폴백",
                    )
            if not pairs:
                pairs = _parse_with_rules(text)
                if llm is None:
                    self.log(context, f"규칙기반 파싱 {len(pairs)}건 (LLM 미설정)")
                else:
                    self.log(context, f"규칙기반 파싱 {len(pairs)}건")

        # 2) DB 종목 매칭 + 검증
        target: dict[str, float] = {}
        resolved: list[dict] = []
        unmatched: list[str] = []
        for name, weight in pairs:
            stock = db.find_stock(name)
            if stock:
                target[stock["stock_code"]] = target.get(stock["stock_code"], 0) + weight
                resolved.append({
                    "stock_code": stock["stock_code"],
                    "stock_name": stock["stock_name"],
                    "sector_name": stock.get("sector_name"),
                    "weight": weight,
                })
            else:
                unmatched.append(name)

        total = sum(target.values())
        warnings: list[str] = []
        if unmatched:
            warnings.append(f"DB에서 찾을 수 없는 종목: {', '.join(unmatched)}")
        if total > 100:
            warnings.append(f"목표 비중 합계가 {total:.1f}%로 100%를 초과합니다.")
        if not target:
            warnings.append("유효한 목표 종목이 없습니다.")

        context["target_portfolio"] = target
        context["target_detail"] = resolved
        context["input_warnings"] = warnings
        self.log(context, f"목표 포트폴리오 확정: {len(target)}종목, 합계 {total:.1f}%")
        return context
