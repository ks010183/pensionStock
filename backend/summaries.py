"""분석 요약 생성 — 희망 포트폴리오 / 보유 ETF.

항상 규칙기반 요약을 생성하고, LLM 이 배정되어 있으면 자연스러운 문장으로 보강한다.
(희망 포트폴리오 요약 = 입력분석 Agent 의 LLM, 보유 ETF 요약 = 계좌분석 Agent 의 LLM)
"""
from __future__ import annotations

from typing import Any

from backend import database as db
from backend.llm import resolve_for_agent

KRW = "{:,.0f}"


async def _polish(agent_key: str, rule_text: str, facts: str) -> tuple[str, str | None]:
    """LLM 이 있으면 사실 기반으로 요약문을 다듬고, 없으면 규칙기반 텍스트 반환."""
    llm = resolve_for_agent(agent_key)
    if llm is None:
        return rule_text, None
    try:
        out = await llm.complete(
            prompt=(
                "다음 사실만 사용해 고객에게 보여줄 2~4문장의 한국어 분석 요약을 작성하세요. "
                "과장/추측/투자권유 없이 사실 기반으로.\n\n" + facts
            ),
            system="당신은 연금 포트폴리오 입력 내용을 요약하는 어시스턴트입니다.",
            max_tokens=500,
        )
        return out.strip(), llm.label
    except Exception:
        return rule_text, None


async def portfolio_summary(entries: list[dict]) -> dict[str, Any]:
    """희망 포트폴리오 [{symbol, name, weight, kind}] 분석 요약."""
    if not entries:
        return {"summary": "입력된 목표 종목이 없습니다.", "provider": None}

    stocks = [e for e in entries if e.get("kind") != "etf"]
    etfs = [e for e in entries if e.get("kind") == "etf"]
    total = sum(float(e.get("weight") or 0) for e in entries)
    top = max(entries, key=lambda e: float(e.get("weight") or 0))

    # 섹터/시장 분포
    sectors: dict[str, float] = {}
    us_weight = 0.0
    unachievable: list[str] = []
    for e in stocks:
        w = float(e.get("weight") or 0)
        sec = db.dominant_sector_for_stock(e["symbol"]) or "기타"
        sectors[sec] = sectors.get(sec, 0) + w
        info = db.lookup_symbol(e["symbol"])
        if info and info["market"] == "US":
            us_weight += w
        if db.held_etf_count(e["symbol"]) == 0:
            unachievable.append(e["name"])
    top_sectors = sorted(sectors.items(), key=lambda kv: -kv[1])[:3]

    parts = [
        f"목표 {len(entries)}종목(주식 {len(stocks)}, ETF {len(etfs)}), 합계 {total:.1f}%."
    ]
    parts.append(f"최대 비중은 {top['name']} {float(top.get('weight') or 0):.1f}%.")
    if top_sectors:
        parts.append(
            "주요 섹터: " + ", ".join(f"{s} {w:.1f}%" for s, w in top_sectors) + "."
        )
    if us_weight > 0:
        parts.append(f"해외(미국) 종목 비중 {us_weight:.1f}%.")
    if total < 100:
        parts.append(f"잔여 {100 - total:.1f}% 는 현금/안전자산으로 배분됩니다.")
    if unachievable:
        parts.append(
            "주의: " + ", ".join(unachievable) + " 은(는) 편입 ETF 가 없어 달성이 어렵습니다."
        )
    rule_text = " ".join(parts)

    facts = (
        f"목표 종목: {[(e['name'], e.get('weight')) for e in entries]}\n"
        f"합계 {total:.1f}%, 섹터 분포 {top_sectors}, 미국 비중 {us_weight:.1f}%, "
        f"달성 불가 종목 {unachievable or '없음'}"
    )
    summary, provider = await _polish("INPUT", rule_text, facts)
    return {"summary": summary, "provider": provider}


async def holdings_summary(holdings: list[dict], account_type: str = "pension",
                           cash: float = 0) -> dict[str, Any]:
    """보유 ETF [{etf_code, amount}] 분석 요약 (룩스루 노출 포함)."""
    if not holdings:
        return {"summary": "보유 중인 ETF가 없습니다. 현금만으로 최적화가 진행됩니다.",
                "provider": None}

    owned = {h["etf_code"]: float(h["amount"]) for h in holdings}
    meta = {e["etf_code"]: e for e in db.all_etfs() if e["etf_code"] in owned}
    hold_map = db.etf_holdings_map(list(owned))

    total_etf = sum(owned.values())
    total = total_etf + cash
    risk = sum(a for c, a in owned.items()
               if meta.get(c, {}).get("asset_class") == "RISK")
    exposure: dict[str, float] = {}
    for code, amt in owned.items():
        for s, w in hold_map.get(code, {}).items():
            exposure[s] = exposure.get(s, 0) + amt * w / 100.0
    names = db.stock_names(list(exposure))
    top_exp = sorted(exposure.items(), key=lambda kv: -kv[1])[:5]

    parts = [
        f"보유 ETF {len(owned)}개, 평가액 {KRW.format(total_etf)}원"
        + (f" + 현금 {KRW.format(cash)}원" if cash else "") + "."
    ]
    if total > 0:
        risk_pct = risk / total * 100
        parts.append(f"위험자산 비중 {risk_pct:.1f}%"
                     + (f" (퇴직연금 한도 70%, 여유 {70 - risk_pct:.1f}%p)."
                        if account_type == "pension" else "."))
    if top_exp:
        parts.append(
            "룩스루 상위 노출: "
            + ", ".join(f"{names.get(s, s)} {v / total * 100:.1f}%" for s, v in top_exp)
            + "."
        )
    safe_names = [meta[c]["etf_name"] for c in owned
                  if meta.get(c, {}).get("asset_class") == "SAFE"]
    if safe_names:
        parts.append("안전자산 ETF: " + ", ".join(safe_names) + ".")
    rule_text = " ".join(parts)

    facts = (
        f"보유: {[(meta.get(c, {}).get('etf_name', c), a) for c, a in owned.items()]}\n"
        f"현금 {cash:,.0f}원, 위험자산 {risk:,.0f}원, "
        f"상위 노출 {[(names.get(s, s), round(v / total * 100, 1)) for s, v in top_exp] if total else []}\n"
        f"계좌유형: {'퇴직연금(위험자산 70% 한도)' if account_type == 'pension' else '개인연금'}"
    )
    summary, provider = await _polish("ACCOUNT", rule_text, facts)
    return {"summary": summary, "provider": provider}
