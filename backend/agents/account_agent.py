"""계좌분석 Agent.

현재 계좌의 보유 ETF들을 분석하여 룩스루(look-through) 종목 노출 합계,
위험/안전자산 비중, 계좌 총액 등을 출력한다.
"""
from __future__ import annotations

from typing import Any

from backend import database as db
from backend.agents.base import BaseAgent


class AccountAnalysisAgent(BaseAgent):
    name = "계좌분석Agent"
    llm_key = "ACCOUNT"

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        account = context.get("account", {})
        owned: dict[str, float] = {
            h["etf_code"]: float(h["amount"]) for h in account.get("holdings", [])
        }
        cash = float(account.get("cash", 0))
        account_type = account.get("account_type", "pension")

        etf_meta = {e["etf_code"]: e for e in db.all_etfs()}
        holdings_map = db.etf_holdings_map(list(owned) or None)

        total_etf = sum(owned.values())
        total_value = total_etf + cash
        risk_value = sum(a for c, a in owned.items()
                         if etf_meta.get(c, {}).get("asset_class") == "RISK")

        # 룩스루 종목 노출 합계 (계좌총액 대비 %)
        exposure: dict[str, float] = {}
        for code, amount in owned.items():
            for stock, w in holdings_map.get(code, {}).items():
                exposure[stock] = exposure.get(stock, 0) + amount * (w / 100.0)
        exposure_pct = {
            s: round(v / total_value * 100, 3) for s, v in exposure.items()
        } if total_value > 0 else {}

        names = db.stock_names(list(exposure_pct))
        exposure_detail = sorted(
            [{"stock_code": s, "stock_name": names.get(s, s), "weight": w}
             for s, w in exposure_pct.items()],
            key=lambda d: d["weight"], reverse=True,
        )

        owned_detail = [{
            "etf_code": c,
            "etf_name": etf_meta.get(c, {}).get("etf_name", c),
            "asset_class": etf_meta.get(c, {}).get("asset_class", "?"),
            "amount": a,
            "weight": round(a / total_value * 100, 2) if total_value else 0,
        } for c, a in owned.items()]

        context["account_analysis"] = {
            "account_type": account_type,
            "total_value": total_value,
            "cash": cash,
            "etf_value": total_etf,
            "risk_value": risk_value,
            "risk_ratio": round(risk_value / total_value, 4) if total_value else 0,
            "owned_detail": owned_detail,
            "exposure": exposure_pct,          # {stock_code: %}
            "exposure_detail": exposure_detail,
        }
        context["owned"] = owned
        context["cash"] = cash
        context["account_type"] = account_type

        # 선택적 LLM 코멘트: AGENT_LLM_ACCOUNT 를 명시했을 때만 호출 (지연 최소화)
        llm = self.get_llm(explicit_only=True)
        if llm is not None and total_value > 0:
            try:
                top = ", ".join(
                    f"{d['stock_name']} {d['weight']}%" for d in exposure_detail[:5]
                ) or "없음"
                comment = await llm.complete(
                    prompt=(
                        "다음 연금계좌 구성을 1~2문장으로 요약하세요 (한국어, 사실 기반).\n"
                        f"계좌유형: {'퇴직연금' if account_type == 'pension' else '개인연금'}, "
                        f"총액 {total_value:,.0f}원 (ETF {total_etf:,.0f} / 현금 {cash:,.0f}), "
                        f"위험자산 {risk_value / total_value * 100:.1f}%, "
                        f"룩스루 상위 노출: {top}"
                    ),
                    max_tokens=300,
                )
                context["account_analysis"]["ai_comment"] = comment.strip()
                context["account_analysis"]["ai_provider"] = llm.label
                self.log(context, f"LLM 계좌 요약 생성 ({llm.label})")
            except Exception as exc:
                self.log(context, f"LLM 계좌 요약 실패({llm.label}: {exc.__class__.__name__}) → 생략")
        self.log(
            context,
            f"계좌총액 {total_value:,.0f}원 (ETF {total_etf:,.0f} + 현금 {cash:,.0f}), "
            f"위험자산 {risk_value/total_value*100 if total_value else 0:.1f}%, "
            f"룩스루 노출 {len(exposure_pct)}종목",
        )
        return context
