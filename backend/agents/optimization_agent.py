"""최적화 Agent.

입력분석 Agent(목표 포트폴리오)와 계좌분석 Agent(보유/현금)의 출력을 받아
QP 기반 최적화 엔진으로 추가 매수 ETF 조합을 계산하고,
목표와의 유사도 기준으로 추천 ETF 를 랭킹하여 출력한다.

후보 유니버스 = 검색Agent가 MCP로 찾은 후보 ETF ∪ 보유 ETF ∪ 안전자산 ETF
(퇴직연금 70% 규정 하에서 안전자산 ETF가 필요할 수 있으므로 항상 포함)
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from backend import config
from backend import database as db
from backend.agents.base import BaseAgent
from backend.optimizer.engine import EtfInfo, OptimizationInput, optimize


class OptimizationAgent(BaseAgent):
    name = "최적화Agent"
    llm_key = "OPTIMIZATION"

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        target: dict[str, float] = context.get("target_portfolio", {})
        owned: dict[str, float] = context.get("owned", {})
        cash: float = context.get("cash", 0)
        account_type: str = context.get("account_type", "pension")
        candidate_codes: set[str] = set(context.get("candidate_etf_codes", []))

        all_meta = db.all_etfs()

        # 안전자산은 시총 상위 N개만 후보에 포함 (실DB 는 채권형 ETF 가 매우 많음)
        safe_codes = [e["etf_code"] for e in all_meta if e["asset_class"] == "SAFE"]
        safe_codes = safe_codes[: config.MAX_SAFE_CANDIDATES]  # all_etfs 는 시총 내림차순

        universe_codes = candidate_codes | set(owned) | set(safe_codes)
        # 후보가 아예 없으면(검색 실패 등) 시총 상위 위험자산으로 보충
        if not candidate_codes:
            risk_top = [e["etf_code"] for e in all_meta if e["asset_class"] == "RISK"][:30]
            universe_codes |= set(risk_top)

        holdings = db.etf_holdings_map(sorted(universe_codes))

        universe = [
            EtfInfo(
                etf_code=e["etf_code"], etf_name=e["etf_name"],
                asset_class=e["asset_class"], close_price=int(e["close_price"]),
                holdings=holdings.get(e["etf_code"], {}),
            )
            for e in all_meta if e["etf_code"] in universe_codes
        ]

        result = optimize(OptimizationInput(
            target=target, owned=owned, cash=cash,
            account_type=account_type, etf_universe=universe,
        ))

        names = db.stock_names(sorted(set(result.achieved) | set(result.before) | set(target)))
        comparison = []
        for s in sorted(set(target) | set(result.achieved), key=lambda k: -target.get(k, 0)):
            comparison.append({
                "stock_code": s,
                "stock_name": names.get(s, s),
                "target": target.get(s, 0.0),
                "before": result.before.get(s, 0.0),
                "after": result.achieved.get(s, 0.0),
            })

        context["optimization"] = {
            "recommendations": [asdict(r) for r in result.recommendations],
            "before_error": result.before_error,
            "after_error": result.after_error,
            "spent": result.spent,
            "remaining_cash": result.remaining_cash,
            "risk_ratio_after": result.risk_ratio_after,
            "comparison": comparison,
            "converged": result.converged,
            "message": result.message,
        }
        self.log(
            context,
            f"최적화 완료: 추천 {len(result.recommendations)}개 ETF, "
            f"트래킹에러 {result.before_error}%p → {result.after_error}%p, "
            f"매수금액 {result.spent:,.0f}원",
        )

        # 선택적 LLM 코멘트: AGENT_LLM_OPTIMIZATION 을 명시했을 때만 호출
        llm = self.get_llm(explicit_only=True)
        if llm is not None and result.recommendations:
            try:
                rec_lines = "; ".join(
                    f"{r.etf_name} {r.shares}주 {r.amount:,.0f}원 (유사도 {r.similarity})"
                    for r in result.recommendations
                )
                comment = await llm.complete(
                    prompt=(
                        "다음 ETF 추가매수 최적화 결과의 배분 근거를 1~2문장으로 "
                        "설명하세요 (한국어, 사실 기반, 투자권유 아님).\n"
                        f"추천: {rec_lines}\n"
                        f"트래킹에러 {result.before_error}%p → {result.after_error}%p, "
                        f"매수 후 위험자산 {result.risk_ratio_after * 100:.1f}%"
                    ),
                    max_tokens=400,
                )
                context["optimization"]["ai_comment"] = comment.strip()
                context["optimization"]["ai_provider"] = llm.label
                self.log(context, f"LLM 배분 설명 생성 ({llm.label})")
            except Exception as exc:
                self.log(context, f"LLM 배분 설명 실패({llm.label}: {exc.__class__.__name__}) → 생략")
        return context
