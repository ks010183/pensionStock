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

        # 0) 구조화 입력 (프론트 자동완성: [{symbol, name, weight, kind}])
        #    — symbol 이 명시된 항목은 심볼 마스터로 검증 후 주식/ETF 를 분리 처리
        if isinstance(raw, list) and any(isinstance(d, dict) and d.get("symbol") for d in raw):
            return await self._run_structured(context, raw)

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
        context["etf_targets"] = {}
        context["target_detail"] = resolved
        context["input_warnings"] = warnings
        self.log(context, f"목표 포트폴리오 확정: {len(target)}종목, 합계 {total:.1f}%")
        return context

    async def _run_structured(self, context: dict[str, Any], raw: list[dict]) -> dict[str, Any]:
        """자동완성 기반 구조화 입력 처리: 주식 목표와 ETF 목표를 분리한다.

        - 주식(kind='stock'): target_portfolio {티커: %} — 최적화 목적함수의 목표 비중
        - ETF (kind='etf')  : etf_targets {티커: %} — 최적화Agent 가 구성종목으로
          룩스루 전개(구성 데이터 없으면 해당 ETF 직접 매수 목표로 처리)
        """
        target: dict[str, float] = {}
        etf_targets: dict[str, float] = {}
        resolved: list[dict] = []
        warnings: list[str] = []

        for d in raw:
            sym = str(d.get("symbol") or "").strip()
            weight = float(d.get("weight") or 0)
            if not sym or weight <= 0:
                continue
            info = db.lookup_symbol(sym)
            if info is None:
                warnings.append(f"심볼 '{sym}' 을 DB에서 찾을 수 없습니다.")
                continue
            kind = d.get("kind") or ("etf" if info["is_etf_like"] else "stock")
            name = d.get("name") or info["name"]

            if kind == "etf":
                etf_targets[sym] = etf_targets.get(sym, 0) + weight
            else:
                target[sym] = target.get(sym, 0) + weight
                if db.held_etf_count(sym) == 0:
                    # infostock_theme 기반 같은 테마 대체 종목 추천
                    alts = db.infostock_alternatives(sym, name)
                    if alts:
                        warnings.append(
                            f"'{name}' 을 편입한 ETF가 없어 목표 달성이 어렵습니다. "
                            f"같은 테마 대체 후보: "
                            + ", ".join(f"{a['name']}({a['themes']})" for a in alts[:4])
                        )
                        context.setdefault("target_alternatives", {})[sym] = {
                            "name": name, "alternatives": alts,
                        }
                    else:
                        warnings.append(
                            f"'{name}' 을 편입한 ETF가 없어 목표 달성이 어렵습니다. "
                            "유사 종목/테마 ETF를 참고하세요."
                        )
                else:
                    # 편입은 되어 있으나 최대 편입비중이 목표보다 작은 경우 → 분할 보완 안내
                    max_w = db.max_etf_weight(sym)
                    if 0 < max_w < weight:
                        alts = db.infostock_alternatives(sym, name)
                        msg = (
                            f"'{name}' 목표 {weight}% 는 ETF 내 최대 편입비중({max_w}%)을 "
                            f"초과해 단독으로는 달성할 수 없습니다."
                        )
                        if alts:
                            msg += (" 같은 테마 보완 후보: "
                                    + ", ".join(f"{a['name']}({a['themes']})" for a in alts[:4]))
                            context.setdefault("target_alternatives", {})[sym] = {
                                "name": name, "alternatives": alts,
                                "max_etf_weight": max_w, "reason": "insufficient",
                            }
                        warnings.append(msg)
            resolved.append({
                "stock_code": sym,
                "stock_name": name,
                "kind": kind,
                "market": info["market"],
                "sec_label": info["sec_label"],
                "sector_name": db.dominant_sector_for_stock(sym) if kind == "stock" else None,
                "weight": weight,
            })

        total = sum(target.values()) + sum(etf_targets.values())
        if total > 100:
            warnings.append(f"목표 비중 합계가 {total:.1f}%로 100%를 초과합니다.")
        if not target and not etf_targets:
            warnings.append("유효한 목표 종목이 없습니다.")

        context["target_portfolio"] = target
        context["etf_targets"] = etf_targets
        context["target_detail"] = resolved
        context["input_warnings"] = warnings
        self.log(
            context,
            f"구조화 입력 확정: 주식 {len(target)}종목 + ETF {len(etf_targets)}종목, "
            f"합계 {total:.1f}%",
        )
        return context
